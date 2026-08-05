# -*- coding: utf-8 -*-
"""
SimpleDoubleSpinBox — QDoubleSpinBox/QSpinBox com AppStyles.input().
====================================================================
Uso INTERNO por GridDoubleSpin. NUNCA importado por plugins.

Suporta type="int" (QSpinBox) e type="double" (QDoubleSpinBox).
"""

from qgis.PyQt.QtWidgets import QDoubleSpinBox, QSpinBox
from ...styles.AppStyles import AppStyles


class SimpleDoubleSpinBox(QDoubleSpinBox):
    """
    QDoubleSpinBox com estilo global AppStyles.input().

    Se type_spec="int", usa QSpinBox em vez de QDoubleSpinBox
    (decimals=0, sem casas decimais).

    Parâmetros
    ----------
    value : int/float, optional
        Valor inicial (default 0).
    min_val : int/float, optional
        Valor mínimo (default 0).
    max_val : int/float, optional
        Valor máximo (default 999999).
    step : int/float, optional
        Incremento do spin (default 1).
    decimals : int, optional
        Casas decimais (default 0). Ignorado se type_spec="int".
    type_spec : str, optional
        "double" (QDoubleSpinBox) ou "int" (QSpinBox).
    parent : QWidget, optional
        Widget pai.

    Autoconfiguração
    ----------------
    - AppStyles.input(): estilo global
    """

    def __init__(
        self,
        value=0,
        min_val=0,
        max_val=999999,
        step=1,
        decimals=0,
        type_spec: str = "double",
        parent=None,
    ):
        # Se type="int", usa QSpinBox como base
        if type_spec == "int":
            self._use_spinbox = True
            super().__init__(parent)
            # Converte para int
            self.setDecimals(0)
            self.setRange(int(min_val), int(max_val))
            self.setSingleStep(int(step))
            self.setValue(int(value))
        else:
            self._use_spinbox = False
            super().__init__(parent)
            self.setRange(min_val, max_val)
            self.setSingleStep(step)
            self.setDecimals(decimals)
            self.setValue(value)

        self._apply_styles()

    def _apply_styles(self):
        """Aplica estilo global via AppStyles.input()."""
        self.setStyleSheet(AppStyles.input())