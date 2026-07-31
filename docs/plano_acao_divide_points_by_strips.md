# 🎯 PLANO DE AÇÃO: Migração DividePointsByStripsPlugin

**Objetivo:** Migrar `DividePointsByStripsPlugin` do sistema antigo (`WidgetFactory`) para o novo sistema de widgets autoconfiguráveis (`resources/new_widgets/`).

**Data:** 2026-07-31
**Plugin:** `plugins/DividePointsByStripsPlugin.py`
**Versão Alvo:** 2.3.80.x

---

## 1. ANÁLISE — WidgetFactory Atual → Novo Widget

| # | Factory (antigo) | Uso no plugin | Novo Widget | Complexidade |
|---|-----------------|---------------|-------------|-------------|
| 1 | `create_label` | Label introdutório | `SimpleLabel` | 🔵 Baixa |
| 2 | `create_layer_input` | Seletor de camada de pontos com checkbox "selecionadas" | `GridComplexSelector` com `allow_layer=True` + `allow_features_check=True` | 🔴 Alta |
| 3 | `create_collapsible_parameters` (x4) | Operational, Sensitivity, Attributes, Saving | `CollapsibleParametersWidget` | 🟡 Média |
| 4 | `create_dropdown_selector` (x4) | id_field, time_field, judge_mode, group_field | `GridComboBox` | 🟡 Média |
| 5 | `create_input_fields_widget` (x2) | operational_fields, sensitivity_fields | `GridInputFields` | 🟡 Média |
| 6 | `create_radio_button_grid` | PATH_MODES (Curva/Reta/Ambos) | `GridRadioButton` com chaves = STR | 🟡 Média |
| 7 | `create_checkbox_grid` | Output fields (DIVIDE_STRIP_FIELDS) com control buttons | `GridCheckbox` + `control_buttons_config` | 🔴 Alta |
| 8 | `create_save_file_selector` (x2) | Salvar pontos + salvar linhas (com checkbox enable) | `GridComplexSelector` + `allow_lock_check=True` | 🟡 Média |
| 9 | `create_bottom_action_buttons` | Botões Executar/Fechar/Info | `GridExecutionButtons` | 🟡 Média |

---

## 2. MAPEAMENTO DETALHADO — API por Widget

### 2.1 Layer Input (`create_layer_input` → `GridComplexSelector`)

**API antiga (LayerInputWidget):**
```python
self.layer_input.current_layer()          # → QgsVectorLayer | None
self.layer_input.layerChanged.connect(fn)  # → signal
self.layer_input.only_selected_enabled()  # → bool (checkbox "apenas selecionadas")
```

**API nova — método genérico `getitem()` no ComplexSelector que retorna tupla `(path, layer)`:**
```python
# GridComplexSelector com config:
# "camada": {
#     "label": STR.INPUT_POINTS,
#     "allow_layer": True,
#     "layer_filters": QgsMapLayerProxyModel.PointLayer,
#     "allow_features_check": True,
#     "features_check_text": "Usar apenas feições selecionadas",
#     "allow_file": True,       # suporta arquivo externo não carregado no QGIS
#     "allow_folder": False,
# }

# NOVO método no ComplexSelector:
def getitem(self) -> tuple[str, object]:
    """
    Retorna tupla genérica (path, layer) com o estado atual do seletor.
    
    Casos:
    - layer combo: (source_path, QgsMapLayer)
    - line edit com arquivo: (file_path, None)
    - vazio: ("", None)
    """
    return self.path(), self.current_layer

# Uso no plugin — SEMPRE usar getitem():
path, layer = self.layer_input.get("camada").getitem()
```

**Lógica de resolução no plugin — método helper:**
```python
def _resolve_input_layer(self):
    """
    Resolve a camada de entrada a partir do seletor.
    
    O ComplexSelector suporta 2 modos:
    - layer combo: getitem() → (source_path, QgsMapLayer)
    - line edit:   getitem() → (file_path, None)
    - vazio:       getitem() → ("", None)
    
    Lógica genérica:
    - layer não-None → usa camada carregada no QGIS
    - layer None + path não-vazio → arquivo externo não carregado
    - layer None + path vazio → nada selecionado
    
    Retorna:
        tuple (path, layer)
    """
    return self.layer_input.get("camada").getitem()
```

**Uso no execute_tool:**
```python
path, layer = self._resolve_input_layer()

if isinstance(layer, QgsVectorLayer):
    # Modo layer combo — usa camada carregada no QGIS
    process_layer = layer
elif path:
    # Modo arquivo externo — carrega via VectorLayerSource
    loaded = VectorLayerSource.open_vector_layer(path, tool_key=self.TOOL_KEY)
    if loaded and loaded.isValid():
        process_layer = loaded
    else:
        QgisMessageUtil.bar_warning(self.iface, STR.SELECT_POINT_VECTOR_LAYER)
        return
else:
    QgisMessageUtil.bar_warning(self.iface, STR.SELECT_POINT_VECTOR_LAYER)
    return
```

**⚠️ NOTA IMPORTANTE:** O arquivo externo carregado via `VectorLayerSource` é uma camada temporária. Ela precisa ser adicionada ao projeto com `ProjectUtils.add_layer()` antes de ser usada como camada de entrada no processamento.

### 2.2 Dropdown Selector (`create_dropdown_selector` → `GridComboBox`)

**API antiga (DropdownSelectorWidget):**
```python
self.id_field_selector.get_selected_key()  # → str
self.id_field_selector.set_options({})     # → seta opções
self.id_field_selector.set_selected_key(k) # → seleciona
```

