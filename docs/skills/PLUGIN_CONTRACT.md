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
---

## 12. Processing — Algoritmos e Preferências

❌ Criar algoritmo de processamento sem herdar de `BaseProcessingAlgorithm`
✅ Toda ferramenta de processing deve ser filha de `BaseProcessingAlgorithm` para garantir padrão de preferências, ícone, instruções e integração Cadmus.

---

## 13. Logger e ToolKey — Rastreamento e Logs

✅ Qualquer classe pode criar um logger próprio (`LogUtils(tool=..., class_name=...)`) para rastreabilidade, mas nem todas precisam. O importante é que as classes principais de ferramentas (algoritmos, plugins, dialogs) tenham tool_key rastreável para logs e preferências. Classes auxiliares podem receber tool_key como argumento se precisarem logar, mas não é obrigatório logar tudo. O foco é garantir que as ações relevantes sejam rastreadas com contexto completo.
✅ Apenas classes de ferramenta (algoritmos, plugins, dialogs principais) podem definir um `TOOL_KEY` próprio.
✅ Classes auxiliares (não ferramentas) devem receber a `tool_key` como argumento em métodos estáticos ou no construtor, se precisarem logar.
❌ Nunca criar logs sem tool_key rastreável (exceto casos de utilitários genéricos).
✅ A `tool_key` é a credencial mestra de rastreio de logs e preferências.
❌ Widgets exclusivos e helpers não precisam logar criação, mas devem logar exceções e erros relevantes se houver tratamento, oque muitas vezes nao ha.


## 14. Preferences — Padrão para Processing

✅ Toda ferramenta de processing deve carregar preferências via `self.load_preferences()` no início de `initAlgorithm`.
✅ Preferências devem ser lidas/salvas apenas via `Preferences.load_tool_prefs` e `Preferences.save_tool_prefs`.
✅ Parâmetros padrão dos algoritmos devem usar `self.prefs.get("chave", valor_padrao)`.
✅ Sempre incluir checkboxes padrão: `OPEN_OUTPUT_FOLDER` e `DISPLAY_HELP`, ambos usando prefs.
❌ Nunca salvar preferências fora dos métodos padrão.

---

## 15. Utils — Regras Gerais

✅ Toda manipulação de arquivos/pastas deve ser feita por ExplorerUtils.
✅ Só VectorLayerSource pode explorar arquivos vetoriais.
✅ Só RasterLayerSource pode explorar arquivos raster.
✅ Só ProjectUtils pode manipular QgsProject (abrir, salvar, backup, layers).
✅ QgisMessageUtil é o único meio de emitir mensagens ao usuário (nunca usar print/qmessagebox direto para usuário).
✅ ToolKey é obrigatório para logs/preferences de ferramentas. Utils/serviços devem receber tool_key externo.
✅ Tudo que for possível deve ser salvo nas preferências (Preferences).
✅ Sempre usar FormatUtils para exibir valores ao usuário (tamanho, tempo, etc).
✅ Nome do arquivo .py deve ser exatamente igual ao nome da classe principal.
❌ Nunca manipular QgsProject fora de ProjectUtils.
❌ Nunca emitir mensagens ao usuário fora de QgisMessageUtil.
❌ Nunca criar helpers duplicados já existentes em utils.
❌ Nunca salvar preferências fora de Preferences.
❌ Nunca explorar arquivos/camadas fora das classes autorizadas.