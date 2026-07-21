# -*- coding: utf-8 -*-
"""
Centraliza o tema visual do plugin.
Responsável apenas por DEFINIR estilos, não por aplicar lógica.

Uso:
    from resources.styles.BaseStyles import BaseStyles
    style = BaseStyles.button()
"""

from __future__ import annotations

from .ThemeManager import theme_manager


# Instância do tema ativo (CoffeTheme, DarkCharcoalTheme, etc.)
current_theme = theme_manager.theme


class BaseStyles:
    """
    Estilos base reutilizáveis entre diversos widgets.
    Todos os tokens visuais são lidos diretamente de current_theme,
    que por sua vez é resolvido pelo ThemeManager.
    """

    # ==========================================================
    # CORES
    # ==========================================================

    COLOR_PRIMARY = current_theme.COLOR_PRIMARY
    COLOR_PRIMARY_LIGHT = current_theme.COLOR_PRIMARY_LIGHT
    COLOR_PRIMARY_DARK = current_theme.COLOR_PRIMARY_DARK

    COLOR_BACKGROUND_MAIN = current_theme.COLOR_BACKGROUND_MAIN
    COLOR_BACKGROUND_PANEL = current_theme.COLOR_BACKGROUND_PANEL
    COLOR_BACKGROUND_SOFT = current_theme.COLOR_BACKGROUND_SOFT
    COLOR_BACKGROUN_TRANSPARENT = current_theme.COLOR_BACKGROUND_TRANSPARENT

    COLOR_TEXT_PRIMARY = current_theme.COLOR_TEXT_PRIMARY
    COLOR_TEXT_SECONDARY = current_theme.COLOR_TEXT_SECONDARY
    COLOR_BUTTON_TEXT = current_theme.COLOR_BUTTON_TEXT

    COLOR_BORDER = current_theme.COLOR_BORDER
    COLOR_CHECKBOX_BG = current_theme.COLOR_CHECKBOX_BG

    COLOR_APPBAR_INFO_BG = current_theme.COLOR_APPBAR_INFO_BG
    COLOR_APPBAR_INFO_BG_HOVER = current_theme.COLOR_APPBAR_INFO_BG_HOVER

    COLOR_LIST_SELECTION = current_theme.COLOR_LIST_SELECTION
    COLOR_LIST_SELECTION_HOVER = current_theme.COLOR_LIST_SELECTION_HOVER

    COLOR_COLLAPSIBLE_HEADER_START = current_theme.COLOR_COLLAPSIBLE_HEADER_START
    COLOR_COLLAPSIBLE_HEADER_END = current_theme.COLOR_COLLAPSIBLE_HEADER_END

    COLOR_COLLAPSIBLE_HEADER_HOVER_START = (
        current_theme.COLOR_COLLAPSIBLE_HEADER_HOVER_START
    )
    COLOR_COLLAPSIBLE_HEADER_HOVER_END = current_theme.COLOR_COLLAPSIBLE_HEADER_HOVER_END

    # ==========================================================
    # FONTES
    # ==========================================================

    FONT_FAMILY_DEFAULT = current_theme.FONT_FAMILY_DEFAULT
    FONT_SIZE_TITLE = current_theme.FONT_SIZE_TITLE
    FONT_SIZE_NORMAL = current_theme.FONT_SIZE_NORMAL
    FONT_SIZE_SMALL = current_theme.FONT_SIZE_SMALL
    FONT_SIZE_BIG = current_theme.FONT_SIZE_BIG

    # ==========================================================
    # DIMENSÕES
    # ==========================================================

    STANDARD_SIZE = current_theme.STANDARD_SIZE
    INPUT_HEIGHT = current_theme.INPUT_HEIGHT
    BUTTON_HEIGHT = current_theme.BUTTON_HEIGHT
    ITEM_HEIGHT = current_theme.ITEM_HEIGHT

    CHECKBOX_SIZE = current_theme.CHECKBOX_SIZE
    RADIO_SIZE = current_theme.RADIO_SIZE

    COLOR_BUTTON_HEX_HEIGHT = current_theme.COLOR_BUTTON_HEX_HEIGHT
    COLOR_BUTTON_PICKER_HEIGHT = current_theme.COLOR_BUTTON_PICKER_HEIGHT
    COLOR_BUTTON_COPY_SIZE = current_theme.COLOR_BUTTON_COPY_SIZE
    COLOR_BUTTON_COPY_ICON_SIZE = current_theme.COLOR_BUTTON_COPY_ICON_SIZE

    # ==========================================================
    # ESPAÇAMENTOS
    # ==========================================================

    LAYOUT_V_SPACING = current_theme.LAYOUT_V_SPACING
    LAYOUT_H_SPACING = current_theme.LAYOUT_H_SPACING
    CONTENT_PADDING = current_theme.CONTENT_PADDING

    # ==========================================================
    # CHECKBOX / RADIO
    # ==========================================================

    CHECKBOX_BORDER_RADIUS = current_theme.CHECKBOX_BORDER_RADIUS
    CHECKBOX_BORDER_WIDTH = current_theme.CHECKBOX_BORDER_WIDTH
    CHECKBOX_SPACING = current_theme.CHECKBOX_SPACING
    RADIO_BORDER_RADIUS = current_theme.RADIO_BORDER_RADIUS

    # ==========================================================
    # BOTÕES
    # ==========================================================

    BUTTON_BORDER_RADIUS = current_theme.BUTTON_BORDER_RADIUS
    BUTTON_PADDING = current_theme.BUTTON_PADDING

    # ==========================================================
    # INPUTS
    # ==========================================================

    INPUT_BORDER_RADIUS = current_theme.INPUT_BORDER_RADIUS
    INPUT_PADDING = current_theme.INPUT_PADDING

    # ==========================================================
    # HELPERS DE ESTILO
    # ==========================================================

    @staticmethod
    def spinbox() -> str:
        return f"""
        QSpinBox,
        QDoubleSpinBox {{
            background: {current_theme.COLOR_BACKGROUND_PANEL};
            color: {current_theme.COLOR_TEXT_PRIMARY};
            font-family: {current_theme.FONT_FAMILY_DEFAULT};
            font-size: {current_theme.FONT_SIZE_NORMAL};
            border: 1px solid {current_theme.COLOR_BORDER};
            border-radius: {current_theme.INPUT_BORDER_RADIUS}px;
            min-height: {current_theme.INPUT_HEIGHT}px;
            padding: 2px 4px;
            padding-right: 18px;
        }}

        QSpinBox:hover,
        QDoubleSpinBox:hover {{
            border: 1px solid {current_theme.COLOR_PRIMARY_LIGHT};
        }}

        QSpinBox:focus,
        QDoubleSpinBox:focus {{
            border: 1px solid {current_theme.COLOR_PRIMARY};
        }}

        QSpinBox:disabled,
        QDoubleSpinBox:disabled {{
            background: {current_theme.COLOR_BACKGROUND_SOFT};
            color: {current_theme.COLOR_TEXT_SECONDARY};
        }}

        QSpinBox::up-button,
        QSpinBox::down-button,
        QDoubleSpinBox::up-button,
        QDoubleSpinBox::down-button {{
            width: 16px;
            height: {current_theme.INPUT_HEIGHT}px;
            border-radius: 2px;
            border-left: 1px solid {current_theme.COLOR_BORDER};
            background: {current_theme.COLOR_PRIMARY};
            padding: 0px;
            margin: 0px;
        }}

        QSpinBox::up-button:hover,
        QSpinBox::down-button:hover,
        QDoubleSpinBox::up-button:hover,
        QDoubleSpinBox::down-button:hover {{
            background: {current_theme.COLOR_PRIMARY_LIGHT};
        }}

        QSpinBox::up-button:pressed,
        QSpinBox::down-button:pressed,
        QDoubleSpinBox::up-button:pressed,
        QDoubleSpinBox::down-button:pressed {{
            background: {current_theme.COLOR_PRIMARY_DARK};
        }}
        """

    @staticmethod
    def checkbox() -> str:
        return f"""
        QCheckBox {{
            color: {current_theme.COLOR_TEXT_PRIMARY};
            font-family: {current_theme.FONT_FAMILY_DEFAULT};
            font-size: {current_theme.FONT_SIZE_NORMAL};
            spacing: {current_theme.CHECKBOX_SPACING}px;
        }}

        QCheckBox::indicator {{
            width: {current_theme.CHECKBOX_SIZE}px;
            height: {current_theme.CHECKBOX_SIZE}px;
            border-radius: {current_theme.CHECKBOX_BORDER_RADIUS}px;
            border: {current_theme.CHECKBOX_BORDER_WIDTH}px solid {current_theme.COLOR_BORDER};
            background: {current_theme.COLOR_CHECKBOX_BG};
        }}

        QCheckBox::indicator:checked {{
            background: {current_theme.COLOR_PRIMARY};
            border: {current_theme.CHECKBOX_BORDER_WIDTH}px solid {current_theme.COLOR_PRIMARY_DARK};
        }}
        """

    @staticmethod
    def radio_button() -> str:
        return f"""
        QRadioButton {{
            color: {current_theme.COLOR_TEXT_PRIMARY};
            font-family: {current_theme.FONT_FAMILY_DEFAULT};
            font-size: {current_theme.FONT_SIZE_NORMAL};
            spacing: {current_theme.CHECKBOX_SPACING}px;
        }}

        QRadioButton::indicator {{
            width: {current_theme.RADIO_SIZE}px;
            height: {current_theme.RADIO_SIZE}px;
            border-radius: {current_theme.RADIO_BORDER_RADIUS}px;
            border: {current_theme.CHECKBOX_BORDER_WIDTH}px solid {current_theme.COLOR_BORDER};
            background: {current_theme.COLOR_BACKGROUND_PANEL};
        }}

        QRadioButton::indicator:checked {{
            background: {current_theme.COLOR_PRIMARY};
        }}
        """

    @staticmethod
    def button() -> str:
        return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {current_theme.COLOR_PRIMARY},
                stop:1 {current_theme.COLOR_PRIMARY_DARK});
            color: {current_theme.COLOR_BUTTON_TEXT};
            border: 1px solid {current_theme.COLOR_PRIMARY_DARK};
            border-radius: {current_theme.BUTTON_BORDER_RADIUS}px;
            padding: {current_theme.BUTTON_PADDING};
            min-height: {current_theme.BUTTON_HEIGHT}px;
        }}

        QPushButton:hover {{
            background: {current_theme.COLOR_PRIMARY_LIGHT};
        }}

        QPushButton:pressed {{
            background: {current_theme.COLOR_PRIMARY_DARK};
        }}

        QPushButton:disabled {{
            background: {current_theme.COLOR_BACKGROUND_SOFT};
            color: {current_theme.COLOR_TEXT_SECONDARY};
        }}
        """

    @staticmethod
    def label() -> str:
        return f"""
        QLabel {{
            color: {current_theme.COLOR_TEXT_PRIMARY};
            font-family: {current_theme.FONT_FAMILY_DEFAULT};
            font-size: {current_theme.FONT_SIZE_NORMAL};
        }}
        """

    @staticmethod
    def input() -> str:
        return f"""
        QLineEdit,
        QSpinBox,
        QDoubleSpinBox {{
            background: {current_theme.COLOR_BACKGROUND_PANEL};
            color: {current_theme.COLOR_TEXT_PRIMARY};
            border: 1px solid {current_theme.COLOR_BORDER};
            border-radius: {current_theme.INPUT_BORDER_RADIUS}px;
            padding: {current_theme.INPUT_PADDING};
            min-height: {current_theme.INPUT_HEIGHT}px;
            max-height: {current_theme.INPUT_HEIGHT + 6}px;
        }}

        QLineEdit:focus,
        QSpinBox:focus,
        QDoubleSpinBox:focus {{
            border: 1px solid {current_theme.COLOR_PRIMARY};
        }}
        """

    @staticmethod
    def map_layer_combobox() -> str:
        return f"""
        QgsMapLayerComboBox {{
            background: {current_theme.COLOR_BACKGROUND_PANEL};
            color: {current_theme.COLOR_TEXT_PRIMARY};
            border: 1px solid {current_theme.COLOR_BORDER};
            border-radius: {current_theme.INPUT_BORDER_RADIUS}px;
            padding: {current_theme.INPUT_PADDING};
            min-height: {current_theme.INPUT_HEIGHT}px;
        }}

        QgsMapLayerComboBox:hover {{
            border: 1px solid {current_theme.COLOR_PRIMARY_LIGHT};
        }}
        """

    @staticmethod
    def scroll_area() -> str:
        return f"""
        QScrollArea {{
            border: none;
            background: transparent;
        }}

        QScrollBar:vertical {{
            width: 8px;
            background: transparent;
        }}

        QScrollBar::handle:vertical {{
            background: {current_theme.COLOR_PRIMARY};
            border-radius: 4px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {current_theme.COLOR_PRIMARY_LIGHT};
        }}
        """