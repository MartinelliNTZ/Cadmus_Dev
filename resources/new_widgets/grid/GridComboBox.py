# -*- coding: utf-8 -*-
"""
GridComboBox — Container de QComboBox configurado via dict.
=============================================================
Plugins USAM este widget. NUNCA importa Simple diretamente.

UM GridComboBox contem N items (combos). Cada item:

    key (identificador unico):
        "label" (obrigatorio): texto do label
        "description" (opcional): tooltip
        "options" (obrigatorio): dict {key: label} para popular o combo
        "selected_key" (opcional): chave inicialmente selecionada
        "onchange" (opcional): callback(chave_selecionada, texto_selecionado)

Uso em plugins:
    combo = GridComboBox(
        config={
            "vector_ext": {
                "label": "Extensao Vetor:",
                "description": "Formato para vetores",
                "options": {".gpkg": "GeoPackage", ".shp": "Shapefile"},
                "selected_key": ".gpkg",
                "onchange": self.on_ext_changed,
            },
            "raster_ext": {
                "label": "Extensao Raster:",
                "options": {".tif": "TIFF", ".png": "PNG"},
                "selected_key": ".tif",
            },
        },
        title="Extensoes",
        parent=self,
    )
    layout.addWidget(combo)

    combo.get_selected_key("vector_ext")    # → ".gpkg"
    combo.set_selected_key("vector_ext", ".shp")
    combo.widget("vector_ext")              # → SimpleComboBox
"""

from typing import Optional, Callable

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
)

from ..simple.SimpleComboBox import SimpleComboBox
from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles


class GridComboBox(QWidget):
    """
    Container de N combos (QComboBox) configurado via dict.

    Parâmetros
    ----------
    config : dict, optional
        Dict de combos. Chave = identificador.
        Valor = dict com:
            - "label" (obrigatorio): texto do label
            - "description" (opcional): tooltip
            - "options" (obrigatorio): dict {key: label} para popular o combo
            - "selected_key" (opcional): chave inicialmente selecionada
            - "onchange" (opcional): callback(chave_selecionada, texto_selecionado)
    title : str or None, optional
        Titulo do grupo (QGroupBox). None = sem grupo.
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
        title: Optional[str] = None,
        separator_top: bool = False,
        separator_bottom: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._config = config or {}
        self._title = title
        self._separator_top = separator_top
        self._separator_bottom = separator_bottom

        # Mapa interno: key -> SimpleComboBox
        self._combos: dict[str, SimpleComboBox] = {}

        self._build_ui()

    # -- API publica -------------------------------------------------

    def get_selected_key(self, key: str) -> Optional[str]:
        """Retorna a chave selecionada do combo."""
        combo = self._combos.get(key)
        return combo.get_selected_key() if combo else None

    def set_selected_key(self, key: str, value: str):
        """Seleciona item do combo pela chave (data)."""
        combo = self._combos.get(key)
        if combo:
            combo.set_selected_key(value)

    def get_options(self, key: str) -> Optional[dict]:
        """Retorna as options atuais do combo (aproximado pelo data dos itens)."""
        combo = self._combos.get(key)
        if not combo:
            return None
        options = {}
        for i in range(combo.count()):
            data = combo.itemData(i)
            text = combo.itemText(i)
            if data is not None:
                options[data] = text
        return options

    def set_options(self, key: str, options: dict):
        """Substitui as options de um combo."""
        combo = self._combos.get(key)
        if combo:
            combo.set_options(options)

    def widget(self, key: str) -> Optional[SimpleComboBox]:
        """Acesso direto ao SimpleComboBox."""
        return self._combos.get(key)

    # -- Build -------------------------------------------------------

    def _build_ui(self):
        """Monta layout com N combos: label + combo na mesma linha."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        theme = AppStyles._get_theme()

        if self._separator_top:
            outer_layout.addWidget(SeparatorWidget())

        # Pequeno espaco apos o separador superior
        if self._separator_top:
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

        # Cria combos (label + combo na mesma linha)
        for key, item_config in self._config.items():
            label_text = item_config.get("label", key)
            description = item_config.get("description", "")
            options = item_config.get("options", {})
            selected_key = item_config.get("selected_key")
            onchange = item_config.get("onchange")

            # Linha horizontal: label + combo
            row_layout = QHBoxLayout()
            row_layout.setSpacing(theme.LAYOUT_HORIZONTAL_SPACING)
            row_layout.setContentsMargins(0, 0, 0, 0)

            # Label opcional: so adiciona se "label" foi explicitamente passado
            has_label = "label" in item_config
            if has_label:
                lbl = QLabel(label_text)
                lbl.setMinimumWidth(theme.LABEL_FIELD_MIN_WIDTH)
                lbl.setWordWrap(False)
                if description:
                    lbl.setToolTip(description)

            # Combo estilizado
            combo = SimpleComboBox(parent=self)
            combo.set_options(options)
            if selected_key is not None:
                combo.set_selected_key(selected_key)
            if description:
                combo.setToolTip(description)

            # Conecta onchange callback
            if onchange:
                combo.currentIndexChanged.connect(
                    lambda _idx, k=key, c=combo: self._fire_onchange(k, c, onchange)
                )

            if has_label:
                row_layout.addWidget(lbl)
            row_layout.addWidget(combo, 1)

            self._combos[key] = combo
            container_layout.addLayout(row_layout)

        outer_layout.addWidget(container)

        if self._separator_bottom:
            outer_layout.addSpacing(theme.LAYOUT_VERTICAL_SPACING)
            outer_layout.addWidget(SeparatorWidget())

    # -- Interno -----------------------------------------------------

    @staticmethod
    def _fire_onchange(key: str, combo: SimpleComboBox, callback: Callable):
        """Dispara o callback com (chave_selecionada, texto_selecionado)."""
        selected_key = combo.get_selected_key()
        selected_text = combo.currentText()
        callback(selected_key, selected_text)