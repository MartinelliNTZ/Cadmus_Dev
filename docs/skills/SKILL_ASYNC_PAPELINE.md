# 📜 CONTRATO PIPELINE — Engines, Steps & Tasks

**Violação = Rejeição de código**

> A pipeline é o coração da execução assíncrona do Cadmus. Toda ferramenta que executa múltiplas etapas sequenciais deve seguir este contrato.

---

## 1. Step — Herança Obrigatória

❌ `class MyStep:` ou `class MyStep(ABC):`
✅ `class MyStep(BaseStep):`

Todo step deve herdar de `BaseStep`. A classe base fornece o ciclo de vida completo (`should_run` → `create_task` → `on_success`/`on_error` → `rollback`). Nunca implementar um step sem ela.

---

## 2. Métodos Obrigatórios do Step

❌ Implementar só `create_task` e esquecer `name()` ou `on_success()`
✅ Implementar sempre os 3 métodos obrigatórios:

```python
def name(self) -> str:          # Identificação única do step
def create_task(self, context): # Retorna BaseTask
def on_success(self, context, result): # Atualiza o contexto
```

`name()` é usado para logs e debug. `create_task()` fabrica a task assíncrona. `on_success()` transfere o resultado da task para o `ExecutionContext` compartilhado.

---

## 3. Step — Parâmetros no `__init__`, Não no Context

❌ `context.set("enable_exif", True)` no plugin + `context.get("enable_exif")` no step
✅ `PhotoEnrichmentStep(enable_exif=True)` — parâmetros explícitos no construtor

Steps **nunca** devem buscar parâmetros de configuração no `ExecutionContext`. Toda configuração específica do step deve ser passada como argumento nomeado no `__init__`. O `ExecutionContext` carrega apenas:

- **Atributos canônicos**: `input_path`, `output_path`, `files`, `tool_key`, `json_path`
- **Resultados entre steps**: via `set_result()` / `get_result()`

```python
# ✅ CORRETO
class PhotoEnrichmentStep(BaseStep):
    def __init__(self, *, source="photo", enable_exif=True, ...):
        self.source = source
        self.enable_exif = enable_exif

    def create_task(self, context):
        return PhotoEnrichmentTask(
            base_folder=context.input_path,  # canônico
            enable_exif=self.enable_exif,     # do __init__
            tool_key=context.tool_key,        # canônico
        )
```

---

## 4. ExecutionContext — Atributos Canônicos + Resultados

❌ `context.set("base_folder", "/path")` para config de step
❌ `context.data["minha_chave"] = valor` (acesso direto a `_data`)
✅ `context.input_path = "/path"` (atributo canônico)
✅ `context.set_result("json_path", "/path/to/file.json")` (resultado entre steps)
✅ `context.get_result("json_path")` (recuperar resultado de step anterior)

O `ExecutionContext` tem duas camadas:

### Atributos Canônicos (acesso direto)
```python
context.input_path    # Diretório de entrada
context.output_path   # Diretório de saída
context.files         # Lista de arquivos
context.tool_key      # ToolKey para logging
context.json_path     # Caminho do JSON (usado por múltiplos steps)
context.lat           # Latitude decimal (setado por PhotoEnrichmentStep ou CoordClickTool)
context.lon           # Longitude decimal (setado por PhotoEnrichmentStep ou CoordClickTool)
```

### Resultados entre Steps (via métodos)
```python
def on_success(self, context, result):
    context.set_result("json_path", result["json_path"])
    context.set_result("total_points", result["total_points"])

# Em outro step:
json_path = context.get_result("json_path")
```

### Legado (DEPRECATED — mantido para compatibilidade)
```python
context.set("chave", valor)   # Ainda funciona, mas prefira canônicos
context.get("chave", default) # Ainda funciona, mas prefira canônicos
```

---

## 5. Task — Sempre Herdar de BaseTask

❌ `class MyTask(QgsTask):` diretamente
✅ `class MyTask(BaseTask):`

`BaseTask` já gerencia `run()` → `finished()`, callbacks `on_success`/`on_error`, log estruturado com `LogUtils`, captura de exceções e sinal de progresso. Nunca subclasse `QgsTask` diretamente.

```python
class MyTask(BaseTask):
    def __init__(self, context, *, tool_key):
        super().__init__("Descrição", tool_key=tool_key)
        self.context = context

    def _run(self) -> bool:
        # Lógica pesada aqui
        self.result = {"vertices": 42}
        return True
```

---

## 6. Task — tool_key Obrigatório

❌ `BaseTask("Descrição")` sem tool_key (padrão `"untraceable"`)
✅ `BaseTask("Descrição", tool_key=ToolKey.MY_PLUGIN)`

`tool_key` é a credencial de rastreio. Tasks sem tool_key válida produzem logs não rastreáveis. Todo step que cria task deve receber tool_key do executor ou do contexto.

---

## 7. Task — Nunca Definir on_success/on_error Diretamente

❌ `task.on_success = minha_funcao`  (substituindo o callback interno)
✅ A engine define `task.on_success` e `task.on_error` automaticamente no `_run_next_step()`

O contrato `on_success`/`on_error` da Task é **reservado para a engine**. O step implementa `on_success()` como método próprio — a engine o chama após o callback da task. Nunca sobrescrever os callbacks da task manualmente.

---

## 8. Step — should_run() para Pular Etapas

❌ Retornar `False` sempre sem condição, ou não implementar
✅ Usar `should_run(context)` para pular dinamicamente:

```python
def should_run(self, context) -> bool:
    return bool(context.json_path)  # Só executa se tem json_path
```

`should_run()` padrão retorna `True`. Use para etapas condicionais. Se retornar `False`, o step é pulado e a engine avança para o próximo sem criar task.

---

## 9. Step — Execução Inline (run_inline)

❌ Criar QgsTask para operações síncronas leves
✅ Implementar `run_inline(context)` para execução síncrona:

```python
def run_inline(self, context):
    context.set_result("timestamp", datetime.now())
    # Operação leve, sem QgsTask
```

Quando `create_task` retorna `None`, a engine verifica se existe `run_inline()`. Se existir, executa síncrono. Use apenas para operações rápidas (< 1s). Operações pesadas SEMPRE devem criar task.

---

## 10. Fluxo de Erro — Hierarquia Clara

❌ Tratar erro direto na task e continuar a pipeline
✅ Seguir o fluxo canônico:

```
Task._run() lança exceção
  → finished(success=False) chama on_error(exception)
    → Engine._handle_task_error() chama step.on_error(context, exc)
      → context.add_error(exception)
        → _finish_error() aborta pipeline com on_error callback
```

`step.on_error()` é opcional (implementação vazia em `BaseStep`). Use para limpeza local. O erro é sempre adicionado ao contexto e a pipeline aborta. **Nunca silenciar exceção e continuar**.

---

## 11. Cancelamento Cooperativo

❌ `while True:` sem verificar cancelamento
✅ Verificar `context.is_cancelled()` ou `self.isCanceled()` periodicamente:

```python
def _run(self) -> bool:
    for i, item in enumerate(big_list):
        if self.isCanceled() or self.context.is_cancelled():
            return False
        process(item)
        self.setProgress(int((i / len(big_list)) * 100))
    return True
```

O cancelamento não é instantâneo — a task precisa cooperar verificando o sinal. A engine sinaliza `context.cancel()` e chama `task.cancel()`. Tasks que não cooperam podem travar o QGIS.

---

## 12. Progresso — Automático pela Engine

❌ `task.setProgress(valor)` manual sem contexto global
✅ A engine conecta automaticamente `task.progressChanged` ao `_set_global_progress()`

O progresso global é calculado como:
```
global = ((step_index + step_progress / 100.0) / total_steps) * 100.0
```

Cada task só precisa reportar seu progresso local (0-100). A engine faz a ponderação entre steps. Nunca calcular progresso global manualmente.

---

## 13. PipelineTask — Interno da Engine

❌ Instanciar `PipelineTask` em steps ou plugins
✅ `PipelineTask` é criado exclusivamente por `AsyncPipelineEngine.__init__()`

`PipelineTask` é um `QgsTask` container que mantém a pipeline viva enquanto steps executam. Nunca subclassificar ou instanciar `PipelineTask`. Ele é marcado como `mark_done()` pela engine ao finalizar (sucesso, erro ou cancelamento).

---

## 14. Rollback — Opcional mas Simétrico

❌ Implementar `rollback()` que não desfaz completamente
✅ Se implementar rollback, ele deve ser simétrico ao que foi feito em `on_success()`:

```python
def on_success(self, context, result):
    context.set_result("temp_file", create_temp_file())  # Cria recurso

def rollback(self, context):
    temp = context.get_result("temp_file")
    if temp and os.path.exists(temp):
        os.remove(temp)  # Desfaz recurso
```

Rollback é chamado em caso de erro em steps posteriores. Atualmente não é chamado automaticamente pela engine — é preparado para futuro. Mas se implementar, faça corretamente.

---

## 15. Step — Limpeza de Erros no Contexto

❌ Acumular erros em variáveis paralelas
✅ Usar `context.add_error()`, `context.has_errors()`, `context.get_errors()`

Erros são coletados centralizadamente no contexto. A engine usa `context.get_errors()` para passar ao callback `on_error`. Nunca criar lista de erros fora do contexto.

---

## 16. Pipeline — Um Step, Uma Task

❌ `create_task()` retornando lista de tasks ou None sem `run_inline()`
✅ Cada step produz **exatamente uma task** OU implementa `run_inline()`:

```python
def create_task(self, context) -> Optional[BaseTask]:
    if self._is_simple():
        return None  # Engine usará run_inline()
    return HeavyTask(context, tool_key=self.tool_key)
```

Se retornar `None` e não tiver `run_inline()`, a engine lança `RuntimeError`. Se precisar de múltiplas tasks paralelas, crie steps separados.

---

## 17. Pipeline — Nunca Acessar Serviços Externos Diretamente

❌ Step chamando `QgsProject.instance()`, `ExplorerUtils`, ou `Preferences` diretamente
✅ Tudo que o step precisa deve vir do `ExecutionContext` (injetado pelo step anterior ou pelo executor)

Steps são unidades isoladas que só dependem do `ExecutionContext`. Acessar serviços externos quebra rastreabilidade, impede testes unitários e dificulta rollback. Dados externos devem ser coletados antes da pipeline ou em steps dedicados que injetam no contexto.

---

## 18. Exemplo Completo — Novo Padrão

### Plugin monta steps com parâmetros explícitos

```python
# Plugin/runner cria context só com atributos canônicos
context = ExecutionContext(
    input_path=base_folder,
    tool_key=self.TOOL_KEY,
    files=paths,
)

# Steps recebem configuração via __init__
steps = [
    PhotoEnrichmentStep(
        source="mrk+photo",
        enable_mrk=True,
        enable_exif=enable_exif,
        enable_xmp=enable_xmp,
        enable_custom_fields=enable_custom_fields,
        selected_required_fields=selected_required_fields,
        selected_custom_fields=selected_custom_fields,
        selected_mrk_fields=selected_mrk_fields,
        project_title=project_title,
        logo_path=logo_path,
        recursive=recursive,
        paths=paths,
    ),
    JsonVectorizationStep(source="mrk+photo"),
]

if generate_report:
    steps.append(ReportGenerationStep())

engine = AsyncPipelineEngine(
    steps=steps,
    context=context,
    on_finished=self._on_pipeline_finished,
    on_error=self._on_pipeline_error,
)
engine.start()
```

### Step resolve do context apenas o canônico

```python
class PhotoEnrichmentStep(BaseStep):
    def __init__(self, *, source="photo", enable_exif=True, ...):
        self.source = source
        self.enable_exif = enable_exif
        # ... outros parâmetros

    def create_task(self, context):
        # Resolve do context apenas atributos canônicos
        tool_key = context.tool_key
        base_folder = context.input_path
        return PhotoEnrichmentTask(
            base_folder=base_folder,
            source=self.source,
            enable_exif=self.enable_exif,
            tool_key=tool_key,
        )

    def on_success(self, context, result):
        # Propaga resultado via set_result
        context.set_result("json_path", result["json_path"])
```

---

## 19. Resumo — O que Usar e Quando

| Situação | O que usar | Exemplo |
|----------|-----------|---------|
| Configuração do step | Parâmetros no `__init__` | `PhotoEnrichmentStep(enable_exif=True)` |
| Dados compartilhados (entrada) | Atributos canônicos | `context.input_path`, `context.tool_key` |
| Resultados entre steps | `set_result`/`get_result` | `context.set_result("json_path", path)` |
| Erros | `add_error`/`has_errors`/`get_errors` | `context.add_error(exc)` |
| Cancelamento | `cancel`/`is_cancelled` | `context.cancel()` |
| Legado (não refatorado) | `set`/`get` (DEPRECATED) | `context.set("chave", valor)` |