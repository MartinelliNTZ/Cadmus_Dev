# -*- coding: utf-8 -*-
import os
from ...core.config.LogUtils import LogUtils
from ...plugins.BaseDialog import BaseDialog
from ...i18n.TranslationManager import STR
from ...utils.ToolKeys import ToolKey
from ...resources.new_widgets.TextBrowser import TextBrowser
from ...resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons


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
        browser = TextBrowser(parent=self)

        if os.path.exists(instructions_path):
            with open(instructions_path, "r", encoding="utf-8") as f:
                md_text = f.read()

            # Renderizacao Markdown com fallback Qt5/Qt6
            browser.set_markdown(md_text)
        else:
            browser.setPlainText(
                f"{STR.FILE_NOT_FOUND}:\n{instructions_path}"
            )

        self.layout.addWidget(browser, stretch=1)

        # ── Botao Fechar ───────────────────────────────────────
        # GridExecutionButtons gerencia o botao fechar internamente
        self.action_buttons = GridExecutionButtons(
            config={},
            enable_close_button=True,
            enable_info=False,
            tool_key=tool_key,
            parent=self,
        )
        self.layout.add_execution_buttons(self.action_buttons)

        self.logger.debug(
            "InfoDialog UI construida com sucesso usando BaseDialog layout."
        )