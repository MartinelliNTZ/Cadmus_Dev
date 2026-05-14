# -*- coding: utf-8 -*-
import json

from qgis.core import QgsProject

from .BaseTask import BaseTask
from ..config.LogUtils import LogUtils
from ..services.PhotoFolderVectorizationService import PhotoFolderVectorizationService
from ...utils.mrk.PhotoMetadata import PhotoMetadata
from ...utils.mrk.MetadataFields import MetadataFields
from ...utils.JsonUtil import JsonUtil


class PhotoEnrichmentTask(BaseTask):
    """
    Task unificada para enriquecimento de metadados de fotos.
    
    Modo 1 - "mrk+photo" (quando json_path é fornecido):
      Carrega pontos MRK existentes e cruza com metadados das fotos
      (EXIF + XMP + CustomFields + contexto MRK)
    
    Modo 2 - "photo_only" (quando json_path é None):
      Lê fotos diretamente da pasta, extrai EXIF/XMP/GPS,
      calcula campos custom e gera JSON v2.0 puro
    
    Em ambos os casos, apenas o JSON é gerado (sem vetorização).
    A vetorização é responsabilidade do JsonVectorizationStep posterior.
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

    def _run(self) -> bool:
        if self.isCanceled():
            return False

        logger = LogUtils(tool=self.tool_key, class_name=self.__class__.__name__)

        # Determina modo baseado na existência de JSON MRK prévio
        has_mrk_data = bool(self.json_path) or bool(self.source_points) or bool(self.layer_id)

        if has_mrk_data:
            # Modo "mrk+photo": enriquece pontos MRK existentes com metadados de fotos
            logger.info(
                "Modo mrk+photo: enriquecendo pontos MRK com metadados de fotos",
                data={
                    "base_folder": self.base_folder,
                    "json_path": self.json_path,
                    "has_layer": bool(self.layer_id),
                    "has_source_points": len(self.source_points) > 0,
                },
            )
            return self._run_enrich_mrk(logger)
        else:
            # Modo "photo_only": extrai metadados diretamente das fotos
            logger.info(
                "Modo photo_only: extraindo metadados de fotos sem MRK",
                data={"base_folder": self.base_folder, "recursive": self.recursive},
            )
            return self._run_photo_only(logger)

    def _run_enrich_mrk(self, logger: LogUtils) -> bool:
        """Modo mrk+photo: cruza pontos MRK com metadados de fotos."""
        pontos = self._extract_source_points(logger)

        logger.info(
            "Pontos extraidos para enriquecimento",
            data={
                "total_pontos": len(pontos),
                "com_mrk_folder": sum(1 for p in pontos if "mrk_folder" in p),
            },
        )

        # Completa atributos faltantes usando os pontos originais do parser
        self._fill_missing_attributes(pontos, logger)

        # Cruza metadados das fotos com os pontos MRK
        enrich_result = PhotoMetadata.enrich(
            pontos,
            base_folder=self.base_folder,
            recursive=self.recursive,
            selected_required_fields=self.selected_required_fields,
            selected_custom_fields=self.selected_custom_fields,
            selected_mrk_fields=self.selected_mrk_fields,
            return_report=True,
        )

        json_path = None
        if isinstance(enrich_result, str):
            json_path = enrich_result

        if json_path:
            logger.info(
                "JSON enriquecido gerado (mrk+photo)",
                code="PHOTO_METADATA_JSON_PATH",
                data={"json_path": json_path},
            )

        self.result = {
            "json_path": json_path,
            "source": "mrk+photo",
            "total_points": len(pontos),
        }
        return True

    def _run_photo_only(self, logger: LogUtils) -> bool:
        """Modo photo_only: extrai metadados diretamente das fotos."""
        try:
            service = PhotoFolderVectorizationService(tool_key=self.tool_key)
            json_path = service.extract_to_json(
                base_folder=self.base_folder,
                recursive=self.recursive,
                tool_key=self.tool_key,
                selected_fields=None,
            )

            if not json_path:
                logger.error("extract_to_json() nao retornou json_path valido")
                return False

            records = JsonUtil.load_records(json_path)
            quality = {}
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    quality = (json.load(f) or {}).get("quality", {})
            except Exception:
                quality = {}

            self.result = {
                "json_path": json_path,
                "source": "photo_only",
                "total_points": len(records),
                "quality": quality,
            }

            logger.info(
                "JSON photo_only gerado com sucesso",
                data={"json_path": json_path, "total_points": len(records)},
            )

            return True

        except Exception as e:
            logger.error(f"Erro na extracao photo_only: {e}")
            raise

    def _extract_source_points(self, logger: LogUtils) -> list:
        """
        Extrai pontos da camada QGIS, do JSON ou da lista fornecida.
        """
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
                    logger.warning(
                        f"Valor de foto nao inteiro: {foto} na feature {feat.id()}. Ignorando."
                    )
                    continue

                ponto = {"foto": foto_int}
                for field in feat.fields():
                    name = field.name()
                    if name == photo_field_name:
                        continue
                    normalized_name = MetadataFields.resolve_key(name)
                    ponto[normalized_name] = feat.attribute(name)

                if feat.fieldNameIndex(mrk_folder_field_name) != -1:
                    mrk_folder = feat.attribute(mrk_folder_field_name)
                    if mrk_folder:
                        ponto["mrk_folder"] = mrk_folder
                pontos.append(ponto)
        else:
            source_records = self.source_points
            if not source_records and self.json_path:
                source_records = JsonUtil.load_records(self.json_path)

            for src in source_records:
                canonical = MetadataFields.normalize_record_to_keys(src or {})
                foto = canonical.get("Foto") or canonical.get("foto")
                if foto is None:
                    continue
                try:
                    foto_int = int(foto)
                except Exception:
                    continue
                ponto = {"foto": foto_int}
                for key, value in canonical.items():
                    ponto[key] = value
                mrk_folder = canonical.get("MrkFolder")
                if mrk_folder:
                    ponto["mrk_folder"] = mrk_folder
                pontos.append(ponto)

        return pontos

    def _fill_missing_attributes(self, pontos: list, logger: LogUtils):
        """
        Preenche atributos faltantes usando pontos do parser original.
        """
        source_by_key = {}
        source_by_foto = {}
        for p in self.source_points:
            try:
                foto_src = int(p.get("foto"))
            except Exception:
                continue
            mrk_src = str(p.get("mrk_folder") or "").strip()
            source_by_key[(mrk_src, foto_src)] = p
            source_by_foto.setdefault(foto_src, p)

        for p in pontos:
            foto_src = p.get("foto")
            mrk_src = str(p.get("mrk_folder") or "").strip()
            src = source_by_key.get((mrk_src, foto_src)) or source_by_foto.get(foto_src)
            if not src:
                continue
            for k, v in src.items():
                if k not in p or p.get(k) in (None, ""):
                    p[k] = v