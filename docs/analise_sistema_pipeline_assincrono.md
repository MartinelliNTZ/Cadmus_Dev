# Sistema de Pipeline Assíncrono - Arquitetura e Funcionamento

---

## 1. Visão Geral

O sistema implementa um **pipeline sequencial assíncrono** composto por etapas (`Steps`) que são executadas uma após a outra. Cada etapa pode executar uma tarefa pesada de forma assíncrona (em background thread) e, ao finalizar, chama um callback de sucesso/erro que avança para a próxima etapa.

O fluxo é: **iniciar pipeline → step 1 → task assíncrona → callback sucesso → step 2 → ... → finalizar**

---

## 2. Peças do Sistema

### 2.1 ExecutionContext

Container de estado compartilhado entre todos os steps da pipeline.

```python
class ExecutionContext:
    def __init__(self, initial_data: dict = None):
        self._data: dict = initial_data.copy() if initial_data else {}
        self._errors: list[Exception] = []
        self._is_cancelled: bool = False
```

**Métodos principais:**
- `set(key, value)` → Armazena valor no contexto (fluent, retorna self)
- `get(key, default=None)` → Recupera valor
- `has(key)` → Verifica se chave existe
- `require(keys: list)` → Lança KeyError se alguma chave obrigatória estiver faltando
- `add_error(exc)` → Adiciona erro à lista
- `get_errors()` → Retorna cópia da lista de erros
- `has_errors()` → True se houve algum erro
- `cancel()` → Marca como cancelado
- `is_cancelled()` → True se foi cancelado
- `clear()` → Reseta todo o estado

**Propósito:** Permite que steps compartilhem dados (ex: step 1 calcula X, step 2 usa X) sem acoplamento direto. Também carrega o estado de cancelamento e erros.

---

### 2.2 BaseStep (Classe Abstrata)

Contrato que define uma etapa da pipeline.

```python
from abc import ABC, abstractmethod

class BaseStep(ABC):
    # Obrigatórios:
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def create_task(self, context: ExecutionContext) -> BaseTask | None: ...

    @abstractmethod
    def on_success(self, context: ExecutionContext, result: Any) -> None: ...

    # Opcionais (com implementação padrão):
    def should_run(self, context: ExecutionContext) -> bool:
        return True  # Permite pular etapa dinamicamente

    def on_error(self, context: ExecutionContext, exception: Exception) -> None:
        pass  # Tratamento específico de erro do step

    def rollback(self, context: ExecutionContext) -> None:
        pass  # Desfazer alterações (opcional)
```

**Métodos obrigatórios:**
1. **`name()`** → Identificador único para logs/debug
2. **`create_task(context)`** → Cria e retorna uma instância de `BaseTask` (trabalho assíncrono). Pode retornar `None` se o step executar inline (síncrono) via `run_inline()`.
3. **`on_success(context, result)`** → Callback executado após a task terminar com sucesso. Recebe o resultado da task. Aqui se atualiza o contexto com os dados produzidos.

**Métodos opcionais:**
- **`should_run(context)`** → Se retornar `False`, o step é pulado automaticamente
- **`on_error(context, exception)`** → Tratamento de erro específico antes de falhar a pipeline inteira
- **`rollback(context)`** → Lógica para desfazer alterações em caso de erro (não é chamado automaticamente, fica a critério de quem implementa)

---

### 2.3 BaseTask

Wrapper para execução de trabalho pesado em background.

```python
class BaseTask:
    def __init__(self, description: str):
        self.exception: Exception | None = None
        self.result: Any = None
        self.on_success: callable | None = None  # Callback: on_success(result)
        self.on_error: callable | None = None    # Callback: on_error(exception)

    def run(self) -> bool:
        """Método principal executado em thread separada."""
        try:
            return self._run()
        except Exception as e:
            self.exception = e
            return False

    def finished(self, success: bool):
        """Chamado na thread principal após run() terminar."""
        if success:
            if self.on_success:
                self.on_success(self.result)
        else:
            if self.on_error:
                self.on_error(self.exception)
            else:
                # Log de erro padrão se não tiver callback
                print(f"Task error: {self.exception}")

    def _run(self) -> bool:
        """Subclasse implementa a lógica pesada aqui."""
        raise NotImplementedError
```

**Fluxo interno:**
1. **`run()`** é executado em **thread separada** (background)
2. Dentro de `run()`, chama `_run()` que contém a lógica real
3. Se `_run()` lançar exceção, ela é capturada e armazenada em `self.exception`, retorna `False`
4. Se `_run()` retornar normalmente, `self.result` deve conter o resultado
5. **`finished(success)`** é chamado na **thread principal** (UI) após o término
6. Se `success == True` → dispara `on_success(self.result)`
7. Se `success == False` → dispara `on_error(self.exception)`

**Observação:** A classe original herda de `QgsTask` (QGIS), mas o conceito é puro: um wrapper que executa trabalho em background, captura exceções, e notifica conclusão com callbacks.

---

### 2.4 AsyncPipelineEngine

Orquestrador principal. Gerencia a execução sequencial dos steps.

```python
class AsyncPipelineEngine:
    def __init__(
        self,
        steps: list[BaseStep],
        context: ExecutionContext,
        *,
        on_finished=None,    # Callback: on_finished(context)
        on_error=None,       # Callback: on_error(list_of_exceptions)
        on_cancelled=None,   # Callback: on_cancelled(context)
    ):
        self._steps = steps
        self._context = context
        self._on_finished = on_finished
        self._on_error = on_error
        self._on_cancelled = on_cancelled

        self._current_index = 0
        self._current_task = None
        self._is_running = False
        self._is_cancelled = False
```

**Fluxo de execução (`start()`):**

```
start()
  │
  ├─ Marca como executando
  ├─ Cria um PipelineTask "guardião" (task que fica viva até o fim)
  ├─ Chama _run_next_step()
  │
  └─ _run_next_step()
       │
       ├─ Se cancelado → _finish_cancelled()
       │
       ├─ Se acabaram os steps → _finish_success()
       │
       ├─ Pega step atual
       │
       ├─ Se step.should_run() == False → avança índice e chama _run_next_step() (recursão)
       │
       ├─ Tenta step.create_task(context)
       │    │
       │    ├─ Se task é None E step tem run_inline() → executa síncrono, avança, recursão
       │    │
       │    └─ Se task é None E NÃO tem run_inline() → ERRO (RuntimeError)
       │
       ├─ Conecta callbacks:
       │    task.on_success = self._handle_task_success
       │    task.on_error = self._handle_task_error
       │    task.progressChanged → self._set_global_progress (atualiza progresso global)
       │
       └─ Dispara a task (adiciona ao executor de background)
```

**Callback de sucesso (`_handle_task_success(result)`):**

```
_handle_task_success(result)
  │
  ├─ step.on_success(context, result) → pode lançar exceção
  │
  ├─ Se on_success() lançou → _handle_task_error(exc)
  │
  └─ Se on_success() OK → avança índice e chama _run_next_step()
```

**Callback de erro (`_handle_task_error(exception)`):**

```
_handle_task_error(exception)
  │
  ├─ step.on_error(context, exception) → tratamento específico (opcional)
  ├─ context.add_error(exception) → armazena erro no contexto
  └─ _finish_error() → para a pipeline (NÃO continua)
```

**Finalizações:**

| Método | Quando chamado | Ações |
|--------|---------------|-------|
| `_finish_success()` | Todos os steps executaram com sucesso | Marca progresso 100%, notifica `on_finished(context)` |
| `_finish_error()` | Algum step falhou | Notifica `on_error(context.get_errors())` |
| `_finish_cancelled()` | Usuário chamou `cancel()` | Notifica `on_cancelled(context)` |

**Cancelamento (`cancel()`):**
```
cancel()
  ├─ context.cancel() → marca contexto como cancelado
  ├─ Se existe task rodando → task.cancel()
  ├─ Se existe pipeline task → pipeline_task.cancel()
  └─ _finish_cancelled()
```

---

## 3. Diagrama de Fluxo Completo

```
[início]
   │
   ▼
start()
   │
   ▼
_run_next_step()  ◄──────────────────────────────┐
   │                                              │
   ├─ cancelado? ─► _finish_cancelled()          │
   │                                              │
   ├─ fim dos steps? ─► _finish_success()         │
   │                                              │
   ├─ should_run? = False ─► índice++ ───────────┘
   │                                              │
   ├─ create_task()                               │
   │   │                                          │
   │   ├─ task=None + run_inline() ─► executa ────┘
   │   │           síncrono, índice++              │
   │   │                                          │
   │   └─ task válida                             │
   │        │                                     │
   │        ▼                                     │
   │   Dispara task em background                 │
   │        │                                     │
   │        ▼                                     │
   │   [task rodando...]                          │
   │        │                                     │
   │   ┌────┴────┐                                │
   │   ▼         ▼                                │
   │ success   error                             │
   │   │         │                                │
   │   ▼         ▼                                │
   │ on_success on_error                         │
   │ (contexto) (contexto)                       │
   │   │         │                                │
   │   ▼         ▼                                │
   │ índice++  add_error +                       │
   │   │       _finish_error()                   │
   │   ▼                                          │
   └──┘ (recursão)                               │
                                                  │
                                                  │
[final] ◄─────────────────────────────────────────┘
```

---

## 4. Como Usar (Exemplo)

```python
# 1. Cria os steps concretos
class StepCalcular(BaseStep):
    def name(self) -> str:
        return "calcular_algo"

    def create_task(self, context):
        return MinhaTask("Calculando...")

    def on_success(self, context, result):
        context.set("resultado_calculo", result)

class StepProcessar(BaseStep):
    def name(self) -> str:
        return "processar_resultado"

    def should_run(self, context):
        # Só roda se o step anterior produziu resultado
        return context.has("resultado_calculo")

    def create_task(self, context):
        dado = context.get("resultado_calculo")
        return MinhaTaskProcessar("Processando...", dado)

    def on_success(self, context, result):
        context.set("dado_final", result)

# 2. Cria as tasks concretas
class MinhaTask(BaseTask):
    def _run(self) -> bool:
        # Trabalho pesado aqui
        import time
        time.sleep(2)
        self.result = 42
        return True

class MinhaTaskProcessar(BaseTask):
    def __init__(self, desc, dado):
        super().__init__(desc)
        self.dado = dado

    def _run(self) -> bool:
        self.result = self.dado * 2
        return True

# 3. Executa a pipeline
context = ExecutionContext({"parametro_inicial": 10})

engine = AsyncPipelineEngine(
    steps=[StepCalcular(), StepProcessar()],
    context=context,
    on_finished=lambda ctx: print(f"Sucesso! Dados: {ctx.get('dado_final')}"),
    on_error=lambda errors: print(f"Erro: {errors}"),
    on_cancelled=lambda ctx: print("Cancelado"),
)

engine.start()

# Para cancelar:
# engine.cancel()
```

---

## 5. Regras e Comportamentos Importantes

| Comportamento | Descrição |
|---------------|-----------|
| **Pipeline só executa uma vez** | Se `start()` for chamado enquanto já está rodando, lança `RuntimeError` |
| **Steps são sequenciais** | Um step só começa quando o anterior termina com sucesso |
| **Step pode ser pulado** | Se `should_run()` retornar `False`, o step é ignorado |
| **Step pode ser síncrono** | Se `create_task()` retornar `None` e existir `run_inline()`, executa na hora |
| **Erro para a pipeline** | Qualquer exceção não tratada em um step interrompe toda a execução |
| **Cancelamento é cooperativo** | O step atual DEVE verificar `context.is_cancelled()` ou `is_canceled()` para parar |
| **Progresso global** | Calculado como: `((step_atual + progresso_step / 100) / total_steps) * 100` |
| **Contexto é o estado** | Steps se comunicam exclusivamente via `ExecutionContext` |

---

## 6. Pontos de Atenção (para implementar em Python puro sem QGIS)

1. **Substituir `QgsTask`** → Usar `threading.Thread` ou `concurrent.futures.ThreadPoolExecutor` para rodar tasks em background, e um mecanismo de `signal`/`event` para notificar a thread principal quando a task terminar.

2. **Substituir `QgsApplication.processEvents()`** → Em Python puro, usar `time.sleep(0.1)` ou um `Event` para manter a "guardiã" viva.

3. **Progresso** → O `PipelineTask` original serve apenas para manter a pipeline "viva" e reportar progresso. Em Python puro, pode ser substituído por um timer + callback de progresso.

4. **Thread safety do ExecutionContext** → Como `on_success` e `on_error` podem rodar em thread diferente da main, considere usar `threading.Lock` no `ExecutionContext` se houver concorrência real.