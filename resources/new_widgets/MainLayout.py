# -*- coding: utf-8 -*-
"""
Novo MainLayout — Sistema novo de layout principal.
Criado do zero, sem dependência do sistema antigo.
Usa AppStyles para estilos e inclui AppBarWidget.

Uso em BaseDialog:
    self.layout = MainLayout(self, title="Meu Plugin", enable_scroll=True)

    # Fundo quadriculado (padrão agora):
    self.layout = MainLayout(self, title="Meu Plugin")

    # Fundo sólido (comportamento antigo, opcional):
    self.layout = MainLayout(
        self, title="Meu Plugin",
        background_texture=BackgroundTexture.SOLID,
    )

REQUISITO EM AppStyles:
    Este arquivo espera que exista um método
    `AppStyles.main_application_square()` retornando um QSS equivalente
    a `main_application()` porém SEM background (só borda/border-radius),
    já que o fundo quadriculado é pintado manualmente via QPainter.
    Ver sugestão de implementação e lista de tokens no final deste arquivo.
"""

import random
from enum import Enum

from qgis.PyQt.QtWidgets import (
    QVBoxLayout, QFrame, QApplication, QWidget, QLayout,
)
from qgis.PyQt.QtCore import Qt, QPoint
from qgis.PyQt.QtGui import (
    QCursor, QPainter, QColor, QPainterPath, QLinearGradient, QBrush,
)
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


def _qt_antialiasing_hint():
    try:
        return QPainter.RenderHint.Antialiasing  # Qt6
    except AttributeError:
        return QPainter.Antialiasing  # Qt5


def _global_pos(event):
    try:
        return event.globalPosition().toPoint()  # Qt6
    except AttributeError:
        return event.globalPos()  # Qt5


class BackgroundTexture(Enum):
    """
    Modo de textura de fundo do MainLayout (aplicado ao EdgeFrame).

    SOLID  -> comportamento original/atual: preenchimento sólido definido
              inteiramente pelo QSS de AppStyles.main_application().
    SQUARE -> fundo quadriculado (grid), pintado manualmente no
              paintEvent do EdgeFrame, inspirado no CheckeredBackground.
    """
    SOLID = "solid"
    SQUARE = "square"


class EdgeFrame(QFrame):
    """QFrame que notifica o MainLayout quando redimensionado.

    Também é responsável por pintar a textura de fundo (SOLID ou SQUARE)
    quando configurada via set_background_texture().
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._owner_layout = None

        # ── Textura de fundo ────────────────────────────────────
        # Apenas guarda o estado inicial; NÃO aplica stylesheet aqui.
        # Quem decide e aplica é MainLayout, via set_background_texture(),
        # chamado logo após setObjectName("main_container") — exatamente
        # na mesma ordem/forma do código original, garantindo que o modo
        # SOLID fique 100% idêntico ao comportamento antigo.
        self._texture = BackgroundTexture.SQUARE
        self._cell_variations = {}  # cache das variações de tom do grid

    def set_owner_layout(self, layout):
        self._owner_layout = layout

    # ── Textura de fundo ────────────────────────────────────────

    def set_background_texture(self, texture: BackgroundTexture):
        """Troca o modo de textura de fundo e força repintura."""
        self._texture = texture
        self._cell_variations = {}
        self._refresh_stylesheet()
        self.update()

    def background_texture(self) -> "BackgroundTexture":
        return self._texture

    def _refresh_stylesheet(self):
        """
        Aplica o QSS correto para a textura atual. Sem gambiarra de
        concatenar/override de string: cada modo usa seu próprio método
        dedicado em AppStyles.

        - SOLID  -> AppStyles.main_application()
                    (comportamento 100% original, background sólido no QSS)
        - SQUARE -> AppStyles.main_application_square()
                    (novo método a ser criado em AppStyles — mesma borda/
                    border-radius, porém SEM background, pois o grid é
                    pintado manualmente em _paint_square_texture())
        """
        if self._texture == BackgroundTexture.SQUARE:
            self.setStyleSheet(AppStyles.main_application_square())
        else:
            self.setStyleSheet(AppStyles.main_application())

    def resizeEvent(self, event):
        # Recalcula variações de cor do grid quando o tamanho muda
        self._cell_variations = {}
        super().resizeEvent(event)
        if self._owner_layout:
            try:
                self._owner_layout._update_border_geometries()
            except Exception:
                pass

    def paintEvent(self, event):
        if self._texture == BackgroundTexture.SQUARE:
            self._paint_square_texture()
        # No modo SOLID isso é idêntico ao comportamento original: o
        # próprio Qt/QSS desenha o fundo sólido + borda + border-radius,
        # pois paintEvent não faz nada além de chamar super() aqui.
        # No modo SQUARE, o QSS (main_application_square) já deixa o
        # background transparente, então isso só desenha a borda por
        # cima do grid pintado manualmente acima.
        super().paintEvent(event)

    def _paint_square_texture(self):
        """
        Pinta um fundo quadriculado (grid) dentro do EdgeFrame, respeitando
        o border-radius configurado, de forma equivalente ao
        CheckeredBackground de referência — porém sem valores de cor fixos:
        tudo é derivado de tokens de AppStyles._get_theme(), com fallbacks
        seguros caso os tokens ainda não existam no tema.

        NOVOS TOKENS DE TEMA (adicionar em AppStyles quando conveniente):
            BACKGROUND_SQUARE_CELL_SIZE     (int)   -> tamanho da célula
            BACKGROUND_SQUARE_BASE_COLOR    (str)   -> cor base (hex)
            BACKGROUND_SQUARE_LINE_ALPHA    (int)   -> alpha das linhas do grid (0-255)
            BACKGROUND_SQUARE_GRADIENT_ALPHA(int)   -> alpha máx. do gradiente de profundidade (0-255)
            BACKGROUND_BORDER_RADIUS        (int)   -> raio usado para recortar o grid nas bordas
        Até lá, valores padrão abaixo são usados como fallback.
        """
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        theme = AppStyles._get_theme()

        cell_size = getattr(theme, "BACKGROUND_SQUARE_CELL_SIZE", 60)
        border_radius = getattr(theme, "BACKGROUND_BORDER_RADIUS", 12)
        base_color_hex = getattr(theme, "BACKGROUND_SQUARE_BASE_COLOR", "#0a2f2b")
        line_alpha = getattr(theme, "BACKGROUND_SQUARE_LINE_ALPHA", 15)
        gradient_alpha = getattr(theme, "BACKGROUND_SQUARE_GRADIENT_ALPHA", 90)

        painter = QPainter(self)
        painter.setRenderHint(_qt_antialiasing_hint())

        # Recorta a pintura para respeitar o border-radius do frame
        clip_path = QPainterPath()
        clip_path.addRoundedRect(0, 0, w, h, border_radius, border_radius)
        painter.setClipPath(clip_path)

        # 1) Cor base
        base_color = QColor(base_color_hex)
        painter.fillRect(0, 0, w, h, base_color)

        # 2) Grid quadriculado com variações sutis de tom (derivadas da
        #    cor base, sem precisar de múltiplos tokens de cor)
        variation_colors = [
            base_color,
            base_color.lighter(120),
            base_color.darker(120),
            base_color.lighter(140),
        ]
        weights = [70, 15, 10, 5]

        cols = int(w // cell_size) + 2
        rows = int(h // cell_size) + 2

        for row in range(rows):
            for col in range(cols):
                key = (row, col)
                if key not in self._cell_variations:
                    self._cell_variations[key] = random.choices(
                        variation_colors, weights=weights, k=1
                    )[0]
                color = self._cell_variations[key]
                x = col * cell_size
                y = row * cell_size
                painter.fillRect(x, y, cell_size, cell_size, color)

        # 3) Linhas do grid (sutis)
        grid_pen_color = QColor(255, 255, 255, line_alpha)
        painter.setPen(grid_pen_color)
        for col in range(cols + 1):
            x = col * cell_size
            painter.drawLine(x, 0, x, h)
        for row in range(rows + 1):
            y = row * cell_size
            painter.drawLine(0, y, w, y)

        # 4) Gradiente por cima para dar profundidade (mais escuro nas bordas)
        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
        gradient.setColorAt(0.5, QColor(0, 0, 0, max(0, int(gradient_alpha * 0.22))))
        gradient.setColorAt(1.0, QColor(0, 0, 0, gradient_alpha))
        painter.fillRect(0, 0, w, h, QBrush(gradient))

        painter.end()


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

    Textura de fundo (novo):
        self.layout = MainLayout(
            self, title="Título",
            background_texture=BackgroundTexture.SQUARE,
        )
        # ou trocar depois:
        self.layout.set_background_texture(BackgroundTexture.SQUARE)
    """

    def __init__(
        self,
        parent=None,
        enable_scroll: bool = False,
        title: str = "Cadmus",
        show_run: bool = False,
        show_info: bool = False,
        show_close: bool = True,
        background_texture: BackgroundTexture = BackgroundTexture.SOLID,
    ):
        super().__init__(parent)

        self.setContentsMargins(0,0, 0, 0)
        self.setSpacing(0)

        # Frame container visual
        self._frame = EdgeFrame(parent)
        self._frame.setObjectName("main_container")
        # Aplica a textura escolhida (isso já seleciona o QSS certo:
        # AppStyles.main_application() para SOLID ou
        # AppStyles.main_application_square() para SQUARE).
        self._frame.set_background_texture(background_texture)
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

    # ── Textura de fundo ────────────────────────────────────────

    def set_background_texture(self, texture: BackgroundTexture):
        """Troca o modo de textura de fundo (SOLID <-> SQUARE) em runtime."""
        self._frame.set_background_texture(texture)

    def background_texture(self) -> BackgroundTexture:
        return self._frame.background_texture()

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


# ═════════════════════════════════════════════════════════════════════
# PENDENTE EM AppStyles (adicionar manualmente)
# ═════════════════════════════════════════════════════════════════════
#
# 1) TOKENS NOVOS NO TEMA (classe de tema usada por AppStyles._get_theme()):
#
#    BACKGROUND_SQUARE_CELL_SIZE      : int   -> tamanho da célula do grid (px)
#    BACKGROUND_SQUARE_BASE_COLOR     : str   -> cor base do grid (hex, ex: "#0a2f2b")
#    BACKGROUND_SQUARE_LINE_ALPHA     : int   -> opacidade das linhas do grid (0-255)
#    BACKGROUND_SQUARE_GRADIENT_ALPHA : int   -> opacidade máx. do gradiente de
#                                                 profundidade nas bordas (0-255)
#    BACKGROUND_BORDER_RADIUS         : int   -> raio de borda (px). Usado tanto
#                                                 no recorte do grid (paintEvent)
#                                                 quanto no QSS de
#                                                 main_application_square(), para
#                                                 os dois baterem exatamente.
#
# 2) NOVO MÉTODO EM AppStyles (paralelo a main_application(), sem alterar o
#    método existente). Sugestão de implementação — ajuste border/cor de
#    borda conforme os tokens que main_application() já usa:
#
#    @staticmethod
#    def main_application_square():
#        """
#        Igual a main_application(), porém SEM background: usado quando
#        MainLayout está em BackgroundTexture.SQUARE, cujo fundo é pintado
#        manualmente via QPainter em EdgeFrame._paint_square_texture().
#        Border/border-radius devem ser mantidos para o frame continuar
#        com a mesma moldura visual do modo SOLID.
#        """
#        theme = AppStyles._get_theme()
#        return f"""
#            #main_container {{
#                background: transparent;
#                border-radius: {theme.BACKGROUND_BORDER_RADIUS}px;
#            }}
#        """
#
#    (Se main_application() já define border/border-width além do
#    border-radius, replique aqui também — só não inclua background/
#    background-color, pois isso é o que abre espaço para o grid aparecer.)
# ═════════════════════════════════════════════════════════════════════