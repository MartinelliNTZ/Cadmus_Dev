# -*- coding: utf-8 -*-
from qgis.core import QgsProject

from ....i18n.TranslationManager import STR
from ....plugins.BaseDialog import BaseDialog
from ....resources.widgets.grid.GridCheckbox import GridCheckbox
from ....resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ....core.config.LogUtils import LogUtils
from ....utils.ToolKeys import ToolKey


class LayoutsSelectionDialog(BaseDialog):
    """
    Diálogo modal para selecionar quais layouts do projeto exportar.

    Usa GridCheckbox com control_buttons_config (Selecionar Todos /
    Desselecionar / Inverter) e GridExecutionButtons (OK/Fechar).
    """

    def __init__(self, selected=None, parent=None):
        super().__init__(parent)
        self.PLUGIN_NAME = STR.SELECT_LAYOUTS_TITLE
        self.logger = LogUtils(
            tool=ToolKey.EXPORT_ALL_LAYOUTS,
            class_name="LayoutsSelectionDialog",
        )
        self._selected = set(selected or [])
        self._checkbox = None

        self.setWindowTitle(STR.SELECT_LAYOUTS_TITLE)
        self.setModal(True)
        self.setMinimumSize(400, 400)

        self._build_ui(
            title=self.PLUGIN_NAME,
            icon_path="export_icon.ico",
            enable_scroll=True,
            minimum_size=(500, 300),
        )
        self._build_inner_ui()

    def _build_inner_ui(self):
        """Constrói o conteúdo interno do diálogo dentro do MainLayout."""
        project = QgsProject.instance()
        layouts = project.layoutManager().layouts()

        config = {}
        for layout in layouts:
            name = layout.name()
            config[name] = {
                "label": name,
                "default": name in self._selected,
            }

        self._checkbox = GridCheckbox(
            config=config,
            title=STR.SELECT_LAYOUTS_HINT,
            items_per_row=1,
            control_buttons_config={
                "select_all": {
                    "label": STR.SELECT_ALL,
                    "callback": lambda: self._checkbox.select_all(),
                },
                "deselect_all": {
                    "label": STR.DESELECT_ALL,
                    "callback": lambda: self._checkbox.deselect_all(),
                },
                "invert": {
                    "label": STR.INVERT_SELECTION,
                    "callback": lambda: self._checkbox.invert_selection(),
                },
            },
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self._checkbox)

        self._buttons = GridExecutionButtons(
            config={
                "ok": {
                    "label": STR.OK,
                    "description": "Confirma a seleção de layouts",
                    "callback": self._on_ok,
                    "is_run_button": True,
                },
            },
            enable_close_button=True,
            enable_config_button=False,
            enable_info=False,
            parent=self,
        )
        self.layout.add_execution_buttons(self._buttons)

    def _on_ok(self):
        """Confirma a seleção e fecha o diálogo."""
        self._selected = set(self._checkbox.get_checked_keys())
        self.accept()

    def get_selected_layouts(self):
        """Retorna a lista de nomes de layouts selecionados."""
        return list(self._selected)