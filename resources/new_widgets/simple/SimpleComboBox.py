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
        set_options(options_dict)
        get_selected_key()
        set_selected_key(key)
    """

    def __init__(self, parent=None, tool_key=None):
        super().__init__(parent)
        self._tool_key = tool_key or "SimpleComboBox"
        self._logger = LogUtils(tool=self._tool_key, class_name="SimpleComboBox")
        self._apply_styles()

    def set_options(self, options_dict: dict):
        """Popula o combo com {key: label}. Preserva selecao atual se possivel."""
        current = self.currentData()
        item_count = len(options_dict)
        self._logger.info(
            f"set_options: {item_count} itens, "
            f"current_data='{current}', "
            f"keys={list(options_dict.keys())[:5]}..."
            f"{' (+' + str(item_count - 5) + ' mais)' if item_count > 5 else ''}",
            code="COMBO_SET_OPTIONS",
        )
        self.blockSignals(True)
        self.clear()
        for key, label in options_dict.items():
            self.addItem(str(label), key)
        self._logger.debug(
            f"set_options: apos clear+addItem, "
            f"count={self.count()}, "
            f"currentIndex={self.currentIndex()}, "
            f"currentData={self.currentData()}",
            code="COMBO_AFTER_ADD",
        )
        if current is not None:
            idx = self.findData(current)
            if idx >= 0:
                self.setCurrentIndex(idx)
                self._logger.debug(
                    f"set_options: restaurado currentIndex={idx}",
                    code="COMBO_RESTORE_INDEX",
                )
        else:
            self._logger.debug(
                "set_options: current=None, sem restauracao de indice",
                code="COMBO_NO_RESTORE",
            )
        self.blockSignals(False)
        self._logger.debug(
            f"set_options: final count={self.count()}, "
            f"currentIndex={self.currentIndex()}",
            code="COMBO_FINAL",
        )

    def get_selected_key(self):
        """Retorna a chave (data) do item selecionado."""
        return self.currentData()

    def set_selected_key(self, key):
        """Seleciona item pela chave (data)."""
        idx = self.findData(key)
        self._logger.info(
            f"set_selected_key: key='{key}', "
            f"encontrado_idx={idx}, "
            f"count={self.count()}",
            code="COMBO_SET_SELECTED",
        )
        if idx >= 0:
            self.setCurrentIndex(idx)
            self._logger.debug(
                f"set_selected_key: currentIndex={self.currentIndex()}, "
                f"currentData={self.currentData()}",
                code="COMBO_SET_SELECTED_DONE",
            )
        else:
            self._logger.warning(
                f"set_selected_key: key='{key}' nao encontrado no combo",
                code="COMBO_KEY_NOT_FOUND",
            )

    def _apply_styles(self):
        """Aplica estilo global via AppStyles."""
        self.setStyleSheet(AppStyles.input())