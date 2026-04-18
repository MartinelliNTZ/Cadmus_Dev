# -*- coding: utf-8 -*-
import sys
import traceback
from ..model.Tool import Tool
from ...resources.IconManager import IconManager as im
from .LogUtils import LogUtils
from ...utils.ToolKeys import ToolKey
from ...utils.QgisMessageUtil import QgisMessageUtil
from ...i18n.TranslationManager import STR
from ...utils.StringManager import StringManager
from ...utils.Preferences import Preferences
from ..enum import ToolTypeEnum


class ToolRegistry:
    # Tipos de ferramenta (não usar enum separado conforme requisito)
    SYSTEM, LAYOUTS, FOLDER, VECTOR, AGRICULTURE, RASTER = (
        StringManager.MENU_CATEGORIES.keys()
    )

    def __init__(self, iface):
        self.iface = iface
        self.logger = LogUtils(tool=ToolKey.SYSTEM, class_name="ToolRegistry")
        self._main_action_prefs = {}  # Inicializar primeiro (vazio, será carregado depois)
        self.tools = self._create_tool_list()
        self._save_tool_metadata()
        self._main_action_prefs = self._load_and_validate_main_actions()
        # Recarregar tools com main_actions validadas
        self.tools = self._create_tool_list()

    def _save_tool_metadata(self):
        """
        Salva category e tool_type nas preferências de cada ferramenta.
        Isso permite que Preferences filtre por categoria posteriormente.
        """
        for tool in self.tools:
            try:
                prefs = Preferences.load_tool_prefs(tool.tool_key)
                prefs["category"] = tool.category
                prefs["tool_type"] = tool.tool_type
                Preferences.save_tool_prefs(tool.tool_key, prefs)
            except Exception as e:
                self.logger.error(
                    f"Erro ao salvar metadata do tool '{tool.tool_key}': {e}"
                )

    def _load_and_validate_main_actions(self):
        """
        Carrega as preferências de main_action de todas as ferramentas,
        valida que exista apenas uma com True POR CATEGORIA, e retorna dict {tool_key: bool}.
        
        Regras por categoria:
        - Se 2+ têm True, mantém apenas a primeira e reseta o resto
        - Se nenhuma tem True, retorna False para todas (padrões em _create_tool_list usam True)
        - Se exatamente 1 é True, retorna normalmente
        """
        main_action_prefs = Preferences.load_pref_key_by_tool("main_action")
        categories = StringManager.MENU_CATEGORIES.keys()
        
        self.logger.info(
            f"[_load_and_validate_main_actions] Iniciando validação. "
            f"Total de ferramentas carregadas: {len(main_action_prefs)}"
        )
        self.logger.debug(f"[_load_and_validate_main_actions] Prefs carregadas: {main_action_prefs}")
        
        # Validar por CATEGORIA
        for category in categories:
            self.logger.debug(f"[_load_and_validate_main_actions] Validando categoria '{category}'")
            
            # Filtrar apenas ferramentas desta categoria
            tools_in_category = {}
            for k, v in main_action_prefs.items():
                tool_cat = Preferences.load_tool_prefs(k).get("category")
                self.logger.debug(
                    f"[_load_and_validate_main_actions] Tool '{k}': "
                    f"category={tool_cat}, main_action={v}"
                )
                if tool_cat == category:
                    tools_in_category[k] = v
            
            self.logger.debug(
                f"[_load_and_validate_main_actions] Categoria '{category}': "
                f"{len(tools_in_category)} ferramentas. "
                f"Tools: {tools_in_category}"
            )
            
            true_count = sum(1 for v in tools_in_category.values() if v is True)
            self.logger.debug(
                f"[_load_and_validate_main_actions] Categoria '{category}': "
                f"{true_count} com main_action=True"
            )
            
            if true_count > 1:
                # Caso 2+: pega a primeira ocorrência e reseta o resto
                self.logger.warning(
                    f"[_load_and_validate_main_actions] Categoria '{category}': "
                    f"{true_count} ferramentas com main_action=True. "
                    f"Mantendo apenas a primeira."
                )
                first_key = next(k for k, v in tools_in_category.items() if v is True)
                for k in tools_in_category:
                    main_action_prefs[k] = (k == first_key)
                    self.logger.debug(
                        f"[_load_and_validate_main_actions] Corrigido '{k}': "
                        f"main_action={(k == first_key)}"
                    )
            elif true_count == 0:
                # Caso 0: nenhuma true nesta categoria - deixar como está
                self.logger.debug(
                    f"[_load_and_validate_main_actions] Categoria '{category}': "
                    f"nenhuma com main_action=True. Usando padrão."
                )
        
        # Salvar correções se necessário
        self.logger.info(
            f"[_load_and_validate_main_actions] Salvando preferências validadas"
        )
        for tool_key, is_main in main_action_prefs.items():
            prefs = Preferences.load_tool_prefs(tool_key)
            prefs["main_action"] = is_main
            Preferences.save_tool_prefs(tool_key, prefs)
            self.logger.debug(
                f"[_load_and_validate_main_actions] Salvo '{tool_key}': "
                f"main_action={is_main}"
            )
        
        self.logger.info(
            f"[_load_and_validate_main_actions] ✓ Validação concluída. "
            f"Result: {main_action_prefs}"
        )
        return main_action_prefs

    def _create_tool_list(self):
        tools = []

        # =====================================================
        # LAYOUTS (Ordem: Export=10, Replace=20)
        # =====================================================

        export_layouts = Tool(
            tool_key=ToolKey.EXPORT_ALL_LAYOUTS,
            name=STR.EXPORT_ALL_LAYOUTS_TITLE,
            icon=im.icon(im.EXPORT_ALL_LAYOUTS),
            category=self.LAYOUTS,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.EXPORT_ALL_LAYOUTS, True),
            executor=self.run_export_layouts,
            tooltip=STR.EXPORT_ALL_LAYOUTS_TOOLTIP,
            order=10,
            show_in_toolbar=True,
        )
        tools.append(export_layouts)

        replace_layouts = Tool(
            tool_key=ToolKey.REPLACE_IN_LAYOUTS,
            name=STR.REPLACE_IN_LAYOUTS_TITLE,
            icon=im.icon(im.REPLACE_IN_LAYOUTS),
            category=self.LAYOUTS,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.REPLACE_IN_LAYOUTS, False),
            executor=self.run_replace_layouts,
            tooltip=STR.REPLACE_IN_LAYOUTS_TOOLTIP,
            order=20,
            show_in_toolbar=True,
        )
        tools.append(replace_layouts)

        # =====================================================
        # SYSTEM (Ordem: Restart=10, Logcat=20, Settings=30, About=40)
        # =====================================================

        restart_qgis = Tool(
            tool_key=ToolKey.RESTART_QGIS,
            name=STR.RESTART_QGIS_TITLE,
            icon=im.icon(im.RESTART_QGIS),
            category=self.SYSTEM,
            tool_type=ToolTypeEnum.INSTANT,
            main_action=self._main_action_prefs.get(ToolKey.RESTART_QGIS, False),
            executor=self.run_restart_qgis,
            tooltip=STR.RESTART_QGIS_TOOLTIP,
            order=10,
            show_in_toolbar=True,
        )
        tools.append(restart_qgis)

        logcat = Tool(
            tool_key=ToolKey.LOGCAT,
            name=STR.LOGCAT_TITLE,
            icon=im.icon(im.LOGCAT),
            category=self.SYSTEM,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.LOGCAT, False),
            executor=self.run_logcat,
            tooltip=STR.LOGCAT_TOOLTIP,
            order=20,
            show_in_toolbar=True,
        )
        tools.append(logcat)

        settings = Tool(
            tool_key=ToolKey.SETTINGS,
            name=STR.SETTINGS_TITLE,
            icon=im.icon(im.SETTINGS),
            category=self.SYSTEM,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.SETTINGS, True),
            executor=self.run_settings,
            tooltip=STR.SETTINGS_TOOLTIP,
            order=30,
            show_in_toolbar=True,
        )
        tools.append(settings)

        about = Tool(
            tool_key=ToolKey.ABOUT_DIALOG,
            name=STR.ABOUT_CADMUS,
            icon=im.icon(im.ABOUT),
            category=self.SYSTEM,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.ABOUT_DIALOG, False),
            executor=self.run_about_dialog,
            tooltip=STR.ABOUT_DIALOG_TOOLTIP,
            order=40,
            show_in_toolbar=True,
        )
        tools.append(about)

        # =====================================================
        # FOLDER (Ordem: Load=10)
        # =====================================================

        load_folder = Tool(
            tool_key=ToolKey.LOAD_FOLDER_LAYERS,
            name=STR.LOAD_FOLDER_LAYERS_TITLE,
            icon=im.icon(im.LOAD_FOLDER_LAYER),
            category=self.FOLDER,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.LOAD_FOLDER_LAYERS, False),
            executor=self.run_load_folder,
            tooltip=STR.LOAD_FOLDER_LAYERS_TOOLTIP,
            order=10,
            show_in_toolbar=True,
        )
        tools.append(load_folder)

        create_project = Tool(
            tool_key=ToolKey.CREATE_PROJECT,
            name=STR.CREATE_PROJECT_TITLE,
            icon=im.icon(im.CREATE_PROJECT),
            category=self.FOLDER,
            tool_type=ToolTypeEnum.INSTANT,
            main_action=self._main_action_prefs.get(ToolKey.CREATE_PROJECT, True),
            executor=self.run_create_project,
            tooltip=STR.CREATE_PROJECT_TOOLTIP,
            order=15,
            show_in_toolbar=True,
        )
        tools.append(create_project)

        vector_to_svg = Tool(
            tool_key=ToolKey.VECTOR_TO_SVG,
            name=STR.VECTOR_TO_SVG_TITLE,
            icon=im.icon(im.VECTOR_TO_SVG),
            category=self.FOLDER,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.VECTOR_TO_SVG, False),
            executor=self.run_vector_to_svg,
            tooltip=STR.VECTOR_TO_SVG_TOOLTIP,
            order=20,
            show_in_toolbar=True,
        )
        tools.append(vector_to_svg)

        # =====================================================
        # VECTOR (Ordem: Fields=10, Coords=20, Pasta=30, Multipart=40, Copy=50)
        # =====================================================

        vector_fields = Tool(
            tool_key=ToolKey.VECTOR_FIELDS,
            name=STR.VECTOR_FIELDS_TITLE,
            icon=im.icon(im.VECTOR_FIELD),
            category=self.VECTOR,
            tool_type=ToolTypeEnum.INSTANT,
            main_action=self._main_action_prefs.get(ToolKey.VECTOR_FIELDS, True),
            executor=self.run_vector_fields,
            tooltip=STR.VECTOR_FIELDS_TOOLTIP,
            order=10,
            show_in_toolbar=True,
        )
        tools.append(vector_fields)

        remove_kml_fields = Tool(
            tool_key=ToolKey.REMOVE_KML_FIELDS,
            name=STR.REMOVE_KML_FIELDS_TITLE,
            icon=im.icon(im.CADMUS_ICON),
            category=self.VECTOR,
            tool_type=ToolTypeEnum.INSTANT,
            main_action=self._main_action_prefs.get(ToolKey.REMOVE_KML_FIELDS, False),
            executor=self.run_remove_kml_fields,
            tooltip=STR.REMOVE_KML_FIELDS_TOOLTIP,
            order=15,
            show_in_toolbar=True,
        )
        tools.append(remove_kml_fields)

        coord_click = Tool(
            tool_key=ToolKey.COORD_CLICK_TOOL,
            name=STR.COORD_CLICK_TOOL_TITLE,
            icon=im.icon(im.COORD_CLICK_TOOL),
            category=self.VECTOR,
            tool_type=ToolTypeEnum.MAP_TOOL,
            main_action=self._main_action_prefs.get(ToolKey.COORD_CLICK_TOOL, False),
            executor=self.run_coord_click,
            tooltip=STR.COORD_CLICK_TOOL_TOOLTIP,
            order=20,
            show_in_toolbar=True,
        )
        tools.append(coord_click)

        multipart = Tool(
            tool_key=ToolKey.CONVERTER_MULTIPART,
            name=STR.CONVERTER_MULTIPART_TITLE,
            icon=im.icon(im.VECTOR_MULTPART),
            category=self.VECTOR,
            tool_type=ToolTypeEnum.INSTANT,
            main_action=self._main_action_prefs.get(ToolKey.CONVERTER_MULTIPART, False),
            executor=self.run_multpart,
            tooltip=STR.CONVERTER_MULTIPART_TOOLTIP,
            order=40,
            show_in_toolbar=True,
        )
        tools.append(multipart)

        copy_attributes = Tool(
            tool_key=ToolKey.COPY_ATTRIBUTES,
            name=STR.COPY_ATTRIBUTES_TITLE,
            icon=im.icon(im.COPY_ATTRIBUTES),
            category=self.VECTOR,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.COPY_ATTRIBUTES, False),
            executor=self.run_copy_atributes,
            tooltip=STR.COPY_ATTRIBUTES_TOOLTIP,
            order=50,
            show_in_toolbar=True,
        )
        tools.append(copy_attributes)

        divide_points_by_strips = Tool(
            tool_key=ToolKey.DIVIDE_POINTS_BY_STRIPS,
            name=STR.DIVIDE_POINTS_BY_STRIPS_TITLE,
            icon=im.icon(im.DIVIDE_POINTS_BY_STRIPS),
            category=self.VECTOR,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.DIVIDE_POINTS_BY_STRIPS, False),
            executor=self.run_divide_points_by_strips,
            tooltip=STR.DIVIDE_POINTS_BY_STRIPS_TOOLTIP,
            order=60,
            show_in_toolbar=True,
        )
        tools.append(divide_points_by_strips)

        # =====================================================
        # AGRICULTURE (Ordem: Drone=10, Trail=20, Report=30)
        # =====================================================

        drone_coords = Tool(
            tool_key=ToolKey.DRONE_COORDINATES,
            name=STR.DRONE_COORDINATES_TITLE,
            icon=im.icon(im.DRONE_COORDINATES),
            category=self.AGRICULTURE,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.DRONE_COORDINATES, True),
            executor=self.run_drone_coords,
            tooltip=STR.DRONE_COORDINATES_TOOLTIP,
            order=10,
            show_in_toolbar=True,
        )
        tools.append(drone_coords)

        gerar_rastro = Tool(
            tool_key=ToolKey.GENERATE_TRAIL,
            name=STR.GENERATE_TRAIL_TITLE,
            icon=im.icon(im.GENERATE_TRAIL),
            category=self.AGRICULTURE,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.GENERATE_TRAIL, False),
            executor=self.run_gerar_rastro,
            tooltip=STR.GENERATE_TRAIL_TOOLTIP,
            order=20,
            show_in_toolbar=True,
        )
        tools.append(gerar_rastro)

        photo_vectorization = Tool(
            tool_key=ToolKey.PHOTO_VECTORIZATION,
            name=STR.PHOTO_VECTORIZATION_TITLE,
            icon=im.icon(im.DRONE_COORDINATES),
            category=self.AGRICULTURE,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.PHOTO_VECTORIZATION, False),
            executor=self.run_photo_vectorization,
            tooltip=STR.PHOTO_VECTORIZATION_TOOLTIP,
            order=25,
            show_in_toolbar=True,
        )
        tools.append(photo_vectorization)

        report_metadata = Tool(
            tool_key=ToolKey.REPORT_METADATA,
            name=STR.REPORT_METADATA_TITLE,
            icon=im.icon(im.DRONE_COORDINATES),
            category=self.AGRICULTURE,
            tool_type=ToolTypeEnum.DIALOG,
            main_action=self._main_action_prefs.get(ToolKey.REPORT_METADATA, False),
            executor=self.run_report_metadata,
            tooltip=STR.REPORT_METADATA_TOOLTIP,
            order=30,
            show_in_toolbar=True,
        )
        tools.append(report_metadata)

        # =====================================================
        # RASTER (Ordem: Mass Clipper=10)
        # =====================================================

        raster_mass_clipper = Tool(
            tool_key=ToolKey.RASTER_MASS_CLIPPER,
            name=STR.RASTER_MASS_CLIPPER_TITLE,
            icon=im.icon(im.RASTER_MASS_CLIPPER),
            category=self.RASTER,
            tool_type=ToolTypeEnum.PROCESSING,
            main_action=self._main_action_prefs.get(ToolKey.RASTER_MASS_CLIPPER, True),
            executor=self.run_raster_mass_clipper,
            tooltip=STR.RASTER_MASS_CLIPPER_TOOLTIP,
            order=10,
            show_in_toolbar=True,
        )
        tools.append(raster_mass_clipper)

        raster_mass_sampler = Tool(
            tool_key=ToolKey.RASTER_MASS_SAMPLER,
            name=STR.RASTER_MASS_SAMPLER_TITLE,
            icon=im.icon(im.RASTER_MASS_SAMPLER),
            category=self.RASTER,
            tool_type=ToolTypeEnum.PROCESSING,
            main_action=self._main_action_prefs.get(ToolKey.RASTER_MASS_SAMPLER, False),
            executor=self.run_raster_mass_sampler,
            tooltip=STR.RASTER_MASS_SAMPLER_TOOLTIP,
            order=20,
            show_in_toolbar=True,
        )
        tools.append(raster_mass_sampler)

        return tools

    def get_tools(self):
        return list(self.tools)

    # =======FERRAMENTAS INSTANTANEAS DE SISTEMA=======
    # =================================================
    # EXECUTAR: Restart QGIS
    # =================================================
    def run_restart_qgis(self):
        try:
            from ...plugins.RestartQgis import run_restart_qgis

            self.logger.info("Iniciando plugin: Restart QGIS")
            run_restart_qgis(self.iface)
            self.logger.info("Plugin Restart QGIS executado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Restart QGIS: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Restart QGIS:\n{str(e)}"
            )

    # ========FERRAMENTAS INSTANTANEAS======
    # ======================================
    # EXECUTAR: Calcular Campos Vetoriais
    # ======================================
    def run_vector_fields(self):
        try:
            from ...plugins.VectorFieldsCalculationPlugin import (
                VectorFieldsCalculationPlugin,
            )

            self.logger.info("Iniciando plugin: Calcular Campos Vetoriais")
            # manter referência viva
            self.vector_field_plugin = VectorFieldsCalculationPlugin(self.iface)
            self.vector_field_plugin.run_vector_field()
            self.logger.info("Plugin Calcular Campos Vetoriais executado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Calcular Campos Vetoriais: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Calcular Campos Vetoriais:{str(e)}"
            )

    # =====================================================
    # EXECUTAR: Converter para Multipart
    # =====================================================
    def run_multpart(self):
        try:
            from ...plugins.VectorMultipartPlugin import VectorMultipartPlugin

            self.logger.info("Iniciando plugin: Converter para Multipart")
            # manter referência viva
            self.vector_multpart_plugin = VectorMultipartPlugin(self.iface)
            self.vector_multpart_plugin.run_multpart()
            self.logger.info("Plugin Converter para Multipart executado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Converter para Multipart: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Converter para Multipart: {str(e)}"
            )

    # =====================================================
    # EXECUTAR: Remover Campos KML
    # =====================================================
    def run_remove_kml_fields(self):
        try:
            from ...plugins.RemoveKmlFieldsPlugin import RemoveKmlFieldsPlugin

            self.logger.info("Iniciando plugin: Remover Campos KML")
            self.remove_kml_fields_plugin = RemoveKmlFieldsPlugin(self.iface)
            self.remove_kml_fields_plugin.run_remove_kml_fields()
            self.logger.info("Plugin Remover Campos KML executado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Remover Campos KML: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Remover Campos KML: {str(e)}"
            )

    # =====FERRAMENTAS INSTANTANEA COM JANELA DE RESULTADOS=

    # =====================================================
    # EXECUTAR: Obter Coordenadas ao Clicar no Mapa
    # =====================================================
    def run_coord_click(self):
        try:
            from ...plugins.CoordClickTool import CoordClickTool

            self.logger.info("Ativando ferramenta: Capturar Coordenadas")
            self.coord_click_tool = CoordClickTool(self.iface)
            self.iface.mapCanvas().setMapTool(self.coord_click_tool)
            self.logger.info("Ferramenta Capturar Coordenadas ativada com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao ativar Capturar Coordenadas: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro na ferramenta Capturar Coordenadas:{str(e)}"
            )

    # ===FERRAMENTAS DE JANELA COM SAIDA QGIS===============
    # =====================================================
    # EXECUTAR: Export All Layouts
    # =====================================================
    def run_export_layouts(self):
        try:
            from ...plugins.ExportAllLayouts import run

            self.logger.info("Abrindo diálogo: Exportar todos os Layouts")
            self.export_dlg = run(self.iface)
            self.logger.info("Diálogo Exportar Layouts fechado")
        except Exception as e:
            self.logger.error(f"Erro ao executar Exportar Layouts: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Exportar Layouts: {str(e)}"
            )

    # =====================================================
    # EXECUTAR: Gerar Rastro Implemento (painel)
    # =====================================================
    def run_gerar_rastro(self):
        try:
            from ...plugins.GenerateTrailPlugin import run

            self.logger.info("Abrindo diálogo: Gerar Rastro Implemento")
            self.gerar_rastro_dlg = run(self.iface)
            self.logger.info("Diálogo Gerar Rastro Implemento aberto com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Gerar Rastro Implemento: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Gerar Rastro Implemento: {str(e)}"
            )

    # =====================================================
    # EXECUTAR: Logcat Tool
    # =====================================================
    def run_logcat(self):
        """
        Abre o Logcat com proteção MÁXIMA contra crashes.
        Qualquer erro será capturado e registrado em arquivo de log.
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("LOGCAT: Iniciando abertura de diálogo")

            # Import isolado
            try:
                from ...plugins.logcat.logcat_plugin import run

                self.logger.info("LOGCAT: Módulo logcat_plugin importado")
            except ImportError as import_err:
                error_msg = f"Erro ao importar logcat_plugin: {str(import_err)}"
                self.logger.critical(error_msg)
                QgisMessageUtil.bar_critical(
                    self.iface, f"Erro de importação:\n{str(import_err)}"
                )
                return

            self.logger.info("Abrindo diálogo: Logcat - Viewer de Logs")

            # Execução com proteção adicional
            try:
                self.logcat_dlg = run(self.iface)
                self.logger.info(
                    "LOGCAT: Diálogo aberto com sucesso (sem crashes detectados)"
                )
                self.logger.info("=" * 60)
            except Exception as run_error:
                # Erro na execução do Logcat
                error_msg = (
                    f"LOGCAT: Erro ao executar logcat_plugin.run(): {str(run_error)}"
                )
                self.logger.critical(error_msg)
                error_trace = traceback.format_exc()
                self.logger.critical(f"Stack trace:\n{error_trace}")
                QgisMessageUtil.bar_critical(
                    self.iface, f"Erro ao abrir Logcat:\n{str(run_error)}"
                )
                self.logger.info("=" * 60)

        except Exception as outer_error:
            # Erro na própria função run_logcat
            error_msg = f"LOGCAT: Erro CRÍTICO em run_logcat(): {str(outer_error)}"
            try:
                self.logger.critical(error_msg)
                error_trace = traceback.format_exc()
                self.logger.critical(f"Stack trace:\n{error_trace}")
                self.logger.info("=" * 60)
            except Exception as e:
                print(error_msg, file=sys.stderr)
                QgisMessageUtil.bar_critical(
                    self.iface,
                    f"Erro crítico no Logcat:\n{str(outer_error)}. Error: {e}",
                )

    # =====================================================
    # EXECUTAR: Obter Coordenadas de Drone
    # =====================================================
    def run_drone_coords(self):
        try:
            from ...plugins.DroneCoordinates import run

            self.logger.info("Abrindo diálogo: Obter Coordenadas de Drone")
            self.drone_cordinates_dlg = run(self.iface)
            self.logger.info("Diálogo Obter Coordenadas de Drone aberto com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Obter Coordenadas de Drone: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Obter Coordenadas de Drone:\n{str(e)}"
            )

    # =====================================================
    # EXECUTAR: Vetorizacao de Fotos
    # =====================================================
    def run_photo_vectorization(self):
        try:
            from ...plugins.PhotoVectorizationPlugin import run

            self.logger.info("Abrindo diálogo: Vetorização de Fotos")
            self.photo_vectorization_dlg = run(self.iface)
            self.logger.info("Diálogo Vetorização de Fotos aberto com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Vetorização de Fotos: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Vetorização de Fotos:\n{str(e)}"
            )

    def run_report_metadata(self):
        try:
            from ...plugins.ReportMetadataPlugin import run

            self.logger.info("Abrindo dialogo: Relatorio de Metadata")
            self.report_metadata_dlg = run(self.iface)
            self.logger.info("Dialogo Relatorio de Metadata aberto com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Relatorio de Metadata: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Relatorio de Metadata:\n{str(e)}"
            )

    # ====FERRAMENTAS DE JANELA SEM SAIDAS=================
    # =====================================================
    # EXECUTAR: Replace Text in Layouts
    # =====================================================
    def run_replace_layouts(self):
        try:
            from ...plugins.ReplaceInLayouts import run

            self.logger.info("Abrindo diálogo: Substituir textos nos Layouts")
            self.replace_layouts_dlg = run(self.iface)
            self.logger.info("Diálogo Substituir Layouts aberto com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Substituir Layouts: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Substituir Layouts:\n{str(e)}"
            )

    # =====================================================
    # EXECUTAR: Load Folder Layers
    # =====================================================
    def run_load_folder(self):
        try:
            from ...plugins.LoadFolderLayers import run

            self.logger.info("Iniciando plugin: Carregar pasta de arquivos")
            self.load_folder_dlg = run(self.iface)
            self.logger.info("Plugin Carregar pasta de arquivos executado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Carregar pasta de arquivos: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Carregar pasta:\n{str(e)}"
            )

    # =====================================================
    # EXECUTAR: Novo Projeto
    # =====================================================
    def run_create_project(self):
        try:
            from ...plugins.CreateProjectPlugin import run

            self.logger.info("Iniciando plugin: Novo Projeto")
            self.create_project_plugin = run(self.iface)
            self.logger.info("Plugin Novo Projeto executado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Novo Projeto: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Novo Projeto:\n{str(e)}"
            )

    # =====================================================
    # EXECUTAR: Vector To SVG
    # =====================================================
    def run_vector_to_svg(self):
        try:
            from ...plugins.VectorToSvgPlugin import run

            self.logger.info("Abrindo diálogo: VectorToSvgPlugin")
            self.vector_to_svg_dlg = run(self.iface)
            self.logger.info("Diálogo VectorToSvgPlugin aberto com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar VectorToSvgPlugin: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin VectorToSvgPlugin:\n{str(e)}"
            )

    # =====================================================
    # EXECUTAR: Raster Mass Clipper (Processing)
    # =====================================================
    def run_raster_mass_clipper(self):
        try:
            import processing

            algorithm_id = "cadmus:raster_mass_clipper"
            self.logger.info(
                f"Abrindo dialogo do Processing para algoritmo: {algorithm_id}"
            )
            processing.execAlgorithmDialog(algorithm_id, {})
            self.logger.info(
                "Dialogo do Raster Mass Clipper aberto com sucesso pelo provider"
            )
        except Exception as e:
            self.logger.error(f"Erro ao executar Raster Mass Clipper: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface,
                f"Erro ao abrir Raster Mass Clipper no Processing:\n{str(e)}",
            )

    # =====================================================
    # EXECUTAR: Raster Mass Sampler (Processing)
    # =====================================================
    def run_raster_mass_sampler(self):
        try:
            import processing

            algorithm_id = "cadmus:raster_mass_sampler"
            self.logger.info(
                f"Abrindo dialogo do Processing para algoritmo: {algorithm_id}"
            )
            processing.execAlgorithmDialog(algorithm_id, {})
            self.logger.info(
                "Dialogo do Raster Mass Sampler aberto com sucesso pelo provider"
            )
        except Exception as e:
            self.logger.error(f"Erro ao executar Raster Mass Sampler: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface,
                f"Erro ao abrir Raster Mass Sampler no Processing:\n{str(e)}",
            )

    # =====================================================
    # EXECUTAR: About Dialog
    # =====================================================
    def run_about_dialog(self):
        try:
            from ...plugins.AboutDialog import run

            self.logger.info("Abrindo diálogo: Sobre o Cadmus")
            self.about_dlg = run(self.iface)
            self.logger.info("Diálogo Sobre Cadmus fechado")
        except Exception as e:
            self.logger.error(f"Erro ao executar Sobre o Cadmus: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro ao abrir Sobre Cadmus:\n{str(e)}"
            )

    # =====================================================
    # EXECUTAR: Copiar Atributos entre Camadas
    # =====================================================
    def run_copy_atributes(self):
        try:
            from ...plugins.CopyAttributesPlugin import run

            self.logger.info("Abrindo diálogo: Copiar Atributos")
            self.copy_attributes_dlg = run(self.iface)
            self.logger.info("Diálogo Copiar Atributos aberto com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Copiar Atributos: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Copiar Atributos:\n{str(e)}"
            )

    # =====================================================
    # EXECUTAR: Configurações
    # =====================================================
    def run_divide_points_by_strips(self):
        try:
            from ...plugins.DividePointsByStripsPlugin import run

            self.logger.info("Abrindo dialogo: Dividir Vetor de Pontos por Faixas")
            self.divide_points_by_strips_dlg = run(self.iface)
            self.logger.info(
                "Dialogo Dividir Vetor de Pontos por Faixas aberto com sucesso"
            )
        except Exception as e:
            self.logger.error(
                f"Erro ao executar Dividir Vetor de Pontos por Faixas: {str(e)}"
            )
            QgisMessageUtil.bar_critical(
                self.iface,
                f"Erro no plugin Dividir Vetor de Pontos por Faixas:\n{str(e)}",
            )

    def run_settings(self):
        try:
            from ...plugins.SettingsPlugin import run

            self.logger.info("Abrindo diálogo: Configurações")
            self.settings_dlg = run(self.iface)
            self.logger.info("Diálogo de configurações aberto com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Configurações: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no diálogo de Configurações:\n{str(e)}"
            )
