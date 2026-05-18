# -*- coding: utf-8 -*-
import os
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsProject

from ..config.LogUtils import LogUtils
from .ReportGenerationService import ReportGenerationService
from ...utils.ExplorerUtils import ExplorerUtils
from ...utils.ToolKeys import ToolKey
from ...utils.mrk.MetadataFields import MetadataFields
from ...utils.mrk.CustomPhotosFieldsUtil import CustomPhotosFieldsUtil
from ...utils.vector.VectorLayerGeometry import VectorLayerGeometry


class PhotoFolderVectorizationService:
    """
    [LEGADO - MANTIDO PARA COMPATIBILIDADE]
    
    Gera camada vetorial a partir de pasta de fotos (sem MRK).
    Agora delega para PhotoMetadata.run_pipeline() para o processamento
    de metadados, mantendo apenas a lógica de vetorização e schema.
    
    Novos fluxos devem usar PhotoEnrichmentStep + JsonVectorizationStep diretamente.
    """
    DJI_PHOTO_RE = re.compile(r"_(\d{4})_[A-Z]\.JPG$", re.IGNORECASE)
    FLIGHT_FOLDER_RE = re.compile(
        r"DJI_\d+_(?P<flight_number>\d+?)_(?P<flight_name>[^_\\\/]+)",
        re.IGNORECASE,
    )

    def __init__(self, tool_key: str = ToolKey.REPORT_METADATA):
        self.tool_key = tool_key
        self.logger = LogUtils(tool=tool_key, class_name="PhotoFolderVectorizationService")

    @staticmethod
    def _to_float(value: Any):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace("+", "")
        if text in ("", "None", "null"):
            return None
        try:
            return float(text)
        except Exception:
            return None

    @staticmethod
    def _normalize_attr_value(value: Any) -> Any:
        if isinstance(value, (list, tuple, dict)):
            try:
                return json.dumps(value, ensure_ascii=False)
            except Exception:
                return str(value)
        return value

    def _build_output_record_from_catalog(self, canonical: Dict[str, Any]) -> Dict[str, Any]:
        output_record: Dict[str, Any] = {}
        mrk_keys = set(MetadataFields.mrk_keys())
        for key in MetadataFields.all_fields().keys():
            if key in mrk_keys:
                continue
            attr_name = MetadataFields.resolve_output_name(key)
            output_record[attr_name] = self._normalize_attr_value(canonical.get(key))
        return output_record

    @staticmethod
    def _filter_out_mrk_fields(record: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(record, dict):
            return {}

        mrk_keys = set(MetadataFields.mrk_keys())
        filtered: Dict[str, Any] = {}
        for key, value in record.items():
            normalized_key = MetadataFields.resolve_key(str(key))
            if normalized_key in mrk_keys:
                continue
            filtered[key] = value
        return filtered

    def _list_photo_files(self, base_folder: str, recursive: bool) -> List[str]:
        output = []
        if not os.path.isdir(base_folder):
            return output

        if recursive:
            walker = os.walk(base_folder)
            for root, _, files in walker:
                for name in files:
                    if name.lower().endswith((".jpg", ".jpeg")):
                        output.append(os.path.join(root, name))
        else:
            for name in os.listdir(base_folder):
                full_path = os.path.join(base_folder, name)
                if os.path.isfile(full_path) and name.lower().endswith((".jpg", ".jpeg")):
                    output.append(full_path)

        return sorted(output)

    def generate_from_folder(
        self,
        base_folder: str,
        recursive: bool = True,
        generate_report: bool = True,
        layer_name: str = "Fotos_Sem_MRK",
    ) -> Dict[str, Any]:
        """
        Gera camada vetorial e relatório a partir de pastas de fotos (sem MRK).
        
        Utiliza PhotoMetadata.run_pipeline() para todo o processamento
        de metadados (esqueleto → EXIF → XMP → custom fields).
        Apenas a vetorização e schema são feitos aqui.
        """
        if not os.path.isdir(base_folder):
            raise ValueError(f"Pasta invalida: {base_folder}")

        files = self._list_photo_files(base_folder, recursive)
        self.logger.info(
            "Iniciando vetorizacao por fotos sem MRK",
            data={"base_folder": base_folder, "recursive": recursive, "total_files": len(files)},
        )

        # Utiliza PhotoMetadata.run_pipeline() para processar metadados
        from ...utils.mrk.PhotoMetadata import PhotoMetadata

        records, quality = PhotoMetadata.run_pipeline(
            base_folder=base_folder,
            points=None,
            recursive=recursive,
            tool_key=self.tool_key,
            enable_mrk=False,
            enable_exif=True,
            enable_xmp=True,
            enable_custom_fields=True,
        )

        if not records:
            self.logger.warning("Nenhum registro gerado pelo pipeline", data={"quality": quality})
            return {
                "layer": None,
                "json_path": None,
                "report_payload": None,
                "quality": quality,
                "total_points": 0,
                "total_files": len(files),
            }

        # Converte records para formato de saída (remove campos MRK)
        key_to_json_key = {
            key: field.key.value
            for key, field in MetadataFields.all_fields().items()
            if field.key is not None
        }
        x_geom_key = MetadataFields.resolve_output_name("GpsLongitude")
        y_geom_key = MetadataFields.resolve_output_name("GpsLatitude")

        points = []
        raw_records = {}
        for record in records:
            canonical = self._filter_out_mrk_fields(record)
            file_key = canonical.get("File") or os.path.basename(canonical.get("Path", ""))
            raw_records[file_key] = canonical

            lat = self._to_float(canonical.get("GpsLatitude"))
            lon = self._to_float(canonical.get("GpsLongitude"))
            if lat is None or lon is None:
                continue

            output_record = self._build_output_record_from_catalog(canonical)
            output_record[x_geom_key] = lon
            output_record[y_geom_key] = lat
            points.append(output_record)

        schema = []
        if points:
            sample = points[0]
            for key, value in sample.items():
                if key in ("Lat", "Lon"):
                    continue
                if isinstance(value, (int, float)):
                    qtype = QVariant.Double
                else:
                    qtype = QVariant.String
                schema.append((key, qtype, key))

        layer = None
        if points:
            layer = VectorLayerGeometry.create_point_layer_from_dicts(
                points=points,
                name=layer_name,
                field_specs=schema,
                geometry_keys=(x_geom_key, y_geom_key),
                tool_key=self.tool_key,
            )
            if layer and layer.isValid():
                QgsProject.instance().addMapLayer(layer)

        # Gera JSON dump
        full_dump_payload = {
            "base_folder": base_folder,
            "recursive": recursive,
            "points_total": len(points),
            "quality": quality,
            "groups": {
                base_folder: {
                    "points": len(points),
                    "indexed": len(raw_records),
                    "raw_records": raw_records,
                }
            },
        }

        json_path = ExplorerUtils.create_temp_json(
            full_dump_payload,
            tool_key=self.tool_key,
            prefix="PFM",
            subfolder=os.path.join(
                ExplorerUtils.REPORTS_TEMP_FOLDER,
                ExplorerUtils.REPORTS_JSON_FOLDER,
            ),
            file_stem_hint=ExplorerUtils.build_report_json_stem(
                base_folder=base_folder,
                points_total=len(points),
            ),
        )

        report_payload = None
        if generate_report and json_path:
            report_payload = ReportGenerationService(tool_key=self.tool_key).generate_from_json(
                json_path
            )

        if quality["with_coords"] == 0:
            self.logger.warning(
                "Nenhuma foto com coordenada valida encontrada",
                data={"quality": quality, "base_folder": base_folder},
            )

        payload = {
            "layer": layer,
            "json_path": json_path,
            "report_payload": report_payload,
            "quality": quality,
            "total_points": len(points),
            "total_files": len(files),
        }
        self.logger.info("Vetorizacao sem MRK concluida", data=payload)
        return payload

    def extract_to_json(
        self,
        base_folder: str,
        recursive: bool = True,
        tool_key: str = None,
        selected_fields: List[str] = None,
    ) -> str:
        """
        [NOVO] Extrai metadata das fotos e salva JSON v2.0 via pipeline.
        
        Utiliza PhotoMetadata.run_pipeline() com todas as etapas exceto MRK.
        source: "photo"
        
        Returns:
            Caminho do JSON gerado
        """
        from ...utils.JsonUtil import JsonUtil
        from ...utils.mrk.PhotoMetadata import PhotoMetadata
        from ...core.enum import MetadataFieldKey

        if tool_key:
            self.tool_key = tool_key
            self.logger = LogUtils(tool=tool_key, class_name="PhotoFolderVectorizationService")

        if not os.path.isdir(base_folder):
            raise ValueError(f"Pasta invalida: {base_folder}")

        files = self._list_photo_files(base_folder, recursive)
        self.logger.info(
            "Iniciando extração de metadados para JSON v2.0 via pipeline",
            data={"base_folder": base_folder, "recursive": recursive, "total_files": len(files)},
        )

        # Usa o pipeline para processar metadados
        records, quality = PhotoMetadata.run_pipeline(
            base_folder=base_folder,
            points=None,
            recursive=recursive,
            tool_key=self.tool_key,
            enable_mrk=False,
            enable_exif=True,
            enable_xmp=True,
            enable_custom_fields=True,
        )

        if not records:
            self.logger.warning("Nenhum registro gerado pelo pipeline")
            return ""

        # Converte records para JSON v2.0
        key_to_json_key = {
            key: field.key.value
            for key, field in MetadataFields.all_fields().items()
            if field.key is not None
        }

        all_records = []
        for record in records:
            # Remove campos MRK
            filtered = self._filter_out_mrk_fields(record)

            # Converter para chaves PascalCase
            json_record = {}
            for key, value in filtered.items():
                if isinstance(key, MetadataFieldKey):
                    json_record[key.value] = value
                    continue

                canonical_key = MetadataFields.resolve_key(str(key))
                mapped_key = key_to_json_key.get(canonical_key, canonical_key)
                json_record[mapped_key] = value

            # Filtrar campos selecionados se especificado
            if selected_fields:
                skip_keys = {
                    MetadataFieldKey.COORD_SOURCE.value,
                    MetadataFieldKey.QUALITY_FLAG.value,
                }
                filtered_record = {
                    k: v for k, v in json_record.items()
                    if k in selected_fields or k in skip_keys
                }
                json_record = filtered_record

            all_records.append(json_record)

        # Gera timestamps
        from ...utils.mrk.PhotoMetadata import PhotoMetadata
        timestamps = dict(PhotoMetadata.get_timestamps())

        # Constroi JSON v2.0
        json_data = JsonUtil.build(
            records=all_records,
            source="photo",
            base_folder=base_folder,
            tool_key=self.tool_key,
            recursive=recursive,
            timestamps=timestamps if timestamps else None,
        )

        # Adiciona quality stats
        json_data["quality"] = quality

        # Salva JSON
        json_path = ExplorerUtils.create_temp_json(
            json_data,
            tool_key=self.tool_key,
            prefix="PFM",
            subfolder=os.path.join(
                ExplorerUtils.REPORTS_TEMP_FOLDER,
                ExplorerUtils.REPORTS_JSON_FOLDER,
            ),
            file_stem_hint=ExplorerUtils.build_report_json_stem(
                base_folder=base_folder,
                points_total=len(all_records),
            ),
        )

        self.logger.info(
            "Extração para JSON v2.0 concluída via pipeline",
            data={
                "json_path": json_path,
                "total_records": len(all_records),
                "quality": quality,
            },
        )

        return json_path