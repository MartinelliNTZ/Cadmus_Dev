# AsyncPipelineEngine — Arquitetura e Guia Técnico

Data: 2026/03/12

Objetivo
--------
Documento técnico detalhando o design, contratos e precauções do sistema de
pipeline assíncrono usado pelo plugin. Cobre `AsyncPipelineEngine`, `BaseTask`,
`BaseStep`, `ExecutionContext`, o `PipelineTask` guard e o `ParallelStep`.

Visão Geral
-----------
O pipeline implementa uma separação clara entre cálculo pesado (worker thread)
e aplicação das mudanças no QGIS (thread principal). A unidade de trabalho é o
`Step` (contrato definido em `core/engine_tasks/BaseStep.py`). Cada `Step`
produz uma `QgsTask` (tipicamente subclasse de `BaseTask`) que roda em background
e retorna um resultado que o `Step.on_success(context, result)` aplica na UI.

Componentes Principais
----------------------
- `ExecutionContext` (`core/engine_tasks/ExecutionContext.py`)
  - Armazena dados compartilhados e erros.
  - API mínima: `set(key,value)`, `get(key,default)`, `require(keys)`,
    `add_error(exc)`, `get_errors()`, `cancel()`, `is_cancelled()`.
  - Regra: não armazenar objetos C/C++ que possam ser deletados por Qt fora
    do escopo. Guardar referências leves (ids, strings, simples wrappers).

- `BaseTask` (`core/task/BaseTask.py`)
  - Subclasse de `QgsTask`. Responsabilidade: executar `_run()` no thread
    worker sem tocar em camadas QGIS (não thread-safe).
  - Deve preencher `self.result` e usar `self.setProgress()`.
  - Callbacks: `on_success(result)` e `on_error(exception)` são setados pelo
    orchestrador (ex.: `AsyncPipelineEngine` ou `ParallelStep`).
  - `finished(success)` invoca `on_success` ou `on_error` conforme o caso.

- `BaseStep` (`core/engine_tasks/BaseStep.py`)
  - Contrato: `name()`, `should_run(context)`, `create_task(context)`,
    `on_success(context, result)`, `on_error(context, exception)`.
  - `create_task` retorna um `QgsTask` (p.ex. instância de `BaseTask`).
  - `on_success` executa no thread principal e deve aplicar alterações em lote.

- `AsyncPipelineEngine` (`core/engine_tasks/AsyncPipelineEngine.py`)
  - Orquestrador sequencial: percorre `steps` e para cada step cria a task via
    `task = step.create_task(context)`, agenda com
    `QgsApplication.taskManager().addTask(task)` e aguarda o callback.
  - Recebe callbacks do task: `task.on_success` → `_handle_task_success`
    e `task.on_error` → `_handle_task_error`.
  - Mantém um `PipelineTask` guard (um `QgsTask` que mantém o pipeline vivo e
    exibe progresso agregado usando `setProgress`).
  - API pública: `start()`, `cancel()`, `is_running()`.

- `ParallelStep` (`core/engine_tasks/ParallelStep.py`)
  - Composite step que encapsula execução paralela de múltiplos `BaseStep`.
  - Cria um `_ParallelGroupTask` (um `QgsTask`) que agenda as tasks dos
    sub-steps, monitora conclusão, agrega resultados `{ step_name: result }`
    e propaga erros/cancelamento.
  - Mantém compatibilidade: `AsyncPipelineEngine` trata `ParallelStep` como um
    `BaseStep` que retorna uma única `QgsTask` (o agrupador).

Fluxo de Execução (sequencial)
-----------------------------
1. `engine.start()` cria `PipelineTask` e chama `_run_next_step()`.
2. Para cada `step`:
   - se `not step.should_run(context)`: pula.
   - `task = step.create_task(context)` → deve retornar `QgsTask`.
   - engine assina `task.on_success = _handle_task_success` e
     `task.on_error = _handle_task_error`.
   - agenda `task` com `QgsApplication.taskManager().addTask(task)`.
3. Quando task chama `on_success(result)`:
   - `engine._handle_task_success` invoca `step.on_success(context, result)`
     no thread principal.
4. Se `step.on_success` lança exceção → `engine._handle_task_error` e aborta.

Fluxo Paralelo (ParallelStep)
-----------------------------
- `ParallelStep.create_task` retorna `_ParallelGroupTask`.
- `_ParallelGroupTask.run()` cria as tasks dos sub-steps e agenda todas.
- Cada subtask tem handlers locais que chamam `s.on_success(context,result)`
  e armazenam `results[s.name()] = result` protegidos por lock.
- Se qualquer erro ocorrer em subtask, o grupo cancela os restantes e
  registra a exceção como erro primário — então falla o grupo.
- Quando todas concluem com sucesso, o `_ParallelGroupTask.finished` chama
  `on_success(aggregated_results)` e o engine prossegue.

Contratos de Dados
------------------
- Forma comum de `result` de uma task: dicionário. Exemplos:
  - `LineFieldsTask.result = { 'updates': { fid: { field_name: value } }, 'missing_fields': [...] }`
  - `ReverseGeocodeTask.result = address_string` (simples)
- Documentar contrato de cada task é obrigatório; o `Step.on_success`
  valida shape antes de aplicar.

Regras Obrigatórias (resumidas)
-------------------------------
1. Task roda em worker thread e NÃO modifica camadas QGIS.
2. Task retorna dados serializáveis no Python (dict/list/primitives).
3. Step.on_success() é executado no thread principal e deve aplicar
   mudanças em lote usando `layer.blockSignals(True)` + `try/finally`
   e chamar `QApplication.processEvents()` entre batches.
4. Decisão sync/async: use `layer.featureCount()` para escolher entre
   execução síncrona ou pipeline assíncrono (threshold empírico ~1000).
5. Cancelamento: Propague `context.cancel()` para tasks; tasks devem checar
   `self.isCanceled()` periodicamente e retornar False rapidamente.

Cancelamento e Limpeza
----------------------
- O engine chama `self._current_task.cancel()` e `self._pipeline_task.cancel()`
  em `cancel()`; `ExecutionContext.cancel()` marca o contexto.
- Tasks devem verificar `isCanceled()` e abortar o loop para permitir
  desbloqueio de `on_success` (que deve usar `break` e não `return` dentro
  de blocos try/finally, para garantir cleanup).
- Em `ParallelStep`, cancelamento do grupo cancela todas subtasks.

Tratamento de Erros
-------------------
- Erros no `_run()` de uma `BaseTask` devem ser capturados e atribuídos a
  `self.exception` (padrão em `BaseTask`). `finished(False)` chama `on_error`.
- Se `step.on_success` lançar exceção, o `AsyncPipelineEngine` chama
  `step.on_error(context, exc)` (se presente), coloca a exceção em
  `context.add_error()` e finaliza a pipeline com `_finish_error()`.
- No `ParallelStep`, a primeira exceção coletada é a que será propagada; as
  demais subtasks são canceladas imediatamente.

Progresso
---------
- `AsyncPipelineEngine` agrega progresso por step via `_set_global_progress`.
- `ParallelStep` tenta forwardar progresso de subtasks conectando
  `task.progressChanged` ao handler `_on_subtask_progress` e chama
  `setProgress()` no grupo. Esta agregação é uma aproximação — adequada para
  feedback visual, não para contabilidade precisa.

Padrões de Implementação (ex.: LineFields)
------------------------------------------
- `LineFieldsTask` calcula os valores e preenche `self.result`.
- `LineFieldsStep.on_success` valida `result` e aplica `changeAttributeValue`
  em batches de `chunk = 2000` com `layer.blockSignals(True)` e
  `QApplication.processEvents()` por batch.

Checklist de Segurança / Prevenção de Bugs
-----------------------------------------
- Nunca modificar `QgsVectorLayer` em `BaseTask._run()`.
- Sempre usar `try/finally` ao bloquear signals da layer.
- Verificar `context.is_cancelled()` dentro dos loops aplicadores.
- Validar shape do `result` antes de aplicar.
- Evitar armazenar objetos C++ Qt em `ExecutionContext` sem wrappers.

Erros Comuns e Sinais de Alerta
-------------------------------
- UI travando por longos períodos:
  - Causa: aplicação síncrona de muitas features sem batching.
  - Mitigação: usar pipeline + batch size 2000 + `QApplication.processEvents()`.
- Layer travada / bloqueada:
  - Causa: blockSignals() sem finally → signals não reativados.
  - Mitigação: try/finally garantido.
- "This action cannot be performed in a worker thread":
  - Causa: task tocando em layer.
  - Mitigação: mover alteração para Step.on_success.
- Cancelamento não interrompe:
  - Causa: task não verifica `isCanceled()` com frequência.
  - Mitigação: checar `isCanceled()` em loops de larga escala e após operações pesadas.

Testes e Validação
------------------
- Testes unitários (recomendado):
  - Criar `FakeTask` e `FakeStep` que simulam `_run()` e validam chamadas a
    `on_success`/`on_error` e ao `ExecutionContext`.
  - Testar `ParallelStep` com: todas subtasks sucesso; uma falha; cancelamento.
- Testes manuais no QGIS:
  - Carregar camada com 10k+ features e executar `LineFieldsStep` para confirmar
    UI responsiva e aplicação correta.

Mapeamento para o Código
------------------------
- Engine: `core/engine_tasks/AsyncPipelineEngine.py`
- Steps de exemplo: `core/engine_tasks/LineFieldsStep.py`, `PointFieldsStep.py`,
  `PolygonFieldsStep.py`, `ReverseGeocodeStep.py`, `AltimetryStep.py`.
- Tasks de exemplo: `core/task/LineFieldsTask.py`, `reverse_geocoding_task.py`,
  `altimetry_task.py`.
- Composite parallel: `core/engine_tasks/ParallelStep.py` (novo).

Recomendações Finais
--------------------
1. Documentar o contrato de `result` de cada `BaseTask` (um parágrafo por
   task em seus módulos) para evitar erros de shape no `on_success`.
2. Adicionar testes unitários para `ParallelStep` e `AsyncPipelineEngine`.
3. Monitorar memória em execuções paralelas (subtasks mantêm dados em memória).
4. Registrar métricas: tempo por step, counts, número de features processadas
   para identificar hotspots.
5. Evitar modificações globais no `ExecutionContext` após o início do pipeline;
   preferir cópias locais quando for necessário manipular dados temporários.

Conclusão
---------
O design atual separa com clareza cálculo e aplicação, usa `QgsTask` para
trabalhos de CPU e protege o QGIS com batches e processEvents. A adição do
`ParallelStep` permite ganhar performance onde etapas são independentes,
preservando comportamento sequencial quando necessário e mantendo o engine
inalterado. Seguir as regras descritas acima reduz risco de travamentos e
erros de thread-safety.
