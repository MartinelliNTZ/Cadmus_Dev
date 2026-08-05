# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import QDialog, QSizeGrip

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
import os
from typing import Optional
from ..resources.widgets.MainLayout import MainLayout
from ..resources.widgets.MainLayout import MainLayout as MainLayoutOld


# Compatibilidade Qt5/Qt6: Qt5 usa Qt.{attr}, Qt6 usa Qt.WindowType.{attr}
def _qt_window_type(name):
    try:
        return getattr(Qt.WindowType, name)
    except AttributeError:
        return getattr(Qt, name)


def _qt_widget_attr(name):
    try:
        return getattr(Qt.WidgetAttribute, name)
    except AttributeError:
        return getattr(Qt, name)


class BaseDialog(QDialog):
    """Base para diálogos, com métodos comuns e integração com iface e logger."""

    layout = None
    logger = None

    def _build_ui(
        self,
        title: Optional[str] = None,
        icon_path: Optional[str] = "cadmus_icon.ico",
        enable_scroll: bool = True,
        minimum_size=(300, 300),
        old = False,
        **kwargs,
    ):
        """Constrói a interface do plugin.
        Recebe: title (str|None), icon_path (str), instructions_file (str), enable_scroll (bool).
        ARQUITETURA (MainLayout encapsula scroll + appbar):
        - MainLayout cria AppBarWidget e ScrollWidget internamente
        - Plugin apenas atribui self.layout = MainLayout()
        - Responsabilidade única: MainLayout gerencia appbar + scroll, plugin usa addWidget()
        """
        if title is not None:
            self.PLUGIN_NAME = title
        self.set_layout(
            enable_scroll=enable_scroll,
            icon_path=icon_path,
            title=self.PLUGIN_NAME,
            minimum_size=minimum_size,
            old=old,
        )

    def set_layout(
            self,
            enable_scroll=True,
            icon_path=None,
            title="Cadmus",
            minimum_size=(300, 300),
            old=False,
        ):
            """Define o layout principal do plugin usando o novo MainLayout."""
            self.logger.debug(f"Construindo UI para plugin: {self.PLUGIN_NAME}")

            # Flags e atributos de janela precisam ser setados ANTES de criar
            # o MainLayout/EdgeFrame, para que a transparência seja aplicada
            # corretamente em toda a hierarquia de widgets filhos.
            self.setWindowFlags(
                _qt_window_type("Dialog") | _qt_window_type("FramelessWindowHint")
            )
            self.setAttribute(_qt_widget_attr("WA_TranslucentBackground"), True)
            # Reforça: o QDialog em si não pode pintar nenhum fundo opaco,
            # senão ele "vaza" atrás do border-radius do #main_container.
            self.setStyleSheet("QDialog { background: transparent; }")

            if old:
                self.layout = MainLayoutOld(
                    self,
                    enable_scroll=enable_scroll,
                    title=title,
                )
            else:
                self.layout = MainLayout(
                    self,
                    enable_scroll=enable_scroll,
                    title=title,
                )

            self.setMinimumSize(*minimum_size)

            # Size grip (resize visual indicator)
            self.size_grip = QSizeGrip(self.layout._frame)
            self.size_grip.setFixedSize(16, 16)
            self.layout.addWidget(
                self.size_grip,
                alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
            )

            # Ícone
            icon_path = os.path.join(
                os.path.dirname(__file__), "..", "resources", "icons", icon_path
            )
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                self.logger.debug(f"Ícone carregado de: {icon_path}")
    def mousePressEvent(self, event):
        """Delega evento de mouse para detecção de bordas e início de resize do MainLayout."""
        if self.layout and hasattr(self.layout, "handle_mouse_press"):
            if self.layout.handle_mouse_press(event):
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Delega evento de mouse para atualização de cursor e resize do MainLayout."""
        if self.layout and hasattr(self.layout, "handle_mouse_move"):
            self.layout.handle_mouse_move(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Delega evento de mouse para finalização de resize do MainLayout."""
        if self.layout and hasattr(self.layout, "handle_mouse_release"):
            if self.layout.handle_mouse_release(event):
                return
        super().mouseReleaseEvent(event)

    def _load_prefs(self):
        """Carrega preferências do plugin.

        Recebe: None.
        Retorna: None.
        Faz: carrega preferências do armazenamento persistente usando TOOL_KEY.
        """