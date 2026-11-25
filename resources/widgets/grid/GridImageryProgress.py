# -*- coding: utf-8 -*-
"""Grade de andamento por etapa do downloader de imagens."""

from qgis.PyQt.QtWidgets import QGridLayout, QLabel, QWidget
from qgis.PyQt.QtCore import Qt

from ...styles.AppStyles import AppStyles


class GridImageryProgress(QWidget):
    """Exibe contadores ``atual/total`` e percentual por etapa."""

    STAGES = (
        "scene",
        "download",
        "clip",
        "reproject",
        "convert",
        "compose",
    )

    def __init__(self, labels=None, parent=None):
        super().__init__(parent)
        self._labels = labels or {}
        self._plan = {}
        self._values = {}
        self._stage_labels = {}
        self._value_labels = {}
        self._build_ui()

    def _build_ui(self):
        theme = AppStyles._get_theme()
        layout = QGridLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(4)

        header_stage = QLabel(self._labels.get("header_stage", "Etapa"))
        header_value = QLabel(self._labels.get("header_value", "Andamento"))
        header_style = (
            f"color: {theme.COLOR_TEXT_SECONDARY};"
            f"font-weight: bold;"
        )
        header_stage.setStyleSheet(header_style)
        header_value.setStyleSheet(header_style)
        layout.addWidget(header_stage, 0, 0)
        layout.addWidget(header_value, 0, 1)

        for row, stage in enumerate(self.STAGES, start=1):
            stage_label = QLabel(self._labels.get(stage, stage))
            value_label = QLabel("0/0")
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            stage_label.setStyleSheet(
                f"color: {theme.COLOR_TEXT_PRIMARY};"
            )
            value_label.setStyleSheet(
                f"color: {theme.COLOR_TEXT_PRIMARY};"
                f"font-weight: bold;"
            )
            layout.addWidget(stage_label, row, 0)
            layout.addWidget(value_label, row, 1)
            self._stage_labels[stage] = stage_label
            self._value_labels[stage] = value_label
            self._plan[stage] = {"total": 0, "enabled": False}
            self._values[stage] = {"current": 0, "total": 0}

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)

    def reset(self):
        """Limpa o plano e os contadores para uma nova execução."""
        for stage in self.STAGES:
            self._plan[stage] = {"total": 0, "enabled": False}
            self._values[stage] = {"current": 0, "total": 0}
            self._value_labels[stage].setText("0/0")
            self._stage_labels[stage].setVisible(False)
            self._value_labels[stage].setVisible(False)

    def set_stage_plan(self, stage: str, total: int, enabled: bool = True):
        """Define o total planejado e a visibilidade de uma etapa."""
        if stage not in self._plan:
            return
        total = max(0, int(total))
        enabled = bool(enabled and total > 0)
        self._plan[stage] = {"total": total, "enabled": enabled}
        self._values[stage] = {"current": 0, "total": total}
        self._stage_labels[stage].setVisible(enabled)
        self._value_labels[stage].setVisible(enabled)
        self._render_stage(stage)

    def update_stage(
        self,
        stage: str,
        current: int,
        total: int = None,
        status: str = "",
    ):
        """Atualiza uma etapa a partir de um evento recebido no main thread."""
        if stage not in self._values:
            return
        current = max(0, int(current))
        planned = self._plan[stage]["total"]
        effective_total = planned if planned > 0 else max(0, int(total or 0))
        if effective_total > 0:
            self._plan[stage]["enabled"] = True
            self._plan[stage]["total"] = effective_total
            self._stage_labels[stage].setVisible(True)
            self._value_labels[stage].setVisible(True)
        self._values[stage] = {
            "current": min(current, effective_total) if effective_total else current,
            "total": effective_total,
            "status": status,
        }
        self._render_stage(stage)

    def _render_stage(self, stage: str):
        value = self._values[stage]
        total = value.get("total", 0)
        current = value.get("current", 0)
        status = value.get("status", "")
        if total > 0:
            percent = min(100.0, current * 100.0 / total)
            text = f"{current}/{total} ({percent:.0f}%)"
        else:
            text = "—"
        if status == "failed":
            text += " · falha"
        self._value_labels[stage].setText(text)
