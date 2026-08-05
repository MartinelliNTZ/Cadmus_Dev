# -*- coding: utf-8 -*-
"""
ReplaceInLayouts — Substitui texto em layouts do projeto.
Plugin migrado para novo sistema de widgets (widgets/).
"""

from ..utils.Preferences import Preferences
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.LayoutsUtils import LayoutsUtils
from ..utils.ProjectUtils import ProjectUtils
from ..utils.ToolKeys import ToolKey
from .BasePlugin import BasePluginMTL
from ..resources.widgets.grid.GridInputFields import GridInputFields
from ..resources.widgets.grid.GridCheckbox import GridCheckbox
from ..resources.widgets.grid.GridLabel import GridLabel
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..i18n.TranslationManager import STR


class ReplaceInLayoutsDialog(BasePluginMTL):
    CHECKBOX_OPTIONS = {
        "case_sensitive": {
            "label": STR.CASE_SENSITIVE,
            "description": "Diferenciar maiusculas de minusculas na busca",
            "default": True,
        },
        "full_replace": {
            "label": STR.FULL_LABEL_REPLACE,
            "description": "Substituir o label inteiro em vez de apenas o texto",
            "default": False,
        },
    }

    TOOL_KEY = ToolKey.REPLACE_IN_LAYOUTS

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface

        self.init(
            self.TOOL_KEY,
            "ReplaceInLayoutsDialog",
            load_system_prefs=False,
            build_ui=True,
        )

    def _build_ui(self, **kwargs):
        super()._build_ui(
            title=STR.REPLACE_IN_LAYOUTS_TITLE,
            icon_path="Cadmus_icon.png",
            enable_scroll=False,
        )

        # ====== CAMPOS DE TEXTO (old_text + new_text) ======
        self.input_fields = GridInputFields(
            config={
                "old_text": {
                    "label": STR.SEARCH_TEXT,
                    "description": "Texto original a ser substituido nos layouts",
                    "default": "",
                },
                "new_text": {
                    "label": STR.REPLACE_WITH_NEW_TEXT,
                    "description": "Novo texto que substituira o original",
                    "default": "",
                },
            },
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self.input_fields)

        # ====== OPCOES (checkboxes) ======
        self.checkbox_widget = GridCheckbox(
            config=self.CHECKBOX_OPTIONS,
            title="Opcoes",
            items_per_row=1,
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self.checkbox_widget)

        # ====== INFO BACKUP ======
        self.info_label = GridLabel(
            config={
                "backup": {
                    "text": STR.PROJECT_BACKUP_INFO,
                    "description": "Backup automatico do projeto antes da substituicao",
                },
            },
            parent=self,
        )
        self.layout.addWidget(self.info_label)

        # ====== BOTOES DE ACAO (Run + Inverter + Close + Info) ======
        self.action_buttons = GridExecutionButtons(
            config={
                "run": {
                    "label": STR.REPLACE_IN_LAYOUTS_RUN,
                    "description": "Inicia a substituicao nos layouts do projeto",
                    "callback": self.execute_tool,
                    "is_run_button": True,
                },
                "swap": {
                    "label": "\u21c4 Inverter",
                    "description": "Inverte old_text com new_text",
                    "callback": self._swap_fields,
                    "is_run_button": False,
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
        self.input_fields.set_values(
            {
                "old_text": self.preferences.get("old_text", ""),
                "new_text": self.preferences.get("new_text", ""),
            }
        )
        self.checkbox_widget.set_checked(
            "case_sensitive", self.preferences.get("case_sensitive", True)
        )
        self.checkbox_widget.set_checked(
            "full_replace", self.preferences.get("full_replace", False)
        )

    def _save_prefs(self):
        """Salva preferencias."""
        values = self.input_fields.get_values()
        self.preferences["old_text"] = values.get("old_text", "")
        self.preferences["new_text"] = values.get("new_text", "")
        self.preferences["case_sensitive"] = self.checkbox_widget.is_checked("case_sensitive")
        self.preferences["full_replace"] = self.checkbox_widget.is_checked("full_replace")
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)

    def _swap_fields(self):
        """Inverte old_text com new_text."""
        old_val = self.input_fields.get_value("old_text")
        new_val = self.input_fields.get_value("new_text")
        self.input_fields.set_value("old_text", new_val)
        self.input_fields.set_value("new_text", old_val)

    def execute_tool(self):
        values = self.input_fields.get_values()
        old_text = values.get("old_text", "").strip()
        new_text = values.get("new_text", "")
        case_sensitive = self.checkbox_widget.is_checked("case_sensitive")
        full_replace = self.checkbox_widget.is_checked("full_replace")

        if not old_text:
            QgisMessageUtil.bar_warning(self.iface, STR.ENTER_TEXT_TO_SEARCH)
            return

        self._save_prefs()

        if not QgisMessageUtil.confirm_destructive(
            self,
            STR.CONFIRM_REPLACEMENTS,
            (
                f"<b>{STR.SEARCH_LABEL}</b> <i>{old_text}</i><br>"
                f"<b>{STR.REPLACE_WITH_LABEL}</b> <i>{new_text}</i>"
            ),
            red_text=STR.DESTRUCTIVE_OPERATION_WARNING,
        ):
            return

        project = ProjectUtils.get_project_instance()

        try:
            # BACKUP (se possivel)
            if ProjectUtils.is_project_saved(project):
                ProjectUtils.create_project_backup(project)

            # PROCESSA LAYOUTS
            result = LayoutsUtils.replace_text_in_layouts(
                project=project,
                tool_key=self.TOOL_KEY,
                old_text=old_text,
                new_text=new_text,
                case_sensitive=case_sensitive,
                full_replace=full_replace,
            )
            total = result.get("total_changes", 0)
            layouts = result.get("total_layouts", 0)
            message = (
                f"<b>{STR.LAYOUTS_ANALYZED}</b> {layouts}<br>"
                f"<b>{STR.CHANGES_APPLIED}</b> {total}"
            )
            QgisMessageUtil.modal_success(
                self.iface, message, STR.REPLACEMENT_COMPLETED_TITLE
            )
        except Exception as e:
            QgisMessageUtil.bar_critical(self, str(e), STR.ERROR)


def run(iface):
    dlg = ReplaceInLayoutsDialog(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg