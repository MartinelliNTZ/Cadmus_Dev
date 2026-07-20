# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QLabel, QVBoxLayout

from ....i18n.TranslationManager import STR
from ....resources.widgets.simple.SelectorWidget import SelectorWidget
from ....resources.widgets.ExecutionButtonsWidget import ExecutionButtonsWidget
from ....plugins.BaseDialog import BaseDialog


class DefaultProjectsFolderDialog(BaseDialog):
    """Diálogo não-modal para seleção da pasta padrão de projetos."""

    folder_selected = pyqtSignal(str)
    DEFAULT_FOLDER = "C:/QgisProjects"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.PLUGIN_NAME = STR.DEFAULT_PROJECTS_FOLDER_TITLE
        from ....core.config.LogUtils import LogUtils
        from ....utils.ToolKeys import ToolKey
        self.logger = LogUtils(
            tool=ToolKey.CREATE_PROJECT, class_name="DefaultProjectsFolderDialog", level="DEBUG"
        )
        self.setWindowTitle(STR.DEFAULT_PROJECTS_FOLDER_TITLE)
        self.setModal(False)
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

        info = QLabel(STR.DEFAULT_PROJECTS_FOLDER_PROMPT)
        info.setWordWrap(True)
        layout.addWidget(info)

        self.selector = SelectorWidget(
            title=STR.PROJECTS_FOLDER,
            mode=SelectorWidget.MODE_FOLDER,
            parent=self,
        )
        self.selector.set_path(self.DEFAULT_FOLDER)
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
        """Retorna o caminho da pasta selecionada."""
        paths = self.selector.get_paths()
        if paths:
            return paths[0].strip()

        fallback_text = self.selector.get_file_path().strip()
        return fallback_text or self.DEFAULT_FOLDER