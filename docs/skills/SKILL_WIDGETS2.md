# 🧩 SKILL: Novo Sistema de Widgets — Autoconfiguráveis

## 📋 RESUMO EXECUTIVO

**Sistema novo de widgets** que substitui `WidgetFactory` por widgets que se autoconfiguram com `AppStyles` + `ThemeManager` + `BaseTheme`.

**Contrato rígido:**
- Plugins NUNCA importam `qgis.PyQt.QtWidgets` direto
- Plugins NUNCA chamam `setStyleSheet()`
- Plugins NUNCA importam `AppStyles` ou `ThemeManager`
- Widgets se autoconfiguram totalmente no `__init__`
- Estilos globais via `AppStyles`, estilo específico via `_specific_style()`
- Separadores são `SeparatorWidget` entre widgets no layout (não margens)

**Princípio:** Widget = **autossuficiente**. Plugin = **consumidor que só passa parâmetros**.

---

## 🏗️ ARQUITETURA

```
Plugin
  └─ importa widget de resources/new_widgets/
      └─ widget.__init__(params, parent)
          ├─ Autoconfiguração total
          ├─ AppStyles (estilos globais)
          ├─ ThemeManager → BaseTheme (cores, fontes, dimensões)
          └─ _specific_style() (estilo próprio do widget)

resources/styles/AppStyles.py
  ├─ Lê de ThemeManager (com cache)
  ├─ Só métodos GLOBAIS: button(), label(), input(), checkbox()
  └─ NUNCA coloca px — tokens já vêm do tema com unidade

resources/styles/ThemeManager.py
  └─ Mantém instância ÚNICA de BaseTheme
      └─ Suporta múltiplos temas no futuro (registro em THEMES)

resources/styles/BaseTheme.py
  └─ Classe de tema com todos os tokens visuais descritivos

resources/new_widgets/
  ├── (raiz)      → widget SEM versão grid
  ├── simple/     → widget TEM versão grid (uso INTERNO)
  └── grid/       → versão grid do widget (plugins USAM esta)
```

---

## 📌 CONTRATO RÍGIDO

### ✅ FAZER:

1. **Widget herda de `QWidget` (ou `QFrame`, `QLabel`, etc)**
2. **`self._apply_styles()`** no final do `__init__` — aplica estilos globais + específico
3. **Estilos globais** → `AppStyles.metodo()` (button, label, input, etc)
4. **Estilo específico** → `_specific_style()` retorna CSS extra
5. **Separadores** → `SeparatorWidget()` entre widgets no layout
6. **Unidades** sempre no tema (`BaseTheme`), nunca `px` no widget ou `AppStyles`
7. **Variável do tema** sempre `theme`, nunca `t`

### ❌ NUNCA FAZER:

```python
# ❌ NUNCA em plugins:
from qgis.PyQt.QtWidgets import QLabel, QPushButton

# ❌ NUNCA setStyleSheet em plugins:
widget.setStyleSheet("color: red")

# ❌ NUNCA importar AppStyles ou ThemeManager em plugins

# ❌ NUNCA unidades fixas em CSS:
min-height: 12px;  # certo: {theme.INPUT_FIELD_MIN_HEIGHT}

# ❌ NUNCA conectar sinais Qt em widgets diretamente:
widget.btn_close.clicked.connect(self.close)
```

### 📋 Padrão de Configuração — Dict `config={}`

Todos os widgets Grid recebem configuração via **dict** `config={}`, onde:
- Cada **chave** é o identificador do componente (ex: `"title"`, `"subfolders"`)
- Cada **valor** é um dict com as propriedades:
  - `"text"` (obrigatório): texto exibido
  - `"description"` (opcional): tooltip do componente
  - `"default"` (opcional): valor padrão (para inputs, checkboxes, etc)

```python
# ✅ CERTO — config dict com identificadores
self.grid_info = GridLabel(config={
    "app_name": {"text": "<h2>Meu App</h2>"},
    "version": {"text": "Versão 1.0", "description": "Data de atualização"},
}, parent=self)

# ❌ ERRADO — lista solta sem identificadores
self.grid_info = GridLabel(items=["Título", "Descrição"], parent=self)
```

**Descrição** sempre vira tooltip no widget, visível ao passar o mouse.

---

### 📞 Regra de Callbacks

Widgets **não expõem sinais Qt** para o plugin. Em vez disso, o plugin passa **funções callback** como parâmetros no construtor do widget. O widget conecta os sinais internamente.

```python
# ✅ CERTO — plugin passa callback:
actions = GridButton(
    close_callback=self.close,
    run_callback=self.execute_tool,
    parent=self,
)

# ❌ ERRADO — plugin conecta sinal no widget:
actions.btn_close.clicked.connect(self.close)
```

**Motivo:** O widget é responsável por seu próprio comportamento interno. O plugin só declara "o que fazer quando" via callbacks, sem conhecer a estrutura interna do widget.

---

## 🧬 CONTRATO DO WIDGET (Template)

```python
# resources/new_widgets/grid/GridExemplo.py
# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout
from ...styles.AppStyles import AppStyles


class GridExemplo(QWidget):
    """
    [Descrição do widget]

    Parâmetros
    ----------
    [param1] : type
        [descrição]
    parent : QWidget, optional
        Widget pai.

    Autoconfiguração
    ----------------
    - AppStyles: métodos globais
    - _specific_style(): estilo específico
    """

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self._params = kwargs

        try:
            self._configure()
            self._apply_styles()
        except Exception as error:
            pass

    def _configure(self):
        """Monta UI com parâmetros."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(AppStyles._get_theme().LAYOUT_VERTICAL_SPACING)

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

## 🚫 Contrato de Unidades

**ERRADO:**
```python
# ❌ UNIDADE FIXA — NÃO FAZER
min-height: {theme.INPUT_FIELD_MIN_HEIGHT}px;
border: 1px solid {theme.COLOR_BORDER};
```

**CERTO:**
```python
# ✅ UNIDADE SEMPRE NO TEMA
# No tema:  INPUT_FIELD_MIN_HEIGHT = "12px"
# No estilo: min-height: {theme.INPUT_FIELD_MIN_HEIGHT};

# No tema:  PXBORDER_ONE = "1px solid"
# No estilo: border: {theme.PXBORDER_ONE} {theme.COLOR_BORDER_DEFAULT};
```

---

## 🆚 AppStyles vs Antigo Styles.py

| Aspecto | AppStyles (NOVO) | Styles.py (ANTIGO) |
|---------|-----------------|-------------------|
| Fonte do tema | `ThemeManager` | `BaseStyles.current_theme = CoffeTheme()` |
| Unidades | Tokens já têm unidade: `"12px"` | Tokens sem unidade: `12` |
| Nomes tokens | `INPUT_FIELD_MIN_HEIGHT` | `INPUT_HEIGHT` |
| Cache | Sim (`_theme` classvar) | Não |
| `_specific_style()` | Cada widget pode ter | Não tem |
| Separadores | Widget separado (`SeparatorWidget`) | Parâmetro `separator_top/bottom` |

---

## ✅ Checklist: Criar Novo Widget no Novo Sistema

- [ ] 1. Widget herda de `QWidget` (ou `QFrame`, `QLabel`, etc)
- [ ] 2. `__init__` recebe `parent=None` + parâmetros específicos
- [ ] 3. `_configure()` monta UI com Simple widgets
- [ ] 4. `_apply_styles()` no final do `__init__`
- [ ] 5. `_get_global_style()` retorna `AppStyles` combinados
- [ ] 6. `_specific_style()` retorna CSS específico (ou `""`)
- [ ] 7. Unidades sempre no tema, nunca `px` no CSS
- [ ] 8. Se tem versão grid → `simple/` + `grid/`
- [ ] 9. Se não tem versão grid → raiz de `new_widgets/`
- [ ] 10. Plugin usa versão grid (nunca simple)

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-21 | 1.0.0 | Criação inicial — Novo sistema de widgets autoconfiguráveis |
| 2026-07-21 | 1.1.0 | Adicionada regra de callbacks (widget não expõe sinais Qt, plugin passa funções callback como parâmetros) |
| 2026-07-21 | 1.2.0 | Adicionado padrão de configuração via dict `config={}` com chaves identificadoras e suporte a `description` para tooltip |
