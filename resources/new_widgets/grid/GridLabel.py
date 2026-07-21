# -*- coding: utf-8 -*-
"""
GridLabel — Container de labels para plugins.
Plugins USAM este widget (composto de SimpleLabel internamente).
"""

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout
from ..simple.SimpleLabel import SimpleLabel
from ...styles.AppStyles import AppStyles


class GridLabel(QWidget):
    """
    Container com labels em layout vertical.

    Uso em plugins:
        info = GridLabel(items=["Título", "Descrição"], parent=self)
        layout.addWidget(info)

    Parâmetros
    ----------
    items : list[str]
        Lista de textos para os labels.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(self, items: list[str], parent=None):
        super().__init__(parent)
        if not items:
            items = [""]

        self._labels = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(AppStyles._get_theme().LAYOUT_VERTICAL_SPACING)

        for text in items:
            label = SimpleLabel(text=text, parent=self)
            self._labels.append(label)
            layout.addWidget(label)

        self._apply_styles()

    def _apply_styles(self):
        combined = self._specific_style()
        if combined:
            self.setStyleSheet(combined)

    def _specific_style(self) -> str:
        return ""