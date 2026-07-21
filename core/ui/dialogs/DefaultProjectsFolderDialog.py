# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QVBoxLayout

from ....i18n.TranslationManager import STR
from ....resources.widgets.simple.SelectorWidget import SelectorWidget
from ....resources.widgets.ExecutionButtonsWidget import ExecutionButtonsWidget
from ....core.ui.WidgetFactory import WidgetFactory
from ....core.config.LogUtils import LogUtils
from ....utils.ToolKeys import ToolKey
from ....plugins.BaseDialog import BaseDialog


class DefaultProjectsFolderDialog(BaseDialog):
    """Diálogo não-modal para seleção da pasta padrão de projetos.

    A pasta padrão NUNCA é hardcoded. Deve vir das Preferences
    e ser passada via construtor em ``current_folder``.
    """

    folder_selected = pyqtSignal(str)

    def __init__(self, current_folder: str = "", parent=None):
        super().__init__(parent)
        self.PLUGIN_NAME = STR.DEFAULT_PROJECTS_FOLDER_TITLE
        self.logger = LogUtils(
            tool=ToolKey.CREATE_PROJECT, class_name="DefaultProjectsFolderDialog", level="DEBUG"
        )
        self._current_folder = current_folder
        self.setWindowTitle(STR.DEFAULT_PROJECTS_FOLDER_TITLE)
        self.resize(620, 160)
        # Inicializa o MainLayout do BaseDialog (cria self.layout)
        self._build_ui(
            title=self.PLUGIN_NAME,
            enable_scroll=False,
            minimum_size=(300, 160),
        )
        self._build_inner_ui()

    def _build_inner_ui(self):
        """Constrói o conteúdo interno do diálogo dentro do MainLayout."""
        layout = QVBoxLayout()

        info = WidgetFactory.create_label(
            text=STR.DEFAULT_PROJECTS_FOLDER_PROMPT,
            word_wrap=True,
        )
        layout.addWidget(info)

        self.selector = SelectorWidget(
            title=STR.PROJECTS_FOLDER,
            mode=SelectorWidget.MODE_FOLDER,
            parent=self,
        )
        if self._current_folder:
            self.selector.set_path(self._current_folder)
        layout.addWidget(self.selector)

        # ExecutionButtonsWidget padronizado: OK + Cancelar (sem info)
        self._buttons_widget = ExecutionButtonsWidget(
            run_callback=self._on_accept,
            close_callback=self._on_reject,
            info_callback=None,
            run_text=STR.OK,
            close_text=STR.CANCEL,
            height=24,
            parent=self,
        )
        layout.addWidget(self._buttons_widget)

        # Adiciona ao MainLayout do BaseDialog
        self.layout.add_items([layout])

    def _on_accept(self):
        """Callback de aceite — emite signal com o caminho e fecha."""
        path = self.get_folder_path()
        self.folder_selected.emit(path)
        self.accept()

    def _on_reject(self):
        """Callback de rejeição — emite signal vazio e fecha."""
        self.folder_selected.emit("")
        self.reject()

    def get_folder_path(self) -> str:
        """Retorna o caminho da pasta selecionada.

        Retorna string vazia se nada foi selecionado.
        NUNCA retorna um valor hardcoded — a pasta deve vir das Preferences.
        """
        paths = self.selector.get_paths()
        if paths:
            return paths[0].strip()

        fallback_text = self.selector.get_file_path().strip()
        return fallback_text or ""