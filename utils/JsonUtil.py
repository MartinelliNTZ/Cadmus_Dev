# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


class JsonUtil:
    """
    Constroi o JSON e tambem e responsavel por manipulacao do mesmo.
    """

    @staticmethod
    def build(
        records: List[Dict[str, Any]],
        source: str,
        base_folder: str,
        tool_key: str,
        recursive: bool = False,
        timestamps: Optional[Dict[str, str]] = None,
        project_title: str = "",
        logo_path: str = "",
    ) -> Dict[str, Any]:
        """
        Constroi JSON v2.0 com records, metadados de qualidade e timestamps opcionais.

        Args:
            records: Lista de registros (pontos enriquecidos)
            source: Fonte dos dados (mrk, mrk+photo, photo_only)
            base_folder: Pasta base das fotos/MRK
            tool_key: Chave da ferramenta
            recursive: Se a busca foi recursiva
            timestamps: Dict opcional com timestamps de cada extrator
            project_title: Título do projeto (ex: "Fazenda Esperança")
            logo_path: Caminho da imagem/logo do projeto
                       Ex: {"pipeline_start": "...", "mrk_start": "...", "mrk_end": "...",
                            "exif_start": "...", "exif_end": "...",
                            "xmp_start": "...", "xmp_end": "...",
                            "custom_start": "...", "custom_end": "...",
                            "pipeline_end": "..."}
        """
        from ..core.config.LogUtils import LogUtils
        logger = LogUtils(tool=tool_key, class_name="JsonUtil")

        normalized_records = records or []

        with_coords = 0
        without_coords = 0
        with_xmp = 0
        with_exif_gps = 0
        missing_xmp_and_exif = 0

        for r in normalized_records:
            source_txt = str(r.get("CoordSource") or "").strip().upper()
            if source_txt and source_txt != "NONE":
                with_coords += 1
            else:
                without_coords += 1

            has_xmp_raw = r.get("HasXmp")
            has_exif_gps_raw = r.get("HasExifGps")
            source_hint = str(r.get("CoordSource") or "").strip().upper()
            has_xmp = bool(has_xmp_raw) or source_hint == "XMP"
            has_exif_gps = bool(has_exif_gps_raw) or source_hint == "EXIF"
            if has_xmp:
                with_xmp += 1
            if has_exif_gps:
                with_exif_gps += 1
            if (not has_xmp) and (not has_exif_gps):
                missing_xmp_and_exif += 1

        quality = {
            "total_files": len(normalized_records),
            "with_coords": with_coords,
            "without_coords": without_coords,
            "with_xmp": with_xmp,
            "with_exif_gps": with_exif_gps,
            "missing_xmp_and_exif": missing_xmp_and_exif,
        }

        groups = {}
        for record in normalized_records:
            folder_key = record.get("MrkFolder") or os.path.dirname(record.get("Path", ""))
            if folder_key not in groups:
                groups[folder_key] = {
                    "MrkFile": record.get("MrkFile", ""),
                    "FlightName": record.get("FlightName", ""),
                    "FlightNumber": record.get("FlightNumber", 0),
                    "points_count": 0,
                    "indexed_count": 0,
                    "records": {},
                }

            file_key = record.get("File")
            if not file_key:
                foto = record.get("Foto")
                if foto is not None:
                    file_key = f"foto_{foto}"
                else:
                    file_key = f"record_{len(groups[folder_key]['records'])}"

            groups[folder_key]["records"][file_key] = record
            groups[folder_key]["points_count"] += 1
            groups[folder_key]["indexed_count"] += 1

        now_iso = datetime.now().isoformat()

        json_data = {
            "schema_version": "2.0",
            "source": source,
            "tool_key": tool_key,
            "base_folder": base_folder,
            "recursive": recursive,
            "generated_at": now_iso,
        }

        # Adiciona titulo do projeto e logotipo se fornecidos
        if project_title:
            json_data["titulo"] = project_title
        if logo_path:
            json_data["logotipo"] = logo_path

        # Adiciona timestamps se fornecidos (logo apos generated_at, antes de quality/groups)
        if timestamps:
            json_data["timestamps"] = timestamps

        json_data["quality"] = quality
        json_data["groups"] = groups

        logger.debug(f"Built JSON v2.0 with {len(groups)} groups and {len(normalized_records)} records")
        return json_data

    @staticmethod
    def save(json_data: Dict[str, Any], output_path: str) -> str:
        from ..core.config.LogUtils import LogUtils
        logger = LogUtils(tool=json_data.get("tool_key", "json_util"), class_name="JsonUtil")
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved JSON to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving JSON to {output_path}: {e}")
            raise

    @staticmethod
    def update_timestamps(json_path: str, new_timestamps: Dict[str, str]) -> Dict[str, Any]:
        """
        Carrega um JSON existente, mescla novos timestamps e salva de volta.

        Args:
            json_path: Caminho do arquivo JSON a ser atualizado
            new_timestamps: Dict com os novos pares chave:timestamp a adicionar

        Returns:
            O dict completo do JSON (com timestamps atualizados)
        """
        from ..core.config.LogUtils import LogUtils
        logger = LogUtils(tool="json_util", class_name="JsonUtil")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            existing = json_data.get("timestamps", {})
            existing.update(new_timestamps)
            json_data["timestamps"] = existing

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Timestamps atualizados no JSON: {list(new_timestamps.keys())}")
            return json_data
        except Exception as e:
            logger.error(f"Erro ao atualizar timestamps em {json_path}: {e}")
            raise

    @staticmethod
    def load_records(json_path: str) -> List[Dict[str, Any]]:
        from ..core.config.LogUtils import LogUtils
        logger = LogUtils(tool="json_util", class_name="JsonUtil")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            version = data.get("schema_version")
            if version != "2.0":
                raise ValueError(
                    f"JSON com schema_version='{version}' nao e suportado. "
                    "Regenere o JSON usando a versao atual do plugin."
                )

            records = []
            for group in data.get("groups", {}).values():
                for record in group.get("records", {}).values():
                    records.append(record)

            logger.debug(f"Loaded {len(records)} records from {json_path}")
            return records
        except Exception as e:
            logger.error(f"Error loading records from {json_path}: {e}")
            raise