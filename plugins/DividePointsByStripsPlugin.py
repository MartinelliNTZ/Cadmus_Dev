# -*- coding: utf-8 -*-

import time
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsVectorLayer,
    QgsProject,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
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
from ..utils.judge.SimpleSPBJudge import SimpleSPBJudge
from ..utils.vector.VectorLayerAttributes import VectorLayerAttributes
from ..utils.vector.VectorLayerSource import VectorLayerSource
from ..utils.MathUtils import MathUtils


class DividePointsByStripsPlugin(BasePluginMTL):
    TOOL_KEY = ToolKey.DIVIDE_POINTS_BY_STRIPS
    PREF_SELECTED_OUTPUT_FIELDS = "selected_output_fields"
    REQUIRED_OUTPUT_FIELD = "shot_id"
    PATH_MODES = [STR.CURVE, STR.STRAIGHT, STR.BOTH_PATH]
    JUDGE_MODES = {"Complexo": "complex", "Simples": "simple"}

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
        judge_mode_layout, self.judge_mode_selector = (
            WidgetFactory.create_dropdown_selector(
                title="Modo de Processamento",
                options_dict=self.JUDGE_MODES,
                selected_key="Complexo",
                allow_empty=False,
                parent=self,
                separator_top=False,
                separator_bottom=False,
            )
        )
        group_field_layout, self.group_field_selector = (
            WidgetFactory.create_dropdown_selector(
                title="Agrupar por Campo (opcional)",
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
        dist_max_layout, self.dist_max_input = WidgetFactory.create_double_spin_input(
            "Distância Máxima de Quebra (m)",
            #tooltip="Distância a partir da qual uma quebra de faixa é forçada automaticamente.",
            value=0.0,
            minimum=0.0,
            maximum=100000.0,
            decimals=1,
            step=10.0,
            #arent=self,
        )
        self.operational_params.add_content_layout(id_field_layout)
        self.operational_params.add_content_layout(time_field_layout)
        self.operational_params.add_content_layout(judge_mode_layout)
        self.operational_params.add_content_layout(group_field_layout)
        self.operational_params.add_content_layout(operational_layout)
        self.operational_params.add_content_layout(dist_max_layout)

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
        self.group_field = self.preferences.get("group_field", "")
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
        
        self.dist_max_input.setValue(float(self.preferences.get("max_distance_meters", 0.0)))

        self.group_field_selector.set_selected_key(self.preferences.get("group_field", ""))

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
        self.preferences["group_field"] = self.group_field_selector.get_selected_key() or ""
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
        self.preferences["max_distance_meters"] = float(self.dist_max_input.value())
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
        """
        Cria um layer com todos os atributos originais + campos calculados selecionados.
        Se um campo calculado já existir no original, SOBRESCREVE (não verifica duplicatas).
        """
        if not result_layer or not result_layer.isValid():
            return result_layer
        if not original_layer or not original_layer.isValid():
            self.logger.warning("Camada original inválida, retornando resultado sem filtro")
            return result_layer

        normalized_map = self._normalize_field_name_map(field_name_map)
        if not selected_output_fields or not normalized_map:
            self.logger.info("Filtro de campos não aplicado (sem seleção ou mapa vazio)")
            return result_layer

        normalized_selected = set(
            self._normalize_selected_output_fields(selected_output_fields)
        )
        selected_keys = [
            key
            for key in SequentialPointBreakJudge.DIVIDE_STRIP_FIELDS.keys()
            if key.value in normalized_selected
        ]

        # Campos da camada ORIGINAL
        original_fields = [
            original_layer.fields().field(i)
            for i in range(original_layer.fields().count())
        ]

        # Campos calculados selecionados — NÃO verifica se já existem,
        # sempre adiciona para sobrescrever valores existentes.
        extra_fields = []
        extra_field_names = set()
        for logical_key in selected_keys:
            field_spec = SequentialPointBreakJudge.DIVIDE_STRIP_FIELDS.get(logical_key)
            field_name = self._resolve_field_name_from_map(normalized_map, logical_key)
            if field_spec and field_name and field_name not in extra_field_names:
                extra_field_names.add(field_name)
                extra_fields.append(
                    QgsField(
                        field_name,
                        field_spec.type,
                        len=field_spec.length,
                        prec=field_spec.precision,
                    )
                )

        # Remove colunas duplicadas entre originais e extras;
        # campos extras SEMPRE substituem os originais de mesmo nome.
        orig_kept = [f for f in original_fields if f.name() not in extra_field_names]

        uri = f"Point?crs={result_layer.crs().authid()}"
        filtered_layer = QgsVectorLayer(uri, f"{original_layer.name()}_filtered", "memory")
        if not filtered_layer.isValid():
            self.logger.error("Falha ao criar camada temporária filtrada")
            return result_layer

        all_fields = orig_kept + extra_fields
        filtered_layer.dataProvider().addAttributes(all_fields)
        filtered_layer.updateFields()

        filtered_layer.startEditing()

        for result_feature in result_layer.getFeatures():
            new_feature = QgsFeature(filtered_layer.fields())
            new_feature.setGeometry(result_feature.geometry())

            # Copia campos originais (exceto os que foram sobrescritos)
            for orig_field in orig_kept:
                field_name = orig_field.name()
                source_idx = result_layer.fields().lookupField(field_name)
                target_idx = filtered_layer.fields().lookupField(field_name)
                if source_idx >= 0 and target_idx >= 0:
                    new_feature.setAttribute(target_idx, result_feature.attribute(source_idx))

            # Copia campos calculados selecionados (sobrescrevem originais se mesmo nome)
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
            "Filtro de atributos concluído (sobrescreve existentes)",
            original_kept_count=len(orig_kept),
            extra_count=len(extra_fields),
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

        self.logger.debug(
            "Campos resolvidos para geração de linhas",
            sid_key=sid_key,
            valid_key=valid_key,
            az_key=az_key,
            point_layer_name=point_layer.name(),
            point_layer_feature_count=point_layer.featureCount()
        )

        # Agrupamento manual para garantir ordem e controle de atributos
        shots_data = {}
        total_features_processed = 0
        skipped_null_sid = 0
        skipped_zero_sid = 0
        skipped_invalid_geom = 0

        for feat in point_layer.getFeatures():
            total_features_processed += 1
            sid = feat.attribute(sid_key)
            if sid is None or sid == 0 or str(sid) == "0":
                if sid is None:
                    skipped_null_sid += 1
                else:
                    skipped_zero_sid += 1
                continue

            if sid not in shots_data:
                shots_data[sid] = {
                    "points": [],
                    "azs": [],
                    "valid": feat.attribute(valid_key),
                }

            geom = feat.geometry()
            if geom and not geom.isEmpty():
                point = geom.asPoint()
                shots_data[sid]["points"].append(QgsPointXY(point.x(), point.y()))
                az_val = feat.attribute(az_key)
                if isinstance(az_val, (int, float)):
                    shots_data[sid]["azs"].append(az_val)
            else:
                skipped_invalid_geom += 1

        self.logger.info(
            "Agrupamento de pontos concluído",
            total_features_processed=total_features_processed,
            unique_shots=len(shots_data),
            skipped_null_sid=skipped_null_sid,
            skipped_zero_sid=skipped_zero_sid,
            skipped_invalid_geom=skipped_invalid_geom
        )

        # Criar camada de memória para linhas
        uri = f"LineString?crs={point_layer.crs().authid()}"
        line_layer = QgsVectorLayer(uri, f"{original_layer_name}_linhas", "memory")
        provider = line_layer.dataProvider()

        # Definir campos agregados
        fields = [
            QgsField("shot_id", QVariant.String, len=50),
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
                self.logger.debug(
                    "Shot ignorado por poucos pontos",
                    shot_id=sid,
                    point_count=len(pts),
                    valid=data.get("valid")
                )
                continue

            line_geom = QgsGeometry.fromPolylineXY(pts)

            if not line_geom or line_geom.isEmpty():
                self.logger.warning(
                    "Falha ao criar geometria de linha",
                    shot_id=sid,
                    points_count=len(pts),
                    points_sample=pts[:3] if len(pts) > 3 else pts
                )
                continue

            feat = QgsFeature(line_layer.fields())
            feat.setGeometry(line_geom)

            # Calcular média circular do azimute para a linha
            avg_az = MathUtils.circular_mean(data["azs"]) if data.get("azs") else 0.0

            feat.setAttribute("shot_id", str(sid))
            feat.setAttribute("shot_valid", int(data["valid"]))
            feat.setAttribute("point_count", len(pts))
            feat.setAttribute("azimuth_mean", float(avg_az))
            feat.setAttribute("source", point_layer.source())
            
            new_features.append(feat)

        # Tenta adicionar via data provider
        try:
            add_result = provider.addFeatures(new_features)
        except Exception:
            add_result = None

        # Atualiza extensões e campos
        line_layer.updateFields()
        line_layer.updateExtents()

        # Verifica se as feições foram realmente adicionadas
        final_count = line_layer.featureCount()

        # Se não houve features adicionadas, tenta um fallback usando edição direta
        if final_count == 0 and new_features:
            try:
                line_layer.startEditing()
                added = 0
                for feat in new_features:
                    ok = line_layer.addFeature(feat)
                    if ok:
                        added += 1
                line_layer.commitChanges()
                line_layer.updateExtents()
                final_count = line_layer.featureCount()
            except Exception:
                final_count = line_layer.featureCount()

        self.logger.info(
            "Geração de linhas concluída",
            total_lines=final_count,
            ignored_single_points=ignored_shots,
            elapsed=round(time.time() - t0, 2),
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
        selected_group = getattr(self, "group_field", "") or self.preferences.get(
            "group_field", ""
        )

        self.id_field_selector.set_options(options)
        self.time_field_selector.set_options(options)
        self.group_field_selector.set_options(options)

        if selected_id:
            self.id_field_selector.set_selected_key(selected_id)
        if selected_time:
            self.time_field_selector.set_selected_key(selected_time)
        if selected_group:
            self.group_field_selector.set_selected_key(selected_group)

    @staticmethod
    def _normalize_group_key(group_value):
        return str(group_value) if group_value is not None else "__NONE__"

    def _build_group_prefixes(self, group_values):
        prefixes = {}
        for idx, gv in enumerate(group_values):
            if idx < 26:
                letter = chr(ord("A") + idx)
            else:
                letter = f"{chr(ord('A') + (idx % 26))}{idx // 26}"
            prefixes[self._normalize_group_key(gv)] = letter
        return prefixes

    def _apply_group_prefix_to_shot_ids(self, layer, prefix):
        if not layer or not layer.isValid() or not prefix:
            self.logger.warning(
                "Aplicação de prefixo pulada",
                reason="layer inválido ou prefixo vazio",
                prefix=prefix,
                layer_valid=layer.isValid() if layer else False
            )
            return

        shot_idx = layer.fields().lookupField(self.REQUIRED_OUTPUT_FIELD)
        if shot_idx == -1:
            self.logger.warning(
                "Campo shot_id não encontrado na camada",
                required_field=self.REQUIRED_OUTPUT_FIELD,
                available_fields=[f.name() for f in layer.fields()]
            )
            return

        layer.startEditing()
        modified_count = 0
        old_shot_idx = layer.fields().lookupField("old_shot_id")
        for feat in layer.getFeatures():
            sid = feat.attribute(shot_idx)
            if sid is None:
                continue
            sid_str = str(sid)
            if sid_str == "0":
                continue
            prefixed = f"{prefix}{sid_str}"
            if prefixed != sid_str:
                layer.changeAttributeValue(feat.id(), shot_idx, prefixed)
                if old_shot_idx != -1:
                    old_sid = feat.attribute(old_shot_idx)
                    if old_sid is not None:
                        old_sid_str = str(old_sid)
                        if old_sid_str != "0":
                            layer.changeAttributeValue(feat.id(), old_shot_idx, f"{prefix}{old_sid_str}")
                modified_count += 1
        layer.commitChanges()

        self.logger.info(
            "Prefixo aplicado aos shot_ids",
            prefix=prefix,
            modified_features=modified_count,
            total_features=layer.featureCount()
        )

    def _create_subset_layer_for_group(self, layer, field_group, group_value):
        crs = layer.crs().authid()
        uri = 'Point?crs=%s' % crs
        subset = QgsVectorLayer(uri, '{}_{}'.format(layer.name(), str(group_value)), "memory")
        subset_data = subset.dataProvider()
        subset_data.addAttributes(layer.fields())
        subset.updateFields()
        new_features = []
        for feat in layer.getFeatures():
            feat_val = feat.attribute(field_group)
            if str(feat_val) == str(group_value):
                new_feat = QgsFeature(subset.fields())
                new_feat.setGeometry(feat.geometry())
                for field in feat.fields():
                    new_feat.setAttribute(field.name(), feat.attribute(field.name()))
                new_features.append(new_feat)
        subset_data.addFeatures(new_features)
        subset.updateFields()
        return subset

    @staticmethod
    def _merge_memory_layers(layers, crs, layer_name):
        if not layers:
            return None
        if len(layers) == 1:
            return layers[0]
        # Detect geometry type from the first valid layer to preserve geometry (Point/LineString/Polygon)
        first = None
        for lyr in layers:
            if lyr and lyr.isValid():
                first = lyr
                break
        if first is None:
            uri = 'Point?crs=%s' % crs
        else:
            geom_type = first.geometryType()  # 0=Point,1=Line,2=Polygon
            if geom_type == 1:
                uri = 'LineString?crs=%s' % crs
            elif geom_type == 2:
                uri = 'Polygon?crs=%s' % crs
            else:
                uri = 'Point?crs=%s' % crs

        merged = QgsVectorLayer(uri, layer_name, "memory")
        merged_data = merged.dataProvider()
        all_field_names = []
        for lyr in layers:
            for field in lyr.fields():
                if field.name() not in all_field_names:
                    all_field_names.append(field.name())
        unique_fields = []
        seen = set()
        for lyr in layers:
            for fname in all_field_names:
                idx = lyr.fields().lookupField(fname)
                if idx >= 0 and fname not in seen:
                    seen.add(fname)
                    unique_fields.append(lyr.fields().field(idx))
        merged_data.addAttributes(unique_fields)
        merged.updateFields()
        for lyr in layers:
            for feat in lyr.getFeatures():
                new_feat = QgsFeature(merged.fields())
                new_feat.setGeometry(feat.geometry())
                for field_name in all_field_names:
                    src_idx = lyr.fields().lookupField(field_name)
                    tgt_idx = merged.fields().lookupField(field_name)
                    if src_idx >= 0 and tgt_idx >= 0:
                        new_feat.setAttribute(tgt_idx, feat.attribute(src_idx))
                merged_data.addFeatures([new_feat])
        merged.updateFields()
        return merged

    def execute_tool(self):
        layer = self.layer_input.current_layer()
        if not isinstance(layer, QgsVectorLayer):
            QgisMessageUtil.bar_warning(self.iface, STR.SELECT_POINT_VECTOR_LAYER)
            return

        field_id = self.id_field_selector.get_selected_key()
        field_time = self.time_field_selector.get_selected_key()
        field_group = self.group_field_selector.get_selected_key()
        
        # O campo ID continua obrigatório para ordenação, mas tempo agora é opcional.
        if not field_id:
            QgisMessageUtil.bar_warning(self.iface, STR.SELECT_REQUIRED_FIELDS)
            return

        self.logger.info(f"Campos selecionados: ID={field_id}, Tempo={field_time or 'N/A'}, Grupo={field_group or 'N/A'}")

        operational_values = self.operational_fields.get_values()
        sensitivity_values = self.sensitivity_fields.get_values()
        max_dist = float(self.dist_max_input.value())

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
            selected_fields = self._get_selected_output_fields()
            path_mode = self.radio_path_mode.get_selected_text()
            if path_mode == STR.STRAIGHT:
                judge_class = SimpleSPBJudge
            else:
                judge_class = SequentialPointBreakJudge
            judge_args = {
                "field_id": field_id,
                "field_time": field_time,
                "point_frequency_seconds": float(
                    operational_values.get("frequencia_pontos", 1) or 1
                ),
                "strip_width_meters": float(
                    operational_values.get("largura_tiro", 20.0) or 20.0
                ),
                "azimuth_window": int(sensitivity_values.get("janela_azimute", 10) or 10),
                "light_azimuth_threshold": float(
                    sensitivity_values.get("threshold_azimute_leve", 20.0) or 20.0
                ),
                "severe_azimuth_threshold": float(
                    sensitivity_values.get("threshold_azimute_grave", 45.0) or 45.0
                ),
                "minimum_break_score": int(
                    sensitivity_values.get("score_minimo_quebra", 3) or 3
                ),
                "minimum_point_count": int(
                    sensitivity_values.get("n_minimo_pontos", 20) or 20
                ),
                "time_tolerance_multiplier": float(
                    sensitivity_values.get("tolerancia_tempo", 3.0) or 3.0
                ),
                "max_desvio": int(sensitivity_values.get("max_desvio", 5) or 5),
                "confirmation_window": 3,
                "min_confirmed": 2,
                "border_azimuth_threshold": 90.0,
                "border_speed_threshold": 1.0,
                "border_distance_threshold": 5.0,
                "retroactive_relabel_window": 5,
                "fusion_azimuth_tolerance": 10.0,
                "conflict_resolver": "replace",
                "path_mode": self.radio_path_mode.get_selected_text(),
                "max_distance_meters": max_dist,
            }

            if field_group:
                group_values = []
                seen_values = set()
                for feat in layer.getFeatures():
                    val = feat.attribute(field_group)
                    key = self._normalize_group_key(val)
                    if key not in seen_values:
                        seen_values.add(key)
                        group_values.append(val)
                self.logger.info(
                    "Processamento por grupo ativado",
                    group_field=field_group,
                    unique_groups=len(group_values),
                    group_values=[str(v) for v in group_values],
                )
            else:
                group_values = [None]

            group_prefixes = self._build_group_prefixes(group_values)

            self.logger.info(
                "Prefixos de grupo construídos",
                group_prefixes=group_prefixes
            )

            all_result_layers = []
            all_strip_layers = []
            all_summaries = []
            total_points_all = 0
            total_shots_all = 0
            valid_shots_all = 0
            invalid_shots_all = 0
            field_name_map = None

            for gv in group_values:
                if field_group:
                    process_layer = self._create_subset_layer_for_group(layer, field_group, gv)
                    group_label = str(gv)
                    self.logger.info(f"Processando grupo: {group_label}", features=process_layer.featureCount())
                    if process_layer.featureCount() == 0:
                        self.logger.warning(f"Grupo '{group_label}' vazio, ignorando.")
                        continue
                else:
                    process_layer = layer
                    group_label = layer.name()

                summary = judge_class(
                    layer=process_layer,
                    tool_key=self.TOOL_KEY,
                ).judge(**judge_args)

                all_summaries.append(summary)

                if field_name_map is None:
                    field_name_map = self._normalize_field_name_map(
                        summary.get("field_name_map", {})
                    )

                total_points_all += summary.get("total_points", 0)
                total_shots_all += summary.get("total_shots", 0)
                valid_shots_all += summary.get("valid_shots", 0)
                invalid_shots_all += summary.get("invalid_shots", 0)

                raw_result_layer = summary.get("result_layer")
                if raw_result_layer and raw_result_layer.isValid():
                    prefix = group_prefixes.get(self._normalize_group_key(gv), "A")
                    self.logger.info(
                        "Aplicando prefixo ao grupo",
                        group_value=gv,
                        prefix=prefix,
                        layer_name=raw_result_layer.name(),
                        feature_count=raw_result_layer.featureCount()
                    )
                    self._apply_group_prefix_to_shot_ids(raw_result_layer, prefix)

                    if field_group and gv is not None:
                        group_idx = raw_result_layer.fields().lookupField(field_group)
                        if group_idx == -1:
                            orig_field = layer.fields().field(
                                layer.fields().lookupField(field_group)
                            )
                            if orig_field.isValid():
                                raw_result_layer.dataProvider().addAttributes([orig_field])
                                raw_result_layer.updateFields()
                                group_idx = raw_result_layer.fields().lookupField(field_group)
                                raw_result_layer.startEditing()
                                for feat in raw_result_layer.getFeatures():
                                    raw_result_layer.changeAttributeValue(
                                        feat.id(), group_idx, gv
                                    )
                                raw_result_layer.commitChanges()

                    all_result_layers.append(raw_result_layer)

                    strip_lines_layer = self._generate_strip_lines_layer(
                        raw_result_layer,
                        field_name_map or {},
                        f"{group_label}"
                    )
                    if strip_lines_layer and strip_lines_layer.isValid():
                        if field_group and gv is not None:
                            lines_data = strip_lines_layer.dataProvider()
                            group_field_idx = strip_lines_layer.fields().lookupField(field_group)
                            if group_field_idx == -1:
                                try:
                                    orig_field_val = layer.fields().field(
                                        layer.fields().lookupField(field_group)
                                    )
                                    if orig_field_val.isValid():
                                        field_type = orig_field_val.type()
                                        field_name_to_use = orig_field_val.name()
                                    else:
                                        field_type = QVariant.String
                                        field_name_to_use = field_group
                                except Exception:
                                    field_type = QVariant.String
                                    field_name_to_use = field_group
                                lines_data.addAttributes(
                                    [QgsField(field_name_to_use, field_type, len=255)]
                                )
                                strip_lines_layer.updateFields()
                                group_idx_line = strip_lines_layer.fields().lookupField(
                                    field_name_to_use
                                )
                                strip_lines_layer.startEditing()
                                for feat in strip_lines_layer.getFeatures():
                                    strip_lines_layer.changeAttributeValue(
                                        feat.id(), group_idx_line, gv
                                    )
                                strip_lines_layer.commitChanges()

                        all_strip_layers.append(strip_lines_layer)

            if not all_result_layers:
                QgisMessageUtil.bar_warning(self.iface, "Nenhum grupo produziu resultado.")
                return

            crs_authid = layer.crs().authid()
            if len(all_result_layers) == 1 and not field_group:
                raw_result_layer = all_result_layers[0]
                summary_data = all_summaries[0]
            else:
                raw_result_layer = self._merge_memory_layers(
                    all_result_layers, crs_authid, f"{layer.name()}_segmentado"
                )
                summary_data = {
                    "total_points": total_points_all,
                    "total_shots": total_shots_all,
                    "valid_shots": valid_shots_all,
                    "invalid_shots": invalid_shots_all,
                    "source_path": layer.source(),
                    "field_name_map": field_name_map,
                    "result_layer": raw_result_layer,
                }

            result_layer = self._build_filtered_result_layer(
                raw_result_layer,
                layer,
                selected_fields,
                field_name_map or {},
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

            if all_strip_layers:
                if len(all_strip_layers) == 1:
                    strip_lines_layer = all_strip_layers[0]
                else:
                    strip_lines_layer = self._merge_memory_layers(
                        all_strip_layers, crs_authid, f"{layer.name()}_linhas"
                    )

                if strip_lines_layer and strip_lines_layer.isValid():
                    QgsProject.instance().addMapLayer(strip_lines_layer)
                    self.logger.info(
                        "Camada de linhas (strips) adicionada ao projeto como camada temporaria"
                    )

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
                                self.logger.warning(
                                    "Falha ao salvar camada de linhas (strips) em arquivo"
                                )
                        else:
                            self.logger.warning(
                                "Salvamento de linhas habilitado, mas caminho de saida esta vazio"
                            )

            processing_time = time.time() - start_time
            safe_summary = {
                "total_points": total_points_all,
                "total_shots": total_shots_all,
                "valid_shots": valid_shots_all,
                "invalid_shots": invalid_shots_all,
                "source_path": layer.source(),
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

            summary = summary_data

        except Exception as e:
            processing_time = time.time() - start_time
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
