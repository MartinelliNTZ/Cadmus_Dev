# Plano de Refatoração — ExecutionContext + Steps

## 1. Diagnóstico — Problema Atual

O `ExecutionContext` atual virou um "saco de gatos" onde **todo tipo de dado** é jogado, misturando:

| Categoria | Exemplos no context atual |
|-----------|--------------------------|
| **Compartilhado (genérico)** | `tool_key`, erros, cancelamento, `results` |
| **Config de pipeline** | `enable_mrk`, `enable_exif`, `enable_xmp`, `enable_custom_fields`, `source` |
| **Parâmetros de step** | `base_folder`, `recursive`, `paths`, `selected_required_fields`, `selected_custom_fields`, `selected_mrk_fields`, `project_title`, `logo_path`, `extra_fields` |
| **UI callback** | `iface`, `points_layer_name` |
| **Resultados entre steps** | `json_path`, `layer`, `report_payload`, `total_points` |

**Consequências:**
- Nenhum step tem contrato claro de entrada — tudo é `context.get("qualquer_coisa")`
- Dá para quebrar pipeline porque um step anterior esqueceu de setar algo
- Impossível saber quais parâmetros cada step realmente precisa sem ler o código inteiro
- Testabilidade prejudicada (precisa mockar um context cheio de lixo)

---

## 2. Proposta — Novo Design

### 2.1. ExecutionContext Limpo

```
ExecutionContext
├── input_path: str           # Diretório de entrada (compartilhado)
├── output_path: str          # Diretório de saída (compartilhado)
├── files: list[str] | None   # Lista de arquivos (compartilhado)
├── tool_key: str             # ToolKey (compartilhado)
├── errors: list[Exception]   # Erros acumulados
├── is_cancelled: bool        # Flag de cancelamento
├── results: dict             # Resultados compartilhados entre steps
│
├── set_result(key, value)    # Guarda resultado de um step
├── get_result(key, default)  # Recupera resultado de step anterior
├── add_error(exc)
├── has_errors()
├── cancel()
├── is_cancelled()
└── clear()
```

**Mantém** `set_result`/`get_result` para comunicação entre steps (ex: `json_path`, `layer`).
**Remove** `set`/`get` genéricos ou os transforma em métodos de resultado apenas.

**Atributos canônicos** (acesso direto):
- `context.input_path = "/path/to/data"`
- `context.output_path = "/path/to/output"`
- `context.tool_key = "my_tool"`
- `context.files = ["file1.las", "file2.las"]`

### 2.2. Steps com Parâmetros Explícitos

Cada step declara seus parâmetros de entrada como argumentos do construtor ou método, não via context:

```python
# ANTES (atual)
class PhotoEnrichmentStep(BaseStep):
    def create_task(self, context):
        return PhotoEnrichmentTask(
            base_folder=context.get("base_folder"),
            recursive=context.get("recursive"),
            source=context.get("source"),
            paths=context.get("paths"),
            enable_exif=context.get("enable_exif"),
            enable_xmp=context.get("enable_xmp"),
            ...
        )

# DEPOIS (proposto)
class PhotoEnrichmentStep(BaseStep):
    def __init__(self, *, source="photo", enable_mrk=False, enable_exif=True,
                 enable_xmp=True, enable_custom_fields=True,
                 selected_required_fields=None, selected_custom_fields=None,
                 selected_mrk_fields=None, project_title="", logo_path=""):
        self.source = source
        self.enable_mrk = enable_mrk
        self.enable_exif = enable_exif
        self.enable_xmp = enable_xmp
        self.enable_custom_fields = enable_custom_fields
        self.selected_required_fields = selected_required_fields or []
        self.selected_custom_fields = selected_custom_fields or []
        self.selected_mrk_fields = selected_mrk_fields or []
        self.project_title = project_title
        self.logo_path = logo_path

    def create_task(self, context):
        context.require(["base_folder", "recursive", "tool_key"])
        return PhotoEnrichmentTask(
            base_folder=context.input_path or context.get("base_folder"),
            recursive=context.get("recursive"),
            source=self.source,
            paths=context.get("paths", []),
            enable_mrk=self.enable_mrk,
            enable_exif=self.enable_exif,
            enable_xmp=self.enable_xmp,
            enable_custom_fields=self.enable_custom_fields,
            selected_required_fields=self.selected_required_fields,
            selected_custom_fields=self.selected_custom_fields,
            selected_mrk_fields=self.selected_mrk_fields,
            project_title=self.project_title,
            logo_path=self.logo_path,
            tool_key=context.tool_key,
        )
```

