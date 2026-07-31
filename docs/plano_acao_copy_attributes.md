# 🎯 PLANO DE AÇÃO: Migração CopyAttributesPlugin para Novo Sistema de Widgets

**Objetivo:** Migrar `CopyAttributesPlugin` do sistema antigo (`WidgetFactory`) para o novo sistema (`resources/new_widgets/`), seguindo o contrato do plano de eliminação da WidgetFactory. Criar novo widget específico `GridAttributeSelector` para seleção de atributos com checkboxes.

**Plugin:** `plugins/CopyAttributesPlugin.py`
**Data:** 2026-07-31
**Versão:** 1.0.0
**Status:** ⬜ Pendente

---

## 1. ANÁLISE DO PLUGIN ATUAL

### 1.1 Widgets Usados via Factory (ANTIGO)

| Widget Factory | Parâmetros | Uso no Plugin |
|----------------|-----------|---------------|
| `create_layer_input()` | `label_text=STR.TARGET_LAYER`, `filters=[VectorLayer]` | Camada de destino |
| `create_layer_input()` | `label_text=STR.SOURCE_LAYER`, `filters=[VectorLayer]` | Camada de origem (com `layerChanged.connect(self._populate_fields)`) |
| `create_attribute_selector()` | `title=STR.SOURCE_LAYER_ATTRIBUTES` | Seletor de atributos com checkboxes + botões Selecionar/Remover/Inverter |
| `create_bottom_action_buttons()` | `run_callback=self.execute_tool`, `close_callback=self.close`, `info_callback=self.show_info_dialog` | Botões de ação |

### 1.2 Widgets Novo Sistema (DESTINO)

| Widget Novo | Substitui | Observações |
|-------------|-----------|-------------|
| `GridComplexSelector` (2x) | `create_layer_input()` (2x) | `allow_layer=True`, `layer_filters=VectorLayer`, `allow_file=False`, `allow_folder=False`. Source layer registra `set_on_changed()` |
| `GridAttributeSelector` (NOVO) | `create_attribute_selector()` | Widget específico com checkboxes 1 coluna + checkbox "usar todos" + GridModernButtons (selecionar/remover/inverter). Estilo próprio via AppStyles |
| `GridExecutionButtons` | `create_bottom_action_buttons()` | Botões modernos com glow/gradiente |
| `SeparatorWidget` | Separadores implícitos | Entre widgets no layout |

### 1.3 Arquitetura do Novo Widget: GridAttributeSelector

O `GridAttributeSelector` é um widget **específico** (não tem versão simple/grid separada — fica na raiz de `new_widgets/`), que encapsula:

```
GridAttributeSelector (QWidget)
├── Título (QGroupBox ou QLabel negrito)
├── Checkbox "Usar todos os atributos" (SimpleCheckbox)
│   └── Quando marcado: desabilita lista + botões de controle
├── Lista de atributos com checkboxes (GridCheckbox, 1 coluna)
│   └── Populado dinamicamente por set_fields()
├── GridModernButtons
│   ├── Selecionar (select_all)
│   ├── Remover (deselect_all)
│   └── Inverter (invert_selection)
└── _specific_style() — estilo próprio importando AppStyles
```

**API Pública:**
| Método | Descrição |
|--------|-----------|
| `set_fields(field_names: list[str])` | Popula checkboxes com nomes dos campos |
| `get_selected_fields()` → `list[str]` | Retorna campos selecionados (None se "usar todos") |
| `use_all_fields()` → `bool` | Retorna True se "usar todos" está marcado |
| `set_checked_all(checked: bool)` | Marca/desmarca "usar todos" |
| `get_all_states()` → `dict[str, bool]` | Retorna todos os estados |

### 1.4 Lógica do Plugin (Métodos Relevantes)

| Método | Descrição | Impacto na Migração |
|--------|-----------|---------------------|
| `_build_ui()` | Constrói interface com WidgetFactory | **REESCREVER** — usar GridComplexSelector + GridAttributeSelector + GridExecutionButtons |
| `_populate_fields()` | Atualiza lista de atributos quando camada origem muda | **CRÍTICO** — usar `set_on_changed()` do GridComplexSelector |
| `_load_prefs()` | Carrega `chk_all` | API compatível: `set_checked_all()` |
| `_save_prefs()` | Salva `chk_all`, `window_width`, `window_height` | API compatível: `use_all_fields()` + `get_all_states()` |
| `execute_tool()` | Obtém source/target layers + fields e executa | Usar `get_current_item()` do GridComplexSelector |

