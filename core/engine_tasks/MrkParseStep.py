# -*- coding: utf-8 -*-
from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.MrkParseTask import MrkParseTask
from ..config.LogUtils import LogUtils


class MrkParseStep(BaseStep):
    """Step responsavel por ler MRKs e gerar JSON base (sem vetorizacao)."""

    def name(self) -> str:
        return "MrkParseStep"

    def create_task(self, context: ExecutionContext):
        context.require(["paths", "recursive", "tool_key"])

        return MrkParseTask(
            paths=context.get("paths"),
            recursive=context.get("recursive", True),
            extra_fields=context.get("extra_fields"),
            tool_key=context.get("tool_key"),
        )

    def on_success(self, context: ExecutionContext, result):
        logger = LogUtils(
            tool=context.get("tool_key"),
            class_name=self.__class__.__name__,
        )

        json_path = result.get("json_path")
        if not json_path:
            logger.error("json_path nao encontrado no resultado do MrkParseTask")
            raise RuntimeError("Nenhum JSON gerado pelos MRKs.")

        context.set("json_path", json_path)
        context.set("source", result.get("source", "mrk"))
        context.set("base_folder", result.get("base_folder"))

        logger.info(
            "JSON MRK gerado com sucesso",
            data={"json_path": json_path, "total_points": len(result.get("points", []))},
        )
