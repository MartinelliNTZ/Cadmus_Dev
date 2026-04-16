# -*- coding: utf-8 -*-
from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.ReportGenerationTask import ReportGenerationTask
from ..config.LogUtils import LogUtils
from ...utils.ExplorerUtils import ExplorerUtils
from ...utils.QgisMessageUtil import QgisMessageUtil
from ...i18n.TranslationManager import STR


class ReportGenerationStep(BaseStep):
    """Step para gerar relatório HTML a partir de JSON de metadados."""

    def name(self) -> str:
        return "ReportGenerationStep"

    def _resolve_json_path(self, context: ExecutionContext):
        return (
            context.get("json_path")
            or context.get("photo_metadata_json_path")
            or context.get("report_json_path")
        )

    def should_run(self, context: ExecutionContext) -> bool:
        """Só executa se json_path estiver disponível no contexto."""
        json_path = self._resolve_json_path(context)
        if not json_path:
            LogUtils(
                tool=context.get("tool_key", "untraceable"),
                class_name=self.__class__.__name__,
            ).info("ReportGenerationStep pulado: json_path não disponível no contexto")
            return False
        return True

    def create_task(self, context: ExecutionContext):
        context.require(["tool_key"])

        json_path = self._resolve_json_path(context)
        if not json_path:
            raise ValueError(
                "ReportGenerationStep: json_path não definido no contexto. O step anterior pode ter falhado em gerar o JSON de metadados."
            )

        if not context.has("json_path") and context.has("photo_metadata_json_path"):
            context.set("json_path", json_path)

        return ReportGenerationTask(
            json_path=json_path,
            html_output_path=context.get("html_output_path"),
            tool_key=context.get("tool_key"),
        )

    def on_success(self, context: ExecutionContext, result):
        if not result or not isinstance(result, dict):
            LogUtils(
                tool=context.get("tool_key"),
                class_name=self.__class__.__name__,
            ).error("Resultado inválido da geração do relatório")
            return

        context.set("report_payload", result)

        LogUtils(
            tool=context.get("tool_key"),
            class_name=self.__class__.__name__,
        ).info("Relatório HTML gerado com sucesso", data=result)

        # Abrir relatório HTML se foi gerado
        html_path = result.get("html_path")
        if html_path:
            opened = ExplorerUtils.open_file(html_path, context.get("tool_key"))
            if not opened:
                LogUtils(
                    tool=context.get("tool_key"),
                    class_name=self.__class__.__name__,
                ).warning(
                    "Falha ao abrir relatório HTML automaticamente",
                    data={"html_path": html_path},
                )
                if context.get("iface"):
                    QgisMessageUtil.bar_warning(
                        context.get("iface"),
                        f"{STR.WARNING}: não foi possível abrir o HTML automaticamente.",
                    )

    def on_error(self, context: ExecutionContext, exception: Exception):
        LogUtils(
            tool=context.get("tool_key"),
            class_name=self.__class__.__name__,
        ).error(f"Erro no step de geração de relatório: {exception}")

        if context.get("iface"):
            QgisMessageUtil.modal_error(
                context.get("iface"),
                f"{STR.ERROR}: {exception}"
            )