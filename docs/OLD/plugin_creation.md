# 🎯 SKILL: Criação de Plugins QGIS Cadmus

**Especialista:** Sistema de Plugins | Arquitetura | Logging | Persistência  
**Versão:** 1.0 | Abril 2026  
**Status:** Completo e Testado

---

## ⚡ TL;DR (30 segundos)

Plugin Cadmus = **ToolRegistry** (o quê) + **Tool** (metadados) + **MenuManager** (onde) + **Plugin** (como executa)

**Fluxo:** ToolRegistry define → MenuManager cria menu → User clica → executor dispara → Plugin executa

**3 Tipos principais:**
- **INSTANT:** Sem UI (validar, processar, feedback)
- **DIALOG:** Com UI (herdar `BasePluginMTL`, WidgetFactory para widgets)
- **MAP_TOOL:** Click no mapa (herdar `QgsMapTool`)

---

## 📐 Arquitetura

### Separação de Responsabilidades

```
ToolRegistry (core/config/)
  ├─ Define ferramentas (metadados + executor)
  └─ Delegador: run_xxx() → Plugin.execute()

MenuManager (core/config/)
  ├─ Converte Tool em QAction
  └─ Cria menus/toolbar dinamicamente

Tool Model (core/model/)
  └─ name, icon, category, executor, tooltip, order, main_action

Plugin (plugins/)
  ├─ Lógica pura (sincronous ou async)
  ├─ Logging com LogUtils
  ├─ Preferences com Preferences
  └─ Feedback com QgisMessageUtil
```

**Por quê?** Menus dinâmicos, plugins descacoplados, fácil reordenar/renomear.

### Fluxo Completo

```
1. User clica botão na toolbar
   ↓
2. QAction.triggered → Tool.executor()
   ↓
3. ToolRegistry.run_xxx()
   ├─ Importa Plugin
   └─ Chama plugin.execute()
   
4. Plugin.execute()
   ├─ Validações (layer? editable?)
   ├─ Lógica (_process_layer)
   └─ Feedback (QgisMessageUtil)

5. Se DIALOG: BasePluginMTL
   ├─ Logger auto-criado em init()
   ├─ Preferences carregadas em _load_prefs()
   └─ Preferences salvam em closeEvent()
```

---

## 🔧 Sistema de Plugins

### 5 Tipos de Plugins

| Tipo | UI | Sync | Uso |
|------|----|----|-----|
| **INSTANT** | ❌ | ✅ | RemoveKmlFields, Restart, Conversões |
| **DIALOG** | ✅ | ✅ | Settings, LoadFolder, Grids |
| **MAP_TOOL** | Resultado | ✅ | Click coordenadas, desenhar |
| **BACKGROUND** | Status bar | ❌ | RasterMassSampler, pesado |
| **PROCESSING** | QGIS Alg | ❌ | Algoritmos ProcessingToolbox |

### ToolTypeEnum

```python
from ..core.enum import ToolTypeEnum

tool_type = ToolTypeEnum.INSTANT    # ou DIALOG, MAP_TOOL, etc.
```

### Tool Model

```python
from ..core.model.Tool import Tool

tool = Tool(
    name=STR.MINHA_FERRAMENTA,           # i18n
    icon=im.icon(im.MINHA_ICON),         # IconManager
    category=self.VECTOR,                 # SYSTEM, LAYOUTS, FOLDER, VECTOR, AGRICULTURE, RASTER
    tool_type=ToolTypeEnum.INSTANT,      # Tipo
    main_action=False,                    # True = principal na toolbar
    executor=self.run_meu_plugin,         # Callback (ToolRegistry method)
    tooltip=STR.MINHA_FERRAMENTA_TOOLTIP, # i18n
    order=25,                             # Posição no menu
    show_in_toolbar=True,                 # Aparecer na toolbar
)
```

### Registro em ToolRegistry

```python
# core/config/ToolRegistry.py

def _create_tool_list(self):
    tools = []
    
    # Criar Tool
    meu_plugin = Tool(
        name=STR.MINHA_FERRAMENTA,
        icon=im.icon(im.ICONE),
        category=self.VECTOR,              # Categoria própria
        tool_type=ToolTypeEnum.INSTANT,    # Seu tipo
        executor=self.run_meu_plugin,
        tooltip=STR.TOOLTIP,
        order=25,
        show_in_toolbar=True,
    )
    tools.append(meu_plugin)
    
    # ... mais ferramentas
    return tools

# Delegador (abaixo em ToolRegistry)
def run_meu_plugin(self):
    """Delegador: importa plugin e executa."""
    from ..plugins.MeuPlugin import MeuPlugin
    plugin = MeuPlugin(self.iface)
    plugin.execute()  # ou .exec_() para DIALOG modal
```

---

## 📝 Criando Plugin INSTANT

### Estrutura

```python
# plugins/MeuPlugin.py
# -*- coding: utf-8 -*-

from ..core.config.LogUtils import LogUtils
from ..utils.ToolKeys import ToolKey
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.ProjectUtils import ProjectUtils
from ..i18n.TranslationManager import STR

class MeuPlugin:
    """Plugin sem UI."""
    
    TOOL_KEY = ToolKey.MINHA_FERRAMENTA
    
    def __init__(self, iface):
        self.iface = iface
        self.logger = LogUtils(
            tool=self.TOOL_KEY,
            class_name="MeuPlugin",
            level=LogUtils.DEBUG
        )
    
    def execute(self):
        """Entry point."""
        self.logger.info("Iniciando")
        
        # 1️⃣ VALIDAÇÃO
        layer = ProjectUtils.get_active_vector_layer(
            self.iface.activeLayer(),
            self.logger,
            require_editable=True
        )
        if not layer:
            self.logger.warning("Nenhuma camada")
            QgisMessageUtil.bar_critical(self.iface, STR.SELECT_VECTOR_LAYER)
            return
        
        # 2️⃣ LÓGICA
        try:
            result = self._process(layer)
            self.logger.info(f"Sucesso: {result}")
        except Exception as e:
            self.logger.error(f"Erro: {e}")
            self.logger.exception(e)  # com traceback
            QgisMessageUtil.bar_critical(self.iface, f"Erro: {e}")
            return
        
        # 3️⃣ FEEDBACK
        QgisMessageUtil.bar_success(self.iface, f"Pronto: {result}")
    
    def _process(self, layer):
        """Lógica pura."""
        # implementação
        return "Resultado"
```

### Checklist INSTANT

```
[ ] 1. ToolKey em utils/ToolKeys.py
[ ] 2. Strings i18n em i18n/Strings_*.py (todos idiomas!)
[ ] 3. Plugin em plugins/MeuPlugin.py
[ ] 4. Registrado em ToolRegistry._create_tool_list()
[ ] 5. Delegador run_meu_plugin em ToolRegistry
[ ] 6. Logger com self.logger = LogUtils(...)
[ ] 7. Validações de entrada
[ ] 8. Try/except Exception
[ ] 9. Feedback QgisMessageUtil
[ ] 10. Testar, verificar logs em cadmus_*.log
```

---

## 🪟 Criando Plugin DIALOG

### Estrutura

```python
# plugins/MeuDialog.py
# -*- coding: utf-8 -*-

from ..plugins.BasePlugin import BasePluginMTL
from ..core.ui.WidgetFactory import WidgetFactory
from ..utils.ToolKeys import ToolKey
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..i18n.TranslationManager import STR

class MeuDialog(BasePluginMTL):
    """Plugin com interface."""
    
    TOOL_KEY = ToolKey.MINHA_FERRAMENTA
    AUTO_SAVE_PREFS_ON_CLOSE = True  # Auto-save prefs ao fechar
    
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.init(
            tool_key=self.TOOL_KEY,
            class_name="MeuDialog",
            build_ui=True  # ← Constrói UI automático
        )
    
    def _build_ui(self, **kwargs):
        """Chamado por init()."""
        super()._build_ui(
            title=STR.MINHA_FERRAMENTA,
            icon_path="meu_icon.ico",
            enable_scroll=True,
            minimum_size=(400, 300),
        )
        
        # Adicionar widgets com WidgetFactory
        layer_layout, self.layer_combo = WidgetFactory.create_layer_selector(
            iface=self.iface,
            parent=self,
            layer_type=WidgetFactory.VECTOR,
            separator_bottom=True,
        )
        self.layout.addLayout(layer_layout)
        
        text_layout, self.input_text = WidgetFactory.create_text_input(
            title="Nome:",
            placeholder="Digite...",
            separator_bottom=True,
        )
        self.layout.addLayout(text_layout)
        
        btn_layout, self.btn_execute = WidgetFactory.create_simple_button(
            text="Executar",
            separator_top=True,
        )
        self.btn_execute.clicked.connect(self._on_execute)
        self.layout.addLayout(btn_layout)
    
    def _load_prefs(self):
        """Restaurar valores salvos (chamado após _build_ui)."""
        super()._load_prefs()
        self.input_text.setText(self.preferences.get("text", ""))
    
    def _on_execute(self):
        """Callback botão."""
        self.logger.info("Executando")
        
        layer = self.layer_combo.currentLayer()
        text = self.input_text.text().strip()
        
        if not layer or not text:
            QgisMessageUtil.bar_critical(self.iface, "Campo inválido")
            return
        
        try:
            result = self._process(layer, text)
            self.logger.info(f"Sucesso: {result}")
            QgisMessageUtil.bar_success(self.iface, "Pronto!")
        except Exception as e:
            self.logger.error(f"Erro: {e}")
            self.logger.exception(e)
            QgisMessageUtil.bar_critical(self.iface, f"Erro: {e}")
    
    def _process(self, layer, text):
        """Lógica."""
        return f"Processado: {layer.name()}"
    
    def _save_prefs(self):
        """Salvar valores (chamado em closeEvent)."""
        self.preferences["text"] = self.input_text.text()
        from ..utils.Preferences import save_tool_prefs
        save_tool_prefs(self.TOOL_KEY, self.preferences)
```

### WidgetFactory (Widgets Prontos)

```python
# Usar em _build_ui():

# Text input
layout, widget = WidgetFactory.create_text_input(
    title="Título:",
    placeholder="hint...",
    separator_top=False,
    separator_bottom=True,
)

# Layer selector
layout, widget = WidgetFactory.create_layer_selector(
    iface=self.iface,
    parent=self,
    layer_type=WidgetFactory.VECTOR,  # ou RASTER
    separator_bottom=True,
)

# Path selector
layout, widget = WidgetFactory.create_path_selector(
    parent=self,
    title="Pasta:",
    mode="folder",  # ou "file"
    separator_bottom=True,
)

# Spinner
layout, widget = WidgetFactory.create_integer_spin_input(
    title="Quantidade:",
    minimum=1,
    maximum=1000,
    step=1,
    separator_bottom=True,
)

# Button
layout, widget = WidgetFactory.create_simple_button(
    text="OK",
    parent=self,
    separator_top=True,
)

# Checkboxes
layout, widget = WidgetFactory.create_checkbox_grid(
    {"key1": "Label 1", "key2": "Label 2"},
    items_per_row=2,
    separator_bottom=True,
)

# Radio buttons
layout, widget = WidgetFactory.create_radio_button_grid(
    items=["Opção A", "Opção B"],
    columns=2,
    title="Selecione:",
    separator_bottom=True,
)
```

### Checklist DIALOG

```
[ ] 1-5. Mesmo que INSTANT (ToolKey, STR, ToolRegistry, etc.)
[ ] 6. Herdar de BasePluginMTL
[ ] 7. Implementar _build_ui() com widgets
[ ] 8. Implementar _load_prefs() para restaurar
[ ] 9. Implementar _save_prefs() para persistir
[ ] 10. AUTO_SAVE_PREFS_ON_CLOSE = True
[ ] 11. Callback para botão executar
[ ] 12. Dialog modal: dialog.exec_() em delegador
```

---

## 🗺️ Criando MAP_TOOL

```python
# plugins/MeuMapTool.py

from qgis.gui import QgsMapTool
from ..core.config.LogUtils import LogUtils
from ..utils.ToolKeys import ToolKey

class MeuMapTool(QgsMapTool):
    """Ferramenta de mapa."""
    
    def __init__(self, iface):
        super().__init__(iface.mapCanvas())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.logger = LogUtils(
            tool=ToolKey.MINHA_FERRAMENTA,
            class_name="MeuMapTool",
        )
    
    def canvasReleaseEvent(self, event):
        """Disparado ao soltar mouse."""
        self.logger.debug("Click detectado")
        
        # Snap automático
        snap = self.canvas.snappingUtils().snapToMap(event.pos())
        point = snap.point() if snap.isValid() else self.toMapCoordinates(event.pos())
        
        # Processar ponto
        x, y = point.x(), point.y()
        self.logger.debug(f"Ponto: {x}, {y}")
```

---

## 📊 Sistema de Logging

### Inicialização (1x ao boot)

```python
# Em PluginBootstrap.startUp():
from pathlib import Path
from ..core.config.LogUtils import LogUtils

plugin_root = Path(__file__).parent.parent
LogUtils.init(plugin_root)
# Cria log em ~/.../Cadmus/log/cadmus_YYYYMMDD_HHMMSS_pidXXXX.log
```

### Uso em Classes

```python
from ..core.config.LogUtils import LogUtils
from ..utils.ToolKeys import ToolKey

class MeuPlugin:
    def __init__(self, iface):
        self.logger = LogUtils(
            tool=ToolKey.MINHA_FERRAMENTA,
            class_name="MeuPlugin",
            level=LogUtils.DEBUG  # opcional
        )
    
    def execute(self):
        self.logger.info("Msg geral")
        self.logger.debug("Debug detalhado")
        self.logger.warning("Aviso")
        self.logger.error("Erro não-fatal")
        self.logger.critical("Erro crítico")
        
        try:
            # código
        except Exception as e:
            self.logger.exception(e)  # com traceback
```

### Estrutura de Log (JSON)

```json
{
  "ts": "2026-04-11T10:30:45",
  "level": "ERROR",
  "plugin": "Cadmus",
  "plugin_version": "2.0.7",
  "session_id": "uuid-xxx",
  "pid": 12345,
  "thread": "MainThread",
  "tool": "minha_ferramenta",
  "class": "MeuPlugin",
  "code": "CUSTOM_CODE",
  "msg": "Described message",
  "data": {"key": "value"}
}
```

---

## 💾 Sistema de Preferências

### Armazenamento

```
~/.../AppDataLocation/MTLTools/mtl_prefs.json

{
  "system": { "language": "pt_BR", "crs": "EPSG:4326" },
  "minha_ferramenta": { "window_width": 500, "text": "valor_salvo" }
}
```

### API

```python
from ..utils.Preferences import Preferences
from ..utils.ToolKeys import ToolKey

# Carregar
prefs = Preferences.load_tool_prefs(ToolKey.MINHA_FERRAMENTA)
valor = prefs.get("chave", "default")

# Salvar
prefs["chave"] = novo_valor
Preferences.save_tool_prefs(ToolKey.MINHA_FERRAMENTA, prefs)
```

### Em DIALOG (Automático)

```python
class MeuDialog(BasePluginMTL):
    AUTO_SAVE_PREFS_ON_CLOSE = True  # ← Auto-save
    
    def _load_prefs(self):
        """Restaura widget values."""
        super()._load_prefs()
        self.widget.setValue(self.preferences.get("chave", default))
    
    def _save_prefs(self):
        """Salva widget values."""
        self.preferences["chave"] = self.widget.value()
        from ..utils.Preferences import save_tool_prefs
        save_tool_prefs(self.TOOL_KEY, self.preferences)
```

---

## ⚙️ Padrões Essenciais

### 1️⃣ Validação

```python
def execute(self):
    # Validar layer
    layer = ProjectUtils.get_active_vector_layer(
        self.iface.activeLayer(),
        self.logger,
        require_editable=True
    )
    if not layer:
        QgisMessageUtil.bar_critical(self.iface, STR.SELECT_VECTOR_LAYER)
        return
    
    # Validar tipo geometria
    from qgis.core import QgsWkbTypes
    if layer.geometryType() != QgsWkbTypes.PolygonGeometry:
        QgisMessageUtil.bar_critical(self.iface, "Deve ser polígono")
        return
```

### 2️⃣ Error Handling

```python
try:
    result = self._process(layer)
    self.logger.info("Sucesso", features=result)
except ValueError as e:
    self.logger.warning(f"Validação: {e}")
    QgisMessageUtil.bar_warning(self.iface, str(e))
except Exception as e:
    self.logger.error(f"Erro: {e}")
    self.logger.exception(e)  # traceback
    QgisMessageUtil.bar_critical(self.iface, f"Erro: {e}")
```

### 3️⃣ Feedback Ao Usuário

```python
from ..utils.QgisMessageUtil import QgisMessageUtil

QgisMessageUtil.bar_info(iface, "Info")           # Azul
QgisMessageUtil.bar_warning(iface, "Aviso")       # Amarelo
QgisMessageUtil.bar_critical(iface, "Erro")       # Vermelho
QgisMessageUtil.bar_success(iface, "Pronto!")     # Verde

confirmed = QgisMessageUtil.confirm(iface, "Tem certeza?")
```

### 4️⃣ Async para Pesado

```python
from ..core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from ..core.engine_tasks.ExecutionContext import ExecutionContext

context = ExecutionContext({"layer": layer, "iface": self.iface})

engine = AsyncPipelineEngine()
engine.add_step(Step1())
engine.add_step(Step2())

engine.on_success(lambda ctx: self._on_success(ctx))
engine.on_error(lambda ctx, errs: self._on_error(errs))

engine.start(context)
```

### 5️⃣ Strings Internacionalizadas

```python
# ❌ Nunca hardcode
QgisMessageUtil.bar_critical(iface, "Selecione camada")

# ✅ Sempre usar STR
from ..i18n.TranslationManager import STR
QgisMessageUtil.bar_critical(iface, STR.SELECT_VECTOR_LAYER)

# Definir em i18n/Strings_pt_BR.py
class STR:
    SELECT_VECTOR_LAYER = "Selecione uma camada vetorial"
```

---

## 🎯 Setup Completo (Checklist)

```
[ ] 1. ToolKey: Adicionar em utils/ToolKeys.py
      MINHA_FERRAMENTA = "minha_ferramenta"

[ ] 2. Strings i18n: Adicionar em i18n/Strings_*.py (5 idiomas!)
      MINHA_FERRAMENTA_TITLE = "Título"
      MINHA_FERRAMENTA_TOOLTIP = "Dica"

[ ] 3. Plugin: Criar em plugins/MeuPlugin.py
      - __init__(iface)
      - execute() ou _build_ui()
      - Logger LogUtils
      - Validações
      - Try/except Exception
      - Feedback QgisMessageUtil

[ ] 4. ToolRegistry: Registrar em core/config/ToolRegistry.py
      - Tool criado em _create_tool_list()
      - Delegador run_xxx() implementado

[ ] 5. DIALOG extras (se DIALOG):
      - Herdar BasePluginMTL
      - _load_prefs()
      - _save_prefs()
      - AUTO_SAVE_PREFS_ON_CLOSE = True

[ ] 6. Testar
      - Abrir QGIS
      - Plugin aparece no menu
      - Funciona sem erros
      - Verifica logs: ~/.../Cadmus/log/cadmus_*.log
```

---

## 🐛 Troubleshooting

### Plugin não aparece?
- Registrou em ToolRegistry._create_tool_list()?
- Adicionou `tools.append(meu_plugin)`?
- Criou delegador `run_meu_plugin()`?
- Reiniciou QGIS?

### Plugin aparece mas não funciona?
- Ver logs em `~/.../Cadmus/log/cadmus_*.log`
- Procurar `"level": "ERROR"`
- Ler stacktrace em `"data": {"exception": {...}}`

### Strings não traduzidas?
- Definir em **todos** Strings_*.py:
  - Strings_pt_BR.py (base)
  - Strings_en.py
  - Strings_de.py
  - Strings_es.py

### Preferences não salvam?
- `AUTO_SAVE_PREFS_ON_CLOSE = True`?
- Implementar `_save_prefs()`?
- Chamar `save_tool_prefs()`?

### UI congela?
- Tarefas pesadas em thread separada
- Usar `AsyncPipelineEngine` para > 19 items
- Não fazer loops longos em thread principal

---

## 📚 Referências Rápidas

### Imports Essenciais

```python
# Logging
from ..core.config.LogUtils import LogUtils

# Preferências
from ..utils.Preferences import Preferences, load_tool_prefs, save_tool_prefs

# IDs de ferramentas
from ..utils.ToolKeys import ToolKey

# Feedback
from ..utils.QgisMessageUtil import QgisMessageUtil

# Layer utilities
from ..utils.ProjectUtils import ProjectUtils

# Internacionalização
from ..i18n.TranslationManager import STR

# UI
from ..core.ui.WidgetFactory import WidgetFactory
from ..plugins.BasePlugin import BasePluginMTL
from ..plugins.BaseDialog import BaseDialog

# Models
from ..core.model.Tool import Tool
from ..core.enum.ToolTypeEnum import ToolTypeEnum

# QGIS
from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsProject
from qgis.gui import QgsMapTool
from qgis.PyQt.QtWidgets import QDialog, QAction
```

### ToolKey Template

```python
# utils/ToolKeys.py
class ToolKey:
    MINHA_FERRAMENTA = "minha_ferramenta"
```

### Tool Template

```python
Tool(
    name=STR.XXX_TITLE,
    icon=im.icon(im.ICON_NAME),
    category=self.VECTOR,  # SYSTEM, LAYOUTS, FOLDER, VECTOR, AGRICULTURE, RASTER
    tool_type=ToolTypeEnum.INSTANT,  # ou DIALOG, MAP_TOOL, etc
    main_action=False,
    executor=self.run_xxx,
    tooltip=STR.XXX_TOOLTIP,
    order=25,
    show_in_toolbar=True,
)
```

---

## 📈 Complexidade Por Tipo

```
INSTANT simples:      1-2 horas (criar + testar)
DIALOG básico:        4-5 horas (UI + prefs)
DIALOG complexo:      8-10 horas (muitos widgets)
MAP_TOOL:             3-4 horas (evento + resultado)
Com Async:            +4-5 horas (pipeline + steps)
```

---

## 🏆 Boas Práticas

✅ **Fazer:**
- Logar em JSON com contexto
- Validar entrada antes de processar
- Usar try/except Exception
- Feedback visual ao usuário
- Strings via STR.CHAVE
- Preferências em JSON
- WidgetFactory para UI
- Separação lógica/UI

❌ **Não fazer:**
- Strings hardcoded
- Bare except: pass
- Bloqueio UI com loops
- Importar Qt direto (usar qgis.PyQt)
- Suprimir erros silenciosamente
- Modificar plugin sem renovação
- Hardcoded paths

---

## 🚀 Quick Start (30 minutos)

### Passo 1: Criar ToolKey (1 min)
```python
# utils/ToolKeys.py
class ToolKey:
    MINHA_FERRAMENTA = "minha_ferramenta"
```

### Passo 2: Criar Strings (2 min)
```python
# i18n/Strings_pt_BR.py (+ en, de, es)
class STR:
    MINHA_FERRAMENTA = "Minha Ferramenta"
    MINHA_FERRAMENTA_TOOLTIP = "Dica"
```

### Passo 3: Criar Plugin (10 min)
```python
# plugins/MeuPlugin.py
class MeuPlugin:
    def __init__(self, iface): ...
    def execute(self): ...
```

### Passo 4: Registrar (5 min)
```python
# core/config/ToolRegistry.py
meu_plugin = Tool(...)
tools.append(meu_plugin)

def run_meu_plugin(self):
    from ..plugins.MeuPlugin import MeuPlugin
    plugin = MeuPlugin(self.iface)
    plugin.execute()
```

### Passo 5: Testar (10 min)
- QGIS init/load → menu aparece
- Click → funciona
- Logs: ~/.../Cadmus/log/cadmus_*.log

**Pronto!** 🎉

---

**Especialista em:** Sistema de Plugins QGIS | Logging Estruturado | Persistência de Dados | Arquitetura Plugin-Agnostic  
**Compatível:** QGIS 3.16+, Qt5 ↔ Qt6, Python 3.10+  
**Status:** ✅ Completo e Pronto

