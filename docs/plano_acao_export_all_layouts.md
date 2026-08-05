# 🎯 PLANO DE AÇÃO: Refatoração ExportAllLayouts — Novo Sistema de Widgets

**Objetivo:** Migrar `ExportAllLayouts` da `WidgetFactory` para o novo sistema de widgets autoconfiguráveis (`resources/widgets/`), eliminando dependências do sistema antigo.

**Data:** 2026-07-24
**Versão:** 2.0.0
**Autor:** Cadmus Engineering
**Status:** ⏳ Planejamento (aguardando validação)

---

## Sumário

1. [Widgets Necessários](#1-widgets-necessários)
2. [Modelo Proposto para ExportAllLayouts](#2-modelo-proposto-para-exportalllayouts)
3. [Novos Widgets a Criar](#3-novos-widgets-a-criar)
4. [Arquivos Afetados](#4-arquivos-afetados)
5. [Estratégia de Implementação](#5-estratégia-de-implementação)
6. [Contrato description/tooltip e callbacks](#6-contrato-descriptiontooltip-e-callbacks)
7. [Riscos e Mitigações](#7-riscos-e-mitigações)
8. [Checklist de Implementação](#8-checklist-de-implementação)

---

## 1. Widgets Necessários

| Widget Atual (WidgetFactory) | Novo Widget (widgets/) | Status |
|---|---|---|
| `create_checkbox_grid()` — Export Options (PDF, PNG, Merge, Replace) | **`GridCheckbox`** 🆕 | ⬜ Criar |
| `create_input_fields_widget()` — Max Width (int, default 3500) | **`GridDoubleSpin`** 🆕 | ⬜ Criar |
| `create_path_selector()` — Output Folder (folder mode) | **`GridComplexSelector`** 🆕 | ⬜ **Usar lógica do antigo `resources/widgets/grid/GridComplexSelector.py` como referência** |
| `create_bottom_action_buttons()` — Run/Close/Info | **`GridExecutionButtons`** ✅ (já existe) | ✅ Usar existente |

### 🧩 GridComplexSelector — Comportamento

Baseado no `GridComplexSelector` existente em `resources/widgets/grid/`, adaptado para widgets:
- **subfolder = "exports"** (subpasta padrão)
- **SEM parent** — seletor independente, sem linking
- **mode = "folder"** — seleciona pasta, não arquivo
- **LogUtils** com ToolKey recebido

---

## 2. Modelo Proposto para ExportAllLayouts

Layout do diálogo (top → bottom):

```
┌─────────────────────────────────────┐
│  AppBar: "Exportar Todos os Layouts" │
├─────────────────────────────────────┤
│                                     │
│  ┌─ GridCheckbox ─────────────────┐ │
│  │  Opções de Exportação           │ │
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
│  │  [⚙️] [ℹ️] [Fechar] [Exportar] │ │
│  └────────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

> **Nota sobre GridExecutionButtons:** A ordem dos botões é definida internamente pelo widget. O plugin apenas passa parâmetros: `enable_config_button`, `enable_info`, `enable_close_button` e o botão de ação no `config`.

---

## 3. Novos Widgets a Criar

### 3.1 GridCheckbox

```python
# resources/widgets/grid/GridCheckbox.py
```

Container de checkboxes configurável via dict. Substitui `WidgetFactory.create_checkbox_grid()`.

**Interface proposta:**

```python
self.checkbox_widget = GridCheckbox(
    config={
        "export_pdf": {
            "label": "Exportar PDF",
            "description": "Exporta layouts em formato PDF",  # tooltip
            "default": True,
            "onchange": self.on_export_pdf_changed,  # opcional
        },
        "export_png": {
            "label": "Exportar PNG",
            "description": "Exporta layouts em formato PNG",  # tooltip
            "default": False,
        },
        "merge_pdf": {
            "label": "Mesclar PDFs",
            "description": "Combina todos os PDFs em um único arquivo",
            "default": False,
        },
        "merge_png": {
            "label": "Mesclar PNGs",
            "description": "Combina todos os PNGs em um único PDF",
            "default": False,
        },
        "replace_existing": {
            "label": "Substituir existentes",
            "description": "Substitui arquivos existentes sem criar cópias numeradas",
            "default": False,
        },
    },
    title="Opções de Exportação",      # título do grupo (opcional)
    items_per_row=2,                    # padrão 2
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
| `config` | dict | `{}` | Dict: chave = identificador, valor = `{"label" obrigatório, "description" opcional, "default" opcional, "onchange" opcional}` |
| `title` | str | `""` | Título opcional do grupo (QGroupBox) |
| `items_per_row` | int | `2` | Itens por linha no grid |
| `separator_top` | bool | `False` | Separador acima |
| `separator_bottom` | bool | `False` | Separador abaixo |
| `parent` | QWidget | `None` | Widget pai |

**Composição interna:**
- `QGroupBox` se `title` for definido
- Layout em grid com `items_per_row` colunas
- Cada item: `SimpleCheckbox` com tooltip = `description`
- `onchange` conectado ao `toggled` do checkbox
- `SeparatorWidget` se `separator_top/bottom`

### SimpleCheckbox

```python
# resources/widgets/simple/SimpleCheckbox.py (NOVO)
```

```python
class SimpleCheckbox(QCheckBox):
    """QCheckBox com AppStyles.checkbox()."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet(AppStyles.checkbox())
```

### 3.2 GridDoubleSpin

```python
# resources/widgets/grid/GridDoubleSpin.py
```

Container de campos numéricos (double/int) com título. Substitui `WidgetFactory.create_input_fields_widget()`.

**Interface proposta:**

```python
self.max_width_input = GridDoubleSpin(
    config={
        "max_width": {
            "label": "Largura Máx. PNG",
            "description": "Largura máxima em pixels para exportação PNG",  # tooltip
            "value": 3500,
            "min": 100,
            "max": 10000,
            "step": 100,
            "decimals": 0,
            "type": "int",               # "int" ou "double"
            "onchange": self.on_max_width_changed,  # opcional: callback(value)
        },
    },
    title="Configurações de imagem",   # título do grupo (opcional)
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
| `config` | dict | `{}` | Dict: chave = identificador, valor = `{"label" obrigatório, "description" opcional, "value" opcional, "min" opcional, "max" opcional, "step" opcional, "decimals" opcional, "type" opcional, "onchange" opcional}` |
| `title` | str | `""` | Título opcional do grupo (QGroupBox) |
| `separator_top` | bool | `False` | Separador acima |
| `separator_bottom` | bool | `False` | Separador abaixo |
| `parent` | QWidget | `None` | Widget pai |

**Composição interna:**
- `QGroupBox` se `title` for definido
- Cada campo: `SimpleLabel` (label) + `SimpleDoubleSpinBox`
- `SimpleLabel` com tooltip = `description`
- `onchange` conectado ao `valueChanged` do spin box
- `SeparatorWidget` se `separator_top/bottom`

### SimpleDoubleSpinBox

```python
# resources/widgets/simple/SimpleDoubleSpinBox.py (NOVO)
```

```python
class SimpleDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox com AppStyles.input(). type="int" vira QSpinBox."""
    def __init__(
        self,
        value=0,
        min_val=0,
        max_val=999999,
        step=1,
        decimals=0,
        type_spec="double",   # "int" → QSpinBox, "double" → QDoubleSpinBox
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

> Se `type="int"`, usa `QSpinBox` em vez de `QDoubleSpinBox` (decimals=0, sem casas decimais).

### 3.3 GridComplexSelector (widgets)

```python
# resources/widgets/grid/GridComplexSelector.py (NOVO — baseado no antigo resources/widgets/grid/GridComplexSelector.py)
```

Seletor de pasta/arquivo com subfolder, simplificado para o novo sistema.

**Interface proposta:**

```python
self.folder_selector = GridComplexSelector(
    config={
        "output_folder": {
            "label": "Pasta de saída",
            "description": "Pasta onde os arquivos exportados serão salvos",
            "path": default_path,
            "mode": "folder",
            "subfolder": "exports",
        },
    },
    tool_key=self.TOOL_KEY,        # para LogUtils
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
| `set_path(key, path)` | Define path de um seletor específico |

**Parâmetros do construtor:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict: chave = identificador, valor = `{"label" obrigatório, "description" opcional, "path" opcional, "mode" opcional ("folder"/"file"), "subfolder" opcional}` |
| `tool_key` | ToolKey/str | `None` | Para LogUtils |
| `separator_top` | bool | `False` | Separador acima |
| `separator_bottom` | bool | `False` | Separador abaixo |
| `parent` | QWidget | `None` | Widget pai |

**Composição interna** (baseada no antigo `GridComplexSelector`):
- `SimpleLabel` com o título (label) + tooltip = description
- `SimpleQLineEdit` readonly exibindo o caminho
- `SimpleModernButton` para abrir o seletor (QFileDialog)
- Se `subfolder="exports"`, o path armazenado = `{selected}/{subfolder}`
- `LogUtils` com `tool_key` recebido

---

## 4. Arquivos Afetados

### Arquivos a criar (3 novos Simple + 3 novos Grid = 6 arquivos)

```
resources/widgets/simple/SimpleCheckbox.py         🆕 NOVO
resources/widgets/simple/SimpleDoubleSpinBox.py    🆕 NOVO
resources/widgets/grid/GridCheckbox.py              🆕 NOVO
resources/widgets/grid/GridDoubleSpin.py            🆕 NOVO
resources/widgets/grid/GridComplexSelector.py       🆕 NOVO (baseado no antigo)
```

### Arquivos a modificar

| Arquivo | Tipo de Mudança | Descrição |
|---------|----------------|-----------|
| `plugins/ExportAllLayouts.py` | Modificar | Substituir WidgetFactory por widgets |
| `docs/skills/SKILL_WIDGETS2.md` | Atualizar | Adicionar catálogo: GridCheckbox, GridDoubleSpin, GridComplexSelector |
| `docs/plano_eliminacao_widgetfactory.md` | Atualizar | Marcar ExportAllLayouts como migrado |
| `docs/ia/changelog.txt` | Atualizar | Registrar nova versão |

### Dependências entre arquivos

```
ExportAllLayouts.py
  ├── GridCheckbox.py        → SimpleCheckbox.py
  ├── GridDoubleSpin.py      → SimpleDoubleSpinBox.py + SimpleLabel.py
  ├── GridComplexSelector.py → SimpleQLineEdit.py (já existe)
  │                          → SimpleModernButton.py (já existe)
  │                          → SimpleLabel.py (já existe)
  └── GridExecutionButtons.py (já existe)
      → SimpleModernButton.py (já existe)
```

---

## 5. Estratégia de Implementação

### FASE 1 — Simple Widgets (2 arquivos)

1. **SimpleCheckbox.py** — `QCheckBox` com `AppStyles.checkbox()`
2. **SimpleDoubleSpinBox.py** — `QDoubleSpinBox` (ou `QSpinBox` se type=int) com `AppStyles.input()`

### FASE 2 — Grid Widgets (3 arquivos)

3. **GridCheckbox.py** — Grid de checkboxes
   - `config` dict com `label`, `description` (tooltip), `default`, `onchange`
   - `title` opcional (QGroupBox)
   - `items_per_row` para número de colunas
   - API: `is_checked()`, `set_checked()`, `get_all_states()`, `widget()`

4. **GridDoubleSpin.py** — Container de campos numéricos
   - `config` dict com `label`, `description` (tooltip), `value`, `min`, `max`, `step`, `decimals`, `type` ("int"/"double"), `onchange`
   - `title` opcional (QGroupBox)
   - API: `get_value()`, `set_value()`, `get_all_values()`

5. **GridComplexSelector.py** — Seletor de pasta/arquivo
   - Baseado no antigo `resources/widgets/grid/GridComplexSelector.py`
   - `config` dict com `label`, `description` (tooltip), `path`, `mode`, `subfolder`
   - `tool_key` para LogUtils
   - API: `get_paths()`, `get_path()`, `set_paths()`, `set_path()`
   - Sem parent/linking — seletor independente

### FASE 3 — Refatorar ExportAllLayouts

6. **Substituir `_build_ui()`:**
   - Remover chamadas `WidgetFactory.create_checkbox_grid()` → `GridCheckbox`
   - Remover chamadas `WidgetFactory.create_input_fields_widget()` → `GridDoubleSpin`
   - Remover chamadas `WidgetFactory.create_path_selector()` → `GridComplexSelector`
   - Remover chamadas `WidgetFactory.create_bottom_action_buttons()` → `GridExecutionButtons`

7. **Adaptar `_load_prefs()`:**
   ```python
   # ANTES (WidgetFactory):
   self.checkbox_map["export_pdf"].setChecked(...)
   self.max_width_input.set_value("max_width", ...)
   self.folder_selector.set_paths([...])

   # DEPOIS (widgets):
   self.checkbox_widget.set_checked("export_pdf", ...)
   self.max_width_input.set_value("max_width", ...)
   self.folder_selector.set_paths([...])
   ```

8. **Adaptar `_save_prefs()`:**
   ```python
   # ANTES:
   self.checkbox_map["export_pdf"].isChecked()
   self.max_width_input.get_values()
   self.folder_selector.get_paths()

   # DEPOIS:
   self.checkbox_widget.is_checked("export_pdf")
   self.max_width_input.get_all_values()
   self.folder_selector.get_paths()
   ```

9. **Adaptar `execute_tool()`:**
   ```python
   # ANTES:
   export_pdf = self.checkbox_map["export_pdf"].isChecked()
   max_width_values = self.max_width_input.get_values()
   paths = self.folder_selector.get_paths()

   # DEPOIS:
   export_pdf = self.checkbox_widget.is_checked("export_pdf")
   values = self.max_width_input.get_all_values()
   max_width = int(values.get("max_width", 3500))
   paths = self.folder_selector.get_paths()
   ```

10. **Manter callbacks existentes:**
    ```python
    # Toggle merge_pdf/merge_png — conectado via widget(key).toggled
    self.checkbox_widget.widget("merge_pdf").toggled.connect(self.on_merge_pdf_changed)
    self.checkbox_widget.widget("merge_png").toggled.connect(self.on_merge_png_changed)
    ```

---

## 6. Contrato description/tooltip e callbacks

### ✅ REGRA: Todo widget Grid aceita `description` no config dict

Cada item do `config` dict DEVE aceitar `description` (opcional) que vira tooltip no widget.

```python
config={
    "export_pdf": {
        "label": "Exportar PDF",
        "description": "Exporta layouts em formato PDF",  # → tooltip
        "default": True,
    },
}
```

### ✅ REGRA: Todo widget Grid aceita `onchange` callback

Cada item do `config` dict PODE ter `onchange` callback para mudança de estado/valor.

```python
config={
    "merge_pdf": {
        "label": "Mesclar PDFs",
        "description": "Combina todos os PDFs em um único arquivo",
        "default": False,
        "onchange": self.on_merge_pdf_changed,  # callback(checked_state)
    },
}
```

### ✅ REGRA: Grid pode ter `title` (QGroupBox)

Se `title` for definido, o widget inteiro é encapsulado em `QGroupBox(title)`.

```python
GridCheckbox(
    config={...},
    title="Opções de Exportação",  # → QGroupBox
)
```

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| ComplexSelector antigo tem muita lógica desnecessária | Alta | Médio | Extrair só o necessário: subfolder, mode, sem parent/linking |
| Quebrar comportamento de subfolder "exports" | Alta | Alto | Manter mesma lógica: path = selected + "/exports" |
| Checkboxes não restaurarem estado do prefs | Média | Alto | API `set_checked()` em lote |
| Callback de merge_pdf/merge_png perdido | Alta | Médio | Manter `.widget().toggled.connect()` |
| Flake8 F401 em imports não usados | Média | Baixo | Rodar flake8 após mudanças |
| Quebrar save_prefs no closeEvent | Média | Alto | Testar fechamento e reabertura |

---

## 8. Checklist de Implementação

```
[ ] FASE 1: Simple Widgets
  [ ] 1.1 Criar SimpleCheckbox.py (QCheckBox + AppStyles.checkbox())
  [ ] 1.2 Criar SimpleDoubleSpinBox.py (QDoubleSpinBox/QSpinBox + AppStyles.input())

[ ] FASE 2: Grid Widgets
  [ ] 2.1 Criar GridCheckbox.py
       [ ] config dict: label, description, default, onchange
       [ ] title opcional (QGroupBox)
       [ ] items_per_row
       [ ] API: is_checked, set_checked, get_all_states, widget(key)
       [ ] description → tooltip no checkbox
       [ ] onchange → conectado ao toggled
  [ ] 2.2 Criar GridDoubleSpin.py
       [ ] config dict: label, description, value, min, max, step, decimals, type, onchange
       [ ] title opcional (QGroupBox)
       [ ] API: get_value, set_value, get_all_values
       [ ] description → tooltip no label
       [ ] onchange → conectado ao valueChanged
  [ ] 2.3 Criar GridComplexSelector.py (widgets)
       [ ] Baseado no antigo resources/widgets/grid/GridComplexSelector.py
       [ ] config dict: label, description, path, mode, subfolder
       [ ] subfolder = "exports"
       [ ] tool_key para LogUtils
       [ ] API: get_paths, get_path, set_paths, set_path
       [ ] description → tooltip
       [ ] Sem parent/linking
  [ ] 2.4 Verificar compatibilidade Qt5/Qt6 nos widgets novos

[ ] FASE 3: Refatorar ExportAllLayouts
  [ ] 3.1 Remover imports: WidgetFactory
  [ ] 3.2 Adicionar imports: GridCheckbox, GridDoubleSpin, GridComplexSelector, GridExecutionButtons
  [ ] 3.3 Reescrever _build_ui() com widgets
       [ ] GridCheckbox com 5 opções (PDF, PNG, Merge PDF, Merge PNG, Replace)
       [ ] GridDoubleSpin com max_width
       [ ] GridComplexSelector com subfolder="exports"
       [ ] GridExecutionButtons: config, info, close
  [ ] 3.4 Adaptar _load_prefs() para nova API
  [ ] 3.5 Adaptar _save_prefs() para nova API
  [ ] 3.6 Adaptar execute_tool() para novos getters
  [ ] 3.7 Manter callbacks: on_merge_pdf_changed, on_merge_png_changed
       [ ] self.checkbox_widget.widget("merge_pdf").toggled.connect(...)
       [ ] self.checkbox_widget.widget("merge_png").toggled.connect(...)
  [ ] 3.8 Executar flake8 em todos os arquivos modificados (sem F401, W292)

[ ] Pós-implementação
  [ ] 4.1 Atualizar docs/skills/SKILL_WIDGETS2.md
       [ ] Adicionar SimpleCheckbox ao catálogo Simple
       [ ] Adicionar SimpleDoubleSpinBox ao catálogo Simple
       [ ] Adicionar GridCheckbox ao catálogo Grid
       [ ] Adicionar GridDoubleSpin ao catálogo Grid
       [ ] Adicionar GridComplexSelector ao catálogo Grid
       [ ] Documentar contrato description/tooltip e onchange
  [ ] 4.2 Atualizar docs/plano_eliminacao_widgetfactory.md (marcar ExportAllLayouts)
  [ ] 4.3 Atualizar docs/ia/changelog.txt
  [ ] 4.4 Testar fluxo completo: abrir → carregar prefs → alterar → fechar → reabrir
  [ ] 4.5 Testar exportação real com PDF e PNG
  [ ] 4.6 Testar merge PDF (PyPDF2) e merge PNG (Pillow)
  [ ] 4.7 Verificar nenhum import não utilizado (F401)
```

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-24 | 1.0.0 | Criação inicial |
| 2026-07-24 | 2.0.0 | **Revisão completa:** GridComplexSelector baseado no antigo `resources/widgets/grid/GridComplexSelector.py`; GridCheckbox e GridDoubleSpin agora com `description`=tooltip e `onchange` callback por item; `title` opcional via QGroupBox; GridExecutionButtons sem ordem fixa; adicionado contrato description/onchange e atualização da SKILL_WIDGETS2.md |