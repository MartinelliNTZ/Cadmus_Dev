# 🎯 PLANO DE AÇÃO: Migração PathExtensionPlugin para Novo Sistema de Widgets

**Objetivo:** Migrar `PathExtensionPlugin` do sistema antigo (`WidgetFactory`) para o novo sistema (`resources/widgets/`), seguindo o contrato do plano de eliminação da WidgetFactory.

**Plugin:** `plugins/PathExtensionPlugin.py`
**Data:** 2026-07-31
**Versão:** 2.0.0
**Status:** ⬜ Pendente

---

## 1. ANÁLISE DO PLUGIN ATUAL

### 1.1 Widgets Usados via Factory (ANTIGO)

| Widget Factory | Parâmetros | Uso no Plugin |
|----------------|-----------|---------------|
| `create_layer_input()` | `label_text=STR.INPUT_LAYER`, `filters=[VectorLayer]`, `allow_empty=False` | Seleção da camada vetorial de entrada |
| `create_dropdown_selector()` | `title=f"{STR.PATH}:"`, `options_dict={}`, `allow_empty=True`, `empty_text=STR.SELECT`, `separator_bottom=True` | Seletor de atributo (campos da camada) |
| `create_radio_button_grid()` | `items=[MODE_REMOVE, MODE_RESTORE, MODE_ZIP, MODE_UNZIP]`, `columns=2`, `checked_index=0` | Seletor de modo de operação |
| `create_bottom_action_buttons()` | `run_callback=self.execute_tool`, `close_callback=self.close`, `info_callback=self.show_info_dialog` | Botões de ação |

### 1.2 Widgets Novo Sistema (DESTINO)

| Widget Novo | Substitui | Observações |
|-------------|-----------|-------------|
| `GridComplexSelector` | `create_layer_input()` | Com `allow_layer=True`, `layer_filters=VectorLayer`, `folder=false`. Usa `set_on_changed()` para registrar callback |
| `GridComboBox` | `create_dropdown_selector()` | Vinculado ao layer selector via callback `_on_layer_changed` |
| `GridRadioButton` | `create_radio_button_grid()` | Mesma lógica, API moderna via dict config com chaves string |
| `GridExecutionButtons` | `create_bottom_action_buttons()` | Botões modernos com glow/gradiente |

### 1.3 Lógica do Plugin (Métodos Relevantes)

| Método | Descrição | Impacto na Migração |
|--------|-----------|---------------------|
| `_on_layer_changed()` | Atualiza options do dropdown de atributos quando a camada muda. Busca campo "path" como default. | **CRÍTICO** — registrado via `set_on_changed()` do `GridComplexSelector` |
| `_load_prefs()` | Carrega `last_mode` do radio button | API compatível: `set_selected_key()` |
| `_save_prefs()` | Salva `last_mode`, `window_width`, `window_height` | API compatível: `get_selected_key()` |
| `execute_tool()` | Obtém layer, attribute, mode e executa pipeline | Usa `get_current_item()` e `get_selected_key()` |
| `_run_async_pipeline()` | Cria pipeline com `PathExtensionStep` | Sem mudanças |

---

## 2. MUDANÇAS NECESSÁRIAS

### 2.1 GridComplexSelector — Adicionar Método `get_current_item(key)`

O `GridComplexSelector` atual **não expõe** um método para obter o item atual (path + layer) de um selector.

**O que precisa ser adicionado:**

```python
def get_current_item(self, key: str):
    """
    Retorna tupla (path, layer_or_none) para um selector.
    
    Parameters
    ----------
    key : str
        Chave do selector no config dict.
    
    Returns
    -------
    tuple
        (path, layer_or_none) onde:
        - path: str, caminho do arquivo/layer source
        - layer_or_none: QgsMapLayer ou None (se for path de arquivo fisico)
    """
    sel = self._selectors.get(key)
    if not sel:
        return ("", None)
    
    path = sel.path()  # sempre retorna o path, independente do modo
    layer = None
    if sel.using_layer_combo:
        layer = sel.current_layer  # property do ComplexSelector
    
    return (path, layer)
```

**Arquivo:** `resources/widgets/grid/GridComplexSelector.py`

### 2.2 GridComplexSelector — API `set_on_changed()` JÁ EXISTE

O `GridComplexSelector` **já possui** o método `set_on_changed(label, callback)` que registra um callback para quando um selector específico mudar. O plugin usará este método diretamente.

**Nenhuma mudança adicional no GridComplexSelector para callbacks.**

### 2.3 GridComboBox — API já Compatível

O `GridComboBox` já possui:
- ✅ `set_options(key, options)` — para atualizar options dinamicamente
- ✅ `set_selected_key(key, value)` — para definir seleção
- ✅ `get_selected_key(key)` — para obter seleção

**Nenhuma mudança necessária.**

### 2.4 GridRadioButton — API já Compatível

O `GridRadioButton` já possui:
- ✅ `get_selected_key()` / `set_selected_key(key)`
- ✅ `get_selected_index()` / `set_selected_index(index)`
- ✅ Suporte a `onchange` callback no config dict

**Nenhuma mudança necessária.**

### 2.5 GridExecutionButtons — API já Compatível

O `GridExecutionButtons` já possui:
- ✅ Config dict com `label`, `callback`, `description`, `is_run_button`
- ✅ `enable_close_button`, `enable_info`, `tool_key`

**Nenhuma mudança necessária.**

---

## 3. ESTRATÉGIA DE MIGRAÇÃO

### 3.1 Passo 1: Adicionar `get_current_item()` ao GridComplexSelector

**Arquivo:** `resources/widgets/grid/GridComplexSelector.py`

Adicionar método público após a seção de API Pública (após linha 600, antes de `get()`):

```python
# ══════════════════════════════════════════════════════════════════
# API Pública — Current Item
# ══════════════════════════════════════════════════════════════════

def get_current_item(self, key: str):
    """
    Retorna tupla (path, layer_or_none) para um selector.
    
    Parameters
    ----------
    key : str
        Chave do selector no config dict.
    
    Returns
    -------
    tuple
        (path, layer_or_none) onde:
        - path: str, caminho do arquivo/layer source
        - layer_or_none: QgsMapLayer ou None (se for path de arquivo fisico)
    """
    sel = self._selectors.get(key)
    if not sel:
        self._logger.info(
            f"get_current_item: selector '{key}' nao encontrado",
            code="GET_CURRENT_ITEM_NOT_FOUND",
        )
        return ("", None)
    
    path = sel.path()
    layer = None
    if sel.using_layer_combo:
        layer = sel.current_layer
        self._logger.info(
            f"get_current_item: key='{key}', path='{path}', "
            f"layer='{layer.name() if layer else None}', modo=layer_combo",
            code="GET_CURRENT_ITEM_LAYER",
        )
    else:
        self._logger.info(
            f"get_current_item: key='{key}', path='{path}', modo=line_edit",
            code="GET_CURRENT_ITEM_PATH",
        )
    
    return (path, layer)
```

### 3.2 Passo 2: Migrar PathExtensionPlugin

**Arquivo:** `plugins/PathExtensionPlugin.py`

#### 3.2.1 Novos Imports

```python
# NOVOS IMPORTS (substituem WidgetFactory)
from ..resources.widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.widgets.grid.GridComboBox import GridComboBox
from ..resources.widgets.grid.GridRadioButton import GridRadioButton
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.widgets.SeparatorWidget import SeparatorWidget

# IMPORTS ANTIGOS QUE PERMANECEM
from qgis.core import QgsMapLayerProxyModel
from ..plugins.BasePlugin import BasePluginMTL
from ..core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from ..core.engine_tasks.PathExtensionStep import PathExtensionStep
from ..core.engine_tasks.ExecutionContext import ExecutionContext
from ..i18n.TranslationManager import STR
from ..utils.ToolKeys import ToolKey
from ..utils.Preferences import Preferences

# IMPORTS QUE SERÃO REMOVIDOS (WidgetFactory)
# from ..core.ui.WidgetFactory import WidgetFactory  ← REMOVER
```

#### 3.2.2 `_build_ui()` Migrado

```python
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
    self.logger.info("GridComplexSelector criado com allow_layer=True, mode_type=input")

    # Registra callback para quando o layer/path mudar
    # O ComplexSelector tem self.on_path_change que é disparado
    # quando o path ou layer muda. O GridComplexSelector encapsula
    # isso via set_on_changed()
    self.layer_selector.set_on_changed("input_layer", self._on_layer_changed)
    self.logger.debug("Callback _on_layer_changed registrado via set_on_changed()")

    self.layout.addWidget(self.layer_selector)

    # ── Separador ────────────────────────────────────────────────
    self.layout.addWidget(SeparatorWidget())

    # ── Atributo Selector (GridComboBox) ─────────────────────────
    self.logger.debug("Criando GridComboBox para selecao de atributo")
    self.attr_selector = GridComboBox(
        config={
            "path_field": {
                "label": f"{STR.PATH}:",
                "description": "Selecione o campo que contem o caminho dos arquivos",
                "options": {},  # vazio inicialmente, preenchido por _on_layer_changed
                "selected_key": None,
            },
        },
        separator_bottom=True,
        parent=self,
    )
    self.logger.info("GridComboBox criado (vazio, aguardando selecao de camada)")
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
    self.logger.info("GridExecutionButtons criado com botao Executar + Fechar + Info")
    self.layout.add_execution_buttons(self.action_buttons)

    self.logger.info("Interface da ferramenta construida com sucesso")
```

#### 3.2.3 `_on_layer_changed()` Migrado

```python
def _on_layer_changed(self, paths: list[str]):
    """
    Atualiza options do dropdown de atributos quando a camada/path muda.
    
    Usa get_current_item() para obter (path, layer_or_none).
    Se layer for valido, popula combo com campos da camada.
    Se layer for None (modo path de arquivo), limpa o combo.
    Sempre busca se o atributo "Path"/"path" existe — se existir, ja aparece selecionado.
    Se nao existir, fica "Selecionar" (vazio).
    """
    self.logger.info(
        f"_on_layer_changed chamado com paths={paths}",
        code="ON_LAYER_CHANGED",
    )

    # Obtem (path, layer) via get_current_item
    path, layer = self.layer_selector.get_current_item("input_layer")
    self.logger.info(
        f"get_current_item: path='{path}', "
        f"layer={layer.name() if layer else None}",
        code="GET_CURRENT_ITEM",
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
                f"Auto-selecionado campo 'path' no combo",
                code="AUTO_SELECT_PATH",
            )
        else:
            self.logger.info(
                "Campo 'path' nao encontrado. Combo permanece sem selecao.",
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

    self.logger.info("_on_layer_changed finalizado", code="ON_LAYER_CHANGED_END")
```

#### 3.2.4 `execute_tool()` Migrado

```python
def execute_tool(self):
    self.logger.info("Iniciando processamento: PathExtension")

    # Obtem (path, layer) via get_current_item
    path, layer = self.layer_selector.get_current_item("input_layer")
    self.logger.info(
        f"execute_tool: path='{path}', "
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
        f"attribute='{attribute}', mode='{mode_key}', "
        f"path='{path}'",
        code="EXECUTE_PARAMS",
    )

    context = ExecutionContext()
    context.set("layer", layer)
    context.set("attribute", attribute)
    context.set("mode", mode_key)
    context.set("tool_key", self.TOOL_KEY)
    context.set("iface", self.iface)

    self._run_async_pipeline(context)
```

#### 3.2.5 `_load_prefs()` Migrado

```python
def _load_prefs(self):
    self.logger.debug("Carregando preferencias")

    last_mode = self.preferences.get("last_mode", "remove")
    self.logger.debug(f"Valor carregado de last_mode: {last_mode} (tipo={type(last_mode).__name__})")

    # Suporte a valor legado: se for int (indice do sistema antigo), converte para string (chave)
    if isinstance(last_mode, int):
        mode_map_reverse = {0: "remove", 1: "restore", 2: "zip", 3: "unzip"}
        converted = mode_map_reverse.get(last_mode, "remove")
        self.logger.info(
            f"Valor legado de modo convertido: indice {last_mode} -> chave '{converted}'",
            code="LEGACY_MODE_CONVERTED",
        )
        last_mode = converted

    self.mode_selector.set_selected_key(str(last_mode))
    self.logger.debug(
        f"Modo selecionado após load: {self.mode_selector.get_selected_key()}",
        code="LOAD_PREFS_DONE",
    )
```

#### 3.2.6 `_save_prefs()` Migrado

```python
def _save_prefs(self):
    self.logger.debug("Salvando preferencias")

    self.preferences["last_mode"] = self.mode_selector.get_selected_key()
    self.preferences["window_width"] = self.width()
    self.preferences["window_height"] = self.height()

    self.logger.debug(
        f"Salvando: last_mode='{self.preferences['last_mode']}', "
        f"window=({self.preferences['window_width']}x{self.preferences['window_height']})",
        code="SAVE_PREFS",
    )

    Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
    self.logger.debug("Preferencias salvas com sucesso", code="SAVE_PREFS_DONE")
```

#### 3.2.7 `_MODE_MAP` Removido

O mapeamento `_MODE_MAP = {0: "remove", 1: "restore", 2: "zip", 3: "unzip"}` foi removido pois agora as chaves são strings diretas no `GridRadioButton`.

---

## 4. DIAGRAMA DE FLUXO

```
Plugin._build_ui()
  ├── Cria GridComplexSelector (allow_layer=True, layer_filters=VectorLayer)
  ├── Registra callback: grid_selector.set_on_changed("input_layer", self._on_layer_changed)
  ├── Cria GridComboBox (vazio)
  ├── Cria GridRadioButton (4 modos)
  └── Cria GridExecutionButtons (Executar + Fechar + Info)

Usuário seleciona camada no QgsMapLayerComboBox
  └── ComplexSelector._on_combo_layer_changed()
      └── ComplexSelector._emit_path_change()
          └── on_path_change(paths)  ← callback nativo
              └── GridComplexSelector wrapper → plugin._on_layer_changed(paths)
                  ├── Log: "ON_LAYER_CHANGED" com paths
                  ├── layer_selector.get_current_item("input_layer")
                  │   ├── Log: "GET_CURRENT_ITEM" com path e layer
                  │   └── Retorna (path, layer_or_none)
                  ├── SE layer for válido:
                  │   ├── Log: "LAYER_MODE" com nome da camada
                  │   ├── Extrai campos da camada
                  │   ├── Se "path" encontrado: Log "PATH_FIELD_FOUND"
                  │   ├── attr_selector.set_options("path_field", options)
                  │   ├── Log: "POPULATE_COMBO" com qtd de campos
                  │   └── Se default_key: auto-select + Log "AUTO_SELECT_PATH"
                  └── SENÃO (modo path):
                      ├── Log: "CLEAR_COMBO"
                      └── attr_selector.set_options("path_field", {})

Usuário clica "Executar"
  └── plugin.execute_tool()
      ├── layer_selector.get_current_item("input_layer")
      │   └── Log: "EXECUTE_TOOL_ITEM"
      ├── attr_selector.get_selected_key("path_field")
      ├── mode_selector.get_selected_key()
      ├── Log: "EXECUTE_PARAMS" com todos os parâmetros
      └── Cria contexto e executa pipeline
```

---

## 5. ARQUIVOS AFETADOS

| Arquivo | Tipo de Mudança | Risco |
|---------|----------------|-------|
| `resources/widgets/grid/GridComplexSelector.py` | Adicionar método `get_current_item(key)` | Baixo |
| `plugins/PathExtensionPlugin.py` | Reescrever `_build_ui()`, `_on_layer_changed()`, `execute_tool()`, `_load_prefs()`, `_save_prefs()` | Médio |
| `docs/ia/changelog.txt` | Adicionar entrada de versão | Baixo |

---

## 6. LOGS ADICIONADOS PARA VALIDAÇÃO

| Local | Código | Mensagem |
|-------|--------|----------|
| `GridComplexSelector.get_current_item()` | `GET_CURRENT_ITEM_NOT_FOUND` | Selector não encontrado |
| `GridComplexSelector.get_current_item()` | `GET_CURRENT_ITEM_LAYER` | Path + layer + modo layer_combo |
| `GridComplexSelector.get_current_item()` | `GET_CURRENT_ITEM_PATH` | Path + modo line_edit |
| `_on_layer_changed()` | `ON_LAYER_CHANGED` | Paths recebidos |
| `_on_layer_changed()` | `GET_CURRENT_ITEM` | Path + layer obtidos |
| `_on_layer_changed()` | `LAYER_MODE` | Camada válida, extraindo campos |
| `_on_layer_changed()` | `PATH_FIELD_FOUND` | Campo "path" encontrado no índice |
| `_on_layer_changed()` | `POPULATE_COMBO` | Qtd de campos + default_key |
| `_on_layer_changed()` | `AUTO_SELECT_PATH` | Auto-selecionado campo "path" |
| `_on_layer_changed()` | `PATH_FIELD_NOT_FOUND` | Campo "path" não encontrado |
| `_on_layer_changed()` | `CLEAR_COMBO` | Limpando combo (modo path) |
| `_on_layer_changed()` | `ON_LAYER_CHANGED_END` | Finalizado |
| `execute_tool()` | `EXECUTE_TOOL_ITEM` | Path + layer obtidos |
| `execute_tool()` | `NO_LAYER` | Nenhuma camada selecionada |
| `execute_tool()` | `NO_ATTRIBUTE` | Nenhum atributo selecionado |
| `execute_tool()` | `NO_MODE` | Nenhum modo selecionado |
| `execute_tool()` | `EXECUTE_PARAMS` | Todos os parâmetros |
| `_load_prefs()` | `LEGACY_MODE_CONVERTED` | Conversão de índice legado |
| `_load_prefs()` | `LOAD_PREFS_DONE` | Modo após load |
| `_save_prefs()` | `SAVE_PREFS` | Valores salvos |
| `_save_prefs()` | `SAVE_PREFS_DONE` | Preferências salvas |

---

## 7. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| `get_current_item()` retornar layer=None mesmo em modo layer combo | Baixa | Médio | Log `GET_CURRENT_ITEM_LAYER` para validar |
| `set_on_changed()` não disparar na primeira seleção | Média | Médio | Verificar se GridComplexSelector wrapper está instalado |
| Preferências legadas (índice int) quebrarem | Média | Baixo | Converter no `_load_prefs()` com log `LEGACY_MODE_CONVERTED` |
| Plugin perder referência do dialog | Baixa | Alto | Manter `return dlg` no `run()` |
| `GridExecutionButtons` não ter `info_callback` separado | Baixa | Baixo | Usar `enable_info=True` + `tool_key` |

---

## 8. CHECKLIST DE MIGRAÇÃO

### Pré-migração
- [ ] Ler `docs/skills/SKILL_WIDGETS2.md` (contrato do novo sistema)
- [ ] Ler `docs/skills/PLUGIN_CONTRACT.md` (12 regras críticas)
- [ ] Ler `docs/plano_eliminacao_widgetfactory.md` (estratégia geral)
- [ ] Analisar `GridComplexSelector.py` atual (entender API)
- [ ] Analisar `GridComboBox.py` atual (entender API)
- [ ] Analisar `GridRadioButton.py` atual (entender API)
- [ ] Analisar `GridExecutionButtons.py` atual (entender API)

### Modificações no GridComplexSelector
- [ ] Adicionar método `get_current_item(key)` (retorna tupla path + layer_or_none)
- [ ] Adicionar logs no `get_current_item()` para validação

### Migração do PathExtensionPlugin
- [ ] Substituir imports: remover `WidgetFactory`, adicionar `GridComplexSelector`, `GridComboBox`, `GridRadioButton`, `GridExecutionButtons`, `SeparatorWidget`
- [ ] Substituir `create_layer_input()` por `GridComplexSelector` com `allow_layer=True`
- [ ] Substituir `create_dropdown_selector()` por `GridComboBox`
- [ ] Substituir `create_radio_button_grid()` por `GridRadioButton` (chaves string)
- [ ] Substituir `create_bottom_action_buttons()` por `GridExecutionButtons`
- [ ] Registrar callback via `set_on_changed("input_layer", self._on_layer_changed)`
- [ ] Adaptar `_on_layer_changed()` para usar `get_current_item()` + logs
- [ ] Adaptar `execute_tool()` para usar `get_current_item()` + logs
- [ ] Adaptar `_load_prefs()` para usar chaves string + conversão legado
- [ ] Adaptar `_save_prefs()` para salvar chaves string
- [ ] Remover `_MODE_MAP` (não é mais necessário)
- [ ] Remover imports não utilizados
- [ ] Adicionar `SeparatorWidget()` entre widgets no layout

### Pós-migração
- [ ] Plugin não importa de `core/ui/WidgetFactory`
- [ ] Plugin não importa de `resources/styles/`
- [ ] Plugin não chama `setStyleSheet()`
- [ ] Atualizar `docs/ia/changelog.txt`
- [ ] Testar fluxo completo: selecionar layer → ver atributos → selecionar modo → executar
- [ ] Testar carregamento de preferências legadas (índice int)
- [ ] Testar salvamento de preferências (chave string)
- [ ] Verificar logs no console QGIS para validação

---

## 9. CONTRATO DO PLUGIN (Verificação)

| Regra | Status | Verificação |
|-------|--------|-------------|
| #1 UI via WidgetFactory (ou widgets) | ✅ | Usa `resources/widgets/` |
| #2 Logging via LogUtils com ToolKey | ✅ | Herda de `BasePluginMTL` |
| #3 Strings via STR | ✅ | Já usa `STR.*` |
| #4 ToolKey é enum | ✅ | `ToolKey.PATH_EXTENSION_TOOL` |
| #5 Estilos via WidgetFactory + Styles.py | ✅ | Widgets se autoconfiguram |
| #6 Exceções logadas com logger.exception | ✅ | Herda tratamento |
| #7 Métodos estáticos recebem tool_key | N/A | Não tem métodos estáticos |
| #8 Configurações via Preferences | ✅ | `_load_prefs()` / `_save_prefs()` |
| #9 Widgets customizados em resources/ | ✅ | Usa widgets existentes |
| #10 Help via InstructionsManager | ✅ | `enable_info=True` no GridExecutionButtons |
| #11 Logs em pt_BR | ✅ | Herda padrão |
| #17 Registro no ToolRegistry | ✅ | Já registrado |

---

## 10. HISTÓRICO DE MUDANÇAS

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-31 | 1.0.0 | Criação inicial do plano |
| 2026-07-31 | 2.0.0 | **Revisão:** Substituído `get_current_layer()` por `get_current_item()` que retorna `(path, layer_or_none)`. Removido `on_path_change` do config dict — plugin usa `set_on_changed()` já existente. Adicionados ~20 logs para validação. Removido `_MODE_MAP`. Adicionado diagrama de fluxo completo. |