# -*- coding: utf-8 -*-
"""
SimpleLabel — QLabel com estilo global via AppStyles.
Uso INTERNO apenas (para construir Grid widgets e widgets da raiz).
NUNCA importado por plugins.
"""

from qgis.PyQt.QtWidgets import QLabel
from ...styles.AppStyles import AppStyles


class SimpleLabel(QLabel):
    """
    QLabel com estilo global AppStyles.label().

    Uso interno para compor widgets maiores.
    Plugin NUNCA importa isto — usa GridLabel.

    Parâmetros
    ----------
    text : str
        Texto do label.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._apply_styles()

    def _apply_styles(self):
        combined = AppStyles.label() + self._specific_style()
        self.setStyleSheet(combined)

    def _specific_style(self) -> str:
        return ""