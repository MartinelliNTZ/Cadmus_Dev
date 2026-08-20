# -*- coding: utf-8 -*-
"""
ImageryDownloaderPlugin — Downloader genérico de imagens de satélite.
=====================================================================
Primeira fonte: Sentinel-2 L2A (STAC Earth Search). Busca cenas por bbox +
datas + % de nuvens, lista com thumbnails, baixa bandas/composições por data
em tasks (engine 2 com ParallelStep quando 2+ datas), aplica processamento
opcional (clip polígono/boundary, reprojeção condicional, ÷10000) e carrega
as camadas no QGIS agrupadas por data.
"""
import os

from ..plugins.BasePlugin import BasePluginMTL
from ..utils.ToolKeys import ToolKey
from ..utils.Preferences import Preferences
from ..utils.DependenciesManager import DependenciesManager
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.ExplorerUtils import ExplorerUtils
from ..i18n.TranslationManager import STR
from ..core.engine_tasks.ExecutionContext import ExecutionContext
from ..core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from ..core.engine_tasks.ImagerySearchStep import ImagerySearchStep
from ..core.engine_tasks.ParallelStep import ParallelStep
from ..core.engine_tasks.DownloadDateStep import DownloadDateStep
from ..core.api.ImageryApi import ImageryApi
from ..resources.widgets.CollapsibleParametersWidget import (
    CollapsibleParametersWidget,
)
from ..resources.widgets.grid.GridBBoxSelector import GridBBoxSelector
from ..resources.widgets.grid.GridDateSelector import GridDateSelector
from ..resources.widgets.grid.GridSlider import GridSlider
from ..resources.widgets.grid.GridCheckbox import GridCheckbox
from ..resources.widgets.ComplexCrsSelector import ComplexCrsSelector
from ..resources.widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons


class ImageryDownloaderPlugin(BasePluginMTL):
    """Ferramenta de download de imagens de satélite (Sentinel-2 L2A)."""

    TOOL_KEY = ToolKey.IMAGERY_DOWNLOADER
    PLUGIN_NAME = STR.IMAGERY_DOWNLOADER_TITLE
    SOURCE_LABEL = "Sentinel-2"
    DEFAULT_BANDS = ("B04", "B03", "B02")

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.init(self.TOOL_KEY, self.__class__.__name__)
        self._check_dependencies()

    # ── Dependências (RF1) ───────────────────────────────────────

    def _check_dependencies(self):
        """Valida PySTACClient e oferece instalação se ausente (RF1)."""
        result = DependenciesManager.validate_dependencies(
            ["PySTACClient"], self.TOOL_KEY
        )
        if result["all_present"]:
            self.logger.info("Dependência PySTACClient presente")
            return True

        self.logger.warning(
            "PySTACClient ausente — perguntando ao usuário",
            code="IMAGERY_DEPENDENCY_MISSING",
        )
        if QgisMessageUtil.confirm(
            self.iface, STR.DEPENDENCY_MISSING_IMAGERY
        ):
            DependenciesManager.install_dependency_gui(
                "PySTACClient", self.iface, self.TOOL_KEY
            )

        result = DependenciesManager.validate_dependencies(
            ["PySTACClient"], self.TOOL_KEY
        )
        if result["all_present"]:
            self.logger.info("PySTACClient instalado e validado")
            return True

        QgisMessageUtil.bar_warning(self.iface, STR.DEPENDENCY_MISSING_IMAGERY)
        return False

    # ── UI ───────────────────────────────────────────────────────

    def _build_ui(self, **kwargs):
        """Método padrão do BasePlugin (substitui super()._build_ui)."""
        super()._build_ui(
            title=STR.IMAGERY_DOWNLOADER_TITLE,
            icon_path="cadmus_icon.ico",
            enable_scroll=True,
        )

        # 1. Configurações — primeiro collapsable: agrupa tudo que ficava
        #    solto no diálogo (extensão, período, nuvens, opções, EPSG e pasta)
        self.settings_collapse = CollapsibleParametersWidget(
            title=STR.SETTINGS,
            expanded_by_default=False,
            parent=self,
        )

        # 1.1 Bounding box (área da busca: camada / tela / desenho)
        self.bbox = GridBBoxSelector(
            iface=self.iface,
            config={
                "capture_label": STR.BBOX_CAPTURE_SCREEN,
                "capture_description": STR.BBOX_CAPTURE_SCREEN_DESC,
                "draw_label": STR.BBOX_DRAW_MAP,
                "draw_description": STR.BBOX_DRAW_MAP_DESC,
            },
            title=STR.BBOX_SOURCE,
            parent=self,
        )
        self.settings_collapse.add_content_widget(self.bbox)

        # 1.2 Datas
        self.dates = GridDateSelector(
            config={
                "start": {"label": STR.START_DATE, "date": "2026-01-01"},
                "end": {"label": STR.END_DATE, "date": "2026-12-31"},
            },
            title=STR.DATE_PERIOD,
            parent=self,
        )
        self.settings_collapse.add_content_widget(self.dates)

        # 1.3 % máximo de nuvens
        self.cloud_slider = GridSlider(
            config={
                "max_cloud": {
                    "label": STR.CLOUD_MAX,
                    "value": 50,
                    "min": 0,
                    "max": 100,
                    "suffix": "%",
                },
            },
            parent=self,
        )
        self.settings_collapse.add_content_widget(self.cloud_slider)

        # 1.4 Opções de processamento (recorte vem do próprio GridBBoxSelector:
        #     polígono desenhado/camada de polígono -> máscara; senão boundary)
        self.options = GridCheckbox(
            config={
                "clip": {
                    "label": STR.CLIP_BY_POLYGON,
                    "description": STR.CLIP_BY_POLYGON_DESC,
                },
                "reproject": {
                    "label": STR.REPROJECT_OUTPUT,
                    "description": STR.REPROJECT_OUTPUT_DESC,
                    "default": True,
                },
                "convert": {
                    "label": STR.CONVERT_UINT16,
                    "description": STR.CONVERT_UINT16_DESC,
                    "default": True,
                },
                "delete": {
                    "label": STR.DELETE_ORIGINALS,
                    "description": STR.DELETE_ORIGINALS_DESC,
                },
            },
            title=STR.OPTIONS,
            items_per_row=2,
            parent=self,
        )
        self.settings_collapse.add_content_widget(self.options)

        # 1.5 EPSG de saída
        self.epsg_output = ComplexCrsSelector(
            label_text=STR.EPSG_OUTPUT,
            default_auth_id="EPSG:4326",
            tooltip=STR.EPSG_OUTPUT,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.settings_collapse.add_content_widget(self.epsg_output)

        # 1.6 Pasta de saída (vazio = temp do Cadmus)
        self.output = GridComplexSelector(
            config={
                "output": {
                    "label": STR.OUTPUT_FOLDER,
                    "description": STR.TEMP_FOLDER_HINT,
                    "mode_type": "output",
                    "allow_file": False,
                    "allow_folder": True,
                },
            },
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.settings_collapse.add_content_widget(self.output)
        self.layout.addWidget(self.settings_collapse)

        # 2. Bandas/composições pré-populadas (RF5) — segundo collapsable
        self.bands_collapse = CollapsibleParametersWidget(
            title=STR.BANDS_ASSETS,
            expanded_by_default=False,
            parent=self,
        )
        self.bands = GridCheckbox(
            config=self._build_bands_config(),
            title=STR.BANDS_ASSETS_DESC,
            items_per_row=3,
            control_buttons_config={
                "select_all": {
                    "label": STR.SELECT_ALL,
                    "callback": lambda: self.bands.select_all(),
                },
                "deselect_all": {
                    "label": STR.DESELECT_ALL,
                    "callback": lambda: self.bands.deselect_all(),
                },
            },
            separator_bottom=True,
            parent=self,
        )
        self.bands_collapse.add_content_widget(self.bands)
        self.layout.addWidget(self.bands_collapse)

        # 3. Botões de execução
        self.buttons = GridExecutionButtons(
            config={
                "run": {
                    "label": STR.SEARCH_SCENES,
                    "description": STR.IMAGERY_DOWNLOADER_TOOLTIP,
                    "callback": self.execute_tool,
                    "is_run_button": True,
                },
            },
            enable_close_button=True,
            enable_config_button=False,
            enable_info=True,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.layout.add_execution_buttons(self.buttons)

    def _build_bands_config(self) -> dict:
        """Monta o config de bandas + composições pré-populado (RF5).

        Filtra bandas/composições cujas bandas não existam na fonte
        (assets/asset_map), evitando checkboxes a assets inexistentes.
        """
        cfg = ImageryApi(tool_key=self.TOOL_KEY).get_source_config("sentinel2")
        available = set(cfg.get("assets", {}).keys()).union(
            set(cfg.get("asset_map", {}).keys())
        )
        config = {}
        for band, (nome, res) in cfg["assets"].items():
            if band not in available:
                continue
            config[band] = {
                "label": f"{band} · {nome} ({res})",
                "description": f"{nome} ({res})",
                "default": band in self.DEFAULT_BANDS,
            }
        for comp_key, comp in cfg["compositions"].items():
            bandas = comp.get("bandas")
            if isinstance(bandas, (list, tuple)) and not any(
                b in available for b in bandas
            ):
                # composição sem bandas válidas na fonte -> não criar checkbox
                continue
            config[f"comp_{comp_key}"] = {
                "label": f"⭐ {comp['nome']}",
                "description": "Composição pronta — marca as bandas ao selecionar",
                "default": False,
                "onchange": lambda checked, k=comp_key: (
                    self._on_composition_changed(checked, k)
                ),
            }
        return config

    def _on_composition_changed(self, checked, comp_key):
        """Marca as bandas de uma composição pronta ao selecioná-la."""
        if not checked:
            return
        cfg = ImageryApi(tool_key=self.TOOL_KEY).get_source_config("sentinel2")
        bandas = cfg["compositions"].get(comp_key, {}).get("bandas")
        if bandas:
            for banda in bandas:
                self.bands.set_checked(banda, True)
        else:
            # composição "TODAS": marca todas as bandas da fonte
            for banda in cfg["assets"]:
                self.bands.set_checked(banda, True)

    # ── Preferências ─────────────────────────────────────────────

    def _load_prefs(self):
        """Carrega preferências persistidas nos widgets."""
        prefs = self.preferences or {}

        dates = prefs.get("dates", {})
        if isinstance(dates, dict):
            self.dates.set_dates(
                {k: v for k, v in dates.items() if k in ("start", "end")}
            )

        self.cloud_slider.set_value("max_cloud", prefs.get("max_cloud", 50))
        self.bbox.set_preferences(prefs.get("bbox", {}))
        self.bands.set_preferences(prefs.get("bands", {}))
        self.options.set_preferences(prefs.get("options", {}))

        epsg = prefs.get("epsg_output", "EPSG:4326")
        if not isinstance(epsg, str) or epsg.strip().lower() in ("", "utm", "native"):
            epsg = "EPSG:4326"
        elif not epsg.strip().upper().startswith("EPSG:"):
            epsg = f"EPSG:{epsg.strip()}"
        if not self.epsg_output.set_crs_authid(epsg):
            self.logger.warning(
                f"SRC inválido salvo: {epsg}, usando EPSG:4326",
                code="IMAGERY_EPSG_INVALID",
            )
            self.epsg_output.set_crs_authid("EPSG:4326")
        self.output.set_preferences(prefs.get("output", {}))

        self.settings_collapse.set_preferences(
            prefs.get("settings_collapse", {})
        )
        self.bands_collapse.set_preferences(prefs.get("bands_collapse", {}))

    def _save_prefs(self):
        """Persiste preferências via Preferences (padrão novo sistema)."""
        self.preferences["dates"] = self.dates.get_dates_str()
        self.preferences["max_cloud"] = self.cloud_slider.get_value(
            "max_cloud"
        )
        self.preferences["bbox"] = self.bbox.get_preferences()
        self.preferences["bands"] = self.bands.get_preferences()
        self.preferences["options"] = self.options.get_preferences()
        self.preferences["epsg_output"] = self.epsg_output.get_crs_authid()
        self.preferences["output"] = self.output.get_preferences()
        self.preferences["settings_collapse"] = (
            self.settings_collapse.get_preferences()
        )
        self.preferences[
            "bands_collapse"
        ] = self.bands_collapse.get_preferences()
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
        self.logger.info("Preferências do ImageryDownloader salvas")

    # ── Validação e orquestração ─────────────────────────────────

    def _resolve_bandas(self) -> list:
        """Expande bandas + composições do GridCheckbox em lista única."""
        states = self.bands.get_preferences().get("checked", {})
        translated = {}
        for key, enabled in states.items():
            translated[key[5:] if key.startswith("comp_") else key] = enabled
        return ImageryApi(tool_key=self.TOOL_KEY).resolve_bands(
            translated, "sentinel2"
        )

    def _validate_inputs(self) -> bool:
        """Valida extensão, datas e bandas antes da busca."""
        if not self.bbox.bbox_wgs84():
            QgisMessageUtil.bar_warning(
                self.iface, STR.VALIDATION_EXTENT
            )
            return False

        d0 = self.dates.get_date_str("start")
        d1 = self.dates.get_date_str("end")
        if not d0 or not d1 or d0 > d1:
            QgisMessageUtil.bar_warning(
                self.iface, STR.VALIDATION_DATES
            )
            return False

        if not self._resolve_bandas():
            QgisMessageUtil.bar_warning(
                self.iface, STR.VALIDATION_BANDS
            )
            return False

        # Recorte: precisa de polígono ou boundary válido vindo do bbox
        if self.options.is_checked("clip") and not self.bbox.is_clip_valid():
            QgisMessageUtil.bar_warning(
                self.iface, STR.VALIDATION_CLIP
            )
            return False

        return True

    def _build_context(self) -> ExecutionContext:
        """Monta o ExecutionContext com todos os parâmetros da busca."""
        context = ExecutionContext(tool_key=self.TOOL_KEY)
        context.set("source", "sentinel2")
        context.set("bbox_wgs84", self.bbox.bbox_wgs84())
        context.set("date_from", self.dates.get_date_str("start"))
        context.set("date_to", self.dates.get_date_str("end"))
        context.set("max_cloud", self.cloud_slider.get_value("max_cloud"))
        context.set("bandas", self._resolve_bandas())
        context.set(
            "options", self.options.get_preferences().get("checked", {})
        )
        context.set("clip_data", self.bbox.build_clip_data())
        context.set("epsg_out", self.epsg_output.get_crs_authid())
        context.set("output_folder", self._resolve_output_folder())
        return context

    def _resolve_output_folder(self) -> str:
        """Resolve a pasta de saída ou a pasta temporária do Cadmus.

        O GridComplexSelector pode devolver a URI de uma camada XYZ/raster
        (ex: url=https...crs=EPSG:3857) em vez de um diretório local. Nesse
        caso, ou quando o caminho é inválido, usa a pasta temporária para não
        gravar os rasters fora do lugar esperado.
        """
        caminho = self.output.get_path("output") or ""
        if not caminho:
            return ""

        # Rejeita URIs de camada (não são diretórios) e caminhos não absolutos.
        if not os.path.isabs(caminho) or any(
            marcador in caminho.lower() for marcador in ("://", "?type=", "crs=")
        ):
            self.logger.warning(
                "Pasta de saída inválida (URI de camada), usando temp",
                code="IMAGERY_OUTPUT_INVALID",
                valor=caminho,
            )
            return ExplorerUtils.get_temp_folder(self.TOOL_KEY, "imagery")

        if os.path.isfile(caminho):
            self.logger.warning(
                "Pasta de saída aponta para um arquivo, usando temp",
                code="IMAGERY_OUTPUT_INVALID_FILE",
                valor=caminho,
            )
            return ExplorerUtils.get_temp_folder(self.TOOL_KEY, "imagery")

        return caminho

    def execute_tool(self):
        """Engine 1: busca as cenas no STAC e abre a seleção."""
        self.logger.info("Iniciando busca de cenas (ImageryDownloader)")
        if not self._validate_inputs():
            return
        self._save_prefs()

        context = self._build_context()
        engine = AsyncPipelineEngine(
            steps=[ImagerySearchStep()],
            context=context,
            on_finished=self._on_search_finished,
            on_error=self._on_pipeline_error,
        )
        self.logger.info("Engine 1 (busca STAC) iniciada")
        engine.start()

    def _on_search_finished(self, context):
        """Após a busca, abre o diálogo de seleção e dispara a engine 2."""
        try:
            scenes = context.get("scenes") or []
        except Exception as e:
            self.logger.error(f"Falha ao ler cenas do contexto: {e}")
            scenes = []

        if not scenes:
            QgisMessageUtil.bar_warning(self.iface, STR.NO_SCENES_FOUND)
            return

        self.logger.info(f"{len(scenes)} {STR.SCENES_FOUND}")

        from ..core.ui.dialogs.SceneSelectionDialog import SceneSelectionDialog

        dlg = SceneSelectionDialog(
            scenes=scenes, tool_key=self.TOOL_KEY, parent=self
        )
        if not dlg.exec():
            self.logger.info("Seleção de cenas cancelada pelo usuário")
            return

        context.set("selected_scenes", dlg.get_selected_scenes())
        self._run_download_pipeline(context)

    def _can_use_parallel(self, dates) -> bool:
        """RF10: paralelismo viável com 2+ datas independentes."""
        return len(dates) >= 2

    def _run_download_pipeline(self, context):
        """Engine 2: baixa as datas selecionadas (ParallelStep ou sequencial)."""
        selected = context.get("selected_scenes", []) or []
        dates = sorted(
            {s.get("date") for s in selected if s.get("date")}
        )
        if not dates:
            QgisMessageUtil.bar_warning(self.iface, STR.NO_SCENE_SELECTED)
            return

        if self._can_use_parallel(dates):
            QgisMessageUtil.bar_info(
                self.iface, STR.PARALLEL_INFO.format(n=len(dates))
            )
            steps = [
                ParallelStep(
                    [
                        DownloadDateStep(d, source_label=self.SOURCE_LABEL)
                        for d in dates
                    ],
                    description="download_dates",
                )
            ]
        else:
            QgisMessageUtil.bar_info(self.iface, STR.PARALLEL_NOT_POSSIBLE)
            steps = [
                DownloadDateStep(d, source_label=self.SOURCE_LABEL)
                for d in dates
            ]

        self.logger.info(
            f"Engine 2 iniciada: {len(steps)} step(s), {len(dates)} data(s)",
            code="IMAGERY_ENGINE2_START",
        )
        engine = AsyncPipelineEngine(
            steps=steps,
            context=context,
            on_finished=self._on_download_pipeline_finished,
            on_error=self._on_pipeline_error,
        )
        engine.start()

    def _on_download_pipeline_finished(self, context):
        """Callback final da engine 2."""
        self.logger.info(STR.DOWNLOAD_FINISHED)
        QgisMessageUtil.bar_success(self.iface, STR.DOWNLOAD_FINISHED)
        if not context.get("output_folder"):
            QgisMessageUtil.bar_info(self.iface, STR.TEMP_FOLDER_HINT)


def run(iface):
    """Função de entrada do plugin (padrão registry DIALOG)."""
    dlg = ImageryDownloaderPlugin(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg

