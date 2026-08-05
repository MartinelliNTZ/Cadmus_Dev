# -*- coding: utf-8 -*-
import os
from qgis.core import QgsProject
from ..plugins.BasePlugin import BasePluginMTL
from ..utils.Preferences import Preferences
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.ExplorerUtils import ExplorerUtils
from ..utils.ProjectUtils import ProjectUtils
from ..core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from ..core.engine_tasks.LoadFilesStep import LoadFilesStep
from ..core.engine_tasks.ExecutionContext import ExecutionContext
from ..i18n.TranslationManager import STR

# ── Novos Widgets ────────────────────────────────────────────────
from ..resources.widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.widgets.grid.GridCheckbox import GridCheckbox
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.widgets.CollapsibleParametersWidget import CollapsibleParametersWidget


# ============================================================
#  ** Janela Principal da Ferramenta **
# ============================================================


class LoadFolderLayersDialog(BasePluginMTL):

    TOOL_KEY = "load_folder_layers"
    ASYNC_THRESHOLD = 19

    FILE_TYPES = {
        "GeoPackage (*.gpkg)": (".gpkg",),
        "Shapefile (*.shp)": (".shp",),
        "GeoJSON (*.geojson *.json)": (".geojson", ".json"),
        "KML (*.kml)": (".kml",),
        "KMZ (*.kmz)": (".kmz",),
        "TIFF/GeoTIFF (*.tif *.tiff)": (".tif", ".tiff"),
        "ECW (*.ecw)": (".ecw",),
        "JPEG2000 (*.jp2)": (".jp2",),
        "ASCII GRID (*.asc)": (".asc",),
        "GPX (*.gpx)": (".gpx",),
        "CSV (*.csv)": (".csv",),
        "MapInfo TAB (*.tab)": (".tab",),
        "LAS/LAZ (*.las *.laz)": (".las", ".laz"),
    }

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface

        # Inicializar via BasePluginMTL
        self.init(
            self.TOOL_KEY,
            "LoadFolderLayersDialog",
            load_system_prefs=False,
            build_ui=True,
        )

    def _build_ui(self, **kwargs):
        # Constrói a UI padronizada usando novos widgets
        super()._build_ui(
            title=STR.LOAD_FOLDER_LAYERS_TITLE,
            icon_path="load_folder.ico",
            enable_scroll=False,
        )

        # ── 1. Seletor de pasta (GridComplexSelector) ─────────────
        self.folder_selector = GridComplexSelector(
            config={
                "folder": {
                    "label": STR.ROOT_FOLDER,
                    "description": "Selecione a pasta raiz para buscar arquivos",
                    "allow_folder": True,
                    "allow_file": False,
                    "mode_type": "input",
                    "show_copy_button": True,
                    "show_explorer_button": True,
                },
            },
            tool_key=self.TOOL_KEY,
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self.folder_selector)

        # ── 2. Opções (GridCheckbox com dependência preserve→lastfolder) ──
        self.chk_options = GridCheckbox(
            config={
                "missing_only": {
                    "label": STR.LOAD_ONLY_MISSING_FILES,
                    "default": False,
                },
                "preserve": {
                    "label": STR.PRESERVE_FOLDER_STRUCTURE,
                    "default": True,
                    "dependents": ["lastfolder"],  # ← O widget gerencia sozinho
                },
                "lastfolder": {
                    "label": STR.DO_NOT_GROUP_LAST_FOLDER,
                    "default": False,
                },
                "backup": {
                    "label": STR.CREATE_PROJECT_BACKUP_IF_SAVED,
                    "default": True,
                },
            },
            items_per_row=1,
            title=None,
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self.chk_options)

        # ── 3. Tipos de arquivo (Collapsible + GridCheckbox com botões) ──
        self.coll_widget = CollapsibleParametersWidget(
            title=STR.FILE_TYPES,
            expanded_by_default=False,
            parent=self,
        )

        file_config = {}
        for label in self.FILE_TYPES.keys():
            file_config[label] = {"label": label, "default": False}

        self.chk_types = GridCheckbox(
            config=file_config,
            items_per_row=2,
            title=None,
            control_buttons_config={
                "select_all": {
                    "label": "Selecionar Todos",
                    "callback": lambda: self.chk_types.select_all(),
                },
                "deselect_all": {
                    "label": "Desmarcar Todos",
                    "callback": lambda: self.chk_types.deselect_all(),
                },
                "invert": {
                    "label": "Inverter",
                    "callback": lambda: self.chk_types.invert_selection(),
                },
            },
            parent=self,
        )
        self.coll_widget.add_content_widget(self.chk_types)
        self.layout.addWidget(self.coll_widget)

        # Desabilitar backup se projeto não salvo
        if not QgsProject.instance().fileName():
            self.chk_options.set_checked("backup", False)
            self.chk_options.widget("backup").setEnabled(False)

        # ── 4. Botões de ação (GridExecutionButtons) ─────────────
        self.action_buttons = GridExecutionButtons(
            config={
                "run": {
                    "label": STR.LOAD_FILES,
                    "description": "Carrega todos os arquivos da pasta selecionada",
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

        # Carregar preferências
        self.logger.debug("Construindo interface de usuário", code="UI_BUILD")
        self._load_prefs()

    # ------------------------------------------------------------------
    def _load_prefs(self):
        """Carrega preferências e repopula widgets."""
        try:
            # Pasta
            folder = self.preferences.get("folder", "")
            if folder:
                self.folder_selector.set_path("folder", folder)

            # Tipos de arquivo
            saved_types = self.preferences.get("types", [])
            for label in self.FILE_TYPES.keys():
                self.chk_types.set_checked(label, label in saved_types)
            self.coll_widget.set_expanded(self.preferences.get("types_expanded", False))

            # Opções (dependência preserve→lastfolder é gerenciada pelo widget)
            self.chk_options.set_checked(
                "missing_only", self.preferences.get("missing_only", False)
            )
            self.chk_options.set_checked(
                "preserve", self.preferences.get("preserve", True)
            )
            self.chk_options.set_checked(
                "lastfolder", self.preferences.get("lastfolder", False)
            )
            self.chk_options.set_checked(
                "backup", self.preferences.get("backup", True)
            )

            # backup só se projeto salvo
            if not QgsProject.instance().fileName():
                self.chk_options.set_checked("backup", False)
                self.chk_options.widget("backup").setEnabled(False)

        except Exception as e:
            self.logger.error(f"Erro ao carregar preferências: {e}")

    # ------------------------------------------------------------------
    def _save_prefs(self):
        """Salva preferências."""
        try:
            states = self.chk_types.get_all_states()
            selected_types = [
                label for label, checked in states.items() if checked
            ]
            folder = self.folder_selector.get_path("folder") or ""

            self.preferences["folder"] = folder
            self.preferences["types"] = selected_types
            self.preferences["missing_only"] = self.chk_options.is_checked("missing_only")
            self.preferences["preserve"] = self.chk_options.is_checked("preserve")
            self.preferences["lastfolder"] = self.chk_options.is_checked("lastfolder")
            self.preferences["backup"] = self.chk_options.is_checked("backup")
            self.preferences["window_width"] = self.width()
            self.preferences["window_height"] = self.height()
            self.preferences["types_expanded"] = self.coll_widget.is_expanded()

            Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
        except Exception as e:
            self.logger.error(f"Erro ao salvar preferências: {e}")

    # ------------------------------------------------------------------
    def execute_tool(self):
        """Executa a ferramenta de carregamento."""
        folder = self.folder_selector.get_path("folder") or ""
        self.start_stats(folder)

        self.logger.info(f"Iniciando execução: pasta={folder}", code="EXEC_START")

        if not folder or not os.path.isdir(folder):
            QgisMessageUtil.bar_warning(self.iface, STR.SELECT_VALID_FOLDER)
            return

        backup_file = None
        if self.chk_options.is_checked("backup"):
            try:
                backup_file = ProjectUtils.create_project_backup(QgsProject.instance())
            except Exception as e:
                self.logger.error(
                    f"Erro criando backup do projeto: {e}", code="BACKUP_ERROR"
                )

        # coletar extensões selecionadas
        extensions = []
        for label in self.FILE_TYPES.keys():
            if self.chk_types.is_checked(label):
                extensions.extend(self.FILE_TYPES.get(label, []))

        if not extensions:
            QgisMessageUtil.bar_warning(self.iface, STR.SELECT_AT_LEAST_ONE_FILE_TYPE)
            return

        # scan via ExplorerUtils
        records = ExplorerUtils.scan_folder(folder, extensions, self.TOOL_KEY)
        self.logger.info(
            f"scan_folder retornou {len(records)} registros", code="SCAN_COMPLETE"
        )

        # decidir entre execução síncrona ou assíncrona baseado no número de arquivos
        total_files = len(records)
        if total_files > self.ASYNC_THRESHOLD:
            self.logger.info(
                f"Arquivos ({total_files}) acima do limiar ({self.ASYNC_THRESHOLD}), "
                f"usando execução assíncrona",
                code="EXEC_STRATEGY",
            )
            return self._run_async_pipeline(
                folder=folder, records=records, backup_file=backup_file
            )
        else:
            self.logger.info(
                f"Arquivos ({total_files}) dentro do limiar ({self.ASYNC_THRESHOLD}), "
                f"usando execução síncrona",
                code="EXEC_STRATEGY",
            )
            return self._run_sync_pipeline(
                folder=folder, records=records, backup_file=backup_file
            )

    def _run_sync_pipeline(self, folder: str, records: list, backup_file: str = None):
        """Executa o carregamento de forma síncrona."""
        project = QgsProject.instance()
        already_loaded = set()
        if self.chk_options.is_checked("missing_only"):
            for layer in project.mapLayers().values():
                src = ProjectUtils.normalize_layer_source(layer.source())
                already_loaded.add(src)

        loaded_count = 0

        for rec in records:
            path = rec.get("path")
            norm = ProjectUtils.normalize_layer_source(path)
            if self.chk_options.is_checked("missing_only") and norm in already_loaded:
                continue

            layer = ExplorerUtils.create_layer(rec, self.TOOL_KEY)
            if not layer or not layer.isValid():
                continue

            if self.chk_options.is_checked("preserve"):
                rel = os.path.relpath(os.path.dirname(path), folder)

                # Se lastfolder estiver ativo, nem sempre queremos o último nível
                if self.chk_options.is_checked("lastfolder") and rel not in (".", ""):
                    parts = rel.split(os.sep)
                    if len(parts) > 1:
                        rel = os.path.join(*parts[:-1])
                    else:
                        rel = "."

                if rel == ".":
                    ProjectUtils.add_layer(layer, add_to_root=True)
                else:
                    group = ProjectUtils.ensure_group(rel)
                    ProjectUtils.add_layer_to_group(layer, group)
            else:
                ProjectUtils.add_layer(layer, add_to_root=True)

            loaded_count += 1
            self.logger.debug(
                f"Layer carregada e adicionada: {path}", code="LAYER_ADDED"
            )
        self.finish_stats()
        QgisMessageUtil.modal_info(
            self.iface,
            f"{STR.FILES_LOADED_PREFIX} {loaded_count} {STR.FILES_SUFFIX}",
        )

    def _run_async_pipeline(self, folder: str, records: list, backup_file: str = None):
        """Inicia pipeline assíncrona para carregar arquivos em background."""
        self.logger.info(
            "_run_async_pipeline: iniciando pipeline assíncrona", code="ASYNC_START"
        )

        ctx = ExecutionContext(
            {
                "folder": folder,
                "records": records,
                "tool_key": self.TOOL_KEY,
                "preserve": self.chk_options.is_checked("preserve"),
                "last_folder": self.chk_options.is_checked("lastfolder"),
                "missing_only": self.chk_options.is_checked("missing_only"),
                "backup_file": backup_file,
                "parent": self,
            }
        )

        engine = AsyncPipelineEngine(
            steps=[LoadFilesStep()],
            context=ctx,
            on_finished=self._on_async_finished,
            on_error=self._on_async_error,
        )

        try:
            engine.start()
            QgisMessageUtil.bar_info(self.iface, STR.ASYNC_STARTED)
        except Exception as e:
            self.logger.error(
                f"Falha iniciando pipeline assíncrona: {e}", code="ASYNC_ERROR"
            )
            QgisMessageUtil.bar_critical(self.iface, f"{STR.ASYNC_START_ERROR} {e}")
        return None

    def _on_async_finished(self, context: ExecutionContext):
        loaded = context.get("loaded_count", 0)
        self.finish_stats()
        self.logger.info(f"_on_async_finished: loaded={loaded}", code="ASYNC_FINISH")
        QgisMessageUtil.bar_info(
            self.iface,
            f"{STR.ASYNC_FINISHED} {STR.FILES_LOADED_PREFIX} {loaded} {STR.FILES_SUFFIX}",
        )

    def _on_async_error(self, errors):
        self.logger.error(f"_on_async_error: {errors}", code="ASYNC_ERROR")
        QgisMessageUtil.modal_error(self.iface, f"{STR.ASYNC_EXECUTION_ERROR} {errors}")


# Função pública
def run(iface):
    dlg = LoadFolderLayersDialog(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg