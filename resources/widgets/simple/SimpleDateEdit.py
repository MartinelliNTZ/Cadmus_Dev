# -*- coding: utf-8 -*-
"""
SimpleDateEdit — QDateEdit com AppStyles.input() e calendário popup.
====================================================================
Uso INTERNO por GridDateSelector. NUNCA importado por plugins.
"""

from qgis.PyQt.QtWidgets import QDateEdit
from qgis.PyQt.QtCore import QDate, Qt

from ...styles.AppStyles import AppStyles


class SimpleDateEdit(QDateEdit):
    """QDateEdit com estilo global AppStyles.input() e calendário popup.

    Parâmetros
    ----------
    date_str : str, optional
        Data inicial no formato ``yyyy-MM-dd`` (se válida).
    parent : QWidget, optional
        Widget pai.

    Autoconfiguração
    ----------------
    - Display format ``yyyy-MM-dd``
    - CalendarPopup habilitado
    - AppStyles.input(): estilo global
    """

    def __init__(self, date_str: str = "", parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("yyyy-MM-dd")

        try:
            self.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        except AttributeError:  # Qt5
            self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        if date_str:
            qdate = QDate.fromString(date_str, "yyyy-MM-dd")
            if qdate.isValid():
                self.setDate(qdate)

        self._apply_styles()

    def _apply_styles(self):
        """Aplica estilo global via AppStyles.input()."""
        self.setStyleSheet(AppStyles.input())