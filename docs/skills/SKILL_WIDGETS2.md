# 🧩 SKILL: Novo Sistema de Widgets — Autoconfiguráveis

## 📋 RESUMO EXECUTIVO

**Sistema novo de widgets** que substitui `WidgetFactory` por widgets que se autoconfiguram com `AppStyles` + `ThemeManager` + `BaseTheme`.

**Contrato rígido:**
- Plugins NUNCA importam `qgis.PyQt.QtWidgets` direto
- Plugins NUNCA chamam `setStyleSheet()`
- Plugins NUNCA importam `AppStyles` ou `ThemeManager`
- Widgets se autoconfiguram totalmente no `__init__`
- Estilos globais via `AppStyles`, estilo específico via `_specific_style()`
- Separadores são `SeparatorWidget` entre widgets no layout (não margens)

**Princípio:** Widget = **autossuficiente**. Plugin = **consumidor que só passa parâmetros**.

---

## 🏗️ ARQUITETURA

```
Plugin
  └─ importa widget de resources/new_widgets/
      └─ widget.__init__(params, parent)
          ├─ Autoconfiguração total
          ├─ AppStyles (estilos globais)
          ├─ ThemeManager → BaseTheme (cores, fontes, dimensões)
          └─ _specific_style() (estilo próprio do widget)

resources/styles/AppStyles.py
  ├─ Lê de ThemeManager (com cache)
  ├─ Métodos GLOBAIS: button(), label(), input(), checkbox()
  ├─ Métodos MODERNOS: modern_button_primary(), modern_button_secondary(),
  │                    modern_button_round_icon(), modern_input_primary(),
  │                    modern_input_secondary()
  └─ NUNCA coloca px — tokens já vêm do tema com unidade

resources/styles/ThemeManager.py
  └─ Mantém instância ÚNICA de BaseTheme
      └─ Suporta múltiplos temas no futuro (registro em THEMES)

resources/styles/BaseTheme.py
  └─ Classe de tema com todos os tokens visuais descritivos

resources/new_widgets/
  ├── (raiz)      → widget SEM versão grid (MainLayout, ScrollWidget, etc)
  ├── simple/     → widget TEM versão grid (uso INTERNO)
  └── grid/       → versão grid do widget (plugins USAM esta)
```

---

## 📦 CATÁLOGO DE WIDGETS SIMPLE (uso interno)

Widgets em `resources/new_widgets/simple/` — NUNCA importados por plugins.

### SimpleLabel
`QLabel` com estilo global `AppStyles.label()`.
```python
# Uso em Simple/Grid widgets internos
label = SimpleLabel(text="<b>Título</b>", parent=self)
```

### SimpleButton
`QPushButton` com estilo global `AppStyles.button()`.
```python
# Uso em GridButton internamente
btn = SimpleButton(text="Fechar", parent=self)
```

### SimpleIconButton
`QPushButton` com ícone + `AppStyles.button()` + `_specific_style()` transparente.
```python
# Uso em GridIconButton internamente
btn = SimpleIconButton(
    icon_path="/path/to/icon.ico",
    tooltip="GitHub",
    icon_size=QSize(32, 32),
    button_size=QSize(40, 40),
    parent=self,
)
```

### SimpleModernButton 🆕
`QPushButton` **sem borda**, com **gradiente 3 stops** + **glow shadow** (`QGraphicsDropShadowEffect`).  
Ao pressionar, a sombra "recolhe" — feedback tátil visual.

**CORES E DIMENSÕES VEM DO TEMA via AppStyles. Nada hardcoded.**

```python
from .SimpleModernButton import SimpleModernButton

# Botão de texto (primary/secondary)
btn = SimpleModernButton(
    text="Executar",
    parent=self,
    primary=True,           # True → PRIMARY, False → NEUTRAL
    object_name="btn_run",  # para seletor CSS específico
)

# Botão de ícone redondo
btn = SimpleModernButton(
    icon=IconManager.icon(IconManager.COPY2),
    icon_size=QSize(14, 14),
    fixed_size=22,           # int = width e height iguais
    tooltip="Copiar",
    parent=self,
    round_icon=True,         # usa estilo modern_button_round_icon
)
```

**Parâmetros:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `text` | str | `""` | Texto do botão |
| `icon` | QIcon | `None` | Ícone do botão |
| `icon_size` | QSize | `None` | Tamanho do ícone (default: 16x16 para round_icon) |
| `fixed_size` | QSize / int | `None` | Tamanho fixo (int = quadrado) |
| `tooltip` | str | `""` | Tooltip do botão |
| `parent` | QWidget | `None` | Widget pai |
| `primary` | bool | `False` | `True` → PRIMARY, `False` → NEUTRAL |
| `round_icon` | bool | `False` | `True` → estilo `modern_button_round_icon` |
| `object_name` | str | `None` | Nome para seletor CSS (auto-gerado se None) |

**Tokens do tema usados:**
- `BUTTON_MIN_HEIGHT`, `BUTTON_ROUND_ICON_SIZE`, `BUTTON_PADDING`, `BUTTON_FONT_SIZE`, `BUTTON_FONT_WEIGHT`
- `BUTTON_SHADOW_BLUR_NORMAL/PRESSED`, `BUTTON_SHADOW_OFFSET_NORMAL/PRESSED`
- `COLOR_GLOW_PRIMARY/NEUTRAL`, `COLOR_GLOW_PRIMARY/NEUTRAL_ALPHA`

