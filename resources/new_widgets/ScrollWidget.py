# -*- coding: utf-8 -*-
"""
ScrollWidget — QScrollArea com estilo AppStyles.
Criado do zero para o novo sistema.
"""

from qgis.PyQt.QtWidgets import QScrollArea, QWidget
from qgis.PyQt.QtCore import Qt
from ..styles.AppStyles import AppStyles


class ScrollWidget(QScrollArea):
    """
    QScrollArea com estilo AppStyles.

    Propaga eventos de mouse para permitir detecção de bordas e resize.

    Uso:
        scroll = ScrollWidget(parent=self)
        scroll.setWidget(content_widget)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet(AppStyles.scroll_area())
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setFrameShadow(QScrollArea.Shadow.Plain)
        self.setMouseTracking(True)

    def set_content_widget(self, widget: QWidget):
        """Define o widget de conteúdo."""
        if widget:
            self.setWidget(widget)

    def add_layout_as_content(self, layout):
        """Cria container e adiciona layout como conteúdo."""
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