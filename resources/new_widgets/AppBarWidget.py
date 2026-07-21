# -*- coding: utf-8 -*-
"""
AppBarWidget — Barra superior dos diálogos Cadmus.
Criado do zero para o novo sistema, sem dependência do antigo.
Usa AppStyles para estilos.

Faz parte do MainLayout — inserida no topo do _inner_layout.
"""

from qgis.PyQt.QtWidgets import QFrame, QLabel, QPushButton, QHBoxLayout
from qgis.PyQt.QtCore import Qt, QPoint
from qgis.PyQt.QtGui import QPixmap
import os
from ..styles.AppStyles import AppStyles


class AppBarWidget(QFrame):
    """
    Barra superior com título, botões de ação e drag da janela.

    Uso interno — instanciado pelo MainLayout.

    Parâmetros
    ----------
    title : str
        Texto do título.
    show_run : bool
        Mostra botão Executar.
    show_info : bool
        Mostra botão Info.
    show_close : bool
        Mostra botão Fechar.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        *,
        title: str,
        show_run: bool = False,
        show_info: bool = False,
        show_close: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("app_bar")
        self._drag_pos = None

        self.setStyleSheet(AppStyles.app_bar())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # Título
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("app_bar_title")
        self.lbl_title.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(self.lbl_title)
        layout.addStretch()

        # Botão Executar
        if show_run:
            self.btn_run = QPushButton("Executar")
            self.btn_run.setObjectName("app_bar_btn_run")
            layout.addWidget(self.btn_run)

        # Botão Info
        if show_info:
            self.btn_info = QPushButton("Info")
            self.btn_info.setObjectName("app_bar_btn_info")
            layout.addWidget(self.btn_info)

        # Botão Fechar
        if show_close:
            self.btn_close = QPushButton("✕")
            self.btn_close.setObjectName("app_bar_btn_close")
            self.btn_close.clicked.connect(self._on_close_clicked)
            layout.addWidget(self.btn_close)

    def set_title(self, title: str):
        """Atualiza o título exibido."""
        self.lbl_title.setText(title)

    def _on_close_clicked(self):
        """Fecha a janela pai."""
        if self.window():
            self.window().close()

    # ── Drag da janela ─────────────────────────────────────

    def _global_pos(self, event):
        try:
            return event.globalPosition().toPoint()  # Qt6
        except AttributeError:
            return event.globalPos()  # Qt5

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                self._global_pos(event)
                - self.window().frameGeometry().topLeft()
            )
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(self._global_pos(event) - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)