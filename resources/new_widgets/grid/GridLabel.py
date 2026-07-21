# -*- coding: utf-8 -*-
"""
GridLabel — Container de labels para plugins.
Plugins USAM este widget.

A configuração é um dict onde cada chave é o identificador do label,
e o valor é um dict com:
  - "text" (obrigatório): texto do label
  - "description" (opcional): tooltip do label
"""

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout
from ..simple.SimpleLabel import SimpleLabel
from ...styles.AppStyles import AppStyles


class GridLabel(QWidget):
    """
    Container com labels em layout vertical.

    Uso em plugins:
        info = GridLabel(config={
            "title": {"text": "<h2>Meu App</h2>"},
            "version": {"text": "Versão 1.0", "description": "Data de atualização"},
        }, parent=self)
        layout.addWidget(info)

    Parâmetros
    ----------
    config : dict
        Dict de labels. Cada chave é identificador, valor é dict com:
        - "text" (str): texto do label
        - "description" (str, optional): tooltip
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        if not config:
            config = {"label": {"text": ""}}

        self._labels = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(AppStyles._get_theme().LAYOUT_VERTICAL_SPACING)

        for key, cfg in config.items():
            text = cfg.get("text", "")
            label = SimpleLabel(text=text, parent=self)

            description = cfg.get("description")
            if description:
                label.setToolTip(description)

            self._labels.append(label)
            layout.addWidget(label)

        self._apply_styles()

    def _apply_styles(self):
        combined = self._specific_style()
        if combined:
            self.setStyleSheet(combined)

    def _specific_style(self) -> str:
        return ""