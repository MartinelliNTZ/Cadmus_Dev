# -*- coding: utf-8 -*-
"""
DeveloperTestTool — Ferramenta oficial de testes do Cadmus.
Permite testar widgets e componentes do sistema em ambiente controlado.
"""

from ..utils.Preferences import Preferences
from ..utils.ToolKeys import ToolKey
from .BasePlugin import BasePluginMTL
from ..resources.widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..i18n.TranslationManager import STR


class DeveloperTestToolDialog(BasePluginMTL):
    """Diálogo de testes do desenvolvedor."""

    TOOL_KEY = ToolKey.DEVELOPER_TEST_TOOL

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface

        self.init(
            self.TOOL_KEY,
            "DeveloperTestToolDialog",
            load_system_prefs=False,
            build_ui=True,
        )

    def _build_ui(self, **kwargs):
        super()._build_ui(
            title=STR.DEVELOPER_TEST_TOOL_TITLE,
            icon_path="Cadmus_icon.png",
            enable_scroll=True,
        )

        # ====== GRID COMPLEX SELECTOR ======
        self.grid_selector = GridComplexSelector(
            config={
                "entrada": {
                    "label": "Arquivo de entrada",
                    "description": "Selecione o arquivo de entrada",
                    "file_filter": "Todos os arquivos (*.*)",
                    "mode_type": "input",
                    "allow_file": True,
                    "allow_folder": True,
                    "multiple": False,
                },
                "saida": {
                    "label": "Pasta de saída",
                    "description": "Pasta para salvar os arquivos",
                    "mode_type": "output",
                    "parent": "entrada",
                    "subfolder": "output",
                    "allow_folder": True,
                },
            },
            tool_key=self.TOOL_KEY,
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self.grid_selector)

        # ====== BOTOES DE ACAO ======
        self.action_buttons = GridExecutionButtons(
            config={
                "run": {
                    "label": STR.EXECUTE,
                    "description": "Executa a ação de teste",
                    "callback": self.execute_tool,
                    "is_run_button": True,
                },
            },
            enable_close_button=True,
            enable_info=True,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.layout.add_execution_buttons(self.action_buttons)

    def _load_prefs(self):
        """Carrega preferencias salvas."""
        self.grid_selector.set_preferences(
            self.preferences.get("grid_selector", {})
        )

    def _save_prefs(self):
        """Salva preferencias."""
        self.preferences["grid_selector"] = self.grid_selector.get_preferences()
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)

    def execute_tool(self):
        """Executa a ação de teste."""
        self.logger.info("Executando Developer Test Tool")
        self._save_prefs()


def run(iface):
    dlg = DeveloperTestToolDialog(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg