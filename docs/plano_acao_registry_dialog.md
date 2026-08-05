# 🎯 PLANO DE AÇÃO: Migração do RegistryDialog para o Novo Sistema de Widgets

**Objetivo:** Migrar `core/ui/RegistryDialog.py` do `WidgetFactory` + QtWidgets direto para os widgets de `resources/widgets/`, seguindo estritamente o contrato do plugin e o plano de eliminação da WidgetFactory.

**Data:** 2026-08-04
**Versão pretendida:** 2.3.86.x
**Autor:** Cadmus Engineering

---

## 1. Resumo da Migração

| Widget Antigo (QtWidgets/Factory) | Widget Novo (widgets) | Observação |
|-----------------------------------|---------------------------|-----------|
| `QLineEdit` (chave) | `GridInputFields` | Campo de texto para chave de licença |
| `QPushButton` Validar (ícone) | `GridExecutionButtons` (item `validate`) | Botão Validar com `is_run_button=True` |
| `QLabel` Nível / Validade / Status (grid 3×2) | `GridLabel` + opção `color` | Labels com cor dinâmica por status |
| `QPushButton` Apagar Licença | `GridExecutionButtons` (item `delete`) | Botão Remover |
| `WidgetFactory.create_grid_complex_selector` (arquivo .dist) | `GridComplexSelector` | Seletor de arquivo `.dist` para restaurar |
| `QPushButton` Restaurar | `GridExecutionButtons` (item `restore`) | Botão Restaurar distribuição |
| `QPushButton` Salvar + Fechar (QHBoxLayout) | `GridExecutionButtons` | `enable_close_button=True` + item `save` |

---

## 2. Widgets Necessários — APIs Confirmadas

| Widget | Arquivo | API usada no plugin |
|--------|---------|---------------------|
| `GridInputFields` | `resources/widgets/grid/GridInputFields.py` | `set_value()`, `get_value()`, `clear()` via `set_value(key, "")` |
| `GridLabel` | `resources/widgets/grid/GridLabel.py` | `set_text()`, `get_text()` — **precisa suporte a `color`** |
| `GridExecutionButtons` | `resources/widgets/grid/GridExecutionButtons.py` | `config` (callbacks por botão), `enable_close_button`, `enable_info` |
| `GridComplexSelector` | `resources/widgets/grid/GridComplexSelector.py` | `get_path("Distribuição")`, `set_path()`, `get_preferences()`/`set_preferences()` |

---

## 3. Ajuste Necessário no Widget: `GridLabel` — Suporte a Cor

O `GridLabel` atual (`resources/widgets/grid/GridLabel.py`, 111 linhas) **NÃO suporta cor por item**. O RegistryDialog precisa colorir o label de Status (verde=ativa, vermelho=inválida, cinza=inativa).

### 3.1 Proposta — adicionar `"color"` ao config dict do `GridLabel`

**Modificação mínima no widget** (o plugin NUNCA chama `setStyleSheet`):

```python
# resources/widgets/grid/GridLabel.py

def __init__(self, config, separator_top=False, separator_bottom=False, parent=None):
    ...
    for key, cfg in config.items():
        text = cfg.get("text", "")
        label = SimpleLabel(text=text, parent=self)

        description = cfg.get("description")
        if description:
            label.setToolTip(description)

        color = cfg.get("color")
        if color:
            label.setStyleSheet(f"{AppStyles.label()} color: {color};")

        self._labels.append(label)
        self._label_map[key] = label
        layout.addWidget(label)
```

E atualizar `set_config()`:

```python
def set_config(self, config: dict) -> None:
    for key, cfg in config.items():
        text = cfg.get("text", "")
        if key in self._label_map:
            self._label_map[key].setText(str(text))
        description = cfg.get("description")
        if description and key in self._label_map:
            self._label_map[key].setToolTip(description)
        color = cfg.get("color")
        if color and key in self._label_map:
            self._label_map[key].setStyleSheet(f"{AppStyles.label()} color: {color};")
```

**Valores de cor usados:** `green`, `red`, `gray` — ou tokens do tema se necessário.

### 3.2 Alternativa considerada (rejeitada)

Usar `GridReadOnly` (SimpleReadOnly) para Nível/Validade/Status — visual de campo readonly, não de label informativo. O usuário pediu explicitamente **GridLabel com opção de cor**, então esta é a abordagem escolhida.

---

## 4. Estrutura do Novo `_build_ui`

### 4.1 Widgets criados

```python
# ── Campo de Chave (GridInputFields) ─────────────────────────────
self.key_input = GridInputFields(
    config={
        "lic_key": {
            "label": f"{STR.VALIDATE}:",
            "description": "Insira a chave de licença",
            "default": "",
        },
    },
    parent=self,
)
self.layout.addWidget(self.key_input)

# ── Labels de Info (GridLabel + opção color) ─────────────────────
self.info_labels = GridLabel(
    config={
        "level": {"text": f"{STR.LEVEL}: -", "color": ""},
        "expiry": {"text": f"{STR.EXPIRATION_DATE}: -", "color": ""},
        "status": {"text": f"{STR.STATUS}: {STR.INACTIVE}", "color": "gray"},
    },
    separator_bottom=True,
    parent=self,
)
self.layout.addWidget(self.info_labels)

# ── Restaurar Distribuição (GridComplexSelector) ─────────────────
self.dist_grid = GridComplexSelector(
    config={
        "Distribuição": {
            "label": f"📦 {STR.SELECT_FILE} (.dist):",
            "description": "Selecione o arquivo de distribuição Cadmus",
            "file_filter": "Distribuição Cadmus (*.dist);;Todos os arquivos (*)",
            "mode_type": "input",
            "allow_file": True,
            "allow_folder": False,
            "multiple": False,
            "show_explorer_button": True,
            "show_copy_button": False,
        },
    },
    tool_key=ToolKey.SETTINGS,
    title="Restaurar Distribuição",
    separator_bottom=True,
    parent=self,
)
self.layout.addWidget(self.dist_grid)

# ── Botões de Ação (GridExecutionButtons) ────────────────────────
self.action_buttons = GridExecutionButtons(
    config={
        "validate": {
            "label": STR.VALIDATE,
            "description": "Valida a chave de licença",
            "callback": self._on_validate,
            "is_run_button": True,
        },
        "delete": {
            "label": f"🗑️ {STR.REMOVE}",
            "description": "Remove a licença atual",
            "callback": self._on_delete,
        },
        "restore": {
            "label": f"📦 {STR.MODE_RESTORE}",
            "description": "Restaura a distribuição a partir do arquivo .dist",
            "callback": self._on_restore_distribution,
        },
        "save": {
            "label": f"💾 {STR.SAVE}",
            "description": "Salva e valida a chave",
            "callback": self._on_save,
        },
    },
    enable_close_button=True,
    enable_config_button=False,
    enable_info=False,
    tool_key=ToolKey.SETTINGS,
    parent=self,
)
self.layout.add_execution_buttons(self.action_buttons)
```

### 4.2 Ordem de adição no layout (MainLayout)

```python
self.layout.addWidget(self.key_input)
self.layout.addWidget(self.info_labels)
self.layout.addWidget(self.dist_grid)
self.layout.add_execution_buttons(self.action_buttons)
```

---

## 5. Ajustes na Lógica (`_refresh` / Handlers)

### 5.1 `_refresh()` — atualizar labels via `GridLabel.set_text()`

```python
def _refresh(self):
    if self.lic_mgr is None:
        # Premium — esconde campos de licença
        self.key_input.setVisible(False)
        self.info_labels.setVisible(False)
        return

    info = self.lic_mgr.get_registry_info()
    has_key = info.get("has_key", False)
    is_active = info.get("is_active", False)
    is_valid = has_key and is_active

    nivel = info.get("nivel", 0)
    self.info_labels.set_text("level", f"{STR.LEVEL}: {str(nivel) if is_valid and nivel > 0 else '-'}")
    self.info_labels.set_text("expiry", f"{STR.EXPIRATION_DATE}: {info.get('expiry') if is_valid else '-'}")

    if is_valid:
        days = info.get("days_remaining", 0)
        self.info_labels.set_text("status", f"{STR.STATUS}: {STR.ACTIVE} ({days} {STR.REMAINING_DAYS})")
        self.info_labels.set_config({"status": {"text": ..., "color": "green"}})
    elif has_key:
        self.info_labels.set_config({"status": {"text": ..., "color": "red"}})
    else:
        self.info_labels.set_config({"status": {"text": ..., "color": "gray"}})
```

### 5.2 `_on_validate()` / `_on_save()`

- `key = self.key_input.get_value("lic_key").strip()`
- Limpar campo: `self.key_input.set_value("lic_key", "")`

### 5.3 `_on_restore_distribution()`

- Obter path do selector: `file_path = self.dist_grid.get_path("Distribuição")`
- O restante da lógica (PackageManager.install_package) permanece igual.

### 5.4 `_on_delete()`

- `self.key_input.set_value("lic_key", "")`
- Restante permanece igual.

---

## 6. Imports Novos (remover WidgetFactory + QtWidgets)

### Remover
```python
from qgis.PyQt.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGridLayout, QWidget
from ...resources.styles.Styles import Styles
from ..ui.WidgetFactory import WidgetFactory
```

### Adicionar
```python
from ..resources.widgets.grid.GridInputFields import GridInputFields
from ..resources.widgets.grid.GridLabel import GridLabel
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.widgets.grid.GridComplexSelector import GridComplexSelector
```

### Manter
```python
from ...plugins.BaseDialog import BaseDialog
from ...i18n.TranslationManager import STR
from ..config.LogUtils import LogUtils
from ...utils.ToolKeys import ToolKey
from ..services.PackageManager import PackageManager
```

---

## 7. Strings — Verificação

### Existentes (reutilizar)
| String | Valor |
|--------|-------|
| `STR.VALIDATE` | "Validar" |
| `STR.REMOVE` | "Remover" |
| `STR.SAVE` | "Salvar" |
| `STR.CLOSE` | "Fechar" |
| `STR.LEVEL` | "Nível" |
| `STR.EXPIRATION_DATE` | "Validade" |
| `STR.STATUS` | "Status" |
| `STR.ACTIVE` | "Ativa" |
| `STR.INACTIVE` | "Inativa" |
| `STR.REMAINING_DAYS` | "dias restantes" |
| `STR.REG_TITLE` | "Gerenciar" |
| `STR.REGISTRY_SAVED_SUCCESS` | "Salvo e validado com sucesso." |
| `STR.REGISTRY_DELETED_SUCCESS` | "Removido com sucesso." |
| `STR.REGISTRY_INVALID` | "Inválido." |
| `STR.REGISTRY_EMPTY` | "Preencha o campo." |

### Novas strings necessárias (adicionar em Strings_pt_BR)
| String | Valor proposto |
|--------|---------------|
| `STR.RESTORE_DISTRIBUTION` | "Restaurar Distribuição" |
| `STR.SELECT_DIST_FILE` | "Selecione um arquivo .dist primeiro." |
| `STR.DIST_FILE_NOT_FOUND` | "Seletor de distribuição não encontrado." |
| `STR.LICENSE_KEY` | "Chave de Licença" |

---

## 8. Passos de Implementação

1. **Modificar** `resources/widgets/grid/GridLabel.py` — adicionar suporte a `"color"` no config dict (seção 3)
2. **Adicionar** strings novas em `i18n/Strings_pt_BR.py` (seção 7)
3. **Migrar** `core/ui/RegistryDialog.py`:
   - Remover imports `WidgetFactory`, `Styles`, QtWidgets
   - Substituir por `GridInputFields` + `GridLabel` + `GridComplexSelector` + `GridExecutionButtons`
   - Ajustar `_refresh()`, `_on_validate()`, `_on_save()`, `_on_delete()`, `_on_restore_distribution()` conforme seção 5
4. **Validar** com flake8 e bandit
5. **Atualizar** `docs/plano_eliminacao_widgetfactory.md` (seção 8.1, TODO 2.20 — RegistryDialog)
6. **Atualizar** `docs/skills/SKILL_WIDGETS2.md` (GridLabel com `color`)
7. **Atualizar** `docs/ia/changelog.txt` (nova versão `2.3.86.x`)

---

## 9. Conformidade com o Contrato

| Regra | Conformidade |
|-------|-------------|
| UI via widgets (nunca QtWidgets direto) | ✅ `GridInputFields`, `GridLabel`, `GridComplexSelector`, `GridExecutionButtons` |
| Logging via LogUtils (nunca print) | ✅ mantém `self.logger` |
| Strings via STR (nunca hardcoded) | ✅ requiridas strings novas |
| ToolKey é enum | ✅ `ToolKey.SETTINGS` |
| Estilos via widgets (nunca setStyleSheet no plugin) | ✅ plugin não chama setStyleSheet; cor via `GridLabel` config |
| Exceções logadas com logger.exception | ✅ mantém |
| Configurações via Preferences | ✅ `GridComplexSelector.get_preferences()/set_preferences()` |
| `GridExecutionButtons` SEM botão config | ✅ `enable_config_button=False` |
| Botões Validar/Remover/Restaurar no GridExecutionButtons | ✅ conforme solicitado |
| `GridComplexSelector` para restaurar distribuição | ✅ conforme solicitado |
| `GridLabel` com opção de cor | ✅ modificação no widget (GridLabel) |

---

## 10. Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| `GridLabel` sem suporte a cor | Adicionar `"color"` ao config dict (modificação mínima no widget) |
| `GridExecutionButtons` sem ícone em botão de config | Botões usam `label` com emoji/texto (🗑️, 📦, 💾) — `SimpleModernButton` suporta texto |
| `_refresh()` esconde/mostra widgets dinamicamente | `setVisible(False)` funciona em qualquer QWidget |
| Flag `_premium` (lic_mgr None) | Manter lógica: esconde `key_input` e `info_labels`, mantém `dist_grid` + botão restaurar visíveis |
| Path do seletor `.dist` | `self.dist_grid.get_path("Distribuição")` — chave do config dict |

---

## 11. Checklist Final

- [ ] Modificar `resources/widgets/grid/GridLabel.py` (suporte a `color`)
- [ ] Adicionar strings novas em `i18n/Strings_pt_BR.py`
- [ ] Migrar `core/ui/RegistryDialog.py` (remover WidgetFactory + QtWidgets)
- [ ] Ajustar `_refresh()` (label status com cor dinâmica)
- [ ] Ajustar handlers (`_on_validate`, `_on_save`, `_on_delete`, `_on_restore_distribution`)
- [ ] Validar flake8 + bandit
- [ ] Atualizar `docs/plano_eliminacao_widgetfactory.md`
- [ ] Atualizar `docs/skills/SKILL_WIDGETS2.md`
- [ ] Atualizar `docs/ia/changelog.txt`