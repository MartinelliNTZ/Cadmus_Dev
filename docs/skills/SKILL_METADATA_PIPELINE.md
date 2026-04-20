---
name: drone-coordinates-report-metadata
description: >
  Sistema end-to-end para processar arquivos MRK, vetorizar fotos, manipular metadata de imagens e gerar relatórios HTML interativos usando pipeline assíncrono baseado em tasks QGIS.
---

# Drone Coordinates Report Metadata

## Resumo Executivo

**drone-coordinates-report-metadata** é um sistema que:
- **Processa MRKs e fotos**: extrai coordenadas georreferenciais, cria camadas vetoriais de pontos e trilhas
- **Manipula metadata de imagens**: enriquece geometrias com EXIF/XMP/MRK fields segundo preferências do usuário
- **Gera relatórios HTML interativos**: agrega metadata em JSONs, renderiza gráficos e mapas de cobertura
- **Orquestra via pipeline assíncrono**: executa steps em sequência usando `AsyncPipelineEngine` com callbacks e rastreamento de contexto

Usado por `DroneCoordinates`, `PhotoVectorizationPlugin`, `ReportMetadataPlugin` e `DroneCoordinatesRunner` para criar um fluxo de trabalho automático sem UI bloqueante.

## Objetivo

Transformar dados brutos de drone (arquivos MRK com localizações GPS, fotografias georreferenciadas) em artefatos prontos para análise: camadas vetoriais com campos de metadata, JSONs estruturados, e relatórios visuais em HTML. O sistema respeita preferências do usuário (quais campos incluir, estilos QML, geração de report) e reutiliza resultados existentes quando possível.

## Entradas

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| paths | list[str] | Sim (MrkParseStep) | Lista de caminhos para arquivos MRK ou pasta raiz |
| recursive | bool | Não | Se True, busca MRKs recursivamente em subpastas (default: True) |
| base_folder | str | Sim (PhotoVectorizationStep) | Pasta contendo imagens para vetorização |
| layer_name | str | Não | Nome da camada vetorial gerada (default: "Fotos_Sem_MRK") |
| extra_fields | dict | Não | Campos customizados a adicionar à camada |
| tool_key | str | Sim | ToolKey para rastreamento de logs (`ToolKey.DRONE_COORDINATES` ou `PHOTO_VECTORIZATION`) |
| iface | QgisInterface | Sim | Interface QGIS para adição de camadas ao projeto |
| json_path | str | Não | Caminho para JSON de metadata pré-gerado (skip MRK parsing) |
| html_output_path | str | Não | Diretório customizado para salvar relatório HTML |
| generate_report | bool | Não | Se True, executa `ReportGenerationStep` após processamento (default: lê de preferências) |

## Saídas

| Campo | Tipo | Descrição |
|-------|------|-----------|
| layer | QgsVectorLayer | Camada vetorial de pontos com geometria e campos de metadata |
| points | list[dict] | Lista de registros de pontos (cada um com `lon`, `lat`, campos de metadata) |
| json_path | str | Caminho para JSON temporário com registros de metadata extraída de imagens |
| report_payload | dict | Dicionário contendo `html_path`, `json_path`, `total_records`, `total_scored` |
| html_path | str | Caminho absoluto para relatório HTML gerado |
| total_points | int | Contagem de pontos processados com sucesso |

## Processamento

### Fase 1 — Inicialização de Contexto

O chamador (plugin ou runner) cria `ExecutionContext` com chaves obrigatórias:

```python
from core.engine_tasks.ExecutionContext import ExecutionContext
from core.engine_tasks.MrkParseStep import MrkParseStep
from core.engine_tasks.PhotoMetadataStep import PhotoMetadataStep
from core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine

context = ExecutionContext()
context.set("paths", ["/path/to/file.mrk"])
context.set("recursive", False)
context.set("tool_key", ToolKey.DRONE_COORDINATES)
context.set("points_layer_name", "MRK_Pontos")
context.set("track_layer_name", "MRK_Trilhas")
context.set("iface", qgis_iface)
```

### Fase 2 — MrkParseStep (Leitura de MRK)

