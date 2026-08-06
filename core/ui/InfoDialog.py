# -*- coding: utf-8 -*-
import os
import webbrowser
from qgis.PyQt.QtWidgets import QHBoxLayout
from ..config.LogUtils import LogUtils
from ...plugins.BaseDialog import BaseDialog
from ...i18n.TranslationManager import STR
from ...utils.ToolKeys import ToolKey
from ...resources.widgets.TextBrowser import TextBrowser
from ...resources.widgets.grid.GridLabel import GridLabel
from ...resources.widgets.grid.GridIconButton import GridIconButton
from ...resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ...resources.IconManager import IconManager
from ...utils.ProjectUtils import ProjectUtils


def _get_plugin_version() -> str:
    """Lê a versão do plugin a partir do metadata.txt."""
    metadata_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "metadata.txt"
    )
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("version="):
                    return line.strip().split("=", 1)[1]
    except OSError:
        pass
    return "0.0.0"


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

        # ── Informacoes + Redes Sociais (mesma linha, rodape) ──
        info_text = (
            f"<b>{STR.APP_NAME}</b> &nbsp;|&nbsp; "
            f"<b>{STR.VERSION}:</b> {_get_plugin_version()} &nbsp;|&nbsp; "
            f"<b>{STR.CREATOR}:</b> Matheus A. S. Martinelli"
        )
        self.info_label = GridLabel(config={
            "info": {"text": info_text},
        }, parent=self)

        self.social_buttons = GridIconButton(
            config={
                "github": {
                    "label": "GitHub",
                    "icon": IconManager.GITHUB,
                    "callback": lambda: webbrowser.open("https://github.com/MartinelliNTZ"),
                    "description": "Visite o GitHub de Matheus Martinelli",
                },
                "linkedin": {
                    "label": "LinkedIn",
                    "icon": IconManager.LINKEDIN,
                    "callback": lambda: webbrowser.open("https://www.linkedin.com/in/matheus-martinelli-a82149108"),
                    "description": "Conecte-se no LinkedIn",
                },
                "instagram": {
                    "label": "Instagram",
                    "icon": IconManager.INSTAGRAM,
                    "callback": lambda: webbrowser.open("https://www.instagram.com/matheusmartinelli00"),
                    "description": "Siga no Instagram",
                },
                "email": {
                    "label": "E-mail",
                    "icon": IconManager.EMAIL,
                    "callback": lambda: webbrowser.open("mailto:martinelli.matheus11@gmail.com"),
                    "description": "Envie um e-mail",
                },
                "buymeacoffee": {
                    "label": "Buy Me a Coffee",
                    "icon": IconManager.BUY_ME_A_COFFEE,
                    "callback": lambda: webbrowser.open("https://buymeacoffee.com/martinelliNTZ"),
                    "description": "Apoie o desenvolvimento",
                },
            },
            parent=self,
        )

        # Layout horizontal: info text + social buttons na mesma linha
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(10)
        bottom_layout.addWidget(self.info_label)
        bottom_layout.addWidget(self.social_buttons)
        bottom_layout.addStretch()
        self.layout.addLayout(bottom_layout)

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