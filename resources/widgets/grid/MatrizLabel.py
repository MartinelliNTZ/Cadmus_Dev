# -*- coding: utf-8 -*-
"""Widget genérico para exibir uma matriz de labels sem bordas."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QGridLayout, QLabel, QWidget

from ...styles.AppStyles import AppStyles


class MatrizLabel(QWidget):
    """Renderiza dados tabulares recebidos em um dicionário.

    O widget não conhece o domínio dos dados. O consumidor informa as colunas,
    as linhas e os metadados; esta classe apenas organiza e exibe o conteúdo.

    Formato aceito por :meth:`set_data`::

        {
            "columns": ["Etapas", "Andamento", "%"],
            "metadata": {"Início": "...", "Tempo decorrido": "..."},
            "rows": {
                "download": {
                    "label": "Download",
                    "current": 2,
                    "total": 5,
                    "percent": 40,
                },
                "total": {"label": "Total", "current": 2, "total": 5},
            },
        }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = AppStyles._get_theme()
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setHorizontalSpacing(10)
        self._layout.setVerticalSpacing(4)
        self._layout.setColumnStretch(0, 1)
        self._layout.setColumnStretch(1, 0)
        self._layout.setColumnStretch(2, 0)

    def set_data(self, data: dict):
        """Substitui o conteúdo exibido pela matriz recebida."""
        if not isinstance(data, dict):
            data = {}

        self._clear()
        columns = data.get("columns") or ["Etapas", "Andamento", "%"]
        metadata = data.get("metadata") or {}
        rows = data.get("rows") or {}

        header_style = (
            f"color: {self._theme.COLOR_TEXT_SECONDARY};"
            "font-weight: bold;"
        )
        value_style = f"color: {self._theme.COLOR_TEXT_PRIMARY};"

        row_index = 0
        if metadata:
            for key, value in metadata.items():
                metadata_label = QLabel(f"{key}: {value}", self)
                metadata_label.setStyleSheet(
                    f"color: {self._theme.COLOR_TEXT_SECONDARY};"
                )
                self._layout.addWidget(metadata_label, row_index, 0, 1, 3)
                row_index += 1

        for column, title in enumerate(columns[:3]):
            header = QLabel(str(title), self)
            header.setStyleSheet(header_style)
            if column:
                header.setAlignment(Qt.AlignmentFlag.AlignRight)
            self._layout.addWidget(header, row_index, column)
        row_index += 1

        items = rows.items() if isinstance(rows, dict) else enumerate(rows)
        for key, row in items:
            row = row if isinstance(row, dict) else {"label": row}
            label = QLabel(str(row.get("label", key)), self)
            andamento = QLabel(self._format_progress(row), self)
            percent = QLabel(self._format_percent(row), self)
            andamento.setAlignment(Qt.AlignmentFlag.AlignRight)
            percent.setAlignment(Qt.AlignmentFlag.AlignRight)

            style = value_style
            if row.get("emphasis"):
                style += "font-weight: bold;"
            if row.get("status") == "failed":
                style += f"color: {self._theme.COLOR_RED};"
            label.setStyleSheet(style)
            andamento.setStyleSheet(style)
            percent.setStyleSheet(style)

            self._layout.addWidget(label, row_index, 0)
            self._layout.addWidget(andamento, row_index, 1)
            self._layout.addWidget(percent, row_index, 2)
            row_index += 1

    def _clear(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _format_progress(row: dict) -> str:
        if "value" in row:
            return str(row["value"])
        current = row.get("current", 0)
        total = row.get("total", 0)
        try:
            return f"{int(current)}/{int(total)}"
        except (TypeError, ValueError):
            return "—"

    @staticmethod
    def _format_percent(row: dict) -> str:
        percent = row.get("percent")
        if percent is None:
            return "—"
        try:
            return f"{float(percent):.0f}%"
        except (TypeError, ValueError):
            return "—"
