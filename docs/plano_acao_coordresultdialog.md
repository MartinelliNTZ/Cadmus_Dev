# 🎯 PLANO DE AÇÃO: Migração CoorResultDialog + Widgets Faltantes

**Objetivo:** Migrar o `CoorResultDialog` (plugin #3 do plano) para o novo sistema de widgets autoconfiguráveis, criando os widgets `GridReadOnly` e demais dependências faltantes.

**Data:** 2026-07-22
**Versão:** 1.0.0
**Autor:** Cadmus Engineering

---

## Sumário

1. [Status Atual da Migração](#1-status-atual-da-migração)
2. [Análise do CoorResultDialog](#2-análise-do-coorresultdialog)
3. [Widgets que Precisam Ser Criados](#3-widgets-que-precisam-ser-criados)
4. [Dependências Entre Widgets](#4-dependências-entre-widgets)
5. [Estratégia de Criação e Migração](#5-estratégia-de-criação-e-migração)
6. [Ordem Execução Detalhada](#6-ordem-execução-detalhada)
7. [FASE 0 — Criar Widgets Simple Faltantes](#7-fase-0--criar-widgets-simple-faltantes)
8. [FASE 1 — Criar GridReadOnly](#8-fase-1--criar-gridreadonly)
9. [FASE 2 — Migrar CoorResultDialog](#9-fase-2--migrar-coorresultdialog)
10. [FASE 3 — Próximos Plugins](#10-fase-3--próximos-plugins)
11. [Riscos e Mitigações](#11-riscos-e-mitigações)
12. [TODO Consolidado](#12-todo-consolidado)

---

## 1. Status Atual da Migração

### ✅ Concluído

| Item | Status |
|------|--------|
| **FASE 0** — BaseTheme + AppStyles + ThemeManager | ✅ |
| **FASE 1.1** — Widgets Simple criados | Parcial |
| **FASE 1.2** — Widgets Grid criados | Parcial |
| **FASE 1.3** — Widgets Raiz criados | Parcial |
| **AboutDialog** (plugin #1) | ✅ |

### 📊 O Que Existe em `resources/widgets/`

```
resources/widgets/
├── __init__.py
├── AppBarWidget.py          ✅ (raiz)
├── MainLayout.py            ✅ (raiz)
├── ScrollWidget.py          ✅ (raiz)
├── SeparatorWidget.py       ✅ (raiz)
│
├── grid/
│   ├── __init__.py
│   ├── GridButton.py        ✅ (botões simples: fechar, executar, info)
│   ├── GridExecutionButtons.py ✅ (botões com config dict + ícones)
│   ├── GridIconButton.py    ✅ (botões de ícone social)
│   └── GridLabel.py         ✅ (labels simples)
│
└── simple/
    ├── __init__.py
    ├── SimpleButton.py      ✅
    ├── SimpleIconButton.py  ✅
    └── SimpleLabel.py       ✅
```

### ❌ Faltando (necessário para o CoorResultDialog)

| Widget | Prioridade | Para que plugin |
|--------|-----------|-----------------|
| `grid/GridReadOnly.py` | 🔴 Crítica | CoorResultDialog (WGS84, UTM, Altimetria) |
| `simple/SimpleReadOnly.py` | 🔴 Crítica | GridReadOnly depende |
|

---

## 2. Análise do CoorResultDialog

### 2.1 Estrutura Atual (Factory)

```python
class CoordResultDialog(BasePluginMTL):
    TOOL_KEY = ToolKey.COORD_CLICK_TOOL

    def _build_ui(self, **kwargs):
        super()._build_ui(title=STR.POINT_COORDINATES, ...)

        # ── 3× ReadOnlyField ────────────────────────────────────────
        ro_layout, self.wgs_widget = WidgetFactory.create_readonly_field(
            title=STR.WGS84_EPSG4326,
            fields={
                "lat_dec": {"title": STR.LATITUDE_DECIMAL, "value": ""},
                "lon_dec": ...,
                "lat_dms": ...,
                "lon_dms": ...,
            },
            num_columns=1,
            copy_all_button_title=STR.COPY_WGS84_FULL,
        )

        ro_layout2, self.utm_widget = WidgetFactory.create_readonly_field(
            title=STR.UTM_SIRGAS_2000,
            fields={"utm_x": ..., "utm_y": ...},
            num_columns=1,
            copy_all_button_title=STR.COPY_UTM_FULL,
            separator_bottom=False,
        )

        ro_layout3, self.alt_widget = WidgetFactory.create_readonly_field(
            title=STR.ALTIMETRY_OPENTOPO,
            fields={"altitude": ...},
            num_columns=1,
            copy_all_button_title=None,
            separator_top=True,
        )

        # ── 6× Labels avulsos ────────────────────────────────────────
        self.lbl_utm_info = WidgetFactory.create_label(text="", parent=self)  # (label simples)
        self.lbl_municipio = WidgetFactory.create_label(...)       # label simples
        self.lbl_state_district = WidgetFactory.create_label(...)  # label simples
        self.lbl_state = WidgetFactory.create_label(...)            # label simples
        self.lbl_region = WidgetFactory.create_label(...)           # label simples
        self.lbl_country = WidgetFactory.create_label(...)          # label simples

        # ── 1× SimpleButton + 1× BottomActions ────────────────────
        copy_layout, self.btn_copy_all = WidgetFactory.create_simple_button(
            text=STR.COPY_LOCATION_FULL, ...)
        self.btn_copy_all.clicked.connect(self.copy_all_info)

        btn_layout, _ = WidgetFactory.create_bottom_action_buttons(
            run_callback=lambda: self.close(),
            close_callback=lambda: self.close(),
            info_callback=lambda: self.show_info_dialog(),
            tool_key=self.TOOL_KEY,
        )

        # ── Layout com add_items (lista) ──────────────────────────
        self.layout.add_items([...])
```

### 2.2 Métodos de Acesso aos Widgets

O plugin interage com os widgets via estes métodos:

| Método | Uso | Tipo |
|--------|-----|------|
| `self.wgs_widget.get_value("lat_dec")` | Leitura | ReadOnlyField |
| `self.wgs_widget.set_value("lat_dec", ...)` | Escrita | ReadOnlyField |
| `self.utm_widget.get_value("utm_x")` | Leitura | ReadOnlyField |
| `self.utm_widget.set_value("utm_x", ...)` | Escrita | ReadOnlyField |
| `self.alt_widget.get_value("altitude")` | Leitura | ReadOnlyField |
| `self.alt_widget.set_value("altitude", ...)` | Escrita | ReadOnlyField |
| `self.lbl_utm_info.setText(...)` | Escrita direta | QLabel |
| `self.lbl_municipio.setText(...)` | Escrita direta | QLabel |
| `self.btn_copy_all.clicked.connect(...)` | Sinal | QPushButton |

### 2.3 Funcionalidades Específicas

1. **ReadOnlyField** com `copy_all_button` — título + campos readonly + botão "Copiar tudo"
2. **Labels avulsos** — 1 label UTM info + 5 labels de endereço (município, estado, região, país)
3. **Botão copiar** — botão simples com callback `copy_all_info`
4. **Bottom action buttons** — executar/fechar/info

### 2.4 Arquitetura Alvo no Novo Sistema

```
CoorResultDialog (novo)
├── GridReadOnly "WGS84" (4 campos: lat_dec, lon_dec, lat_dms, lon_dms)
├── GridReadOnly "UTM" (2 campos: utm_x, utm_y)
├── GridLabel "UTM Info" (1 label com info da zona/hemisfério)
├── GridReadOnly "Altimetria" (1 campo: altitude)
├── GridLabel × 5 (endereço: município, state_district, state, region, country)
├── SeparatorWidget()
└── GridExecutionButtons (fechar, info)├──  (copy_all)
```

---

## 3. Widgets que Precisam Ser Criados

### 3.1 SimpleReadOnly — Interno para GridReadOnly

```python
# resources/widgets/simple/SimpleReadOnly.py
"""
SimpleReadOnly — QLineEdit readonly + AppStyles.input()
USO INTERNO — GridReadOnly usa este widget.
"""
class SimpleReadOnly(QLineEdit):
    def __init__(self, text="", placeholder="", parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setText(text)
        if placeholder:
            self.setPlaceholderText(placeholder)
        # estilo: AppStyles.input() (readonly fields usam input style)

    def _apply_styles(self):
        self.setStyleSheet(AppStyles.input())
```

**API necessária:**
- `setText(text: str)` — herda de QLineEdit
- `text()` — herda de QLineEdit
- `setPlaceholderText(text: str)` — herda de QLineEdit

### 3.2 GridReadOnly — Container de ReadOnly Fields

```python
# resources/widgets/grid/GridReadOnly.py
"""
GridReadOnly — Container de campos readonly com título e botão copiar opcional.
Plugins USAM este widget.

Uso:
    wgs84 = GridReadOnly(
        title=STR.WGS84_EPSG4326,
        fields={
            "lat_dec": {"title": STR.LATITUDE_DECIMAL, "value": ""},
            "lon_dec": {"title": STR.LONGITUDE_DECIMAL, "value": ""},
        },
        copy_all_button_text=STR.COPY_WGS84_FULL,
        parent=self,
    )
    layout.addWidget(wgs84)

    # API pública:
    wgs84.set_value("lat_dec", "-10.12345678")
    wgs84.get_value("lat_dec")  # -> "-10.12345678"
"""
class GridReadOnly(QWidget):
    def __init__(self, title="", fields=None, copy_all_button_text=None, parent=None):
        ...
    
    def set_value(self, key: str, value: str):
        """Atualiza valor de um campo pelo identificador."""
        if key in self._fields:
            self._fields[key].setText(str(value))

    def get_value(self, key: str) -> str:
        """Retorna valor de um campo pelo identificador."""
        if key in self._fields:
            return self._fields[key].text()
        return ""

    def set_title_label(self, text: str):
        """Atualiza o texto do título."""
        self._title_label.setText(text)
```

---

## 4. Dependências Entre Widgets

```
CoorResultDialog
├── GridReadOnly
│   └── SimpleReadOnly (NOVO) ← QLineEdit readonly + AppStyles.input()
│
├── GridExecutionButtons (já existe ✅)
│   └── SimpleButton (já existe ✅)
│
├── GridLabel (já existe ✅)
│   └── SimpleLabel (já existe ✅)
│
├── GridButton (já existe ✅)
│   └── SimpleButton (já existe ✅)
│
└── SeparatorWidget (já existe ✅)
```

**Dependência mínima:** Apenas 2 widgets novos para migrar o CoorResultDialog:
1. `simple/SimpleReadOnly.py` ← base
2. `grid/GridReadOnly.py` ← container

---

## 5. Estratégia de Criação e Migração

### 5.1 Princípios

1. **Criar SimpleReadOnly** primeiro — depende de nada
2. **Criar GridReadOnly** depois — depende de SimpleReadOnly
3. **Migrar CoorResultDialog** — substituir Factory → widgets
4. **Nunca modificar arquivos antigos** — manter `WidgetFactory.py`, `resources/widgets/`, etc.

### 5.2 Contratos Obrigatórios

✅ Todo widget em `widgets/` segue o contrato SKILL_WIDGETS2.md:
- Herda de `QWidget` (ou similar)
- `try/except` com logger no `__init__`
- `_apply_styles()` no final
- Plugin NUNCA chama `setStyleSheet()`
- Plugin NUNCA importa `AppStyles` ou `ThemeManager`
- Callbacks são passadas como parâmetros, não como sinais Qt expostos

### 5.3 API de Comunicação

No sistema novo:

```python
# ANTIGO (Factory) — plugin recebe (layout, widget)
ro_layout, self.wgs_widget = WidgetFactory.create_readonly_field(...)
self.layout.add_items([ro_layout, ...])

# NOVO (widgets) — plugin instancia widget direto
self.wgs_widget = GridReadOnly(
    title=STR.WGS84_EPSG4326,
    fields={...},
    copy_all_button_text=STR.COPY_WGS84_FULL,
    parent=self,
)
self.layout.addWidget(self.wgs_widget)

# API de acesso mantida IDÊNTICA:
self.wgs_widget.set_value("lat_dec", f"{info['lat']:.8f}")
self.wgs_widget.get_value("lat_dec")  # mesma assinatura
```

A API `set_value(key, value)` e `get_value(key)` é mantida **exatamente igual** para minimizar mudanças na lógica do plugin.

---

## 6. Ordem Execução Detalhada

### 🔴 Passo 1: Criar `SimpleReadOnly`

**Arquivo:** `resources/widgets/simple/SimpleReadOnly.py`

Baseado em `QLineEdit` com `setReadOnly(True)`.
- Aplica `AppStyles.input()` no `_apply_styles()`
- NÃO precisa de `_specific_style()` (readonly usa estilo de input)

### 🔴 Passo 2: Criar `GridReadOnly`

**Arquivo:** `resources/widgets/grid/GridReadOnly.py`

Container título + campos readonly + botão copiar opcional.
- Título: `SimpleLabel` (bold, maior)
- Campos: `SimpleReadOnly` com label ao lado (ex: "Latitude Decimal: -10.12345678")
- Botão copiar: `SimpleButton` (opcional, via parâmetro `copy_all_button_text`)
- Layout: `QVBoxLayout` com grid interno de labels + fields

### 🟡 Passo 3: Migrar `CoorResultDialog`

**Arquivo:** `plugins/CoorResultDialog.py`

Substituir todas as chamadas `WidgetFactory.create_xxx()` por widgets de `widgets/`:

| Factory (antigo) | widgets (novo) |
|-----------------|-------------------|
| `create_readonly_field(...)` → retorna (layout, widget) | `GridReadOnly(...)` → retorna widget |
| `create_label(text="", parent=self)` | `SimpleLabel(text="", parent=self)` ou `GridLabel` com config dict |
| `create_simple_button(text=..., parent=self)` | `SimpleButton(text=..., parent=self)` |
| `create_bottom_action_buttons(...)` | `GridExecutionButtons(config={...}, enable_close_button=True, enable_info=True, ...)` |

**Mudanças no layout:**
- `self.layout.add_items([...])` → vários `self.layout.addWidget(widget)`
- Adicionar `SeparatorWidget()` entre blocos lógicos

**Mudanças na API de botão:**
- `self.btn_copy_all.clicked.connect(self.copy_all_info)` → o widget recebe `callback` como parâmetro

### 🟢 Passo 4: Validar Funcionalidades

- `update_info(info)` → chamar `set_value()` nos GridReadOnly
- `set_altitude(value)` → chamar `set_value()` no GridReadOnly de altitude
- `set_address(data)` → chamar `setText()` nos SimpleLabel/GridLabel de endereço
- `copy_all_info()` → chamar `get_value()` nos GridReadOnly
- `copy_address()` → chamar `text()` nos labels

---

## 7. FASE 0 — Criar Widgets Simple Faltantes

### 7.1 SimpleReadOnly

```python
# resources/widgets/simple/SimpleReadOnly.py
# -*- coding: utf-8 -*-
"""
SimpleReadOnly — QLineEdit readonly com AppStyles.input().
USO INTERNO — GridReadOnly usa este widget.
Plugins NUNCA importam Simple diretamente.
"""

from qgis.PyQt.QtWidgets import QLineEdit
from ...styles.AppStyles import AppStyles


class SimpleReadOnly(QLineEdit):
    """
    Campo de texto readonly com estilo de input.

    Parâmetros
    ----------
    text : str, optional
        Texto inicial.
    placeholder : str, optional
        Placeholder text.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(self, text: str = "", placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        if text:
            self.setText(text)
        if placeholder:
            self.setPlaceholderText(placeholder)
        self._apply_styles()

    def _apply_styles(self):
        """Aplica estilos globais de input."""
        self.setStyleSheet(AppStyles.input())

    def setText(self, text: str):
        """Sobrescreve para aceitar None."""
        super().setText(str(text) if text is not None else "")
```

### 7.2 Por que SimpleReadOnly em vez de SimpleLabel para readonly?

| Característica | SimpleLabel | SimpleReadOnly (QLineEdit readonly) |
|---------------|-------------|--------------------------------------|
| Selecionável | ❌ | ✅ — usuário pode copiar texto |
| Aparência de input | ❌ | ✅ — consistente com outros campos |
| Compatível com tema | ✅ | ✅ — usa AppStyles.input() |
| Placeholder | ❌ | ✅ |

O CoorResultDialog usa `ReadOnlyFieldWidget` do sistema antigo que também usava QLineEdit readonly. Manter o padrão para consistência.

---

## 8. FASE 1 — Criar GridReadOnly

```python
# resources/widgets/grid/GridReadOnly.py
# -*- coding: utf-8 -*-
"""
GridReadOnly — Container de campos readonly com título e botão copiar opcional.
Plugins USAM este widget.

Uso:
    wgs84 = GridReadOnly(
        title=STR.WGS84_EPSG4326,
        fields={
            "lat_dec": {"title": STR.LATITUDE_DECIMAL, "value": ""},
            "lon_dec": {"title": STR.LONGITUDE_DECIMAL, "value": ""},
        },
        copy_all_button_text=STR.COPY_WGS84_FULL,
        parent=self,
    )
    layout.addWidget(wgs84)

    # API:
    wgs84.set_value("lat_dec", "-10.12345678")
    wgs84.get_value("lat_dec")  # -> "-10.12345678"

Parâmetros
----------
title : str
    Título do bloco (ex: "WGS84 (EPSG:4326)").
fields : dict
    Dict de campos. Cada chave é identificador, valor é dict com:
    - "title" (str): rótulo do campo
    - "value" (str, optional): valor inicial
copy_all_button_text : str, optional
    Texto do botão "Copiar tudo". Se None, não exibe botão.
copy_callback : callable, optional
    Callback customizado para o botão copiar.
parent : QWidget, optional
    Widget pai.
"""

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from ..simple.SimpleLabel import SimpleLabel
from ..simple.SimpleReadOnly import SimpleReadOnly  # NOVO
from ..simple.SimpleButton import SimpleButton
from ...styles.AppStyles import AppStyles


class GridReadOnly(QWidget):
    """
    Container com título + campos readonly + botão copiar opcional.
    API pública: set_value(key, value), get_value(key).
    """

    def __init__(
        self,
        title: str = "",
        fields: dict = None,
        copy_all_button_text: str = None,
        copy_callback: callable = None,
        parent=None,
    ):
        super().__init__(parent)
        self._fields = {}
        self._title_label = None

        try:
            self._configure(title, fields or {}, copy_all_button_text, copy_callback)
            self._apply_styles()
        except Exception as error:
            pass  # logger seria útil, mas widget não tem logger próprio

    def _configure(self, title, fields, copy_all_button_text, copy_callback):
        """Monta UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        theme = AppStyles._get_theme()
        layout.setSpacing(theme.LAYOUT_VERTICAL_SPACING)

        # ── Título ──
        if title:
            self._title_label = SimpleLabel(text=f"<b>{title}</b>", parent=self)
            layout.addWidget(self._title_label)

        # ── Campos readonly ──
        for key, cfg in fields.items():
            field_title = cfg.get("title", key)
            field_value = cfg.get("value", "")

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(theme.LAYOUT_HORIZONTAL_SPACING)

            label = SimpleLabel(text=f"{field_title}:", parent=self)
            readonly = SimpleReadOnly(text=field_value, parent=self)

            self._fields[key] = readonly

            row.addWidget(label)
            row.addWidget(readonly, stretch=1)
            layout.addLayout(row)

        # ── Botão Copiar Tudo ──
        if copy_all_button_text:
            if copy_callback is None:
                # callback padrão: selecionar texto de todos os campos
                copy_callback = self._default_copy_all

            self._copy_button = SimpleButton(
                text=copy_all_button_text,
                parent=self,
            )
            self._copy_button.clicked.connect(copy_callback)
            layout.addWidget(self._copy_button)

    def _default_copy_all(self):
        """Callback padrão: junta todos os valores com newline."""
        parts = []
        for key, field in self._fields.items():
            parts.append(f"{key}: {field.text()}")
        from qgis.PyQt.QtWidgets import QApplication
        QApplication.clipboard().setText("\n".join(parts))

    # ── API Pública ────────────────────────────────────────

    def set_value(self, key: str, value: str) -> None:
        """Atualiza valor de um campo pelo identificador."""
        if key in self._fields:
            self._fields[key].setText(str(value))

    def get_value(self, key: str) -> str:
        """Retorna valor de um campo pelo identificador."""
        if key in self._fields:
            return self._fields[key].text()
        return ""

    def set_title_label(self, text: str) -> None:
        """Atualiza o texto do título."""
        if self._title_label:
            self._title_label.setText(f"<b>{text}</b>")

    # ── Estilos ────────────────────────────────────────────

    def _apply_styles(self):
        """Aplica estilos globais."""
        combined = self._get_global_style() + self._specific_style()
        self.setStyleSheet(combined)

    def _get_global_style(self) -> str:
        return AppStyles.label() + AppStyles.input()

    def _specific_style(self) -> str:
        return ""
```

---

## 9. FASE 2 — Migrar CoorResultDialog

### 9.1 Código Migrado

```python
# plugins/CoorResultDialog.py (MIGRADO)
# -*- coding: utf-8 -*-
from ..utils.ToolKeys import ToolKey
from .BasePlugin import BasePluginMTL
from ..utils.ProjectUtils import ProjectUtils
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.Preferences import Preferences
from ..i18n.TranslationManager import STR
from ..resources.widgets.grid.GridReadOnly import GridReadOnly
from ..resources.widgets.grid.GridLabel import GridLabel
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.widgets.grid.GridButton import GridButton
from ..resources.widgets.simple.SimpleLabel import SimpleLabel
from ..resources.widgets.SeparatorWidget import SeparatorWidget


class CoordResultDialog(BasePluginMTL):
    TOOL_KEY = ToolKey.COORD_CLICK_TOOL

    def __init__(self, iface, info):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.info = info
        self.init(
            tool_key=self.TOOL_KEY, class_name="CoordResultDialog", build_ui=True
        )

        try:
            self.update_info(info)
        except Exception as e:
            self.logger.error(f"Error {e}")

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
            copy_all_button_text=STR.COPY_WGS84_FULL,
            parent=self,
        )
        self.layout.addWidget(self.wgs_widget)

        self.layout.addWidget(SeparatorWidget())  # ← separador entre blocos

        # ── UTM ReadOnly ─────────────────────────────────────
        self.utm_widget = GridReadOnly(
            title=STR.UTM_SIRGAS_2000,
            fields={
                "utm_x": {"title": STR.EASTING_X, "value": ""},
                "utm_y": {"title": STR.NORTHING_Y, "value": ""},
            },
            copy_all_button_text=STR.COPY_UTM_FULL,
            parent=self,
        )
        self.layout.addWidget(self.utm_widget)

        # ── UTM Info Label ────────────────────────────────────
        self.lbl_utm_info = SimpleLabel(text="", parent=self)
        self.layout.addWidget(self.lbl_utm_info)

        self.layout.addWidget(SeparatorWidget())

        # ── Altimetria ReadOnly ──────────────────────────────
        self.alt_widget = GridReadOnly(
            title=STR.ALTIMETRY_OPENTOPO,
            fields={
                "altitude": {
                    "title": STR.APPROX_ALTITUDE_METERS,
                    "value": STR.LOADING,
                }
            },
            copy_all_button_text=None,  # sem botão copiar
            parent=self,
        )
        self.layout.addWidget(self.alt_widget)

        self.layout.addWidget(SeparatorWidget())

        # ── Labels de Endereço ────────────────────────────────
        # Usando GridLabel com config dict (padrão do novo sistema)
        self.address_labels = GridLabel(config={
            "municipio": {"text": f"{STR.CITY}: {STR.LOADING_LOWER}"},
            "state_district": {"text": f"{STR.INTERMEDIATE_REGION}: {STR.LOADING_LOWER}"},
            "state": {"text": f"{STR.STATE}: {STR.LOADING_LOWER}"},
            "region": {"text": f"{STR.REGION}: {STR.LOADING_LOWER}"},
            "country": {"text": f"{STR.COUNTRY}: {STR.LOADING_LOWER}"},
        }, parent=self)
        self.layout.addWidget(self.address_labels)

        self.layout.addWidget(SeparatorWidget())

        # ── Botão Copiar Localização ──────────────────────────
        self.copy_layout_btn = GridButton(
            close_callback=self.copy_all_info,
            run_text=STR.COPY_LOCATION_FULL,
            parent=self,
        )
        self.layout.addWidget(self.copy_layout_btn)

        self.layout.addWidget(SeparatorWidget())

        # ── Botões de Ação ────────────────────────────────────
        self.action_buttons = GridExecutionButtons(
            config={
                "execute": {
                    "label": STR.EXECUTE,
                    "callback": lambda: self.close(),
                },
            },
            enable_close_button=True,
            enable_info=True,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.layout.add_execution_buttons(self.action_buttons)

    # ── Métodos existentes mantidos (com adaptações) ─────