# 📜 CONTRATO DO PLUGIN — 12 Regras Críticas

**Violação = Rejeição de código**

---

## 1. UI — Widgets

❌ `from qgis.PyQt.QtWidgets import QLabel, QPushButton`
✅ `widget = WidgetFactory.create_label("Texto")`

Plugins nunca importam QtWidgets direto. Toda UI passa por WidgetFactory que centraliza estilos e garante consistência visual em todo o plugin.

---

## 2. Logging

❌ `print("Erro")` ou `sys.stderr.write()`
✅ `LogUtils(tool=ToolKey.X, class_name="Y").error("Erro", code="...")`

Logs devem ser estruturados, rastreáveis e em pt_BR. Print e stderr não deixam rastro. LogUtils armazena em JSON estruturado com contexto completo (timestamp, thread, session, code).

---

## 3. Strings

❌ `label = "Meu Título"` ou `msg = "Selecione camada"`
✅ `label = STR.TITLE_MY_PLUGIN` ou `msg = f"{STR.LAYER}:"`

Strings hardcoded ficam presas ao código. STR permite tradução futura semântica, reutilização e manutenção centralizada. Sempre em Strings_pt_BR como padrão.

---

## 4. ToolKey

❌ `tool_key = "my_plugin"` ou `Preferences.load_tool_prefs("vector_field")`
✅ `tool_key = ToolKey.MY_PLUGIN` ou `Preferences.load_tool_prefs(ToolKey.VECTOR_FIELD)`

ToolKey é enum, não string. Evita typos, facilita refatoração global e garante rastreamento em logs. Se a chave não existe em ToolKey, deve ser criada lá.

---

## 5. Estilos

❌ `label.setStyleSheet("color: red; font-weight: bold")`
✅ Usar `WidgetFactory` que aplica `Styles.label()` automaticamente

Estilos customizados em plugins quebram consistência visual e dificultam mudanças globais. Todos os estilos em Styles.py, aplicados via Factory. Se precisa estilo novo, criar em Styles.py.

---

## 6. Exceções

❌ `except:` ou `except Exception: pass`
✅ `except Exception as e: logger.exception(e, code="ERROR_CODE")`

Exceções silenciosas ocultam erros e dificultam debug. Sempre capturar e logar com logger.exception() que inclui traceback completo. Se é erro esperado, logger.warning() com tratamento.

---

## 7. Métodos Estáticos

❌ `@staticmethod def process(data): logger.info("...")`
✅ `@staticmethod def process(data, *, tool_key): logger = LogUtils(tool=tool_key, ...)`

Métodos estáticos não têm contexto de qual plugin os chamou. Passar tool_key como parâmetro garante rastreamento. Sem tool_key, logs não sabem de onde vieram.

---

## 8. Configurações

❌ `GLOBAL_CONFIG = {...}` ou `json.load(open("config.json"))`
✅ `Preferences.load_tool_prefs(ToolKey.X)` ou `Preferences.save_tool_prefs(ToolKey.X, {...})`

Variáveis globais são compartilhadas (conflitos). Arquivos diretos são não-sincronizados. Preferences centraliza, persiste, é versionada e compartilhável entre plugins.

---

## 9. Widgets Customizados

❌ `class MyDialog(QDialog):` em `plugins/`
✅ Criar em `resources/widgets/MyCustomWidget.py` + `WidgetFactory.create_my_custom_widget(...)`

Widgets em plugins criam acoplamento UI-lógica e violam contrato. Widgets compostos ficam em resources/widgets/ com encapsulamento, e Factory os fornece ao plugin.

---

## 10. Instruções & Help

❌ `help_text = "Este algoritmo..."`
✅ `help_path = InstructionsManager.get(ToolKey.X)` (lê `.md` de `resources/instructions/pt_BR/`)

Help hardcoded em código é impossível traduzir, mistura lógica com documentação. Arquivos `.md` centralizados permitem tradução futura e edição sem tocar código.

---

## 11. Logs Nunca Traduzem

❌ `logger.info(STR.MESSAGE)`
✅ `logger.info("Mensagem iniciada")` (sempre pt_BR)

Logs servem auditoria/debug de desenvolvedores. STR é para UI do usuário. Logs traduzidos quebram rastreamento e dificultam busca. Sempre em pt_BR.

---
