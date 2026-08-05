# -*- coding: utf-8 -*-
import os
from ..plugins.BasePlugin import BasePluginMTL
from ..core.services.DronePipelineService import DronePipelineService
from ..utils.StringManager import StringManager
from ..utils.Preferences import Preferences
from ..utils.ToolKeys import ToolKey
from ..i18n.TranslationManager import STR
from ..utils.DependenciesManager import DependenciesManager
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.mrk.MetadataFields import MetadataFields
from ..utils.adapter.StringAdapter import StringAdapter

# ── Novos Widgets ──────────────────────────────────────────────
from ..resources.widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.widgets.grid.GridCheckbox import GridCheckbox
from ..resources.widgets.grid.GridInputFields import GridInputFields
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.widgets.CollapsibleParametersWidget import (
    CollapsibleParametersWidget,
)
from ..resources.widgets.SeparatorWidget import SeparatorWidget


def _to_checkbox_config(items) -> dict:
    """
    Converte lista de dicts (StringAdapter.to_key_label_description)
    em dict config para GridCheckbox.

    Parâmetros
    ----------
    items : list[dict]
        Lista com chaves "key", "label", "description".

    Returns
    -------
    dict
        {"key": {"label": ..., "description": ...}}
    """
    config = {}
    for item in items or []:
        raw_key = item.get("key", "")
        if not raw_key:
            continue
        # Converte MetadataFieldKey (enum) para string value
        key = getattr(raw_key, "value", raw_key)
        label = item.get("label") or key
        description = item.get("description") or ""
        config[key] = {"label": label, "description": description}
    return config


