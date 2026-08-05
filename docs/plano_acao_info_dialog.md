# 🎯 PLANO DE AÇÃO: Migração InfoDialog

**Objetivo:** Migrar o `core/ui/info_dialog.py` para o novo sistema de widgets autoconfiguráveis, eliminando dependência da `WidgetFactory`.

**Data:** 2026-07-24
**Versão:** 1.1.0
**Autor:** Cadmus Engineering

---

## Sumário

1. [Análise do InfoDialog](#1-análise-do-infodialog)
2. [Widgets Necessários](#2-widgets-necessários)
3. [Dependências Entre Widgets](#3-dependências-entre-widgets)
4. [Estratégia de Migração](#4-estratégia-de-migração)
5. [FASE 0 — Criar TextBrowser](#5-fase-0--criar-textbrowser)
6. [FASE 1 — Migrar InfoDialog](#6-fase-1--migrar-infodialog)
7. [FASE 2 — Atualizar Usuários do InfoDialog](#7-fase-2--atualizar-usuários-do-infodialog)
8. [Riscos e Mitigações](#8-riscos-e-mitigações)
9. [TODO Consolidado](#9-todo-consolidado)

---

## 1. Análise do InfoDialog

### 1.1 Arquitetura Atual

```
InfoDialog (core/ui/info_dialog.py)
├── herda BaseDialog
├── __init__(instructions_path, parent, title, tool_key)
│   ├── self._build_ui(title, enable_scroll=False, minimum_size=(700, 550))
│   ├── browser = WidgetFactory.create_text_browser(parent=self)  ← QTextBrowser
│   ├── Carrega .md → setMarkdown() ou _markdown_to_html() fallback
│   ├── self.layout.addWidget(browser)
│   ├── btn_layout, btn_widget = WidgetFactory.create_simple_button(
│   │       text=STR.CLOSE, parent=self, spacing=20)
│   ├── btn_widget.clicked.connect(self.close)
│   └── self.layout.addLayout(btn_layout)
│
└── _markdown_to_html(text) → str  (fallback Qt < 5.14)
```

### 1.2 Dependências da Factory

| Chamada Factory | Retorno | Uso no InfoDialog |
|----------------|---------|-------------------|
| `create_text_browser(parent=self)` | `QTextBrowser` widget | Exibir markdown/HTML |
| `create_simple_button(text=STR.CLOSE, parent=self, spacing=20)` | `(QVBoxLayout, QPushButton)` | Botão fechar |

### 1.3 Onde InfoDialog é Usado

Preciso rastrear quem instancia `InfoDialog` para garantir que a migração não quebre nada.

### 1.4 Funcionalidades Específicas

1. **Renderização Markdown** — usa `setMarkdown()` nativo (Qt ≥ 5.14) ou fallback `_markdown_to_html()`
2. **Botão Fechar** — botão simples que fecha o diálogo
3. **Sem scroll** — `enable_scroll=False` (diálogo de tamanho fixo 700×550)
4. **ToolKey configurável** — recebe `tool_key` como parâmetro (padrão `UNTRACEABLE`)

---

## 2. Widgets Necessários

### 2.1 TextBrowser (NOVO — raiz de `widgets/`)

Widget na raiz de `resources/widgets/` — **não tem versão grid** porque não precisa. Apenas widgets que precisam de múltiplas instâncias organizadas em grid têm versão `simple/` + `grid/`.

```python
# resources/widgets/TextBrowser.py
"""
TextBrowser — QTextBrowser com AppStyles.text_browser().
Widget raiz (sem versão grid) — usado diretamente pelo InfoDialog.

Uso:
    browser = TextBrowser(parent=self)
    browser.set_markdown(text)  # setMarkdown com fallback Qt5/Qt6
    browser.set_html(html)
"""
```

**API necessária:**
- `set_markdown(text: str)` — setMarkdown com fallback Qt5/Qt6
- `set_html(html: str)` — setHtml
- `set_plain_text(text: str)` — setPlainText
- `document()` — acesso ao QTextDocument

**Estilo:** `AppStyles.text_browser()` (NOVO método em AppStyles)

### 2.2 Widgets Existentes que Serão Usados

| Widget | Local | Já existe? |
|--------|-------|-----------|
| `GridExecutionButtons` | `resources/widgets/grid/` | ✅ |
| `MainLayout` | `resources/widgets/` | ✅ |

> **Nota:** O `GridExecutionButtons` gerencia internamente seus botões (fechar, info, config). O InfoDialog só precisa de um botão fechar, que é habilitado via `enable_close_button=True`. Não é necessário instanciar `SimpleModernButton` separadamente.

---

## 3. Dependências Entre Widgets

```
InfoDialog (MIGRADO)
├── TextBrowser (NOVO — raiz) ← QTextBrowser + AppStyles.text_browser()
│   └── AppStyles.text_browser() (NOVO método)
│
├── GridExecutionButtons (já existe ✅)
│
└── MainLayout (já existe ✅)
    └── BaseDialog._build_ui() (já existe ✅)
```

**Dependência mínima:** Apenas 1 widget novo + 1 método novo em AppStyles:
1. `resources/widgets/TextBrowser.py` ← widget base (raiz, sem grid)
2. `AppStyles.text_browser()` ← método de estilo

---

## 4. Estratégia de Migração

### 4.1 Princípios

1. **Criar TextBrowser** primeiro — depende de AppStyles.text_browser()
2. **Adicionar AppStyles.text_browser()** — estilo para QTextBrowser
3. **Migrar InfoDialog** — substituir Factory → widgets
4. **Nunca modificar arquivos antigos** — manter `WidgetFactory.py`, `resources/widgets/`, etc.

### 4.2 Contratos Obrigatórios

✅ Segue SKILL_WIDGETS2.md:
- Herda de `QWidget` (ou similar)
- `try/except` no `__init__`
- `_apply_styles()` no final
- Plugin NUNCA chama `setStyleSheet()`
- Plugin NUNCA importa `AppStyles` ou `ThemeManager`
- Callbacks são passadas como parâmetros, não como sinais Qt expostos

### 4.3 API de Comunicação

```python
# ANTIGO (Factory) — plugin recebe widget
browser = WidgetFactory.create_text_browser(parent=self)
browser.document().setMarkdown(md_text)

# NOVO (widgets) — plugin instancia widget direto
browser = TextBrowser(parent=self)
browser.set_markdown(md_text)

# API de acesso mantida:
browser.document()  # ainda disponível (herda de QTextBrowser)
```

### 4.4 Botão Fechar

```python
# ANTIGO — Factory retorna (layout, widget)
btn_layout, btn_widget = WidgetFactory.create_simple_button(
    text=STR.CLOSE, parent=self, spacing=20)
btn_widget.clicked.connect(self.close)
self.layout.addLayout(btn_layout)

# NOVO — GridExecutionButtons com enable_close_button=True
# O GridExecutionButtons gerencia o botão fechar internamente.
# Não precisa conectar sinal — o callback de fechar é automático.
self.action_buttons = GridExecutionButtons(
    config={},
    enable_close_button=True,
    enable_info=False,
    tool_key=tool_key,
    parent=self,
)
self.layout.add_execution_buttons(self.action_buttons)
```

---

## 5. FASE 0 — Criar TextBrowser

### 5.1 AppStyles.text_browser()

Adicionar método em `resources/styles/AppStyles.py`:

```python
@classmethod
def text_browser(cls) -> str:
    """Estilo para QTextBrowser."""
    theme = cls._get_theme()
    return f"""
    QTextBrowser {{
        background: {theme.COLOR_PANEL_BACKGROUND};
        color: {theme.COLOR_TEXT_PRIMARY};
        border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
        border-radius: {theme.BORDER_RADIUS_INPUT_FIELD};
        padding: {theme.PADDING_INPUT_FIELD};
        font-size: {theme.INPUT_FIELD_FONT_SIZE};
        selection-background-color: {theme.COLOR_PRIMARY};
        selection-color: {theme.COLOR_TEXT_ON_PRIMARY};
    }}
    QTextBrowser:hover {{
        border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_HOVER};
    }}
    """
```

### 5.2 TextBrowser

```python
# resources/widgets/TextBrowser.py
# -*- coding: utf-8 -*-
"""
TextBrowser — QTextBrowser com AppStyles.text_browser().
Widget raiz (sem versão grid) — usado diretamente pelo InfoDialog.

Características:
- Renderização Markdown nativa (setMarkdown) com fallback Qt5/Qt6
- Links externos abrem no navegador padrão
- Read-only por padrão
"""

from qgis.PyQt.QtWidgets import QTextBrowser
from ..styles.AppStyles import AppStyles


class TextBrowser(QTextBrowser):
    """
    QTextBrowser com estilo AppStyles.text_browser().

    Parâmetros
    ----------
    open_external_links : bool, optional
        Abrir links externos no navegador (padrão True).
    read_only : bool, optional
        Read-only (padrão True).
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        open_external_links: bool = True,
        read_only: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.setOpenExternalLinks(open_external_links)
        self.setReadOnly(read_only)
        self._apply_styles()

    def _apply_styles(self):
        """Aplica estilos globais de text browser."""
        combined = self._get_global_style() + self._specific_style()
        self.setStyleSheet(combined)

    def _get_global_style(self) -> str:
        return AppStyles.text_browser()

    def _specific_style(self) -> str:
        return ""

    def set_markdown(self, text: str) -> None:
        """
        Define conteúdo Markdown com fallback Qt5/Qt6.

        Usa setMarkdown se disponível (Qt >= 5.14),
        caso contrário converte para HTML.
        """
        doc = self.document()
        if hasattr(doc, "setMarkdown"):
            doc.setMarkdown(text)
        else:
            html = self._markdown_to_html(text)
            self.setHtml(html)

    @staticmethod
    def _markdown_to_html(text: str) -> str:
        """
        Conversão simples de Markdown para HTML.
        Compatível com QGIS 3.16 (sem setMarkdown).
        """
        import re

        html = text

        # Títulos
        html = re.sub(r"^###### (.*)", r"<h6>\1</h6>", html, flags=re.MULTILINE)
        html = re.sub(r"^##### (.*)", r"<h5>\1</h5>", html, flags=re.MULTILINE)
        html = re.sub(r"^#### (.*)", r"<h4>\1</h4>", html, flags=re.MULTILINE)
        html = re.sub(r"^### (.*)", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.*)", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.*)", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # Negrito
        html = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", html)

        # Itálico
        html = re.sub(r"\*(.*?)\*", r"<i>\1</i>", html)

        # Quebra de linha
        html = html.replace("\n", "<br>")

        return f"<html><body>{html}</body></html>"
```

---

## 6. FASE 1 — Migrar InfoDialog

### 6.1 Código Migrado

```python
# core/ui/info_dialog.py (MIGRADO)
# -*- coding: utf-8 -*-
import os
from ..core.config.LogUtils import LogUtils
from ..plugins.BaseDialog import BaseDialog
from ..i18n.TranslationManager import STR
from ..utils.ToolKeys import ToolKey
from ..resources.widgets.TextBrowser import TextBrowser
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons


class InfoDialog(BaseDialog):
    def __init__(
        self,
        instructions_path: str,
        parent=None,
        title=STR.APP_NAME,
        tool_key=ToolKey.UNTRACEABLE,
    ):
        super().__init__(parent)
        self.logger = LogUtils(
            tool=tool_key, class_name=self.__class__.__name__, level=LogUtils.DEBUG
        )
        self.logger.debug(
            f"Inicializando InfoDialog com arquivo: {instructions_path}"
        )

        # Use BaseDialog layout builder so dialogs share the same shell
        self._build_ui(
            title=title, enable_scroll=False, minimum_size=(700, 550)
        )

        # ── Text Browser com Markdown ──────────────────────────
        browser = TextBrowser(parent=self)

        if os.path.exists(instructions_path):
            with open(instructions_path, "r", encoding="utf-8") as f:
                md_text = f.read()

            # Renderização Markdown com fallback Qt5/Qt6
            browser.set_markdown(md_text)
        else:
            browser.setPlainText(
                f"{STR.FILE_NOT_FOUND}:\n{instructions_path}"
            )

        self.layout.addWidget(browser)

        # ── Botão Fechar ───────────────────────────────────────
        # GridExecutionButtons gerencia o botão fechar internamente
        self.action_buttons = GridExecutionButtons(
            config={},
            enable_close_button=True,
            enable_info=False,
            tool_key=tool_key,
            parent=self,
        )
        self.layout.add_execution_buttons(self.action_buttons)

        self.logger.debug(
            "InfoDialog UI construída com sucesso usando BaseDialog layout."
        )
```

### 6.2 Mudanças em Relação ao Original

| Aspecto | Antigo | Novo |
|---------|--------|------|
| Import WidgetFactory | `from ...core.ui.WidgetFactory import WidgetFactory` | ❌ Removido |
| Import TextBrowser | ❌ Não existia | `from ..resources.widgets.TextBrowser import TextBrowser` |
| Import GridExecutionButtons | ❌ Não existia | `from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons` |
| Criar browser | `WidgetFactory.create_text_browser(parent=self)` | `TextBrowser(parent=self)` |
| Renderizar markdown | `doc.setMarkdown(md_text)` ou `_markdown_to_html()` | `browser.set_markdown(md_text)` (encapsulado) |
| Criar botão fechar | `WidgetFactory.create_simple_button(text=STR.CLOSE, ...)` | `GridExecutionButtons(config={}, enable_close_button=True, ...)` |
| Conectar botão | `btn_widget.clicked.connect(self.close)` | Automático (GridExecutionButtons gerencia) |
| Adicionar ao layout | `self.layout.addLayout(btn_layout)` | `self.layout.add_execution_buttons(self.action_buttons)` |
| `_markdown_to_html()` | Método próprio | Movido para `TextBrowser._markdown_to_html()` |

### 6.3 Compatibilidade Retroativa

A API pública do `InfoDialog` **não muda**:
- `__init__(instructions_path, parent, title, tool_key)` — mesma assinatura
- Comportamento: abre diálogo com markdown + botão fechar — idêntico

---

## 7. FASE 2 — Atualizar Usuários do InfoDialog

### 7.1 Quem Usa InfoDialog?

Preciso verificar no código quem importa `InfoDialog` para garantir que a migração não quebre nada.

**Prováveis usuários:**
- `InstructionsManager` (resources/InstructionsManager.py) — exibe instruções .md
- `BaseProcessingAlgorithm` (processing/BaseProcessingAlgorithm.py) — exibe help
- Outros plugins que chamam `show_info_dialog()`

### 7.2 Checklist de Verificação

- [ ] Nenhum import quebra (assinatura do `__init__` não muda)
- [ ] Nenhum método público removido
- [ ] Comportamento visual idêntico
- [ ] ToolKey é passado corretamente

---

## 8. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| `_markdown_to_html()` removido e alguém usava | Baixa | Alto | Manter como método estático em TextBrowser |
| `setMarkdown` não disponível no Qt da instalação | Média | Alto | Fallback `_markdown_to_html()` dentro de `set_markdown()` |
| GridExecutionButtons sem `enable_info=False` exibir botão info | Média | Baixo | Passar `enable_info=False` explicitamente |
| Layout mudar (addLayout vs add_execution_buttons) | Baixa | Médio | Testar visualmente |
| Alguém chama `_markdown_to_html()` externamente | Baixa | Baixo | Método era privado (`_markdown_to_html`) |

---

## 9. TODO Consolidado

```
[ ] FASE 0: Criar TextBrowser
  [ ] 0.1 Adicionar AppStyles.text_browser() em resources/styles/AppStyles.py
  [ ] 0.2 Criar resources/widgets/TextBrowser.py (raiz, sem versão grid)

[ ] FASE 1: Migrar InfoDialog
  [ ] 1.1 Substituir imports da WidgetFactory por TextBrowser + GridExecutionButtons
  [ ] 1.2 Substituir create_text_browser() por TextBrowser()
  [ ] 1.3 Substituir create_simple_button() por GridExecutionButtons(enable_close_button=True)
  [ ] 1.4 Remover _markdown_to_html() (movido para TextBrowser)
  [ ] 1.5 Ajustar layout (addWidget + add_execution_buttons)
  [ ] 1.6 Remover import WidgetFactory

[ ] FASE 2: Verificar Usuários
  [ ] 2.1 Rastrear quem importa InfoDialog
  [ ] 2.2 Verificar compatibilidade (assinatura não muda)
  [ ] 2.3 Testar visualmente

[ ] Pós-migração
  [ ] 3.1 Atualizar docs/skills/SKILL_WIDGETS2.md (adicionar TextBrowser ao catálogo)
  [ ] 3.2 Atualizar docs/plano_eliminacao_widgetfactory.md (marcar InfoDialog como migrado)
  [ ] 3.3 Atualizar docs/ia/changelog.txt
```

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-24 | 1.0.0 | Criação inicial — Plano de migração do InfoDialog |
| 2026-07-24 | 1.1.0 | Corrigido: TextBrowser movido para raiz (sem versão grid). Removida referência a SimpleModernButton (GridExecutionButtons gerencia internamente). |