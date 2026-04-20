# -*- coding: utf-8 -*-
import sys
import traceback
from qgis.core import QgsApplication
from qgis.PyQt.QtWidgets import QAction, QMenu, QToolButton, QWidgetAction
from pathlib import Path
from .utils.ToolKeys import ToolKey
from .utils.QgisMessageUtil import QgisMessageUtil
from .core.config.LogUtils import LogUtils
from .resources.IconManager import IconManager as im
from .i18n.TranslationManager import TM, STR
from .core.config.PluginBootstrap import PluginBootstrap
from .resources.widgets.DropdownToolButton import DropdownToolButton

class CadmusPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.menu = None
        self.toolbar = None
        self.actions = []
        self.provider = None
        self.logger = None
        self.TOOL_KEY = ToolKey.SYSTEM

    # =====================================================
    # INICIAR GUI E PROCESSING
    # =====================================================
    def initGui(self):

        locale = QgsApplication.locale()  # ex: 'pt_BR'

        plugin_root = Path(__file__).resolve().parent

        # Inicializar componentes críticos via PluginBootstrap
        bootstrap = PluginBootstrap(self.iface)
        self.provider = bootstrap.bootstrap(plugin_root)

        # Criar logger para CadmusPlugin
        self.logger = LogUtils(tool=self.TOOL_KEY, class_name="Cadmus", level=LogUtils.DEBUG)

        self.logger.info("Plugin inicializado")
        self.logger.info(f"Locale: {locale}. TM.STR: {STR.APP_NAME}")
        # -------------------------
        # 2) CRIAR TOOLBAR EXCLUSIVA
        # -------------------------
        try:
            self.toolbar = self.iface.addToolBar("Cadmus")
            self.toolbar.setObjectName("Cadmus_Toolbar")
            self.logger.debug("Toolbar Cadmus criada com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao criar toolbar: {str(e)}")
            return

        # -------------------------
        # 3) MENU PRINCIPAL E SUBMENUS
        # -------------------------
        try:
            self.menu = QMenu("Cadmus", self.iface.mainWindow())
            self.menu.setObjectName("Cadmus")
            standard_menu = self.iface.firstRightStandardMenu()
            self.iface.mainWindow().menuBar().insertMenu(
                standard_menu.menuAction(), self.menu
            )
            self.menu.clear()
            self.logger.debug("Menu Cadmus criado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao criar menu principal: {str(e)}")
            return

        # Submenus
        try:
            self.agriculture_menu = QMenu("Agricultura de Precisão", self.menu)
            self.agriculture_menu.setIcon(im.icon(im.AGRICULTURE))

            self.layers_menu = QMenu("Camadas", self.menu)
            self.layers_menu.setIcon(im.icon(im.LAYER))

            self.layouts_menu = QMenu("Layouts", self.menu)
            self.layouts_menu.setIcon(im.icon(im.LAYOUT))

            self.raster_menu = QMenu("Raster", self.menu)
            self.raster_menu.setIcon(im.icon(im.RASTER))

            self.system_menu = QMenu("Sistema", self.menu)
            self.system_menu.setIcon(im.icon(im.SYSTEM))

            self.vectors_menu = QMenu("Vetores", self.menu)
            self.vectors_menu.setIcon(im.icon(im.VECTOR))

            # Adiciona submenus ao menu principal
            self.menu.addMenu(self.agriculture_menu)
            self.menu.addMenu(self.layers_menu)
            self.menu.addMenu(self.layouts_menu)
            self.menu.addMenu(self.raster_menu)
            self.menu.addMenu(self.vectors_menu)
            self.menu.addMenu(self.system_menu)
            self.logger.debug("Submenus criados com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao criar submenus: {str(e)}")
            return

        # -------------------------
        # 4) CONFIGURAÇÃO DAS AÇÕES (ORDEM NUMÉRICA)
        # -------------------------
        try:
            # 1-Export All Layouts
            self.action_export_all = QAction(
                im.icon(im.EXPORT_ALL_LAYOUTS),
                "Exportar todos os Layouts",
                self.iface.mainWindow(),
            )
            self.action_export_all.triggered.connect(self.run_export_layouts)
            self.action_export_all.setToolTip(
                "Exporta todos os Layouts do projeto para arquivos PDF ou imagens.\n"
            )

            # 2-Replace in Layouts
            self.action_replace_layouts = QAction(
                im.icon(im.REPLACE_IN_LAYOUTS),
                "Substituir textos nos Layouts",
                self.iface.mainWindow(),
            )
            self.action_replace_layouts.triggered.connect(self.run_replace_layouts)
            self.action_replace_layouts.setToolTip(
                "Substitui textos em massa nos Layouts do projeto.\n"
                "Permite criar um mapa de substituição a partir de uma camada vetorial ou tabela, onde um campo é usado para identificar os Layouts e outro campo é usado para o novo valor a ser inserido.\n"
                "Útil para atualizar informações como títulos, legendas ou rótulos em múltiplos Layouts de forma rápida e consistente."
            )

            # 3-Restart QGIS
            self.action_restart_qgis = QAction(
                im.icon(im.RESTART_QGIS),
                "Salvar, Fechar e Reabrir Projeto",
                self.iface.mainWindow(),
            )
            self.action_restart_qgis.triggered.connect(self.run_restart_qgis)
            self.action_restart_qgis.setToolTip(
                "Salva o projeto atual, fecha o QGIS e reabre o mesmo projeto automaticamente.\n"
                "Útil para resolver travamentos, bugs visuais ou de renderização sem perder o trabalho."
            )

            # 4-Carregar pasta de arquivos
            self.action_load_folder = QAction(
                im.icon(im.LOAD_FOLDER_LAYER),
                "Carregar pasta de arquivos",
                self.iface.mainWindow(),
            )
            self.action_load_folder.triggered.connect(self.run_load_folder)
            self.action_load_folder.setToolTip(
                "Carrega em massa uma pasta de arquivos como camadas no QGIS.\n"
            )

            # 5-Gerar Rastro Implemento
            self.action_gerar_rastro = QAction(
                im.icon(im.GENERATE_TRAIL),
                "Gerar Rastro Implemento",
                self.iface.mainWindow(),
            )
            self.action_gerar_rastro.triggered.connect(self.run_gerar_rastro)
            self.action_gerar_rastro.setToolTip(
                "Gera um rastro do movimento de um implemento agrícola com base em uma linha.\n"
            )

            # 6-About Dialog
            self.action_about_dialog = QAction(
                im.icon(im.ABOUT), "Sobre o Cadmus", self.iface.mainWindow()
            )
            self.action_about_dialog.triggered.connect(self.run_about_dialog)
            self.action_about_dialog.setToolTip("Informações sobre o plugin Cadmus.")

            # 12-Logcat Tool
            self.action_logcat = QAction(
                im.icon(im.LOGCAT), "Logcat - Viewer de Logs", self.iface.mainWindow()
            )
            self.action_logcat.triggered.connect(self.run_logcat)
            self.action_logcat.setToolTip(
                "Abre o Logcat, uma ferramenta de visualização dos logs do plugin Cadmus"
            )

            # 13-Settings
            self.action_settings = QAction(
                im.icon(im.SETTINGS), "Configurações", self.iface.mainWindow()
            )
            self.action_settings.triggered.connect(self.run_settings)
            self.action_settings.setToolTip("Configurações do plugin Cadmus.")

            # 7-Capturar Coordenadas
            self.action_coord_click = QAction(
                im.icon(im.COORD_CLICK_TOOL),
                "Capturar Coordenadas",
                self.iface.mainWindow(),
            )
            self.action_coord_click.triggered.connect(self.run_coord_click)
            self.action_coord_click.setToolTip(
                "Clique no mapa para obter coordenadas geográficas\n"
                "Ative a ferramenta e clique em qualquer ponto do mapa para\n"
                "visualizar diversas informações a respeito daquele ponto"
                "Incluindo, UTM Zone, Municipio, Altitude em SRTM 90m."
            )

            # 8-Calcular campos vetoriais
            self.action_vector_fields = QAction(
                im.icon(im.VECTOR_FIELD),
                "Calcular Campos Vetoriais",
                self.iface.mainWindow(),
            )
            self.action_vector_fields.triggered.connect(self.run_vector_fields)
            self.action_vector_fields.setToolTip(
                "Calcula automaticamente campos: Área, Comprimento ou X/Y\n"
                "Selecione uma camada vetorial ativa e execute a ferramenta\n"
                "para adicionar os campos calculados."
            )

            # 09-Obter coordenadas de drone
            self.action_drone_coords = QAction(
                im.icon(im.DRONE_COORDINATES),
                "Obter Coordenadas de Drone",
                self.iface.mainWindow(),
            )
            self.action_drone_coords.triggered.connect(self.run_drone_coords)
            self.action_drone_coords.setToolTip(
                "Gera uma camada de pontos com as coordenadas de cada foto.\n"
                "Gera um linha da trajetória do drone, conectando os pontos na ordem de captura.\n"
                "Pode cruzar os pontos das fotos com os metadados das fotos para adicionar atributos/n"
                "como altitude, data/hora, etc."
            )

            # 10-Realizar multipart de todas as feições
            self.action_multpart = QAction(
                im.icon(im.VECTOR_MULTPART),
                "Promover a multiparte",
                self.iface.mainWindow(),
            )
            self.action_multpart.triggered.connect(self.run_multpart)
            self.action_multpart.setToolTip(
                "Promove feições para o tipo multiparte\n"
                "Selecione uma camada vetorial ativa e execute a ferramenta\n"
                "para promover as feições."
            )

            # 11-Copiar atributos entre camadas
            self.action_copy_atributes = QAction(
                im.icon(im.COPY_ATTRIBUTES), "Copiar Atributos", self.iface.mainWindow()
            )
            self.action_copy_atributes.triggered.connect(self.run_copy_atributes)
            self.logger.debug("Todas as ações criadas com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao criar ações: {str(e)}")
            return

        # -------------------------
        # 5) ADICIONAR AÇÕES AO MENU (ORDEM ALFABÉTICA)
        # -------------------------
        try:
            # Agricultura de Precisão
            self.agriculture_menu.addAction(self.action_gerar_rastro)
            self.agriculture_menu.addAction(self.action_drone_coords)

            # Camadas
            self.layers_menu.addAction(self.action_load_folder)

            # Layouts
            self.layouts_menu.addAction(self.action_export_all)
            self.layouts_menu.addAction(self.action_replace_layouts)

            # Sistema
            self.system_menu.addAction(self.action_restart_qgis)
            self.system_menu.addAction(self.action_logcat)
            self.system_menu.addAction(self.action_settings)

            # Vetores
            self.vectors_menu.addAction(self.action_coord_click)
            self.vectors_menu.addAction(self.action_vector_fields)

            # Menu principal
            self.menu.addAction(self.action_about_dialog)

            self.logger.debug("Ações adicionadas aos menus com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao adicionar ações aos menus: {str(e)}")
            return

        # -------------------------
        # 6) TOOLBAR
        # -------------------------
        try:
            # ==================================================
            # BOTÃO SISTEMA NA TOOLBAR (com dropdown)
            # ==================================================
            button = DropdownToolButton(self.iface.mainWindow())
            button.setup(
                title="Sistema",
                main_action=self.action_restart_qgis,
                secondary_actions=[
                    self.action_restart_qgis,
                    self.action_logcat,
                    self.action_settings,
                    self.action_about_dialog,
                ],
            )
            widget_action = QWidgetAction(self.toolbar)
            widget_action.setDefaultWidget(button)
            self.toolbar.addAction(widget_action)

            # ==================================================
            # BOTÃO LAYOUTS NA TOOLBAR (com dropdown)
            # ==================================================
            button = DropdownToolButton(self.iface.mainWindow())
            button.setup(
                title="Layouts",
                main_action=self.action_export_all,
                secondary_actions=[
                    self.action_export_all,
                    self.action_replace_layouts,
                ],
            )
            widget_action = QWidgetAction(self.toolbar)
            widget_action.setDefaultWidget(button)
            self.toolbar.addAction(widget_action)

            # ==================================================
            # BOTÃO CAMADAS NA TOOLBAR (com dropdown)
            # ==================================================
            button = DropdownToolButton(self.iface.mainWindow())
            button.setup(
                title="Vetores",
                main_action=self.action_load_folder,
                secondary_actions=[self.action_load_folder],
            )
            widget_action = QWidgetAction(self.toolbar)
            widget_action.setDefaultWidget(button)
            self.toolbar.addAction(widget_action)
            # ==================================================
            # BOTÃO "VETORES" NA TOOLBAR (com dropdown)
            # ==================================================
            button = DropdownToolButton(self.iface.mainWindow())
            button.setup(
                title="Vetores",
                main_action=self.action_vector_fields,
                secondary_actions=[
                    self.action_vector_fields,
                    self.action_coord_click,
                    self.action_copy_atributes,
                    self.action_multpart,
                ],
            )
            widget_action = QWidgetAction(self.toolbar)
            widget_action.setDefaultWidget(button)
            self.toolbar.addAction(widget_action)
            # ==================================================
            # BOTÃO "AGRICULTURA DE PRECISÃO" NA TOOLBAR (com dropdown)
            # ==================================================
            button = DropdownToolButton(self.iface.mainWindow())
            button.setup(
                title="Agricultura de Precisão",
                main_action=self.action_drone_coords,
                secondary_actions=[self.action_drone_coords, self.action_gerar_rastro],
            )
            widget_action = QWidgetAction(self.toolbar)
            widget_action.setDefaultWidget(button)
            self.toolbar.addAction(widget_action)
            # ==================================================
            # BOTÃO "RASTER" NA TOOLBAR (com dropdown)
            # ==================================================

            self.toolbar.addSeparator()
            self.logger.debug("Botões de toolbar criados com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao criar botões da toolbar: {str(e)}")
            return

        # Salva todas as ações para cleanup
        try:
            self.actions.extend(
                [
                    self.action_export_all,
                    self.action_replace_layouts,
                    self.action_restart_qgis,
                    self.action_load_folder,
                    self.action_gerar_rastro,
                    self.action_about_dialog,
                    self.action_logcat,
                    self.action_settings,
                    self.action_coord_click,
                    self.action_vector_fields,
                    self.action_drone_coords,
                    self.action_multpart,
                    self.action_copy_atributes,
                ]
            )
            self.logger.info("Cadmus: GUI inicializada com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao salvar ações para cleanup: {str(e)}")

    # =====================================================
    # DESCARREGAR PLUGIN
    # =====================================================
    def unload(self):
        try:
            # Remover provider do Processing
            if self.provider:
                QgsApplication.processingRegistry().removeProvider(self.provider)
                self.logger.info("Processing Provider removido com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao remover Processing Provider: {str(e)}")

        try:
            # Remover ações do menu e toolbar
            for act in self.actions:
                self.iface.removePluginMenu("Cadmus", act)
                self.iface.removeToolBarIcon(act)
            self.logger.info("Ações removidas com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao remover ações: {str(e)}")

        try:
            # Remover toolbar
            if self.toolbar:
                del self.toolbar
                self.logger.info("Toolbar removida com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao remover toolbar: {str(e)}")

        self.logger.info("Plugin Cadmus descarregado")

    # =======FERRAMENTAS INSTANTANEAS DE SISTEMA=======
    # =================================================
    # EXECUTAR: Restart QGIS
    # =================================================
    def run_restart_qgis(self):
        try:
            from .plugins.RestartQgis import run_restart_qgis

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
            from .plugins.VectorFieldsCalculationPlugin import (
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
            from .plugins.VectorMultipartPlugin import VectorMultipartPlugin

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

    # =====FERRAMENTAS INSTANTANEA COM JANELA DE RESULTADOS=

    # =====================================================
    # EXECUTAR: Obter Coordenadas ao Clicar no Mapa
    # =====================================================
    def run_coord_click(self):
        try:
            from .plugins.coord_click_tool import CoordClickTool

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
            from .plugins.ExportAllLayouts import run_export_all_layouts

            self.logger.info("Abrindo diálogo: Exportar todos os Layouts")
            self.export_dlg = run_export_all_layouts(self.iface)
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
            from .plugins.GenerateTrailPlugin import run_gerar_rastro

            self.logger.info("Abrindo diálogo: Gerar Rastro Implemento")
            self.gerar_rastro_dlg = run_gerar_rastro(self.iface)
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
                from .plugins.logcat.logcat_plugin import run

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
            from .plugins.DroneCoordinates import run_drone_cordinates

            self.logger.info("Abrindo diálogo: Obter Coordenadas de Drone")
            self.drone_cordinates_dlg = run_drone_cordinates(self.iface)
            self.logger.info("Diálogo Obter Coordenadas de Drone aberto com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Obter Coordenadas de Drone: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Obter Coordenadas de Drone:\n{str(e)}"
            )

    # ====FERRAMENTAS DE JANELA SEM SAIDAS=================
    # =====================================================
    # EXECUTAR: Replace Text in Layouts
    # =====================================================
    def run_replace_layouts(self):
        try:
            from .plugins.ReplaceInLayouts import run_replace_in_layouts

            self.logger.info("Abrindo diálogo: Substituir textos nos Layouts")
            self.replace_layouts_dlg = run_replace_in_layouts(self.iface)
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
            from .plugins.LoadFolderLayers import run_load_folder_layers

            self.logger.info("Iniciando plugin: Carregar pasta de arquivos")
            self.load_folder_dlg = run_load_folder_layers(self.iface)
            self.logger.info("Plugin Carregar pasta de arquivos executado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Carregar pasta de arquivos: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Carregar pasta:\n{str(e)}"
            )

    # =====================================================
    # EXECUTAR: About Dialog
    # =====================================================
    def run_about_dialog(self):
        try:
            from .plugins.AboutDialog import run_about_dialog

            self.logger.info("Abrindo diálogo: Sobre o Cadmus")
            self.about_dlg = run_about_dialog(self.iface)
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
            from .plugins.CopyAttributesPlugin import run_copy_attributes

            self.logger.info("Abrindo diálogo: Copiar Atributos")
            self.copy_attributes_dlg = run_copy_attributes(self.iface)
            self.logger.info("Diálogo Copiar Atributos aberto com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Copiar Atributos: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin Copiar Atributos:\n{str(e)}"
            )

    # =====================================================
    # EXECUTAR: Configurações
    # =====================================================
    def run_settings(self):
        try:
            from .plugins.SettingsPlugin import run_settings

            self.logger.info("Abrindo diálogo: Configurações")
            self.settings_dlg = run_settings(self.iface)
            self.logger.info("Diálogo de configurações aberto com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar Configurações: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no diálogo de Configurações:\n{str(e)}"
            )
