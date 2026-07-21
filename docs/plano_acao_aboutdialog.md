# 🎯 PLANO DE AÇÃO: Migração AboutDialog

**Objetivo:** Migrar o `AboutDialog` do sistema antigo (`WidgetFactory`) para o novo sistema (`new_widgets` + `AppStyles`).

**Data:** 2026-07-21
**Plugin:** `plugins/AboutDialog.py`
**Herda de:** `BaseDialog`
**Versão alvo:** 2.3.63

---

## 1. Análise do Plugin Atual

### O que AboutDialog usa da WidgetFactory

| # | Chamada | Widget gerado | Parâmetros relevantes |
|---|---------|---------------|-----------------------|
| 1 | `WidgetFactory.create_label()` | QLabel | text, bold, word_wrap, text_format, alignment |
| 2 | `WidgetFactory.create_label()` | QLabel | text, bold, word_wrap, text_format, alignment, text_interaction_flags, open_external_links |
| 3 | `WidgetFactory.create_simple_button()` | layout + QPushButton | text, separator_top, separator_bottom |

### O que permanece igual (NÃO será migrado agora)

- `BaseDialog._build_ui()` — ERRADO MUDANÇA PARA O SISTEMA NOVO COMPLETA CRIE O NOVO MAINLAYOUT 
- `BaseDialog` — herança inalterada
- `LogUtils` com `ToolKey.ABOUT_DIALOG` — permanece
- `STR.` strings — permanece
- Ícones sociais (QPushButton + QHBoxLayout) — permanece (código manual, não via Factory)

---

## 2. Widgets Necessários (Novo Sistema)

### Simple (USO INTERNO)

| Widget | Arquivo | Qt Base | AppStyles | Métodos extras |
|--------|---------|---------|-----------|----------------|
| `SimpleLabel` | `new_widgets/simple/SimpleLabel.py` | QLabel | `label()` | `setText()`, `setAlignment()` |   ERRADO VC IRA CRIAR UM SIMPLE LABEL PARA USO EM WIDGETS E UM GRIDLABELWIDGET PARA USO INTERNO DO PLUGIN
| `SimpleButton` | `new_widgets/simple/SimpleButton.py` | QPushButton | `button()` | `clicked` SERA VIA CALLBACK NAO POR SINAL WIDGETS NAO USAM SINAL ?(ADICIONE NA SKILL )

### Grid (PLUGINS USAM)

| Widget | Arquivo | Composição | Parâmetros |
|--------|---------|------------|------------|
| `GridLabel` | `new_widgets/grid/GridLabel.py` | 1+ SimpleLabel em VBox | `items: list[str]` |
| `GridButton` | `new_widgets/grid/GridButton.py` | 1+ SimpleButton em layout | `close_callback`, `run_callback`, `info_callback` |

### Raiz (SEM versão grid)

| Widget | Arquivo | Qt Base | Descrição |
|--------|---------|---------|-----------|
| `SeparatorWidget` | `new_widgets/SeparatorWidget.py` | QFrame | Separador visual entre widgets |

---

## 3. Mapeamento Antigo → Novo

### Antes (WidgetFactory)

```python
lbl_title = WidgetFactory.create_label(
    text=f"<h2>{STR.APP_NAME}</h2>",
    bold=False, word_wrap=True, parent=self,
    text_format=Qt.TextFormat.RichText,
    alignment=Qt.AlignmentFlag.AlignCenter,
)
self.layout.addWidget(lbl_title)

lbl_info = WidgetFactory.create_label(
    text=info_text,
    bold=False, word_wrap=True, parent=self,
    text_format=Qt.TextFormat.RichText,
    text_interaction_flags=_qt_text_browser_interaction(),
    open_external_links=True,
    alignment=Qt.AlignmentFlag.AlignCenter,
)
self.layout.addWidget(lbl_info)

close_layout, close_button = WidgetFactory.create_simple_button(
    text=STR.CLOSE,
    parent=self,
    separator_top=True,
    separator_bottom=False,
)
close_button.clicked.connect(self.close)
self.layout.addLayout(close_layout)
```

### Depois (New Widgets)

```python
from ..resources.new_widgets.grid.GridLabel import GridLabel
from ..resources.new_widgets.grid.GridButton import GridButton
from ..resources.new_widgets.SeparatorWidget import SeparatorWidget

# Labels via GridLabel
self.grid_info = GridLabel(
    items=[
        f"<h2>{STR.APP_NAME}</h2>",
        info_text,
    ],
    parent=self,
)
self.layout.addWidget(self.grid_info)

# Separador
self.layout.addWidget(SeparatorWidget())

# Botão fechar via GridButton
self.action_buttons = GridButton(
    close_callback=self.close,
    parent=self,
)
self.layout.addWidget(self.action_buttons)
```

---

## 4. Checklist de Implementação

### Pré-requisitos (FASE 0)
- [x] BaseTheme com tokens descritivos
- [x] ThemeManager com BaseTheme registrado
- [x] AppStyles.py criado
- [x] utils/qt_compat.py criado
- [x] SKILL_WIDGETS2.md criada

### Widgets a criar (FASE 1)
- [ ] `new_widgets/simple/__init__.py`
- [ ] `new_widgets/simple/SimpleLabel.py`
- [ ] `new_widgets/simple/SimpleButton.py`
- [ ] `new_widgets/grid/__init__.py`
- [ ] `new_widgets/grid/GridLabel.py`
- [ ] `new_widgets/grid/GridButton.py`
- [ ] `new_widgets/SeparatorWidget.py`
- [ ] `new_widgets/__init__.py`

### Migração (FASE 2 — AboutDialog)
- [ ] Remover `from ..core.ui.WidgetFactory import WidgetFactory`
- [ ] Adicionar imports dos new_widgets
- [ ] Substituir `create_label()` por `GridLabel`
- [ ] Substituir `create_simple_button()` por `GridButton` + `SeparatorWidget`
- [ ] NÃO modificar ícones sociais (código manual)

### Pós-migração
- [ ] Plugin não importa `core/ui/WidgetFactory`
- [ ] Plugin não importa `resources/styles/`
- [ ] Plugin não chama `setStyleSheet()`
- [ ] Atualizar `docs/ia/changelog.txt`

---

## 5. Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Quebrar links (text_interaction_flags) | Baixa | Alto | Testar clique nos links após migração |
| Perder alinhamento dos labels | Média | Médio | Verificar alignment no SimpleLabel |
| Botão close sem callback | Baixa | Alto | Garantir que `clicked.connect` funcione |
| Social icons quebrarem | Baixa | Médio | Não tocar no código deles |
</file_content>