---

## 2. MUDANÇAS NECESSÁRIAS

### 2.1 NOVO Widget: GridAttributeSelector

**Arquivo:** `resources/new_widgets/GridAttributeSelector.py`

Widget específico para seleção de atributos com checkboxes, estilo próprio importando AppStyles.

```python
# -*- coding: utf-8 -*-
"""
GridAttributeSelector — Widget específico para seleção de atributos.
========================================================================
Widget com:
- Título do grupo
- Checkbox "Usar todos os atributos"
- Grid de checkboxes (1 coluna) para cada campo
- GridModernButtons: selecionar, remover, inverter
- Estilo próprio via _specific_style() + AppStyles

Uso em plugins:
    attr_selector = GridAttributeSelector(
        title="Atributos da Camada de Origem",
        parent=self,
    )
    attr_selector.set_fields(["campo1", "campo2", "campo3"])
    attr_selector.use_all_fields()  # True/False
    attr_selector.get_selected_fields()  # ["campo1", "campo3"]
"""

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QGroupBox
from ..styles.AppStyles import AppStyles
from .simple.SimpleCheckbox import SimpleCheckbox
from .grid.GridCheckbox import GridCheckbox
from .grid.GridModernButtons import GridModernButtons
from .SeparatorWidget import SeparatorWidget


class GridAttributeSelector(QWidget):
    """
    Widget específico para seleção de atributos com checkboxes.
    
    Parâmetros
    ----------
    title : str, optional
        Título do grupo (QGroupBox).
    check_all_text : str, optional
        Texto do checkbox "Usar todos os atributos".
    parent : QWidget, optional
        Widget pai.
    
    Autoconfiguração
    ----------------
    - AppStyles: métodos globais
    - _specific_style(): estilo específico com tokens do tema
    """

    def __init__(
        self,
        title: str = "",
        check_all_text: str = "Usar todos os atributos",
        parent=None,
    ):
        super().__init__(parent)
        self._title = title
        self._check_all_text = check_all_text
        
        # Checkbox "Usar todos os atributos"
        self._chk_all = None
        
        # Grid de checkboxes dos atributos (1 coluna)
        self._attr_grid = None
        
        # Botões de controle
        self._control_buttons = None
        
        # Estados internos
        self._field_names: list[str] = []
        
        try:
            self._build_ui()
            self._apply_styles()
        except Exception as error:
            # Logger opcional
            pass

    # ══════════════════════════════════════════════════════════════
    # API Pública
    # ══════════════════════════════════════════════════════════════

    def set_fields(self, field_names: list[str]):
        """
        Popula checkboxes com nomes dos campos.
        
        Parameters
        ----------
        field_names : list[str]
            Lista de nomes de campos da camada.
        """
        self._field_names = list(field_names)
        
        # Reconstrói grid de checkboxes com novos campos
        self._rebuild_attr_grid()

    def get_selected_fields(self):
        """
        Retorna campos selecionados.
        
        Returns
        -------
        list[str] or None
            None se "usar todos" estiver marcado.
            Lista de nomes se seleção manual.
        """
        if self._chk_all and self._chk_all.isChecked():
            return None
        
        if not self._attr_grid:
            return []
        
        return [
            name for name in self._field_names
            if self._attr_grid.is_checked(name)
        ]

    def use_all_fields(self) -> bool:
        """Retorna True se 'Usar todos os atributos' está marcado."""
        return self._chk_all.isChecked() if self._chk_all else False

    def set_checked_all(self, checked: bool):
        """Marca/desmarca 'Usar todos os atributos'."""
        if self._chk_all:
            self._chk_all.setChecked(checked)

    def get_all_states(self) -> dict[str, bool]:
        """Retorna dict {campo: bool} com estado de cada checkbox."""
        if not self._attr_grid:
            return {}
        return self._attr_grid.get_all_states()

    # ══════════════════════════════════════════════════════════════
    # Interno
    # ══════════════════════════════════════════════════════════════

    def _build_ui(self):
        """Monta layout do widget."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        theme = AppStyles._get_theme()

        # ── Container com título ────────────────────────────────
        if self._title:
            container = QGroupBox(self._title)
            container.setStyleSheet(
                "QGroupBox {"
                f"    background: transparent;"
                f"    border: none;"
                f"    margin-top: 16px;"
                f"    font-weight: bold;"
                f"    font-size: {theme.FONT_SIZE_SECTION_TITLE};"
                f"    color: {theme.COLOR_TEXT_PRIMARY};"
                f"    text-align: center;"
                f"    padding: 0px;"
                f"}}"
                f"QGroupBox::title {{"
                f"    subcontrol-origin: margin;"
                f"    subcontrol-position: top center;"
                f"    padding: 0 4px;"
                f"}}"
            )
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(6, 6, 6, 6)
            container_layout.setSpacing(theme.LAYOUT_VERTICAL_SPACING)
        else:
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(theme.LAYOUT_VERTICAL_SPACING)

        # ── Checkbox "Usar todos os atributos" ──────────────────
        self._chk_all = SimpleCheckbox(
            text=self._check_all_text,
            parent=self,
        )
        self._chk_all.toggled.connect(self._on_chk_all_toggled)
        container_layout.addWidget(self._chk_all)

        # ── Grid de checkboxes (1 coluna) — criado sob demanda ─
        self._attr_grid = GridCheckbox(
            config={},  # vazio, preenchido por set_fields()
            items_per_row=1,
            parent=self,
        )
        container_layout.addWidget(self._attr_grid)

        # ── Botões de controle (GridModernButtons) ──────────────
        self._control_buttons = GridModernButtons(
            config={
                "select_all": {
                    "label": "Selecionar",
                    "callback": self._on_select_all,
                    "primary": False,
                },
                "deselect_all": {
                    "label": "Remover",
                    "callback": self._on_deselect_all,
                    "primary": False,
                },
                "invert": {
                    "label": "Inverter",
                    "callback": self._on_invert_selection,
                    "primary": False,
                },
            },
            alignment="justify",
            separator_top=True,
            separator_bottom=False,
            parent=self,
        )
        container_layout.addWidget(self._control_buttons)

        outer.addWidget(container)

    def _rebuild_attr_grid(self):
        """Reconstrói grid de checkboxes com campos atuais."""
        if not self._attr_grid:
            return

        config = {}
        for name in self._field_names:
            config[name] = {
                "label": name,
                "default": True,  # Todos marcados por padrão
            }

        # Remove layout antigo e recria
        # GridCheckbox não tem método para reconfigurar, então
        # substituímos o widget inteiro
        parent_layout = self._attr_grid.parent().layout()
        if parent_layout:
            idx = parent_layout.indexOf(self._attr_grid)
            if idx >= 0:
                parent_layout.removeWidget(self._attr_grid)
                self._attr_grid.deleteLater()

        self._attr_grid = GridCheckbox(
            config=config,
            items_per_row=1,
            parent=self,
        )

        # Reinsere na mesma posição (antes dos botões)
        if parent_layout:
            # Insere antes do índice do _control_buttons
            btn_idx = parent_layout.indexOf(self._control_buttons)
            if btn_idx >= 0:
                parent_layout.insertWidget(btn_idx, self._attr_grid)
            else:
                parent_layout.addWidget(self._attr_grid)

        # Aplica estado do "usar todos"
        if self._chk_all and self._chk_all.isChecked():
            self._attr_grid.setEnabled(False)
            self._control_buttons.setEnabled(False)

    def _on_chk_all_toggled(self, checked: bool):
        """
        Quando 'Usar todos os atributos' está ativo,
        desabilita grid de checkboxes e botões de controle.
        """
        if self._attr_grid:
            self._attr_grid.setEnabled(not checked)
        if self._control_buttons:
            self._control_buttons.setEnabled(not checked)

    def _on_select_all(self):
        """Seleciona todos os atributos."""
        if self._attr_grid:
            self._attr_grid.select_all()

    def _on_deselect_all(self):
        """Remove seleção de todos os atributos."""
        if self._attr_grid:
            self._attr_grid.deselect_all()

    def _on_invert_selection(self):
        """Inverte seleção dos atributos."""
        if self._attr_grid:
            self._attr_grid.invert_selection()

    # ══════════════════════════════════════════════════════════════
    # Estilos
    # ══════════════════════════════════════════════════════════════

    def _apply_styles(self):
        """Aplica estilos globais + específico."""
        combined = self._get_global_style() + self._specific_style()
        self.setStyleSheet(combined)

    def _get_global_style(self) -> str:
        """Estilos globais via AppStyles."""
        return (
            AppStyles.label()
            + AppStyles.checkbox()
            + AppStyles.button()
        )

    def _specific_style(self) -> str:
        """
        Estilo específico do GridAttributeSelector.
        Usa tokens do tema com nomes descritivos.

        Estiliza:
        - Checkbox "Usar todos os atributos" com destaque visual
        - Container do grupo de atributos
        """
        theme = AppStyles._get_theme()
        return (
            # Checkbox "Usar todos" com destaque
            f"QCheckBox#chk_all_attributes {{"
            f"    font-weight: bold;"
            f"    font-size: {theme.FONT_SIZE_CHECKBOX_BOLD};"
            f"    color: {theme.COLOR_TEXT_ACCENT};"
            f"    padding: {theme.PADDING_CHECKBOX_BOLD};"
            f"}}"
            # Grid de checkboxes com padding
            f"QGroupBox#attr_group {{"
            f"    background: {theme.COLOR_PANEL_BACKGROUND};"
            f"    border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};"
            f"    border-radius: {theme.BORDER_RADIUS_PANEL};"
            f"    padding: {theme.PADDING_PANEL};"
            f"}}"
        )
```