**API nova (GridComboBox):**
```python
self.id_field_selector.get_selected_key("id_field")   # → str
self.id_field_selector.set_options("id_field", opts)  # → seta opções
self.id_field_selector.set_selected_key("id_field", k) # → seleciona
```

**✅ Compatível — API já existe.**

### 2.3 Input Fields (`create_input_fields_widget` → `GridInputFields`)

**API antiga (GridInputFieldsWidget):**
```python
self.operational_fields.set_values(dict)  # → define valores
self.operational_fields.get_values()      # → dict
```

**API nova (GridInputFields):**
```python
self.operational_fields.set_values(dict)
self.operational_fields.get_values()
```

**✅ Compatível — API já existe.**

### 2.4 Radio Button Grid (`create_radio_button_grid` → `GridRadioButton`)

**API antiga (RadioButtonGridWidget):**
```python
self.radio_path_mode.set_selected_index(int)  # → 0, 1, 2
self.radio_path_mode.get_selected_text()      # → "Ambos"
```

**API nova (GridRadioButton) — usar os STR como chaves do dict config:**
```python
self.radio_path_mode = GridRadioButton(
    config={
        STR.CURVE: {"label": STR.CURVE},
        STR.STRAIGHT: {"label": STR.STRAIGHT},
        STR.BOTH_PATH: {"label": STR.BOTH_PATH},
    },
    columns=3,
    default_key=STR.BOTH_PATH,
    separator_bottom=False,
    parent=self,
)

self.radio_path_mode.get_selected_key()      # → STR.BOTH_PATH (mesmo que antigo get_selected_text)
self.radio_path_mode.set_selected_key(STR.CURVE)  # → seleciona
```

**✅ SEM adaptação em widget — como as chaves são os próprios STR, `get_selected_key()` retorna exatamente o mesmo valor que o antigo `get_selected_text()`.**

### 2.5 Checkbox Grid (`create_checkbox_grid` → `GridCheckbox`)

**API antiga (GridCheckboxWidget):**
```python
self.output_fields_grid.get_checked_keys()    # → list[str]
self.output_fields_grid.set_checked_keys([k]) # → marca keys
self.output_fields_grid.get_checkbox(key)     # → QCheckBox
```

**API nova (GridCheckbox):**
```python
self.output_fields_grid.get_checked_keys()    # → list[str] (PRECISA ADICIONAR)
self.output_fields_grid.set_checked_keys([k]) # → marca keys (PRECISA ADICIONAR)
self.output_fields_grid.get_checkbox(key)     # → SimpleCheckbox (PRECISA ADICIONAR — alias p/ widget)
self.output_fields_grid.widget(key)           # → já existe
self.output_fields_grid.select_all()          # → já existe
self.output_fields_grid.deselect_all()        # → já existe
self.output_fields_grid.invert_selection()    # → já existe
self.output_fields_grid.get_all_states()      # → já existe
```

**⚠️ 3 MÉTODOS PRECISAM SER ADICIONADOS ao `GridCheckbox` na FASE 1.**

### 2.6 Save File Selector (`create_save_file_selector` → `GridComplexSelector` + `allow_lock_check`)

**API antiga (SelectorWidget mode=file):**
```python
self.save_points_selector.is_enabled()        # → bool (checkbox marcado)
self.save_points_selector.set_enabled(bool)   # → marca/desmarca checkbox
self.save_points_selector.get_file_path()     # → str
self.save_points_selector.set_file_path(str)  # → define path
```

**API nova — usar o LOCK BUTTON do ComplexSelector (essa é exatamente a função dele):**
```python
# GridComplexSelector com config:
# "save_points": {
#     "label": "Salvar pontos em",
#     "mode_type": "output",
#     "allow_file": True,
#     "allow_folder": False,
#     "file_filter": StringManager.FILTER_VECTOR,
#     "allow_lock_check": True,       # ✅ lock button = habilita/desabilita
#     "lock_check_default": False,    # começa bloqueado (desabilitado)
#     "show_explorer_button": True,
#     "show_copy_button": False,
# }

# Mapeamento direto:
self.save_points_selector.get_lock_state("save_points")   # → bool (True = habilitado) — ANTIGO is_enabled()
self.save_points_selector.set_lock_state("save_points", b) # → define — ANTIGO set_enabled()
self.save_points_selector.get_path("save_points")          # → str — ANTIGO get_file_path()
self.save_points_selector.set_path("save_points", path)    # → define — ANTIGO set_file_path()
```

**✅ O lock button JÁ faz o papel de habilitar/desabilitar o seletor — NÃO precisa criar `enable_checkbox`.**

**Comportamento:**
- `lock_check_default=True` → lock ativo → widget desbloqueado → podem editar
- `lock_check_default=False` → lock inativo → widget bloqueado → não podem editar
- Clicar no lock button alterna entre os dois estados

### 2.7 Collapsible Parameters (`create_collapsible_parameters` → `CollapsibleParametersWidget`)

**API antiga (CollapsibleParametersWidget):**
```python
self.operational_params.add_content_layout(layout)  # → adiciona layout
self.operational_params.set_expanded(bool)          # → expande/recolhe
self.operational_params.is_expanded()               # → bool
```

**API nova (CollapsibleParametersWidget new):**
```python
self.operational_params.add_content_widget(widget)  # → adiciona widget
self.operational_params.add_content_layout(layout)  # → adiciona layout
self.operational_params.set_expanded(bool)
self.operational_params.is_expanded()
```

**✅ Compatível — API já existe em `resources/new_widgets/CollapsibleParametersWidget.py`.**

### 2.8 Bottom Action Buttons (`create_bottom_action_buttons` → `GridExecutionButtons`)

**API antiga (ExecutionButtonsWidget):**
```python
# Retorna (layout, widget)
# Botões: Executar, Fechar, Info
```

**API nova (GridExecutionButtons):**
```python
self.action_buttons = GridExecutionButtons(
    config={
        "run": {
            "label": STR.EXECUTE,
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

**✅ Compatível — API já existe.**

---

## 3. MUDANÇAS NECESSÁRIAS NOS WIDGETS EXISTENTES

### 3.1 GridCheckbox — Adicionar 3 métodos

### 3.2 ComplexSelector — Adicionar método genérico `getitem()`

**Arquivo:** `resources/new_widgets/simple/ComplexSelector.py`

Método **genérico** que retorna tupla `(path, layer)` — a forma canônica de acessar o estado do seletor:

```python
def getitem(self) -> tuple[str, object]:
    """
    Retorna tupla genérica (path, layer) com o estado atual do seletor.

    Casos possíveis:
    - layer combo:          (source_path, QgsMapLayer)
    - line edit com arquivo: (file_path, None)
    - vazio:                 ("", None)

    Lógica de interpretação pelo plugin:
    - layer não-None → camada carregada no QGIS
    - layer None + path não-vazio → arquivo externo não carregado
    - layer None + path vazio → nada selecionado
    """
    return self.path(), self.current_layer
```

**Arquivo:** `resources/new_widgets/grid/GridCheckbox.py`

```python
def get_checked_keys(self) -> list[str]:
    """
    Retorna lista de chaves onde checkbox está marcado.
    Equivalente ao antigo GridCheckboxWidget.get_checked_keys().
    """
    return [key for key, cb in self._checkboxes.items() if cb.isChecked()]


def set_checked_keys(self, keys: list[str]):
    """
    Marca as chaves da lista, desmarca as demais.
    Equivalente ao antigo GridCheckboxWidget.set_checked_keys().
    """
    keys_set = set(keys or [])
    for key, cb in self._checkboxes.items():
        cb.setChecked(key in keys_set)


def get_checkbox(self, key: str):
    """
    Alias para widget(key) — retorna o SimpleCheckbox.
    Compatibilidade com API antiga get_checkbox().
    """
    return self._checkboxes.get(key)
