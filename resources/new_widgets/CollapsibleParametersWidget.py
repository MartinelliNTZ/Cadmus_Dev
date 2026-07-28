# -*- coding: utf-8 -*-
"""
CollapsibleParametersWidget — Seção colapsável com header gradiente via paintEvent.
===================================================================================
Widget raiz (sem versão grid). Segue o contrato do novo sistema:
- paintEvent com QPainter + QLinearGradient usando CORES GENÉRICAS DO TEMA
- Header clicável com ícone ▶/▼
- Conteúdo mostra/esconde
- AppStyles + tokens do BaseTheme

Uso em plugins:
    coll = CollapsibleParametersWidget(
        title="Configurações Avançadas",
        expanded_by_default=False,
        parent=self,
    )
    coll.add_content_widget(my_widget)
    self.layout.addWidget(coll)
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPainter, QLinearGradient, QColor, QPen

from ..styles.AppStyles import AppStyles


def _parse_rgba(rgba_str: str) -> QColor:
    """Converte 'rgba(r, g, b, a)' para QColor."""
    rgba_str = rgba_str.replace("rgba(", "").replace(")", "")
    parts = [int(x.strip()) for x in rgba_str.split(",")]
    return QColor(*parts)


class _CollapsibleHeader(QFrame):
    """Header com gradiente via paintEvent para CollapsibleParametersWidget."""

    def __init__(self, parent_widget: "CollapsibleParametersWidget", parent=None):
        super().__init__(parent)
        self._parent_widget = parent_widget
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(32)
        self.mousePressEvent = self._on_click

    def _on_click(self, event=None):
        self._parent_widget.set_expanded(not self._parent_widget._is_expanded)

    def paintEvent(self, event):
        """Pinta gradiente horizontal no header usando cores genéricas do tema."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        theme = AppStyles._get_theme()
        rect = self.rect()

        # Usa cores genéricas do tema com alpha para o gradiente
        # Normal: tons de NEUTRAL com baixa opacidade
        # Hover: tons de PRIMARY com baixa opacidade
        if self._parent_widget._hovered:
            base_hex = theme.COLOR_PRIMARY
            alpha = 40
        else:
            base_hex = theme.COLOR_NEUTRAL
            alpha = 30

        # Cria duas variações: uma levemente mais clara para o start
        start_rgba = theme.rgba(base_hex, alpha)
        end_rgba = theme.rgba(base_hex, alpha + 20)

        start_color = _parse_rgba(start_rgba)
        end_color = _parse_rgba(end_rgba)

        # Gradiente horizontal
        gradient = QLinearGradient(rect.topLeft().toPointF(), rect.topRight().toPointF())
        gradient.setColorAt(0.0, start_color)
        gradient.setColorAt(1.0, end_color)

        # Preenche com gradiente
        painter.fillRect(rect, gradient)

        # Borda inferior sutil
        border_color = QColor(theme.COLOR_BORDER_DEFAULT)
        pen = QPen(border_color, 1)
        painter.setPen(pen)
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        painter.end()


class CollapsibleParametersWidget(QWidget):
    """
    Seção colapsável com header clicável e gradiente via paintEvent.

    - paintEvent: gradiente horizontal no header usando CORES GENÉRICAS DO TEMA
    - Header: clique alterna expandido/recolhido com ícone ▶/▼
    - Conteúdo: mostra/esconde
    - Estilos: AppStyles + tokens do BaseTheme

    Parâmetros
    ----------
    title : str, optional
        Título exibido no header.
    expanded_by_default : bool, optional
        Se True, inicia expandido.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        title: str = "",
        expanded_by_default: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._title = title
        self._is_expanded = expanded_by_default
        self._hovered = False

        # Container para o conteúdo
        self._content_container = QFrame()
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(4)

        # Header com paintEvent
        self._header = _CollapsibleHeader(self)

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(10, 0, 10, 0)
        header_layout.setSpacing(6)

        self._icon_label = QLabel("▶" if not self._is_expanded else "▼")
        self._icon_label.setFixedWidth(14)
        header_layout.addWidget(self._icon_label)

        self._title_label = QLabel(self._title)
        header_layout.addWidget(self._title_label, 1)

        # Monta estrutura
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self._header)
        main_layout.addWidget(self._content_container)

        # Estado inicial do conteúdo
        self._content_container.setVisible(self._is_expanded)

        # Aplica estilos
        self._apply_styles()

        # Hover tracking
        self._header.enterEvent = lambda e: self._on_hover(True)
        self._header.leaveEvent = lambda e: self._on_hover(False)

    # ── API Pública ────────────────────────────────────────────────

    def add_content_widget(self, widget):
        """Adiciona widget ao conteúdo expandível."""
        self._content_layout.addWidget(widget)

    def add_content_layout(self, layout):
        """Adiciona layout ao conteúdo expandível."""
        self._content_layout.addLayout(layout)

    def set_expanded(self, expanded: bool):
        """Expande ou recolhe a seção."""
        if expanded == self._is_expanded:
            return
        self._is_expanded = expanded
        self._icon_label.setText("▼" if expanded else "▶")
        self._content_container.setVisible(expanded)
        self._header.update()

    def is_expanded(self) -> bool:
        """Retorna True se expandido."""
        return self._is_expanded

    # ── Eventos ────────────────────────────────────────────────────

    def _on_hover(self, hovered: bool):
        """Atualiza estado de hover para repaint do header."""
        self._hovered = hovered
        self._header.update()

    # ── Estilos ────────────────────────────────────────────────────

    def _apply_styles(self):
        """Aplica estilos."""
        combined = self._get_global_style() + self._specific_style()
        self.setStyleSheet(combined)

        theme = AppStyles._get_theme()

        # Estilo do header é via paintEvent, mas precisa de fundo transparente
        self._header.setStyleSheet("background: transparent; border: none;")

        # Estilo do título
        self._title_label.setStyleSheet(
            f"color: {theme.COLOR_TEXT_PRIMARY};"
            f"font-size: {theme.FONT_SIZE_SECTION_TITLE};"
            f"font-weight: bold;"
            f"background: transparent;"
            f"border: none;"
            f"padding: 0px;"
        )
        self._icon_label.setStyleSheet(
            f"color: {theme.COLOR_TEXT_PRIMARY};"
            f"background: transparent;"
            f"border: none;"
            f"font-size: 10pt;"
        )

        # Estilo do container de conteúdo
        self._content_container.setStyleSheet(
            f"background: transparent;"
            f"border: none;"
            f"padding: 4px 0px 0px 0px;"
        )

    def _get_global_style(self) -> str:
        return ""

    def _specific_style(self) -> str:
        return ""