### 2.2 GridComplexSelector — API `get_current_item()` JÁ EXISTE

O `GridComplexSelector` já possui o método `get_current_item(key)` adicionado na migração do PathExtensionPlugin. O plugin usará este método para obter `(path, layer_or_none)`.

**Nenhuma mudança adicional no GridComplexSelector para este plugin.**

### 2.3 GridComplexSelector — API `set_on_changed()` JÁ EXISTE

O `GridComplexSelector` já possui o método `set_on_changed(label, callback)` que registra um callback para quando um selector específico mudar. O plugin usará este método para registrar `_populate_fields` no selector de origem.

**Nenhuma mudança adicional no GridComplexSelector para callbacks.**

---

## 3. ESTRATÉGIA DE MIGRAÇÃO

### 3.1 Passo 1: Criar GridAttributeSelector

**Arquivo:** `resources/new_widgets/GridAttributeSelector.py`

Widget específico conforme descrito na seção 2.1.

### 3.2 Passo 2: Migrar CopyAttributesPlugin

**Arquivo:** `plugins/CopyAttributesPlugin.py`

#### 3.2.1 Novos Imports

```python
# NOVOS IMPORTS (substituem WidgetFactory)
from ..resources.new_widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.new_widgets.GridAttributeSelector import GridAttributeSelector
from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.new_widgets.SeparatorWidget import SeparatorWidget

# IMPORTS ANTIGOS QUE PERMANECEM
from qgis.core import QgsVectorLayer, QgsMapLayerProxyModel
from ..utils.ToolKeys import ToolKey
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.Preferences import Preferences
from ..utils.vector.VectorLayerAttributes import VectorLayerAttributes
from ..plugins.BasePlugin import BasePluginMTL
from ..i18n.TranslationManager import STR

# IMPORTS QUE SERÃO REMOVIDOS (WidgetFactory)
# from ..core.ui.WidgetFactory import WidgetFactory  ← REMOVER
```