**Estilos AppStyles usados:**
- `modern_button_primary(object_name)` — gradiente PRIMARY
- `modern_button_secondary(object_name)` — gradiente NEUTRAL
- `modern_button_round_icon(object_name)` — gradiente NEUTRAL, sem padding

### SimpleCheckbox 🆕
`QCheckBox` com estilo global `AppStyles.checkbox()`.

```python
from .SimpleCheckbox import SimpleCheckbox

cb = SimpleCheckbox(text="Exportar PDF", parent=self)
```

**API pública:**
- `isChecked()` → bool
- `setChecked(bool)`
- `toggled` signal

### SimpleDoubleSpinBox 🆕
`QDoubleSpinBox` com estilo global `AppStyles.input()`. Suporta `type_spec="int"` para exibir inteiros.

```python
from .SimpleDoubleSpinBox import SimpleDoubleSpinBox

spin = SimpleDoubleSpinBox(
    value=3500,
    min_val=100,
    max_val=10000,
    step=100,
    decimals=0,
    type_spec="int",
    parent=self,
)
```

**Parâmetros:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `value` | float | `0` | Valor inicial |
| `min_val` | float | `0` | Valor mínimo |
| `max_val` | float | `999999` | Valor máximo |
| `step` | float | `1` | Incremento |
| `decimals` | int | `0` | Casas decimais |
| `type_spec` | str | `"double"` | `"int"` ou `"double"` |
| `parent` | QWidget | `None` | Widget pai |

### ComplexSelector 🆕
Seletor de arquivo/pasta/camada completo com:
- `QLineEdit` com glow (`SimpleQLineEdit` / `AppStyles.modern_input_primary()`)
- Botões: 📄 (project/layer), 📥 (origin), 🛠️ (suggest), 📂 (explorer), 📋 (copy)
- Suporte a `QgsMapLayerComboBox` via `layer_filters`
- Suporte a `mode_type="input"` / `"output"` com parent linking

```python
from .ComplexSelector import ComplexSelector

selector = ComplexSelector(
    label_text="Arquivo de entrada",
    default_path="",
    tooltip="Selecione o arquivo",
    file_filter="LAS/LAZ (*.las *.laz)",
    allow_file=True,
    allow_folder=False,
    multiple=False,
    selection_mode="file",
    mode_type="input",
    parent_selector=None,
    layer_filters=QgsMapLayerProxyModel.PointCloud,
    tool_key=self.TOOL_KEY,
    parent=self,
)
```

**API pública:**
- `path()` → str (primeiro path)
- `get_paths()` → list[str]
- `set_path(path)` / `set_paths(paths)`
- `on_path_change` — callback(paths)

### SimpleComboBox 🆕
`QComboBox` com `AppStyles.input()`. Uso INTERNO por `GridComboBox`. Plugins NUNCA importam.

```python
from .SimpleComboBox import SimpleComboBox

combo = SimpleComboBox(parent=self)
combo.set_options({".gpkg": "GeoPackage", ".shp": "Shapefile"})
combo.get_selected_key()  # → ".gpkg"
combo.set_selected_key(".shp")
```

**API interna:**
- `set_options(options_dict)` — popula o combo com {key: label}
- `get_selected_key()` → str
- `set_selected_key(key)`

### SquareIconButton 🆕
`QPushButton` quadrado com ícone, sem borda, fundo transparente. Usa `AppStyles.button()` + estilo específico para tamanho fixo.

```python
from .SquareIconButton import SquareIconButton

btn = SquareIconButton(
    icon=IconManager.icon(IconManager.COPY2),
    icon_size=QSize(16, 16),
    button_size=QSize(28, 28),
    tooltip="Copiar",
    parent=self,
)
```

### SimpleRadioButton 🆕
`QRadioButton` com estilo global `AppStyles.radio_button()`.

```python
from .SimpleRadioButton import SimpleRadioButton

radio = SimpleRadioButton(text="Opção 1", parent=self)
```

**API pública:**
- `isChecked()` → bool
- `setChecked(bool)`
- `toggled` signal
- `text()` → str

---

### SimpleQLineEdit 🆕
`QLineEdit` **sem borda**, com **gradiente 3 stops** + **glow shadow**, condizente com `SimpleModernButton`.

```python
from .SimpleQLineEdit import SimpleQLineEdit

# Input readonly primário
input_edit = SimpleQLineEdit(
    text="valor",
    placeholder="Digite...",
    read_only=True,
    primary=True,
    parent=self,
)
```

**Parâmetros:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `text` | str | `""` | Texto inicial |
| `placeholder` | str | `""` | Placeholder |
| `read_only` | bool | `False` | `True` ⇒ readonly |
| `primary` | bool | `True` | `True` → PRIMARY, `False` → NEUTRAL |
| `object_name` | str | `None` | Nome para seletor CSS (auto-gerado se None) |
| `parent` | QWidget | `None` | Widget pai |

**Comportamento visual:**
- Sombra expande ao ganhar foco (`focusInEvent`) e recolhe ao perder (`focusOutEvent`)
- `setMinimumHeight` + `setMaximumHeight` respeitam os tokens do tema

**Tokens do tema usados:**
- `INPUT_FIELD_MIN_HEIGHT: "32px"`, `INPUT_FIELD_MAX_HEIGHT: "36px"`
- `INPUT_FIELD_PADDING: "4px 10px"`, `INPUT_FIELD_FONT_SIZE: "11px"`, `INPUT_FIELD_FONT_WEIGHT: "500"`
- `INPUT_SHADOW_BLUR_NORMAL/FOCUSED`, `INPUT_SHADOW_OFFSET_NORMAL/FOCUSED`

