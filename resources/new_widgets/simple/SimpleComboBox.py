# -*- coding: utf-8 -*-
"""
SimpleComboBox — QComboBox com AppStyles.input().
===================================================
Uso INTERNO por GridComboBox. Plugins NUNCA importam.
"""

from qgis.PyQt.QtWidgets import QComboBox

from ....core.config.LogUtils import LogUtils
from ...styles.AppStyles import AppStyles


class SimpleComboBox(QComboBox):
    """
    QComboBox com estilo AppStyles.input().

    Uso INTERNO por GridComboBox. Plugins NUNCA importam.

    API interna:
        set_options(options_dict, allow_empty=False, empty_text="Selecionar...")
        get_selected_key()
        set_selected_key(key)
    """

    def __init__(self, parent=None, tool_key=None):
        super().__init__(parent)
        self._tool_key = tool_key or "SimpleComboBox"
        self._logger = LogUtils(tool=self._tool_key, class_name="SimpleComboBox")
        self._apply_styles()

    def set_options(self, options_dict: dict, allow_empty: bool = False, empty_text: str = "Selecionar..."):
        """Popula o combo com {key: label}. Preserva selecao atual se possivel."""
        current = self.currentData()
        self._logger.info(
            f"set_options: {len(options_dict)} itens, "
            f"allow_empty={allow_empty}, current_data='{current}'",
            code="COMBO_SET_OPTIONS",
        )
        self.blockSignals(True)
        self.clear()
        if allow_empty:
            self.addItem(str(empty_text), None)
        for key, label in options_dict.items():
            self.addItem(str(label), key)
        if current is not None:
            idx = self.findData(current)
            if idx >= 0:
                self.setCurrentIndex(idx)
            elif allow_empty:
                # Campo opcional: se selecao anterior nao existe mais, volta para vazio
                self.setCurrentIndex(0)
        self.blockSignals(False)

    def get_selected_key(self):
        """Retorna a chave (data) do item selecionado."""
        return self.currentData()

    def set_selected_key(self, key):
        """Seleciona item pela chave (data). Suporta None para item vazio."""
        if key is None:
            # Campo vazio (allow_empty=True) — seleciona o item com data None
            idx = self.findData(None)
            if idx >= 0:
                self.setCurrentIndex(idx)
                return
        idx = self.findData(key)
        self._logger.info(
            f"set_selected_key: key='{key}', "
            f"encontrado_idx={idx}, count={self.count()}",
            code="COMBO_SET_SELECTED",
        )
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self._logger.warning(
                f"set_selected_key: key='{key}' nao encontrado no combo",
                code="COMBO_KEY_NOT_FOUND",
            )

    def _apply_styles(self):
        """Aplica estilo global via AppStyles."""
        self.setStyleSheet(AppStyles.combobox())
