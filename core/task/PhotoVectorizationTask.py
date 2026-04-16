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
            result = service.generate_from_folder(
                base_folder=self.base_folder,
                recursive=self.recursive,
                generate_report=False,  # Relatório será gerado pelo ReportGenerationStep
                layer_name=self.layer_name,
            )

            if not result or not isinstance(result, dict):
                logger.error("Resultado inválido do serviço de vetorização", data={"result": result})
                return False

            json_path = result.get("json_path")
            if not json_path:
                logger.error("json_path não encontrado no resultado do serviço", data=result)
                return False

            self.result = result
            logger.info("Vetorização de fotos concluída com sucesso", data={
                "has_layer": result.get("layer") is not None,
                "json_path": json_path,
                "total_points": result.get("total_points", 0)
            })
            return True

        except Exception as e:
            logger.error(f"Erro na vetorização de fotos: {e}")
            raise e