# -*- coding: utf-8 -*-
"""
GridRadioButton — Container de radio buttons configurável via dict.
==================================================================
Plugins USAM este widget. NUNCA importa Simple diretamente.

Cada item do config dict:
    key (identificador único):
        "label" (obrigatório): texto do radio button
        "description" (opcional): tooltip
        "onchange" (opcional): callback(chave_selecionada)

Uso em plugins:
    mode_selector = GridRadioButton(
        config={
            "remove": {
                "label": "Remover Extensão",
                "description": "Remove a extensão dos arquivos",
            },
            "restore": {
                "label": "Restaurar Extensão",
            },
            "zip": {
                "label": "Zipar",
            },
            "unzip": {
                "label": "Deszipar",
            },
        },
        columns=2,
        default_key="remove",
        separator_bottom=True,
        parent=self,
    )
    self.layout.addWidget(mode_selector)

    mode_selector.get_selected_key()    # → "remove"
    mode_selector.set_selected_key("zip")
    mode_selector.get_selected_index()  # → 2
"""

from typing import Optional

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QButtonGroup,
)
from qgis.PyQt.QtCore import Qt

from ..simple.SimpleRadioButton import SimpleRadioButton
from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles


class GridRadioButton(QWidget):
    """
    Container de radio buttons configurável via dict.

    Parâmetros
    ----------
    config : dict, optional
        Dict de radio buttons. Chave = identificador.
        Valor = dict com:
            - "label" (obrigatório): texto do radio button
            - "description" (opcional): tooltip
            - "onchange" (opcional): callback(chave_selecionada)
    columns : int, optional
        Número de colunas no grid (default 1).
    default_key : str, optional
        Chave do item selecionado por padrão (None = nenhum).
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
        columns: int = 1,
        default_key: Optional[str] = None,
        separator_top: bool = False,
        separator_bottom: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._config = config or {}
        self._columns = max(1, columns)
        self._default_key = default_key
        self._separator_top = separator_top
        self._separator_bottom = separator_bottom

        # Mapa interno: key -> SimpleRadioButton
        self._radios: dict[str, SimpleRadioButton] = {}
        # Lista ordenada de chaves para suporte a índice
        self._keys_order: list[str] = []

        # ButtonGroup para exclusividade
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self._build_ui()

    # -- API publica -------------------------------------------------

    def get_selected_key(self) -> Optional[str]:
        """Retorna a chave do radio button selecionado."""
        checked = self._button_group.checkedButton()
        if checked is None:
            return None
        # Busca a chave pelo objeto radio
        for key, radio in self._radios.items():
            if radio is checked:
                return key
        return None

    def set_selected_key(self, key: str):
        """Seleciona o radio button pela chave."""
        radio = self._radios.get(key)
        if radio:
            radio.setChecked(True)

    def get_selected_index(self) -> int:
        """Retorna o índice do radio button selecionado (0-based)."""
        key = self.get_selected_key()
        if key is None:
            return -1
        try:
            return self._keys_order.index(key)
        except ValueError:
            return -1

    def set_selected_index(self, index: int):
        """Seleciona o radio button pelo índice (0-based)."""
        if 0 <= index < len(self._keys_order):
            key = self._keys_order[index]
            self.set_selected_key(key)

    # -- Build -------------------------------------------------------

    def _build_ui(self):
        """Monta layout com radio buttons em grid."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        theme = AppStyles._get_theme()

        if self._separator_top:
            outer_layout.addWidget(SeparatorWidget())

        # Container interno
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(theme.LAYOUT_VERTICAL_SPACING)

        # Grid de radio buttons
        grid_layout = QGridLayout()
        grid_layout.setSpacing(6)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        items = list(self._config.items())
        self._keys_order = [key for key, _ in items]

        for index, (key, item_config) in enumerate(items):
            label = item_config.get("label", key)
            description = item_config.get("description", "")
            onchange = item_config.get("onchange")

            radio = SimpleRadioButton(text=label, parent=self)
            if description:
                radio.setToolTip(description)

            # Conecta callback
            if onchange:
                radio.toggled.connect(
                    lambda checked, k=key, cb=onchange: self._fire_onchange(
                        checked, k, cb
                    )
                )

            # Adiciona ao ButtonGroup
            self._button_group.addButton(radio)

            self._radios[key] = radio

            row = index // self._columns
            col = index % self._columns
            grid_layout.addWidget(radio, row, col)

        # Aplica default_key
        if self._default_key and self._default_key in self._radios:
            self._radios[self._default_key].setChecked(True)

        # Adiciona stretch na ultima linha para alinhar ao topo
        if items:
            last_row = (len(items) - 1) // self._columns
            grid_layout.setRowStretch(last_row, 0)
            grid_layout.setRowStretch(last_row + 1, 1)

        container_layout.addLayout(grid_layout)
        outer_layout.addWidget(container)

        if self._separator_bottom:
            outer_layout.addWidget(SeparatorWidget())

    # -- Interno -----------------------------------------------------

    @staticmethod
    def _fire_onchange(checked: bool, key: str, callback):
        """Dispara o callback com a chave selecionada (só quando checked=True)."""
        if checked:
            callback(key)