`MrkParseStep` executa `MrkParseTask` que:
- Lê arquivos MRK usando `MrkParseTask` (lógica em `core/task/MrkParseTask.py`)
- Extrai lista de pontos com estrutura: `{"lon": float, "lat": float, "alt": float, "date_name": str, ...}`
- Cria `QgsVectorLayer` de pontos com campos QGIS tipados:
  - `foto` (Int) — número da fotografia
  - `alt` (Double) — altitude em metros
  - `date_name` (String) — data/hora formatada
  - `flight_number`, `flight_name`, `folder_level1/2` (String)
  - `mrk_folder` (String) — caminho do MRK

```python
# Em MrkParseStep.on_success():
layer = VectorLayerGeometry.create_point_layer_from_dicts(
    points=points,
    name=layer_name,
    field_specs=[
        ("foto", QVariant.Int, "foto"),
        ("alt", QVariant.Double, "alt"),
        ("date_name", QVariant.String, "date_name"),
        # ... mais fields
    ],
    geometry_keys=("lon", "lat"),
    extra_fields=context.get("extra_fields"),
)
QgsProject.instance().addMapLayer(layer)
context.set("layer", layer)
context.set("points", points)
```

### Fase 3 — PhotoMetadataStep (Enriquecimento de Metadata)

Se `apply_photos=True` em preferências, `PhotoMetadataStep` executa `PhotoMetadataTask` que:
- Itera sobre pontos de geometria criados na Fase 2
- Busca fotografias correspondentes (matching por número/locação)
- Extrai metadata: EXIF (ISO, cameramake, etc), XMP (DJI campos), custom fields
- Enriquece atributos da camada com esses campos
- Aplica type inference automático (String vs Double) respeitando lista `_FORCE_STRING_FIELDS`

```python
# Em PhotoMetadataStep._infer_field_type():
_FORCE_STRING_FIELD_KEYS = {
    "file", "path", "DateTimeOriginal", "FlightName", "CaptureUUID", ...
}

@classmethod
def _infer_field_type(cls, field_name, sample_values):
    if field_name in cls._FORCE_STRING_FIELDS:
        return QVariant.String
    numeric_count = sum(1 for v in sample_values if cls._is_numeric_candidate(field_name, v))
    return QVariant.Double if numeric_count == len(sample_values) else QVariant.String
```

### Fase 4 — PhotoVectorizationStep (Vetorização Direta de Fotos)

Se chamado sem MRK (via `PhotoVectorizationPlugin`), `PhotoVectorizationStep` executa `PhotoVectorizationTask` que:
- Busca imagens em `base_folder` recursivamente (se `recursive=True`)
- Extrai metadata de cada foto (EXIF/XMP)
- Cria geometria de ponto a partir de GPS data da imagem
- Gera JSON de metadata em `{TOOL_KEY}/reports/json/` 
- Retorna `{"layer": QgsVectorLayer, "json_path": str, "total_points": int}`

```python
# Em PhotoVectorizationStep.on_success():
if layer and layer.isValid():
    context.set("layer", layer)
    context.set("json_path", result.get("json_path"))
    context.set("total_points", result.get("total_points", 0))
```

### Fase 5 — ReportGenerationStep (Geração de Relatório HTML)

Executado se JSON está disponível e `generate_report=True`. `ReportGenerationStep`:
- Recupera JSON via `_resolve_json_path()` (busca em `json_path`, `photo_metadata_json_path`, `report_json_path`)
- Chama `ReportGenerationService.generate_from_json(json_path)` que:
  - Carrega records do JSON usando `JSONUtil.load_records()`
  - Cria `IMGMetadata` para cada record e calcula `.score()`
  - Agrega estatísticas com `AggregateAnalyzer.analyze()`
  - Renderiza gráficos (histogramas, distribuições) com `RenderEngine.generate_charts()`
  - Gera mapa interativo de cobertura com `RenderEngine.generate_map_data()`
  - Renderiza HTML final e salva em `{TOOL_KEY}/reports/html/report_metadata_*.html`
- Abre HTML no navegador padrão se possível

```python
# Em ReportGenerationService.generate_from_json():
range_metadata_manager.load(tool_key=self.tool_key)
records = JSONUtil.load_records(json_path=json_path, tool_key=self.tool_key)
results = [IMGMetadata(record).score() for record in records]
agg = AggregateAnalyzer.analyze(results)
engine = RenderEngine(tool_key=self.tool_key)
charts = engine.generate_charts(agg)
map_data = engine.generate_map_data(results)
html = engine.render_report(results=results, agg=agg, charts=charts, map_data=map_data)
engine.save_report(html, target_path)
```

### Fluxo Completo via AsyncPipelineEngine

`AsyncPipelineEngine` orquestra os steps em sequência assíncrona:

```python
steps = [
    MrkParseStep(),           # Fase 2: parse MRK
    PhotoMetadataStep(),      # Fase 3: enriquecimento (if apply_photos==True)
]
if generate_report:
    steps.append(ReportGenerationStep())  # Fase 5: report

engine = AsyncPipelineEngine(
    steps=steps,
    context=context,
    on_finished=self._on_pipeline_finished,
    on_error=self._on_pipeline_error,
)
engine.start()  # Inicia QgsTask no task manager
```

Cada step:
1. Recebe contexto compartilhado
2. Implementa `should_run(context)` para skip condicional
3. Cria `QgsTask` via `create_task(context)`
4. Executa assincronamente via QGIS task manager
5. Chama `on_success()` com resultado ou `on_error()` com exceção
6. Passa controle para próximo step

---

## Regras

### ✅ Sempre:

- Exigir `tool_key` em todas as operações para rastreabilidade de logs estruturados
- Validar existência de arquivo/pasta antes de processar (`ExplorerUtils.is_file()`)
- Carregar preferências do usuário via `Preferences.load_tool_prefs(tool_key)` para respeitar filtros de campos
- Reutilizar camadas existentes quando arquivo GPKG já existe (verificar com `VectorLayerSource.load_existing_vector_layer()`)
- Armazenar resultados intermediários em contexto compartilhado (`ExecutionContext`)
- Logar com `LogUtils(tool=tool_key, class_name=self.__class__.__name__)` estruturadamente
- Abrir camadas no projeto QGIS via `QgsProject.instance().addMapLayer()` após geração
- Chamar callbacks `on_finished(payload)` e `on_error(exception)` ao final do pipeline

### ❌ Nunca:

- Chamar `.start()` em `AsyncPipelineEngine` se já está rodando (`is_running() == True`)
- Escrever logs com `print()` ou `sys.stderr.write()` — usar `LogUtils` sempre
- Hardcodar nomes de campos ou tipos QGIS — usar `MetadataFields` para normalização
- Criar camada sem validação (`if not layer or not layer.isValid()`)
- Gerar relatório sem JSON válido — `ReportGenerationStep.should_run()` valida primeiro
- Ignorar exceções — sempre capturar e logar com `logger.exception(e, code="...")`
- Assumir que geometria GPS existe em imagem — validar antes de criar ponto

---

## Padrões de Uso

### Padrão 1 — Pipeline completo via DroneCoordinatesRunner (sem UI)

Chamado quando arquivo MRK é dropado ou selecionado:

```python
from core.services.DroneCoordinatesRunner import DroneCoordinatesRunner
from utils.ToolKeys import ToolKey

runner = DroneCoordinatesRunner(iface, tool_key=ToolKey.DRONE_COORDINATES)
runner.run_mrk_file(
    file_path="/path/to/drone.mrk",
    on_finished=lambda payload: print(f"Pontos: {payload.get('points_layer')}"),
    on_error=lambda exc: print(f"Erro: {exc}")
)
# Retorna True se pipeline iniciado, False se arquivo inválido
```

**Internamente em `run_mrk_file()`:**
- Carrega preferências (apply_photos, generate_report, campos selecionados)
- Cria contexto e steps conforme preferências
- Inicializa `AsyncPipelineEngine` com callbacks
- Executa assincronamente (não bloqueia thread)

### Padrão 2 — Plugin com UI (PhotoVectorizationPlugin)

```python
from core.engine_tasks.PhotoVectorizationStep import PhotoVectorizationStep
from core.engine_tasks.ReportGenerationStep import ReportGenerationStep
from core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from core.engine_tasks.ExecutionContext import ExecutionContext
from utils.ToolKeys import ToolKey

photo_folder = "/path/to/photos"
recursive = True
generate_report = True

context = ExecutionContext()
context.set("base_folder", photo_folder)
context.set("recursive", recursive)
context.set("generate_report", generate_report)
context.set("layer_name", "Fotos_Sem_MRK")
context.set("tool_key", ToolKey.PHOTO_VECTORIZATION)
context.set("iface", self.iface)

steps = [PhotoVectorizationStep()]
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

### Padrão 3 — Regeneração de Relatório (sem processar imagens)

Usar diretamente `ReportGenerationService` sem pipeline:

```python
from core.services.ReportGenerationService import ReportGenerationService
from utils.ToolKeys import ToolKey

service = ReportGenerationService(tool_key=ToolKey.REPORT_METADATA)
payload = service.generate_from_json(
    json_path="/path/to/metadata.json",
    html_output_path="/path/to/custom/output.html"  # opcional
)
print(f"Relatório: {payload['html_path']}")
# Retorna: {"json_path": str, "html_path": str, "total_records": int, "total_scored": int}
```

---

## Dependências

| Módulo | Caminho | Responsabilidade |
|--------|---------|-----------------|
| MrkParseStep | core/engine_tasks/MrkParseStep.py | Orquestra MrkParseTask, cria layer de pontos a partir de MRK |
| PhotoMetadataStep | core/engine_tasks/PhotoMetadataStep.py | Enriquece camada com metadata de imagens (EXIF/XMP/MRK) |
| PhotoVectorizationStep | core/engine_tasks/PhotoVectorizationStep.py | Vetoriza pasta de fotos sem MRK, passa json_path |
| ReportGenerationStep | core/engine_tasks/ReportGenerationStep.py | Valida e executa ReportGenerationService |
| AsyncPipelineEngine | core/engine_tasks/AsyncPipelineEngine.py | Orquestrador genérico de steps em fila assíncrona |
| ExecutionContext | core/engine_tasks/ExecutionContext.py | Contexto compartilhado entre steps (chaves/valores em dict) |
| ReportGenerationService | core/services/ReportGenerationService.py | Gera relatório HTML a partir de JSON de metadata |
| DroneCoordinatesRunner | core/services/DroneCoordinatesRunner.py | Entrada sem UI para processar MRK (drag-drop, automação) |
| DroneCoordinates | plugins/DroneCoordinates.py | Plugin com UI para configurar MRK + metadata + report |
| PhotoVectorizationPlugin | plugins/PhotoVectorizationPlugin.py | Plugin com UI para vetorizar pasta de fotos |
| ReportMetadataPlugin | plugins/ReportMetadataPlugin.py | Plugin com UI para regenerar relatório de JSON existente |
| MetadataFields | utils/mrk/MetadataFields.py | Enum de campos EXIF/XMP/MRK com normalização e descrições |
| VectorLayerGeometry | utils/vector/VectorLayerGeometry.py | Factory para criar layers vetoriais de pontos/linhas |
| VectorLayerSource | utils/vector/VectorLayerSource.py | Save/load vetores em GPKG, verificação de existência |
| ExplorerUtils | utils/ExplorerUtils.py | Paths, folders, file operations, abertura em explorer |

---

## Exemplos Completos

### Exemplo 1 — Processar MRK com report automático

```python
# Contexto: DroneCoordinatesRunner.run_mrk_file() chamado via drag-drop

from core.engine_tasks.MrkParseStep import MrkParseStep
from core.engine_tasks.PhotoMetadataStep import PhotoMetadataStep
from core.engine_tasks.ReportGenerationStep import ReportGenerationStep
from core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from core.engine_tasks.ExecutionContext import ExecutionContext
from utils.Preferences import load_tool_prefs
from utils.ToolKeys import ToolKey

file_path = "/drone/data/flight_001.mrk"
tool_key = ToolKey.DRONE_COORDINATES

# Carregar preferências salvas
prefs = load_tool_prefs(tool_key)
apply_photos = prefs.get("photos", False)
generate_report = prefs.get("generate_report", False)

# Montar contexto
context = ExecutionContext()
context.set("paths", [file_path])
context.set("recursive", False)
context.set("tool_key", tool_key)
context.set("points_layer_name", "Flight_001_Points")
context.set("track_layer_name", "Flight_001_Track")
context.set("iface", qgis_iface)

# Montar steps
steps = [MrkParseStep()]
if apply_photos:
    steps.append(PhotoMetadataStep())
if generate_report and apply_photos:
    steps.append(ReportGenerationStep())

# Executar
engine = AsyncPipelineEngine(
    steps=steps,
    context=context,
    on_finished=lambda ctx: print("✓ Pipeline concluído"),
    on_error=lambda ctx, exc: print(f"✗ Erro: {exc}")
)
engine.start()
```

### Exemplo 2 — Vetorizar pasta de fotos com UI progressivo

```python
# Contexto: PhotoVectorizationPlugin.execute_tool() após usuário clicar "VECTORIZE_PHOTOS"

from core.engine_tasks.PhotoVectorizationStep import PhotoVectorizationStep
from core.engine_tasks.ReportGenerationStep import ReportGenerationStep
from core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from core.engine_tasks.ExecutionContext import ExecutionContext
from utils.ToolKeys import ToolKey

photo_folder = self.photo_folder_selector.get_paths()[0]
recursive = self.photo_opts_map["photo_recursive"].isChecked()
generate_report = self.photo_opts_map["photo_generate_report"].isChecked()

context = ExecutionContext()
context.set("base_folder", photo_folder)
context.set("recursive", recursive)
context.set("generate_report", generate_report)
context.set("layer_name", "Fotos_Sem_MRK")
context.set("tool_key", ToolKey.PHOTO_VECTORIZATION)
context.set("iface", self.iface)

steps = [PhotoVectorizationStep()]
if generate_report:
    steps.append(ReportGenerationStep())

self.logger.info("Iniciando pipeline de vetorização", data={
    "base_folder": photo_folder,
    "recursive": recursive,
    "generate_report": generate_report
})

engine = AsyncPipelineEngine(
    steps=steps,
    context=context,
    on_finished=self._on_pipeline_finished,
    on_error=self._on_pipeline_error,
)
engine.start()
```

---

## Limitações

- **JSON intermediário obrigatório**: `ReportGenerationStep` não funciona sem JSON de metadata válido. Se etapa anterior falhar ao gerar JSON, step é pulado (mas sem erro) conforme `should_run()`.
- **GPS em imagem não garantido**: Fotos podem não ter EXIF GPS válido. `PhotoVectorizationTask` filtra e reporta silenciosamente.
- **Type inference ambíguo**: Campos com valores mistos (string "123" vs int 123) enfocam heurística in `PhotoMetadataStep._infer_field_type()`. Lista `_FORCE_STRING_FIELDS` força tipos mas não cobre todos os casos.
- **Reutilização de layer em memória**: Se MRK já foi processado e GPKG existe, runner reutiliza arquivo mas pode usar layer em memória desatualizado se projeto foi modificado.
- **Sem validação de CRS**: Camadas criadas assumem EPSG:4326. Se MRK/fotos estão em CRS diferente, geometria estará incorreta.
- **ReportGenerationService é síncrono**: `generate_from_json()` bloqueia até completar renderização HTML. Para grandes JSONs, pode congelar UI se chamado em thread principal.

---

## Validação

| Critério | Status | Justificativa |
|----------|--------|---------------|
| Reutilizável? | ✅ | Cada step é independente, contexto é compartilhado via `ExecutionContext`. Pode ser montado em qualquer ordem respeitando dependências. |
| Clara? | ✅ | Fluxo é linear: MRK → Metadata → Report. Cada fase tem responsabilidade única. Callbacks explícitos. |
| Independente de contexto oculto? | ✅ | Todas as chaves de contexto são definidas explicitamente pelo chamador ou geradas internamente. Sem variáveis globais. |

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-04-20 | 1.0.0 | Criação via SKILL_FACTORY — lidos: MrkParseStep.py, PhotoMetadataStep.py, PhotoVectorizationStep.py, ReportGenerationStep.py, AsyncPipelineEngine.py, ExecutionContext.py, DroneCoordinatesRunner.py, ReportGenerationService.py, DroneCoordinates.py, PhotoVectorizationPlugin.py, ReportMetadataPlugin.py |