class DroneCordinates(BasePluginMTL):

    TOOL_KEY = ToolKey.DRONE_COORDINATES

    # Nível mínimo de licença exigido para funcionalidades premium (relatório, logo, título)
    REGISTRY_LEVEL: int = 3

    CHECKBOX_OPTIONS = {
        "recursive": STR.RECURSIVE_SEARCH,
        "use_mrk": STR.USE_MRK_DATA,
        "photos": STR.PHOTOS_METADATA,
        "generate_report": STR.GENERATE_REPORT,
    }

    AUTO_SAVE_PREFS_ON_CLOSE = True

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface

        # Inicializa a UI e preferências via BasePluginMTL
        self.init(
            self.TOOL_KEY,
            "Drone Coordinates",
            load_system_prefs=False,
            build_ui=True,
        )

    def _build_ui(self, **kwargs):
        super()._build_ui(
            title=STR.DRONE_COORDINATES_TITLE,
            icon_path="coord.ico",
            enable_scroll=True,
        )

        # Verifica licença — controla exibição de itens do relatório
        try:
            from ..core.config.RegistryManager import RegistryManager
            lic_mgr = RegistryManager(tool_key=self.TOOL_KEY)
            is_lic_valid = lic_mgr.has_minimum_level(self.REGISTRY_LEVEL)
        except Exception as e:
            self.logger.error(
                f"Erro ao verificar licença: {e}", code="CHECK_ERROR"
            )
            is_lic_valid = False

        # ====== PASTA MRK (GridComplexSelector folder input) ======
        self.grid_input = GridComplexSelector(
            config={
                "pasta_mrk": {
                    "label": STR.MRK_FOLDER,
                    "description": "Pasta contendo os arquivos MRK",
                    "allow_file": False,
                    "allow_folder": True,
                    "mode_type": "input",
                },
            },
            tool_key=self.TOOL_KEY,
            grid_id="grid_input",
            parent=self,
        )
        self.layout.addWidget(self.grid_input)
        self.layout.addWidget(SeparatorWidget())

        # ====== OPÇÕES (CollapsibleParametersWidget) ======
        self.opts_collapsible = CollapsibleParametersWidget(
            title=STR.OPTIONS,
            expanded_by_default=False,
            parent=self,
        )
        self.layout.addWidget(self.opts_collapsible)

        # ====== LOGO / IMAGE SELECTOR (só se licença válida) ======
        if is_lic_valid:
            self.logo_selector = GridComplexSelector(
                config={
                    "logo": {
                        "label": STR.LOGO_LABEL,
                        "description": "Arquivo de logotipo",
                        "mode_type": "output",
                        "allow_file": True,
                        "allow_folder": False,
                        "file_filter": StringManager.FILTER_IMAGES,
                        "allow_lock_check": True,
                        "lock_check_default": False,
                    },
                },
                tool_key=self.TOOL_KEY,
                grid_id="grid_logo",
                parent=self,
            )
            self.opts_collapsible.add_content_widget(self.logo_selector)

        # ====== PROJETO TITLE (só se licença válida) ======
        if is_lic_valid:
            self.title_input = GridInputFields(
                config={
                    "project_title": {
                        "label": STR.PROJECT_TITLE,
                        "description": STR.PROJECT_TITLE_HINT,
                        "default": "",
                    },
                },
                title=None,
                separator_bottom=False,
                parent=self,
            )
            self.opts_collapsible.add_content_widget(self.title_input)

        # ====== OPÇÕES CHECKBOXES (GridCheckbox 1 coluna) ======
        checkbox_options = dict(self.CHECKBOX_OPTIONS)
        if not is_lic_valid:
            checkbox_options.pop("generate_report", None)

        self.opts_checkbox = GridCheckbox(
            config={
                key: {"label": label} for key, label in checkbox_options.items()
            },
            items_per_row=2,
            separator_bottom=False,
            parent=self,
        )
        self.opts_collapsible.add_content_widget(self.opts_checkbox)

        # Connect checkbox toggles for dependency checks
        self.chk_photos = self.opts_checkbox.widget("photos")
        if self.chk_photos is not None:
            self.chk_photos.toggled.connect(self.on_photos_changed)

        # Connect use_mrk toggle to enable/disable MRK sections
        self.chk_use_mrk = self.opts_checkbox.widget("use_mrk")
        if self.chk_use_mrk is not None:
            self.chk_use_mrk.toggled.connect(self._on_use_mrk_changed)

        # ====== METADATA EXIF FIELDS ======
        self.exif_fields_collapsible = CollapsibleParametersWidget(
            title="EXIF Fields",
            expanded_by_default=False,
            parent=self,
        )
        self.layout.addWidget(self.exif_fields_collapsible)

        exif_items = _to_checkbox_config(
            StringAdapter.to_key_label_description(MetadataFields.EXIF_FIELDS)
        )
        self.exif_checkbox = GridCheckbox(
            config=exif_items,
            items_per_row=2,
            control_buttons_config={
                "select_all": {
                    "label": STR.SELECT_ALL,
                    "callback": lambda: self.exif_checkbox.select_all(),
                },
                "deselect_all": {
                    "label": STR.DESELECT_ALL,
                    "callback": lambda: self.exif_checkbox.deselect_all(),
                },
                "invert": {
                    "label": STR.INVERT,
                    "callback": lambda: self.exif_checkbox.invert_selection(),
                },
            },
            separator_bottom=False,
            parent=self,
        )
        self.exif_checkbox.set_checked_keys(MetadataFields.exif_keys())
        self.exif_fields_collapsible.add_content_widget(self.exif_checkbox)

        # ====== METADATA DJI FIELDS (XMP) ======
        self.xmp_fields_collapsible = CollapsibleParametersWidget(
            title="DJI Fields",
            expanded_by_default=False,
            parent=self,
        )
        self.layout.addWidget(self.xmp_fields_collapsible)

        xmp_items = _to_checkbox_config(
            StringAdapter.to_key_label_description(MetadataFields.DJI_XMP_FIELDS)
        )
        self.xmp_checkbox = GridCheckbox(
            config=xmp_items,
            items_per_row=2,
            control_buttons_config={
                "select_all": {
                    "label": STR.SELECT_ALL,
                    "callback": lambda: self.xmp_checkbox.select_all(),
                },
                "deselect_all": {
                    "label": STR.DESELECT_ALL,
                    "callback": lambda: self.xmp_checkbox.deselect_all(),
                },
                "invert": {
                    "label": STR.INVERT,
                    "callback": lambda: self.xmp_checkbox.invert_selection(),
                },
            },
            separator_bottom=False,
            parent=self,
        )
        self.xmp_checkbox.set_checked_keys(MetadataFields.xmp_keys())
        self.xmp_fields_collapsible.add_content_widget(self.xmp_checkbox)

        # ====== METADATA CUSTOM FIELDS ======
        self.custom_fields_collapsible = CollapsibleParametersWidget(
            title="Custom Fields",
            expanded_by_default=False,
            parent=self,
        )
        self.layout.addWidget(self.custom_fields_collapsible)

        custom_items = _to_checkbox_config(
            StringAdapter.to_key_label_description(MetadataFields.CUSTOM_FIELDS)
        )
        self.custom_checkbox = GridCheckbox(
            config=custom_items,
            items_per_row=2,
            control_buttons_config={
                "select_all": {
                    "label": STR.SELECT_ALL,
                    "callback": lambda: self.custom_checkbox.select_all(),
                },
                "deselect_all": {
                    "label": STR.DESELECT_ALL,
                    "callback": lambda: self.custom_checkbox.deselect_all(),
                },
                "invert": {
                    "label": STR.INVERT,
                    "callback": lambda: self.custom_checkbox.invert_selection(),
                },
            },
            separator_bottom=False,
            parent=self,
        )
        self.custom_checkbox.set_checked_keys(MetadataFields.custom_keys())
        self.custom_fields_collapsible.add_content_widget(self.custom_checkbox)

        # ====== METADATA INITIAL FIELDS ======
        self.initial_fields_collapsible = CollapsibleParametersWidget(
            title="Initial Fields",
            expanded_by_default=False,
            parent=self,
        )
        self.layout.addWidget(self.initial_fields_collapsible)

        initial_items = _to_checkbox_config(
            StringAdapter.to_key_label_description(MetadataFields.INITIAL_FIELDS)
        )
        self.initial_checkbox = GridCheckbox(
            config=initial_items,
            items_per_row=2,
            control_buttons_config={
                "select_all": {
                    "label": STR.SELECT_ALL,
                    "callback": lambda: self.initial_checkbox.select_all(),
                },
                "deselect_all": {
                    "label": STR.DESELECT_ALL,
                    "callback": lambda: self.initial_checkbox.deselect_all(),
                },
                "invert": {
                    "label": STR.INVERT,
                    "callback": lambda: self.initial_checkbox.invert_selection(),
                },
            },
            separator_bottom=False,
            parent=self,
        )
        self.initial_checkbox.set_checked_keys(MetadataFields.initial_keys())
        self.initial_fields_collapsible.add_content_widget(self.initial_checkbox)

        # ====== METADATA MRK FIELDS ======
        self.mrk_fields_collapsible = CollapsibleParametersWidget(
            title="MRK Fields",
            expanded_by_default=False,
            parent=self,
        )
        self.layout.addWidget(self.mrk_fields_collapsible)

        mrk_items = _to_checkbox_config(
            StringAdapter.to_key_label_description(MetadataFields.MRK_FIELDS)
        )
        self.mrk_checkbox = GridCheckbox(
            config=mrk_items,
            items_per_row=2,
            control_buttons_config={
                "select_all": {
                    "label": STR.SELECT_ALL,
                    "callback": lambda: self.mrk_checkbox.select_all(),
                },
                "deselect_all": {
                    "label": STR.DESELECT_ALL,
                    "callback": lambda: self.mrk_checkbox.deselect_all(),
                },
                "invert": {
                    "label": STR.INVERT,
                    "callback": lambda: self.mrk_checkbox.invert_selection(),
                },
            },
            separator_bottom=False,
            parent=self,
        )
        self.mrk_checkbox.set_checked_keys(MetadataFields.mrk_keys())
        self.mrk_fields_collapsible.add_content_widget(self.mrk_checkbox)

        # ====== SALVAMENTO (Collapsible + GridComplexSelector) ======
        self.save_collapsible = CollapsibleParametersWidget(
            title=STR.SAVING,
            expanded_by_default=False,
            parent=self,
        )
        self.layout.addWidget(self.save_collapsible)

        self.grid_save = GridComplexSelector(
            config={
                "save_points": {
                    "label": STR.SAVE_IN,
                    "description": STR.SAVE_POINTS_CHECKBOX,
                    "mode_type": "output",
                    "parent": "grid_input.pasta_mrk",
                    "allow_file": True,
                    "allow_folder": False,
                    "file_filter": StringManager.FILTER_VECTOR,
                    "allow_lock_check": True,
                    "lock_check_default": False,
                },
                "save_track": {
                    "label": STR.SAVE_IN,
                    "description": STR.SAVE_TRACK_CHECKBOX,
                    "mode_type": "output",
                    "parent": "grid_input.pasta_mrk",
                    "allow_file": True,
                    "allow_folder": False,
                    "file_filter": StringManager.FILTER_VECTOR,
                    "allow_lock_check": True,
                    "lock_check_default": False,
                },
            },
            tool_key=self.TOOL_KEY,
            grid_id="grid_save",
            parent=self,
        )
        self.save_collapsible.add_content_widget(self.grid_save)

        # ====== ESTILOS (QML) - Collapsible + GridComplexSelector ======
        self.styles_collapsible = CollapsibleParametersWidget(
            title=STR.STYLES,
            expanded_by_default=False,
            parent=self,
        )
        self.layout.addWidget(self.styles_collapsible)

        self.grid_qml = GridComplexSelector(
            config={
                "qml_points": {
                    "label": STR.QML_POINTS,
                    "description": STR.APPLY_STYLE_POINTS,
                    "mode_type": "output",
                    "parent": "grid_input.pasta_mrk",
                    "allow_file": True,
                    "allow_folder": False,
                    "file_filter": StringManager.FILTER_QGIS_STYLE,
                    "allow_lock_check": True,
                    "lock_check_default": False,
                },
                "qml_track": {
                    "label": STR.QML_TRACK,
                    "description": STR.APPLY_STYLE_TRACK,
                    "mode_type": "output",
                    "parent": "grid_input.pasta_mrk",
                    "allow_file": True,
                    "allow_folder": False,
                    "file_filter": StringManager.FILTER_QGIS_STYLE,
                    "allow_lock_check": True,
                    "lock_check_default": False,
                },
            },
            tool_key=self.TOOL_KEY,
            grid_id="grid_qml",
            parent=self,
        )
        self.styles_collapsible.add_content_widget(self.grid_qml)

        # ====== BOTÕES (GridExecutionButtons — FORA do scroll) ======
        self.action_buttons = GridExecutionButtons(
            config={
                "run": {
                    "label": STR.EXECUTE,
                    "description": "Inicia o processamento de coordenadas de drone",
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

    def _on_use_mrk_changed(self, checked: bool):
        """Habilita/desabilita seção MRK conforme checkbox 'Obter dados MRK'."""
        self.mrk_fields_collapsible.setVisible(checked)
        self.mrk_fields_collapsible.setEnabled(checked)
        if not checked:
            # Se não usa MRK, também limpa a seleção de campos MRK
            self.mrk_checkbox.set_checked_keys([])

    def _ensure_photos_dependency(self, checked: bool):
        if not checked:
            return
        if DependenciesManager.check_dependency("Pillow", self.TOOL_KEY):
            return
        confirmed = QgisMessageUtil.confirm(
            self.iface,
            STR.PHOTOS_METADATA_REQUIRED_MESSAGE,
            STR.REQUIRED_LIBRARY,
        )
        if not confirmed:
            self.chk_photos.setChecked(False)
            return
        started = DependenciesManager.install_dependency_gui(
            "Pillow", self.iface, self.TOOL_KEY
        )
        if not started:
            QgisMessageUtil.modal_error(
                self.iface,
                STR.INSTALL_DEPENDENCY_FAILED.format("Pillow"),
            )
            self.chk_photos.setChecked(False)

    def on_photos_changed(self, checked: bool):
        self._ensure_photos_dependency(checked)

    def _load_prefs(self):
        self.logger.debug("Carregando preferencias do DroneCoordinates",
                          code="PREFS_LOAD_START")

        # GridComplexSelectors (paths + lock_state + checked_state)
        grid_input_prefs = self.preferences.get("grid_input", {})
        if grid_input_prefs:
            self.grid_input.set_preferences(grid_input_prefs)
        grid_save_prefs = self.preferences.get("grid_save", {})
        if grid_save_prefs:
            self.grid_save.set_preferences(grid_save_prefs)
        grid_qml_prefs = self.preferences.get("grid_qml", {})
        if grid_qml_prefs:
            self.grid_qml.set_preferences(grid_qml_prefs)
        if hasattr(self, "logo_selector"):
            grid_logo_prefs = self.preferences.get("grid_logo", {})
            if grid_logo_prefs:
                self.logo_selector.set_preferences(grid_logo_prefs)

        # GridCheckbox (opções + metadados)
        checkbox_prefs = self.preferences.get("opts_checkbox", {})
        if checkbox_prefs:
            self.opts_checkbox.set_preferences(checkbox_prefs)
        checkbox_prefs = self.preferences.get("exif_checkbox", {})
        if checkbox_prefs:
            self.exif_checkbox.set_preferences(checkbox_prefs)
        checkbox_prefs = self.preferences.get("xmp_checkbox", {})
        if checkbox_prefs:
            self.xmp_checkbox.set_preferences(checkbox_prefs)
        checkbox_prefs = self.preferences.get("custom_checkbox", {})
        if checkbox_prefs:
            self.custom_checkbox.set_preferences(checkbox_prefs)
        checkbox_prefs = self.preferences.get("initial_checkbox", {})
        if checkbox_prefs:
            self.initial_checkbox.set_preferences(checkbox_prefs)
        checkbox_prefs = self.preferences.get("mrk_checkbox", {})
        if checkbox_prefs:
            self.mrk_checkbox.set_preferences(checkbox_prefs)

        # GridInputFields (título do projeto)
        if hasattr(self, "title_input"):
            title_prefs = self.preferences.get("title_input", {})
            if title_prefs:
                self.title_input.set_preferences(title_prefs)

        # CollapsibleParametersWidget (estado expandido)
        collapsible_map = {
            "opts_collapsible": self.opts_collapsible,
            "exif_fields_collapsible": self.exif_fields_collapsible,
            "xmp_fields_collapsible": self.xmp_fields_collapsible,
            "custom_fields_collapsible": self.custom_fields_collapsible,
            "initial_fields_collapsible": self.initial_fields_collapsible,
            "mrk_fields_collapsible": self.mrk_fields_collapsible,
            "save_collapsible": self.save_collapsible,
            "styles_collapsible": self.styles_collapsible,
        }
        for prefs_key, collapsible in collapsible_map.items():
            prefs = self.preferences.get(prefs_key, {})
            if prefs:
                collapsible.set_preferences(prefs)

        # Aplica visibilidade do MRK conforme checkbox "Obter dados MRK"
        use_mrk = self.opts_checkbox.is_checked("use_mrk")
        self.mrk_fields_collapsible.setVisible(use_mrk)
        self.mrk_fields_collapsible.setEnabled(use_mrk)

        self.logger.debug("Preferências carregadas",
                          code="PREFS_LOAD_COMPLETE")

    def _save_prefs(self):
        self.logger.debug("Salvando preferências", code="PREFS_SAVE_START")

        # GridComplexSelectors (paths + lock_state + checked_state)
        self.preferences["grid_input"] = self.grid_input.get_preferences()
        self.preferences["grid_save"] = self.grid_save.get_preferences()
        self.preferences["grid_qml"] = self.grid_qml.get_preferences()
        if hasattr(self, "logo_selector"):
            self.preferences["grid_logo"] = self.logo_selector.get_preferences()

        # GridCheckbox (opções + metadados)
        self.preferences["opts_checkbox"] = self.opts_checkbox.get_preferences()
        self.preferences["exif_checkbox"] = self.exif_checkbox.get_preferences()
        self.preferences["xmp_checkbox"] = self.xmp_checkbox.get_preferences()
        self.preferences["custom_checkbox"] = self.custom_checkbox.get_preferences()
        self.preferences["initial_checkbox"] = self.initial_checkbox.get_preferences()
        self.preferences["mrk_checkbox"] = self.mrk_checkbox.get_preferences()

        # GridInputFields (título do projeto)
        if hasattr(self, "title_input"):
            self.preferences["title_input"] = self.title_input.get_preferences()

        # CollapsibleParametersWidget (estado expandido)
        collapsible_map = {
            "opts_collapsible": self.opts_collapsible,
            "exif_fields_collapsible": self.exif_fields_collapsible,
            "xmp_fields_collapsible": self.xmp_fields_collapsible,
            "custom_fields_collapsible": self.custom_fields_collapsible,
            "initial_fields_collapsible": self.initial_fields_collapsible,
            "mrk_fields_collapsible": self.mrk_fields_collapsible,
            "save_collapsible": self.save_collapsible,
            "styles_collapsible": self.styles_collapsible,
        }
        for prefs_key, collapsible in collapsible_map.items():
            self.preferences[prefs_key] = collapsible.get_preferences()

        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
        self.logger.debug("Preferências salvas", code="PREFS_SAVE_COMPLETE")

    def execute_tool(self):
        self.logger.info(
            "Iniciando processamento de coordenadas de drone", code="EXEC_START"
        )

        folder_path = self.grid_input.get_path("pasta_mrk") or ""
        if not folder_path:
            self.logger.error("Nenhum diretório selecionado",
                              code="NO_SELECTION")
            return

        apply_photos = self.opts_checkbox.is_checked("photos")

        if apply_photos and not DependenciesManager.check_dependency(
            "Pillow", self.TOOL_KEY
        ):
            self.logger.warning(
                "Cruzamento com metadados solicitado sem Pillow disponível; será ignorado"
            )
            apply_photos = False
            self.opts_checkbox.set_checked("photos", False)

        first_path = folder_path
        base_folder = (
            os.path.dirname(first_path)
            if first_path and os.path.isfile(first_path)
            else first_path
        )

        # Salva preferências atuais antes de executar
        self._save_prefs()

        # Delega montagem e execução do pipeline para o DronePipelineService
        DronePipelineService.execute(
            iface=self.iface,
            input_path=base_folder,
            paths=[folder_path],
        )


def run(iface):
    dlg = DroneCordinates(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg