# -*- coding: utf-8 -*-
"""
GridIconButton — Container de botões de ação com ícones (ex: sociais).
Plugins USAM este widget (composto de SimpleIconButton internamente).

A configuração é feita via dict `config={}`, onde:
- Cada chave é o identificador do botão (ex: "github", "linkedin")
- Cada valor é um dict com:
  - "icon": nome do arquivo de ícone (ex: IconManager.GITHUB)
  - "url": URL para abrir ao clicar
  - "label": tooltip do botão (obrigatório)
  - "description": descrição adicional (opcional)
  - "icon_size": QSize opcional para o ícone
  - "button_size": QSize opcional para o botão

Callbacks são passadas via parâmetros, não por sinais Qt.
Widgets não expõem sinais — o plugin passa funções callback.

Uso em plugins:
    social = GridIconButton(
        config={
            "github": {
                "label": "GitHub",
                "icon": IconManager.GITHUB,
                "url": "https://github.com/user",
                "description": "Visite o GitHub",
            },
            "linkedin": {
                "label": "LinkedIn",
                "icon": IconManager.LINKEDIN,
                "url": "https://linkedin.com/in/user",
            },
        },
        url_callback=lambda url: webbrowser.open(url),
        parent=self,
    )
    layout.addWidget(social)
"""

from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout
from qgis.PyQt.QtCore import QSize, Qt
from ..simple.SimpleIconButton import SimpleIconButton
from ...styles.AppStyles import AppStyles
import os


class GridIconButton(QWidget):
    """
    Container com botões de ação que usam ícone (ex: redes sociais).

    Parâmetros
    ----------
    config : dict
        Dicionário de configuração. Cada chave é o identificador do botão.
        Cada valor é um dict com: "label" (obrigatório), "icon", "url",
        "description" (opcional), "icon_size" (opcional), "button_size" (opcional).
    url_callback : callable
        Função chamada ao clicar em um botão, recebe a url como argumento.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        config: dict = None,
        url_callback=None,
        parent=None,
    ):
        super().__init__(parent)

        self._config = config or {}
        self._url_callback = url_callback

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
            url = btn_config.get("url", "")
            icon_size = btn_config.get("icon_size", QSize(32, 32))
            button_size = btn_config.get("button_size", QSize(40, 40))

            btn = SimpleIconButton(
                icon_path=icon_path,
                tooltip=tooltip,
                icon_size=icon_size,
                button_size=button_size,
                parent=self,
            )

            if self._url_callback and url:
                btn.clicked.connect(lambda checked, u=url: self._url_callback(u))
            layout.addWidget(btn)

        self._apply_styles()

    def _apply_styles(self):
        combined = self._specific_style()
        if combined:
            self.setStyleSheet(combined)

    def _specific_style(self) -> str:
        return ""