# 🎯 PLANO DE AÇÃO: Eliminação da WidgetFactory

**Objetivo:** Eliminar completamente o uso da `WidgetFactory`, migrando para um modelo onde widgets se autoconfiguram com `AppStyles` + `ThemeManager` + `BaseTheme`, e plugins declaram widgets via parâmetros/dict sem saber de estilos.

**Data:** 2026-07-21
**Versão:** 4.0.0
**Autor:** Cadmus Engineering

---

## Sumário

1. [Arquitetura Atual](#1-arquitetura-atual)
2. [Arquitetura Alvo](#2-arquitetura-alvo)
3. [Estratégia de Migração Não-Destrutiva](#3-estratégia-de-migração-não-destrutiva)
4. [Organização e Hierarquia de Widgets](#4-organização-e-hierarquia-de-widgets)
5. [Contrato de Tokens e Unidades](#5-contrato-de-tokens-e-unidades)
6. [FASE 0 — Fundação](#6-fase-0--fundação)
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
      └─ current_theme = CoffeTheme()  ← instância direta, SEM ThemeManager

BaseStyles
  ├─ Atributos de classe: COLOR_PRIMARY, current_theme.COLOR_PRIMARY, etc.
  └─ Métodos estáticos: button(), label(), input(), checkbox()

BaseTheme (resources/styles/BaseTheme.py) — ANTIGO
  └─ 135 linhas com todos os tokens visuais — FOI LIMPO
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
  └── new_widgets/         ← NOVO (sistema novo)
      ├── widget_comum.py          ← widget sem versão grid
      ├── simple/
      │   └── SimpleLayerInput.py  ← widget TEM versão grid (não usar em plugins!)
      └── grid/
          └── GridLayerInput.py    ← versão grid DO MESMO widget (plugins USAM esta)
```

### Regra de Ouro: Simple vs Grid vs Raiz

```
Se um widget TEM uma versão grid:
  └── A versão base vai para simple/   (ex: SimpleLayerInput)
  └── A versão com grid vai para grid/ (ex: GridLayerInput)
  └── Plugins usam SEMPRE grid/

Se um widget NÃO TEM versão grid:
  └── Fica na raiz de new_widgets/ (ex: CollapsibleParametersWidget)

Se um widget é COMPLEXO (simple + funções):
  └── É nomenclatura, não pasta
  └── Ex: ComplexPathSelector.py na raiz — tem título + path + botões
```

### Fluxo de Migração

```
1. BaseTheme já está limpo ✅
2. Adicionar tokens descritivos no BaseTheme.py
3. Criar AppStyles.py → lê de ThemeManager com tokens descritivos
4. Atualizar ThemeManager.py → apontar para BaseTheme (NÃO AppTheme filho)
5. Criar widgets em new_widgets/ → seguindo hierarquia simple/grid/raiz
6. Migrar plugins 1 por vez → usar widgets de new_widgets/
7. NUNCA deletar nada antigo
```

---

## 4. Organização e Hierarquia de Widgets

### 4.1 Regras de Organização

```
new_widgets/
├── grid/           ← Widget TEM versão grid (plugins SEMPRE usam grid)
│   ├── GridLabel.py
│   ├── GridInput.py
│   ├── GridCheckbox.py
│   ├── GridRadioButton.py
│   ├── GridLayerInput.py
│   ├── GridButton.py
│   ├── GridReadOnly.py
│   └── GridDropdown.py
│
├── simple/         ← Widget TEM versão grid (NUNCA importado por plugins)
│   ├── SimpleLabel.py
│   ├── SimpleInput.py
│   ├── SimpleCheckbox.py
│   ├── SimpleRadioButton.py
│   ├── SimpleLayerInput.py
│   ├── SimpleButton.py
│   ├── SimpleReadOnly.py
│   └── SimpleDropdown.py
│
└── (raiz)          ← Widget SEM versão grid
    ├── SeparatorWidget.py    ← QFrame separador visual (gradiente horizontal)
    ├── AppBarWidget.py
    ├── CollapsibleParametersWidget.py
    ├── ComplexPathSelector.py     ← nomenclatura complex, fica na raiz
    ├── ComplexColorPicker.py       ← nomenclatura complex, fica na raiz
    └── GridComplexSelector.py      ← grid de complex, fica na raiz
```

### 4.2 Quando Usar Cada Um

```
PLUGIN:
  ├── Grid (PRIORIDADE) → se widget tem versão grid
  ├── Raiz → se widget NÃO tem versão grid
  └── NUNCA Simple → simple é uso INTERNO de outros widgets

WIDGET INTERNO:
  ├── Simple → para construir Grid e widgets da raiz
  └── Grid → para construir GridComplex
```

### 4.3 Complex é Nomenclatura, Não Pasta

"Nome complex" significa que o widget tem:
- Título
- Inputs
- Botões
- Funções internas (path selector, color picker, etc.)

Mas isso NÃO define uma pasta. O widget fica na raiz conforme a regra acima.

Exemplos:
- `ComplexPathSelector.py` → raiz (não tem versão grid)
- `ComplexColorPicker.py` → raiz (não tem versão grid)
- `ComplexCollapsible.py` → raiz (não tem versão grid)
- `GridComplexSelector.py` → raiz (é grid de complex, mas nome indica grid)

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
  BUTTON_DEFAULT_MIN_HEIGHT: str = "4px"       ← unidade AQUI
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

## 6. FASE 0 — Fundação

### 6.1 BaseTheme JÁ Está Limpo ✅

O `resources/styles/BaseTheme.py` já foi limpo. Agora contém apenas `rgba()`.

**NÃO** tem relação com `BaseStyles.current_theme = CoffeTheme()` do sistema antigo.

**BaseTheme é o tema ÚNICO.** Não terá temas filhos por enquanto.  
Só quando o sistema estiver completamente modificado e estável, poderemos criar temas filhos (DarkTheme, LightTheme, etc.).

### 6.2 Adicionar Tokens Descritivos no `BaseTheme.py`

```python
# resources/styles/BaseTheme.py
# -*- coding: utf-8 -*-
"""
BaseTheme — Tema ÚNICO do sistema Cadmus
==========================================
Contém todos os tokens visuais com nomes DESCRITIVOS.
NÃO terá temas filhos por enquanto.
Quando o sistema estiver completamente modificado, 
poderemos criar temas filhos (DarkTheme, LightTheme, etc.).

Uso:
    from resources.styles.ThemeManager import theme_manager
    bg = theme_manager.COLOR_BACKGROUND_PRIMARY
"""

from __future__ import annotations


class BaseTheme:
    """
    Tema padrão do Cadmus.
    Todos os tokens com nomes descritivos (sem medo de serem grandes).
    """

    @staticmethod
    def rgba(hex_color: str, alpha: int) -> str:
        """
        Converte HEX + alpha para rgba().
        Exemplo:
        rgba("#a6784f", 120) -> "rgba(166,120,79,120)"
        """
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    # ════════════════════════════════════════════════════════════
    # CORES
    # ════════════════════════════════════════════════════════════

    COLOR_PRIMARY: str = "#a6784f"
    COLOR_PRIMARY_LIGHT: str = "#c1936b"
    COLOR_PRIMARY_DARK: str = "#6b4a2f"

    COLOR_BACKGROUND_MAIN: str = "rgba(16, 14, 12, 255)"
    COLOR_BACKGROUND_PANEL: str = "rgba(34, 30, 26, 255)"
    COLOR_BACKGROUND_SOFT: str = "rgba(26, 22, 20, 220)"
    COLOR_BACKGROUND_TRANSPARENT: str = "transparent"

    COLOR_TEXT_PRIMARY: str = "#ece6df"
    COLOR_TEXT_SECONDARY: str = "#d2bca6"
    COLOR_BUTTON_TEXT: str = "#ffffff"

    COLOR_BORDER_DEFAULT: str = "#a6784f"
    COLOR_CHECKBOX_BACKGROUND: str = "#5a5a5a"

    COLOR_LIST_SELECTION_BACKGROUND: str = "rgba(166, 120, 79, 120)"
    COLOR_LIST_SELECTION_HOVER_BACKGROUND: str = "rgba(166, 120, 79, 60)"

    COLOR_APP_BAR_INFO_BUTTON_BACKGROUND: str = "rgba(255, 255, 255, 20)"
    COLOR_APP_BAR_INFO_BUTTON_HOVER_BACKGROUND: str = "rgba(255, 255, 255, 40)"

    COLOR_COLLAPSIBLE_HEADER_START_GRADIENT: str = "rgba(106, 74, 47, 100)"
    COLOR_COLLAPSIBLE_HEADER_END_GRADIENT: str = "rgba(166, 120, 79, 100)"
    COLOR_COLLAPSIBLE_HEADER_HOVER_START_GRADIENT: str = "rgba(106, 74, 47, 140)"
    COLOR_COLLAPSIBLE_HEADER_HOVER_END_GRADIENT: str = "rgba(166, 120, 79, 140)"

    # ════════════════════════════════════════════════════════════
    # FONTES
    # ════════════════════════════════════════════════════════════

    FONT_FAMILY_DEFAULT: str = "'Segoe UI', Arial, sans-serif"
    FONT_SIZE_APP_BAR_TITLE: str = "10.5pt"
    FONT_SIZE_BUTTON_TEXT: str = "8pt"
    FONT_SIZE_LABEL_TEXT: str = "9pt"
    FONT_SIZE_INPUT_TEXT: str = "9pt"
    FONT_SIZE_SECTION_TITLE: str = "12pt"
    FONT_SIZE_APP_BAR_CLOSE_BUTTON: str = "14pt"

    # ════════════════════════════════════════════════════════════
    # DIMENSÕES — TODAS COM UNIDADE
    # ════════════════════════════════════════════════════════════

    INPUT_FIELD_MIN_HEIGHT: str = "12px"
    INPUT_FIELD_MAX_HEIGHT: str = "18px"
    BUTTON_DEFAULT_MIN_HEIGHT: str = "12px"
    ITEM_DEFAULT_HEIGHT: str = "12px"

    CHECKBOX_INDICATOR_SIZE: str = "12px"
    RADIO_BUTTON_INDICATOR_SIZE: str = "12px"

    COLOR_BUTTON_HEX_INPUT_HEIGHT: str = "18px"
    COLOR_BUTTON_COPY_BUTTON_SIZE: str = "20px"
    COLOR_BUTTON_COPY_ICON_SIZE: str = "10px"

    APP_BAR_MIN_HEIGHT: str = "35px"

    SCROLL_BAR_VERTICAL_WIDTH: str = "8px"

    # ════════════════════════════════════════════════════════════
    # BORDAS — TODAS COM UNIDADE
    # ════════════════════════════════════════════════════════════

    PXBORDER_ONE: str = "1px solid"

    CHECKBOX_BORDER_WIDTH: str = "1px"

    # ════════════════════════════════════════════════════════════
    # BORDER RADIUS — TODOS COM UNIDADE
    # ════════════════════════════════════════════════════════════

    BORDER_RADIUS_INPUT_FIELD: str = "4px"
    BORDER_RADIUS_BUTTON_DEFAULT: str = "6px"
    BORDER_RADIUS_CHECKBOX: str = "3px"
    BORDER_RADIUS_RADIO_BUTTON: str = "6px"
    BORDER_RADIUS_CONTAINER_MAIN: str = "8px"
    BORDER_RADIUS_SMALL_COMPONENT: str = "2px"
    BORDER_RADIUS_SCROLL_BAR_HANDLE: str = "4px"
    BORDER_RADIUS_COLLAPSIBLE_HEADER: str = "6px"

    CONTAINER_MAIN_BORDER_SIZE: str = "3px"

    # ════════════════════════════════════════════════════════════
    # PADDINGS — TODOS COM UNIDADE
    # ════════════════════════════════════════════════════════════

    PADDING_INPUT_FIELD: str = "2px 8px"
    PADDING_INPUT_FIELD_RIGHT_EXTRA: str = "18px"
    PADDING_BUTTON_DEFAULT: str = "4px 12px"
    PADDING_BUTTON_SMALL: str = "4px 14px"
    PADDING_PANEL_CONTENT: str = "8px"
    PADDING_LIST_ITEM: str = "4px"

    # ════════════════════════════════════════════════════════════
    # SEPARADOR
    # ════════════════════════════════════════════════════════════

    SEPARATOR_LINE_HEIGHT: str = "3px"
    SEPARATOR_LINE_MARGIN: str = "4px 0px"

    # ════════════════════════════════════════════════════════════
    # ESPAÇAMENTOS
    # ════════════════════════════════════════════════════════════

    LAYOUT_VERTICAL_SPACING: int = 2
    LAYOUT_HORIZONTAL_SPACING: int = 2
    CHECKBOX_LABEL_SPACING: str = "6px"
    SPINBOX_ARROW_BUTTON_WIDTH: str = "16px"

    # ════════════════════════════════════════════════════════════
    # FLAGS BOOLEANAS PARA EFEITOS VISUAIS
    # ════════════════════════════════════════════════════════════

    ALLOW_COMPONENT_SHADOW: bool = True
    ALLOW_COMPONENT_GLOW: bool = False

    # ════════════════════════════════════════════════════════════
    # PROPRIEDADES COMPUTADAS
    # ════════════════════════════════════════════════════════════

    @property
    def BOX_SHADOW_COMPONENT(self) -> str:
        """Sombra para painéis e containers (se ALLOW_COMPONENT_SHADOW=True)."""
        if self.ALLOW_COMPONENT_SHADOW:
            return "0px 0px 6px rgba(0,0,0,0.4)"
        return "none"

    @property
    def COLLAPSIBLE_HEADER_BUTTON_BACKGROUND(self) -> str:
        return "transparent"

    @property
    def COLLAPSIBLE_HEADER_BUTTON_BORDER(self) -> str:
        return "none"

    @property
    def APP_BAR_TITLE_FONT_WEIGHT(self) -> str:
        return "bold"

    @property
    def APP_BAR_RUN_BUTTON_FONT_WEIGHT(self) -> str:
        return "bold"
```

### 6.3 Atualizar `ThemeManager.py` (Apenas BaseTheme)

```python
# resources/styles/ThemeManager.py
# -*- coding: utf-8 -*-
"""
ThemeManager — Gerenciador central de temas
=============================================
Usado pelo NOVO sistema (AppStyles, new_widgets).
Mantém instância ÚNICA de BaseTheme (sem temas filhos por enquanto).

O sistema antigo (BaseStyles) usa current_theme = CoffeTheme() direto.

Uso:
    from resources.styles.ThemeManager import theme_manager
    theme_manager.COLOR_BACKGROUND_MAIN
"""

from __future__ import annotations
from typing import Any
from .BaseTheme import BaseTheme


class ThemeManager:
    """
    Gerenciador singleton de tema.
    Mantém instância ÚNICA de BaseTheme.
    Quando o sistema estiver completamente modificado,
    poderemos adicionar temas filhos (DarkTheme, LightTheme, etc.).
    """

    _instance: ThemeManager | None = None
    _theme: BaseTheme | None = None

    def __new__(cls) -> ThemeManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._theme = BaseTheme()
        return cls._instance

    @property
    def theme(self) -> BaseTheme:
        """Retorna a instância do tema atual."""
        return self._theme

    def reload_theme(self) -> None:
        """Recria a instância do tema."""
        self._theme = BaseTheme()

    @property
    def current_info(self) -> dict[str, Any]:
        """Metadados do tema atual."""
        return {
            "name": "BaseTheme",
            "description": "Tema padrão do Cadmus",
            "version": "1.0.0",
        }

    def _sync_attributes(self) -> None:
        """
        Sincroniza tokens do tema como atributos diretos do ThemeManager.
        Permite acesso via: theme_manager.COLOR_PRIMARY
        """
        for attr_name in dir(self._theme):
            if attr_name.startswith("_"):
                continue
            attr_value = getattr(self._theme, attr_name)
            if callable(attr_value):
                continue
            setattr(self, attr_name, attr_value)


# ── Singleton pré-instanciado ──────────────────────────────────
theme_manager: ThemeManager = ThemeManager()
```

### 6.4 Criar `resources/styles/AppStyles.py`

```python
# resources/styles/AppStyles.py
# -*- coding: utf-8 -*-
"""
AppStyles — Estilos GLOBAIS do Cadmus
======================================
Ponto único de estilos visuais GLOBAIS.
Lê tokens do ThemeManager (cada token já contém unidade: "4px").

NUNCA use px nos estilos — tokens do tema já têm unidade.
NUNCA use 't' — use 'theme' sempre.

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
        theme = cls._get_theme()
        return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {theme.COLOR_PRIMARY},
                stop:1 {theme.COLOR_PRIMARY_DARK});
            color: {theme.COLOR_BUTTON_TEXT};
            border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY_DARK};
            border-radius: {theme.BORDER_RADIUS_BUTTON_DEFAULT};
            padding: {theme.PADDING_BUTTON_DEFAULT};
            min-height: {theme.BUTTON_DEFAULT_MIN_HEIGHT};
        }}
        QPushButton:hover {{
            background: {theme.COLOR_PRIMARY_LIGHT};
        }}
        QPushButton:pressed {{
            background: {theme.COLOR_PRIMARY_DARK};
        }}
        QPushButton:disabled {{
            background: {theme.COLOR_BACKGROUND_SOFT};
            color: {theme.COLOR_TEXT_SECONDARY};
        }}
        """

    @classmethod
    def label(cls) -> str:
        theme = cls._get_theme()
        return f"""
        QLabel {{
            color: {theme.COLOR_TEXT_PRIMARY};
            font-family: {theme.FONT_FAMILY_DEFAULT};
            font-size: {theme.FONT_SIZE_LABEL_TEXT};
        }}
        """

    @classmethod
    def input(cls) -> str:
        theme = cls._get_theme()
        return f"""
        QLineEdit,
        QSpinBox,
        QDoubleSpinBox {{
            background: {theme.COLOR_BACKGROUND_PANEL};
            color: {theme.COLOR_TEXT_PRIMARY};
            border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
            border-radius: {theme.BORDER_RADIUS_INPUT_FIELD};
            padding: {theme.PADDING_INPUT_FIELD};
            min-height: {theme.INPUT_FIELD_MIN_HEIGHT};
            max-height: {theme.INPUT_FIELD_MAX_HEIGHT};
        }}
        QLineEdit:focus,
        QSpinBox:focus,
        QDoubleSpinBox:focus {{
            border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY};
        }}
        """

    @classmethod
    def checkbox(cls) -> str:
        theme = cls._get_theme()
        return f"""
        QCheckBox {{
            color: {theme.COLOR_TEXT_PRIMARY};
            font-family: {theme.FONT_FAMILY_DEFAULT};
            font-size: {theme.FONT_SIZE_LABEL_TEXT};
            spacing: {theme.CHECKBOX_LABEL_SPACING};
        }}
        QCheckBox::indicator {{
            width: {theme.CHECKBOX_INDICATOR_SIZE};
            height: {theme.CHECKBOX_INDICATOR_SIZE};
            border-radius: {theme.BORDER_RADIUS_CHECKBOX};
            border: {theme.CHECKBOX_BORDER_WIDTH} {theme.COLOR_BORDER_DEFAULT};
            background: {theme.COLOR_CHECKBOX_BACKGROUND};
        }}
        QCheckBox::indicator:checked {{
            background: {theme.COLOR_PRIMARY};
            border: {theme.CHECKBOX_BORDER_WIDTH} {theme.COLOR_PRIMARY_DARK};
        }}
        """

    @classmethod
    def radio_button(cls) -> str:
        theme = cls._get_theme()
        return f"""
        QRadioButton {{
            color: {theme.COLOR_TEXT_PRIMARY};
            font-family: {theme.FONT_FAMILY_DEFAULT};
            font-size: {theme.FONT_SIZE_LABEL_TEXT};
            spacing: {theme.CHECKBOX_LABEL_SPACING};
        }}
        QRadioButton::indicator {{
            width: {theme.RADIO_BUTTON_INDICATOR_SIZE};
            height: {theme.RADIO_BUTTON_INDICATOR_SIZE};
            border-radius: {theme.BORDER_RADIUS_RADIO_BUTTON};
            border: {theme.CHECKBOX_BORDER_WIDTH} {theme.COLOR_BORDER_DEFAULT};
            background: {theme.COLOR_BACKGROUND_PANEL};
        }}
        QRadioButton::indicator:checked {{
            background: {theme.COLOR_PRIMARY};
        }}
        """

    @classmethod
    def spinbox(cls) -> str:
        theme = cls._get_theme()
        return f"""
        QSpinBox,
        QDoubleSpinBox {{
            background: {theme.COLOR_BACKGROUND_PANEL};
            color: {theme.COLOR_TEXT_PRIMARY};
            font-family: {theme.FONT_FAMILY_DEFAULT};
            font-size: {theme.FONT_SIZE_INPUT_TEXT};
            border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
            border-radius: {theme.BORDER_RADIUS_INPUT_FIELD};
            min-height: {theme.INPUT_FIELD_MIN_HEIGHT};
            padding: {theme.PADDING_INPUT_FIELD};
            padding-right: {theme.PADDING_INPUT_FIELD_RIGHT_EXTRA};
        }}
        QSpinBox:hover,
        QDoubleSpinBox:hover {{
            border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY_LIGHT};
        }}
        QSpinBox:focus,
        QDoubleSpinBox:focus {{
            border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY};
        }}
        QSpinBox:disabled,
        QDoubleSpinBox:disabled {{
            background: {theme.COLOR_BACKGROUND_SOFT};
            color: {theme.COLOR_TEXT_SECONDARY};
        }}
        QSpinBox::up-button,
        QSpinBox::down-button,
        QDoubleSpinBox::up-button,
        QDoubleSpinBox::down-button {{
            width: {theme.SPINBOX_ARROW_BUTTON_WIDTH};
            height: {theme.INPUT_FIELD_MIN_HEIGHT};
            border-radius: {theme.BORDER_RADIUS_SMALL_COMPONENT};
            border-left: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
            background: {theme.COLOR_PRIMARY};
            padding: 0px;
            margin: 0px;
        }}
        QSpinBox::up-button:hover,
        QSpinBox::down-button:hover,
        QDoubleSpinBox::up-button:hover,
        QDoubleSpinBox::down-button:hover {{
            background: {theme.COLOR_PRIMARY_LIGHT};
        }}
        QSpinBox::up-button:pressed,
        QSpinBox::down-button:pressed,
        QDoubleSpinBox::up-button:pressed,
        QDoubleSpinBox::down-button:pressed {{
            background: {theme.COLOR_PRIMARY_DARK};
        }}
        """

    @classmethod
    def map_layer_combobox(cls) -> str:
        theme = cls._get_theme()
        return f"""
        QgsMapLayerComboBox {{
            background: {theme.COLOR_BACKGROUND_PANEL};
            color: {theme.COLOR_TEXT_PRIMARY};
            border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
            border-radius: {theme.BORDER_RADIUS_INPUT_FIELD};
            padding: {theme.PADDING_INPUT_FIELD};
            min-height: {theme.INPUT_FIELD_MIN_HEIGHT};
        }}
        QgsMapLayerComboBox:hover {{
            border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY_LIGHT};
        }}
        """

    @classmethod
    def scroll_area(cls) -> str:
        theme = cls._get_theme()
        return f"""
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollBar:vertical {{
            width: {theme.SCROLL_BAR_VERTICAL_WIDTH};
            background: transparent;
        }}
        QScrollBar::handle:vertical {{
            background: {theme.COLOR_PRIMARY};
            border-radius: {theme.BORDER_RADIUS_SCROLL_BAR_HANDLE};
        }}
        QScrollBar::handle:vertical:hover {{
            background: {theme.COLOR_PRIMARY_LIGHT};
        }}
        """

    @classmethod
    def separator(cls) -> str:
        theme = cls._get_theme()
        return f"""
        QFrame {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {theme.COLOR_BACKGROUND_PANEL},
                stop:0.5 {theme.COLOR_PRIMARY},
                stop:1 {theme.COLOR_BACKGROUND_PANEL});
            height: {theme.SEPARATOR_LINE_HEIGHT};
            border: none;
            margin: {theme.SEPARATOR_LINE_MARGIN};
        }}
        """

    @classmethod
    def main_application(cls) -> str:
        theme = cls._get_theme()
        return f"""
        #main_container {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 {theme.COLOR_BACKGROUND_MAIN},
                stop:0.5 {theme.COLOR_BACKGROUND_PANEL},
                stop:1 {theme.COLOR_BACKGROUND_MAIN});
            border: {theme.CONTAINER_MAIN_BORDER_SIZE} {theme.COLOR_BORDER_DEFAULT};
            border-radius: {theme.BORDER_RADIUS_CONTAINER_MAIN};
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
        theme = cls._get_theme()
        return f"""
        #app_bar {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {theme.COLOR_PRIMARY_DARK},
                stop:1 {theme.COLOR_PRIMARY});
            border-bottom: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
            border-radius: {theme.BORDER_RADIUS_RADIO_BUTTON};
            min-height: {theme.APP_BAR_MIN_HEIGHT};
        }}
        #app_bar_title {{
            color:{theme.COLOR_TEXT_PRIMARY};
            font-weight:{theme.APP_BAR_TITLE_FONT_WEIGHT};
            font-size:{theme.FONT_SIZE_APP_BAR_TITLE};
        }}
        QPushButton#app_bar_btn_run {{
            background:{theme.COLOR_PRIMARY};
            border: {theme.PXBORDER_ONE} {theme.COLOR_PRIMARY_DARK};
            padding: {theme.PADDING_BUTTON_SMALL};
            font-weight:{theme.APP_BAR_RUN_BUTTON_FONT_WEIGHT};
            font-size:{theme.FONT_SIZE_BUTTON_TEXT};
        }}
        QPushButton#app_bar_btn_run:hover {{
            background:{theme.COLOR_PRIMARY_LIGHT};
        }}
        QPushButton#app_bar_btn_info {{
            background:{theme.COLOR_APP_BAR_INFO_BUTTON_BACKGROUND};
            color:{theme.COLOR_TEXT_SECONDARY};
            border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
        }}
        QPushButton#app_bar_btn_info:hover {{
            background:{theme.COLOR_APP_BAR_INFO_BUTTON_HOVER_BACKGROUND};
        }}
        QPushButton#app_bar_btn_close {{
            background:transparent;
            border:none;
            font-size:{theme.FONT_SIZE_APP_BAR_CLOSE_BUTTON};
        }}
        """

    @classmethod
    def panel(cls) -> str:
        theme = cls._get_theme()
        return f"""
        QFrame {{
            background:{theme.COLOR_BACKGROUND_SOFT};
            border-radius: {theme.BORDER_RADIUS_BUTTON_DEFAULT};
            padding: {theme.PADDING_PANEL_CONTENT};
        }}
        """

    @classmethod
    def collapsible_parameters(cls) -> str:
        theme = cls._get_theme()
        return f"""
        #collapsible_header {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {theme.COLOR_COLLAPSIBLE_HEADER_START_GRADIENT},
                stop:1 {theme.COLOR_COLLAPSIBLE_HEADER_END_GRADIENT});
            border-bottom: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
            border-radius: {theme.BORDER_RADIUS_COLLAPSIBLE_HEADER} {theme.BORDER_RADIUS_COLLAPSIBLE_HEADER} 0 0;
        }}
        #collapsible_header:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {theme.COLOR_COLLAPSIBLE_HEADER_HOVER_START_GRADIENT},
                stop:1 {theme.COLOR_COLLAPSIBLE_HEADER_HOVER_END_GRADIENT});
        }}
        #collapsible_icon {{
            color: {theme.COLOR_TEXT_PRIMARY};
            font-weight: bold;
            font-size: {theme.FONT_SIZE_SECTION_TITLE};
            qproperty-alignment: AlignCenter;
        }}
        #collapsible_title {{
            color: {theme.COLOR_TEXT_PRIMARY};
            font-weight: bold;
            font-size: {theme.FONT_SIZE_LABEL_TEXT};
            font-family: {theme.FONT_FAMILY_DEFAULT};
            background: transparent;
        }}
        #collapsible_header_btn {{
            background: {theme.COLLAPSIBLE_HEADER_BUTTON_BACKGROUND};
            border: {theme.COLLAPSIBLE_HEADER_BUTTON_BORDER};
            padding: 0px;
            margin: 0px;
        }}
        #collapsible_content {{
            background: {theme.COLOR_BACKGROUND_SOFT};
            border-bottom: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
            border-left: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
            border-right: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
            border-radius: 0 0 {theme.BORDER_RADIUS_BUTTON_DEFAULT} {theme.BORDER_RADIUS_BUTTON_DEFAULT};
        }}
        """

    @classmethod
    def calc_checkbox_grid_height(cls, num_items: int, items_per_row: int = 1) -> int:
        theme = cls._get_theme()
        rows = (num_items + items_per_row - 1) // items_per_row
        item_h = int(theme.ITEM_DEFAULT_HEIGHT.replace("px", ""))
        spacing = theme.LAYOUT_VERTICAL_SPACING
        return (rows * item_h) + ((rows - 1) * spacing)
```

---

## 7. FASE 1 — Criação dos Widgets

### 7.1 Widgets Simple (USO INTERNO APENAS)

Criados em `resources/new_widgets/simple/`. Estes widgets TEM versão grid.  
**NUNCA** importados por plugins. Usados APENAS internamente por Grid e widgets da raiz.

| Arquivo | Classe | Descrição |
|---------|--------|-----------|
| `SimpleLabel.py` | `SimpleLabel` | QLabel + AppStyles.label() |
| `SimpleInput.py` | `SimpleInput` | QLineEdit + AppStyles.input() |
| `SimpleButton.py` | `SimpleButton` | QPushButton + AppStyles.button() |
| `SimpleComboBox.py` | `SimpleComboBox` | QComboBox + AppStyles.input() |
| `SimpleSpinBox.py` | `SimpleSpinBox` | QDoubleSpinBox + AppStyles.spinbox() |
| `SimpleCheckbox.py` | `SimpleCheckbox` | QCheckBox + AppStyles.checkbox() |
| `SimpleRadioButton.py` | `SimpleRadioButton` | QRadioButton + AppStyles.radio_button() |

### 7.2 Widgets Grid (PLUGINS USAM ESTES)

Criados em `resources/new_widgets/grid/`. Compostos de Simple + layout.

| Arquivo | Classe | Descrição |
|---------|--------|-----------|
| `GridLabel.py` | `GridLabel` | 1+ labels em grid |
| `GridInput.py` | `GridInput` | 1+ inputs em grid |
| `GridCheckbox.py` | `GridCheckbox` | Grid de checkboxes |
| `GridRadioButton.py` | `GridRadioButton` | Grid de radio buttons |
| `GridLayerInput.py` | `GridLayerInput` | Label + combobox + checkbox |
| `GridButton.py` | `GridButton` | Grid de botões (bottom actions) |
| `GridReadOnly.py` | `GridReadOnly` | Campos read-only |
| `GridDropdown.py` | `GridDropdown` | Label + dropdown |

### 7.3 Widgets na Raiz (SEM versão grid)

Criados em `resources/new_widgets/`. Nomenclatura "Complex" indica widget composto, mas fica na raiz pois não há versão grid.

| Arquivo | Classe | Descrição |
|---------|--------|-----------|
| `SeparatorWidget.py` | `SeparatorWidget` | QFrame separador visual (gradiente) |
| `AppBarWidget.py` | `AppBarWidget` | Barra superior |
| `CollapsibleParametersWidget.py` | `CollapsibleParametersWidget` | Conteúdo colapsável |
| `ComplexPathSelector.py` | `ComplexPathSelector` | Título + path + botões |
| `ComplexColorPicker.py` | `ComplexColorPicker` | Título + color + hex |
| `ComplexCrsSelector.py` | `ComplexCrsSelector` | Título + CRS |
| `GridComplexSelector.py` | `GridComplexSelector` | Grid de selectors complexos |

### 7.4 SeparatorWidget — Widget Visual Separado

```python
# resources/new_widgets/SeparatorWidget.py
# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import QFrame
from ...resources.styles.AppStyles import AppStyles


class SeparatorWidget(QFrame):
    """
    Separador visual — QFrame HLine com gradiente.
    
    É um widget Qt separado, NÃO uma margem/padding.
    O plugin insere entre widgets no layout:
    
        layout.addWidget(widget1)
        layout.addWidget(SeparatorWidget())
        layout.addWidget(widget2)
    
    Parâmetros
    ----------
    height : str, optional
        Altura do separador (default: theme.SEPARATOR_LINE_HEIGHT)
    parent : QWidget, optional
        Widget pai
    """

    def __init__(self, height: str = None, parent=None):
        super().__init__(parent)
        
        # Compatibilidade Qt5/Qt6 para QFrame.Shape
        try:
            shape_hline = QFrame.Shape.HLine
        except AttributeError:
            shape_hline = QFrame.HLine
        
        try:
            shadow_sunken = QFrame.Shadow.Sunken
        except AttributeError:
            shadow_sunken = QFrame.Sunken
        
        self.setFrameShape(shape_hline)
        self.setFrameShadow(shadow_sunken)
        
        theme = AppStyles._get_theme()
        h = height or theme.SEPARATOR_LINE_HEIGHT
        h_int = int(h.replace("px", ""))
        self.setFixedHeight(h_int)
        self.setStyleSheet(AppStyles.separator())
```

### 7.5 Template de Widget Grid

```python
# resources/new_widgets/grid/GridExemplo.py
# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout
from ....core.config.LogUtils import LogUtils
from ....utils.ToolKeys import ToolKey
from ....resources.styles.AppStyles import AppStyles


class GridExemplo(QWidget):
    """
    [Descrição]
    
    Parâmetros
    ----------
    [param1] : type
        [descrição]
    parent : QWidget, optional
        Widget pai
    
    Autoconfiguração
    ----------------
    - AppStyles: métodos globais
    - _specific_style(): estilo específico
    """

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self._params = kwargs

        self.logger = LogUtils(
            tool=ToolKey.WIDGETS,
            class_name=self.__class__.__name__,
        )
        try:
            self._configure()
            self._apply_styles()
        except Exception as error:
            self.logger.exception(error, code="WIDGET_INIT_ERROR")

    def _configure(self):
        """Monta UI com parâmetros."""
        layout = QVBoxLayout(self)
        # ... criar widgets, montar layout, conectar sinais

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

## 8. FASE 2 — Migração Plugin por Plugin

### 8.1 Ordem

| # | Plugin | Factory (antigo) | new_widgets (novo) |
|---|--------|-----------------|-------------------|
| 1 | `AboutDialog` | create_label, create_text_browser, create_image_widget | GridLabel + raiz |
| 2 | `RestartQgis` | create_simple_button | GridButton |
| 3 | `CoorResultDialog` | create_label, create_readonly_field, create_bottom_action_buttons | GridReadOnly + GridButton |
| 4 | `VectorMultipartPlugin` | create_layer_input, create_bottom_action_buttons | GridLayerInput + GridButton |
| 5 | `ExportAllLayouts` | create_readonly_field, create_bottom_action_buttons | GridReadOnly + GridButton |
| 6 | `CopyAttributesPlugin` | create_layer_input, create_checkbox_grid, create_bottom_action_buttons | GridLayerInput + GridCheckbox + GridButton |
| 7 | `DividePointsByStripsPlugin` | create_layer_input, create_input_fields, create_bottom_action_buttons | GridLayerInput + GridInput + GridButton |
| 8 | `DroneCoordinates` | create_label, create_double_spin_input | GridInput |
| 9 | `LoadFolderLayers` | create_path_selector, create_checkbox_grid, create_bottom_action_buttons | ComplexPathSelector + GridCheckbox + GridButton |
| 10 | `PathExtensionPlugin` | create_layer_input, create_dropdown_selector, create_radio_button_grid, create_bottom_action_buttons | GridLayerInput + GridDropdown + GridRadioButton + GridButton |
| 11 | `ReplaceInLayouts` | create_layer_input, create_dropdown_selector, create_bottom_action_buttons | GridLayerInput + GridDropdown + GridButton |
| 12 | `SaveTemporaryLayersPlugin` | create_path_selector, create_layer_input, create_bottom_action_buttons | ComplexPathSelector + GridLayerInput + GridButton |
| 13 | `GenerateTrailPlugin` | create_layer_input, create_dropdown_selector, create_input_fields, create_color_button, create_bottom_action_buttons | GridLayerInput + GridDropdown + GridInput + ComplexColorPicker + GridButton |
| 14 | `ReportMetadataPlugin` | create_path_selector, create_layer_input, create_checkbox_grid, create_bottom_action_buttons | ComplexPathSelector + GridLayerInput + GridCheckbox + GridButton |
| 15 | `VectorFieldsCalculationPlugin` | create_layer_input, create_dropdown_selector, create_input_fields, create_bottom_action_buttons | GridLayerInput + GridDropdown + GridInput + GridButton |
| 16 | `VectorToSvgPlugin` | create_path_selector, create_layer_input, create_checkbox_grid, create_bottom_action_buttons | ComplexPathSelector + GridLayerInput + GridCheckbox + GridButton |
| 17 | `SettingsPlugin` | Múltiplos | Análise individual |

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

### 8.3 Exemplo: PathExtensionPlugin

```python
# plugins/PathExtensionPlugin.py

from ..resources.new_widgets.grid.GridLayerInput import GridLayerInput
from ..resources.new_widgets.grid.GridDropdown import GridDropdown
from ..resources.new_widgets.grid.GridRadioButton import GridRadioButton
from ..resources.new_widgets.grid.GridButton import GridButton
from ..resources.new_widgets.SeparatorWidget import SeparatorWidget


class PathExtensionPlugin(BasePluginMTL):
    def _build_ui(self, **kwargs):
        super()._build_ui(title=STR.PATH_EXTENSION_TITLE, enable_scroll=True)

        self.layer_input = GridLayerInput(
            label_text=STR.INPUT_LAYER,
            filters=[QgsMapLayerProxyModel.Filter.VectorLayer],
            allow_empty=False,
            parent=self,
        )

        self.attr_selector = GridDropdown(
            title=f"{STR.PATH}:",
            options_dict={},
            allow_empty=True,
            empty_text=STR.SELECT,
            parent=self,
        )

        self.radio_mode = GridRadioButton(
            items=[STR.MODE_REMOVE, STR.MODE_RESTORE,
                   STR.MODE_ZIP, STR.MODE_UNZIP],
            columns=2,
            checked_index=0,
            tool_key=self.TOOL_KEY,
            parent=self,
        )

        self.action_buttons = GridButton(
            parent=self,
            run_callback=self.execute_tool,
            close_callback=self.close,
            info_callback=self.show_info_dialog,
            tool_key=self.TOOL_KEY,
        )

        # Layout com separadores entre widgets
        self.layout.addWidget(self.layer_input)
        self.layout.addWidget(SeparatorWidget())
        self.layout.addWidget(self.attr_selector)
        self.layout.addWidget(SeparatorWidget())
        self.layout.addWidget(self.radio_mode)
        self.layout.addWidget(SeparatorWidget())
        self.layout.addWidget(self.action_buttons)
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
```

### 11.2 Onde Aplicar

- `new_widgets/` — todos os widgets
- `AppStyles` — seguro (só strings CSS)
- `SeparatorWidget` — precisa de compat QFrame.Shape e QFrame.Shadow
- `BaseDialog.py` — já tem compat

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
[ ] FASE 0: Fundação
  [ ] 0.1 BaseTheme já limpo ✅
  [ ] 0.2 Adicionar tokens descritivos no BaseTheme.py
  [ ] 0.3 Atualizar ThemeManager.py (apenas BaseTheme, sem temas filhos)
  [ ] 0.4 Criar resources/styles/AppStyles.py
  [ ] 0.5 Criar utils/qt_compat.py
  [ ] 0.6 Testar AppStyles + ThemeManager + BaseTheme

[ ] FASE 1: Criação dos Widgets
  [ ] 1.1 Simple (USO INTERNO)
    [ ] SimpleLabel.py
    [ ] SimpleInput.py
    [ ] SimpleButton.py
    [ ] SimpleComboBox.py
    [ ] SimpleSpinBox.py
    [ ] SimpleCheckbox.py
    [ ] SimpleRadioButton.py
  [ ] 1.2 Grid (PLUGINS USAM)
    [ ] GridLabel.py
    [ ] GridInput.py
    [ ] GridCheckbox.py
    [ ] GridRadioButton.py
    [ ] GridLayerInput.py
    [ ] GridButton.py
    [ ] GridReadOnly.py
    [ ] GridDropdown.py
  [ ] 1.3 Raiz (SEM versão grid)
    [ ] SeparatorWidget.py
    [ ] AppBarWidget.py
    [ ] CollapsibleParametersWidget.py
    [ ] ComplexPathSelector.py
    [ ] ComplexColorPicker.py
    [ ] ComplexCrsSelector.py
    [ ] GridComplexSelector.py
  [ ] 1.4 resources/new_widgets/__init__.py

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
  [ ] 3.3 Criar docs/skills/SKILL_WIDGETS2.md
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
| 2026-07-21 | 4.0.0 | **Correções:** Separador é QFrame visual (não margem), `SeparatorWidget` separado, ThemeManager só com BaseTheme (sem temas filhos), BaseTheme é o tema ÚNICO, Qt5/Qt6 compat via try/except |