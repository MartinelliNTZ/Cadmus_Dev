# 🎯 PLANO DE AÇÃO: Migração SaveTemporaryLayersPlugin — Novo Sistema de Widgets

**Objetivo:** Migrar `SaveTemporaryLayersPlugin` da `WidgetFactory` para o novo sistema de widgets autoconfiguráveis (`resources/widgets/`), eliminando dependências do sistema antigo.

**Data:** 2026-07-27
**Versão:** 1.1.0
**Autor:** Cadmus Engineering
**Status:** ⏳ Planejamento

---

## Sumário

1. [Widgets Necessários](#1-widgets-necessários)
2. [Modelo Proposto para SaveTemporaryLayersPlugin](#2-modelo-proposto-para-savetemporarylayersplugin)
3. [Novo Widget a Criar: GridComboBox](#3-novo-widget-a-criar-gridcombobox)
4. [Arquivos Afetados](#4-arquivos-afetados)
5. [Estratégia de Implementação](#5-estratégia-de-implementação)
6. [Riscos e Mitigações](#6-riscos-e-mitigações)
7. [Checklist de Implementação](#7-checklist-de-implementação)

---

## 1. Widgets Necessários

| Widget Atual (WidgetFactory) | Novo Widget (widgets/) | Status |
|---|---|---|
| `create_input_fields_widget()` — prefix + suffix | **`GridInputFields`** | ✅ Já existe |
| `create_dropdown_selector()` x2 (vetor + raster) | **`GridComboBox`** 🆕 — **1 widget com 2 items** | ⬜ Criar |
| `create_grid_complex_selector()` — pasta saída | **`GridComplexSelector`** | ✅ Já existe |
| `create_bottom_action_buttons()` — run/close/info | **`GridExecutionButtons`** | ✅ Já existe |

### 🔍 Análise do antigo DropdownSelectorWidget

`resources/widgets/DropdownSelectorWidget.py`:
- Usa **pyqtSignal** `selectionChanged` — **viola o novo contrato** (nada de signals, só callbacks)
- API: `get_selected_key()`, `set_selected_key()`

O novo `GridComboBox` substitui por:
- **Config via dict `config={}`** com `onchange` callback
- **Sem signals Qt expostos** — plugin só passa callbacks
- **2 items no mesmo grid** (vetor + raster), não 2 grids separados

---

## 2. Modelo Proposto para SaveTemporaryLayersPlugin

Layout do diálogo (top → bottom):

```
┌────────────────────────────────────────┐
│  AppBar: "Salvar Camadas Temporárias"  │
├────────────────────────────────────────┤
│                                        │
│  ┌─ GridInputFields ─────────────────┐ │
│  │  Prefixo: [_______________]       │ │
│  │  Sufixo:  [_______________]       │ │
│  └───────────────────────────────────┘ │
│                                        │
│  ┌─ GridComboBox ────────────────────┐ │
│  │  Extensão Vetor:  [▼ .gpkg    ]  │ │  ← item 1
│  │  Extensão Raster: [▼ .tif     ]  │ │  ← item 2 (mesmo grid)
│  └───────────────────────────────────┘ │
│                                        │
│  ┌─ GridComplexSelector ─────────────┐ │
│  │  Pasta de saída: [C:/...] 📁 📥  │ │
│  └───────────────────────────────────┘ │
│                                        │
│  ┌─ GridExecutionButtons ────────────┐ │
│  │  [ℹ️] [Fechar] [💾 Salvar]       │ │
│  └───────────────────────────────────┘ │
│                                        │
└────────────────────────────────────────┘
```

### GridComplexSelector

Usado com **1 seletor independente** (`output_folder`):
- `mode_type="output"` — pasta de saída
- Sem `parent` — seletor independente
- `allow_folder=True`, `allow_file=False`

As subpastas `vectors/` e `rasters/` continuam sendo criadas no `execute_tool()`.

---

## 3. Novo Widget a Criar: GridComboBox

### 3.1 SimpleComboBox (Simple Widget — uso interno)

```python
# resources/widgets/simple/SimpleComboBox.py (NOVO)
```

`QComboBox` com `AppStyles.input()`. **NUNCA importado por plugins.**

```python
class SimpleComboBox(QComboBox):
    """
    QComboBox com estilo AppStyles.input().
    Uso INTERNO por GridComboBox. Plugins NUNCA importam.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_styles()

    def set_options(self, options_dict: dict):
        """Popula o combo com {key: label}."""
        current = self.currentData()
        self.blockSignals(True)
        self.clear()
        for key, label in options_dict.items():
            self.addItem(str(label), key)
        if current is not None:
            idx = self.findData(current)
            if idx >= 0:
                self.setCurrentIndex(idx)
        self.blockSignals(False)

    def get_selected_key(self):
        return self.currentData()

    def set_selected_key(self, key):
        idx = self.findData(key)
        if idx >= 0:
            self.setCurrentIndex(idx)

    def _apply_styles(self):
        self.setStyleSheet(AppStyles.input())
```

### 3.2 GridComboBox (Grid Widget — plugin USA)

```python
# resources/widgets/grid/GridComboBox.py (NOVO)
```

Container de combos com **1 config dict** contendo **N items**. Plugins configuram `onchange` por item.

```python
# ── UNO GridComboBox com 2 items ─────────────────────
self.ext_combo = GridComboBox(
    config={
        "vector_ext": {
            "label": "Extensão Vetor:",
            "description": "Formato para salvar camadas vetoriais",
            "options": {
                ".gpkg": "GeoPackage (.gpkg)",
                ".shp": "Shapefile (.shp)",
                ".geojson": "GeoJSON (.geojson)",
            },
            "selected_key": ".gpkg",
            "onchange": self.on_vector_ext_changed,  # callback(chave, label)
        },
        "raster_ext": {
            "label": "Extensão Raster:",
            "description": "Formato para salvar camadas raster",
            "options": {
                ".tif": "TIFF (.tif)",
                ".jp2": "JPEG 2000 (.jp2)",
                ".png": "PNG (.png)",
            },
            "selected_key": ".tif",
            "onchange": self.on_raster_ext_changed,  # callback(chave, label)
        },
    },
    title="Extensões",
    separator_top=False,
    separator_bottom=True,
    parent=self,
)
layout.addWidget(self.ext_combo)
```

**API pública:**

| Método | Descrição |
|--------|-----------|
| `get_selected_key(key)` → `str` | Retorna chave selecionada do item |
| `set_selected_key(key, value)` | Define chave selecionada do item |
| `get_options(key)` → `dict` | Retorna options de um combo |
| `set_options(key, options)` | Substitui options de um combo |
| `widget(key)` → `SimpleComboBox` | Acesso direto ao QComboBox |

**Parâmetros do `__init__`:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict de combos. Cada item: `label`, `description`, `options`, `selected_key`, `onchange` |
| `title` | str | `None` | Título opcional (QGroupBox). `None` = sem grupo |
| `separator_top` | bool | `False` | Separador acima |
| `separator_bottom` | bool | `False` | Separador abaixo |
| `parent` | QWidget | `None` | Widget pai |

**Parâmetros de cada item no config dict:**

| Propriedade | Obrigatório | Descrição |
|-------------|-------------|-----------|
| `"label"` | Sim | Texto do label |
| `"description"` | Não | Tooltip |
| `"options"` | Sim | Dict `{key: label}` para popular o combo |
| `"selected_key"` | Não | Chave inicialmente selecionada |
| `"onchange"` | Não | `callback(chave_selecionada, texto_selecionado)` |

---

## 4. Arquivos Afetados

### Criar (1 Simple + 1 Grid = 2 arquivos)

```
resources/widgets/simple/SimpleComboBox.py         🆕 NOVO
resources/widgets/grid/GridComboBox.py             🆕 NOVO
```

### Modificar

| Arquivo | Mudança |
|---------|---------|
| `plugins/SaveTemporaryLayersPlugin.py` | Substituir WidgetFactory por widgets |
| `docs/skills/SKILL_WIDGETS2.md` | Adicionar SimpleComboBox + GridComboBox |
| `docs/plano_eliminacao_widgetfactory.md` | Marcar SaveTemporaryLayersPlugin como migrado |
| `docs/ia/changelog.txt` | Registrar nova versão |

---

## 5. Estratégia de Implementação

### FASE 1 — SimpleComboBox

1. Criar `SimpleComboBox.py`:
   - `QComboBox` + `AppStyles.input()`
   - `set_options()`, `get_selected_key()`, `set_selected_key()`
   - `_apply_styles()` no `__init__`
   - **Não expõe signals** — quem usar conecta ao `currentIndexChanged` nativo

### FASE 2 — GridComboBox

2. Criar `GridComboBox.py`:
   - `config` dict com N items (label + options + selected_key + onchange)
   - Cada item: `QLabel` + `SimpleComboBox` na mesma linha
   - `onchange` callback conectado ao `currentIndexChanged` do SimpleComboBox
   - `title` opcional → QGroupBox
   - API: `get_selected_key(key)`, `set_selected_key(key, value)`, `widget(key)`

### FASE 3 — Refatorar SaveTemporaryLayersPlugin

3. **Imports:**
   ```python
   # REMOVER
   from ..core.ui.WidgetFactory import WidgetFactory
   
   # ADICIONAR
   from ..resources.widgets.grid.GridInputFields import GridInputFields
   from ..resources.widgets.grid.GridComboBox import GridComboBox
   from ..resources.widgets.grid.GridComplexSelector import GridComplexSelector
   from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
   ```

4. **`_build_ui()` — estrutura:**
   ```python
   # GridInputFields: prefix + suffix
   self.input_fields = GridInputFields(
       config={
           "prefix": {"label": f"{STR.PREFIX}:", "default": ""},
           "suffix": {"label": f"{STR.SUFFIX}:", "default": ""},
       },
       separator_bottom=True,
       parent=self,
   )
   self.layout.addWidget(self.input_fields)

   # GridComboBox: vector + raster extension (1 widget, 2 items)
   self.ext_combo = GridComboBox(
       config={
           "vector_ext": {
               "label": f"{STR.VECTOR_EXTENSIONS}:",
               "options": self.VECTOR_EXTENSIONS,
               "selected_key": ".gpkg",
           },
           "raster_ext": {
               "label": f"{STR.RASTER_EXTENSIONS}:",
               "options": self.RASTER_EXTENSIONS,
               "selected_key": ".tif",
           },
       },
       title="Extensões",
       separator_bottom=True,
       parent=self,
   )
   self.layout.addWidget(self.ext_combo)

   # GridComplexSelector: output folder
   self.folder_selector = GridComplexSelector(
       config={
           "output_folder": {
               "label": f"{STR.OUTPUT_FOLDER}:",
               "mode_type": "output",
               "allow_file": False,
               "allow_folder": True,
           },
       },
       tool_key=self.TOOL_KEY,
       separator_bottom=True,
       parent=self,
   )
   self.layout.addWidget(self.folder_selector)

   # GridExecutionButtons: Salvar / Fechar / Info
   self.action_buttons = GridExecutionButtons(
       config={"salvar": {
           "label": STR.SAVE,
           "callback": self.execute_tool,
           "is_run_button": True,
       }},
       enable_close_button=True,
       enable_info=True,
       tool_key=self.TOOL_KEY,
       parent=self,
   )
   self.layout.add_execution_buttons(self.action_buttons)
   ```

5. **`_load_prefs()`:**
   ```python
   self.input_fields.set_values({
       "prefix": self.preferences.get("prefix", ""),
       "suffix": self.preferences.get("suffix", ""),
   })
   self.ext_combo.set_selected_key("vector_ext", self.preferences.get("vector_extension", ".gpkg"))
   self.ext_combo.set_selected_key("raster_ext", self.preferences.get("raster_extension", ".tif"))
   
   output_path = self.preferences.get("output_path", "")
   if output_path:
       self.folder_selector.set_path("output_folder", output_path)
   ```

6. **`_save_prefs()`:**
   ```python
   values = self.input_fields.get_values()
   self.preferences["prefix"] = values.get("prefix", "")
   self.preferences["suffix"] = values.get("suffix", "")
   self.preferences["vector_extension"] = self.ext_combo.get_selected_key("vector_ext")
   self.preferences["raster_extension"] = self.ext_combo.get_selected_key("raster_ext")
   self.preferences["output_path"] = self.folder_selector.get_path("output_folder")
   Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
   ```

7. **`execute_tool()`:**
   ```python
   values = self.input_fields.get_values()
   prefix = values.get("prefix", "")
   suffix = values.get("suffix", "")
   vector_ext = self.ext_combo.get_selected_key("vector_ext") or ".gpkg"
   raster_ext = self.ext_combo.get_selected_key("raster_ext") or ".tif"
   output_root = self.folder_selector.get_path("output_folder") or ""
   ```

8. **Manter inalterado:** `_get_temporary_layers()`, `_replace_memory_layer()`, `_replace_raster_layer()`

---

## 6. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Plugin tentar conectar signal no widget | Média | Médio | Contrato proíbe; plugin só passa `onchange` |
| output_path vazio no execute_tool | Alta | Alto | Fallback: pasta do projeto (já existe) |
| Quebrar save_prefs no closeEvent | Média | Alto | Testar fechamento e reabertura |
| Flake8 F401 em imports não usados | Média | Baixo | Rodar flake8 após mudanças |

---

## 7. Checklist de Implementação

```
[ ] FASE 1: SimpleComboBox
  [ ] 1.1 Criar resources/widgets/simple/SimpleComboBox.py
       [ ] QComboBox + AppStyles.input()
       [ ] set_options(), get_selected_key(), set_selected_key()
       [ ] _apply_styles() no __init__

[ ] FASE 2: GridComboBox
  [ ] 2.1 Criar resources/widgets/grid/GridComboBox.py
       [ ] config dict com N items
       [ ] Cada item: QLabel + SimpleComboBox na mesma linha
       [ ] title opcional → QGroupBox
       [ ] onchange callback conectado ao currentIndexChanged
       [ ] API: get_selected_key, set_selected_key, get_options, set_options, widget

[ ] FASE 3: Refatorar SaveTemporaryLayersPlugin
  [ ] 3.1 Remover import WidgetFactory
  [ ] 3.2 Adicionar imports: GridInputFields, GridComboBox, GridComplexSelector, GridExecutionButtons
  [ ] 3.3 Reescrever _build_ui():
       [ ] GridInputFields para prefix + suffix
       [ ] GridComboBox com 2 items: vector_ext + raster_ext
       [ ] GridComplexSelector para output folder
       [ ] GridExecutionButtons: salvar, fechar, info
  [ ] 3.4 Adaptar _load_prefs()
  [ ] 3.5 Adaptar _save_prefs()
  [ ] 3.6 Adaptar execute_tool()
  [ ] 3.7 Manter lógica de negócio inalterada

[ ] Pós-implementação
  [ ] 4.1 Atualizar docs/skills/SKILL_WIDGETS2.md
  [ ] 4.2 Atualizar docs/plano_eliminacao_widgetfactory.md
  [ ] 4.3 Atualizar docs/ia/changelog.txt
  [ ] 4.4 Rodar flake8 (sem F401, W292)
```

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-27 | 1.0.0 | Criação inicial |
| 2026-07-27 | 1.1.0 | Corrigido: GridCombo → **GridComboBox**; **1 widget com 2 items** (não 2 grids); sem pyqtSignal, só `onchange` callback |