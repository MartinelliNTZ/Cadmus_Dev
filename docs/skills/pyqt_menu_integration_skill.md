# SKILL: PyQtSignalManager Neutro e Reconstrução de Toolbar no BasePlugin

Especialista: `PyQtSignalManager` | `BasePluginMTL` | `MenuManager` | sinais PyQt e reconstrução de UI
Versao: 1.0 | Abril 2026
Status: Pronto para uso

---

## TL;DR

`PyQtSignalManager` é neutro, recém-criado, sem funções específicas além de escutar sinais globais. `BasePluginMTL` emite sinais de instanciação e usa `MenuManager.get_instance()` para reconstruir apenas a toolbar ao fechar plugins, mudando a ordem dos itens.

Padrao base:

```python
# Em BasePluginMTL.__init__
hub = get_plugin_signal_hub()
hub.plugin_instantiated.emit(self._plugin_signal_context)

# Em BasePluginMTL.on_finish_plugin
menu_manager = MenuManager.get_instance()
menu_manager.reconstruct_toolbar()
```

---

## Quando usar

Use `PyQtSignalManager` para:

- Escutar sinais globais de instanciação de plugins sem interferir na lógica
- Logar eventos de plugins de forma centralizada
- Manter um hub neutro para futuros sinais PyQt

Use reconstrução de toolbar em `BasePluginMTL` para:

- Atualizar a ordem dos botões na toolbar após fechar um plugin
- Garantir que o main_action seja resetado e setado corretamente por categoria
- Manter a UI sincronizada com as preferências atualizadas

Nao use para:

- Criar menus ou toolbars (isso é feito em `cadmus_plugin.py`)
- Modificar lógica de instanciação de plugins

---

## Regras praticas

1. `PyQtSignalManager` permanece neutro: apenas escuta e loga sinais.
2. Em `BasePluginMTL.__init__`, emita `plugin_instantiated` via hub global.
3. Em `BasePluginMTL.on_finish_plugin`, use `MenuManager.get_instance().reconstruct_toolbar()` para atualizar apenas a toolbar.
4. Não instancie novo `MenuManager` em `BasePluginMTL`; use o singleton.
5. A reconstrução afeta apenas a ordem dos itens na toolbar, não cria novos menus.

---

## Padrao: Emissão de sinal e reconstrução de toolbar

### 1. Em BasePluginMTL.__init__

```python
def __init__(self, parent=None):
    super().__init__(parent)
    # Emitir sinal de instanciação (neutro, apenas para logging)
    try:
        from ..core.config.PyQtSignalManager import get_plugin_signal_hub
        hub = get_plugin_signal_hub()
        hub.plugin_instantiated.emit(self._plugin_signal_context)
    except Exception as e:
        pass
```

### 2. Em BasePluginMTL.on_finish_plugin

```python
def on_finish_plugin(self):
    # ... lógica de preferences ...
    
    # Reconstruir apenas a toolbar para mudar ordem dos itens
    menu_manager = MenuManager.get_instance()
    mgr = MenuManager.get_instance()
    if mgr:
        mgr.reconstruct_toolbar()
    if menu_manager is not None:
        menu_manager.reconstruct_toolbar()
```

### 3. Em PyQtSignalManager (neutro)

```python
class PyQtSignalManager(QObject):
    def start(self):
        self._signal_hub.plugin_instantiated.connect(self._on_plugin_instantiated)
    
    def _on_plugin_instantiated(self, payload):
        # Apenas loga, sem interferir
        self.logger.info(f"[plugin_instantiated] {payload}")
```

---

## Benefícios

- **Neutralidade**: `PyQtSignalManager` não interfere na lógica existente
- **Centralização de sinais**: Todos os sinais passam por um hub global
- **Reconstrução eficiente**: Apenas a toolbar é recriada, não menus inteiros
- **Ordem dinâmica**: Itens da toolbar mudam conforme main_action por categoria

---

## Dependências

- `qgis.PyQt.QtCore.QObject`
- `qgis.PyQt.QtCore.pyqtSignal`
- `MenuManager` com método `get_instance()` e `reconstruct_toolbar()`
- `Preferences` para atualizar main_action

---

## Exemplo de uso

1. Plugin é instanciado: sinal `plugin_instantiated` é emitido e logado por `PyQtSignalManager`
2. Plugin fecha: `on_finish_plugin` reseta main_action por categoria e chama `reconstruct_toolbar()`
3. Toolbar é recriada com nova ordem de itens, refletindo as mudanças de main_action