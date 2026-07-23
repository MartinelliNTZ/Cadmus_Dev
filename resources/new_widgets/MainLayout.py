# -*- coding: utf-8 -*-
"""
Novo MainLayout — Sistema novo de layout principal.
Criado do zero, sem dependência do sistema antigo.
Usa AppStyles para estilos e inclui AppBarWidget.

Uso em BaseDialog:
    self.layout = MainLayout(self, title="Meu Plugin", enable_scroll=True)
"""

from qgis.PyQt.QtWidgets import (
    QVBoxLayout, QFrame, QApplication, QWidget, QLayout,
)
from qgis.PyQt.QtCore import Qt, QPoint
from qgis.PyQt.QtGui import QCursor
from typing import Optional
from ..styles.AppStyles import AppStyles
from .ScrollWidget import ScrollWidget
from .AppBarWidget import AppBarWidget


# Compatibilidade Qt5/Qt6
def _qt_wa_transparent():
    try:
        return Qt.WidgetAttribute.WA_TransparentForMouseEvents
    except AttributeError:
        return Qt.WA_TransparentForMouseEvents


def _global_pos(event):
    try:
        return event.globalPosition().toPoint()  # Qt6
    except AttributeError:
        return event.globalPos()  # Qt5


class EdgeFrame(QFrame):
    """QFrame que notifica o MainLayout quando redimensionado."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._owner_layout = None

    def set_owner_layout(self, layout):
        self._owner_layout = layout

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._owner_layout:
            try:
                self._owner_layout._update_border_geometries()
            except Exception:
                pass


class BorderHitWidget(QWidget):
    """Widget invisível nas bordas para captura de mouse (resize)."""

    def __init__(self, parent, edge: str, main_layout):
        super().__init__(parent)
        self._edge = edge
        self._layout = main_layout
        self.setMouseTracking(True)
        self.setAttribute(_qt_wa_transparent(), False)
        self.setStyleSheet("background: rgba(0,0,0,0); border: none;")

    def enterEvent(self, event):
        try:
            self._layout._update_cursor(self._edge)
        except Exception:
            pass

    def leaveEvent(self, event):
        try:
            self._layout._update_cursor(None)
            QApplication.restoreOverrideCursor()
        except Exception:
            pass

    def mousePressEvent(self, event):
        try:
            self._layout._start_resize_from_edge(event, self._edge)
            event.accept()
        except Exception:
            pass

    def mouseMoveEvent(self, event):
        try:
            if self._layout._resize_active:
                self._layout._perform_resize_move(event)
            else:
                self._layout._update_cursor(self._edge)
        except Exception:
            pass

    def mouseReleaseEvent(self, event):
        try:
            self._layout._end_resize()
            event.accept()
        except Exception:
            pass


class MainLayout(QVBoxLayout):
    """
    Layout principal dos diálogos Cadmus.

    ARQUITETURA:
    - QVBoxLayout externo (com margens para o border-radius)
    - EdgeFrame interno (container visual com estilo)
    - _inner_layout: SEM margens/espaçamento — contém apenas a AppBar
      (que assim ocupa 100% da largura do frame, colada nas bordas)
      e o _content_layout logo abaixo.
    - _content_layout: COM margem de 5px em todos os lados — é onde
      entram o ScrollWidget (se enable_scroll=True) e todos os widgets
      / layouts adicionados via addWidget/addLayout/add_items/etc.
    - BorderHitWidgets nas bordas para resize

    Uso em BaseDialog:
        self.layout = MainLayout(self, title="Título", enable_scroll=True)
        self.layout.addWidget(meu_widget)
    """

    def __init__(
        self,
        parent=None,
        enable_scroll: bool = False,
        title: str = "Cadmus",
        show_run: bool = False,
        show_info: bool = False,
        show_close: bool = True,
    ):
        super().__init__(parent)

        self.setContentsMargins(0,0, 0, 0)
        self.setSpacing(0)

        # Frame container visual
        self._frame = EdgeFrame(parent)
        self._frame.setObjectName("main_container")
        self._frame.setStyleSheet(AppStyles.main_application())
        self._frame.setMouseTracking(True)
        try:
            self._frame.set_owner_layout(self)
        except Exception:
            pass

        # Layout interno — SEM margens, a AppBar ocupa 100% do espaço
        self._inner_layout = QVBoxLayout(self._frame)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(0)

        # AppBar no topo, colada nas bordas (sem margem)
        self._app_bar = AppBarWidget(
            title=title,
            show_run=show_run,
            show_info=show_info,
            show_close=show_close,
            parent=parent,
        )
        self._inner_layout.insertWidget(0, self._app_bar)

        # Layout de conteúdo — COM margem interna de 5px. Tudo que for
        # adicionado depois (scroll, widgets, botões) passa por aqui.
        self._content_layout = QVBoxLayout()
        self._content_layout.setContentsMargins(5, 5, 5, 5)
        self._content_layout.setSpacing(
            AppStyles._get_theme().LAYOUT_VERTICAL_SPACING
        )
        self._inner_layout.addLayout(self._content_layout)

        # Scroll opcional — entra dentro do content_layout (com margem)
        self._scroll = None
        if enable_scroll:
            self._scroll = ScrollWidget(parent)
            self._content_layout.addWidget(self._scroll)

        # Adiciona frame ao layout principal
        super().addWidget(self._frame)

        # Resize handlers
        self._resize_border = 10
        self._resize_active = False
        self._resize_edge = None
        self._last_pos = None
        self._parent_dialog = parent

        self._borders = {}
        try:
            self._create_border_widgets()
            self._update_border_geometries()
        except Exception:
            pass

        if parent:
            parent.setMouseTracking(True)

    def set_appbar_title(self, title: str):
        """Atualiza o título da AppBar."""
        if self._app_bar:
            self._app_bar.set_title(title)

    def addWidget(self, widget, *args, **kwargs):
        """Adiciona widget ao layout (scroll ou content)."""
        if self._scroll is not None:
            self._scroll.addWidget(widget)
        else:
            self._content_layout.addWidget(widget, *args, **kwargs)

    def addLayout(self, layout, *args, **kwargs):
        """Adiciona layout ao layout (scroll ou content)."""
        if self._scroll is not None:
            self._scroll.addLayout(layout)
        else:
            self._content_layout.addLayout(layout, *args, **kwargs)

    def addStretch(self, *args, **kwargs):
        self._content_layout.addStretch(*args, **kwargs)

    def addSpacing(self, *args, **kwargs):
        self._content_layout.addSpacing(*args, **kwargs)

    def add_execution_buttons(self, buttons_widget):
        """
        Adiciona widget de botões de execução fixo na parte inferior,
        SEMPRE fora da área de scroll (se houver), mas ainda dentro
        do _content_layout (respeitando a margem de 5px).

        - Se scroll está habilitado: adiciona diretamente ao
          _content_layout após o scroll, SEM stretch (o scroll
          já ocupa o espaço disponível acima).
        - Se scroll está desabilitado: adiciona ao _content_layout
          após os demais widgets, com stretch antes para empurrar
          para baixo.
        - Adiciona um pequeno espaçamento (LAYOUT_VERTICAL_SPACING) após
          os botões para não colar na borda inferior.
        """
        # Stretch antes dos botões APENAS quando não há scroll
        # (com scroll, o scroll widget já ocupa o espaço disponível)
        if self._scroll is None:
            self._content_layout.addStretch()
        # Botões fixos no final (fora do scroll)
        self._content_layout.addWidget(buttons_widget)
        # Pequeno espaçamento após os botões para não colar na borda
        self._content_layout.addSpacing(
            AppStyles._get_theme().LAYOUT_VERTICAL_SPACING
        )

    def add_items(self, items):
        """
        Adiciona widgets e/ou layouts ao layout.

        Se scroll está habilitado, coleta todos os itens e os adiciona
        ao scroll como um único layout.

        Se scroll está desabilitado, adiciona ao _content_layout
        diretamente (respeitando a margem de 5px).

        Parameters
        ----------
        items : iterable
            Lista ou tupla contendo QLayout e/ou QWidget
        """
        if not items:
            return

        if self._scroll is not None:
            # Scroll habilitado: coleta itens em um layout e adiciona ao scroll
            container_layout = QVBoxLayout()
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(
                AppStyles._get_theme().LAYOUT_VERTICAL_SPACING
            )

            for item in items:
                if isinstance(item, QLayout):
                    container_layout.addLayout(item)
                elif isinstance(item, QWidget):
                    container_layout.addWidget(item)
                else:
                    raise TypeError(
                        f"Tipo inválido em MainLayout.add_items: {type(item)}"
                    )

            # Adiciona ao scroll
            self._scroll.add_layout_as_content(container_layout)
        else:
            # Scroll desabilitado: adiciona diretamente ao content_layout
            for item in items:
                if isinstance(item, QLayout):
                    self._content_layout.addLayout(item)
                elif isinstance(item, QWidget):
                    self._content_layout.addWidget(item)
                else:
                    raise TypeError(
                        f"Tipo inválido em MainLayout.add_items: {type(item)}"
                    )

            # Adiciona stretch ao final para evitar gaps quando sem scroll
            self._content_layout.addStretch()

    # ── Resize ──────────────────────────────────────────────────

    def _get_resize_edge(self, pos: QPoint) -> Optional[str]:
        if not self._parent_dialog:
            return None
        rect = self._parent_dialog.rect()
        b = self._resize_border
        if pos.x() < b and pos.y() < b:
            return "top-left"
        elif pos.x() > rect.width() - b and pos.y() < b:
            return "top-right"
        elif pos.x() < b and pos.y() > rect.height() - b:
            return "bottom-left"
        elif pos.x() > rect.width() - b and pos.y() > rect.height() - b:
            return "bottom-right"
        elif pos.x() < b:
            return "left"
        elif pos.x() > rect.width() - b:
            return "right"
        elif pos.y() < b:
            return "top"
        elif pos.y() > rect.height() - b:
            return "bottom"
        return None

    def _create_border_widgets(self):
        edges = [
            "left", "right", "top", "bottom",
            "top-left", "top-right", "bottom-left", "bottom-right",
        ]
        for e in edges:
            w = BorderHitWidget(self._frame, e, self)
            w.setObjectName(f"border_hit_{e}")
            w.setAttribute(_qt_wa_transparent(), False)
            w.setMouseTracking(True)
            w.raise_()
            self._borders[e] = w

    def _update_border_geometries(self):
        if not self._frame:
            return
        fw = self._frame.width()
        fh = self._frame.height()
        b = self._resize_border
        geo = {
            "left": (0, 0, b, fh),
            "right": (max(0, fw - b), 0, b, fh),
            "top": (0, 0, fw, b),
            "bottom": (0, max(0, fh - b), fw, b),
            "top-left": (0, 0, b, b),
            "top-right": (max(0, fw - b), 0, b, b),
            "bottom-left": (0, max(0, fh - b), b, b),
            "bottom-right": (max(0, fw - b), max(0, fh - b), b, b),
        }
        for edge, (x, y, w, h) in geo.items():
            if edge in self._borders:
                self._borders[edge].setGeometry(x, y, w, h)
                self._borders[edge].raise_()

    def _start_resize_from_edge(self, event, edge):
        self._resize_active = True
        self._resize_edge = edge
        self._last_pos = _global_pos(event)

    def _perform_resize_move(self, event):
        if not (self._resize_active and self._resize_edge and self._last_pos and self._parent_dialog):
            return
        delta = _global_pos(event) - self._last_pos
        new_rect = self._parent_dialog.geometry()
        if "top" in self._resize_edge:
            new_rect.setTop(new_rect.top() + delta.y())
        if "bottom" in self._resize_edge:
            new_rect.setBottom(new_rect.bottom() + delta.y())
        if "left" in self._resize_edge:
            new_rect.setLeft(new_rect.left() + delta.x())
        if "right" in self._resize_edge:
            new_rect.setRight(new_rect.right() + delta.x())
        if new_rect.width() >= self._parent_dialog.minimumWidth() and new_rect.height() >= self._parent_dialog.minimumHeight():
            self._parent_dialog.setGeometry(new_rect)
            self._last_pos = _global_pos(event)

    def _end_resize(self):
        self._resize_active = False
        self._resize_edge = None
        self._last_pos = None
        self._update_cursor(None)
        QApplication.restoreOverrideCursor()

    def _update_cursor(self, edge: Optional[str]):
        cursors = {
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "top-left": Qt.CursorShape.SizeFDiagCursor,
            "top-right": Qt.CursorShape.SizeBDiagCursor,
            "bottom-left": Qt.CursorShape.SizeBDiagCursor,
            "bottom-right": Qt.CursorShape.SizeFDiagCursor,
        }
        if self._parent_dialog:
            cur = cursors.get(edge, Qt.CursorShape.ArrowCursor)
            self._parent_dialog.setCursor(QCursor(cur))

    # ── Métodos delegados do BaseDialog ─────────────────────────

    def handle_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            mapped_pos = None
            if self._parent_dialog:
                try:
                    mapped = self._parent_dialog.mapFromGlobal(_global_pos(event))
                    mapped_pos = QPoint(mapped.x(), mapped.y())
                except Exception:
                    mapped_pos = event.pos()
            else:
                mapped_pos = event.pos()
            edge = self._get_resize_edge(mapped_pos)
            if edge:
                self._resize_active = True
                self._resize_edge = edge
                self._last_pos = _global_pos(event)
                event.accept()
                return True
        return False

    def handle_mouse_move(self, event):
        mapped_pos = None
        if self._parent_dialog:
            try:
                mapped = self._parent_dialog.mapFromGlobal(_global_pos(event))
                mapped_pos = QPoint(mapped.x(), mapped.y())
            except Exception:
                mapped_pos = event.pos()
        else:
            mapped_pos = event.pos()
        edge = self._get_resize_edge(mapped_pos)
        self._update_cursor(edge)
        if self._resize_active and self._resize_edge and self._last_pos and self._parent_dialog:
            delta = _global_pos(event) - self._last_pos
            new_rect = self._parent_dialog.geometry()
            if "top" in self._resize_edge:
                new_rect.setTop(new_rect.top() + delta.y())
            if "bottom" in self._resize_edge:
                new_rect.setBottom(new_rect.bottom() + delta.y())
            if "left" in self._resize_edge:
                new_rect.setLeft(new_rect.left() + delta.x())
            if "right" in self._resize_edge:
                new_rect.setRight(new_rect.right() + delta.x())
            if new_rect.width() >= self._parent_dialog.minimumWidth() and new_rect.height() >= self._parent_dialog.minimumHeight():
                self._parent_dialog.setGeometry(new_rect)
                self._last_pos = _global_pos(event)

    def handle_mouse_release(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._resize_active:
            self._resize_active = False
            self._resize_edge = None
            self._last_pos = None
            self._update_cursor(None)
            event.accept()
            return True
        return False