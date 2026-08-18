# -*- coding: utf-8 -*-
from qgis.core import QgsCoordinateReferenceSystem

from ..utils.StringManager import StringManager
from ..plugins.BasePlugin import BasePluginMTL
from ..utils.Preferences import Preferences
from ..utils.ToolKeys import ToolKey
from ..utils.ExplorerUtils import ExplorerUtils
from ..i18n.TranslationManager import STR, TranslationManager
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..core.config.MenuManager import MenuManager
from ..resources.styles.ThemeManager import ThemeManager, theme_manager
from ..resources.widgets.CollapsibleParametersWidget import (
    CollapsibleParametersWidget,
)
from ..resources.widgets.ComplexCrsSelector import ComplexCrsSelector
from ..resources.widgets.grid.GridComboBox import GridComboBox
from ..resources.widgets.grid.GridDoubleSpin import GridDoubleSpin
from ..resources.widgets.grid.GridCheckbox import GridCheckbox
from ..resources.widgets.grid.GridRadioButton import GridRadioButton
from ..resources.widgets.grid.GridInputFields import GridInputFields
from ..resources.widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons


class SettingsPlugin(BasePluginMTL):
    """
    Plugin de configurações do Cadmus.

    Permite ao usuário:
    - Acessar preferências do aplicativo
    - Configurar método de cálculo vetorial (Elipsoidal, Cartesiana, Ambos)
    """

    CALCULATION_METHODS = [
        STR.ELLIPSOIDAL,
        STR.CARTESIAN,
        STR.BOTH,
    ]
    DEFAULT_CRS_AUTHID = "EPSG:4326"
    AUTO_SAVE_PREFS_ON_CLOSE = False
    system_preferences = {}
    prefer_VectorFields = {}

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.init(ToolKey.SETTINGS, "SettingsPlugin", load_system_prefs=True)
        self.logger.info("SettingsPlugin inicializado")

    def _build_ui(self, **kwargs):
        """Constrói a interface de configurações."""
        self.logger.debug("Construindo interface de configurações")

        super()._build_ui(
            title=STR.SETTINGS_TITLE,
            icon_path="settings.ico",
        )

        self.logger.info("Construindo componentes de interface")

        # ── Colapsável Geral ──────────────────────────────────────
        self.geral_collapsable = CollapsibleParametersWidget(
            title=STR.GENERAL,
            expanded_by_default=True,
            parent=self,
        )

        # ── Pasta de Projetos (GridComplexSelector - folder) ──────
        self.project_folder_selector = GridComplexSelector(
            config={
                "projects_folder": {
                    "label": STR.PROJECTS_FOLDER,
                    "description": STR.PROJECTS_FOLDER_DESC,
                    "mode_type": "input",
                    "allow_file": False,
                    "allow_folder": True,
                },
            },
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.geral_collapsable.add_content_widget(self.project_folder_selector)
        self.logger.debug("Seletor de pasta de projetos adicionado")

        # ── Seletor de EPSG (ComplexCrsSelector) ──────────────────
        self.crs_selector = ComplexCrsSelector(
            label_text=STR.DEFAULT_CRS,
            default_auth_id=self.system_preferences.get(
                "default_crs_authid", self.DEFAULT_CRS_AUTHID
            ),
            tooltip=STR.DEFAULT_CRS_DESC,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.geral_collapsable.add_content_widget(self.crs_selector)
        self.logger.debug("Widget de selecao de SRC adicionado")

        # ── Idioma + Tema (GridComboBox — 1 widget, N items) ──────
        langs = StringManager.AVAILABLE_LANGUAGES
        selected_lang = self.system_preferences.get("plugin_language", "none")
        theme_options = {
            key: meta.get("label", key)
            for key, meta in ThemeManager.available_themes().items()
        }
        self.lang_selector = GridComboBox(
            config={
                "language": {
                    "label": STR.PLUGIN_LANGUAGE,
                    "description": STR.PLUGIN_LANGUAGE_DESC,
                    "options": langs,
                    "selected_key": selected_lang,
                },
                "theme": {
                    "label": STR.THEME,
                    "description": STR.THEME_DESC,
                    "options": theme_options,
                    "allow_empty": True,
                    "selected_key": self.system_preferences.get("theme"),
                },
            },
            parent=self,
        )
        self.geral_collapsable.add_content_widget(self.lang_selector)
        self.logger.debug("Seletores de idioma e tema adicionados")

        # ── Precisão de campos vetoriais (GridDoubleSpin) ─────────
        self.spin_precision = GridDoubleSpin(
            config={
                "precision": {
                    "label": STR.VECTOR_FIELDS_PRECISION,
                    "description": STR.VECTOR_FIELDS_PRECISION_DESC,
                    "value": 2,
                    "min": 0,
                    "max": 10,
                    "step": 1,
                    "type": "int",
                },
            },
            parent=self,
        )
        self.geral_collapsable.add_content_widget(self.spin_precision)
        self.logger.debug("Widget de precisão de campos vetoriais adicionado")

        # ── Limiar assíncrono (GridDoubleSpin) ────────────────────
        self.spin_threshold = GridDoubleSpin(
            config={
                "threshold": {
                    "label": STR.ASYNC_THRESHOLD,
                    "description": STR.ASYNC_THRESHOLD_DESC,
                    "value": 1000,
                    "min": 1,
                    "max": 100000000,
                    "step": 1,
                    "type": "int",
                },
            },
            parent=self,
        )
        self.geral_collapsable.add_content_widget(self.spin_threshold)
        self.logger.debug("Widget de limiar assíncrono por feições adicionado")

        # ── Toolbar - Categorias visíveis (GridCheckbox - 3 colunas)
        self.toolbar_category_checks = GridCheckbox(
            config={
                key: {
                    "label": label,
                    "description": STR.TOOLBAR_VISIBLE_CATEGORIES_DESC,
                    "default": True,
                }
                for key, label in MenuManager.toolbar_category_options().items()
            },
            items_per_row=3,
            title=STR.TOOLBAR_VISIBLE_CATEGORIES,
            parent=self,
        )
        self.geral_collapsable.add_content_widget(self.toolbar_category_checks)
        self.logger.debug("Grid de categorias visiveis da toolbar adicionado")

        # ── Colapsável Cálculos Vetoriais ─────────────────────────
        self.calc_collapsable = CollapsibleParametersWidget(
            title=STR.VECTOR_CALCULATIONS_PLUGIN,
            expanded_by_default=False,
            parent=self,
        )

        # ── Método de Cálculo (GridRadioButton) ───────────────────
        self.radio_calc = GridRadioButton(
            config={
                STR.ELLIPSOIDAL: {
                    "label": STR.ELLIPSOIDAL,
                    "description": STR.ELLIPSOIDAL_DESC,
                },
                STR.CARTESIAN: {
                    "label": STR.CARTESIAN,
                    "description": STR.CARTESIAN_DESC,
                },
                STR.BOTH: {
                    "label": STR.BOTH,
                    "description": STR.BOTH_DESC,
                },
            },
            columns=3,
            default_key=STR.ELLIPSOIDAL,
            parent=self,
        )
        self.calc_collapsable.add_content_widget(self.radio_calc)
        self.logger.debug("Widget de cálculo vetorial adicionado")

        # ── Sufixos de área (GridInputFields) ─────────────────────
        self.area_fields_inputs = GridInputFields(
            config={
                "cartesian_suffix": {
                    "label": STR.CARTESIAN_SUFFIX,
                    "description": STR.CARTESIAN_SUFFIX_DESC,
                    "default": "",
                },
                "ellipsoidal_suffix": {
                    "label": STR.ELLIPSOIDAL_SUFFIX,
                    "description": STR.ELLIPSOIDAL_SUFFIX_DESC,
                    "default": "_eli",
                },
            },
            parent=self,
        )
        self.calc_collapsable.add_content_widget(self.area_fields_inputs)
        self.logger.debug("Widget de sufixos de área adicionado")

        # ── Botões de Ação (GridExecutionButtons) ─────────────────
        self.action_buttons = GridExecutionButtons(
            config={
                "save": {
                    "label": STR.SAVE,
                    "description": STR.SAVE_DESC,
                    "callback": self.execute_tool,
                    "is_run_button": True,
                },
                "open_prefs": {
                    "label": STR.OPEN_PREFERENCES_FOLDER,
                    "description": STR.OPEN_PREFERENCES_FOLDER_DESC,
                    "callback": self._open_preferences_folder,
                },
                "open_registry": {
                    "label": STR.REG_TITLE,
                    "description": STR.REG_TITLE_DESC,
                    "callback": self._open_lic_dialog,
                },
            },
            enable_close_button=True,
            enable_config_button=False,
            enable_info=True,
            tool_key=self.TOOL_KEY,
            parent=self,
        )

        # Ordem de adição no layout
        self.layout.addWidget(self.geral_collapsable)
        self.layout.addWidget(self.calc_collapsable)
        self.layout.add_execution_buttons(self.action_buttons)
        self.logger.info("Interface de configurações construída com sucesso")

    def _load_prefs(self):
        """Carrega preferências salvas."""
        self.logger.debug("Carregando preferências")
        self.prefer_VectorFields = Preferences.load_tool_prefs(ToolKey.VECTOR_FIELDS)

        calc_method = self.system_preferences.get("calculation_method", STR.ELLIPSOIDAL)
        if calc_method in self.CALCULATION_METHODS:
            self.radio_calc.set_selected_index(
                self.CALCULATION_METHODS.index(calc_method)
            )
            self.logger.debug(f"Método de cálculo carregado: {calc_method}")
        else:
            self.logger.warning(
                f"Método de cálculo inválido: {calc_method}, usando padrão"
            )
            self.radio_calc.set_selected_index(0)

        selected_language = self.system_preferences.get("plugin_language", "none")
        if selected_language in StringManager.AVAILABLE_LANGUAGES:
            self.lang_selector.set_selected_key("language", selected_language)
            self.logger.debug(f"Idioma selecionado carregado: {selected_language}")
        else:
            self.logger.warning(f"Idioma inválido: {selected_language}, usando padrão")
            self.lang_selector.set_selected_key("language", "pt_BR")

        selected_theme = self.system_preferences.get("theme")
        self.lang_selector.set_selected_key("theme", selected_theme)
        if selected_theme:
            self.logger.debug(f"Tema carregado das preferências: {selected_theme}")
        else:
            self.logger.debug("Nenhum tema salvo nas preferências — usando padrão")

        selected_crs_authid = self.system_preferences.get(
            "default_crs_authid", self.DEFAULT_CRS_AUTHID
        )
        if not self.crs_selector.set_crs_authid(selected_crs_authid):
            self.logger.warning(f"SRC invalido: {selected_crs_authid}, usando padrao")
            self.crs_selector.set_crs_authid(self.DEFAULT_CRS_AUTHID)
        self.logger.debug(f"SRC padrao carregado: {self.crs_selector.get_crs_authid()}")

        if "async_threshold_features" in self.system_preferences:
            thresh_feats = self.system_preferences.get("async_threshold_features", 1000)
        else:
            old_bytes = self.system_preferences.get("async_threshold_bytes")
            if old_bytes is not None:
                self.logger.warning(
                    "Preferência antiga 'async_threshold_bytes' encontrada, substituindo por limite de feições padrão"
                )
            thresh_feats = 1000

        thresh_value = (
            int(thresh_feats)
            if isinstance(thresh_feats, int)
            else (int(thresh_feats) if str(thresh_feats).isdigit() else 1000)
        )
        self.spin_threshold.set_value("threshold", thresh_value)
        self.logger.debug(f"Limiar assíncrono carregado: {thresh_value} feições")

        prec = self.system_preferences.get("vector_field_precision", 2)
        precision_value = (
            int(prec)
            if isinstance(prec, int)
            else (int(prec) if str(prec).isdigit() else 2)
        )
        self.spin_precision.set_value("precision", precision_value)
        self.logger.debug(f"Precisão de campos vetoriais carregada: {precision_value}")

        self.area_fields_inputs.set_values(
            {
                "cartesian_suffix": self.prefer_VectorFields.get(
                    "cartesian_suffix", ""
                ),
                "ellipsoidal_suffix": self.prefer_VectorFields.get(
                    "ellipsoidal_suffix", "_eli"
                ),
            }
        )

        toolbar_visibility = MenuManager.normalize_toolbar_category_visibility(
            self.system_preferences.get(MenuManager.TOOLBAR_VISIBILITY_PREF_KEY)
        )
        for category in MenuManager.toolbar_category_options():
            self.toolbar_category_checks.set_checked(
                category, toolbar_visibility.get(category, True)
            )

        project_folder = self.system_preferences.get("projects_folder", "")
        if project_folder:
            self.project_folder_selector.set_path("projects_folder", project_folder)

        self.calc_collapsable.set_expanded(self.preferences.get("calc_expanded", False))
        self.geral_collapsable.set_expanded(
            self.preferences.get("geral_expanded", True)
        )

    def _save_prefs(self):
        """Salva preferências."""
        self.logger.debug("Salvando preferências")
        self.preferences["calc_expanded"] = self.calc_collapsable.is_expanded()
        self.preferences["geral_expanded"] = self.geral_collapsable.is_expanded()

        selected_text = self.radio_calc.get_selected_key()
        self.system_preferences["calculation_method"] = selected_text
        selected_crs = self.crs_selector.get_crs()
        if not selected_crs or not selected_crs.isValid():
            selected_crs = QgsCoordinateReferenceSystem(self.DEFAULT_CRS_AUTHID)
            self.crs_selector.set_crs(selected_crs)
        self.system_preferences["default_crs_authid"] = selected_crs.authid()
        self.logger.debug(f"SRC padrao salvo: {selected_crs.authid()}")

        feats_value = int(self.spin_threshold.get_value("threshold"))
        self.system_preferences["async_threshold_features"] = feats_value
        self.logger.debug(f"Limiar assíncrono por feições salvo: {feats_value} feições")

        precision_val = int(self.spin_precision.get_value("precision"))
        self.system_preferences["vector_field_precision"] = precision_val
        self.logger.debug(f"Precisão de campos vetoriais salva: {precision_val} casas")

        selected_language = self.lang_selector.get_selected_key("language")
        if selected_language != "none":
            self.system_preferences["plugin_language"] = selected_language
            self.logger.debug(f"Idioma selecionado salvo: {selected_language}")
        else:
            if "plugin_language" in self.system_preferences:
                del self.system_preferences["plugin_language"]
                self.logger.debug("Idioma selecionado removido para auto-detectar")

        selected_theme = self.lang_selector.get_selected_key("theme")
        if selected_theme:
            self.system_preferences["theme"] = selected_theme
            self.logger.debug(f"Tema selecionado salvo: {selected_theme}")
        else:
            self.system_preferences.pop("theme", None)
            self.logger.debug("Tema em branco — nenhum tema salvo nas preferências")

        toolbar_visibility = self.toolbar_category_checks.get_all_states()

        # Detecta se houve alteração na visibilidade para disparar refresh dinâmico
        old_visibility = self.system_preferences.get(
            MenuManager.TOOLBAR_VISIBILITY_PREF_KEY, {}
        )
        needs_toolbar_refresh = old_visibility != toolbar_visibility

        self.system_preferences[MenuManager.TOOLBAR_VISIBILITY_PREF_KEY] = (
            toolbar_visibility
        )
        self.logger.debug(
            f"Categorias visiveis na toolbar salvas: {toolbar_visibility}"
        )

        paths = self.project_folder_selector.get_paths()
        self.system_preferences["projects_folder"] = paths[0] if paths else ""

        cartesian_suffix = (
            self.area_fields_inputs.get_value("cartesian_suffix") or ""
        ).strip()
        ellipsoidal_suffix = (
            self.area_fields_inputs.get_value("ellipsoidal_suffix") or "_eli"
        ).strip()

        if cartesian_suffix == ellipsoidal_suffix:
            QgisMessageUtil.modal_warning(
                self.iface,
                STR.AREA_SUFFIXES_CANNOT_MATCH,
            )
            self.logger.warning("Salvamento cancelado: sulfixos de area duplicados")
            return False

        self.prefer_VectorFields["cartesian_suffix"] = cartesian_suffix
        self.prefer_VectorFields["ellipsoidal_suffix"] = ellipsoidal_suffix

        self._persist_window_size()
        self.on_finish_plugin()
        Preferences.save_tool_prefs(ToolKey.SYSTEM, self.system_preferences)
        Preferences.save_tool_prefs(ToolKey.VECTOR_FIELDS, self.prefer_VectorFields)
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
        self.logger.info(
            f"Preferências salvas:{self.system_preferences}==={self.preferences}"
        )

        # Recarrega o tema ativo (ThemeManager + AppStyles) para aplicar a seleção
        theme_manager.reload_theme()
        self.logger.debug(
            "Tema ativo recarregado: "
            f"{self.system_preferences.get('theme', 'padrão')}"
        )

        # Se a visibilidade mudou, emite um evento abstrato para ajustes de toolbar
        if needs_toolbar_refresh:
            try:
                from ..core.config.PyQtSignalManager import get_plugin_signal_hub

                hub = get_plugin_signal_hub()
                hub.toolbar_category_visibility_changed.emit(toolbar_visibility)
                self.logger.debug(
                    "Sinal de alteração de visibilidade da toolbar emitido pelo SettingsPlugin"
                )
            except Exception as e:
                self.logger.error(
                    f"Erro ao emitir sinal de alteração de visibilidade da toolbar: {e}"
                )

        return True

    def execute_tool(self):
        """Executa as configurações e fecha o diálogo."""
        self.logger.info("Aplicando configurações")
        if not self._save_prefs():
            return

        selected_method = self.radio_calc.get_selected_key()
        QgisMessageUtil.modal_info(
            self.iface,
            message=(
                f"{STR.CALCULATION_METHOD_LABEL} {selected_method}. "
                f"{STR.DEFAULT_CRS}: {self.crs_selector.get_crs_authid()}. "
                f"{STR.SETTINGS_SAVED_MESSAGE}"
            ),
        )

        # Recarregar strings de tradução com o novo idioma
        TranslationManager.reload_strings()
        self.logger.info(
            f"TranslationManager recarregado com locale: "
            f"{self.system_preferences.get('plugin_language', 'pt_BR')}"
        )

        self.logger.info("Configurações aplicadas e salvas")
        self.close()

    def _open_lic_dialog(self):
        """
        Abre o diálogo de gerenciamento de licença.
        A licença é salva/gerenciada pelo LicDialog diretamente via LicManager.
        """
        self.logger.debug("Abrindo diálogo de gerenciamento de licença")
        from ..core.ui.RegistryDialog import RegistryDialog

        dialog = RegistryDialog(iface=self.iface, parent=self)
        if hasattr(dialog, "exec_"):
            dialog.exec_()
        else:
            dialog.exec()

    def _open_preferences_folder(self):
        """Abre a pasta de preferências do Cadmus."""
        self.logger.debug("Abrindo pasta de preferências")

        from ..utils.Preferences import PREF_FOLDER

        if ExplorerUtils.open_folder(PREF_FOLDER, self.TOOL_KEY):
            self.logger.info(f"Abrindo pasta: {PREF_FOLDER}")
        else:
            self.logger.warning(f"Pasta de preferências não encontrada: {PREF_FOLDER}")
            QgisMessageUtil.modal_warning(
                iface=self.iface,
                message=f"{STR.PREFERENCES_FOLDER_NOT_FOUND} {PREF_FOLDER}",
            )


def run(iface):
    """Função de entrada do plugin."""
    dlg = SettingsPlugin(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg
