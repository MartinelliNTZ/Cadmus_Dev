# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import (
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
)
from qgis.PyQt.QtCore import Qt

from ....i18n.TranslationManager import STR
from ....resources.styles.Styles import Styles
from ....resources.widgets.ExecutionButtonsWidget import ExecutionButtonsWidget
from ....core.config.LogUtils import LogUtils
from ....utils.Preferences import Preferences
from ....utils.QgisMessageUtil import QgisMessageUtil
from ....utils.ToolKeys import ToolKey


class ProjectNameDialog:
    """
    Dialogo de nome de projeto com:
    - Exibição da pasta atual
    - Botão para abrir Configurações Cadmus
    - ExecutionButtonsWidget: Criar Projeto + Fechar + Instruções
    """

    def __init__(
        self,
        suggested_name: str,
        base_folder: str = "",
        project_tool_key: str = ToolKey.CREATE_PROJECT,
        parent=None,
    ):
        self._suggested_name = suggested_name
        self._base_folder = base_folder
        self._project_tool_key = project_tool_key
        self._parent = parent
        self._result = False
        self._project_name = ""

        from qgis.PyQt.QtWidgets import QDialog as QD

        self.dialog = QD(parent)
        self.dialog.setObjectName("project_name_dialog")
        self.dialog.setWindowTitle(STR.PROJECT_NAME_TITLE)
        self.dialog.setModal(False)
        self.dialog.resize(480, 220)

        self.logger = LogUtils(
            tool=project_tool_key, class_name="ProjectNameDialog", level="DEBUG"
        )

        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        """Monta os widgets do dialogo."""
        layout = QVBoxLayout(self.dialog)

        # ── Pasta atual (exibição) ──
        folder_label = QLabel(f"📂 {STR.PROJECTS_DEFAULT_FOLDER}:")
        folder_label.setObjectName("project_name_folder_label")
        layout.addWidget(folder_label)

        folder_path = QLineEdit(self._base_folder)
        folder_path.setObjectName("project_name_folder_path")
        folder_path.setReadOnly(True)
        layout.addWidget(folder_path)

        # ── Botão Configurações ──
        from qgis.PyQt.QtWidgets import QPushButton

        settings_btn = QPushButton(f"⚙️ {STR.OPEN_SETTINGS}")
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

        # ── ExecutionButtonsWidget: Criar + Fechar + Instruções ──
        self._buttons_widget = ExecutionButtonsWidget(
            run_callback=self._on_accept,
            close_callback=self._on_reject,
            info_callback=self._show_instructions,
            run_text=STR.CREATE_PROJECT,
            close_text=STR.CANCEL,
            height=24,
            parent=self.dialog,
        )
        layout.addWidget(self._buttons_widget)

    def _apply_styles(self):
        """Aplica o stylesheet."""
        self.dialog.setStyleSheet(Styles.project_name_dialog())

    def _open_settings(self):
        """Abre Configurações Cadmus."""
        self.logger.info("Abrindo Configurações Cadmus via ProjectNameDialog")
        try:
            # Tentar obter iface do parent chain
            iface = None
            p = self.dialog.parent()
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
                    "Abra Configurações Cadmus pelo menu Cadmus > Sistema > Configurações.",
                )
                return

            from ....plugins.SettingsPlugin import SettingsPlugin

            dlg = SettingsPlugin(iface)
            dlg.setModal(False)
            dlg.show()
        except Exception as e:
            self.logger.error(f"Erro ao abrir Configurações: {e}")
            QgisMessageUtil.bar_warning(
                None,
                "Abra Configurações Cadmus pelo menu Cadmus > Sistema > Configurações.",
            )

    def _show_instructions(self):
        """Exibe instruções da ferramenta."""
        self.logger.debug("Exibindo instruções via ProjectNameDialog")
        try:
            from ....resources.InstructionsManager import InstructionsManager
            from ....core.ui.info_dialog import InfoDialog

            instructions_file = InstructionsManager.get(self._project_tool_key)
            title = f"📘 {STR.INSTRUCTIONS} – {STR.CREATE_PROJECT_TITLE}"
            InfoDialog(instructions_file, self.dialog, title).exec()
        except Exception as e:
            self.logger.error(f"Erro ao exibir instruções: {e}")

    def _on_accept(self):
        """Callback de aceite — fecha com resultado positivo."""
        self._project_name = self.name_input.text().strip()
        self._result = True
        self.dialog.accept()

    def _on_reject(self):
        """Callback de rejeição — fecha com resultado negativo."""
        self._result = False
        self.dialog.reject()

    def exec(self):
        """Executa o dialogo modalmente."""
        return self.dialog.exec()

    def get_project_name(self) -> str:
        """Retorna o nome de projeto informado sem espacos extras."""
        return self._project_name or self.name_input.text().strip()