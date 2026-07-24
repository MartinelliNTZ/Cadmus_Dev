# -*- coding: utf-8 -*-
"""
SquareIconButton — QPushButton quadrado para ícone, sem borda, com glow.
USO INTERNO apenas (ComplexSelector, GridExecutionButtons, SimpleReadOnly).
Plugins NUNCA importam isto.

Uso:
    btn = SquareIconButton(
        icon=IconManager.icon(IconManager.FILE1),
        tooltip="Selecionar arquivo",
        parent=self,
    )
"""

from qgis.PyQt.QtWidgets import QPushButton, QGraphicsDropShadowEffect, QSizePolicy
from qgis.PyQt.QtCore import Qt, QSize
from ...styles.AppStyles import AppStyles


# ── Compatibilidade Qt5 / Qt6 ──────────────────────────────────
try:
    _CURSOR_POINTING_HAND = Qt.CursorShape.PointingHandCursor  # Qt6
except AttributeError:
    _CURSOR_POINTING_HAND = Qt.PointingHandCursor  # Qt5

try:
    _SIZE_POLICY_FIXED = QSizePolicy.Policy.Fixed  # Qt6
except AttributeError:
    _SIZE_POLICY_FIXED = QSizePolicy.Fixed  # Qt5


class SquareIconButton(QPushButton):
    """
    QPushButton quadrado para ícone, sem borda, com glow shadow.

    Parâmetros
    ----------
    icon : QIcon
        Ícone do botão.
    tooltip : str, optional
        Tooltip do botão.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        icon=None,
        tooltip: str = "",
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(f"square_icon_btn_{id(self)}")
        self.setFlat(True)
        self.setCursor(_CURSOR_POINTING_HAND)
        self.setSizePolicy(_SIZE_POLICY_FIXED, _SIZE_POLICY_FIXED)

        if tooltip:
            self.setToolTip(tooltip)

        # ── Dimensões do tema ──────────────────────────────────
        theme = AppStyles._get_theme()
        sz = int(theme.BUTTON_ROUND_ICON_SIZE.replace("px", ""))
        self.setFixedSize(sz, sz)

        # ── Ícone ─────────────────────────────────────────────
        if icon is not None:
            self.setIcon(icon)
            self.setIconSize(QSize(16, 16))

        # ── Sombra (glow) ──────────────────────────────────────
        self._shadow = QGraphicsDropShadowEffect(self)
        glow_color = _glow_qcolor(
            theme.COLOR_GLOW_NEUTRAL, theme.COLOR_GLOW_NEUTRAL_ALPHA
        )
        self._shadow_blur_normal = theme.BUTTON_SHADOW_BLUR_NORMAL
        self._shadow_blur_pressed = theme.BUTTON_SHADOW_BLUR_PRESSED
        self._shadow_offset_normal = theme.BUTTON_SHADOW_OFFSET_NORMAL
        self._shadow_offset_pressed = theme.BUTTON_SHADOW_OFFSET_PRESSED
        self._shadow.setBlurRadius(self._shadow_blur_normal)
        self._shadow.setOffset(0, self._shadow_offset_normal)
        self._shadow.setColor(glow_color)
        self.setGraphicsEffect(self._shadow)

        # ── Sinais ─────────────────────────────────────────────
        self.pressed.connect(self._on_pressed)
        self.released.connect(self._on_released)

        # ── Aplica estilo ──────────────────────────────────────
        self.setStyleSheet(AppStyles.square_icon_button(self.objectName()))

    def _on_pressed(self):
        self._shadow.setBlurRadius(self._shadow_blur_pressed)
        self._shadow.setOffset(0, self._shadow_offset_pressed)

    def _on_released(self):
        self._shadow.setBlurRadius(self._shadow_blur_normal)
        self._shadow.setOffset(0, self._shadow_offset_normal)


def _glow_qcolor(hex_color: str, alpha: int):
    """Constrói QColor a partir de HEX + alpha."""
    from ...styles.BaseTheme import BaseTheme
    rgba_str = BaseTheme.rgba(hex_color, alpha)
    rgba_str = rgba_str.replace("rgba(", "").replace(")", "")
    parts = [int(x.strip()) for x in rgba_str.split(",")]
    from qgis.PyQt.QtGui import QColor
    return QColor(*parts)