#### 3.2.2 `_build_ui()` Migrado

```python
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
        separator_bottom=True,
        parent=self,
    )
    self.logger.info("GridComplexSelector criado com 2 seletores: target e source")

    # Registra callback para quando a camada de origem mudar
    self.layer_selector.set_on_changed(
        "source_layer", self._populate_fields
    )
    self.logger.debug("Callback _populate_fields registrado no source_layer")

    self.layout.addWidget(self.layer_selector)

    # ── Separador ──────────────────────────────────────────────────
    self.layout.addWidget(SeparatorWidget())

    # ── Attribute Selector (GridAttributeSelector) ─────────────────
    self.logger.debug("Criando GridAttributeSelector")
    self.attr_selector = GridAttributeSelector(
        title=STR.SOURCE_LAYER_ATTRIBUTES,
        check_all_text=STR.USE_ALL_ATTRIBUTES,
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
    self.logger.info("GridExecutionButtons criado com botao Executar + Fechar + Info")
    self.layout.add_execution_buttons(self.action_buttons)

    self.logger.info("Interface da ferramenta construida com sucesso")

    # Popula campos se já houver camada selecionada
    self._populate_fields([])
```

#### 3.2.3 `_populate_fields()` Migrado

```python
def _populate_fields(self, paths: list[str] = None):
    """
    Atualiza lista de atributos quando a camada de origem muda.
    
    Obtém (path, layer) via get_current_item("source_layer").
    Se layer for válido, extrai campos e popula o GridAttributeSelector.
    Se layer for None, limpa a lista de atributos.
    """
    self.logger.info(
        "_populate_fields chamado",
        code="POPULATE_FIELDS",
    )

    # Obtém (path, layer) via get_current_item
    path, layer = self.layer_selector.get_current_item("source_layer")
    self.logger.info(
        f"get_current_item: path='{path}', "
        f"layer={layer.name() if layer else None}",
        code="GET_CURRENT_ITEM",
    )

    if isinstance(layer, QgsVectorLayer) and layer.isValid():
        # Modo camada válida: extrai campos
        field_names = [f.name() for f in layer.fields()]
        self.logger.info(
            f"Camada '{layer.name()}' valida, "
            f"{len(field_names)} campos encontrados",
            code="LAYER_FIELDS",
        )
        self.logger.debug(f"Campos: {field_names}")

        self.attr_selector.set_fields(field_names)
        self.logger.info(
            f"GridAttributeSelector populado com {len(field_names)} campos",
            code="ATTR_SELECTOR_POPULATED",
        )
    else:
        # Modo inválido: limpa atributos
        self.logger.info(
            "Camada de origem invalida ou None, limpando atributos",
            code="CLEAR_FIELDS",
        )
        self.attr_selector.set_fields([])

    self.logger.info(
        "_populate_fields finalizado",
        code="POPULATE_FIELDS_END",
    )
```

#### 3.2.4 `_load_prefs()` Migrado

```python
def _load_prefs(self):
    self.logger.debug("Carregando preferencias")
    
    chk_all = self.preferences.get("chk_all", False)
    self.logger.debug(f"Valor carregado de chk_all: {chk_all}")
    
    self.attr_selector.set_checked_all(chk_all)
    self.logger.debug(
        f"chk_all aplicado: {self.attr_selector.use_all_fields()}",
        code="LOAD_PREFS_DONE",
    )
```

#### 3.2.5 `_save_prefs()` Migrado

```python
def _save_prefs(self):
    self.logger.debug("Salvando preferencias")
    
    self.preferences["chk_all"] = self.attr_selector.use_all_fields()
    self.preferences["window_width"] = self.width()
    self.preferences["window_height"] = self.height()
    
    self.logger.debug(
        f"Salvando: chk_all={self.preferences['chk_all']}, "
        f"window=({self.preferences['window_width']}x{self.preferences['window_height']})",
        code="SAVE_PREFS",
    )
    
    Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
    self.logger.debug("Preferencias salvas com sucesso", code="SAVE_PREFS_DONE")
```

#### 3.2.6 `execute_tool()` Migrado

```python
def execute_tool(self):
    self.logger.info("Iniciando copia de atributos")

    # Obtém (path, layer) via get_current_item
    src_path, source = self.layer_selector.get_current_item("source_layer")
    tgt_path, target = self.layer_selector.get_current_item("target_layer")
    
    self.logger.info(
        f"execute_tool: source={source.name() if source else None}, "
        f"target={target.name() if target else None}",
        code="EXECUTE_TOOL_LAYERS",
    )

    if not isinstance(source, QgsVectorLayer):
        QgisMessageUtil.bar_warning(self.iface, STR.INVALID_SOURCE_LAYER)
        self.logger.warning(
            "Camada de origem invalida",
            code="INVALID_SOURCE",
        )
        return

    if not isinstance(target, QgsVectorLayer):
        QgisMessageUtil.bar_warning(self.iface, STR.INVALID_TARGET_LAYER)
        self.logger.warning(
            "Camada de destino invalida",
            code="INVALID_TARGET",
        )
        return

    from ..utils.ProjectUtils import ProjectUtils

    if not ProjectUtils.ensure_editable(target, self.logger):
        QgisMessageUtil.bar_critical(self.iface, STR.LAYER_MUST_BE_EDITABLE)
        self.logger.warning(
            "Camada de destino nao editavel",
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
            QgisMessageUtil.bar_warning(self.iface, STR.NO_ATTRIBUTE_SELECTED)
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
        return QgisMessageUtil.ask_field_conflict(self.iface, field_name)

    self.logger.info(
        f"Iniciando copia: source='{source.name()}', target='{target.name()}', "
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
        QgisMessageUtil.bar_success(self.iface, STR.ATTRIBUTES_COPIED_SUCCESS)
        self.logger.info(
            "Copia de atributos finalizada com sucesso",
            code="COPY_SUCCESS",
        )
    else:
        self.logger.error(
            "Falha na copia de atributos",
            code="COPY_FAILED",
        )
```

---

## 4. DIAGRAMA DE FLUXO

```
Plugin._build_ui()
  ├── Cria GridComplexSelector (2 items: target_layer, source_layer)
  │   ├── target_layer: allow_layer=True, VectorLayer, mode_type=input
  │   └── source_layer: allow_layer=True, VectorLayer, mode_type=input
  │       └── Registra callback: set_on_changed("source_layer", self._populate_fields)
  ├── Cria GridAttributeSelector
  │   ├── Título: "Atributos da Camada de Origem"
  │   ├── Checkbox "Usar todos os atributos"
  │   ├── Grid de checkboxes (1 coluna)
  │   └── GridModernButtons: Selecionar, Remover, Inverter
  └── Cria GridExecutionButtons (Executar + Fechar + Info)

Usuário seleciona camada de origem no QgsMapLayerComboBox
  └── ComplexSelector._on_combo_layer_changed()
      └── ComplexSelector._emit_path_change()
          └── on_path_change(paths)  ← callback nativo
              └── GridComplexSelector wrapper → plugin._populate_fields(paths)
                  ├── Log: "POPULATE_FIELDS"
                  ├── layer_selector.get_current_item("source_layer")
                  │   ├── Log: "GET_CURRENT_ITEM" com path e layer
                  │   └── Retorna (path, layer_or_none)
                  ├── SE layer for QgsVectorLayer válido:
                  │   ├── Log: "LAYER_FIELDS" com qtd de campos
                  │   ├── Extrai field_names da camada
                  │   ├── attr_selector.set_fields(field_names)
                  │   └── Log: "ATTR_SELECTOR_POPULATED"
                  └── SENÃO (inválido):
                      ├── Log: "CLEAR_FIELDS"
                      └── attr_selector.set_fields([])

Usuário marca/desmarca "Usar todos os atributos"
  └── GridAttributeSelector._on_chk_all_toggled(checked)
      ├── Desabilita/Habilita grid de checkboxes
      └── Desabilita/Habilita botões de controle

Usuário clica "Selecionar"
  └── GridAttributeSelector._on_select_all()
      └── attr_grid.select_all()

Usuário clica "Remover"
  └── GridAttributeSelector._on_deselect_all()
      └── attr_grid.deselect_all()

Usuário clica "Inverter"
  └── GridAttributeSelector._on_invert_selection()
      └── attr_grid.invert_selection()

Usuário clica "Executar"
  └── plugin.execute_tool()
      ├── layer_selector.get_current_item("source_layer")
      ├── layer_selector.get_current_item("target_layer")
      ├── Log: "EXECUTE_TOOL_LAYERS"
      ├── Valida source e target
      ├── SE use_all_fields(): Log "USE_ALL_FIELDS"
      │   └── fields = None (todos)
      ├── SENÃO: get_selected_fields()
      │   ├── Log: "SELECTED_FIELDS"
      │   └── Se vazio: Log "NO_FIELDS_SELECTED", aborta
      ├── Log: "COPY_START" com parâmetros
      ├── VectorLayerAttributes.copy_attributes()
      └── Log: "COPY_SUCCESS" ou "COPY_FAILED"
```

---

## 5. ARQUIVOS AFETADOS

| Arquivo | Tipo de Mudança | Risco |
|---------|----------------|-------|
| `resources/new_widgets/GridAttributeSelector.py` | **CRIAR** — widget específico novo | Baixo |
| `plugins/CopyAttributesPlugin.py` | Reescrever `_build_ui()`, `_populate_fields()`, `execute_tool()`, `_load_prefs()`, `_save_prefs()` | Médio |
| `docs/ia/changelog.txt` | Adicionar entrada de versão | Baixo |

---

## 6. LOGS ADICIONADOS PARA VALIDAÇÃO

