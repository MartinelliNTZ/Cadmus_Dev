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
        "dependents" (opcional): list[str] — chaves que dependem deste checkbox
            Ex: "preserve": {"dependents": ["lastfolder"]}
            Quando preserve for desmarcado, lastfolder é desmarcado e desabilitado.
            Quando preserve for marcado, lastfolder é reabilitado com estado anterior.

Parâmetro opcional:
    control_buttons_config (dict, opcional):
        Dict de botões de controle (Selecionar/Desmarcar/Inverter).
        Cria GridModernButtons internamente.
        Ex: {"select_all": {"label": "Selecionar Todos", "callback": ...}, ...}

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
from .GridModernButtons import GridModernButtons
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
            - "dependents" (opcional): list[str] — chaves dependentes
    title : str, optional
        Título do grupo (QGroupBox).
    items_per_row : int, optional
        Itens por linha no grid (default 2).
    control_buttons_config : dict, optional
        Se fornecido, cria botões de controle (GridModernButtons).
        Dict no formato {key: {"label": ..., "callback": ...}}.
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
        control_buttons_config: dict = None,
        separator_top: bool = False,
        separator_bottom: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._config = config or {}
        self._title = title
        self._items_per_row = max(1, items_per_row)
        self._control_buttons_config = control_buttons_config or {}
        self._separator_top = separator_top
        self._separator_bottom = separator_bottom

        # Mapa interno: key -> SimpleCheckbox
        self._checkboxes: dict[str, SimpleCheckbox] = {}

        # Sistema de dependentes: pai -> [filhos]
        self._dependents_map: dict[str, list[str]] = {}
        # Estados salvos dos dependentes (antes de desabilitar)
        self._dep_states: dict[str, bool] = {}

        # Botões de controle (GridModernButtons)
        self._control_buttons: GridModernButtons = None

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

    def get_checked_keys(self) -> list:
        """
        Retorna lista de chaves onde checkbox está marcado.
        Equivalente ao antigo GridCheckboxWidget.get_checked_keys().
        """
        return [key for key, cb in self._checkboxes.items() if cb.isChecked()]

    def set_checked_keys(self, keys: list):
        """
        Marca as chaves da lista, desmarca as demais.
        Equivalente ao antigo GridCheckboxWidget.set_checked_keys().
        """
        keys_set = set(keys or [])
        for key, cb in self._checkboxes.items():
            cb.setChecked(key in keys_set)

    def get_checkbox(self, key: str):
        """
        Alias para widget(key) — retorna o SimpleCheckbox.
        Compatibilidade com API antiga get_checkbox().
        """
        return self._checkboxes.get(key)

    def select_all(self):
        """Marca todos os checkboxes."""
        for cb in self._checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(True)

    def deselect_all(self):
        """Desmarca todos os checkboxes."""
        for cb in self._checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(False)

    def invert_selection(self):
        """Inverte estado de todos os checkboxes habilitados."""
        for cb in self._checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(not cb.isChecked())

    def get_control_buttons(self):
        """Acesso ao GridModernButtons (se existir)."""
        return self._control_buttons

    # -- Sistema de dependentes --------------------------------------

    def _on_toggled(self, key: str, checked: bool):
        """Gerencia dependentes quando um checkbox muda."""
        dependents = self._dependents_map.get(key, [])
        for dep_key in dependents:
            dep_cb = self._checkboxes.get(dep_key)
            if not dep_cb:
                continue
            if not checked:
                # Pai desmarcado → desabilita e desmarca dependente
                self._dep_states[dep_key] = dep_cb.isChecked()
                dep_cb.setChecked(False)
                dep_cb.setEnabled(False)
            else:
                # Pai marcado → reabilita dependente com estado anterior
                dep_cb.setEnabled(True)
                dep_cb.setChecked(self._dep_states.get(dep_key, False))

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
                    f"    padding: 0 4px;"
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

        # Primeira passada: identificar dependentes
        for key, item_config in items:
            dependents = item_config.get("dependents", [])
            if dependents:
                self._dependents_map[key] = dependents
                for dep_key in dependents:
                    # Salva estado inicial do dependente
                    dep_config = self._config.get(dep_key, {})
                    self._dep_states[dep_key] = dep_config.get("default", False)

        # Segunda passada: criar checkboxes
        for index, (key, item_config) in enumerate(items):
            label = item_config.get("label", key)
            description = item_config.get("description", "")
            default = item_config.get("default", False)
            onchange = item_config.get("onchange")
            dependents = item_config.get("dependents", [])

            cb = SimpleCheckbox(text=label, parent=self)
            cb.setChecked(bool(default))

            if description:
                cb.setToolTip(description)

            if onchange:
                cb.toggled.connect(onchange)

            # Conecta ao sistema de dependentes (wrapper para preservar outros callbacks)
            if dependents:
                cb.toggled.connect(lambda checked, k=key: self._on_toggled(k, checked))

            self._checkboxes[key] = cb

            row = index // self._items_per_row
            col = index % self._items_per_row
            grid_layout.addWidget(cb, row, col)

        # Aplica estado inicial dos dependentes
        for parent_key, dep_keys in self._dependents_map.items():
            parent_cb = self._checkboxes.get(parent_key)
            if parent_cb and not parent_cb.isChecked():
                # Pai desmarcado inicialmente → dependentes começam desabilitados
                for dep_key in dep_keys:
                    dep_cb = self._checkboxes.get(dep_key)
                    if dep_cb:
                        dep_cb.setChecked(False)
                        dep_cb.setEnabled(False)

        # Adiciona stretch na ultima linha para alinhar ao topo
        if items:
            last_row = (len(items) - 1) // self._items_per_row
            grid_layout.setRowStretch(last_row, 0)
            grid_layout.setRowStretch(last_row + 1, 1)

        container_layout.addLayout(grid_layout)

        # Botões de controle (opcionais) — separador ABAIXO dos botões
        if self._control_buttons_config:
            self._control_buttons = GridModernButtons(
                config=self._control_buttons_config,
                separator_top=False,
                separator_bottom=True,
                parent=self,
            )
            container_layout.addWidget(self._control_buttons)

        outer_layout.addWidget(container)

        if self._separator_bottom:
            outer_layout.addWidget(SeparatorWidget())