**Estilos AppStyles usados:**
- `modern_input_primary(object_name)` — gradiente PANEL com destaque PRIMARY no foco
- `modern_input_secondary(object_name)` — gradiente NEUTRAL

### SimpleReadOnly
Campo readonly composto por `SimpleQLineEdit` + botão copiar (`SimpleModernButton`) opcional.

```python
from .SimpleReadOnly import SimpleReadOnly

# Com botão copiar (primary)
readonly = SimpleReadOnly(
    text="-10.12345678",
    show_copy_button=True,
    primary=True,       # estilo do input (True=PRIMARY, False=NEUTRAL)
    parent=self,
)

# Sem botão copiar (padrão)
readonly = SimpleReadOnly(text="valor", parent=self)
```

**API pública:**
- `setText(text)` — define o texto (aceita `None`)
- `text()` — retorna o texto
- `setPlaceholderText(text)` — define placeholder

---

## 📦 CATÁLOGO DE WIDGETS GRID (uso em plugins)

Widgets em `resources/new_widgets/grid/` — plugins USAM estes.

### GridLabel
Container de labels em layout vertical. Configuração via dict.

```python
info = GridLabel(config={
    "title": {"text": "<h2>Meu App</h2>"},
    "version": {"text": "Versão 1.0", "description": "Data de atualização"},
}, parent=self)
```

**API pública:**
- `set_text(key, text)` — atualiza texto
- `get_text(key)` → str
- `set_config(config)` — atualiza múltiplos labels

### GridReadOnly
Container com título + campos readonly (`SimpleReadOnly`). Cada campo pode ter botão copiar individual.

```python
wgs84 = GridReadOnly(
    title="WGS84 (EPSG:4326)",
    fields={
        "lat_dec": {"title": "Latitude", "value": ""},
        "lon_dec": {"title": "Longitude", "value": ""},
    },
    show_copy_buttons=True,   # botão copiar em cada campo (usa SimpleModernButton + COPY2)
    separator_bottom=True,
    parent=self,
)
layout.addWidget(wgs84)

# API pública
wgs84.set_value("lat_dec", "-10.12345678")
wgs84.get_value("lat_dec")  # → "-10.12345678"
```

**Parâmetros:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `title` | str | `""` | Título do bloco |
| `fields` | dict | `{}` | Dict de campos (chave → `{"title", "value"}`) |
| `show_copy_buttons` | bool | `False` | Botão copiar por campo |
| `separator_top` | bool | `False` | Separador antes |
| `separator_bottom` | bool | `False` | Separador depois |
| `parent` | QWidget | `None` | Widget pai |

### GridExecutionButtons
Container de botões de execução configurável via dict. Usa `SimpleModernButton` internamente.

```python
actions = GridExecutionButtons(
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
layout.add_execution_buttons(actions)  # via MainLayout
```

**Parâmetros adicionais:**
- `enable_config_button` + `config_callback` — botão Config ⚙️
- `separator_top/bottom` — separadores

### GridIconButton
Container de botões com ícone (`SimpleIconButton`). Configuração via dict.

```python
social = GridIconButton(config={
    "github": {
        "label": "GitHub",
        "icon": IconManager.GITHUB,
        "callback": lambda: webbrowser.open("https://github.com/user"),
    },
}, parent=self)
layout.addWidget(social)
```

### GridCheckbox 🆕
Container de checkboxes configurável via dict. Usa `SimpleCheckbox` internamente. Suporta `items_per_row` para layout em grid.

```python
checkbox_widget = GridCheckbox(
    config={
        "export_pdf": {
            "label": "Exportar PDF",
            "description": "Exporta layouts em PDF",
            "default": True,
        },
        "export_png": {
            "label": "Exportar PNG",
            "description": "Exporta layouts em PNG",
            "default": False,
        },
        "merge_pdf": {
            "label": "Concatenar PDFs",
            "description": "Combina todos os PDFs em um único arquivo",
            "default": False,
            "onchange": self.on_merge_pdf_changed,
        },
    },
    title="Opções de Exportação",
    items_per_row=2,
    parent=self,
)
layout.addWidget(checkbox_widget)
```

**API pública:**
- `is_checked(key)` → bool
- `set_checked(key, value)`
- `get_all_states()` → dict[str, bool]
- `widget(key)` → QCheckBox (acesso direto ao signal `toggled`)

**Parâmetros:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict de checkboxes (chave → `label`, `description`, `default`, `onchange`) |
| `title` | str | `""` | Título do grupo (QGroupBox) |
| `items_per_row` | int | `2` | Itens por linha no grid |
| `separator_top` | bool | `False` | Separador antes |
| `separator_bottom` | bool | `False` | Separador depois |
| `parent` | QWidget | `None` | Widget pai |

### GridInputFields 🆕
Container de campos de entrada de texto com labels, configurável via dict. Usa `SimpleQLineEdit` (glow/gradiente) internamente. **Não possui botão Inverter integrado** — o plugin declara o botão via `GridExecutionButtons` se necessário.

```python
input_fields = GridInputFields(
    config={
        "old_text": {
            "label": "Texto a buscar",
            "description": "Texto original a ser substituido",
            "default": "",
        },
        "new_text": {
            "label": "Substituir por",
            "description": "Novo texto",
            "default": "",
        },
    },
    title="Buscar e Substituir",
    separator_bottom=True,
    parent=self,
)
layout.addWidget(input_fields)

# API publica
input_fields.get_value("old_text")          # → ""
input_fields.set_value("old_text", "novo")  # define valor
input_fields.get_values()                   # → {"old_text": "novo", "new_text": ""}
input_fields.set_values({"old_text": "a", "new_text": "b"})
input_fields.widget("old_text")             # → SimpleQLineEdit (acesso direto)
```

**API pública:**
| Método | Descrição |
|--------|-----------|
| `get_value(key)` | Retorna valor de um campo |
| `set_value(key, value)` | Define valor de um campo |
| `get_values()` | Retorna dict `{key: value, ...}` |
| `set_values(values)` | Define múltiplos campos via dict |
| `widget(key)` | Acesso direto ao QLineEdit |

**Parâmetros:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict de campos (chave → `label`, `description`, `default`) |
| `title` | str | `""` | Título do grupo (QGroupBox) |
| `separator_top` | bool | `False` | Separador antes |
| `separator_bottom` | bool | `False` | Separador depois |
| `parent` | QWidget | `None` | Widget pai |

### GridComboBox 🆕
Container de N combos (QComboBox) configurável via dict. Usa `SimpleComboBox` internamente. Cada item tem `onchange` callback (sem pyqtSignal).

**UM GridComboBox contem N items.** NÃO crie 2 GridComboBox separados — use 1 widget com 2+ items.

```python
combo = GridComboBox(
    config={
        "vector_ext": {
            "label": "Extensão Vetor:",
            "description": "Formato para camadas vetoriais",
            "options": {
                ".gpkg": "GeoPackage (.gpkg)",
                ".shp": "Shapefile (.shp)",
            },
            "selected_key": ".gpkg",
            "onchange": self.on_ext_changed,  # callback(chave, texto)
        },
        "raster_ext": {
            "label": "Extensão Raster:",
            "options": {".tif": "TIFF (.tif)", ".png": "PNG (.png)"},
            "selected_key": ".tif",
        },
    },
    title="Extensões",    # opcional → QGroupBox
    parent=self,
)
layout.addWidget(combo)

combo.get_selected_key("vector_ext")  # → ".gpkg"
combo.set_selected_key("vector_ext", ".shp")
combo.widget("vector_ext")            # → SimpleComboBox
```

**API pública:**

| Método | Descrição |
|--------|-----------|
| `get_selected_key(key)` → `str` | Retorna chave selecionada |
| `set_selected_key(key, value)` | Define chave selecionada |
| `get_options(key)` → `dict` | Retorna options do combo |
| `set_options(key, options)` | Substitui options do combo |
| `widget(key)` → `SimpleComboBox` | Acesso direto ao QComboBox |

**Parâmetros de cada item no config dict:**

| Propriedade | Obrigatório | Descrição |
|-------------|-------------|-----------|
| `"label"` | Sim | Texto do label |
| `"description"` | Não | Tooltip |
| `"options"` | Sim | Dict `{key: label}` para popular o combo |
| `"selected_key"` | Não | Chave inicialmente selecionada |
| `"onchange"` | Não | `callback(chave_selecionada, texto_selecionado)` |

### GridRadioButton 🆕
Container de radio buttons configurável via dict, com `QButtonGroup` exclusivo. Usa `SimpleRadioButton` internamente. Suporta `columns` para layout em grid e `default_key` para seleção inicial.

```python
mode_selector = GridRadioButton(
    config={
        "remove": {
            "label": "Remover Extensão",
            "description": "Remove a extensão dos arquivos",
        },
        "restore": {
            "label": "Restaurar Extensão",
        },
        "zip": {
            "label": "Zipar",
        },
        "unzip": {
            "label": "Deszipar",
            "onchange": lambda key: print(f"Selecionado: {key}"),
        },
    },
    columns=2,
    default_key="remove",
    separator_bottom=True,
    parent=self,
)
layout.addWidget(mode_selector)

# API pública
mode_selector.get_selected_key()    # → "remove"
mode_selector.set_selected_key("zip")
mode_selector.get_selected_index()  # → 2
mode_selector.set_selected_index(2)
```

**API pública:**

| Método | Descrição |
|--------|-----------|
| `get_selected_key()` → `str` | Retorna chave do radio selecionado |
| `set_selected_key(key)` | Seleciona radio pela chave |
| `get_selected_index()` → `int` | Retorna índice (0-based) do selecionado |
| `set_selected_index(index)` | Seleciona radio pelo índice |

**Parâmetros:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict de radio buttons (chave → `label`, `description`, `onchange`) |
| `columns` | int | `1` | Número de colunas no grid |
| `default_key` | str | `None` | Chave do item selecionado por padrão |
| `separator_top` | bool | `False` | Separador antes |
| `separator_bottom` | bool | `False` | Separador depois |
| `parent` | QWidget | `None` | Widget pai |

---

### GridDoubleSpin 🆕
Container de campos numéricos configurável via dict. Usa `SimpleDoubleSpinBox` internamente. Suporta `type="int"` ou `type="double"`.

