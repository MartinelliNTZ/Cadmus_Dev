# -*- coding: utf-8 -*-
import os
import re
from pathlib import Path

from ..core.ui.dialogs.DefaultProjectsFolderDialog import DefaultProjectsFolderDialog
from ..core.ui.dialogs.ProjectNameDialog import ProjectNameDialog
from ..i18n.TranslationManager import STR
from ..plugins.BasePlugin import BasePluginMTL
from ..resources.OtherFilesManager import OtherFilesManager
from ..utils.ExplorerUtils import ExplorerUtils
from ..utils.Preferences import Preferences
from ..utils.ProjectUtils import ProjectUtils
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.raster.RasterLayerSource import RasterLayerSource
from ..utils.ToolKeys import ToolKey
from ..utils.vector.VectorLayerSource import VectorLayerSource


class CreateProjectPlugin(BasePluginMTL):
    PROJECTS_FOLDER_PREF_KEY = "projects_folder"
    TOOL_KEY = ToolKey.CREATE_PROJECT
    GENERIC_PROJECT_PATTERN = re.compile(r"^NovoProjeto_(\d+)$")
    DEFAULT_CRS_AUTHID = "EPSG:4326"
    DEFAULT_CRS_PREF_KEY = "default_crs_authid"
    DEFAULT_GOOGLE_BASEMAP_STYLE = "hybrid"
    SCENARIO_UNSAVED_WITH_CONTENT = 1
    SCENARIO_SAVED_CURRENT_PROJECT = 2
    SCENARIO_UNSAVED_EMPTY_PROJECT = 3

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self._system_prefs = {}
        self._base_folder = ""
        self._project_name = ""
        self._default_crs_authid = ""
        self.init(
            tool_key=self.TOOL_KEY,
            class_name="CreateProjectPlugin",
            load_system_prefs=False,
            build_ui=False,
        )

    def execute(self):
        """Mantem compatibilidade com chamadas legadas."""
        return self.execute_tool()

    def execute_tool(self):
        """Executa o fluxo completo de criacao de projeto."""
        self.logger.info("Iniciando fluxo de criacao de novo projeto")
        # Carrega system prefs FRESCAS do disco para evitar estado obsoleto
        self._system_prefs = Preferences.load_tool_prefs(ToolKey.SYSTEM)
        self.logger.debug(f"[execute_tool] system_prefs carregadas: {self._system_prefs}")
        self._default_crs_authid = (
            self._system_prefs.get(self.DEFAULT_CRS_PREF_KEY) or self.DEFAULT_CRS_AUTHID
        )
        self.logger.debug(f"[execute_tool] default_crs_authid: {self._default_crs_authid}")
        self._base_folder = ""
        self._project_name = ""
        self._resolve_base_folder()

    def _resolve_base_folder(self):
        """Resolve a pasta base — se ja configurada, segue; senao, abre dialogo."""
        base_folder = (
            self._system_prefs.get(self.PROJECTS_FOLDER_PREF_KEY) or ""
        ).strip()
        self.logger.debug(f"[_resolve_base_folder] base_folder da prefs: '{base_folder}'")
        if base_folder:
            if self._prepare_existing_base_folder(base_folder):
                self._base_folder = base_folder
                self.logger.debug(f"[_resolve_base_folder] base_folder definida: {self._base_folder}")
                self._resolve_project_name()
            else:
                # Pasta configurada mas inacessivel: pede reconfiguracao
                self.logger.warning(f"[_resolve_base_folder] Pasta configurada inacessivel: {base_folder}")
                self._prompt_and_persist_base_folder()
            return

        self.logger.debug("[_resolve_base_folder] Nenhuma pasta configurada — abrindo dialogo")
        self._prompt_and_persist_base_folder()

    def _prompt_and_persist_base_folder(self):
        """Abre dialogo modal para definir a pasta padrao."""
        self.logger.debug("[_prompt_and_persist_base_folder] Exibindo confirmacao para definir pasta padrao")
        should_define = QgisMessageUtil.confirm(
            self.iface,
            STR.PROJECTS_DEFAULT_FOLDER_MISSING,
            title=STR.PROJECTS_DEFAULT_FOLDER_MISSING_TITLE,
        )
        if not should_define:
            self.logger.info("Usuario cancelou definicao da pasta padrao")
            QgisMessageUtil.modal_warning(
                self.iface,
                message=STR.PROJECTS_DEFAULT_FOLDER_MISSING,
            )
            return

        folder_dialog = DefaultProjectsFolderDialog(parent=self.iface.mainWindow())
        if folder_dialog.exec():
            path = folder_dialog.get_folder_path()
            self.logger.debug(f"[_prompt_and_persist_base_folder] Pasta selecionada: '{path}'")
            self._on_folder_selected(path)
        else:
            self.logger.debug("[_prompt_and_persist_base_folder] Dialogo de pasta cancelado")

    def _on_folder_selected(self, base_folder: str):
        """Callback quando o dialogo de pasta e confirmado."""
        if not base_folder:
            self.logger.info("Usuario cancelou o dialogo da pasta padrao")
            return

        base_folder = base_folder.strip()
        self.logger.debug(f"[_on_folder_selected] Pasta confirmada: '{base_folder}'")
        self._system_prefs[self.PROJECTS_FOLDER_PREF_KEY] = base_folder
        Preferences.save_tool_prefs(ToolKey.SYSTEM, self._system_prefs)
        self.logger.info(f"Pasta padrao salva nas system prefs: {base_folder}")

        if not self._prepare_new_base_folder(base_folder):
            self.logger.error(f"[_on_folder_selected] Falha ao preparar pasta: {base_folder}")
            return

        self._base_folder = base_folder
        self._resolve_project_name()

    def _prepare_new_base_folder(self, base_folder: str) -> bool:
        self.logger.debug(f"[_prepare_new_base_folder] Verificando/criando pasta: {base_folder}")
        if ExplorerUtils.ensure_folder_exists(base_folder, self.TOOL_KEY):
            self.logger.debug(f"[_prepare_new_base_folder] Pasta OK: {base_folder}")
            return True

        self.logger.error(f"[_prepare_new_base_folder] Falha ao criar pasta: {base_folder}")
        QgisMessageUtil.modal_error(
            self.iface,
            f"{STR.PROJECT_DEFAULT_FOLDER_PREPARE_ERROR}\n{base_folder}",
        )
        return False

    def _prepare_existing_base_folder(self, base_folder: str) -> bool:
        self.logger.debug(f"[_prepare_existing_base_folder] Verificando pasta existente: {base_folder}")
        if ExplorerUtils.ensure_folder_exists(base_folder, self.TOOL_KEY):
            self.logger.debug(f"[_prepare_existing_base_folder] Pasta OK: {base_folder}")
            return True

        self.logger.error(f"[_prepare_existing_base_folder] Pasta inacessivel: {base_folder}")
        QgisMessageUtil.modal_error(
            self.iface,
            f"{STR.PROJECT_DEFAULT_FOLDER_ACCESS_ERROR}\n{base_folder}",
        )
        return False

    def _resolve_project_name(self):
        """Abre dialogo nao-modal para nome do projeto."""
        if not self._base_folder:
            self.logger.error("_base_folder vazio — impossivel criar projeto")
            QgisMessageUtil.modal_error(
                self.iface,
                f"{STR.PROJECT_DEFAULT_FOLDER_PREPARE_ERROR}\n{STR.PROJECTS_DEFAULT_FOLDER_MISSING}",
            )
            return

        suggested_name = ExplorerUtils.next_indexed_folder_name(
            base_folder=self._base_folder,
            prefix="NovoProjeto_",
            pattern=self.GENERIC_PROJECT_PATTERN,
        )
        self.logger.debug(f"[_resolve_project_name] suggested_name: '{suggested_name}', base_folder: '{self._base_folder}'")
        self._name_dialog = ProjectNameDialog(
            suggested_name=suggested_name,
            base_folder=self._base_folder,
            project_tool_key=self.TOOL_KEY,
            parent=self.iface.mainWindow(),
        )
        # Nao-modal: usa signal + show()
        self._name_dialog.project_accepted.connect(self._on_project_name_accepted)
        self._name_dialog.show()
        self.logger.debug("[_resolve_project_name] Dialogo de nome exibido (nao-modal)")

    def _on_project_name_accepted(self, project_name: str):
        """Callback quando o nome do projeto e confirmado no dialogo nao-modal."""
        self.logger.debug(f"[_on_project_name_accepted] project_name recebido: '{project_name}'")

        # BUGFIX: Se project_name vier vazio (usuario clicou sem digitar),
        # usa o suggested_name do dialogo como fallback
        resolved = project_name.strip() if project_name else ""
        if not resolved:
            resolved = self._name_dialog._suggested_name
            self.logger.debug(f"[_on_project_name_accepted] Usando suggested_name fallback: '{resolved}'")

        self._project_name = ExplorerUtils.sanitize_path_component(resolved)
        if not self._project_name:
            self._project_name = self._name_dialog._suggested_name
            self.logger.debug(f"[_on_project_name_accepted] sanitize retornou vazio, usando fallback: '{self._project_name}'")

        self.logger.info(f"Nome do projeto resolvido: '{self._project_name}'")

        if not self._project_name:
            self.logger.error("[_on_project_name_accepted] Nome do projeto vazio apos todas as tentativas — abortando")
            QgisMessageUtil.modal_error(
                self.iface,
                "Nome do projeto invalido. A criacao foi cancelada.",
            )
            return

        self.logger.debug(f"[_on_project_name_accepted] Chamando _create_project_structure com base='{self._base_folder}', nome='{self._project_name}'")
        self._create_project_structure(
            self._base_folder,
            self._project_name,
            self._default_crs_authid,
        )
        self._name_dialog.deleteLater()
        self._name_dialog = None

    def _detect_creation_scenario(self, current_project) -> int:
        if ProjectUtils.is_project_saved(current_project):
            return self.SCENARIO_SAVED_CURRENT_PROJECT
        if not ProjectUtils.is_project_empty(current_project):
            return self.SCENARIO_UNSAVED_WITH_CONTENT
        return self.SCENARIO_UNSAVED_EMPTY_PROJECT

    def _should_load_line_for_scenario(self, scenario: int) -> bool:
        return scenario in (
            self.SCENARIO_SAVED_CURRENT_PROJECT,
            self.SCENARIO_UNSAVED_EMPTY_PROJECT,
        )

    def _copy_and_load_line_reference_layer(
        self, project, project_vectors_folder: Path
    ):
        line_path = OtherFilesManager.vector_path(OtherFilesManager.LINE_VECTOR)
        if not os.path.exists(line_path):
            self.logger.warning(
                f"Arquivo de referencia nao encontrado para carga automatica: {line_path}"
            )
            return None, ""

        self.logger.debug(f"[_copy_and_load_line_reference_layer] Copiando line.gpkg de '{line_path}' para '{project_vectors_folder}'")
        copied_line_path = ExplorerUtils.copy_file_to_folder(
            source_file=line_path,
            destination_folder=str(project_vectors_folder),
            tool_key=self.TOOL_KEY,
            overwrite=True,
        )
        if not copied_line_path:
            self.logger.warning(
                f"Falha ao copiar line.gpkg para pasta do projeto: {project_vectors_folder}"
            )
            return None, ""

        self.logger.debug(f"[_copy_and_load_line_reference_layer] Copiado para: {copied_line_path}")
        normalized_target = ProjectUtils.normalize_layer_source(copied_line_path)
        for layer in ProjectUtils.project_layers(project).values():
            source_normalized = ProjectUtils.normalize_layer_source(layer.source())
            if source_normalized == normalized_target:
                self.logger.debug(
                    f"Camada de referencia ja carregada no projeto: {copied_line_path}"
                )
                if layer and hasattr(layer, "isValid") and layer.isValid():
                    return layer, copied_line_path
                return None, copied_line_path

        line_layer = VectorLayerSource.load_existing_vector_layer(
            copied_line_path, tool_key=self.TOOL_KEY
        )
        if not line_layer or not line_layer.isValid():
            self.logger.warning(
                f"Falha ao carregar camada de referencia line.gpkg copiada: {copied_line_path}"
            )
            return None, copied_line_path

        ProjectUtils.add_layer(line_layer, add_to_root=True, project=project)
        self.logger.info(
            f"Camada de referencia carregada a partir da copia: {copied_line_path}"
        )
        return line_layer, copied_line_path

    def _apply_project_crs(self, project, authid: str):
        crs = ProjectUtils.resolve_valid_crs(
            authid=authid,
            fallback_authid=self.DEFAULT_CRS_AUTHID,
            tool_key=self.TOOL_KEY,
        )
        ProjectUtils.set_project_crs(project, crs)
        self.logger.info(f"SRC aplicado ao projeto: {crs.authid()}")

    def _create_project_structure(
        self, base_folder: str, project_name: str, default_crs_authid: str
    ):
        project_folder = Path(base_folder) / project_name
        project_file = project_folder / f"{project_name}.qgz"
        vectors_folder = project_folder / "vectors"
        rasters_folder = project_folder / "rasters"
        current_project = ProjectUtils.get_project_instance()
        current_project_path = ProjectUtils.get_project_file_name(current_project)
        scenario = self._detect_creation_scenario(current_project)
        should_load_line = self._should_load_line_for_scenario(scenario)

        self.logger.debug(f"[_create_project_structure] project_folder: {project_folder}")
        self.logger.debug(f"[_create_project_structure] project_file: {project_file}")
        self.logger.debug(f"[_create_project_structure] current_project_path: '{current_project_path}'")
        self.logger.debug(f"[_create_project_structure] scenario: {scenario}")
        self.logger.debug(f"[_create_project_structure] should_load_line: {should_load_line}")

        if project_folder.exists():
            self.logger.warning(f"Pasta de projeto ja existe: {project_folder}")
            should_continue = QgisMessageUtil.confirm(
                self.iface,
                f"{STR.PROJECT_FOLDER_ALREADY_EXISTS}\n{project_folder}\n\n{STR.CONTINUE_ANYWAY}",
                title=STR.PROJECT_FOLDER_ALREADY_EXISTS,
            )
            if not should_continue:
                self.logger.info("Usuario cancelou criacao do projeto existente")
                return

        try:
            if not ExplorerUtils.ensure_folder_exists(
                str(vectors_folder), self.TOOL_KEY
            ):
                raise RuntimeError("Falha ao criar pasta vectors")
            if not ExplorerUtils.ensure_folder_exists(
                str(rasters_folder), self.TOOL_KEY
            ):
                raise RuntimeError("Falha ao criar pasta rasters")
        except Exception as e:
            self.logger.error(
                f"Erro ao criar estrutura de pastas para '{project_folder}': {e}"
            )
            QgisMessageUtil.modal_error(
                self.iface,
                f"{STR.PROJECT_FOLDER_CREATE_ERROR}\n{project_folder}\n\n{e}",
            )
            return

        try:
            if not current_project_path:
                self.logger.debug("[_create_project_structure] Projeto atual sem arquivo — salvando no lugar")
                self._apply_project_crs(current_project, default_crs_authid)
                RasterLayerSource().add_google_basemap(
                    current_project,
                    basemap_style=self.DEFAULT_GOOGLE_BASEMAP_STYLE,
                    external_tool_key=self.TOOL_KEY,
                )
                line_layer = None
                line_path_in_project = ""
                if should_load_line:
                    line_layer, line_path_in_project = (
                        self._copy_and_load_line_reference_layer(
                            current_project, vectors_folder
                        )
                    )
                    if line_layer:
                        ProjectUtils.center_canvas_on_file_extent(
                            iface=self.iface,
                            file_path=line_path_in_project,
                            project=current_project,
                            layer_name=line_layer.name(),
                            tool_key=self.TOOL_KEY,
                        )
                ProjectUtils.set_project_home_path(current_project, str(project_folder))
                ProjectUtils.set_project_file_name(current_project, str(project_file))

                self.logger.debug(f"[_create_project_structure] Escrevendo projeto atual em: {project_file}")
                if not ProjectUtils.write_project(current_project, str(project_file)):
                    raise RuntimeError(
                        STR.CURRENT_PROJECT_SAVE_TO_NEW_DESTINATION_ERROR
                    )

                self.logger.info(f"Projeto atual sem arquivo salvo em: {project_file}")
            else:
                self.logger.debug("[_create_project_structure] Projeto ja salvo — criando nova instancia e abrindo nova janela")
                new_project = ProjectUtils.create_project_instance()
                self._apply_project_crs(new_project, default_crs_authid)
                RasterLayerSource().add_google_basemap(
                    new_project,
                    basemap_style=self.DEFAULT_GOOGLE_BASEMAP_STYLE,
                    external_tool_key=self.TOOL_KEY,
                )
                line_layer = None
                if should_load_line:
                    line_layer, _ = self._copy_and_load_line_reference_layer(
                        new_project, vectors_folder
                    )
                ProjectUtils.set_project_home_path(new_project, str(project_folder))
                ProjectUtils.set_project_file_name(new_project, str(project_file))

                self.logger.debug(f"[_create_project_structure] Escrevendo novo projeto em: {project_file}")
                if not ProjectUtils.write_project(new_project, str(project_file)):
                    raise RuntimeError(STR.NEW_PROJECT_FILE_WRITE_ERROR)

                line_extent = None
                if line_layer and line_layer.isValid():
                    layer_extent = line_layer.extent()
                    if not layer_extent.isEmpty():
                        line_extent = (
                            layer_extent.xMinimum(),
                            layer_extent.yMinimum(),
                            layer_extent.xMaximum(),
                            layer_extent.yMaximum(),
                        )

                self.logger.debug(f"[_create_project_structure] Abrindo nova janela QGIS com: {project_file}")
                if not ProjectUtils.open_project_in_new_window(
                    str(project_file), line_extent
                ):
                    raise RuntimeError(STR.OPEN_NEW_QGIS_WINDOW_ERROR)
        except Exception as e:
            self.logger.error(f"Erro ao criar projeto QGIS '{project_file}': {e}")
            QgisMessageUtil.modal_error(
                self.iface,
                f"{STR.PROJECT_FILE_CREATE_ERROR}\n{project_file}\n\n{e}",
            )
            return

        # Finalizacao com sucesso: incrementa uso e persiste prefs
        self.on_finish_plugin()
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)

        self.logger.info(f"Projeto criado com sucesso em: {project_folder}")
        QgisMessageUtil.modal_result_with_folder(
            self.iface,
            title=STR.PROJECT_CREATED_TITLE,
            message=(
                STR.PROJECT_CREATED_SUCCESS.format(project_name=project_name)
                if not current_project_path
                else STR.PROJECT_CREATED_OPENED_NEW_WINDOW.format(
                    project_name=project_name
                )
            ),
            folder_path=str(project_folder),
            parent=self.iface.mainWindow(),
        )


def run(iface):
    """Ponto de entrada do plugin instantaneo de criacao de projeto."""
    plugin = CreateProjectPlugin(iface)
    plugin.execute_tool()
    return plugin