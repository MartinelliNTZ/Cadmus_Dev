# 🎯 PLANO DE AÇÃO: Migração do SettingsPlugin para o Novo Sistema de Widgets

**Objetivo:** Migrar `plugins/SettingsPlugin.py` do `WidgetFactory` para os widgets de `resources/widgets/`, seguindo estritamente o contrato do plugin e o plano de eliminação da WidgetFactory.

**Data:** 2026-08-04
**Versão pretendida:** 2.3.85.x
**Autor:** Cadmus Engineering

---

## 1. Resumo da Migração

| Widget Antigo (Factory) | Widget Novo (widgets) | Observação |
|-------------------------|---------------------------|-----------|
| `create_collapsible_parameters` (Geral) | `CollapsibleParametersWidget` | Colapsável "Geral" |
| `create_path_selector` (folder) | `GridComplexSelector` (allow_folder) | Pasta de projetos |
| `create_crs_selector` | **NOVO `ComplexCrsSelector`** | Seletor de EPSG (não existe ainda) |
| `create_dropdown_selector` | `GridComboBox` | Idioma do plugin |
| `create_double_spin_input` (x2) | `GridDoubleSpin` | Precisão + Threshold async |
| `create_checkbox_grid` | `GridCheckbox` (items_per_row=3) | Categorias visíveis da toolbar |
| `create_collapsible_parameters` (Cálculos) | `CollapsibleParametersWidget` | Colapsável "Cálculos Vetoriais" |
| `create_radio_button_grid` | `GridRadioButton` | Método de cálculo vetorial |
| `create_input_fields_widget` | `GridInputFields` | Sufixos cartesiano/elipsoidal |
| `create_bottom_action_buttons` | `GridExecutionButtons` | Botões Salvar/Fechar/Info + extras (Preferências + Registry) |

---

## 2. Widgets Necessários (já existentes) — APIs Confirmadas

| Widget | Arquivo | API usada no plugin |
|--------|---------|---------------------|
| `CollapsibleParametersWidget` | `resources/widgets/CollapsibleParametersWidget.py` | `add_content_layout()`, `set_expanded()`, `is_expanded()` |
| `GridComplexSelector` | `resources/widgets/grid/GridComplexSelector.py` | `set_path()`, `get_paths()`, `get_path()` |
| `GridComboBox` | `resources/widgets/grid/GridComboBox.py` | `set_selected_key()`, `get_selected_key()` |
| `GridDoubleSpin` | `resources/widgets/grid/GridDoubleSpin.py` | `set_value()`, `get_value()` |
| `GridCheckbox` | `resources/widgets/grid/GridCheckbox.py` | `get_all_states()`, `set_checked()`, `get_checkbox()` |
| `GridRadioButton` | `resources/widgets/grid/GridRadioButton.py` | `set_selected_index()`, `get_selected_key()` |
| `GridInputFields` | `resources/widgets/grid/GridInputFields.py` | `set_values()`, `get_value()` |
| `GridExecutionButtons` | `resources/widgets/grid/GridExecutionButtons.py` | `config` (callbacks por botão), `enable_close_button`, `enable_info`, `enable_config_button` |

---

## 3. NOVO Widget Necessário: `ComplexCrsSelector` (Seleção de EPSG)

Não existe seletor de CRS no novo sistema. **Precisa criar** `resources/widgets/ComplexCrsSelector.py` (raiz, SEM versão grid — é um widget composto específico, como `ComplexColorPicker`).

### Composição (layout horizontal)
```
[SimpleLabel (título)] [QgsProjectionSelectionWidget] 
```

### Referência: `resources/widgets/CrsSelectorWidget.py` (antigo — NÃO TOCAR)

### API pública obrigatória (compatível com o uso atual do plugin)

| Método | Descrição |
|--------|-----------|
| `set_crs(crs)` | Define CRS via `QgsCoordinateReferenceSystem` |
| `set_crs_authid(authid)` → bool | Define CRS por authid (retorna False se inválido) |
| `get_crs()` → QgsCoordinateReferenceSystem | Retorna CRS atual |
| `get_crs_authid()` → str | Retorna authid do CRS atual |

### Contrato do widget
- Herda de `QWidget`
- `self.logger = LogUtils(tool=tool_key, class_name="ComplexCrsSelector")`
- `try/except` com `self.logger.exception(..., code="CRS_SELECTOR_BUILD_ERROR")`
- `_apply_styles()` no final do `__init__`
- Estilos globais via `AppStyles` + `_specific_style()`
- `QgsProjectionSelectionWidget.crsChanged.connect(self._on_crs_changed)`
- Unidades/tokens sempre do tema (nunca `px`)

### Parâmetros do construtor
| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `label_text` | str | `""` | Texto do label |
| `default_auth_id` | str | `""` | Authid inicial |
| `tooltip` | str | `""` | Tooltip |
| `tool_key` | ToolKey | `None` | ToolKey para logs |
| `parent` | QWidget | `None` | Widget pai |

---

## 4. Estrutura do Novo `_build_ui`

### 4.1 Widgets criados

```python
# ── Geral (CollapsibleParametersWidget) ─────────────────────────
self.geral_collapsable = CollapsibleParametersWidget(
    title=STR.GENERAL,
    expanded_by_default=True,
    parent=self,
)
self.layout.addWidget(self.geral_collapsable)

# ── Pasta de Projetos (GridComplexSelector - folder) ────────────
self.project_folder_selector = GridComplexSelector(
    config={
        "projects_folder": {
            "label": STR.PROJECTS_FOLDER,
            "mode_type": "input",
            "allow_file": False,
            "allow_folder": True,
            "selection_mode": "folder",
        },
    },
    tool_key=self.TOOL_KEY,
    parent=self,
)
self.geral_collapsable.add_content_widget(self.project_folder_selector)

# ── Seletor de EPSG (NOVO ComplexCrsSelector) ───────────────────
self.crs_selector = ComplexCrsSelector(
    label_text=STR.DEFAULT_CRS,
    default_auth_id=self.system_preferences.get(
        "default_crs_authid", self.DEFAULT_CRS_AUTHID
    ),
    tool_key=self.TOOL_KEY,
    parent=self,
)
self.geral_collapsable.add_content_widget(self.crs_selector)

# ── Idioma (GridComboBox) ───────────────────────────────────────
self.lang_selector = GridComboBox(
    config={
        "language": {
            "label": STR.PLUGIN_LANGUAGE,
            "options": StringManager.AVAILABLE_LANGUAGES,
            "selected_key": self.system_preferences.get("plugin_language", "none"),
        },
    },
    parent=self,
)
self.geral_collapsable.add_content_widget(self.lang_selector)

# ── Precisão + Threshold (GridDoubleSpin) ───────────────────────
self.spin_precision = GridDoubleSpin(
    config={
        "precision": {
            "label": STR.VECTOR_FIELDS_PRECISION,
            "value": 2,
            "min": 0,
            "max": 10,
            "step": 1,
            "type": "int",
        },
    },
    parent=self,
)
self.geral_collapsable.add_content_widget(self.spin_precision)

self.spin_threshold = GridDoubleSpin(
    config={
        "threshold": {
            "label": STR.ASYNC_THRESHOLD,
            "value": 1000,
            "min": 1,
            "max": 100000000,
            "step": 1,
            "type": "int",
        },
    },
    parent=self,
)
self.geral_collapsable.add_content_widget(self.spin_threshold)

# ── Toolbar Categorias (GridCheckbox - 3 colunas) ───────────────
self.toolbar_category_checks = GridCheckbox(
    config={
        key: {"label": label, "default": True}
        for key, label in MenuManager.toolbar_category_options().items()
    },
    items_per_row=3,
    title=STR.TOOLBAR_VISIBLE_CATEGORIES,
    parent=self,
)
self.geral_collapsable.add_content_widget(self.toolbar_category_checks)

# ── Cálculos Vetoriais (CollapsibleParametersWidget) ────────────
self.calc_collapsable = CollapsibleParametersWidget(
    title=STR.VECTOR_CALCULATIONS_PLUGIN,
    expanded_by_default=False,
    parent=self,
)
self.layout.addWidget(self.calc_collapsable)

# ── Método de Cálculo (GridRadioButton) ─────────────────────────
self.radio_calc = GridRadioButton(
    config={
        STR.ELLIPSOIDAL: {"label": STR.ELLIPSOIDAL},
        STR.CARTESIAN: {"label": STR.CARTESIAN},
        STR.BOTH: {"label": STR.BOTH},
    },
    columns=3,
    default_key=STR.ELLIPSOIDAL,
    parent=self,
)
self.calc_collapsable.add_content_widget(self.radio_calc)

# ── Sufixos (GridInputFields) ───────────────────────────────────
self.area_fields_inputs = GridInputFields(
    config={
        "cartesian_suffix": {
            "label": STR.CARTESIAN_SUFFIX,
            "default": "",
        },
        "ellipsoidal_suffix": {
            "label": STR.ELLIPSOIDAL_SUFFIX,
            "default": "_eli",
        },
    },
    parent=self,
)
self.calc_collapsable.add_content_widget(self.area_fields_inputs)

# ── Botões de Ação (GridExecutionButtons) ───────────────────────
self.action_buttons = GridExecutionButtons(
    config={
        "save": {
            "label": STR.SAVE,
            "description": "Salva as configurações",
            "callback": self.execute_tool,
            "is_run_button": True,
        },
        "open_prefs": {
            "label": STR.OPEN_PREFERENCES_FOLDER,
            "description": "Abre a pasta de preferências",
            "callback": self._open_preferences_folder,
        },
        "open_registry": {
            "label": STR.REG_TITLE,
            "description": "Abre o gerenciador de licença/registry",
            "callback": self._open_lic_dialog,
        },
    },
    enable_close_button=True,
    enable_config_button=False,   # ← SEM botão config (é o próprio Settings)
    enable_info=True,
    tool_key=self.TOOL_KEY,
    parent=self,
)
self.layout.add_execution_buttons(self.action_buttons)
```

### 4.2 Ordem de adição no layout (MainLayout)

```python
self.layout.addWidget(self.geral_collapsable)
self.layout.addWidget(self.calc_collapsable)
self.layout.add_execution_buttons(self.action_buttons)
```

---

## 5. Ajustes na Lógica (`_load_prefs` / `_save_prefs`)

### 5.1 `GridRadioButton` — sem `get_selected_text()`

O antigo `radio_calc.get_selected_text()` NÃO existe no novo `GridRadioButton`. Como as **chaves** do config são os próprios textos (`STR.ELLIPSOIDAL`, etc.), usar `get_selected_key()` retorna o texto desejado.

**`_save_prefs`:**
```python
# ANTES:
selected_text = self.radio_calc.get_selected_text()

# DEPOIS:
selected_text = self.radio_calc.get_selected_key()
```

**`_load_prefs`:** mantém `set_selected_index()` (API existe no novo widget).

### 5.2 `GridComboBox` — `lang_selector`

API compatível: `get_selected_key()` / `set_selected_key()`.
- `_load_prefs`: `self.lang_selector.set_selected_key("language", selected_language)`
- `_save_prefs`: `selected_language = self.lang_selector.get_selected_key("language")`

### 5.3 `GridDoubleSpin` — `spin_precision` / `spin_threshold`

API nova: `set_value(key, value)` / `get_value(key)`.
- `_load_prefs`: `self.spin_precision.set_value("precision", precision_value)` e `self.spin_threshold.set_value("threshold", thresh_value)`
- `_save_prefs`: `precision_val = int(self.spin_precision.get_value("precision"))` e `feats_value = int(self.spin_threshold.get_value("threshold"))`

### 5.4 `GridCheckbox` — `toolbar_category_checks`

O antigo retornava `dict {category: checkbox}` e o plugin iterava `for category, checkbox in self.toolbar_category_checks.items()`.

O novo `GridCheckbox` NÃO itera por itens diretamente. Usar:
- `_load_prefs`: `self.toolbar_category_checks.set_checked(category, toolbar_visibility.get(category, True))`
- `_save_prefs`: `toolbar_visibility = self.toolbar_category_checks.get_all_states()` (retorna `{key: bool}`)

### 5.5 `GridComplexSelector` — `project_folder_selector`

API nova: `set_path(key, path)` / `get_paths()`.
- `_load_prefs`: `self.project_folder_selector.set_path("projects_folder", project_folder)`
- `_save_prefs`: `paths = self.project_folder_selector.get_paths()` → `paths[0] if paths else ""`

### 5.6 `ComplexCrsSelector` — `crs_selector`

API compatível com o antigo `CrsSelectorWidget`:
- `set_crs_authid()`, `get_crs()`, `get_crs_authid()`, `set_crs()` — todos existem.
- Nenhuma mudança na lógica de `_load_prefs`/`_save_prefs`.

### 5.7 `GridInputFields` — `area_fields_inputs`

API compatível: `set_values()` / `get_value()`.
- `_load_prefs`: `self.area_fields_inputs.set_values({...})`
- `_save_prefs`: `self.area_fields_inputs.get_value("cartesian_suffix")`

### 5.8 `CollapsibleParametersWidget` — `geral_collapsable` / `calc_collapsable`

API compatível: `set_expanded()` / `is_expanded()`.
- `_load_prefs`: `self.calc_collapsable.set_expanded(...)`, `self.geral_collapsable.set_expanded(...)`
- `_save_prefs`: `self.preferences["calc_expanded"] = self.calc_collapsable.is_expanded()`, idem geral

---

## 6. Imports Novos (remover WidgetFactory)

### Remover
```python
from ..core.ui.WidgetFactory import WidgetFactory
```

### Adicionar
```python
from ..resources.widgets.CollapsibleParametersWidget import CollapsibleParametersWidget
from ..resources.widgets.ComplexCrsSelector import ComplexCrsSelector      # NOVO
from ..resources.widgets.grid.GridComboBox import GridComboBox
from ..resources.widgets.grid.GridDoubleSpin import GridDoubleSpin
from ..resources.widgets.grid.GridCheckbox import GridCheckbox
from ..resources.widgets.grid.GridRadioButton import GridRadioButton
from ..resources.widgets.grid.GridInputFields import GridInputFields
from ..resources.widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
```

### Manter
```python
from qgis.core import QgsCoordinateReferenceSystem
from ..utils.StringManager import StringManager
from ..plugins.BasePlugin import BasePluginMTL
from ..utils.Preferences import Preferences
from ..utils.ToolKeys import ToolKey
from ..utils.ExplorerUtils import ExplorerUtils
from ..i18n.TranslationManager import STR, TranslationManager
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..core.config.MenuManager import MenuManager
```

---

## 7. Strings — Verificação

O plugin já usa `STR.*` para todos os labels. Verificar se `STR.REG_TITLE` e `STR.ASYNC_THRESHOLD` existem (usados no código atual). Nenhuma string nova parece necessária, mas confirmar:
- `STR.OPEN_PREFERENCES_FOLDER` ✅ (existe)
- `STR.REG_TITLE` ✅ (existe — "Gerenciar")
- `STR.ASYNC_THRESHOLD` ✅ (existe)
- `STR.DEFAULT_CRS` ✅ (existe)
- `STR.VECTOR_CALCULATIONS_PLUGIN` — confirmar existência

---

## 8. Passos de Implementação

1. **Criar** `resources/widgets/ComplexCrsSelector.py` (raiz, sem versão grid)
2. **Atualizar** `docs/plano_eliminacao_widgetfactory.md` (seção 8.1, TODO 1.3, FASE 2 — SettingsPlugin)
3. **Atualizar** `docs/skills/SKILL_WIDGETS2.md` (adicionar `ComplexCrsSelector` ao catálogo raiz)
4. **Migrar** `plugins/SettingsPlugin.py`:
   - Remover import `WidgetFactory`
   - Substituir cada `create_*` pelo widget novo
   - Ajustar `_load_prefs`/`_save_prefs` conforme seção 5
   - Adicionar `SeparatorWidget()` entre widgets conforme necessário
5. **Validar** com flake8 e bandit
6. **Atualizar** `docs/ia/changelog.txt` (nova versão `2.3.85.x`)

---

## 9. Conformidade com o Contrato

| Regra | Conformidade |
|-------|-------------|
| UI via WidgetFactory / widgets (nunca QtWidgets direto) | ✅ widgets |
| Logging via LogUtils (nunca print) | ✅ mantém |
| Strings via STR (nunca hardcoded) | ✅ mantém |
| ToolKey é enum | ✅ mantém |
| Estilos via widgets (nunca setStyleSheet no plugin) | ✅ |
| Exceções logadas com logger.exception | ✅ |
| Configurações via Preferences | ✅ mantém |
| `GridExecutionButtons` SEM botão config | ✅ `enable_config_button=False` |
| Botões extras (Prefs + Registry) via config dict | ✅ |

---

## 10. Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| `GridRadioButton` sem `get_selected_text()` | Usar `get_selected_key()` (chaves = textos) |
| `GridCheckbox` sem iteração direta | Usar `set_checked()`/`get_all_states()` |
| Novo `ComplexCrsSelector` | Criar seguindo padrão `ComplexColorPicker` |
| `GridDoubleSpin` sem `setValue()` direto | Usar `set_value(key, value)` |
| `GridComplexSelector` para pasta | Config `allow_folder=True, allow_file=False, selection_mode="folder"` |

---

## 11. Checklist Final

- [ ] Criar `resources/widgets/ComplexCrsSelector.py`
- [ ] Migrar `plugins/SettingsPlugin.py` (remover WidgetFactory)
- [ ] Ajustar `_load_prefs`/`_save_prefs` (APIs novas)
- [ ] `GridExecutionButtons` com `enable_config_button=False`
- [ ] Botões extras: Abrir Preferências + Registry via config dict
- [ ] Validar flake8 + bandit
- [ ] Atualizar `docs/plano_eliminacao_widgetfactory.md`
- [ ] Atualizar `docs/skills/SKILL_WIDGETS2.md`
- [ ] Atualizar `docs/ia/changelog.txt`