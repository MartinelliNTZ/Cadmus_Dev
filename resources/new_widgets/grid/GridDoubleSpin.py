# -*- coding: utf-8 -*-
"""
GridDoubleSpin — Container de campos numéricos configurável via dict.
====================================================================
Plugins USAM este widget. NUNCA importa Simple diretamente.

Cada item do config dict:
    key (identificador único):
        "label" (obrigatório): texto do label
        "description" (opcional): tooltip do label
        "value" (opcional): valor inicial
        "min" (opcional): valor mínimo
        "max" (opcional): valor máximo
        "step" (opcional): incremento
        "decimals" (opcional): casas decimais
        "type" (opcional): "int" ou "double"
        "onchange" (opcional): callback(value)

Uso em plugins:
    spin = GridDoubleSpin(
        config={
            "max_width": {
                "label": "Largura Máx. PNG",
                "description": "Largura máxima em pixels",
                "value": 3500,
                "min": 100,
                "max": 10000,
                "step": 100,
                "decimals": 0,
                "type": "int",
            },
        },
        title="Configurações",
        parent=self,
    )
    self.layout.addWidget(spin)
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
)
from qgis.PyQt.QtCore import Qt

from ..simple.SimpleLabel import SimpleLabel
from ..simple.SimpleDoubleSpinBox import SimpleDoubleSpinBox
from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles


class GridDoubleSpin(QWidget):
    """
    Container de campos numéricos configurável via dict.

    Parâmetros
    ----------
    config : dict, optional
        Dict de campos. Chave = identificador.
        Valor = dict com:
            - "label" (obrigatório): texto do label
            - "description" (opcional): tooltip
            - "value" (opcional): valor inicial
            - "min" (opcional): valor mínimo
            - "max" (opcional): valor máximo
            - "step" (opcional): incremento
            - "decimals" (opcional): casas decimais
            - "type" (opcional): "int" ou "double"
            - "onchange" (opcional): callback(value)
    title : str, optional
        Título do grupo (QGroupBox).
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
        title: str = "",
        separator_top: bool = False,
        separator_bottom: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._config = config or {}
        self._title = title
        self._separator_top = separator_top
        self._separator_bottom = separator_bottom

        # Mapa interno: key → SimpleDoubleSpinBox
        self._spins: dict[str, SimpleDoubleSpinBox] = {}

        self._build_ui()

    # ── API pública ────────────────────────────────────────────

    def get_value(self, key: str):
        """Retorna valor atual do campo."""
        spin = self._spins.get(key)
        return spin.value() if spin else 0

    def set_value(self, key: str, value):
        """Define valor do campo."""
        spin = self._spins.get(key)
        if spin:
            spin.setValue(value)

    def get_all_values(self) -> dict:
        """Retorna todos os valores como dict {key: value}."""
        return {key: spin.value() for key, spin in self._spins.items()}

    # ── Build ──────────────────────────────────────────────────

    def _build_ui(self):
        """Monta layout com campos numéricos."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        if self._separator_top:
            outer_layout.addWidget(SeparatorWidget())

        # Container com título opcional
        if self._title:
            container = QGroupBox(self._title)
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(6, 6, 6, 6)
            container_layout.setSpacing(
                AppStyles._get_theme().LAYOUT_VERTICAL_SPACING
            )
        else:
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(
                AppStyles._get_theme().LAYOUT_VERTICAL_SPACING
            )

        # Cada campo: label + spin em linha
        for key, field_config in self._config.items():
            label_text = field_config.get("label", key)
            description = field_config.get("description", "")
            value = field_config.get("value", 0)
            min_val = field_config.get("min", 0)
            max_val = field_config.get("max", 999999)
            step = field_config.get("step", 1)
            decimals = field_config.get("decimals", 0)
            type_spec = field_config.get("type", "double")
            onchange = field_config.get("onchange")

            # Layout horizontal: SimpleLabel + SimpleDoubleSpinBox
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            label_widget = SimpleLabel(text=label_text, parent=self)
            if description:
                label_widget.setToolTip(description)
            row_layout.addWidget(label_widget)

            spin = SimpleDoubleSpinBox(
                value=value,
                min_val=min_val,
                max_val=max_val,
                step=step,
                decimals=decimals,
                type_spec=type_spec,
                parent=self,
            )
            if onchange:
                spin.valueChanged.connect(onchange)

            self._spins[key] = spin
            row_layout.addWidget(spin)

            container_layout.addLayout(row_layout)

        outer_layout.addWidget(container)

        if self._separator_bottom:
            outer_layout.addWidget(SeparatorWidget())