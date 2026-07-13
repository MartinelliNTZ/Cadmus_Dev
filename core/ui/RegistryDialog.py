# -*- coding: utf-8 -*-
"""
LicenseDialog — Diálogo de gerenciamento de licença
====================================================
Diálogo modal com:
- QLineEdit para inserir chave + botão 🔑 para validar
- Grid de labels: nível, validade, status
- Botão Apagar Licença
- Botão Salvar
"""

from qgis.PyQt.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGridLayout,
    QWidget,
)
from ...plugins.BaseDialog import BaseDialog
from ...i18n.TranslationManager import STR
from ...resources.styles.Styles import Styles
from ..config.RegistryManager import RegistryManager
from ..config.LogUtils import LogUtils
from ...utils.ToolKeys import ToolKey


class RegistryDialog(BaseDialog):
    """
    Diálogo modal para gerenciamento de licença.

    Layout:
    - QLineEdit para inserir chave
    - Botão 🔑 para validar
    - Grid: Nível, Validade, Status
    - Botão Apagar Licença
    - Botão Salvar + Fechar
    """

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.logger = LogUtils(tool=ToolKey.SETTINGS, class_name="LicenseDialog")
        self._license_mgr = RegistryManager(tool_key=ToolKey.SETTINGS)

        self.setWindowTitle(STR.LICENSE_TITLE)
        self.setMinimumWidth(400)
        self.setModal(True)

        self._input_key = None
        self._btn_validate = None
        self._lbl_level = None
        self._lbl_expiry = None
        self._lbl_status = None
        self._btn_delete = None
        self._btn_save = None

        self._build_ui()
        self._refresh()

    # ----------------------------------------------------------------
    # UI
    # ----------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Linha: input + botão validar
        key_row = QHBoxLayout()
        key_row.setSpacing(4)

        self._input_key = QLineEdit()
        self._input_key.setPlaceholderText("...")
        self._input_key.setStyleSheet(Styles.input())
        key_row.addWidget(self._input_key)

        self._btn_validate = QPushButton("_")
        self._btn_validate.setFixedWidth(32)
        self._btn_validate.setFixedHeight(24)
        self._btn_validate.setToolTip(STR.VALIDATE)
        self._btn_validate.clicked.connect(self._on_validate)
        key_row.addWidget(self._btn_validate)

        layout.addLayout(key_row)

        # Grid: Nível, Validade, Status
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(6)
        grid.setContentsMargins(0, 4, 0, 4)

        self._lbl_level_title = QLabel(f"{STR.LEVEL}:")
        self._lbl_level_title.setStyleSheet("font-weight: bold;")
        self._lbl_level = QLabel("-")
        grid.addWidget(self._lbl_level_title, 0, 0)
        grid.addWidget(self._lbl_level, 0, 1)

        self._lbl_expiry_title = QLabel(f"{STR.EXPIRATION_DATE}:")
        self._lbl_expiry_title.setStyleSheet("font-weight: bold;")
        self._lbl_expiry = QLabel("-")
        grid.addWidget(self._lbl_expiry_title, 1, 0)
        grid.addWidget(self._lbl_expiry, 1, 1)

        self._lbl_status_title = QLabel(f"{STR.STATUS}:")
        self._lbl_status_title.setStyleSheet("font-weight: bold;")
        self._lbl_status = QLabel(STR.INACTIVE)
        self._lbl_status.setStyleSheet("color: gray;")
        grid.addWidget(self._lbl_status_title, 2, 0)
        grid.addWidget(self._lbl_status, 2, 1)

        layout.addWidget(grid_w)

        # Botão Apagar
        self._btn_delete = QPushButton(f"🗑️ {STR.REMOVE}")
        self._btn_delete.clicked.connect(self._on_delete)
        layout.addWidget(self._btn_delete)

        # Botões Salvar + Fechar
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_save = QPushButton(f"💾 {STR.SAVE}")
        self._btn_save.setFixedHeight(28)
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_save)

        btn_close = QPushButton(STR.CLOSE)
        btn_close.setFixedHeight(28)
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

    # ----------------------------------------------------------------
    # Handlers
    # ----------------------------------------------------------------

    def _on_validate(self):
        self._do_save(show_message=False)

    def _on_save(self):
        self._do_save(show_message=True)

    def _do_save(self, show_message: bool):
        key = self._input_key.text().strip()
        if not key:
            self._refresh()
            if show_message:
                from ...utils.QgisMessageUtil import QgisMessageUtil
                QgisMessageUtil.modal_warning(
                    self.iface,
                    message=STR.LICENSE_EMPTY_KEY,
                    title=STR.LICENSE_TITLE,
                )
            return

        result = self._license_mgr.save_license_key(key)
        self._refresh()

        if show_message:
            from ...utils.QgisMessageUtil import QgisMessageUtil
            if result.get("success"):
                QgisMessageUtil.modal_info(
                    self.iface,
                    message=STR.LICENSE_SAVED_SUCCESS,
                    title=STR.LICENSE_TITLE,
                )
                self.accept()
            else:
                QgisMessageUtil.modal_warning(
                    self.iface,
                    message=result.get("message", STR.LICENSE_INVALID_KEY),
                    title=STR.LICENSE_TITLE,
                )

    def _on_delete(self):
        self._license_mgr.delete_license()
        self._input_key.clear()
        self._refresh()
        from ...utils.QgisMessageUtil import QgisMessageUtil
        QgisMessageUtil.modal_info(
            self.iface,
            message=STR.LICENSE_DELETED_SUCCESS,
            title=STR.LICENSE_TITLE,
        )

    def _refresh(self):
        info = self._license_mgr.get_license_info()

        has_key = info.get("has_key", False)
        is_active = info.get("is_active", False)
        is_valid = has_key and is_active

        nivel = info.get("nivel", 0)
        self._lbl_level.setText(str(nivel) if is_valid and nivel > 0 else "")
        self._lbl_expiry.setText(info.get("expiry") if is_valid else "")

        # Show/hide title labels based on whether a license exists
        self._lbl_level_title.setVisible(is_valid)
        self._lbl_expiry_title.setVisible(is_valid)
        self._lbl_status_title.setVisible(is_valid)

        if is_valid:
            self.setWindowTitle(STR.LICENSE_TITLE)
            self._btn_delete.setText(f"🗑️ {STR.REMOVE}")
            self._btn_save.setText(f"💾 {STR.SAVE}")

            days = info.get("days_remaining", 0)
            self._lbl_status.setText(f"{STR.ACTIVE} ({days} {STR.REMAINING_DAYS})")
            self._lbl_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.setWindowTitle("")
            self._btn_delete.setText("")
            self._btn_save.setText("")

            if not has_key:
                self._lbl_status.setText("")
                self._lbl_status.setStyleSheet("color: gray;")
            else:
                self._lbl_status.setText("")
                self._lbl_status.setStyleSheet("color: red; font-weight: bold;")