### 2.3. Runner/Plugin com Montagem Limpa

O plugin ou runner monta os steps com parâmetros explícitos:

```python
# ANTES (DroneCoordinates.execute_tool)
context.set("source", "mrk+photo")
context.set("enable_mrk", True)
context.set("enable_exif", enable_exif)
context.set("enable_xmp", enable_xmp)
context.set("enable_custom_fields", enable_custom_fields)
context.set("selected_required_fields", ...)
context.set("selected_custom_fields", ...)
context.set("selected_mrk_fields", ...)
context.set("project_title", project_title)
context.set("logo_path", logo_path)
context.set("points_layer_name", "MRK_Points")
context.set("paths", paths)
context.set("base_folder", base_folder)
context.set("recursive", recursive)
context.set("tool_key", self.TOOL_KEY)
context.set("iface", self.iface)

steps = [PhotoEnrichmentStep(), JsonVectorizationStep()]
```

```python
# DEPOIS (DroneCoordinates.execute_tool)
context = ExecutionContext(
    input_path=base_folder,
    output_path=output_dir,
    files=paths,
    tool_key=self.TOOL_KEY,
)

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
    ),
    JsonVectorizationStep(),
]
if generate_report:
    steps.append(ReportGenerationStep())
```

---

## 3. O que NÃO Muda

- `AsyncPipelineEngine` — continua orquestrando steps do mesmo jeito
- `BaseStep` — continua com `create_task(context)`, `on_success(context, result)` etc.
- `BaseTask` — continua igual
- Fluxo de erro/cancelamento — idem
- Progresso global — idem
- Steps continuam usando `context.get()` para **resultados de steps anteriores** (`json_path`, `layer`)

---

## 4. O que MUDA (por arquivo)

### 4.1. `core/engine_tasks/ExecutionContext.py`

| Mudança | Descrição |
|---------|-----------|
| Adicionar atributos de classe | `input_path`, `output_path`, `files`, `tool_key` com type hints e docstrings |
| `__init__` aceitar kwargs | Seta os atributos canônicos |
| Manter `set_result`/`get_result` | Para comunicação entre steps |
| Manter `errors`, `is_cancelled` | Igual |
| `set`/`get` genéricos | Manter como fallback para compatibilidade (marcar como deprecated) |
| Adicionar `require()` | Validação de chaves obrigatórias no context |

### 4.2. `core/engine_tasks/PhotoEnrichmentStep.py`

| Mudança | Descrição |
|---------|-----------|
| `__init__` com parâmetros | `source`, `enable_mrk`, `enable_exif`, `enable_xmp`, `enable_custom_fields`, `selected_required_fields`, `selected_custom_fields`, `selected_mrk_fields`, `project_title`, `logo_path` |
| `create_task` usa atributos | Em vez de `context.get()` para parâmetros específicos |
| `context.require()` | Validar só o que é compartilhado (`input_path`/`base_folder`, `tool_key`) |

### 4.3. `core/engine_tasks/JsonVectorizationStep.py`

| Mudança | Descrição |
|---------|-----------|
| `run_inline` usa `context.get("json_path")` | Isso é RESULTADO de step anterior, mantém via context |
| Mantém `context.get("layer")` | Resultado que vai para callback `on_finished` |

### 4.4. `core/engine_tasks/ReportGenerationStep.py`

| Mudança | Descrição |
|---------|-----------|
| Mantém `context.get("json_path")` | Resultado de step anterior |
| Mantém `context.get("html_output_path")` | Pode ser parâmetro do step ou do context |

### 4.5. `plugins/DroneCoordinates.py`

