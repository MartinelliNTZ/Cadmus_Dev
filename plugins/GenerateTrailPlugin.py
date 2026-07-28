# -*- coding: utf-8 -*-
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes, QgsMapLayerProxyModel
from typing import Optional, Tuple
from ..plugins.BasePlugin import BasePluginMTL
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.vector.VectorLayerGeometry import VectorLayerGeometry
from ..utils.vector.VectorLayerProjection import VectorLayerProjection
from ..utils.vector.VectorLayerSource import VectorLayerSource
from ..utils.Preferences import Preferences
from ..utils.ToolKeys import ToolKey
from ..core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from ..core.engine_tasks.BufferStep import BufferStep
from ..core.engine_tasks.ExecutionContext import ExecutionContext
from ..core.engine_tasks.ExplodeStep import ExplodeStep
from ..core.engine_tasks.SaveVectorStep import SaveVectorStep
from ..i18n.TranslationManager import STR
from ..resources.new_widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.new_widgets.grid.GridDoubleSpin import GridDoubleSpin
from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.new_widgets.CollapsibleParametersWidget import (
    CollapsibleParametersWidget,
)


class GenerateTrailPlugin(BasePluginMTL):
    # Essa é uma ferramenta de janela com geração de produtos: do tipo vetoriais.
    # O valor inicial ainda existe como fallback caso as preferências globais
    # não sejam carregadas. O padrão atualizado é 20 MB.

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        # precisamos das preferências globais (Settings) para ler o limiar
        # assíncrono definido pelo usuário
        self.init(
            ToolKey.GENERATE_TRAIL,
            "GenerateTrailPlugin",
            load_system_prefs=True,
        )

    def _build_ui(self, **kwargs):
        self.logger.debug("Inicializando PLUGIN Gerar Rastro Implemento")
        super()._build_ui(
            title=STR.GENERATE_TRAIL_TITLE,
            icon_path="gerar_rastro.ico",
            enable_scroll=True,
        )
        self.logger.info("Construindo interface da ferramenta")

        # GridComplexSelector: Input + Output
        self.grid = GridComplexSelector(
            config={
                "input_layer": {
                    "label": f"{STR.INPUT_LINE_LAYER}:",
                    "mode_type": "input",
                    "allow_file": False,
                    "allow_folder": False,
                    "layer_filters": QgsMapLayerProxyModel.LineLayer,
                    # Lock check (bloqueia widget quando desmarcado)
                    # Features check (somente feições selecionadas)
                    "allow_features_check": True,
                    "allow_layer": True,
                    "features_check_text": STR.ONLY_SELECTED_FEATURES,
                },
                "output_trail": {
                    "label": f"{STR.SAVE_TRAIL_IN}:",
                    "mode_type": "output",
                    "parent": "input_layer",
                    "suffix": "_trail",
                    "fixed_extension": "gpkg",
                    "subfolder": "",
                    "fixed_name": "implement_trail",
                    "allow_file": True,
                    "allow_folder": True,
                    "file_filter": "GeoPackage (*.gpkg)",
                    # Lock check (bloqueia widget quando desmarcado)
                    "allow_lock_check": True,
                    "lock_check_default": True,
                },
            },
            tool_key=self.TOOL_KEY,
            separator_bottom=True,
            parent=self,
        )
        self.logger.debug("GridComplexSelector input+output adicionado")
        self.layout.addWidget(self.grid)

        # GridDoubleSpin: Implement Size
        self.implement_spin = GridDoubleSpin(
            config={
                "implement_size": {
                    "label": f"{STR.IMPLEMENT_SIZE}:",
                    "value": 3500,
                    "min": 10,
                    "max": 50000,
                    "step": 100,
                    "decimals": 0,
                    "type": "int",
                },
            },
            separator_bottom=True,
            parent=self,
        )
        self.logger.debug("GridDoubleSpin tamanho implemento adicionado")
        self.layout.addWidget(self.implement_spin)

        # CollapsibleParameters: Advanced
        self.advanced_params = CollapsibleParametersWidget(
            title=STR.ADVANCED_PARAMETERS,
            expanded_by_default=False,
            parent=self,
        )

        # GridComplexSelector QML (dentro do collapsible)
        self.qml_grid = GridComplexSelector(
            config={
                "qml_style": {
                    "label": f"{STR.QML_STYLE}:",
                    "mode_type": "input",
                    "allow_file": True,
                    "allow_folder": False,
                    "file_filter": "QML (*.qml)",
                    "allow_lock_check": True,
                    "lock_check_default": True,
                },
            },
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.logger.debug("GridComplexSelector QML adicionado")
        self.advanced_params.add_content_widget(self.qml_grid)
        self.layout.addWidget(self.advanced_params)

        # GridExecutionButtons
        self.action_buttons = GridExecutionButtons(
            config={
                "run": {
                    "label": STR.EXECUTE,
                    "description": "Gera o rastro do implemento",
                    "callback": self.execute_tool,
                    "is_run_button": True,
                },
            },
            enable_close_button=True,
            enable_info=True,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.logger.info("Interface da ferramenta construída com sucesso")
        self.layout.add_execution_buttons(self.action_buttons)

    def _load_prefs(self):
        self.logger.debug(f"Carregando preferências salvas da ferramenta. Self={self}")

        # Carrega GridComplexSelector (paths + lock_state + checked_state)
        grid_prefs = self.preferences.get("grid", {})
        if grid_prefs:
            self.grid.set_preferences(grid_prefs)

        # Carrega QML GridComplexSelector
        qml_prefs = self.preferences.get("qml_grid", {})
        if qml_prefs:
            self.qml_grid.set_preferences(qml_prefs)

        # Carrega CollapsibleParametersWidget (estado expandido)
        collapsible_prefs = self.preferences.get("advanced_params", {})
        if collapsible_prefs:
            self.advanced_params.set_preferences(collapsible_prefs)

        # Carrega GridDoubleSpin (tamanho do implemento)
        last_tam = self.preferences.get("last_implement_length")
        if last_tam is not None:
            try:
                self.implement_spin.set_value("implement_size", float(last_tam))
            except Exception as e:
                self.logger.warning(
                    f"Valor de tamanho do implemento inválido nas preferências: {last_tam}. Erro: {str(e)}"
                )

        self.logger.debug("Preferências carregadas e aplicadas com sucesso")

    def _save_prefs(self):
        self.logger.debug("Salvando preferências da ferramenta")

        # Salva GridComplexSelector (paths + lock_state + checked_state)
        self.preferences["grid"] = self.grid.get_preferences()

        # Salva QML GridComplexSelector
        self.preferences["qml_grid"] = self.qml_grid.get_preferences()

        # Salva CollapsibleParametersWidget (estado expandido)
        self.preferences["advanced_params"] = self.advanced_params.get_preferences()

        # Salva GridDoubleSpin (tamanho do implemento)
        self.preferences["last_implement_length"] = float(
            self.implement_spin.get_value("implement_size")
        )

        # Salva dimensões da janela
        self.preferences["window_width"] = self.width()
        self.preferences["window_height"] = self.height()

        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
        self.logger.debug(
            f"Preferências salvas: tamanho={self.preferences['last_implement_length']}m, "
            f"expanded={self.preferences.get('advanced_params', {}).get('expanded', False)}"
        )

    def execute_tool(self):
        self.logger.info("Iniciando processamento: Gerar Rastro Implemento")

        input_layer = self.grid.get("input_layer").current_layer
        self.start_stats(input_layer)

        if not isinstance(input_layer, QgsVectorLayer):
            self.logger.warning("Nenhuma camada de linhas válida selecionada")
            QgisMessageUtil.bar_warning(self.iface, STR.SELECT_VALID_LINE_LAYER)
            return

        only_selected = self.grid.get_checked_state("input_layer")
        implement_length = self.implement_spin.get_value("implement_size")
        output_path = self.grid.get_path("output_trail")
        save_to_folder = bool(output_path)
        output_name = STR.IMPLEMENT_TRAIL

        self.logger.info(
            f"Parâmetros: camada='{input_layer.name()}', tamanho={implement_length}m, "
            f"selecionadas={only_selected}, salvar_arquivo={save_to_folder}"
        )

        layer, implement_length = self._resolve_input_layer(
            input_layer, implement_length
        )
        if layer is None:
            self.logger.warning("_resolve_input_layer returned None, aborting")
            return

        ok, error = VectorLayerSource.validate_layer(
            layer, expected_geometry=QgsWkbTypes.LineGeometry
        )
        if not ok:
            self.logger.error(f"Layer validation failed: {error}")
            QgisMessageUtil.modal_error(self.iface, error)
            return

        layer = self._process_selection(layer, only_selected)
        if layer is None:
            self.logger.warning("_process_selection returned None, aborting")
            return

        if implement_length == 0:
            self.logger.error("implement_length is zero, aborting")
            QgisMessageUtil.modal_error(self.iface, STR.BUFFER_CANNOT_BE_ZERO)
            return

        buffer_distance = float(implement_length) / 2.0

        context = ExecutionContext()
        context.set("layer", layer)
        context.set("save_to_folder", save_to_folder)
        context.set("output_path", output_path)
        context.set("output_name", output_name)
        context.set("tool_key", self.TOOL_KEY)
        context.set("buffer_distance", buffer_distance)
        context.set("buffer_dissolve", False)

        feature_count = layer.featureCount() if layer else 0
        threshold = int(self.system_preferences.get("async_threshold_features", 1000))
        self.logger.debug(
            f"Comparando feições: {feature_count} versus {threshold} (limiar)"
        )

        if feature_count > threshold:
            self.logger.info("Processamento iniciado em background (assíncrono)")
            self._run_async_pipeline(context)
        else:
            self.logger.info("Executando processamento de forma síncrona")
            self._run_sync_pipeline(context)

    def _resolve_input_layer(
        self, input_layer, implement_length: float
    ) -> Tuple[Optional[QgsVectorLayer], float]:
        """Etapa 1: Resolver camada de entrada e converter tamanho se necessário"""
        layer = (
            input_layer
            if isinstance(input_layer, QgsVectorLayer)
            else QgsProject.instance().mapLayer(input_layer)
        )
        self.logger.debug(f"Camada resolvida: {layer.name() if layer else 'None'}")

        if not isinstance(layer, QgsVectorLayer):
            self.logger.error("Camada de entrada inválida - não é QgsVectorLayer")
            QgisMessageUtil.modal_error(self.iface, STR.INVALID_INPUT_LAYER)
            return None, implement_length

        implement_length = VectorLayerProjection.convert_distance_to_layer_units(
            layer, implement_length
        )
        return layer, implement_length

    def _process_selection(
        self, layer: QgsVectorLayer, only_selected: bool
    ) -> Optional[QgsVectorLayer]:
        """Etapa 3: Processar seleção de feições"""
        self.logger.info("3/6] Processando seleção de feições")
        if only_selected:
            self.logger.debug(
                f"Filtrando apenas feições selecionadas. Total selecionadas: {layer.selectedFeatureCount()}"
            )
            layer_sel, err = VectorLayerGeometry.get_selected_features(layer)
            if err:
                self.logger.error(f"Erro ao obter feições selecionadas: {err}")
                QgisMessageUtil.modal_error(self.iface, err)
                return None
            layer = layer_sel
            self.logger.debug(f"Usando camada com feições selecionadas: {layer.name()}")
        else:
            self.logger.debug(
                f"Processando todas as feições da camada. Total: {layer.featureCount()}"
            )
        return layer

    def _run_sync_pipeline(self, context: ExecutionContext) -> Optional[QgsVectorLayer]:
        """
        Executa a pipeline de forma síncrona:
        Explode -> Buffer -> Save
        Retorna camada final.
        """
        try:
            layer = context.get("layer")
            if not layer or not layer.isValid():
                raise RuntimeError(STR.INVALID_INPUT_LAYER)

            save_to_folder = context.get("save_to_folder")
            output_path = context.get("output_path")
            output_name = context.get("output_name")
            buffer_distance = context.get("buffer_distance")
            dissolve = context.get("buffer_dissolve")

            self.logger.debug("SYNC: ExplodeStep")
            exploded = VectorLayerGeometry.explode_multipart_features(
                layer=layer, external_tool_key=self.TOOL_KEY
            )
            if not exploded or not exploded.isValid():
                raise RuntimeError("Falha no explode")

            self.logger.debug("SYNC: BufferStep")
            buffered = VectorLayerGeometry.create_buffer_geometry(
                layer=exploded,
                distance=buffer_distance,
                dissolve=dissolve,
                external_tool_key=self.TOOL_KEY,
            )
            if not buffered or not buffered.isValid():
                raise RuntimeError("Falha no buffer")

            self.logger.debug("SYNC: SaveVectorStep")
            final_layer = VectorLayerSource.save_vector_layer(
                layer=buffered,
                output_path=output_path,
                save_to_folder=save_to_folder,
                output_name=output_name,
                external_tool_key=self.TOOL_KEY,
            )
            if not final_layer or not final_layer.isValid():
                raise RuntimeError("Falha ao salvar camada")

            context.set("layer", final_layer)
            self._on_pipeline_finished(context)
            return final_layer

        except Exception as e:
            self.logger.error(f"Erro pipeline SYNC: {e}. Contexto: {context}.")
            QgisMessageUtil.modal_error(self.iface, str(e))
            return None

    def _run_async_pipeline(self, context: ExecutionContext):
        engine = AsyncPipelineEngine(
            steps=[ExplodeStep(), BufferStep(), SaveVectorStep()],
            context=context,
            on_finished=self._on_pipeline_finished,
            on_error=self._on_pipeline_error,
        )
        self.logger.info("Starting AsyncPipelineEngine")
        engine.start()

    def _on_pipeline_finished(self, context):
        final_layer = context.get("layer")
        if not final_layer:
            QgisMessageUtil.modal_error(self.iface, STR.FINAL_LAYER_NOT_FOUND)
            return

        if not QgsProject.instance().mapLayer(final_layer.id()):
            QgsProject.instance().addMapLayer(final_layer)

        if self.qml_grid.get_path("qml_style"):
            qml = self.qml_grid.get_path("qml_style")
            self.apply_qml_style(final_layer, qml)
            self.logger.info("QML style applied to final layer")

        QgisMessageUtil.bar_success(self.iface, STR.SUCCESS_MESSAGE)
        self.finish_stats()


def run(iface):
    dlg = GenerateTrailPlugin(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg
