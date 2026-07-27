# -*- coding: utf-8 -*-
"""
SimpleComboBox — QComboBox com AppStyles.input().
===================================================
Uso INTERNO por GridComboBox. Plugins NUNCA importam.
"""

from qgis.PyQt.QtWidgets import QComboBox
from ...styles.AppStyles import AppStyles


class SimpleComboBox(QComboBox):
    """
    QComboBox com estilo AppStyles.input().

    Uso INTERNO por GridComboBox. Plugins NUNCA importam.

    API interna:
        set_options(options_dict)
        get_selected_key()
        set_selected_key(key)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_styles()

    def set_options(self, options_dict: dict):
        """Popula o combo com {key: label}. Preserva selecao atual se possivel."""
        current = self.currentData()
        self.blockSignals(True)
        self.clear()
        for key, label in options_dict.items():
            self.addItem(str(label), key)
        if current is not None:
            idx = self.findData(current)
            if idx >= 0:
                self.setCurrentIndex(idx)
        self.blockSignals(False)

    def get_selected_key(self):
        """Retorna a chave (data) do item selecionado."""
        return self.currentData()

    def set_selected_key(self, key):
        """Seleciona item pela chave (data)."""
        idx = self.findData(key)
        if idx >= 0:
            self.setCurrentIndex(idx)

    def _apply_styles(self):
        """Aplica estilo global via AppStyles."""
        self.setStyleSheet(AppStyles.input())