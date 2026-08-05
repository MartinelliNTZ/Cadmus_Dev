# 🎯 PLANO DE AÇÃO: Migração do VectorToSvgPlugin para Novo Sistema de Widgets

**Objetivo:** Migrar o `VectorToSvgPlugin` do `WidgetFactory` para o novo sistema `resources/widgets/`, eliminando dependência da Factory e de `resources/styles/`.

**Data:** 2026-07-31
**Versão:** 5.8.0
**Autor:** Cadmus Engineering

---

## 1. Contexto

O `VectorToSvgPlugin` é a ferramenta #18 da FASE 2 do plano de eliminação da WidgetFactory. Atualmente usa:

| Widget atual | Factory | Widget alvo (widgets) |
|-------------|---------|--------------------------|
| Layer input | `create_layer_input` | `GridComplexSelector` (layer + file) |
| Cor de fundo | `create_color_button` | `ComplexColorPicker` (NOVO) |
| Cor da borda | `create_color_button` | `ComplexColorPicker` (NOVO) |
| Cor do rótulo | `create_color_button` | `ComplexColorPicker` (NOVO) |
| Espessura da borda | `create_double_spin_input` | `GridDoubleSpin` |
| Tamanho do rótulo | `create_double_spin_input` | `GridDoubleSpin` |
| Opções | `create_checkbox_grid` | `GridCheckbox` (2 colunas) |
| Pasta de saída | `create_path_selector` (folder) | `GridComplexSelector` (output folder) |
| Botões | `create_bottom_action_buttons` | `GridExecutionButtons` |

---

## 2. Análise do Estado Atual

### 2.1 Widgets usados hoje (via Factory)

```python
layer_layout, self.layer_input = WidgetFactory.create_layer_input(
    STR.VECTOR_LAYER_LABEL,
    QgsMapLayerProxyModel.Filter.VectorLayer,
    allow_empty=False,
    enable_selected_checkbox=True,
)

fill_layout, self.fill_color_widget = WidgetFactory.create_color_button(
    title=STR.BACKGROUND_COLOR, initial_color=QColor("#ffffff"), ...
)
# border_color, label_color — mesmo padrão

border_width_layout, self.border_width_spin = WidgetFactory.create_double_spin_input(
    STR.BORDER_WIDTH, decimals=2, step=0.2, minimum=0.0, maximum=50.0, value=1.2, ...
)
# label_size — mesmo padrão (value=14.0, max=200.0, decimals=1)

options_layout, self.options_map = WidgetFactory.create_checkbox_grid(
    options, items_per_row=1, checked_by_default=False, ...
)

buttons_layout, self.action_buttons = WidgetFactory.create_bottom_action_buttons(...)

folder_layout, self.folder_selector = WidgetFactory.create_path_selector(
    title=STR.OUTPUT_FOLDER, mode="folder", path_button="svgs", ...
)
```

### 2.2 Padrões na API atual

- `self.layer_input.current_layer()` → `QgsMapLayer`
- `self.layer_input.only_selected_enabled()` → bool
- `self.fill_color_widget.get_color()` → `QColor`
- `self.options_map["chave"].isChecked()` → bool
- `self.folder_selector.get_paths()` → list[str]

### 2.3 Contrato base

- Herda de `BasePluginMTL` ✅
- `TOOL_KEY = ToolKey.VECTOR_TO_SVG` ✅
- Logger via base ✅
- Preferences via `Preferences.load_tool_prefs/save_tool_prefs` (via `self.preferences`) ✅

---

## 3. Estratégia de Migração

### 3.1 GridComplexSelector — Layer Input + Pasta de Saída (mesmo grid)

**Requisito do usuário:** no mesmo grid já vem o output tendo o input como parent, porém no modo folder com subfolder `"svgs"` sem fixed name ou suffix — porque é pasta de saída, não arquivo.

```python
self.grid_selectors = GridComplexSelector(
    config={
        "camada": {
            "label": STR.VECTOR_LAYER_LABEL,
            "description": "Camada vetorial do projeto ou arquivo externo",
            "allow_layer": True,
            "layer_filters": QgsMapLayerProxyModel.Filter.VectorLayer,
            "allow_features_check": True,
            "features_check_text": STR.ONLY_SELECTED_FEATURES,
            "allow_file": True,
            "allow_folder": False,
            "file_filter": StringManager.FILTER_VECTOR,
        },
        "pasta_saida": {
            "label": STR.OUTPUT_FOLDER,
            "description": "Pasta onde os SVGs serão salvos",
            "mode_type": "output",
            "parent": "camada",
            "subfolder": "svgs",
            "allow_file": False,
            "allow_folder": True,
            "show_copy_button": False,
        },
    },
    tool_key=self.TOOL_KEY,
    separator_bottom=False,
    parent=self,
)
self.layout.addWidget(self.grid_selectors)
```

