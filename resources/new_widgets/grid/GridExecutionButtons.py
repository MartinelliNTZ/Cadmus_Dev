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
    enable_info=True → adiciona botão Info (usa tool_key + InstructionsManager)

Ordem dos botões (inversa):
    config_item_N, ..., config_item_1(executar), close_button, info_button

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
        Se True, adiciona botão Fechar ao final.
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
        self._enable_info = enable_info
        self._separator_top = separator_top
        self._separator_bottom = separator_bottom

        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        """Monta layout com botões na ordem inversa."""
        # Layout externo para separadores
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Separador top
        if self._separator_top:
            outer_layout.addWidget(SeparatorWidget())

        # Layout interno dos botões
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(AppStyles._get_theme().LAYOUT_HORIZONTAL_SPACING)

        # Botão Info (sempre primeiro na ordem, mas visualmente à esquerda)
        if self._enable_info:
            self.btn_info = QPushButton("?")
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

        # Botão Close
        if self._enable_close:
            self.btn_close = SimpleButton(text="Fechar", parent=self)
            self.btn_close.clicked.connect(self._on_close_clicked)
            layout.addWidget(self.btn_close)

        # Itens do config em ordem inversa
        # Último item do dict aparece primeiro (mais à direita no layout)
        items = list(self._config.items())

        for btn_id, btn_config in reversed(items):
            label = btn_config.get("label", btn_id)
            callback = btn_config.get("callback")
            description = btn_config.get("description", "")
            is_run = btn_config.get("is_run_button", False)

            btn = SimpleButton(text=label, parent=self)
            if description:
                btn.setToolTip(description)
            if callback:
                btn.clicked.connect(callback)

            # Botão run tem destaque visual
            if is_run:
                btn.setObjectName("btn_run_execution")
                btn.setStyleSheet(self._run_button_style())

            layout.addWidget(btn)

        layout.addStretch()

        # Adiciona layout interno ao outer
        outer_layout.addLayout(layout)

        # Separador bottom
        if self._separator_bottom:
            outer_layout.addWidget(SeparatorWidget())

    def _run_button_style(self) -> str:
        """Estilo especial para o botão executar."""
        return f"""
        QPushButton#btn_run_execution {{
            font-weight: bold;
        }}
        """

    def _show_info(self, instructions_path: str):
        """Abre diálogo de informações (lazy import para evitar circular)."""
        from ...core.ui.info_dialog import InfoDialog
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
