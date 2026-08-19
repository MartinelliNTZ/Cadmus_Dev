# -*- coding: utf-8 -*-
"""
SceneSelectionDialog — Diálogo de seleção de cenas com thumbnails.
=================================================================
Lista as cenas retornadas pela busca STAC com checkbox + thumbnail,
Selecionar/Desselecionar todas e botão Baixar Selecionadas.
"""

from qgis.PyQt.QtCore import QThread, pyqtSignal

from ....plugins.BaseDialog import BaseDialog
from ....resources.widgets.SceneSelectionListWidget import (
    SceneSelectionListWidget,
)
from ....resources.widgets.grid.GridComboBox import GridComboBox
from ....resources.widgets.grid.GridExecutionButtons import (
    GridExecutionButtons,
)
from ....resources.widgets.grid.GridLabel import GridLabel
from ....core.api.ImageryApi import ImageryApi
from ....i18n.TranslationManager import STR
from ....core.config.LogUtils import LogUtils


class _ThumbnailLoader(QThread):
    """Carrega os thumbnails das cenas em thread de trabalho."""

    thumbnail_ready = pyqtSignal(str, object)

    def __init__(self, api, scenes, parent=None):
        super().__init__(parent)
        self._api = api
        self._scenes = list(scenes or [])

    def run(self):
        """Baixa cada thumbnail e emite o signal para a thread da UI."""
        for scene in self._scenes:
            if self.isInterruptionRequested():
                return
            data = self._api.get_thumbnail(scene)
            self.thumbnail_ready.emit(str(scene.get("id", "")), data)


class SceneSelectionDialog(BaseDialog):
    """Diálogo modal de seleção de cenas com thumbnails (RF9).

    Parâmetros
    ----------
    scenes : list[dict]
        Cenas normalizadas retornadas por ``ImageryApi.search_scenes``.
    tool_key : ToolKey
        ToolKey para logs rastreáveis.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(self, scenes=None, tool_key=None, parent=None):
        super().__init__(parent)
        self.PLUGIN_NAME = STR.SELECT_SCENES
        self._scenes = list(scenes or [])
        self._tool_key = tool_key
        self._selected = []
        self._thumb_loader = None

        self._api = ImageryApi(tool_key=tool_key)
        self.logger = LogUtils(
            tool=tool_key, class_name="SceneSelectionDialog"
        )

        self.setWindowTitle(STR.SELECT_SCENES)
        self.setModal(True)

        self._build_ui(
            title=STR.SELECT_SCENES,
            icon_path="cadmus_icon.ico",
            enable_scroll=True,
            minimum_size=(720, 520),
        )
        self._build_inner_ui()
        self._load_thumbnails()

    def _build_inner_ui(self):
        """Monta o conteúdo interno do diálogo dentro do MainLayout."""
        # Fonte (futuras fontes além de sentinel2)
        self._source_combo = GridComboBox(
            config={
                "source": {
                    "label": STR.SOURCE,
                    "options": self._api.source_labels(),
                    "selected_key": ImageryApi.DEFAULT_SOURCE,
                },
            },
            parent=self,
        )
        self.layout.addWidget(self._source_combo)

        # Status + lista de cenas
        self._status = GridLabel(
            config={
                "status": {
                    "text": f"{len(self._scenes)} {STR.SCENES_FOUND}",
                },
            },
            parent=self,
        )
        self.layout.addWidget(self._status)

        self._scene_list = SceneSelectionListWidget(parent=self)
        self.layout.addWidget(self._scene_list)
        self._scene_list.set_scenes(self._build_scene_items())

        # Botões: Selecionar/Desselecionar todas + Baixar Selecionadas
        self._buttons = GridExecutionButtons(
            config={
                "select_all": {
                    "label": STR.SELECT_ALL,
                    "description": "Marca todas as cenas",
                    "callback": lambda: self._scene_list.select_all(),
                },
                "deselect_all": {
                    "label": STR.DESELECT_ALL,
                    "description": "Desmarca todas as cenas",
                    "callback": lambda: self._scene_list.deselect_all(),
                },
                "download": {
                    "label": STR.DOWNLOAD_SELECTED,
                    "description": "Confirma e inicia o download das cenas marcadas",
                    "callback": self._on_download,
                    "is_run_button": True,
                },
            },
            enable_close_button=True,
            enable_config_button=False,
            enable_info=False,
            parent=self,
        )
        self.layout.add_execution_buttons(self._buttons)

    def _build_scene_items(self) -> list:
        """Constrói os itens exibidos (dict id + label + default)."""
        items = []
        for scene in self._scenes:
            item = dict(scene)
            try:
                nuvens = f"{float(scene.get('nuvens', 0)):.0f}%"
            except (TypeError, ValueError):
                nuvens = "-"
            item["label"] = (
                f"{scene.get('date', '')} · tile {scene.get('tile', '')} · "
                f"{scene.get('plataforma', '')} · {nuvens} {STR.CLOUD_COVER}"
            )
            item["default"] = True
            items.append(item)
        return items

    def _load_thumbnails(self):
        """Inicia o carregamento assíncrono dos thumbnails."""
        if not self._scenes:
            return
        self._status.set_text(
            "status", f"⏳ Carregando thumbnails ({len(self._scenes)})..."
        )
        self._thumb_loader = _ThumbnailLoader(
            self._api, self._scenes, parent=self
        )
        self._thumb_loader.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._thumb_loader.finished.connect(self._on_thumbs_finished)
        self._thumb_loader.start()

    def _on_thumbnail_ready(self, scene_id: str, data):
        """Aplica o thumbnail recebido da thread ao card da cena."""
        self._scene_list.set_thumbnail(scene_id, data)

    def _on_thumbs_finished(self):
        """Restaura o status após o carregamento dos thumbnails."""
        try:
            if self._status is not None:
                self._status.set_text(
                    "status", f"{len(self._scenes)} {STR.SCENES_FOUND}"
                )
        except RuntimeError:
            self.logger.warning(
                "status C++ deletado ao finalizar thumbnails",
                code="SCENE_DLG_THUMBS_FINISHED",
            )

    def _on_download(self):
        """Confirma a seleção e fecha o diálogo com sucesso."""
        self._selected = self._scene_list.get_selected_scenes()
        if not self._selected:
            self.logger.warning(
                "Nenhuma cena selecionada para download",
                code="SCENE_DLG_NO_SELECTION",
            )
            return
        self.logger.info(
            f"{len(self._selected)} cena(s) selecionada(s)",
            code="SCENE_DLG_SELECTED",
        )
        self.accept()

    def get_selected_scenes(self) -> list:
        """Retorna as cenas marcadas (dicts originais normalizados)."""
        return list(self._selected)

    def closeEvent(self, event):
        """Interrompe a thread de thumbnails ao fechar."""
        if self._thumb_loader is not None:
            try:
                self._thumb_loader.requestInterruption()
                self._thumb_loader.wait(2000)
            except RuntimeError:
                pass
        super().closeEvent(event)