```python
spin = GridDoubleSpin(
    config={
        "max_width": {
            "label": "Largura Máx. PNG",
            "description": "Largura máxima em pixels",
            "value": 3500,
            "min": 100,
            "max": 10000,
            "step": 100,
            "decimals": 0,
            "type": "int",
        },
    },
    title="Configurações",
    parent=self,
)
layout.addWidget(spin)

# API pública
spin.get_value("max_width")        # → 3500
spin.set_value("max_width", 4000)  # define valor
spin.get_all_values()              # → {"max_width": 4000}
```

**Parâmetros:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict de campos (chave → `label`, `description`, `value`, `min`, `max`, `step`, `decimals`, `type`, `onchange`) |
| `title` | str | `""` | Título do grupo (QGroupBox) |
| `separator_top` | bool | `False` | Separador antes |
| `separator_bottom` | bool | `False` | Separador depois |
| `parent` | QWidget | `None` | Widget pai |

### GridComplexSelector 🆕
Grade de seletores de arquivo/pasta/camada configurados por dicionário. Usa `ComplexSelector` internamente. Suporta linking parent-child entre selectores e dynamic_parent.

```python
grid = GridComplexSelector(
    config={
        "entrada": {
            "label": "Arquivo de entrada",
            "description": "Selecione o arquivo de entrada",
            "file_filter": "LAS/LAZ (*.las *.laz)",
            "mode_type": "input",
            "allow_file": True,
            "allow_folder": False,
            "multiple": False,
        },
        "saida": {
            "label": "Pasta de saída",
            "description": "Pasta para salvar os arquivos",
            "mode_type": "output",
            "parent": "entrada",
            "suffix": "_converted",
            "fixed_extension": "gpkg",
            "subfolder": "output",
            "allow_folder": True,
        },
    },
    tool_key=self.TOOL_KEY,
    parent=self,
)
layout.addWidget(grid)

# API pública
grid.get_paths()                    # → ["/path/to/file.las", "/path/to/output/file_converted.gpkg"]
grid.get_path("entrada")            # → "/path/to/file.las"
grid.set_path("entrada", "/novo/path.las")
grid.get_preferences()              # → dict com paths + lock_state + checked_state
grid.set_preferences(prefs)         # → carrega paths + lock_state + checked_state
```

**Parâmetros do config dict (por seletor):**

| Propriedade | Obrigatório | Descrição |
|-------------|-------------|-----------|
| `"label"` | Sim | Texto do label |
| `"description"` | Não | Tooltip |
| `"path"` | Não | Path inicial |
| `"mode_type"` | Não | `"input"` ou `"output"` (default `"input"`) |
| `"parent"` | Não | Chave do seletor pai (para linking) |
| `"suffix"` | Não | Sufixo no nome do output |
| `"fixed_extension"` | Não | Extensão fixa do output |
| `"subfolder"` | Não | Subpasta para output |
| `"fixed_name"` | Não | Nome fixo do output |
| `"allow_file"` | Não | Permite selecionar arquivos |
| `"allow_folder"` | Não | Permite selecionar pastas |
| `"multiple"` | Não | Seleção múltipla |
| `"file_filter"` | Não | Filtro de arquivos |
| `"layer_filters"` | Não | QgsMapLayerProxyModel filter |
| `"show_explorer_button"` | Não | Botão explorar |
| `"show_copy_button"` | Não | Botão copiar |

**Parâmetros do construtor:**

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict de seletores |
| `tool_key` | ToolKey | `None` | ToolKey para logs |
| `title` | str | `None` | Título do grupo (QGroupBox) |
| `grid_id` | str | `""` | ID para cross-grid parent linking |
| `separator_top` | bool | `False` | Separador antes |
| `separator_bottom` | bool | `False` | Separador depois |
| `parent` | QWidget | `None` | Widget pai |

### GridButton (legado — prefira GridExecutionButtons)
Container simples com botões Fechar/Executar/Info.

---

## 🧩 WIDGETS RAIZ (sem versão grid)

### MainLayout
Layout principal dos diálogos. Substitui o antigo `BaseLayout`.

```python
# No BaseDialog (self.layout já é um MainLayout):
# NUNCA importar QVBoxLayout do QtWidgets — use os métodos do MainLayout
```

**Métodos:**
- `addWidget(widget)` — adiciona widget ao scroll (se habilitado) ou content
- `addLayout(layout)` — adiciona layout ao scroll (se habilitado) ou content
- `add_execution_buttons(buttons_widget)` — adiciona botões FIXOS fora do scroll (sempre abaixo do conteúdo). **ÚNICA maneira correta de adicionar GridExecutionButtons**
- `add_items(items)` — adiciona múltiplos widgets/layouts de uma vez
- `set_appbar_title(title)` — atualiza título da AppBar

**⚠️ REGRA ABSOLUTA (Contrato):**

1. **NUNCA importe `QVBoxLayout`, `QHBoxLayout` ou qualquer `QWidget` do QtWidgets nos diálogos.**  
   O diálogo herda de `BaseDialog` que já fornece `self.layout` como `MainLayout`.  
   Use `self.layout.addWidget()`, `self.layout.add_execution_buttons()`, etc.

2. **GridExecutionButtons DEVE ser adicionado via `self.layout.add_execution_buttons()`** —  
   este método coloca os botões FORA da área de scroll (fixos na parte inferior).  
   NUNCA adicione `GridExecutionButtons` com `addWidget()`.

3. **Plugins/Dialogs NUNCA criam layouts intermediários** (`QVBoxLayout()`, etc).  
   Adicione widgets diretamente ao `self.layout` do `MainLayout`.

