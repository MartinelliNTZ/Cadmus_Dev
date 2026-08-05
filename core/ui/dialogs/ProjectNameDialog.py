# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import pyqtSignal

from ....i18n.TranslationManager import STR
from ....plugins.BaseDialog import BaseDialog
from ....resources.widgets.grid.GridLabel import GridLabel
from ....resources.widgets.grid.GridInputFields import GridInputFields
from ....resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ....core.config.LogUtils import LogUtils
from ....utils.ToolKeys import ToolKey


class ProjectNameDialog(BaseDialog):
    """
    Dialogo nao-modal de nome de projeto com:
    - Exibicao da pasta atual (GridLabel unico)
    - Campo de nome com suggest (GridInputFields com placeholder)
    - GridExecutionButtons: Criar Projeto + Fechar + Config + Info (nativos)
    """

    project_accepted = pyqtSignal(str)

    def __init__(
        self,
        suggested_name: str,
        base_folder: str = "",
        project_tool_key: str = ToolKey.CREATE_PROJECT,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("project_name_dialog")
        self.setWindowTitle(STR.PROJECT_NAME_TITLE)
        self.resize(480, 220)

        self._suggested_name = suggested_name
        self._base_folder = base_folder
        self._project_tool_key = project_tool_key
        self._result = False
        self._project_name = ""

        self.PLUGIN_NAME = STR.PROJECT_NAME_TITLE

        self.logger = LogUtils(
            tool=project_tool_key, class_name="ProjectNameDialog", level="DEBUG"
        )

        # Inicializa o MainLayout do BaseDialog (cria self.layout)
        self._build_ui(
            title=self.PLUGIN_NAME,
            enable_scroll=False,
            minimum_size=(300, 220),
        )
        self._build_inner_ui()

    def _build_inner_ui(self):
        """Monta os widgets do dialogo."""

        # ── GridLabel UNICO com pasta + label do nome ──
        self.info_group = GridLabel(config={
            "folder_title": {"text": f"\U0001F4C2 {STR.PROJECTS_DEFAULT_FOLDER}:"},
            "folder_path": {"text": self._base_folder},
            "explicacao": {"text": "Para mudar a pasta padrão, clique no botão Configurações ⚙️."},
        }, parent=self)
        self.layout.addWidget(self.info_group)

        # ── GridInputFields com placeholder (suggest ao fundo) ──
        self.name_input = GridInputFields(config={
            "project_name": {
                "label": f"\u270F\ufe0f {STR.PROJECT_NAME_LABEL}:",
                "description": STR.PROJECT_NAME_PROMPT,
                "placeholder": self._suggested_name,
                "default": "",
            },
        }, title=None, separator_top=True, separator_bottom=True, parent=self)
        self.layout.addWidget(self.name_input)

        # ── GridExecutionButtons: Criar + Fechar + Config + Info (nativos) ──
        self._buttons_widget = GridExecutionButtons(
            config={
                "create": {
                    "label": STR.CREATE_PROJECT,
                    "description": "Criar o projeto na pasta definida",
                    "callback": self._on_accept,
                    "is_run_button": True,
                },
            },
            enable_info=True,
            tool_key=self._project_tool_key,
            parent=self,
        )
        self.layout.add_execution_buttons(self._buttons_widget)

    def _on_accept(self):
        """Callback de aceite — emite signal com o nome e fecha."""
        raw_name = self.name_input.get_value("project_name").strip()
        # Se usuario nao digitou nada, usa o suggested_name (placeholder)
        self._project_name = raw_name if raw_name else self._suggested_name
        self._result = True
        name = self.get_project_name()
        self.project_accepted.emit(name)
        self.accept()

    def get_project_name(self) -> str:
        """Retorna o nome de projeto informado sem espacos extras."""
        if self._project_name:
            return self._project_name
        raw = self.name_input.get_value("project_name").strip()
        return raw if raw else self._suggested_name
