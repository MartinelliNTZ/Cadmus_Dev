# -*- coding: utf-8 -*-
import os
from ..config.LogUtils import LogUtils
from ...plugins.BaseDialog import BaseDialog
from ...i18n.TranslationManager import STR
from ...utils.ToolKeys import ToolKey
from ...resources.widgets.TextBrowser import TextBrowser
from ...resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ...utils.ProjectUtils import ProjectUtils


class InfoDialog(BaseDialog):
    def __init__(
        self,
        instructions_path: str,
        parent=None,
        title=STR.APP_NAME,
        tool_key=ToolKey.UNTRACEABLE,
    ):
        super().__init__(parent)
        self.logger = LogUtils(
            tool=tool_key, class_name=self.__class__.__name__, level=LogUtils.DEBUG
        )
        self.logger.debug(
            f"Inicializando InfoDialog com arquivo: {instructions_path}"
        )

        # Use BaseDialog layout builder so dialogs share the same shell
        self._build_ui(
            title=title, enable_scroll=False, minimum_size=(700, 550)
        )

        # ── Text Browser com Markdown ──────────────────────────
        self.browser = TextBrowser(parent=self)

        if os.path.exists(instructions_path):
            with open(instructions_path, "r", encoding="utf-8") as f:
                md_text = f.read()

            # Renderizacao Markdown com fallback Qt5/Qt6
            self.browser.set_markdown(md_text)
        else:
            self.browser.setPlainText(
                f"{STR.FILE_NOT_FOUND}:\n{instructions_path}"
            )

        self.layout.addWidget(self.browser, stretch=1)

        # ── Botoes de Acao ─────────────────────────────────────
        # GridExecutionButtons gerencia os botoes internamente
        self.action_buttons = GridExecutionButtons(
            config={
                "copy": {
                    "label": "Copiar texto",
                    "description": "Copia todo o conteudo para a area de transferencia",
                    "callback": self._copy_all_text,
                },
            },
            enable_close_button=True,
            enable_info=False,
            tool_key=tool_key,
            enable_config_button=False,
            parent=self,
        )
        self.layout.add_execution_buttons(self.action_buttons)

        self.logger.debug(
            "InfoDialog UI construida com sucesso usando BaseDialog layout."
        )

    def _copy_all_text(self):
        """Copia todo o conteudo do browser para a area de transferencia via ProjectUtils."""
        text = self.browser.toPlainText()
        if text:
            ProjectUtils.set_clipboard_text(text)
            self.logger.debug(
                f"Texto copiado para area de transferencia ({len(text)} caracteres)"
            )
