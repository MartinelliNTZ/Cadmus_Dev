# -*- coding: utf-8 -*-
import json
import os

from .BaseTask import BaseTask
from ..config.LogUtils import LogUtils
from ..enum import MetadataFieldKey
from ...utils.mrk.PhotoMetadata import PhotoMetadata
from ...utils.mrk.MetadataFields import MetadataFields
from ...utils.JsonUtil import JsonUtil
from ...utils.ExplorerUtils import ExplorerUtils


class PhotoEnrichmentTask(BaseTask):
    """
    Task unificada para enriquecimento de metadados de fotos.
    
    Utiliza o pipeline linear do PhotoMetadata.run_pipeline() com flags
    de habilitação de cada etapa.
    
    Modo 1 - "mrk+photo" (quando há pontos MRK):
      Executa pipeline com enable_mrk=True
      → Gera JSON v2.0 com source="mrk+photo"
    
    Modo 2 - "photo_only" (quando NÃO há MRK):
      Executa pipeline com enable_mrk=False (apenas esqueleto + EXIF + XMP + custom)
      → Gera JSON v2.0 com source="photo"
    
    Modo 3 - "skeleton_only" (apenas esqueleto, sem EXIF/XMP/custom):
      Executa pipeline com enable_mrk=True, enable_exif=False, enable_xmp=False, enable_custom_fields=False
      → Gera JSON v2.0 com source="photo" (apenas coordenadas do MRK + estrutura de pastas)
    
    Em todos os casos:
    - Aplica filtro de campos selecionados (selected_keys)
    - Constrói JSON via JsonUtil.build()
    - Salva JSON via ExplorerUtils.create_temp_json()
    - NÃO vetoriza (vetorização é do JsonVectorizationStep posterior)
    """

    def __init__(
        self,
        base_folder: str,
        recursive: bool,
        json_path: str = None,
        source_points: list = None,
        layer_id: str = "",
        selected_required_fields: list = None,
        selected_custom_fields: list = None,
        selected_mrk_fields: list = None,
        tool_key: str = None,
        existing_timestamps: dict = None,
        enable_mrk: bool = False,
        enable_exif: bool = True,
        enable_xmp: bool = True,
        enable_custom_fields: bool = True,
    ):
        super().__init__("Enriquecendo fotos", tool_key)
        self.base_folder = base_folder
        self.recursive = recursive
        self.json_path = json_path
        self.source_points = source_points or []
        self.layer_id = layer_id
        self.selected_required_fields = selected_required_fields or []
        self.selected_custom_fields = selected_custom_fields or []
        self.selected_mrk_fields = selected_mrk_fields or []
        self.existing_timestamps = existing_timestamps or {}

        # Flags do pipeline
        self.enable_mrk = enable_mrk
        self.enable_exif = enable_exif
        self.enable_xmp = enable_xmp
        self.enable_custom_fields = enable_custom_fields

    def _get_selected_keys(self) -> set:
        """Constrói conjunto de chaves selecionadas pelo usuário."""
        selected = set(self.selected_required_fields)
        selected.update(self.selected_custom_fields)
        selected.update(self.selected_mrk_fields)
        return selected

    def _build_timestamps(self, source: str) -> dict:
        """
        Monta o dict de timestamps mesclando timestamps existentes (do MrkParseStep)
        com os timestamps recém-capturados do PhotoMetadata (EXIF/XMP/Custom).
        """
        timestamps = dict(self.existing_timestamps)

        # Obtem timestamps do PhotoMetadata (preenchidos apos run_pipeline)
        photo_ts = PhotoMetadata.get_timestamps()

        if photo_ts.get("exif_start"):
            timestamps["exif_start"] = photo_ts["exif_start"]
        if photo_ts.get("exif_xmp_end"):
            timestamps["exif_xmp_end"] = photo_ts["exif_xmp_end"]
        if photo_ts.get("custom_start"):
            timestamps["custom_start"] = photo_ts["custom_start"]
        if photo_ts.get("custom_end"):
            timestamps["custom_end"] = photo_ts["custom_end"]

        return timestamps

    def _run(self) -> bool:
        if self.isCanceled():
            return False

        logger = LogUtils(tool=self.tool_key, class_name=self.__class__.__name__)

        # Limpa timestamps anteriores do PhotoMetadata
        PhotoMetadata.clear_timestamps()

        # Determina se há dados MRK
        has_mrk_data = bool(self.json_path) or bool(self.source_points) or bool(self.layer_id)

        # Se enable_mrk foi explicitamente passado como False, não usa MRK mesmo que haja dados
        use_mrk = self.enable_mrk and has_mrk_data

        if use_mrk:
            logger.info(
                "Modo mrk+photo",
                data={
                    "base_folder": self.base_folder,
                    "enable_exif": self.enable_exif,
                    "enable_xmp": self.enable_xmp,
                    "enable_custom_fields": self.enable_custom_fields,
                },
            )
            records, quality = self._run_pipeline_with_mrk(logger)
            source = "mrk+photo"
        else:
            logger.info(
                "Modo photo",
                data={
                    "base_folder": self.base_folder,
                    "enable_exif": self.enable_exif,
                    "enable_xmp": self.enable_xmp,
                    "enable_custom_fields": self.enable_custom_fields,
                },
            )
            records, quality = self._run_pipeline_photo_only(logger)
            source = "photo"

        if not records:
            logger.error("Nenhum registro gerado no enriquecimento")
            return False

        # Aplica filtro de campos selecionados
        selected_keys = self._get_selected_keys()
        if selected_keys:
            filtered = []
            skip_keys = {
                MetadataFieldKey.COORD_SOURCE.value,
                MetadataFieldKey.QUALITY_FLAG.value,
                "HasXmp",
                "HasExifGps",
            }
            for record in records:
                filtered_record = {
                    k: v
                    for k, v in record.items()
                    if k in selected_keys
                    or k in skip_keys
                }
                if filtered_record:
                    filtered.append(filtered_record)
            records = filtered

        if not records:
            logger.warning("Todos os registros foram filtrados pelas chaves selecionadas")
            return False

        # Converte records para PascalCase (formato JSON v2.0)
        key_to_json_key = {
            key: field.key.value
            for key, field in MetadataFields.all_fields().items()
            if field.key is not None
        }
        json_records = []
        for record in records:
            json_record = {}
            for k, v in record.items():
                if isinstance(v, dict):
                    continue
                if isinstance(k, MetadataFieldKey):
                    json_record[k.value] = v
                else:
                    canonical_key = MetadataFields.resolve_key(str(k))
                    mapped_key = key_to_json_key.get(canonical_key, canonical_key)
                    json_record[mapped_key] = v
            json_records.append(json_record)

        # Constrói timestamps mesclados
        timestamps = self._build_timestamps(source)

        # Constrói JSON v2.0 com timestamps
        json_data = JsonUtil.build(
            records=json_records,
            source=source,
            base_folder=self.base_folder,
            tool_key=self.tool_key,
            recursive=self.recursive,
            timestamps=timestamps if timestamps else None,
        )

        # Adiciona quality stats
        if quality:
            json_data["quality"] = quality

        # Salva JSON
        if source == "mrk+photo":
            prefix = "DPM"
        elif self.enable_exif or self.enable_xmp or self.enable_custom_fields:
            prefix = "PFM"
        else:
            prefix = "SKL"  # skeleton_only

        json_path = ExplorerUtils.create_temp_json(
            json_data,
            tool_key=self.tool_key,
            prefix=prefix,
            subfolder=os.path.join(
                ExplorerUtils.REPORTS_TEMP_FOLDER,
                ExplorerUtils.REPORTS_JSON_FOLDER,
            ),
            file_stem_hint=ExplorerUtils.build_report_json_stem(
                base_folder=self.base_folder,
                points_total=len(json_records),
            ),
        )

        self.result = {
            "json_path": json_path,
            "source": source,
            "total_points": len(json_records),
            "timestamps": timestamps,
        }

        logger.info(
            "JSON enriquecido salvo",
            data={
                "json_path": json_path,
                "source": source,
                "total_points": len(json_records),
            },
        )

        return True

    def _run_pipeline_with_mrk(self, logger: LogUtils) -> tuple:
        """
        Modo mrk+photo: extrai pontos MRK e executa pipeline completo.
        """
        from qgis.core import QgsProject

        pontos = []
        layer = QgsProject.instance().mapLayer(self.layer_id) if self.layer_id else None

        if layer and layer.isValid():
            photo_field_name = MetadataFields.get_attribute("foto", "foto")
            mrk_folder_field_name = MetadataFields.get_attribute("mrk_folder", "mrk_folder")
            for feat in layer.getFeatures():
                foto = feat.attribute(photo_field_name)
                if foto is None:
                    continue
                try:
                    foto_int = int(foto)
                except Exception:
                    continue
                ponto = {"foto": foto_int}
                for field in feat.fields():
                    name = field.name()
                    if name == photo_field_name:
                        continue
                    ponto[MetadataFields.resolve_key(name)] = feat.attribute(name)
                if feat.fieldNameIndex(mrk_folder_field_name) != -1:
                    mrk_folder = feat.attribute(mrk_folder_field_name)
                    if mrk_folder:
                        ponto["mrk_folder"] = mrk_folder
                pontos.append(ponto)
        else:
            src = self.source_points
            if not src and self.json_path:
                src = JsonUtil.load_records(self.json_path)
            for s in src:
                canonical = MetadataFields.normalize_record_to_keys(s or {})
                foto = canonical.get("Foto") or canonical.get("foto")
                if foto is None:
                    continue
                try:
                    ponto = {"foto": int(foto)}
                    for k, v in canonical.items():
                        ponto[k] = v
                    mrk_folder = canonical.get("MrkFolder")
                    if mrk_folder:
                        ponto["mrk_folder"] = mrk_folder
                    pontos.append(ponto)
                except Exception:
                    continue

        # Preenche atributos faltantes dos source_points
        source_by_key = {}
        for p in self.source_points:
            try:
                source_by_key[(str(p.get("mrk_folder", "")).strip(), int(p.get("foto")))] = p
            except Exception:
                continue
        for p in pontos:
            key = (str(p.get("mrk_folder", "")).strip(), p.get("foto"))
            src = source_by_key.get(key)
            if src:
                for k, v in src.items():
                    if k not in p or p.get(k) in (None, ""):
                        p[k] = v

        logger.info("Pontos extraidos", data={"total": len(pontos)})

        # Executa pipeline com MRK habilitado e as flags de etapas
        records, quality = PhotoMetadata.run_pipeline(
            base_folder=self.base_folder,
            points=pontos,
            recursive=self.recursive,
            tool_key=self.tool_key,
            enable_mrk=True,
            enable_exif=self.enable_exif,
            enable_xmp=self.enable_xmp,
            enable_custom_fields=self.enable_custom_fields,
        )

        return records, quality

    def _run_pipeline_photo_only(self, logger: LogUtils) -> tuple:
        """
        Modo photo_only: executa pipeline sem MRK.
        """
        records, quality = PhotoMetadata.run_pipeline(
            base_folder=self.base_folder,
            points=None,
            recursive=self.recursive,
            tool_key=self.tool_key,
            enable_mrk=False,
            enable_exif=self.enable_exif,
            enable_xmp=self.enable_xmp,
            enable_custom_fields=self.enable_custom_fields,
        )
        return records, quality