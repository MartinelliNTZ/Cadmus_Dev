# -*- coding: utf-8 -*-
from qgis.core import QgsMapLayerProxyModel

from ..plugins.BasePlugin import BasePluginMTL
from ..core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from ..core.engine_tasks.PathExtensionStep import PathExtensionStep
from ..core.engine_tasks.ExecutionContext import ExecutionContext
from ..i18n.TranslationManager import STR
from ..utils.ToolKeys import ToolKey
from ..utils.Preferences import Preferences
from ..utils.StringManager import StringManager

# NOVOS WIDGETS (substituem WidgetFactory)
from ..resources.new_widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.new_widgets.grid.GridComboBox import GridComboBox
from ..resources.new_widgets.grid.GridRadioButton import GridRadioButton
from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.new_widgets.SeparatorWidget import SeparatorWidget


class PathExtensionPlugin(BasePluginMTL):
    """
    Ferramenta para remover/restaurar extensão de arquivos
    ou zipar/deszipar fotos nos paths armazenados em feições vetoriais.
    """

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.init(ToolKey.PATH_EXTENSION_TOOL, "PathExtensionPlugin")

    def _build_ui(self, **kwargs):
        self.logger.debug("Inicializando PLUGIN PathExtensionPlugin")
        super()._build_ui(
            title=STR.PATH_EXTENSION_TITLE,
            icon_path="path_extension.ico",
            enable_scroll=True,
        )
        self.logger.info("Construindo interface da ferramenta")

        # ── Layer/Path Selector (GridComplexSelector) ────────────────
        self.logger.debug("Criando GridComplexSelector para selecao de camada")
        self.layer_selector = GridComplexSelector(
            config={
                "input_layer": {
                    "label": STR.INPUT_LAYER,
                    "description": "Selecione a camada vetorial de entrada",
                    "allow_layer": True,
                    "layer_filters": QgsMapLayerProxyModel.VectorLayer,
                    "allow_file": True,
                    "allow_folder": False,
                    "file_filter": StringManager.FILTER_VECTOR,
                    "mode_type": "input",
                    "allow_features_check": True,
                    "features_check_text": STR.ONLY_SELECTED_FEATURES,
                },
            },
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.logger.info(
            "GridComplexSelector criado com allow_layer=True, "
            "file_filter=StringManager.FILTER_VECTOR"
        )

        # ── Atributo Selector (GridComboBox) ─────────────────────────
        self.logger.debug("Criando GridComboBox para selecao de atributo")
        self.attr_selector = GridComboBox(
            config={
                "path_field": {
                    "label": f"{STR.PATH}:",
                    "description": (
                        "Selecione o campo que contem o caminho dos arquivos"
                    ),
                    "options": {},  # vazio inicialmente
                    "selected_key": None,
                },
            },
            separator_bottom=True,
            parent=self,
        )
        self.logger.info(
            "GridComboBox criado (vazio, aguardando selecao de camada)"
        )

        # Registra callback para quando o layer/path mudar
        self.layer_selector.set_on_changed(
            "input_layer", self._on_layer_changed
        )
        self.logger.debug(
            "Callback _on_layer_changed registrado via set_on_changed()"
        )

        # Popula inicialmente com a camada atual
        # O ComplexSelector com allow_layer=True e setAllowEmptyLayer(False)
        # já seleciona a primeira camada disponível automaticamente.
        # Precisamos disparar o callback manualmente para popular o combo.
        sel = self.layer_selector.get("input_layer")
        if sel and sel.using_layer_combo and sel.current_layer:
            self.logger.debug(
                "Populando combo inicialmente com a camada atual: "
                f"'{sel.current_layer.name()}'",
                code="INITIAL_POPULATE",
            )
            self._on_layer_changed(sel.get_paths())
        else:
            self.logger.debug(
                "Nenhuma camada selecionada inicialmente. "
                f"using_layer_combo={sel.using_layer_combo if sel else 'N/A'}, "
                f"current_layer={sel.current_layer if sel else 'N/A'}",
                code="INITIAL_POPULATE_SKIP",
            )

        self.layout.addWidget(self.layer_selector)
        self.layout.addWidget(SeparatorWidget())
        self.layout.addWidget(self.attr_selector)

        # ── Modo de Operação (GridRadioButton) ──────────────────────
        self.logger.debug("Criando GridRadioButton para modo de operacao")
        self.mode_selector = GridRadioButton(
            config={
                "remove": {
                    "label": STR.MODE_REMOVE,
                    "description": "Remove a extensao dos arquivos",
                },
                "restore": {
                    "label": STR.MODE_RESTORE,
                    "description": "Restaura a extensao dos arquivos",
                },
                "zip": {
                    "label": STR.MODE_ZIP,
                    "description": "Compacta os arquivos em ZIP",
                },
                "unzip": {
                    "label": STR.MODE_UNZIP,
                    "description": "Descompacta arquivos ZIP",
                },
            },
            columns=2,
            default_key="remove",
            separator_bottom=True,
            parent=self,
        )
        self.logger.info(
            "GridRadioButton criado com 4 modos: remove, restore, zip, unzip"
        )
        self.layout.addWidget(self.mode_selector)

        # ── Botões de Ação (GridExecutionButtons) ────────────────────
        self.logger.debug("Criando GridExecutionButtons")
        self.action_buttons = GridExecutionButtons(
            config={
                "run": {
                    "label": "Executar",
                    "description": "Inicia o processamento",
                    "callback": self.execute_tool,
                    "is_run_button": True,
                },
            },
            enable_close_button=True,
            enable_info=True,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.logger.info(
            "GridExecutionButtons criado com botao Executar + Fechar + Info"
        )
        self.layout.add_execution_buttons(self.action_buttons)

        self.logger.info("Interface da ferramenta construida com sucesso")

    def _obter_layer_do_selector(self):
        """
        Obtém a camada atual do ComplexSelector interno do GridComplexSelector.

        Returns
        -------
        tuple
            (selector, layer_or_none)
        """
        sel = self.layer_selector.get("input_layer")
        if not sel:
            return (None, None)

        layer = None
        if sel.using_layer_combo:
            layer = sel.current_layer
        return (sel, layer)

    def _on_layer_changed(self, paths: list[str]):
        """
        Atualiza options do dropdown de atributos quando a camada/path muda.
        Se a camada tiver atributo "Path"/"path", auto-seleciona.
        """
        _sel, layer = self._obter_layer_do_selector()

        if layer and layer.isValid():
            fields = layer.fields()
            options = {}
            default_key = None
            for i in range(fields.count()):
                field = fields.at(i)
                name = field.name()
                options[name] = name
                if name.lower() == "path":
                    default_key = name

            self.attr_selector.set_options("path_field", options)

            if default_key:
                self.attr_selector.set_selected_key("path_field", default_key)
        else:
            self.attr_selector.set_options("path_field", {})

    def _load_prefs(self):
        self.logger.debug("Carregando preferencias")

        last_mode = self.preferences.get("last_mode", "remove")
        if isinstance(last_mode, int):
            mode_map_reverse = {
                0: "remove", 1: "restore", 2: "zip", 3: "unzip",
            }
            last_mode = mode_map_reverse.get(last_mode, "remove")

        self.mode_selector.set_selected_key(str(last_mode))

    def _save_prefs(self):
        self.logger.debug("Salvando preferencias")

        self.preferences["last_mode"] = self.mode_selector.get_selected_key()
        self.preferences["window_width"] = self.width()
        self.preferences["window_height"] = self.height()

        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)

    def execute_tool(self):
        self.logger.info("Iniciando processamento: PathExtension")

        _sel, layer = self._obter_layer_do_selector()

        if not layer or not layer.isValid():
            self.logger.warning("Nenhuma camada vetorial valida selecionada")
            return

        attribute = self.attr_selector.get_selected_key("path_field")
        if not attribute:
            self.logger.warning("Nenhum atributo selecionado")
            return

        mode_key = self.mode_selector.get_selected_key()
        if not mode_key:
            self.logger.warning("Nenhum modo selecionado")
            return

        self.logger.info(
            f"Parametros: layer='{layer.name()}', "
            f"attribute='{attribute}', mode='{mode_key}'"
        )

        context = ExecutionContext()
        context.set("layer", layer)
        context.set("attribute", attribute)
        context.set("mode", mode_key)
        context.set("tool_key", self.TOOL_KEY)
        context.set("iface", self.iface)

        self._run_async_pipeline(context)

    def _run_async_pipeline(self, context: ExecutionContext):
        self.logger.info("Executando pipeline assincrona")

        steps = [PathExtensionStep()]

        engine = AsyncPipelineEngine(
            steps=steps,
            context=context,
            on_finished=self._on_pipeline_finished,
            on_error=self._on_pipeline_error,
        )

        engine.start()
        self.logger.info("Pipeline assincrona iniciada")

    def _on_pipeline_finished(self, context):
        super()._on_pipeline_finished(context)

    def _on_pipeline_error(self, errors):
        super()._on_pipeline_error(errors)


def run(iface):
    dlg = PathExtensionPlugin(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg