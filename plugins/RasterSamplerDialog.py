# -*- coding: utf-8 -*-
"""
RasterSamplerDialog — Dialog da ferramenta de amostragem de rasters.
====================================================================
Herda BasePluginMTL (padrao CoordResultDialog).

Permite selecionar multiplos rasters do projeto via ListSelectionDialog,
exibe os valores amostrados no ponto clicado via GridLabel
e persiste a selecao via Preferences.
"""

from ..utils.ToolKeys import ToolKey
from ..utils.Preferences import Preferences
from ..utils.ProjectUtils import ProjectUtils
from ..i18n.TranslationManager import STR
from .BasePlugin import BasePluginMTL
from ..core.ui.dialogs.ListSelectionDialog import ListSelectionDialog
from ..resources.widgets.grid.GridLabel import GridLabel
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..utils.QgisMessageUtil import QgisMessageUtil


class RasterSamplerDialog(BasePluginMTL):
    """Dialog de amostragem de valores de rasters."""

    TOOL_KEY = ToolKey.RASTER_SAMPLER

    def __init__(self, iface):
        """Inicializa a dialog com a interface do QGIS."""
        super().__init__(iface.mainWindow())
        self.iface = iface
        self._selected_raster_ids = set()
        self.init(
            tool_key=self.TOOL_KEY, class_name="RasterSamplerDialog", build_ui=True
        )

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self, **kwargs):
        """Constroi a interface com botao de selecao e labels de valores."""
        super()._build_ui(
            title=STR.RASTER_SAMPLER_TITLE,
            icon_path="cadmus_icon.ico",
            enable_scroll=True,
        )

        # ── Labels de valores (um por raster selecionado) ──
        self.values_label = GridLabel(
            config=self._build_values_label_config(),
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self.values_label)

        # ── Botao de selecao de rasters ──
        self.action_buttons = GridExecutionButtons(
            config={
                "select_rasters": {
                    "label": STR.RASTER_SAMPLER_SELECT_RASTERS,
                    "description": "Seleciona quais rasters amostrar",
                    "callback": self.open_raster_selection,
                },
            },
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

    def _build_values_label_config(self) -> dict:
        """
        Constroi o config dict do GridLabel com um label por raster.

        Chave = layer.id(), texto inicial = hint.
        """
        config = {"hint": {"text": STR.RASTER_SAMPLER_CLICK_CANVAS_HINT}}
        for layer in self._get_raster_layers():
            config[layer.id()] = {"text": ""}
        return config

    def _update_selection_button_label(self):
        """Atualiza o texto do botao de selecao com a contagem de rasters."""
        count = len(self._selected_raster_ids)
        self.action_buttons.update_button_label(
            "select_rasters",
            f"{STR.RASTER_SAMPLER_SELECT_RASTERS} ({count})",
        )

    # ------------------------------------------------------------------
    # Selecao de rasters via ListSelectionDialog
    # ------------------------------------------------------------------
    def open_raster_selection(self):
        """Abre o dialogo de selecao de rasters."""
        self.logger.debug("Abrindo dialogo de selecao de rasters")

        layers = self._get_raster_layers()
        if not layers:
            QgisMessageUtil.modal_error(self.iface, STR.RASTER_SAMPLER_NO_RASTERS)
            return

        items = {}
        for layer in layers:
            items[layer.id()] = {
                "label": layer.name(),
                "default": layer.id() in self._selected_raster_ids,
            }

        dlg = ListSelectionDialog(
            items=items,
            title=STR.RASTER_SAMPLER_SELECT_RASTERS,
            hint=STR.RASTER_SAMPLER_SELECT_RASTERS,
            tool_key=self.TOOL_KEY,
            icon_path="cadmus_icon.ico",
            parent=self,
        )
        if dlg.exec():
            self._selected_raster_ids = set(dlg.get_selected_items())
            self._update_selection_button_label()
            self.logger.info(
                f"Rasters selecionados: {len(self._selected_raster_ids)}"
            )

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------
    def get_selected_raster_ids(self) -> list:
        """Retorna lista de layer.id() dos rasters selecionados."""
        return list(self._selected_raster_ids)

    def set_selected_raster_ids(self, ids: list):
        """Define os rasters selecionados."""
        self._selected_raster_ids = set(ids or [])
        self._update_selection_button_label()

    def refresh_raster_list(self):
        """
        Recarrega a lista de rasters do projeto mantendo a selecao atual
        para camadas que ainda existem.
        """
        current_ids = {layer.id() for layer in self._get_raster_layers()}
        self._selected_raster_ids = {
            rid for rid in self._selected_raster_ids if rid in current_ids
        }
        self._update_selection_button_label()

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
        for layer_id in self._selected_raster_ids:
            config[layer_id] = {"text": ""}
        self.values_label.set_config(config)

    # ------------------------------------------------------------------
    # Preferencias
    # ------------------------------------------------------------------
    def _load_prefs(self):
        """Carrega os rasters selecionados das preferencias."""
        saved_ids = self.preferences.get("selected_rasters", [])
        self._selected_raster_ids = set(i for i in saved_ids if i)
        self._update_selection_button_label()
        self.logger.debug(
            f"_load_prefs: selecao restaurada: {list(self._selected_raster_ids)}"
        )

    def _save_prefs(self):
        """Salva os rasters selecionados nas preferencias."""
        self.preferences["selected_rasters"] = list(self._selected_raster_ids)
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
        self.logger.debug(
            f"_save_prefs: prefs salvas: {self.preferences.get('selected_rasters')}"
        )