```python
# ✅ CERTO — diálogo usa MainLayout:
class MeuDialogo(BaseDialog):
    def _build_inner_ui(self):
        self.layout.addWidget(self.grid_label)
        self.layout.addWidget(self.selector)
        self.layout.add_execution_buttons(self.buttons)  # GridExecutionButtons SEMPRE aqui

# ❌ ERRADO — importa QtWidgets e cria layout manual:
from qgis.PyQt.QtWidgets import QVBoxLayout  # QUEBRA CONTRATO

layout = QVBoxLayout()                    # QUEBRA CONTRATO
layout.addWidget(self.grid_label)
...
self.layout.add_items([layout])           # gambiarra desnecessária

# ❌ ERRADO — GridExecutionButtons com addWidget:
self.layout.addWidget(self.buttons)       # botões ficam no scroll!
```

### AppBarWidget
Barra superior com título, botões e drag. Instanciado pelo `MainLayout`.

### ScrollWidget
QScrollArea com estilo `AppStyles.scroll_area()`. Instanciado pelo `MainLayout`.

### SeparatorWidget
QFrame HLine com gradiente horizontal.

### TextBrowser 🆕
QTextBrowser com `AppStyles.text_browser()`, **sem versão grid**. Usado para exibir conteúdo Markdown/HTML com fallback Qt5/Qt6.

```python
from ..resources.new_widgets.TextBrowser import TextBrowser

browser = TextBrowser(parent=self)
browser.set_markdown(md_text)   # setMarkdown com fallback Qt < 5.14
# ou
browser.setHtml(html_text)
# ou
browser.setPlainText(text)
```

**Renderização Markdown:**
- Qt ≥ 5.14: usa `QTextDocument.setMarkdown()` nativo
- Qt < 5.14 (fallback): converte Markdown → HTML via `_markdown_to_html()` interno

**API pública:**
| Método | Descrição |
|--------|-----------|
| `set_markdown(text)` | Define Markdown com fallback automático |
| `set_html(html)` | Define HTML direto |
| `setPlainText(text)` | Define texto plano |
| `document()` | Acesso ao QTextDocument |

**Parâmetros do construtor:**
| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `open_external_links` | bool | `True` | Abrir links no navegador |
| `read_only` | bool | `True` | Read-only |
| `parent` | QWidget | `None` | Widget pai |

### CollapsibleParametersWidget 🆕
Seção colapsável com header clicável e gradiente via paintEvent. Suporta persistência de estado expandido/recolhido via `get_preferences()`/`set_preferences()`.

```python
from ..resources.new_widgets.CollapsibleParametersWidget import CollapsibleParametersWidget

coll = CollapsibleParametersWidget(
    title="Configurações Avançadas",
    expanded_by_default=False,
    parent=self,
)
coll.add_content_widget(my_widget)
self.layout.addWidget(coll)

# Salvar/carregar estado expandido
prefs = coll.get_preferences()
Preferences.save_tool_prefs(self.TOOL_KEY, {"collapsible": prefs})
coll.set_preferences(Preferences.load_tool_prefs(self.TOOL_KEY).get("collapsible", {}))
```

**API pública:**
| Método | Descrição |
|--------|-----------|
| `add_content_widget(widget)` | Adiciona widget ao conteúdo expandível |
| `add_content_layout(layout)` | Adiciona layout ao conteúdo expandível |
| `set_expanded(bool)` | Expande ou recolhe a seção |
| `is_expanded()` → `bool` | Retorna True se expandido |
| `get_preferences()` → `dict` | Retorna `{"expanded": bool}` para salvar em Preferences |
| `set_preferences(prefs)` | Carrega estado de um dict vindo de Preferences |

---

## 📌 CONTRATO RÍGIDO

### ✅ FAZER:

1. **Widget herda de `QWidget` (ou `QFrame`, `QLabel`, etc)**
2. **`self._apply_styles()`** no final do `__init__` — aplica estilos globais + específico
3. **Estilos globais** → `AppStyles.metodo()` (button, label, input, etc)
4. **Estilo específico** → `_specific_style()` retorna CSS extra
5. **Separadores** → `SeparatorWidget()` entre widgets no layout
6. **Unidades** sempre no tema (`BaseTheme`), nunca `px` no widget ou `AppStyles`
7. **Variável do tema** sempre `theme`, nunca `t`
8. **Widgets que precisam de gradiente + glow** → use `SimpleModernButton` (botões) e `SimpleQLineEdit` (inputs)
9. **⚠️ `if widget is not None` EM VEZ DE `if widget:`** — Em PyQt, `if widget:` verifica se o objeto C++ subjacente ainda existe via `sip.isdeleted()`. Se o C++ foi deletado (ex: garbage collection do container intermediário), `bool(widget)` retorna `False` mesmo com o objeto Python ainda existindo. Sempre use `if widget is not None` para verificar se o widget existe, e envolva chamadas em `try/except RuntimeError` para capturar caso o C++ tenha sido deletado.

### ❌ NUNCA FAZER:

