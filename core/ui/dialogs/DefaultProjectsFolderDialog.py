# -*- coding: utf-8 -*-
from ....i18n.TranslationManager import STR
from ....resources.widgets.grid.GridLabel import GridLabel
from ....resources.widgets.grid.GridComplexSelector import GridComplexSelector
from ....resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ....core.config.LogUtils import LogUtils
from ....utils.ToolKeys import ToolKey
from ....plugins.BaseDialog import BaseDialog


class DefaultProjectsFolderDialog(BaseDialog):
    """Diálogo não-modal para seleção da pasta padrão de projetos.

    A pasta padrão NUNCA é hardcoded. Deve vir das Preferences
    e ser passada via construtor em ``current_folder``.
    """

    def __init__(self, current_folder: str = "", parent=None):
        super().__init__(parent)
        self.PLUGIN_NAME = STR.DEFAULT_PROJECTS_FOLDER_TITLE
        self.logger = LogUtils(
            tool=ToolKey.CREATE_PROJECT, class_name="DefaultProjectsFolderDialog", level="DEBUG"
        )
        self._current_folder = current_folder
        self._result_path = ""
        self.setWindowTitle(STR.DEFAULT_PROJECTS_FOLDER_TITLE)
        self.resize(620, 200)
        # Inicializa o MainLayout do BaseDialog (cria self.layout)
        self._build_ui(
            title=self.PLUGIN_NAME,
            enable_scroll=False,
            minimum_size=(300, 200),
        )
        self._build_inner_ui()

    def _build_inner_ui(self):
        """Constrói o conteúdo interno do diálogo dentro do MainLayout."""

        # GridLabel com texto informativo
        info = GridLabel(config={
            "prompt": {"text": STR.DEFAULT_PROJECTS_FOLDER_PROMPT},
        }, parent=self)
        self.layout.addWidget(info)

        # GridComplexSelector para pasta
        self.selector = GridComplexSelector(
            config={
                "projects_folder": {
                    "label": STR.PROJECTS_FOLDER,
                    "description": STR.DEFAULT_PROJECTS_FOLDER_PROMPT,
                    "allow_folder": True,
                    "allow_file": False,
                    "multiple": False,
                    "mode_type": "input",
                    "show_explorer_button": True,
                },
            },
            tool_key=ToolKey.CREATE_PROJECT,
            separator_top=True,
            separator_bottom=True,
            parent=self,
        )
        if self._current_folder:
            self.selector.set_path("projects_folder", self._current_folder)
        self.layout.addWidget(self.selector)

        # GridExecutionButtons — NATIVO (close, config, info built-in)
        self._buttons_widget = GridExecutionButtons(
            config={
                "accept": {
                    "label": STR.OK,
                    "description": "Confirmar pasta padrão",
                    "callback": self._on_accept,
                    "is_run_button": True,
                },
            },
            tool_key=ToolKey.CREATE_PROJECT,
            parent=self,
        )
        self.layout.add_execution_buttons(self._buttons_widget)

    def _on_accept(self):
        """Callback de aceite — salva o caminho e fecha."""
        self._result_path = self.get_folder_path()
        self.accept()

    def get_folder_path(self) -> str:
        """Retorna o caminho da pasta selecionada.

        Retorna string vazia se nada foi selecionado.
        NUNCA retorna um valor hardcoded — a pasta deve vir das Preferences.
        """
        paths = self.selector.get_paths()
        if paths:
            return paths[0].strip()
        return self._result_path or ""