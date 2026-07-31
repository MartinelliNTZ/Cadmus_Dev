# -*- coding: utf-8 -*-
from qgis.core import QgsMapLayerProxyModel

from ..plugins.BasePlugin import BasePluginMTL
from ..core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from ..core.engine_tasks.PathExtensionStep import PathExtensionStep
from ..core.engine_tasks.ExecutionContext import ExecutionContext
from ..i18n.TranslationManager import STR
from ..utils.ToolKeys import ToolKey
from ..utils.Preferences import Preferences

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
                    "allow_file": False,        # folder=false
                    "allow_folder": False,       # folder=false
                    "mode_type": "input",
                },
            },
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.logger.info(
            "GridComplexSelector criado com allow_layer=True, mode_type=input"
        )

        # Registra callback via set_on_changed()
        # O GridComplexSelector encapsula o on_path_change do ComplexSelector
        # Quando o layer/path mudar, _on_layer_changed é chamado com paths
        self.layer_selector.set_on_changed(
            "input_layer", self._on_layer_changed
        )
        self.logger.debug(
            "Callback _on_layer_changed registrado via set_on_changed()"
        )

        self.layout.addWidget(self.layer_selector)

        # ── Separador ────────────────────────────────────────────────
        self.layout.addWidget(SeparatorWidget())

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
        
        Usa self.layer_selector.get("input_layer") para acessar o ComplexSelector
        diretamente, e então usa a property current_layer do ComplexSelector.
        
        Returns
        -------
        tuple
            (selector, layer_or_none) onde:
            - selector: ComplexSelector ou None
            - layer_or_none: QgsMapLayer ou None
        """
        sel = self.layer_selector.get("input_layer")
        if not sel:
            self.logger.warning(
                "Selector 'input_layer' nao encontrado no GridComplexSelector",
                code="GET_SELECTOR_NOT_FOUND",
            )
            return (None, None)

        layer = None
        if sel.using_layer_combo:
            layer = sel.current_layer
            self.logger.info(
                f"_obter_layer_do_selector: modo=layer_combo, "
                f"layer={layer.name() if layer else 'None'}, "
                f"layer_valid={layer.isValid() if layer else False}",
                code="GET_SELECTOR_LAYER",
            )
        else:
            self.logger.info(
                f"_obter_layer_do_selector: modo=line_edit, "
                f"path='{sel.path()}'",
                code="GET_SELECTOR_PATH",
            )

        return (sel, layer)

    def _on_layer_changed(self, paths: list[str]):
        """
        Atualiza options do dropdown de atributos quando a camada/path muda.

        Usa _obter_layer_do_selector() para obter o ComplexSelector e a layer.
        Se layer for valido, popula combo com campos da camada.
        Se layer for None (modo path de arquivo), limpa o combo.
        Sempre busca se o atributo "Path"/"path" existe — se existir,
        ja aparece selecionado. Se nao existir, fica sem selecao.
        """
        self.logger.info(
            f"_on_layer_changed chamado com paths={paths}",
            code="ON_LAYER_CHANGED",
        )

        # Obtem selector e layer via metodo auxiliar
        _sel, layer = self._obter_layer_do_selector()
        self.logger.info(
            f"_on_layer_changed: selector={_sel is not None}, "
            f"layer={layer.name() if layer else None}",
            code="ON_LAYER_CHANGED_ITEM",
        )

        if layer and layer.isValid():
            # Modo camada: popula com campos da camada
            self.logger.info(
                f"Modo layer: camada '{layer.name()}' valida, "
                f"extraindo campos...",
                code="LAYER_MODE",
            )

            fields = layer.fields()
            options = {}
            default_key = None
            for i in range(fields.count()):
                field = fields.at(i)
                name = field.name()
                options[name] = name
                if name.lower() == "path":
                    default_key = name
                    self.logger.info(
                        f"Campo 'path' encontrado no indice {i}",
                        code="PATH_FIELD_FOUND",
                    )

            self.logger.info(
                f"Populando combo com {len(options)} campos, "
                f"default_key='{default_key}'",
                code="POPULATE_COMBO",
            )
            self.logger.debug(f"Options do combo: {list(options.keys())}")

            self.attr_selector.set_options("path_field", options)

            if default_key:
                self.attr_selector.set_selected_key("path_field", default_key)
                self.logger.info(
                    "Auto-selecionado campo 'path' no combo",
                    code="AUTO_SELECT_PATH",
                )
            else:
                self.logger.info(
                    "Campo 'path' nao encontrado. "
                    "Combo permanece sem selecao.",
                    code="PATH_FIELD_NOT_FOUND",
                )
        else:
            # Modo path (arquivo): limpa options
            self.logger.info(
                "Modo path: limpando combo de atributos "
                f"(layer={layer})",
                code="CLEAR_COMBO",
            )
            self.attr_selector.set_options("path_field", {})

        self.logger.info(
            "_on_layer_changed finalizado", code="ON_LAYER_CHANGED_END"
        )

    def _load_prefs(self):
        self.logger.debug("Carregando preferencias")

        last_mode = self.preferences.get("last_mode", "remove")
        self.logger.debug(
            f"Valor carregado de last_mode: {last_mode} "
            f"(tipo={type(last_mode).__name__})"
        )

        # Suporte a valor legado: se for int (indice do sistema antigo),
        # converte para string (chave)
        if isinstance(last_mode, int):
            mode_map_reverse = {
                0: "remove", 1: "restore", 2: "zip", 3: "unzip",
            }
            converted = mode_map_reverse.get(last_mode, "remove")
            self.logger.info(
                f"Valor legado de modo convertido: "
                f"indice {last_mode} -> chave '{converted}'",
                code="LEGACY_MODE_CONVERTED",
            )
            last_mode = converted

        self.mode_selector.set_selected_key(str(last_mode))
        self.logger.debug(
            f"Modo selecionado apos load: "
            f"{self.mode_selector.get_selected_key()}",
            code="LOAD_PREFS_DONE",
        )

    def _save_prefs(self):
        self.logger.debug("Salvando preferencias")

        self.preferences["last_mode"] = self.mode_selector.get_selected_key()
        self.preferences["window_width"] = self.width()
        self.preferences["window_height"] = self.height()

        self.logger.debug(
            f"Salvando: last_mode='{self.preferences['last_mode']}', "
            f"window=({self.preferences['window_width']}"
            f"x{self.preferences['window_height']})",
            code="SAVE_PREFS",
        )

        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
        self.logger.debug(
            "Preferencias salvas com sucesso", code="SAVE_PREFS_DONE"
        )

    def execute_tool(self):
        self.logger.info("Iniciando processamento: PathExtension")

        # Obtem selector e layer via metodo auxiliar
        _sel, layer = self._obter_layer_do_selector()
        self.logger.info(
            f"execute_tool: selector={_sel is not None}, "
            f"layer={layer.name() if layer else None}",
            code="EXECUTE_TOOL_ITEM",
        )

        if not layer or not layer.isValid():
            self.logger.warning(
                "Nenhuma camada vetorial valida selecionada",
                code="NO_LAYER",
            )
            return

        attribute = self.attr_selector.get_selected_key("path_field")
        if not attribute:
            self.logger.warning(
                "Nenhum atributo selecionado",
                code="NO_ATTRIBUTE",
            )
            return

        mode_key = self.mode_selector.get_selected_key()
        if not mode_key:
            self.logger.warning(
                "Nenhum modo selecionado",
                code="NO_MODE",
            )
            return

        self.logger.info(
            f"Parametros: layer='{layer.name()}', "
            f"attribute='{attribute}', mode='{mode_key}'",
            code="EXECUTE_PARAMS",
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