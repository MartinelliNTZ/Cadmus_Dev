# -*- coding: utf-8 -*-
"""
GridModernButtons — Container de botões configurável via dict, totalmente genérico.
===================================================================================
SEM botões built-in. SEM lógica de execução. Apenas botões configurados via dict.
Usa SimpleModernButton internamente (gradiente + glow).

Suporta alinhamento: left, right, center, justify (default).
Modo justify: distribui botões proporcionalmente ao espaço disponível.
Se não couber mesmo no mínimo, QUEBRA LINHA automaticamente.

Uso:
    buttons = GridModernButtons(
        config={
            "select_all": {
                "label": "Selecionar Todos",
                "callback": self._select_all,
                "primary": False,
            },
            ...
        },
        alignment="justify",
        parent=self,
    )
"""

from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout
from qgis.PyQt.QtCore import Qt

from ..simple.SimpleModernButton import SimpleModernButton
from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles


class GridModernButtons(QWidget):
    """
    Container de botões configurável via dict, totalmente genérico.
    Usa QGridLayout para suportar quebra de linha automática.

    Alinhamento:
        "left"    — botões alinhados à esquerda
        "right"   — botões alinhados à direita
        "center"  — botões centralizados
        "justify" — (default) distribui botões proporcionalmente.
                    Se não couber no mínimo, quebra linha.

    Parâmetros
    ----------
    config : dict, optional
        Dict de botões. Chave = identificador.
        Valor = dict com: "label", "callback", "description", "primary"
    alignment : str, optional
        "left", "right", "center" ou "justify" (default).
    separator_top : bool, optional
    separator_bottom : bool, optional
    parent : QWidget, optional
    """

    _SPACING = 6      # px entre botões
    _MIN_W = 60       # px mínimo por botão
    _PADDING = 44     # padding interno do SimpleModernButton

    def __init__(
        self,
        config: dict = None,
        alignment: str = "justify",
        separator_top: bool = False,
        separator_bottom: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._config = config or {}
        self._alignment = alignment.lower()
        if self._alignment not in ("left", "right", "center", "justify"):
            self._alignment = "justify"

        self._sep_top = separator_top
        self._sep_bot = separator_bottom

        # Grid layout — linhas e colunas dinâmicas
        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(self._SPACING)

        # Container externo com separadores
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        if self._sep_top:
            outer.addWidget(SeparatorWidget())
        outer.addLayout(self._grid)
        if self._sep_bot:
            outer.addWidget(SeparatorWidget())

        # Cria botões e armazena
        self._buttons: dict[str, SimpleModernButton] = {}
        self._btn_list: list[SimpleModernButton] = []

        for key, bc in self._config.items():
            btn = SimpleModernButton(
                text=bc.get("label", key),
                tooltip=bc.get("description", ""),
                primary=bc.get("primary", False),
                parent=self,
            )
            cb = bc.get("callback")
            if cb:
                btn.clicked.connect(cb)
            self._buttons[key] = btn
            self._btn_list.append(btn)

        # Layout inicial
        self._do_layout()

        self._apply_styles()

    # ── API ────────────────────────────────────────────────────────

    def get_button(self, key: str):
        return self._buttons.get(key)

    def set_button_enabled(self, key: str, enabled: bool):
        btn = self._buttons.get(key)
        if btn:
            btn.setEnabled(enabled)

    # ── Layout ─────────────────────────────────────────────────────

    def _do_layout(self):
        """Posiciona botões no grid conforme alinhamento e largura."""
        self._clear_grid()
        if not self._btn_list:
            return

        w = self.width() if self.width() > 50 else 400

        if self._alignment == "justify":
            self._do_justify(w)
        else:
            self._do_simple(w)

    def _do_simple(self, w: int):
        """left / right / center — uma linha só."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(self._SPACING)

        for btn in self._btn_list:
            btn.setFixedWidth(self._natural_w(btn))
            row.addWidget(btn)

        if self._alignment == "left":
            row.addStretch()
        elif self._alignment == "right":
            row.insertStretch(0)
        elif self._alignment == "center":
            row.insertStretch(0)
            row.addStretch()

        self._grid.addLayout(row, 0, 0)

    def _do_justify(self, w: int):
        """Distribui em linhas com quebra automática."""
        spacing = self._SPACING
        min_w = self._MIN_W
        buttons = self._btn_list
        n = len(buttons)

        # Quantos botões cabem por linha
        bpr = self._bpr(n, w, min_w, spacing)

        row = 0
        for i in range(0, n, bpr):
            row_btns = buttons[i:i + bpr]
            self._place_row(row, row_btns, w)
            row += 1

    def _bpr(self, total: int, avail: int, min_w: int, spacing: int) -> int:
        """Buttons per row: máximo que cabe no mínimo."""
        if total <= 1:
            return 1
        for n in range(total, 0, -1):
            if n * min_w + (n - 1) * spacing <= avail:
                return n
        return 1

    def _place_row(self, row: int, btns: list, avail: int):
        """Posiciona uma linha no grid com distribuição proporcional."""
        count = len(btns)
        spacing = self._SPACING
        usable = max(0, avail - spacing * (count - 1))

        # Larguras naturais
        nat = [self._natural_w(b) for b in btns]
        total_nat = sum(nat)

        if total_nat <= usable:
            extra = (usable - total_nat) // count
            widths = [n + extra for n in nat]
        else:
            widths = self._shrink(nat, total_nat - usable)

        for col, btn in enumerate(btns):
            btn.setFixedWidth(max(self._MIN_W, widths[col]))
            self._grid.addWidget(btn, row, col)

    def _natural_w(self, btn: SimpleModernButton) -> int:
        """Largura natural do botão baseada no texto."""
        from qgis.PyQt.QtGui import QFontMetrics
        m = QFontMetrics(btn.font())
        tw = m.horizontalAdvance(btn.text()) if hasattr(m, 'horizontalAdvance') else m.width(btn.text())
        return tw + self._PADDING

    def _shrink(self, widths: list[int], deficit: int) -> list[int]:
        """Reduz proporcionalmente, maiores perdem mais."""
        res = list(widths)
        rem = deficit
        mw = self._MIN_W
        avail = sum(max(0, w - mw) for w in res)
        if avail <= 0:
            return [mw] * len(res)

        ratio = min(1.0, rem / avail)
        for i in range(len(res)):
            excess = max(0, res[i] - mw)
            cut = int(excess * ratio)
            res[i] = max(mw, res[i] - cut)
            rem -= cut
        return res

    def _clear_grid(self):
        """Remove todos os itens do grid."""
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.layout():
                while item.layout().count():
                    li = item.layout().takeAt(0)
                    if li.widget():
                        li.widget().setParent(None)
            elif item.widget():
                item.widget().setParent(None)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._alignment == "justify" and self._btn_list:
            self._do_layout()

    # ── Estilos ────────────────────────────────────────────────────

    def _apply_styles(self):
        self.setStyleSheet(self._get_global_style() + self._specific_style())

    def _get_global_style(self) -> str:
        return AppStyles.button()

    def _specific_style(self) -> str:
        return ""