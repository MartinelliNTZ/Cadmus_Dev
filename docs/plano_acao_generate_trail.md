# 🎯 PLANO DE AÇÃO: Migração GenerateTrailPlugin — Novo Sistema de Widgets

**Objetivo:** Migrar `GenerateTrailPlugin` da `WidgetFactory` para o novo sistema de widgets autoconfiguráveis (`resources/widgets/`), com modificações no `ComplexSelector` e `GridComplexSelector` para suportar checkbox de proteção (bloqueio) e sub-label "somente feições selecionadas".

**Data:** 2026-07-27
**Versão:** 2.0.0
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

### 1.1 Mapeamento WidgetFactory → widgets

| Widget Atual (WidgetFactory) | Novo Widget (widgets/) | Status |
|---|---|---|
| `create_layer_input()` — camada linha | `GridComplexSelector` (input_layer com checkbox) | ⬜ Modificar |
| `create_save_file_selector()` — saída | `GridComplexSelector` (output_trail com parent=input_layer) — **mesmo GridComplexSelector do input** | ⬜ Modificar |
| `create_double_spin_input()` — tamanho implemento | `GridDoubleSpin` | ✅ Já existe |
| `create_collapsible_parameters()` — avançados | `CollapsibleParametersWidget` | ✅ Já existe |
| `create_qml_selector()` — dentro collapsible | `GridComplexSelector` separado (qml_style, 1 seletor) — **sempre GridComplexSelector, nunca ComplexSelector direto** | ⬜ Modificar |
| `create_bottom_action_buttons()` — run/close/info | `GridExecutionButtons` | ✅ Já existe |

### 1.2 GridComplexSelector Principal — Input + Output (2 seletores)

**REGRA ABSOLUTA:** Plugins usam **APENAS** `GridComplexSelector`. Nunca importam `ComplexSelector` direto.

```python
self.grid = GridComplexSelector(
    config={
        # ── Seletor 1: Input Layer ─────────────────────────
        "input_layer": {
            "label": "Camada de linhas:",
            "mode_type": "input",
            "allow_file": False,
            "allow_folder": False,
            "layer_filters": QgsMapLayerProxyModel.LineLayer,
            "allow_checked": True,                      # 🆕 ativa checkbox
            "checked_text": STR.ONLY_SELECTED_FEATURES,  # 🆕 texto descritivo
            "checked_default": False,                    # 🆕 default desmarcado
        },
        # ── Seletor 2: Output Trail ────────────────────────
        "output_trail": {
            "label": "Salvar rastro em:",
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
self.layout.addWidget(self.grid)
```

### 1.3 GridComplexSelector QML — Separado (1 seletor, dentro do collapsible)

```python
self.qml_grid = GridComplexSelector(
    config={
        "qml_style": {
            "label": "Estilo QML:",
            "mode_type": "input",
            "allow_file": True,
            "allow_folder": False,
            "file_filter": "QML (*.qml)",
        },
    },
    tool_key=self.TOOL_KEY,
    parent=self,
)
```

### 1.4 Parametrização do Checkbox (via config dict)

| Chave no config | Tipo | Padrão | Descrição |
|---|---|---|---|
| `"allow_checked"` | bool | `False` | Se `True`, exibe checkbox entre lineedit e botões |
| `"checked_text"` | str | `""` | Texto descritivo da checkbox (tooltip) + sub-label |
| `"checked_default"` | bool | `False` | Estado inicial da checkbox |

**Regra de bloqueio:**
- `checked_default=False` (padrão) → checkbox desmarcada → selector **bloqueado**
- `checked_default=True` → checkbox marcada → selector **liberado**
- O plugin consulta o estado via `grid.get_checked_state("input_layer")` → `bool`

### 1.5 GridDoubleSpin — Config do Tamanho

```python
self.implement_spin = GridDoubleSpin(
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
self.layout.addWidget(self.implement_spin)
```

---

## 2. Layout Proposto

Layout do diálogo (top → bottom):

```
┌─────────────────────────────────────────────────────┐
│  AppBar: "Gerar Rastro Implemento"                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─ GridComplexSelector (input+output) ───────────┐ │
│  │  Camada de linhas: [____________________] ☐ 🔍 │ │ ← ☐ checkbox proteção
│  │  ❏ Somente feições selecionadas                │ │ ← sub-label
│  │  ─────────────────────────────────────────────  │ │
│  │  Salvar rastro em: [C:/...]  📁 📥 🛠️ ➡️ 📋 │ │
│  └─────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ GridDoubleSpin (implement_size) ───────────────┐ │
│  │  Tamanho do implemento (m): [ 3500     ]       │ │
│  └─────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ CollapsibleParametersWidget ───────────────────┐ │
│  │  ▼ Parâmetros Avançados                        │ │
│  │  ┌─ GridComplexSelector (qml) ────────────────┐ │ │
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

### 3.1 Novos parâmetros no config (via `__init__`)

Adicionar ao construtor do `ComplexSelector`:

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `allow_checked` | bool | `False` | Ativa checkbox de proteção entre lineedit e botões |
| `checked_text` | str | `""` | Texto descritivo (tooltip da checkbox + sub-label) |
| `checked_default` | bool | `False` | Estado inicial da checkbox |

### 3.2 Comportamento

Quando `allow_checked=True`:

```
LAYOUT:
  [Label] [LineEdit] [☐ (sem texto)] [Botões]
  [❤️ checked_text]                    ← sub-label abaixo

COMPORTAMENTO:
  - Checkbox SEM TEXTO VISÍVEL (text=""), só tooltip = checked_text
  - Sub-label com checked_text abaixo do layout principal
  - checked_default=False (padrão):
    → ComplexSelector inteiro fica disabled (bloqueado)
    → setEnabled(False) em tudo exceto na própria checkbox
    → Input, botões, combo ficam cinza/inoperantes
  - checked_default=True:
    → ComplexSelector liberado (habilitado)
  - toggle da checkbox → _update_blocked_state()

GERENCIAMENTO INTERNO:
  - ComplexSelector gerencia o bloqueio internamente
  - Nenhuma intervenção do GridComplexSelector ou plugin
  - _update_blocked_state() chamado sempre que checkbox muda
```

### 3.3 API Pública (somente consulta, sem property)

```python
def get_checked_state(self) -> bool:
    """
    Retorna estado atual da checkbox de proteção.
    Se allow_checked=False, retorna o valor de checked_default.
    """
    if not self._allow_checked:
        return self._checked_default
    return self._feicoes_checkbox.isChecked()

def set_checked_state(self, checked: bool):
    """Define estado da checkbox programaticamente."""
    if hasattr(self, '_feicoes_checkbox'):
        self._feicoes_checkbox.setChecked(checked)
```

### 3.4 Estrutura Interna Modificada

```python
# NOVO no __init__:
self._allow_checked = allow_checked
self._checked_text = checked_text
self._checked_default = checked_default

# NOVO no _build_ui():
if self._allow_checked:
    # Checkbox sem texto, apenas tooltip
    self._feicoes_checkbox = QCheckBox()
    self._feicoes_checkbox.setText("")  # SEM texto visível
    self._feicoes_checkbox.setChecked(self._checked_default)
    if checked_text:
        self._feicoes_checkbox.setToolTip(checked_text)
    self._feicoes_checkbox.toggled.connect(self._on_checked_toggled)
    # Inserir entre stack e botões (antes dos botões)
    layout.insertWidget(layout.count() - num_botoes, self._feicoes_checkbox, 0, Qt.AlignVCenter)
    
    # Sub-label abaixo
    self._checked_label = QLabel(checked_text)
    self._checked_label.setStyleSheet("color: gray; font-size: 10px; padding-left: 130px;")
    # Adiciona abaixo do layout principal
    
    # Bloqueia conforme estado inicial
    self._update_blocked_state()
```

### 3.5 Métodos Internos Novos

```python
def _on_checked_toggled(self, checked: bool):
    """Quando checkbox muda, atualiza bloqueio."""
    self._update_blocked_state()

def _update_blocked_state(self):
    """Gerencia bloqueio do widget baseado no estado da checkbox."""
    if not self._allow_checked:
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
```

### 3.6 Backward Compatibility

```python
# ✅ COMPLETAMENTE BACKWARD COMPATIBLE
# allow_checked=False (padrão):
#   - Checkbox não é criada
#   - Sub-label não é exibido
#   - Comportamento idêntico ao atual
#   - get_checked_state() retorna checked_default (False)
```

---

## 4. Modificações no GridComplexSelector

### 4.1 Propagação dos Novos Parâmetros

No método `_build_selector()` do `GridComplexSelector`, adicionar:

```python
# NOVOS parâmetros lidos do field_config:
allow_checked = field_config.get("allow_checked", False)
checked_text = field_config.get("checked_text", "")
checked_default = field_config.get("checked_default", False)

# Passar para o ComplexSelector:
selector = ComplexSelector(
    ...
    allow_checked=allow_checked,          # 🆕
    checked_text=checked_text,            # 🆕
    checked_default=checked_default,      # 🆕
    ...
)
```

### 4.2 API Pública no GridComplexSelector

```python
def get_checked_state(self, label: str) -> bool:
    """
    Retorna estado do checkbox de proteção para um selector.
    Se o selector não tem allow_checked, retorna False.
    """
    sel = self._selectors.get(label)
    return sel.get_checked_state() if sel else False

def set_checked_state(self, label: str, checked: bool):
    """Define estado do checkbox programaticamente."""
    sel = self._selectors.get(label)
    if sel:
        sel.set_checked_state(checked)
```

---

## 5. Arquivos Afetados

### Modificar (3 arquivos)

| Arquivo | Mudança |
|---------|---------|
| `resources/widgets/simple/ComplexSelector.py` | Adicionar `allow_checked`, `checked_text`, `checked_default`; checkbox; sub-label; `get_checked_state()`; `set_checked_state()` |
| `resources/widgets/grid/GridComplexSelector.py` | Propagar novos parâmetros; `get_checked_state(label)`; `set_checked_state(label, checked)` |
| `docs/skills/SKILL_WIDGETS2.md` | Documentar novos parâmetros e API |

### Reescrever (1 arquivo)

| Arquivo | Mudança |
|---------|---------|
| `plugins/GenerateTrailPlugin.py` | Substituir WidgetFactory por widgets |

### Atualizar (2 arquivos)

| Arquivo | Mudança |
|---------|---------|
| `docs/plano_eliminacao_widgetfactory.md` | Marcar GenerateTrailPlugin como migrado (FASE 2 item 15) |
| `docs/ia/changelog.txt` | Registrar nova versão |

---

## 6. Estratégia de Implementação

### FASE 1 — Modificar ComplexSelector

1. Adicionar parâmetros ao `__init__`:
   - `allow_checked: bool = False`
   - `checked_text: str = ""`
   - `checked_default: bool = False`

2. No `_build_ui()`:
   - Se `allow_checked=True`:
     - Inserir `QCheckBox` SEM TEXTO entre o `QStackedWidget` e os botões
     - Tooltip da checkbox = `checked_text`
     - Criar `QLabel` com `checked_text` abaixo do layout principal
     - Conectar `toggled` → `_update_blocked_state()`

3. Métodos novos:
   - `_on_checked_toggled(checked)`
   - `_update_blocked_state()`
   - `get_checked_state() → bool`
   - `set_checked_state(bool)`

4. Garantir backward compatibility (tudo opcional, default False)

### FASE 2 — Modificar GridComplexSelector

1. No `_build_selector()`:
   - Ler `allow_checked`, `checked_text`, `checked_default` do `field_config`
   - Passar para o construtor do `ComplexSelector`

2. API pública nova:
   - `get_checked_state(label) → bool`
   - `set_checked_state(label, checked)`

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
   from ..resources.widgets.grid.GridComplexSelector import GridComplexSelector
   from ..resources.widgets.grid.GridDoubleSpin import GridDoubleSpin
   from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
   from ..resources.widgets.CollapsibleParametersWidget import CollapsibleParametersWidget
   from ..resources.widgets.SeparatorWidget import SeparatorWidget
   ```

2. **`_build_ui()` — estrutura completa:**
   ```python
   def _build_ui(self, **kwargs):
       super()._build_ui(
           title=STR.GENERATE_TRAIL_TITLE,
           icon_path="gerar_rastro.ico",
           enable_scroll=True,
       )

       # ── GridComplexSelector: Input + Output ─────────────
       self.grid = GridComplexSelector(
           config={
               "input_layer": {
                   "label": f"{STR.INPUT_LINE_LAYER}:",
                   "mode_type": "input",
                   "allow_file": False,
                   "allow_folder": False,
                   "layer_filters": QgsMapLayerProxyModel.LineLayer,
                   "allow_checked": True,
                   "checked_text": STR.ONLY_SELECTED_FEATURES,
                   "checked_default": False,
               },
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
       self.layout.addWidget(self.grid)

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

       # ── CollapsibleParameters: Advanced ─────────────────
       self.advanced_params = CollapsibleParametersWidget(
           title=STR.ADVANCED_PARAMETERS,
           expanded_by_default=False,
           parent=self,
       )

       # GridComplexSelector QML (dentro do collapsible)
       self.qml_grid = GridComplexSelector(
           config={
               "qml_style": {
                   "label": f"{STR.QML_STYLE}:",
                   "mode_type": "input",
                   "allow_file": True,
                   "allow_folder": False,
                   "file_filter": "QML (*.qml)",
               },
           },
           tool_key=self.TOOL_KEY,
           parent=self,
       )
       self.advanced_params.add_content(self.qml_grid)
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
       # Input path
       last_input = self.preferences.get("last_input_path", "")
       if last_input:
           self.grid.set_path("input_layer", last_input)

       # Output path
       last_output = self.preferences.get("last_output_path", "")
       if last_output:
           self.grid.set_path("output_trail", last_output)

       # Implement size
       last_tam = self.preferences.get("last_implement_length")
       if last_tam is not None:
           self.implement_spin.set_value("implement_size", float(last_tam))

       # QML path
       last_qml = self.preferences.get("last_qml_path", "")
       if last_qml:
           self.qml_grid.set_path("qml_style", last_qml)

       # Checked state
       checked = self.preferences.get("only_selected", False)
       self.grid.set_checked_state("input_layer", checked)
   ```

4. **`_save_prefs()`:**
   ```python
   def _save_prefs(self):
       self.preferences["last_input_path"] = self.grid.get_path("input_layer")
       self.preferences["last_output_path"] = self.grid.get_path("output_trail")
       self.preferences["last_implement_length"] = self.implement_spin.get_value("implement_size")
       self.preferences["last_qml_path"] = self.qml_grid.get_path("qml_style")
       self.preferences["only_selected"] = self.grid.get_checked_state("input_layer")
       self.preferences["window_width"] = self.width()
       self.preferences["window_height"] = self.height()
       Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
   ```

5. **`execute_tool()` adaptado:**
   ```python
   def execute_tool(self):
       # Input via GridComplexSelector
       input_layer = self.grid.get("input_layer").current_layer
       if not input_layer:
           QgisMessageUtil.bar_warning(self.iface, STR.SELECT_VALID_LINE_LAYER)
           return

       only_selected = self.grid.get_checked_state("input_layer")
       implement_length = self.implement_spin.get_value("implement_size")
       output_path = self.grid.get_path("output_trail")
       save_to_folder = bool(output_path)

       # QML
       qml_path = self.qml_grid.get_path("qml_style")
       qml_enabled = bool(qml_path)

       # ... resto da lógica (resolve_input_layer, process_selection, pipeline)
       # Manter lógica síncrona/assíncrona inalterada
   ```

### FASE 4 — Documentação

1. Atualizar `docs/skills/SKILL_WIDGETS2.md`:
   - Adicionar parâmetros `allow_checked`, `checked_text`, `checked_default` no ComplexSelector
   - Adicionar métodos `get_checked_state()`, `set_checked_state()` no ComplexSelector
   - Adicionar `get_checked_state(label)`, `set_checked_state(label, checked)` no GridComplexSelector
   - Documentar comportamento de bloqueio
   - Reforçar regra: plugins SEMPRE usam GridComplexSelector, nunca ComplexSelector direto

2. Atualizar `docs/plano_eliminacao_widgetfactory.md`:
   - Marcar GenerateTrailPlugin como migrado (FASE 2 item 15)

3. Atualizar `docs/ia/changelog.txt`

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Checkbox bloqueia indevidamente botão de output | Média | Alto | Testar `_update_blocked_state()` exaustivamente |
| Quebrar backward compatibility no ComplexSelector | Baixa | Alto | `allow_checked=False` por padrão, sem criar checkbox |
| GridComplexSelector não propaga allow_checked | Baixa | Médio | Adicionar parâmetro no `_build_selector()` explicitamente |
| Checked state não persiste entre sessões | Média | Baixo | Salvar em `_save_prefs()` e restaurar em `_load_prefs()` |
| ComplexSelector com checkbox + layer combo conflita | Baixa | Médio | Checkbox bloqueia TUDO, inclusive combo |
| Flake8 F401 em imports não usados | Média | Baixo | Rodar flake8 após mudanças |
| output_path vazio se input não selecionado | Alta | Alto | Fallback: mesmo diretório do projeto |

---

## 8. Checklist de Implementação

```
[ ] FASE 1: Modificar ComplexSelector
  [ ] 1.1 Adicionar parâmetros: allow_checked (False), checked_text (""), checked_default (False)
  [ ] 1.2 No _build_ui(): inserir QCheckBox sem texto entre stack e botões
  [ ] 1.3 Criar _on_checked_toggled() e _update_blocked_state()
  [ ] 1.4 Adicionar sub-label abaixo do layout principal
  [ ] 1.5 API: get_checked_state(), set_checked_state()
  [ ] 1.6 Default False, backward compatibility mantida

[ ] FASE 2: Modificar GridComplexSelector
  [ ] 2.1 No _build_selector(): ler allow_checked, checked_text, checked_default do config
  [ ] 2.2 Passar para ComplexSelector
  [ ] 2.3 API: get_checked_state(label), set_checked_state(label, checked)

[ ] FASE 3: Reescrever GenerateTrailPlugin
  [ ] 3.1 Remover imports antigos (WidgetFactory, engine_tasks)
  [ ] 3.2 Adicionar imports: GridComplexSelector, GridDoubleSpin, GridExecutionButtons,
  [ ]     CollapsibleParametersWidget, SeparatorWidget
  [ ] 3.3 Reescrever _build_ui():
       [ ] GridComplexSelector principal: input_layer (LineLayer + allow_checked) + output_trail
       [ ] GridDoubleSpin implement_size
       [ ] CollapsibleParametersWidget + GridComplexSelector qml_style
       [ ] GridExecutionButtons run/close/info
  [ ] 3.4 Adaptar _load_prefs() para widgets API
  [ ] 3.5 Adaptar _save_prefs() para widgets API
  [ ] 3.6 Adaptar execute_tool() para widgets API
  [ ] 3.7 Manter lógica de negócio (pipeline sync/async) inalterada

[ ] FASE 4: Pós-implementação
  [ ] 4.1 Atualizar docs/skills/SKILL_WIDGETS2.md (novos params + API)
  [ ] 4.2 Atualizar docs/plano_eliminacao_widgetfactory.md (marcar migrado)
  [ ] 4.3 Atualizar docs/ia/changelog.txt
  [ ] 4.4 Rodar flake8 (sem F401, W292)
  [ ] 4.5 Testar GenerateTrailPlugin completo (sync + async)
  [ ] 4.6 Testar backward compatibility do ComplexSelector sem allow_checked
```

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-27 | 1.0.0 | Criação inicial |
| 2026-07-27 | 2.0.0 | Correções: input+output no MESMO GridComplexSelector; QML via GridComplexSelector separado (nunca ComplexSelector direto); `allow_feicoes` renomeado para `allow_checked`/`checked_text`/`checked_default` (via config dict, sem property); API simplificada para `get_checked_state()`/`set_checked_state()` |