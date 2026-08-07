# -*- coding: utf-8 -*-
"""
GridLabel — Container de labels para plugins.
Plugins USAM este widget.

A configuração é um dict onde cada chave é o identificador do label,
e o valor é um dict com:
  - "text" (obrigatório): texto do label
  - "description" (opcional): tooltip do label
"""

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout
from ..simple.SimpleLabel import SimpleLabel
from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles


class GridLabel(QWidget):
    """
    Container com labels em layout vertical.

    Uso em plugins:
        info = GridLabel(config={
            "title": {"text": "<h2>Meu App</h2>"},
            "version": {"text": "Versão 1.0", "description": "Data de atualização"},
        }, parent=self)
        layout.addWidget(info)

    Parâmetros
    ----------
    config : dict
        Dict de labels. Cada chave é identificador, valor é dict com:
        - "text" (str): texto do label
        - "description" (str, optional): tooltip
    separator_top : bool, optional
        Adiciona separador antes do widget.
    separator_bottom : bool, optional
        Adiciona separador após o widget.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(self, config: dict, separator_top: bool = False, separator_bottom: bool = False, parent=None):
        super().__init__(parent)
        if not config:
            config = {"label": {"text": ""}}

        self._labels = []
        self._label_map = {}  # key → SimpleLabel
        self._separator_top = separator_top
        self._separator_bottom = separator_bottom
        theme = AppStyles._get_theme()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(theme.LAYOUT_VERTICAL_SPACING)

        if separator_top:
            self._layout.addWidget(SeparatorWidget())

        for key, cfg in config.items():
            text = cfg.get("text", "")
            label = SimpleLabel(text=text, parent=self)

            description = cfg.get("description")
            if description:
                label.setToolTip(description)

            color = cfg.get("color")
            if color:
                label.setStyleSheet(f"{AppStyles.label()} color: {color};")

            self._labels.append(label)
            self._label_map[key] = label
            self._layout.addWidget(label)

        if separator_bottom:
            self._layout.addWidget(SeparatorWidget())

        self._apply_styles()

    # ── API Pública ────────────────────────────────────────

    def set_text(self, key: str, text: str) -> None:
        """Atualiza o texto de um label pelo identificador."""
        if key in self._label_map:
            self._label_map[key].setText(str(text))

    def get_text(self, key: str) -> str:
        """Retorna o texto de um label pelo identificador."""
        if key in self._label_map:
            return self._label_map[key].text()
        return ""

    def set_config(self, config: dict) -> None:
        """Atualiza múltiplos labels a partir de um config dict.
        
        Exemplo:
            labels.set_config({
                "municipio": {"text": "Cidade: Palmas"},
                "state": {"text": "Estado: TO"},
            })
        """
        for key, cfg in config.items():
            text = cfg.get("text", "")
            if key in self._label_map:
                self._label_map[key].setText(str(text))
            description = cfg.get("description")
            if description and key in self._label_map:
                self._label_map[key].setToolTip(description)
            color = cfg.get("color")
            if color and key in self._label_map:
                self._label_map[key].setStyleSheet(
                    f"{AppStyles.label()} color: {color};"
                )

    def rebuild(self, config: dict) -> None:
        """
        Remove todos os labels existentes e reconstrói a partir do config dict.

        Exemplo:
            labels.rebuild({
                "hint": {"text": "Clique no canvas"},
                "layer1": {"text": "1 - MDS_N: 188.2"},
            })
        """
        # Remove labels existentes do layout
        for label in self._labels:
            self._layout.removeWidget(label)
            label.deleteLater()
        self._labels.clear()
        self._label_map.clear()

        if not config:
            config = {"label": {"text": ""}}

        for key, cfg in config.items():
            text = cfg.get("text", "")
            label = SimpleLabel(text=text, parent=self)

            description = cfg.get("description")
            if description:
                label.setToolTip(description)

            color = cfg.get("color")
            if color:
                label.setStyleSheet(f"{AppStyles.label()} color: {color};")

            self._labels.append(label)
            self._label_map[key] = label
            self._layout.addWidget(label)

    def _apply_styles(self):
        combined = self._specific_style()
        if combined:
            self.setStyleSheet(combined)

    def _specific_style(self) -> str:
        return ""