```

---

## 4. ESTRATÉGIA DE MIGRAÇÃO

### FASE 1 — Preparação dos Widgets

- [ ] 1.1 Adicionar `get_checked_keys()`, `set_checked_keys()`, `get_checkbox()` ao `GridCheckbox`

### FASE 2 — Migração do Plugin

- [ ] 2.1 Substituir imports: remover `WidgetFactory`, adicionar novos widgets
- [ ] 2.2 Migrar `_build_ui()` completo
- [ ] 2.3 Migrar `_load_prefs()` com nova API
- [ ] 2.4 Migrar `_save_prefs()` com nova API
- [ ] 2.5 Migrar `_refresh_field_selectors()` — usar `self.layer_input.get("camada").current_layer`
- [ ] 2.6 Migrar `_on_layer_changed()` — adaptar callback
- [ ] 2.7 Migrar `execute_tool()` — usar `_resolve_input_layer()` helper
- [ ] 2.8 Migrar `_get_selected_output_fields()` — usar `get_checked_keys()`
- [ ] 2.9 Remover imports de `WidgetFactory` e `Styles`

### FASE 3 — Validação

- [ ] 3.1 Plugin abre sem erros
- [ ] 3.2 Layer input funciona com camada carregada
- [ ] 3.3 Layer input funciona com arquivo externo não carregado
- [ ] 3.4 Features checkbox "apenas selecionadas" aparece em modo layer
- [ ] 3.5 Dropdowns populam corretamente
- [ ] 3.6 Input fields carregam/salvam valores
- [ ] 3.7 Radio buttons selecionam corretamente (Curva/Reta/Ambos)
- [ ] 3.8 Checkbox grid — shot_id fixo marcado/desabilitado
- [ ] 3.9 Save selectors — lock button habilita/desabilita
- [ ] 3.10 Collapsibles expandem/recolhem e persistem estado
- [ ] 3.11 Botões de ação funcionam
- [ ] 3.12 Preferências salvam/carregam corretamente
- [ ] 3.13 Execução completa funciona (segmentação + linhas)
- [ ] 3.14 Nenhum `setStyleSheet` no plugin
- [ ] 3.15 Nenhum import de `WidgetFactory` ou `Styles`

### FASE 4 — Documentação

- [ ] 4.1 Atualizar `docs/ia/changelog.txt`
- [ ] 4.2 Atualizar `docs/plano_eliminacao_widgetfactory.md` (marcar migrado)

---

## 5. DETALHAMENTO DA MIGRAÇÃO — Código Novo

### 5.1 Imports

**Remover:**
```python
from ..core.ui.WidgetFactory import WidgetFactory
```

**Adicionar:**
```python
from ..resources.new_widgets.simple.SimpleLabel import SimpleLabel
from ..resources.new_widgets.SeparatorWidget import SeparatorWidget
from ..resources.new_widgets.CollapsibleParametersWidget import CollapsibleParametersWidget
from ..resources.new_widgets.grid.GridComboBox import GridComboBox
from ..resources.new_widgets.grid.GridInputFields import GridInputFields
from ..resources.new_widgets.grid.GridRadioButton import GridRadioButton
from ..resources.new_widgets.grid.GridCheckbox import GridCheckbox
from ..resources.new_widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons
```

### 5.2 `_build_ui()` Novo

```python
def _build_ui(self, **kwargs):
    """Monta componentes da interface com novo sistema de widgets."""
    super()._build_ui(
        title=STR.DIVIDE_POINTS_BY_STRIPS_TITLE,
        icon_path="vector.ico",
        enable_scroll=True,
    )

    # ── Label Introdutório ────────────────────────────────────
    self.intro_label = SimpleLabel(
        text=STR.DIVIDE_POINTS_BY_STRIPS_INTRO,
        parent=self,
    )
    self.layout.addWidget(self.intro_label)
    self.layout.addWidget(SeparatorWidget())

    # ── Layer Input (GridComplexSelector) ─────────────────────
    self.layer_input = GridComplexSelector(
        config={
            "camada": {
                "label": STR.INPUT_POINTS,
                "description": "Camada de pontos ou arquivo externo",
                "allow_layer": True,
                "layer_filters": QgsMapLayerProxyModel.PointLayer,
                "allow_features_check": True,
                "features_check_text": "Usar apenas feições selecionadas",
                "allow_file": True,
                "allow_folder": False,
                "file_filter": StringManager.FILTER_VECTOR,
                "show_explorer_button": False,
                "show_copy_button": False,
            },
        },
        tool_key=self.TOOL_KEY,
        separator_bottom=False,
        parent=self,
    )
    self.layer_input.set_on_changed("camada", self._on_layer_changed)
    self.layout.addWidget(self.layer_input)
    self.layout.addWidget(SeparatorWidget())

    # ── Operational Parameters (Collapsible) ──────────────────
    self.operational_params = CollapsibleParametersWidget(
        title=STR.OPERATIONAL_PARAMETERS,
        expanded_by_default=True,
        parent=self,
    )

    self.id_field_selector = GridComboBox(
        config={
            "id_field": {
                "label": STR.UNIQUE_SEQUENTIAL_ID_FIELD,
                "description": "Campo com ID sequencial único",
                "options": {},
                "selected_key": "",
            },
        },
        title="",
        parent=self,
    )
    self.operational_params.add_content_widget(self.id_field_selector)

    self.group_field_selector = GridComboBox(
        config={
            "group_field": {
                "label": "Agrupar por Campo (opcional)",
                "description": "Agrupa pontos por valor de campo",
                "options": {},
                "selected_key": "",
            },
        },
        title="",
        parent=self,
    )
    self.operational_params.add_content_widget(self.group_field_selector)

    self.operational_fields = GridInputFields(
        config=StringManager.DIVIDE_POINTS_OPERATIONAL_FIELDS,
        title="",
        parent=self,
    )
    self.operational_params.add_content_widget(self.operational_fields)

    self.layout.addWidget(self.operational_params)
    self.layout.addWidget(SeparatorWidget())

    # ── Sensitivity Parameters (Collapsible) ──────────────────
    self.sensitivity_params = CollapsibleParametersWidget(
        title=STR.SENSITIVITY_PARAMETERS,
        expanded_by_default=True,
        parent=self,
    )

    self.sensitivity_fields = GridInputFields(
        config=StringManager.DIVIDE_POINTS_SENSITIVITY_FIELDS,
        title="",
        parent=self,
    )
    self.sensitivity_params.add_content_widget(self.sensitivity_fields)

    self.time_field_selector = GridComboBox(
        config={
            "time_field": {
                "label": STR.TIMESTAMP_FIELD,
                "description": "Campo com timestamp",
                "options": {},
                "selected_key": "",
            },
        },
        title="",
        parent=self,
    )
    self.sensitivity_params.add_content_widget(self.time_field_selector)

    self.judge_mode_selector = GridComboBox(
        config={
            "judge_mode": {
                "label": "Modo de Processamento",
                "description": "Algoritmo de julgamento",
                "options": self.JUDGE_MODES,
                "selected_key": self.preferences.get(self.PREF_JUDGE_MODE, "Complexo"),
            },
        },
        title="",
        parent=self,
    )
    self.sensitivity_params.add_content_widget(self.judge_mode_selector)

    # ── Radio Button: Path Mode (chaves = STR) ────────────────
    self.radio_path_mode = GridRadioButton(
        config={
            STR.CURVE: {"label": STR.CURVE},
            STR.STRAIGHT: {"label": STR.STRAIGHT},
            STR.BOTH_PATH: {"label": STR.BOTH_PATH},
        },
        columns=3,
        default_key=STR.BOTH_PATH,
        parent=self,
    )
    self.sensitivity_params.add_content_widget(self.radio_path_mode)

    self.layout.addWidget(self.sensitivity_params)
    self.layout.addWidget(SeparatorWidget())

    # ── Attributes (Collapsible) ──────────────────────────────
    self.attributes_params = CollapsibleParametersWidget(
        title=STR.ATTRIBUTES,
        expanded_by_default=True,
        parent=self,
    )

    # Constrói config dict do GridCheckbox a partir de DIVIDE_STRIP_FIELDS
    strip_config = {}
    for field_key, field_spec in SequentialPointBreakJudge.DIVIDE_STRIP_FIELDS.items():
        key_value = field_key.value if hasattr(field_key, "value") else field_key
        strip_config[key_value] = {
            "label": field_spec.label,
            "description": field_spec.description,
            "default": True,
        }

    self.output_fields_grid = GridCheckbox(
        config=strip_config,
        items_per_row=2,
        control_buttons_config={
            "select_all": {
                "label": "Selecionar",
                "callback": self._select_all_output_fields,
            },
            "deselect_all": {
                "label": "Remover",
                "callback": self._deselect_all_output_fields,
            },
            "invert": {
                "label": "Inverter",
                "callback": self._invert_output_fields,
            },
        },
        parent=self,
    )

    # Forçar shot_id sempre marcado e desabilitado
    shot_id_cb = self.output_fields_grid.get_checkbox(self.REQUIRED_OUTPUT_FIELD)
    if shot_id_cb is not None:
        shot_id_cb.setChecked(True)
        shot_id_cb.setEnabled(False)

    self.attributes_params.add_content_widget(self.output_fields_grid)

    self.layout.addWidget(self.attributes_params)
    self.layout.addWidget(SeparatorWidget())

    # ── Saving (Collapsible) ──────────────────────────────────
    self.save_collapsible = CollapsibleParametersWidget(
        title=STR.SAVING,
        expanded_by_default=False,
        parent=self,
    )

    # Save Points Selector — lock button habilita/desabilita
    self.save_points_selector = GridComplexSelector(
        config={
            "save_points": {
                "label": "Salvar pontos em",
                "mode_type": "output",
                "allow_file": True,
                "allow_folder": False,
                "file_filter": StringManager.FILTER_VECTOR,
                "allow_lock_check": True,
                "lock_check_default": False,
                "show_explorer_button": True,
                "show_copy_button": False,
            },
        },
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    self.save_collapsible.add_content_widget(self.save_points_selector)

    # Save Track Selector — lock button habilita/desabilita
    self.save_track_selector = GridComplexSelector(
        config={
            "save_track": {
                "label": "Salvar trilhas em",
                "mode_type": "output",
                "allow_file": True,
                "allow_folder": False,
                "file_filter": StringManager.FILTER_VECTOR,
                "allow_lock_check": True,
                "lock_check_default": False,
                "show_explorer_button": True,
                "show_copy_button": False,
            },
        },
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    self.save_collapsible.add_content_widget(self.save_track_selector)

    self.layout.addWidget(self.save_collapsible)

    # ── Action Buttons ────────────────────────────────────────
    self.action_buttons = GridExecutionButtons(
        config={
            "run": {
                "label": STR.EXECUTE,
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

    self._refresh_field_selectors()
```

### 5.3 Control Buttons (callbacks dos botões Selecionar/Remover/Inverter)

```python
def _select_all_output_fields(self):
    """Marca todos os checkboxes de campos de saída."""
    self.output_fields_grid.select_all()
    shot_id_cb = self.output_fields_grid.get_checkbox(self.REQUIRED_OUTPUT_FIELD)
    if shot_id_cb is not None:
        shot_id_cb.setChecked(True)


def _deselect_all_output_fields(self):
    """Desmarca todos os checkboxes de campos de saída (exceto shot_id)."""
    self.output_fields_grid.deselect_all()
    shot_id_cb = self.output_fields_grid.get_checkbox(self.REQUIRED_OUTPUT_FIELD)
    if shot_id_cb is not None:
        shot_id_cb.setChecked(True)


def _invert_output_fields(self):
    """Inverte seleção de todos os checkboxes de campos de saída."""
    self.output_fields_grid.invert_selection()
    shot_id_cb = self.output_fields_grid.get_checkbox(self.REQUIRED_OUTPUT_FIELD)
    if shot_id_cb is not None:
        shot_id_cb.setChecked(True)
```

### 5.4 Helper — Resolver Camada de Entrada

```python
def _resolve_input_layer(self):
    """
    Resolve a camada de entrada a partir do seletor.

    Usa o método genérico getitem() do ComplexSelector que retorna
    tupla (path, layer):

    - layer não-None → camada carregada no QGIS
    - layer None + path não-vazio → arquivo externo não carregado
    - layer None + path vazio → nada selecionado

    Retorna:
        tuple (path, layer)
    """
    return self.layer_input.get("camada").getitem()
```

### 5.5 `_on_layer_changed()` e `_refresh_field_selectors()`

```python
def _on_layer_changed(self, paths):
    """Recarrega seletores após troca de camada ou arquivo."""
    self._refresh_field_selectors()

def _refresh_field_selectors(self):
    """Atualiza opções dos seletores de campo com base na camada atual."""
    path, layer = self._resolve_input_layer()

    # Se modo line edit (arquivo externo), tenta carregar só para ler campos
    if layer is None and path:
        loaded = VectorLayerSource.open_vector_layer(path, tool_key=self.TOOL_KEY)
        if loaded and loaded.isValid():
            layer = loaded

    options = VectorLayerAttributes.get_field_options(layer) if layer else {}

    selected_id = self.id_field_selector.get_selected_key("id_field") or ""
    selected_time = self.time_field_selector.get_selected_key("time_field") or ""
    selected_group = self.group_field_selector.get_selected_key("group_field") or ""

    self.id_field_selector.set_options("id_field", options)
    self.time_field_selector.set_options("time_field", options)
    self.group_field_selector.set_options("group_field", options)

    if selected_id:
        self.id_field_selector.set_selected_key("id_field", selected_id)
    if selected_time:
        self.time_field_selector.set_selected_key("time_field", selected_time)
    if selected_group:
        self.group_field_selector.set_selected_key("group_field", selected_group)
```

### 5.6 `_load_prefs()` Novo

```python
def _load_prefs(self):
    """Restaura preferências na UI."""
    operational_fields = self.preferences.get("operational_fields", {})
    if "largura_lateral" in operational_fields and "largura_tiro" not in operational_fields:
        operational_fields["largura_tiro"] = operational_fields["largura_lateral"]
    self.operational_fields.set_values(operational_fields)
    self.sensitivity_fields.set_values(self.preferences.get("sensitivity_fields", {}))

    # Path mode — chaves são os STR, então funciona direto
    path_mode = self.preferences.get("path_mode", STR.BOTH_PATH)
    if path_mode in self.PATH_MODES:
        self.radio_path_mode.set_selected_key(path_mode)

    # Output fields
    selected_output_fields = self.preferences.get(self.PREF_SELECTED_OUTPUT_FIELDS, [])
    normalized_selected = self._normalize_selected_output_fields(selected_output_fields)
    self.output_fields_grid.set_checked_keys(normalized_selected)
    shot_id_cb = self.output_fields_grid.get_checkbox(self.REQUIRED_OUTPUT_FIELD)
    if shot_id_cb is not None:
        shot_id_cb.setChecked(True)
        shot_id_cb.setEnabled(False)

    # Save selectors — lock button controla habilitado
    self.save_points_selector.set_lock_state(
        "save_points", self.preferences.get("save_to_folder", False)
    )
    self.save_points_selector.set_path(
        "save_points", self.preferences.get("last_output_file", "")
    )
    self.save_track_selector.set_lock_state(
        "save_track", self.preferences.get("save_track_to_folder", False)
    )
    self.save_track_selector.set_path(
        "save_track", self.preferences.get("last_output_track_file", "")
    )

    # Combinos
    self.group_field_selector.set_selected_key(
        "group_field", self.preferences.get("group_field", "")
    )
    self.judge_mode_selector.set_selected_key(
        "judge_mode", self.preferences.get(self.PREF_JUDGE_MODE, "Complexo")
    )

    # Estados de expansão dos colapsáveis
    self.operational_params.set_expanded(self.preferences.get("expanded_operational", True))
    self.sensitivity_params.set_expanded(self.preferences.get("expanded_sensitivity", True))
    self.attributes_params.set_expanded(self.preferences.get("expanded_attributes", True))
    self.save_collapsible.set_expanded(self.preferences.get("expanded_save", False))

    self._refresh_field_selectors()
```

### 5.7 `_save_prefs()` Novo

```python
def _save_prefs(self):
    """Persiste preferências da UI."""
    self.preferences["id_field"] = self.id_field_selector.get_selected_key("id_field") or ""
    self.preferences["time_field"] = self.time_field_selector.get_selected_key("time_field") or ""
    self.preferences["group_field"] = self.group_field_selector.get_selected_key("group_field") or ""
    self.preferences[self.PREF_JUDGE_MODE] = self.judge_mode_selector.get_selected_key("judge_mode") or "Complexo"
    self.preferences["operational_fields"] = self.operational_fields.get_values()
    self.preferences["sensitivity_fields"] = self.sensitivity_fields.get_values()
    self.preferences["path_mode"] = self.radio_path_mode.get_selected_key()
    self.preferences[self.PREF_SELECTED_OUTPUT_FIELDS] = self._get_selected_output_fields()

    # Save selectors — lock button estado = habilitado
    self.preferences["save_to_folder"] = self.save_points_selector.get_lock_state("save_points")
    self.preferences["last_output_file"] = self.save_points_selector.get_path("save_points")
    self.preferences["save_track_to_folder"] = self.save_track_selector.get_lock_state("save_track")
    self.preferences["last_output_track_file"] = self.save_track_selector.get_path("save_track")

    self.preferences["window_width"] = self.width()
    self.preferences["window_height"] = self.height()

    # Estados de expansão dos colapsáveis
    self.preferences["expanded_operational"] = self.operational_params.is_expanded()
    self.preferences["expanded_sensitivity"] = self.sensitivity_params.is_expanded()
    self.preferences["expanded_attributes"] = self.attributes_params.is_expanded()
    self.preferences["expanded_save"] = self.save_collapsible.is_expanded()

    Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
```

### 5.8 `_get_selected_output_fields()` — usar nova API

```python
def _get_selected_output_fields(self):
    """Retorna campos de saída marcados."""
    selected = (
        self.output_fields_grid.get_checked_keys()
        if hasattr(self, "output_fields_grid")
        else []
    )
    return self._normalize_selected_output_fields(selected)
```

### 5.9 `execute_tool()` — ajustes de API

```python
def execute_tool(self):
    """Executa processamento de segmentação."""
    path, layer = self._resolve_input_layer()

    if isinstance(layer, QgsVectorLayer):
        pass  # camada carregada — OK
    elif path:
        loaded = VectorLayerSource.open_vector_layer(path, tool_key=self.TOOL_KEY)
        if loaded and loaded.isValid():
            layer = loaded
            ProjectUtils.add_layer(layer)
        else:
            QgisMessageUtil.bar_warning(self.iface, STR.SELECT_POINT_VECTOR_LAYER)
            return
    else:
        QgisMessageUtil.bar_warning(self.iface, STR.SELECT_POINT_VECTOR_LAYER)
        return

    field_id = self.id_field_selector.get_selected_key("id_field")
    field_time = self.time_field_selector.get_selected_key("time_field")
    field_group = self.group_field_selector.get_selected_key("group_field")

    if not field_id:
        QgisMessageUtil.bar_warning(self.iface, STR.SELECT_REQUIRED_FIELDS)
        return

    # ... resto do método igual, exceto:
    # - self.operational_fields.get_values() → igual
    # - self.sensitivity_fields.get_values() → igual
    # - self.judge_mode_selector.get_selected_key() → agora com "judge_mode"
    judge_mode = self.judge_mode_selector.get_selected_key("judge_mode")
    # - self.radio_path_mode.get_selected_text() → agora get_selected_key() (mesma coisa)
    path_mode = self.radio_path_mode.get_selected_key()

    # Save checks:
    # - self.save_points_selector.is_enabled() → get_lock_state("save_points")
    if self.save_points_selector.get_lock_state("save_points"):
        out_path = self.save_points_selector.get_path("save_points").strip()
        ...
    # - self.save_track_selector.is_enabled() → get_lock_state("save_track")
    if self.save_track_selector.get_lock_state("save_track"):
        line_out_path = self.save_track_selector.get_path("save_track").strip()
        ...
```

---

## 6. MAPEAMENTO COMPLETO DE API — ANTES × DEPOIS

| Local | Antigo | Novo |
|-------|--------|------|
| `execute_tool` | `self.layer_input.current_layer()` | `self._resolve_input_layer()` → `(path, layer)` via `getitem()` |
| `execute_tool` | `self.layer_input.only_selected_enabled()` | `self.layer_input.get_checked_state("camada")` |
| `execute_tool` | `self.id_field_selector.get_selected_key()` | `self.id_field_selector.get_selected_key("id_field")` |
| `execute_tool` | `self.time_field_selector.get_selected_key()` | `self.time_field_selector.get_selected_key("time_field")` |
| `execute_tool` | `self.group_field_selector.get_selected_key()` | `self.group_field_selector.get_selected_key("group_field")` |
| `execute_tool` | `self.judge_mode_selector.get_selected_key()` | `self.judge_mode_selector.get_selected_key("judge_mode")` |
| `execute_tool` | `self.radio_path_mode.get_selected_text()` | `self.radio_path_mode.get_selected_key()` (chaves = STR) |
| `execute_tool` | `self.save_points_selector.is_enabled()` | `self.save_points_selector.get_lock_state("save_points")` |
| `execute_tool` | `self.save_points_selector.get_file_path()` | `self.save_points_selector.get_path("save_points")` |
| `execute_tool` | `self.save_track_selector.is_enabled()` | `self.save_track_selector.get_lock_state("save_track")` |
| `execute_tool` | `self.save_track_selector.get_file_path()` | `self.save_track_selector.get_path("save_track")` |
| `_load_prefs` | `self.radio_path_mode.set_selected_index(i)` | `self.radio_path_mode.set_selected_key(path_mode)` |
| `_load_prefs` | `self.save_points_selector.set_enabled(b)` | `self.save_points_selector.set_lock_state("save_points", b)` |
| `_load_prefs` | `self.save_points_selector.set_file_path(p)` | `self.save_points_selector.set_path("save_points", p)` |
| `_load_prefs` | `self.save_track_selector.set_enabled(b)` | `self.save_track_selector.set_lock_state("save_track", b)` |
| `_load_prefs` | `self.save_track_selector.set_file_path(p)` | `self.save_track_selector.set_path("save_track", p)` |
| `_load_prefs` | `self.group_field_selector.set_selected_key(k)` | `self.group_field_selector.set_selected_key("group_field", k)` |
| `_load_prefs` | `self.judge_mode_selector.set_selected_key(k)` | `self.judge_mode_selector.set_selected_key("judge_mode", k)` |
| `_load_prefs` | `self.output_fields_grid.set_checked_keys(k)` | `self.output_fields_grid.set_checked_keys(k)` (MÉTODO NOVO) |
| `_load_prefs` | `self.output_fields_grid.get_checkbox(k)` | `self.output_fields_grid.get_checkbox(k)` (MÉTODO NOVO) |
| `_save_prefs` | `self.id_field_selector.get_selected_key()` | `self.id_field_selector.get_selected_key("id_field")` |
| `_save_prefs` | `self.time_field_selector.get_selected_key()` | `self.time_field_selector.get_selected_key("time_field")` |
| `_save_prefs` | `self.group_field_selector.get_selected_key()` | `self.group_field_selector.get_selected_key("group_field")` |
| `_save_prefs` | `self.judge_mode_selector.get_selected_key()` | `self.judge_mode_selector.get_selected_key("judge_mode")` |
| `_save_prefs` | `self.radio_path_mode.get_selected_text()` | `self.radio_path_mode.get_selected_key()` |
| `_save_prefs` | `self.save_points_selector.is_enabled()` | `self.save_points_selector.get_lock_state("save_points")` |
| `_save_prefs` | `self.save_points_selector.get_file_path()` | `self.save_points_selector.get_path("save_points")` |
| `_save_prefs` | `self.save_track_selector.is_enabled()` | `self.save_track_selector.get_lock_state("save_track")` |
| `_save_prefs` | `self.save_track_selector.get_file_path()` | `self.save_track_selector.get_path("save_track")` |
| `_get_selected_output_fields` | `self.output_fields_grid.get_checked_keys()` | `self.output_fields_grid.get_checked_keys()` (MÉTODO NOVO) |
| `_refresh_field_selectors` | `self.layer_input.current_layer()` | `self._resolve_input_layer()` → `(path, layer)` via `getitem()` |

---

## 7. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| `GridCheckbox` sem `get_checked_keys()` quebra `_get_selected_output_fields()` | Alta | Alto | Adicionar método na FASE 1 ANTES da migração |
| Arquivo externo não carregado — precisa carregar via VectorLayerSource antes de processar | Média | Médio | `_resolve_input_layer()` carrega arquivo temporário e adiciona ao projeto |
| `GridRadioButton` chaves = STR mudam semântica de `PATH_MODES` | Baixa | Baixo | `PATH_MODES` já contém os mesmos STR — `path_mode` salvo nas prefs continua igual (STR) |
| Lock button semântica invertida (True = habilitado, False = bloqueado) | Média | Baixo | `get_lock_state()` retorna True = desbloqueado — mapear como `is_enabled()` |
| `add_execution_buttons` substitui uso de `add_items` com `buttons_layout` | Baixa | Baixo | Seguir padrão: `self.layout.add_execution_buttons(self.action_buttons)` |
| Preferências antigas salvam `path_mode` como STR — novo `get_selected_key()` retorna STR | Baixa | Baixo | Chaves do GridRadioButton = STR → compatível |

---

## 8. ORDEM DE EXECUÇÃO RECOMENDADA

```
1. FASE 1 — Adicionar métodos ao GridCheckbox (get_checked_keys, set_checked_keys, get_checkbox) + getitem() ao ComplexSelector
2. FASE 2 — Migrar imports e _build_ui()
3. Migrar _load_prefs() e _save_prefs()
4. Migrar _refresh_field_selectors() com _resolve_input_layer() (usando getitem())
5. Migrar execute_tool() — ajustar chamadas de API
6. FASE 3 — Testar fluxo completo
7. FASE 4 — Atualizar changelog e plano_eliminacao_widgetfactory.md
```

---

## 9. CHECKLIST RESUMIDO

### FASE 1 — Preparação (2 tabelas)
- [x] **1.1** `GridCheckbox.get_checked_keys()`, `set_checked_keys()`, `get_checkbox()`
- [x] **1.2** `ComplexSelector.getitem()` → tupla `(path, layer)`

### FASE 2 — Migração ✅ (2.3.80.1)
- [x] **2.1** Substituir imports (remover WidgetFactory, adicionar new_widgets)
- [x] **2.2** Migrar `_build_ui()` completo
- [x] **2.3** Migrar `_load_prefs()` com nova API
- [x] **2.4** Migrar `_save_prefs()` com nova API
- [x] **2.5** Migrar `_refresh_field_selectors()` com `_resolve_input_layer()`
- [x] **2.6** Migrar `_on_layer_changed()` — callback com paths
- [x] **2.7** Migrar `execute_tool()` — usar `_resolve_input_layer()`
- [x] **2.8** Migrar `_get_selected_output_fields()` — usar `get_checked_keys()`
- [x] **2.9** Remover imports de `WidgetFactory` e `Styles`
- [x] **2.10** Adicionar helpers: `_resolve_input_layer()`, `_select_all_output_fields()`, `_deselect_all_output_fields()`, `_invert_output_fields()`
- [x] **2.11** Suporte a campo vazio (allow_empty=True) em time_field e group_field — restaura comportamento do DropdownSelectorWidget allow_empty=True

### FASE 3 — Validação
- [x] **3.1** Plugin abre sem erros
- [x] **3.2** Layer input com camada carregada no QGIS
- [x] **3.3** Layer input com arquivo externo não carregado
- [x] **3.4** Features checkbox aparece no modo layer
- [x] **3.5** Dropdowns populam corretamente
- [x] **3.6** Input fields carregam/salvam valores
- [x] **3.7** Radio buttons selecionam corretamente
- [x] **3.8** Checkbox grid — shot_id fixo marcado/desabilitado
- [x] **3.9** Save selectors — lock button habilita/desabilita
- [x] **3.10** Collapsibles expandem/recolhem e persistem
- [x] **3.11** Botões de ação funcionam
- [x] **3.12** Preferências salvam/carregam corretamente
- [x] **3.13** Execução completa funciona (segmentação + linhas)
- [x] **3.14** Nenhum `setStyleSheet` no plugin
- [x] **3.15** Nenhum import de `WidgetFactory` ou `Styles`
- [x] **3.16** Combos opcionais (time_field/group_field) permitem campo vazio "Selecionar..."

### FASE 4 — Documentação ✅
- [x] **4.1** Atualizar `docs/ia/changelog.txt`
- [x] **4.2** Atualizar `docs/plano_eliminacao_widgetfactory.md` (marcar migrado)
- [x] **4.3** Atualizar SKILL_WIDGETS2.md com allow_empty/empty_text

---

## 10. COMPLEXIDADE ESTIMADA

**Geral: ALTA** — plugin grande com 9+ widgets, 4 collapsibles, lógica de preferências complexa, e suporte a arquivo externo não carregado.

**Esforço estimado:** 2-3 sessões de desenvolvimento
- Sessão 1: Preparação do GridCheckbox + Migração do `_build_ui()`
- Sessão 2: Migração do `_load_prefs()`, `_save_prefs()`, `execute_tool()` + helpers
- Sessão 3: Testes e correções

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-31 | 1.0.0 | Criação inicial — plano de migração DividePointsByStripsPlugin |
| 2026-07-31 | 2.0.0 | **Revisão completa:** (1) Usar `GridComplexSelector.get()` + `ComplexSelector.getitem()` → tupla `(path, layer)` — NÃO criar `get_layer()`; (2) GridRadioButton com chaves = STR para compatibilidade com `get_selected_text()`; (3) Save selectors usam `allow_lock_check` (lock button) — NÃO criar `enable_checkbox`; (4) GridCheckbox ganha `get_checked_keys()`, `set_checked_keys()`, `get_checkbox()`; (5) `ComplexSelector` ganha `getitem()` — método genérico que retorna `(path, layer)`; (6) Adicionado `_resolve_input_layer()` que usa `getitem()` para suportar arquivo externo não carregado |
| 2026-07-31 | 3.0.0 | **MIGRAÇÃO CONCLUÍDA ✅ (2.3.80.1/2.3.80.2):** Plugin 100% sem WidgetFactory. GridComboBox com chaves identificadoras. Save selectors via lock_state. Corrigidos bugs (advanced_params, duplicados). **Adicionado suporte a campo vazio nos combos opcionais:** SimpleComboBox/GridComboBox com `allow_empty`/`empty_text` — time_field e group_field usam `allow_empty=True` restaurando comportamento do DropdownSelectorWidget. Changelog, plano_eliminacao_widgetfactory.md v5.7.0 e SKILL_WIDGETS2.md v2.8.0 atualizados. |
