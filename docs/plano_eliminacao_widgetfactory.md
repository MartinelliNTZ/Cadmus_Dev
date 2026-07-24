# 🎯 PLANO DE AÇÃO: Eliminação da WidgetFactory

**Objetivo:** Eliminar completamente o uso da `WidgetFactory`, migrando para um modelo onde widgets se autoconfiguram com `AppStyles` + `ThemeManager` + `BaseTheme`, e plugins declaram widgets via parâmetros/dict sem saber de estilos.

**Data:** 2026-07-24
**Versão:** 5.1.0
**Autor:** Cadmus Engineering

---

## Sumário

1. [Arquitetura Atual](#1-arquitetura-atual)
2. [Arquitetura Alvo](#2-arquitetura-alvo)
3. [Estratégia de Migração Não-Destrutiva](#3-estratégia-de-migração-não-destrutiva)
4. [Organização e Hierarquia de Widgets](#4-organização-e-hierarquia-de-widgets)
5. [Contrato de Tokens e Unidades](#5-contrato-de-tokens-e-unidades)
6. [FASE 0 — Fundação ✅](#6-fase-0--fundação)
7. [FASE 1 — Criação dos Widgets](#7-fase-1--criação-dos-widgets)
8. [FASE 2 — Migração Plugin por Plugin](#8-fase-2--migração-plugin-por-plugin)
9. [FASE 3 — Eliminação da WidgetFactory](#9-fase-3--eliminação-da-widgetfactory)
10. [Contrato do Widget](#10-contrato-do-widget)
11. [Compatibilidade Qt5/Qt6](#11-compatibilidade-qt5qt6)
12. [Riscos e Mitigações](#12-riscos-e-mitigações)
13. [TODO Interno Consolidado](#13-todo-interno-consolidado)

---

## 1. Arquitetura Atual

### Diagrama de Dependências (Atual)

```
Plugin
  └─ importa WidgetFactory de core/ui/WidgetFactory.py
      └─ WidgetFactory.create_xxx(params)
          ├─ Cria widget (importa de resources/widgets/)
          ├─ Cria layout (QVBoxLayout)
          ├─ Aplica Styles.xxx() (importa de resources/styles/Styles.py)
          ├─ Adiciona separadores (top/bottom) via QFrame
          └─ Retorna (layout, widget)

Styles (resources/styles/Styles.py)
  └─ herda BaseStyles (resources/styles/BaseStyles.py)
      └─ current_theme = theme_manager.theme ← agora lê de ThemeManager

BaseStyles
  ├─ Atributos de classe: COLOR_PRIMARY, current_theme.COLOR_PRIMARY, etc.
  └─ Métodos estáticos: button(), label(), input(), checkbox()

BaseTheme (resources/styles/BaseTheme.py) — NOVO
  └─ 275 linhas com todos os tokens visuais — tema ÚNICO do sistema

ThemeManager
  └─ Mantém instância ÚNICA de BaseTheme (THEMES registra "base" como padrão)
```

### O que NÃO mudará (mantido como está)

| Arquivo | Motivo |
|---------|--------|
| `resources/styles/BaseStyles.py` | `current_theme = CoffeTheme()` — exclusivo do sistema antigo |
| `resources/styles/Styles.py` | Mantido para widgets antigos |
| `resources/styles/CoffeTheme.py` | Exclusivo do sistema antigo |
| `resources/widgets/` | Widgets antigos continuam funcionando |
| `core/ui/WidgetFactory.py` | Mantido durante migração |

### Problemas Identificados

| # | Problema | Impacto |
|---|----------|---------|
| 1 | `BaseStyles` copia tokens na importação | Se tema mudar, não atualiza |
| 2 | `Styles` + `BaseStyles` duplicados | Manutenção confusa |
| 3 | `WidgetFactory` 1135 linhas (viola SRP) | Difícil testar/manter |
| 4 | Plugin sabe de layout (recebe `(layout, widget)`) | Acoplamento |
| 5 | Unidades `px` espalhadas | Mudar tamanho exige N alterações |
| 6 | Widgets antigos não têm `_specific_style()` | Estilo misturado |

---

## 2. Arquitetura Alvo

### Diagrama de Dependências (Novo)

```
Plugin
  └─ importa widget de resources/new_widgets/
      └─ widget.__init__(params, parent)
          ├─ Autoconfiguração total
          ├─ AppStyles (estilos globais)
          ├─ ThemeManager → BaseTheme (cores, fontes, dimensões)
          └─ _specific_style() (estilo próprio do widget)

AppStyles (resources/styles/AppStyles.py)
  ├─ Lê de ThemeManager (com cache)
  ├─ Só métodos GLOBAIS: button(), label(), input(), checkbox()
  ├─ Nomes de tokens SEMPRE descritivos: {theme.INPUT_FIELD_MIN_HEIGHT}
  ├─ MÉTODOS MODERNOS: modern_button_primary(), modern_button_secondary(),
  │                    modern_button_round_icon(), modern_input_primary(),
  │                    modern_input_secondary()
  └─ SEM `px` — tokens já vêm do tema com unidade

ThemeManager
  └─ Mantém instância ÚNICA de BaseTheme (sem temas filhos por enquanto)
      └─ BaseTheme é o próprio tema — tem todos os tokens

BaseTheme (NOVO — resources/styles/BaseTheme.py)
  └─ Classe ÚNICA de tema: rgba() + todos os tokens visuais descritivos

Widgets (resources/new_widgets/)
  ├── widget comum → raiz (não tem versão grid)
  ├── simple/      → widget TEM versão grid (plugins usam grid)
  └── grid/        → versão grid do widget (plugins USAM esta)
```

---

## 3. Estratégia de Migração Não-Destrutiva

### ⚠️ REGRA FUNDAMENTAL: NÃO MODIFICAR ARQUIVOS EXISTENTES

```
resources/
  ├── styles/
  │   ├── BaseStyles.py   ← NÃO TOCAR (current_theme = CoffeTheme() — SISTEMA ANTIGO)
  │   ├── Styles.py        ← NÃO TOCAR (herda BaseStyles — SISTEMA ANTIGO)
  │   ├── CoffeTheme.py    ← NÃO TOCAR (tema antigo)
  │   ├── BaseTheme.py     ← FOI LIMPO — agora é o tema ÚNICO do NOVO sistema
  │   │                      (tem rgba() + todos os tokens visuais)
  │   ├── ThemeManager.py  ← ATUALIZAR — gerenciar o BaseTheme
  │   └── AppStyles.py     ← NOVO (lê de ThemeManager)
  │
  ├── widgets/             ← NÃO TOCAR (widgets antigos)
  │
  └── new_widgets/         ← NOVO SISTEMA
      ├── MainLayout.py           ← Layout principal (appbar + scroll + content)
      ├── AppBarWidget.py         ← Barra superior com título, botões, drag
      ├── ScrollWidget.py         ← QScrollArea com estilo
      ├── SeparatorWidget.py      ← QFrame HLine com gradiente
      ├── TextBrowser.py          ← QTextBrowser com set_markdown() e fallback Qt5/Qt6
      ├── simple/
      │   ├── SimpleLabel.py
      │   ├── SimpleButton.py
      │   ├── SimpleIconButton.py
      │   ├── SimpleModernButton.py   ← gradiente 3 stops + glow shadow
      │   ├── SimpleQLineEdit.py      ← gradiente 3 stops + glow shadow
      │   └── SimpleReadOnly.py       ← SimpleQLineEdit + botão copiar
      └── grid/
          ├── GridLabel.py
          ├── GridReadOnly.py
          ├── GridButton.py
          ├── GridExecutionButtons.py
          └── GridIconButton.py
```

### Regra de Ouro: Simple vs Grid vs Raiz

```
Se um widget TEM uma versão grid:
  └── A versão base vai para simple/   (ex: SimpleLabel)
  └── A versão com grid vai para grid/ (ex: GridLabel)
  └── Plugins usam SEMPRE grid/

Se um widget NÃO TEM versão grid:
  └── Fica na raiz de new_widgets/ (ex: MainLayout, SeparatorWidget)

Se um widget é COMPLEXO (simple + funções):
  └── É nomenclatura, não pasta
  └── Ex: ComplexPathSelector.py na raiz — tem título + path + botões
```

### Fluxo de Migração

```
1. BaseTheme + ThemeManager OK ✅
2. AppStyles criado ✅
3. Widgets criados (simple/grid/raiz) — PARCIAL
4. Plugins migrados 1 por vez — AboutDialog ✅, CoorResultDialog ✅, InfoDialog ✅
5. NUNCA deletar nada antigo
```

---

## 4. Organização e Hierarquia de Widgets

### 4.1 Regras de Organização — ESTADO ATUAL

```
new_widgets/                          ← NOVO SISTEMA (criado)
├── MainLayout.py                     ← Layout principal (appbar + scroll + content)
├── AppBarWidget.py                   ← Barra superior
├── ScrollWidget.py                   ← QScrollArea
├── SeparatorWidget.py                ← QFrame separador visual (gradiente horizontal)
├── TextBrowser.py                    ← QTextBrowser com set_markdown() e fallback Qt5/Qt6
│
├── simple/                           ← USO INTERNO (NUNCA importado por plugins)
│   ├── SimpleLabel.py                ← QLabel + AppStyles.label()
│   ├── SimpleButton.py               ← QPushButton + AppStyles.button()
│   ├── SimpleIconButton.py           ← QPushButton + ícone + transparente
│   ├── SimpleModernButton.py         ← QPushButton glow/gradiente (primary/secondary/round_icon)
│   ├── SimpleQLineEdit.py            ← QLineEdit glow/gradiente (primary/secondary)
│   └── SimpleReadOnly.py             ← SimpleQLineEdit + botão copiar SimpleModernButton
│
└── grid/                             ← PLUGINS USAM ESTES
    ├── GridLabel.py                  ← Container de labels (dict config)
    ├── GridReadOnly.py               ← Container de SimpleReadOnly (dict config + botões copiar)
    ├── GridButton.py                 ← Container simples de botões (Fechar/Executar/Info) — LEGADO
    ├── GridExecutionButtons.py       ← Container de botões modernos (SimpleModernButton)
    └── GridIconButton.py             ← Container de botões com ícone (SimpleIconButton)
```

### 4.2 CATÁLOGO COMPLETO — Definição de Cada Widget

#### Widgets Simple (USO INTERNO APENAS — plugins NUNCA importam)

| Arquivo | Classe | Base | Estilo Global | Descrição |
|---------|--------|------|---------------|-----------|
| `SimpleLabel.py` | `SimpleLabel` | QLabel | `AppStyles.label()` | Label com texto estilizado |
| `SimpleButton.py` | `SimpleButton` | QPushButton | `AppStyles.button()` | Botão padrão com gradiente primary |
| `SimpleIconButton.py` | `SimpleIconButton` | QPushButton | `AppStyles.button()` + `_specific_style()` transparente | Botão com ícone, tamanho configurável |
| `SimpleModernButton.py` | `SimpleModernButton` | QPushButton | `AppStyles.modern_button_primary/secondary/round_icon()` | Botão **sem borda**, gradiente 3 stops + glow shadow (`QGraphicsDropShadowEffect`). Primary/secondary/round_icon. Tokens: `BUTTON_MIN_HEIGHT`, `BUTTON_ROUND_ICON_SIZE`, `BUTTON_PADDING`, `BUTTON_FONT_SIZE`, `BUTTON_FONT_WEIGHT`, `BUTTON_SHADOW_BLUR_*`, `BUTTON_SHADOW_OFFSET_*`, `COLOR_GLOW_*` |
| `SimpleQLineEdit.py` | `SimpleQLineEdit` | QLineEdit | `AppStyles.modern_input_primary/secondary()` | Input **sem borda**, gradiente 3 stops + glow shadow. Sombra expande no foco (focusInEvent) e recolhe (focusOutEvent). Tokens: `INPUT_FIELD_*`, `INPUT_SHADOW_*` |
| `SimpleReadOnly.py` | `SimpleReadOnly` | QWidget | Composto: `SimpleQLineEdit` + `SimpleModernButton` (ícone COPY2) | Campo readonly com botão copiar opcional. API: `setText()`, `text()`, `setPlaceholderText()` |

#### Widgets Grid (PLUGINS USAM ESTES)

| Arquivo | Classe | Descrição | Parâmetros principais |
|---------|--------|-----------|----------------------|
| `GridLabel.py` | `GridLabel` | Container de labels em layout vertical. Configuração via dict. | `config={"key": {"text": "<h2>Título</h2>"}}` |
| `GridReadOnly.py` | `GridReadOnly` | Container com título + campos readonly (`SimpleReadOnly`). Botão copiar individual. | `title`, `fields={"key": {"title": ..., "value": ...}}`, `show_copy_buttons`, `separator_top/bottom` |
| `GridButton.py` | `GridButton` | **LEGADO** — container simples com botões Fechar/Executar/Info. Use `GridExecutionButtons` preferencialmente. | `run_callback`, `close_callback`, `info_callback` |
| `GridExecutionButtons.py` | `GridExecutionButtons` | Container de botões modernos (`SimpleModernButton`). Configuração via dict. | `config={"key": {"label": ..., "callback": ..., "is_run_button": True}}`, `enable_close_button`, `enable_info`, `enable_config_button`, `tool_key` |
| `GridIconButton.py` | `GridIconButton` | Container de botões com ícone (`SimpleIconButton`). Configuração via dict. | `config={"key": {"label": ..., "icon": ..., "callback": ..., "description": ...}}` |

#### Widgets Raiz (SEM versão grid)

| Arquivo | Classe | Descrição |
|---------|--------|-----------|
| `MainLayout.py` | `MainLayout` | Layout principal dos diálogos. Substitui o antigo `BaseLayout`. Cria `AppBarWidget` e `ScrollWidget` internamente. Métodos: `addWidget()`, `addLayout()`, `add_execution_buttons()`, `add_items()`, `set_appbar_title()` |
| `AppBarWidget.py` | `AppBarWidget` | Barra superior com título, botões (run/info/close/close) e drag |
| `ScrollWidget.py` | `ScrollWidget` | QScrollArea com estilo `AppStyles.scroll_area()` |
| `SeparatorWidget.py` | `SeparatorWidget` | QFrame HLine com gradiente horizontal. É um widget Qt separado, NÃO margem/padding |
| `TextBrowser.py` | `TextBrowser` | QTextBrowser com `AppStyles.text_browser()`, sem borda, fundo transparente. Renderização Markdown nativa com fallback Qt5/Qt6. API: `set_markdown()`, `setHtml()`, `setPlainText()`, `document()` |

### 4.3 Quando Usar Cada Um

```
PLUGIN:
  ├── Grid (PRIORIDADE) → se widget tem versão grid
  ├── Raiz → se widget NÃO tem versão grid
  └── NUNCA Simple → simple é uso INTERNO de outros widgets

WIDGET INTERNO:
  ├── Simple → para construir Grid e widgets da raiz
  └── Grid → para construir widgets compostos
```

### 4.4 Separadores Widgets Separados (NÃO São Margens)

**SEPARADOR é um QFrame visual**, não padding/margem.  
O widget `SeparatorWidget` é um QFrame com estilo de gradiente horizontal.

```python
# resources/new_widgets/SeparatorWidget.py
class SeparatorWidget(QFrame):
    """
    Separador visual — QFrame com gradiente horizontal.
    
    Parâmetros
    ----------
    height : str, optional
        Altura do separador (default: usa theme.SEPARATOR_LINE_HEIGHT)
    """

    def __init__(self, height: str = None, parent=None):
        super().__init__(parent)
        theme = AppStyles._get_theme()
        
        # Compatibilidade Qt5/Qt6 para QFrame.Shape
        try:
            shape = QFrame.Shape.HLine
        except AttributeError:
            shape = QFrame.HLine
        
        try:
            shadow = QFrame.Shadow.Sunken
        except AttributeError:
            shadow = QFrame.Sunken
        
        self.setFrameShape(shape)
        self.setFrameShadow(shadow)
        
        h = height or theme.SEPARATOR_LINE_HEIGHT
        h_int = int(h.replace("px", ""))
        self.setFixedHeight(h_int)
        self.setStyleSheet(AppStyles.separator())
```

**Plugins adicionam separadores entre widgets:**

```python
# NO LAYOUT do plugin:
self.layout.addWidget(self.layer_input)
self.layout.addWidget(SeparatorWidget())        # separador entre widgets
self.layout.addWidget(self.dropdown_selector)
self.layout.addWidget(SeparatorWidget())
self.layout.addWidget(self.action_buttons)
```

**Widgets NÃO têm `separator_top/bottom/left/right` como parâmetros.**  
Separador é um widget separado que o plugin insere entre os widgets.

---

## 5. Contrato de Tokens e Unidades

### 5.1 🚫 NUNCA Colocar `px` no Widget ou AppStyles

**ERRADO:**
```python
# ❌ UNIDADE FIXA — NÃO FAZER
min-height: {theme.INPUT_FIELD_MIN_HEIGHT}px;
border: 1px solid {theme.COLOR_BORDER};
```

**CERTO:**
```python
# ✅ UNIDADE SEMPRE NO TEMA
# No tema:  INPUT_FIELD_MIN_HEIGHT = "4px"
# No estilo: min-height: {theme.INPUT_FIELD_MIN_HEIGHT};

# No tema:  PXBORDER_ONE = "1px solid"
# No estilo: border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
```

### 5.2 NUNCA Usar `t` — Use `theme`

```python
# ❌ AMBÍGUO — NÃO FAZER
t = cls._get_theme()
min-height: {t.INPUT_FIELD_MIN_HEIGHT};

# ✅ DESCRITIVO — FAZER
theme = cls._get_theme()
min-height: {theme.INPUT_FIELD_MIN_HEIGHT};
```

### 5.3 Nomes de Tokens DESCRITIVOS (sem medo de tamanho)

```python
class BaseTheme:
    # ❌ AMBÍGUO
    INPUT_HEIGHT: str = "4px"
    BUTTON_BG: str = "#333"
    
    # ✅ DESCRITIVO (pode ser grande, mas nunca ambíguo)
    INPUT_FIELD_MIN_HEIGHT: str = "4px"
    BUTTON_DEFAULT_BACKGROUND_COLOR: str = "#333"
    BUTTON_HOVER_BACKGROUND_COLOR: str = "#555"
    BUTTON_DISABLED_BACKGROUND_COLOR: str = "#222"
    COLLAPSIBLE_HEADER_BUTTON_BACKGROUND: str = "transparent"
    COLLAPSIBLE_HEADER_BUTTON_BORDER: str = "none"
    APP_BAR_TITLE_FONT_WEIGHT: str = "bold"
    SEPARATOR_LINE_HEIGHT: str = "3px"
    SEPARATOR_LINE_MARGIN: str = "4px 0px"
```

### 5.4 Onde Cada Token Fica

```
TEMA (BaseTheme):
  INPUT_FIELD_MIN_HEIGHT: str = "4px"          ← unidade AQUI
  INPUT_FIELD_PADDING: str = "4px 10px"        ← unidade AQUI
  INPUT_FIELD_FONT_SIZE: str = "11px"          ← unidade AQUI
  INPUT_FIELD_FONT_WEIGHT: str = "500"         ← unidade AQUI
  BUTTON_DEFAULT_MIN_HEIGHT: str = "4px"       ← unidade AQUI
  BUTTON_MIN_HEIGHT: str = "30px"              ← unidades modernos
  BUTTON_ROUND_ICON_SIZE: str = "30px"         ← unidade AQUI
  BUTTON_PADDING: str = "7px 22px"             ← unidade AQUI
  BUTTON_FONT_SIZE: str = "12px"               ← unidade AQUI
  BUTTON_FONT_WEIGHT: str = "600"              ← unidade AQUI
  BUTTON_SHADOW_BLUR_NORMAL: int = 12          ← sem unidade
  BUTTON_SHADOW_BLUR_PRESSED: int = 4          ← sem unidade
  BUTTON_SHADOW_OFFSET_NORMAL: int = 3         ← sem unidade
  BUTTON_SHADOW_OFFSET_PRESSED: int = 1        ← sem unidade
  INPUT_SHADOW_BLUR_NORMAL: int = 8            ← sem unidade
  INPUT_SHADOW_BLUR_FOCUSED: int = 12          ← sem unidade
  INPUT_SHADOW_OFFSET_NORMAL: int = 2          ← sem unidade
  INPUT_SHADOW_OFFSET_FOCUSED: int = 2         ← sem unidade
  PXBORDER_ONE: str = "1px solid"              ← tudo AQUI
  PADDING_INPUT_FIELD: str = "2px 8px"         ← unidade AQUI
  BORDER_RADIUS_INPUT_FIELD: str = "4px"       ← unidade AQUI
  SEPARATOR_LINE_HEIGHT: str = "3px"           ← unidade AQUI
  SEPARATOR_LINE_MARGIN: str = "4px 0px"       ← unidade AQUI
  COLLAPSIBLE_HEADER_BUTTON_BACKGROUND: str = "transparent"  ← valor direto
  COLLAPSIBLE_HEADER_BUTTON_BORDER: str = "none"              ← valor direto

  # Flags booleanas
  ALLOW_COMPONENT_SHADOW: bool = True
  ALLOW_COMPONENT_GLOW: bool = False
  
  # Propriedades computadas
  @property
  def BOX_SHADOW_COMPONENT(self) -> str:
      """Sombra padrão para componentes (ex: painéis)."""
      if self.ALLOW_COMPONENT_SHADOW:
          return "0px 0px 4px rgba(0,0,0,0.3)"
      return "none"

AppStyles / Widget:
  min-height: {theme.INPUT_FIELD_MIN_HEIGHT};     ← sem px
  border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
  padding: {theme.PADDING_INPUT_FIELD};
  border-radius: {theme.BORDER_RADIUS_INPUT_FIELD};
  background: {theme.COLLAPSIBLE_HEADER_BUTTON_BACKGROUND};
  border: {theme.COLLAPSIBLE_HEADER_BUTTON_BORDER};
```

### 5.5 `_specific_style()` Padronizado

TODO widget DEVE ter:

```python
def _specific_style(self) -> str:
    """
    Estilo específico deste widget.
    Usa tokens do tema com nomes descritivos.
    SOBRESCREVER em subclasses se necessário.
    """
    return ""
```

---

## 6. FASE 0 — Fundação ✅

### 6.1 Status: ✅ COMPLETA

| Item | Status | Descrição |
|------|--------|-----------|
| 0.1 BaseTheme limpo | ✅ | `BaseTheme.py` com `rgba()` e todos os tokens visuais |
| 0.2 Adicionar tokens descritivos | ✅ | 275 linhas com `rgba()` + tokens completos (INPUT_FIELD_PADDING, BUTTON_SHADOW_*, INPUT_SHADOW_*, etc.) |
| 0.3 ThemeManager atualizado | ✅ | Singleton, registro THEMES, preferência "theme" do System, _sync_attributes |
| 0.4 AppStyles criado | ✅ | Métodos globais + modernos: `modern_button_primary()`, `modern_button_secondary()`, `modern_button_round_icon()`, `modern_input_primary()`, `modern_input_secondary()` |
| 0.5 utils/qt_compat.py criado | ✅ | Helpers: `resolve_qt_enum()`, `resolve_qframe_shape()`, `resolve_qt_window_modality()` |
| 0.6 Testado | ✅ | Changelog 2.3.62.1 confirma |

### 6.2 Registrado no Changelog

```
2.3.62.1[21/07/2026] FASE 0 — Fundação do novo sistema de widgets autoconfiguráveis:
   - Adicionados tokens descritivos em BaseTheme.py
   - Criado resources/styles/AppStyles.py
   - Criado utils/qt_compat.py
   - Adicionado BaseTheme como tema registrado no ThemeManager (chave "base")
   - Criado docs/skills/SKILL_WIDGETS2.md e docs/plano_acao_aboutdialog.md
```

---

## 7. FASE 1 — Criação dos Widgets

### 7.1 Widgets Simple (USO INTERNO APENAS) — PARCIAL

Criados em `resources/new_widgets/simple/`. Estes widgets TEM versão grid.  
**NUNCA** importados por plugins. Usados APENAS internamente por Grid e widgets da raiz.

| Arquivo | Classe | Status | Observação |
|---------|--------|--------|-----------|
| `SimpleLabel.py` | `SimpleLabel` | ✅ | QLabel + AppStyles.label() |
| `SimpleButton.py` | `SimpleButton` | ✅ | QPushButton + AppStyles.button() |
| `SimpleIconButton.py` | `SimpleIconButton` | ✅ | QPushButton + ícone + `_specific_style()` transparente |
| `SimpleModernButton.py` | `SimpleModernButton` | ✅ | **NOVO** — QPushButton gradiente 3 stops + glow shadow. Usado por `GridExecutionButtons`. Tokens: `BUTTON_*`, `COLOR_GLOW_*` |
| `SimpleQLineEdit.py` | `SimpleQLineEdit` | ✅ | **NOVO** — QLineEdit gradiente 3 stops + glow shadow. Usado por `SimpleReadOnly`. Tokens: `INPUT_*` |
| `SimpleReadOnly.py` | `SimpleReadOnly` | ✅ | Composto: `SimpleQLineEdit` + `SimpleModernButton` (ícone COPY2). API: `setText()`, `text()`, `setPlaceholderText()` 

### 7.2 Widgets Grid (PLUGINS USAM ESTES) — PARCIAL

Criados em `resources/new_widgets/grid/`. Compostos de Simple + layout.

| Arquivo | Classe | Status | Descrição |
|---------|--------|--------|-----------|
| `GridLabel.py` | `GridLabel` | ✅ | Container de labels (dict config). Métodos: `set_text()`, `get_text()`, `set_config()` |
| `GridReadOnly.py` | `GridReadOnly` | ✅ | Container com título + campos `SimpleReadOnly`. Botão copiar individual. API: `set_value()`, `get_value()`. Parâmetros: `title`, `fields`, `show_copy_buttons`, `separator_top/bottom` |
| `GridButton.py` | `GridButton` | ✅ | **LEGADO** — container de botões Fechar/Executar/Info. Use `GridExecutionButtons` para novos plugins |
| `GridExecutionButtons.py` | `GridExecutionButtons` | ✅ | **NOVO** — Container de botões modernos (`SimpleModernButton`). Configuração via dict. Parâmetros: `config`, `enable_close_button`, `enable_info`, `enable_config_button`, `tool_key` |
| `GridIconButton.py` | `GridIconButton` | ✅ | **NOVO** — Container de botões com ícone (`SimpleIconButton`). Configuração via dict com callback por item 

### 7.3 Widgets na Raiz (SEM versão grid) — PARCIAL

Criados em `resources/new_widgets/`.

| Arquivo | Classe | Status | Descrição |
|---------|--------|--------|-----------|
| `MainLayout.py` | `MainLayout` | ✅ | **NOVO** — Layout principal. Substitui BaseLayout. Cria AppBarWidget + ScrollWidget internamente. Métodos: `addWidget()`, `addLayout()`, `add_execution_buttons()`, `add_items()`, `set_appbar_title()` |
| `AppBarWidget.py` | `AppBarWidget` | ✅ | Barra superior com título, botões (run/info/close) e drag |
| `ScrollWidget.py` | `ScrollWidget` | ✅ | QScrollArea com estilo `AppStyles.scroll_area()` |
| `SeparatorWidget.py` | `SeparatorWidget` | ✅ | QFrame HLine com gradiente horizontal. `height` opcional |
| `TextBrowser.py` | `TextBrowser` | ✅ | QTextBrowser com `AppStyles.text_browser()`, sem borda, fundo transparente. Renderização Markdown nativa com fallback Qt5/Qt6. API: `set_markdown()`, `setHtml()`, `setPlainText()`, `document()` |


---

## 8. FASE 2 — Migração Plugin por Plugin

### 8.1 Ordem e Status

| # | Plugin | Factory (antigo) | new_widgets (novo) | Status |
|---|--------|-----------------|-------------------|--------|
| 1 | `AboutDialog` | create_label, create_text_browser, create_image_widget | GridLabel + GridExecutionButtons + GridIconButton | ✅ Migrado (2.3.62.2) |
| 2 | `CoorResultDialog` | create_label, create_readonly_field, create_bottom_action_buttons | GridReadOnly + GridLabel + GridExecutionButtons + SimpleLabel | ✅ Migrado (2.3.63.3) |
| 3 | `InfoDialog` | create_text_browser, create_simple_button | TextBrowser + GridExecutionButtons | ✅ Migrado (2.3.64.1) |
| 4 | `RestartQgis` | create_simple_button | GridButton | ⬜ Pendente |
| 5 | `VectorMultipartPlugin` | create_layer_input, create_bottom_action_buttons | GridLayerInput + GridButton | ⬜ Pendente |
| 6 | `ExportAllLayouts` | create_readonly_field, create_bottom_action_buttons | GridReadOnly + GridButton | ⬜ Pendente |
| 7 | `CopyAttributesPlugin` | create_layer_input, create_checkbox_grid, create_bottom_action_buttons | GridLayerInput + GridCheckbox + GridButton | ⬜ Pendente |
| 8 | `DividePointsByStripsPlugin` | create_layer_input, create_input_fields, create_bottom_action_buttons | GridLayerInput + GridInput + GridButton | ⬜ Pendente |
| 9 | `DroneCoordinates` | create_label, create_double_spin_input | GridInput | ⬜ Pendente |
| 10 | `LoadFolderLayers` | create_path_selector, create_checkbox_grid, create_bottom_action_buttons | ComplexPathSelector + GridCheckbox + GridButton | ⬜ Pendente |
| 11 | `PathExtensionPlugin` | create_layer_input, create_dropdown_selector, create_radio_button_grid, create_bottom_action_buttons | GridLayerInput + GridDropdown + GridRadioButton + GridButton | ⬜ Pendente |
| 12 | `ReplaceInLayouts` | create_layer_input, create_dropdown_selector, create_bottom_action_buttons | GridLayerInput + GridDropdown + GridButton | ⬜ Pendente |
| 13 | `SaveTemporaryLayersPlugin` | create_path_selector, create_layer_input, create_bottom_action_buttons | ComplexPathSelector + GridLayerInput + GridButton | ⬜ Pendente |
| 14 | `GenerateTrailPlugin` | create_layer_input, create_dropdown_selector, create_input_fields, create_color_button, create_bottom_action_buttons | GridLayerInput + GridDropdown + GridInput + ComplexColorPicker + GridButton | ⬜ Pendente |
| 15 | `ReportMetadataPlugin` | create_path_selector, create_layer_input, create_checkbox_grid, create_bottom_action_buttons | ComplexPathSelector + GridLayerInput + GridCheckbox + GridButton | ⬜ Pendente |
| 16 | `VectorFieldsCalculationPlugin` | create_layer_input, create_dropdown_selector, create_input_fields, create_bottom_action_buttons | GridLayerInput + GridDropdown + GridInput + GridButton | ⬜ Pendente |
| 17 | `VectorToSvgPlugin` | create_path_selector, create_layer_input, create_checkbox_grid, create_bottom_action_buttons | ComplexPathSelector + GridLayerInput + GridCheckbox + GridButton | ⬜ Pendente |
| 18 | `SettingsPlugin` | Múltiplos | Análise individual | ⬜ Pendente |

### 8.2 Checklist por Plugin

```markdown
## Plugin: [NOME]

### Análise
- [ ] Quais widgets usa via Factory?
- [ ] Pode usar Grid? (sim, prioridade)
- [ ] Obedece contrato PLUGIN_CONTRACT.md?
- [ ] TEM LOGGER? (sim, herda de BasePluginMTL)

### Migração
- [ ] Substituir WidgetFactory.create_xxx() por widget de new_widgets/
- [ ] Remover imports da Factory
- [ ] Adicionar SeparatorWidget() entre widgets no layout
- [ ] Ajustar layout (addWidget)

### Pós-migração
- [ ] Plugin não importa de core/ui/WidgetFactory
- [ ] Plugin não importa de resources/styles/
- [ ] Plugin não chama setStyleSheet()
- [ ] Atualizar docs/ia/changelog.txt
```

### 8.3 Exemplo: CoorResultDialog (MIGRADO ✅)

```python
# plugins/CoorResultDialog.py

from ..resources.new_widgets.grid.GridReadOnly import GridReadOnly
from ..resources.new_widgets.grid.GridLabel import GridLabel
from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.new_widgets.simple.SimpleLabel import SimpleLabel


class CoordResultDialog(BasePluginMTL):
    TOOL_KEY = ToolKey.COORD_CLICK_TOOL

    def _build_ui(self, **kwargs):
        super()._build_ui(
            title=STR.POINT_COORDINATES,
            icon_path="mtl_agro.ico",
            enable_scroll=True,
        )

        # ── WGS84 ReadOnly ────────────────────────────────────
        self.wgs_widget = GridReadOnly(
            title=STR.WGS84_EPSG4326,
            fields={
                "lat_dec": {"title": STR.LATITUDE_DECIMAL, "value": ""},
                "lon_dec": {"title": STR.LONGITUDE_DECIMAL, "value": ""},
                "lat_dms": {"title": STR.LATITUDE_DMS, "value": ""},
                "lon_dms": {"title": STR.LONGITUDE_DMS, "value": ""},
            },
            show_copy_buttons=True,
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self.wgs_widget)

        # ── UTM ReadOnly ─────────────────────────────────────
        self.utm_widget = GridReadOnly(
            title=STR.UTM_SIRGAS_2000,
            fields={
                "utm_x": {"title": STR.EASTING_X, "value": ""},
                "utm_y": {"title": STR.NORTHING_Y, "value": ""},
            },
            show_copy_buttons=True,
            parent=self,
        )
        self.layout.addWidget(self.utm_widget)

        # ── UTM Info Label ────────────────────────────────────
        self.lbl_utm_info = SimpleLabel(text="", parent=self)
        self.layout.addWidget(self.lbl_utm_info)

        # ── Altimetria ReadOnly ──────────────────────────────
        self.alt_widget = GridReadOnly(
            title=STR.ALTIMETRY_OPENTOPO,
            fields={
                "altitude": {
                    "title": STR.APPROX_ALTITUDE_METERS,
                    "value": STR.LOADING,
                }
            },
            show_copy_buttons=True,
            separator_top=True,
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self.alt_widget)

        # ── Labels de Endereço ────────────────────────────────
        self.address_labels = GridLabel(config={
            "municipio": {"text": f"{STR.CITY}: {STR.LOADING_LOWER}"},
            "state_district": {"text": f"{STR.INTERMEDIATE_REGION}: {STR.LOADING_LOWER}"},
            "state": {"text": f"{STR.STATE}: {STR.LOADING_LOWER}"},
            "region": {"text": f"{STR.REGION}: {STR.LOADING_LOWER}"},
            "country": {"text": f"{STR.COUNTRY}: {STR.LOADING_LOWER}"},
        }, separator_bottom=True, parent=self)
        self.layout.addWidget(self.address_labels)

        # ── Botões de Ação (Copiar Tudo + Fechar + Info) ─────
        self.action_buttons = GridExecutionButtons(
            config={
                "copy_all": {
                    "label": STR.COPY_LOCATION_FULL,
                    "description": "Copia todas as coordenadas e endereço",
                    "callback": self.copy_all_info,
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

### 8.4 Exemplo: AboutDialog (MIGRADO ✅)

```python
# plugins/AboutDialog.py

from ..resources.new_widgets.grid.GridLabel import GridLabel
from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.new_widgets.grid.GridIconButton import GridIconButton


class AboutDialog(BaseDialog):
    def __init__(self, iface):
        self.iface = iface
        try:
            super().__init__(iface.mainWindow())
            self._build_ui(
                title=STR.ABOUT_CADMUS, enable_scroll=False, minimum_size=(420, 520)
            )

            # Labels via GridLabel com config dict
            self.grid_info = GridLabel(config={
                "app_name": {"text": f"<h2>{STR.APP_NAME}</h2>"},
                "info": {"text": info_text},
            }, parent=self)
            self.layout.addWidget(self.grid_info)

            # Social icons via GridIconButton — cada item tem seu próprio callback
            self.social_buttons = GridIconButton(
                config={
                    "github": {
                        "label": "GitHub",
                        "icon": IconManager.GITHUB,
                        "callback": lambda: webbrowser.open("https://github.com/MartinelliNTZ"),
                        "description": "Visite o GitHub de Matheus Martinelli",
                    },
                    # ... mais itens
                },
                parent=self,
            )
            self.layout.addWidget(self.social_buttons)

            # Botões de ação via GridExecutionButtons
            self.action_buttons = GridExecutionButtons(
                config={
                    "run": {
                        "label": "Executar",
                        "description": "Botão executar principal",
                        "callback": lambda: None,
                        "is_run_button": True,
                    },
                },
                enable_close_button=True,
                enable_info=True,
                enable_config_button=True,
                tool_key=ToolKey.ABOUT_DIALOG,
                parent=self,
            )
            self.layout.add_execution_buttons(self.action_buttons)
```

---

## 9. FASE 3 — Eliminação da WidgetFactory

### 9.1 Após TODOS os plugins migrados

```python
# core/ui/WidgetFactory.py — DEPRECATED
import warnings
warnings.warn(
    "WidgetFactory obsoleto. Use widgets de resources/new_widgets/. "
    "Consulte docs/plano_eliminacao_widgetfactory.md",
    DeprecationWarning, stacklevel=2,
)
```

### 9.2 Após 1 release

- Deletar `core/ui/WidgetFactory.py`
- Remover imports da Factory de todos os plugins
- Atualizar SKILL_WIDGETS2.md
- Atualizar PLUGIN_CONTRACT.md regra #1
- Atualizar docs/ia/changelog.txt

### 9.3 O que NUNCA será removido

- `resources/widgets/` (antigos — compatibilidade)
- `resources/styles/Styles.py` (antigo)
- `resources/styles/BaseStyles.py` (antigo)
- `resources/styles/CoffeTheme.py` (antigo)

---

## 10. Contrato do Widget

### 10.1 Regras Obrigatórias

1. **Herda de `QWidget`** (ou `QDialog`)
2. **`self.logger`** no `__init__`
3. **`try`** com `self.logger.exception(error, code=...)`
4. **`self._apply_styles()`** no final do `__init__`
5. **Estilos globais** → `AppStyles`
6. **Estilo específico** → `_specific_style()`
7. **Plugin NUNCA** chama `setStyleSheet()`
8. **Plugin NUNCA** importa `AppStyles` ou `ThemeManager`
9. **Separadores** são widgets separados (`SeparatorWidget`), não margens
10. **Unidades** sempre no tema, nunca `px` no estilo
11. **Variável do tema** sempre `theme`, nunca `t`
12. **Nomes de tokens** sempre descritivos (ex: `INPUT_FIELD_MIN_HEIGHT`)
13. **Regra ABSOLUTA:** Configuração via dict `config={}` com chaves identificadoras
14. **Callbacks:** Widget não expõe sinais Qt — plugin passa funções callback
15. **Botão com gradiente/glow:** Use `SimpleModernButton` (nunca `QPushButton` cru)
16. **Input com gradiente/glow:** Use `SimpleQLineEdit` (nunca `QLineEdit` cru)
17. **`add_execution_buttons` SEM stretch se scroll estiver habilitado**

---

## 11. Compatibilidade Qt5/Qt6

### 11.1 Helper de Compatibilidade

```python
# utils/qt_compat.py
"""Helpers de compatibilidade Qt5/Qt6 para widgets."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QFrame


def resolve_qt_enum(module, qt5_attribute_name: str, qt6_class_name: str, qt6_attribute_name: str):
    """Resolve enum Qt5 → Qt6 via try/except."""
    try:
        return getattr(getattr(module, qt6_class_name), qt6_attribute_name)
    except AttributeError:
        return getattr(module, qt5_attribute_name)


def resolve_qt_window_type(name: str):
    """Qt.WindowType.Dialog → Qt.Dialog"""
    return resolve_qt_enum(Qt, name, "WindowType", name)


def resolve_qt_widget_attribute(name: str):
    """Qt.WidgetAttribute.WA_TranslucentBackground → Qt.WA_TranslucentBackground"""
    return resolve_qt_enum(Qt, name, "WidgetAttribute", name)


def resolve_qt_alignment_flag(name: str):
    """Qt.AlignmentFlag.AlignLeft → Qt.AlignLeft"""
    return resolve_qt_enum(Qt, name, "AlignmentFlag", name)


def resolve_qframe_shape(name: str):
    """QFrame.Shape.HLine → QFrame.HLine"""
    try:
        return getattr(QFrame.Shape, name)
    except AttributeError:
        return getattr(QFrame, name)


def resolve_qframe_shadow(name: str):
    """QFrame.Shadow.Sunken → QFrame.Sunken"""
    try:
        return getattr(QFrame.Shadow, name)
    except AttributeError:
        return getattr(QFrame, name)

def resolve_qt_window_modality(name: str):
    """Qt.WindowModality.WindowModal → Qt.WindowModal"""
    try:
        return getattr(Qt.WindowModality, name)
    except AttributeError:
        return getattr(Qt, name)
```

### 11.2 Onde Aplicar

- `new_widgets/` — todos os widgets
- `AppStyles` — seguro (só strings CSS)
- `SeparatorWidget` — precisa de compat QFrame.Shape e QFrame.Shadow
- `BaseDialog.py` — já tem compat via `_qt_window_type()` e `_qt_widget_attr()`

---

## 12. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Quebrar Qt5/Qt6 | Média | Alto | Helper `resolve_qt_enum()` em todos os widgets |
| Plugin quebrar durante migração | Alta | Alto | Migrar 1 por vez; antigo continua |
| Perder estilos específicos | Média | Médio | Mover para `_specific_style()` |
| Tema mudar em runtime | Baixa | Médio | AppStyles com cache + `reload_theme()` |
| Widget sem `_apply_styles()` | Média | Médio | Template obrigatório |
| Unidade hardcoded no widget | Alta | Alto | Template proíbe |
| Widget antigo quebrar | Baixa | Baixo | Widgets antigos usam Styles.py |
| Plugin esquecer SeparatorWidget | Baixa | Baixo | Separadores são opcionais |

---

## 13. TODO Interno Consolidado

```
[ ] FASE 0: Fundação ✅
  [x] 0.1 BaseTheme limpo
  [x] 0.2 Adicionar tokens descritivos no BaseTheme.py
  [x] 0.3 Atualizar ThemeManager.py (singleton + registro THEMES + preferências)
  [x] 0.4 Criar resources/styles/AppStyles.py
  [x] 0.5 Criar utils/qt_compat.py
  [x] 0.6 Testar AppStyles + ThemeManager + BaseTheme

[ ] FASE 1: Criação dos Widgets — PARCIAL
  [ ] 1.1 Simple (USO INTERNO)
    [x] SimpleLabel.py
    [x] SimpleButton.py
    [x] SimpleIconButton.py
    [x] SimpleModernButton.py ← NOVO (gradiente 3 stops + glow shadow)
    [x] SimpleQLineEdit.py ← NOVO (gradiente 3 stops + glow shadow)
    [x] SimpleReadOnly.py
    [ ] SimpleComboBox.py
    [ ] SimpleSpinBox.py
    [ ] SimpleCheckbox.py
    [ ] SimpleRadioButton.py
    [ ] SimpleLayerInput.py
    [ ] SimpleDropdown.py
  [ ] 1.2 Grid (PLUGINS USAM)
    [x] GridLabel.py
    [x] GridReadOnly.py
    [x] GridButton.py
    [x] GridExecutionButtons.py ← NOVO (SimpleModernButton + dict config)
    [x] GridIconButton.py ← NOVO (SimpleIconButton + dict config + callback por item)
    [ ] GridInput.py
    [ ] GridCheckbox.py
    [ ] GridRadioButton.py
    [ ] GridLayerInput.py
    [ ] GridDropdown.py
  [ ] 1.3 Raiz (SEM versão grid)
    [x] MainLayout.py ← NOVO (substitui BaseLayout)
    [x] AppBarWidget.py
    [x] ScrollWidget.py
    [x] SeparatorWidget.py
    [x] TextBrowser.py ← NOVO (QTextBrowser com set_markdown + fallback Qt5/Qt6)
    [ ] CollapsibleParametersWidget.py
    [ ] ComplexPathSelector.py
    [ ] ComplexColorPicker.py
    [ ] ComplexCrsSelector.py
    [ ] GridComplexSelector.py

[ ] FASE 2: Migração Plugin por Plugin — PARCIAL
  [x] 2.1 AboutDialog ✅ (2.3.62.2)
  [x] 2.2 CoorResultDialog ✅ (2.3.63.3)
  [x] 2.3 InfoDialog ✅ (2.3.64.1)
  [ ] 2.4 RestartQgis
  [ ] 2.5 VectorMultipartPlugin
  [ ] 2.6 ExportAllLayouts
  [ ] 2.7 CopyAttributesPlugin
  [ ] 2.8 DividePointsByStripsPlugin
  [ ] 2.9 DroneCoordinates
  [ ] 2.10 LoadFolderLayers
  [ ] 2.11 PathExtensionPlugin
  [ ] 2.12 ReplaceInLayouts
  [ ] 2.13 SaveTemporaryLayersPlugin
  [ ] 2.14 GenerateTrailPlugin
  [ ] 2.15 ReportMetadataPlugin
  [ ] 2.16 VectorFieldsCalculationPlugin
  [ ] 2.17 VectorToSvgPlugin
  [ ] 2.18 SettingsPlugin

[ ] FASE 3: Eliminação da WidgetFactory
  [ ] 3.1 Marcar WidgetFactory como deprecated
  [ ] 3.2 Remover WidgetFactory (após 1 release)
  [ ] 3.3 Manter docs/skills/SKILL_WIDGETS2.md atualizada
  [ ] 3.4 Atualizar PLUGIN_CONTRACT.md (regra #1)
  [ ] 3.5 Atualizar docs/ia/changelog.txt
```

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-21 | 1.0.0 | Criação inicial |
| 2026-07-21 | 2.0.0 | Estratégia não-destrutiva + hierarquia |
| 2026-07-21 | 3.0.0 | BaseTheme limpo, AppTheme, theme (não t), nomes descritivos |
| 2026-07-21 | 4.0.0 | Correções: Separador é QFrame visual, SeparatorWidget separado, ThemeManager só BaseTheme |
| 2026-07-24 | 5.0.0 | **Atualização:** FASE 0 marcada como completa; FASE 1 atualizada com SimpleModernButton, SimpleQLineEdit, GridExecutionButtons, GridIconButton, MainLayout, ScrollWidget, AppBarWidget; FASE 2 atualizada com AboutDialog e CoorResultDialog como migrados; adicionadas regras 13-17 do contrato (config dict, callbacks, modern widgets, add_execution_buttons sem stretch) |
| 2026-07-24 | 5.1.0 | **Atualização:** Adicionado TextBrowser.py aos widgets raiz (FASE 1.3). Adicionado InfoDialog como migrado (FASE 2 - 2.3.64.1). Atualizadas seções 3, 4.1, 4.2, 7.3, 8.1 e TODO com TextBrowser e InfoDialog. |
