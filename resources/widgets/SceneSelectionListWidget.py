# -*- coding: utf-8 -*-
"""
SceneSelectionListWidget — Lista rolável de cenas com thumbnail + checkbox.
=======================================================================
Widget específico (exceção de generalismo) para o ImageryDownloader.

Cada linha exibe um SimpleCheckbox + thumbnail (QPixmap) + texto
(tile · data · plataforma · % nuvens). As thumbnails chegam de forma
assíncrona via `set_thumbnail` (bytes) e, em falha, exibem placeholder.

Uso por SceneSelectionDialog:
    scene_list = SceneSelectionListWidget(parent=self)
    scene_list.set_scenes(items)            # list[dict] com id/label/default
    scene_list.set_thumbnail(scene_id, data)  # bytes (JPEG) | None
    scene_list.get_selected_scenes()        # → list[dict]
    scene_list.select_all() / deselect_all()
"""

from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...i18n.TranslationManager import STR
from ..styles.AppStyles import AppStyles
from ...utils.qt_compat import resolve_qt_enum
from .simple.SimpleCheckbox import SimpleCheckbox


def _keep_aspect_ratio():
    """Retorna Qt.KeepAspectRatio (Qt5) ou AspectRatioMode (Qt6)."""
    return resolve_qt_enum(
        Qt, "KeepAspectRatio", "AspectRatioMode", "KeepAspectRatio"
    )


def _smooth_transformation():
    """Retorna Qt.SmoothTransformation (Qt5) ou TransformationMode (Qt6)."""
    return resolve_qt_enum(
        Qt, "SmoothTransformation", "TransformationMode", "SmoothTransformation"
    )


class SceneSelectionListWidget(QWidget):
    """Lista rolável de cenas com checkbox + thumbnail + informações.

    Parâmetros
    ----------
    parent : QWidget, opcional
        Widget pai.

    Autoconfiguração
    ----------------
    - AppStyles: label(), checkbox() e scroll_area() como estilos globais
    - _specific_style(): cartões das cenas com tokens do tema
    """

    _THUMB_WIDTH = 64
    _THUMB_HEIGHT = 56
    _SCROLL_MAX_HEIGHT = 420

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scenes = {}
        self._checkboxes = {}
        self._thumb_labels = {}

        self._build_layout()
        self._apply_styles()

    # ── Construção ────────────────────────────────────────────────

    def _build_layout(self):
        """Monta o layout do widget: scroll com cartões por cena."""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(AppStyles._get_theme().LAYOUT_VERTICAL_SPACING)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setMaximumHeight(self._SCROLL_MAX_HEIGHT)
        self._scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll_area.setFrameShadow(QScrollArea.Shadow.Plain)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(4, 4, 4, 4)
        self._container_layout.setSpacing(
            AppStyles._get_theme().LAYOUT_VERTICAL_SPACING
        )

        self._scroll_area.setWidget(self._container)
        self._layout.addWidget(self._scroll_area)

    def _clear(self):
        """Remove todos os cartões existentes do layout."""
        while self._container_layout.count():
            item = self._container_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    # ── API pública ───────────────────────────────────────────────

    def set_scenes(self, scenes: list):
        """Substitui a lista de cenas exibidas.

        Cada dict deve conter, no mínimo, uma chave ``id`` (str). Os
        campos ``label``, ``default``, ``date``, ``tile``, ``plataforma``
        e ``nuvens`` são usados para exibição quando presentes.
        """
        self._clear()
        self._scenes = {}
        self._checkboxes = {}
        self._thumb_labels = {}

        for index, item in enumerate(scenes or []):
            scene_id = str(item.get("id") or f"scene_{index}")
            self._scenes[scene_id] = item
            self._add_scene_row(scene_id, item)

        self._container_layout.addStretch()

    def set_thumbnail(self, scene_id: str, data):
        """Define a thumbnail (bytes) de uma cena já adicionada.

        Em falha (None, bytes inválidos) exibe placeholder.
        """
        label = self._thumb_labels.get(str(scene_id))
        if label is None:
            return

        if not isinstance(data, (bytes, bytearray)):
            self._set_thumbnail_placeholder(label)
            return

        pixmap = QPixmap()
        if not pixmap.loadFromData(bytes(data)):
            self._set_thumbnail_placeholder(label)
            return

        scaled = pixmap.scaled(
            QSize(self._THUMB_WIDTH - 8, self._THUMB_HEIGHT - 8),
            _keep_aspect_ratio(),
            _smooth_transformation(),
        )
        label.setPixmap(scaled)

    def get_selected_scenes(self) -> list:
        """Retorna os dicts originais das cenas marcadas (ordem da lista)."""
        return [
            self._scenes[scene_id]
            for scene_id, checkbox in self._checkboxes.items()
            if checkbox.isChecked()
        ]

    def select_all(self):
        """Marca todos os checkboxes habilitados."""
        for checkbox in self._checkboxes.values():
            if checkbox.isEnabled():
                checkbox.setChecked(True)

    def deselect_all(self):
        """Desmarca todos os checkboxes habilitados."""
        for checkbox in self._checkboxes.values():
            if checkbox.isEnabled():
                checkbox.setChecked(False)

    # ── Construção interna ────────────────────────────────────────

    def _add_scene_row(self, scene_id: str, item: dict):
        """Cria a linha de cartão com checkbox + thumbnail + texto."""
        card = QFrame()
        card.setObjectName("scene_card")
        row_layout = QHBoxLayout(card)
        row_layout.setContentsMargins(4, 2, 4, 2)
        row_layout.setSpacing(
            AppStyles._get_theme().LAYOUT_HORIZONTAL_SPACING
        )

        checkbox = SimpleCheckbox(text="", parent=card)
        checkbox.setChecked(bool(item.get("default", True)))
        row_layout.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignVCenter)

        thumb_label = QLabel(card)
        thumb_label.setObjectName("scene_thumb")
        thumb_label.setFixedSize(self._THUMB_WIDTH, self._THUMB_HEIGHT)
        thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_thumbnail_placeholder(thumb_label)
        row_layout.addWidget(thumb_label, 0, Qt.AlignmentFlag.AlignVCenter)

        text_label = QLabel(self._build_label_text(item), card)
        text_label.setObjectName("scene_text")
        text_label.setWordWrap(True)
        text_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        row_layout.addWidget(text_label, 1)

        self._checkboxes[scene_id] = checkbox
        self._thumb_labels[scene_id] = thumb_label
        self._container_layout.addWidget(card)

    def _build_label_text(self, item: dict) -> str:
        """Retorna o texto da cena; prioriza ``label`` do dict."""
        label = item.get("label")
        if label:
            return label
        try:
            nuvens = f"{float(item.get('nuvens', 0)):.0f}%"
        except (TypeError, ValueError):
            nuvens = "-"
        return (
            f"{item.get('date', '')} · tile {item.get('tile', '')} · "
            f"{item.get('plataforma', '')} · {nuvens}"
        )

    def _set_thumbnail_placeholder(self, label: QLabel):
        """Exibe o texto de placeholder no label de thumbnail.

        QLabel exibe apenas um conteúdo (texto OU pixmap): limpa o
        pixmap primeiro e depois aplica o texto do placeholder.
        """
        label.setPixmap(QPixmap())
        label.setText(STR.NO_THUMBNAIL)

    # ── Estilos ───────────────────────────────────────────────────

    def _apply_styles(self):
        """Aplica estilos globais + específico."""
        self.setStyleSheet(self._get_global_style() + self._specific_style())

    def _get_global_style(self) -> str:
        """Estilos globais via AppStyles."""
        return (
            AppStyles.label()
            + AppStyles.checkbox()
            + AppStyles.scroll_area()
        )

    def _specific_style(self) -> str:
        """Estilo específico: cartões, thumbnail e texto da lista."""
        theme = AppStyles._get_theme()
        return (
            f"QScrollArea {{"
            f"    background: {theme.COLOR_BACKGROUND_TRANSPARENT};"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    border-radius: {theme.BORDER_RADIUS_SMALL_COMPONENT};"
            f"}}"
            f"QWidget#scene_card {{"
            f"    background: {theme.COLOR_BACKGROUND_SOFT};"
            f"    border-radius: {theme.BORDER_RADIUS_SMALL_COMPONENT};"
            f"    padding: {theme.PADDING_LIST_ITEM};"
            f"}}"
            f"QLabel#scene_thumb {{"
            f"    background: {theme.COLOR_BACKGROUND_PANEL};"
            f"    color: {theme.COLOR_TEXT_SECONDARY};"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    border-radius: {theme.BORDER_RADIUS_SMALL_COMPONENT};"
            f"    font-size: {theme.FONT_SIZE_LABEL_TEXT};"
            f"}}"
            f"QLabel#scene_text {{"
            f"    color: {theme.COLOR_TEXT_PRIMARY};"
            f"    font-family: {theme.FONT_FAMILY_DEFAULT};"
            f"    font-size: {theme.FONT_SIZE_LABEL_TEXT};"
            f"}}"
        )
