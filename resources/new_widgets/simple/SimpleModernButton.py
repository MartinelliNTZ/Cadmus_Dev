# -*- coding: utf-8 -*-
"""
SimpleModernButton — QPushButton com gradiente 3 stops + glow shadow.
USO INTERNO apenas (para compor Grid widgets e Simple widgets).
NUNCA importado por plugins.
"""

from qgis.PyQt.QtWidgets import (
    QPushButton,
    QGraphicsDropShadowEffect,
    QSizePolicy,
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt, QSize
from ...styles.AppStyles import AppStyles


# ── Compatibilidade Qt5 / Qt6 ──────────────────────────────────
try:
    _CURSOR_POINTING_HAND = Qt.CursorShape.PointingHandCursor  # Qt6
except AttributeError:
    _CURSOR_POINTING_HAND = Qt.PointingHandCursor  # Qt5

try:
    _SIZE_POLICY_PREFERRED = QSizePolicy.Policy.Preferred  # Qt6
    _SIZE_POLICY_FIXED = QSizePolicy.Policy.Fixed  # Qt6
except AttributeError:
    _SIZE_POLICY_PREFERRED = QSizePolicy.Preferred  # Qt5
    _SIZE_POLICY_FIXED = QSizePolicy.Fixed  # Qt5


def _glow_qcolor(hex_color: str, alpha: int) -> QColor:
    """Constrói QColor a partir de HEX + alpha (usa método estático do tema)."""
    from ...styles.BaseTheme import BaseTheme  # pylint: disable=import-outside-toplevel
    rgba_str = BaseTheme.rgba(hex_color, alpha)
    rgba_str = rgba_str.replace("rgba(", "").replace(")", "")
    parts = [int(x.strip()) for x in rgba_str.split(",")]
    return QColor(*parts)


class SimpleModernButton(QPushButton):
    """
    QPushButton sem borda, com gradiente de 3 stops (luz vindo de cima) +
    sombra colorida (glow), dando efeito de elevação/3D.

    CORES E DIMENSÕES VEM DO TEMA via AppStyles.
    Nada hardcoded aqui.

    Uso INTERNO apenas (GridExecutionButtons, SimpleReadOnly, etc).
    Plugins NUNCA importam isto.

    Parâmetros
    ----------
    text : str, optional
        Texto do botão.
    icon : QIcon, optional
        Ícone do botão.
    icon_size : QSize, optional
        Tamanho do ícone. Se não fornecido, usa 16x16 para round_icon.
    fixed_size : QSize ou int, optional
        Tamanho fixo do botão. Se for int, aplica em width e height.
        Se não fornecido, usa dimensões do tema (BUTTON_ROUND_ICON_SIZE
        para round_icon, BUTTON_MIN_HEIGHT para texto).
    tooltip : str, optional
        Tooltip do botão.
    parent : QWidget, optional
    primary : bool, optional
        True → estilo primary (paleta PRIMARY do tema).
        False → estilo secondary (paleta NEUTRAL do tema).
    round_icon : bool, optional
        True → botão de ícone (usa estilo modern_button_round_icon).
    object_name : str, optional
        Nome do objeto para seletor CSS específico.
    """

    def __init__(
        self,
        text="",
        icon=None,
        icon_size=None,
        fixed_size=None,
        tooltip="",
        parent=None,
        primary: bool = False,
        round_icon: bool = False,
        object_name: str = None,
    ):
        super().__init__(text, parent)
        self._primary = primary
        self._round_icon = round_icon
        self._object_name = object_name or f"modern_btn_{id(self)}"
        self.setObjectName(self._object_name)

        self.setCursor(_CURSOR_POINTING_HAND)
        self.setSizePolicy(_SIZE_POLICY_PREFERRED, _SIZE_POLICY_FIXED)
        # Só setFlat se não for round_icon com fixed_size (flat limita altura)
        if not (round_icon and fixed_size is not None):
            self.setFlat(True)

        if tooltip:
            self.setToolTip(tooltip)

        # ── Ícone ─────────────────────────────────────────────
        if icon is not None:
            self.setIcon(icon)
            if icon_size is not None:
                self.setIconSize(icon_size)
            else:
                self.setIconSize(QSize(16, 16))

        # ── Dimensões ─────────────────────────────────────────
        theme = self._get_theme()
        if fixed_size is not None:
            if isinstance(fixed_size, int):
                self.setFixedSize(fixed_size, fixed_size)
            else:
                self.setFixedSize(fixed_size)
        elif round_icon:
            sz = int(theme.BUTTON_ROUND_ICON_SIZE.replace("px", ""))
            self.setFixedSize(sz, sz)
            if icon_size is None:
                self.setIconSize(QSize(16, 16))
        else:
            min_h = int(theme.BUTTON_MIN_HEIGHT.replace("px", ""))
            self.setMinimumHeight(min_h)

        # ── Sombra (glow) ──────────────────────────────────────
        self._shadow = QGraphicsDropShadowEffect(self)
        if primary:
            glow_color = _glow_qcolor(
                theme.COLOR_GLOW_PRIMARY, theme.COLOR_GLOW_PRIMARY_ALPHA
            )
        else:
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

        # ── Aplica estilo do AppStyles ─────────────────────────
        self._apply_style()

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _get_theme():
        """Retorna tema atual via AppStyles (usa cache do AppStyles)."""
        return AppStyles._get_theme()

    def _on_pressed(self):
        self._shadow.setBlurRadius(self._shadow_blur_pressed)
        self._shadow.setOffset(0, self._shadow_offset_pressed)

    def _on_released(self):
        self._shadow.setBlurRadius(self._shadow_blur_normal)
        self._shadow.setOffset(0, self._shadow_offset_normal)

    def _apply_style(self):
        """Aplica QSS via AppStyles conforme tipo do botão."""
        if self._round_icon:
            qss = AppStyles.modern_button_round_icon(self._object_name)
        elif self._primary:
            qss = AppStyles.modern_button_primary(self._object_name)
        else:
            qss = AppStyles.modern_button_secondary(self._object_name)
        self.setStyleSheet(qss)