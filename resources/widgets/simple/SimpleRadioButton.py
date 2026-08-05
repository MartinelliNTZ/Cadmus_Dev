# -*- coding: utf-8 -*-
"""
SimpleRadioButton — QRadioButton com AppStyles.radio_button().
==============================================================
Uso INTERNO por GridRadioButton. NUNCA importado por plugins.
"""

from qgis.PyQt.QtWidgets import QRadioButton
from ...styles.AppStyles import AppStyles


class SimpleRadioButton(QRadioButton):
    """
    QRadioButton com estilo global AppStyles.radio_button().

    Parâmetros
    ----------
    text : str, optional
        Texto do radio button.
    parent : QWidget, optional
        Widget pai.

    Autoconfiguração
    ----------------
    - AppStyles.radio_button(): estilo global
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._apply_styles()

    def _apply_styles(self):
        """Aplica estilo global via AppStyles.radio_button()."""
        self.setStyleSheet(AppStyles.radio_button())