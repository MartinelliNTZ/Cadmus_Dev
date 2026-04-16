# -*- coding: utf-8 -*-
from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.PhotoVectorizationTask import PhotoVectorizationTask
from ..config.LogUtils import LogUtils
from ...utils.ExplorerUtils import ExplorerUtils
from ...utils.QgisMessageUtil import QgisMessageUtil
from ...i18n.TranslationManager import STR


class PhotoVectorizationStep(BaseStep):
    """Step para gerar camada vetorial a partir de pasta de fotos (sem MRK)."""

    def name(self) -> str:
        return "PhotoVectorizationStep"

    def create_task(self, context: ExecutionContext):
        context.require(["base_folder", "recursive", "layer_name", "tool_key"])

        return PhotoVectorizationTask(
            base_folder=context.get("base_folder"),
            recursive=context.get("recursive", True),
            layer_name=context.get("layer_name", "Fotos_Sem_MRK"),
            tool_key=context.get("tool_key"),
        )

    def on_success(self, context: ExecutionContext, result):
        logger = LogUtils(
            tool=context.get("tool_key"),
            class_name=self.__class__.__name__,
        )

        if not result or not isinstance(result, dict):
            logger.error("Resultado inválido da vetorização de fotos")
            return

        layer = result.get("layer")
        json_path = result.get("json_path")

        logger.info("PhotoVectorizationStep.on_success chamado", data={
            "has_layer": layer is not None,
            "json_path": json_path,
            "total_points": result.get("total_points", 0)
        })

        # Sempre definir json_path no contexto se estiver disponível
        if json_path:
            context.set("json_path", json_path)
            logger.info("json_path definido no contexto", data={"json_path": json_path})
        else:
            logger.warning("json_path não disponível no resultado")

        if layer and layer.isValid():
            context.set("layer", layer)
            context.set("report_payload", result.get("report_payload"))
            context.set("total_points", result.get("total_points", 0))
            context.set("quality", result.get("quality", {}))

            logger.info("Camada vetorial de fotos criada com sucesso", data={
                "total_points": result.get("total_points", 0),
                "layer_name": layer.name(),
                "has_json": json_path is not None
            })

            # Abrir relatório HTML se foi gerado
            report_payload = result.get("report_payload")
            if report_payload and isinstance(report_payload, dict):
                html_path = report_payload.get("html_path")
                if html_path and context.get("iface"):
                    if not ExplorerUtils.open_file(html_path, context.get("tool_key")):
                        QgisMessageUtil.bar_warning(
                            context.get("iface"),
                            f"{STR.WARNING}: não foi possível abrir o HTML automaticamente.",
                        )