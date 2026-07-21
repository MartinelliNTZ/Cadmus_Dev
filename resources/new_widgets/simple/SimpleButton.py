# -*- coding: utf-8 -*-
"""
SimpleButton — QPushButton com estilo global via AppStyles.
Uso INTERNO apenas (para construir Grid widgets e widgets da raiz).
NUNCA importado por plugins.
"""

from qgis.PyQt.QtWidgets import QPushButton
from ...styles.AppStyles import AppStyles


class SimpleButton(QPushButton):
    """
    QPushButton com estilo global AppStyles.button().

    Uso interno para compor widgets maiores.
    Plugin NUNCA importa isto — usa GridButton.

    Callbacks são passados via parâmetros no GridButton,
    não conectando sinais diretamente aqui.

    Parâmetros
    ----------
    text : str
        Texto do botão.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._apply_styles()

    def _apply_styles(self):
        combined = AppStyles.button() + self._specific_style()
        self.setStyleSheet(combined)

    def _specific_style(self) -> str:
        return ""