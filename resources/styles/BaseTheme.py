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
    # PALETA BASE — 9 CORES (3 grupos × 3 variações)
    # ════════════════════════════════════════════════════════════

    # ── Primary ────────────────────────────────────────────────
    COLOR_PRIMARY: str = "#8b5cf6"
    COLOR_PRIMARY_LIGHT: str = "#a78bfa"
    COLOR_PRIMARY_DARK: str = "#6d28d9"

    # ── Secondary ──────────────────────────────────────────────
    COLOR_SECONDARY: str = "#f59e0b"
    COLOR_SECONDARY_LIGHT: str = "#fbbf24"
    COLOR_SECONDARY_DARK: str = "#d97706"

    # ── Neutral ────────────────────────────────────────────────
    COLOR_NEUTRAL: str = "#6b7280"
    COLOR_NEUTRAL_LIGHT: str = "#9ca3af"
    COLOR_NEUTRAL_DARK: str = "#4b5563"

    # ════════════════════════════════════════════════════════════
    # CORES FIXAS (não variam entre temas)
    # ════════════════════════════════════════════════════════════

    COLOR_WHITE: str = "#ffffff"
    COLOR_BLACK: str = "#000000"
    COLOR_RED: str = "#ef4444"

    # ════════════════════════════════════════════════════════════
    # GLOW COLORS (para QGraphicsDropShadowEffect)
    # HEX + alpha separado para construir QColor via rgba()
    # ════════════════════════════════════════════════════════════

    COLOR_GLOW_PRIMARY: str = "#1446A0"
    COLOR_GLOW_PRIMARY_ALPHA: int = 110

    COLOR_GLOW_SECONDARY: str = "#d97706"
    COLOR_GLOW_SECONDARY_ALPHA: int = 110

    COLOR_GLOW_NEUTRAL: str = "#1f2937"
    COLOR_GLOW_NEUTRAL_ALPHA: int = 130

    # ════════════════════════════════════════════════════════════
    # CORES DE FUNDO / PAINEL
    # ════════════════════════════════════════════════════════════

    COLOR_BACKGROUND_MAIN: str = "#0f0f17"
    COLOR_BACKGROUND_PANEL: str = "#1b1b2b"
    COLOR_BACKGROUND_SOFT: str = "rgba(27, 27, 43, 220)"
    COLOR_BACKGROUND_TRANSPARENT: str = "transparent"

    # ════════════════════════════════════════════════════════════
    # CORES DE TEXTO
    # ════════════════════════════════════════════════════════════

    COLOR_TEXT_PRIMARY: str = "#f5f3ff"
    COLOR_TEXT_SECONDARY: str = "#c4b5fd"
    COLOR_BUTTON_TEXT: str = "#ffffff"

    # ════════════════════════════════════════════════════════════
    # CORES DE BORDA / CHECKBOX
    # ════════════════════════════════════════════════════════════

    COLOR_BORDER_DEFAULT: str = "#6d28d9"
    COLOR_CHECKBOX_BACKGROUND: str = "#312e81"

    # ════════════════════════════════════════════════════════════
    # CORES DE LISTA / SELEÇÃO
    # ════════════════════════════════════════════════════════════

    COLOR_LIST_SELECTION_BACKGROUND: str = "rgba(166, 120, 79, 120)"
    COLOR_LIST_SELECTION_HOVER_BACKGROUND: str = "rgba(166, 120, 79, 60)"

    # ════════════════════════════════════════════════════════════
    # CORES APP BAR
    # ════════════════════════════════════════════════════════════

    COLOR_APP_BAR_INFO_BUTTON_BACKGROUND: str = "rgba(255, 255, 255, 20)"
    COLOR_APP_BAR_INFO_BUTTON_HOVER_BACKGROUND: str = "rgba(255, 255, 255, 40)"

    # ════════════════════════════════════════════════════════════
    # CORES COLLAPSIBLE HEADER
    # ════════════════════════════════════════════════════════════

    COLOR_COLLAPSIBLE_HEADER_START_GRADIENT: str = "rgba(106, 74, 47, 100)"
    COLOR_COLLAPSIBLE_HEADER_END_GRADIENT: str = "rgba(166, 120, 79, 100)"
    COLOR_COLLAPSIBLE_HEADER_HOVER_START_GRADIENT: str = "rgba(106, 74, 47, 140)"
    COLOR_COLLAPSIBLE_HEADER_HOVER_END_GRADIENT: str = "rgba(166, 120, 79, 140)"

    # ════════════════════════════════════════════════════════════
    # FONTES
    # ════════════════════════════════════════════════════════════

    FONT_FAMILY_DEFAULT: str = "'Segoe UI', Arial, sans-serif"
    FONT_SIZE_APP_BAR_TITLE: str = "10.5pt"
    FONT_SIZE_BUTTON_TEXT: str = "8pt"
    FONT_SIZE_LABEL_TEXT: str = "9pt"
    FONT_SIZE_INPUT_TEXT: str = "9pt"
    FONT_SIZE_SECTION_TITLE: str = "12pt"
    FONT_SIZE_APP_BAR_CLOSE_BUTTON: str = "14pt"

    # ════════════════════════════════════════════════════════════
    # DIMENSÕES — TODAS COM UNIDADE
    # ════════════════════════════════════════════════════════════

    INPUT_FIELD_MIN_HEIGHT: str = "12px"
    INPUT_FIELD_MAX_HEIGHT: str = "18px"
    BUTTON_DEFAULT_MIN_HEIGHT: str = "12px"
    ITEM_DEFAULT_HEIGHT: str = "12px"

    CHECKBOX_INDICATOR_SIZE: str = "12px"
    RADIO_BUTTON_INDICATOR_SIZE: str = "12px"

    COLOR_BUTTON_HEX_INPUT_HEIGHT: str = "18px"
    COLOR_BUTTON_COPY_BUTTON_SIZE: str = "20px"
    COLOR_BUTTON_COPY_ICON_SIZE: str = "10px"

    APP_BAR_MIN_HEIGHT: str = "35px"

    SCROLL_BAR_VERTICAL_WIDTH: str = "8px"

    # ════════════════════════════════════════════════════════════
    # DIMENSÕES — BOTÕES MODERNOS (GridExecutionButtons)
    # ════════════════════════════════════════════════════════════

    BUTTON_MIN_HEIGHT: str = "36px"
    BUTTON_ROUND_ICON_SIZE: str = "32px"
    BUTTON_PADDING: str = "7px 22px"
    BUTTON_FONT_SIZE: str = "12px"
    BUTTON_FONT_WEIGHT: str = "600"

    # ════════════════════════════════════════════════════════════
    # SOMBRA — BOTÕES MODERNOS (GridExecutionButtons)
    # ════════════════════════════════════════════════════════════

    BUTTON_SHADOW_BLUR_NORMAL: int = 12
    BUTTON_SHADOW_BLUR_PRESSED: int = 4
    BUTTON_SHADOW_OFFSET_NORMAL: int = 3
    BUTTON_SHADOW_OFFSET_PRESSED: int = 1

    # ════════════════════════════════════════════════════════════
    # BORDAS — TODAS COM UNIDADE
    # ════════════════════════════════════════════════════════════

    PXBORDER_ONE: str = "1px solid"

    CHECKBOX_BORDER_WIDTH: str = "1px"

    # ════════════════════════════════════════════════════════════
    # BORDER RADIUS — TODOS COM UNIDADE
    # ════════════════════════════════════════════════════════════

    BORDER_RADIUS_INPUT_FIELD: str = "4px"
    BORDER_RADIUS_BUTTON_DEFAULT: str = "6px"
    BORDER_RADIUS_CHECKBOX: str = "3px"
    BORDER_RADIUS_RADIO_BUTTON: str = "6px"
    BORDER_RADIUS_CONTAINER_MAIN: str = "8px"
    BORDER_RADIUS_SMALL_COMPONENT: str = "2px"
    BORDER_RADIUS_SCROLL_BAR_HANDLE: str = "4px"
    BORDER_RADIUS_COLLAPSIBLE_HEADER: str = "6px"

    CONTAINER_MAIN_BORDER_SIZE: str = "3px"

    # ════════════════════════════════════════════════════════════
    # PADDINGS — TODOS COM UNIDADE
    # ════════════════════════════════════════════════════════════

    PADDING_INPUT_FIELD: str = "2px 8px"
    PADDING_INPUT_FIELD_RIGHT_EXTRA: str = "18px"
    PADDING_BUTTON_DEFAULT: str = "4px 12px"
    PADDING_BUTTON_SMALL: str = "4px 14px"
    PADDING_PANEL_CONTENT: str = "8px"
    PADDING_LIST_ITEM: str = "4px"

    # ════════════════════════════════════════════════════════════
    # SEPARADOR
    # ════════════════════════════════════════════════════════════

    SEPARATOR_LINE_HEIGHT: str = "3px"
    SEPARATOR_LINE_MARGIN: str = "4px 0px"

    # ════════════════════════════════════════════════════════════
    # ESPAÇAMENTOS
    # ════════════════════════════════════════════════════════════

    LAYOUT_VERTICAL_SPACING: int = 2
    LAYOUT_HORIZONTAL_SPACING: int = 2
    CHECKBOX_LABEL_SPACING: str = "6px"
    SPINBOX_ARROW_BUTTON_WIDTH: str = "16px"

    # ════════════════════════════════════════════════════════════
    # FLAGS BOOLEANAS PARA EFEITOS VISUAIS
    # ════════════════════════════════════════════════════════════

    ALLOW_COMPONENT_SHADOW: bool = True
    ALLOW_COMPONENT_GLOW: bool = False

    # ════════════════════════════════════════════════════════════
    # PROPRIEDADES COMPUTADAS
    # ════════════════════════════════════════════════════════════

    @property
    def BOX_SHADOW_COMPONENT(self) -> str:
        """Sombra para painéis e containers (se ALLOW_COMPONENT_SHADOW=True)."""
        if self.ALLOW_COMPONENT_SHADOW:
            return "0px 0px 6px rgba(0,0,0,0.4)"
        return "none"

    @property
    def COLLAPSIBLE_HEADER_BUTTON_BACKGROUND(self) -> str:
        return "transparent"

    @property
    def COLLAPSIBLE_HEADER_BUTTON_BORDER(self) -> str:
        return "none"

    @property
    def APP_BAR_TITLE_FONT_WEIGHT(self) -> str:
        return "bold"

    @property
    def APP_BAR_RUN_BUTTON_FONT_WEIGHT(self) -> str:
        return "bold"