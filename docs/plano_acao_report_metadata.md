# 🎯 PLANO DE AÇÃO: Migração do ReportMetadataPlugin

**Objetivo:** Migrar `plugins/ReportMetadataPlugin.py` do sistema antigo (`WidgetFactory`) para o novo sistema de widgets autoconfiguráveis (`resources/new_widgets/`).

**Data:** 2026-07-27
**Versão:** 1.0.0
**Plugin:** ReportMetadataPlugin (ToolKey: `REPORT_METADATA`)

---

## Sumário

1. [Análise do Plugin Atual](#1-análise-do-plugin-atual)
2. [Mapeamento WidgetFactory → new_widgets](#2-mapeamento-widgetfactory--new_widgets)
3. [Estratégia de Migração](#3-estratégia-de-migração)
4. [Checklist de Migração](#4-checklist-de-migração)
5. [Código Migrado (Preview)](#5-código-migrado-preview)
6. [Pós-migração](#6-pós-migração)

---

## 1. Análise do Plugin Atual

### 1.1 Widgets Usados via WidgetFactory

| # | Widget Factory | Uso no Plugin | Retorno | Callbacks |
|---|---------------|---------------|---------|-----------|
| # | Widget Factory | Uso no Plugin | Retorno | Callbacks |
|---|---------------|---------------|---------|-----------|
| 1 | `create_dropdown_selector` | Seletor de JSONs temporários | `(dropdown_layout, self.json_selector)` | Nenhum (acesso via `get_selected_key()`) |
| 2 | `create_simple_button` (x4) | Refresh, Open JSONs, Open Reports, Vetorizar | `(layout, self.refresh_button)` etc | `clicked.connect(self._on_*)` |
| 3 | `create_bottom_action_buttons` | Gerar Relatório + Fechar + Info | `(buttons_layout, _)` | `run_callback`, `close_callback`, `info_callback` |
| — | **Ausente** | **Explicação do plugin (tooltip/texto descritivo)** | — | — |

### 1.2 Métodos e Atributos Relevantes

| Método/Atributo | Descrição | Impacto na Migração |
|-----------------|-----------|---------------------|
| `self.json_selector` | Widget do dropdown (API: `get_selected_key()`, `set_options()`) | Mudar para `GridComboBox` |
| `self.refresh_button` | Botão refresh | Mudar para `GridModernButtons` |
| `self.open_json_button` | Botão abrir pasta JSON | Mudar para `GridModernButtons` |
| `self.open_reports_button` | Botão abrir pasta Reports | Mudar para `GridModernButtons` |
| `self.vetorize_button` | Botão vetorizar voo | Mudar para `GridModernButtons` |
| `_reload_json_options(initial)` | Recarrega lista de JSONs e atualiza dropdown | Adaptar para `GridComboBox.set_options()` |
| `_apply_compact_horizontal_ui()` | Ajusta tamanhos e políticas de redimensionamento | **Remover** (novos widgets gerenciam isso) |
| `_save_prefs()` | Salva JSON selecionado nas preferências | Adaptar para nova API |
| `execute_tool()` | Gera relatório a partir do JSON selecionado | Adaptar para nova API do combo |
| `_vectorize_from_json()` | Vetoriza voo a partir do JSON | Adaptar para nova API do combo |

### 1.3 Imports Atuais (WidgetFactory)

```python
from ..core.ui.WidgetFactory import WidgetFactory
```

### 1.4 Layout Atual (Ordem dos Widgets)

```
1. Dropdown (JSON selector)     ← WidgetFactory.create_dropdown_selector
2. Botão Refresh                ← WidgetFactory.create_simple_button
3. Botão Open JSONs Folder      ← WidgetFactory.create_simple_button
4. Botão Open Reports Folder    ← WidgetFactory.create_simple_button
5. Botão Vetorizar Voo          ← WidgetFactory.create_simple_button
6. Botões Executar/Fechar/Info  ← WidgetFactory.create_bottom_action_buttons
```

---

## 2. Mapeamento WidgetFactory → new_widgets

### 2.1 Tabela de Substituição

| WidgetFactory (ANTIGO) | new_widgets (NOVO) | Arquivo |
|------------------------|-------------------|---------|
| — (ausente) | **`GridLabel`** (explicação do plugin) | `resources/new_widgets/grid/GridLabel.py` |
| `create_dropdown_selector` | `GridComboBox` (1 item: "json_selector") | `resources/new_widgets/grid/GridComboBox.py` |
| `create_simple_button` (x4) | `GridModernButtons` (4 itens no config) | `resources/new_widgets/grid/GridModernButtons.py` |
| `create_bottom_action_buttons` | `GridExecutionButtons` | `resources/new_widgets/grid/GridExecutionButtons.py` |

### 2.2 GridComboBox — Configuração

```python
self.json_selector = GridComboBox(
    config={
        "json_selector": {
            "label": "JSON:",
            "description": "Selecione o arquivo JSON temporário",
            "options": self.json_options,  # {path: label}
            "selected_key": self.preferences.get(self.PREF_SELECTED_JSON),
            "onchange": self._on_json_changed,  # callback(chave, texto)
        },
    },
    parent=self,
)
```

**API de substituição:**

| Acesso Antigo | Acesso Novo |
|---------------|-------------|
| `self.json_selector.get_selected_key()` | `self.json_selector.get_selected_key("json_selector")` |
| `self.json_selector.set_options(options)` | `self.json_selector.set_options("json_selector", options)` |
| `self.json_selector.combo()` | `self.json_selector.widget("json_selector")` |

### 2.3 GridModernButtons — Configuração (abrir pasta/refresh)

```python
self.action_buttons = GridModernButtons(
    config={
        "refresh": {
            "label": STR.REFRESH_JSON_LIST,
            "callback": self._on_refresh,
            "description": "Atualizar lista de JSONs",
            "primary": False,
        },
        "open_json": {
            "label": STR.OPEN_JSONS_FOLDER,
            "callback": self._open_json_folder,
            "description": "Abrir pasta de JSONs",
            "primary": False,
        },
        "open_reports": {
            "label": STR.OPEN_REPORTS_FOLDER,
            "callback": self._open_reports_folder,
            "description": "Abrir pasta de relatórios",
            "primary": False,
        },
    },
    separator_top=True,
    separator_bottom=True,
    parent=self,
)
```

**⚠️ Mudança importante:** Não há mais `self.refresh_button`, `self.open_json_button`, etc. como atributos individuais. Os botões são gerenciados internamente pelo `GridModernButtons`. O `_apply_compact_horizontal_ui()` que ajustava `setMaximumWidth` e `setCursor` em cada botão **deve ser removido** — o `GridModernButtons` gerencia o layout automaticamente.

### 2.4 GridExecutionButtons — Configuração

```python
self.exec_buttons = GridExecutionButtons(
    config={
        "run": {
            "label": STR.GENERATE_REPORT,
            "description": "Gerar relatório HTML a partir do JSON selecionado",
            "callback": self.execute_tool,
            "is_run_button": True,
        },
    },
    enable_close_button=True,
    enable_info=True,
    tool_key=self.TOOL_KEY,
    parent=self,
)
```

### 2.5 Separadores

Adicionar `SeparatorWidget()` entre seções para melhor organização visual:

```python
self.layout.addWidget(self.json_selector)
self.layout.addWidget(SeparatorWidget())
self.layout.addWidget(self.action_buttons)       # GridModernButtons
self.layout.add_execution_buttons(self.exec_buttons)  # GridExecutionButtons
```

---

## 3. Estratégia de Migração

### 3.1 O que MUDA

1. **Imports:** Remover `WidgetFactory`, adicionar `GridComboBox`, `GridModernButtons`, `GridExecutionButtons`, `SeparatorWidget`
2. **UI:** Substituir chamadas Factory por construtores de new_widgets
3. **API de acesso ao combo:** `self.json_selector.get_selected_key()` → `self.json_selector.get_selected_key("json_selector")`
4. **API de atualização do combo:** `self.json_selector.set_options(options)` → `self.json_selector.set_options("json_selector", options)`
5. **Botões individuais:** Remover `self.refresh_button`, `self.open_json_button`, `self.open_reports_button`, `self.vetorize_button` — usar `GridModernButtons`
6. **`_apply_compact_horizontal_ui()`:** Remover completamente
7. **Layout:** Usar `self.layout.addWidget()` + `self.layout.add_execution_buttons()`
8. **`_reload_json_options(initial)`:** Simplificar — não precisa mais do parâmetro `initial`

### 3.2 O que NÃO MUDA

1. Lógica de negócio (`execute_tool`, `_vectorize_from_json`, `_create_track_from_layer`, etc.)
2. Preferências (`_save_prefs`, `_load_prefs`)
3. ToolKey (`TOOL_KEY = ToolKey.REPORT_METADATA`)
4. Logger e tratamento de exceções
5. Métodos auxiliares (`_list_json_files`, `_format_json_label`, `_resolve_layer_name`, etc.)
6. Herança de `BasePluginMTL`

### 3.3 Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| API do combo mudar | Baixa | Alto | Testar `get_selected_key("json_selector")` |
| Botões sem referência individual | Média | Médio | `GridModernButtons` não expõe botões individuais — verificar se `_apply_compact_horizontal_ui` é realmente necessário |
| `onchange` callback não funcionar | Baixa | Médio | Testar callback do `GridComboBox` |
| Layout quebrar sem `_apply_compact_horizontal_ui` | Média | Baixo | `GridModernButtons` com `alignment="left"` já gerencia layout |

---

## 4. Checklist de Migração

### 4.1 Pré-migração

- [ ] Ler `docs/skills/SKILL_WIDGETS2.md` (contrato do novo sistema)
- [ ] Ler `docs/skills/PLUGIN_CONTRACT.md` (12 regras críticas)
- [ ] Verificar se `GridComboBox` suporta `onchange` callback
- [ ] Verificar se `GridModernButtons` suporta `alignment="left"`
- [ ] Verificar se `GridExecutionButtons` suporta `enable_close_button` + `enable_info`

### 4.2 Migração

- [ ] **Substituir imports:**
  - Remover: `from ..core.ui.WidgetFactory import WidgetFactory`
  - Adicionar: `from ..resources.new_widgets.grid.GridComboBox import GridComboBox`
  - Adicionar: `from ..resources.new_widgets.grid.GridModernButtons import GridModernButtons`
  - Adicionar: `from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons`
  - Adicionar: `from ..resources.new_widgets.SeparatorWidget import SeparatorWidget`

- [ ] **Substituir dropdown selector:**
  - Antigo: `dropdown_layout, self.json_selector = WidgetFactory.create_dropdown_selector(...)`
  - Novo: `self.json_selector = GridComboBox(config={...}, parent=self)`

- [ ] **Substituir botões de ação (refresh, open, vetorizar):**
  - Antigo: 4x `WidgetFactory.create_simple_button(...)` + `clicked.connect(...)`
  - Novo: 1x `GridModernButtons(config={...}, alignment="left", parent=self)`

- [ ] **Substituir botões de execução:**
  - Antigo: `buttons_layout, _ = WidgetFactory.create_bottom_action_buttons(...)`
  - Novo: `self.exec_buttons = GridExecutionButtons(config={...}, ...)`

- [ ] **Atualizar `_reload_json_options`:**
  - Remover parâmetro `initial`
  - Usar `self.json_selector.set_options("json_selector", self.json_options)`

- [ ] **Atualizar `_save_prefs`:**
  - Antigo: `self.json_selector.get_selected_key()`
  - Novo: `self.json_selector.get_selected_key("json_selector")`

- [ ] **Atualizar `execute_tool`:**
  - Antigo: `self.json_selector.get_selected_key()`
  - Novo: `self.json_selector.get_selected_key("json_selector")`

- [ ] **Atualizar `_vectorize_from_json`:**
  - Antigo: `self.json_selector.get_selected_key()`
  - Novo: `self.json_selector.get_selected_key("json_selector")`

- [ ] **Atualizar layout (`_build_ui`):**
  - Antigo: `self.layout.add_items([dropdown_layout, refresh_layout, ...])`
  - Novo: `self.layout.addWidget(self.json_selector)` + `self.layout.addWidget(self.action_buttons)` + `self.layout.add_execution_buttons(self.exec_buttons)`

- [ ] **Remover `_apply_compact_horizontal_ui`:**
  - Remover chamada no final de `_build_ui`
  - Remover definição do método

- [ ] **Remover `_qt_adjust_to_minimum_contents_length_with_icon`:**
  - Função auxiliar de compatibilidade não é mais necessária

### 4.3 Pós-migração

- [ ] Plugin não importa de `core/ui/WidgetFactory`
- [ ] Plugin não importa de `resources/styles/`
- [ ] Plugin não chama `setStyleSheet()`
- [ ] Plugin não importa `qgis.PyQt.QtWidgets` direto (exceto `QComboBox` se necessário)
- [ ] `GridExecutionButtons` adicionado via `self.layout.add_execution_buttons()`
- [ ] Testar carregamento da lista de JSONs
- [ ] Testar seleção de JSON
- [ ] Testar botão Refresh
- [ ] Testar botão Open JSONs Folder
- [ ] Testar botão Open Reports Folder
- [ ] Testar botão Vetorizar Voo
- [ ] Testar botão Gerar Relatório
- [ ] Testar botão Fechar
- [ ] Testar botão Info
- [ ] Testar salvamento de preferências (JSON selecionado persiste)
- [ ] Atualizar `docs/ia/changelog.txt`

---

## 5. Código Migrado (Preview)

### 5.1 Novos Imports

```python
# Remover:
# from ..core.ui.WidgetFactory import WidgetFactory
# from qgis.PyQt.QtWidgets import QComboBox, QSizePolicy
# from qgis.PyQt.QtCore import Qt
# Função _qt_adjust_to_minimum_contents_length_with_icon

# Adicionar:
from ..resources.new_widgets.grid.GridLabel import GridLabel
from ..resources.new_widgets.grid.GridComboBox import GridComboBox
from ..resources.new_widgets.grid.GridModernButtons import GridModernButtons
from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons
```

### 5.2 Novo `_build_ui`

⚠️ **Importante:** `_reload_json_options()` NÃO pode ser chamado antes do `GridComboBox` existir, pois ele tenta acessar `self.json_selector.set_options()`. Em vez disso, carregar os files manualmente antes de criar os widgets.

```python
def _build_ui(self, **kwargs):
    super()._build_ui(
        title=STR.REPORT_METADATA_TITLE,
        icon_path=im.REPORT_METADATA,
        enable_scroll=True,
    )

    # Carrega lista de JSONs ANTES de criar widgets
    files = self._list_json_files()
    self.json_options = {path: self._format_json_label(path) for path in files}

    # ── Explicação do Plugin (GridLabel) ────────────────────
    self.explanation_label = GridLabel(
        config={
            "explanation": {
                "text": STR.REPORT_METADATA_TOOLTIP,
                "description": "Ferramenta para regerar relatorios HTML a partir de JSONs temporarios",
            },
        },
        separator_bottom=True,
        parent=self,
    )
    self.layout.addWidget(self.explanation_label)

    # ── JSON Selector (GridComboBox) ────────────────────────
    self.json_selector = GridComboBox(
        config={
            "json_selector": {
                "label": "JSON:",
                "description": "Selecione o arquivo JSON temporário",
                "options": self.json_options,
                "selected_key": self.preferences.get(self.PREF_SELECTED_JSON),
                "onchange": self._on_json_changed,
            },
        },
        parent=self,
    )
    self.layout.addWidget(self.json_selector)

    # ── Action Buttons (GridModernButtons) ──────────────────
    self.action_buttons = GridModernButtons(
        config={
            "refresh": {
                "label": STR.REFRESH_JSON_LIST,
                "callback": self._on_refresh,
                "description": "Atualizar lista de JSONs temporários",
                "primary": False,
            },
            "open_json": {
                "label": STR.OPEN_JSONS_FOLDER,
                "callback": self._open_json_folder,
                "description": "Abrir pasta de JSONs temporários",
                "primary": False,
            },
            "open_reports": {
                "label": STR.OPEN_REPORTS_FOLDER,
                "callback": self._open_reports_folder,
                "description": "Abrir pasta de relatórios HTML",
                "primary": False,
            },
        },
        separator_top=True,
        separator_bottom=True,
        parent=self,
    )
    self.layout.addWidget(self.action_buttons)

    # ── Execution Buttons (GridExecutionButtons) ────────────
    self.exec_buttons = GridExecutionButtons(
        config={
            "vetorize": {
                "label": STR.VETORIZE_FLIGHT,
                "callback": self._vectorize_from_json,
                "description": "Vetorizar voo a partir do JSON selecionado",
                "is_run_button": False,
            },
            "run": {
                "label": STR.GENERATE_REPORT,
                "description": "Gerar relatório HTML a partir do JSON selecionado",
                "callback": self.execute_tool,
                "is_run_button": True,
            },
        },
        enable_close_button=True,
        enable_info=True,
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    self.layout.add_execution_buttons(self.exec_buttons)
```

### 5.3 Novo `_reload_json_options`

```python
def _reload_json_options(self):
    """Recarrega a lista de JSONs temporários e atualiza o combo."""
    files = self._list_json_files()
    self.json_options = {path: self._format_json_label(path) for path in files}
    self.json_selector.set_options("json_selector", self.json_options)
    self.logger.info(
        "Lista de JSONs temporarios atualizada",
        data={"total_json": len(self.json_options)},
    )
```

### 5.4 Novo `_save_prefs`

```python
def _save_prefs(self):
    selected = self.json_selector.get_selected_key("json_selector") if self.json_selector else ""
    self.preferences[self.PREF_SELECTED_JSON] = selected or ""
    Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
```

### 5.5 Callback `_on_json_changed` (NOVO)

```python
def _on_json_changed(self, key, text):
    """Callback quando o usuário seleciona um JSON diferente."""
    self._save_prefs()
```

### 5.6 Atualizações em `execute_tool` e `_vectorize_from_json`

Ambos os métodos usam `self.json_selector.get_selected_key()` — mudar para:

```python
selected_json = self.json_selector.get_selected_key("json_selector") if self.json_selector else ""
```

### 5.7 Remoções

Os seguintes itens **devem ser removidos**:

1. **`_apply_compact_horizontal_ui`** — método inteiro
2. **`_qt_adjust_to_minimum_contents_length_with_icon`** — função helper
3. **Chamada `self._apply_compact_horizontal_ui()`** no final de `_build_ui`
4. **Atributos individuais** `self.refresh_button`, `self.open_json_button`, `self.open_reports_button`, `self.vetorize_button`
5. **Import** `from qgis.PyQt.QtWidgets import QComboBox, QSizePolicy` (se não usado em outro lugar)
6. **Import** `from ..core.ui.WidgetFactory import WidgetFactory`

---

## 6. Pós-migração

### 6.1 Verificações Finais

- [ ] Plugin abre sem erros
- [ ] Lista de JSONs carrega corretamente
- [ ] Seleção de JSON persiste entre execuções
- [ ] Botão Refresh atualiza a lista
- [ ] Botão Open JSONs Folder abre a pasta correta
- [ ] Botão Open Reports Folder abre a pasta correta
- [ ] Botão Vetorizar Voo funciona
- [ ] Botão Gerar Relatório funciona
- [ ] Botão Fechar fecha o diálogo
- [ ] Botão Info abre as instruções
- [ ] UI não está quebrada (sem overflow, sem cortes)

### 6.2 Atualizações Necessárias

- [ ] Atualizar `docs/ia/changelog.txt` com a migração
- [ ] Atualizar `docs/plano_eliminacao_widgetfactory.md` (marcar ReportMetadataPlugin como migrado na FASE 2)

### 6.3 Changelog

```
2.3.71.1[27/07/2026] Migração ReportMetadataPlugin para new_widgets:
   - Substituído WidgetFactory.create_dropdown_selector por GridComboBox
   - Substituído WidgetFactory.create_simple_button (x4) por GridModernButtons
   - Substituído WidgetFactory.create_bottom_action_buttons por GridExecutionButtons
   - Removido _apply_compact_horizontal_ui (gerenciado pelos novos widgets)
   - Removido _qt_adjust_to_minimum_contents_length_with_icon (não necessário)
   - Adicionado SeparatorWidget entre seções
   - Adicionado callback _on_json_changed para salvar preferências ao selecionar JSON
```

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-27 | 1.0.0 | Criação inicial — Plano de migração do ReportMetadataPlugin |