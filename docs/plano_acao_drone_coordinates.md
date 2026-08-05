# 🎯 PLANO DE AÇÃO: Migração do DroneCoordinates para Novo Sistema de Widgets

**Objetivo:** Migrar o `DroneCoordinates` do `WidgetFactory` para o novo sistema `resources/widgets/`, eliminando dependência da Factory e de `resources/styles/`.

**Data:** 2026-08-04
**Versão:** 5.9.0
**Autor:** Cadmus Engineering

---

## 1. Contexto

O `DroneCoordinates` é a ferramenta #9 da FASE 2 do plano de eliminação da WidgetFactory. Atualmente usa:

| Widget atual | Factory | Widget alvo (widgets) |
|-------------|---------|--------------------------|
| Pasta MRK | `create_path_selector` (folder) | `GridComplexSelector` (folder input) |
| Opções (checkboxes) | `create_checkbox_grid` | `GridCheckbox` (1 coluna) |
| Logo | `create_save_file_selector` | `GridComplexSelector` (output file) + `GridCheckbox` |
| Título do projeto | `create_input_fields_widget` | `GridInputFields` |
| EXIF Fields | `create_collapsible_parameters` + `create_checkbox_grid` | `CollapsibleParametersWidget` + `GridCheckbox` |
| DJI Fields (XMP) | `create_collapsible_parameters` + `create_checkbox_grid` | `CollapsibleParametersWidget` + `GridCheckbox` |
| Custom Fields | `create_collapsible_parameters` + `create_checkbox_grid` | `CollapsibleParametersWidget` + `GridCheckbox` |
| Initial Fields | `create_collapsible_parameters` + `create_checkbox_grid` | `CollapsibleParametersWidget` + `GridCheckbox` |
| MRK Fields | `create_collapsible_parameters` + `create_checkbox_grid` | `CollapsibleParametersWidget` + `GridCheckbox` |
| Salvamento | `create_collapsible_parameters` + `create_save_file_selector` (x2) | `CollapsibleParametersWidget` + `GridComplexSelector` (output + lock) |
| Estilos (QML) | `create_collapsible_parameters` + `create_qml_selector` (x2) | `CollapsibleParametersWidget` + `GridComplexSelector` (output QML + lock) |
| Botões | `create_bottom_action_buttons` | `GridExecutionButtons` |

---

## 2. Análise do Estado Atual

### 2.1 Widgets usados hoje (via Factory)

```python
# ── Pasta MRK (folder input) ──
folder_layout, self.folder_selector = WidgetFactory.create_path_selector(
    parent=self, title=STR.MRK_FOLDER, mode="folder", separator_bottom=True,
)

# ── Opções (Collapsible) ──
opts_layout, self.opts_collapsible = WidgetFactory.create_collapsible_parameters(
    parent=self, title=STR.OPTIONS, expanded_by_default=False,
)

# ── Logo (só se licença válida) ──
logo_layout, self.logo_selector = WidgetFactory.create_save_file_selector(
    parent=self, file_filter=StringManager.FILTER_IMAGES,
    checkbox_text=STR.USE_LOGO, label_text=STR.LOGO_LABEL, mode="file",
)
self.opts_collapsible.add_content_layout(logo_layout)

# ── Título (só se licença válida) ──
title_layout, self.title_input = WidgetFactory.create_input_fields_widget(
    fields_dict=title_fields, parent=self,
)
self.opts_collapsible.add_content_layout(title_layout)

# ── Checkboxes de opções ──
opts_checkbox_layout, self.checkbox_map = WidgetFactory.create_checkbox_grid(
    options_data=checkbox_options, items_per_row=1,
    checked_by_default=False, separator_bottom=False,
)
self.opts_collapsible.add_content_layout(opts_checkbox_layout)

# ── EXIF Fields (Collapsible + checkbox grid) ──
exif_layout, self.exif_fields_collapsible = WidgetFactory.create_collapsible_parameters(
    parent=self, title="EXIF Fields", expanded_by_default=False,
)
exif_items = StringAdapter.to_key_label_description(MetadataFields.EXIF_FIELDS)
exif_grid_layout, self.exif_fields_grid = WidgetFactory.create_checkbox_grid(
    options_data=exif_items, items_per_row=2, checked_by_default=True,
    return_widget=True, separator_bottom=False, show_control_buttons=True,
)
self.exif_fields_collapsible.add_content_layout(exif_grid_layout)

# ... (mesmo padrão para DJI/XMP, Custom, Initial, MRK) ...

# ── Salvamento (Collapsible + save selectors) ──
save_layout, self.save_collapsible = WidgetFactory.create_collapsible_parameters(
    parent=self, title=STR.SAVING, expanded_by_default=False,
)
save_points_layout, self.save_points_selector = WidgetFactory.create_save_file_selector(
    parent=self, file_filter=StringManager.FILTER_VECTOR,
    checkbox_text=STR.SAVE_POINTS_CHECKBOX, label_text=STR.SAVE_IN,
)
self.save_collapsible.add_content_layout(save_points_layout)
# save_track_selector — mesmo padrão

# ── Estilos QML (Collapsible + qml selectors) ──
styles_layout, self.styles_collapsible = WidgetFactory.create_collapsible_parameters(
    parent=self, title=STR.STYLES, expanded_by_default=False,
)
qml_points_layout, self.qml_points_selector = WidgetFactory.create_qml_selector(
    parent=self, checkbox_text=STR.APPLY_STYLE_POINTS, label_text=STR.QML_POINTS,
)
self.styles_collapsible.add_content_layout(qml_points_layout)
# qml_track_selector — mesmo padrão

# ── Botões ──
buttons_layout, self.action_buttons = WidgetFactory.create_bottom_action_buttons(
    parent=self, run_callback=self.execute_tool, close_callback=self.close,
    info_callback=self.show_info_dialog, tool_key=self.TOOL_KEY,
)

# ── Layout final ──
self.layout.add_items([folder_layout, opts_layout, exif_layout, xmp_layout,
    custom_layout, initial_layout, mrk_layout, save_layout, styles_layout, buttons_layout])
```

### 2.2 Padrões na API atual

| Método atual | Novo método |
|--------------|-------------|
| `self.folder_selector.get_paths()` | `self.grid_input.get_path("pasta_mrk")` |
| `self.checkbox_map["recursive"].isChecked()` | `self.opts_checkbox.is_checked("recursive")` |
| `self.checkbox_map["use_mrk"].isChecked()` | `self.opts_checkbox.is_checked("use_mrk")` |
| `self.chk_photos.toggled.connect(...)` | `self.opts_checkbox.widget("photos").toggled.connect(...)` |
| `self.exif_fields_grid.get_checked_keys()` | `self.exif_checkbox.get_checked_keys()` |
| `self.exif_fields_grid.set_checked_keys(keys)` | `self.exif_checkbox.set_checked_keys(keys)` |
| `self.save_points_selector.is_enabled()` | `self.grid_save.get_lock_state("save_points")` |
| `self.save_points_selector.get_file_path()` | `self.grid_save.get_path("save_points")` |
| `self.save_points_selector.set_enabled(bool)` | `self.grid_save.set_lock_state("save_points", bool)` |
| `self.save_points_selector.set_file_path(path)` | `self.grid_save.set_path("save_points", path)` |
| `self.opts_collapsible.set_expanded(bool)` | `self.opts_collapsible.set_expanded(bool)` (igual) |
| `self.opts_collapsible.is_expanded()` | `self.opts_collapsible.is_expanded()` (igual) |

### 2.3 Contrato base

- Herda de `BasePluginMTL` ✅
- `TOOL_KEY = ToolKey.DRONE_COORDINATES` ✅
- Logger via base ✅
- Preferences via `self.preferences` ✅
- `AUTO_SAVE_PREFS_ON_CLOSE = True` ✅
- `REGISTRY_LEVEL = 3` (controle de licença) ✅

---

## 3. Estratégia de Migração

### 3.1 GridComplexSelector — Pasta MRK (folder input)

**Requisito do usuário:** gridcomplex folder input para a pasta MRK.

```python
self.grid_input = GridComplexSelector(
    config={
        "pasta_mrk": {
            "label": STR.MRK_FOLDER,
            "description": "Pasta contendo os arquivos MRK",
            "allow_file": False,
            "allow_folder": True,
            "selection_mode": "folder",
            "mode_type": "input",
        },
    },
    tool_key=self.TOOL_KEY,
    separator_bottom=False,
    parent=self,
)
self.layout.addWidget(self.grid_input)
self.layout.addWidget(SeparatorWidget())
```

**API:**
- `self.grid_input.get_path("pasta_mrk")` → str
- `self.grid_input.set_path("pasta_mrk", path)` → restaura prefs
- `self.grid_input.get("pasta_mrk")` → ComplexSelector (acesso direto)

### 3.2 GridCheckbox — Opções (1 coluna, dentro do collapsible OPTIONS)

```python
self.opts_collapsible = CollapsibleParametersWidget(
    title=STR.OPTIONS,
    expanded_by_default=False,
    parent=self,
)
self.layout.addWidget(self.opts_collapsible)
```

**Checkbox de opções:**

```python
checkbox_options = dict(self.CHECKBOX_OPTIONS)
if not is_lic_valid:
    checkbox_options.pop("generate_report", None)

self.opts_checkbox = GridCheckbox(
    config={
        key: {"label": label} for key, label in checkbox_options.items()
    },
    items_per_row=1,
    separator_bottom=False,
    parent=self,
)
self.opts_collapsible.add_content_widget(self.opts_checkbox)
```

**Conexões (após criação):**
```python
self.chk_photos = self.opts_checkbox.widget("photos")
if self.chk_photos is not None:
    self.chk_photos.toggled.connect(self.on_photos_changed)

self.chk_use_mrk = self.opts_checkbox.widget("use_mrk")
if self.chk_use_mrk is not None:
    self.chk_use_mrk.toggled.connect(self._on_use_mrk_changed)
```

**Logo e Título (só se licença válida) — dentro do collapsible OPTIONS:**

```python
if is_lic_valid:
    # Logo: GridComplexSelector (output file + lock) dentro do collapsible
    self.logo_selector = GridComplexSelector(
        config={
            "logo": {
                "label": STR.LOGO_LABEL,
                "description": "Arquivo de logotipo",
                "mode_type": "output",
                "allow_file": True,
                "allow_folder": False,
                "file_filter": StringManager.FILTER_IMAGES,
                "allow_lock_check": True,
                "lock_check_default": False,
            },
        },
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    self.opts_collapsible.add_content_widget(self.logo_selector)

    # Título: GridInputFields dentro do collapsible
    self.title_input = GridInputFields(
        config={
            "project_title": {
                "label": STR.PROJECT_TITLE,
                "description": STR.PROJECT_TITLE_HINT,
                "default": "",
            },
        },
        title=None,
        separator_bottom=False,
        parent=self,
    )
    self.opts_collapsible.add_content_widget(self.title_input)
```

**Nota de API para o logo (lock = enable antigo):**
| Antigo (SelectorWidget) | Novo (GridComplexSelector) |
|--------------------------|----------------------------|
| `logo_selector.is_enabled()` | `logo_selector.get_lock_state("logo")` |
| `logo_selector.set_enabled(bool)` | `logo_selector.set_lock_state("logo", bool)` |
| `logo_selector.get_file_path()` | `logo_selector.get_path("logo")` |
| `logo_selector.set_file_path(path)` | `logo_selector.set_path("logo", path)` |

### 3.3 Collapsible + GridCheckbox — Metadados (EXIF, DJI, Custom, Initial, MRK)

**Padrão repetido 5×** — EXIF, DJI (XMP), Custom, Initial, MRK.

```python
# ── EXIF Fields ──
self.exif_fields_collapsible = CollapsibleParametersWidget(
    title="EXIF Fields",
    expanded_by_default=False,
    parent=self,
)
self.layout.addWidget(self.exif_fields_collapsible)

exif_items = StringAdapter.to_key_label_description(MetadataFields.EXIF_FIELDS)
self.exif_checkbox = GridCheckbox(
    config={
        key: {"label": item["label"], "description": item.get("description", "")}
        for key, item in exif_items
    },
    items_per_row=2,
    separator_bottom=False,
    parent=self,
)
self.exif_checkbox.set_checked_keys(MetadataFields.exif_keys())  # checked_by_default=True
self.exif_fields_collapsible.add_content_widget(self.exif_checkbox)
```

**⚠️ Ponto de atenção — control_buttons (Selecionar/Remover/Inverter):**
- O antigo `show_control_buttons=True` criava botões de controle internamente no `GridCheckboxWidget`.
- O novo `GridCheckbox` suporta `control_buttons_config` para criar `GridModernButtons`.
- Para replicar o comportamento, passar:

```python
self.exif_checkbox = GridCheckbox(
    config={...},
    items_per_row=2,
    control_buttons_config={
        "select_all": {"label": STR.SELECT_ALL, "callback": self.exif_checkbox.select_all},
        "deselect_all": {"label": STR.DESELECT_ALL, "callback": self.exif_checkbox.deselect_all},
        "invert": {"label": STR.INVERT, "callback": self.exif_checkbox.invert_selection},
    },
    parent=self,
)
```

> **Verificar strings Necessárias:** `STR.SELECT_ALL`, `STR.DESELECT_ALL`, `STR.INVERT` — adicionar em Strings_pt_BR se não existirem.

**API mantida (compatível com o antigo GridCheckboxWidget):**
| Método antigo | Novo método |
|---------------|-------------|
| `get_checked_keys()` | `get_checked_keys()` (igual) |
| `set_checked_keys(keys)` | `set_checked_keys(keys)` (igual) |
| `get_checkbox("key")` | `get_checkbox("key")` (igual) |
| `toggled.connect()` via `get_checkbox()` | `widget("key").toggled.connect()` |

### 3.4 Collapsible + GridComplexSelector — Salvamento (SAVING)

