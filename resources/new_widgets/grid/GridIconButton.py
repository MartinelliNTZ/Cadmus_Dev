# -*- coding: utf-8 -*-
"""
GridIconButton — Container genérico de botões com ícone.
Plugins USAM este widget (composto de SimpleIconButton internamente).

Cada item no config dict tem seu próprio callback.
O widget não sabe o que cada botão faz — o plugin decide.

Callbacks são passadas no dict de cada item, não por sinais Qt.
Widgets não expõem sinais — o plugin passa funções callback.

Uso em plugins:
    social = GridIconButton(config={
        "github": {
            "label": "GitHub",
            "icon": IconManager.GITHUB,
            "callback": lambda: webbrowser.open("https://github.com/user"),
            "description": "Visite o GitHub",
        },
        "linkedin": {
            "label": "LinkedIn",
            "icon": IconManager.LINKEDIN,
            "callback": lambda: webbrowser.open("https://linkedin.com/in/user"),
        },
    }, parent=self)
    layout.addWidget(social)
"""

from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout
from qgis.PyQt.QtCore import QSize, Qt
from ..simple.SimpleIconButton import SimpleIconButton
from ...styles.AppStyles import AppStyles
import os


class GridIconButton(QWidget):
    """
    Container genérico de botões com ícone.

    Cada item no config deve ter:
    - "label" (obrigatório): tooltip do botão
    - "icon" (obrigatório): nome do arquivo de ícone
    - "callback" (obrigatório): função chamada ao clicar

    Opcionais:
    - "description": tooltip adicional
    - "icon_size": QSize do ícone (default: 32x32)
    - "button_size": QSize do botão (default: 40x40)

    Parâmetros
    ----------
    config : dict
        Dicionário de configuração onde cada chave é o identificador
        e cada valor é um dict com "label", "icon", "callback" e opcionais.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        config: dict = None,
        parent=None,
    ):
        super().__init__(parent)

        self._config = config or {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 4)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icons_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "resources", "icons"
        )

        for btn_id, btn_config in self._config.items():
            icon_file = btn_config.get("icon", "")
            icon_path = os.path.join(icons_dir, icon_file)
            if not os.path.exists(icon_path):
                continue

            tooltip = btn_config.get("label", btn_id)
            callback = btn_config.get("callback")
            icon_size = btn_config.get("icon_size", QSize(32, 32))
            button_size = btn_config.get("button_size", QSize(40, 40))

            btn = SimpleIconButton(
                icon_path=icon_path,
                tooltip=tooltip,
                icon_size=icon_size,
                button_size=button_size,
                parent=self,
            )

            if callback:
                btn.clicked.connect(callback)
            layout.addWidget(btn)

        self._apply_styles()

    def _apply_styles(self):
        combined = self._specific_style()
        if combined:
            self.setStyleSheet(combined)

    def _specific_style(self) -> str:
        return ""