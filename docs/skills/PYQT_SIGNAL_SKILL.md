# SKILL: PyQt Signal no Cadmus

Especialista: `pyqtSignal` | `QObject` | eventos entre widgets e managers
Versao: 1.0 | Abril 2026
Status: Pronto para uso

---

## TL;DR

Use `pyqtSignal` quando um objeto precisa avisar outro sem acoplamento direto.

Padrao base:

```python
from qgis.PyQt.QtCore import QObject, pyqtSignal


class MyEmitter(QObject):
    finished = pyqtSignal(dict)

    def run(self):
        self.finished.emit({"status": "ok"})
```

Escuta:

```python
emitter = MyEmitter()
emitter.finished.connect(self._on_finished)
```

---

## Quando usar

Use `pyqtSignal` para:

- avisar que um dialogo abriu, fechou ou terminou processamento
- comunicar widget com manager sem importar a classe consumidora
- disparar eventos globais via hub singleton
- reduzir acoplamento entre plugins, dialogs e servicos de UI

Nao use `pyqtSignal` para:

- passar dependencias obrigatorias de construcao
- substituir retorno simples de funcao
- esconder fluxo critico que deveria ser explicito

---

## Regras praticas

1. Declarar o sinal como atributo de classe, nunca dentro de metodo.
2. Herdar de `QObject` ou de uma classe Qt que ja herda de `QObject`.
3. Conectar com `.connect(...)` e emitir com `.emit(...)`.
4. Preferir payload pequeno e estavel, geralmente `dict`, `str`, `bool` ou `object`.
5. Se o evento so pode acontecer uma vez por janela, usar uma trava booleana.
6. Em utilitarios sem contexto de plugin, logar com `ToolKey.UNTRACEABLE`.

---

## Padrao 1: sinal local de um widget

Use quando um widget ou dialogo precisa notificar quem o criou.

```python
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QDialog


class MyDialog(QDialog):
    accepted_payload = pyqtSignal(dict)

    def _on_ok_clicked(self):
        self.accepted_payload.emit({"name": "cadmus"})
```

Quem cria:

```python
self.dialog = MyDialog(self.iface.mainWindow())
self.dialog.accepted_payload.connect(self._on_dialog_payload)
self.dialog.show()
```

---

## Padrao 2: hub global de sinais

Use quando varias instancias diferentes precisam publicar e ouvir o mesmo evento.

Exemplo do Cadmus:

```python
from qgis.PyQt.QtCore import QObject, pyqtSignal


class _PluginSignalHub(QObject):
    plugin_instantiated = pyqtSignal(dict)


_plugin_signal_hub = None


def get_plugin_signal_hub():
    global _plugin_signal_hub
    if _plugin_signal_hub is None:
        _plugin_signal_hub = _PluginSignalHub()
    return _plugin_signal_hub
```

Publicacao:

```python
payload = {
    "tool_key": self.TOOL_KEY,
    "class_name": self.__class__.__name__,
}
get_plugin_signal_hub().plugin_instantiated.emit(payload)
```

Consumo:

```python
self._signal_hub = get_plugin_signal_hub()
self._signal_hub.plugin_instantiated.connect(self._on_plugin_instantiated)
```

---

## Padrao 3: manager que observa e loga

Use quando o evento precisa ser centralizado em um unico ponto.

Exemplo:

```python
class PyQtSignalManager(QObject):
    def __init__(self, tool_key=ToolKey.UNTRACEABLE, parent=None):
        super().__init__(parent)
        self.logger = LogUtils(
            tool=tool_key,
            class_name="PyQtSignalManager",
            level=LogUtils.DEBUG,
        )
        self._signal_hub = get_plugin_signal_hub()
        self._is_connected = False

    def start(self):
        if self._is_connected:
            return
        self._signal_hub.plugin_instantiated.connect(
            self._on_plugin_instantiated
        )
        self._is_connected = True
```

Boas praticas:

- ter `start()` e `stop()`
- evitar conectar duas vezes
- envolver `disconnect()` com `try/except Exception as e`
- manter o manager vivo durante o ciclo de vida do plugin principal

---

## Melhor ponto para emitir

No Cadmus, para eventos de "abriu a janela", prefira `showEvent()` em vez de um metodo manual de inicializacao.

Exemplo:

```python
def showEvent(self, event):
    super().showEvent(event)

    if self._plugin_signal_emitted:
        return

    self._emit_plugin_instantiated_signal()
    self._plugin_signal_emitted = True
```

Por que isso e melhor:

- dispara no evento real de abertura
- nao depende de lembrar de chamar um metodo auxiliar
- reduz chance de falso positivo durante construcao da instancia

---

## Erros comuns

### 1. Declarar sinal dentro do `__init__`

Errado:

```python
def __init__(self):
    self.changed = pyqtSignal(dict)
```

Correto:

```python
class MyWidget(QWidget):
    changed = pyqtSignal(dict)
```

### 2. Esquecer `super().__init__(...)`

Sem isso, o objeto Qt pode nao inicializar corretamente.

### 3. Conectar repetidamente

Se `start()` for chamado varias vezes, o slot pode executar duplicado.

### 4. Emitir cedo demais

Se o evento e "janela aberta", emitir no `init` pode ser cedo demais.

### 5. Payload instavel

Se cada emissao usa chaves diferentes, o consumidor fica fragil.

Padronize o contrato:

```python
{
    "tool_key": "...",
    "class_name": "...",
    "plugin_name": "...",
    "build_ui": True,
}
```

---

## Checklist rapido

- a classe herda de `QObject` ou derivada Qt?
- o sinal foi declarado no nivel da classe?
- existe `.connect(...)` em um ponto controlado?
- existe `.emit(...)` no evento correto?
- o payload e pequeno e previsivel?
- ha protecao contra emissao ou conexao duplicada?

---

## Referencia no projeto

Arquivos atuais relacionados:

- `plugins/BasePlugin.py`
- `core/config/PyQtSignalManager.py`
- `cadmus_plugin.py`

Use esses arquivos como referencia viva para o padrao adotado no Cadmus.
