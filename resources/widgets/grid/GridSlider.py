# -*- coding: utf-8 -*-
"""
GridSlider — Container de N sliders configurável via dict.
============================================================
Plugins USAM este widget. NUNCA importa Simple diretamente.

Cada item do config dict:
    key (identificador único):
        "label" (obrigatório): texto do label
        "description" (opcional): tooltip
        "value" (opcional): valor inicial
        "min" (opcional): valor mínimo
        "max" (opcional): valor máximo
        "suffix" (opcional): sufixo do valor (ex: "%")
        "onchange" (opcional): callback(value)

Uso em plugins:
    cloud = GridSlider(
        config={
            "max_cloud": {
                "label": STR.CLOUD_MAX,
                "value": 50,
                "min": 0,
                "max": 100,
                "suffix": "%",
                "onchange": self.on_cloud_changed,
            },
        },
        parent=self,
    )
    self.layout.addWidget(cloud)

    cloud.get_value("max_cloud")     # → 50
    cloud.set_value("max_cloud", 80)
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
)

from ..simple.SimpleLabel import SimpleLabel
from ..simple.SimpleSlider import SimpleSlider
from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles


class GridSlider(QWidget):
    """Container de N sliders configurável via dict (padrão GridDoubleSpin)."""

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

        self._sliders: dict[str, SimpleSlider] = {}

        self._build_ui()

    # ── API pública ────────────────────────────────────────────

    def get_value(self, key: str) -> int:
        """Retorna valor atual do slider."""
        slider = self._sliders.get(key)
        return slider.value() if slider else 0

    def set_value(self, key: str, value: int):
        """Define valor do slider."""
        slider = self._sliders.get(key)
        if slider:
            slider.set_value(value)

    def get_all_values(self) -> dict:
        """Retorna todos os valores como dict {key: int}."""
        return {key: slider.value() for key, slider in self._sliders.items()}

    def set_values(self, values: dict):
        """Define múltiplos valores via dict."""
        for key, value in (values or {}).items():
            self.set_value(key, value)

    # ── Build ──────────────────────────────────────────────────

    def _build_ui(self):
        """Monta layout com labels + SimpleSlider por linha."""
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
            value = item_config.get("value", 50)
            min_val = item_config.get("min", 0)
            max_val = item_config.get("max", 100)
            suffix = item_config.get("suffix", "")
            onchange = item_config.get("onchange")

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)

            label = SimpleLabel(text=label_text, parent=self)
            if description:
                label.setToolTip(description)
            label.setMinimumWidth(
                AppStyles._get_theme().LABEL_FIELD_MIN_WIDTH
            )
            row.addWidget(label)

            slider = SimpleSlider(
                min_val=min_val,
                max_val=max_val,
                value=value,
                suffix=suffix,
                parent=self,
            )
            if description:
                slider.setToolTip(description)
            if onchange:
                slider._slider.valueChanged.connect(onchange)
            self._sliders[key] = slider
            row.addWidget(slider, 1)

            container_layout.addLayout(row)

        outer.addWidget(container)

        if self._separator_bottom:
            outer.addWidget(SeparatorWidget())