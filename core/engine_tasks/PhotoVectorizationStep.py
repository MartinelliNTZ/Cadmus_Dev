# -*- coding: utf-8 -*-
from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.PhotoVectorizationTask import PhotoVectorizationTask
from ..config.LogUtils import LogUtils


class PhotoVectorizationStep(BaseStep):
    """Step para extrair/enriquecer JSON de fotos (sem vetorizacao)."""

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
            logger.error("Resultado invalido da extracao de fotos")
            return

        json_path = result.get("json_path")
        if not json_path:
            logger.error("json_path nao encontrado no resultado")
            return

        context.set("json_path", json_path)
        context.set("source", "photo_only")
        context.set("quality", result.get("quality", {}))

        logger.info(
            "JSON de fotos extraido com sucesso",
            data={"json_path": json_path, "source": "photo_only"},
        )
