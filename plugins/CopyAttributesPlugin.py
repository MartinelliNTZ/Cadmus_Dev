# -*- coding: utf-8 -*-

from qgis.core import QgsVectorLayer, QgsMapLayerProxyModel

from ..utils.ToolKeys import ToolKey
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.Preferences import Preferences
from ..utils.vector.VectorLayerAttributes import VectorLayerAttributes
from .BasePlugin import BasePluginMTL
from ..i18n.TranslationManager import STR

# NOVOS WIDGETS (substituem WidgetFactory)
from ..resources.new_widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.new_widgets.GridAttributeSelector import GridAttributeSelector
from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.new_widgets.SeparatorWidget import SeparatorWidget


class CopyAttributes(BasePluginMTL):
    TOOL_KEY = ToolKey.COPY_ATTRIBUTES

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.init(ToolKey.COPY_ATTRIBUTES, "CopyAttributes")

    # =========================
    # UI
    # =========================
    def _build_ui(self, **kwargs):
        self.logger.debug("Inicializando PLUGIN CopyAttributes")
        super()._build_ui(
            title=STR.COPY_ATTRIBUTES_TITLE,
            icon_path="copy_attributes.ico",
            enable_scroll=True,
        )
        self.logger.info("Construindo interface da ferramenta")

        # ── Layer Selectors (GridComplexSelector) ──────────────────────
        self.logger.debug("Criando GridComplexSelector para camadas")
        self.layer_selector = GridComplexSelector(
            config={
                "target_layer": {
                    "label": STR.TARGET_LAYER,
                    "description": "Selecione a camada vetorial de destino",
                    "allow_layer": True,
                    "layer_filters": QgsMapLayerProxyModel.VectorLayer,
                    "allow_file": False,
                    "allow_folder": False,
                    "mode_type": "input",
                },
                "source_layer": {
                    "label": STR.SOURCE_LAYER,
                    "description": "Selecione a camada vetorial de origem",
                    "allow_layer": True,
                    "layer_filters": QgsMapLayerProxyModel.VectorLayer,
                    "allow_file": False,
                    "allow_folder": False,
                    "mode_type": "input",
                },
            },
            tool_key=self.TOOL_KEY,
            separator_bottom=False,
            parent=self,
        )
        self.logger.info(
            "GridComplexSelector criado com 2 items: "
            "target_layer e source_layer"
        )

        # Registra callback para quando a camada de origem mudar
        self.layer_selector.set_on_changed(
            "source_layer", self._populate_fields
        )
        self.logger.debug(
            "Callback _populate_fields registrado no source_layer"
        )

        self.layout.addWidget(self.layer_selector)

        # ── Separador ──────────────────────────────────────────────────
        self.layout.addWidget(SeparatorWidget())

        # ── Attribute Selector (GridAttributeSelector) ─────────────────
        self.logger.debug("Criando GridAttributeSelector")
        self.attr_selector = GridAttributeSelector(
            title=STR.SOURCE_LAYER_ATTRIBUTES,
            check_all_text=STR.USE_ALL_ATTRIBUTES,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.logger.info("GridAttributeSelector criado")
        self.layout.addWidget(self.attr_selector)

        # ── Separador ──────────────────────────────────────────────────
        self.layout.addWidget(SeparatorWidget())

        # ── Botões de Ação (GridExecutionButtons) ──────────────────────
        self.logger.debug("Criando GridExecutionButtons")
        self.action_buttons = GridExecutionButtons(
            config={
                "run": {
                    "label": "Executar",
                    "description": "Inicia a copia de atributos",
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

        # Popula campos se já houver camada selecionada
        self._populate_fields([])

    def _obter_layer_do_selector(self, key: str):
        """
        Obtém a camada atual do ComplexSelector interno do GridComplexSelector.

        Parameters
        ----------
        key : str
            Chave do selector no config dict ("target_layer" ou "source_layer").

        Returns
        -------
        tuple
            (selector, layer_or_none)
        """
        sel = self.layer_selector.get(key)
        if not sel:
            return (None, None)

        layer = None
        if sel.using_layer_combo:
            layer = sel.current_layer
        return (sel, layer)

    def _populate_fields(self, paths: list[str] = None):
        """
        Atualiza lista de atributos quando a camada de origem muda.

        Obtém a camada via get() no ComplexSelector interno.
        Se layer for QgsVectorLayer válido, extrai campos e popula
        o GridAttributeSelector. Se inválido, limpa a lista.
        """
        self.logger.info(
            "_populate_fields chamado", code="POPULATE_FIELDS"
        )

        _sel, layer = self._obter_layer_do_selector("source_layer")
        self.logger.info(
            f"layer={layer.name() if layer else None}",
            code="GET_SOURCE_LAYER",
        )

        if isinstance(layer, QgsVectorLayer) and layer.isValid():
            field_names = [f.name() for f in layer.fields()]
            self.logger.info(
                f"Camada '{layer.name()}' valida, "
                f"{len(field_names)} campos encontrados",
                code="LAYER_FIELDS",
            )
            self.logger.debug(f"Campos: {field_names}")

            self.attr_selector.set_fields(field_names)
            self.logger.info(
                f"GridAttributeSelector populado com "
                f"{len(field_names)} campos",
                code="ATTR_SELECTOR_POPULATED",
            )
        else:
            self.logger.info(
                "Camada de origem invalida, limpando atributos",
                code="CLEAR_FIELDS",
            )
            self.attr_selector.set_fields([])

        self.logger.info(
            "_populate_fields finalizado", code="POPULATE_FIELDS_END"
        )

    def _load_prefs(self):
        self.logger.debug("Carregando preferencias")

        chk_all = self.preferences.get("chk_all", False)
        self.logger.debug(f"Valor carregado de chk_all: {chk_all}")

        self.attr_selector.set_checked_all(chk_all)
        self.logger.debug(
            f"chk_all aplicado: {self.attr_selector.use_all_fields()}",
            code="LOAD_PREFS_DONE",
        )

    def _save_prefs(self):
        self.logger.debug("Salvando preferencias")

        self.preferences["chk_all"] = self.attr_selector.use_all_fields()
        self.preferences["window_width"] = self.width()
        self.preferences["window_height"] = self.height()

        self.logger.debug(
            f"Salvando: chk_all={self.preferences['chk_all']}, "
            f"window=({self.preferences['window_width']}"
            f"x{self.preferences['window_height']})",
            code="SAVE_PREFS",
        )

        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
        self.logger.debug(
            "Preferencias salvas com sucesso", code="SAVE_PREFS_DONE"
        )

    # =========================
    # CONTROLLER
    # =========================
    def execute_tool(self):
        self.logger.info("Iniciando copia de atributos")

        # Obtém camadas via get() nos ComplexSelectors internos
        _sel, source = self._obter_layer_do_selector("source_layer")
        _sel, target = self._obter_layer_do_selector("target_layer")

        self.logger.info(
            f"execute_tool: source={source.name() if source else None}, "
            f"target={target.name() if target else None}",
            code="EXECUTE_TOOL_LAYERS",
        )

        if not isinstance(source, QgsVectorLayer):
            QgisMessageUtil.bar_warning(self.iface, STR.INVALID_SOURCE_LAYER)
            self.logger.warning(
                "Camada de origem invalida", code="INVALID_SOURCE"
            )
            return

        if not isinstance(target, QgsVectorLayer):
            QgisMessageUtil.bar_warning(self.iface, STR.INVALID_TARGET_LAYER)
            self.logger.warning(
                "Camada de destino invalida", code="INVALID_TARGET"
            )
            return

        from ..utils.ProjectUtils import ProjectUtils

        # Pergunta ao usuario se deseja tornar a camada de destino editavel
        if not ProjectUtils.ask_and_make_editable(self.iface, target, self.logger):
            self.logger.info(
                "Operacao cancelada: usuario recusou editar a camada de destino",
                code="TARGET_NOT_EDITABLE",
            )
            return

        fields = None
        if not self.attr_selector.use_all_fields():
            fields = self.attr_selector.get_selected_fields()
            self.logger.debug(
                f"Campos selecionados manualmente: {fields}",
                code="SELECTED_FIELDS",
            )

            if not fields:
                QgisMessageUtil.bar_warning(
                    self.iface, STR.NO_ATTRIBUTE_SELECTED
                )
                self.logger.warning(
                    "Execucao abortada: nenhum atributo selecionado",
                    code="NO_FIELDS_SELECTED",
                )
                return
        else:
            self.logger.info(
                "Usando todos os atributos (chk_all=True)",
                code="USE_ALL_FIELDS",
            )

        def conflict_resolver(field_name):
            return QgisMessageUtil.ask_field_conflict(
                self.iface, field_name
            )

        self.logger.info(
            f"Iniciando copia: source='{source.name()}', "
            f"target='{target.name()}', "
            f"fields={'ALL' if fields is None else len(fields)}",
            code="COPY_START",
        )

        ok = VectorLayerAttributes.copy_attributes(
            target_layer=target,
            source_layer=source,
            field_names=fields,
            conflict_resolver=conflict_resolver,
        )

        if ok:
            QgisMessageUtil.bar_success(
                self.iface, STR.ATTRIBUTES_COPIED_SUCCESS
            )
            self.logger.info(
                "Copia de atributos finalizada com sucesso",
                code="COPY_SUCCESS",
            )
        else:
            self.logger.error(
                "Falha na copia de atributos", code="COPY_FAILED"
            )


def run(iface):
    dlg = CopyAttributes(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg