# -*- coding: utf-8 -*-
"""
GridExecutionButtons — Container de botões de execução configurável via dict.
Plugins USAM este widget.

Versão com botões modernos: QPushButton customizado com gradiente vertical
e QGraphicsDropShadowEffect, dando impressão de elevação/3D. Ao pressionar,
a sombra "recolhe" e o gradiente inverte, simulando o botão afundando —
feedback tátil visual.

Cada item do config dict define um botão com:
    label (obrigatório): texto do botão
    callback (obrigatório): função chamada ao clicar
    description (opcional): tooltip do botão
    is_run_button (opcional): bool, True destaca o botão como principal
        (gradiente na cor primária, mais proeminente)

Botões built-in:
    enable_close_button=True → adiciona botão Fechar
    enable_config_button=True → adiciona botão Config ⚙️ (abre SettingsPlugin)
    enable_info=True → adiciona botão Info (usa tool_key + InstructionsManager)

Ordem dos botões:
    item3, item2, item1(executar), close_button, config_button, info_button

Uso em plugins:
    actions = GridExecutionButtons(
        config={
            "run": {
                "label": "Executar",
                "description": "Inicia o processamento",
                "callback": self.execute_tool,
                "is_run_button": True,
            },
            "extra": {
                "label": "Abrir pasta",
                "description": "Abre o explorador de arquivos",
                "callback": self.open_folder,
            },
        },
        enable_close_button=True,
        enable_config_button=True,
        enable_info=True,
        tool_key=self.TOOL_KEY,
        separator_top=False,
        separator_bottom=False,
        parent=self,
    )
    layout.addWidget(actions)
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QGraphicsDropShadowEffect,
    QSizePolicy,
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt

from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles
from ...InstructionsManager import InstructionsManager
from ...IconManager import IconManager


# ── Compatibilidade Qt5 / Qt6 ──────────────────────────────────
# No Qt6 (PyQt6/PySide6) os enums viraram "scoped" (ex.: Qt.CursorShape.X,
# QSizePolicy.Policy.X). No Qt5 eles ficam soltos direto na classe
# (Qt.X, QSizePolicy.X). Resolvemos em tempo de import, com fallback,
# para o mesmo código rodar em ambas as versões sem alterações.
try:
    _CURSOR_POINTING_HAND = Qt.CursorShape.PointingHandCursor  # Qt6
except AttributeError:
    _CURSOR_POINTING_HAND = Qt.PointingHandCursor  # Qt5

try:
    _SIZE_POLICY_PREFERRED = QSizePolicy.Policy.Preferred  # Qt6
    _SIZE_POLICY_FIXED = QSizePolicy.Policy.Fixed  # Qt6
except AttributeError:
    _SIZE_POLICY_PREFERRED = QSizePolicy.Preferred  # Qt5
    _SIZE_POLICY_FIXED = QSizePolicy.Fixed  # Qt5


class ModernButton(QPushButton):
    """
    QPushButton sem borda, com gradiente de 3 stops (luz vindo de cima) +
    sombra colorida (glow), dando efeito de elevação/3D real mesmo sobre
    fundo escuro (sombra preta se perde num fundo escuro, por isso usamos
    uma sombra com cor/alpha ao invés de preto puro).

    Cores fixas (hardcoded) — não dependem do ThemeManager, para garantir
    contraste e acabamento visual consistentes.

    Parâmetros
    ----------
    text : str
        Texto do botão.
    parent : QWidget, optional
    primary : bool, optional
        True → paleta azul vibrante (botão de destaque/executar).
        False → paleta neutra grafite (estilo secundário).
    round_icon : bool, optional
        True → botão circular pequeno (usado para ícones como config/info).
    """

    # Border-radius padrão — leve, só pra arredondar as pontas (mesmo valor
    # pra todos os botões, incluindo os de ícone; nada de círculo perfeito).
    _RADIUS = "6px"

    # Paleta primária (azul) — 3 stops: claro (luz) → médio → escuro (sombra própria)
    _PRIMARY_TOP = "#5FB4FF"
    _PRIMARY_MID = "#2E86F5"
    _PRIMARY_BOTTOM = "#0B5AC9"
    _PRIMARY_HOVER_TOP = "#7CC4FF"
    _PRIMARY_HOVER_MID = "#4A98FF"
    _PRIMARY_HOVER_BOTTOM = "#1468DB"
    _PRIMARY_PRESSED_TOP = "#0B5AC9"
    _PRIMARY_PRESSED_MID = "#0A4CA8"
    _PRIMARY_PRESSED_BOTTOM = "#083E8A"
    _PRIMARY_TEXT = "#FFFFFF"
    _PRIMARY_GLOW = QColor(20, 70, 160, 110)

    # Paleta neutra (grafite) — para botões secundários (Fechar, extras)
    _NEUTRAL_TOP = "#6A7280"
    _NEUTRAL_MID = "#484F5A"
    _NEUTRAL_BOTTOM = "#2C3138"
    _NEUTRAL_HOVER_TOP = "#7C8492"
    _NEUTRAL_HOVER_MID = "#59616D"
    _NEUTRAL_HOVER_BOTTOM = "#383E46"
    _NEUTRAL_PRESSED_TOP = "#2C3138"
    _NEUTRAL_PRESSED_MID = "#23272D"
    _NEUTRAL_PRESSED_BOTTOM = "#191C20"
    _NEUTRAL_TEXT = "#F0F1F3"
    _NEUTRAL_GLOW = QColor(10, 12, 16, 130)

    def __init__(
        self,
        text="",
        parent=None,
        primary: bool = False,
        round_icon: bool = False,
        object_name: str = None,
    ):
        super().__init__(text, parent)
        self._primary = primary
        self._round_icon = round_icon
        # object_name customizado (ex.: "btn_run_execution") permite que
        # código externo continue localizando/estilizando este botão por
        # nome; senão, gera um nome único (id do próprio objeto) só pra
        # garantir especificidade máxima no seletor QSS.
        self._object_name = object_name or f"modern_btn_{id(self)}"
        self.setObjectName(self._object_name)

        self.setCursor(_CURSOR_POINTING_HAND)
        self.setSizePolicy(_SIZE_POLICY_PREFERRED, _SIZE_POLICY_FIXED)
        self.setFlat(True)  # remove chrome nativo do estilo do SO

        if round_icon:
            self.setFixedSize(32, 32)
            self.setIconSize(self._icon_size())
        else:
            self.setMinimumHeight(36)

        # Sombra sutil (glow escuro/translúcido) — dá elevação sem "brilhar"
        # como um halo branco.
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow_blur_normal = 12
        self._shadow_blur_pressed = 4
        self._shadow_offset_normal = 3
        self._shadow_offset_pressed = 1
        self._shadow.setBlurRadius(self._shadow_blur_normal)
        self._shadow.setOffset(0, self._shadow_offset_normal)
        self._shadow.setColor(self._PRIMARY_GLOW if primary else self._NEUTRAL_GLOW)
        self.setGraphicsEffect(self._shadow)

        self.pressed.connect(self._on_pressed)
        self.released.connect(self._on_released)

        self._apply_style()

    @staticmethod
    def _icon_size():
        from qgis.PyQt.QtCore import QSize
        return QSize(16, 16)

    def _on_pressed(self):
        self._shadow.setBlurRadius(self._shadow_blur_pressed)
        self._shadow.setOffset(0, self._shadow_offset_pressed)

    def _on_released(self):
        self._shadow.setBlurRadius(self._shadow_blur_normal)
        self._shadow.setOffset(0, self._shadow_offset_normal)

    def _apply_style(self):
        if self._primary:
            top, mid, bottom = self._PRIMARY_TOP, self._PRIMARY_MID, self._PRIMARY_BOTTOM
            h_top, h_mid, h_bottom = self._PRIMARY_HOVER_TOP, self._PRIMARY_HOVER_MID, self._PRIMARY_HOVER_BOTTOM
            p_top, p_mid, p_bottom = self._PRIMARY_PRESSED_TOP, self._PRIMARY_PRESSED_MID, self._PRIMARY_PRESSED_BOTTOM
            text_color = self._PRIMARY_TEXT
        else:
            top, mid, bottom = self._NEUTRAL_TOP, self._NEUTRAL_MID, self._NEUTRAL_BOTTOM
            h_top, h_mid, h_bottom = self._NEUTRAL_HOVER_TOP, self._NEUTRAL_HOVER_MID, self._NEUTRAL_HOVER_BOTTOM
            p_top, p_mid, p_bottom = self._NEUTRAL_PRESSED_TOP, self._NEUTRAL_PRESSED_MID, self._NEUTRAL_PRESSED_BOTTOM
            text_color = self._NEUTRAL_TEXT

        padding = "0px" if self._round_icon else "7px 22px"

        # Seletor por #objectName: especificidade máxima, garante que nenhum
        # stylesheet global (aplicado num ancestral) sobrescreva o border-radius
        # ou o "border: none" deste botão especificamente.
        sel = f"QPushButton#{self._object_name}"

        self.setStyleSheet(f"""
            {sel} {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {top}, stop:0.5 {mid}, stop:1 {bottom});
                color: {text_color};
                border: none;
                border-radius: {self._RADIUS};
                padding: {padding};
                font-weight: 600;
                font-size: 12px;
            }}
            {sel}:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {h_top}, stop:0.5 {h_mid}, stop:1 {h_bottom});
            }}
            {sel}:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {p_top}, stop:0.5 {p_mid}, stop:1 {p_bottom});
            }}
            {sel}:disabled {{
                background: #3A3D42;
                color: #8A8D93;
            }}
        """)


class GridExecutionButtons(QWidget):
    """
    Container de botões de execução configurável via dict.

    Parâmetros
    ----------
    config : dict, optional
        Dicionário onde cada chave é identificador do botão.
        Cada valor é um dict com:
            - "label" (obrigatório): texto do botão
            - "callback" (obrigatório): função chamada ao clicar
            - "description" (opcional): tooltip do botão
            - "is_run_button" (opcional): bool, True para destaque visual
    enable_close_button : bool, optional
        Se True, adiciona botão Fechar.
    enable_config_button : bool, optional
        Se True, adiciona botão Config ⚙️ (abre SettingsPlugin por padrão).
    config_callback : callable, optional
        Callback customizado para botão Config. Se None, abre SettingsPlugin.
    enable_info : bool, optional
        Se True, adiciona botão Info (usa tool_key para InstructionsManager).
    tool_key : str, optional
        ToolKey usada pelo botão Info para exibir instruções.
    separator_top : bool, optional
        Adiciona separador acima do widget.
    separator_bottom : bool, optional
        Adiciona separador abaixo do widget.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        config: dict = None,
        enable_close_button: bool = True,
        enable_config_button: bool = False,
        config_callback: callable = None,
        enable_info: bool = False,
        tool_key: str = None,
        separator_top: bool = False,
        separator_bottom: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._config = config or {}
        self._tool_key = tool_key
        self._enable_close = enable_close_button
        self._enable_config = enable_config_button
        self._config_callback = config_callback
        self._enable_info = enable_info
        self._separator_top = separator_top
        self._separator_bottom = separator_bottom

        self._run_button = None  # referência direta ao botão is_run_button

        self._build_ui()

    def _build_ui(self):
        """Monta layout com botões na ordem: item3, item2, item1, close, config, info."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        if self._separator_top:
            outer_layout.addWidget(SeparatorWidget())

        layout = QHBoxLayout()
        # Margens não-zero: a sombra (QGraphicsDropShadowEffect) precisa de
        # espaço "livre" ao redor do botão pra não ser cortada pelo container.
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(AppStyles._get_theme().LAYOUT_HORIZONTAL_SPACING)

        # Stretch à esquerda para alinhar à direita
        layout.addStretch()

        # 1. Itens do config em ordem reversa (item3, item2, item1)
        for btn_id, btn_config in reversed(list(self._config.items())):
            label = btn_config.get("label", btn_id)
            callback = btn_config.get("callback")
            description = btn_config.get("description", "")
            is_run = btn_config.get("is_run_button", False)

            btn = ModernButton(
                text=label,
                parent=self,
                primary=is_run,
                object_name="btn_run_execution" if is_run else None,
            )
            if description:
                btn.setToolTip(description)
            if callback:
                btn.clicked.connect(callback)

            if is_run:
                self._run_button = btn

            layout.addWidget(btn)

        # 2. Botão Close
        if self._enable_close:
            self.btn_close = ModernButton(text="Fechar", parent=self, primary=False)
            self.btn_close.clicked.connect(self._on_close_clicked)
            self.btn_close.setToolTip("Fecha a janela atual")
            layout.addWidget(self.btn_close)

        # 3. Botão Config ⚙️ (entre close e info)
        if self._enable_config:
            self.btn_config = ModernButton(parent=self, primary=False, round_icon=True)
            self.btn_config.setIcon(IconManager.icon(IconManager.CONFIG3))
            self.btn_config.setToolTip("Abre as configurações do plugin")
            if self._config_callback:
                self.btn_config.clicked.connect(self._config_callback)
            else:
                self.btn_config.clicked.connect(self._open_settings)
            layout.addWidget(self.btn_config)

        # 4. Botão Info
        if self._enable_info:
            self.btn_info = ModernButton(parent=self, primary=False, round_icon=True)
            self.btn_info.setIcon(IconManager.icon(IconManager.INFO))
            self.btn_info.setToolTip("Exibe instruções e informações do plugin")
            if self._tool_key:
                instructions_path = InstructionsManager.get(self._tool_key)
                self.btn_info.clicked.connect(
                    lambda: self._show_info(instructions_path)
                )
            else:
                self.btn_info.setVisible(False)
            layout.addWidget(self.btn_info)

        outer_layout.addLayout(layout)

        if self._separator_bottom:
            outer_layout.addWidget(SeparatorWidget())

    def _open_settings(self):
        """Abre o SettingsPlugin (lazy import para evitar circular)."""
        from qgis.core import QgsApplication
        from ....plugins.SettingsPlugin import run as run_settings

        window = self.window()
        iface = None
        for attr in ("iface", "_iface"):
            if hasattr(window, attr):
                iface = getattr(window, attr)
                break
        if iface is None:
            app = QgsApplication.instance()
            if app and hasattr(app, "activeInstance"):
                iface = app.activeInstance().mainWindow()
        if iface:
            dlg = run_settings(iface)
            dlg.show()

    def _show_info(self, instructions_path: str):
        """Abre diálogo de informações (lazy import para evitar circular)."""
        from ....core.ui.info_dialog import InfoDialog
        dlg = InfoDialog(instructions_path, self.window())
        dlg.exec()

    def _on_close_clicked(self):
        """Fecha a janela pai."""
        if self.window():
            self.window().close()

    # ── API pública ────────────────────────────────────────────

    def set_run_enabled(self, enabled: bool):
        """Habilita/desabilita o botão marcado como is_run_button."""
        if self._run_button:
            self._run_button.setEnabled(enabled)