# -*- coding: utf-8 -*-
"""
SimpleIconButton — QPushButton com ícone e estilo global via AppStyles.
Uso INTERNO apenas (para construir Grid widgets e widgets da raiz).
NUNCA importado por plugins.
"""

from qgis.PyQt.QtWidgets import QPushButton
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSize, Qt
from ...styles.AppStyles import AppStyles


class SimpleIconButton(QPushButton):
    """
    QPushButton com ícone e estilo global AppStyles.button().

    Uso interno para compor widgets maiores (ex: GridIconButton).
    Plugin NUNCA importa isto — usa GridIconButton.

    Parâmetros
    ----------
    icon_path : str
        Caminho completo do arquivo de ícone.
    tooltip : str, optional
        Tooltip do botão.
    icon_size : QSize, optional
        Tamanho do ícone (default: 32x32).
    button_size : QSize, optional
        Tamanho fixo do botão (default: 40x40).
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        icon_path: str,
        tooltip: str = "",
        icon_size: QSize = None,
        button_size: QSize = None,
        parent=None,
    ):
        super().__init__(parent)

        if icon_size is None:
            icon_size = QSize(32, 32)
        if button_size is None:
            button_size = QSize(40, 40)

        self.setIcon(QIcon(icon_path))
        self.setIconSize(icon_size)
        self.setFixedSize(button_size)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)

        self._apply_styles()

    def _apply_styles(self):
        combined = AppStyles.button() + self._specific_style()
        self.setStyleSheet(combined)

    def _specific_style(self) -> str:
        return (
            "QPushButton {"
            "    border: none;"
            "    background: transparent;"
            "}"
            "QPushButton:hover {"
            "    background: rgba(255, 255, 255, 30);"
            "    border-radius: 6px;"
            "}"
        )