# -*- coding: utf-8 -*-
"""
ComplexColorPicker — Seletor de cor com label, QgsColorButton, hex readonly e botão copiar.
============================================================================================
Widget raiz (SEM versão grid). Plugins USAM este widget.

Composição (layout horizontal):
    [SimpleLabel] [QgsColorButton] [SimpleQLineEdit (hex readonly)] [SquareIconButton (COPY2)]

Autoconfiguração total:
- AppStyles para estilos globais
- ThemeManager → BaseTheme para tokens visuais
- _specific_style() para estilo próprio

Uso em plugins:
    color_picker = ComplexColorPicker(
        label_text=STR.BACKGROUND_COLOR,
        initial_color=QColor("#ffffff"),
        tooltip=STR.SELECT_FILL_COLOR,
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    self.layout.addWidget(color_picker)

    color_picker.set_color(QColor("#ff0000"))
    color = color_picker.get_color()
"""

from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsColorButton

from ...core.config.LogUtils import LogUtils
from ...utils.ProjectUtils import ProjectUtils
from ..IconManager import IconManager
from ..styles.AppStyles import AppStyles
from .simple.SimpleLabel import SimpleLabel
from .simple.SimpleQLineEdit import SimpleQLineEdit
from .simple.SquareIconButton import SquareIconButton


class ComplexColorPicker(QWidget):
    """
    Seletor de cor com label, QgsColorButton, campo hex readonly e botão copiar.

    Parâmetros
    ----------
    label_text : str, optional
        Texto do label.
    initial_color : QColor, optional
        Cor inicial (default: branco).
    tooltip : str, optional
        Tooltip do seletor.
    tool_key : ToolKey, optional
        ToolKey para logs.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        label_text: str = "",
        initial_color: QColor = None,
        tooltip: str = "",
        tool_key=None,
        parent=None,
    ):
        super().__init__(parent)

        self._label_text = label_text
        self._initial_color = initial_color or QColor("#ffffff")
        self._tooltip = tooltip
        self._tool_key = tool_key

        # Logger
        tool_name = tool_key or "ComplexColorPicker"
        self.logger = LogUtils(tool=tool_name, class_name="ComplexColorPicker")

        try:
            self._build_ui()
            self._apply_styles()
        except Exception as error:
            self.logger.exception(
                "Erro ao construir ComplexColorPicker",
                code="COLOR_PICKER_BUILD_ERROR",
                error=str(error),
            )

    # ══════════════════════════════════════════════════════════════════
    # UI
    # ══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        """Monta layout horizontal: label + color button + hex readonly + copiar."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ── Label ────────────────────────────────────────────────
        self._label = SimpleLabel(text=self._label_text, parent=self)
        if self._tooltip:
            self._label.setToolTip(self._tooltip)
        layout.addWidget(self._label, 0)

        # ── QgsColorButton (seletor de cor) ──────────────────────
        self._color_button = QgsColorButton()
        self._color_button.setAllowOpacity(True)
        self._color_button.setToolTip(self._tooltip or "Escolha uma cor")
        self._color_button.colorChanged.connect(self._on_color_changed)
        layout.addWidget(self._color_button, 0)

        # ── Hex readonly (SimpleQLineEdit) ───────────────────────
        self._hex_edit = SimpleQLineEdit(
            text="",
            placeholder="",
            read_only=True,
            primary=True,
            parent=self,
        )
        layout.addWidget(self._hex_edit, 1)

        # ── Botão copiar (SquareIconButton + COPY2) ──────────────
        self._copy_button = SquareIconButton(
            icon=IconManager.icon(IconManager.COPY2),
            tooltip="Copiar valor hexadecimal",
            parent=self,
        )
        self._copy_button.clicked.connect(self._copy_to_clipboard)
        layout.addWidget(self._copy_button, 0)

        # Define cor inicial
        self.set_color(self._initial_color)

    # ══════════════════════════════════════════════════════════════════
    # Handlers
    # ══════════════════════════════════════════════════════════════════

    def _on_color_changed(self, color: QColor):
        """Atualiza o campo hex quando a cor muda."""
        self._update_hex_text(color)

    def _update_hex_text(self, color: QColor):
        """Exibe HexRgb ou HexArgb conforme opacidade."""
        if color.alpha() < 255:
            text = color.name(QColor.NameFormat.HexArgb)
        else:
            text = color.name(QColor.NameFormat.HexRgb)
        self._hex_edit.setText(text)

    def _copy_to_clipboard(self):
        """Copia o valor hexadecimal para a área de transferência."""
        text = self._hex_edit.text()
        if text:
            ProjectUtils.set_clipboard_text(text)
            self.logger.info(
                "Valor hexadecimal copiado para área de transferência",
                code="COLOR_PICKER_COPY_CLIPBOARD",
            )

    # ══════════════════════════════════════════════════════════════════
    # API Pública
    # ══════════════════════════════════════════════════════════════════

    def set_color(self, color: QColor):
        """Define a cor e atualiza o campo hex."""
        if color is None:
            color = QColor("#ffffff")
        self._color_button.setColor(color)
        self._update_hex_text(color)

    def get_color(self) -> QColor:
        """Retorna a cor atual."""
        return self._color_button.color()

    def color(self) -> QColor:
        """Alias de get_color()."""
        return self.get_color()

    def color_button(self) -> QgsColorButton:
        """Acesso direto ao QgsColorButton."""
        return self._color_button

    def hex_input(self):
        """Acesso direto ao campo hex (SimpleQLineEdit)."""
        return self._hex_edit

    # ══════════════════════════════════════════════════════════════════
    # Estilos
    # ══════════════════════════════════════════════════════════════════

    def _apply_styles(self):
        """Aplica estilos globais + específico."""
        combined_style = self._get_global_style() + self._specific_style()
        self.setStyleSheet(combined_style)

    def _get_global_style(self) -> str:
        """Estilos globais via AppStyles."""
        return AppStyles.label() + AppStyles.input()

    def _specific_style(self) -> str:
        """
        Estilo específico deste widget.
        Usa tokens do tema com nomes descritivos.
        """
        return ""
