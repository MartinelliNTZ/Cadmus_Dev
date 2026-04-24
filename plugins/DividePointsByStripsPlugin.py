# -*- coding: utf-8 -*-

import time
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsVectorLayer,
    QgsProject,
    QgsField,
    QgsFeature,
    QgsGeometry,
)
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsProject

from .BasePlugin import BasePluginMTL
from ..core.ui.WidgetFactory import WidgetFactory
from ..i18n.TranslationManager import STR
from ..utils.Preferences import load_tool_prefs, save_tool_prefs
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.StringManager import StringManager
from ..utils.ToolKeys import ToolKey
from ..utils.adapter.StringAdapter import StringAdapter
from ..core.enum.OutputFieldKey import StripOutputFieldKey
from ..utils.judge.SequentialPointBreakJudge import SequentialPointBreakJudge
from ..utils.vector.VectorLayerAttributes import VectorLayerAttributes
from ..utils.vector.VectorLayerSource import VectorLayerSource
from ..utils.MathUtils import MathUtils


class DividePointsByStripsPlugin(BasePluginMTL):
    TOOL_KEY = ToolKey.DIVIDE_POINTS_BY_STRIPS
    PREF_SELECTED_OUTPUT_FIELDS = "selected_output_fields"
    REQUIRED_OUTPUT_FIELD = "shot_id"
    PATH_MODES = [STR.CURVE, STR.STRAIGHT, STR.BOTH_PATH]

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.save_points_selector = None
        self.save_track_selector = None
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
                fields_dict=StringManager.DIVIDE_POINTS_OPERATIONAL_FIELDS,
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
                fields_dict=StringManager.DIVIDE_POINTS_SENSITIVITY_FIELDS,
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

        radio_layout, self.radio_path_mode = WidgetFactory.create_radio_button_grid(
            items=self.PATH_MODES,
            columns=3,
            title=STR.SEGMENTATION_MODE,
            checked_index=2,
            tool_key=self.TOOL_KEY,
            parent=self,
            separator_top=False,
            separator_bottom=True,
        )

        output_layout, self.output_fields_grid = WidgetFactory.create_checkbox_grid(
            options_data=StringAdapter.to_key_label_description(
                SequentialPointBreakJudge.DIVIDE_STRIP_FIELDS
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

        # ====== SALVAMENTO (Expandido para Pontos e Linhas) ======
        save_layout, self.save_collapsible = (
            WidgetFactory.create_collapsible_parameters(
                parent=self,
                title=STR.SAVING,
                expanded_by_default=False,
                separator_bottom=True,
            )
        )
        save_pts_layout, self.save_points_selector = WidgetFactory.create_save_file_selector(
            parent=self,
            file_filter=StringManager.FILTER_VECTOR,
            checkbox_text=STR.SAVE_POINTS_CHECKBOX,
            label_text=STR.SAVE_IN,
        )
        save_lines_layout, self.save_track_selector = WidgetFactory.create_save_file_selector(
            parent=self,
            file_filter=StringManager.FILTER_VECTOR,
            checkbox_text=STR.SAVE_TRACK_CHECKBOX,
            label_text=STR.SAVE_IN,
        )
        self.save_collapsible.add_content_layout(save_pts_layout)
        self.save_collapsible.add_content_layout(save_lines_layout)

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
                radio_layout,
                operational_container_layout,
                advanced_layout,                
                attributes_layout,
                save_layout,
                buttons_layout,
            ]
        )
        self._refresh_field_selectors()

    def _load_prefs(self):
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

        path_mode = self.preferences.get("path_mode", STR.BOTH_PATH)
        if path_mode in self.PATH_MODES:
            self.radio_path_mode.set_selected_index(self.PATH_MODES.index(path_mode))

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
            self.preferences.get("save_to_folder", False)
        )
        self.save_points_selector.set_file_path(
            self.preferences.get("last_output_file", "")
        )
        self.save_track_selector.set_enabled(
            self.preferences.get("save_track_to_folder", False)
        )
        self.save_track_selector.set_file_path(
            self.preferences.get("last_output_track_file", "")
        )

        # Restaurar estado de expansão dos colapsáveis
        self.operational_params.set_expanded(self.preferences.get("expanded_operational", True))
        self.advanced_params.set_expanded(self.preferences.get("expanded_sensitivity", True))
        self.attributes_params.set_expanded(self.preferences.get("expanded_attributes", True))
        
        self.save_collapsible.set_expanded(self.preferences.get("expanded_save", False))

        self._refresh_field_selectors()

    def _save_prefs(self):
        self.preferences["id_field"] = self.id_field_selector.get_selected_key() or ""
        self.preferences["time_field"] = (
            self.time_field_selector.get_selected_key() or ""
        )
        self.preferences["operational_fields"] = self.operational_fields.get_values()
        self.preferences["sensitivity_fields"] = self.sensitivity_fields.get_values()
        self.preferences["path_mode"] = self.radio_path_mode.get_selected_text()
        self.preferences[self.PREF_SELECTED_OUTPUT_FIELDS] = (
            self._get_selected_output_fields()
        )
        self.preferences["save_to_folder"] = bool(self.save_points_selector.is_enabled())
        self.preferences["last_output_file"] = self.save_points_selector.get_file_path()
        self.preferences["save_track_to_folder"] = bool(self.save_track_selector.is_enabled())
        self.preferences["last_output_track_file"] = self.save_track_selector.get_file_path()
        self.preferences["window_width"] = self.width()
        self.preferences["window_height"] = self.height()

        # Salvar estado de expansão dos colapsáveis
        self.preferences["expanded_operational"] = self.operational_params.is_expanded()
        self.preferences["expanded_sensitivity"] = self.advanced_params.is_expanded()
        self.preferences["expanded_attributes"] = self.attributes_params.is_expanded()
        
        self.preferences["expanded_save"] = self.save_collapsible.is_expanded()

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

    @staticmethod
    def _normalize_field_name_map(field_name_map):
        normalized = {}
        if not isinstance(field_name_map, dict):
            return normalized
        for key, value in field_name_map.items():
            if not value:
                continue
            key_value = key.value if hasattr(key, "value") else key
            normalized[str(key_value)] = str(value)
        return normalized

    def _build_filtered_result_layer(
        self, 
        result_layer,      # camada de resultado (já com todos os campos)
        original_layer,    # camada de entrada original (para obter os campos originais)
        selected_output_fields, 
        field_name_map
    ):
        """Cria um layer com todos os atributos originais + apenas os campos calculados selecionados."""
        if not result_layer or not result_layer.isValid():
            return result_layer
        if not original_layer or not original_layer.isValid():
            self.logger.warning("Camada original inválida, usando apenas campos selecionados")
            # fallback para o comportamento antigo? melhor retornar a result_layer sem filtro
            return result_layer

        normalized_map = self._normalize_field_name_map(field_name_map)
        if not selected_output_fields or not normalized_map:
            self.logger.info("Filtro de campos não aplicado")
            return result_layer

        normalized_selected = set(
            self._normalize_selected_output_fields(selected_output_fields)
        )
        selected_keys = [
            key
            for key in SequentialPointBreakJudge.DIVIDE_STRIP_FIELDS.keys()
            if key.value in normalized_selected
        ]

        # 1. Obtém todos os campos da camada ORIGINAL (mantém todos)
        original_fields = [original_layer.fields().field(i) for i in range(original_layer.fields().count())]

        # 2. Adiciona apenas os campos calculados que foram selecionados (se não existirem nos originais)
        extra_fields = []
        for logical_key in selected_keys:
            field_spec = SequentialPointBreakJudge.DIVIDE_STRIP_FIELDS.get(logical_key)
            field_name = self._resolve_field_name_from_map(normalized_map, logical_key)
            if field_spec and field_name:
                if any(f.name() == field_name for f in original_fields):
                    continue  # não duplicar
                extra_fields.append(
                    QgsField(
                        field_name,
                        field_spec.type,
                        len=field_spec.length,
                        prec=field_spec.precision,
                    )
                )

        # Cria a nova camada
        uri = f"Point?crs={result_layer.crs().authid()}"
        filtered_layer = QgsVectorLayer(uri, f"{original_layer.name()}_filtered", "memory")
        if not filtered_layer.isValid():
            self.logger.error("Falha ao criar camada temporária filtrada")
            return result_layer

        # Adiciona todos os campos originais + os extras selecionados
        all_fields = original_fields + extra_fields
        filtered_layer.dataProvider().addAttributes(all_fields)
        filtered_layer.updateFields()

        filtered_layer.startEditing()

        # Para cada feição da camada de resultado, copiamos:
        # - geometria
        # - todos os atributos originais (buscando da result_layer, que os possui)
        # - apenas os atributos calculados selecionados
        for result_feature in result_layer.getFeatures():
            new_feature = QgsFeature(filtered_layer.fields())
            new_feature.setGeometry(result_feature.geometry())

            # Copia todos os campos originais (usando os nomes dos campos originais)
            for orig_field in original_fields:
                field_name = orig_field.name()
                source_idx = result_layer.fields().lookupField(field_name)
                target_idx = filtered_layer.fields().lookupField(field_name)
                if source_idx >= 0 and target_idx >= 0:
                    new_feature.setAttribute(target_idx, result_feature.attribute(source_idx))

            # Copia apenas os campos calculados selecionados
            for logical_key in selected_keys:
                resolved_name = self._resolve_field_name_from_map(normalized_map, logical_key)
                if not resolved_name:
                    continue
                source_idx = result_layer.fields().lookupField(resolved_name)
                target_idx = filtered_layer.fields().lookupField(resolved_name)
                if source_idx >= 0 and target_idx >= 0:
                    new_feature.setAttribute(target_idx, result_feature.attribute(source_idx))

            filtered_layer.addFeature(new_feature)

        filtered_layer.commitChanges()
        filtered_layer.updateFields()
        self.logger.info(
            "Filtro de atributos concluído: originais + selecionados",
            filtered_field_names=[f.name() for f in filtered_layer.fields()],
            feature_count=filtered_layer.featureCount(),
        )
        return filtered_layer

    def _generate_strip_lines_layer(self, point_layer, field_name_map, original_layer_name):
        """Gera uma camada de linhas onde cada feição representa um shot_id."""
        t0 = time.time()
        self.logger.info("Iniciando agrupamento de pontos para geração de linhas (strips)")

        sid_key = self._resolve_field_name_from_map(field_name_map, StripOutputFieldKey.SHOT_ID)
        valid_key = self._resolve_field_name_from_map(field_name_map, StripOutputFieldKey.SHOT_VALID)
        az_key = self._resolve_field_name_from_map(field_name_map, StripOutputFieldKey.AZIMUTH_INSTANT)

        # Agrupamento manual para garantir ordem e controle de atributos
        shots_data = {}
        for feat in point_layer.getFeatures():
            sid = feat.attribute(sid_key)
            if sid is None or sid == 0:
                continue
            
            if sid not in shots_data:
                shots_data[sid] = {
                    "points": [],
                    "azs": [],
                    "valid": feat.attribute(valid_key),
                }
            
            geom = feat.geometry()
            if geom and not geom.isEmpty():
                shots_data[sid]["points"].append(geom.asPoint())
                az_val = feat.attribute(az_key)
                if isinstance(az_val, (int, float)):
                    shots_data[sid]["azs"].append(az_val)

        # Criar camada de memória para linhas
        uri = f"LineString?crs={point_layer.crs().authid()}"
        line_layer = QgsVectorLayer(uri, f"{original_layer_name}_linhas", "memory")
        provider = line_layer.dataProvider()

        # Definir campos agregados
        fields = [
            QgsField("shot_id", QVariant.Int),
            QgsField("shot_valid", QVariant.Int),
            QgsField("point_count", QVariant.Int),
            QgsField("azimuth_mean", QVariant.Double, len=10, prec=2),
            QgsField("source", QVariant.String, len=255)
        ]
        provider.addAttributes(fields)
        line_layer.updateFields()

        new_features = []
        ignored_shots = 0

        for sid in sorted(shots_data.keys()):
            data = shots_data[sid]
            pts = data["points"]
            
            if len(pts) < 2:
                ignored_shots += 1
                continue
            
            line_geom = QgsGeometry.fromPolylineXY(pts)
            
            feat = QgsFeature(line_layer.fields())
            feat.setGeometry(line_geom)
            
            # Calcular média circular do azimute para a linha
            avg_az = MathUtils.circular_mean(data["azs"]) if data.get("azs") else 0.0
            
            feat.setAttribute("shot_id", int(sid))
            feat.setAttribute("shot_valid", int(data["valid"]))
            feat.setAttribute("point_count", len(pts))
            feat.setAttribute("azimuth_mean", float(avg_az))
            feat.setAttribute("source", point_layer.source())
            
            new_features.append(feat)

        provider.addFeatures(new_features)
        line_layer.updateFields()
        
        self.logger.info(
            "Geração de linhas concluída",
            total_lines=len(new_features),
            ignored_single_points=ignored_shots,
            elapsed=round(time.time() - t0, 2)
        )
        
        return line_layer

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
        
        # O campo ID continua obrigatório para ordenação, mas tempo agora é opcional.
        if not field_id:
            QgisMessageUtil.bar_warning(self.iface, STR.SELECT_REQUIRED_FIELDS)
            return

        self.logger.info(f"Campos selecionados: ID={field_id}, Tempo={field_time or 'N/A'}")

        operational_values = self.operational_fields.get_values()
        sensitivity_values = self.sensitivity_fields.get_values()

        self.logger.info(
            "Executando segmentacao de tiros em camada de pontos",
            layer=layer.name(),
            source_path=layer.source(),
            id_field=field_id,
            time_field=field_time,
            operational_fields=operational_values,
            sensitivity_fields=sensitivity_values,
        )

        import time

        start_time = time.time()
        self.logger.info("Iniciando processamento sincrono da segmentacao")

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
                retroactive_relabel_window=5,
                fusion_azimuth_tolerance=10.0,
                conflict_resolver=lambda field_name: QgisMessageUtil.ask_field_conflict(
                    self.iface, field_name
                ),
                path_mode=self.radio_path_mode.get_selected_text(),
            )
            processing_time = time.time() - start_time
            selected_fields = self._get_selected_output_fields()
            field_name_map = self._normalize_field_name_map(
                summary.get("field_name_map", {})
            )
            safe_summary = {
                "total_points": summary.get("total_points"),
                "total_shots": summary.get("total_shots"),
                "valid_shots": summary.get("valid_shots"),
                "invalid_shots": summary.get("invalid_shots"),
                "source_path": summary.get("source_path"),
            }
            self.logger.info(
                "Segmentacao concluida com sucesso",
                processing_time_seconds=round(processing_time, 2),
                summary=safe_summary,
            )
            self.logger.info(
                "Configuracao de filtro de atributos de saida",
                selected_output_fields=selected_fields,
                required_output_field=self.REQUIRED_OUTPUT_FIELD,
                field_name_map=field_name_map,
            )

            raw_result_layer = summary.get("result_layer")
            result_layer = self._build_filtered_result_layer(
                raw_result_layer,
                layer,  # <--- passe a camada de entrada original
                selected_fields,
                field_name_map,
            )

            if result_layer and result_layer.isValid():
                QgsProject.instance().addMapLayer(result_layer)
                self.logger.info(
                    "Nova camada adicionada ao projeto", layer_name=result_layer.name()
                )
            else:
                self.logger.warning("Camada de resultado invalida ou nao encontrada")

            if self.save_points_selector and self.save_points_selector.is_enabled():
                out_path = self.save_points_selector.get_file_path().strip()
                if out_path:
                    if result_layer and result_layer.isValid():
                        self.logger.info(
                            "Schema da camada preparada para salvar",
                            out_path=out_path,
                            field_names=[f.name() for f in result_layer.fields()],
                            feature_count=result_layer.featureCount(),
                        )
                    saved_layer = VectorLayerSource.save_and_load_layer(
                        result_layer,
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
                else:
                    self.logger.warning(
                        "Salvamento habilitado, mas caminho de saida esta vazio"
                    )
            else:
                self.logger.info(
                    "Salvamento em arquivo desabilitado; resultado filtrado mantido apenas no projeto"
                )

            # ====== NOVA SAÍDA: GERAÇÃO DE LINHAS (STRIPS) ======
            strip_lines_layer = self._generate_strip_lines_layer(
                raw_result_layer, 
                field_name_map, 
                layer.name()
            )
            
            if strip_lines_layer and strip_lines_layer.isValid():
                # Obrigatorio: Adiciona camada temporária em memória
                QgsProject.instance().addMapLayer(strip_lines_layer)
                self.logger.info("Camada de linhas (strips) adicionada ao projeto como camada temporária")

                # Opcional: Salva em disco se o seletor estiver ativo e com caminho
                if self.save_track_selector and self.save_track_selector.is_enabled():
                    line_out_path = self.save_track_selector.get_file_path().strip()
                    if line_out_path:
                        saved_line_layer = VectorLayerSource.save_and_load_layer(
                            strip_lines_layer,
                            line_out_path,
                            tool_key=self.TOOL_KEY,
                            decision="rename",
                        )
                        if saved_line_layer and saved_line_layer.isValid():
                            QgsProject.instance().addMapLayer(saved_line_layer)
                            self.logger.info(
                                "Camada de linhas salva em disco e carregada", 
                                path=line_out_path
                            )
                        else:
                            self.logger.warning("Falha ao salvar camada de linhas (strips) em arquivo")
                    else:
                        self.logger.warning("Salvamento de linhas habilitado, mas caminho de saída está vazio")

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(
                f"Erro na segmentacao de tiros apos {processing_time:.2f}s: {e}",
                exception_details=str(e),
            )
            self.logger.exception(e)
            QgisMessageUtil.bar_critical(self.iface, f"{STR.ERROR}\n{e}")
            return

        try:
            layer.triggerRepaint()
        except Exception as e:
            self.logger.warning(
                f"Falha ao atualizar camada original apos julgamento: {e}"
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
