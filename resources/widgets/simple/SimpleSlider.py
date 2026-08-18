# -*- coding: utf-8 -*-
"""
SimpleSlider — QSlider horizontal com label de valor.
======================================================
Uso INTERNO por GridSlider. NUNCA importado por plugins.
"""

from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QSlider
from qgis.PyQt.QtCore import Qt

from .SimpleLabel import SimpleLabel
from ...styles.AppStyles import AppStyles
from ....utils.qt_compat import resolve_qt_enum


class SimpleSlider(QWidget):
    """QSlider horizontal com SimpleLabel exibindo o valor.

    Parâmetros
    ----------
    min_val : int
        Valor mínimo.
    max_val : int
        Valor máximo.
    value : int
        Valor inicial.
    suffix : str
        Sufixo exibido ao lado do valor (ex: "%").
    parent : QWidget, optional
        Widget pai.

    Autoconfiguração
    ----------------
    - AppStyles.input(): estilo global (sliders e label)
    """

    def __init__(
        self,
        min_val: int = 0,
        max_val: int = 100,
        value: int = 50,
        suffix: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._suffix = str(suffix)
        self.setMinimumWidth(220)

        self._slider = QSlider(
            resolve_qt_enum(Qt, "Horizontal", "Orientation", "Horizontal"),
            self,
        )
        self._slider.setRange(int(min_val), int(max_val))
        self._slider.setValue(int(value))
        self._slider.setSingleStep(1)

        self._label = SimpleLabel(
            f"{int(value)}{self._suffix}", parent=self
        )
        self._label.setMinimumWidth(48)
        self._label.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._slider, 1)
        layout.addWidget(self._label)

        self._slider.valueChanged.connect(self._on_value_changed)
        self._apply_styles()

    def _on_value_changed(self, value: int):
        """Atualiza o label quando o valor muda."""
        self._label.setText(f"{value}{self._suffix}")

    def value(self) -> int:
        """Retorna o valor atual do slider."""
        return self._slider.value()

    def set_value(self, value: int):
        """Define o valor do slider."""
        self._slider.setValue(int(value))

    def _apply_styles(self):
        """Aplica estilos globais."""
        self.setStyleSheet(AppStyles.input())