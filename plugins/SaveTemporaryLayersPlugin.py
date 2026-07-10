# -*- coding: utf-8 -*-
"""
Salvar Temporárias — Salva camadas temporárias (memory) do projeto QGIS
em arquivos permanentes no disco.

UI:
  - InputFieldsWidget: prefixo + sufixo
  - DropdownSelectorWidget: extensões vetor (shp, gpkg, geojson, ...)
  - DropdownSelectorWidget: extensões raster (tif, jp2, png, ...)
  - Output folder com 3 botões:
      📁 selecionar pasta manualmente
      🛠️ sugerir pasta do projeto
      ➡️ abrir explorer

  Vetores salvos em <output>/vectors/
  Rasters salvos em <output>/rasters/
"""

import os
from ..plugins.BasePlugin import BasePluginMTL
from ..core.ui.WidgetFactory import WidgetFactory
from ..i18n.TranslationManager import STR
from ..utils.ToolKeys import ToolKey
from ..utils.Preferences import Preferences
from ..utils.ProjectUtils import ProjectUtils
from ..utils.ExplorerUtils import ExplorerUtils
from ..utils.QgisMessageUtil import QgisMessageUtil
from qgis.PyQt.QtWidgets import QHBoxLayout, QLineEdit, QPushButton
from qgis.PyQt.QtCore import QTimer


class SaveTemporaryLayersPlugin(BasePluginMTL):
    """
    Ferramenta para salvar camadas temporárias (memory) do projeto QGIS
    em arquivos permanentes no disco.
    """

    VECTOR_EXTENSIONS = {
        ".gpkg": "GeoPackage (.gpkg)",
        ".shp": "Shapefile (.shp)",
        ".geojson": "GeoJSON (.geojson)",
        ".kml": "KML (.kml)",
        ".dxf": "DXF (.dxf)",
        ".gml": "GML (.gml)",
        ".csv": "CSV (.csv)",
    }

    RASTER_EXTENSIONS = {
        ".tif": "TIFF (.tif)",
        ".jp2": "JPEG 2000 (.jp2)",
        ".png": "PNG (.png)",
        ".jpg": "JPEG (.jpg)",
    }

    VECTOR_SUBFOLDER = "vectors"
    RASTER_SUBFOLDER = "rasters"

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.init(ToolKey.SAVE_TEMPORARY_LAYER, "SaveTemporaryLayersPlugin")

    def _build_ui(self, **kwargs):
        self.logger.debug("Inicializando PLUGIN SaveTemporaryLayersPlugin")
        super()._build_ui(
            title=STR.SAVE_TEMPORARY_LAYER_TITLE,
            icon_path="save_temporary_layer.ico",
            enable_scroll=True,
        )
        self.logger.info("Construindo interface da ferramenta")

        # ── Prefixo e Sufixo (InputFieldsWidget) ──
        fields_dict = {
            "prefix": {
                "title": f"{STR.PREFIX}:",
                "type": "text",
                "default": "",
                "description": "Prefixo adicionado ao nome dos arquivos de saída",
            },
            "suffix": {
                "title": f"{STR.SUFFIX}:",
                "type": "text",
                "default": "",
                "description": "Sufixo adicionado ao nome dos arquivos de saída",
            },
        }
        fields_layout, self.fields_widget = (
            WidgetFactory.create_input_fields_widget(
                fields_dict=fields_dict,
                parent=self,
                separator_bottom=True,
            )
        )

        # ── Extensão Vetor (DropdownSelectorWidget) ──
        vector_ext_layout, self.vector_ext_selector = (
            WidgetFactory.create_dropdown_selector(
                title=f"{STR.VECTOR_EXTENSIONS}:",
                options_dict=self.VECTOR_EXTENSIONS,
                selected_key=".gpkg",
                parent=self,
                separator_bottom=True,
            )
        )

        # ── Extensão Raster (DropdownSelectorWidget) ──
        raster_ext_layout, self.raster_ext_selector = (
            WidgetFactory.create_dropdown_selector(
                title=f"{STR.RASTER_EXTENSIONS}:",
                options_dict=self.RASTER_EXTENSIONS,
                selected_key=".tif",
                parent=self,
                separator_bottom=True,
            )
        )

        # ── Pasta de saída com 3 botões (PyQt5 nativo, sem PySide6) ──
        output_layout, self.output_path, self._output_buttons = (
            self._build_output_folder_selector()
        )

        # ── Botões de ação ──
        buttons_layout, self.action_buttons = (
            WidgetFactory.create_bottom_action_buttons(
                parent=self,
                run_callback=self.execute_tool,
                close_callback=self.close,
                info_callback=self.show_info_dialog,
                tool_key=self.TOOL_KEY,
                run_text=STR.SAVE,
            )
        )

        self.layout.add_items(
            [
                fields_layout,
                vector_ext_layout,
                raster_ext_layout,
                output_layout,
                buttons_layout,
            ]
        )
        self.logger.info("Interface da ferramenta construída com sucesso")

    def _build_output_folder_selector(self):
        """Constrói seletor de pasta com 📁 🛠️ ➡️ usando PyQt5."""
        from ..resources.styles.Styles import Styles
        from qgis.PyQt.QtWidgets import QVBoxLayout, QFrame

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        # Label
        from qgis.PyQt.QtWidgets import QLabel

        lbl = QLabel(f"{STR.OUTPUT_FOLDER}:")
        lbl.setMinimumWidth(100)
        row.addWidget(lbl)

        # Line edit
        path_edit = QLineEdit()
        path_edit.setPlaceholderText("Selecione a pasta de saída...")
        path_edit.setStyleSheet(Styles.input())
        path_edit.setReadOnly(True)
        row.addWidget(path_edit)

        # 📁 folder button
        btn_folder = QPushButton("📁")
        btn_folder.setFixedWidth(32)
        btn_folder.setToolTip("Selecionar pasta de saída")
        btn_folder.clicked.connect(lambda: self._on_browse_folder(path_edit))
        row.addWidget(btn_folder)

        # 🛠️ suggest button
        btn_suggest = QPushButton("🛠️")
        btn_suggest.setFixedWidth(30)
        btn_suggest.setToolTip("Usar pasta do projeto")
        btn_suggest.clicked.connect(lambda: self._on_suggest_path(path_edit))
        row.addWidget(btn_suggest)

        # ➡️ explorer button
        btn_explorer = QPushButton("➡️")
        btn_explorer.setFixedWidth(30)
        btn_explorer.setToolTip("Abrir localização no Explorer")
        btn_explorer.clicked.connect(lambda: self._on_open_explorer(path_edit))
        row.addWidget(btn_explorer)

        layout.addLayout(row)
        return layout, path_edit, (btn_folder, btn_suggest, btn_explorer)

    def _on_browse_folder(self, path_edit):
        """📁 Abre diálogo de selecionar pasta."""
        initial_dir = path_edit.text() or ""
        folder = ExplorerUtils.select_directory_dialog(
            STR.SELECT_OUTPUT_FOLDER, initial_dir, self
        )
        if folder:
            path_edit.setText(folder)

    def _on_suggest_path(self, path_edit):
        """🛠️ Sugere pasta do projeto."""
        project = ProjectUtils.get_project_instance()
        project_path = ProjectUtils.get_project_dir(project)
        if project_path:
            suggested = project_path
            if os.path.isfile(project_path):
                suggested = os.path.dirname(project_path)
            path_edit.setText(suggested)
            self.logger.info(f"Pasta do projeto sugerida: {suggested}")
        else:
            QgisMessageUtil.bar_warning(
                self.iface,
                "Salve o projeto primeiro para usar esta opção.",
            )

    def _on_open_explorer(self, path_edit):
        """➡️ Abre Explorer no diretório."""
        current = path_edit.text()
        if current:
            ExplorerUtils.open_folder(current, tool_key=self.TOOL_KEY)
        else:
            QgisMessageUtil.bar_warning(
                self.iface,
                "Selecione ou sugira uma pasta primeiro.",
            )

    def _load_prefs(self):
        """Carrega preferências salvas."""
        self.logger.debug("Carregando preferências")
        prefix = self.preferences.get("prefix", "")
        suffix = self.preferences.get("suffix", "")
        self.fields_widget.set_values({"prefix": prefix, "suffix": suffix})

        vector_ext = self.preferences.get("vector_extension", ".gpkg")
        self.vector_ext_selector.set_selected_key(vector_ext)

        raster_ext = self.preferences.get("raster_extension", ".tif")
        self.raster_ext_selector.set_selected_key(raster_ext)

        output_path = self.preferences.get("output_path", "")
        if output_path:
            self.output_path.setText(output_path)

    def _save_prefs(self):
        """Salva preferências."""
        self.logger.debug("Salvando preferências")
        values = self.fields_widget.get_values()
        self.preferences["prefix"] = values.get("prefix", "")
        self.preferences["suffix"] = values.get("suffix", "")
        self.preferences["vector_extension"] = (
            self.vector_ext_selector.get_selected_key()
        )
        self.preferences["raster_extension"] = (
            self.raster_ext_selector.get_selected_key()
        )
        self.preferences["output_path"] = self.output_path.text()
        self.preferences["window_width"] = self.width()
        self.preferences["window_height"] = self.height()
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)

    def _get_temporary_layers(self):
        """
        Retorna as camadas temporárias (memory) do projeto QGIS atual.

        Usa ProjectUtils.get_temporary_layers() que itera por project.mapLayers()
        e filtra por providerType() == "memory".

        Returns:
            tuple: (vector_layers, raster_layers)
                vector_layers: list de (nome, QgsVectorLayer)
                raster_layers: list de (nome, QgsRasterLayer)
        """
        vector_layers = []
        raster_layers = []

        from qgis.core import QgsVectorLayer, QgsRasterLayer

        project = ProjectUtils.get_project_instance()
        if not project:
            self.logger.warning("Nenhum projeto QGIS aberto")
            return [], []

        # Usa o novo método do ProjectUtils com logger para debug detalhado
        temp_layers = ProjectUtils.get_temporary_layers(
            project=project,
            provider_name="memory",
            logger=self.logger,
        )

        self.logger.debug(
            f"get_temporary_layers retornou {len(temp_layers)} camada(s)"
        )

        for layer in temp_layers:
            self.logger.debug(
                f"Processando camada temporária: name='{layer.name()}', "
                f"type(QgsVectorLayer)={isinstance(layer, QgsVectorLayer)}, "
                f"type(QgsRasterLayer)={isinstance(layer, QgsRasterLayer)}, "
                f"providerType()='{layer.providerType()}'"
            )

            if isinstance(layer, QgsVectorLayer):
                vector_layers.append((layer.name(), layer))
            elif isinstance(layer, QgsRasterLayer):
                raster_layers.append((layer.name(), layer))
            else:
                self.logger.warning(
                    f"Camada temporária ignorada por tipo desconhecido: "
                    f"name='{layer.name()}', type={type(layer).__name__}"
                )

        self.logger.info(
            f"Camadas temporárias encontradas: {len(vector_layers)} vetor(es), "
            f"{len(raster_layers)} raster(s)"
        )
        return vector_layers, raster_layers

    def execute_tool(self):
        """Salva camadas temporárias em arquivos permanentes."""
        self.logger.info("Iniciando salvamento de camadas temporárias")

        # Resolver pasta de saída
        output_root = self.output_path.text().strip()

        if not output_root:
            # Tentar usar pasta do projeto
            project = ProjectUtils.get_project_instance()
            project_path = ProjectUtils.get_project_dir(project)
            if project_path:
                output_root = project_path
                if os.path.isfile(project_path):
                    output_root = os.path.dirname(project_path)
                self.logger.info(f"Usando pasta do projeto: {output_root}")
            else:
                self.logger.warning("Nenhuma pasta de saída selecionada e nenhum projeto salvo")
                QgisMessageUtil.bar_warning(
                    self.iface,
                    "Selecione uma pasta de saída ou salve o projeto primeiro.",
                )
                return

        # Garantir pastas
        try:
            os.makedirs(output_root, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Erro ao criar pasta de saída: {e}")
            return

        vectors_dir = os.path.join(output_root, self.VECTOR_SUBFOLDER)
        rasters_dir = os.path.join(output_root, self.RASTER_SUBFOLDER)
        try:
            os.makedirs(vectors_dir, exist_ok=True)
            os.makedirs(rasters_dir, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Erro ao criar subpastas: {e}")
            return

        # Obter valores
        values = self.fields_widget.get_values()
        prefix = values.get("prefix", "")
        suffix = values.get("suffix", "")
        vector_ext = self.vector_ext_selector.get_selected_key() or ".gpkg"
        raster_ext = self.raster_ext_selector.get_selected_key() or ".tif"

        if not vector_ext.startswith("."):
            vector_ext = f".{vector_ext}"
        if not raster_ext.startswith("."):
            raster_ext = f".{raster_ext}"

        self.logger.info(
            f"Parâmetros: prefix='{prefix}', suffix='{suffix}', "
            f"vector_ext='{vector_ext}', raster_ext='{raster_ext}', "
            f"output='{output_root}'"
        )

        vector_layers, raster_layers = self._get_temporary_layers()

        if not vector_layers and not raster_layers:
            self.logger.info("Nenhuma camada temporária encontrada para salvar")
            QgisMessageUtil.bar_info(
                self.iface,
                "Nenhuma camada temporária encontrada no projeto.",
            )
            return

        saved_count = 0
        errors = []

        for layer_name, layer in vector_layers:
            filename = f"{prefix}{layer_name}{suffix}{vector_ext}"
            filepath = os.path.join(vectors_dir, filename)
            try:
                from qgis.core import QgsVectorFileWriter, QgsCoordinateTransformContext

                write_options = QgsVectorFileWriter.SaveVectorOptions()
                write_options.driverName = self._driver_for_ext(vector_ext)
                write_options.fileEncoding = "UTF-8"

                result = QgsVectorFileWriter.writeAsVectorFormatV3(
                    layer, filepath, QgsCoordinateTransformContext(), write_options
                )

                # Retorno varia conforme versão do QGIS:
                # - QGIS < 3.28: (error_code, error_message)
                # - QGIS >= 3.28: (error_code, error_message, new_filename)
                # Normaliza para (error_code, error_message)
                if isinstance(result, tuple) and len(result) >= 2:
                    error = result[0]
                    error_msg = result[1]
                else:
                    error = result
                    error_msg = ""

                if error == QgsVectorFileWriter.NoError:
                    self.logger.info(f"Vetor salvo: {filepath}")
                    saved_count += 1
                else:
                    error_msg_text = f"Erro ao salvar vetor '{layer_name}': {error_msg}"
                    self.logger.error(error_msg_text)
                    errors.append(error_msg_text)

            except Exception as e:
                err_msg = f"Exceção ao salvar vetor '{layer_name}': {e}"
                self.logger.error(err_msg)
                errors.append(err_msg)

        for layer_name, layer in raster_layers:
            filename = f"{prefix}{layer_name}{suffix}{raster_ext}"
            filepath = os.path.join(rasters_dir, filename)
            try:
                from qgis.core import QgsRasterFileWriter, QgsCoordinateTransformContext

                file_writer = QgsRasterFileWriter(filepath)
                file_writer.writeRasterLayer(
                    layer,
                    layer.extent(),
                    layer.crs(),
                    QgsCoordinateTransformContext(),
                )

                self.logger.info(f"Raster salvo: {filepath}")
                saved_count += 1

            except Exception as e:
                err_msg = f"Exceção ao salvar raster '{layer_name}': {e}"
                self.logger.error(err_msg)
                errors.append(err_msg)

        if errors:
            msg = (
                f"Salvas: {saved_count} camada(s). "
                f"Erros: {len(errors)}. "
                f"Vetores em: {vectors_dir}, Rasters em: {rasters_dir}"
            )
            self.logger.warning(msg)
            QgisMessageUtil.bar_warning(self.iface, msg)
        else:
            msg = (
                f"{saved_count} camada(s) temporária(s) salva(s) com sucesso! "
                f"Vetores em: {vectors_dir}, Rasters em: {rasters_dir}"
            )
            self.logger.info(msg)
            QgisMessageUtil.bar_info(self.iface, msg)

    @staticmethod
    def _driver_for_ext(ext: str) -> str:
        """Retorna o nome do driver GDAL para a extensão."""
        driver_map = {
            ".gpkg": "GPKG",
            ".shp": "ESRI Shapefile",
            ".geojson": "GeoJSON",
            ".kml": "KML",
            ".dxf": "DXF",
            ".gml": "GML",
            ".csv": "CSV",
        }
        return driver_map.get(ext, "GPKG")


def run(iface):
    dlg = SaveTemporaryLayersPlugin(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg