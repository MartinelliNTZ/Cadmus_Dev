# -*- coding: utf-8 -*-
"""
BaseTheme — Classe base abstrata para todos os temas
======================================================
Define o contrato mínimo de tokens visuais que cada tema deve implementar.
Qualquer tema concreto (CoffeTheme, DarkCharcoalTheme, etc.) deve herdar
desta classe e sobrescrever todos os atributos.

Uso:
    class MeuTema(BaseTheme):
        COLOR_PRIMARY = "#ff6600"
        ...
"""

from __future__ import annotations


class BaseTheme:
    """
    Classe base para temas visuais.
    Contém todos os tokens que um tema deve definir.
    Os valores aqui são placeholders — temas concretos devem sobrescrevê-los.
    """

    # ════════════════════════════════════════════════════════════
    # UTILITÁRIO DE COR
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def rgba(hex_color: str, alpha: int) -> str:
        """
        Converte HEX + alpha para rgba().
        Exemplo:
        rgba("#a6784f", 120) -> "rgba(166,120,79,120)"
        """
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    # ════════════════════════════════════════════════════════════
    # CORES BASE
    # ════════════════════════════════════════════════════════════

    COLOR_PRIMARY: str = "#000000"
    COLOR_PRIMARY_LIGHT: str = "#333333"
    COLOR_PRIMARY_DARK: str = "#000000"

    COLOR_BACKGROUND_MAIN: str = "#000000"
    COLOR_BACKGROUND_PANEL: str = "#111111"
    COLOR_BACKGROUND_SOFT: str = "#1a1a1a"
    COLOR_BACKGROUND_TRANSPARENT: str = "transparent"

    COLOR_TEXT_PRIMARY: str = "#ffffff"
    COLOR_TEXT_SECONDARY: str = "#cccccc"
    COLOR_BUTTON_TEXT: str = "#ffffff"

    COLOR_BORDER: str = "#333333"

    COLOR_CHECKBOX_BG: str = "#444444"

    COLOR_APPBAR_INFO_BG: str = "rgba(255, 255, 255, 20)"
    COLOR_APPBAR_INFO_BG_HOVER: str = "rgba(255, 255, 255, 40)"

    COLOR_LIST_SELECTION: str = "rgba(100, 100, 100, 120)"
    COLOR_LIST_SELECTION_HOVER: str = "rgba(100, 100, 100, 60)"

    COLOR_COLLAPSIBLE_HEADER_START: str = "rgba(80, 80, 80, 100)"
    COLOR_COLLAPSIBLE_HEADER_END: str = "rgba(120, 120, 120, 100)"

    COLOR_COLLAPSIBLE_HEADER_HOVER_START: str = "rgba(80, 80, 80, 140)"
    COLOR_COLLAPSIBLE_HEADER_HOVER_END: str = "rgba(120, 120, 120, 140)"

    # ════════════════════════════════════════════════════════════
    # FONTES
    # ════════════════════════════════════════════════════════════

    FONT_FAMILY_DEFAULT: str = "'Segoe UI', Arial, sans-serif"
    FONT_SIZE_TITLE: str = "20pt"
    FONT_SIZE_BIG: str = "12pt"
    FONT_SIZE_NORMAL: str = "9pt"
    FONT_SIZE_SMALL: str = "8pt"

    # ════════════════════════════════════════════════════════════
    # DIMENSÕES BASE
    # ════════════════════════════════════════════════════════════

    STANDARD_SIZE: int = 12

    INPUT_HEIGHT: int = STANDARD_SIZE
    BUTTON_HEIGHT: int = STANDARD_SIZE
    ITEM_HEIGHT: int = STANDARD_SIZE
    CHECKBOX_SIZE: int = STANDARD_SIZE
    RADIO_SIZE: int = STANDARD_SIZE
    COLOR_BUTTON_HEX_HEIGHT: int = 18
    COLOR_BUTTON_PICKER_HEIGHT: int = 18
    COLOR_BUTTON_COPY_SIZE: int = 20
    COLOR_BUTTON_COPY_ICON_SIZE: int = 10

    # ════════════════════════════════════════════════════════════
    # ESPAÇAMENTOS
    # ════════════════════════════════════════════════════════════

    LAYOUT_V_SPACING: int = 2
    LAYOUT_H_SPACING: int = 2
    CONTENT_PADDING: int = 2

    # ════════════════════════════════════════════════════════════
    # CHECKBOX
    # ════════════════════════════════════════════════════════════

    CHECKBOX_BORDER_RADIUS: int = 3
    CHECKBOX_BORDER_WIDTH: int = 1
    CHECKBOX_SPACING: int = 6

    # ════════════════════════════════════════════════════════════
    # RADIO BUTTON
    # ════════════════════════════════════════════════════════════

    RADIO_BORDER_RADIUS: int = 6

    # ════════════════════════════════════════════════════════════
    # BOTÕES
    # ════════════════════════════════════════════════════════════

    BUTTON_BORDER_RADIUS: int = 6
    BUTTON_PADDING: str = "4px 12px"

    # ════════════════════════════════════════════════════════════
    # INPUTS
    # ════════════════════════════════════════════════════════════

    INPUT_BORDER_RADIUS: int = 4
    INPUT_PADDING: str = "2px 8px"