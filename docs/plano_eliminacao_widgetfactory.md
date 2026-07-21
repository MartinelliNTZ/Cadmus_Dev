# 🎯 PLANO DE AÇÃO: Eliminação da WidgetFactory

**Objetivo:** Eliminar completamente o uso da `WidgetFactory`, migrando para um modelo onde widgets se autoconfiguram com `AppStyles` + `ThemeManager`, e plugins declaram widgets via parâmetros/dict sem saber de estilos.

**Data:** 2026-07-21
**Versão:** 2.0.0
**Autor:** Cadmus Engineering

---

## Sumário

1. [Arquitetura Atual](#1-arquitetura-atual)
2. [Arquitetura Alvo](#2-arquitetura-alvo)
3. [Estratégia de Migração Não-Destrutiva](#3-estratégia-de-migração-não-destrutiva)
4. [Hierarquia de Widgets](#4-hierarquia-de-widgets)
5. [Contrato de Unidades e Estilo](#5-contrato-de-unidades-e-estilo)
6. [FASE 0 — Fundação](#6-fase-0--fundação)
7. [FASE 1 — Criação dos Novos Widgets](#7-fase-1--criação-dos-novos-widgets)
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
  └─ importa WidgetFactory
      └─ WidgetFactory.create_xxx(params)
          ├─ Cria widget (importa de resources/widgets/)
          ├─ Cria layout (QVBoxLayout)
          ├─ Aplica Styles.xxx() (importa de resources/styles/Styles.py)
          ├─ Adiciona separadores (top/bottom)
          └─ Retorna (layout, widget)

Styles (resources/styles/Styles.py)
  └─ herda BaseStyles
      └─ importa current_theme de ThemeManager (variável de módulo)
          └─ ThemeManager.theme → CoffeTheme

BaseStyles
  ├─ Atributos de classe: COLOR_PRIMARY, FONT_SIZE_NORMAL, etc.
  │   └─ Lidos de current_theme (resolvido na importação!)
  └─ Métodos estáticos: button(), label(), input(), checkbox(), etc.
```

### Problemas Identificados

| # | Problema | Impacto |
|---|----------|---------|
| 1 | `BaseStyles` copia tokens como atributos de classe | Resolvido na importação — se tema mudar, atributos ficam desatualizados |
| 2 | `Styles` + `BaseStyles` são 2 arquivos duplicados | Manutenção confusa |
| 3 | `WidgetFactory` tem 1135 linhas (viola SRP) | Difícil testar/manter |
| 4 | Plugin sabe de layout (recebe `(layout, widget)`) | Acoplamento |
| 5 | Unidades de medida (`px`) espalhadas em Styles.py e widgets | Se tema mudar tamanho base, precisa mudar em N lugares |
| 6 | Widgets antigos não têm `_specific_style()` padronizado | Estilo específico misturado com global |

---

## 2. Arquitetura Alvo

### Diagrama de Dependências (Novo)

```
Plugin
  └─ importa GRID widget de resources/new_widgets/grid/
      └─ widget.__init__(params, parent)
          ├─ Autoconfiguração total
          ├─ AppStyles (estilos globais)
          ├─ ThemeManager (cores, fontes, dimensões)
          └─ _specific_style() (estilo próprio)

AppStyles (resources/styles/AppStyles.py — NOVO)
  ├─ Lê de ThemeManager (com cache)
  ├─ Só métodos GLOBAIS: button(), label(), input(), checkbox()
  ├─ SEM unidades fixas — usa tokens do tema (ex: {t.INPUT_HEIGHT})
  └─ SEM atributos de classe copiados

ThemeManager
  └─ Mantido → AppStyles lê dele

Widgets (resources/new_widgets/)
  ├─ simple/   → itens básicos (QLineEdit, QLabel) — uso INTERNO apenas
  ├─ grid/     → composto de simples — PRIORIDADE para plugins (mesmo 1 item)
  ├─ complex/  → simple + título + botões + funções internas
  └─ grid_complex/ → grid de complex — PRIORIDADE MÁXIMA para plugins
```

---

## 3. Estratégia de Migração Não-Destrutiva

### ⚠️ REGRA FUNDAMENTAL: NÃO MODIFICAR ARQUIVOS EXISTENTES

Para não quebrar o sistema durante a migração:

```
resources/
  ├── styles/
  │   ├── BaseStyles.py   ← NÃO TOCAR (mantido para widgets antigos)
  │   ├── Styles.py        ← NÃO TOCAR (mantido para widgets antigos)
  │   ├── ThemeManager.py  ← OK usar (já existe)
  │   ├── BaseTheme.py     ← OK usar (já existe)
  │   ├── CoffeTheme.py    ← OK usar (já existe)
  │   └── AppStyles.py     ← NOVO (criado na FASE 0)
  │
  ├── widgets/             ← NÃO TOCAR (widgets antigos continuam funcionando)
  │
  └── new_widgets/         ← NOVO (tudo novo aqui)
      ├── simple/
      │   ├── SimpleLabel.py
      │   ├── SimpleInput.py
      │   ├── SimpleButton.py
      │   └── SimpleComboBox.py
      │
      ├── grid/
      │   ├── GridLabel.py        → grid de QLabel(s)
      │   ├── GridInput.py         → grid de QLineEdit(s)
      │   ├── GridCheckbox.py      → grid de QCheckBox(es)
      │   ├── GridRadioButton.py   → grid de QRadioButton(s)
      │   ├── GridLayerInput.py    → LayerInput refatorado
      │   └── GridButton.py        → grid de botões (ex: bottom actions)
      │
      ├── complex/
      │   ├── ComplexSelector.py   → título + input + botões
      │   ├── ComplexPath.py       → título + path selector + botões
      │   ├── ComplexColor.py      → título + color picker + hex
      │   └── ComplexCollapsible.py→ título + conteúdo colapsável
      │
      └── grid_complex/
          └── GridComplexSelector.py → grid de ComplexSelector
```

### Fluxo de Migração

```
1. Criar AppStyles.py          → sem modificar Styles/BaseStyles
2. Criar simple/ widgets       → widgets base
3. Criar grid/ widgets         → compostos de simple (para plugins)
4. Criar complex/ widgets      → simples + funções
5. Criar grid_complex/ widgets → grids de complex
6. Migrar Plugin A             → usar grid/grid_complex de new_widgets
7. Migrar Plugin B             → idem
8. ... até todos plugins migrados
9. NUNCA deletar widgets/ antigos ou Styles.py
```

---

## 4. Hierarquia de Widgets

### 4.1 Categorias

| Categoria | Descrição | Onde Fica | Quem Usa |
|-----------|-----------|-----------|----------|
| **Simple** | Item UI mais básico: QLineEdit, QLabel, QComboBox, QPushButton | `new_widgets/simple/` | ⚠️ USO INTERNO apenas (outros widgets) |
| **Grid** | Composto de vários simples + layout + separadores | `new_widgets/grid/` | ✅ PRIORIDADE para plugins (mesmo 1 item) |
| **Complex** | Simple + título + botões + funções internas | `new_widgets/complex/` | ✅ USO em plugins quando necessário |
| **Grid Complex** | Grid de ComplexSelectors com parent linking | `new_widgets/grid_complex/` | ✅ PRIORIDADE MÁXIMA para plugins |

### 4.2 Regra de Uso

```
Plugin:
  ├── PRIORIDADE 1: GridComplex (se precisar de múltiplos complexos)
  ├── PRIORIDADE 2: Complex (se precisar de título + botões + função)
  ├── PRIORIDADE 3: Grid (se for entrada simples)
  └── NUNCA: Simple (uso interno apenas)

Widget interno:
  ├── Simple: para construir Grid e Complex
  └── Grid/Complex: para construir GridComplex
```

### 4.3 Separadores em Todos os Widgets

TODO widget em `new_widgets/` DEVE suportar separadores nos 4 lados:

```python
class MeuWidget(QWidget):
    def __init__(self, parent=None, **kwargs):
        # ...
        self._separator_top = kwargs.pop("separator_top", False)
        self._separator_bottom = kwargs.pop("separator_bottom", False)
        self._separator_left = kwargs.pop("separator_left", False)
        self._separator_right = kwargs.pop("separator_right", False)
```

Os separadores são adicionados no layout interno do widget (margens):

```python
def _build_layout(self):
    layout = QVBoxLayout(self)
    layout.setContentsMargins(
        self._PADDING if self._separator_left else 0,
        self._PADDING if self._separator_top else 0,
        self._PADDING if self._separator_right else 0,
        self._PADDING if self._separator_bottom else 0,
    )
```

---

## 5. Contrato de Unidades e Estilo

### 5.1 🚫 NUNCA Colocar `px` no Widget ou AppStyles

**ERRADO:**
```python
# ❌ UNIDADE FIXA NO ESTILO — NÃO FAZER
min-height: {current_theme.INPUT_HEIGHT}px;
border: 1px solid {current_theme.COLOR_BORDER};
```

**CERTO:**
```python
# ✅ UNIDADE SEMPRE NO TEMA
# No theme:  INPUT_HEIGHT = "4px"
# No style:  min-height: {t.INPUT_HEIGHT};

# No theme:  PXBORDER = "1px solid"
# No style:  border: {t.PXBORDER} {t.COLOR_BORDER};
```

### 5.2 Onde a Unidade Fica

```
TEMA (BaseTheme / CoffeTheme):
  INPUT_HEIGHT: str = "4px"          ← unidade AQUI
  BUTTON_HEIGHT: str = "4px"         ← unidade AQUI
  PXBORDER: str = "1px solid"       ← unidade AQUI
  PADDING_INPUT: str = "2px 8px"    ← unidade AQUI
  BORDER_RADIUS: str = "4px"        ← unidade AQUI
  MARGIN_SEPARATOR: str = "4px 0px" ← unidade AQUI

AppStyles / Widget:
  min-height: {t.INPUT_HEIGHT};      ← sem px, sem unidade
  border: {t.PXBORDER} {t.COLOR_BORDER};
  padding: {t.PADDING_INPUT};
  border-radius: {t.BORDER_RADIUS};
  margin: {t.MARGIN_SEPARATOR};
```

### 5.3 Temas com Variáveis Booleanas

Temas podem ter flags booleanas para efeitos visuais:

```python
class CoffeTheme(BaseTheme):
    ALLOW_SHADOW: bool = True
    ALLOW_GLOW: bool = False
    SHADOW_SIZE: str = "0px"  # ou "4px" quando ALLOW_SHADOW=True
    GLOW_SIZE: str = "0px"    # ou "4px" quando ALLOW_GLOW=True

Uso no AppStyles:
```python
@classmethod
def panel(cls) -> str:
    t = cls._get_theme()
    return f"""
    QFrame {{
        background:{t.COLOR_BACKGROUND_SOFT};
        border-radius:{t.BORDER_RADIUS};
        padding:{t.PADDING_INPUT};
        box-shadow: {shadow};
    }}
    """
```

### 5.4 Padronização de `_specific_style()`

TODO widget em `new_widgets/` DEVE ter:

```python
def _specific_style(self) -> str:
    """
    Estilo específico deste widget.
    Usa tokens do tema (sem unidades fixas).
    SOBRESCREVER nas subclasses se necessário.
    """
    return ""
```

---

## 6. FASE 0 — Fundação

### 6.1 Criar `resources/styles/AppStyles.py`

**Arquivo novo** que concentra estilos globais. Lê tokens do tema via cache com `_get_theme()`.

**Regras:**
- Só métodos de estilo **global** (button, label, input, checkbox, radio, spinbox, map_layer_combobox, scroll_area, separator, main_application, app_bar, panel, collapsible_parameters)
- **NÃO** contém estilos específicos de widget (vão para `_specific_style()` do widget)
- **NÃO** usa `px` ou unidades — tokens do tema já têm unidade
- Usa cache com `_get_theme()` e `reload_theme()`

**Estrutura:**

```python
# resources/styles/AppStyles.py
# -*- coding: utf-8 -*-
"""
AppStyles — Estilos globais do Cadmus
======================================
Ponto único de estilos visuais GLOBAIS.
Lê tokens do ThemeManager (cada token já contém unidade: "4px").
Widgets específicos têm estilos próprios em _specific_style().

Uso:
    from resources.styles.AppStyles import AppStyles
    style = AppStyles.button()
"""

from __future__ import annotations
from typing import ClassVar, Optional


class AppStyles:
    """Estilos globais — lê do ThemeManager com cache."""

    _theme: ClassVar[Optional[object]] = None

    @classmethod
    def _get_theme(cls):
        """Retorna tema atual (com cache). Invalida com reload_theme()."""
        if cls._theme is None:
            from .ThemeManager import theme_manager
            cls._theme = theme_manager.theme
        return cls._theme

    @classmethod
    def reload_theme(cls):
        """Invalida cache e recarrega tema."""
        from .ThemeManager import theme_manager
        theme_manager.reload_theme()
        cls._theme = theme_manager.theme

    @classmethod
    def button(cls) -> str:
        t = cls._get_theme()
        return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {t.COLOR_PRIMARY},
                stop:1 {t.COLOR_PRIMARY_DARK});
            color: {t.COLOR_BUTTON_TEXT};
            border: {t.PXBORDER} {t.COLOR_PRIMARY_DARK};
            border-radius: {t.BUTTON_BORDER_RADIUS};
            padding: {t.BUTTON_PADDING};
            min-height: {t.BUTTON_HEIGHT};
        }}
        QPushButton:hover {{
            background: {t.COLOR_PRIMARY_LIGHT};
        }}
        QPushButton:pressed {{
            background: {t.COLOR_PRIMARY_DARK};
        }}
        QPushButton:disabled {{
            background: {t.COLOR_BACKGROUND_SOFT};
            color: {t.COLOR_TEXT_SECONDARY};
        }}
        """

    @classmethod
    def label(cls) -> str:
        t = cls._get_theme()
        return f"""
        QLabel {{
            color: {t.COLOR_TEXT_PRIMARY};
            font-family: {t.FONT_FAMILY_DEFAULT};
            font-size: {t.FONT_SIZE_NORMAL};
        }}
        """

    @classmethod
    def input(cls) -> str:
        t = cls._get_theme()
        return f"""
        QLineEdit,
        QSpinBox,
        QDoubleSpinBox {{
            background: {t.COLOR_BACKGROUND_PANEL};
            color: {t.COLOR_TEXT_PRIMARY};
            border: {t.PXBORDER} {t.COLOR_BORDER};
            border-radius: {t.INPUT_BORDER_RADIUS};
            padding: {t.INPUT_PADDING};
            min-height: {t.INPUT_HEIGHT};
            max-height: {t.INPUT_MAX_HEIGHT};
        }}
        QLineEdit:focus,
        QSpinBox:focus,
        QDoubleSpinBox:focus {{
            border: {t.PXBORDER} {t.COLOR_PRIMARY};
        }}
        """

    @classmethod
    def checkbox(cls) -> str:
        t = cls._get_theme()
        return f"""
        QCheckBox {{
            color: {t.COLOR_TEXT_PRIMARY};
            font-family: {t.FONT_FAMILY_DEFAULT};
            font-size: {t.FONT_SIZE_NORMAL};
            spacing: {t.CHECKBOX_SPACING};
        }}
        QCheckBox::indicator {{
            width: {t.CHECKBOX_SIZE};
            height: {t.CHECKBOX_SIZE};
            border-radius: {t.CHECKBOX_BORDER_RADIUS};
            border: {t.CHECKBOX_BORDER_WIDTH} {t.COLOR_BORDER};
            background: {t.COLOR_CHECKBOX_BG};
        }}
        QCheckBox::indicator:checked {{
            background: {t.COLOR_PRIMARY};
            border: {t.CHECKBOX_BORDER_WIDTH} {t.COLOR_PRIMARY_DARK};
        }}
        """

    @classmethod
    def radio_button(cls) -> str:
        t = cls._get_theme()
        return f"""
        QRadioButton {{
            color: {t.COLOR_TEXT_PRIMARY};
            font-family: {t.FONT_FAMILY_DEFAULT};
            font-size: {t.FONT_SIZE_NORMAL};
            spacing: {t.CHECKBOX_SPACING};
        }}
        QRadioButton::indicator {{
            width: {t.RADIO_SIZE};
            height: {t.RADIO_SIZE};
            border-radius: {t.RADIO_BORDER_RADIUS};
            border: {t.CHECKBOX_BORDER_WIDTH} {t.COLOR_BORDER};
            background: {t.COLOR_BACKGROUND_PANEL};
        }}
        QRadioButton::indicator:checked {{
            background: {t.COLOR_PRIMARY};
        }}
        """

    @classmethod
    def spinbox(cls) -> str:
        t = cls._get_theme()
        return f"""
        QSpinBox,
        QDoubleSpinBox {{
            background: {t.COLOR_BACKGROUND_PANEL};
            color: {t.COLOR_TEXT_PRIMARY};
            font-family: {t.FONT_FAMILY_DEFAULT};
            font-size: {t.FONT_SIZE_NORMAL};
            border: {t.PXBORDER} {t.COLOR_BORDER};
            border-radius: {t.INPUT_BORDER_RADIUS};
            min-height: {t.INPUT_HEIGHT};
            padding: {t.INPUT_PADDING};
            padding-right: {t.INPUT_PADDING_RIGHT};
        }}
        QSpinBox:hover,
        QDoubleSpinBox:hover {{
            border: {t.PXBORDER} {t.COLOR_PRIMARY_LIGHT};
        }}
        QSpinBox:focus,
        QDoubleSpinBox:focus {{
            border: {t.PXBORDER} {t.COLOR_PRIMARY};
        }}
        QSpinBox:disabled,
        QDoubleSpinBox:disabled {{
            background: {t.COLOR_BACKGROUND_SOFT};
            color: {t.COLOR_TEXT_SECONDARY};
        }}
        QSpinBox::up-button,
        QSpinBox::down-button,
        QDoubleSpinBox::up-button,
        QDoubleSpinBox::down-button {{
            width: {t.INPUT_BUTTON_WIDTH};
            height: {t.INPUT_HEIGHT};
            border-radius: {t.BORDER_RADIUS_SMALL};
            border-left: {t.PXBORDER} {t.COLOR_BORDER};
            background: {t.COLOR_PRIMARY};
            padding: 0px;
            margin: 0px;
        }}
        QSpinBox::up-button:hover,
        QSpinBox::down-button:hover,
        QDoubleSpinBox::up-button:hover,
        QDoubleSpinBox::down-button:hover {{
            background: {t.COLOR_PRIMARY_LIGHT};
        }}
        QSpinBox::up-button:pressed,
        QSpinBox::down-button:pressed,
        QDoubleSpinBox::up-button:pressed,
        QDoubleSpinBox::down-button:pressed {{
            background: {t.COLOR_PRIMARY_DARK};
        }}
        """

    @classmethod
    def map_layer_combobox(cls) -> str:
        t = cls._get_theme()
        return f"""
        QgsMapLayerComboBox {{
            background: {t.COLOR_BACKGROUND_PANEL};
            color: {t.COLOR_TEXT_PRIMARY};
            border: {t.PXBORDER} {t.COLOR_BORDER};
            border-radius: {t.INPUT_BORDER_RADIUS};
            padding: {t.INPUT_PADDING};
            min-height: {t.INPUT_HEIGHT};
        }}
        QgsMapLayerComboBox:hover {{
            border: {t.PXBORDER} {t.COLOR_PRIMARY_LIGHT};
        }}
        """

    @classmethod
    def scroll_area(cls) -> str:
        t = cls._get_theme()
        return f"""
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollBar:vertical {{
            width: {t.SCROLLBAR_WIDTH};
            background: transparent;
        }}
        QScrollBar::handle:vertical {{
            background: {t.COLOR_PRIMARY};
            border-radius: {t.SCROLLBAR_RADIUS};
        }}
        QScrollBar::handle:vertical:hover {{
            background: {t.COLOR_PRIMARY_LIGHT};
        }}
        """

    @classmethod
    def separator(cls) -> str:
        t = cls._get_theme()
        return f"""
        QFrame {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {t.COLOR_BACKGROUND_PANEL},
                stop:0.5 {t.COLOR_PRIMARY},
                stop:1 {t.COLOR_BACKGROUND_PANEL});
            height: {t.SEPARATOR_HEIGHT};
            border: none;
            margin: {t.SEPARATOR_MARGIN};
        }}
        """

    @classmethod
    def main_application(cls) -> str:
        t = cls._get_theme()
        return f"""
        #main_container {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 {t.COLOR_BACKGROUND_MAIN},
                stop:0.5 {t.COLOR_BACKGROUND_PANEL},
                stop:1 {t.COLOR_BACKGROUND_MAIN});
            border: {t.PXBORDER} {t.COLOR_BORDER};
            border-radius: {t.CONTAINER_RADIUS};
        }}
        {cls.label()}
        {cls.checkbox()}
        {cls.radio_button()}
        {cls.button()}
        {cls.input()}
        {cls.map_layer_combobox()}
        {cls.scroll_area()}
        """

    @classmethod
    def app_bar(cls) -> str:
        t = cls._get_theme()
        return f"""
        #app_bar {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {t.COLOR_PRIMARY_DARK},
                stop:1 {t.COLOR_PRIMARY});
            border-bottom: {t.PXBORDER} {t.COLOR_BORDER};
            border-radius: {t.RADIO_BORDER_RADIUS};
            min-height: {t.APPBAR_HEIGHT};
        }}
        #app_bar_title {{
            color:{t.COLOR_TEXT_PRIMARY};
            font-weight:bold;
            font-size:{t.APPBAR_TITLE_SIZE};
        }}
        QPushButton#app_bar_btn_run {{
            background:{t.COLOR_PRIMARY};
            border: {t.PXBORDER} {t.COLOR_PRIMARY_DARK};
            padding: {t.BUTTON_PADDING_SMALL};
            font-weight:bold;
            font-size:{t.FONT_SIZE_SMALL};
        }}
        QPushButton#app_bar_btn_run:hover {{
            background:{t.COLOR_PRIMARY_LIGHT};
        }}
        QPushButton#app_bar_btn_info {{
            background:{t.COLOR_APPBAR_INFO_BG};
            color:{t.COLOR_TEXT_SECONDARY};
            border: {t.PXBORDER} {t.COLOR_BORDER};
        }}
        QPushButton#app_bar_btn_info:hover {{
            background:{t.COLOR_APPBAR_INFO_BG_HOVER};
        }}
        QPushButton#app_bar_btn_close {{
            background:transparent;
            border:none;
            font-size:{t.APPBAR_CLOSE_SIZE};
        }}
        """

    @classmethod
    def panel(cls) -> str:
        t = cls._get_theme()
        return f"""
        QFrame {{
            background:{t.COLOR_BACKGROUND_SOFT};
            border-radius: {t.BORDER_RADIUS};
            padding: {t.PADDING_INPUT};
        }}
        """

    @classmethod
    def collapsible_parameters(cls) -> str:
        t = cls._get_theme()
        return f"""
        #collapsible_header {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {t.COLOR_COLLAPSIBLE_HEADER_START},
                stop:1 {t.COLOR_COLLAPSIBLE_HEADER_END});
            border-bottom: {t.PXBORDER} {t.COLOR_BORDER};
            border-radius: {t.BORDER_RADIUS} {t.BORDER_RADIUS} 0 0;
        }}
        #collapsible_header:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {t.COLOR_COLLAPSIBLE_HEADER_HOVER_START},
                stop:1 {t.COLOR_COLLAPSIBLE_HEADER_HOVER_END});
        }}
        #collapsible_icon {{
            color: {t.COLOR_TEXT_PRIMARY};
            font-weight: bold;
            font-size: {t.FONT_SIZE_BIG};
            qproperty-alignment: AlignCenter;
        }}
        #collapsible_title {{
            color: {t.COLOR_TEXT_PRIMARY};
            font-weight: bold;
            font-size: {t.FONT_SIZE_NORMAL};
            font-family: {t.FONT_FAMILY_DEFAULT};
            background: transparent;
        }}
        #collapsible_header_btn {{
            background: transparent;
            border: none;
            padding: 0px;
            margin: 0px;
        }}
        #collapsible_content {{
            background: {t.COLOR_BACKGROUND_SOFT};
            border-bottom: {t.PXBORDER} {t.COLOR_BORDER};
            border-left: {t.PXBORDER} {t.COLOR_BORDER};
            border-right: {t.PXBORDER} {t.COLOR_BORDER};
            border-radius: 0 0 {t.BORDER_RADIUS} {t.BORDER_RADIUS};
        }}
        """

    @classmethod
    def calc_checkbox_grid_height(cls, num_items: int, items_per_row: int = 1) -> int:
        t = cls._get_theme()
        rows = (num_items + items_per_row - 1) // items_per_row
        item_h = int(t.ITEM_HEIGHT.replace("px", ""))
        spacing = t.LAYOUT_V_SPACING
        return (rows * item_h) + ((rows - 1) * spacing)
```

### 6.2 Adicionar Tokens com Unidade no `BaseTheme.py`

**NÃO modificar tokens existentes** — adicionar NOVOS tokens com unidade:

```python
class BaseTheme:
    # ── Tokens existentes (mantidos para compatibilidade) ────
    STANDARD_SIZE: int = 12
    INPUT_HEIGHT: int = STANDARD_SIZE
    BUTTON_HEIGHT: int = STANDARD_SIZE
    # ... demais tokens existentes (NÃO MODIFICAR)

    # ── NOVOS tokens com unidade ─────────────────────────────
    INPUT_HEIGHT: str = "12px"
    INPUT_MAX_HEIGHT: str = "18px"
    BUTTON_HEIGHT: str = "12px"
    PXBORDER: str = "1px solid"
    PADDING_INPUT: str = "2px 8px"
    PADDING_BUTTON: str = "4px 12px"
    BORDER_RADIUS: str = "6px"
    BORDER_RADIUS_SMALL: str = "2px"
    CONTAINER_RADIUS: str = "8px"
    SEPARATOR_HEIGHT: str = "3px"
    SEPARATOR_MARGIN: str = "4px 0px"
    SCROLLBAR_WIDTH: str = "8px"
    SCROLLBAR_RADIUS: str = "4px"
    APPBAR_HEIGHT: str = "35px"
    APPBAR_TITLE_SIZE: str = "10.5pt"
    APPBAR_CLOSE_SIZE: str = "14pt"
    CHECKBOX_SIZE: str = "12px"
    RADIO_SIZE: str = "12px"
    CHECKBOX_BORDER_RADIUS: str = "3px"
    CHECKBOX_BORDER_WIDTH: str = "1px"
    CHECKBOX_SPACING: str = "6px"
    RADIO_BORDER_RADIUS: str = "6px"
    INPUT_BORDER_RADIUS: str = "4px"
    INPUT_BUTTON_WIDTH: str = "16px"
    INPUT_PADDING_RIGHT: str = "18px"
    BUTTON_BORDER_RADIUS: str = "6px"
    LAYOUT_V_SPACING: int = 2
    LAYOUT_H_SPACING: int = 2
    ITEM_HEIGHT: str = "12px"

    # ── Flags booleanas para efeitos visuais ────────────────
    ALLOW_SHADOW: bool = False
    ALLOW_GLOW: bool = False
    SHADOW_SIZE: str = "0px"
```

---

## 7. FASE 1 — Criação dos Novos Widgets

### 7.1 Widgets Simple (USO INTERNO)

Criados em `resources/new_widgets/simple/`. Usados apenas por Grid, Complex e GridComplex.

| Arquivo | Classe | Descrição |
|---------|--------|-----------|
| `SimpleLabel.py` | `SimpleLabel` | QLabel configurado com AppStyles.label() |
| `SimpleInput.py` | `SimpleInput` | QLineEdit configurado |
| `SimpleButton.py` | `SimpleButton` | QPushButton configurado |
| `SimpleComboBox.py` | `SimpleComboBox` | QComboBox configurado |
| `SimpleSpinBox.py` | `SimpleSpinBox` | QDoubleSpinBox configurado |
| `SimpleCheckbox.py` | `SimpleCheckbox` | QCheckBox configurado |
| `SimpleRadioButton.py` | `SimpleRadioButton` | QRadioButton configurado |
| `SimpleSeparator.py` | `SimpleSeparator` | QFrame separador |

### 7.2 Widgets Grid (PRIORIDADE para plugins)

Criados em `resources/new_widgets/grid/`. Compostos de Simple widgets + layout.

| Arquivo | Classe | Descrição |
|---------|--------|-----------|
| `GridLabel.py` | `GridLabel` | Grid de QLabels (1 ou mais) |
| `GridInput.py` | `GridInput` | Grid de QLineEdits |
| `GridCheckbox.py` | `GridCheckbox` | Grid de QCheckBoxes |
| `GridRadioButton.py` | `GridRadioButton` | Grid de QRadioButtons |
| `GridLayerInput.py` | `GridLayerInput` | LayerInput refatorado (label + combobox + checkbox) |
| `GridButton.py` | `GridButton` | Grid de botões (bottom actions) |
| `GridReadOnly.py` | `GridReadOnly` | Grid de campos read-only |
| `GridDropdown.py` | `GridDropdown` | Dropdown com label |

### 7.3 Widgets Complex

Criados em `resources/new_widgets/complex/`. Simple + título + botões + funções internas.

| Arquivo | Classe | Descrição |
|---------|--------|-----------|
| `ComplexSelector.py` | `ComplexSelector` | Título + input + botão + checkbox (seleção de arquivo/pasta) |
| `ComplexPath.py` | `ComplexPath` | Título + path selector + botões |
| `ComplexColor.py` | `ComplexColor` | Título + color picker + hex input + copy |
| `ComplexCollapsible.py` | `ComplexCollapsible` | Título + conteúdo colapsável (avançados) |
| `ComplexCrs.py` | `ComplexCrs` | Título + CRS selector |

### 7.4 Widgets GridComplex (PRIORIDADE MÁXIMA)

Criados em `resources/new_widgets/grid_complex/`.

| Arquivo | Classe | Descrição |
|---------|--------|-----------|
| `GridComplexSelector.py` | `GridComplexSelector` | Grid de ComplexSelectors com parent linking |

### 7.5 Template de Widget Grid

```python
# resources/new_widgets/grid/GridLayerInput.py
# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsVectorLayer, QgsMapLayerProxyModel, QgsProject
from ....core.config.LogUtils import LogUtils
from ....utils.ToolKeys import ToolKey
from ....resources.styles.AppStyles import AppStyles
from ....i18n.TranslationManager import STR


class GridLayerInput(QWidget):
    """
    Widget grid para seleção de camada.
    
    PRIORIDADE para uso em plugins (substitui LayerInputWidget antigo).
    
    Parâmetros
    ----------
    label_text : str
        Texto do label
    filters : QgsMapLayerProxyModel.Filter | list
        Filtros para o combobox
    allow_empty : bool, optional
        Permite nenhuma camada selecionada (default True)
    enable_selected_checkbox : bool, optional
        Exibe checkbox "usar apenas seleção" (default True)
    separator_top : bool, optional
        Separador no topo (default False)
    separator_bottom : bool, optional
        Separador na base (default False)
    separator_left : bool, optional
        Separador na esquerda (default False)
    separator_right : bool, optional
        Separador na direita (default False)
    parent : QWidget, optional
        Widget pai
    
    Autoconfiguração
    ----------------
    - AppStyles: label(), checkbox(), map_layer_combobox()
    - _specific_style(): margens e padding
    """

    layerChanged = pyqtSignal(object)

    def __init__(
        self,
        label_text: str,
        filters,
        *,
        allow_empty: bool = True,
        enable_selected_checkbox: bool = True,
        separator_top: bool = False,
        separator_bottom: bool = False,
        separator_left: bool = False,
        separator_right: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._separator_top = separator_top
        self._separator_bottom = separator_bottom
        self._separator_left = separator_left
        self._separator_right = separator_right

        self.logger = LogUtils(
            tool=ToolKey.WIDGETS,
            class_name="GridLayerInput",
        )
        try:
            self._state_layer = None
            self._filters = self._normalize_filters(filters)

            self._label = QLabel(label_text)
            self._combo = QgsMapLayerComboBox()
            self._combo.setAllowEmptyLayer(allow_empty)
            self._combo.setFilters(self._filters)

            self._chk_selected = None
            if enable_selected_checkbox:
                self._chk_selected = QCheckBox(STR.ONLY_SELECTED_FEATURES)
                self._chk_selected.setEnabled(False)

            self._build_layout()
            self._apply_styles()
            self._bind_events()
            self._try_select_active_layer()
        except Exception as e:
            self.logger.exception(e, code="GRID_LAYER_INPUT_INIT_ERR")

    def _build_layout(self):
        """Monta layout com separadores nos 4 lados."""
        t = AppStyles._get_theme()
        padding = {
            "left": t.PADDING_INPUT if self._separator_left else "0px",
            "top": t.PADDING_INPUT if self._separator_top else "0px",
            "right": t.PADDING_INPUT if self._separator_right else "0px",
            "bottom": t.PADDING_INPUT if self._separator_bottom else "0px",
        }
        layout = QVBoxLayout(self)
        # Converter px strings para int
        layout.setContentsMargins(
            int(padding["left"].replace("px", "")),
            int(padding["top"].replace("px", "")),
            int(padding["right"].replace("px", "")),
            int(padding["bottom"].replace("px", "")),
        )
        layout.setSpacing(t.LAYOUT_V_SPACING)
        layout.addWidget(self._label)
        layout.addWidget(self._combo)
        if self._chk_selected:
            layout.addWidget(self._chk_selected)

    def _apply_styles(self):
        """Aplica estilos globais + específico."""
        style = (
            AppStyles.label()
            + AppStyles.checkbox()
            + AppStyles.map_layer_combobox()
            + self._specific_style()
        )
        self.setStyleSheet(style)

    def _specific_style(self) -> str:
        """
        Estilo específico do GridLayerInput.
        SOBRESCREVER em subclasses se necessário.
        """
        return ""

    # ── Demais métodos (bindings, eventos, API pública) ────────
    # (mesma lógica do LayerInputWidget atual)
```

---

## 8. FASE 2 — Migração Plugin por Plugin

### 8.1 Ordem de Migração

Cada plugin é migrado individualmente. Enquanto não é migrado, continua usando a Factory antiga sem problemas.

### 8.2 Exemplo: `PathExtensionPlugin` Migrado

```python
# plugins/PathExtensionPlugin.py

from ..resources.new_widgets.grid.GridLayerInput import GridLayerInput
from ..resources.new_widgets.grid.GridDropdown import GridDropdown
from ..resources.new_widgets.grid.GridRadioButton import GridRadioButton
from ..resources.new_widgets.grid.GridButton import GridButton


class PathExtensionPlugin(BasePluginMTL):
    def _build_ui(self, **kwargs):
        super()._build_ui(title=STR.PATH_EXTENSION_TITLE, enable_scroll=True)

        # GridLayerInput substitui WidgetFactory.create_layer_input()
        self.layer_input = GridLayerInput(
            label_text=STR.INPUT_LAYER,
            filters=[QgsMapLayerProxyModel.Filter.VectorLayer],
            allow_empty=False,
            parent=self,
            # Separadores são opcionais internos ao widget
        )

        # GridDropdown substitui WidgetFactory.create_dropdown_selector()
        self.attr_selector = GridDropdown(
            title=f"{STR.PATH}:",
            options_dict={},
            allow_empty=True,
            empty_text=STR.SELECT,
            parent=self,
        )

        # GridRadioButton substitui WidgetFactory.create_radio_button_grid()
        self.radio_mode = GridRadioButton(
            items=[STR.MODE_REMOVE, STR.MODE_RESTORE,
                   STR.MODE_ZIP, STR.MODE_UNZIP],
            columns=2,
            checked_index=0,
            tool_key=self.TOOL_KEY,
            parent=self,
        )

        # GridButton substitui WidgetFactory.create_bottom_action_buttons()
        self.action_buttons = GridButton(
            parent=self,
            run_callback=self.execute_tool,
            close_callback=self.close,
            info_callback=self.show_info_dialog,
            tool_key=self.TOOL_KEY,
        )

        # Layout simples: plugin só dá addWidget()
        self.layout.addWidget(self.layer_input)
        self.layout.addWidget(self.attr_selector)
        self.layout.addWidget(self.radio_mode)
        self.layout.addWidget(self.action_buttons)
```

### 8.3 Tabela de Migração

| # | Plugin | Widget Antigo (Factory) | Widget Novo (new_widgets) |
|---|--------|------------------------|--------------------------|
| 1 | `AboutDialog` | create_label, create_text_browser, create_image_widget | GridLabel + complex |
| 2 | `RestartQgis` | create_simple_button | GridButton |
| 3 | `CoorResultDialog` | create_label, create_readonly_field, create_bottom_action_buttons | GridReadOnly + GridButton |
| 4 | `VectorMultipartPlugin` | create_layer_input, create_bottom_action_buttons | GridLayerInput + GridButton |
| 5 | `ExportAllLayouts` | create_readonly_field, create_bottom_action_buttons | GridReadOnly + GridButton |
| 6 | `CopyAttributesPlugin` | create_layer_input, create_checkbox_grid, create_bottom_action_buttons | GridLayerInput + GridCheckbox + GridButton |
| 7 | `DividePointsByStripsPlugin` | create_layer_input, create_input_fields_widget, create_bottom_action_buttons | GridLayerInput + GridInput + GridButton |
| 8 | `DroneCoordinates` | create_label, create_double_spin_input | GridInput |
| 9 | `LoadFolderLayers` | create_path_selector, create_checkbox_grid, create_bottom_action_buttons | ComplexPath + GridCheckbox + GridButton |
| 10 | `PathExtensionPlugin` | create_layer_input, create_dropdown_selector, create_radio_button_grid, create_bottom_action_buttons | GridLayerInput + GridDropdown + GridRadioButton + GridButton |
| 11 | `ReplaceInLayouts` | create_layer_input, create_dropdown_selector, create_bottom_action_buttons | GridLayerInput + GridDropdown + GridButton |
| 12 | `SaveTemporaryLayersPlugin` | create_path_selector, create_layer_input, create_bottom_action_buttons | ComplexPath + GridLayerInput + GridButton |
| 13 | `GenerateTrailPlugin` | create_layer_input, create_dropdown_selector, create_input_fields_widget, create_color_button, create_bottom_action_buttons | GridLayerInput + GridDropdown + GridInput + ComplexColor + GridButton |
| 14 | `ReportMetadataPlugin` | create_path_selector, create_layer_input, create_checkbox_grid, create_bottom_action_buttons | ComplexPath + GridLayerInput + GridCheckbox + GridButton |
| 15 | `VectorFieldsCalculationPlugin` | create_layer_input, create_dropdown_selector, create_input_fields_widget, create_bottom_action_buttons | GridLayerInput + GridDropdown + GridInput + GridButton |
| 16 | `VectorToSvgPlugin` | create_path_selector, create_layer_input, create_checkbox_grid, create_bottom_action_buttons | ComplexPath + GridLayerInput + GridCheckbox + GridButton |
| 17 | `SettingsPlugin` | Múltiplos | Grid + Complex (análise individual) |

### 8.4 Checklist de Migração por Plugin

```markdown
## Plugin: [NOME]

### Análise
- [ ] Quais widgets usa atualmente (via Factory)?
- [ ] Pode usar GridComplex? Complex? Grid?
- [ ] Obedece ao contrato PLUGIN_CONTRACT.md?
- [ ] TEM LOGGER? (sim, herda de BasePluginMTL)

### Migração
- [ ] Substituir WidgetFactory.create_xxx() por widget de new_widgets/
- [ ] Remover imports da Factory
- [ ] Usar Grid (prioridade) ou Complex (se necessário)
- [ ] Separadores: configurar via parâmetros do widget
- [ ] Ajustar layout (addWidget em vez de add_items)

### Pós-migração
- [ ] Plugin não importa mais nada de core/ui/WidgetFactory
- [ ] Plugin não importa nada de resources/styles/
- [ ] Plugin não chama setStyleSheet()
- [ ] Atualizar docs/ia/changelog.txt
```

---

## 9. FASE 3 — Eliminação da WidgetFactory

### 9.1 Após TODOS os plugins migrados

Quando nenhum plugin depender mais da WidgetFactory:

```python
# core/ui/WidgetFactory.py — DEPRECATED
import warnings
warnings.warn(
    "WidgetFactory obsoleto. Use widgets de resources/new_widgets/. "
    "Consulte docs/plano_eliminacao_widgetfactory.md",
    DeprecationWarning, stacklevel=2,
)
```

### 9.2 Remover (após 1 release)

- Deletar `core/ui/WidgetFactory.py`
- Remover imports da Factory de todos os plugins
- Atualizar SKILL_WIDGETS.md
- Atualizar PLUGIN_CONTRACT.md regra #1
- Atualizar docs/ia/changelog.txt

### 9.3 O que NUNCA será removido

- `resources/widgets/` (widgets antigos — mantidos para compatibilidade)
- `resources/styles/Styles.py` (mantido para widgets antigos)
- `resources/styles/BaseStyles.py` (mantido para compatibilidade)

---

## 10. Contrato do Widget

### 10.1 Regras Obrigatórias

1. **Todo widget herda de `QWidget`** (ou `QDialog`)
2. **Todo widget tem `self.logger`** no `__init__`
3. **Todo `try`** usa `self.logger.exception(e, code=...)`
4. **Todo widget chama `self._apply_styles()`** no final do `__init__`
5. **Estilos globais** vêm de `AppStyles`
6. **Estilos específicos** vêm de `_specific_style()` (sempre sobrescrita)
7. **Plugin NUNCA** chama `setStyleSheet()` no widget
8. **Plugin NUNCA** importa `AppStyles` ou `ThemeManager`
9. **Separadores** nos 4 lados: `separator_top/bottom/left/right`
10. **Unidades** sempre no tema — never hardcoded `px` no widget/style

### 10.2 Template Completo

```python
# resources/new_widgets/categoria/MeuWidget.py
# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout
from ....core.config.LogUtils import LogUtils
from ....utils.ToolKeys import ToolKey
from ....resources.styles.AppStyles import AppStyles


class MeuWidget(QWidget):
    """
    [Descrição]
    
    Parâmetros
    ----------
    [param1] : type
        [descrição]
    separator_top/bottom/left/right : bool
        Separadores nos 4 lados (default False)
    parent : QWidget, optional
        Widget pai
    
    Autoconfiguração
    ----------------
    - AppStyles: métodos globais
    - _specific_style(): estilo específico
    - Logger no __init__
    """

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self._separator_top = kwargs.pop("separator_top", False)
        self._separator_bottom = kwargs.pop("separator_bottom", False)
        self._separator_left = kwargs.pop("separator_left", False)
        self._separator_right = kwargs.pop("separator_right", False)

        self.logger = LogUtils(
            tool=ToolKey.WIDGETS,
            class_name=self.__class__.__name__,
        )
        try:
            self._params = kwargs
            self._configure()
            self._apply_styles()
        except Exception as e:
            self.logger.exception(e, code="WIDGET_INIT_ERR")

    def _configure(self):
        """Monta UI com parâmetros e separadores."""
        t = AppStyles._get_theme()
        padding = {
            "left": t.PADDING_INPUT if self._separator_left else "0px",
            "top": t.PADDING_INPUT if self._separator_top else "0px",
            "right": t.PADDING_INPUT if self._separator_right else "0px",
            "bottom": t.PADDING_INPUT if self._separator_bottom else "0px",
        }
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            int(padding["left"].replace("px", "")),
            int(padding["top"].replace("px", "")),
            int(padding["right"].replace("px", "")),
            int(padding["bottom"].replace("px", "")),
        )
        # ... criar widgets filhos, montar layout, conectar sinais

    def _apply_styles(self):
        """Aplica estilos globais + específico."""
        style = (
            self._global_style()
            + self._specific_style()
        )
        self.setStyleSheet(style)

    def _global_style(self) -> str:
        """Estilos globais via AppStyles (opcional)."""
        return (
            AppStyles.label()
            + AppStyles.button()
            + AppStyles.input()
        )

    def _specific_style(self) -> str:
        """
        Estilo específico do widget.
        SOBRESCREVER nas subclasses.
        Usa tokens do tema, SEM unidades fixas.
        """
        return ""
```

---

## 11. Compatibilidade Qt5/Qt6

### 11.1 Helper de Compatibilidade

```python
# utils/qt_compat.py
"""Helpers de compatibilidade Qt5/Qt6."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QFrame


def qt_enum(module, qt5_name: str, qt6_attr: str, qt6_name: str):
    """Resolve enum compatível Qt5 → Qt6."""
    try:
        return getattr(getattr(module, qt6_attr), qt6_name)
    except AttributeError:
        return getattr(module, qt5_name)


def qt_window_type(name: str):
    """Qt.WindowType.Dialog → Qt.Dialog"""
    return qt_enum(Qt, name, "WindowType", name)


def qt_widget_attr(name: str):
    """Qt.WidgetAttribute.WA_TranslucentBackground → Qt.WA_TranslucentBackground"""
    return qt_enum(Qt, name, "WidgetAttribute", name)


def qt_alignment(name: str):
    """Qt.AlignmentFlag.AlignLeft → Qt.AlignLeft"""
    return qt_enum(Qt, name, "AlignmentFlag", name)


def qframe_shape(name: str):
    """QFrame.Shape.HLine → QFrame.HLine"""
    try:
        return getattr(QFrame.Shape, name)
    except AttributeError:
        return getattr(QFrame, name)


def qframe_shadow(name: str):
    """QFrame.Shadow.Sunken → QFrame.Sunken"""
    try:
        return getattr(QFrame.Shadow, name)
    except AttributeError:
        return getattr(QFrame, name)
```

### 11.2 Onde Aplicar

- `BaseDialog.py` (já tem `_qt_window_type` e `_qt_widget_attr`)
- `new_widgets/` — todos os widgets que usam `Qt.` enums
- `AppStyles` — não usa enums (só strings CSS) → seguro

---

## 12. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Quebrar compatibilidade Qt5/Qt6 | Média | Alto | Helper `qt_enum()` em todos os widgets |
| Plugin parar durante migração | Alta | Alto | Migrar 1 plugin por vez; antigo continua funcionando |
| Perder estilos específicos | Média | Médio | Mover para `_specific_style()` do widget |
| BaseStyles desatualizado | Baixa | Baixo | Mantido como alias, não removido |
| Tema mudar em runtime | Baixa | Médio | AppStyles com cache + `reload_theme()` |
| Widget sem `_apply_styles()` | Média | Médio | Template obrigatório |
| Plugin importar QtWidgets direto | Média | Alto | Code review + linter |
| Unidade hardcoded no widget | Alta | Alto | Template proíbe; usar tokens do tema |
| Widget antigo quebrar com novo AppStyles | Baixa | Baixo | Widgets antigos continuam usando Styles.py |

---

## 13. TODO Interno Consolidado

```
[ ] FASE 0: Fundação
  [ ] 0.1 Criar resources/styles/AppStyles.py
  [ ] 0.2 Adicionar tokens com unidade no BaseTheme.py (NOVOS, sem modificar existentes)
  [ ] 0.3 Criar utils/qt_compat.py (helper Qt5/Qt6)
  [ ] 0.4 Testar AppStyles com tema atual

[ ] FASE 1: Criação dos Novos Widgets
  [ ] 1.1 Simple
    [ ] SimpleLabel.py
    [ ] SimpleInput.py
    [ ] SimpleButton.py
    [ ] SimpleComboBox.py
    [ ] SimpleSpinBox.py
    [ ] SimpleCheckbox.py
    [ ] SimpleRadioButton.py
    [ ] SimpleSeparator.py
  [ ] 1.2 Grid
    [ ] GridLabel.py
    [ ] GridInput.py
    [ ] GridCheckbox.py
    [ ] GridRadioButton.py
    [ ] GridLayerInput.py
    [ ] GridButton.py
    [ ] GridReadOnly.py
    [ ] GridDropdown.py
  [ ] 1.3 Complex
    [ ] ComplexSelector.py
    [ ] ComplexPath.py
    [ ] ComplexColor.py
    [ ] ComplexCollapsible.py
    [ ] ComplexCrs.py
  [ ] 1.4 GridComplex
    [ ] GridComplexSelector.py
  [ ] 1.5 resources/new_widgets/__init__.py

[ ] FASE 2: Migração Plugin por Plugin
  [ ] 2.1 AboutDialog
  [ ] 2.2 RestartQgis
  [ ] 2.3 CoorResultDialog
  [ ] 2.4 VectorMultipartPlugin
  [ ] 2.5 ExportAllLayouts
  [ ] 2.6 CopyAttributesPlugin
  [ ] 2.7 DividePointsByStripsPlugin
  [ ] 2.8 DroneCoordinates
  [ ] 2.9 LoadFolderLayers
  [ ] 2.10 PathExtensionPlugin
  [ ] 2.11 ReplaceInLayouts
  [ ] 2.12 SaveTemporaryLayersPlugin
  [ ] 2.13 GenerateTrailPlugin
  [ ] 2.14 ReportMetadataPlugin
  [ ] 2.15 VectorFieldsCalculationPlugin
  [ ] 2.16 VectorToSvgPlugin
  [ ] 2.17 SettingsPlugin

[ ] FASE 3: Eliminação da WidgetFactory
  [ ] 3.1 Marcar WidgetFactory como deprecated
  [ ] 3.2 Remover WidgetFactory (após 1 release)
  [ ] 3.3 Atualizar docs/skills/SKILL_WIDGETS.md
  [ ] 3.4 Atualizar docs/skills/PLUGIN_CONTRACT.md (regra #1)
  [ ] 3.5 Atualizar docs/ia/changelog.txt
```

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-21 | 1.0.0 | Criação inicial do plano |
| 2026-07-21 | 2.0.0 | **Revisão completa:** estratégia não-destrutiva (`new_widgets/`), hierarquia simple/grid/complex/grid_complex, unidades no tema (nunca `px` em estilo), separadores 4 lados, `_specific_style()` padronizado, flags booleanas no tema, helper Qt5/Qt6, sem modificação de Styles.py ou BaseStyles.py |