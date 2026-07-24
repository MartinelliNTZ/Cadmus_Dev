# -*- coding: utf-8 -*-
"""
GridCheckbox — Container de checkboxes configurável via dict.
=============================================================
Plugins USAM este widget. NUNCA importa Simple diretamente.

Cada item do config dict:
    key (identificador único):
        "label" (obrigatório): texto do checkbox
        "description" (opcional): tooltip do checkbox
        "default" (opcional): bool, estado inicial
        "onchange" (opcional): callback(checked_state)

Uso em plugins:
    checkbox_widget = GridCheckbox(
        config={
            "export_pdf": {
                "label": "Exportar PDF",
                "description": "Exporta layouts em PDF",
                "default": True,
            },
            "export_png": {
                "label": "Exportar PNG",
                "default": False,
            },
        },
        title="Opções de Exportação",
        items_per_row=2,
        parent=self,
    )
    self.layout.addWidget(checkbox_widget)
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QGroupBox,
)
from qgis.PyQt.QtCore import Qt

from ..simple.SimpleCheckbox import SimpleCheckbox
from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles


class GridCheckbox(QWidget):
    """
    Container de checkboxes configurável via dict.

    Parâmetros
    ----------
    config : dict, optional
        Dict de checkboxes. Chave = identificador.
        Valor = dict com:
            - "label" (obrigatório): texto do checkbox
            - "description" (opcional): tooltip
            - "default" (opcional): bool, estado inicial
            - "onchange" (opcional): callback(checked_state)
    title : str, optional
        Título do grupo (QGroupBox).
    items_per_row : int, optional
        Itens por linha no grid (default 2).
    separator_top : bool, optional
        Separador acima.
    separator_bottom : bool, optional
        Separador abaixo.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        config: dict = None,
        title: str = "",
        items_per_row: int = 2,
        separator_top: bool = False,
        separator_bottom: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._config = config or {}
        self._title = title
        self._items_per_row = max(1, items_per_row)
        self._separator_top = separator_top
        self._separator_bottom = separator_bottom

        # Mapa interno: key -> SimpleCheckbox
        self._checkboxes: dict[str, SimpleCheckbox] = {}

        self._build_ui()

    # -- API publica -------------------------------------------------

    def is_checked(self, key: str) -> bool:
        """Retorna estado do checkbox."""
        cb = self._checkboxes.get(key)
        return cb.isChecked() if cb else False

    def set_checked(self, key: str, value: bool):
        """Define estado do checkbox."""
        cb = self._checkboxes.get(key)
        if cb:
            cb.setChecked(value)

    def get_all_states(self) -> dict[str, bool]:
        """Retorna todos os estados como dict {key: bool}."""
        return {key: cb.isChecked() for key, cb in self._checkboxes.items()}

    def widget(self, key: str):
        """Acesso direto ao QCheckBox (para signals como toggled)."""
        return self._checkboxes.get(key)

    # -- Build -------------------------------------------------------

    def _build_ui(self):
        """Monta layout com checkboxes em grid."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        if self._separator_top:
            outer_layout.addWidget(SeparatorWidget())

        theme = AppStyles._get_theme()

        # Container com titulo opcional
        if self._title:
            container = QGroupBox(self._title)

            # Estilo condicional do titulo: fundo transparente se ENABLE_GRID_CHECKBOX_BACKGROUND=False
            if not theme.ENABLE_GRID_CHECKBOX_BACKGROUND:
                container.setStyleSheet(
                    "QGroupBox {"
                    f"    background: transparent;"
                    f"    border: none;"
                    f"    margin-top: 16px;"
                    f"    font-weight: bold;"
                    f"    font-size: {theme.FONT_SIZE_SECTION_TITLE};"
                    f"    color: {theme.COLOR_TEXT_PRIMARY};"
                    f"    text-align: center;"
                    f"    padding: 0px;"
                    f"}}"
                    f"QGroupBox::title {{"
                    f"    subcontrol-origin: margin;"
                    f"    subcontrol-position: top center;"
                    f"    padding: 0 8px;"
                    f"}}"
                )

            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(6, 6, 6, 6)
            container_layout.setSpacing(theme.LAYOUT_VERTICAL_SPACING)
        else:
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(theme.LAYOUT_VERTICAL_SPACING)

        # Grid de checkboxes
        grid_layout = QGridLayout()
        grid_layout.setSpacing(6)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        items = list(self._config.items())
        for index, (key, item_config) in enumerate(items):
            label = item_config.get("label", key)
            description = item_config.get("description", "")
            default = item_config.get("default", False)
            onchange = item_config.get("onchange")

            cb = SimpleCheckbox(text=label, parent=self)
            cb.setChecked(bool(default))

            if description:
                cb.setToolTip(description)

            if onchange:
                cb.toggled.connect(onchange)

            self._checkboxes[key] = cb

            row = index // self._items_per_row
            col = index % self._items_per_row
            grid_layout.addWidget(cb, row, col)

        # Adiciona stretch na ultima linha para alinhar ao topo
        if items:
            last_row = (len(items) - 1) // self._items_per_row
            grid_layout.setRowStretch(last_row, 0)
            grid_layout.setRowStretch(last_row + 1, 1)

        container_layout.addLayout(grid_layout)
        outer_layout.addWidget(container)

        if self._separator_bottom:
            outer_layout.addWidget(SeparatorWidget())