| Local | Código | Mensagem |
|-------|--------|----------|
| `_populate_fields()` | `POPULATE_FIELDS` | _populate_fields chamado |
| `_populate_fields()` | `GET_CURRENT_ITEM` | Path + layer obtidos |
| `_populate_fields()` | `LAYER_FIELDS` | Qtd de campos encontrados |
| `_populate_fields()` | `ATTR_SELECTOR_POPULATED` | GridAttributeSelector populado |
| `_populate_fields()` | `CLEAR_FIELDS` | Limpando atributos (camada inválida) |
| `_populate_fields()` | `POPULATE_FIELDS_END` | Finalizado |
| `execute_tool()` | `EXECUTE_TOOL_LAYERS` | Source + target layers |
| `execute_tool()` | `INVALID_SOURCE` | Camada de origem inválida |
| `execute_tool()` | `INVALID_TARGET` | Camada de destino inválida |
| `execute_tool()` | `TARGET_NOT_EDITABLE` | Camada de destino não editável |
| `execute_tool()` | `SELECTED_FIELDS` | Campos selecionados manualmente |
| `execute_tool()` | `NO_FIELDS_SELECTED` | Nenhum campo selecionado |
| `execute_tool()` | `USE_ALL_FIELDS` | Usando todos os atributos |
| `execute_tool()` | `COPY_START` | Iniciando cópia com parâmetros |
| `execute_tool()` | `COPY_SUCCESS` | Cópia finalizada com sucesso |
| `execute_tool()` | `COPY_FAILED` | Falha na cópia |
| `_load_prefs()` | `LOAD_PREFS_DONE` | chk_all aplicado |
| `_save_prefs()` | `SAVE_PREFS` | Valores salvos |
| `_save_prefs()` | `SAVE_PREFS_DONE` | Preferências salvas |

---

## 7. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| `GridAttributeSelector._rebuild_attr_grid()` remover/inserir widget quebrar layout | Média | Médio | Testar com diferentes quantidades de campos |
| `set_on_changed()` não disparar na primeira seleção | Média | Médio | Chamar `_populate_fields([])` no final de `_build_ui()` |
| Plugin perder referência do dialog | Baixa | Alto | Manter `return dlg` no `run()` |
| `GridExecutionButtons` não ter `info_callback` separado | Baixa | Baixo | Usar `enable_info=True` + `tool_key` |
| Preferências legadas (chk_all) carregarem corretamente | Baixa | Baixo | Compatibilidade mantida via `set_checked_all()` |

---

## 8. CHECKLIST DE MIGRAÇÃO

### Pré-migração
- [ ] Ler `docs/skills/SKILL_WIDGETS2.md` (contrato do novo sistema)
- [ ] Ler `docs/skills/PLUGIN_CONTRACT.md` (12 regras críticas)
- [ ] Ler `docs/plano_eliminacao_widgetfactory.md` (estratégia geral)
- [ ] Analisar `GridComplexSelector.py` atual (API get_current_item + set_on_changed)
- [ ] Analisar `GridCheckbox.py` atual (API select_all, deselect_all, invert_selection)
- [ ] Analisar `GridModernButtons.py` atual (API config dict)
- [ ] Analisar `GridExecutionButtons.py` atual (API config dict)

### Criação do GridAttributeSelector
- [ ] Criar `resources/new_widgets/GridAttributeSelector.py`
- [ ] Implementar `__init__` com título, check_all_text, parent
- [ ] Implementar `_build_ui()` com container, chk_all, GridCheckbox, GridModernButtons
- [ ] Implementar `_rebuild_attr_grid()` para reconstruir checkboxes dinamicamente
- [ ] Implementar `set_fields(field_names)` — API pública
- [ ] Implementar `get_selected_fields()` — retorna lista ou None
- [ ] Implementar `use_all_fields()` — retorna bool
- [ ] Implementar `set_checked_all(checked)` — API pública
- [ ] Implementar `get_all_states()` — API pública
- [ ] Implementar `_on_chk_all_toggled()` — desabilita/habilita grid + botões
- [ ] Implementar `_on_select_all()`, `_on_deselect_all()`, `_on_invert_selection()`
- [ ] Implementar `_apply_styles()` com `_get_global_style()` + `_specific_style()`
- [ ] Implementar `_specific_style()` com tokens do tema (AppStyles)

