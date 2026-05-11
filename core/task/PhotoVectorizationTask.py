# -*- coding: utf-8 -*-
from .BaseTask import BaseTask
from ..config.LogUtils import LogUtils
from ..services.PhotoFolderVectorizationService import PhotoFolderVectorizationService


class PhotoVectorizationTask(BaseTask):
    """Task que gera camada vetorial a partir de pasta de fotos (sem MRK)."""

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
            # Novo: usar extract_to_json() em vez de generate_from_folder()
            json_path = service.extract_to_json(
                base_folder=self.base_folder,
                recursive=self.recursive,
                tool_key=self.tool_key,
                selected_fields=None,  # Todos os campos
            )

            if not json_path:
                logger.error("extract_to_json() não retornou json_path válido")
                return False

            self.result = {
                "json_path": json_path,
                "total_points": 0,  # Será determinado pelo translator
                "quality": {},  # Será populado pelo translator se necessário
            }

            logger.info("Extração de JSON para vetorização concluída", data={
                "json_path": json_path,
                "base_folder": self.base_folder
            })

            return True

        except Exception as e:
            logger.error(f"Erro na extração de JSON: {e}")
            raise e