# -*- coding: utf-8 -*-
"""
SimpleCheckbox — QCheckBox com AppStyles.checkbox().
===================================================
Uso INTERNO por GridCheckbox. NUNCA importado por plugins.
"""

from qgis.PyQt.QtWidgets import QCheckBox
from ...styles.AppStyles import AppStyles


class SimpleCheckbox(QCheckBox):
    """
    QCheckBox com estilo global AppStyles.checkbox().

    Parâmetros
    ----------
    text : str, optional
        Texto do checkbox.
    parent : QWidget, optional
        Widget pai.

    Autoconfiguração
    ----------------
    - AppStyles.checkbox(): estilo global
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._apply_styles()

    def _apply_styles(self):
        """Aplica estilo global via AppStyles.checkbox()."""
        self.setStyleSheet(AppStyles.checkbox())