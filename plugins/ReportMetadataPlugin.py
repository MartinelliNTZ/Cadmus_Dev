# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QComboBox, QSizePolicy

from ..core.ui.WidgetFactory import WidgetFactory
from ..core.services.ReportGenerationService import ReportGenerationService
from ..i18n.TranslationManager import STR
from ..resources.IconManager import IconManager as im
from ..plugins.BasePlugin import BasePluginMTL
from ..utils.ExplorerUtils import ExplorerUtils
from ..utils.Preferences import Preferences
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.ToolKeys import ToolKey
from ..utils.vector.VectorLayerAttributes import VectorLayerAttributes
from ..utils.vector.VectorLayerGeometry import VectorLayerGeometry
from ..utils.mrk.MetadataFields import MetadataFields


class ReportMetadataPlugin(BasePluginMTL):
    """Ferramenta para regerar relatorios HTML a partir de JSONs temporarios."""

    TOOL_KEY = ToolKey.REPORT_METADATA
    PREF_SELECTED_JSON = "selected_json"

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.json_options = {}
        self.init(self.TOOL_KEY, self.__class__.__name__)

    def _build_ui(self, **kwargs):
        super()._build_ui(
            title=STR.REPORT_METADATA_TITLE,
            icon_path=im.REPORT_METADATA,
            enable_scroll=True,
        )

        self._reload_json_options(initial=True)

        dropdown_layout, self.json_selector = WidgetFactory.create_dropdown_selector(
            title="JSON:",
            options_dict=self.json_options,
            selected_key=self.preferences.get(self.PREF_SELECTED_JSON),
            allow_empty=True,
            empty_text=STR.SELECT,
            separator_top=False,
            separator_bottom=False,
            parent=self,
        )

        refresh_layout, self.refresh_button = WidgetFactory.create_simple_button(
            text=STR.REFRESH_JSON_LIST,
            parent=self,
            spacing=8,
        )
        self.refresh_button.clicked.connect(self._on_refresh)

        open_json_layout, self.open_json_button = WidgetFactory.create_simple_button(
            text=STR.OPEN_JSONS_FOLDER,
            parent=self,
            spacing=8,
        )
        self.open_json_button.clicked.connect(self._open_json_folder)

        open_reports_layout, self.open_reports_button = WidgetFactory.create_simple_button(
            text=STR.OPEN_REPORTS_FOLDER,
            parent=self,
            spacing=8,
        )
        self.open_reports_button.clicked.connect(self._open_reports_folder)

        # === NOVO BOTAO: VETORIZAR VOO A PARTIR DO JSON ===
        vetorize_layout, self.vetorize_button = WidgetFactory.create_simple_button(
            text=STR.VETORIZE_FLIGHT,
            parent=self,
            spacing=8,
        )
        self.vetorize_button.clicked.connect(self._vectorize_from_json)

        buttons_layout, _ = WidgetFactory.create_bottom_action_buttons(
            parent=self,
            run_callback=self.execute_tool,
            close_callback=self.close,
            info_callback=self.show_info_dialog,
            tool_key=self.TOOL_KEY,
            run_text=STR.GENERATE_REPORT,
        )

        self.layout.add_items(
            [
                dropdown_layout,
                refresh_layout,
                open_json_layout,
                open_reports_layout,
                vetorize_layout,
                buttons_layout,
            ]
        )
        self._apply_compact_horizontal_ui()

    def _apply_compact_horizontal_ui(self):
        """Evita largura horizontal excessiva no plugin de relatorios."""
        try:
            combo = self.json_selector.combo()
            if isinstance(combo, QComboBox):
                # Evita que o maior texto do JSON force largura minima gigante.
                combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
                combo.setMinimumContentsLength(24)
                combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                combo.setMaximumWidth(520)

            for btn in (
                self.refresh_button,
                self.open_json_button,
                self.open_reports_button,
                self.vetorize_button,
            ):
                btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
                btn.setMaximumWidth(360)
                btn.setCursor(Qt.PointingHandCursor)
        except Exception as e:
            self.logger.warning(f"Falha ao ajustar UI compacta: {e}")

    def _format_json_label(self, file_path: str) -> str:
        file_name = os.path.basename(file_path)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            size_kb = round(os.path.getsize(file_path) / 1024.0, 1)
            return f"{file_name}"
        except Exception:
            return file_name

    def _list_json_files(self):
        json_dir = ExplorerUtils.get_temp_folder(
            self.TOOL_KEY,
            ExplorerUtils.REPORTS_TEMP_FOLDER,
            ExplorerUtils.REPORTS_JSON_FOLDER,
        )
        files = []
        if os.path.isdir(json_dir):
            for name in os.listdir(json_dir):
                if name.lower().endswith(".json"):
                    files.append(os.path.join(json_dir, name))
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return files

    def _reload_json_options(self, initial=False):
        files = self._list_json_files()
        self.json_options = {path: self._format_json_label(path) for path in files}
        if not initial:
            self.json_selector.set_options(self.json_options)
        self.logger.info(
            "Lista de JSONs temporarios atualizada",
            data={"total_json": len(self.json_options)},
        )

    def _on_refresh(self):
        self._reload_json_options(initial=False)
        if not self.json_options:
            QgisMessageUtil.bar_warning(
                self.iface,
                STR.NO_JSON_FOUND,
            )

    def _open_reports_folder(self):
        folder = ExplorerUtils.get_temp_folder(
            self.TOOL_KEY,
            ExplorerUtils.REPORTS_TEMP_FOLDER,
            ExplorerUtils.REPORTS_HTML_FOLDER,
        )
        ExplorerUtils.ensure_folder_exists(folder, self.TOOL_KEY)
        if not ExplorerUtils.open_folder(folder, self.TOOL_KEY):
            QgisMessageUtil.modal_warning(self.iface, STR.INVALID_FOLDER)

    def _open_json_folder(self):
        folder = ExplorerUtils.get_temp_folder(
            self.TOOL_KEY,
            ExplorerUtils.REPORTS_TEMP_FOLDER,
            ExplorerUtils.REPORTS_JSON_FOLDER,
        )
        ExplorerUtils.ensure_folder_exists(folder, self.TOOL_KEY)
        if not ExplorerUtils.open_folder(folder, self.TOOL_KEY):
            QgisMessageUtil.modal_warning(self.iface, STR.INVALID_FOLDER)

    def _save_prefs(self):
        selected = self.json_selector.get_selected_key() if self.json_selector else ""
        self.preferences[self.PREF_SELECTED_JSON] = selected or ""
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)

    def _load_prefs(self):
        self.logger.debug("Carregando preferências do ReportMetadataPlugin")

    # ─────────────────────────────────────────────────────────
    # VETORIZAR VOO A PARTIR DO JSON
    # ─────────────────────────────────────────────────────────
    def _vectorize_from_json(self):
        """Gera camada vetorial de pontos e rastro a partir do JSON selecionado."""
        selected_json = self.json_selector.get_selected_key() if self.json_selector else ""
        if not selected_json:
            QgisMessageUtil.modal_warning(self.iface, STR.SELECT_FILE)
            return

        if not os.path.isfile(selected_json):
            QgisMessageUtil.modal_warning(
                self.iface,
                f"{STR.FILE_NOT_FOUND}: {selected_json}",
            )
            return

        self.logger.info(
            "Iniciando vetorizacao a partir do JSON",
            data={"json_path": selected_json},
        )

        try:
            # Usa o JsonToVectorTranslator para criar a camada de pontos
            from ..core.translator.JsonToVectorTranslator import JsonToVectorTranslator

            # Determinar layer name baseado no titulo do JSON ou nome do arquivo
            layer_name = self._resolve_layer_name(selected_json)
            source = self._resolve_source(selected_json)

            translator = JsonToVectorTranslator(tool_key=self.TOOL_KEY)
            layer = translator.translate(
                json_path=selected_json,
                layer_name=layer_name,
                selected_keys=None,
                source=source,
            )

            if not layer or not layer.isValid():
                raise RuntimeError("Falha ao criar camada vetorial via JsonToVectorTranslator")

            # Reordenar campos alfabeticamente
            sorted_layer = VectorLayerAttributes.reorder_fields_alphabetically(layer)
            if sorted_layer is not None:
                layer = sorted_layer

            # Adicionar ao projeto
            QgsProject.instance().addMapLayer(layer)

            # Gerar rastro (linha) a partir dos pontos
            self._create_track_from_layer(layer)

            self._save_prefs()
            total = int(layer.featureCount())
            QgisMessageUtil.bar_success(
                self.iface,
                f"Voo vetorizado: {total} pontos e rastro gerados.",
            )

        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            self.logger.error(
                f"Erro ao vetorizar voo: {e}\nTraceback:\n{tb_str}",
            )
            QgisMessageUtil.modal_error(self.iface, f"Erro ao vetorizar voo: {e}")

    def _resolve_layer_name(self, json_path: str) -> str:
        """Resolve o nome da layer a partir do titulo do JSON ou nome do arquivo."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            titulo = data.get("titulo", "")
            if titulo:
                return f"Flight_{titulo}"
        except Exception:
            pass
        # Fallback: usar nome do arquivo sem extensao
        stem = os.path.splitext(os.path.basename(json_path))[0]
        return f"Flight_{stem}"

    def _resolve_source(self, json_path: str) -> str:
        """Resolve a fonte de coordenadas do JSON."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("source", "mrk+photo")
        except Exception:
            return "mrk+photo"

    def _create_track_from_layer(self, layer: QgsVectorLayer):
        """Cria camada de rastro (linha) a partir da camada de pontos."""
        try:
            order_field = self._resolve_track_order_field(layer)
            group_fields = self._resolve_track_group_fields(layer)
            vl_line = VectorLayerGeometry.create_line_layer_from_points(
                list(layer.getFeatures()),
                order_by_field=order_field,
                group_by_fields=group_fields,
                attribute_fields=MetadataFields.default_track_attribute_keys(),
            )
            if vl_line:
                QgsProject.instance().addMapLayer(vl_line)
                self.logger.info(
                    "Rastro criado com sucesso",
                    data={"layer_name": vl_line.name(), "features": vl_line.featureCount()},
                )
        except Exception as e:
            self.logger.error(f"Falha ao gerar camada de rastro: {e}")

    @staticmethod
    def _resolve_track_order_field(layer):
        candidates = [
            "Foto",
            "foto",
            "PhotoNum",
            MetadataFields.resolve_output_name("Foto"),
            "mrk_index",
            "id",
        ]
        for name in candidates:
            if name and layer.fields().lookupField(name) != -1:
                return name
        return layer.fields().field(0).name()

    @staticmethod
    def _resolve_track_group_fields(layer):
        pairs = [
            ("MrkPath", "MrkFile"),
            ("mrk_path", "mrk_file"),
            (
                MetadataFields.resolve_output_name("MrkPath"),
                MetadataFields.resolve_output_name("MrkFile"),
            ),
        ]
        for a, b in pairs:
            if layer.fields().lookupField(a) != -1 and layer.fields().lookupField(b) != -1:
                return [a, b]
        return None

    # ─────────────────────────────────────────────────────────
    # EXECUTAR (GERAR RELATORIO)
    # ─────────────────────────────────────────────────────────
    def execute_tool(self):
        selected_json = self.json_selector.get_selected_key() if self.json_selector else ""
        if not selected_json:
            QgisMessageUtil.modal_warning(self.iface, STR.SELECT_FILE)
            return

        if not os.path.isfile(selected_json):
            QgisMessageUtil.modal_warning(
                self.iface,
                f"{STR.FILE_NOT_FOUND}: {selected_json}",
            )
            return

        try:
            payload = ReportGenerationService(tool_key=self.TOOL_KEY).generate_from_json(
                selected_json
            )
            html_path = payload.get("html_path", "")
            if html_path:
                if not ExplorerUtils.open_file(html_path, self.TOOL_KEY):
                    QgisMessageUtil.bar_warning(
                        self.iface,
                        f"{STR.WARNING}: nao foi possivel abrir o HTML automaticamente.",
                    )
            self._save_prefs()
            QgisMessageUtil.bar_success(
                self.iface,
                f"{STR.SUCCESS_MESSAGE} {html_path}",
            )
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            self.logger.error(f"Erro ao gerar relatorio via plugin: {e}\nTraceback:\n{tb_str}")
            QgisMessageUtil.modal_error(self.iface, f"{STR.ERROR}: {e}")


def run(iface):
    dlg = ReportMetadataPlugin(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg