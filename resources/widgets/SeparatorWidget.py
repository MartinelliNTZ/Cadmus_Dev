# -*- coding: utf-8 -*-
"""
SeparatorWidget — Separador visual entre widgets no layout.
É um QFrame HLine com gradiente horizontal, NÃO uma margem/padding.

Uso em plugins:
    layout.addWidget(widget1)
    layout.addWidget(SeparatorWidget())
    layout.addWidget(widget2)
"""

from qgis.PyQt.QtWidgets import QFrame
from ..styles.AppStyles import AppStyles
from ...utils.qt_compat import resolve_qframe_shape, resolve_qframe_shadow


class SeparatorWidget(QFrame):
    """
    Separador visual — QFrame com gradiente horizontal.

    Parâmetros
    ----------
    height : str, optional
        Altura do separador (default: theme.SEPARATOR_LINE_HEIGHT).
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(self, height: str = None, parent=None):
        super().__init__(parent)

        shape = resolve_qframe_shape("HLine")
        shadow = resolve_qframe_shadow("Sunken")

        self.setFrameShape(shape)
        self.setFrameShadow(shadow)

        theme = AppStyles._get_theme()
        h = height or theme.SEPARATOR_LINE_HEIGHT
        h_int = int(h.replace("px", ""))
        self.setFixedHeight(h_int)
        self.setStyleSheet(AppStyles.separator())