### Migração do CopyAttributesPlugin
- [ ] Substituir imports: remover `WidgetFactory`, adicionar `GridComplexSelector`, `GridAttributeSelector`, `GridExecutionButtons`, `SeparatorWidget`
- [ ] Substituir `create_layer_input()` (2x) por `GridComplexSelector` com 2 items
- [ ] Substituir `create_attribute_selector()` por `GridAttributeSelector`
- [ ] Substituir `create_bottom_action_buttons()` por `GridExecutionButtons`
- [ ] Registrar callback via `set_on_changed("source_layer", self._populate_fields)`
- [ ] Adaptar `_populate_fields()` para usar `get_current_item()` + logs
- [ ] Adaptar `execute_tool()` para usar `get_current_item()` + logs
- [ ] Adaptar `_load_prefs()` para usar `set_checked_all()`
- [ ] Adaptar `_save_prefs()` para usar `use_all_fields()` + `get_all_states()`
- [ ] Remover imports não utilizados
- [ ] Adicionar `SeparatorWidget()` entre widgets no layout

### Pós-migração
- [ ] Plugin não importa de `core/ui/WidgetFactory`
- [ ] Plugin não importa de `resources/styles/`
- [ ] Plugin não chama `setStyleSheet()`
- [ ] Atualizar `docs/ia/changelog.txt`
- [ ] Testar fluxo completo: selecionar source → ver atributos → selecionar target → executar
- [ ] Testar "Usar todos os atributos" checkbox (desabilita/habilita grid)
- [ ] Testar botões Selecionar/Remover/Inverter
- [ ] Testar carregamento de preferências (chk_all)
- [ ] Testar salvamento de preferências
- [ ] Verificar logs no console QGIS para validação

---

## 9. CONTRATO DO PLUGIN (Verificação)

| Regra | Status | Verificação |
|-------|--------|-------------|
| #1 UI via WidgetFactory (ou new_widgets) | ✅ | Usa `resources/new_widgets/` |
| #2 Logging via LogUtils com ToolKey | ✅ | Herda de `BasePluginMTL` |
| #3 Strings via STR | ✅ | Já usa `STR.*` |
| #4 ToolKey é enum | ✅ | `ToolKey.COPY_ATTRIBUTES` |
| #5 Estilos via WidgetFactory + Styles.py | ✅ | Widgets se autoconfiguram com AppStyles + _specific_style() |
| #6 Exceções logadas com logger.exception | ✅ | Herda tratamento |
| #7 Métodos estáticos recebem tool_key | N/A | Não tem métodos estáticos |
| #8 Configurações via Preferences | ✅ | `_load_prefs()` / `_save_prefs()` |
| #9 Widgets customizados em resources/ | ✅ | `GridAttributeSelector` em `resources/new_widgets/` |
| #10 Help via InstructionsManager | ✅ | `enable_info=True` no GridExecutionButtons |
| #11 Logs em pt_BR | ✅ | Herda padrão |
| #17 Registro no ToolRegistry | ✅ | Já registrado |

---

## 10. CONSIDERAÇÕES DE DESIGN

### 10.1 GridAttributeSelector vs Reutilizar GridCheckbox Direto

**Opção A (escolhida):** Criar `GridAttributeSelector` como widget específico na raiz.
- Vantagem: Encapsula lógica de "usar todos os atributos" + botões de controle + layout
- Vantagem: Estilo próprio via `_specific_style()` com tokens do tema
- Vantagem: API limpa e específica para o caso de uso
- Desvantagem: Um arquivo a mais para manter

**Opção B (rejeitada):** Usar `GridCheckbox` diretamente no plugin.
- Desvantagem: Plugin precisaria gerenciar "usar todos" + botões manualmente
- Desvantagem: Lógica de seleção/desmarcar/inverter ficaria no plugin
- Desvantagem: Violaria contrato de plugin não ter lógica de UI complexa

### 10.2 Atualização Dinâmica do Grid

O `GridAttributeSelector` usa `_rebuild_attr_grid()` para substituir o `GridCheckbox` interno quando `set_fields()` é chamado. Isso é necessário porque o `GridCheckbox` atual não suporta reconfiguração dinâmica do config dict.

Alternativa futura: Adicionar método `set_config()` ao `GridCheckbox` para evitar reconstrução.

---

## 11. HISTÓRICO DE MUDANÇAS

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-31 | 1.0.0 | Criação inicial do plano |