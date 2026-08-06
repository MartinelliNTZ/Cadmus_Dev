# -*- coding: utf-8 -*-
"""
RasterSamplerDialog — Dialog da ferramenta de amostragem de rasters.
====================================================================
Herda BasePluginMTL (padrao CoordResultDialog).

Permite selecionar multiplos rasters do projeto via GridCheckbox,
exibe os valores amostrados no ponto clicado via GridLabel
e persiste a selecao via Preferences.
"""

from ..utils.ToolKeys import ToolKey
from ..utils.Preferences import Preferences
from ..utils.ProjectUtils import ProjectUtils
from ..i18n.TranslationManager import STR
from .BasePlugin import BasePluginMTL
from ..resources.widgets.grid.GridCheckbox import GridCheckbox
from ..resources.widgets.grid.GridLabel import GridLabel
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons


class RasterSamplerDialog(BasePluginMTL):
    """Dialog de amostragem de valores de rasters."""

    TOOL_KEY = ToolKey.RASTER_SAMPLER

    def __init__(self, iface):
        """Inicializa a dialog com a interface do QGIS."""
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.init(
            tool_key=self.TOOL_KEY, class_name="RasterSamplerDialog", build_ui=True
        )

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self, **kwargs):
        """Constroi a interface com checkboxes de rasters e labels de valores."""
        super()._build_ui(
            title=STR.RASTER_SAMPLER_TITLE,
            icon_path="cadmus_icon.ico",
            enable_scroll=True,
        )

        # ── Selecao de rasters (uma checkbox por raster do projeto) ──
        self.raster_checkboxes = GridCheckbox(
            config=self._build_raster_checkbox_config(),
            title=STR.RASTER_SAMPLER_SELECT_RASTERS,
            items_per_row=1,
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self.raster_checkboxes)

        # ── Labels de valores (um por raster do projeto) ──
        self.values_label = GridLabel(
            config=self._build_values_label_config(),
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self.values_label)

        # ── Botoes (Fechar + Info) ──
        self.action_buttons = GridExecutionButtons(
            config={},
            enable_close_button=True,
            enable_info=True,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.layout.add_execution_buttons(self.action_buttons)

    def _get_raster_layers(self) -> list:
        """Retorna as camadas raster do projeto via ProjectUtils."""
        return ProjectUtils.get_all_layers(
            project=ProjectUtils.get_project_instance(),
            layer_type="raster",
            logger=self.logger,
        )

    def _build_raster_checkbox_config(self) -> dict:
        """
        Constroi o config dict do GridCheckbox com um item por raster.

        Chave = layer.id(), label = nome da camada.
        """
        config = {}
        for layer in self._get_raster_layers():
            config[layer.id()] = {"label": layer.name()}
        return config

    def _build_values_label_config(self) -> dict:
        """
        Constroi o config dict do GridLabel com um label por raster.

        Chave = layer.id(), texto inicial = hint.
        """
        config = {"hint": {"text": STR.RASTER_SAMPLER_CLICK_CANVAS_HINT}}
        for layer in self._get_raster_layers():
            config[layer.id()] = {"text": ""}
        return config

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------
    def get_selected_raster_ids(self) -> list:
        """Retorna lista de layer.id() dos rasters selecionados."""
        return self.raster_checkboxes.get_checked_keys()

    def set_selected_raster_ids(self, ids: list):
        """Marca os rasters informados e desmarca os demais."""
        self.raster_checkboxes.set_checked_keys(ids)

    def refresh_raster_list(self):
        """
        Recarrega a lista de rasters do projeto mantendo a selecao atual
        para camadas que ainda existem.
        """
        previous = set(self.get_selected_raster_ids())
        new_config = self._build_raster_checkbox_config()

        # Restaura selecao apenas das camadas que ainda existem
        self.raster_checkboxes.set_checked_keys(
            [key for key in previous if key in new_config]
        )

    def set_raster_values(self, values: dict):
        """
        Atualiza os labels com os valores amostrados.

        values: dict {layer_id: valor} — valor pode ser float ou None (NoData).
        """
        config = {}
        for layer_id, value in values.items():
            layer = ProjectUtils.get_project_instance().mapLayer(layer_id)
            if layer is None:
                continue
            if value is None:
                text = STR.UNAVAILABLE
            else:
                text = f"{value:.4f}"
            config[layer_id] = {"text": f"{layer.name()}: {text}"}
        config["hint"] = {"text": ""}
        self.values_label.set_config(config)

    def clear_values(self):
        """Limpa os valores exibidos."""
        config = {"hint": {"text": STR.RASTER_SAMPLER_CLICK_CANVAS_HINT}}
        for layer_id in self.get_selected_raster_ids():
            config[layer_id] = {"text": ""}
        self.values_label.set_config(config)

    # ------------------------------------------------------------------
    # Preferencias
    # ------------------------------------------------------------------
    def _load_prefs(self):
        """Carrega os rasters selecionados das preferencias."""
        saved_ids = self.preferences.get("selected_rasters", [])
        self.set_selected_raster_ids([i for i in saved_ids if i])
        self.logger.debug(
            f"_load_prefs: selecao restaurada: {self.get_selected_raster_ids()}"
        )

    def _save_prefs(self):
        """Salva os rasters selecionados nas preferencias."""
        self.preferences["selected_rasters"] = self.get_selected_raster_ids()
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
        self.logger.debug(
            f"_save_prefs: prefs salvas: {self.preferences.get('selected_rasters')}"
        )