**Comportamento do parent linking (folder mode):**
- O selector `"pasta_saida"` tem `parent="camada"` e `mode_type="output"`
- Ao selecionar a camada/arquivo no input, o output gera automaticamente `os.path.join(parent_dir, "svgs")`
- Botão 📥 (origin) usa o mesmo diretório do parent + subfolder
- Botão 🛠️ (suggest) usa pasta do projeto + subfolder `"svgs"`

### 3.2 ⚠️ Ajuste necessário no GridComplexSelector._generate_output (folder mode)

O `_generate_output` atual gera **nome de arquivo**:

```python
# ATUAL (gera arquivo):
output_name = f"{parent_stem}{suffix}{ext}"
output_path = os.path.join(parent_dir, output_name)
```

**Necessário:** quando o output selector for **folder mode** (`allow_folder=True`, `allow_file=False`), gerar **pasta**:

```python
# NOVO (folder mode):
if selector.selection_mode == "folder":
    subfolder = meta.get("subfolder", "")
    output_path = os.path.join(parent_dir, subfolder) if subfolder else parent_dir
else:
    # fluxo atual de arquivo (suffix/fixed_name/fixed_extension)
    ...
```

**Local da mudança:** `resources/widgets/grid/GridComplexSelector.py` → `_generate_output()`.

**Regra:** folder mode ignora `suffix`, `fixed_name` e `fixed_extension` — somente usa `subfolder`.

### 3.3 ComplexColorPicker — NOVO widget raiz

**Requisito do usuário:** `label | seletor de cor | simplelineedit | iconbutton copiar` — mesmo padrão de composição do `ComplexSelector`.

**Arquivo:** `resources/widgets/ComplexColorPicker.py`

**Composição (layout horizontal):**

```
[SimpleLabel] [QgsColorButton] [SimpleQLineEdit (hex readonly)] [SimpleModernButton (ícone COPY2)]
```

**Parâmetros do construtor:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `label_text` | str | `""` | Texto do label |
| `initial_color` | QColor | `QColor("#ffffff")` | Cor inicial |
| `tooltip` | str | `""` | Tooltip do seletor |
| `tool_key` | ToolKey | `None` | ToolKey para logs |
| `parent` | QWidget | `None` | Widget pai |

**API pública:**

| Método | Descrição |
|--------|-----------|
| `set_color(color: QColor)` | Define cor e atualiza hex |
| `get_color() → QColor` | Retorna cor atual |
| `color() → QColor` | Alias de get_color |

**Detalhes de implementação:**
- `QgsColorButton` de `qgis.gui` — permite opacidade (setAllowOpacity(True))
- `SimpleQLineEdit` readonly exibe HexRgb ou HexArgb (se alpha < 255)
- `SimpleModernButton` round_icon com ícone `IconManager.COPY2` — copia hex para clipboard via `ProjectUtils.set_clipboard_text()`
- `_apply_styles()` com `AppStyles.label() + AppStyles.input()` + `_specific_style()`
- Exceções logadas via `LogUtils` com `tool_key` recebido por parâmetro

### 3.4 GridDoubleSpin — Espessura da Borda + Tamanho do Rótulo

```python
self.border_width_spin = GridDoubleSpin(
    config={
        "border_width": {
            "label": STR.BORDER_WIDTH,
            "value": 1.2,
            "min": 0.0,
            "max": 50.0,
            "step": 0.2,
            "decimals": 2,
            "type": "double",
        },
    },
    parent=self,
)
self.layout.addWidget(self.border_width_spin)

self.label_size_spin = GridDoubleSpin(
    config={
        "label_size": {
            "label": STR.LABEL_SIZE,
            "value": 14.0,
            "min": 1.0,
            "max": 200.0,
            "step": 1.0,
            "decimals": 1,
            "type": "double",
        },
    },
    parent=self,
)
self.layout.addWidget(self.label_size_spin)
```

**API:** `get_value("border_width")`, `get_value("label_size")`, `get_all_values()`.

### 3.5 GridCheckbox — Opções (2 colunas)

```python
self.options_checkbox = GridCheckbox(
    config={
        "transparent_background": {"label": STR.TRANSPARENT_BACKGROUND},
        "show_border": {"label": STR.SHOW_BORDER},
        "show_label": {"label": STR.SHOW_LABEL},
        "for_each_feature": {"label": STR.GENERATE_SVG_FOR_EACH_FEATURE},
    },
    title="",
    items_per_row=2,  # grid 2 colunas
    parent=self,
)
self.layout.addWidget(self.options_checkbox)
```