```python
# ❌ NUNCA em plugins:
from qgis.PyQt.QtWidgets import QLabel, QPushButton

# ❌ NUNCA setStyleSheet em plugins:
widget.setStyleSheet("color: red")

# ❌ NUNCA importar AppStyles ou ThemeManager em plugins

# ❌ NUNCA unidades fixas em CSS:
min-height: 12px;  # certo: {theme.INPUT_FIELD_MIN_HEIGHT}

# ❌ NUNCA conectar sinais Qt em widgets diretamente:
widget.btn_close.clicked.connect(self.close)

# ❌ NUNCA usar QPushButton cru em Simple widgets quando precisar de gradiente:
# Use SimpleModernButton em vez disso.

# ❌ NUNCA usar QLineEdit cru em Simple widgets quando precisar de gradiente:
# Use SimpleQLineEdit em vez disso.
```

### 📋 ⚠️ REGRA ABSOLUTA: Configuração via Dict `config={}`

**TODO widget Grid usa APENAS dict `config={}`. NUNCA use listas, tuplas ou arrays.**

Cada **chave** do dict é o **identificador único** do componente (ex: `"github"`, `"subfolders"`, `"app_name"`).  
Cada **valor** é um dict com as propriedades específicas do componente.

```python
# ✅ CERTO — dict config com chaves identificadoras e callback por item
self.social = GridIconButton(config={
    "github": {
        "label": "GitHub",
        "icon": IconManager.GITHUB,
        "callback": lambda: webbrowser.open("https://github.com/user"),
        "description": "Visite o GitHub",
    },
}, parent=self)

# ❌ ERRADO — lista de tuplas (NUNCA use isso)
self.social = GridIconButton(items=[...], parent=self)
```

**Propriedades comuns do dict de cada componente:**

| Propriedade | Obrigatório | Descrição |
|-------------|-------------|-----------|
| `"text"` | Sim (labels) | Texto exibido no label |
| `"label"` | Sim (botões) | Tooltip/label do botão |
| `"icon"` | Sim (icon buttons) | Nome do arquivo de ícone (ex: `IconManager.GITHUB`) |
| `"callback"` | Sim (ações) | Função chamada ao clicar no botão |
| `"description"` | Não | Tooltip/descrição adicional |
| `"default"` | Não | Valor padrão (inputs, checkboxes) |
| `"icon_size"` | Não | QSize do ícone |
| `"button_size"` | Não | QSize do botão |

**`description`** sempre vira tooltip no widget, visível ao passar o mouse.

---

### 📞 Regra de Callbacks

Widgets **não expõem sinais Qt** para o plugin. Em vez disso, o plugin passa **funções callback** como parâmetros no construtor do widget. O widget conecta os sinais internamente.

```python
# ✅ CERTO — plugin passa callback:
actions = GridExecutionButtons(
    config={"run": {"label": "Executar", "callback": self.execute_tool}},
    parent=self,
)

# ❌ ERRADO — plugin conecta sinal no widget:
actions.btn_close.clicked.connect(self.close)
```

**Motivo:** O widget é responsável por seu próprio comportamento interno. O plugin só declara "o que fazer quando" via callbacks, sem conhecer a estrutura interna do widget.

---

### 🧬 CONTRATO DO WIDGET (Template)

```python
# resources/new_widgets/grid/GridExemplo.py
# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout
from ...styles.AppStyles import AppStyles


class GridExemplo(QWidget):
    """
    [Descrição do widget]

    Parâmetros
    ----------
    [param1] : type
        [descrição]
    parent : QWidget, optional
        Widget pai.

    Autoconfiguração
    ----------------
    - AppStyles: métodos globais
    - _specific_style(): estilo específico
    """

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self._params = kwargs

        try:
            self._configure()
            self._apply_styles()
        except Exception as error:
            pass

    def _configure(self):
        """Monta UI com parâmetros."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(AppStyles._get_theme().LAYOUT_VERTICAL_SPACING)

    def _apply_styles(self):
        """Aplica estilos globais + específico."""
        combined_style = (
            self._get_global_style()
            + self._specific_style()
        )
        self.setStyleSheet(combined_style)

    def _get_global_style(self) -> str:
        """Estilos globais via AppStyles."""
        return (
            AppStyles.label()
            + AppStyles.input()
            + AppStyles.button()
        )

    def _specific_style(self) -> str:
        """
        Estilo específico deste widget.
        Usa tokens do tema com nomes descritivos.
        SOBRESCREVER em subclasses se necessário.
        """
        return ""
```

---

## 🚫 Contrato de Unidades

**ERRADO:**
```python
# ❌ UNIDADE FIXA — NÃO FAZER
min-height: {theme.INPUT_FIELD_MIN_HEIGHT}px;
border: 1px solid {theme.COLOR_BORDER};
```

**CERTO:**
```python
# ✅ UNIDADE SEMPRE NO TEMA
# No tema:  INPUT_FIELD_MIN_HEIGHT = "32px"
# No estilo: min-height: {theme.INPUT_FIELD_MIN_HEIGHT};

# No tema:  PXBORDER_ONE = "1px solid"
# No estilo: border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
```

---

## 🆚 AppStyles vs Antigo Styles.py

| Aspecto | AppStyles (NOVO) | Styles.py (ANTIGO) |
|---------|-----------------|-------------------|
| Fonte do tema | `ThemeManager` | `BaseStyles.current_theme = CoffeTheme()` |
| Unidades | Tokens já têm unidade: `"32px"` | Tokens sem unidade: `12` |
| Nomes tokens | `INPUT_FIELD_MIN_HEIGHT` | `INPUT_HEIGHT` |
| Cache | Sim (`_theme` classvar) | Não |
| `_specific_style()` | Cada widget pode ter | Não tem |
| Separadores | Widget separado (`SeparatorWidget`) | Parâmetro `separator_top/bottom` |
| Botões com glow | `SimpleModernButton` + `modern_button_*()` | Não tinha |
| Inputs com glow | `SimpleQLineEdit` + `modern_input_*()` | Não tinha |
| `add_execution_buttons` | Fora do scroll (fixo embaixo) | Dentro do scroll |
| `show_copy_buttons` | Botão copiar com `COPY2` + `SimpleModernButton` | Emoji 📋 |

