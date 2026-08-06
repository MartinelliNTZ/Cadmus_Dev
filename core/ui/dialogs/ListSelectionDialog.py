# -*- coding: utf-8 -*-
"""
ListSelectionDialog — Diálogo genérico para seleção de itens com checkboxes.
=======================================================================
Substitui o LayoutsSelectionDialog específico.

Recebe um dict de itens, exibe checkboxes com controles
(Selecionar Todos / Desselecionar / Inverter) e retorna
as chaves selecionadas.

Uso em plugins:
    items = {
        "key1": {"label": "Item 1", "default": True},
        "key2": {"label": "Item 2", "default": False},
    }
    dlg = ListSelectionDialog(
        items=items,
        title="Selecionar Itens",
        hint="Marque os itens desejados",
        tool_key=ToolKey.MY_PLUGIN,
        icon_path="cadmus_icon.ico",
        parent=self,
    )
    if dlg.exec():
        selected = dlg.get_selected_items()
"""

from ....plugins.BaseDialog import BaseDialog
from ....resources.widgets.grid.GridCheckbox import GridCheckbox
from ....resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ....i18n.TranslationManager import STR
from ....core.config.LogUtils import LogUtils


class ListSelectionDialog(BaseDialog):
    """
    Diálogo modal genérico para selecionar itens de uma lista.

    O plugin constrói o dict de itens e passa ao construtor.
    O diálogo exibe checkboxes com botões de controle
    (Selecionar Todos / Desselecionar / Inverter) e OK/Fechar.

    Parâmetros
    ----------
    items : dict
        Dict de itens: {key: {"label": str, "default": bool}}
        Onde key é o identificador único do item.
        "label" é o texto exibido no checkbox.
        "default" (True/False) indica se o item vem marcado.
    title : str
        Título do diálogo e da janela.
    hint : str, optional
        Texto do grupo de checkboxes (QGroupBox).
    tool_key : ToolKey
        ToolKey do plugin que abriu o diálogo (para logs rastreáveis).
    icon_path : str, optional
        Caminho do ícone (relativo a resources/icons/).
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        items=None,
        title="",
        hint="",
        tool_key=None,
        icon_path="cadmus_icon.ico",
        parent=None,
    ):
        super().__init__(parent)
        self.PLUGIN_NAME = title
        self._items = items or {}
        self._hint = hint
        self._icon_path = icon_path
        self._checkbox = None
        self._selected = set()

        self.logger = LogUtils(
            tool=tool_key,
            class_name="ListSelectionDialog",
        )

        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(400, 400)

        self._build_ui(
            title=title,
            icon_path=icon_path,
            enable_scroll=True,
            minimum_size=(500, 300),
        )
        self._build_inner_ui()

    def _build_inner_ui(self):
        """Constrói o conteúdo interno do diálogo dentro do MainLayout."""
        config = {}
        for key, item in self._items.items():
            config[key] = {
                "label": item.get("label", key),
                "default": item.get("default", True),
            }

        self._checkbox = GridCheckbox(
            config=config,
            title=self._hint,
            items_per_row=1,
            control_buttons_config={
                "select_all": {
                    "label": STR.SELECT_ALL,
                    "callback": lambda: self._checkbox.select_all(),
                },
                "deselect_all": {
                    "label": STR.DESELECT_ALL,
                    "callback": lambda: self._checkbox.deselect_all(),
                },
                "invert": {
                    "label": STR.INVERT_SELECTION,
                    "callback": lambda: self._checkbox.invert_selection(),
                },
            },
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self._checkbox)

        self._buttons = GridExecutionButtons(
            config={
                "ok": {
                    "label": STR.OK,
                    "description": "Confirma a seleção",
                    "callback": self._on_ok,
                    "is_run_button": True,
                },
            },
            enable_close_button=True,
            enable_config_button=False,
            enable_info=False,
            parent=self,
        )
        self.layout.add_execution_buttons(self._buttons)

    def _on_ok(self):
        """Confirma a seleção e fecha o diálogo."""
        self._selected = set(self._checkbox.get_checked_keys())
        self.accept()

    def get_selected_items(self):
        """
        Retorna a lista de chaves dos itens selecionados.

        Deve ser chamado após exec() retornar True.
        """
        return list(self._selected)