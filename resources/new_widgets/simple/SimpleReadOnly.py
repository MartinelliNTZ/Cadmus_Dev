# -*- coding: utf-8 -*-
"""
SimpleReadOnly — QLineEdit readonly com AppStyles.input() e botão copiar opcional.
USO INTERNO — GridReadOnly usa este widget.
Plugins NUNCA importam Simple diretamente.
"""

from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout
from qgis.PyQt.QtCore import QSize
from ...IconManager import IconManager
from .SimpleModernButton import SimpleModernButton
from .SimpleQLineEdit import SimpleQLineEdit
from ....utils.ProjectUtils import ProjectUtils


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
    primary : bool, optional
        True → estilo primary (paleta PRIMARY do tema).
        False → estilo secondary (paleta NEUTRAL do tema).
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(self, text: str = "", placeholder: str = "", show_copy_button: bool = False, primary: bool = True, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._line_edit = SimpleQLineEdit(
            text=text,
            placeholder=placeholder,
            read_only=True,
            primary=primary,
            parent=self,
        )

        layout.addWidget(self._line_edit, stretch=1)

        if show_copy_button:
            self._copy_btn = SimpleModernButton(
                icon=IconManager.icon(IconManager.COPY2),
                icon_size=QSize(16, 16),
                fixed_size=32,
                tooltip="Copiar",
                parent=self,
                round_icon=True,
            )
            self._copy_btn.clicked.connect(self._copy_to_clipboard)
            layout.addWidget(self._copy_btn)

    def _copy_to_clipboard(self):
        """Copia o texto do campo para a área de transferência via ProjectUtils."""
        text = self._line_edit.text()
        if text:
            ProjectUtils.set_clipboard_text(text)

    def setText(self, text: str):
        """Define o texto do campo (aceita None)."""
        self._line_edit.setText(str(text) if text is not None else "")

    def text(self) -> str:
        """Retorna o texto do campo."""
        return self._line_edit.text()

    def setPlaceholderText(self, text: str):
        """Define o placeholder do campo."""
        self._line_edit.setPlaceholderText(text)