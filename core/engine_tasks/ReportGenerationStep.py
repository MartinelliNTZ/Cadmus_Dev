# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional

from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.ReportGenerationTask import ReportGenerationTask
from ..config.LogUtils import LogUtils
from ...utils.ExplorerUtils import ExplorerUtils


class ReportGenerationStep(BaseStep):
    """
    Step para gerar relatório HTML a partir de JSON de metadados.

    Parâmetros explícitos (passados no __init__):
        html_output_path (str, opcional): Caminho para salvar o HTML.

    Usa do ExecutionContext (canônico):
        json_path: Caminho do JSON (set_result do step anterior)
        tool_key: ToolKey para logging
    """

    def __init__(self, *, html_output_path: Optional[str] = None):
        self.html_output_path = html_output_path

    def name(self) -> str:
        return "ReportGenerationStep"

    def _resolve_tool_key(self, context: ExecutionContext) -> str:
        tk = context.tool_key
        if tk:
            return tk
        raise KeyError("ExecutionContext.tool_key não definido")

    def _resolve_json_path(self, context: ExecutionContext) -> str:
        jp = context.json_path or context.get_result("json_path")
        if not jp:
            raise ValueError(
                "ReportGenerationStep: json_path não definido no contexto. "
                "O step anterior pode ter falhado em gerar o JSON de metadados."
            )
        return jp

    def should_run(self, context: ExecutionContext) -> bool:
        """Só executa se json_path estiver disponível no contexto."""
        json_path = context.json_path or context.get_result("json_path")
        if not json_path:
            LogUtils(
                tool=context.tool_key or "untraceable",
                class_name=self.__class__.__name__,
            ).info(
                "ReportGenerationStep pulado: json_path não disponível no contexto"
            )
            return False
        return True

    def create_task(self, context: ExecutionContext):
        tool_key = self._resolve_tool_key(context)
        json_path = self._resolve_json_path(context)

        return ReportGenerationTask(
            json_path=json_path,
            html_output_path=self.html_output_path,
            tool_key=tool_key,
        )

    def on_success(self, context: ExecutionContext, result):
        if not result or not isinstance(result, dict):
            LogUtils(
                tool=self._resolve_tool_key(context),
                class_name=self.__class__.__name__,
            ).error("Resultado inválido da geração do relatório")
            return

        context.set_result("report_payload", result)

        LogUtils(
            tool=self._resolve_tool_key(context),
            class_name=self.__class__.__name__,
        ).info("Relatório HTML gerado com sucesso", data=result)

        # Abrir relatório HTML se foi gerado
        html_path = result.get("html_path")
        if html_path:
            opened = ExplorerUtils.open_file(
                html_path, self._resolve_tool_key(context)
            )
            if not opened:
                LogUtils(
                    tool=self._resolve_tool_key(context),
                    class_name=self.__class__.__name__,
                ).warning(
                    "Falha ao abrir relatório HTML automaticamente",
                    data={"html_path": html_path},
                )

    def on_error(self, context: ExecutionContext, exception: Exception):
        LogUtils(
            tool=self._resolve_tool_key(context),
            class_name=self.__class__.__name__,
        ).error(f"Erro no step de geração de relatório: {exception}")