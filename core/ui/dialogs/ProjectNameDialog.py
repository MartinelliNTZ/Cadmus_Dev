# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
)

from ....i18n.TranslationManager import STR
from ....plugins.BaseDialog import BaseDialog
from ....resources.styles.Styles import Styles
from ....resources.widgets.ExecutionButtonsWidget import ExecutionButtonsWidget
from ....core.config.LogUtils import LogUtils
from ....utils.QgisMessageUtil import QgisMessageUtil
from ....utils.ToolKeys import ToolKey


class ProjectNameDialog(BaseDialog):
    """
    Dialogo nao-modal de nome de projeto com:
    - Exibicao da pasta atual
    - Botao para abrir Configuracoes Cadmus
    - ExecutionButtonsWidget: Criar Projeto + Fechar + Instrucoes
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
        self.setModal(False)
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
        self._apply_styles()

    def _build_inner_ui(self):
        """Monta os widgets do dialogo."""
        layout = QVBoxLayout()

        # ── Pasta atual (exibicao) ──
        folder_label = QLabel(f"\U0001F4C2 {STR.PROJECTS_DEFAULT_FOLDER}:")
        folder_label.setObjectName("project_name_folder_label")
        layout.addWidget(folder_label)

        folder_path = QLineEdit(self._base_folder)
        folder_path.setObjectName("project_name_folder_path")
        folder_path.setReadOnly(True)
        layout.addWidget(folder_path)

        # ── Botao Configuracoes ──
        from qgis.PyQt.QtWidgets import QPushButton

        settings_btn = QPushButton(f"\u2699\ufe0f {STR.OPEN_SETTINGS}")
        settings_btn.setObjectName("project_name_settings_btn")
        settings_btn.setFixedHeight(24)
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)

        # ── Nome do projeto ──
        info = QLabel(STR.PROJECT_NAME_PROMPT)
        info.setObjectName("project_name_info_label")
        info.setWordWrap(True)
        layout.addWidget(info)

        row = QHBoxLayout()
        field_label = QLabel(STR.PROJECT_NAME_LABEL)
        field_label.setObjectName("project_name_field_label")
        row.addWidget(field_label)

        self.name_input = QLineEdit()
        self.name_input.setObjectName("project_name_input")
        self.name_input.setPlaceholderText(self._suggested_name)
        row.addWidget(self.name_input)
        layout.addLayout(row)

        # ── ExecutionButtonsWidget: Criar + Fechar + Instrucoes ──
        self._buttons_widget = ExecutionButtonsWidget(
            run_callback=self._on_accept,
            close_callback=self._on_reject,
            info_callback=self._show_instructions,
            run_text=STR.CREATE_PROJECT,
            close_text=STR.CANCEL,
            height=24,
            parent=self,
        )
        layout.addWidget(self._buttons_widget)

        # Adiciona ao MainLayout do BaseDialog
        self.layout.add_items([layout])

    def _apply_styles(self):
        """Aplica o stylesheet."""
        self.setStyleSheet(Styles.project_name_dialog())

    def _open_settings(self):
        """Abre Configuracoes Cadmus."""
        self.logger.info("Abrindo Configuracoes Cadmus via ProjectNameDialog")
        try:
            # Tentar obter iface do parent chain
            iface = None
            p = self.parent()
            while p is not None:
                if hasattr(p, "iface"):
                    iface = p.iface
                    break
                p = p.parent()

            if iface is None:
                # Fallback: tentar do QgisInterface global
                try:
                    from qgis.utils import iface as qgis_iface

                    iface = qgis_iface
                except Exception:
                    pass

            if iface is None:
                QgisMessageUtil.bar_warning(
                    None,
                    "Abra Configuracoes Cadmus pelo menu Cadmus > Sistema > Configuracoes.",
                )
                return

            from ....plugins.SettingsPlugin import SettingsPlugin

            dlg = SettingsPlugin(iface)
            dlg.setModal(False)
            dlg.show()
        except Exception as e:
            self.logger.error(f"Erro ao abrir Configuracoes: {e}")
            QgisMessageUtil.bar_warning(
                None,
                "Abra Configuracoes Cadmus pelo menu Cadmus > Sistema > Configuracoes.",
            )

    def _show_instructions(self):
        """Exibe instrucoes da ferramenta."""
        self.logger.debug("Exibindo instrucoes via ProjectNameDialog")
        try:
            from ....resources.InstructionsManager import InstructionsManager
            from ....core.ui.info_dialog import InfoDialog

            instructions_file = InstructionsManager.get(self._project_tool_key)
            title = f"\U0001F4D8 {STR.INSTRUCTIONS} \u2013 {STR.CREATE_PROJECT_TITLE}"
            InfoDialog(instructions_file, self, title).exec()
        except Exception as e:
            self.logger.error(f"Erro ao exibir instrucoes: {e}")

    def _on_accept(self):
        """Callback de aceite — emite signal com o nome e fecha."""
        self._project_name = self.name_input.text().strip()
        self._result = True
        name = self.get_project_name()
        self.project_accepted.emit(name)
        self.accept()

    def _on_reject(self):
        """Callback de rejeicao — emite signal None e fecha."""
        self._result = False
        self.project_accepted.emit(None)
        self.reject()

    def get_project_name(self) -> str:
        """Retorna o nome de projeto informado sem espacos extras."""
        return self._project_name or self.name_input.text().strip()