---

## ✅ Checklist: Criar Novo Widget no Novo Sistema

- [ ] 1. Widget herda de `QWidget` (ou `QFrame`, `QLabel`, etc)
- [ ] 2. `__init__` recebe `parent=None` + parâmetros específicos
- [ ] 3. `_configure()` monta UI com Simple widgets
- [ ] 4. `_apply_styles()` no final do `__init__`
- [ ] 5. `_get_global_style()` retorna `AppStyles` combinados
- [ ] 6. `_specific_style()` retorna CSS específico (ou `""`)
- [ ] 7. Unidades sempre no tema, nunca `px` no CSS
- [ ] 8. Se tem versão grid → `simple/` + `grid/`
- [ ] 9. Se não tem versão grid → raiz de `new_widgets/`
- [ ] 10. Plugin usa versão grid (nunca simple)
- [ ] 11. Botão com gradiente/glow → `SimpleModernButton`
- [ ] 12. Input com gradiente/glow → `SimpleQLineEdit`
- [ ] 13. `add_execution_buttons` SEM stretch se scroll estiver habilitado

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-21 | 1.0.0 | Criação inicial — Novo sistema de widgets autoconfiguráveis |
| 2026-07-21 | 1.1.0 | Adicionada regra de callbacks (widget não expõe sinais Qt, plugin passa funções callback como parâmetros) |
| 2026-07-21 | 1.2.0 | Adicionado padrão de configuração via dict `config={}` com chaves identificadoras e suporte a `description` para tooltip |
| 2026-07-23 | 2.0.0 | Adicionados `SimpleModernButton` (gradiente + glow), `SimpleQLineEdit` (gradiente + glow), `SimpleReadOnly` atualizado com `SimpleModernButton` + `SimpleQLineEdit` + ícone COPY2. Adicionados tokens `INPUT_FIELD_PADDING`, `INPUT_FIELD_FONT_SIZE`, `INPUT_FIELD_FONT_WEIGHT`, `INPUT_SHADOW_*`. Adicionados métodos `modern_input_primary()`, `modern_input_secondary()`. Documentado comportamento de `add_execution_buttons` sem stretch com scroll. |
| 2026-07-24 | 2.1.0 | Adicionado `TextBrowser` (raiz, sem versão grid) — QTextBrowser com `AppStyles.text_browser()`, set_markdown com fallback Qt5/Qt6. |
| 2026-07-24 | 2.2.0 | Adicionados Simple widgets faltantes: `SimpleCheckbox`, `SimpleDoubleSpinBox`, `ComplexSelector`, `SquareIconButton`. Adicionados Grid widgets: `GridCheckbox`, `GridDoubleSpin`, `GridComplexSelector`. Atualizado ExportAllLayouts status — plugin 100% migrado para novo sistema (usa GridCheckbox + GridDoubleSpin + GridComplexSelector + GridExecutionButtons, sem WidgetFactory). |
| 2026-07-27 | 2.3.0 | Adicionado `GridInputFields` ao catálogo Grid — container de campos de texto com labels + SimpleQLineEdit (glow/gradiente). API: get_value/set_value/get_values/set_values/widget. ReplaceInLayouts migrado usando GridInputFields + GridCheckbox + GridLabel + GridExecutionButtons. |
| 2026-07-27 | 2.4.0 | Adicionados `SimpleComboBox` (QComboBox + AppStyles.input()) e `GridComboBox` (container de N combos com onchange callback, sem pyqtSignal). API: get_selected_key/set_selected_key/get_options/set_options/widget. SaveTemporaryLayersPlugin migrado usando GridInputFields + GridComboBox + GridComplexSelector + GridExecutionButtons. |
| 2026-07-28 | 2.5.0 | Adicionado `CollapsibleParametersWidget` ao catálogo de widgets raiz com `get_preferences()`/`set_preferences()` para persistir estado expandido. `GridComplexSelector.get_preferences()`/`set_preferences()` agora inclui `lock_state` e `checked_state` de cada selector. GenerateTrailPlugin refatorado para usar `get_preferences()`/`set_preferences()` unificados. |
| 2026-07-30 | 2.6.0 | Adicionados `SimpleRadioButton` (QRadioButton + AppStyles.radio_button()) e `GridRadioButton` (container de radio buttons com QButtonGroup + dict config + columns + default_key). API: get_selected_key/set_selected_key/get_selected_index/set_selected_index. |
| 2026-07-31 | 2.7.0 | **⚠️ Lição crítica:** Adicionada regra `if widget is not None` em vez de `if widget:` no contrato. Em PyQt, `if widget:` verifica `sip.isdeleted()` e pode retornar `False` mesmo com o objeto Python existindo. Sempre usar `if widget is not None` + `try/except RuntimeError` para segurança. GridComboBox corrigido com esta regra. PathExtensionPlugin migrado com `GridComplexSelector` + `GridComboBox` + `GridRadioButton` + `GridExecutionButtons`. População inicial do combo via `_on_layer_changed` após `set_on_changed()`. |
