# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from ....i18n.TranslationManager import STR
from ....plugins.BaseDialog import BaseDialog


class ProjectNameDialog(BaseDialog):
    def __init__(self, suggested_name: str, parent=None):
        super().__init__(parent)
        self._suggested_name = suggested_name
        self.setWindowTitle(STR.PROJECT_NAME_TITLE)
        self.setModal(False)
        self.resize(460, 110)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(STR.PROJECT_NAME_PROMPT)
        info.setWordWrap(True)
        layout.addWidget(info)

        row = QHBoxLayout()
        row.addWidget(QLabel(STR.PROJECT_NAME_LABEL))

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(self._suggested_name)
        row.addWidget(self.name_input)
        layout.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_project_name(self) -> str:
        return self.name_input.text().strip()
