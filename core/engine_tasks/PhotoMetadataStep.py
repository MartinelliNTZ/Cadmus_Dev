# -*- coding: utf-8 -*-

from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.PhotoMetadataTask import PhotoMetadataTask
from ..config.LogUtils import LogUtils


class PhotoMetadataStep(BaseStep):
    """Step para enriquecer JSON com metadados de fotos (sem vetorizacao)."""

    def name(self) -> str:
        return "PhotoMetadataStep"

    def create_task(self, context: ExecutionContext):
        context.require(["base_folder", "recursive", "tool_key"])

        layer = context.get("layer")
        return PhotoMetadataTask(
            layer_id=layer.id() if layer else "",
            base_folder=context.get("base_folder"),
            recursive=context.get("recursive", True),
            source_points=[],
            json_path=context.get("json_path"),
            selected_required_fields=context.get("selected_required_fields", []),
            selected_custom_fields=context.get("selected_custom_fields", []),
            selected_mrk_fields=context.get("selected_mrk_fields", []),
            tool_key=context.get("tool_key"),
        )

    def on_success(self, context: ExecutionContext, result):
        if not result or not isinstance(result, dict):
            return

        json_path = result.get("json_path")
        if not json_path:
            LogUtils(
                tool=context.get("tool_key"),
                class_name=self.__class__.__name__,
            ).error("json_path nao encontrado no resultado do PhotoMetadataTask")
            return

        context.set("json_path", json_path)
        context.set("source", "mrk+photo")

        LogUtils(
            tool=context.get("tool_key"),
            class_name=self.__class__.__name__,
        ).info("JSON enriquecido com metadados de foto", data={"json_path": json_path})