**API:** `is_checked(key)`, `set_checked(key, value)`, `get_all_states()`.

### 3.6 GridExecutionButtons — Ações

```python
self.action_buttons = GridExecutionButtons(
    config={
        "run": {
            "label": STR.EXECUTE,
            "description": "Inicia a exportacao de SVG",
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

**⚠️ REGRA:** usar `self.layout.add_execution_buttons()` (fora do scroll), NUNCA `addWidget()`.

---

## 4. Layout Final do Plugin

```python
def _build_ui(self, **kwargs):
    super()._build_ui(
        title=STR.VECTOR_TO_SVG_TITLE,
        icon_path="cadmus_icon.ico",
        enable_scroll=True,
    )

    # ── GridComplexSelector (layer + file + pasta saída) ──
    self.grid_selectors = GridComplexSelector(...)  # seção 3.1
    self.layout.addWidget(self.grid_selectors)
    self.layout.addWidget(SeparatorWidget())

    # ── ComplexColorPicker (3 instâncias) ──
    self.fill_color_widget = ComplexColorPicker(
        label_text=STR.BACKGROUND_COLOR,
        initial_color=QColor("#ffffff"),
        tooltip=STR.SELECT_FILL_COLOR,
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    self.layout.addWidget(self.fill_color_widget)

    self.border_color_widget = ComplexColorPicker(
        label_text=STR.BORDER_COLOR,
        initial_color=QColor("#000000"),
        tooltip=STR.SELECT_BORDER_COLOR,
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    self.layout.addWidget(self.border_color_widget)

    self.label_color_widget = ComplexColorPicker(
        label_text=STR.LABEL_COLOR,
        initial_color=QColor("#000000"),
        tooltip=STR.SELECT_LABEL_COLOR,
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    self.layout.addWidget(self.label_color_widget)
    self.layout.addWidget(SeparatorWidget())

    # ── GridDoubleSpin (2 instâncias) ──
    self.border_width_spin = GridDoubleSpin(...)  # seção 3.4
    self.layout.addWidget(self.border_width_spin)
    self.label_size_spin = GridDoubleSpin(...)
    self.layout.addWidget(self.label_size_spin)
    self.layout.addWidget(SeparatorWidget())

    # ── GridCheckbox (2 colunas) ──
    self.options_checkbox = GridCheckbox(...)  # seção 3.5
    self.layout.addWidget(self.options_checkbox)

    # ── GridExecutionButtons (fora do scroll) ──
    self.action_buttons = GridExecutionButtons(...)  # seção 3.6
    self.layout.add_execution_buttons(self.action_buttons)
```

---

## 5. Adaptação de _load_prefs / _save_prefs

### 5.1 _load_prefs

```python
def _load_prefs(self):
    self.logger.debug("Carregando preferencias do VectorToSvg")

    self.fill_color_widget.set_color(QColor(self.preferences.get("fill_color", "#ffffff")))
    self.border_color_widget.set_color(QColor(self.preferences.get("border_color", "#000000")))
    self.label_color_widget.set_color(QColor(self.preferences.get("label_color", "#000000")))

    self.border_width_spin.set_value("border_width", float(self.preferences.get("border_width", 1.2)))
    self.label_size_spin.set_value("label_size", float(self.preferences.get("label_size", 14.0)))

    for key in ("transparent_background", "show_border", "show_label", "for_each_feature"):
        self.options_checkbox.set_checked(key, bool(self.preferences.get(key, False)))

    # GridComplexSelector: restaura paths + layer mode + features/lock state
    self.grid_selectors.set_preferences(
        self.preferences.get("grid_selectors", {})
    )
```

**Nota:** `set_preferences()` restaura `using_layer_combo`, `lock_state` e `checked_state` de cada selector automaticamente.

### 5.2 _save_prefs

```python
def _save_prefs(self):
    self.logger.debug("Salvando preferencias do VectorToSvg")

    self.preferences["fill_color"] = self.fill_color_widget.get_color().name(QColor.NameFormat.HexArgb)
    self.preferences["border_color"] = self.border_color_widget.get_color().name(QColor.NameFormat.HexArgb)
    self.preferences["label_color"] = self.label_color_widget.get_color().name(QColor.NameFormat.HexArgb)

    self.preferences["label_size"] = float(self.label_size_spin.get_value("label_size"))
    self.preferences["border_width"] = float(self.border_width_spin.get_value("border_width"))

    states = self.options_checkbox.get_all_states()
    self.preferences["transparent_background"] = bool(states.get("transparent_background", False))
    self.preferences["show_border"] = bool(states.get("show_border", False))
    self.preferences["show_label"] = bool(states.get("show_label", False))
    self.preferences["for_each_feature"] = bool(states.get("for_each_feature", False))

    # GridComplexSelector salva tudo (paths, layer mode, lock, features)
    self.preferences["grid_selectors"] = self.grid_selectors.get_preferences()

    self.preferences["window_width"] = self.width()
    self.preferences["window_height"] = self.height()

    Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
```

---

## 6. Adaptação de execute_tool

### 6.1 Helper _resolve_input_layer (padrão DividePointsByStripsPlugin)

```python
def _resolve_input_layer(self):
    """
    Resolve a camada de entrada a partir do seletor.

    Usa getitem() do ComplexSelector que retorna tupla (path, layer):
    - layer não-None → camada carregada no QGIS
    - layer None + path não-vazio → arquivo externo não carregado
    - layer None + path vazio → nada selecionado
    """
    return self.grid_selectors.get("camada").getitem()
```

### 6.2 execute_tool

```python
def execute_tool(self):
    self.logger.info("Iniciando exportacao de SVG a partir de camada vetorial")
    path, layer = self._resolve_input_layer()

    if isinstance(layer, QgsVectorLayer):
        pass  # camada carregada no QGIS — OK
    elif path:
        loaded = VectorLayerSource.open_vector_layer(path, tool_key=self.TOOL_KEY)
        if loaded and loaded.isValid():
            layer = loaded
            ProjectUtils.add_layer(layer)
        else:
            QgisMessageUtil.bar_warning(self.iface, STR.SELECT_VECTOR_LAYER)
            return
    else:
        QgisMessageUtil.bar_warning(self.iface, STR.SELECT_VECTOR_LAYER)
        return

    self.start_stats(layer)

    if not VectorLayerAttributes.ensure_has_features(layer, self.logger):
        QgisMessageUtil.bar_warning(self.iface, STR.LAYER_HAS_NO_FEATURES)
        return

    output_folder = self._resolve_output_folder()
    if not output_folder:
        return

    only_selected = self.grid_selectors.get_checked_state("camada")
    export_layer = self._resolve_export_layer(layer, only_selected)
    if not export_layer:
        return

    # ... restante mantido (features, style, export)
```

### 6.3 _resolve_output_folder

```python
def _resolve_output_folder(self):
    output_folder = self.grid_selectors.get_path("pasta_saida") or ""

    if not output_folder:
        QgisMessageUtil.bar_warning(self.iface, STR.OUTPUT_FOLDER)
        return None

    try:
        os.makedirs(output_folder, exist_ok=True)
        self.logger.debug(f"Pasta de saida garantida: {output_folder}")
        return output_folder
    except Exception as e:
        self.logger.error(f"Erro ao preparar pasta de saida '{output_folder}': {e}")
        QgisMessageUtil.modal_error(self.iface, f"{STR.ERROR}\n{e}")
        return None
```

### 6.4 _build_style

```python
def _build_style(self):
    return {
        "background_color": self.fill_color_widget.get_color().name(QColor.NameFormat.HexRgb),
        "border_color": self.border_color_widget.get_color().name(QColor.NameFormat.HexRgb),
        "label_color": self.label_color_widget.get_color().name(QColor.NameFormat.HexRgb),
        "label_size": float(self.label_size_spin.get_value("label_size")),
        "border_width": float(self.border_width_spin.get_value("border_width")),
        "transparent_background": bool(self.options_checkbox.is_checked("transparent_background")),
        "show_border": bool(self.options_checkbox.is_checked("show_border")),
        "show_label": bool(self.options_checkbox.is_checked("show_label")),
    }
```

### 6.5 Exportação por feição

```python
for_each_feature = self.options_checkbox.is_checked("for_each_feature")
```

---

## 7. Ordem de Implementação

| # | Ação | Arquivo |
|---|------|---------|
| 1 | Criar `ComplexColorPicker` (label + QgsColorButton + SimpleQLineEdit + SimpleModernButton copy) | `resources/widgets/ComplexColorPicker.py` |
| 2 | Ajustar `GridComplexSelector._generate_output()` para suportar **folder mode** com `subfolder` | `resources/widgets/grid/GridComplexSelector.py` |
| 3 | Substituir imports da Factory por widgets | `plugins/VectorToSvgPlugin.py` |
| 4 | Reescrever `_build_ui` | `plugins/VectorToSvgPlugin.py` |
| 5 | Adaptar `_load_prefs`/`_save_prefs` | `plugins/VectorToSvgPlugin.py` |
| 6 | Adaptar `execute_tool` e helpers | `plugins/VectorToSvgPlugin.py` |
| 7 | Remover imports não utilizados — flake8 F401 | `plugins/VectorToSvgPlugin.py` |
| 8 | Atualizar SKILL_WIDGETS2.md | `docs/skills/SKILL_WIDGETS2.md` |
| 9 | Atualizar docs/plano_eliminacao_widgetfactory.md | `docs/plano_eliminacao_widgetfactory.md` |
| 10 | Atualizar docs/ia/changelog.txt | `docs/ia/changelog.txt` |

---

## 8. Validação (Checklist)

```markdown
## Plugin: VectorToSvgPlugin

### Análise
- [x] Quais widgets usa via Factory? create_layer_input, create_color_button (x3), create_double_spin_input (x2), create_checkbox_grid, create_bottom_action_buttons, create_path_selector
- [x] Pode usar Grid? SIM — GridComplexSelector + GridDoubleSpin + GridCheckbox + GridExecutionButtons
- [x] Obedece contrato PLUGIN_CONTRACT.md? SIM
- [x] TEM LOGGER? SIM (herda de BasePluginMTL)

### Migração
- [ ] Criar ComplexColorPicker em resources/widgets/
- [ ] Ajustar GridComplexSelector para folder mode
- [ ] Substituir WidgetFactory.create_xxx() por widgets
- [ ] Remover imports da Factory
- [ ] Adicionar SeparatorWidget() entre widgets
- [ ] GridExecutionButtons via add_execution_buttons()
- [ ] _resolve_input_layer() via getitem() (camada carregada OU arquivo externo)
- [ ] _resolve_output_folder() via get_path("pasta_saida")
- [ ] only_selected via get_checked_state("camada")

### Pós-migração
- [ ] Plugin não importa de core/ui/WidgetFactory
- [ ] Plugin não importa de resources/styles/
- [ ] Plugin não chama setStyleSheet()
- [ ] flake8 limpo (sem imports não utilizados, linha vazia no final)
- [ ] Atualizar docs/ia/changelog.txt
```

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| `_generate_output` gerar arquivo em vez de pasta no folder mode | Alta | Alto | Testar folder mode antes de migrar o plugin |
| `set_preferences()` não restaurar modo layer combo corretamente | Média | Médio | Usar `get_preferences()`/`set_preferences()` do GridComplexSelector (já testado) |
| Perda do checkbox "Somente feições selecionadas" | Média | Médio | `allow_features_check=True` no config da camada |
| `only_selected_enabled()` → `get_checked_state("camada")` | Baixa | Baixo | API já existe no GridComplexSelector |
| Cores com opacidade (HexArgb) | Baixa | Baixo | `QgsColorButton.setAllowOpacity(True)` mantém suporte |
| `_resolve_input_layer()` para arquivo externo não carregado | Média | Médio | Padrão já validado no DividePointsByStripsPlugin (VectorLayerSource) |

---

## 10. Changelog Esperado

```
2.3.83 31/07/2026
[2.3.83.1][31/07/2026] Criado ComplexColorPicker (label + QgsColorButton + SimpleQLineEdit + SimpleModernButton copy) em resources/widgets/
[2.3.83.2][31/07/2026] GridComplexSelector._generate_output() agora suporta folder mode com subfolder (ignora suffix/fixed_name/fixed_extension)
[2.3.83.3][31/07/2026] VectorToSvgPlugin migrado para novo sistema de widgets:
   - GridComplexSelector (layer + file + pasta saída com subfolder "svgs" + parent linking)
   - 3× ComplexColorPicker (fundo, borda, rótulo)
   - 2× GridDoubleSpin (espessura borda, tamanho rótulo)
   - GridCheckbox 2 colunas (opções)
   - GridExecutionButtons via add_execution_buttons()
   - _resolve_input_layer() via getitem() (camada carregada OU arquivo externo)
   - Plugin 100% sem WidgetFactory
```

---

## 11. Resumo dos Widgets Novos Necessários

| Widget | Tipo | Arquivo | Status |
|--------|------|---------|--------|
| `ComplexColorPicker` | Raiz | `resources/widgets/ComplexColorPicker.py` | ⬜ Criar |
| `GridComplexSelector` folder mode | Grid | `resources/widgets/grid/GridComplexSelector.py` | ⬜ Ajustar `_generate_output()` |