| Mudança | Descrição |
|---------|-----------|
| `execute_tool` para de poluir o context | Cria steps com parâmetros nomeados |
| Context só com o canônico | `input_path=base_folder`, `tool_key=self.TOOL_KEY`, `files=paths` |
| Remove `context.set("iface", ...)` | Usar callback `on_finished` já existente na engine |
| `_on_pipeline_finished` | Recebe o context e usa `self.iface` direto (já tem) |

### 4.6. `core/services/DroneCoordinatesRunner.py`

| Mudança | Descrição |
|---------|-----------|
| Mesma lógica do DroneCoordinates | Monta steps com parâmetros explícitos |
| Context limpo | Só o canônico + resultados entre steps |

---

## 5. Estratégia de Implementação (Ordem)

```
Fase 1 — ExecutionContext (base)
  ├── 1.1. Novo ExecutionContext com atributos canônicos
  └── 1.2. Manter compatibilidade (set/get genérico como fallback)

Fase 2 — Steps (refatorar um a um)
  ├── 2.1. PhotoEnrichmentStep → parâmetros no __init__
  ├── 2.2. JsonVectorizationStep → verified (já usa pouco context)
  ├── 2.3. ReportGenerationStep → parâmetros no __init__
  └── 2.4. Outros steps (ReverseGeocodeStep, etc.) → mesma abordagem

Fase 3 — Plugins/Runners (consumidores)
  ├── 3.1. DroneCoordinates.py → montagem limpa
  ├── 3.2. DroneCoordinatesRunner.py → montagem limpa
  ├── 3.3. PhotoVectorizationPlugin.py → verificar
  └── 3.4. Outros plugins → verificar

Fase 4 — Documentação
  ├── 4.1. Atualizar SKILL_ASYNC_PAPELINE.md
  ├── 4.2. Atualizar SKILL_AGENT.md (se necessário)
  └── 4.3. Atualizar changelog.txt
```

---

## 6. Benefícios

| Benefício | Descrição |
|-----------|-----------|
| **Contrato claro** | Cada step declara explicitamente o que precisa |
| **Auto-documentado** | `PhotoEnrichmentStep(source="mrk+photo", enable_exif=True)` é auto-explicativo |
| **Testabilidade** | Step pode ser testado sem context mockado |
| **Type safety** | IDE autocompleta parâmetros dos steps |
| **Manutenibilidade** | Novo dev sabe exatamente o que cada step faz |
| **Reuso** | Steps podem ser instanciados com configurações diferentes sem tocar no context |
| **Performance** | Não precisa serializar/deserializar dict gigante |
| **Debug** | Logs mostram parâmetros reais dos steps |

---

## 7. Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Quebrar pipelines existentes | Manter compatibilidade: `set`/`get` genérico funciona, mas emite warning |
| Steps acessarem context de outros lugares | Auditoria: grep em `context.get(` e `context.set(` no codebase |
| Sobrecarga de parâmetros em steps complexos | Agrupar parâmetros relacionados em dataclasses (ex: `MetadataConfig`) |
| Migração grande de uma vez | Faseado: cada step vira PR separado |

---

## 8. Passo Inicial — Teste Piloto

O primeiro arquivo a ser refatorado é **`plugins/DroneCoordinates.py`** + **`core/services/DroneCoordinatesRunner.py`** (conforme solicitado).

### 8.1. Checklist para o teste piloto

- [ ] Novo `ExecutionContext` com atributos canônicos
- [ ] `PhotoEnrichmentStep` com `__init__` parametrizado
- [ ] `JsonVectorizationStep` mantido (já minimalista)
- [ ] `ReportGenerationStep` com `__init__` parametrizado
- [ ] `DroneCoordinates.py` com montagem limpa
- [ ] `DroneCoordinatesRunner.py` com montagem limpa
- [ ] Pipeline executa e produz mesmo resultado
- [ ] Compatibilidade mantida (outros plugins não quebram)

---

## 9. Próximos Passos

1. ✅ Revisar e aprovar este plano
2. Implementar Fase 1 (novo ExecutionContext)
3. Implementar Fase 2 (steps)
4. Implementar Fase 3 (DroneCoordinates + Runner)
5. Testar pipeline completa
6. Atualizar documentação