```python
self.save_collapsible = CollapsibleParametersWidget(
    title=STR.SAVING,
    expanded_by_default=False,
    parent=self,
)
self.layout.addWidget(self.save_collapsible)

self.grid_save = GridComplexSelector(
    config={
        "save_points": {
            "label": STR.SAVE_IN,
            "description": STR.SAVE_POINTS_CHECKBOX,
            "mode_type": "output",
            "parent": "pasta_mrk",       # cross-grid
            "allow_file": True,
            "allow_folder": False,
            "file_filter": StringManager.FILTER_VECTOR,
            "allow_lock_check": True,     # substitui checkbox "Salvar pontos?"
            "lock_check_default": False,
        },
        "save_track": {
            "label": STR.SAVE_IN,
            "description": STR.SAVE_TRACK_CHECKBOX,
            "mode_type": "output",
            "parent": "pasta_mrk",       # cross-grid
            "allow_file": True,
            "allow_folder": False,
            "file_filter": StringManager.FILTER_VECTOR,
            "allow_lock_check": True,
            "lock_check_default": False,
        },
    },
    tool_key=self.TOOL_KEY,
    grid_id="grid_save",                 # para parent cross-grid
    parent=self,
)
self.save_collapsible.add_content_widget(self.grid_save)
```

**⚠️ Cross-grid parent linking (NOVO requisito):**
- O antigo `SelectorWidget` tinha checkbox interno que habilitava/desabilitava o campo.
- O novo padrão usa `allow_lock_check=True` — checkbox LOCK desbloqueia/bloqueia o seletor.
- Para o `parent` cross-grid (pasta_mrk está em outro GridComplexSelector), o config deve usar `parent="grid_input.pasta_mrk"`.
- **Ajuste necessário:** `GridComplexSelector._resolve_parent_selector()` já suporta parent cross-grid via registro global (`grid_id.selector_key`). Verificar se o `_generate_output` em folder mode gera pasta corretamente quando o parent é folder.

**API de lock (substitui checkbox salvar):**
| Antigo | Novo |
|--------|------|
| `save_points_selector.is_enabled()` | `grid_save.get_lock_state("save_points")` |
| `save_points_selector.set_enabled(bool)` | `grid_save.set_lock_state("save_points", bool)` |
| `save_points_selector.get_file_path()` | `grid_save.get_path("save_points")` |
| `save_points_selector.set_file_path(path)` | `grid_save.set_path("save_points", path)` |

### 3.5 Collapsible + GridComplexSelector — Estilos QML (STYLES)

```python
self.styles_collapsible = CollapsibleParametersWidget(
    title=STR.STYLES,
    expanded_by_default=False,
    parent=self,
)
self.layout.addWidget(self.styles_collapsible)

self.grid_qml = GridComplexSelector(
    config={
        "qml_points": {
            "label": STR.QML_POINTS,
            "description": STR.APPLY_STYLE_POINTS,
            "mode_type": "output",
            "parent": "grid_input.pasta_mrk",
            "allow_file": True,
            "allow_folder": False,
            "file_filter": StringManager.FILTER_QGIS_STYLE,
            "allow_lock_check": True,
            "lock_check_default": False,
        },
        "qml_track": {
            "label": STR.QML_TRACK,
            "description": STR.APPLY_STYLE_TRACK,
            "mode_type": "output",
            "parent": "grid_input.pasta_mrk",
            "allow_file": True,
            "allow_folder": False,
            "file_filter": StringManager.FILTER_QGIS_STYLE,
            "allow_lock_check": True,
            "lock_check_default": False,
        },
    },
    tool_key=self.TOOL_KEY,
    grid_id="grid_qml",
    parent=self,
)
self.styles_collapsible.add_content_widget(self.grid_qml)
```

**API de lock:**
| Antigo | Novo |
|--------|------|
| `qml_points_selector.is_enabled()` | `grid_qml.get_lock_state("qml_points")` |
| `qml_points_selector.set_enabled(bool)` | `grid_qml.set_lock_state("qml_points", bool)` |
| `qml_points_selector.get_file_path()` | `grid_qml.get_path("qml_points")` |
| `qml_points_selector.set_file_path(path)` | `grid_qml.set_path("qml_points", path)` |
| `qml_track_selector.is_enabled()` | `grid_qml.get_lock_state("qml_track")` |
| `qml_track_selector.set_enabled(bool)` | `grid_qml.set_lock_state("qml_track", bool)` |
| `qml_track_selector.get_file_path()` | `grid_qml.get_path("qml_track")` |
| `qml_track_selector.set_file_path(path)` | `grid_qml.set_path("qml_track", path)` |

### 3.6 GridExecutionButtons — Ações (fora do scroll)

```python
self.action_buttons = GridExecutionButtons(
    config={
        "run": {
            "label": STR.EXECUTE,
            "description": "Inicia o processamento de coordenadas de drone",
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

**⚠️ REGRA ABSOLUTA:** usar `self.layout.add_execution_buttons()` (fora do scroll), NUNCA `addWidget()`.

---

## 4. Layout Final do Plugin

```python
def _build_ui(self, **kwargs):
    super()._build_ui(
        title=STR.DRONE_COORDINATES_TITLE,
        icon_path="coord.ico",
        enable_scroll=True,
    )

    # Verificação de licença
    is_lic_valid = self._check_registry_level()

    # ── Pasta MRK (GridComplexSelector folder input) ──
    self.grid_input = GridComplexSelector(
        config={
            "pasta_mrk": {
                "label": STR.MRK_FOLDER,
                "description": "Pasta contendo os arquivos MRK",
                "allow_file": False,
                "allow_folder": True,
                "mode_type": "input",
            },
        },
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    self.layout.addWidget(self.grid_input)
    self.layout.addWidget(SeparatorWidget())

    # ── Opções (CollapsibleParametersWidget) ──
    self.opts_collapsible = CollapsibleParametersWidget(
        title=STR.OPTIONS, expanded_by_default=False, parent=self,
    )
    self.layout.addWidget(self.opts_collapsible)

    if is_lic_valid:
        # Logo (GridComplexSelector output + lock)
        self.logo_selector = GridComplexSelector(...)  # seção 3.2
        self.opts_collapsible.add_content_widget(self.logo_selector)

        # Título (GridInputFields)
        self.title_input = GridInputFields(...)  # seção 3.2
        self.opts_collapsible.add_content_widget(self.title_input)

    # Checkboxes de opções (GridCheckbox 1 coluna)
    self.opts_checkbox = GridCheckbox(...)  # seção 3.2
    self.opts_collapsible.add_content_widget(self.opts_checkbox)

    # Conexões de dependência
    self.chk_photos = self.opts_checkbox.widget("photos")
    if self.chk_photos is not None:
        self.chk_photos.toggled.connect(self.on_photos_changed)
    self.chk_use_mrk = self.opts_checkbox.widget("use_mrk")
    if self.chk_use_mrk is not None:
        self.chk_use_mrk.toggled.connect(self._on_use_mrk_changed)

    # ── Metadados (5× CollapsibleParametersWidget + GridCheckbox) ──
    self.exif_fields_collapsible = CollapsibleParametersWidget(
        title="EXIF Fields", expanded_by_default=False, parent=self)
    self.layout.addWidget(self.exif_fields_collapsible)
    self.exif_checkbox = GridCheckbox(...)  # seção 3.3
    self.exif_fields_collapsible.add_content_widget(self.exif_checkbox)

    # DJI (XMP), Custom, Initial, MRK — mesmo padrão

    # ── Salvamento (Collapsible + GridComplexSelector) ──
    self.save_collapsible = CollapsibleParametersWidget(
        title=STR.SAVING, expanded_by_default=False, parent=self)
    self.layout.addWidget(self.save_collapsible)
    self.grid_save = GridComplexSelector(...)  # seção 3.4
    self.save_collapsible.add_content_widget(self.grid_save)

    # ── Estilos QML (Collapsible + GridComplexSelector) ──
    self.styles_collapsible = CollapsibleParametersWidget(
        title=STR.STYLES, expanded_by_default=False, parent=self)
    self.layout.addWidget(self.styles_collapsible)
    self.grid_qml = GridComplexSelector(...)  # seção 3.5
    self.styles_collapsible.add_content_widget(self.grid_qml)

    # ── Botões (GridExecutionButtons — FORA do scroll) ──
    self.action_buttons = GridExecutionButtons(...)  # seção 3.6
    self.layout.add_execution_buttons(self.action_buttons)
```

---

## 5. Adaptação de _load_prefs / _save_prefs

### 5.1 _load_prefs

```python
def _load_prefs(self):
    # ── Pasta MRK ──
    folder_path = self.preferences.get("folder", "")
    if folder_path:
        self.grid_input.set_path("pasta_mrk", folder_path)

    # ── Checkboxes de opções ──
    self.opts_checkbox.set_checked("recursive", self.preferences.get("recursive", True))
    self.opts_checkbox.set_checked("use_mrk", self.preferences.get("use_mrk", True))
    self.opts_checkbox.set_checked("photos", self.preferences.get("photos", True))
    chk_report = self.opts_checkbox.widget("generate_report")
    if chk_report is not None:
        chk_report.setChecked(self.preferences.get("generate_report", True))

    # ── Campos de metadados ──
    initial_selected = self.preferences.get(self.PREF_INITIAL_FIELDS)
    if isinstance(initial_selected, list):
        self.initial_checkbox.set_checked_keys(
            MetadataFields.normalize_selected_keys(
                initial_selected, allowed_keys=MetadataFields.initial_keys()))
    # ... (exif, xmp, custom, mrk — mesmo padrão) ...

    # ── Salvamento (lock + path) ──
    self.grid_save.set_lock_state("save_points", self.preferences.get("save_file_pts", False))
    self.grid_save.set_path("save_points", self.preferences.get("output_path_pts", ""))
    self.grid_save.set_lock_state("save_track", self.preferences.get("save_file", False))
    self.grid_save.set_path("save_track", self.preferences.get("output_path", ""))

    # ── Logo (só se licença válida) ──
    if hasattr(self, "logo_selector"):
        self.logo_selector.set_lock_state("logo", self.preferences.get("logo_enabled", False))
        self.logo_selector.set_path("logo", self.preferences.get("logo_path", ""))

    # ── Título (só se licença válida) ──
    if hasattr(self, "title_input"):
        title_val = self.preferences.get("project_title", "")
        if title_val:
            self.title_input.set_value("project_title", title_val)

    # ── Estilos QML (lock + path) ──
    self.grid_qml.set_lock_state("qml_points", self.preferences.get("apply_style_points", False))
    self.grid_qml.set_path("qml_points", self.preferences.get("qml_path_points", ""))
    self.grid_qml.set_lock_state("qml_track", self.preferences.get("apply_style_track", False))
    self.grid_qml.set_path("qml_track", self.preferences.get("qml_path_track", ""))

    # ── Estados dos collapsibles ──
    self.opts_collapsible.set_expanded(self.preferences.get("opts_expanded", True))
    self.exif_fields_collapsible.set_expanded(self.preferences.get("exif_expanded", False))
    self.xmp_fields_collapsible.set_expanded(self.preferences.get("xmp_expanded", False))
    self.custom_fields_collapsible.set_expanded(self.preferences.get("custom_expanded", False))
    self.initial_fields_collapsible.set_expanded(self.preferences.get("initial_expanded", False))
    self.mrk_fields_collapsible.set_expanded(self.preferences.get("mrk_expanded", False))
    self.save_collapsible.set_expanded(self.preferences.get("save_expanded", False))
    self.styles_collapsible.set_expanded(self.preferences.get("styles_expanded", False))

    # ── Visibilidade do MRK conforme use_mrk ──
    use_mrk = self.preferences.get("use_mrk", True)
    self.mrk_fields_collapsible.setVisible(use_mrk)
    self.mrk_fields_collapsible.setEnabled(use_mrk)
```

### 5.2 _save_prefs

```python
def _save_prefs(self):
    # ── Pasta MRK ──
    self.preferences["folder"] = self.grid_input.get_path("pasta_mrk") or ""

    # ── Checkboxes de opções ──
    self.preferences["recursive"] = self.opts_checkbox.is_checked("recursive")
    self.preferences["use_mrk"] = self.opts_checkbox.is_checked("use_mrk")
    self.preferences["photos"] = self.opts_checkbox.is_checked("photos")
    chk_report = self.opts_checkbox.widget("generate_report")
    if chk_report is not None:
        self.preferences["generate_report"] = chk_report.isChecked()

    # ── Campos de metadados ──
    self.preferences[self.PREF_INITIAL_FIELDS] = self._get_selected_initial_fields()
    self.preferences[self.PREF_EXIF_FIELDS] = self._get_selected_exif_fields()
    self.preferences[self.PREF_XMP_FIELDS] = self._get_selected_xmp_fields()
    self.preferences[self.PREF_CUSTOM_FIELDS] = self._get_selected_custom_fields()
    self.preferences[self.PREF_MRK_FIELDS] = self._get_selected_mrk_fields()

    # ── Salvamento (lock + path) ──
    self.preferences["save_file"] = self.grid_save.get_lock_state("save_track")
    self.preferences["save_file_pts"] = self.grid_save.get_lock_state("save_points")
    self.preferences["output_path"] = self.grid_save.get_path("save_track")
    self.preferences["output_path_pts"] = self.grid_save.get_path("save_points")

    # ── Logo e título (só se licença válida) ──
    if hasattr(self, "title_input"):
        self.preferences["project_title"] = self.title_input.get_value("project_title")
    if hasattr(self, "logo_selector"):
        self.preferences["logo_path"] = self.logo_selector.get_path("logo")
        self.preferences["logo_enabled"] = self.logo_selector.get_lock_state("logo")

    # ── Estilos QML (lock + path) ──
    self.preferences["apply_style_track"] = self.grid_qml.get_lock_state("qml_track")
    self.preferences["qml_path_track"] = self.grid_qml.get_path("qml_track")
    self.preferences["apply_style_points"] = self.grid_qml.get_lock_state("qml_points")
    self.preferences["qml_path_points"] = self.grid_qml.get_path("qml_points")

    # ── Estados dos collapsibles ──
    self.preferences["opts_expanded"] = self.opts_collapsible.is_expanded()
    self.preferences["exif_expanded"] = self.exif_fields_collapsible.is_expanded()
    self.preferences["xmp_expanded"] = self.xmp_fields_collapsible.is_expanded()
    self.preferences["custom_expanded"] = self.custom_fields_collapsible.is_expanded()
    self.preferences["initial_expanded"] = self.initial_fields_collapsible.is_expanded()
    self.preferences["mrk_expanded"] = self.mrk_fields_collapsible.is_expanded()
    self.preferences["save_expanded"] = self.save_collapsible.is_expanded()
    self.preferences["styles_expanded"] = self.styles_collapsible.is_expanded()

    save_tool_prefs(self.TOOL_KEY, self.preferences)
```

### 5.3 Helpers _get_selected_*_fields (adaptação dos nomes)

```python
def _get_selected_exif_fields(self):
    return MetadataFields.normalize_selected_keys(
        self.exif_checkbox.get_checked_keys(),
        allowed_keys=MetadataFields.exif_keys(),
    )
# ... (xmp, custom, initial, mrk — mesmo padrão) ...
```

### 5.4 _on_use_mrk_changed (adaptação)

```python
def _on_use_mrk_changed(self, checked: bool):
    """Habilita/desabilita seção MRK conforme checkbox 'Obter dados MRK'."""
    self.mrk_fields_collapsible.setVisible(checked)
    self.mrk_fields_collapsible.setEnabled(checked)
    if not checked:
        self.mrk_checkbox.set_checked_keys([])
```

---

## 6. Adaptação de execute_tool

```python
def execute_tool(self):
    self.logger.info("Iniciando processamento de coordenadas de drone", code="EXEC_START")

    folder_path = self.grid_input.get_path("pasta_mrk") or ""
    if not folder_path:
        self.logger.error("Nenhum diretório selecionado", code="NO_SELECTION")
        return

    apply_photos = self.opts_checkbox.is_checked("photos")
    if apply_photos and not DependenciesManager.check_dependency("Pillow", self.TOOL_KEY):
        self.logger.warning(
            "Cruzamento com metadados solicitado sem Pillow disponível; será ignorado"
        )
        apply_photos = False
        self.opts_checkbox.set_checked("photos", False)

    first_path = folder_path
    base_folder = (
        os.path.dirname(first_path)
        if first_path and os.path.isfile(first_path)
        else first_path
    )

    self._save_prefs()

    DronePipelineService.execute(
        iface=self.iface,
        input_path=base_folder,
        paths=[folder_path],
    )
```

---

## 7. Ordem de Implementação

| # | Ação | Arquivo |
|---|------|---------|
| 1 | Verificar/suportar parent cross-grid no `GridComplexSelector._resolve_parent_selector()` — já existe via `grid_id.selector_key` no registro global | `resources/widgets/grid/GridComplexSelector.py` |
| 2 | Verificar `_generate_output()` no folder mode quando parent é **folder** (pasta MRK) — gerar subpasta quando aplicável | `resources/widgets/grid/GridComplexSelector.py` |
| 3 | Substituir imports da Factory por widgets (remover `WidgetFactory`, `StringAdapter` se não usado após migração) | `plugins/DroneCoordinates.py` |
| 4 | Reescrever `_build_ui` (seções 3.1–3.6) | `plugins/DroneCoordinates.py` |
| 5 | Adaptar `_load_prefs`/`_save_prefs` (seção 5) | `plugins/DroneCoordinates.py` |
| 6 | Adaptar `execute_tool` e `_on_use_mrk_changed` (seção 6, 5.4) | `plugins/DroneCoordinates.py` |
| 7 | Verificar strings STR.SELECT_ALL / STR.DESELECT_ALL / STR.INVERT em Strings_pt_BR | `i18n/Strings_pt_BR.py` |
| 8 | Remover imports não utilizados — flake8 F401 + linha vazia final (W292) | `plugins/DroneCoordinates.py` |
| 9 | Atualizar SKILL_WIDGETS2.md (padrão grid_complex_parent_cross_grid + lock checkbox em collapsible) | `docs/skills/SKILL_WIDGETS2.md` |
| 10 | Atualizar docs/plano_eliminacao_widgetfactory.md (DroneCoordinates migrado) | `docs/plano_eliminacao_widgetfactory.md` |
| 11 | Atualizar docs/ia/changelog.txt | `docs/ia/changelog.txt` |

---

## 8. Validação (Checklist)

```markdown
## Plugin: DroneCoordinates

### Análise
- [x] Quais widgets usa via Factory? create_path_selector (folder), create_collapsible_parameters (x8), create_checkbox_grid (x6), create_save_file_selector (x3), create_input_fields_widget (x1), create_qml_selector (x2), create_bottom_action_buttons (x1)
- [x] Pode usar Grid? SIM — GridComplexSelector + GridCheckbox + GridInputFields + CollapsibleParametersWidget + GridExecutionButtons
- [x] Obedece contrato PLUGIN_CONTRACT.md? SIM
- [x] TEM LOGGER? SIM (herda de BasePluginMTL)

### Migração
- [ ] Substituir WidgetFactory.create_xxx() por widgets
- [ ] Remover import WidgetFactory
- [ ] GridComplexSelector folder input para pasta MRK
- [ ] CollapsibleParametersWidget + GridCheckbox para metadados (EXIF, DJI, Custom, Initial, MRK)
- [ ] CollapsibleParametersWidget + GridComplexSelector (lock) para Salvamento
- [ ] CollapsibleParametersWidget + GridComplexSelector (lock) para Estilos QML
- [ ] GridCheckbox 1 coluna para opções (recursive, use_mrk, photos, generate_report)
- [ ] GridInputFields para título do projeto
- [ ] lock_state (get/set) substitui is_enabled/set_enabled dos save/qml/logo selectors
- [ ] GridExecutionButtons via add_execution_buttons()
- [ ] Adicionar SeparatorWidget() entre widgets
- [ ] manutenção de _on_use_mrk_changed com mrk_checkbox.set_checked_keys([])

### Pós-migração
- [ ] Plugin não importa de core/ui/WidgetFactory
- [ ] Plugin não importa de resources/styles/
- [ ] Plugin não chama setStyleSheet()
- [ ] flake8 limpo (sem imports não utilizados, linha vazia no final — W292)
- [ ] Atualizar docs/ia/changelog.txt
```

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| `_on_use_mrk_changed` depende de `self.checkbox_map["use_mrk"]` — migração para `opts_checkbox` | Alta | Alto | Refatorar para `self.opts_checkbox = GridCheckbox(...)` + `widget("use_mrk")` |
| `get_checked_keys()`/`set_checked_keys()` do novo GridCheckbox compatíveis? | Alta | Alto | Já implementados (linha 140-154 de GridCheckbox.py) — validar com MetadataFields.normalize_selected_keys |
| Lock checkbox do ComplexSelector substitui checkbox "Salvar em arquivo?" | Alta | Médio | `allow_lock_check=True` + `get/set_lock_state()` — padrão já validado no DividePointsByStripsPlugin |
| Cross-grid parent (pasta_mrk → save/qml) | Média | Médio | `GridComplexSelector._grid_registry` + `parent="grid_input.pasta_mrk"` — já suportado |
| `_generate_output` em folder mode com parent folder | Média | Alto | Validar: parent=pasta_mrk (folder), output=save_points — deve gerar subpasta ou só usar parent dir conforme config |
| Perda dos botões Selecionar/Remover/Inverter nos campos de metadados | Média | Médio | `control_buttons_config` no GridCheckbox — criar GridModernButtons internamente |
| `self.chk_photos`/`self.chk_use_mrk` acessados antes de existir | Média | Alto | Usar `if widget is not None:` (regra crítica #9 SKILL_WIDGETS2.md v2.7.0) |
| Remover import não utilizado `StringAdapter` (se não usar mais) | Baixa | Baixo | flake8 F401 |
| `show_info_dialog` não existe no novo GridExecutionButtons (uso `enable_info=True`) | Baixa | Baixo | GridExecutionButtons cria InfoDialog internamente via InstructionsManager |

---

## 10. Changelog Esperado

```
2.3.84 04/08/2026
[2.3.84.1][04/08/2026] DroneCoordinates migrado para novo sistema de widgets:
   - Plugin 100% sem WidgetFactory
   - GridComplexSelector: pasta_mrk (folder input) + grid_save + grid_qml (output com lock)
   - GridCheckbox 1 coluna (opções) + 5x GridCheckbox 2 colunas (EXIF/DJI/Custom/Initial/MRK) com control_buttons_config
   - CollapsibleParametersWidget x8 (Opções, EXIF, DJI, Custom, Initial, MRK, Salvamento, Estilos)
   - GridInputFields (título do projeto)
   - GridExecutionButtons via add_execution_buttons()
   - lock_state (get/set) substitui is_enabled/set_enabled dos save/qml/logo selectors
   - Cross-grid parent linking (grid_input.pasta_mrk → grid_save/grid_qml)
   - _on_use_mrk_changed refatorado com opts_checkbox.widget("use_mrk")
   - Plugin em conformidade com PLUGIN_CONTRACT.md
```

---

## 11. Resumo dos Widgets Novos Necessários

| Widget | Tipo | Arquivo | Status |
|--------|------|---------|--------|
| `GridComplexSelector` cross-grid parent validado | Grid | `resources/widgets/grid/GridComplexSelector.py` | ⬜ Validar `_resolve_parent_selector()` + `_grid_registry` |
| `GridComplexSelector` `_generate_output` folder-mode com parent folder | Grid | `resources/widgets/grid/GridComplexSelector.py` | ⬜ Validar comportamento |
| `GridCheckbox` `control_buttons_config` (Selecionar/Remover/Inverter) | Grid | `resources/widgets/grid/GridCheckbox.py` | ✅ Já existe |
| `CollapsibleParametersWidget` | Raiz | `resources/widgets/CollapsibleParametersWidget.py` | ✅ Já existe |
| `GridExecutionButtons` | Grid | `resources/widgets/grid/GridExecutionButtons.py` | ✅ Já existe |
| `GridInputFields` | Grid | `resources/widgets/grid/GridInputFields.py` | ✅ Já existe |

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-08-04 | 5.9.0 | Criação inicial — Plano de migração do DroneCoordinates (ferramenta #9 FASE 2) |