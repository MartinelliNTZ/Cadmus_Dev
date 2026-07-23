# -*- coding: utf-8 -*-
"""
SimpleQLineEdit — QLineEdit com gradiente 3 stops + glow shadow.
USO INTERNO apenas (para compor Grid widgets e Simple widgets).
NUNCA importado por plugins.
"""

from qgis.PyQt.QtWidgets import QLineEdit, QGraphicsDropShadowEffect
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt
from ...styles.AppStyles import AppStyles


def _glow_qcolor(hex_color: str, alpha: int) -> QColor:
    """Constrói QColor a partir de HEX + alpha (usa método estático do tema)."""
    from ...styles.BaseTheme import BaseTheme  # pylint: disable=import-outside-toplevel
    rgba_str = BaseTheme.rgba(hex_color, alpha)
    rgba_str = rgba_str.replace("rgba(", "").replace(")", "")
    parts = [int(x.strip()) for x in rgba_str.split(",")]
    return QColor(*parts)


class SimpleQLineEdit(QLineEdit):
    """
    QLineEdit sem borda, com gradiente de 3 stops + sombra colorida (glow),
    dando efeito de elevação/3D condizente com SimpleModernButton.

    CORES E DIMENSÕES VEM DO TEMA via AppStyles.
    Nada hardcoded aqui.

    Uso INTERNO apenas (SimpleReadOnly, etc).
    Plugins NUNCA importam isto.

    Parâmetros
    ----------
    text : str, optional
        Texto inicial.
    placeholder : str, optional
        Placeholder text.
    read_only : bool, optional
        Se True, o campo é readonly.
    primary : bool, optional
        True → estilo primary (paleta PRIMARY do tema).
        False → estilo secondary (paleta NEUTRAL do tema).
    object_name : str, optional
        Nome do objeto para seletor CSS específico.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        text="",
        placeholder="",
        read_only: bool = False,
        primary: bool = True,
        object_name: str = None,
        parent=None,
    ):
        super().__init__(parent)
        self._primary = primary
        self._object_name = object_name or f"modern_input_{id(self)}"
        self.setObjectName(self._object_name)

        if read_only:
            self.setReadOnly(True)
        if text:
            self.setText(str(text))
        if placeholder:
            self.setPlaceholderText(placeholder)

        # ── Dimensões do tema ──────────────────────────────────
        theme = self._get_theme()
        min_h = int(theme.MODERN_INPUT_MIN_HEIGHT.replace("px", ""))
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
        self._shadow_blur_normal = theme.MODERN_INPUT_SHADOW_BLUR_NORMAL
        self._shadow_blur_focused = theme.MODERN_INPUT_SHADOW_BLUR_FOCUSED
        self._shadow_offset_normal = theme.MODERN_INPUT_SHADOW_OFFSET_NORMAL
        self._shadow_offset_focused = theme.MODERN_INPUT_SHADOW_OFFSET_FOCUSED
        self._shadow.setBlurRadius(self._shadow_blur_normal)
        self._shadow.setOffset(0, self._shadow_offset_normal)
        self._shadow.setColor(glow_color)
        self.setGraphicsEffect(self._shadow)

        # ── Sinais ─────────────────────────────────────────────
        self.textChanged.connect(self._on_text_changed)

        # ── Aplica estilo do AppStyles ─────────────────────────
        self._apply_style()

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _get_theme():
        """Retorna tema atual via AppStyles (usa cache do AppStyles)."""
        return AppStyles._get_theme()

    def _on_text_changed(self, text):
        """Quando o texto muda, ajusta sombra para dar feedback visual."""
        if self.hasFocus():
            self._shadow.setBlurRadius(self._shadow_blur_focused)
            self._shadow.setOffset(0, self._shadow_offset_focused)
        else:
            self._shadow.setBlurRadius(self._shadow_blur_normal)
            self._shadow.setOffset(0, self._shadow_offset_normal)

    def focusInEvent(self, event):
        """Ao ganhar foco, expande a sombra para feedback visual."""
        super().focusInEvent(event)
        self._shadow.setBlurRadius(self._shadow_blur_focused)
        self._shadow.setOffset(0, self._shadow_offset_focused)

    def focusOutEvent(self, event):
        """Ao perder foco, retorna sombra ao normal."""
        super().focusOutEvent(event)
        self._shadow.setBlurRadius(self._shadow_blur_normal)
        self._shadow.setOffset(0, self._shadow_offset_normal)

    def _apply_style(self):
        """Aplica QSS via AppStyles conforme tipo."""
        if self._primary:
            qss = AppStyles.modern_input_primary(self._object_name)
        else:
            qss = AppStyles.modern_input_secondary(self._object_name)
        self.setStyleSheet(qss)