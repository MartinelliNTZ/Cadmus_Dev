# -*- coding: utf-8 -*-
"""
GridInputFields — Container de campos de entrada de texto com labels.
=====================================================================
Plugins USAM este widget. NUNCA importa Simple diretamente.

CADA CAMPO: label + input na MESMA LINHA (QHBoxLayout).
TODAS as dimensoes (margins, spacing, padding, height) vem do tema.

title=None → SEM QGroupBox, SEM espaco para titulo.

Cada item do config dict:
    key (identificador unico):
        "label" (obrigatorio): texto do label do campo
        "description" (opcional): tooltip do campo
        "default" (opcional): str, valor inicial

Uso em plugins:
    input_fields = GridInputFields(
        config={
            "old_text": {
                "label": "Texto a buscar",
                "description": "Texto original",
                "default": "",
            },
            "new_text": {
                "label": "Substituir por",
                "description": "Novo texto",
                "default": "",
            },
        },
        title=None,
        separator_bottom=True,
        parent=self,
    )
    self.layout.addWidget(input_fields)
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
)
from qgis.PyQt.QtCore import Qt

from ..simple.SimpleQLineEdit import SimpleQLineEdit
from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles


class GridInputFields(QWidget):
    """
    Container de campos de entrada de texto com labels, configurável via dict.

    CADA CAMPO: label + SimpleQLineEdit na MESMA LINHA.
    TODAS dimensoes vem do tema via AppStyles + BaseTheme.

    Parâmetros
    ----------
    config : dict, optional
        Dict de campos. Chave = identificador.
        Valor = dict com:
            - "label" (obrigatorio): texto do label do campo
            - "description" (opcional): tooltip do campo
            - "default" (opcional): str, valor inicial
    title : str or None, optional
        Titulo do grupo (QGroupBox). None = sem grupo, sem espaco.
    separator_top : bool, optional
        Separador acima.
    separator_bottom : bool, optional
        Separador abaixo.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        config: dict = None,
        title: str = None,
        separator_top: bool = False,
        separator_bottom: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._config = config or {}
        self._title = title
        self._separator_top = separator_top
        self._separator_bottom = separator_bottom

        # Mapa interno: key -> SimpleQLineEdit
        self._fields: dict[str, SimpleQLineEdit] = {}

        self._build_ui()

    # -- Preferencias -------------------------------------------------

    def get_preferences(self) -> dict:
        """
        Retorna dict com todos os valores dos campos para salvar em Preferences.

        Returns
        -------
        dict
            {"values": {key: str, ...}} — valores de cada campo.
        """
        return {"values": self.get_values()}

    def set_preferences(self, prefs: dict):
        """
        Carrega valores dos campos de um dict (vindo de Preferences).

        Parâmetros
        ----------
        prefs : dict
            Dict com chave "values" ({key: str}).
        """
        if not prefs:
            return
        values = prefs.get("values")
        if isinstance(values, dict):
            self.set_values(values)

    # -- API publica -------------------------------------------------

    def get_value(self, key: str) -> str:
        """Retorna o valor do campo."""
        field = self._fields.get(key)
        return field.text() if field else ""

    def set_value(self, key: str, value: str):
        """Define o valor do campo."""
        field = self._fields.get(key)
        if field:
            field.setText(str(value))

    def get_values(self) -> dict[str, str]:
        """Retorna todos os valores como dict {key: value}."""
        return {key: field.text() for key, field in self._fields.items()}

    def set_values(self, values: dict[str, str]):
        """Define valores de multiplos campos via dict {key: value}."""
        for key, value in values.items():
            self.set_value(key, value)

    def widget(self, key: str):
        """Acesso direto ao QLineEdit (para signals)."""
        return self._fields.get(key)

    # -- Build -------------------------------------------------------

    def _build_ui(self):
        """Monta layout com campos: label + input na mesma linha."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        theme = AppStyles._get_theme()

        if self._separator_top:
            outer_layout.addWidget(SeparatorWidget())
            # Pequeno espaco apos o separador superior
            outer_layout.addSpacing(theme.LAYOUT_VERTICAL_SPACING)

        # Container com titulo opcional
        if self._title:
            container = QGroupBox(self._title)
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(
                theme.CONTAINER_MARGIN_LEFT,
                theme.CONTAINER_MARGIN_TOP,
                theme.CONTAINER_MARGIN_RIGHT,
                theme.CONTAINER_MARGIN_BOTTOM,
            )
            container_layout.setSpacing(theme.LAYOUT_VERTICAL_SPACING)
        else:
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(theme.LAYOUT_VERTICAL_SPACING)

        # Cria campos (label + input na mesma linha)
        for key, field_config in self._config.items():
            label_text = field_config.get("label", key)
            description = field_config.get("description", "")
            default = field_config.get("default", "")

            # Linha horizontal: label + input
            row_layout = QHBoxLayout()
            row_layout.setSpacing(theme.LAYOUT_HORIZONTAL_SPACING)
            row_layout.setContentsMargins(0, 0, 0, 0)

            # Label — usa tamanhos do tema
            lbl = QLabel(label_text)
            lbl.setMinimumWidth(theme.LABEL_FIELD_MIN_WIDTH)
            lbl.setWordWrap(False)

            # Input com glow/gradiente (SimpleQLineEdit usa tokens do tema)
            input_field = SimpleQLineEdit(
                text=default,
                placeholder=description or label_text,
                read_only=False,
                primary=True,
                parent=self,
            )

            if description:
                input_field.setToolTip(description)

            # Suporte a placeholder explicito (suggest ao fundo)
            placeholder = field_config.get("placeholder")
            if placeholder:
                input_field.setPlaceholderText(placeholder)

            row_layout.addWidget(lbl)
            row_layout.addWidget(input_field, 1)  # stretch=1 para ocupar resto

            self._fields[key] = input_field
            container_layout.addLayout(row_layout)

        outer_layout.addWidget(container)

        if self._separator_bottom:
            # Pequeno espaco antes do separador inferior
            outer_layout.addSpacing(theme.LAYOUT_VERTICAL_SPACING)
            outer_layout.addWidget(SeparatorWidget())
