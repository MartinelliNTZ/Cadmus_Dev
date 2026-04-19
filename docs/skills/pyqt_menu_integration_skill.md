# SKILL: Ciclo de Vida PyQtSignalManager, BasePluginMTL e Separação de Responsabilidade

Especialista: `PyQtSignalManager` | `BasePluginMTL` | `MenuManager` | sinais PyQt | ciclo de vida
Versao: 2.0 | Abril 2026
Status: Pronto para uso

---

## TL;DR

**Separação de responsabilidade clara:**

1. **BasePluginMTL.\_\_init\_\_** → apenas emite sinal "fui aberto"
2. **BasePluginMTL.init()** → emite novamente via hub global (com contexto)
3. **BasePluginMTL.on_finish_plugin()** → atualiza preferences (main_action por categoria)
4. **PyQtSignalManager** → neutro, escuta e loga sinais (preparado para orquestração futura)
5. **MenuManager** → criado em `cadmus_plugin.py`, reconstruído via `get_instance()` (fora do BasePlugin)

---

## Quando usar

Use `PyQtSignalManager` para:

- Escutar sinais globais de instanciação sem interferir na lógica
- Logar eventos de plugins de forma centralizada
- Manter um hub neutro para futuros sinais PyQt

Use `BasePluginMTL` para:

- Emitir sinais de instanciação (lógica de UI)
- Atualizar preferences ao fechar (lógica de estado)

Nao use para:

- Criar menus ou toolbars (responsabilidade de `cadmus_plugin.py`)
- Instanciar MenuManager (já é singleton em `cadmus_plugin.py`)
- Reconstruir toolbar (será feito por callback/sinal futuramente)

---

## Regras praticas

1. `BasePluginMTL.__init__()`: super().__init__() simples, sem lógica
2. `BasePluginMTL.init()`: emita sinal com contexto completo; inicialize logger após ativar sinal
3. `BasePluginMTL.on_finish_plugin()`: apenas preferences logic, sem MenuManager
4. `PyQtSignalManager`: neutro, apenas `.start()` e `.stop()`, loga eventos
5. **NÃO** instancie MenuManager em BasePluginMTL; use singleton via `MenuManager.get_instance()` se necessário (futuramente via sinal)

---

## Padrao: Ciclo de vida correto

### 1. CadmusPlugin.initGui() - Criar UI uma vez

```python
def initGui(self):
    # ... bootstrap ...
    
    # Inicializar PyQtSignalManager para escutar
    self.pyqt_signal_manager = PyQtSignalManager(tool_key=self.TOOL_KEY)
    self.pyqt_signal_manager.start()
    
    # Criar ToolRegistry
    self.tool_registry = ToolRegistry(self.iface)
    
    # Criar MenuManager e UI (UMA VEZ)
    self.menu_manager = MenuManager(self.iface, self.tool_registry.tools, self.logger)
    self.menu_manager.create_menu()
    self.menu_manager.create_toolbar()
    self.menu_manager.populate_menus()
```

### 2. BasePluginMTL.__init__() - Vazio

```python
def __init__(self, parent=None):
    super().__init__(parent)
    # Sem lógica; tudo vai para init()
```

### 3. BasePluginMTL.init() - Emitir sinal "fui aberto"

```python
def init(self, tool_key="base_plugin", class_name="BasePluginMTL", ...):
    self.TOOL_KEY = tool_key
    self.logger = LogUtils(tool=self.TOOL_KEY, class_name=class_name)
    self.preferences = Preferences.load_tool_prefs(self.TOOL_KEY)
    self._plugin_signal_context = {
        "tool_key": self.TOOL_KEY,
        "class_name": class_name,
        "plugin_name": self.PLUGIN_NAME or class_name,
        "build_ui": bool(build_ui),
    }
    
    # Emitir sinal: "fui aberto"
    try:
        from ..core.config.PyQtSignalManager import get_plugin_signal_hub
        hub = get_plugin_signal_hub()
        hub.plugin_instantiated.emit(self._plugin_signal_context)
        self.logger.debug(f"[Plugin aberto] {self._plugin_signal_context['plugin_name']}")
    except Exception as e:
        self.logger.warning(f"Falha ao emitir sinal: {e}")
    
    # ... resto do init (build_ui, etc) ...
```

### 4. BasePluginMTL.on_finish_plugin() - Atualizar preferences

```python
def on_finish_plugin(self):
    try:
        # 1. Incrementar uso
        self.preferences["usages"] = self.preferences.get("usages", 0) + 1
        
        # 2. Obter categoria
        tool_category = self.preferences.get("category")
        if not tool_category:
            return
        
        # 3. Resetar main_action na categoria
        Preferences.set_value_for_all_tools("main_action", False, filter_by={"category": tool_category})
        
        # 4. Setar este tool como main_action=True
        self.preferences["main_action"] = True
        
        # 5. Salvar preferences
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
        self.logger.info("[on_finish_plugin] Preferences salvas")
        
    except Exception as e:
        self.logger.error(f"[on_finish_plugin] Erro: {e}")
```

### 5. PyQtSignalManager - Neutro

```python
class PyQtSignalManager(QObject):
    def start(self):
        self._signal_hub.plugin_instantiated.connect(self._on_plugin_instantiated)
        self.logger.info("[start] Escutando sinais")
    
    def stop(self):
        self._signal_hub.plugin_instantiated.disconnect(self._on_plugin_instantiated)
        self.logger.info("[stop] Desconectado")
    
    def _on_plugin_instantiated(self, payload):
        # Apenas loga: "fui aberto"
        self.logger.info(f"[plugin_instantiated] {payload}")
```

---

## Benefícios

- **Separação clara**: Cada classe tem responsabilidade única
- **Sem acoplamento**: BasePlugin não conhece MenuManager
- **Escalável**: Sinais podem ser processados por múltiplos listeners
- **Testável**: PyQtSignalManager pode ser mockado

---

## Dependências

- `qgis.PyQt.QtCore.QObject`, `pyqtSignal`
- `MenuManager` com singleton `get_instance()`
- `Preferences` para gerenciar main_action
- `LogUtils` para logging

---

## Ciclo de vida completo

```
cadmus_plugin.initGui()
  ↓
  PyQtSignalManager.start() [escutando]
  ↓
  MenuManager criado [singleton]
  ↓
Plugin específico chamado
  ↓
  BasePluginMTL.init()
    ↓
    hub.plugin_instantiated.emit()
    ↓
    PyQtSignalManager._on_plugin_instantiated() [apenas loga]
  ↓
  Plugin executa
  ↓
Plugin fecha (closeEvent)
  ↓
  BasePluginMTL.on_finish_plugin() [atualiza preferences]
  ↓
  UI pode ser reconstruída via callback futuro
```