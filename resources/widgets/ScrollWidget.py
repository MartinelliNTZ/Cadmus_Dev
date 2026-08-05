# -*- coding: utf-8 -*-
"""
ScrollWidget — QScrollArea com estilo AppStyles.
Criado do zero para o novo sistema.
"""

from qgis.PyQt.QtWidgets import QScrollArea, QWidget, QVBoxLayout
from qgis.PyQt.QtCore import Qt
from ..styles.AppStyles import AppStyles


class ScrollWidget(QScrollArea):
    """
    QScrollArea com estilo AppStyles.

    Suporta adição incremental de widgets via addWidget().
    Mantém um widget container interno com QVBoxLayout acumulativo.

    Propaga eventos de mouse para permitir detecção de bordas e resize.

    Uso:
        scroll = ScrollWidget(parent=self)
        scroll.addWidget(widget1)
        scroll.addWidget(widget2)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Widget container interno com layout acumulativo
        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(AppStyles._get_theme().LAYOUT_VERTICAL_SPACING)

        self.setWidgetResizable(True)
        self.setStyleSheet(AppStyles.scroll_area())
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setFrameShadow(QScrollArea.Shadow.Plain)
        self.setMouseTracking(True)

        # Define o container como widget do scroll area
        self.setWidget(self._container)

    def addWidget(self, widget: QWidget):
        """Adiciona widget ao layout interno do scroll."""
        self._layout.addWidget(widget)

    def addLayout(self, layout):
        """Adiciona layout ao layout interno do scroll."""
        self._layout.addLayout(layout)

    def addStretch(self, *args, **kwargs):
        """Adiciona stretch ao layout interno do scroll."""
        self._layout.addStretch(*args, **kwargs)

    def set_content_widget(self, widget: QWidget):
        """Define o widget de conteúdo (substitui tudo)."""
        if widget:
            self.setWidget(widget)

    def add_layout_as_content(self, layout):
        """Cria container e adiciona layout como conteúdo (substitui tudo)."""
        container = QWidget()
        container.setLayout(layout)
        self.set_content_widget(container)

    def mouseMoveEvent(self, event):
        """Propaga eventos de mouse para parent (resize detection)."""
        super().mouseMoveEvent(event)
        if self.parent():
            self.parent().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """Propaga eventos de mouse para parent (resize detection)."""
        super().mousePressEvent(event)
        if self.parent():
            self.parent().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Propaga eventos de mouse para parent (resize detection)."""
        super().mouseReleaseEvent(event)
        if self.parent():
            self.parent().mouseReleaseEvent(event)