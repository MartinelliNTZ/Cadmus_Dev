# 🎯 PLANO DE AÇÃO: Migração GenerateTrailPlugin — Novo Sistema de Widgets

**Objetivo:** Migrar `GenerateTrailPlugin` da `WidgetFactory` para o novo sistema de widgets autoconfiguráveis (`resources/new_widgets/`), com modificações no `ComplexSelector` e `GridComplexSelector` para suportar checkbox de bloqueio e sub-label "somente feições selecionadas".

**Data:** 2026-07-27
**Versão:** 1.0.0
**Autor:** Cadmus Engineering
**Status:** ⏳ Planejamento

---

## Sumário

1. [Widgets Necessários](#1-widgets-necessários)
2. [Layout Proposto](#2-layout-proposto)
3. [Modificações no ComplexSelector](#3-modificações-no-complexselector)
4. [Modificações no GridComplexSelector](#4-modificações-no-gridcomplexselector)
5. [Arquivos Afetados](#5-arquivos-afetados)
6. [Estratégia de Implementação](#6-estratégia-de-implementação)
7. [Riscos e Mitigações](#7-riscos-e-mitigações)
8. [Checklist de Implementação](#8-checklist-de-implementação)

---

## 1. Widgets Necessários

### 1.1 Mapeamento WidgetFactory → new_widgets

| Widget Atual (WidgetFactory) | Novo Widget (new_widgets/) | Status |
|---|---|---|
| `create_layer_input()` — camada linha | `GridComplexSelector` **modificado** (layer_filters=LineLayer + checkbox bloqueio) | ⬜ Modificar |
| `create_double_spin_input()` — tamanho implemento | `GridDoubleSpin` | ✅ Já existe |
| `create_save_file_selector()` — saída | `GridComplexSelector` (parent=input, suffix="_trail", extension=".gpkg") | ✅ Já existe (precisa modificar) |
| `create_collapsible_parameters()` — avançados | `CollapsibleParametersWidget` | ✅ Já existe |
| `create_qml_selector()` — dentro collapsible | `ComplexSelector` (file filter .qml) direto | ✅ Já existe |
| `create_bottom_action_buttons()` — run/close/info | `GridExecutionButtons` | ✅ Já existe |

### 1.2 GridComplexSelector — Config dos Seletores

#### Seletor de Entrada (input)
```
Config:
  "input_layer": {
    "label": "Camada de linhas:",
    "mode_type": "input",
    "allow_file": False,
    "allow_folder": False,
    "layer_filters": QgsMapLayerProxyModel.LineLayer,
    "allow_feicoes": True,           # 🆕 NOVO — ativa checkbox de bloqueio
    "only_selected_label": "Somente feições selecionadas",  # 🆕 NOVO
  }
```

#### Seletor de Saída (output)
```
Config:
  "output_trail": {
    "label": "Salvar rastro em:",
    "mode_type": "output",
    "parent": "input_layer",
    "suffix": "_trail",
    "fixed_extension": "gpkg",
    "subfolder": "",
    "fixed_name": "implement_trail",        # ou STR se disponível
    "allow_file": True,
    "allow_folder": True,
  }
```

### 1.3 GridComplexSelector — Config do Tamanho do Implemento

```python
GridDoubleSpin(
    config={
        "implement_size": {
            "label": "Tamanho do implemento (m):",
            "description": "Largura do implemento agrícola em metros",
            "value": 3500,
            "min": 10,
            "max": 50000,
            "step": 100,
            "decimals": 0,
            "type": "int",
        },
    },
    separator_bottom=True,
    parent=self,
)
```

### 1.4 CollapsibleParametersWidget + QML Selector

```python
# Dentro do CollapsibleParametersWidget
self.advanced_params = CollapsibleParametersWidget(
    title="Parâmetros Avançados",
    expanded_by_default=False,
    parent=self,
)
self.layout.addWidget(self.advanced_params)

# ComplexSelector para QML (file filter .qml)
self.qml_selector = ComplexSelector(
    label_text="Estilo QML:",
    file_filter="QML (*.qml)",
    allow_file=True,
    allow_folder=False,
    selection_mode="file",
    mode_type="input",
    show_explorer_button=True,
    show_copy_button=True,
    parent=self,
)
self.advanced_params.add_content(self.qml_selector)
```

---

## 2. Layout Proposto

Layout do diálogo (top → bottom):

```
┌─────────────────────────────────────────────────────┐
│  AppBar: "Gerar Rastro Implemento"                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─ GridComplexSelector (input_layer) ────────────┐ │
│  │  Camada de linhas: [____________________] ☐ 🔍 │ │ ← ☐ é o checkbox de bloqueio
│  │  ❏ Somente feições selecionadas                │ │ ← sub-label
│  │  Salvar rastro em: [C:/...]  📁 📥 🛠️ ➡️ 📋 │ │
│  └─────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ GridDoubleSpin (implement_size) ───────────────┐ │
│  │  Tamanho do implemento (m): [ 3500     ]       │ │
│  └─────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ CollapsibleParametersWidget ───────────────────┐ │
│  │  ▼ Parâmetros Avançados (▼ expandir)           │ │
│  │  ┌─ ComplexSelector (qml) ────────────────────┐ │ │
│  │  │  Estilo QML: [___________] 🔍 ➡️ 📋     │ │ │
│  │  └─────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ GridExecutionButtons ──────────────────────────┐ │
│  │  [ℹ️] [Fechar] [▶ Executar]                    │ │
│  └─────────────────────────────────────────────────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 3. Modificações no ComplexSelector

### 3.1 Novo parâmetro: `allow_feicoes`

Adicionar ao construtor do `ComplexSelector`:

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `allow_feicoes` | bool | `False` | Ativa checkbox de bloqueio ao lado do lineedit |
| `only_selected_label` | str | `""` | Texto do sub-label "Somente feições selecionadas" |

### 3.2 Comportamento

Quando `allow_feicoes=True`:

```
LAYOUT:
  [Label] [LineEdit] [☐ Checkbox sem texto] [Botões]
  [❤️ Somente feições selecionadas]                    ← sub-label abaixo

COMPORTAMENTO:
  - Checkbox fica entre o QStackedWidget e os botões
  - Checkbox NÃO TEM TEXTO VISÍVEL (text=""), só tooltip/description
  - Tooltip da checkbox vem de `only_selected_label`
  - Quando checkbox está DESMARCADA (padrão):
    → ComplexSelector inteiro fica disabled (bloqueado)
    → `setEnabled(False)` em todo o widget exceto na checkbox
    → Input, botões, combo ficam cinza/inoperantes
  - Quando checkbox está MARCADA:
    → ComplexSelector volta ao normal (habilitado)
    → Widgets internos recebem `setEnabled(True)`
  - Estado inicial: checkbox desmarcada (bloqueado)

GERENCIAMENTO INTERNO:
  - ComplexSelector gerencia o bloqueio internamente
  - Nenhuma intervenção do GridComplexSelector ou plugin
  - `_update_blocked_state()` é chamado sempre que a checkbox muda
```

### 3.3 API Pública

```python
@property
def allow_feicoes(self) -> bool:
    return self._allow_feicoes

@allow_feicoes.setter
def allow_feicoes(self, value: bool):
    self._allow_feicoes = value
    # Se False, esconde checkbox e libera widget
    # Se True, mostra checkbox e bloqueia widget

@property
def only_selected_enabled(self) -> bool:
    """Retorna True se o checkbox de feições selecionadas estiver marcado."""
    return self._feicoes_checkbox.isChecked() if hasattr(self, '_feicoes_checkbox') else True

def set_only_selected_enabled(self, enabled: bool):
    """Define estado do checkbox programaticamente."""
    if hasattr(self, '_feicoes_checkbox'):
        self._feicoes_checkbox.setChecked(enabled)

def get_only_selected_state(self) -> bool:
    return self.only_selected_enabled
```

### 3.4 Estrutura Interna Modificada

```python
# NOVO no __init__:
self._allow_feicoes = allow_feicoes
self._only_selected_label = only_selected_label

# NOVO no _build_ui():
if self._allow_feicoes:
    # Checkbox sem texto, apenas description/tooltip
    self._feicoes_checkbox = QCheckBox()
    self._feicoes_checkbox.setText("")  # SEM texto
    self._feicoes_checkbox.setChecked(False)  # Default: desmarcado
    if only_selected_label:
        self._feicoes_checkbox.setToolTip(only_selected_label)
    self._feicoes_checkbox.toggled.connect(self._on_feicoes_toggled)
    layout.insertWidget(botões_index, self._feicoes_checkbox, 0, Qt.AlignVCenter)
    
    # Sub-label abaixo
    self._only_selected_label_widget = QLabel(only_selected_label)
    self._only_selected_label_widget.setStyleSheet("color: gray; font-size: 10px;")
    # Adiciona abaixo do layout principal
    
    # Bloqueia inicialmente
    self._update_blocked_state()
```

### 3.5 Métodos Internos Novos

```python
def _on_feicoes_toggled(self, checked: bool):
    """Quando checkbox muda, atualiza bloqueio."""
    self._update_blocked_state()

def _update_blocked_state(self):
    """Gerencia o bloqueio do widget baseado no estado da checkbox."""
    if not self._allow_feicoes:
        return
    
    blocked = not self._feicoes_checkbox.isChecked()
    
    # Bloqueia/desbloqueia tudo EXCETO a própria checkbox
    for widget in [self._edit, self._stack, self._combo]:
        widget.setEnabled(not blocked)
    
    # Botões
    for btn_name in ['_btn_file', '_btn_folder', '_btn_project', 
                     '_btn_origin', '_btn_suggest', '_btn_explorer', '_btn_copy']:
        btn = getattr(self, btn_name, None)
        if btn:
            btn.setEnabled(not blocked)

def only_selected_enabled(self) -> bool:
    """Retorna True se apenas feições selecionadas devem ser usadas."""
    if not self._allow_feicoes:
        return False  # Se não tem checkbox, retorna False (usa todas)
    return self._feicoes_checkbox.isChecked()
```

### 3.6 Backward Compatibility

```python
# ✅ COMPLETAMENTE BACKWARD COMPATIBLE
# Se allow_feicoes=False (padrão), nada muda:
#   - Checkbox não é criada
#   - Sub-label não é exibido
#   - Comportamento idêntico ao atual
```

---

## 4. Modificações no GridComplexSelector

### 4.1 Propagação dos Novos Parâmetros

No método `_build_selector()` do `GridComplexSelector`, adicionar:

```python
# NOVOS parâmetros lidos do field_config:
allow_feicoes = field_config.get("allow_feicoes", False)
only_selected_label = field_config.get("only_selected_label", "")

# Passar para o ComplexSelector:
selector = ComplexSelector(
    ...
    allow_feicoes=allow_feicoes,                    # 🆕
    only_selected_label=only_selected_label,        # 🆕
    ...
)
```

### 4.2 API Pública no GridComplexSelector

```python
def is_only_selected_enabled(self, label: str) -> bool:
    """Retorna estado do checkbox de feições selecionadas para um selector."""
    sel = self._selectors.get(label)
    return sel.only_selected_enabled() if sel else False

def set_only_selected_enabled(self, label: str, enabled: bool):
    """Define estado do checkbox programaticamente."""
    sel = self._selectors.get(label)
    if sel:
        sel.set_only_selected_enabled(enabled)
```

---

## 5. Arquivos Afetados

### Modificar (3 arquivos)

| Arquivo | Mudança |
|---------|---------|
| `resources/new_widgets/simple/ComplexSelector.py` | Adicionar `allow_feicoes`, checkbox bloqueio, sub-label, API pública |
| `resources/new_widgets/grid/GridComplexSelector.py` | Propagar novos parâmetros, API pública |
| `docs/skills/SKILL_WIDGETS2.md` | Documentar novos parâmetros |

### Reescrever (1 arquivo)

| Arquivo | Mudança |
|---------|---------|
| `plugins/GenerateTrailPlugin.py` | Substituir WidgetFactory por new_widgets |

### Atualizar (2 arquivos)

| Arquivo | Mudança |
|---------|---------|
| `docs/plano_eliminacao_widgetfactory.md` | Marcar GenerateTrailPlugin como migrado |
| `docs/ia/changelog.txt` | Registrar nova versão |

---

## 6. Estratégia de Implementação

### FASE 1 — Modificar ComplexSelector

1. Adicionar parâmetros ao `__init__`:
   - `allow_feicoes: bool = False`
   - `only_selected_label: str = ""`

2. No `_build_ui()`:
   - Se `allow_feicoes=True`:
     - Inserir `QCheckBox` SEM TEXTO entre o `QStackedWidget` e os botões no `QHBoxLayout`
     - Tooltip da checkbox = `only_selected_label`
     - Criar `QLabel` com `only_selected_label` abaixo do layout principal
     - Conectar `toggled` → `_update_blocked_state()`

3. Métodos novos:
   - `_on_feicoes_toggled(checked)`
   - `_update_blocked_state()`
   - `only_selected_enabled() → bool`
   - `set_only_selected_enabled(bool)`

4. Garantir backward compatibility (tudo opcional, default False)

### FASE 2 — Modificar GridComplexSelector

1. No `_build_selector()`:
   - Ler `allow_feicoes` e `only_selected_label` do `field_config`
   - Passar para o construtor do `ComplexSelector`

2. API pública nova:
   - `is_only_selected_enabled(label) → bool`
   - `set_only_selected_enabled(label, enabled)`

### FASE 3 — Reescrever GenerateTrailPlugin

1. **Imports:**
   ```python
   # REMOVER
   from ..core.ui.WidgetFactory import WidgetFactory
   from ..core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
   from ..core.engine_tasks.BufferStep import BufferStep
   from ..core.engine_tasks.ExplodeStep import ExplodeStep
   from ..core.engine_tasks.SaveVectorStep import SaveVectorStep
   from ..core.engine_tasks.ExecutionContext import ExecutionContext
   
   # ADICIONAR
   from ..resources.new_widgets.grid.GridComplexSelector import GridComplexSelector
   from ..resources.new_widgets.grid.GridDoubleSpin import GridDoubleSpin
   from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons
   from ..resources.new_widgets.CollapsibleParametersWidget import CollapsibleParametersWidget
   from ..resources.new_widgets.simple.ComplexSelector import ComplexSelector  # QML
   from ..resources.new_widgets.SeparatorWidget import SeparatorWidget
   ```

2. **`_build_ui()` — estrutura:**
   ```python
   def _build_ui(self, **kwargs):
       super()._build_ui(
           title=STR.GENERATE_TRAIL_TITLE,
           icon_path="gerar_rastro.ico",
           enable_scroll=True,
       )

       # ── GridComplexSelector: Input Layer ─────────────────
       self.input_selector = GridComplexSelector(
           config={
               "input_layer": {
                   "label": f"{STR.INPUT_LINE_LAYER}:",
                   "mode_type": "input",
                   "allow_file": False,
                   "allow_folder": False,
                   "layer_filters": QgsMapLayerProxyModel.LineLayer,
                   "allow_feicoes": True,
                   "only_selected_label": STR.ONLY_SELECTED_FEATURES,
               },
           },
           tool_key=self.TOOL_KEY,
           separator_bottom=True,
           parent=self,
       )
       self.layout.addWidget(self.input_selector)

       # ── GridDoubleSpin: Implement Size ──────────────────
       self.implement_spin = GridDoubleSpin(
           config={
               "implement_size": {
                   "label": f"{STR.IMPLEMENT_SIZE}:",
                   "value": 3500,
                   "min": 10,
                   "max": 50000,
                   "step": 100,
                   "decimals": 0,
                   "type": "int",
               },
           },
           separator_bottom=True,
           parent=self,
       )
       self.layout.addWidget(self.implement_spin)

       # ── GridComplexSelector: Output Trail ────────────────
       self.output_selector = GridComplexSelector(
           config={
               "output_trail": {
                   "label": f"{STR.SAVE_TRAIL_IN}:",
                   "mode_type": "output",
                   "parent": "input_layer",
                   "suffix": "_trail",
                   "fixed_extension": "gpkg",
                   "subfolder": "",
                   "fixed_name": STR.IMPLEMENT_TRAIL,
                   "allow_file": True,
                   "allow_folder": True,
                   "file_filter": "GeoPackage (*.gpkg)",
               },
           },
           tool_key=self.TOOL_KEY,
           separator_bottom=True,
           parent=self,
       )
       self.layout.addWidget(self.output_selector)

       # ── CollapsibleParameters: Advanced ─────────────────
       self.advanced_params = CollapsibleParametersWidget(
           title=STR.ADVANCED_PARAMETERS,
           expanded_by_default=False,
           parent=self,
       )
       
       # QML Selector dentro do collapsible
       self.qml_selector = ComplexSelector(
           label_text=f"{STR.QML_STYLE}:",
           file_filter="QML (*.qml)",
           allow_file=True,
           allow_folder=False,
           selection_mode="file",
           mode_type="input",
           show_explorer_button=True,
           show_copy_button=True,
           tool_key=self.TOOL_KEY,
           parent=self,
       )
       self.advanced_params.add_content(self.qml_selector)
       self.layout.addWidget(self.advanced_params)

       # ── GridExecutionButtons ────────────────────────────
       self.action_buttons = GridExecutionButtons(
           config={
               "run": {
                   "label": STR.EXECUTE,
                   "description": "Gera o rastro do implemento",
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
   ```

3. **`_load_prefs()`:**
   ```python
   def _load_prefs(self):
       # Carregar paths
       last_input = self.preferences.get("last_input_path", "")
       if last_input:
           self.input_selector.set_path("input_layer", last_input)
       
       last_output = self.preferences.get("last_output_path", "")
       if last_output:
           self.output_selector.set_path("output_trail", last_output)
       
       # Carregar tamanho
       last_tam = self.preferences.get("last_implement_length")
       if last_tam is not None:
           self.implement_spin.set_value("implement_size", float(last_tam))
       
       # QML
       last_qml = self.preferences.get("last_qml_path", "")
       if last_qml:
           self.qml_selector.set_path(last_qml)
       
       # Only selected state
       only_selected = self.preferences.get("only_selected", False)
       self.input_selector.set_only_selected_enabled("input_layer", only_selected)
   ```

4. **`_save_prefs()`:**
   ```python
   def _save_prefs(self):
       self.preferences["last_input_path"] = self.input_selector.get_path("input_layer")
       self.preferences["last_output_path"] = self.output_selector.get_path("output_trail")
       self.preferences["last_implement_length"] = self.implement_spin.get_value("implement_size")
       self.preferences["last_qml_path"] = self.qml_selector.path()
       self.preferences["only_selected"] = self.input_selector.is_only_selected_enabled("input_layer")
       self.preferences["window_width"] = self.width()
       self.preferences["window_height"] = self.height()
       Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
   ```

5. **`execute_tool()` adaptado:**
   ```python
   def execute_tool(self):
       # Input via selector
       input_layer = self.input_selector.get("input_layer").current_layer
       if not input_layer:
           QgisMessageUtil.bar_warning(self.iface, STR.SELECT_VALID_LINE_LAYER)
           return
       
       only_selected = self.input_selector.is_only_selected_enabled("input_layer")
       implement_length = self.implement_spin.get_value("implement_size")
       output_path = self.output_selector.get_path("output_trail")
       save_to_folder = bool(output_path)
       
       # QML
       qml_path = self.qml_selector.path()
       qml_enabled = bool(qml_path)
       
       # ... resto da lógica (resolve_input_layer, process_selection, pipeline)
       # Usar input_layer, only_selected, implement_length, output_path
       # Manter a lógica síncrona/assíncrona inalterada
   ```

### FASE 4 — Documentação

1. Atualizar `docs/skills/SKILL_WIDGETS2.md`:
   - Adicionar parâmetros `allow_feicoes`, `only_selected_label` no ComplexSelector
   - Adicionar métodos `only_selected_enabled()`, `set_only_selected_enabled()` no ComplexSelector
   - Adicionar `is_only_selected_enabled()`, `set_only_selected_enabled()` no GridComplexSelector
   - Documentar comportamento de bloqueio

2. Atualizar `docs/plano_eliminacao_widgetfactory.md`:
   - Marcar GenerateTrailPlugin como migrado (FASE 2 item 15)

3. Atualizar `docs/ia/changelog.txt`

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Checkbox bloqueia indevidamente botão de output | Média | Alto | Testar `_update_blocked_state()` exaustivamente |
| Quebrar backward compatibility no ComplexSelector | Baixa | Alto | `allow_feicoes=False` por padrão, sem criar checkbox |
| GridComplexSelector não propaga allow_feicoes | Baixa | Médio | Adicionar parâmetro no `_build_selector()` explicitamente |
| Only selected state não persiste entre sessões | Média | Baixo | Salvar em `_save_prefs()` e restaurar em `_load_prefs()` |
| ComplexSelector com checkbox + layer combo conflita | Baixa | Médio | Checkbox bloqueia TUDO, inclusive combo |
| Flake8 F401 em imports não usados | Média | Baixo | Rodar flake8 após mudanças |
| output_path vazio se input não selecionado | Alta | Alto | Fallback: mesmo diretório do projeto |

---

## 8. Checklist de Implementação

```
[ ] FASE 1: Modificar ComplexSelector
  [ ] 1.1 Adicionar parâmetros: allow_feicoes (False), only_selected_label ("")
  [ ] 1.2 No _build_ui(): inserir QCheckBox sem texto entre stack e botões
  [ ] 1.3 Criar _on_feicoes_toggled() e _update_blocked_state()
  [ ] 1.4 Adicionar sub-label abaixo do layout principal
  [ ] 1.5 API: only_selected_enabled(), set_only_selected_enabled()
  [ ] 1.6 Default False, backward compatibility mantida

[ ] FASE 2: Modificar GridComplexSelector
  [ ] 2.1 No _build_selector(): ler allow_feicoes, only_selected_label do config
  [ ] 2.2 Passar para ComplexSelector
  [ ] 2.3 API: is_only_selected_enabled(label), set_only_selected_enabled(label, enabled)

[ ] FASE 3: Reescrever GenerateTrailPlugin
  [ ] 3.1 Remover imports: WidgetFactory, AsyncPipelineEngine, steps, ExecutionContext
  [ ] 3.2 Adicionar imports: GridComplexSelector, GridDoubleSpin, GridExecutionButtons,
  [ ]     CollapsibleParametersWidget, ComplexSelector, SeparatorWidget
  [ ] 3.3 Reescrever _build_ui():
       [ ] GridComplexSelector input_layer (LineLayer + allow_feicoes=True)
       [ ] GridDoubleSpin implement_size
       [ ] GridComplexSelector output_trail (parent=input, suffix, extension, fixed_name)
       [ ] CollapsibleParametersWidget + ComplexSelector QML
       [ ] GridExecutionButtons run/close/info
  [ ] 3.4 Adaptar _load_prefs() para new_widgets API
  [ ] 3.5 Adaptar _save_prefs() para new_widgets API
  [ ] 3.6 Adaptar execute_tool() para new_widgets API
  [ ] 3.7 Manter lógica de negócio (pipeline sync/async) inalterada

[ ] FASE 4: Pós-implementação
  [ ] 4.1 Atualizar docs/skills/SKILL_WIDGETS2.md (novos params + API)
  [ ] 4.2 Atualizar docs/plano_eliminacao_widgetfactory.md (marcar migrado)
  [ ] 4.3 Atualizar docs/ia/changelog.txt
  [ ] 4.4 Rodar flake8 (sem F401, W292)
  [ ] 4.5 Testar GenerateTrailPlugin completo (sync + async)
  [ ] 4.6 Testar backward compatibility do ComplexSelector sem allow_feicoes
```

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-27 | 1.0.0 | Criação inicial |