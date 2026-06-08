# -*- coding: utf-8 -*-
from qgis.core import QgsMapLayerProxyModel
from ..plugins.BasePlugin import BasePluginMTL
from ..core.ui.WidgetFactory import WidgetFactory
from ..core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from ..core.engine_tasks.PathExtensionStep import PathExtensionStep
from ..core.engine_tasks.ExecutionContext import ExecutionContext
from ..i18n.TranslationManager import STR
from ..utils.ToolKeys import ToolKey
from ..utils.Preferences import Preferences


class PathExtensionPlugin(BasePluginMTL):
    """
    Ferramenta para remover ou restaurar extensão de arquivos
    nos paths armazenados em feições vetoriais.
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

        layer_layout, self.layer_input = WidgetFactory.create_layer_input(
            label_text=STR.INPUT_LAYER,
            filters=[QgsMapLayerProxyModel.VectorLayer],
            parent=self,
            allow_empty=False,
        )
        self.logger.debug("Componente de camada de entrada adicionado")

        # Seletor de atributo usando dropdown (campos da camada)
        attr_layout, self.attr_selector = WidgetFactory.create_dropdown_selector(
            title=f"{STR.PATH}:",
            options_dict={},
            parent=self,
            allow_empty=True,
            empty_text=STR.SELECT,
            separator_bottom=True,
        )
        self.logger.debug("Componente de seletor de atributo adicionado")

        # Conectar mudança de camada para atualizar combo de atributos
        self.layer_input.layerChanged.connect(self._on_layer_changed)

        # Seletor de modo via radio button grid
        mode_layout, self.radio_mode = WidgetFactory.create_radio_button_grid(
            items=[STR.MODE_REMOVE, STR.MODE_RESTORE],
            columns=2,
            checked_index=0,
            tool_key=self.TOOL_KEY,
            separator_bottom=True,
        )
        self.logger.debug("Componente de modo de operação adicionado")

        buttons_layout, self.action_buttons = (
            WidgetFactory.create_bottom_action_buttons(
                parent=self,
                run_callback=self.execute_tool,
                close_callback=self.close,
                info_callback=self.show_info_dialog,
                tool_key=self.TOOL_KEY,
            )
        )

        self.layout.add_items(
            [layer_layout, attr_layout, mode_layout, buttons_layout]
        )
        self.logger.info("Interface da ferramenta construída com sucesso")

    def _on_layer_changed(self):
        """Atualiza options do dropdown de atributos quando a camada muda."""
        layer = self.layer_input.current_layer()
        if not layer or not layer.isValid():
            self.attr_selector.set_options({})
            return

        fields = layer.fields()
        options = {}
        default_key = None
        for i in range(fields.count()):
            field = fields.at(i)
            name = field.name()
            options[name] = name
            if name.lower() == "path":
                default_key = name

        self.attr_selector.set_options(options)
        if default_key:
            self.attr_selector.set_selected_key(default_key)

    def _load_prefs(self):
        self.logger.debug("Carregando preferências")
        last_mode = self.preferences.get("last_mode", 0)
        self.radio_mode.set_selected_index(int(last_mode))

    def _save_prefs(self):
        self.logger.debug("Salvando preferências")
        self.preferences["last_mode"] = self.radio_mode.get_selected_index()
        self.preferences["window_width"] = self.width()
        self.preferences["window_height"] = self.height()
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)

    def execute_tool(self):
        self.logger.info("Iniciando processamento: PathExtension")

        layer = self.layer_input.current_layer()
        if not layer or not layer.isValid():
            self.logger.warning("Nenhuma camada vetorial válida selecionada")
            return

        attribute = self.attr_selector.get_selected_key()
        if not attribute:
            self.logger.warning("Nenhum atributo selecionado")
            return

        mode_index = self.radio_mode.get_selected_index()
        mode = "remove" if mode_index == 0 else "restore"
        if not mode:
            self.logger.warning("Nenhum modo selecionado")
            return

        self.logger.info(
            f"Parâmetros: layer='{layer.name()}', "
            f"attribute='{attribute}', mode='{mode}'"
        )

        context = ExecutionContext()
        context.set("layer", layer)
        context.set("attribute", attribute)
        context.set("mode", mode)
        context.set("tool_key", self.TOOL_KEY)
        context.set("iface", self.iface)

        self._run_async_pipeline(context)

    def _run_async_pipeline(self, context: ExecutionContext):
        self.logger.info("Executando pipeline assíncrona")

        steps = [PathExtensionStep()]

        engine = AsyncPipelineEngine(
            steps=steps,
            context=context,
            on_finished=self._on_pipeline_finished,
            on_error=self._on_pipeline_error,
        )

        engine.start()
        self.logger.info("Pipeline assíncrona iniciada")

    def _on_pipeline_finished(self, context):
        super()._on_pipeline_finished(context)

    def _on_pipeline_error(self, errors):
        super()._on_pipeline_error(errors)


def run(iface):
    dlg = PathExtensionPlugin(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg