# -*- coding: utf-8 -*-
"""
GridReadOnly — Container de campos readonly com título e botão copiar opcional.
==============================================================================
Plugins USAM este widget.

Uso:
    wgs84 = GridReadOnly(
        title=STR.WGS84_EPSG4326,
        fields={
            "lat_dec": {"title": STR.LATITUDE_DECIMAL, "value": ""},
            "lon_dec": {"title": STR.LONGITUDE_DECIMAL, "value": ""},
        },
        parent=self,
    )
    layout.addWidget(wgs84)

    wgs84.set_value("lat_dec", "-10.12345678")
    wgs84.get_value("lat_dec")  # -> "-10.12345678"

Parâmetros
----------
title : str
    Título do bloco (ex: "WGS84 (EPSG:4326)").
fields : dict
    Dict de campos. Cada chave é identificador, valor é dict com:
    - "title" (str): rótulo do campo
    - "value" (str, optional): valor inicial
show_copy_buttons : bool, optional
    Se True, cada campo readonly terá um botão copiar individual.
separator_top : bool, optional
    Adiciona separador antes do widget.
separator_bottom : bool, optional
    Adiciona separador após o widget.
parent : QWidget, optional
    Widget pai.

API pública:
    set_value(key, value) -> None
    get_value(key) -> str
"""

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from ..simple.SimpleLabel import SimpleLabel
from ..simple.SimpleReadOnly import SimpleReadOnly
from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles


class GridReadOnly(QWidget):
    """
    Container com título + campos readonly.
    API pública: set_value(key, value), get_value(key).

    Separadores são controlados via parâmetros separator_top/separator_bottom.
    Plugins NUNCA importam SeparatorWidget diretamente.

    NOTA: Cada linha (label + readonly) é um QWidget container para
    garantir que a referência C++ dos widgets filhos seja mantida.
    """

    def __init__(
        self,
        title: str = "",
        fields: dict = None,
        show_copy_buttons: bool = False,
        separator_top: bool = False,
        separator_bottom: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._fields = {}
        self._title_label = None
        self._row_widgets = []  # mantém referência aos containers de linha

        try:
            self._configure(title, fields or {}, show_copy_buttons, separator_top, separator_bottom)
            self._apply_styles()
        except Exception as error:
            pass

    def _configure(self, title: str, fields: dict, show_copy_buttons: bool, separator_top: bool, separator_bottom: bool):
        """Monta UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        theme = AppStyles._get_theme()
        layout.setSpacing(theme.LAYOUT_VERTICAL_SPACING)

        if separator_top:
            layout.addWidget(SeparatorWidget())

        # ── Título ──
        if title:
            self._title_label = SimpleLabel(text=f"<b>{title}</b>", parent=self)
            layout.addWidget(self._title_label)

        # ── Campos readonly ──
        for key, cfg in fields.items():
            field_title = cfg.get("title", key)
            field_value = cfg.get("value", "")

            # Container QWidget para manter referência C++ dos filhos
            row_container = QWidget(self)
            row_layout = QHBoxLayout(row_container)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(theme.LAYOUT_HORIZONTAL_SPACING)

            label = SimpleLabel(text=f"{field_title}:", parent=row_container)
            readonly = SimpleReadOnly(text=field_value, show_copy_button=show_copy_buttons, parent=row_container)

            self._fields[key] = readonly

            row_layout.addWidget(label)
            row_layout.addWidget(readonly, stretch=1)

            self._row_widgets.append(row_container)
            layout.addWidget(row_container)

        if separator_bottom:
            layout.addWidget(SeparatorWidget())

    # ── API Pública ────────────────────────────────────────

    def set_value(self, key: str, value: str) -> None:
        """Atualiza valor de um campo pelo identificador."""
        if key in self._fields:
            field = self._fields[key]
            if field is not None:
                try:
                    field.setText(str(value))
                except RuntimeError:
                    self._fields.pop(key, None)

    def get_value(self, key: str) -> str:
        """Retorna valor de um campo pelo identificador."""
        if key in self._fields:
            field = self._fields[key]
            if field is not None:
                try:
                    return field.text()
                except RuntimeError:
                    self._fields.pop(key, None)
        return ""

    # ── Estilos ────────────────────────────────────────────

    def _apply_styles(self):
        """Aplica estilos globais."""
        combined = self._get_global_style() + self._specific_style()
        self.setStyleSheet(combined)

    def _get_global_style(self) -> str:
        return AppStyles.label() + AppStyles.input()

    def _specific_style(self) -> str:
        return ""