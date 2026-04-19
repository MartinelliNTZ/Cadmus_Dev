# SKILL: PyQt Signal no Cadmus

Especialista: `pyqtSignal` | `QObject` | eventos entre componentes
Versão: 2.0 | Abril 2026 (Refatorado pós-limpeza)
Status: Pronto para produção

---

## TL;DR

Use `pyqtSignal` para avisar componentes sem acoplamento direto. Padrão Cadmus:

```python
from qgis.PyQt.QtCore import QObject, pyqtSignal

class _PluginSignalHub(QObject):
    plugin_instantiated = pyqtSignal(dict)  # {tool_key, class_name, plugin_name, build_ui}
    plugin_finished = pyqtSignal(dict)      # {tool_key, preferences}

hub = get_plugin_signal_hub()
hub.plugin_instantiated.emit(payload)  # Emitir
hub.plugin_instantiated.connect(handler)  # Escutar
```

---

## Arquitetura Cadmus: Fluxo de Sinais

### Ciclo de Vida do Plugin

```
1. PLUGIN ABRE (init())
   └─ BasePlugin.init() → emite plugin_instantiated
      └─ PyQtSignalManager._on_plugin_instantiated()
         └─ ToolRegistry.update_tool_main_action() [atualiza ToolList + Preferences]
            └─ MenuManager.reconstruct_toolbar() [reconstrói com ToolList nova]

2. PLUGIN FECHA (on_finish_plugin())
   └─ BasePlugin.on_finish_plugin() → emite plugin_finished
      └─ PyQtSignalManager._on_plugin_finished()
         └─ ToolRegistry.update_tool_main_action() [atualiza ToolList + Preferences]
            └─ SEM reconstruir toolbar (próximo aberto faz isso)
```

### Responsabilidades

| Componente | Responsabilidade | Log | Delegações |
|-----------|------------------|-----|-----------|
| **BasePlugin** | Emitir sinais nos eventos certos | debug/info | - |
| **PyQtSignalManager** | Coordenar sinais com componentes | info/warn | ToolRegistry, MenuManager |
| **ToolRegistry** | Gerenciar ToolList + Preferences | debug/info | Preferences (só init + mudança) |
| **MenuManager** | Reconstruir UI baseado em ToolList | debug/info | ToolRegistry |
| **Preferences** | Persistência JSON | debug | - |

---

## Padrão: Signal Hub Global

Implementado em `PyQtSignalManager.py`:

```python
class _PluginSignalHub(QObject):
    plugin_instantiated = pyqtSignal(dict)
    plugin_finished = pyqtSignal(dict)

_plugin_signal_hub = None

def get_plugin_signal_hub():
    global _plugin_signal_hub
    if _plugin_signal_hub is None:
        _plugin_signal_hub = _PluginSignalHub()
    return _plugin_signal_hub
```

**Vantagens:**
- Desacoplamento: emissores não conhecem receptores
- Centralizado: um ponto de verdade para eventos
- Testável: fácil mockar sinais

---

## Padrão: Manager que Observa

`PyQtSignalManager` conecta-se ao hub e coordena:

```python
class PyQtSignalManager(QObject):
    def __init__(self, tool_key=ToolKey.UNTRACEABLE):
        super().__init__()
        self.logger = LogUtils(tool=tool_key, class_name="PyQtSignalManager")
        self._signal_hub = get_plugin_signal_hub()
        self._is_connected = False

    def start(self):
        """Conecta handlers."""
        if self._is_connected:
            return
        self._signal_hub.plugin_instantiated.connect(self._on_plugin_instantiated)
        self._signal_hub.plugin_finished.connect(self._on_plugin_finished)
        self._is_connected = True

    def stop(self):
        """Desconecta handlers."""
        if not self._is_connected:
            return
        try:
            self._signal_hub.plugin_instantiated.disconnect(self._on_plugin_instantiated)
            self._signal_hub.plugin_finished.disconnect(self._on_plugin_finished)
        except Exception as e:
            self.logger.error(f"Erro ao desconectar: {e}")
        finally:
            self._is_connected = False
```

---

## Implementação no BasePlugin

Emitir sinais nos pontos certos:

```python
class BasePluginMTL(BaseDialog):
    def init(self, tool_key, class_name, ...):
        # Setup completo...
        self._plugin_signal_context = {
            "tool_key": self.TOOL_KEY,
            "class_name": class_name,
            "plugin_name": self.PLUGIN_NAME,
            "build_ui": build_ui,
        }
        # Emitir APÓS todo setup pronto
        hub = get_plugin_signal_hub()
        hub.plugin_instantiated.emit(self._plugin_signal_context)

    def on_finish_plugin(self):
        # Incrementar uso
        self.preferences["usages"] = self.preferences.get("usages", 0) + 1
        # Emitir
        context = {"tool_key": self.TOOL_KEY, "preferences": self.preferences}
        hub = get_plugin_signal_hub()
        hub.plugin_finished.emit(context)
```

---

## Fluxo Detalhado: Plugin Abre

```python
# 1. BasePlugin.init() - após UI completa
hub.plugin_instantiated.emit({
    "tool_key": "my_plugin",
    "class_name": "MyDialog",
    "plugin_name": "Meu Plugin",
    "build_ui": True,
})

# 2. PyQtSignalManager._on_plugin_instantiated(payload)
tool_registry = ToolRegistry.get_instance()
category = tool_registry.update_tool_main_action("my_plugin")
# ToolRegistry.update_tool_main_action():
#   - Encontra tool em ToolList
#   - Reseta main_action em categoria
#   - Seta main_action=True para tool
#   - Persiste em Preferences
#   - Retorna categoria

# 3. MenuManager.reconstruct_toolbar()
menu_manager.reconstruct_toolbar()
# MenuManager.reconstruct_toolbar():
#   - Remove toolbar anterior
#   - Recarrega visibilidade de categorias
#   - Chama _refresh_tool_main_actions()
#   - Reconstrói toolbar com novos estados

# 4. MenuManager._refresh_tool_main_actions()
# Sincroniza main_action com ToolRegistry (NÃO Preferences)
updated_tools = tool_registry.get_tools()
for tool in self.tools:
    tool.main_action = updated_tools_dict[tool.tool_key].main_action
```

---

## Fluxo Detalhado: Plugin Fecha

```python
# 1. BasePlugin.on_finish_plugin()
hub.plugin_finished.emit({
    "tool_key": "my_plugin",
    "preferences": {...}
})

# 2. PyQtSignalManager._on_plugin_finished(payload)
tool_registry = ToolRegistry.get_instance()
category = tool_registry.update_tool_main_action("my_plugin")
# ToolRegistry ATUALIZA ToolList + Preferences
# MAS: MenuManager NÃO reconstrói toolbar

# Próximo plugin aberto é que reconstrói (economiza ciclos)
```

---

## Princípios Implementados

### 1. ToolList como Fonte de Verdade
- Lida em memória durante sessão QGIS
- Preferences **APENAS** para persistência entre sessões
- Nenhuma re-leitura de Preferences após init

### 2. Separação de Responsabilidades
| Quem | O quê | Não faz |
|-----|-------|---------|
| ToolRegistry | Gerencia ToolList + Preferences | UI |
| MenuManager | Constrói UI | Gerenciar estado |
| PyQtSignalManager | Coordena | Lógica de negócio |

### 3. Logging Limpo
- `info`: Marcos importantes (plugin aberto, toolbar reconstruída)
- `debug`: Operações internas (sincronização de states)
- Sem `print()` ou logs redundantes

---

## Checklist de Implementação

- ✓ Classe herda de `QObject` ou derivada Qt
- ✓ Sinais declarados no nível da classe
- ✓ `get_plugin_signal_hub()` retorna singleton
- ✓ `PyQtSignalManager.start()` e `.stop()` bem definidos
- ✓ Handlers com try/except Exception
- ✓ Logging em níveis apropriados (info/debug)
- ✓ Emissão APÓS setup completo (não no __init__)
- ✓ Payload é dict pequeno e estável

---

## Arquivos de Referência

| Arquivo | Propósito | Status |
|---------|----------|--------|
| [PyQtSignalManager.py](../../core/config/PyQtSignalManager.py) | Hub + Manager | ✓ Limpo |
| [BasePlugin.py](../../plugins/BasePlugin.py) | Emissores de sinal | ✓ Limpo |
| [ToolRegistry.py](../../core/config/ToolRegistry.py) | Gerencia ToolList | ✓ Limpo |
| [MenuManager.py](../../core/config/MenuManager.py) | Reconstrói UI | ✓ Limpo |
| [Preferences.py](../../utils/Preferences.py) | Persistência | ✓ Limpo |

---

## Troubleshooting

### Sinal não dispara
- ✗ Emissão no `__init__` (muito cedo)
- ✓ Emissão após setup completo em `init()` ou `showEvent()`

### Conexão duplicada
- ✗ `start()` chamado múltiplas vezes sem `_is_connected`
- ✓ Usar flag `_is_connected` para prevenir duplicação

### Erro no disconnect
- ✗ Não usar try/except Exception
- ✓ Sempre usar try/except em `stop()`

### Log poluído
- ✗ `logger.debug()` para cada passo
- ✓ `logger.debug()` só para sincronizações; `logger.info()` para marcos

---

## Referência Rápida

```python
# Emitir
hub = get_plugin_signal_hub()
hub.plugin_instantiated.emit({"tool_key": "...", "class_name": "..."})

# Escutar
hub.plugin_instantiated.connect(self._on_plugin_instantiated)

# Desconectar
try:
    hub.plugin_instantiated.disconnect(self._on_plugin_instantiated)
except Exception as e:
    logger.error(f"Erro: {e}")

# Usar manager
signal_manager = PyQtSignalManager(tool_key)
signal_manager.start()  # Quando sistema inicia
signal_manager.stop()   # Quando sistema encerra
```

---

## Evolução Recente (v2.0)

- ✓ Limpeza de logs excessivos (debug removidos, info mantidos)
- ✓ Simplificação de métodos (menos linhas, mesma lógica)
- ✓ Clareza de responsabilidades (quem faz o quê)
- ✓ Documentação atualizada refletindo implementação real

**Próximo:** Monitoramento em produção para validar assumções.

