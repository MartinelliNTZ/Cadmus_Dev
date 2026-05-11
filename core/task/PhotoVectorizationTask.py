# -*- coding: utf-8 -*-
import json

from .BaseTask import BaseTask
from ..config.LogUtils import LogUtils
from ..services.PhotoFolderVectorizationService import PhotoFolderVectorizationService
from ...utils.JsonUtil import JsonUtil


class PhotoVectorizationTask(BaseTask):
    """Task que extrai JSON v2.0 a partir de pasta de fotos (sem MRK)."""

    def __init__(
        self,
        base_folder: str,
        recursive: bool,
        layer_name: str,
        tool_key: str,
    ):
        super().__init__("Gerando vetor de fotos", tool_key)
        self.base_folder = base_folder
        self.recursive = recursive
        self.layer_name = layer_name

    def _run(self) -> bool:
        if self.isCanceled():
            return False

        logger = LogUtils(tool=self.tool_key, class_name=self.__class__.__name__)

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
                "total_points": len(records),
                "quality": quality,
            }

            logger.info(
                "Extracao de JSON para vetorizacao concluida",
                data={"json_path": json_path, "base_folder": self.base_folder},
            )

            return True

        except Exception as e:
            logger.error(f"Erro na extracao de JSON: {e}")
            raise
