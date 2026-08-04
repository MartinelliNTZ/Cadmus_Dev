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
from ..resources.new_widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.new_widgets.grid.GridCheckbox import GridCheckbox
from ..resources.new_widgets.grid.GridInputFields import GridInputFields
from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.new_widgets.CollapsibleParametersWidget import (
    CollapsibleParametersWidget,
)
from ..resources.new_widgets.SeparatorWidget import SeparatorWidget


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
        key = item.get("key", "")
        if not key:
            continue
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

    PREF_INITIAL_FIELDS = "initial_fields_selected"
    PREF_EXIF_FIELDS = "exif_fields_selected"
    PREF_XMP_FIELDS = "xmp_fields_selected"
    PREF_CUSTOM_FIELDS = "custom_fields_selected"
    PREF_MRK_FIELDS = "mrk_fields_selected"
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
            items_per_row=1,
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

    def _get_selected_exif_fields(self):
        return MetadataFields.normalize_selected_keys(
            self.exif_checkbox.get_checked_keys(),
            allowed_keys=MetadataFields.exif_keys(),
        )

    def _get_selected_xmp_fields(self):
        return MetadataFields.normalize_selected_keys(
            self.xmp_checkbox.get_checked_keys(),
            allowed_keys=MetadataFields.xmp_keys(),
        )

    def _get_selected_custom_fields(self):
        return MetadataFields.normalize_selected_keys(
            self.custom_checkbox.get_checked_keys(),
            allowed_keys=MetadataFields.custom_keys(),
        )

    def _get_selected_initial_fields(self):
        return MetadataFields.normalize_selected_keys(
            self.initial_checkbox.get_checked_keys(),
            allowed_keys=MetadataFields.initial_keys(),
        )

    def _get_selected_mrk_fields(self):
        return MetadataFields.normalize_selected_keys(
            self.mrk_checkbox.get_checked_keys(),
            allowed_keys=MetadataFields.mrk_keys(),
        )

    def _load_prefs(self):
        folder_path = self.preferences.get("folder", "")
        if folder_path:
            self.grid_input.set_path("pasta_mrk", folder_path)
            self.logger.debug(
                "Caminho restaurado", code="PREFS_FOLDER_RESTORED", path=folder_path
            )
        self.opts_checkbox.set_checked("recursive", self.preferences.get("recursive", True))
        self.opts_checkbox.set_checked("use_mrk", self.preferences.get("use_mrk", True))
        self.opts_checkbox.set_checked("photos", self.preferences.get("photos", True))
        chk_report = self.opts_checkbox.widget("generate_report")
        if chk_report is not None:
            chk_report.setChecked(self.preferences.get("generate_report", True))
        initial_selected = self.preferences.get(self.PREF_INITIAL_FIELDS)
        exif_selected = self.preferences.get(self.PREF_EXIF_FIELDS)
        xmp_selected = self.preferences.get(self.PREF_XMP_FIELDS)
        custom_selected = self.preferences.get(self.PREF_CUSTOM_FIELDS)
        mrk_selected = self.preferences.get(self.PREF_MRK_FIELDS)
        if isinstance(initial_selected, list):
            self.initial_checkbox.set_checked_keys(
                MetadataFields.normalize_selected_keys(
                    initial_selected,
                    allowed_keys=MetadataFields.initial_keys(),
                )
            )
        if isinstance(exif_selected, list):
            self.exif_checkbox.set_checked_keys(
                MetadataFields.normalize_selected_keys(
                    exif_selected,
                    allowed_keys=MetadataFields.exif_keys(),
                )
            )
        if isinstance(xmp_selected, list):
            self.xmp_checkbox.set_checked_keys(
                MetadataFields.normalize_selected_keys(
                    xmp_selected,
                    allowed_keys=MetadataFields.xmp_keys(),
                )
            )
        if isinstance(custom_selected, list):
            self.custom_checkbox.set_checked_keys(
                MetadataFields.normalize_selected_keys(
                    custom_selected,
                    allowed_keys=MetadataFields.custom_keys(),
                )
            )
        if isinstance(mrk_selected, list):
            self.mrk_checkbox.set_checked_keys(
                MetadataFields.normalize_selected_keys(
                    mrk_selected,
                    allowed_keys=MetadataFields.mrk_keys(),
                )
            )
        self.grid_save.set_lock_state("save_points", self.preferences.get("save_file_pts", False))
        self.grid_save.set_path("save_points", self.preferences.get("output_path_pts", ""))
        self.grid_save.set_lock_state("save_track", self.preferences.get("save_file", False))
        self.grid_save.set_path("save_track", self.preferences.get("output_path", ""))
        if hasattr(self, "logo_selector"):
            self.logo_selector.set_lock_state("logo", self.preferences.get("logo_enabled", False))
            self.logo_selector.set_path("logo", self.preferences.get("logo_path", ""))
        if hasattr(self, "title_input"):
            title_val = self.preferences.get("project_title", "")
            if title_val:
                self.title_input.set_value("project_title", title_val)
        self.grid_qml.set_lock_state("qml_points", self.preferences.get("apply_style_points", False))
        self.grid_qml.set_path("qml_points", self.preferences.get("qml_path_points", ""))
        self.grid_qml.set_lock_state("qml_track", self.preferences.get("apply_style_track", False))
        self.grid_qml.set_path("qml_track", self.preferences.get("qml_path_track", ""))
        self.opts_collapsible.set_expanded(
            self.preferences.get("opts_expanded", True))
        self.exif_fields_collapsible.set_expanded(
            self.preferences.get("exif_expanded", False)
        )
        self.xmp_fields_collapsible.set_expanded(
            self.preferences.get("xmp_expanded", False)
        )
        self.custom_fields_collapsible.set_expanded(
            self.preferences.get("custom_expanded", False)
        )
        self.initial_fields_collapsible.set_expanded(
            self.preferences.get("initial_expanded", False)
        )
        self.mrk_fields_collapsible.set_expanded(
            self.preferences.get("mrk_expanded", False)
        )
        self.save_collapsible.set_expanded(
            self.preferences.get("save_expanded", False))
        self.styles_collapsible.set_expanded(
            self.preferences.get("styles_expanded", False)
        )

        # Aplica visibilidade do MRK conforme preferência
        use_mrk = self.preferences.get("use_mrk", True)
        self.mrk_fields_collapsible.setVisible(use_mrk)
        self.mrk_fields_collapsible.setEnabled(use_mrk)

        self.logger.debug("Preferências carregadas",
                          code="PREFS_LOAD_COMPLETE")

    def _save_prefs(self):
        self.logger.debug("Salvando preferências", code="PREFS_SAVE_START")
        self.preferences["folder"] = self.grid_input.get_path("pasta_mrk") or ""
        self.preferences["recursive"] = self.opts_checkbox.is_checked("recursive")
        self.preferences["use_mrk"] = self.opts_checkbox.is_checked("use_mrk")
        self.preferences["photos"] = self.opts_checkbox.is_checked("photos")
        chk_report = self.opts_checkbox.widget("generate_report")
        if chk_report is not None:
            self.preferences["generate_report"] = chk_report.isChecked()
        self.preferences[self.PREF_INITIAL_FIELDS] = self._get_selected_initial_fields()
        self.preferences[self.PREF_EXIF_FIELDS] = self._get_selected_exif_fields()
        self.preferences[self.PREF_XMP_FIELDS] = self._get_selected_xmp_fields()
        self.preferences[self.PREF_CUSTOM_FIELDS] = self._get_selected_custom_fields()
        self.preferences[self.PREF_MRK_FIELDS] = self._get_selected_mrk_fields()
        self.preferences["save_file"] = self.grid_save.get_lock_state("save_track")
        self.preferences["save_file_pts"] = self.grid_save.get_lock_state("save_points")
        self.preferences["output_path"] = self.grid_save.get_path("save_track")
        self.preferences["output_path_pts"] = self.grid_save.get_path("save_points")
        if hasattr(self, "title_input"):
            self.preferences["project_title"] = self.title_input.get_value("project_title")
        if hasattr(self, "logo_selector"):
            self.preferences["logo_path"] = self.logo_selector.get_path("logo")
            self.preferences["logo_enabled"] = self.logo_selector.get_lock_state("logo")
        self.preferences["apply_style_track"] = self.grid_qml.get_lock_state("qml_track")
        self.preferences["qml_path_track"] = self.grid_qml.get_path("qml_track")
        self.preferences["apply_style_points"] = self.grid_qml.get_lock_state("qml_points")
        self.preferences["qml_path_points"] = self.grid_qml.get_path("qml_points")
        self.preferences["opts_expanded"] = self.opts_collapsible.is_expanded()
        self.preferences["exif_expanded"] = self.exif_fields_collapsible.is_expanded()
        self.preferences["xmp_expanded"] = self.xmp_fields_collapsible.is_expanded()
        self.preferences["custom_expanded"] = (
            self.custom_fields_collapsible.is_expanded()
        )
        self.preferences["initial_expanded"] = (
            self.initial_fields_collapsible.is_expanded()
        )
        self.preferences["mrk_expanded"] = self.mrk_fields_collapsible.is_expanded()
        self.preferences["save_expanded"] = self.save_collapsible.is_expanded()
        self.preferences["styles_expanded"] = self.styles_collapsible.is_expanded()
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