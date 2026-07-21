# 🎯 PLANO DE AÇÃO: Eliminação da WidgetFactory

**Objetivo:** Eliminar completamente o uso da `WidgetFactory`, migrando para um modelo onde widgets se autoconfiguram com `AppStyles` + `ThemeManager`, e plugins declaram widgets via parâmetros/dict sem saber de estilos.

**Data:** 2026-07-21
**Versão:** 1.0.0
**Autor:** Cadmus Engineering

---

## Sumário

1. [Arquitetura Atual](#1-arquitetura-atual)
2. [Arquitetura Alvo](#2-arquitetura-alvo)
3. [FASE 0 — Fundação](#3-fase-0--fundação)
4. [FASE 1 — Migração Plugin por Plugin](#4-fase-1--migração-plugin-por-plugin)
5. [FASE 2 — Refatoração dos Widgets](#5-fase-2--refatoração-dos-widgets)
6. [FASE 3 — Eliminação da WidgetFactory](#6-fase-3--eliminação-da-widgetfactory)
7. [Contrato do Widget Autoconfigurável](#7-contrato-do-widget-autoconfigurável)
8. [Compatibilidade Qt5/Qt6](#8-compatibilidade-qt5qt6)
9. [Riscos e Mitigações](#9-riscos-e-mitigações)
10. [TODO Interno Consolidado](#10-todo-interno-consolidado)

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
  └─ herda BaseStyles (resources/styles/BaseStyles.py)
      └─ importa current_theme de ThemeManager (variável de módulo)
          └─ ThemeManager.theme → CoffeTheme (instância concreta)

BaseStyles
  ├─ Atributos de classe: COLOR_PRIMARY, FONT_SIZE_NORMAL, etc.
  │   └─ Lidos de current_theme (resolvido na importação!)
  └─ Métodos estáticos: button(), label(), input(), checkbox(), etc.
      └─ Usam current_theme direto (também variável de módulo)
```

### Problemas Identificados

| # | Problema | Impacto |
|---|----------|---------|
| 1 | `BaseStyles` copia tokens do tema como atributos de classe (`COLOR_PRIMARY = current_theme.COLOR_PRIMARY`) | Resolvido na importação — se tema mudar em runtime, atributos ficam desatualizados |
| 2 | `Styles` + `BaseStyles` são 2 arquivos com responsabilidade duplicada | Manutenção confusa, viola DRY |
| 3 | `WidgetFactory` tem 1135 linhas e faz TUDO: cria widget + layout + estilo + separadores + conecta sinais | Violação SRP, difícil testar, difícil manter |
| 4 | Plugin recebe `(layout, widget)` da Factory e precisa gerenciar layout externo | Acoplamento, plugin sabe de estrutura de layout |
| 5 | Estilos específicos de widget misturados com estilos globais em `Styles.py` | Widget não é autossuficiente |
| 6 | `current_theme` é variável de módulo em `BaseStyles.py` | Se ThemeManager recarregar tema, BaseStyles não atualiza |

---

## 2. Arquitetura Alvo

### Diagrama de Dependências (Novo)

```
Plugin
  └─ importa widget direto de resources/widgets/
      └─ widget.__init__(params, parent)
          ├─ self._configure(params) → aplica parâmetros
          ├─ self._apply_styles()
          │   ├─ AppStyles.global_style() → estilos globais (botão, input, label...)
          │   ├─ ThemeManager.current_theme → cores, fontes, dimensões
          │   └─ self._specific_style() → estilo próprio do widget
          └─ self.logger (inicializado no __init__)

AppStyles (resources/styles/AppStyles.py)
  ├─ Singleton: lê de ThemeManager.current_theme
  ├─ Só métodos estáticos GLOBAIS: button(), label(), input(), checkbox(), etc.
  └─ SEM atributos de classe copiados do tema

ThemeManager (resources/styles/ThemeManager.py)
  └─ Mantido como está (singleton, reload_theme())
      └─ AppStyles._get_theme() → theme_manager.theme

Widget (cada widget em resources/widgets/)
  ├─ __init__(self, parent=None, **kwargs)
  │   ├─ self._params = kwargs
  │   ├─ self.logger = LogUtils(...)
  │   ├─ self._configure()
  │   └─ self._apply_styles()
  ├─ _configure() → monta UI com params
  ├─ _apply_styles() → AppStyles + específico
  └─ _specific_style() → str (opcional)
```

### Fluxo de Autoconfiguração

```
Plugin declara:
    widget = LayerInputWidget(
        label_text=STR.INPUT_LAYER,
        filters=[VectorLayer],
        parent=self,
    )

Dentro de LayerInputWidget.__init__():
    1. self._params = {label_text, filters, parent}
    2. self.logger = LogUtils(tool=..., class_name="LayerInputWidget")
    3. self._configure():
        - Cria QLabel(label_text)
        - Cria QgsMapLayerComboBox()
        - Cria QCheckBox()
        - Monta layout
    4. self._apply_styles():
        - AppStyles.label() → QLabel
        - AppStyles.map_layer_combobox() → QComboBox
        - AppStyles.checkbox() → QCheckBox
        - self._specific_style() → margens, padding extra
    5. Pronto! Plugin só dá addWidget()
```

---

## 3. FASE 0 — Fundação

### 3.1 Criar `resources/styles/AppStyles.py`

**Arquivo novo** que unifica `Styles` + `BaseStyles` em um único ponto de estilos globais.

**Regras:**
- Só contém métodos de estilo **global** (aplicáveis a qualquer widget do sistema)
- **NÃO** contém estilos específicos de widget (ex: `path_selector_widget()`, `attribute_selector()`)
- Lê tokens direto de `ThemeManager.current_theme` em cada chamada de método
- **NÃO** copia tokens como atributos de classe
- Usa cache interno com invalidação via `reload_theme()`

**Métodos que vão para AppStyles:**

| Método | Origem | Descrição |
|--------|--------|-----------|
| `button()` | BaseStyles | QPushButton global |
| `label()` | BaseStyles | QLabel global |
| `input()` | BaseStyles | QLineEdit, QSpinBox, QDoubleSpinBox |
| `checkbox()` | BaseStyles | QCheckBox + indicator |
| `radio_button()` | BaseStyles | QRadioButton + indicator |
| `spinbox()` | BaseStyles | QSpinBox, QDoubleSpinBox (completo) |
| `map_layer_combobox()` | BaseStyles | QgsMapLayerComboBox |
| `scroll_area()` | BaseStyles | QScrollArea + QScrollBar |
| `separator()` | Styles | QFrame separador |
| `main_application()` | Styles | Container principal |
| `app_bar()` | Styles | AppBar gradient |
| `panel()` | Styles | QFrame painel |
| `collapsible_parameters()` | Styles | Header + conteúdo colapsável |
| `calc_checkbox_grid_height()` | Styles | Cálculo de altura |

**Métodos que NÃO vão para AppStyles (ficam no widget como `_specific_style()`):**

| Método Atual | Destino |
|-------------|---------|
| `attribute_selector()` | AttributeSelectorWidget._specific_style() |
| `path_selector_widget()` | SelectorWidget._specific_style() |
| `layer_input_widget()` | LayerInputWidget._specific_style() |
| `radio_button_grid_widget()` | RadioButtonGridWidget._specific_style() |
| `grid_checkboxes()` | GridCheckboxWidget._specific_style() |
| `bottom_action_buttons_widget()` | ExecutionButtonsWidget._specific_style() |
| `input_fields_widget()` | GridInputFieldsWidget._specific_style() |
| `dropdown_selector_widget()` | DropdownSelectorWidget._specific_style() |
| `simple_button_widget()` | SimpleButtonWidget._specific_style() |
| `color_button_widget()` | ColorButtonWidget._specific_style() |
| `project_name_dialog()` | ProjectNameDialog._specific_style() |

**Estrutura do AppStyles:**

```python
# resources/styles/AppStyles.py
# -*- coding: utf-8 -*-
"""
AppStyles — Estilos globais do Cadmus
======================================
Ponto único de estilos visuais globais.
Lê tokens diretamente do ThemeManager.current_theme.
Widgets específicos têm seus estilos próprios em _specific_style().

Uso:
    from resources.styles.AppStyles import AppStyles
    style = AppStyles.button()
"""

from __future__ import annotations

from typing import ClassVar, Optional


class AppStyles:
    """Estilos globais reutilizáveis entre todos os widgets."""

    _theme: ClassVar[Optional[object]] = None

    @classmethod
    def _get_theme(cls):
        """Retorna o tema atual, com cache."""
        if cls._theme is None:
            from .ThemeManager import theme_manager
            cls._theme = theme_manager.theme
        return cls._theme

    @classmethod
    def reload_theme(cls):
        """Invalida o cache de tema (chamar quando tema mudar)."""
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
            border: 1px solid {t.COLOR_PRIMARY_DARK};
            border-radius: {t.BUTTON_BORDER_RADIUS}px;
            padding: {t.BUTTON_PADDING};
            min-height: {t.BUTTON_HEIGHT}px;
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
            border: 1px solid {t.COLOR_BORDER};
            border-radius: {t.INPUT_BORDER_RADIUS}px;
            padding: {t.INPUT_PADDING};
            min-height: {t.INPUT_HEIGHT}px;
            max-height: {t.INPUT_HEIGHT + 6}px;
        }}
        QLineEdit:focus,
        QSpinBox:focus,
        QDoubleSpinBox:focus {{
            border: 1px solid {t.COLOR_PRIMARY};
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
            spacing: {t.CHECKBOX_SPACING}px;
        }}
        QCheckBox::indicator {{
            width: {t.CHECKBOX_SIZE}px;
            height: {t.CHECKBOX_SIZE}px;
            border-radius: {t.CHECKBOX_BORDER_RADIUS}px;
            border: {t.CHECKBOX_BORDER_WIDTH}px solid {t.COLOR_BORDER};
            background: {t.COLOR_CHECKBOX_BG};
        }}
        QCheckBox::indicator:checked {{
            background: {t.COLOR_PRIMARY};
            border: {t.CHECKBOX_BORDER_WIDTH}px solid {t.COLOR_PRIMARY_DARK};
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
            spacing: {t.CHECKBOX_SPACING}px;
        }}
        QRadioButton::indicator {{
            width: {t.RADIO_SIZE}px;
            height: {t.RADIO_SIZE}px;
            border-radius: {t.RADIO_BORDER_RADIUS}px;
            border: {t.CHECKBOX_BORDER_WIDTH}px solid {t.COLOR_BORDER};
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
            border: 1px solid {t.COLOR_BORDER};
            border-radius: {t.INPUT_BORDER_RADIUS}px;
            min-height: {t.INPUT_HEIGHT}px;
            padding: 2px 4px;
            padding-right: 18px;
        }}
        QSpinBox:hover,
        QDoubleSpinBox:hover {{
            border: 1px solid {t.COLOR_PRIMARY_LIGHT};
        }}
        QSpinBox:focus,
        QDoubleSpinBox:focus {{
            border: 1px solid {t.COLOR_PRIMARY};
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
            width: 16px;
            height: {t.INPUT_HEIGHT}px;
            border-radius: 2px;
            border-left: 1px solid {t.COLOR_BORDER};
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
            border: 1px solid {t.COLOR_BORDER};
            border-radius: {t.INPUT_BORDER_RADIUS}px;
            padding: {t.INPUT_PADDING};
            min-height: {t.INPUT_HEIGHT}px;
        }}
        QgsMapLayerComboBox:hover {{
            border: 1px solid {t.COLOR_PRIMARY_LIGHT};
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
            width: 8px;
            background: transparent;
        }}
        QScrollBar::handle:vertical {{
            background: {t.COLOR_PRIMARY};
            border-radius: 4px;
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
            height:3px;
            border:none;
            margin:4px 0px;
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
            border:3px solid {t.COLOR_BORDER};
            border-radius:8px;
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
            border-bottom:1px solid {t.COLOR_BORDER};
            border-radius: {t.RADIO_BORDER_RADIUS};
            min-height:35px;
        }}
        #app_bar_title {{
            color:{t.COLOR_TEXT_PRIMARY};
            font-weight:bold;
            font-size:10.5pt;
        }}
        QPushButton#app_bar_btn_run {{
            background:{t.COLOR_PRIMARY};
            border:1px solid {t.COLOR_PRIMARY_DARK};
            padding:4px 14px;
            font-weight:bold;
            font-size:{t.FONT_SIZE_SMALL};
        }}
        QPushButton#app_bar_btn_run:hover {{
            background:{t.COLOR_PRIMARY_LIGHT};
        }}
        QPushButton#app_bar_btn_info {{
            background:{t.COLOR_APPBAR_INFO_BG};
            color:{t.COLOR_TEXT_SECONDARY};
            border:1px solid {t.COLOR_BORDER};
        }}
        QPushButton#app_bar_btn_info:hover {{
            background:{t.COLOR_APPBAR_INFO_BG_HOVER};
        }}
        QPushButton#app_bar_btn_close {{
            background:transparent;
            border:none;
            font-size:14pt;
        }}
        """

    @classmethod
    def panel(cls) -> str:
        t = cls._get_theme()
        return f"""
        QFrame {{
            background:{t.COLOR_BACKGROUND_SOFT};
            border-radius:6px;
            padding:8px;
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
            border-bottom: 1px solid {t.COLOR_BORDER};
            border-radius: 6px 6px 0px 0px;
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
            background:{t.COLOR_BACKGROUND_TRANSPARENT};
            border: none;
            padding: 0px;
            margin: 0px;
        }}
        #collapsible_content {{
            background: {t.COLOR_BACKGROUND_SOFT};
            border-bottom: 1px solid {t.COLOR_BORDER};
            border-left: 1px solid {t.COLOR_BORDER};
            border-right: 1px solid {t.COLOR_BORDER};
            border-radius: 0px 0px 6px 6px;
        }}
        """

    @classmethod
    def calc_checkbox_grid_height(cls, num_items: int, items_per_row: int = 1) -> int:
        t = cls._get_theme()
        rows = (num_items + items_per_row - 1) // items_per_row
        return (rows * t.ITEM_HEIGHT) + ((rows - 1) * t.LAYOUT_V_SPACING)
```

### 3.2 Adaptar `Styles.py` como Ponte de Transição

`Styles.py` passa a herdar de `AppStyles` e manter os métodos específicos de widget como **deprecated**:

```python
# resources/styles/Styles.py
# -*- coding: utf-8 -*-
"""
Styles — Ponte de transição (DEPRECATED)
=========================================
Mantido para compatibilidade durante migração.
Novos códigos devem usar AppStyles diretamente.
Os métodos específicos de widget serão movidos para cada widget.
"""

import warnings
from .AppStyles import AppStyles


class Styles(AppStyles):
    """DEPRECATED: Use AppStyles para estilos globais."""

    # ── Métodos específicos de widget (serão movidos) ──────────

    @staticmethod
    def attribute_selector():
        warnings.warn(
            "Styles.attribute_selector() movido para "
            "AttributeSelectorWidget._specific_style()",
            DeprecationWarning, stacklevel=2,
        )
        return _attribute_selector_style()

    @staticmethod
    def path_selector_widget():
        warnings.warn(
            "Styles.path_selector_widget() movido para "
            "SelectorWidget._specific_style()",
            DeprecationWarning, stacklevel=2,
        )
        return _path_selector_style()

    # ... demais métodos específicos com warnings
```

### 3.3 Adaptar `BaseStyles.py` como Alias

```python
# resources/styles/BaseStyles.py
# -*- coding: utf-8 -*-
"""
BaseStyles — Alias para AppStyles (DEPRECATED)
===============================================
Mantido para compatibilidade. Use AppStyles.
"""

import warnings
from .AppStyles import AppStyles

warnings.warn(
    "BaseStyles foi movido para AppStyles. "
    "Use 'from resources.styles.AppStyles import AppStyles'.",
    DeprecationWarning, stacklevel=2,
)

current_theme = None  # Não use mais — acesse via AppStyles._get_theme()

class BaseStyles(AppStyles):
    """DEPRECATED: Use AppStyles."""
    pass
```

### 3.4 Atualizar `resources/__init__.py`

```python
# resources/__init__.py
from .styles.AppStyles import AppStyles
from .styles.Styles import Styles  # mantido para compatibilidade
from .styles.BaseTheme import BaseTheme
from .styles.CoffeTheme import CoffeTheme
from .styles.ThemeManager import ThemeManager, theme_manager
```

---

## 4. FASE 1 — Migração Plugin por Plugin

### 4.1 Ordem de Migração

Os plugins serão migrados em ordem crescente de complexidade. Cada plugin segue o checklist:

1. Analisar quais widgets o plugin usa
2. Verificar se plugin pode usar grid layout (se tem múltiplos widgets)
3. Verificar se plugin obedece ao contrato (PLUGIN_CONTRACT.md)
4. Verificar se todos os widgets usados têm `self.logger`
5. Migrar plugin para usar widgets diretos (sem Factory)
6. Adaptar AppStyles com métodos necessários (se aplicável)
7. Atualizar changelog

### 4.2 Tabela de Plugins

| # | Plugin | Widgets Usados | Complexidade | Grid? | Logger? | Dependências |
|---|--------|---------------|-------------|-------|---------|-------------|
| 1 | `AboutDialog` | label, text_browser, image_widget | 🔵 Fácil | Não | Sim (herda) | Nenhuma |
| 2 | `RestartQgis` | simple_button | 🔵 Fácil | Não | Sim (herda) | Nenhuma |
| 3 | `CoorResultDialog` | label, readonly_field, bottom_action_buttons | 🔵 Fácil | Sim | Sim (herda) | Nenhuma |
| 4 | `VectorMultipartPlugin` | layer_input, bottom_action_buttons | 🔵 Fácil | Sim | Sim | Nenhuma |
| 5 | `ExportAllLayouts` | readonly_field, bottom_action_buttons | 🔵 Fácil | Não | Sim | Nenhuma |
| 6 | `CopyAttributesPlugin` | layer_input, checkbox_grid, bottom_action_buttons | 🟡 Médio | Sim | Sim | Nenhuma |
| 7 | `DividePointsByStripsPlugin` | layer_input, input_fields, bottom_action_buttons | 🟡 Médio | Sim | Sim | Nenhuma |
| 8 | `DroneCoordinates` | label, double_spin_input, custom | 🟡 Médio | Sim | Sim | Nenhuma |
| 9 | `LoadFolderLayers` | path_selector, checkbox_grid, bottom_action_buttons | 🟡 Médio | Sim | Sim | Nenhuma |
| 10 | `PathExtensionPlugin` | layer_input, dropdown_selector, radio_button_grid, bottom_action_buttons | 🟡 Médio | Sim | Sim | Nenhuma |
| 11 | `ReplaceInLayouts` | layer_input, dropdown_selector, bottom_action_buttons | 🟡 Médio | Sim | Sim | Nenhuma |
| 12 | `SaveTemporaryLayersPlugin` | path_selector, layer_input, bottom_action_buttons | 🟡 Médio | Sim | Sim | Nenhuma |
| 13 | `GenerateTrailPlugin` | layer_input, dropdown_selector, input_fields, color_button, bottom_action_buttons | 🔴 Complexo | Sim | Sim | Nenhuma |
| 14 | `ReportMetadataPlugin` | path_selector, layer_input, checkbox_grid, bottom_action_buttons | 🔴 Complexo | Sim | Sim | Pipeline |
| 15 | `VectorFieldsCalculationPlugin` | layer_input, dropdown_selector, input_fields, bottom_action_buttons | 🔴 Complexo | Sim | Sim | Nenhuma |
| 16 | `VectorToSvgPlugin` | path_selector, layer_input, checkbox_grid, bottom_action_buttons | 🔴 Complexo | Sim | Sim | Nenhuma |
| 17 | `SettingsPlugin` | Múltiplos (tema, preferências, etc) | 🔴 Complexo | Não | Sim | Sistema |

### 4.3 Exemplo de Migração: `PathExtensionPlugin`

**Antes (com Factory):**
```python
class PathExtensionPlugin(BasePluginMTL):
    def _build_ui(self, **kwargs):
        super()._build_ui(title=STR.PATH_EXTENSION_TITLE, enable_scroll=True)

        layer_layout, self.layer_input = WidgetFactory.create_layer_input(
            label_text=STR.INPUT_LAYER,
            filters=[QgsMapLayerProxyModel.Filter.VectorLayer],
            allow_empty=False,
        )

        attr_layout, self.attr_selector = WidgetFactory.create_dropdown_selector(
            title=f"{STR.PATH}:",
            options_dict={},
            allow_empty=True,
            empty_text=STR.SELECT,
            separator_bottom=True,
        )

        mode_layout, self.radio_mode = WidgetFactory.create_radio_button_grid(
            items=[STR.MODE_REMOVE, STR.MODE_RESTORE, STR.MODE_ZIP, STR.MODE_UNZIP],
            columns=2,
            checked_index=0,
            tool_key=self.TOOL_KEY,
            separator_bottom=True,
        )

        buttons_layout, self.action_buttons = WidgetFactory.create_bottom_action_buttons(
            parent=self,
            run_callback=self.execute_tool,
            close_callback=self.close,
            info_callback=self.show_info_dialog,
            tool_key=self.TOOL_KEY,
        )

        self.layout.add_items([layer_layout, attr_layout, mode_layout, buttons_layout])
```

**Depois (sem Factory):**
```python
class PathExtensionPlugin(BasePluginMTL):
    def _build_ui(self, **kwargs):
        super()._build_ui(title=STR.PATH_EXTENSION_TITLE, enable_scroll=True)

        self.layer_input = LayerInputWidget(
            label_text=STR.INPUT_LAYER,
            filters=[QgsMapLayerProxyModel.Filter.VectorLayer],
            allow_empty=False,
            parent=self,
        )

        self.attr_selector = DropdownSelectorWidget(
            title=f"{STR.PATH}:",
            options_dict={},
            allow_empty=True,
            empty_text=STR.SELECT,
            parent=self,
        )

        self.radio_mode = RadioButtonGridWidget(
            items=[STR.MODE_REMOVE, STR.MODE_RESTORE, STR.MODE_ZIP, STR.MODE_UNZIP],
            columns=2,
            checked_index=0,
            tool_key=self.TOOL_KEY,
            parent=self,
        )

        self.action_buttons = ExecutionButtonsWidget(
            parent=self,
            run_callback=self.execute_tool,
            close_callback=self.close,
            info_callback=self.show_info_dialog,
            tool_key=self.TOOL_KEY,
        )

        self.layout.addWidget(self.layer_input)
        self.layout.addWidget(self.attr_selector)
        self.layout.addWidget(self.radio_mode)
        self.layout.addWidget(self.action_buttons)
```

### 4.4 Checklist de Migração por Plugin

```markdown
## Plugin: [NOME]

### Análise
- [ ] Quais widgets usa?
- [ ] Pode usar grid layout?
- [ ] Obedece ao contrato PLUGIN_CONTRACT.md?
- [ ] Todos widgets têm self.logger?

### Migração
- [ ] Substituir WidgetFactory.create_xxx() por widget direto
- [ ] Remover imports da Factory
- [ ] Ajustar layout (addWidget em vez de add_items com layouts)
- [ ] Verificar se AppStyles tem todos os métodos necessários
- [ ] Testar funcionamento

### Pós-migração
- [ ] Atualizar docs/ia/changelog.txt
- [ ] Verificar se não quebrou nada
```

---

## 5. FASE 2 — Refatoração dos Widgets

### 5.1 Contrato do Widget Autoconfigurável

Cada widget em `resources/widgets/` deve seguir este contrato:

```python
class MeuWidget(QWidget):
    """
    [Descrição do widget]
    
    Parâmetros
    ----------
    [param1] : type
        [descrição]
    parent : QWidget, optional
        Widget pai
    
    Autoconfiguração
    ----------------
    - Estilos globais via AppStyles
    - Estilo específico via _specific_style()
    - Logger inicializado no __init__
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
        except Exception as e:
            self.logger.exception(e, code="WIDGET_INIT_ERR")
    
    def _configure(self):
        """Monta a UI com base nos parâmetros recebidos."""
        raise NotImplementedError
    
    def _apply_styles(self):
        """Aplica estilos globais + específico."""
        combined = self._global_style() + self._specific_style()
        self.setStyleSheet(combined)
    
    def _global_style(self) -> str:
        """Estilos globais via AppStyles (opcional)."""
        return ""
    
    def _specific_style(self) -> str:
        """Estilo específico deste widget (opcional)."""
        return ""
```

### 5.2 Tabela de Refatoração por Widget

| Widget | `_global_style()` (AppStyles) | `_specific_style()` (próprio) | Logger? |
|--------|------------------------------|------------------------------|---------|
| `LayerInputWidget` | label, checkbox, map_layer_combobox | Margens, padding do layout | ✅ |
| `AttributeSelectorWidget` | label, checkbox, button, list | Padding, spacing do list | ✅ |
| `GridCheckboxWidget` | label, checkbox | Grid layout, tooltip | ✅ |
| `RadioButtonGridWidget` | label, radio_button | Grid layout, spacing | ✅ |
| `ColorButtonWidget` | label, input, button | Hex input, copy button, layout | ✅ |
| `CollapsibleParametersWidget` | collapsible_parameters | Animação, ícone | ✅ |
| `DropdownSelectorWidget` | label, combobox | Padding, hover states | ✅ |
| `CrsSelectorWidget` | label, combobox | Layout específico | ✅ |
| `SimpleButtonWidget` | button | Padding fixo, expansão | ✅ |
| `ExecutionButtonsWidget` | button | Layout horizontal, padding | ✅ |
| `SelectorWidget` | input, button, label | Layout, tooltip, checkbox | ✅ |
| `GridInputFieldsWidget` | label, input, spinbox | Grid layout, validação | ✅ |
| `ReadOnlyFieldWidget` | label, button | Grid layout, copy button | ✅ |
| `ComplexSelector` | input, button, label | Layout, tooltip, project button | ✅ |
| `GridComplexSelector` | (usa ComplexSelector) | Grid layout, parent linking | ✅ |
| `ImageWidget` | (sem estilo Qt) | paintEvent, click | ✅ |
| `ScrollWidget` | scroll_area | (usa QScrollArea nativo) | ✅ |
| `AppBarWidget` | app_bar | Botões, título, ícone | ✅ |
| `MainLayout` | main_application | Scroll, resize, drag | ✅ |

### 5.3 Exemplo de Widget Refatorado: `LayerInputWidget`

```python
# resources/widgets/LayerInputWidget.py
# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsVectorLayer, QgsMapLayerProxyModel, QgsProject
from ...core.config.LogUtils import LogUtils
from ...utils.ToolKeys import ToolKey
from ...resources.styles.AppStyles import AppStyles
from ...i18n.TranslationManager import STR


class LayerInputWidget(QWidget):
    """
    Widget padrão para seleção de camada.
    
    Parâmetros
    ----------
    label_text : str
        Texto do label
    filters : QgsMapLayerProxyModel.Filter | list
        Filtros para o combobox
    allow_empty : bool, optional
        Se True, permite nenhuma camada selecionada (default True)
    enable_selected_checkbox : bool, optional
        Se True, exibe checkbox "usar apenas seleção" (default True)
    parent : QWidget, optional
        Widget pai
    
    Autoconfiguração
    ----------------
    - Estilos globais: AppStyles.label(), AppStyles.checkbox(), AppStyles.map_layer_combobox()
    - Estilo específico: margens e padding do layout
    """

    layerChanged = pyqtSignal(object)  # QgsMapLayer | None

    def __init__(
        self,
        label_text: str,
        filters,
        *,
        allow_empty: bool = True,
        enable_selected_checkbox: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.logger = LogUtils(
            tool=ToolKey.WIDGETS,
            class_name="LayerInputWidget",
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
            self.logger.exception(e, code="LAYER_INPUT_INIT_ERR")

    def _build_layout(self):
        """Monta o layout vertical."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
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
        """Estilo específico do LayerInputWidget."""
        return """
        QWidget {
            margin: 0px;
            padding: 0px;
        }
        """

    # ── Demais métodos (bindings, eventos, API pública) ────────
    # ... (mantidos iguais aos atuais)
```

---

## 6. FASE 3 — Eliminação da WidgetFactory

### 6.1 Marcar como Deprecated

Após todos os plugins e widgets migrados, `WidgetFactory.py` vira:

```python
# core/ui/WidgetFactory.py
# -*- coding: utf-8 -*-
"""
WidgetFactory — DEPRECATED
==========================
Toda criação de widget agora é feita diretamente pelas classes em
resources/widgets/. Os widgets se autoconfiguram com AppStyles + ThemeManager.

Use:
    from resources.widgets.LayerInputWidget import LayerInputWidget
    widget = LayerInputWidget(label_text="...", filters=[...])

Em vez de:
    from core.ui.WidgetFactory import WidgetFactory
    layout, widget = WidgetFactory.create_layer_input(...)
"""

import warnings

warnings.warn(
    "WidgetFactory está obsoleto. "
    "Use os widgets diretamente de resources/widgets/. "
    "Consulte docs/plano_eliminacao_widgetfactory.md para detalhes.",
    DeprecationWarning,
    stacklevel=2,
)

# Mantido apenas para compatibilidade durante transição
# Será removido na próxima versão
from ...resources.widgets.LayerInputWidget import LayerInputWidget
# ... (demais imports e métodos delegados)
```

### 6.2 Remover Completamente

Após 1 release de transição:
- Deletar `core/ui/WidgetFactory.py`
- Remover imports da Factory de todos os arquivos
- Remover referências em `docs/skills/SKILL_WIDGETS.md`

### 6.3 Atualizar Skills e Contratos

**`docs/skills/SKILL_WIDGETS.md`** — Reescrever para o novo modelo:
- Remover toda referência à WidgetFactory
- Documentar o novo contrato de autoconfiguração
- Documentar AppStyles como ponto único de estilos globais
- Documentar `_specific_style()` para estilos específicos

**`docs/skills/PLUGIN_CONTRACT.md`** — Atualizar regra #1:
```
## 1. UI — Widgets

❌ from core.ui.WidgetFactory import WidgetFactory
✅ from resources.widgets.LayerInputWidget import LayerInputWidget

Plugins nunca importam QtWidgets direto. Todo widget é importado
diretamente de resources/widgets/ e se autoconfigura com AppStyles + ThemeManager.
O plugin passa apenas parâmetros de configuração, sem saber de estilos.
```

---

## 7. Contrato do Widget Autoconfigurável

### 7.1 Regras Obrigatórias

1. **Todo widget herda de `QWidget`** (ou `QDialog` para diálogos)
2. **Todo widget tem `self.logger`** inicializado no `__init__`
3. **Todo `try` usa `self.logger.exception()`** no except
4. **Todo widget chama `self._apply_styles()`** no final do `__init__`
5. **Estilos globais** vêm de `AppStyles`
6. **Estilos específicos** vêm de `_specific_style()` (método do próprio widget)
7. **Plugin NUNCA** chama `setStyleSheet()` no widget
8. **Plugin NUNCA** importa `AppStyles` ou `ThemeManager`
9. **Widget recebe params** como argumentos nomeados no `__init__`
10. **Widget NÃO** depende de `WidgetFactory` para nada

### 7.2 Template de Widget

```python
# resources/widgets/MeuWidget.py
# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout
from ...core.config.LogUtils import LogUtils
from ...utils.ToolKeys import ToolKey
from ...resources.styles.AppStyles import AppStyles


class MeuWidget(QWidget):
    """
    [Descrição do widget]
    
    Parâmetros
    ----------
    [param1] : type
        [descrição]
    parent : QWidget, optional
        Widget pai
    """

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
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
        """Monta a UI com base nos parâmetros."""
        # Criar widgets filhos
        # Montar layout
        # Conectar sinais
        pass

    def _apply_styles(self):
        """Aplica estilos globais + específico."""
        style = self._global_style() + self._specific_style()
        self.setStyleSheet(style)

    def _global_style(self) -> str:
        """Estilos globais via AppStyles."""
        return (
            AppStyles.label()
            + AppStyles.button()
            + AppStyles.input()
        )

    def _specific_style(self) -> str:
        """Estilo específico deste widget."""
        return """
        QWidget {
            margin: 4px;
            padding: 2px;
        }
        """
```

---

## 8. Compatibilidade Qt5/Qt6

### 8.1 Pontos de Atenção

| Qt5 | Qt6 | Onde Usar |
|-----|-----|-----------|
| `Qt.AlignLeft` | `Qt.AlignmentFlag.AlignLeft` | Alinhamentos |
| `Qt.WA_TranslucentBackground` | `Qt.WidgetAttribute.WA_TranslucentBackground` | Atributos de widget |
| `Qt.Dialog` | `Qt.WindowType.Dialog` | Window flags |
| `QFrame.HLine` | `QFrame.Shape.HLine` | Formas de QFrame |
| `QFrame.Sunken` | `QFrame.Shadow.Sunken` | Sombras de QFrame |

### 8.2 Padrão de Compatibilidade

```python
# helpers compat
def _qt_enum(module, qt5_name, qt6_attr, qt6_name):
    """Resolve enum compatível Qt5/Qt6."""
    try:
        return getattr(getattr(module, qt6_attr), qt6_name)
    except AttributeError:
        return getattr(module, qt5_name)

# Uso:
ALIGN_LEFT = _qt_enum(Qt, "AlignLeft", "AlignmentFlag", "AlignLeft")
WA_TRANSLUCENT = _qt_enum(Qt, "WA_TranslucentBackground", "WidgetAttribute", "WA_TranslucentBackground")
WINDOW_DIALOG = _qt_enum(Qt, "Dialog", "WindowType", "Dialog")
```

### 8.3 Onde Aplicar

- `BaseDialog.py` (já tem `_qt_window_type` e `_qt_widget_attr`)
- `WidgetFactory.create_separator()` (já tem compat)
- Todos os widgets que usam `Qt.` enums
- `AppStyles` (não usa enums, só strings CSS — seguro)

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Quebrar compatibilidade Qt5/Qt6 | Média | Alto | Usar helpers de compatibilidade em todos os widgets |
| Plugin parar de funcionar durante migração | Alta | Alto | Migrar 1 plugin por vez, testar cada um antes de passar ao próximo |
| Perder estilos específicos que estavam em Styles.py | Média | Médio | Mover para `_specific_style()` do widget correspondente |
| BaseStyles ainda ser importado por código externo | Baixa | Baixo | Manter como alias para AppStyles durante transição |
| ThemeManager.current_theme mudar em runtime | Baixa | Médio | AppStyles usa cache com invalidação via `reload_theme()` |
| Widget esquecer de chamar `_apply_styles()` | Média | Médio | Chamar no `__init__` dentro do template obrigatório |
| Plugin importar QtWidgets direto | Média | Alto | Revisão de código + linter rule |
| Esquecer de adicionar `self.logger` | Média | Baixo | Template obrigatório + code review |

---

## 10. TODO Interno Consolidado

```
[ ] FASE 0: Fundação
  [ ] 0.1 Criar resources/styles/AppStyles.py
  [ ] 0.2 Adaptar Styles.py como ponte (herda AppStyles + deprecated warnings)
  [ ] 0.3 Adaptar BaseStyles.py como alias (deprecated)
  [ ] 0.4 Atualizar resources/__init__.py
  [ ] 0.5 Adicionar helpers de compatibilidade Qt5/Qt6
  [ ] 0.6 Testar se AppStyles funciona com tema atual

[ ] FASE 1: Migração Plugin por Plugin
  [ ] 1.1 AboutDialog
  [ ] 1.2 RestartQgis
  [ ] 1.3 CoorResultDialog
  [ ] 1.4 VectorMultipartPlugin
  [ ] 1.5 ExportAllLayouts
  [ ] 1.6 CopyAttributesPlugin
  [ ] 1.7 DividePointsByStripsPlugin
  [ ] 1.8 DroneCoordinates
  [ ] 1.9 LoadFolderLayers
  [ ] 1.10 PathExtensionPlugin
  [ ] 1.11 ReplaceInLayouts
  [ ] 1.12 SaveTemporaryLayersPlugin
  [ ] 1.13 GenerateTrailPlugin
  [ ] 1.14 ReportMetadataPlugin
  [ ] 1.15 VectorFieldsCalculationPlugin
  [ ] 1.16 VectorToSvgPlugin
  [ ] 1.17 SettingsPlugin

[ ] FASE 2: Refatoração dos Widgets
  [ ] 2.1 LayerInputWidget
  [ ] 2.2 AttributeSelectorWidget
  [ ] 2.3 GridCheckboxWidget
  [ ] 2.4 RadioButtonGridWidget
  [ ] 2.5 ColorButtonWidget
  [ ] 2.6 CollapsibleParametersWidget
  [ ] 2.7 DropdownSelectorWidget
  [ ] 2.8 CrsSelectorWidget
  [ ] 2.9 SimpleButtonWidget
  [ ] 2.10 ExecutionButtonsWidget
  [ ] 2.11 SelectorWidget
  [ ] 2.12 GridInputFieldsWidget
  [ ] 2.13 ReadOnlyFieldWidget
  [ ] 2.14 ComplexSelector
  [ ] 2.15 GridComplexSelector
  [ ] 2.16 ImageWidget
  [ ] 2.17 ScrollWidget
  [ ] 2.18 AppBarWidget
  [ ] 2.19 MainLayout

[ ] FASE 3: Eliminação da WidgetFactory
  [ ] 3.1 Marcar WidgetFactory como deprecated
  [ ] 3.2 Remover WidgetFactory (após 1 release)
  [ ] 3.3 Atualizar docs/skills/SKILL_WIDGETS.md
  [ ] 3.4 Atualizar docs/skills/PLUGIN_CONTRACT.md (regra #1)
  [ ] 3.5 Atualizar docs/ia/changelog.txt
  [ ] 3.6 Remover referências obsoletas em todo código
```

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-21 | 1.0.0 | Criação do plano de ação para eliminação da WidgetFactory |