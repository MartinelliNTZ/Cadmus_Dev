# -*- coding: utf-8 -*-
from .BaseTask import BaseTask
from ..config.LogUtils import LogUtils
from ..services.ReportGenerationService import ReportGenerationService


class ReportGenerationTask(BaseTask):
    """Task que gera relatório HTML a partir de JSON de metadados."""

    def __init__(
        self,
        json_path: str,
        html_output_path: str = None,
        tool_key: str = None,
    ):
        super().__init__("Gerando relatório HTML", tool_key)
        self.json_path = json_path
        self.html_output_path = html_output_path

    def _run(self) -> bool:
        if self.isCanceled():
            return False

        logger = LogUtils(tool=self.tool_key, class_name=self.__class__.__name__)

        try:
            service = ReportGenerationService(tool_key=self.tool_key)
            result = service.generate_from_json(
                json_path=self.json_path,
                html_output_path=self.html_output_path,
            )

            self.result = result
            logger.info("Relatório HTML gerado com sucesso", data=result)
            return True

        except Exception as e:
            logger.error(f"Erro na geração do relatório HTML: {e}")
            raise e