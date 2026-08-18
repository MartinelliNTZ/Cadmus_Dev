# -*- coding: utf-8 -*-
"""
BlackGoldTheme — Black + Gold visual theme
============================================
Concrete theme that inherits from BaseTheme and overrides every visual
token with a black + gold palette.

Usage:
    from .BaseTheme import BaseTheme
    from .BlackGoldTheme import BlackGoldTheme

    theme = BlackGoldTheme()
    app.setStyleSheet(build_stylesheet(theme))
"""

from __future__ import annotations

from .BaseTheme import BaseTheme


class BlackGoldTheme(BaseTheme):
    """
    Black + Gold theme.
    Deep black backgrounds combined with warm gold accents.
    """

    # ════════════════════════════════════════════════════════════
    # BACKGROUND GRID / SQUARE PATTERN
    # ════════════════════════════════════════════════════════════

    BACKGROUND_SQUARE_CELL_SIZE = 50
    BACKGROUND_SQUARE_BASE_COLOR = "#0a0a0a"
    BACKGROUND_SQUARE_LINE_ALPHA = 255
    BACKGROUND_SQUARE_GRADIENT_ALPHA = 255
    BACKGROUND_BORDER_RADIUS = 8

    # ════════════════════════════════════════════════════════════
    # BASE PALETTE — 9 COLORS (3 groups × 3 variations)
    # ════════════════════════════════════════════════════════════

    # ── Primary (Gold) ────────────────────────────────────────
    COLOR_PRIMARY: str = "#d4af37"
    COLOR_PRIMARY_LIGHT: str = "#f0d878"
    COLOR_PRIMARY_DARK: str = "#a6842a"

    # ── Secondary (Muted Gold / Bronze) ─────────────────────────
    COLOR_SECONDARY: str = "#8a7128"
    COLOR_SECONDARY_LIGHT: str = "#b3934a"
    COLOR_SECONDARY_DARK: str = "#5c4b1c"

    # ── Neutral (Black / Charcoal) ───────────────────────────────
    COLOR_NEUTRAL: str = "#1a1a1a"
    COLOR_NEUTRAL_LIGHT: str = "#2b2b2b"
    COLOR_NEUTRAL_DARK: str = "#0d0d0d"

    # ════════════════════════════════════════════════════════════
    # FIXED COLORS (do not vary between themes)
    # ════════════════════════════════════════════════════════════

    COLOR_WHITE: str = "#ffffff"
    COLOR_BLACK: str = "#000000"
    COLOR_RED: str = "#8a2c2c"  # Kept as a muted red for warnings/errors

    # ════════════════════════════════════════════════════════════
    # GLOW COLORS (for QGraphicsDropShadowEffect)
    # HEX + separate alpha to build QColor via rgba()
    # ════════════════════════════════════════════════════════════

    COLOR_GLOW_PRIMARY: str = "#d4af37"
    COLOR_GLOW_PRIMARY_ALPHA: int = 90

    COLOR_GLOW_SECONDARY: str = "#8a7128"
    COLOR_GLOW_SECONDARY_ALPHA: int = 80

    COLOR_GLOW_NEUTRAL: str = "#000000"
    COLOR_GLOW_NEUTRAL_ALPHA: int = 120

    # ════════════════════════════════════════════════════════════
    # BACKGROUND / PANEL COLORS
    # ════════════════════════════════════════════════════════════

    COLOR_BACKGROUND_MAIN: str = "#000000"
    COLOR_BACKGROUND_PANEL: str = "#121212"
    COLOR_BACKGROUND_SOFT: str = "rgba(18, 18, 18, 0.85)"
    COLOR_BACKGROUND_TRANSPARENT: str = "transparent"

    # ════════════════════════════════════════════════════════════
    # TEXT COLORS
    # ════════════════════════════════════════════════════════════

    COLOR_TEXT_PRIMARY: str = "#f5f0e1"
    COLOR_TEXT_SECONDARY: str = "#c9b77e"
    COLOR_BUTTON_TEXT: str = "#0d0d0d"  # Dark text on gold buttons

    # ════════════════════════════════════════════════════════════
    # BORDER / CHECKBOX COLORS
    # ════════════════════════════════════════════════════════════

    COLOR_BORDER_DEFAULT: str = "#3a3323"
    COLOR_CHECKBOX_BACKGROUND: str = "#2b2418"

    # ════════════════════════════════════════════════════════════
    # LIST / SELECTION COLORS
    # ════════════════════════════════════════════════════════════

    COLOR_LIST_SELECTION_BACKGROUND: str = "rgba(212, 175, 55, 110)"
    COLOR_LIST_SELECTION_HOVER_BACKGROUND: str = "rgba(212, 175, 55, 55)"

    # ════════════════════════════════════════════════════════════
    # APP BAR COLORS
    # ════════════════════════════════════════════════════════════

    COLOR_APP_BAR_INFO_BUTTON_BACKGROUND: str = "rgba(212, 175, 55, 25)"
    COLOR_APP_BAR_INFO_BUTTON_HOVER_BACKGROUND: str = "rgba(212, 175, 55, 50)"

    COLOR_COLLAPSIBLE_HEADER_HOVER_END_GRADIENT: str = "rgba(212, 175, 55, 140)"

    # ════════════════════════════════════════════════════════════
    # FONTS
    # ════════════════════════════════════════════════════════════

    FONT_FAMILY_DEFAULT: str = "'Segoe UI', Arial, sans-serif"
    FONT_SIZE_APP_BAR_TITLE: str = "10.5pt"
    FONT_SIZE_BUTTON_TEXT: str = "8pt"
    FONT_SIZE_LABEL_TEXT: str = "9pt"
    FONT_SIZE_INPUT_TEXT: str = "9pt"
    FONT_SIZE_SECTION_TITLE: str = "12pt"
    FONT_SIZE_APP_BAR_CLOSE_BUTTON: str = "14pt"

    # ════════════════════════════════════════════════════════════
    # DIMENSIONS — ALL WITH UNITS
    # ════════════════════════════════════════════════════════════

    INPUT_FIELD_MIN_HEIGHT: str = "22px"
    INPUT_FIELD_MAX_HEIGHT: str = "22px"
    INPUT_FIELD_PADDING: str = "4px 4px"
    INPUT_FIELD_FONT_SIZE: str = "11px"
    INPUT_FIELD_FONT_WEIGHT: str = "50"
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
    # SHADOW — INPUT FIELD
    # ════════════════════════════════════════════════════════════

    INPUT_SHADOW_BLUR_NORMAL: int = 8
    INPUT_SHADOW_BLUR_FOCUSED: int = 12
    INPUT_SHADOW_OFFSET_NORMAL: int = 2
    INPUT_SHADOW_OFFSET_FOCUSED: int = 2

    # ════════════════════════════════════════════════════════════
    # DIMENSIONS — MODERN BUTTONS (GridExecutionButtons)
    # ════════════════════════════════════════════════════════════

    BUTTON_MIN_HEIGHT: str = "30px"
    BUTTON_ROUND_ICON_SIZE: str = "30px"
    BUTTON_PADDING: str = "4px 4px"
    BUTTON_FONT_SIZE: str = "12px"
    BUTTON_FONT_WEIGHT: str = "600"

    # ════════════════════════════════════════════════════════════
    # SHADOW — MODERN BUTTONS (GridExecutionButtons)
    # ════════════════════════════════════════════════════════════

    BUTTON_SHADOW_BLUR_NORMAL: int = 12
    BUTTON_SHADOW_BLUR_PRESSED: int = 4
    BUTTON_SHADOW_OFFSET_NORMAL: int = 3
    BUTTON_SHADOW_OFFSET_PRESSED: int = 1

    # ════════════════════════════════════════════════════════════
    # BORDERS — ALL WITH UNITS
    # ════════════════════════════════════════════════════════════

    PXBORDER_ONE: str = "1px solid"

    CHECKBOX_BORDER_WIDTH: str = "1px"

    # ════════════════════════════════════════════════════════════
    # BORDER RADIUS — ALL WITH UNITS
    # ════════════════════════════════════════════════════════════

    BORDER_RADIUS_INPUT_FIELD: str = "6px"
    BORDER_RADIUS_BUTTON_DEFAULT: str = "6px"
    BORDER_RADIUS_CHECKBOX: str = "3px"
    BORDER_RADIUS_RADIO_BUTTON: str = "6px"
    BORDER_RADIUS_CONTAINER_MAIN: str = "8px"
    BORDER_RADIUS_SMALL_COMPONENT: str = "2px"
    BORDER_RADIUS_SCROLL_BAR_HANDLE: str = "4px"
    BORDER_RADIUS_COLLAPSIBLE_HEADER: str = "6px"

    CONTAINER_MAIN_BORDER_SIZE: str = "3px"

    # ════════════════════════════════════════════════════════════
    # PADDINGS — ALL WITH UNITS
    # ════════════════════════════════════════════════════════════

    PADDING_INPUT_FIELD: str = "2px 4px"
    PADDING_INPUT_FIELD_RIGHT_EXTRA: str = "4px"
    PADDING_BUTTON_DEFAULT: str = "4px 4px"
    PADDING_BUTTON_SMALL: str = "4px 4px"
    PADDING_PANEL_CONTENT: str = "4px"
    PADDING_LIST_ITEM: str = "4px"

    # ════════════════════════════════════════════════════════════
    # SEPARATOR
    # ════════════════════════════════════════════════════════════

    SEPARATOR_LINE_HEIGHT: str = "3px"
    SEPARATOR_LINE_MARGIN: str = "4px 0px"

    # ════════════════════════════════════════════════════════════
    # SPACING
    # ════════════════════════════════════════════════════════════

    LAYOUT_VERTICAL_SPACING: int = 2
    LAYOUT_HORIZONTAL_SPACING: int = 2
    CHECKBOX_LABEL_SPACING: str = "6px"
    SPINBOX_ARROW_BUTTON_WIDTH: str = "16px"

    # ════════════════════════════════════════════════════════════
    # CONTAINER MARGINS
    # ════════════════════════════════════════════════════════════

    CONTAINER_MARGIN_LEFT: int = 8
    CONTAINER_MARGIN_TOP: int = 2
    CONTAINER_MARGIN_RIGHT: int = 8
    CONTAINER_MARGIN_BOTTOM: int = 2

    # ════════════════════════════════════════════════════════════
    # LABEL FIELD — minimum label width in field
    # ════════════════════════════════════════════════════════════

    LABEL_FIELD_MIN_WIDTH: int = 100

    # ════════════════════════════════════════════════════════════
    # BOOLEAN FLAGS FOR VISUAL EFFECTS
    # ════════════════════════════════════════════════════════════

    ALLOW_COMPONENT_SHADOW: bool = True
    ALLOW_COMPONENT_GLOW: bool = True
    ENABLE_GRID_CHECKBOX_BACKGROUND: bool = False

    # ════════════════════════════════════════════════════════════
    # COMPUTED PROPERTIES
    # ════════════════════════════════════════════════════════════

    @property
    def BOX_SHADOW_COMPONENT(self) -> str:
        """Shadow for panels and containers (if ALLOW_COMPONENT_SHADOW=True)."""
        if self.ALLOW_COMPONENT_SHADOW:
            return "0px 0px 8px rgba(0,0,0,0.6)"
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