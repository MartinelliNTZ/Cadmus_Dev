# 🎯 PLANO DE AÇÃO: Refatoração ExportAllLayouts — Novo Sistema de Widgets

**Objetivo:** Migrar `ExportAllLayouts` da `WidgetFactory` para o novo sistema de widgets autoconfiguráveis (`resources/new_widgets/`), eliminando dependências do sistema antigo e criando os widgets faltantes.

**Data:** 2026-07-24
**Versão:** 1.0.0
**Autor:** Cadmus Engineering
**Status:** ⏳ Planejamento (aguardando validação)

---

## Sumário

1. [Widgets Necessários](#1-widgets-necessários)
2. [Modelo Proposto para ExportAllLayouts](#2-modelo-proposto-para-exportalllayouts)
3. [Novos Widgets a Criar](#3-novos-widgets-a-criar)
4. [Arquivos Afetados](#4-arquivos-afetados)
5. [Estratégia de Implementação](#5-estratégia-de-implementação)
6. [Riscos e Mitigações](#6-riscos-e-mitigações)
7. [Checklist de Implementação](#7-checklist-de-implementação)

---

## 1. Widgets Necessários

Com base na análise do código atual de `ExportAllLayouts.py` e no modelo solicitado pelo usuário:

| Widget Atual (WidgetFactory) | Novo Widget (new_widgets/) | Status |
|---|---|---|
| `create_checkbox_grid()` — Export Options (PDF, PNG, Merge, Replace) | **`GridCheckbox`** 🆕 | ⬜ Criar |
| `create_input_fields_widget()` — Max Width (int, default 3500) | **`GridDoubleSpin`** 🆕 | ⬜ Criar |
| `create_path_selector()` — Output Folder (folder mode, subfolder "exports") | **`GridComplexSelector`** 🆕 | ⬜ Criar |
| `create_bottom_action_buttons()` — Run/Close/Info | **`GridExecutionButtons`** ✅ (já existe) | ✅ Usar existente |

### 🧩 GridComplexSelector — Comportamento Especial

O usuário especificou que este widget deve:
- Ser um **seletor de pasta** com comportamento especial
- **subfolder = "exports"** (subpasta padrão)
- **SEM parent** — ou seja, não usa `parent` como filtro de diretório
- Funcionar como seletor de pasta com caminho base + "/exports"

---

## 2. Modelo Proposto para ExportAllLayouts

Layout do diálogo (top → bottom):

```
┌─────────────────────────────────────┐
│  AppBar: "Exportar Todos os Layouts" │
├─────────────────────────────────────┤
│                                     │
│  ┌─ GridCheckbox ─────────────────┐ │
│  │  ☐ Exportar PDF                │ │
│  │  ☐ Exportar PNG                │ │
│  │  ☐ Mesclar PDFs                │ │
│  │  ☐ Mesclar PNGs                │ │
│  │  ☐ Substituir existentes       │ │
│  └────────────────────────────────┘ │
│                                     │
│  ┌─ GridDoubleSpin ───────────────┐ │
│  │  Largura Máx. PNG: [3500]      │ │
│  └────────────────────────────────┘ │
│                                     │
│  ┌─ GridComplexSelector ──────────┐ │
│  │  Pasta de saída: [C://...] 📁  │ │
│  │  (subfolder = exports)          │ │
│  └────────────────────────────────┘ │
│                                     │
│  ┌─ GridExecutionButtons ─────────┐ │
│  │        [⚙️] [?] [Fechar] [Exportar]  │ │
│  └────────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

### Ordem dos botões no GridExecutionButtons

Conforme solicitado:
1. **⚙️ Settings** → `enable_config_button=True` (abre SettingsPlugin)
2. **ℹ️ Info** → `enable_info=True` (instruções via tool_key)
3. **Fechar** → `enable_close_button=True`
4. **Exportar** → botão `is_run_button=True` com callback `self.execute_tool`

---

## 3. Novos Widgets a Criar

### 3.1 GridCheckbox

```python
# resources/new_widgets/grid/GridCheckbox.py
```

Container de checkboxes configurável via dict. Substitui `WidgetFactory.create_checkbox_grid()`.

**Interface proposta:**

```python
from ..resources.new_widgets.grid.GridCheckbox import GridCheckbox

self.checkbox_widget = GridCheckbox(
    config={
        "export_pdf": {
            "label": "Exportar PDF",
            "default": True,
            "callback": self.on_checkbox_changed,  # opcional, por item
            "description": "Exporta layouts em formato PDF",
        },
        "export_png": {
            "label": "Exportar PNG",
            "default": False,
        },
        # ... mais opções
    },
    items_per_row=2,             # opcional, default 2
    title="Opções de Exportação", # opcional, título do grupo
    separator_top=False,
    separator_bottom=True,
    parent=self,
)
self.layout.addWidget(self.checkbox_widget)

# API pública
self.checkbox_widget.is_checked("export_pdf")     # → bool
self.checkbox_widget.set_checked("export_pdf", True)
self.checkbox_widget.get_all_checked()            # → dict {key: bool}
self.checkbox_widget.widget("export_pdf")         # → QCheckBox
```

**Parâmetros do construtor:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict de checkboxes. Chave = identificador, valor = `{"label", "default", "callback", "description"}` |
| `items_per_row` | int | `2` | Itens por linha no grid |
| `title` | str | `""` | Título opcional do grupo |
| `separator_top` | bool | `False` | Separador acima |
| `separator_bottom` | bool | `False` | Separador abaixo |
| `parent` | QWidget | `None` | Widget pai |

**Composição interna:**
- Usa `SimpleCheckbox` 🆕 (Simple) para cada checkbox individual
- Layout em grid/matrix com `items_per_row` colunas
- `SeparatorWidget` se `separator_top/bottom`

### SimpleCheckbox

```python
# resources/new_widgets/simple/SimpleCheckbox.py (NOVO)
```

Checkbox individual com `AppStyles.checkbox()`. (Também usado por outros widgets internamente.)

### 3.2 GridDoubleSpin

```python
# resources/new_widgets/grid/GridDoubleSpin.py
```

Container de campos numéricos (double/int) com título. Substitui `WidgetFactory.create_input_fields_widget()`.

**Interface proposta:**

```python
from ..resources.new_widgets.grid.GridDoubleSpin import GridDoubleSpin

self.max_width_input = GridDoubleSpin(
    config={
        "max_width": {
            "label": "Largura Máx. PNG",
            "value": 3500,
            "min": 100,
            "max": 10000,
            "step": 100,
            "decimals": 0,
            "type": "int",           # "int" ou "double"
        },
    },
    separator_top=False,
    separator_bottom=True,
    parent=self,
)
self.layout.addWidget(self.max_width_input)

# API pública
self.max_width_input.get_value("max_width")   # → int/float
self.max_width_input.set_value("max_width", 3500)
```

**Parâmetros do construtor:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict de campos. Chave = identificador, valor = `{"label", "value", "min", "max", "step", "decimals", "type"}` |
| `separator_top` | bool | `False` | Separador acima |
| `separator_bottom` | bool | `False` | Separador abaixo |
| `parent` | QWidget | `None` | Widget pai |

**Composição interna:**
- Usa `SimpleDoubleSpinBox` 🆕 (Simple) — `QDoubleSpinBox` com `AppStyles.input()`
- Cada campo: layout horizontal com `SimpleLabel` + `SimpleDoubleSpinBox`
- `SeparatorWidget` se `separator_top/bottom`

### SimpleDoubleSpinBox

```python
# resources/new_widgets/simple/SimpleDoubleSpinBox.py (NOVO)
```
tem um label tambem com titulo individual 
`QDoubleSpinBox` (ou `QSpinBox` se type=int) com estilo `AppStyles.input()`.

### 3.3 GridComplexSelector

## 4. Arquivos Afetados

### Arquivos a criar (3 novos Simple + 3 novos Grid = 6 arquivos)

```
resources/new_widgets/simple/SimpleCheckbox.py        🆕 NOVO
resources/new_widgets/simple/SimpleDoubleSpinBox.py   🆕 NOVO
resources/new_widgets/grid/GridCheckbox.py             🆕 NOVO
resources/new_widgets/grid/GridDoubleSpin.py           🆕 NOVO
resources/new_widgets/grid/GridComplexSelector.py      🆕 NOVO
```

### Arquivos a modificar

| Arquivo | Tipo de Mudança | Descrição |
|---------|----------------|-----------|
| `plugins/ExportAllLayouts.py` | Modificar | Substituir WidgetFactory por new_widgets. Remover imports: WidgetFactory, ProgressDialog (checar). Adicionar imports: GridCheckbox, GridDoubleSpin, GridComplexSelector, GridExecutionButtons. |
| `docs/plano_eliminacao_widgetfactory.md` | Atualizar | Marcar ExportAllLayouts como migrado (FASE 2 - item 6). Atualizar TODO interno. |
| `docs/ia/changelog.txt` | Atualizar | Registrar nova versão com a migração. |

### Dependências entre arquivos

```
ExportAllLayouts.py
  ├── GridCheckbox.py        → SimpleCheckbox.py
  ├── GridDoubleSpin.py      → SimpleDoubleSpinBox.py
  ├── GridComplexSelector.py → SimpleQLineEdit.py (já existe)
  │                          → SimpleModernButton.py (já existe)
  └── GridExecutionButtons.py (já existe)
      → SimpleModernButton.py (já existe)
```

---

## 5. Estratégia de Implementação

### FASE 1 — Criar Simple Widgets (2 arquivos)

1. `SimpleCheckbox.py` — `QCheckBox` + `AppStyles.checkbox()`
2. `SimpleDoubleSpinBox.py` — `QDoubleSpinBox` com `AppStyles.input()`, suporte a int/double, min/max/step/decimals

### FASE 2 — Criar Grid Widgets (3 arquivos)

3. `GridCheckbox.py` — Layout de checkboxes em grid com `items_per_row`
4. `GridDoubleSpin.py` — Container de campos numéricos
5. `GridComplexSelector.py` — Seletor de pasta/arquivo com subfolder

### FASE 3 — Refatorar ExportAllLayouts

6. Substituir imports da `WidgetFactory` pelos novos widgets
7. Adaptar `_build_ui()` para usar `self.layout.addWidget()` (não `self.layout.add_items()`)
8. Adaptar `_load_prefs()` e `_save_prefs()` para a nova API
9. Adaptar `execute_tool()` para usar a nova API dos widgets
10. Verificar se `ProgressDialog` precisa continuar sendo importado
11. Remover imports não utilizados
12. Testar funcionalidade completa

### Observações Importantes

- `enable_scroll=False` no ExportAllLayouts atual → permanece `False`
- `add_execution_buttons()` do MainLayout coloca botões fixos na parte inferior
- Todos os widgets devem ser adicionados via `self.layout.addWidget(widget)` (não add_items)
- `SeparatorWidget` entre widgets conforme necessário (widgets podem ter `separator_top/bottom`)

---

## 6. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Quebrar comportamento de subfolder "exports" | Alta | Alto | Testar path selecionado + subfolder manualmente |
| Checkboxes não restaurarem estado do prefs | Média | Alto | API `set_checked()` deve funcionar em lote |
| DoubleSpin não carregar valor salvo | Média | Médio | API `set_value()` testada |
| ComplexSelector não funcionar com `set_paths()` | Média | Médio | Usar `get_paths()` para consistência com antigo |
| Callback de merge_pdf/merge_png perdido | Alta | Médio | Manter lógica de toggle connect no ExportAllLayouts |
| Esquecer de remover imports não usados | Média | Baixo | Flake8 F401 detecta |
| Quebrar save_prefs no closeEvent | Média | Alto | Testar fechamento e reabertura |

---

## 7. Checklist de Implementação

```
[ ] FASE 1: Simple Widgets
  [ ] 1.1 Criar SimpleCheckbox.py (QCheckBox + AppStyles.checkbox())
  [ ] 1.2 Criar SimpleDoubleSpinBox.py (QDoubleSpinBox + AppStyles.input())

[ ] FASE 2: Grid Widgets
  [ ] 2.1 Criar GridCheckbox.py (Grid de checkboxes, items_per_row, title, config dict)
  [ ] 2.2 Criar GridDoubleSpin.py (Container de spin boxes, config dict)
  [ ] 2.3 Criar GridComplexSelector.py (Seletor pasta/arquivo, subfolder="exports", sem parent)
  [ ] 2.4 Verificar compatibilidade Qt5/Qt6 nos widgets novos

[ ] FASE 3: Refatorar ExportAllLayouts
  [ ] 3.1 Remover imports: WidgetFactory, ProgressDialog (se não usado mais)
  [ ] 3.2 Adicionar imports: GridCheckbox, GridDoubleSpin, GridComplexSelector
  [ ] 3.3 Reescrever _build_ui() com new_widgets
       [ ] GridCheckbox com opções de exportação (PDF, PNG, Merge, Replace)
       [ ] GridDoubleSpin com max_width
       [ ] GridComplexSelector com subfolder="exports"
       [ ] GridExecutionButtons: settings, info, fechar, exportar
  [ ] 3.4 Adaptar _load_prefs() para nova API
  [ ] 3.5 Adaptar _save_prefs() para nova API
  [ ] 3.6 Adaptar execute_tool() para novos getters
  [ ] 3.7 Manter callbacks: on_merge_pdf_changed, on_merge_png_changed
  [ ] 3.8 Verificar se SeparatorWidget é necessário entre seções
  [ ] 3.9 Executar flake8 no ExportAllLayouts.py modificado

[ ] Pós-implementação
  [ ] 4.1 Atualizar docs/plano_eliminacao_widgetfactory.md (marcar ExportAllLayouts como migrado)
  [ ] 4.2 Atualizar docs/ia/changelog.txt
  [ ] 4.3 Testar fluxo completo: abrir → carregar prefs → alterar → fechar → reabrir
  [ ] 4.4 Testar exportação real com PDF e PNG
  [ ] 4.5 Testar merge PDF (PyPDF2) e merge PNG (Pillow)
  [ ] 4.6 Verificar nenhum import não utilizado (F401)
```

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-24 | 1.0.0 | Criação inicial — Plano de ação para refatoração do ExportAllLayouts |
</content>
</write_question>

Wait — I need to switch to the proper tool. Let me use write_to_file.

<write_to_file>
<path>docs/plano_acao_export_all_layouts.md</path>
<content>
# 🎯 PLANO DE AÇÃO: Refatoração ExportAllLayouts — Novo Sistema de Widgets

**Objetivo:** Migrar `ExportAllLayouts` da `WidgetFactory` para o novo sistema de widgets autoconfiguráveis (`resources/new_widgets/`), eliminando dependências do sistema antigo e criando os widgets faltantes.

**Data:** 2026-07-24
**Versão:** 1.0.0
**Autor:** Cadmus Engineering
**Status:** ⏳ Planejamento (aguardando validação)

---

## Sumário

1. [Widgets Necessários](#1-widgets-necessários)
2. [Modelo Proposto para ExportAllLayouts](#2-modelo-proposto-para-exportalllayouts)
3. [Novos Widgets a Criar](#3-novos-widgets-a-criar)
4. [Arquivos Afetados](#4-arquivos-afetados)
5. [Estratégia de Implementação](#5-estratégia-de-implementação)
6. [Riscos e Mitigações](#6-riscos-e-mitigações)
7. [Checklist de Implementação](#7-checklist-de-implementação)

---

## 1. Widgets Necessários

Com base na análise do código atual de `ExportAllLayouts.py` e no modelo solicitado pelo usuário:

| Widget Atual (WidgetFactory) | Novo Widget (new_widgets/) | Status |
|---|---|---|
| `create_checkbox_grid()` — Export Options (PDF, PNG, Merge, Replace) | **`GridCheckbox`** 🆕 | ⬜ Criar |
| `create_input_fields_widget()` — Max Width (int, default 3500) | **`GridDoubleSpin`** 🆕 | ⬜ Criar |
| `create_path_selector()` — Output Folder (folder mode, subfolder "exports") | **`GridComplexSelector`** 🆕 | ⬜ Criar |
| `create_bottom_action_buttons()` — Run/Close/Info | **`GridExecutionButtons`** ✅ (já existe) | ✅ Usar existente |

### 🧩 GridComplexSelector — Comportamento Especial

O usuário especificou que este widget deve:
- Ser um **seletor de pasta** com comportamento especial
- **subfolder = "exports"** (subpasta padrão)
- **SEM parent** — ou seja, não usa `parent` como filtro de diretório
- Funcionar como seletor de pasta com caminho base + "/exports"

---

## 2. Modelo Proposto para ExportAllLayouts

Layout do diálogo (top → bottom):

```
┌─────────────────────────────────────┐
│  AppBar: "Exportar Todos os Layouts" │
├─────────────────────────────────────┤
│                                     │
│  ┌─ GridCheckbox ─────────────────┐ │
│  │  ☐ Exportar PDF                │ │
│  │  ☐ Exportar PNG                │ │
│  │  ☐ Mesclar PDFs                │ │
│  │  ☐ Mesclar PNGs                │ │
│  │  ☐ Substituir existentes       │ │
│  └────────────────────────────────┘ │
│                                     │
│  ┌─ GridDoubleSpin ───────────────┐ │
│  │  Largura Máx. PNG: [3500]      │ │
│  └────────────────────────────────┘ │
│                                     │
│  ┌─ GridComplexSelector ──────────┐ │
│  │  Pasta de saída: [C://...] 📁  │ │
│  │  (subfolder = exports)          │ │
│  └────────────────────────────────┘ │
│                                     │
│  ┌─ GridExecutionButtons ─────────┐ │
│  │        [⚙️] [?] [Fechar] [Exportar]  │ │
│  └────────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

### Ordem dos botões no GridExecutionButtons

Conforme solicitado:
1. **⚙️ Settings** → `enable_config_button=True` (abre SettingsPlugin)
2. **ℹ️ Info** → `enable_info=True` (instruções via tool_key)
3. **Fechar** → `enable_close_button=True`
4. **Exportar** → botão `is_run_button=True` com callback `self._on_export`

A ordem na barra (direita para esquerda) será:
`Exportar → Fechar → ⚙️ → ℹ️`

> Nota: O `GridExecutionButtons` existente coloca os botões na ordem: `item3 → item2 → item1 → close → config → info`. Para ter a ordem desejada (Exportar, Fechar, Config, Info), os botões do config devem ser: `exportar` como único item do dict com `is_run_button=True`, e os built-ins `close`, `config`, `info` completam.

---

## 3. Novos Widgets a Criar

### 3.1 GridCheckbox

```python
# resources/new_widgets/grid/GridCheckbox.py
```

Container de checkboxes configurável via dict. Substitui `WidgetFactory.create_checkbox_grid()`.

**Interface proposta:**

```python
self.checkbox_widget = GridCheckbox(
    config={
        "export_pdf": {
            "label": "Exportar PDF",
            "default": True,
            "description": "Exporta layouts em formato PDF",
        },
        "export_png": {
            "label": "Exportar PNG",
            "default": False,
        },
        # ... mais opções
    },
    items_per_row=2,
    title="Opções de Exportação",
    separator_top=False,
    separator_bottom=True,
    parent=self,
)
self.layout.addWidget(self.checkbox_widget)
```

**API pública:**

| Método | Descrição |
|--------|-----------|
| `is_checked(key)` → `bool` | Retorna estado do checkbox |
| `set_checked(key, value)` | Define estado do checkbox |
| `get_all_states()` → `dict` | Retorna todos os estados {key: bool} |
| `widget(key)` → `QCheckBox` | Acesso direto ao QCheckBox (para signals) |

**Parâmetros do construtor:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict de checkboxes. Chave = identificador, valor = `{"label", "default", "callback", "description"}` |
| `items_per_row` | int | `2` | Itens por linha no grid |
| `title` | str | `""` | Título opcional do grupo |
| `separator_top` | bool | `False` | Separador acima |
| `separator_bottom` | bool | `False` | Separador abaixo |
| `parent` | QWidget | `None` | Widget pai |

**Composição interna:**
- Usa `SimpleCheckbox` 🆕 para cada checkbox individual
- Layout em grid/matrix com `items_per_row` colunas
- `SeparatorWidget` se `separator_top/bottom`

### SimpleCheckbox

```python
# resources/new_widgets/simple/SimpleCheckbox.py (NOVO)
```

Checkbox individual com `AppStyles.checkbox()`.

```python
class SimpleCheckbox(QCheckBox):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet(AppStyles.checkbox())
```

### 3.2 GridDoubleSpin

```python
# resources/new_widgets/grid/GridDoubleSpin.py
```

Container de campos numéricos (double/int) com título.

**Interface proposta:**

```python
self.max_width_input = GridDoubleSpin(
    config={
        "max_width": {
            "label": "Largura Máx. PNG",
            "value": 3500,
            "min": 100,
            "max": 10000,
            "step": 100,
            "decimals": 0,
        },
    },
    separator_top=False,
    separator_bottom=True,
    parent=self,
)
self.layout.addWidget(self.max_width_input)
```

**API pública:**

| Método | Descrição |
|--------|-----------|
| `get_value(key)` → `int/float` | Retorna valor atual |
| `set_value(key, value)` | Define valor |
| `get_all_values()` → `dict` | Retorna todos os valores {key: value} |

**Parâmetros do construtor:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict de campos. Chave = identificador, valor = `{"label", "value", "min", "max", "step", "decimals"}` |
| `separator_top` | bool | `False` | Separador acima |
| `separator_bottom` | bool | `False` | Separador abaixo |
| `parent` | QWidget | `None` | Widget pai |

**Composição interna:**
- Usa `SimpleDoubleSpinBox` 🆕 — `QDoubleSpinBox` com `AppStyles.input()`
- Cada campo: `SimpleLabel` + `SimpleDoubleSpinBox` em layout horizontal
- `SeparatorWidget` se `separator_top/bottom`

### SimpleDoubleSpinBox

```python
# resources/new_widgets/simple/SimpleDoubleSpinBox.py (NOVO)
```

`QDoubleSpinBox` com estilo `AppStyles.input()`.

```python
class SimpleDoubleSpinBox(QDoubleSpinBox):
    def __init__(
        self,
        value=0,
        min_val=0,
        max_val=999999,
        step=1,
        decimals=0,
        parent=None,
    ):
        super().__init__(parent)
        self.setRange(min_val, max_val)
        self.setSingleStep(step)
        self.setDecimals(decimals)
        self.setValue(value)
        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet(AppStyles.input())
```

### 3.3 GridComplexSelector

```python
# resources/new_widgets/grid/GridComplexSelector.py
```

Seletor de pasta/arquivo complexo com:
- Campo readonly (`SimpleQLineEdit`)
- Botão "Selecionar" (`SimpleModernButton`)
- **Comportamento "subfolder":** caminho armazenado = `{path_selecionado}/{subfolder}`
- **Sem parent:** caminho base livre

**Interface proposta:**

```python
self.folder_selector = GridComplexSelector(
    config={
        "output_folder": {
            "label": "Pasta de saída",
            "path": default_path,
            "mode": "folder",
            "subfolder": "exports",  # sempre adiciona /exports
        },
    },
    separator_top=False,
    separator_bottom=False,
    parent=self,
)
self.layout.addWidget(self.folder_selector)
```

**API pública:**

| Método | Descrição |
|--------|-----------|
| `get_paths()` → `list[str]` | Retorna paths (com subfolder) |
| `get_path(key)` → `str` | Retorna path específico (com subfolder) |
| `set_paths(paths)` | Define paths |

**Parâmetros do construtor:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict de seletores. Chave = identificador, valor = `{"label", "path", "mode", "subfolder"}` |
| `separator_top` | bool | `False` | Separador acima |
| `separator_bottom` | bool | `False` | Separador abaixo |
| `parent` | QWidget | `None` | Widget pai |

**Composição interna:**
- `SimpleLabel` com o título (ex: "Pasta de saída")
- `SimpleQLineEdit` readonly exibindo o caminho
- `SimpleModernButton` para abrir o seletor
- Se `subfolder="exports"`, o path real armazenado é `{selected}/exports`
- O `QLineEdit` mostra `{selected}/exports` para o usuário

---

## 4. Arquivos Afetados

### Arquivos a criar (3 novos Simple + 3 novos Grid = 6 arquivos)

```
resources/new_widgets/simple/SimpleCheckbox.py         🆕 NOVO
resources/new_widgets/simple/SimpleDoubleSpinBox.py    🆕 NOVO
resources/new_widgets/grid/GridCheckbox.py              🆕 NOVO
resources/new_widgets/grid/GridDoubleSpin.py            🆕 NOVO
resources/new_widgets/grid/GridComplexSelector.py       🆕 NOVO
```

### Arquivos a modificar

| Arquivo | Tipo de Mudança | Descrição |
|---------|----------------|-----------|
| `plugins/ExportAllLayouts.py` | Modificar | Substituir WidgetFactory por new_widgets. Remover imports: WidgetFactory, ProgressDialog (se não usado mais). Adicionar imports: GridCheckbox, GridDoubleSpin, GridComplexSelector, GridExecutionButtons. |
| `docs/plano_eliminacao_widgetfactory.md` | Atualizar | Marcar ExportAllLayouts como migrado (FASE 2 - item 6). Atualizar TODO interno. |
| `docs/ia/changelog.txt` | Atualizar | Registrar nova versão com a migração. |

### Dependências entre arquivos

```
ExportAllLayouts.py
  ├── GridCheckbox.py        → SimpleCheckbox.py
  ├── GridDoubleSpin.py      → SimpleDoubleSpinBox.py
  ├── GridComplexSelector.py → SimpleQLineEdit.py (já existe)
  │                          → SimpleModernButton.py (já existe)
  └── GridExecutionButtons.py (já existe)
      → SimpleModernButton.py (já existe)
```

---

## 5. Estratégia de Implementação

### FASE 1 — Criar Simple Widgets (2 arquivos)

1. **SimpleCheckbox.py** — `QCheckBox` com `AppStyles.checkbox()` 
   - `__init__(text, parent)`
   - `_apply_styles()` com `AppStyles.checkbox()`

2. **SimpleDoubleSpinBox.py** — `QDoubleSpinBox` com `AppStyles.input()`
   - `__init__(value, min_val, max_val, step, decimals, parent)`
   - `_apply_styles()` com `AppStyles.input()`

### FASE 2 — Criar Grid Widgets (3 arquivos)

3. **GridCheckbox.py** — Layout de checkboxes em grid
   - `config` dict com chaves identificadoras
   - `items_per_row` para número de colunas
   - `title` opcional como label do grupo
   - API: `is_checked()`, `set_checked()`, `get_all_states()`, `widget()`
   - Usa `SimpleCheckbox` internamente

4. **GridDoubleSpin.py** — Container de campos numéricos
   - `config` dict com chaves identificadoras
   - API: `get_value()`, `set_value()`, `get_all_values()`
   - Usa `SimpleDoubleSpinBox` + `SimpleLabel` internamente

5. **GridComplexSelector.py** — Seletor de pasta/arquivo
   - `config` dict com `mode`, `subfolder`
   - `subfolder` sempre adiciona subpasta ao path
   - API: `get_paths()`, `get_path()`, `set_paths()`
   - Usa `SimpleQLineEdit` + `SimpleModernButton` internamente

### FASE 3 — Refatorar ExportAllLayouts

6. **Substituir `_build_ui()`:**
   - Remover chamadas `WidgetFactory.create_checkbox_grid()`
   - Remover chamadas `WidgetFactory.create_input_fields_widget()`
   - Remover chamadas `WidgetFactory.create_path_selector()`
   - Remover chamadas `WidgetFactory.create_bottom_action_buttons()`
   - Adicionar `GridCheckbox` com opções (PDF, PNG, Merge PDF, Merge PNG, Replace)
   - Adicionar `GridDoubleSpin` com max_width
   - Adicionar `GridComplexSelector` com subfolder="exports"
   - Adicionar `GridExecutionButtons` com:
     - `enable_config_button=True` (⚙️ Settings)
     - `enable_info=True` (ℹ️ Info)
     - `enable_close_button=True` (Fechar)
     - Botão "Exportar" como `is_run_button=True` com `callback=self._on_export`

7. **Adaptar `_load_prefs()`:**
   - `self.checkbox_map["export_pdf"].setChecked(...)` → `self.checkbox_widget.set_checked("export_pdf", ...)`
   - `self.max_width_input.set_value("max_width", ...)` → mesmo padrão API
   - `self.folder_selector.set_paths([...])` → mesmo padrão API

8. **Adaptar `_save_prefs()`:**
   - `self.checkbox_map["export_pdf"].isChecked()` → `self.checkbox_widget.is_checked("export_pdf")`
   - `self.max_width_input.get_values()` → `self.max_width_input.get_all_values()`
   - `self.folder_selector.get_paths()` → mesmo padrão API

9. **Adaptar `execute_tool()`:**
   - `self.checkbox_map["export_pdf"].isChecked()` → `self.checkbox_widget.is_checked("export_pdf")`
   - `self.max_width_input.get_values()` → `self.max_width_input.get_all_values()`
   - `self.folder_selector.get_paths()` → mesmo padrão API

10. **Manter callbacks existentes:**
    - `on_merge_pdf_changed()` — conectado ao checkbox "merge_pdf"
    - `on_merge_png_changed()` — conectado ao checkbox "merge_png"
    - Conexão via `self.checkbox_widget.widget("merge_pdf").toggled.connect(self.on_merge_pdf_changed)`

### Layout Final (código resumido)

```python
def _build_ui(self, **kwargs):
    super()._build_ui(
        title=STR.EXPORT_ALL_LAYOUTS_TITLE,
        icon_path="export_icon.ico",
        enable_scroll=False,
    )

    # ── Checkboxes de Exportação ──────────────────────────────
    self.checkbox_widget = GridCheckbox(
        config={
            "export_pdf": {"label": STR.EXPORT_PDF, "default": True},
            "export_png": {"label": STR.EXPORT_PNG, "default": False},
            "merge_pdf": {"label": STR.MERGE_PDFS_FINAL, "default": False},
            "merge_png": {"label": STR.MERGE_PNGS_FINAL, "default": False},
            "replace_existing": {"label": STR.REPLACE_EXISTING_FILES, "default": False},
        },
        items_per_row=2,
        title=STR.EXPORT_OPTIONS,
        separator_top=False,
        separator_bottom=True,
        parent=self,
    )
    self.layout.addWidget(self.checkbox_widget)

    # ── Connect merge dependency checks ───────────────────────
    self.checkbox_widget.widget("merge_pdf").toggled.connect(self.on_merge_pdf_changed)
    self.checkbox_widget.widget("merge_png").toggled.connect(self.on_merge_png_changed)

    # ── Max Width ─────────────────────────────────────────────
    self.max_width_input = GridDoubleSpin(
        config={
            "max_width": {
                "label": STR.MAX_WIDTH_PNG,
                "value": 3500,
                "min": 100,
                "max": 10000,
                "step": 100,
                "decimals": 0,
            },
        },
        separator_top=False,
        separator_bottom=True,
        parent=self,
    )
    self.layout.addWidget(self.max_width_input)

    # ── Output Folder ─────────────────────────────────────────
    default_path = os.path.join(QgsProject.instance().homePath(), "exports")
    self.folder_selector = GridComplexSelector(
        config={
            "output_folder": {
                "label": STR.OUTPUT_FOLDER,
                "path": default_path,
                "mode": "folder",
                "subfolder": "exports",
            },
        },
        separator_top=False,
        separator_bottom=False,
        parent=self,
    )
    self.layout.addWidget(self.folder_selector)

    # ── Execution Buttons ─────────────────────────────────────
    self.action_buttons = GridExecutionButtons(
        config={
            "exportar": {
                "label": "Exportar",
                "description": "Inicia a exportação dos layouts",
                "callback": self._on_export,
                "is_run_button": True,
            },
        },
        enable_close_button=True,
        enable_config_button=True,
        enable_info=True,
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    self.layout.add_execution_buttons(self.action_buttons)
```

> **Nota:** `_on_export()` renomeado de `execute_tool()` para evitar conflito com o callback do `GridExecutionButtons`. Ou mantém `execute_tool` se preferir — ambos funcionam.

---

## 6. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Quebrar comportamento de subfolder "exports" | Alta | Alto | Testar path selecionado + subfolder manualmente |
| Checkboxes não restaurarem estado do prefs | Média | Alto | API `set_checked()` deve funcionar em lote |
| DoubleSpin não carregar valor salvo | Média | Médio | API `set_value()` testada |
| ComplexSelector não funcionar com `set_paths()` | Média | Médio | Usar `get_paths()` para consistência com antigo |
| Callback de merge_pdf/merge_png perdido | Alta | Médio | Manter lógica de toggle connect no ExportAllLayouts |
| Esquecer de remover imports não usados | Média | Baixo | Flake8 F401 detecta |
| Quebrar save_prefs no closeEvent | Média | Alto | Testar fechamento e reabertura |

---

## 7. Checklist de Implementação

```
[ ] FASE 1: Simple Widgets
  [ ] 1.1 Criar SimpleCheckbox.py (QCheckBox + AppStyles.checkbox())
  [ ] 1.2 Criar SimpleDoubleSpinBox.py (QDoubleSpinBox + AppStyles.input())

[ ] FASE 2: Grid Widgets
  [ ] 2.1 Criar GridCheckbox.py (Grid de checkboxes, items_per_row, title, config dict)
  [ ] 2.2 Criar GridDoubleSpin.py (Container de spin boxes, config dict)
  [ ] 2.3 Criar GridComplexSelector.py (Seletor pasta/arquivo, subfolder, sem parent)
  [ ] 2.4 Verificar compatibilidade Qt5/Qt6 nos widgets novos

[ ] FASE 3: Refatorar ExportAllLayouts
  [ ] 3.1 Remover imports: WidgetFactory
  [ ] 3.2 Adicionar imports: GridCheckbox, GridDoubleSpin, GridComplexSelector
  [ ] 3.3 Reescrever _build_ui() com new_widgets
       [ ] GridCheckbox com opções de exportação
       [ ] GridDoubleSpin com max_width
       [ ] GridComplexSelector com subfolder="exports"
       [ ] GridExecutionButtons: settings, info, fechar, exportar
  [ ] 3.4 Adaptar _load_prefs() para nova API
  [ ] 3.5 Adaptar _save_prefs() para nova API
  [ ] 3.6 Adaptar execute_tool() para novos getters
  [ ] 3.7 Manter callbacks: on_merge_pdf_changed, on_merge_png_changed
  [ ] 3.8 Verificar se SeparatorWidget é necessário entre seções
  [ ] 3.9 Executar flake8 no ExportAllLayouts.py modificado

[ ] Pós-implementação
  [ ] 4.1 Atualizar docs/plano_eliminacao_widgetfactory.md
  [ ] 4.2 Atualizar docs/ia/changelog.txt
  [ ] 4.3 Testar fluxo completo: abrir → carregar prefs → alterar → fechar → reabrir
  [ ] 4.4 Testar exportação real com PDF e PNG
  [ ] 4.5 Testar merge PDF (PyPDF2) e merge PNG (Pillow)
  [ ] 4.6 Verificar nenhum import não utilizado (F401)
```

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-24 | 1.0.0 | Criação inicial — Plano de ação para refatoração do ExportAllLayouts |