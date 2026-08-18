# -*- coding: utf-8 -*-
"""
GridDateSelector — Container de N datas configurável via dict.
========================================================================
Plugins USAM este widget. NUNCA importa Simple diretamente.

Cada item do config dict:
    key (identificador único):
        "label" (obrigatório): texto do label
        "description" (opcional): tooltip
        "date" (opcional): data inicial "yyyy-MM-dd"

Uso em plugins:
    dates = GridDateSelector(
        config={
            "start": {"label": STR.START_DATE, "date": "2026-01-01"},
            "end":   {"label": STR.END_DATE,   "date": "2026-12-31"},
        },
        title=STR.DATE_PERIOD,
        parent=self,
    )
    self.layout.addWidget(dates)

    dates.get_date("start")     # → QDate
    dates.set_date("start", q)
    dates.get_date_str("start") # → "yyyy-MM-dd"
    dates.get_dates()           # → {"start": QDate, "end": QDate}
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
)
from qgis.PyQt.QtCore import QDate
from qgis.PyQt.QtWidgets import QLabel

from ..simple.SimpleLabel import SimpleLabel
from ..simple.SimpleDateEdit import SimpleDateEdit
from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles


class GridDateSelector(QWidget):
    """Container de datas configurável via dict (padrão grid do novo sistema).

    Parâmetros
    ----------
    config : dict, optional
        Dict de datas. Chave = identificador.
        Valor = dict com "label" (obrigatório), "description" (opcional),
        "date" (opcional, "yyyy-MM-dd").
    title : str, optional
        Título do grupo (QGroupBox).
    separator_top / separator_bottom : bool, optional
        Separadores.
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

        self._edits: dict[str, SimpleDateEdit] = {}
        self._labels: dict[str, QLabel] = {}

        self._build_ui()

    # ── API pública ────────────────────────────────────────────

    def get_date(self, key: str) -> QDate:
        """Retorna QDate de um campo (inválido se ausente)."""
        edit = self._edits.get(key)
        return edit.date() if edit else QDate()

    def get_date_str(self, key: str, fmt: str = "yyyy-MM-dd") -> str:
        """Retorna a data de um campo como string formatada."""
        qd = self.get_date(key)
        return qd.toString(fmt) if qd.isValid() else ""

    def set_date(self, key: str, date):
        """Define a data de um campo (aceita QDate ou string "yyyy-MM-dd")."""
        edit = self._edits.get(key)
        if not edit:
            return
        if isinstance(date, QDate):
            edit.setDate(date)
            return
        if isinstance(date, str):
            qd = QDate.fromString(date, "yyyy-MM-dd")
            if qd.isValid():
                edit.setDate(qd)

    def get_dates(self) -> dict:
        """Retorna dict {key: QDate} de todos os campos."""
        return {key: edit.date() for key, edit in self._edits.items()}

    def get_dates_str(self, fmt: str = "yyyy-MM-dd") -> dict:
        """Retorna dict {key: str} de todos os campos."""
        result = {}
        for key, edit in self._edits.items():
            result[key] = edit.date().toString(fmt)
        return result

    def set_dates(self, dates: dict):
        """Define múltiplas datas via dict {key: QDate|str}."""
        for key, value in (dates or {}).items():
            self.set_date(key, value)

    # ── Build ──────────────────────────────────────────────────

    def _build_ui(self):
        """Monta layout com labels + SimpleDateEdit por linha."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        if self._separator_top:
            outer.addWidget(SeparatorWidget())

        if self._title:
            container = QGroupBox(self._title)
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(
                AppStyles._get_theme().CONTAINER_MARGIN_LEFT,
                AppStyles._get_theme().CONTAINER_MARGIN_TOP,
                AppStyles._get_theme().CONTAINER_MARGIN_RIGHT,
                AppStyles._get_theme().CONTAINER_MARGIN_BOTTOM,
            )
        else:
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(
            AppStyles._get_theme().LAYOUT_VERTICAL_SPACING
        )

        for key, item_config in self._config.items():
            label_text = item_config.get("label", key)
            description = item_config.get("description", "")
            date_val = item_config.get("date", "")

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)

            label = SimpleLabel(text=label_text, parent=self)
            if description:
                label.setToolTip(description)
            label.setMinimumWidth(
                AppStyles._get_theme().LABEL_FIELD_MIN_WIDTH
            )
            self._labels[key] = label
            row.addWidget(label)

            edit = SimpleDateEdit(date_str=date_val, parent=self)
            if description:
                edit.setToolTip(description)
            self._edits[key] = edit
            row.addWidget(edit, 1)

            container_layout.addLayout(row)

        outer.addWidget(container)

        if self._separator_bottom:
            outer.addWidget(SeparatorWidget())