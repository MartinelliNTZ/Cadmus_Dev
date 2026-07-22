# -*- coding: utf-8 -*-
"""
SimpleReadOnly — QLineEdit readonly com AppStyles.input() e botão copiar opcional.
USO INTERNO — GridReadOnly usa este widget.
Plugins NUNCA importam Simple diretamente.
"""

from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from qgis.PyQt.QtCore import Qt
from ...styles.AppStyles import AppStyles


class SimpleReadOnly(QWidget):
    """
    Campo de texto readonly com estilo de input e botão copiar opcional.

    Parâmetros
    ----------
    text : str, optional
        Texto inicial.
    placeholder : str, optional
        Placeholder text.
    show_copy_button : bool, optional
        Se True, exibe botão copiar ao lado do campo.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(self, text: str = "", placeholder: str = "", show_copy_button: bool = False, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._line_edit = QLineEdit(self)
        self._line_edit.setReadOnly(True)
        if text:
            self._line_edit.setText(str(text))
        if placeholder:
            self._line_edit.setPlaceholderText(placeholder)
        self._line_edit.setStyleSheet(AppStyles.input())

        layout.addWidget(self._line_edit, stretch=1)

        if show_copy_button:
            self._copy_btn = QPushButton("📋", self)
            self._copy_btn.setFixedSize(20, 20)
            self._copy_btn.setToolTip("Copiar")
            self._copy_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 10px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background: rgba(166, 120, 79, 80);
                    border-radius: 3px;
                }
            """)
            self._copy_btn.clicked.connect(self._copy_to_clipboard)
            layout.addWidget(self._copy_btn)

    def _copy_to_clipboard(self):
        """Copia o texto do campo para a área de transferência."""
        from qgis.PyQt.QtWidgets import QApplication
        text = self._line_edit.text()
        if text:
            QApplication.clipboard().setText(text)

    def setText(self, text: str):
        """Define o texto do campo (aceita None)."""
        self._line_edit.setText(str(text) if text is not None else "")

    def text(self) -> str:
        """Retorna o texto do campo."""
        return self._line_edit.text()

    def setPlaceholderText(self, text: str):
        """Define o placeholder do campo."""
        self._line_edit.setPlaceholderText(text)