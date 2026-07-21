# -*- coding: utf-8 -*-
"""
GridExecutionButtons — Container de botões de execução configurável via dict.
Plugins USAM este widget.

Cada item do config dict define um botão com:
    label (obrigatório): texto do botão
    callback (obrigatório): função chamada ao clicar
    description (opcional): tooltip do botão
    is_run_button (opcional): bool, True destaca o botão como principal

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

from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout
from ..simple.SimpleButton import SimpleButton
from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles
from ...InstructionsManager import InstructionsManager
from ...IconManager import IconManager


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

        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        """Monta layout com botões na ordem: item3, item2, item1, close, config, info."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        if self._separator_top:
            outer_layout.addWidget(SeparatorWidget())

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(AppStyles._get_theme().LAYOUT_HORIZONTAL_SPACING)

        # Stretch à esquerda para alinhar à direita
        layout.addStretch()

        # 1. Itens do config em ordem reversa (item3, item2, item1)
        for btn_id, btn_config in reversed(list(self._config.items())):
            label = btn_config.get("label", btn_id)
            callback = btn_config.get("callback")
            description = btn_config.get("description", "")
            is_run = btn_config.get("is_run_button", False)

            btn = SimpleButton(text=label, parent=self)
            if description:
                btn.setToolTip(description)
            if callback:
                btn.clicked.connect(callback)

            if is_run:
                btn.setObjectName("btn_run_execution")
                btn.setStyleSheet(self._run_button_style())

            layout.addWidget(btn)

        # 2. Botão Close
        if self._enable_close:
            self.btn_close = SimpleButton(text="Fechar", parent=self)
            self.btn_close.clicked.connect(self._on_close_clicked)
            layout.addWidget(self.btn_close)

        # 3. Botão Config ⚙️ (entre close e info)
        if self._enable_config:
            self.btn_config = QPushButton()
            self.btn_config.setIcon(IconManager.icon(IconManager.INFO))
            self.btn_config.setToolTip("Configurações")
            self.btn_config.setFixedWidth(24)
            self.btn_config.setFixedHeight(24)
            if self._config_callback:
                self.btn_config.clicked.connect(self._config_callback)
            else:
                self.btn_config.clicked.connect(self._open_settings)
            layout.addWidget(self.btn_config)

        # 4. Botão Info
        if self._enable_info:
            self.btn_info = QPushButton()
            self.btn_info.setIcon(IconManager.icon(IconManager.INFO))
            self.btn_info.setToolTip("Informações")
            self.btn_info.setFixedWidth(24)
            self.btn_info.setFixedHeight(24)
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

    def _run_button_style(self) -> str:
        return f"""
        QPushButton#btn_run_execution {{
            font-weight: bold;
        }}
        """

    def _show_info(self, instructions_path: str):
        """Abre diálogo de informações (lazy import para evitar circular)."""
        from ....core.ui.info_dialog import InfoDialog
        dlg = InfoDialog(instructions_path, self.window())
        dlg.exec()

    def _on_close_clicked(self):
        """Fecha a janela pai."""
        if self.window():
            self.window().close()

    def _apply_styles(self):
        combined = self._specific_style()
        if combined:
            self.setStyleSheet(combined)

    def _specific_style(self) -> str:
        return ""

    # ── API pública ────────────────────────────────────────────

    def set_run_enabled(self, enabled: bool):
        """Habilita/desabilita o botão marcado como is_run_button."""
        for btn_id, btn_config in self._config.items():
            if btn_config.get("is_run_button", False):
                btn = self.findChild(SimpleButton)
                if btn and btn.text() == btn_config.get("label", btn_id):
                    btn.setEnabled(enabled)
                break