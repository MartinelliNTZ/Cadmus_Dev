# -*- coding: utf-8 -*-
"""
AppStyles — Estilos GLOBAIS do Cadmus
======================================
Ponto único de estilos visuais GLOBAIS.
Lê tokens do ThemeManager (cada token já contém unidade: "4px").

NUNCA use px nos estilos — tokens do tema já têm unidade.
NUNCA use 't' — use 'theme' sempre.

Uso:
    from resources.styles.AppStyles import AppStyles
    style = AppStyles.button()
"""

from __future__ import annotations
from typing import ClassVar, Optional


class AppStyles:
    """Estilos globais — lê do ThemeManager com cache."""

    _theme: ClassVar[Optional[object]] = None

    @classmethod
    def _get_theme(cls):
        """Retorna tema atual (com cache). Invalida com reload_theme()."""
        if cls._theme is None:
            from .ThemeManager import (
                theme_manager,
            )  # pylint: disable=import-outside-toplevel

            cls._theme = theme_manager.theme
        return cls._theme

    @classmethod
    def reload_theme(cls):
        """Invalida cache e recarrega tema."""
        from .ThemeManager import (
            theme_manager,
        )  # pylint: disable=import-outside-toplevel

        theme_manager.reload_theme()
        cls._theme = theme_manager.theme

    @classmethod
    def button(cls) -> str:
        """Estilo global para QPushButton."""
        theme = cls._get_theme()
        return (
            "QPushButton {"
            f"    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_PRIMARY},"
            f"        stop:1 {theme.COLOR_PRIMARY_DARK});"
            f"    color: {theme.COLOR_BUTTON_TEXT};"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY_DARK};"
            f"    border-radius: {theme.BORDER_RADIUS_BUTTON_DEFAULT};"
            f"    padding: {theme.PADDING_BUTTON_DEFAULT};"
            "}"
            "QPushButton:hover {"
            f"    background: {theme.COLOR_PRIMARY_LIGHT};"
            "}"
            "QPushButton:pressed {"
            f"    background: {theme.COLOR_PRIMARY_DARK};"
            "}"
            "QPushButton:disabled {"
            f"    background: {theme.COLOR_BACKGROUND_SOFT};"
            f"    color: {theme.COLOR_TEXT_SECONDARY};"
            "}"
        )

    @classmethod
    def label(cls) -> str:
        """Estilo global para QLabel."""
        theme = cls._get_theme()
        return (
            "QLabel {"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            f"    font-family: {theme.FONT_FAMILY_DEFAULT};"
            f"    font-size: {theme.FONT_SIZE_LABEL_TEXT};"
            "}"
        )

    @classmethod
    def input(cls) -> str:
        """Estilo global para QLineEdit, QSpinBox, QDoubleSpinBox."""
        theme = cls._get_theme()
        return (
            "QLineEdit,"
            "QSpinBox,"
            "QDoubleSpinBox {"
            f"    background: {theme.COLOR_BACKGROUND_PANEL};"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    border-radius: {theme.BORDER_RADIUS_INPUT_FIELD};"
            f"    padding: {theme.PADDING_INPUT_FIELD};"
            f"    min-height: {theme.INPUT_FIELD_MIN_HEIGHT};"
            f"    max-height: {theme.INPUT_FIELD_MAX_HEIGHT};"
            "}"
            "QLineEdit:focus,"
            "QSpinBox:focus,"
            "QDoubleSpinBox:focus {"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY};"
            "}"
        )

    @classmethod
    def checkbox(cls) -> str:
        """Estilo global para QCheckBox."""
        theme = cls._get_theme()
        return (
            "QCheckBox {"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            f"    font-family: {theme.FONT_FAMILY_DEFAULT};"
            f"    font-size: {theme.FONT_SIZE_LABEL_TEXT};"
            f"    spacing: {theme.CHECKBOX_LABEL_SPACING};"
            "}"
            "QCheckBox::indicator {"
            f"    width: {theme.CHECKBOX_INDICATOR_SIZE};"
            f"    height: {theme.CHECKBOX_INDICATOR_SIZE};"
            f"    border-radius: {theme.BORDER_RADIUS_CHECKBOX};"
            f"    border: {theme.CHECKBOX_BORDER_WIDTH} solid {theme.COLOR_BORDER_DEFAULT};"
            f"    background: {theme.COLOR_CHECKBOX_BACKGROUND};"
            "}"
            "QCheckBox::indicator:checked {"
            f"    background: {theme.COLOR_PRIMARY};"
            f"    border: {theme.CHECKBOX_BORDER_WIDTH} solid {theme.COLOR_PRIMARY_DARK};"
            "}"
        )

    @classmethod
    def radio_button(cls) -> str:
        """Estilo global para QRadioButton."""
        theme = cls._get_theme()
        return (
            "QRadioButton {"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            f"    font-family: {theme.FONT_FAMILY_DEFAULT};"
            f"    font-size: {theme.FONT_SIZE_LABEL_TEXT};"
            f"    spacing: {theme.CHECKBOX_LABEL_SPACING};"
            "}"
            "QRadioButton::indicator {"
            f"    width: {theme.RADIO_BUTTON_INDICATOR_SIZE};"
            f"    height: {theme.RADIO_BUTTON_INDICATOR_SIZE};"
            f"    border-radius: {theme.BORDER_RADIUS_RADIO_BUTTON};"
            f"    border: {theme.CHECKBOX_BORDER_WIDTH} solid {theme.COLOR_BORDER_DEFAULT};"
            f"    background: {theme.COLOR_BACKGROUND_PANEL};"
            "}"
            "QRadioButton::indicator:checked {"
            f"    background: {theme.COLOR_PRIMARY};"
            "}"
        )

    @classmethod
    def spinbox(cls) -> str:
        """Estilo global para QSpinBox e QDoubleSpinBox com setas."""
        theme = cls._get_theme()
        return (
            "QSpinBox,"
            "QDoubleSpinBox {"
            f"    background: {theme.COLOR_BACKGROUND_PANEL};"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            f"    font-family: {theme.FONT_FAMILY_DEFAULT};"
            f"    font-size: {theme.FONT_SIZE_INPUT_TEXT};"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    border-radius: {theme.BORDER_RADIUS_INPUT_FIELD};"
            f"    min-height: {theme.INPUT_FIELD_MIN_HEIGHT};"
            f"    padding: {theme.PADDING_INPUT_FIELD};"
            f"    padding-right: {theme.PADDING_INPUT_FIELD_RIGHT_EXTRA};"
            "}"
            "QSpinBox:hover,"
            "QDoubleSpinBox:hover {"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY_LIGHT};"
            "}"
            "QSpinBox:focus,"
            "QDoubleSpinBox:focus {"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY};"
            "}"
            "QSpinBox:disabled,"
            "QDoubleSpinBox:disabled {"
            f"    background: {theme.COLOR_BACKGROUND_SOFT};"
            f"    color: {theme.COLOR_TEXT_SECONDARY};"
            "}"
            "QSpinBox::up-button,"
            "QSpinBox::down-button,"
            "QDoubleSpinBox::up-button,"
            "QDoubleSpinBox::down-button {"
            f"    width: {theme.SPINBOX_ARROW_BUTTON_WIDTH};"
            f"    min-height: {theme.INPUT_FIELD_MIN_HEIGHT};"
            f"    border-radius: {theme.BORDER_RADIUS_SMALL_COMPONENT};"
            f"    border-left: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    background: {theme.COLOR_PRIMARY};"
            "    padding: 0px;"
            "    margin: 0px;"
            "}"
            "QSpinBox::up-button:hover,"
            "QSpinBox::down-button:hover,"
            "QDoubleSpinBox::up-button:hover,"
            "QDoubleSpinBox::down-button:hover {"
            f"    background: {theme.COLOR_PRIMARY_LIGHT};"
            "}"
            "QSpinBox::up-button:pressed,"
            "QSpinBox::down-button:pressed,"
            "QDoubleSpinBox::up-button:pressed,"
            "QDoubleSpinBox::down-button:pressed {"
            f"    background: {theme.COLOR_PRIMARY_DARK};"
            "}"
        )

    @classmethod
    def map_layer_combobox(cls) -> str:
        """Estilo global para QgsMapLayerComboBox."""
        theme = cls._get_theme()
        return (
            "QgsMapLayerComboBox {"
            f"    background: {theme.COLOR_BACKGROUND_PANEL};"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    border-radius: {theme.BORDER_RADIUS_INPUT_FIELD};"
            f"    padding: {theme.PADDING_INPUT_FIELD};"
            f"    min-height: {theme.INPUT_FIELD_MIN_HEIGHT};"
            "}"
            "QgsMapLayerComboBox:hover {"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY_LIGHT};"
            "}"
        )

    @classmethod
    def combobox(cls) -> str:
        """Estilo global para QComboBox."""
        import os

        theme = cls._get_theme()
        arrow_path = os.path.join(
            os.path.dirname(__file__), "..", "icons", "arrow_down.svg"
        ).replace("\\", "/")
        return (
            "QComboBox {"
            f"    background: {theme.COLOR_BACKGROUND_PANEL};"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    border-radius: {theme.BORDER_RADIUS_INPUT_FIELD};"
            f"    padding: {theme.PADDING_INPUT_FIELD};"
            f"    min-height: {theme.INPUT_FIELD_MIN_HEIGHT};"
            "}"
            "QComboBox:hover {"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY_LIGHT};"
            "}"
            "QComboBox:focus {"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY};"
            "}"
            "QComboBox::drop-down {"
            f"    width: {theme.SPINBOX_ARROW_BUTTON_WIDTH};"
            f"    border-left: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    background: {theme.COLOR_PRIMARY};"
            f"    border-top-right-radius: {theme.BORDER_RADIUS_INPUT_FIELD};"
            f"    border-bottom-right-radius: {theme.BORDER_RADIUS_INPUT_FIELD};"
            "}"
            "QComboBox::down-arrow {"
            f"    image: url(\"{arrow_path}\");"
            "    width: 12px;"
            "    height: 8px;"
            "}"
        )

    @classmethod
    def scroll_area(cls) -> str:
        """Estilo global para QScrollArea e QScrollBar."""
        theme = cls._get_theme()
        return (
            "QScrollArea {"
            "    border: none;"
            "    background: transparent;"
            "}"
            "QScrollBar:vertical {"
            f"    width: {theme.SCROLL_BAR_VERTICAL_WIDTH};"
            "    background: transparent;"
            "}"
            "QScrollBar::handle:vertical {"
            f"    background: {theme.COLOR_PRIMARY};"
            f"    border-radius: {theme.BORDER_RADIUS_SCROLL_BAR_HANDLE};"
            "}"
            "QScrollBar::handle:vertical:hover {"
            f"    background: {theme.COLOR_PRIMARY_LIGHT};"
            "}"
        )

    @classmethod
    def separator(cls) -> str:
        """Estilo global para SeparatorWidget (QFrame HLine)."""
        theme = cls._get_theme()
        return (
            "QFrame {"
            "    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"        stop:0 {theme.COLOR_BACKGROUND_PANEL},"
            f"        stop:0.5 {theme.COLOR_PRIMARY},"
            f"        stop:1 {theme.COLOR_BACKGROUND_PANEL});"
            "    border: none;"
            f"    margin: {theme.SEPARATOR_LINE_MARGIN};"
            "}"
        )

    @classmethod
    def main_application(cls) -> str:
        """Estilo global para o container principal."""
        theme = cls._get_theme()
        return (
            "#main_container {"
            "    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"        stop:0 {theme.COLOR_BACKGROUND_MAIN},"
            f"        stop:0.5 {theme.COLOR_BACKGROUND_PANEL},"
            f"        stop:1 {theme.COLOR_BACKGROUND_MAIN});"
            f"    border: {theme.CONTAINER_MAIN_BORDER_SIZE} solid {theme.COLOR_BORDER_DEFAULT};"
            f"    border-radius: {theme.BORDER_RADIUS_CONTAINER_MAIN};"
            "}"
            + cls.label()
            + cls.checkbox()
            + cls.radio_button()
            + cls.button()
            + cls.input()
            + cls.combobox()
            + cls.map_layer_combobox()
            + cls.scroll_area()
        )

    @classmethod
    def app_bar(cls) -> str:
        theme = cls._get_theme()

        # Ajusta o raio do appbar descontando a espessura do border do container,
        # para o arco do appbar coincidir com o arco externo do main_container.
        border_px = int(theme.CONTAINER_MAIN_BORDER_SIZE.replace("px", ""))
        radius_px = int(theme.BORDER_RADIUS_CONTAINER_MAIN.replace("px", ""))
        appbar_radius = f"{max(0, radius_px - border_px)}px"

        return (
            "#app_bar {"
            "    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"        stop:0 {theme.COLOR_PRIMARY_DARK},"
            f"        stop:1 {theme.COLOR_PRIMARY});"
            f"    border-bottom: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    border-top-left-radius: {appbar_radius};"
            f"    border-top-right-radius: {appbar_radius};"
            "    border-bottom-left-radius: 0px;"
            "    border-bottom-right-radius: 0px;"
            f"    min-height: {theme.APP_BAR_MIN_HEIGHT};"
            "}"
            "#app_bar_title {"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            f"    font-weight: {theme.APP_BAR_TITLE_FONT_WEIGHT};"
            f"    font-size: {theme.FONT_SIZE_APP_BAR_TITLE};"
            "}"
            "#app_bar_icon {"
            "    background: transparent;"
            "    border: none;"
            f"    padding: 0px;"
            "    margin: 0px 0px 0px 8px;"
            "}"
            "QPushButton#app_bar_btn_run {"
            f"    background: {theme.COLOR_PRIMARY};"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY_DARK};"
            f"    padding: {theme.PADDING_BUTTON_SMALL};"
            f"    font-weight: {theme.APP_BAR_RUN_BUTTON_FONT_WEIGHT};"
            f"    font-size: {theme.FONT_SIZE_BUTTON_TEXT};"
            "}"
            "QPushButton#app_bar_btn_run:hover {"
            f"    background: {theme.COLOR_PRIMARY_LIGHT};"
            "}"
            "QPushButton#app_bar_btn_info {"
            f"    background: {theme.COLOR_APP_BAR_INFO_BUTTON_BACKGROUND};"
            f"    color: {theme.COLOR_TEXT_SECONDARY};"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            "}"
            "QPushButton#app_bar_btn_info:hover {"
            f"    background: {theme.COLOR_APP_BAR_INFO_BUTTON_HOVER_BACKGROUND};"
            "}"
            "QPushButton#app_bar_btn_close {"
            "    background: transparent;"
            "    border: none;"
            f"    font-size: {theme.FONT_SIZE_APP_BAR_CLOSE_BUTTON};"
            "}"
        )

    @classmethod
    def panel(cls) -> str:
        """Estilo global para QFrame painel."""
        theme = cls._get_theme()
        return (
            "QFrame {"
            f"    background: {theme.COLOR_BACKGROUND_SOFT};"
            f"    border-radius: {theme.BORDER_RADIUS_BUTTON_DEFAULT};"
            f"    padding: {theme.PADDING_PANEL_CONTENT};"
            "}"
        )

    @classmethod
    def collapsible_parameters(cls) -> str:
        """Estilo global para CollapsibleParametersWidget."""
        theme = cls._get_theme()
        return (
            "#collapsible_header {"
            "    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f"        stop:0 {theme.COLOR_COLLAPSIBLE_HEADER_START_GRADIENT},"
            f"        stop:1 {theme.COLOR_COLLAPSIBLE_HEADER_END_GRADIENT});"
            f"    border-bottom: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    border-radius: {theme.BORDER_RADIUS_COLLAPSIBLE_HEADER} {theme.BORDER_RADIUS_COLLAPSIBLE_HEADER} 0 0;"
            "}"
            "#collapsible_header:hover {"
            "    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f"        stop:0 {theme.COLOR_COLLAPSIBLE_HEADER_HOVER_START_GRADIENT},"
            f"        stop:1 {theme.COLOR_COLLAPSIBLE_HEADER_HOVER_END_GRADIENT});"
            "}"
            "#collapsible_icon {"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            "    font-weight: bold;"
            f"    font-size: {theme.FONT_SIZE_SECTION_TITLE};"
            "    qproperty-alignment: AlignCenter;"
            "}"
            "#collapsible_title {"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            "    font-weight: bold;"
            f"    font-size: {theme.FONT_SIZE_LABEL_TEXT};"
            f"    font-family: {theme.FONT_FAMILY_DEFAULT};"
            "    background: transparent;"
            "}"
            "#collapsible_header_btn {"
            f"    background: {theme.COLLAPSIBLE_HEADER_BUTTON_BACKGROUND};"
            f"    border: {theme.COLLAPSIBLE_HEADER_BUTTON_BORDER};"
            "    padding: 0px;"
            "    margin: 0px;"
            "}"
            "#collapsible_content {"
            f"    background: {theme.COLOR_BACKGROUND_SOFT};"
            f"    border-bottom: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    border-left: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    border-right: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    border-radius: 0 0 {theme.BORDER_RADIUS_BUTTON_DEFAULT} {theme.BORDER_RADIUS_BUTTON_DEFAULT};"
            "}"
        )

    # ── Modern Input Styles (SimpleQLineEdit) ────────────────────────────

    @classmethod
    def modern_input_primary(cls, object_name: str = None) -> str:
        """
        Estilo para QLineEdit primário (modo normal/foco).
        Gradiente 3 stops na paleta PRIMARY, sem borda.
        Dimensões via Python (setMinimumHeight).

        Parâmetros
        ----------
        object_name : str, optional
            Se fornecido, usa seletor QLineEdit#object_name.
        """
        theme = cls._get_theme()
        sel = f"QLineEdit#{object_name}" if object_name else "QLineEdit"
        return (
            f"{sel} {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_BACKGROUND_PANEL},"
            f"        stop:0.5 {theme.COLOR_BACKGROUND_SOFT},"
            f"        stop:1 {theme.COLOR_BACKGROUND_PANEL});"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            "    border: none;"
            f"    border-radius: {theme.BORDER_RADIUS_INPUT_FIELD};"
            f"    padding: {theme.INPUT_FIELD_PADDING};"
            f"    font-size: {theme.INPUT_FIELD_FONT_SIZE};"
            f"    font-weight: {theme.INPUT_FIELD_FONT_WEIGHT};"
            "}"
            f"{sel}:focus {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_PRIMARY_DARK},"
            f"        stop:0.3 {theme.COLOR_BACKGROUND_PANEL},"
            f"        stop:1 {theme.COLOR_BACKGROUND_PANEL});"
            "}"
            f"{sel}:disabled {{"
            f"    background: {theme.COLOR_NEUTRAL_DARK};"
            f"    color: {theme.COLOR_NEUTRAL};"
            "}"
        )

    @classmethod
    def modern_input_secondary(cls, object_name: str = None) -> str:
        """
        Estilo para QLineEdit secundário (modo normal/foco).
        Gradiente 3 stops na paleta NEUTRAL, sem borda.
        Dimensões via Python (setMinimumHeight).

        Parâmetros
        ----------
        object_name : str, optional
            Se fornecido, usa seletor QLineEdit#object_name.
        """
        theme = cls._get_theme()
        sel = f"QLineEdit#{object_name}" if object_name else "QLineEdit"
        return (
            f"{sel} {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_NEUTRAL_LIGHT},"
            f"        stop:0.5 {theme.COLOR_NEUTRAL},"
            f"        stop:1 {theme.COLOR_NEUTRAL_DARK});"
            f"    color: {theme.COLOR_WHITE};"
            "    border: none;"
            f"    border-radius: {theme.BORDER_RADIUS_INPUT_FIELD};"
            f"    padding: {theme.INPUT_FIELD_PADDING};"
            f"    font-size: {theme.INPUT_FIELD_FONT_SIZE};"
            f"    font-weight: {theme.INPUT_FIELD_FONT_WEIGHT};"
            "}"
            f"{sel}:focus {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_NEUTRAL},"
            f"        stop:0.5 {theme.COLOR_NEUTRAL_DARK},"
            f"        stop:1 {theme.COLOR_NEUTRAL_DARK});"
            "}"
            f"{sel}:disabled {{"
            f"    background: {theme.COLOR_NEUTRAL_DARK};"
            f"    color: {theme.COLOR_NEUTRAL};"
            "}"
        )

    # ── Modern Button Styles (GridExecutionButtons) ──────────────────────

    @classmethod
    def modern_button_primary(cls, object_name: str = None) -> str:
        """
        Estilo para botão primário (run/executar).
        Gradiente 3 stops usando paleta PRIMARY do tema.
        Sem borda. Dimensões setadas via Python (setMinimumHeight).

        Parâmetros
        ----------
        object_name : str, optional
            Se fornecido, usa seletor QPushButton#object_name para
            especificidade máxima. Se None, usa QPushButton genérico.
        """
        theme = cls._get_theme()
        sel = f"QPushButton#{object_name}" if object_name else "QPushButton"
        return (
            f"{sel} {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_PRIMARY_LIGHT},"
            f"        stop:0.5 {theme.COLOR_PRIMARY},"
            f"        stop:1 {theme.COLOR_PRIMARY_DARK});"
            f"    color: {theme.COLOR_BUTTON_TEXT};"
            "    border: none;"
            f"    border-radius: {theme.BORDER_RADIUS_BUTTON_DEFAULT};"
            f"    padding: {theme.BUTTON_PADDING};"
            f"    font-size: {theme.BUTTON_FONT_SIZE};"
            f"    font-weight: {theme.BUTTON_FONT_WEIGHT};"
            "}"
            f"{sel}:hover {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_PRIMARY},"
            f"        stop:0.5 {theme.COLOR_PRIMARY},"
            f"        stop:1 {theme.COLOR_PRIMARY_DARK});"
            "}"
            f"{sel}:pressed {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_PRIMARY_DARK},"
            f"        stop:0.5 {theme.COLOR_PRIMARY_DARK},"
            f"        stop:1 {theme.COLOR_PRIMARY_DARK});"
            "}"
            f"{sel}:disabled {{"
            f"    background: {theme.COLOR_NEUTRAL_DARK};"
            f"    color: {theme.COLOR_NEUTRAL};"
            "}"
        )

    @staticmethod
    def main_application_square():
        """
        #        Igual a main_application(), porém SEM background: usado quando
        #        MainLayout está em BackgroundTexture.SQUARE, cujo fundo é pintado
        #        manualmente via QPainter em EdgeFrame._paint_square_texture().
        #        Border/border-radius devem ser mantidos para o frame continuar
        #        com a mesma moldura visual do modo SOLID.
        #"""
        theme = AppStyles._get_theme()
        return f"""
                #main_container {{
                    background: transparent;
                    border-radius: {theme.BACKGROUND_BORDER_RADIUS}px;
                }}
            """

    @classmethod
    def modern_button_secondary(cls, object_name: str = None) -> str:
        """
        Estilo para botão secundário (Fechar, extras).
        Gradiente 3 stops usando paleta NEUTRAL do tema.
        Sem borda. Dimensões setadas via Python.

        Parâmetros
        ----------
        object_name : str, optional
            Se fornecido, usa seletor QPushButton#object_name.
        """
        theme = cls._get_theme()
        sel = f"QPushButton#{object_name}" if object_name else "QPushButton"
        return (
            f"{sel} {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_NEUTRAL_LIGHT},"
            f"        stop:0.5 {theme.COLOR_NEUTRAL},"
            f"        stop:1 {theme.COLOR_NEUTRAL_DARK});"
            f"    color: {theme.COLOR_WHITE};"
            "    border: none;"
            f"    border-radius: {theme.BORDER_RADIUS_BUTTON_DEFAULT};"
            f"    padding: {theme.BUTTON_PADDING};"
            f"    font-size: {theme.BUTTON_FONT_SIZE};"
            f"    font-weight: {theme.BUTTON_FONT_WEIGHT};"
            "}"
            f"{sel}:hover {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_NEUTRAL},"
            f"        stop:0.5 {theme.COLOR_NEUTRAL},"
            f"        stop:1 {theme.COLOR_NEUTRAL_DARK});"
            "}"
            f"{sel}:pressed {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_NEUTRAL_DARK},"
            f"        stop:0.5 {theme.COLOR_NEUTRAL_DARK},"
            f"        stop:1 {theme.COLOR_NEUTRAL_DARK});"
            "}"
            f"{sel}:disabled {{"
            f"    background: {theme.COLOR_NEUTRAL_DARK};"
            f"    color: {theme.COLOR_NEUTRAL};"
            "}"
        )

    @classmethod
    def modern_button_round_icon(cls, object_name: str = None) -> str:
        """
        Estilo para botão redondo de ícone (Config, Info).
        Usa paleta NEUTRAL, border-radius padrão (6px) como os demais botões.
        Dimensões fixas setadas via Python (setFixedSize).

        Parâmetros
        ----------
        object_name : str, optional
            Se fornecido, usa seletor QPushButton#object_name.
        """
        theme = cls._get_theme()
        sel = f"QPushButton#{object_name}" if object_name else "QPushButton"
        return (
            f"{sel} {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_NEUTRAL_LIGHT},"
            f"        stop:0.5 {theme.COLOR_NEUTRAL},"
            f"        stop:1 {theme.COLOR_NEUTRAL_DARK});"
            f"    color: {theme.COLOR_WHITE};"
            "    border: none;"
            f"    border-radius: {theme.BORDER_RADIUS_BUTTON_DEFAULT};"
            "    padding: 0px;"
            "    min-height: 0px;"
            "    max-height: 100px;"
            "}"
            f"{sel}:hover {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_NEUTRAL},"
            f"        stop:0.5 {theme.COLOR_NEUTRAL},"
            f"        stop:1 {theme.COLOR_NEUTRAL_DARK});"
            "}"
            f"{sel}:pressed {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_NEUTRAL_DARK},"
            f"        stop:0.5 {theme.COLOR_NEUTRAL_DARK},"
            f"        stop:1 {theme.COLOR_NEUTRAL_DARK});"
            "}"
            f"{sel}:disabled {{"
            f"    background: {theme.COLOR_NEUTRAL_DARK};"
            f"    color: {theme.COLOR_NEUTRAL};"
            "}"
        )

    @classmethod
    def square_icon_button(cls, object_name: str = None) -> str:
        """
        Estilo para SquareIconButton (botão quadrado de ícone).
        Gradiente 3 stops na paleta NEUTRAL, sem borda, sem padding.
        Dimensões fixas setadas via Python (setFixedSize).

        Parâmetros
        ----------
        object_name : str, optional
            Se fornecido, usa seletor QPushButton#object_name.
        """
        theme = cls._get_theme()
        sel = f"QPushButton#{object_name}" if object_name else "QPushButton"
        return (
            f"{sel} {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_NEUTRAL_LIGHT},"
            f"        stop:0.5 {theme.COLOR_NEUTRAL},"
            f"        stop:1 {theme.COLOR_NEUTRAL_DARK});"
            f"    color: {theme.COLOR_WHITE};"
            "    border: none;"
            f"    border-radius: {theme.BORDER_RADIUS_BUTTON_DEFAULT};"
            "    padding: 0px;"
            "    min-height: 30px;"
            "    max-height: 30px;"
            "}"
            f"{sel}:hover {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_NEUTRAL},"
            f"        stop:0.5 {theme.COLOR_NEUTRAL},"
            f"        stop:1 {theme.COLOR_NEUTRAL_DARK});"
            "}"
            f"{sel}:pressed {{"
            "    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"        stop:0 {theme.COLOR_NEUTRAL_DARK},"
            f"        stop:0.5 {theme.COLOR_NEUTRAL_DARK},"
            f"        stop:1 {theme.COLOR_NEUTRAL_DARK});"
            "}"
            f"{sel}:disabled {{"
            f"    background: {theme.COLOR_NEUTRAL_DARK};"
            f"    color: {theme.COLOR_NEUTRAL};"
            "}"
        )

    @classmethod
    def text_browser(cls) -> str:
        """Estilo global para QTextBrowser — sem borda, fundo transparente."""
        theme = cls._get_theme()
        return (
            "QTextBrowser {"
            f"    background: transparent;"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            "    border: none;"
            f"    font-size: {theme.INPUT_FIELD_FONT_SIZE};"
            f"    selection-background-color: {theme.COLOR_PRIMARY};"
            f"    selection-color: {theme.COLOR_WHITE};"
            "}"
        )

    @classmethod
    def calc_checkbox_grid_height(cls, num_items: int, items_per_row: int = 1) -> int:
        """Calcula altura total de um grid de checkboxes."""
        theme = cls._get_theme()
        rows = (num_items + items_per_row - 1) // items_per_row
        item_h = int(theme.ITEM_DEFAULT_HEIGHT.replace("px", ""))
        spacing = theme.LAYOUT_VERTICAL_SPACING
        return (rows * item_h) + ((rows - 1) * spacing)
