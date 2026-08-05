# 🎯 PLANO DE AÇÃO: Migração do LoadFolderLayers

**Objetivo:** Migrar o plugin `LoadFolderLayers` do sistema antigo (`WidgetFactory`) para o novo sistema (`widgets`), eliminando dependências de `core/ui/WidgetFactory.py` e `resources/widgets/`.

**Data:** 2026-07-27
**Versão:** 2.0.0
**Plugin:** `plugins/LoadFolderLayers.py`

---

## 1. ANÁLISE — O que o plugin usa HOJE

| Widget Factory (ANTIGO) | O que faz | Novo widget (NOVO) |
|-------------------------|-----------|-------------------|
| `create_collapsible_parameters(title, expanded_by_default)` | Seção colapsável "Tipos de Arquivo" | **CRIAR** `CollapsibleParametersWidget` (com paintEvent gradiente) |
| `create_checkbox_grid(options_dict, items_per_row, ...)` | Grid de checkboxes de tipos de arquivo (2 colunas) + opções (1 coluna) | **MELHORAR** `GridCheckbox` — add `dependents` + `control_buttons` |
| `create_path_selector(mode="folder")` | Seletor de pasta raiz | `GridComplexSelector` com `allow_folder=True, allow_file=False` ✅ |
| `create_bottom_action_buttons(run_callback, close_callback, info_callback)` | Botões Carregar + Fechar + Info | `GridExecutionButtons` ✅ |

### 1.1 Funcionalidades especiais do LoadFolderLayers

1. **Dependência entre checkboxes:** `preserve` → habilita/desabilita `lastfolder`
   - `lastfolder` só faz sentido se `preserve` estiver ativado
   - O **próprio widget** gerencia a dependência, plugin só informa quem depende de quem
2. **Collapsible com conteúdo interno:** Tipos de arquivo ficam dentro de seção colapsável
3. **Prefs:** Salva estado expandido do collapsible (`types_expanded`)
4. **Backup:** Checkbox de backup desabilitado se projeto não salvo
5. **Botões de controle:** Antigo `show_control_buttons=True` exibia Selecionar Todos / Desmarcar Todos / Inverter

---

## 2. O QUE PRECISA SER CRIADO / MELHORADO

### 2.1 `CollapsibleParametersWidget` (NOVO — raiz de widgets/)

**Arquivo:** `resources/widgets/CollapsibleParametersWidget.py`

Widget expansível igual ao antigo, mas seguindo o contrato DO NOVO SISTEMA:

```python
class CollapsibleParametersWidget(QWidget):
    """
    Seção colapsável com header clicável e gradiente via paintEvent.
    
    - paintEvent: gradiente horizontal no header usando tokens do tema
    - Header: clique alterna expandido/recolhido com ícone ▶/▼
    - Conteúdo: mostra/esconde com animação suave
    - Estilos: AppStyles + tokens do BaseTheme (sem px, sem cores fixas)
    """
```

**Requisitos:**
- `paintEvent` com gradiente — usar `QPainter`, `QLinearGradient`, tokens do tema como `COLOR_SURFACE_1`, `COLOR_SURFACE_2`, `COLOR_BORDER_DEFAULT`
- Estilo via `AppStyles` + `_specific_style()` — seguir padrão dos outros widgets
- Tokens do tema para: gradiente do header, cor do texto, altura, padding, ícone
- API: `add_content_widget(widget)`, `add_content_layout(layout)`, `set_expanded(bool)`, `is_expanded()`
- Compatibilidade Qt5/Qt6

**API necessária:**
```python
class CollapsibleParametersWidget(QWidget):
    def __init__(self, title="", expanded_by_default=False, parent=None):
        ...
    
    def add_content_widget(self, widget):
        """Adiciona widget ao conteúdo expandível."""
    
    def add_content_layout(self, layout):
        """Adiciona layout ao conteúdo expandível."""
    
    def set_expanded(self, expanded: bool):
        """Expande ou recolhe a seção."""
    
    def is_expanded(self) -> bool:
        """Retorna True se expandido."""
```

### 2.2 `GridCheckboxButtons` (NOVO — grid/)

**Arquivo:** `resources/widgets/grid/GridCheckboxButtons.py`

Widget de botões genérico, similar ao `GridExecutionButtons` mas **sem botões built-in** (sem Fechar, Info, Config). TODOS os botões são configurados via `config` dict. Usa `SimpleModernButton` internamente (gradiente + glow).

```python
class GridCheckboxButtons(QWidget):
    """
    Container de botões configuráveis via dict.
    
    Similar ao GridExecutionButtons mas SEM botões pré-prontos.
    TODOS os botões vêm do config dict.
    
    Uso:
        buttons = GridCheckboxButtons(config={
            "select_all": {
                "label": "Selecionar Todos",
                "callback": self._select_all,
                "is_run_button": False,
            },
            "deselect_all": {
                "label": "Desmarcar Todos",
                "callback": self._deselect_all,
            },
            "invert": {
                "label": "Inverter",
                "callback": self._invert_selection,
            },
        }, parent=self)
    """
```

**Parâmetros:**
| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `config` | dict | `{}` | Dict de botões (chave → `label`, `callback`, `description`, `is_run_button`) |
| `separator_top` | bool | `False` | Separador antes |
| `separator_bottom` | bool | `False` | Separador depois |
| `parent` | QWidget | `None` | Widget pai |

### 2.3 `GridCheckbox` — Melhorias (ADAPTAR)

**Arquivo:** `resources/widgets/grid/GridCheckbox.py`

#### 2.3.1 Sistema de dependentes (`dependents`)

Adicionar suporte a dependência entre checkboxes. O **próprio widget gerencia**, o plugin só declara.

```python
# NOVO no config dict de cada item:
config={
    "preserve": {
        "label": "Preservar estrutura",
        "default": True,
        "dependents": ["lastfolder"],  # ← NOVO: quando preserve mudar, lastfolder reage
    },
    "lastfolder": {
        "label": "Não agrupar última pasta",
        "default": False,
    },
}
```

**Regras de dependência:**
- Quando o checkbox **pai** (`preserve`) for **desmarcado**:
  - Todos os dependentes (`lastfolder`) são **desmarcados**
  - Todos os dependentes são **desabilitados** (`setEnabled(False)`)
- Quando o checkbox **pai** for **marcado**:
  - Todos os dependentes são **habilitados** (`setEnabled(True)`)
  - O estado anterior do dependente é restaurado (se salvo)

**Como o plugin declara:**
```python
# Opção 1: Direto no config dict (recomendado)
self.chk_options = GridCheckbox(config={
    "preserve": {
        "label": STR.PRESERVE_FOLDER_STRUCTURE,
        "default": True,
        "dependents": ["lastfolder"],  # ← O widget gerencia sozinho
    },
    "lastfolder": {
        "label": STR.DO_NOT_GROUP_LAST_FOLDER,
        "default": False,
    },
    ...
})
```

**Implementação interna:**
```python
class GridCheckbox(QWidget):
    def __init__(self, config=None, ..., parent=None):
        ...
        self._dependents_map: dict[str, list[str]] = {}  # pai → [filhos]
        self._dep_states: dict[str, bool] = {}  # filho → estado salvo
        ...

    def _build_ui(self):
        ...
        for key, item_config in items:
            dependents = item_config.get("dependents", [])
            if dependents:
                self._dependents_map[key] = dependents
                for dep_key in dependents:
                    self._dep_states[dep_key] = item_config.get("default", False)
            
            cb = SimpleCheckbox(...)
            cb.toggled.connect(lambda checked, k=key: self._on_toggled(k, checked))
            ...

    def _on_toggled(self, key: str, checked: bool):
        """Gerencia dependentes quando um checkbox muda."""
        dependents = self._dependents_map.get(key, [])
        for dep_key in dependents:
            dep_cb = self._checkboxes.get(dep_key)
            if not dep_cb:
                continue
            if not checked:
                # Pai desmarcado → desabilita e desmarca dependente
                self._dep_states[dep_key] = dep_cb.isChecked()
                dep_cb.setChecked(False)
                dep_cb.setEnabled(False)
            else:
                # Pai marcado → reabilita dependente com estado anterior
                dep_cb.setEnabled(True)
                dep_cb.setChecked(self._dep_states.get(dep_key, False))
```

#### 2.3.2 Botões de controle opcionais (`control_buttons_config`)

Adicionar parâmetro `control_buttons_config` ao `GridCheckbox`. Quando fornecido, cria um `GridCheckboxButtons` abaixo dos checkboxes.

```python
# NOVO parâmetro no construtor do GridCheckbox:
self.chk_types = GridCheckbox(
    config=file_config,
    items_per_row=2,
    title=None,
    control_buttons_config={  # ← NOVO: ativa botões de controle
        "select_all": {
            "label": "Selecionar Todos",
            "callback": self._select_all_types,
            "is_run_button": False,
        },
        "deselect_all": {
            "label": "Desmarcar Todos",
            "callback": self._deselect_all_types,
        },
        "invert": {
            "label": "Inverter",
            "callback": self._invert_types,
        },
    },
    parent=self,
)
```

**Comportamento:**
- Se `control_buttons_config` for `None` ou `{}` → sem botões (default)
- Se fornecido → cria `GridCheckboxButtons` com os botões configurados
- Os callbacks recebem o próprio `GridCheckbox` para manipular estados
- O widget fornece métodos auxiliares: `select_all()`, `deselect_all()`, `invert_selection()`

**Métodos auxiliares no GridCheckbox:**
```python
def select_all(self):
    """Marca todos os checkboxes."""
    for cb in self._checkboxes.values():
        cb.setChecked(True)

def deselect_all(self):
    """Desmarca todos os checkboxes."""
    for cb in self._checkboxes.values():
        cb.setChecked(False)

def invert_selection(self):
    """Inverte estado de todos os checkboxes."""
    for cb in self._checkboxes.values():
        cb.setChecked(not cb.isChecked())
```

---

## 3. MAPEAMENTO COMPLETO

### 3.1 Widgets antigos → novos

| Código antigo | Código novo |
|---------------|-------------|
| `coll_layout, self.coll_widget = WidgetFactory.create_collapsible_parameters(...)` | `self.coll_widget = CollapsibleParametersWidget(title=STR.FILE_TYPES, expanded_by_default=False, parent=self)` |
| `types_layout, self.chk_types = WidgetFactory.create_checkbox_grid(file_options, items_per_row=2, show_control_buttons=True, ...)` | `self.chk_types = GridCheckbox(config=file_config, items_per_row=2, control_buttons_config=btn_config, title=None, parent=self)` |
| `self.coll_widget.add_content_layout(types_layout)` | `self.coll_widget.add_content_widget(self.chk_types)` |
| `folder_layout, self.folder_selector = WidgetFactory.create_path_selector(mode="folder", ...)` | `self.folder_selector = GridComplexSelector(config={"folder": {"label": STR.ROOT_FOLDER, "allow_folder": True, "allow_file": False, "mode_type": "input"}}, parent=self)` |
| `opts_layout, opts_map = WidgetFactory.create_checkbox_grid(opts, items_per_row=1, ...)` | `self.chk_options = GridCheckbox(config=opts_config, items_per_row=1, title=None, parent=self)` |
| `self.chk_preserve_structure.set_dependents([self.chk_last_folder])` | `self.chk_options = GridCheckbox(config={..., "preserve": {"dependents": ["lastfolder"], ...}, ...})` |
| `buttons_layout, self.action_buttons = WidgetFactory.create_bottom_action_buttons(...)` | `self.action_buttons = GridExecutionButtons(config={"run": {"label": STR.LOAD_FILES, "callback": self.execute_tool, "is_run_button": True}}, enable_close_button=True, enable_info=True, tool_key=self.TOOL_KEY, parent=self)` |

### 3.2 Acesso a widgets (API)

| Código antigo | Código novo |
|---------------|-------------|
| `self.folder_selector.get_paths()` | `self.folder_selector.get_paths()` (mesma API) |
| `self.folder_selector.set_paths([folder])` | `self.folder_selector.set_path("folder", folder)` |
| `self.chk_types.items()` | `self.chk_types.get_all_states()` |
| `chk.isChecked()` | `self.chk_types.is_checked(key)` |
| `self.chk_preserve_structure` | `self.chk_options.is_checked("preserve")` |
| `self.chk_last_folder` | `self.chk_options.is_checked("lastfolder")` |
| `self.chk_load_missing_only` | `self.chk_options.is_checked("missing_only")` |
| `self.chk_backup` | `self.chk_options.is_checked("backup")` |
| `self.coll_widget.is_expanded()` | `self.coll_widget.is_expanded()` (mesma API) |
| `self.coll_widget.set_expanded(...)` | `self.coll_widget.set_expanded(...)` (mesma API) |

---

## 4. ESTRUTURA DO NOVO `_build_ui` (LoadFolderLayers)

```python
def _build_ui(self, **kwargs):
    super()._build_ui(
        title=STR.LOAD_FOLDER_LAYERS_TITLE,
        icon_path="load_folder.ico",
        enable_scroll=False,
    )

    # ── 1. Seletor de pasta (GridComplexSelector) ─────────────
    self.folder_selector = GridComplexSelector(
        config={
            "folder": {
                "label": STR.ROOT_FOLDER,
                "description": "Selecione a pasta raiz para buscar arquivos",
                "allow_folder": True,
                "allow_file": False,
                "mode_type": "input",
                "show_copy_button": False,
                "show_explorer_button": True,
            },
        },
        tool_key=self.TOOL_KEY,
        separator_bottom=True,
        parent=self,
    )
    self.layout.addWidget(self.folder_selector)

    # ── 2. Tipos de arquivo (Collapsible + GridCheckbox com botões) ──
    self.coll_widget = CollapsibleParametersWidget(
        title=STR.FILE_TYPES,
        expanded_by_default=False,
        parent=self,
    )

    file_config = {}
    for label in self.FILE_TYPES.keys():
        file_config[label] = {"label": label, "default": False}

    self.chk_types = GridCheckbox(
        config=file_config,
        items_per_row=2,
        title=None,
        control_buttons_config={  # Botões: Selecionar / Desmarcar / Inverter
            "select_all": {
                "label": "Selecionar Todos",
                "callback": lambda: self.chk_types.select_all(),
            },
            "deselect_all": {
                "label": "Desmarcar Todos",
                "callback": lambda: self.chk_types.deselect_all(),
            },
            "invert": {
                "label": "Inverter",
                "callback": lambda: self.chk_types.invert_selection(),
            },
        },
        parent=self,
    )
    self.coll_widget.add_content_widget(self.chk_types)
    self.layout.addWidget(self.coll_widget)

    # ── 3. Opções (GridCheckbox com dependência preserve→lastfolder) ──
    self.chk_options = GridCheckbox(
        config={
            "missing_only": {
                "label": STR.LOAD_ONLY_MISSING_FILES,
                "default": False,
            },
            "preserve": {
                "label": STR.PRESERVE_FOLDER_STRUCTURE,
                "default": True,
                "dependents": ["lastfolder"],  # ← O WIDGET GERENCIA SOZINHO
            },
            "lastfolder": {
                "label": STR.DO_NOT_GROUP_LAST_FOLDER,
                "default": False,
            },
            "backup": {
                "label": STR.CREATE_PROJECT_BACKUP_IF_SAVED,
                "default": True,
            },
        },
        items_per_row=1,
        title=None,
        separator_bottom=True,
        parent=self,
    )
    self.layout.addWidget(self.chk_options)

    # Desabilitar backup se projeto não salvo
    if not QgsProject.instance().fileName():
        self.chk_options.set_checked("backup", False)
        self.chk_options.widget("backup").setEnabled(False)

    # ── 4. Botões de ação (GridExecutionButtons) ─────────────
    self.action_buttons = GridExecutionButtons(
        config={
            "run": {
                "label": STR.LOAD_FILES,
                "description": "Carrega todos os arquivos da pasta selecionada",
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

    self._load_prefs()
```

---

## 5. MUDANÇAS NO `_load_prefs` E `_save_prefs`

### `_load_prefs`
```python
def _load_prefs(self):
    try:
        # Pasta
        folder = self.preferences.get("folder", "")
        if folder:
            self.folder_selector.set_path("folder", folder)

        # Tipos de arquivo
        saved_types = self.preferences.get("types", [])
        for label in self.FILE_TYPES.keys():
            self.chk_types.set_checked(label, label in saved_types)
        self.coll_widget.set_expanded(self.preferences.get("types_expanded", False))

        # Opções (dependência preserve→lastfolder é gerenciada pelo widget)
        self.chk_options.set_checked("missing_only", self.preferences.get("missing_only", False))
        self.chk_options.set_checked("preserve", self.preferences.get("preserve", True))
        self.chk_options.set_checked("lastfolder", self.preferences.get("lastfolder", False))
        self.chk_options.set_checked("backup", self.preferences.get("backup", True))
    except Exception as e:
        self.logger.error(f"Erro ao carregar prefs: {e}")
```

### `_save_prefs`
```python
def _save_prefs(self):
    try:
        states = self.chk_types.get_all_states()
        selected_types = [label for label, checked in states.items() if checked]
        folder = self.folder_selector.get_path("folder") or ""

        self.preferences["folder"] = folder
        self.preferences["types"] = selected_types
        self.preferences["missing_only"] = self.chk_options.is_checked("missing_only")
        self.preferences["preserve"] = self.chk_options.is_checked("preserve")
        self.preferences["lastfolder"] = self.chk_options.is_checked("lastfolder")
        self.preferences["backup"] = self.chk_options.is_checked("backup")
        self.preferences["window_width"] = self.width()
        self.preferences["window_height"] = self.height()
        self.preferences["types_expanded"] = self.coll_widget.is_expanded()

        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
    except Exception as e:
        self.logger.error(f"Erro ao salvar prefs: {e}")
```

---

## 6. MUDANÇAS NO `execute_tool`

```python
def execute_tool(self):
    folder = self.folder_selector.get_path("folder") or ""
    self.start_stats(folder)
    self.logger.info(f"Iniciando execução: pasta={folder}", code="EXEC_START")

    if not folder or not os.path.isdir(folder):
        QgisMessageUtil.bar_warning(self.iface, STR.SELECT_VALID_FOLDER)
        return

    # Backup
    backup_file = None
    if self.chk_options.is_checked("backup"):
        try:
            backup_file = ProjectUtils.create_project_backup(QgsProject.instance())
        except Exception as e:
            self.logger.error(f"Erro criando backup: {e}", code="BACKUP_ERROR")

    # Extensões
    extensions = []
    for label in self.FILE_TYPES.keys():
        if self.chk_types.is_checked(label):
            extensions.extend(self.FILE_TYPES.get(label, []))

    if not extensions:
        QgisMessageUtil.bar_warning(self.iface, STR.SELECT_AT_LEAST_ONE_FILE_TYPE)
        return

    # Scan
    records = ExplorerUtils.scan_folder(folder, extensions, self.TOOL_KEY)
    self.logger.info(f"scan_folder retornou {len(records)} registros", code="SCAN_COMPLETE")

    # Decidir sync/async
    total_files = len(records)
    if total_files > self.ASYNC_THRESHOLD:
        return self._run_async_pipeline(
            folder=folder, records=records, backup_file=backup_file
        )
    else:
        return self._run_sync_pipeline(
            folder=folder, records=records, backup_file=backup_file
        )
```

E no `_run_sync_pipeline`, substituir:
```python
# ANTIGO:
self.chk_load_missing_only.isChecked()
self.chk_preserve_structure.isChecked()
self.chk_last_folder.isChecked()

# NOVO:
self.chk_options.is_checked("missing_only")
self.chk_options.is_checked("preserve")
self.chk_options.is_checked("lastfolder")
```

---

## 7. IMPORTS A REMOVER E ADICIONAR

### Remover (imports antigos)
```python
from ..core.ui.WidgetFactory import WidgetFactory
# Nenhum import de resources/widgets/ ou resources/styles/
```

### Adicionar (imports novos)
```python
from ..resources.widgets.grid.GridComplexSelector import GridComplexSelector
from ..resources.widgets.grid.GridCheckbox import GridCheckbox
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.widgets.CollapsibleParametersWidget import CollapsibleParametersWidget
```

---

## 8. ORDEM DE IMPLEMENTAÇÃO

| Passo | O que fazer | Arquivos |
|-------|-------------|----------|
| 1 | **CRIAR** `GridCheckboxButtons` — widget genérico de botões (sem built-ins, tudo via dict) | `resources/widgets/grid/GridCheckboxButtons.py` |
| 2 | **MELHORAR** `GridCheckbox` — adicionar `dependents` (sistema de dependência) + `control_buttons_config` (botões opcionais) + `select_all/deselect_all/invert_selection` | `resources/widgets/grid/GridCheckbox.py` |
| 3 | **CRIAR** `CollapsibleParametersWidget` — com paintEvent gradiente, AppStyles, tokens do tema | `resources/widgets/CollapsibleParametersWidget.py` |
| 4 | **ATUALIZAR** `docs/skills/SKILL_WIDGETS2.md` — adicionar CollapsibleParametersWidget + GridCheckboxButtons + GridCheckbox melhorias | `docs/skills/SKILL_WIDGETS2.md` |
| 5 | **MIGRAR** `LoadFolderLayers.py` — substituir todos os widgets da Factory | `plugins/LoadFolderLayers.py` |
| 6 | **ATUALIZAR** `docs/plano_eliminacao_widgetfactory.md` — marcar LoadFolderLayers como migrado | `docs/plano_eliminacao_widgetfactory.md` |
| 7 | **ATUALIZAR** `docs/ia/changelog.txt` | `docs/ia/changelog.txt` |

---

## 9. RISCOS

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| `CollapsibleParametersWidget` com paintEvent gradiente não ficar igual ao antigo | Alto | Seguir o padrão dos widgets widgets: AppStyles + tokens do tema |
| Sistema de `dependents` quebrar outros plugins que usam GridCheckbox | Alto | `dependents` é opcional (default vazio). Só afeta quem declarar |
| `control_buttons_config` aumentar complexidade do GridCheckbox | Médio | Desacoplar: GridCheckbox cria GridCheckboxButtons internamente, sem expor ao plugin |
| Prefs antigas não carregarem no novo formato | Baixo | `set_preferences()` aceita dict vazio |

---

## 10. CHECKLIST FINAL

### 10.1 Criar `GridCheckboxButtons`
- [ ] Widget genérico: TODOS os botões via `config` dict
- [ ] Usa `SimpleModernButton` (gradiente + glow)
- [ ] Sem botões built-in (Fechar/Info/Config)
- [ ] `separator_top`, `separator_bottom`
- [ ] `_apply_styles()` com `AppStyles` + `_specific_style()`

### 10.2 Melhorar `GridCheckbox`
- [ ] Sistema `dependents` no config dict: `"key": {"dependents": ["filho1", "filho2"]}`
- [ ] Quando pai desmarcado → dependentes desmarcados + desabilitados
- [ ] Quando pai marcado → dependentes reabilitados com estado anterior
- [ ] Estado dos dependentes salvo antes de desabilitar (`_dep_states`)
- [ ] Parâmetro `control_buttons_config` (None = sem botões)
- [ ] Métodos: `select_all()`, `deselect_all()`, `invert_selection()`
- [ ] `control_buttons_config` cria `GridCheckboxButtons` internamente

### 10.3 Criar `CollapsibleParametersWidget`
- [ ] `paintEvent` com `QPainter` + `QLinearGradient`
- [ ] Gradiente horizontal usando tokens: `COLOR_SURFACE_1`, `COLOR_SURFACE_2`, etc.
- [ ] Header clicável com ícone ▶/▼
- [ ] `add_content_widget(widget)` e `add_content_layout(layout)`
- [ ] `set_expanded(bool)` e `is_expanded()`
- [ ] `_apply_styles()` com `AppStyles` + `_specific_style()`
- [ ] Compatibilidade Qt5/Qt6

### 10.4 Migrar `LoadFolderLayers.py`
- [ ] `GridComplexSelector` para seletor de pasta
- [ ] `CollapsibleParametersWidget` + `GridCheckbox` com `control_buttons_config` para tipos
- [ ] `GridCheckbox` com `dependents` para opções (preserve → lastfolder)
- [ ] `GridExecutionButtons` para botões de ação
- [ ] `_load_prefs` e `_save_prefs` atualizados
- [ ] `execute_tool` e `_run_sync_pipeline` atualizados
- [ ] Imports antigos removidos
- [ ] Plugin não importa `core/ui/WidgetFactory`
- [ ] Plugin não importa `resources/styles/`
- [ ] Plugin não chama `setStyleSheet()`

### 10.5 Atualizar documentação
- [ ] `docs/skills/SKILL_WIDGETS2.md` — CollapsibleParametersWidget + GridCheckboxButtons + GridCheckbox atualizado
- [ ] `docs/plano_eliminacao_widgetfactory.md` — FASE 2.10 marcado
- [ ] `docs/ia/changelog.txt` — nova versão

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-27 | 1.0.0 | Criação do plano de ação inicial |
| 2026-07-27 | 2.0.0 | **Revisão:** CollapsibleParametersWidget com paintEvent gradiente + AppStyles; GridCheckbox com sistema `dependents` nativo; GridCheckbox com `control_buttons_config` + `GridCheckboxButtons` widget genérico; dependência gerenciada pelo widget, plugin só declara |