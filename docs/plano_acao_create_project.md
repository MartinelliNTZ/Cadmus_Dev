# 🎯 PLANO DE AÇÃO: Refatoração CreateProjectPlugin — Novo Sistema de Widgets

**Objetivo:** Migrar `CreateProjectPlugin` (incluindo `DefaultProjectsFolderDialog` e `ProjectNameDialog`) da `WidgetFactory` para o novo sistema de widgets autoconfiguráveis (`resources/new_widgets/`), eliminando dependências do sistema antigo.

**Data:** 2026-07-27
**Versão:** 2.0.0
**Autor:** Cadmus Engineering
**Status:** ⏳ Planejamento (aguardando validação)

---

## Sumário

1. [Widgets Necessários](#1-widgets-necessários)
2. [Modelo Proposto — DefaultProjectsFolderDialog (NOVO)](#2-modelo-proposto--defaultprojectsfolderdialog-novo)
3. [Modelo Proposto — ProjectNameDialog (NOVO)](#3-modelo-proposto--projectnamedialog-novo)
4. [Modelo Proposto — CreateProjectPlugin (alterações)](#4-modelo-proposto--createprojectplugin-alterações)
5. [Arquivos Afetados](#5-arquivos-afetados)
6. [Estratégia de Implementação](#6-estratégia-de-implementação)
7. [Checklist de Implementação](#7-checklist-de-implementação)

---

## 1. Widgets Necessários

### 1.1 DefaultProjectsFolderDialog (NOVO)

| Widget Atual (WidgetFactory) | Novo Widget (new_widgets/) | Status |
|---|---|---|
| `WidgetFactory.create_label()` — texto informativo | **`GridLabel`** ✅ | ✅ Existe |
| `SelectorWidget` — seletor de pasta | **`GridComplexSelector`** ✅ | ✅ Existe |
| `ExecutionButtonsWidget` — OK + Cancelar | **`GridExecutionButtons`** ✅ (nativo: accept + close + info) | ✅ Existe |

### 1.2 ProjectNameDialog (NOVO)

| Widget Atual (WidgetFactory) | Novo Widget (new_widgets/) | Status |
|---|---|---|
| `WidgetFactory.create_label()` + QLineEdit + QHBoxLayout — tudo num único GridLabel | **`GridLabel`** ✅ (único, com texto formatado: pasta + nome) | ✅ Existe |
| `WidgetFactory.create_simple_button()` — ⚙️ Abrir Config | **❌ Removido** — `GridExecutionButtons` já tem `enable_config_button` nativo | 🔄 Substituir |
| `QLineEdit` + `Styles.input_fields_widget()` — input nome | **`GridInputFields`** ✅ (com placeholder via `setPlaceholderText()` no SimpleQLineEdit) | ✅ Existe |
| `ExecutionButtonsWidget` — Criar + Fechar + Info | **`GridExecutionButtons`** ✅ (nativo: config item + close + info) | ✅ Existe |

---

## 2. Modelo Proposto — DefaultProjectsFolderDialog (NOVO)

Layout do diálogo (top → bottom):

```
┌─────────────────────────────────────┐
│  AppBar: "Pasta Padrão de Projetos" │
├─────────────────────────────────────┤
│                                     │
│  ┌─ GridLabel ────────────────────┐ │
│  │  [Texto informativo]           │ │
│  └────────────────────────────────┘ │
│                                     │
│  ┌─ GridComplexSelector ──────────┐ │
│  │  Pasta de projetos: [______] 🔍│ │
│  └────────────────────────────────┘ │
│                                     │
│  ┌─ GridExecutionButtons ─────────┐ │
│  │  [Aceitar]  [Fechar]  ⚙️  📖  │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### 2.1 GridComplexSelector — Comportamento

- **mode = "folder"** — seleciona pasta, não arquivo
- **allow_folder = True**, allow_file = False
- **multiple = False** — apenas uma pasta
- **show_explorer_button = True** — botão 📂 para abrir explorador
- **show_copy_button** — NÃO especificar (default True, mantém comportamento padrão)
- **mode_type = "input"** — pasta de entrada
- **tool_key** recebido do plugin

```python
self.selector = GridComplexSelector(
    config={
        "projects_folder": {
            "label": STR.PROJECTS_FOLDER,
            "description": STR.DEFAULT_PROJECTS_FOLDER_PROMPT,
            "allow_folder": True,
            "allow_file": False,
            "multiple": False,
            "mode_type": "input",
            "show_explorer_button": True,
        },
    },
    tool_key=self.TOOL_KEY,
    separator_top=True,
    separator_bottom=True,
    parent=self,
)
```

### 2.2 GridExecutionButtons — Comportamento (NATIVO)

**REGRAS:**
- `enable_close_button = True` — nativo, vira "Fechar" (resolve o cancelar)
- `enable_config_button = True` — nativo, ⚙️ Config (default True, NÃO mexer)
- `enable_info = True` — nativo, 📖 Info (default True, NÃO mexer)
- Botão principal (Aceitar) via config com `is_run_button = True`
- **NÃO** adicionar item "cancel" no config — o botão Fechar built-in já resolve

```python
self.action_buttons = GridExecutionButtons(
    config={
        "accept": {
            "label": STR.OK,
            "description": "Confirmar pasta padrão",
            "callback": self._on_accept,
            "is_run_button": True,
        },
    },
    # enable_close_button, enable_config_button, enable_info são True por padrão
    tool_key=self.TOOL_KEY,
    parent=self,
)
```

### 2.3 Substituir signals por callback direto

**ANTIGO:** `self.folder_selected = pyqtSignal(str)` — plugin conecta externamente.  
**NOVO:** Método `get_folder_path()` + callback direto. O diálogo retorna o path via `show()` não-modal, usando callback.

```python
class DefaultProjectsFolderDialog(BaseDialog):
    """Diálogo para seleção da pasta padrão de projetos."""

    def __init__(self, current_folder: str = "", parent=None):
        super().__init__(parent)
        self._current_folder = current_folder
        self._result_path = ""
        
        self._build_ui(
            title=STR.DEFAULT_PROJECTS_FOLDER_TITLE,
            enable_scroll=False,
            minimum_size=(300, 160),
        )
        self._build_inner_ui()
    
    def get_folder_path(self) -> str:
        """Retorna o caminho da pasta selecionada."""
        return self._result_path

    def _build_inner_ui(self):
        # GridLabel com texto informativo
        info = GridLabel(config={
            "prompt": {"text": STR.DEFAULT_PROJECTS_FOLDER_PROMPT},
        }, parent=self)
        self.layout.addWidget(info)

        # GridComplexSelector para pasta
        self.selector = GridComplexSelector(config={
            "projects_folder": {
                "label": STR.PROJECTS_FOLDER,
                "allow_folder": True,
                "allow_file": False,
                "multiple": False,
                "mode_type": "input",
            },
        }, tool_key=self.TOOL_KEY, parent=self)
        if self._current_folder:
            self.selector.set_path("projects_folder", self._current_folder)
        self.layout.addWidget(self.selector)

        # GridExecutionButtons — NATIVO (close, config, info built-in)
        self.action_buttons = GridExecutionButtons(
            config={
                "accept": {
                    "label": STR.OK,
                    "callback": self._on_accept,
                    "is_run_button": True,
                },
            },
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.layout.add_execution_buttons(self.action_buttons)
```

---

## 3. Modelo Proposto — ProjectNameDialog (NOVO)

Layout do diálogo (top → bottom):

```
┌─────────────────────────────────────┐
│  AppBar: "Nome do Projeto"          │
├─────────────────────────────────────┤
│                                     │
│  ┌─ GridLabel (ÚNICO) ────────────┐ │
│  │  📂 Pasta padrão de projetos:   │ │
│  │  C:\Users\...\projetos          │ │
│  │                                 │ │
│  │  ✏️ Nome do projeto:            │ │
│  │  [___________] (suggest fundo)  │ │
│  └────────────────────────────────┘ │
│                                     │
│  (Botão Config ⚙️ já está no       │ │
│   GridExecutionButtons embaixo)    │ │
│                                     │
│  ┌─ GridExecutionButtons ─────────┐ │
│  │  [Criar Projeto]  [Fechar] ⚙️ 📖│ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### 3.1 GridLabel ÚNICO — Exibir pasta + nome do projeto

**APENAS 1 GridLabel** com tudo: título da pasta, caminho, label do nome, e o input do nome.

```python
# ── GridLabel ÚNICO com tudo ──
self.info_group = GridLabel(config={
    "folder_title": {"text": f"📂 {STR.PROJECTS_DEFAULT_FOLDER}:"},
    "folder_path": {"text": self._base_folder},
    "name_label": {"text": f"✏️ {STR.PROJECT_NAME_LABEL}:"},
}, parent=self)
self.layout.addWidget(self.info_group)
```

### 3.2 GridInputFields — Nome do projeto com PLACEHOLDER (não default)

**CORREÇÃO:** `default` NÃO é placeholder. O `GridInputFields` precisa ser ajustado para suportar `placeholder` no config dict, que chama `setPlaceholderText()` no `SimpleQLineEdit`.

O `SimpleQLineEdit` já tem parâmetro `placeholder`. O `GridInputFields` precisa passar esse valor para o `SimpleQLineEdit`.

**Mudança necessária no `GridInputFields`:** Adicionar suporte a `"placeholder"` no config dict, que chama `setPlaceholderText()` no input.

```python
# ── Nome do projeto com placeholder (suggest ao fundo) ──
self.name_input = GridInputFields(config={
    "project_name": {
        "label": STR.PROJECT_NAME_LABEL,
        "description": STR.PROJECT_NAME_PROMPT,
        "placeholder": self._suggested_name,  # suggest como PLACEHOLDER (texto ao fundo)
        "default": "",                         # campo vazio inicialmente
    },
}, title=None, separator_top=True, separator_bottom=True, parent=self)
self.layout.addWidget(self.name_input)

# API pública: acessar o valor
# project_name = self.name_input.get_value("project_name")
```

**Ajuste necessário no `GridInputFields._build_ui()`:**

```python
# No loop de criação dos campos, após criar o input_field:
placeholder = field_config.get("placeholder", "")
if placeholder:
    input_field.setPlaceholderText(placeholder)
```

### 3.3 GridExecutionButtons — Criar + Fechar + Config + Info (NATIVO)

O botão ⚙️ Config **já vem built-in** no `GridExecutionButtons` via `enable_config_button=True` (default).  
Não precisa mais de botão separado como no `ProjectNameDialog` antigo.

```python
self.action_buttons = GridExecutionButtons(
    config={
        "create": {
            "label": STR.CREATE_PROJECT,
            "description": "Criar o projeto na pasta definida",
            "callback": self._on_accept,
            "is_run_button": True,
        },
    },
    # enable_close_button, enable_config_button, enable_info são True por padrão
    tool_key=self.TOOL_KEY,
    parent=self,
)
self.layout.add_execution_buttons(self.action_buttons)
```

**Vantagem:** O `config_callback` padrão do `GridExecutionButtons` já abre o `SettingsPlugin` automaticamente — não precisa mais implementar `_open_settings()` manualmente no diálogo.

### 3.4 Diálogo NÃO-MODAL (show)

**CORREÇÃO:** O diálogo deve ser NÃO-MODAL, usando `show()` em vez de `exec()`.

O `CreateProjectPlugin._resolve_project_name()` precisa:
1. Criar o `ProjectNameDialog` com os parâmetros atuais
2. Chamar `show()` (não-modal)
3. Conectar ao signal `project_accepted` para receber o nome

```python
def _resolve_project_name(self):
    """Abre dialogo nao-modal para nome do projeto."""
    if not self._base_folder:
        self.logger.error("_base_folder vazio — impossivel criar projeto")
        QgisMessageUtil.modal_error(...)
        return

    suggested_name = ExplorerUtils.next_indexed_folder_name(
        base_folder=self._base_folder,
        prefix="NovoProjeto_",
        pattern=self.GENERIC_PROJECT_PATTERN,
    )
    name_dialog = ProjectNameDialog(
        suggested_name=suggested_name,
        base_folder=self._base_folder,
        project_tool_key=self.TOOL_KEY,
        parent=self.iface.mainWindow(),
    )
    # NÃO-MODAL: usa signal + show()
    name_dialog.project_accepted.connect(self._on_project_name_accepted)
    name_dialog.show()
```

**Manter o signal `project_accepted`** no `ProjectNameDialog` para comunicação não-modal.

---

## 4. Modelo Proposto — CreateProjectPlugin (alterações)

### 4.1 Fluxo geral (mantido)

```
execute_tool()
  └─ _resolve_base_folder()
      ├─ Prefs tem pasta? → _prepare_existing_base_folder() → _resolve_project_name()
      └─ Não tem → _prompt_and_persist_base_folder()
          └─ DefaultProjectsFolderDialog (NOVO) → _on_folder_selected() → _resolve_project_name()
              └─ ProjectNameDialog (NOVO, show()) → signal project_accepted → _on_project_name_accepted()
                  └─ _create_project_structure()
```

### 4.2 Mudanças no CreateProjectPlugin

| Aspecto | Antes | Depois |
|---------|-------|--------|
| `DefaultProjectsFolderDialog` | `from ..core.ui.dialogs.DefaultProjectsFolderDialog` | **Mesmo import** (diálogo refatorado internamente) |
| `ProjectNameDialog` | `from ..core.ui.dialogs.ProjectNameDialog` | **Mesmo import** (diálogo refatorado internamente) |
| `get_project_name()` no `ProjectNameDialog` | Lê de `self.name_input.text()` | Lê de `self.name_input.get_value("project_name")` |
| Botão Config ⚙️ | Botão separado no layout do `ProjectNameDialog` | **Removido** — `GridExecutionButtons` já tem `enable_config_button` nativo |
| `_resolve_project_name()` | `exec()` modal | `show()` não-modal + signal |

**O plugin em si (`CreateProjectPlugin.py`) NÃO precisa mudar imports de widgets** — ele só importa os diálogos, que serão refatorados internamente.

---

## 5. Arquivos Afetados

### 5.1 Arquivos a Modificar

| Arquivo | Tipo | Mudança |
|---------|------|---------|
| `core/ui/dialogs/DefaultProjectsFolderDialog.py` | Refatorar | Substituir WidgetFactory + SelectorWidget + ExecutionButtonsWidget por GridLabel + GridComplexSelector + GridExecutionButtons (nativo) |
| `core/ui/dialogs/ProjectNameDialog.py` | Refatorar | Substituir WidgetFactory + QLineEdit + ExecutionButtonsWidget por GridLabel único + GridInputFields + GridExecutionButtons (nativo). Remover botão Config ⚙️ manual. |
| `resources/new_widgets/grid/GridInputFields.py` | Melhorar | Adicionar suporte a `"placeholder"` no config dict (chama `setPlaceholderText()`) |

### 5.2 Arquivos NÃO Modificados

| Arquivo | Motivo |
|---------|--------|
| `plugins/CreateProjectPlugin.py` | Plugin só importa os diálogos, não precisa mudar |

### 5.3 Dependências

- `GridLabel` ✅ — já existe em `resources/new_widgets/grid/GridLabel.py`
- `GridComplexSelector` ✅ — já existe em `resources/new_widgets/grid/GridComplexSelector.py`
- `GridInputFields` ✅ — já existe em `resources/new_widgets/grid/GridInputFields.py` (precisa adicionar suporte a `placeholder`)
- `GridExecutionButtons` ✅ — já existe em `resources/new_widgets/grid/GridExecutionButtons.py`
- `SeparatorWidget` ✅ — já existe em `resources/new_widgets/SeparatorWidget.py`

---

## 6. Estratégia de Implementação

### 6.1 Ordem de Implementação

```
1. Adicionar suporte a "placeholder" no GridInputFields
2. Refatorar DefaultProjectsFolderDialog (substituir widgets antigos)
3. Refatorar ProjectNameDialog (substituir widgets antigos + remover botão Config manual)
4. Testar fluxo completo de CreateProjectPlugin
```

### 6.2 Passo 0 — GridInputFields: Adicionar suporte a placeholder

No método `_build_ui()` do `GridInputFields`, após criar o `input_field`:

```python
# Adicionar suporte a placeholder
placeholder = field_config.get("placeholder", "")
if placeholder:
    input_field.setPlaceholderText(placeholder)
```

### 6.3 Passo 1 — DefaultProjectsFolderDialog

1. Substituir imports antigos:
   - ❌ `from ....resources.widgets.simple.SelectorWidget import SelectorWidget`
   - ❌ `from ....resources.widgets.ExecutionButtonsWidget import ExecutionButtonsWidget`
   - ❌ `from ....core.ui.WidgetFactory import WidgetFactory`
   - ✅ `from ..resources.new_widgets.grid.GridLabel import GridLabel`
   - ✅ `from ..resources.new_widgets.grid.GridComplexSelector import GridComplexSelector`
   - ✅ `from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons`

2. Substituir `WidgetFactory.create_label()` por `GridLabel(config=...)`

3. Substituir `SelectorWidget` por `GridComplexSelector(config=...)`

4. Substituir `ExecutionButtonsWidget` por `GridExecutionButtons(config=...)` com apenas 1 item (accept) + built-ins

5. Remover `pyqtSignal` — usar callback direto

### 6.4 Passo 2 — ProjectNameDialog

1. Substituir imports antigos:
   - ❌ `from ....resources.widgets.ExecutionButtonsWidget import ExecutionButtonsWidget`
   - ❌ `from ....core.ui.WidgetFactory import WidgetFactory`
   - ❌ `from ....plugins.SettingsPlugin import SettingsPlugin`
   - ✅ `from ..resources.new_widgets.grid.GridLabel import GridLabel`
   - ✅ `from ..resources.new_widgets.grid.GridInputFields import GridInputFields`
   - ✅ `from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons`

2. Substituir labels + QLineEdit da pasta + QHBoxLayout manual por **1 único `GridLabel`** com todos os textos

3. Substituir QLineEdit do nome por `GridInputFields(config=...)` com `placeholder`

4. Remover botão Config ⚙️ manual e método `_open_settings()` — `GridExecutionButtons` já tem `enable_config_button` nativo

5. Remover import de `SettingsPlugin` (não é mais necessário)

6. Substituir `ExecutionButtonsWidget` por `GridExecutionButtons(config=...)` com apenas 1 item (create) + built-ins

7. Manter signal `project_accepted` para comunicação não-modal

---

## 7. Checklist de Implementação

### 7.0 GridInputFields

- [ ] Adicionar suporte a `"placeholder"` no config dict
- [ ] Chamar `input_field.setPlaceholderText(placeholder)` no `_build_ui()`

### 7.1 DefaultProjectsFolderDialog

- [ ] Substituir imports antigos por new_widgets
- [ ] Substituir `WidgetFactory.create_label()` por `GridLabel(config=...)`
- [ ] Substituir `SelectorWidget` por `GridComplexSelector(config=...)`
- [ ] Substituir `ExecutionButtonsWidget` por `GridExecutionButtons(config=...)` com 1 item + built-ins
- [ ] Ajustar `_on_accept()` para ler path do `GridComplexSelector`
- [ ] Ajustar `get_folder_path()` para retornar do `self._result_path`
- [ ] Remover `pyqtSignal`

### 7.2 ProjectNameDialog

- [ ] Substituir imports antigos por new_widgets
- [ ] Substituir labels + QLineEdit da pasta por **1 único `GridLabel`** com textos
- [ ] Substituir QLineEdit + QHBoxLayout do nome por `GridInputFields(config=...)` com `placeholder`
- [ ] Remover botão Config ⚙️ manual (linhas `settings_layout, settings_btn = ...`)
- [ ] Remover método `_open_settings()` (não é mais necessário)
- [ ] Remover import de `SettingsPlugin` (não é mais necessário)
- [ ] Substituir `ExecutionButtonsWidget` por `GridExecutionButtons(config=...)` com 1 item + built-ins
- [ ] Ajustar `_on_accept()` para ler nome do `GridInputFields`
- [ ] Ajustar `get_project_name()` para usar nova API
- [ ] Manter signal `project_accepted` (necessário para não-modal)
- [ ] Manter `_show_instructions()` e `InfoDialog` (ainda relevante)

### 7.3 Pós-Migração

- [ ] `DefaultProjectsFolderDialog` não importa de `core/ui/WidgetFactory`
- [ ] `DefaultProjectsFolderDialog` não importa de `resources/widgets/`
- [ ] `DefaultProjectsFolderDialog` não importa de `resources/styles/`
- [ ] `ProjectNameDialog` não importa de `core/ui/WidgetFactory`
- [ ] `ProjectNameDialog` não importa de `resources/widgets/`
- [ ] `ProjectNameDialog` não importa de `resources/styles/`
- [ ] Testar fluxo completo: execute_tool() → pasta → nome → criar projeto
- [ ] Testar cancelamento em cada etapa
- [ ] Testar Config ⚙️ abre SettingsPlugin corretamente (nativo)
- [ ] Atualizar `docs/ia/changelog.txt`

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-27 | 1.0.0 | Criação inicial |
| 2026-07-27 | 2.0.0 | Correções: ProjectNameDialog com 1 GridLabel único; DefaultProjectsFolderDialog usa GridExecutionButtons nativo (close/config/info built-in, sem cancel item); GridInputFields precisa de suporte a `placeholder` (não `default`); diálogo não-modal com `show()` |