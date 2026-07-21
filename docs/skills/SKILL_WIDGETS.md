# 🧠 SKILL: WidgetFactory — Sistema de Widgets Centralizados

## 📋 RESUMO EXECUTIVO

**WidgetFactory** é o ponto único de acesso a componentes UI no Cadmus:
- **Contrato rígido:** Plugins NUNCA importam `qgis.PyQt.QtWidgets` direto
- **Responsabilidade única:** Criar e estilizar
- **Três categorias:** Componentes simples, compostos (exclusivos), widgets exclusivos
- **Estilos centralizados:** Via `Styles.py`
- **Encapsulamento:** Lógica específica fica no widget, não na factory

**Princípio:** Factory = **fabricante de peças prontas**. Plugins = **consumidores**.

---

## 🎯 OBJETIVO

Centralizar a criação de UI, garantir consistência visual, facilitar manutenção de estilos e impedir acoplamento entre plugins e QtWidgets diretamente.

---

## 📋 CONTRATO RIGIDO: O QUE FACTORY FAZ / NÃO FAZ

### ✅ **FACTORY FAZ:**

1. **Criar componentes simples pré-configurados**
   - Exemplo: `QLineEdit` já com estilo, padding, border radius
   - Método: `@staticmethod` que retorna widget configurado

2. **Criar widgets compostos (2-3 widgets + layout)**
   - Exemplo: `create_layer_input()` = Label + ComboBox (camadas)
   - Resultado: Widget exclusivo que encapsula o comportamento
   - Retorna: Widget completo pronto para usar

3. **Aplicar estilos via Styles.py**
   - Factory chama `Styles.componente()`
   - Resultado: UI consistente em todo o plugin

4. **Gerenciar separadores opcionais (top/bottom)**
   - Parâmetro: `separator_top=False, separator_bottom=True`
   - Simplifica layouts

### ❌ **FACTORY NÃO FAZ:**

1. **Métodos de população específicos (populate_dropdown, populate_tree, etc)**
   - Exemplo: ❌ `populate_layer_selector(layers_list)`
   - Responsabilidade do widget exclusivo

2. **Lógica de comportamento**
   - ❌ Tratamento de eventos
   - ❌ Validação de dados
   - ❌ Sinais/slots específicos
   - Tudo fica na classe do widget exclusivo

3. **Estilos customizados por plugin**
   - Sempre usar `Styles.py`
   - ❌ `widget.setStyleSheet("color: red")`

4. **Métodos de acesso (getter/setter) gerais**
   - Exemplo: ❌ `factory.get_value(widget)`
   - Cada widget sabe sua própria lógica

---

## ⚙️ TRÊS CATEGORIAS DE COMPONENTES

### **Categoria 1: Componentes Simples**

**O que é:** Um único widget Qt configurado e estilizado.

**Exemplo:**
- `create_label(text, bold=False, ...)`
- `create_text_browser(open_external_links=True, ...)`
- `create_separator(height=1, color="palette(mid)")`

**Retorno:** Widget Qt puro (`QLabel`, `QLineEdit`, etc)

**Código típico:**
```python
@staticmethod
def create_label(*, text="", bold=False, parent=None):
    label = QLabel(text, parent)
    if bold:
        font = label.font()
        font.setBold(True)
        label.setFont(font)
    label.setStyleSheet(Styles.label())
    return label
```

---

### **Categoria 2: Componentes Compostos (Widgets Exclusivos)**

**O que é:** 2-3 widgets Qt + layout que formam comportamento único.

**Exemplo:**
- `create_layer_input()` = Label + ComboBox de camadas + layout
- `create_checkbox_grid()` = Grid de checkboxes + layout
- `create_color_button()` = QLineEdit hex + QPushButton color picker + layout

**Retorno:** Widget exclusivo customizado (`LayerInputWidget`, `CheckboxGridWidget`, etc)

**Estrutura:**
```python
# resources/widgets/LayerInputWidget.py
class LayerInputWidget(QWidget):
    """Seletor de camada com checkbox de 'usar seleção'"""
    
    def __init__(self, label_text, filters, ...):
        self.label = QLabel(label_text)
        self.combo = QComboBox()
        self.checkbox = QCheckBox("Usar apenas seleção")
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.combo)
        layout.addWidget(self.checkbox)
        self.setLayout(layout)
    
    def current_layer(self):
        """Método específico do widget"""
        return self.combo.currentData()

# core/ui/WidgetFactory.py
@staticmethod
def create_layer_input(label_text, filters, *, parent=None, separator_top=False):
    layout = QVBoxLayout()
    if separator_top:
        layout.addWidget(WidgetFactory._create_separator())
    
    widget = LayerInputWidget(label_text, filters, parent=parent)
    widget.setStyleSheet(Styles.layer_input_widget())
    layout.addWidget(widget)
    
    return widget
```

---

### **Categoria 3: Adaptação de Widgets Existentes**

**O que é:** Modificar parâmetro de widget existente sem quebrar compatibilidade.

**Exemplo:** `CheckboxGridWidget` já existe com `items_per_row=3`. Novo requisito: "adicionar linhas de separação entre grupos".

**Solução (✅ CORRETA):**
```python
def create_checkbox_grid(
    options_data=None,
    *,
    items_per_row=3,
    separator_lines=None,  # NOVO: [(índice, color), ...]
    ...
):
    widget = CheckboxGridWidget(
        options_data,
        items_per_row=items_per_row,
        separator_lines=separator_lines,  # passa ao widget
        ...
    )
    return widget

# Em CheckboxGridWidget
class CheckboxGridWidget(QWidget):
    def __init__(self, options_data, *, items_per_row=3, separator_lines=None, ...):
        # código existente mantido
        if separator_lines:
            # adiciona linhas de separação
            for idx, color in separator_lines:
                self._insert_separator(idx, color)
```

**❌ ERRADO (não fazer):**
```python
# Criar CheckboxGridWithSeparators que é idêntico ao outro
# Viola DRY (Don't Repeat Yourself)
```

---

## 📏 REGRAS

### ✅ **SEMPRE:**

- **Factory é único ponto de acesso a widgets**
  ```python
  from core.ui.WidgetFactory import WidgetFactory
  widget = WidgetFactory.create_label("Título")
  ```

- **Factory aplica estilos automaticamente**
  ```python
  # Não fazer:
  widget = WidgetFactory.create_label("Título")
  widget.setStyleSheet("color: red")
  
  # Factory já faz:
  widget.setStyleSheet(Styles.label())
  ```

- **Usar parâmetros nomeados opcionais para customização**
  ```python
  def create_checkbox_grid(
      ...,
      items_per_row=3,        # padrão
      separator_lines=None,   # opcional
      show_control_buttons=False,
      ...
  ):
  ```

- **Métodos específicos ficam no widget exclusivo**
  ```python
  # Não em Factory:
  widget = WidgetFactory.create_layer_input(...)
  widget.current_layer()  # ✅ Método do LayerInputWidget
  widget.set_layer(layer) # ✅ Método do LayerInputWidget
  ```

- **Lógica de população é responsabilidade do plugin**
  ```python
  widget = WidgetFactory.create_dropdown_selector(
      title="Selecione",
      options_dict={...}  # ✅ Plugin passa dados
  )
  # Factory não faz populate_dropdown()
  ```

- **Separadores opcionais em factory**
  ```python
  widget = WidgetFactory.create_layer_input(
      ...,
      separator_top=True,
      separator_bottom=False
  )
  ```

### ❌ **NUNCA:**

- Não importar QtWidgets em plugins
  ```python
  # ❌ NUNCA em plugins:
  from qgis.PyQt.QtWidgets import QLabel, QPushButton
  
  # ✅ SEMPRE via Factory:
  from core.ui.WidgetFactory import WidgetFactory
  label = WidgetFactory.create_label("Texto")
  ```

- Não criar métodos de população em Factory
  ```python
  # ❌ NUNCA:
  @staticmethod
  def populate_layer_selector(widget, layers):
      ...
  
  # ✅ SEMPRE no widget exclusivo:
  class LayerInputWidget(QWidget):
      def set_layers(self, layers):
          ...
  ```

- Não criar widgets com lógica de evento em Factory
  ```python
  # ❌ NUNCA (Factory):
  def create_color_button(...):
      btn = QPushButton()
      btn.clicked.connect(open_color_dialog)  # LÓGICA
      return btn
  
  # ✅ SEMPRE (Widget exclusivo):
  class ColorButtonWidget(QWidget):
      def __init__(self):
          self.btn = QPushButton()
          self.btn.clicked.connect(self._on_color_click)
      
      def _on_color_click(self):
          dialog = QColorDialog()
          ...
  ```

- Não duplicar widgets funcionais
  ```python
  # ❌ NUNCA:
  # CheckboxGrid.py (original)
  # CheckboxGridWithSeparators.py (novo, idêntico com 1 linha a mais)
  
  # ✅ SEMPRE:
  # Adaptar CheckboxGrid com parâmetro opcional separator_lines
  ```

- Não customizar estilos por componente em Factory
  ```python
  # ❌ NUNCA:
  widget.setStyleSheet(Styles.label() + "; color: green")
  
  # ✅ SEMPRE:
  # Se precisa estilo customizado, criar em Styles.py
  widget.setStyleSheet(Styles.label_success())
  ```

---

## 📦 DEPENDÊNCIAS

```python
from core.ui.WidgetFactory import WidgetFactory
from resources.styles.Styles import Styles
from resources.widgets.LayerInputWidget import LayerInputWidget
from resources.widgets.CheckboxGridWidget import CheckboxGridWidget
# ... outros widgets exclusivos
from i18n.TranslationManager import STR
```

---

## 🔧 EXEMPLOS

### **Exemplo 1: Plugin Usa Factory (Correto)**

```python
# plugins/MyPlugin.py

from core.ui.WidgetFactory import WidgetFactory
from i18n.TranslationManager import STR
from utils.ToolKeys import ToolKey

class MyPluginDialog:
    def __init__(self):
        layout = QVBoxLayout()
        
        # ✅ Usar Factory para tudo
        title = WidgetFactory.create_label(
            text=STR.TITLE_MY_PLUGIN,
            bold=True
        )
        
        layer_input = WidgetFactory.create_layer_input(
            label_text=f"{STR.LAYER}:",
            filters=["Polygon"],
            separator_bottom=True
        )
        
        width_input = WidgetFactory.create_double_spin_input(
            label_text=f"{STR.WIDTH} (mm):",
            value=2.0,
            minimum=0.1
        )
        
        layout.addWidget(title)
        layout.addWidget(layer_input)
        layout.addWidget(width_input)
        
        self.layer_widget = layer_input
        self.width_widget = width_input
    
    def get_layer(self):
        return self.layer_widget.current_layer()  # ✅ Método do widget
```

---

### **Exemplo 2: Criar Widget Exclusivo**

```python
# resources/widgets/DroneCoordinatesWidget.py

from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit
from ...resources.styles.Styles import Styles
from ...i18n.TranslationManager import STR

class DroneCoordinatesWidget(QWidget):
    """Widget exclusivo para entrada de coordenadas de drone"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.lat_label = QLabel(f"{STR.LATITUDE}:")
        self.lon_label = QLabel(f"{STR.LONGITUDE}:")
        self.alt_label = QLabel(f"{STR.ALTITUDE}:")
        
        self.lat_input = QLineEdit()
        self.lon_input = QLineEdit()
        self.alt_input = QLineEdit()
        
        layout = QVBoxLayout()
        
        # Linha 1: Latitude
        h1 = QHBoxLayout()
        h1.addWidget(self.lat_label)
        h1.addWidget(self.lat_input)
        layout.addLayout(h1)
        
        # Linha 2: Longitude
        h2 = QHBoxLayout()
        h2.addWidget(self.lon_label)
        h2.addWidget(self.lon_input)
        layout.addLayout(h2)
        
        # Linha 3: Altitude
        h3 = QHBoxLayout()
        h3.addWidget(self.alt_label)
        h3.addWidget(self.alt_input)
        layout.addLayout(h3)
        
        self.setLayout(layout)
        self._apply_styles()
    
    def _apply_styles(self):
        """Aplicar estilos via Styles.py"""
        self.lat_input.setStyleSheet(Styles.input())
        self.lon_input.setStyleSheet(Styles.input())
        self.alt_input.setStyleSheet(Styles.input())
    
    def get_coordinates(self):
        """Lógica específica do widget"""
        try:
            return {
                "latitude": float(self.lat_input.text()),
                "longitude": float(self.lon_input.text()),
                "altitude": float(self.alt_input.text())
            }
        except ValueError:
            return None
    
    def validate(self):
        """Validação específica"""
        coords = self.get_coordinates()
        if not coords:
            return False
        if not (-90 <= coords["latitude"] <= 90):
            return False
        if not (-180 <= coords["longitude"] <= 180):
            return False
        return True

# core/ui/WidgetFactory.py
@staticmethod
def create_drone_coordinates_input(
    *,
    parent=None,
    separator_top=False,
    separator_bottom=True
):
    layout = QVBoxLayout()
    
    if separator_top:
        layout.addWidget(WidgetFactory._create_separator())
    
    widget = DroneCoordinatesWidget(parent=parent)
    layout.addWidget(widget)
    
    if separator_bottom:
        layout.addWidget(WidgetFactory._create_separator())
    
    return widget
```

**Uso em Plugin:**
```python
drone_widget = WidgetFactory.create_drone_coordinates_input(separator_bottom=True)

# Plugin chama métodos do widget, não da factory
coords = drone_widget.get_coordinates()
is_valid = drone_widget.validate()
```

---

### **Exemplo 3: Adaptar Widget Existente**

**Situação:** `CheckboxGridWidget` existe. Novo requisito: separadores entre grupos.

```python
# resources/widgets/CheckboxGridWidget.py
class CheckboxGridWidget(QWidget):
    def __init__(
        self,
        options_data,
        *,
        items_per_row=3,
        separator_indices=None,  # NOVO: [1, 3, 5] = índices para separadores
        ...
    ):
        super().__init__()
        self.options_data = options_data
        self.items_per_row = items_per_row
        self.separator_indices = separator_indices or []
        
        self._build_grid()
    
    def _build_grid(self):
        grid_layout = QGridLayout()
        
        for idx, item in enumerate(self.options_data):
            if idx in self.separator_indices:
                # Inserir separador
                grid_layout.addWidget(
                    self._create_separator(),
                    idx, 0, 1, self.items_per_row
                )
            
            # Inserir checkbox
            # ... resto do código

# core/ui/WidgetFactory.py
@staticmethod
def create_checkbox_grid(
    options_data,
    *,
    items_per_row=3,
    separator_indices=None,  # NOVO
    ...
):
    layout = QVBoxLayout()
    widget = CheckboxGridWidget(
        options_data,
        items_per_row=items_per_row,
        separator_indices=separator_indices,  # passa ao widget
        ...
    )
    layout.addWidget(widget)
    return widget

# Plugin (compatível com código antigo)
grid = WidgetFactory.create_checkbox_grid(
    options_data={"a": "Label A", "b": "Label B"},
    items_per_row=2
    # separator_indices não precisa (opcional)
)

# Novo código aproveita:
grid = WidgetFactory.create_checkbox_grid(
    options_data={...},
    items_per_row=2,
    separator_indices=[2, 4]  # Novo parâmetro
)
```

---

### **Exemplo 4: Componente Simples vs Composto**

```python
# ✅ SIMPLES (retorna Qt puro):
label = WidgetFactory.create_label(text="Título", bold=True)
# Retorna: QLabel

# ✅ COMPOSTO (retorna widget exclusivo):
layer_input = WidgetFactory.create_layer_input(
    label_text="Camada",
    filters=["Polygon"]
)
# Retorna: LayerInputWidget

# Plugin usa:
layer = layer_input.current_layer()  # Método do widget composto
label.setText("Novo título")  # Qt puro
```

---

## 📋 CHECKLIST: CRIAR NOVO MÉTODO EM FACTORY

**Pergunta 1:** É apenas 1 widget Qt?
- ✅ SIM → Criar método que retorna widget simples
- ❌ NÃO → Próxima pergunta

**Pergunta 2:** São 2-3 widgets + layout?
- ✅ SIM → Criar Widget exclusivo + método em Factory
- ❌ NÃO → Próxima pergunta

**Pergunta 3:** Precisa de métodos específicos (populate, validate, etc)?
- ✅ SIM → Deve ser Widget exclusivo + método em Factory
- ❌ NÃO → Perguntar novamente (é realmente composto?)

**Pergunta 4:** Já existe widget similar?
- ✅ SIM → Adaptar com parâmetros opcionais
- ❌ NÃO → Criar novo

---

## ⚠️ LIMITAÇÕES

- **Factory não faz lógica:** Cada widget responsável por si
- **Sem getter/setter genérico:** Cada widget expõe sua interface
- **Estilos fixos:** Customização por plugin é ❌
- **Sem propagação de eventos:** Factory cria, widget gerencia

---

## 🔍 VALIDAÇÃO

| Critério | Status |
|----------|--------|
| **Reutilizável?** | ✅ SIM — centraliza UI |
| **Clara?** | ✅ SIM — 3 categorias bem definidas |
| **Contrato rígido?** | ✅ SIM — Plugins/Factory/Widgets isolados |
| **Extensível?** | ✅ SIM — Adaptar vs novo é claro |

---

## 🎓 CONCLUSÃO

**WidgetFactory é contrato entre Plugins e QtWidgets:**

1. **Plugins:** NUNCA importam QtWidgets direto
2. **Factory:** Cria (sem lógica) + estiliza
3. **Widgets exclusivos:** Encapsulam lógica específica
4. **Styles:** Fonte única de estilos
5. **Adaptação:** Preferível a duplicação

**Três camadas:**
- **Simples:** Qt puro + estilo (QLabel, QLineEdit, etc)
- **Composto:** 2-3 widgets + widget exclusivo
- **Adaptação:** Parâmetros opcionais, nunca novo widget idêntico

**Contrato é rígido. Sem exceções.**

## Hist�rico de Mudan�as

| Data | Vers�o | Descri��o |
|------|--------|-----------|
| 2026-04-20 | 1.0.1 | Adicionado padr�o de estilo dedicado para di�logos simples com escopo por objectName no Styles.py (ex.: ProjectNameDialog). |
| 2026-04-20 | 1.0.2 | Ajustado padr�o para estiliza��o confi�vel de bot�es em QDialogButtonBox usando selector dedicado + objectName dos bot�es, evitando override por tema nativo. |
| 2026-04-20 | 1.0.3 | Em di�logos simples com necessidade de estilo consistente de a��o, preferir `QPushButton` expl�cito no lugar de `QDialogButtonBox` para evitar interfer�ncia de tema nativo. |
| 2026-04-20 | 1.0.4 | Ajustado stylesheet de ProjectNameDialog para escopo direto em `QPushButton` por `objectName`, removendo seletor legado com `QDialogButtonBox`. |
