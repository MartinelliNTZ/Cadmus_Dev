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

    # Paleta de 5 cores para enumeracao dos rasters (CSS hex)
    RASTER_COLORS = [
        "#16A085",  # 1 - verde
        "#E67E22",  # 2 - laranja
        "#2980B9",  # 3 - azul
        "#C0392B",  # 4 - vermelho
        "#8E44AD",  # 5 - roxo
    ]

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
        # Stretch para empurrar todos os itens do GridLabel para cima
        self.layout.addStretch()

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

    def _get_selected_layers_ordered(self) -> list:
        """
        Retorna as camadas selecionadas na ordem do projeto.

        Usa a ordem natural de _get_raster_layers() filtrada pela
        selecao atual, garantindo enumeracao estavel e consistente.
        """
        return [
            layer
            for layer in self._get_raster_layers()
            if layer.id() in self._selected_raster_ids
        ]

    def _raster_color(self, index: int) -> str:
        """
        Retorna a cor da paleta para o raster na posicao (1-based).

        Reinicia o ciclo a cada 5 rasters.
        """
        return self.RASTER_COLORS[(index - 1) % len(self.RASTER_COLORS)]

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
            self._rebuild_labels()
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
        self._rebuild_labels()

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
        self._rebuild_labels()

    def _rebuild_labels(self):
        """
        Reconstrói os labels com a quantidade atual de rasters selecionados.

        Cada linha exibe a enumeração na cor do próprio raster e os diffs
        na cor do raster referenciado. Formato HTML:

            1 - <span color verde>MDS_N</span>: 188.2000
                &emsp;<span color laranja>(2: 0.21)</span>
                &emsp;<span color azul>(3: 0.24)</span>
        """
        config = {"hint": {"text": STR.RASTER_SAMPLER_CLICK_CANVAS_HINT}}
        layers = self._get_selected_layers_ordered()
        for i, layer in enumerate(layers, start=1):
            color = self._raster_color(i)
            config[layer.id()] = {
                "text": (
                    f"<span style='color:{color};'><b>{i} - {layer.name()}</b></span>:"
                )
            }
        self.values_label.rebuild(config)

    def set_raster_values(self, values: dict):
        """
        Atualiza os labels com os valores amostrados.

        Exibe cada raster enumerado com seu valor e a diferenca
        para os demais rasters selecionados. Formato:

            1 - <span verde>MDS_N</span>: 188.20
                &emsp;<span laranja>(2: 0.21)</span>
                &emsp;<span azul>(3: 0.24)</span>
            2 - <span laranja>MDS_x</span>: 18.50
                &emsp;<span verde>(1: -0.21)</span>
                &emsp;<span azul>(3: 0.24)</span>

        O nome de cada raster aparece na cor da paleta dele, e cada
        diferenca "(N: X.XX)" aparece na cor do raster N referenciado,
        facilitando a associacao visual.

        values: dict {layer_id: valor} — valor pode ser float ou None (NoData).
        """
        config = {}
        layers = self._get_selected_layers_ordered()
        for i, layer in enumerate(layers, start=1):
            color = self._raster_color(i)
            value = values.get(layer.id())
            if value is None:
                config[layer.id()] = {
                    "text": (
                        f"<span style='color:{color};'><b>{i} - {layer.name()}</b></span>"
                        f": {STR.UNAVAILABLE}"
                    )
                }
                continue

            parts = []
            for j, other in enumerate(layers, start=1):
                if j == i:
                    continue
                other_value = values.get(other.id())
                if other_value is not None:
                    other_color = self._raster_color(j)
                    parts.append(
                        f"&emsp;<span style='color:{other_color};'>"
                        f"({j}: {value - other_value:.2f})</span>"
                    )
            config[layer.id()] = {
                "text": (
                    f"<span style='color:{color};'><b>{i} - {layer.name()}</b></span>"
                    f": {value:.4f}{''.join(parts)}"
                )
            }
        config["hint"] = {"text": ""}
        self.values_label.set_config(config)

    def clear_values(self):
        """Limpa os valores exibidos mantendo a enumeracao e as cores."""
        config = {"hint": {"text": STR.RASTER_SAMPLER_CLICK_CANVAS_HINT}}
        for i, layer in enumerate(self._get_selected_layers_ordered(), start=1):
            color = self._raster_color(i)
            config[layer.id()] = {
                "text": (
                    f"<span style='color:{color};'><b>{i} - {layer.name()}</b></span>:"
                )
            }
        self.values_label.set_config(config)

    # ------------------------------------------------------------------
    # Preferencias
    # ------------------------------------------------------------------
    def _load_prefs(self):
        """Carrega os rasters selecionados das preferencias."""
        saved_ids = self.preferences.get("selected_rasters", [])
        self._selected_raster_ids = set(i for i in saved_ids if i)
        self._update_selection_button_label()
        self._rebuild_labels()
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