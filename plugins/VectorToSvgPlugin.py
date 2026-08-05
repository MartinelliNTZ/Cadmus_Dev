# -*- coding: utf-8 -*-
import os

from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsVectorLayer,
)

from .BasePlugin import BasePluginMTL
from ..i18n.TranslationManager import STR
from ..utils.Preferences import Preferences
from ..utils.ProjectUtils import ProjectUtils
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.SVGUtils import SVGUtils
from ..utils.StringManager import StringManager
from ..utils.ToolKeys import ToolKey
from ..utils.vector.VectorLayerAttributes import VectorLayerAttributes
from ..utils.vector.VectorLayerGeometry import VectorLayerGeometry
from ..utils.vector.VectorLayerSource import VectorLayerSource

# NOVOS WIDGETS (substituem WidgetFactory)
from ..resources.widgets.ComplexColorPicker import ComplexColorPicker
from ..resources.widgets.SeparatorWidget import SeparatorWidget
from ..resources.widgets.grid.GridCheckbox import GridCheckbox
from ..resources.widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.widgets.grid.GridDoubleSpin import GridDoubleSpin
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons


class VectorToSvgPlugin(BasePluginMTL):
    TOOL_KEY = ToolKey.VECTOR_TO_SVG

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.init(
            tool_key=self.TOOL_KEY,
            class_name=self.__class__.__name__,
            load_system_prefs=False,
            build_ui=True,
        )

    def _build_ui(self, **kwargs):
        super()._build_ui(
            title=STR.VECTOR_TO_SVG_TITLE,
            icon_path="cadmus_icon.ico",
            enable_scroll=True,
        )

        self.grid_selectors = GridComplexSelector(
            config={
                "camada": {
                    "label": STR.VECTOR_LAYER_LABEL,
                    "description": "Camada vetorial do projeto ou arquivo externo",
                    "allow_layer": True,
                    "layer_filters": QgsMapLayerProxyModel.Filter.VectorLayer,
                    "allow_features_check": True,
                    "features_check_text": STR.ONLY_SELECTED_FEATURES,
                    "allow_file": True,
                    "allow_folder": False,
                    "file_filter": StringManager.FILTER_VECTOR,
                },
                "pasta_saida": {
                    "label": STR.OUTPUT_FOLDER,
                    "description": "Pasta onde os SVGs serao salvos",
                    "mode_type": "output",
                    "parent": "camada",
                    "subfolder": "svgs",
                    "allow_file": False,
                    "allow_folder": True,
                    "show_copy_button": False,
                },
            },
            tool_key=self.TOOL_KEY,
            separator_bottom=False,
            parent=self,
        )
        self.layout.addWidget(self.grid_selectors)
        self.layout.addWidget(SeparatorWidget())

        self.fill_color_widget = ComplexColorPicker(
            label_text=STR.BACKGROUND_COLOR,
            initial_color=QColor("#ffffff"),
            tooltip=STR.SELECT_FILL_COLOR,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.layout.addWidget(self.fill_color_widget)

        self.border_color_widget = ComplexColorPicker(
            label_text=STR.BORDER_COLOR,
            initial_color=QColor("#000000"),
            tooltip=STR.SELECT_BORDER_COLOR,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.layout.addWidget(self.border_color_widget)

        self.border_width_spin = GridDoubleSpin(
            config={
                "border_width": {
                    "label": STR.BORDER_WIDTH,
                    "value": 1.2,
                    "min": 0.0,
                    "max": 50.0,
                    "step": 0.2,
                    "decimals": 2,
                    "type": "double",
                },
            },
            parent=self,
        )
        self.layout.addWidget(self.border_width_spin)

        self.label_color_widget = ComplexColorPicker(
            label_text=STR.LABEL_COLOR,
            initial_color=QColor("#000000"),
            tooltip=STR.SELECT_LABEL_COLOR,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.layout.addWidget(self.label_color_widget)
        self.layout.addWidget(SeparatorWidget())

        self.label_size_spin = GridDoubleSpin(
            config={
                "label_size": {
                    "label": STR.LABEL_SIZE,
                    "value": 14.0,
                    "min": 1.0,
                    "max": 200.0,
                    "step": 1.0,
                    "decimals": 1,
                    "type": "double",
                },
            },
            parent=self,
        )
        self.layout.addWidget(self.label_size_spin)
        self.layout.addWidget(SeparatorWidget())

        self.options_checkbox = GridCheckbox(
            config={
                "transparent_background": {"label": STR.TRANSPARENT_BACKGROUND},
                "show_border": {"label": STR.SHOW_BORDER},
                "show_label": {"label": STR.SHOW_LABEL},
                "for_each_feature": {"label": STR.GENERATE_SVG_FOR_EACH_FEATURE},
            },
            title="",
            items_per_row=2,
            parent=self,
        )
        self.layout.addWidget(self.options_checkbox)

        self.action_buttons = GridExecutionButtons(
            config={
                "run": {
                    "label": STR.EXECUTE,
                    "description": "Inicia a exportacao de SVG",
                    "callback": self.execute_tool,
                    "is_run_button": True,
                },
            },
            enable_close_button=True,
            enable_info=True,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.layout.add_execution_buttons(self.action_buttons)

    def _load_prefs(self):
        self.logger.debug("Carregando preferencias do VectorToSvg")

        self.fill_color_widget.set_color(
            QColor(self.preferences.get("fill_color", "#ffffff"))
        )
        self.border_color_widget.set_color(
            QColor(self.preferences.get("border_color", "#000000"))
        )
        self.label_color_widget.set_color(
            QColor(self.preferences.get("label_color", "#000000"))
        )
        self.label_size_spin.set_value(
            "label_size", float(self.preferences.get("label_size", 14.0))
        )
        self.border_width_spin.set_value(
            "border_width", float(self.preferences.get("border_width", 1.2))
        )

        for key in (
            "transparent_background",
            "show_border",
            "show_label",
            "for_each_feature",
        ):
            self.options_checkbox.set_checked(
                key, bool(self.preferences.get(key, False))
            )

        # GridComplexSelector restaura paths + layer mode + features/lock state
        self.grid_selectors.set_preferences(
            self.preferences.get("grid_selectors", {})
        )

    def _save_prefs(self):
        self.logger.debug("Salvando preferencias do VectorToSvg")

        self.preferences["fill_color"] = self.fill_color_widget.get_color().name(
            QColor.NameFormat.HexArgb
        )
        self.preferences["border_color"] = self.border_color_widget.get_color().name(
            QColor.NameFormat.HexArgb
        )
        self.preferences["label_color"] = self.label_color_widget.get_color().name(
            QColor.NameFormat.HexArgb
        )
        self.preferences["label_size"] = float(
            self.label_size_spin.get_value("label_size")
        )
        self.preferences["border_width"] = float(
            self.border_width_spin.get_value("border_width")
        )
        states = self.options_checkbox.get_all_states()
        self.preferences["transparent_background"] = bool(
            states.get("transparent_background", False)
        )
        self.preferences["show_border"] = bool(states.get("show_border", False))
        self.preferences["show_label"] = bool(states.get("show_label", False))
        self.preferences["for_each_feature"] = bool(
            states.get("for_each_feature", False)
        )

        # GridComplexSelector salva tudo (paths, layer mode, lock, features)
        self.preferences["grid_selectors"] = self.grid_selectors.get_preferences()

        self.preferences["window_width"] = self.width()
        self.preferences["window_height"] = self.height()

        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)

    def _resolve_input_layer(self):
        """
        Resolve a camada de entrada a partir do seletor.

        Usa getitem() do ComplexSelector que retorna tupla (path, layer):
        - layer nao-None -> camada carregada no QGIS
        - layer None + path nao-vazio -> arquivo externo nao carregado
        - layer None + path vazio -> nada selecionado
        """
        return self.grid_selectors.get("camada").getitem()

    def execute_tool(self):
        self.logger.info("Iniciando exportacao de SVG a partir de camada vetorial")
        path, layer = self._resolve_input_layer()

        if isinstance(layer, QgsVectorLayer):
            pass
        elif path:
            loaded = VectorLayerSource.open_vector_layer(
                path, tool_key=self.TOOL_KEY
            )
            if loaded and loaded.isValid():
                layer = loaded
                ProjectUtils.add_layer(layer)
            else:
                QgisMessageUtil.bar_warning(self.iface, STR.SELECT_VECTOR_LAYER)
                return
        else:
            QgisMessageUtil.bar_warning(self.iface, STR.SELECT_VECTOR_LAYER)
            return

        self.start_stats(layer)

        if not VectorLayerAttributes.ensure_has_features(layer, self.logger):
            QgisMessageUtil.bar_warning(self.iface, STR.LAYER_HAS_NO_FEATURES)
            return

        output_folder = self._resolve_output_folder()
        if not output_folder:
            return

        only_selected = self.grid_selectors.get_checked_state("camada")
        export_layer = self._resolve_export_layer(layer, only_selected)
        if not export_layer:
            return

        features = SVGUtils.collect_features_for_svg(
            export_layer, tool_key=self.TOOL_KEY
        )
        if not features:
            QgisMessageUtil.bar_warning(self.iface, STR.LAYER_HAS_NO_FEATURES)
            return

        style = self._build_style()
        for_each_feature = self.options_checkbox.is_checked("for_each_feature")

        try:
            if for_each_feature:
                generated = self._export_one_svg_per_feature(
                    layer, features, output_folder, style
                )
            else:
                generated = [
                    self._export_single_svg(layer, features, output_folder, style)
                ]
        except Exception as e:
            self.logger.error(f"Erro ao gerar SVG: {e}")
            QgisMessageUtil.modal_error(self.iface, f"{STR.ERROR}\n{e}")
            return

        if not generated:
            QgisMessageUtil.bar_warning(self.iface, STR.ERROR)
            return

        self.finish_stats(input_obj=export_layer)
        message = f"{len(generated)} {STR.SVGS_GENERATED_SUCCESS}"
        self.logger.info(message)
        QgisMessageUtil.modal_result_with_folder(
            self.iface,
            STR.EXPORT,
            message,
            output_folder,
            parent=self,
        )

    def _resolve_output_folder(self):
        output_folder = self.grid_selectors.get_path("pasta_saida") or ""
        if not output_folder:
            QgisMessageUtil.bar_warning(self.iface, STR.OUTPUT_FOLDER)
            return None

        try:
            os.makedirs(output_folder, exist_ok=True)
            self.logger.debug(f"Pasta de saida garantida: {output_folder}")
            return output_folder
        except Exception as e:
            self.logger.error(f"Erro ao preparar pasta de saida '{output_folder}': {e}")
            QgisMessageUtil.modal_error(self.iface, f"{STR.ERROR}\n{e}")
            return None

    def _resolve_export_layer(self, layer, only_selected):
        if not only_selected:
            self.logger.debug(
                f"Exportando todas as feicoes da camada '{layer.name()}'."
            )
            return layer

        self.logger.debug(
            f"Opcao somente feicoes selecionadas ativa. Total selecionadas: {layer.selectedFeatureCount()}"
        )
        selected_layer, error = VectorLayerGeometry.get_selected_features(
            layer, tool_key=self.TOOL_KEY
        )
        if error:
            self.logger.warning(f"Falha ao obter feicoes selecionadas: {error}")
            QgisMessageUtil.modal_error(self.iface, error)
            return None

        return selected_layer

    def _build_style(self):
        return {
            "background_color": self.fill_color_widget.get_color().name(QColor.NameFormat.HexRgb),
            "border_color": self.border_color_widget.get_color().name(QColor.NameFormat.HexRgb),
            "label_color": self.label_color_widget.get_color().name(QColor.NameFormat.HexRgb),
            "label_size": float(self.label_size_spin.get_value("label_size")),
            "border_width": float(self.border_width_spin.get_value("border_width")),
            "transparent_background": bool(
                self.options_checkbox.is_checked("transparent_background")
            ),
            "show_border": bool(self.options_checkbox.is_checked("show_border")),
            "show_label": bool(self.options_checkbox.is_checked("show_label")),
        }

    def _export_single_svg(self, layer, features, output_folder, style):
        base_name = SVGUtils.sanitize_filename(layer.name())
        output_path = SVGUtils.unique_svg_path(output_folder, base_name)
        label_text = layer.name()
        svg_content = SVGUtils.build_svg_document(
            layer, features, label_text, style, tool_key=self.TOOL_KEY
        )
        SVGUtils.write_svg(output_path, svg_content, tool_key=self.TOOL_KEY)
        self.logger.info(f"SVG unico gerado: {output_path}")
        return output_path

    def _export_one_svg_per_feature(self, layer, features, output_folder, style):
        generated = []
        for index, item in enumerate(features, start=1):
            feature = item["feature"]
            base_name = self._feature_output_base_name(layer, feature, index)
            output_path = SVGUtils.unique_svg_path(output_folder, base_name)
            label_text = self._feature_label(layer, feature, index)
            svg_content = SVGUtils.build_svg_document(
                layer, [item], label_text, style, tool_key=self.TOOL_KEY
            )
            SVGUtils.write_svg(output_path, svg_content, tool_key=self.TOOL_KEY)
            generated.append(output_path)
            self.logger.debug(f"SVG por feicao gerado: {output_path}")
        return generated

    def _feature_output_base_name(self, layer, feature, index):
        field_index = feature.fields().lookupField("Name")
        if field_index != -1:
            value = feature.attribute(field_index)
            if value is not None and str(value).strip():
                return SVGUtils.sanitize_filename(str(value).strip())

        return SVGUtils.sanitize_filename(f"{layer.name()}_{index}")

    def _feature_label(self, layer, feature, index):
        field_index = feature.fields().lookupField("Name")
        if field_index != -1:
            value = feature.attribute(field_index)
            if value is not None and str(value).strip():
                return str(value).strip()
        return f"{layer.name()}_{index}"


def run(iface):
    dlg = VectorToSvgPlugin(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg
