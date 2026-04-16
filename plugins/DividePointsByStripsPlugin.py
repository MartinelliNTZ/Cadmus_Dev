# -*- coding: utf-8 -*-

from qgis.core import (
    QgsMapLayerProxyModel,
    QgsVectorLayer,
    QgsProject,
    QgsField,
    QgsFeature,
)

from .BasePlugin import BasePluginMTL
from ..core.ui.WidgetFactory import WidgetFactory
from ..i18n.TranslationManager import STR
from ..utils.Preferences import load_tool_prefs, save_tool_prefs
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.StringManager import StringManager
from ..utils.ToolKeys import ToolKey
from ..utils.adapter.StringAdapter import StringAdapter
from ..utils.judge.SequentialPointBreakJudge import SequentialPointBreakJudge
from ..utils.vector.VectorLayerAttributes import VectorLayerAttributes
from ..utils.vector.VectorLayerSource import VectorLayerSource


class DividePointsByStripsPlugin(BasePluginMTL):
    TOOL_KEY = ToolKey.DIVIDE_POINTS_BY_STRIPS
    PREF_SELECTED_OUTPUT_FIELDS = "selected_output_fields"
    REQUIRED_OUTPUT_FIELD = "shot_id"

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.save_points_selector = None
        self.init(
            tool_key=self.TOOL_KEY,
            class_name=self.__class__.__name__,
            build_ui=True,
        )

    def _build_ui(self, **kwargs):
        super()._build_ui(
            title=STR.DIVIDE_POINTS_BY_STRIPS_TITLE,
            icon_path="vector.ico",
            enable_scroll=True,
        )

        intro_label = WidgetFactory.create_label(
            text=STR.DIVIDE_POINTS_BY_STRIPS_INTRO,
            word_wrap=True,
            parent=self,
        )

        layer_layout, self.layer_input = WidgetFactory.create_layer_input(
            label_text=STR.INPUT_POINTS,
            filters=[QgsMapLayerProxyModel.PointLayer],
            allow_empty=False,
            enable_selected_checkbox=False,
            parent=self,
            separator_top=False,
            separator_bottom=True,
        )
        self.layer_input.layerChanged.connect(self._on_layer_changed)

        operational_container_layout, self.operational_params = (
            WidgetFactory.create_collapsible_parameters(
                parent=self,
                title=STR.OPERATIONAL_PARAMETERS,
                expanded_by_default=True,
                separator_top=False,
                separator_bottom=True,
            )
        )
        id_field_layout, self.id_field_selector = (
            WidgetFactory.create_dropdown_selector(
                title=STR.UNIQUE_SEQUENTIAL_ID_FIELD,
                options_dict={},
                allow_empty=True,
                empty_text=STR.SELECT,
                parent=self,
                separator_top=False,
                separator_bottom=False,
            )
        )
        time_field_layout, self.time_field_selector = (
            WidgetFactory.create_dropdown_selector(
                title=STR.TIMESTAMP_FIELD,
                options_dict={},
                allow_empty=True,
                empty_text=STR.SELECT,
                parent=self,
                separator_top=False,
                separator_bottom=False,
            )
        )
        operational_layout, self.operational_fields = (
            WidgetFactory.create_input_fields_widget(
                fields_dict={
                    "frequencia_pontos": {
                        "title": STR.EXPECTED_POINT_FREQUENCY_SECONDS,
                        "type": "int",
                        "default": 1,
                    },
                    "largura_tiro": {
                        "title": STR.EXPECTED_LATERAL_WIDTH_METERS,
                        "type": "float",
                        "default": 20.0,
                    },
                },
                parent=self,
                separator_top=False,
                separator_bottom=False,
            )
        )
        self.operational_params.add_content_layout(id_field_layout)
        self.operational_params.add_content_layout(time_field_layout)
        self.operational_params.add_content_layout(operational_layout)

        sensitivity_layout, self.sensitivity_fields = (
            WidgetFactory.create_input_fields_widget(
                fields_dict={
                    "janela_azimute": {
                        "title": STR.AZIMUTH_MOVING_WINDOW,
                        "description": "Número de pontos usados para calcular a direção média antes de detectar mudança de rumo.",
                        "type": "int",
                        "default": 10,
                    },
                    "threshold_azimute_leve": {
                        "title": STR.LIGHT_AZIMUTH_DEVIATION_THRESHOLD,
                        "description": "Desvio leve de azimute que inicia a identificação de uma possível quebra.",
                        "type": "float",
                        "default": 20.0,
                    },
                    "threshold_azimute_grave": {
                        "title": STR.SEVERE_AZIMUTH_DEVIATION_THRESHOLD,
                        "description": "Desvio alto de azimute que indica uma mudança de direção clara.",
                        "type": "float",
                        "default": 45.0,
                    },
                    "score_minimo_quebra": {
                        "title": STR.MINIMUM_BREAK_SCORE,
                        "description": "Pontos necessários para que o desvio seja considerado uma quebra real.",
                        "type": "int",
                        "default": 3,
                    },
                    "n_minimo_pontos": {
                        "title": STR.MINIMUM_POINT_COUNT,
                        "description": "Menor quantidade de pontos que um trecho precisa para ser aceito.",
                        "type": "int",
                        "default": 20,
                    },
                    "tolerancia_tempo": {
                        "title": STR.TIME_TOLERANCE_MULTIPLIER,
                        "description": "Multiplica a diferença de tempo permitida entre fotos para evitar quebra por pequenas variações.",
                        "type": "float",
                        "default": 3.0,
                    },
                    "max_desvio": {
                        "title": "Número máx de pontos desvio",
                        "description": "Máximo de pontos fora do padrão que serão ignorados antes de confirmar a quebra.",
                        "type": "int",
                        "default": 5,
                    },
                },
                parent=self,
                separator_top=False,
                separator_bottom=False,
            )
        )

        advanced_layout, self.advanced_params = (
            WidgetFactory.create_collapsible_parameters(
                parent=self,
                title=STR.SENSITIVITY_PARAMETERS,
                expanded_by_default=True,
                separator_top=False,
                separator_bottom=True,
            )
        )
        self.advanced_params.add_content_layout(sensitivity_layout)

        output_layout, self.output_fields_grid = WidgetFactory.create_checkbox_grid(
            options_data=StringAdapter.to_key_label_description(
                SequentialPointBreakJudge.OUTPUT_FIELDS
            ),
            items_per_row=2,
            checked_by_default=True,
            show_control_buttons=True,
            return_widget=True,
            separator_top=False,
            separator_bottom=False,
        )
        self.output_fields_grid.set_checked_keys(["shot_id"])
        shot_id_checkbox = self.output_fields_grid.get_checkbox("shot_id")
        if shot_id_checkbox is not None:
            shot_id_checkbox.setChecked(True)
            shot_id_checkbox.setEnabled(False)

        attributes_layout, self.attributes_params = (
            WidgetFactory.create_collapsible_parameters(
                parent=self,
                title=STR.ATTRIBUTES,
                expanded_by_default=True,
                separator_top=False,
                separator_bottom=True,
            )
        )
        self.attributes_params.add_content_layout(output_layout)

        save_layout, self.save_collapsible, self.save_points_selector = (
            WidgetFactory.create_save_layer_collapsible(
                parent=self,
                title=STR.SAVING,
                expanded_by_default=False,
                file_filter=StringManager.FILTER_VECTOR,
                checkbox_text=STR.SAVE_POINTS_CHECKBOX,
                label_text=STR.SAVE_IN,
                separator_top=False,
                separator_bottom=True,
            )
        )

        buttons_layout, self.action_buttons = (
            WidgetFactory.create_bottom_action_buttons(
                parent=self,
                run_callback=self.execute_tool,
                close_callback=self.close,
                info_callback=self.show_info_dialog,
                tool_key=self.TOOL_KEY,
                separator_top=False,
                separator_bottom=False,
            )
        )

        self.layout.add_items(
            [
                intro_label,
                layer_layout,
                operational_container_layout,
                advanced_layout,
                attributes_layout,
                save_layout,
                buttons_layout,
            ]
        )
        self._refresh_field_selectors()

    def _load_prefs(self):
        #self.preferences = load_tool_prefs(self.TOOL_KEY)
        self.id_field = self.preferences.get("id_field", "")
        self.time_field = self.preferences.get("time_field", "")
        operational_fields = self.preferences.get("operational_fields", {})
        if (
            "largura_lateral" in operational_fields
            and "largura_tiro" not in operational_fields
        ):
            operational_fields["largura_tiro"] = operational_fields["largura_lateral"]
        self.operational_fields.set_values(operational_fields)
        self.sensitivity_fields.set_values(
            self.preferences.get("sensitivity_fields", {})
        )
        selected_output_fields = self.preferences.get(
            self.PREF_SELECTED_OUTPUT_FIELDS, []
        )
        normalized_selected = self._normalize_selected_output_fields(
            selected_output_fields
        )

        self.output_fields_grid.set_checked_keys(normalized_selected)
        shot_id_checkbox = self.output_fields_grid.get_checkbox(
            self.REQUIRED_OUTPUT_FIELD
        )
        if shot_id_checkbox is not None:
            shot_id_checkbox.setChecked(True)
            shot_id_checkbox.setEnabled(False)

        self.save_points_selector.set_enabled(
            self.preferences.get("save_layer_enabled", False)
        )
        self.save_points_selector.set_file_path(
            self.preferences.get("save_layer_path", "")
        )
        self._refresh_field_selectors()

    def _save_prefs(self):
        self.preferences["id_field"] = self.id_field_selector.get_selected_key() or ""
        self.preferences["time_field"] = (
            self.time_field_selector.get_selected_key() or ""
        )
        self.preferences["operational_fields"] = self.operational_fields.get_values()
        self.preferences["sensitivity_fields"] = self.sensitivity_fields.get_values()
        self.preferences[self.PREF_SELECTED_OUTPUT_FIELDS] = (
            self._get_selected_output_fields()
        )
        self.preferences["save_layer_enabled"] = self.save_points_selector.is_enabled()
        self.preferences["save_layer_path"] = self.save_points_selector.get_file_path()
        self.preferences["window_width"] = self.width()
        self.preferences["window_height"] = self.height()
        save_tool_prefs(self.TOOL_KEY, self.preferences)

    def _on_layer_changed(self, _layer):
        self._refresh_field_selectors()

    def _normalize_selected_output_fields(self, selected_output_fields):
        normalized = []
        for value in selected_output_fields or []:
            if hasattr(value, "value"):
                normalized.append(str(value.value))
            else:
                normalized.append(str(value))
        normalized = [v for v in normalized if v]
        if self.REQUIRED_OUTPUT_FIELD not in normalized:
            normalized.append(self.REQUIRED_OUTPUT_FIELD)
        return normalized

    def _get_selected_output_fields(self):
        selected = (
            self.output_fields_grid.get_checked_keys()
            if hasattr(self, "output_fields_grid")
            else []
        )
        return self._normalize_selected_output_fields(selected)

    @staticmethod
    def _resolve_field_name_from_map(field_name_map, logical_key):
        if not isinstance(field_name_map, dict):
            return None
        key_value = logical_key.value if hasattr(logical_key, "value") else logical_key
        return (
            field_name_map.get(logical_key)
            or field_name_map.get(key_value)
            or field_name_map.get(str(key_value))
        )

    def _build_filtered_result_layer(
        self, layer, selected_output_fields, field_name_map
    ):
        """Cria um layer temporário com apenas os campos selecionados para salvar."""
        if not layer or not layer.isValid():
            return layer

        if not selected_output_fields or not field_name_map:
            return layer

        normalized_selected = set(
            self._normalize_selected_output_fields(selected_output_fields)
        )
        selected_keys = [
            key
            for key in SequentialPointBreakJudge.OUTPUT_FIELDS.keys()
            if key.value in normalized_selected
        ]

        selected_field_names = [
            self._resolve_field_name_from_map(field_name_map, key)
            for key in selected_keys
            if self._resolve_field_name_from_map(field_name_map, key)
        ]

        if not selected_field_names:
            return layer

        uri = f"Point?crs={layer.crs().authid()}"
        filtered_layer = QgsVectorLayer(uri, f"{layer.name()}_filtered", "memory")
        if not filtered_layer.isValid():
            return layer

        fields = []
        for logical_key in selected_keys:
            field_spec = SequentialPointBreakJudge.OUTPUT_FIELDS.get(logical_key)
            field_name = self._resolve_field_name_from_map(field_name_map, logical_key)
            if field_spec and field_name:
                fields.append(
                    QgsField(
                        field_name,
                        field_spec.type,
                        len=field_spec.length,
                        prec=field_spec.precision,
                    )
                )

        filtered_layer.dataProvider().addAttributes(fields)
        filtered_layer.updateFields()

        filtered_layer.startEditing()
        for feature in layer.getFeatures():
            new_feature = QgsFeature(filtered_layer.fields())
            new_feature.setGeometry(feature.geometry())
            for logical_key in selected_keys:
                resolved_name = self._resolve_field_name_from_map(
                    field_name_map, logical_key
                )
                if not resolved_name:
                    continue
                source_index = layer.fields().lookupField(resolved_name)
                target_index = filtered_layer.fields().lookupField(resolved_name)
                if source_index >= 0 and target_index >= 0:
                    new_feature.setAttribute(
                        target_index,
                        feature.attribute(source_index),
                    )
            filtered_layer.addFeature(new_feature)
        filtered_layer.commitChanges()
        filtered_layer.updateFields()
        return filtered_layer

    def _refresh_field_selectors(self):
        layer = self.layer_input.current_layer()
        options = VectorLayerAttributes.get_field_options(layer)

        selected_id = getattr(self, "id_field", "") or self.preferences.get(
            "id_field", ""
        )
        selected_time = getattr(self, "time_field", "") or self.preferences.get(
            "time_field", ""
        )

        self.id_field_selector.set_options(options)
        self.time_field_selector.set_options(options)

        if selected_id:
            self.id_field_selector.set_selected_key(selected_id)
        if selected_time:
            self.time_field_selector.set_selected_key(selected_time)

    def execute_tool(self):
        layer = self.layer_input.current_layer()
        if not isinstance(layer, QgsVectorLayer):
            QgisMessageUtil.bar_warning(self.iface, STR.SELECT_POINT_VECTOR_LAYER)
            return

        field_id = self.id_field_selector.get_selected_key()
        field_time = self.time_field_selector.get_selected_key()
        if not field_id or not field_time:
            QgisMessageUtil.bar_warning(self.iface, STR.SELECT_REQUIRED_FIELDS)
            return

        operational_values = self.operational_fields.get_values()
        sensitivity_values = self.sensitivity_fields.get_values()

        self.logger.info(
            "Executando segmentação de tiros em camada de pontos",
            layer=layer.name(),
            source_path=layer.source(),
            id_field=field_id,
            time_field=field_time,
            operational_fields=operational_values,
            sensitivity_fields=sensitivity_values,
        )

        import time

        start_time = time.time()
        self.logger.info("Iniciando processamento síncrono da segmentação")

        try:
            summary = SequentialPointBreakJudge(
                layer=layer,
                tool_key=self.TOOL_KEY,
            ).judge(
                field_id=field_id,
                field_time=field_time,
                point_frequency_seconds=float(
                    operational_values.get("frequencia_pontos", 1) or 1
                ),
                strip_width_meters=float(
                    operational_values.get("largura_tiro", 20.0) or 20.0
                ),
                azimuth_window=int(sensitivity_values.get("janela_azimute", 10) or 10),
                light_azimuth_threshold=float(
                    sensitivity_values.get("threshold_azimute_leve", 20.0) or 20.0
                ),
                severe_azimuth_threshold=float(
                    sensitivity_values.get("threshold_azimute_grave", 45.0) or 45.0
                ),
                minimum_break_score=int(
                    sensitivity_values.get("score_minimo_quebra", 3) or 3
                ),
                minimum_point_count=int(
                    sensitivity_values.get("n_minimo_pontos", 20) or 20
                ),
                time_tolerance_multiplier=float(
                    sensitivity_values.get("tolerancia_tempo", 3.0) or 3.0
                ),
                max_desvio=int(sensitivity_values.get("max_desvio", 5) or 5),
                confirmation_window=3,
                min_confirmed=2,
                border_azimuth_threshold=90.0,
                border_speed_threshold=1.0,
                border_distance_threshold=5.0,
                retroactive_window=5,
                fusion_azimuth_tolerance=10.0,
                conflict_resolver=lambda field_name: QgisMessageUtil.ask_field_conflict(
                    self.iface, field_name
                ),
            )
            processing_time = time.time() - start_time
            self.logger.info(
                "Segmentação concluída com sucesso",
                processing_time_seconds=round(processing_time, 2),
                summary=summary,
            )

            # Adicionar nova camada ao projeto
            result_layer = summary.get("result_layer")
            if result_layer and result_layer.isValid():
                QgsProject.instance().addMapLayer(result_layer)
                self.logger.info(
                    "Nova camada adicionada ao projeto", layer_name=result_layer.name()
                )
            else:
                self.logger.warning("Camada de resultado inválida ou não encontrada")

            if (
                hasattr(self, "save_points_selector")
                and self.save_points_selector
                and self.save_points_selector.is_enabled()
            ):
                out_path = self.save_points_selector.get_file_path().strip()
                if out_path:
                    selected_fields = self._get_selected_output_fields()
                    filtered_layer = self._build_filtered_result_layer(
                        result_layer,
                        selected_fields,
                        summary.get("field_name_map", {}),
                    )
                    saved_layer = VectorLayerSource.save_and_load_layer(
                        filtered_layer,
                        out_path,
                        tool_key=self.TOOL_KEY,
                        decision="rename",
                    )
                    if saved_layer and saved_layer.isValid():
                        QgsProject.instance().addMapLayer(saved_layer)
                        result_layer = saved_layer
                        self.logger.info(
                            "Camada salva e carregada", layer_name=saved_layer.name()
                        )
                    else:
                        self.logger.warning(
                            "Falha ao salvar camada de resultado selecionada"
                        )
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(
                f"Erro na segmentação de tiros após {processing_time:.2f}s: {e}",
                exception_details=str(e),
            )
            self.logger.exception(e)
            QgisMessageUtil.bar_critical(self.iface, f"{STR.ERROR}\n{e}")
            return

        try:
            layer.triggerRepaint()
        except Exception as e:
            self.logger.warning(
                f"Falha ao atualizar camada original após julgamento: {e}"
            )

        QgisMessageUtil.bar_success(
            self.iface,
            STR.SHOT_SEGMENTATION_BUFFER_COMPLETED.format(
                total_points=summary["total_points"],
                total_shots=summary["total_shots"],
                valid_shots=summary["valid_shots"],
                invalid_shots=summary["invalid_shots"],
            ),
            duration=8,
        )


def run(iface):
    dlg = DividePointsByStripsPlugin(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg
