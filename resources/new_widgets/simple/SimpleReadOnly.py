# -*- coding: utf-8 -*-
"""
SimpleReadOnly — QLineEdit readonly com AppStyles.input().
USO INTERNO — GridReadOnly usa este widget.
Plugins NUNCA importam Simple diretamente.
"""

from qgis.PyQt.QtWidgets import QLineEdit
from ...styles.AppStyles import AppStyles


class SimpleReadOnly(QLineEdit):
    """
    Campo de texto readonly com estilo de input.

    Parâmetros
    ----------
    text : str, optional
        Texto inicial.
    placeholder : str, optional
        Placeholder text.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(self, text: str = "", placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        if text:
            self.setText(text)
        if placeholder:
            self.setPlaceholderText(placeholder)
        self._apply_styles()

    def _apply_styles(self):
        """Aplica estilos globais de input."""
        self.setStyleSheet(AppStyles.input())

    def setText(self, text: str):
        """Sobrescreve para aceitar None."""
        super().setText(str(text) if text is not None else "")