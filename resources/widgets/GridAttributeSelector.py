# -*- coding: utf-8 -*-
"""
GridAttributeSelector — Widget específico para seleção de atributos.
========================================================================
Widget com:
- Título do grupo
- Checkbox "Usar todos os atributos"
- Grid de checkboxes (1 coluna) para cada campo
- GridModernButtons: selecionar, remover, inverter
- Estilo próprio via _specific_style() + AppStyles
- Logger obrigatório via LogUtils com tool_key

Uso em plugins:
    attr_selector = GridAttributeSelector(
        title="Atributos da Camada de Origem",
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    attr_selector.set_fields(["campo1", "campo2", "campo3"])
    attr_selector.use_all_fields()  # True/False
    attr_selector.get_selected_fields()  # ["campo1", "campo3"]
"""

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QScrollArea
from qgis.PyQt.QtCore import Qt
from ...core.config.LogUtils import LogUtils
from ..styles.AppStyles import AppStyles
from .simple.SimpleCheckbox import SimpleCheckbox
from .grid.GridCheckbox import GridCheckbox
from .grid.GridModernButtons import GridModernButtons


class GridAttributeSelector(QWidget):
    """
    Widget específico para seleção de atributos com checkboxes.

    Parâmetros
    ----------
    title : str, optional
        Título do grupo (QGroupBox).
    check_all_text : str, optional
        Texto do checkbox "Usar todos os atributos".
    tool_key : ToolKey, optional
        ToolKey para logging. Obrigatório se não parent com logger.
    parent : QWidget, optional
        Widget pai.

    Autoconfiguração
    ----------------
    - AppStyles: métodos globais
    - _specific_style(): estilo específico com tokens do tema
    - LogUtils: logger obrigatório para rastreamento
    """

    def __init__(
        self,
        title: str = "",
        check_all_text: str = "Usar todos os atributos",
        tool_key=None,
        parent=None,
    ):
        super().__init__(parent)

        self._title = title
        self._check_all_text = check_all_text
        self._tool_key = tool_key

        # Logger obrigatório
        self._logger = LogUtils(
            tool=tool_key or "GridAttributeSelector",
            class_name="GridAttributeSelector",
        )

        # Checkbox "Usar todos os atributos"
        self._chk_all = None

        # Grid de checkboxes dos atributos (1 coluna)
        self._attr_grid = None

        # Scroll area interna para o grid de checkboxes
        self._scroll_area = None
        self._scroll_container = None

        # Botões de controle
        self._control_buttons = None

        # Estados internos
        self._field_names: list[str] = []

        try:
            self._build_ui()
            self._apply_styles()
        except Exception as error:
            self._logger.exception(
                error, code="GRID_ATTR_SELECTOR_INIT_ERR"
            )

    # ══════════════════════════════════════════════════════════════
    # API Pública
    # ══════════════════════════════════════════════════════════════

    def set_fields(self, field_names: list[str]):
        """
        Popula checkboxes com nomes dos campos.

        Parameters
        ----------
        field_names : list[str]
            Lista de nomes de campos da camada.
        """
        self._field_names = list(field_names)
        self._rebuild_attr_grid()
        self._logger.info(
            f"set_fields: {len(field_names)} campos populados",
            code="ATTR_SET_FIELDS",
        )

    def get_selected_fields(self):
        """
        Retorna campos selecionados.

        Returns
        -------
        list[str] or None
            None se "usar todos" estiver marcado.
            Lista de nomes se seleção manual.
        """
        if self._chk_all and self._chk_all.isChecked():
            return None

        if not self._attr_grid:
            return []

        return [
            name for name in self._field_names
            if self._attr_grid.is_checked(name)
        ]

    def use_all_fields(self) -> bool:
        """Retorna True se 'Usar todos os atributos' está marcado."""
        return self._chk_all.isChecked() if self._chk_all else False

    def set_checked_all(self, checked: bool):
        """Marca/desmarca 'Usar todos os atributos'."""
        if self._chk_all:
            self._chk_all.setChecked(checked)

    def get_all_states(self) -> dict[str, bool]:
        """Retorna dict {campo: bool} com estado de cada checkbox."""
        if not self._attr_grid:
            return {}
        return self._attr_grid.get_all_states()

    # ══════════════════════════════════════════════════════════════
    # Interno
    # ══════════════════════════════════════════════════════════════

    def _build_ui(self):
        """Monta layout do widget."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        theme = AppStyles._get_theme()

        # ── Container com título ────────────────────────────────
        if self._title:
            container = QGroupBox(self._title)
            container.setObjectName("attr_group")
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

        # ── Checkbox "Usar todos os atributos" ──────────────────
        self._chk_all = SimpleCheckbox(
            text=self._check_all_text,
            parent=self,
        )
        self._chk_all.setObjectName("chk_all_attributes")
        self._chk_all.toggled.connect(self._on_chk_all_toggled)
        container_layout.addWidget(self._chk_all)

        # ── Scroll area para o grid de checkboxes ──────────────
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll_area.setFrameShadow(QScrollArea.Shadow.Plain)
        self._scroll_area.setObjectName("attr_scroll")
        # Altura máxima para ativar scroll quando houver muitos campos
        self._scroll_area.setMaximumHeight(200)

        # Container interno do scroll com fundo secondary + transparencia
        self._scroll_container = QWidget()
        self._scroll_container.setObjectName("attr_scroll_container")
        self._scroll_container_layout = QVBoxLayout(
            self._scroll_container
        )
        self._scroll_container_layout.setContentsMargins(4, 4, 4, 4)
        self._scroll_container_layout.setSpacing(2)

        # ── Grid de checkboxes (1 coluna) — criado sob demanda ─
        self._attr_grid = GridCheckbox(
            config={},  # vazio, preenchido por set_fields()
            items_per_row=2,
            parent=self._scroll_container,
        )
        self._scroll_container_layout.addWidget(self._attr_grid)
        self._scroll_container_layout.addStretch()

        self._scroll_area.setWidget(self._scroll_container)
        container_layout.addWidget(self._scroll_area)

        # ── Botões de controle (GridModernButtons) ──────────────
        self._control_buttons = GridModernButtons(
            config={
                "select_all": {
                    "label": "Selecionar",
                    "callback": self._on_select_all,
                    "primary": False,
                },
                "deselect_all": {
                    "label": "Remover",
                    "callback": self._on_deselect_all,
                    "primary": False,
                },
                "invert": {
                    "label": "Inverter",
                    "callback": self._on_invert_selection,
                    "primary": False,
                },
            },
            alignment="justify",
            separator_top=True,
            separator_bottom=False,
            parent=self,
        )
        container_layout.addWidget(self._control_buttons)

        outer.addWidget(container)

    def _rebuild_attr_grid(self):
        """Reconstrói grid de checkboxes com campos atuais."""
        if not self._attr_grid or not self._scroll_container_layout:
            return

        try:
            config = {}
            for name in self._field_names:
                config[name] = {
                    "label": name,
                    "default": True,  # Todos marcados por padrão
                }

            # Remove o GridCheckbox antigo do scroll container
            old_grid = self._attr_grid
            self._scroll_container_layout.removeWidget(old_grid)
            old_grid.deleteLater()

            # Remove o stretch antigo (último item)
            while self._scroll_container_layout.count():
                item = self._scroll_container_layout.takeAt(
                    self._scroll_container_layout.count() - 1
                )
                if item.spacerItem():
                    del item
                else:
                    break

            # Cria novo GridCheckbox dentro do scroll container
            self._attr_grid = GridCheckbox(
                config=config,
                items_per_row=2,
                parent=self._scroll_container,
            )
            self._scroll_container_layout.addWidget(self._attr_grid)
            self._scroll_container_layout.addStretch()

            # Aplica estado do "usar todos"
            if self._chk_all and self._chk_all.isChecked():
                self._attr_grid.setEnabled(False)
                if self._control_buttons:
                    self._control_buttons.setEnabled(False)

        except Exception as error:
            self._logger.exception(
                error, code="ATTR_REBUILD_GRID_ERR"
            )

    def _on_chk_all_toggled(self, checked: bool):
        """
        Quando 'Usar todos os atributos' está ativo,
        desabilita scroll area, grid de checkboxes e botões de controle.
        """
        try:
            if self._scroll_area:
                self._scroll_area.setEnabled(not checked)
            if self._attr_grid:
                self._attr_grid.setEnabled(not checked)
            if self._control_buttons:
                self._control_buttons.setEnabled(not checked)
        except Exception as error:
            self._logger.exception(
                error, code="ATTR_CHK_ALL_TOGGLED_ERR"
            )

    def _on_select_all(self):
        """Seleciona todos os atributos."""
        try:
            if self._attr_grid:
                self._attr_grid.select_all()
        except Exception as error:
            self._logger.exception(
                error, code="ATTR_SELECT_ALL_ERR"
            )

    def _on_deselect_all(self):
        """Remove seleção de todos os atributos."""
        try:
            if self._attr_grid:
                self._attr_grid.deselect_all()
        except Exception as error:
            self._logger.exception(
                error, code="ATTR_DESELECT_ALL_ERR"
            )

    def _on_invert_selection(self):
        """Inverte seleção dos atributos."""
        try:
            if self._attr_grid:
                self._attr_grid.invert_selection()
        except Exception as error:
            self._logger.exception(
                error, code="ATTR_INVERT_SEL_ERR"
            )

    # ══════════════════════════════════════════════════════════════
    # Estilos
    # ══════════════════════════════════════════════════════════════

    def _apply_styles(self):
        """Aplica estilos globais + específico."""
        try:
            combined = self._get_global_style() + self._specific_style()
            self.setStyleSheet(combined)
        except Exception as error:
            self._logger.exception(
                error, code="ATTR_APPLY_STYLES_ERR"
            )

    def _get_global_style(self) -> str:
        """Estilos globais via AppStyles."""
        return (
            AppStyles.label()
            + AppStyles.checkbox()
            + AppStyles.button()
        )

    def _specific_style(self) -> str:
        """
        Estilo específico do GridAttributeSelector.
        Usa tokens do tema com nomes descritivos.

        Estiliza:
        - Checkbox "Usar todos os atributos" com destaque visual
        - Container do grupo de atributos
        - Scroll area com fundo secondary + transparencia
        - Container interno do scroll com fundo secondary + transparencia
        """
        theme = AppStyles._get_theme()
        fs = theme.FONT_SIZE_CHECKBOX_BOLD
        ca = theme.COLOR_TEXT_ACCENT
        pb = theme.PADDING_CHECKBOX_BOLD
        cp = theme.COLOR_PANEL_BACKGROUND
        po = theme.PXBORDER_ONE
        cd = theme.COLOR_BORDER_DEFAULT
        br = theme.BORDER_RADIUS_PANEL
        pp = theme.PADDING_PANEL
        # Fundo secondary com transparencia (COLOR_BACKGROUND_SOFT = "rgba(24, 24, 27, 0.8)")
        soft = theme.COLOR_BACKGROUND_SOFT
        return (
            "QCheckBox#chk_all_attributes {"
            f"    font-weight: bold;"
            f"    font-size: {fs};"
            f"    color: {ca};"
            f"    padding: {pb};"
            "}"
            "QGroupBox#attr_group {"
            f"    background: {cp};"
            f"    border: {po} {cd};"
            f"    border-radius: {br};"
            f"    padding: {pp};"
            "}"
            "QScrollArea#attr_scroll {"
            f"    background: {soft};"
            f"    border: {po} {cd};"
            f"    border-radius: {br};"
            "}"
            "QWidget#attr_scroll_container {"
            f"    background: {soft};"
            "}"
        )
