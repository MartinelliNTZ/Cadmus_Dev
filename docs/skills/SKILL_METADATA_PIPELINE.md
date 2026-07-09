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

Usado por `DroneCoordinates`, `PhotoVectorizationPlugin`, `ReportMetadataPlugin` e `DroneCoordinatesRunner`.

---

## Arquitetura de Pipeline Unificada

Os 3 pipelines principais (DroneCoordinates, DroneCoordinatesRunner, PhotoVectorizationPlugin) seguem **exatamente o mesmo fluxo**:

```
DroneCoordinates / Runner:
  PhotoEnrichmentStep → ReverseGeocodeStep → JsonVectorizationStep → (ReportGenerationStep?)

PhotoVectorizationPlugin:
  PhotoEnrichmentStep → ReverseGeocodeStep → JsonVectorizationStep → (ReportGenerationStep?)
```

**ReverseGeocodeStep** é inserido entre o enriquecimento e a vetorização:
- Lê o `json_path` do contexto (setado pelo PhotoEnrichmentStep)
- Extrai coordenadas (Lat/Lon) da **primeira foto** do JSON
- Executa reverse geocode via BigDataCloud API
- Persiste dados de localização no cabeçalho do JSON (`geocode.municipio`, `geocode.state`, etc.)
- Adiciona timestamps `geocode_start`/`geocode_end` ao JSON
- Steps são independentes: se geocode falhar, pipeline continua normalmente

**PhotoEnrichmentStep** detecta automaticamente se há dados MRK (paths no `__init__`) ou não:
- Com MRK → modo `"mrk+photo"` → cruza pontos MRK com EXIF+XMP+CustomFields
- Sem MRK → modo `"photo"` → extrai EXIF+XMP+CustomFields direto das fotos

**JsonVectorizationStep** usa `CoordSource` de cada registro para decidir geometria:
- `CoordSource=MRK` → LAT/LON (coordenadas originais do MRK)
- `CoordSource=XMP/EXIF` → GPS_LATITUDE/GPS_LONGITUDE (coordenadas enriquecidas das fotos)

---

## Novo Padrão — Parâmetros no Step, Context Apenas Canônico

**ANTES** (context poluído):
```python
context = ExecutionContext()
context.set("paths", ["/flight.mrk"])
context.set("base_folder", "/photos")
context.set("recursive", True)
context.set("tool_key", ToolKey.DRONE_COORDINATES)
context.set("selected_required_fields", [...])
context.set("enable_exif", True)
context.set("generate_report", True)
context.set("iface", iface)

steps = [PhotoEnrichmentStep(), JsonVectorizationStep()]
```

**DEPOIS** (parâmetros no step, context só canônico):
```python
context = ExecutionContext(
    input_path="/photos",
    tool_key=ToolKey.DRONE_COORDINATES,
    files=["/flight.mrk"],
)

steps = [
    PhotoEnrichmentStep(
        source="mrk+photo",
        enable_mrk=True,
        enable_exif=True,
        enable_xmp=True,
        enable_custom_fields=True,
        selected_required_fields=[...],
        selected_custom_fields=[...],
        selected_mrk_fields=[...],
        recursive=True,
        paths=["/flight.mrk"],
    ),
    JsonVectorizationStep(source="mrk+photo"),
]
if generate_report:
    steps.append(ReportGenerationStep())

engine = AsyncPipelineEngine(steps=steps, context=context, ...)
engine.start()
```

---

## Entradas do Pipeline

### ExecutionContext (atributos canônicos)

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `input_path` | str | Diretório base para busca de arquivos/fotos |
| `output_path` | str | Diretório de saída (opcional) |
| `files` | list[str] \| None | Lista de caminhos MRK |
| `tool_key` | ToolKey | ToolKey para rastreamento de logs |
| `json_path` | str | Caminho do JSON (resultado entre steps) |

### Steps (parâmetros explícitos no `__init__`)

#### PhotoEnrichmentStep

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `source` | str | Sim | `"mrk+photo"`, `"mrk"` ou `"photo"` |
| `enable_mrk` | bool | Não | Habilita parsing MRK (default: False) |
| `enable_exif` | bool | Não | Habilita extração EXIF (default: True) |
| `enable_xmp` | bool | Não | Habilita extração XMP (default: True) |
| `enable_custom_fields` | bool | Não | Habilita campos custom (default: True) |
| `selected_required_fields` | list[str] | Não | Campos EXIF/XMP selecionados |
| `selected_custom_fields` | list[str] | Não | Campos custom selecionados |
| `selected_mrk_fields` | list[str] | Não | Campos MRK selecionados |
| `project_title` | str | Não | Título do projeto |
| `logo_path` | str | Não | Caminho do logotipo |
| `recursive` | bool | Não | Busca recursiva (default: True) |
| `paths` | list[str] | Não | Caminhos MRK específicos |

#### JsonVectorizationStep

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `source` | str | Não | Identificador da fonte (ex: `"mrk+photo"`) |
| `layer_name` | str | Não | Nome da camada vetorial |

#### ReportGenerationStep

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `html_output_path` | str | Não | Diretório customizado para salvar relatório HTML |

---

## Fluxo Completo do Pipeline

### Fase 1 — Criação do Context + Steps

```python
from core.engine_tasks.ExecutionContext import ExecutionContext
from core.engine_tasks.PhotoEnrichmentStep import PhotoEnrichmentStep
from core.engine_tasks.JsonVectorizationStep import JsonVectorizationStep
from core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine

context = ExecutionContext(
    input_path="/path/to/photos",
    tool_key=ToolKey.DRONE_COORDINATES,
    files=["/path/to/file.mrk"],
)

steps = [
    PhotoEnrichmentStep(
        source="mrk+photo",
        enable_mrk=True,
        enable_exif=True,
        enable_xmp=True,
        enable_custom_fields=True,
        selected_required_fields=["File", "GpsLatitude", "GpsLongitude"],
        selected_custom_fields=["GroundSampleDistanceCm"],
        selected_mrk_fields=["Foto", "MrkFile"],
        recursive=False,
        paths=["/path/to/file.mrk"],
    ),
    JsonVectorizationStep(source="mrk+photo"),
]
if generate_report:
    steps.append(ReportGenerationStep())
```

### Fase 2 — ReverseGeocodeStep (Geolocalização do Endereço)

Step que executa reverse geocode para obter endereço a partir das coordenadas da primeira foto.

**Modos de operação** (por ordem de prioridade):
1. Coordenadas explícitas passadas via `__init__(lat=..., lon=...)`
2. Coordenadas do contexto legado (`context.get("lat")` / `context.get("lon")`)
3. **JSON path**: lê a primeira foto do JSON e extrai `Lat`/`Lon`

**Fluxo**:
1. `should_run(context)`: verifica se há coordenadas disponíveis (explícitas ou via JSON)
2. `create_task(context)`: resolve coordenadas, cria `ReverseGeocodeTask`
3. `ReverseGeocodeTask._run()`: chama BigDataCloud API com lat/lon
4. `on_success(context, result)`:
   - `context.set_result("address_data", result)` — propaga para steps posteriores
   - `JsonUtil.update_geocode_data(json_path, geocode_payload)` — persiste no JSON
   - `JsonUtil.update_timestamps(json_path, {"geocode_start": ..., "geocode_end": ...})`

**Estrutura adicionada ao JSON**:
```json
{
  "schema_version": "2.0",
  "geocode": {
    "municipio": "São Paulo",
    "state_district": "São Paulo",
    "state": "São Paulo",
    "region": "Southeast",
    "country": "Brazil"
  },
  "timestamps": {
    "geocode_start": "2026-07-09T14:36:43.221270",
    "geocode_end": "2026-07-09T14:36:45.123456"
  }
}
```

### Fase 3 — PhotoEnrichmentStep (Enriquecimento de Metadata)

Step **unificado** que substitui os antigos `MrkParseStep` e `PhotoMetadataStep`.

**Funcionamento**:

1. `create_task(context)`:
   - Resolve `input_path` do context canônico
   - Resolve `tool_key` do context canônico
   - Resolve paths MRK de `self.paths` ou `context.files`
   - Cria `PhotoEnrichmentTask` com todos os parâmetros

2. `PhotoEnrichmentTask._run()`:
   - Modo `"mrk+photo"`: extrai pontos MRK + executa pipeline completo de enriquecimento
   - Modo `"photo"`: apenas extração EXIF/XMP das fotos
   - Aplica filtro de campos selecionados
   - Converte records para PascalCase (formato JSON v2.0)
   - Salva JSON via `PhotoMetadata.build_and_save_json()`

3. `on_success(context, result)`:
   - `context.set_result("json_path", result["json_path"])` — propaga para próximo step

**Extração de metadados** (executado dentro de `PhotoMetadata`):
```
FOTO .JPG 
    ↓
ExifUtil.extract_metadata_os()     → File, Path, SizeMb, DateTime
ExifUtil.extract_metadata_image()  → ExifImageWidth/Height, Format, DPI
ExifUtil.extract_metadata_exif()   → ISO, FNumber, DateTimeOriginal, GPS*, LightSource...
XmpUtil.extract_metadata()         → AbsoluteAltitude, RelativeAltitude, GimbalYaw, RtkFlag...
    ↓
Mescla com contexto MRK por sequência (0001, 0002...)
    ↓
MetadataFields.normalize_record_to_keys() → PascalCase
    ↓
_extract_position() → lat, lon, alt, CoordSource (XMP|EXIF|NONE)
    ↓
CustomPhotosFieldsUtil.calculate_all_custom_fields() → GSD, GimbalOffset, YawAlignmentError, etc.
    ↓
Retorna lista de records enriquecidos
```

### Fase 4 — JsonVectorizationStep (Vetorização do JSON)

Step que executa inline (`run_inline()`, sem QgsTask).

1. `should_run(context)`: verifica se `context.json_path` ou `context.get_result("json_path")` existe
2. `run_inline(context)`:
   - Lê JSON v2.0
   - Para cada record, resolve geometria usando `CoordSource` individual
   - Constrói schema: mapeia campos JSON para atributos QGIS
   - Cria `QgsVectorLayer` e adiciona ao projeto
3. `context.set_result("layer", layer)` — propaga layer para callback `on_finished`

### Fase 5 — ReportGenerationStep (Geração de Relatório HTML)

Executado se JSON está disponível e step foi adicionado à pipeline:

1. `should_run(context)`: verifica `context.json_path` ou `context.get_result("json_path")`
2. `create_task(context)`: cria `ReportGenerationTask` que chama `ReportGenerationService.generate_from_json()`
3. `on_success(context, result)`: `context.set_result("report_payload", result)`

**Processo interno do relatório**:
1. `RangeMetadataManager.load()` → carrega config.yaml
2. `JSONUtil.load_records()` → carrega records do JSON v2.0
3. Classifica cada imagem (1-5) via `RangeMetadataManager.classify()`
4. `AggregateAnalyzer.analyze(results)` → estatísticas agregadas
5. `AlertManager.analyze(results, agg)` → alertas do config.yaml
6. `RenderEngine.generate_charts(agg)` → Chart.js
7. `RenderEngine.generate_map_data(results)` → Leaflet
8. `RenderEngine.render_report()` → Jinja2 HTML

---

## Post-Pipeline (Criação da Trilha)

Após o pipeline (callback `_on_pipeline_finished`):
1. Reordena campos alfabeticamente
2. Salva layer de PONTOS em GPKG se configurado
3. Aplica QML de PONTOS se configurado
4. Cria layer de TRILHA:
   - Ordena por `foto`
   - Agrupa por `MrkPath` + `MrkFile`
   - `VectorLayerGeometry.create_line_layer_from_points()`
5. Salva layer de TRILHA em GPKG se configurado
6. Aplica QML de TRILHA se configurado

---

## Contratos do ExecutionContext (comunicação entre steps)

| Resultado (`set_result`) | Setado Por | Consumido Por |
|--------------------------|-----------|---------------|
| `json_path` | PhotoEnrichmentStep | ReverseGeocodeStep, JsonVectorizationStep, ReportGenerationStep |
| `address_data` | ReverseGeocodeStep | `_on_pipeline_finished` (custom callback) |
| `layer` | JsonVectorizationStep | `_on_pipeline_finished` |
| `total_points` | JsonVectorizationStep | `_on_pipeline_finished` |
| `report_payload` | ReportGenerationStep | `_on_pipeline_finished` |

---

## Exemplos Completos

### Exemplo 1 — DroneCoordinates (Plugin com UI)

```python
from core.engine_tasks import (
    PhotoEnrichmentStep, ReverseGeocodeStep, JsonVectorizationStep,
    ReportGenerationStep, AsyncPipelineEngine, ExecutionContext
)

context = ExecutionContext(
    input_path="/photos",
    tool_key=ToolKey.DRONE_COORDINATES,
    files=["/flight.mrk"],
)

steps = [
    PhotoEnrichmentStep(
        source="mrk+photo",
        enable_mrk=True,
        enable_exif=True,
        enable_xmp=True,
        enable_custom_fields=True,
        selected_required_fields=["File", "GpsLatitude", "GpsLongitude", "Iso"],
        selected_custom_fields=["GroundSampleDistanceCm"],
        selected_mrk_fields=["Foto", "MrkFile"],
        recursive=False,
        paths=["/flight.mrk"],
    ),
    # ReverseGeocodeStep lê json_path do context e extrai coordenadas da primeira foto
    ReverseGeocodeStep(),
    JsonVectorizationStep(source="mrk+photo"),
]
if generate_report:
    steps.append(ReportGenerationStep())

engine = AsyncPipelineEngine(steps=steps, context=context, ...)
engine.start()
```

### Exemplo 2 — DroneCoordinatesRunner (Headless)

```python
runner = DroneCoordinatesRunner(iface, tool_key=ToolKey.DRONE_COORDINATES)
runner.run_mrk_file(
    file_path="/flight.mrk",
    on_finished=lambda payload: print("✓", payload),
    on_error=lambda exc: print("✗", exc)
)
# Internamente monta:
# [PhotoEnrichmentStep, ReverseGeocodeStep, JsonVectorizationStep, ReportGenerationStep?]
```

### Exemplo 3 — PhotoVectorizationPlugin (sem MRK)

```python
context = ExecutionContext(
    input_path="/photos",
    tool_key=ToolKey.PHOTO_VECTORIZATION,
)

steps = [
    PhotoEnrichmentStep(
        source="photo",
        enable_mrk=False,
        enable_exif=True,
        enable_xmp=True,
        enable_custom_fields=True,
        recursive=True,
    ),
    ReverseGeocodeStep(),
    JsonVectorizationStep(source="photo"),
]
if generate_report:
    steps.append(ReportGenerationStep())

engine = AsyncPipelineEngine(steps=steps, context=context, ...)
engine.start()
```

---

## Dependências

| Módulo | Caminho | Responsabilidade |
|--------|---------|-----------------|
| **PhotoEnrichmentStep** | core/engine_tasks/PhotoEnrichmentStep.py | Enriquecimento unificado (mrk+photo / photo) |
| **ReverseGeocodeStep** | core/engine_tasks/ReverseGeocodeStep.py | Reverse geocode da primeira foto do JSON |
| **JsonVectorizationStep** | core/engine_tasks/JsonVectorizationStep.py | JSON → QgsVectorLayer (usa CoordSource) |
| **ReportGenerationStep** | core/engine_tasks/ReportGenerationStep.py | JSON → HTML Report |
| **PhotoMetadata** | utils/mrk/PhotoMetadata.py | Orquestrador puro: extrai fotos + mescla com MRK |
| **MrkUtil** | utils/mrk/MrkUtil.py | Parse de arquivos .MRK |
| **ExifUtil** | utils/mrk/ExifUtil.py | Extração EXIF de imagens |
| **XmpUtil** | utils/mrk/XmpUtil.py | Extração XMP de imagens |
| **CustomPhotosFieldsUtil** | utils/mrk/CustomPhotosFieldsUtil.py | Cálculo de campos custom derivados |
| **MetadataFields** | utils/mrk/MetadataFields.py | Catálogo central de campos |
| **JsonToVectorTranslator** | core/translator/JsonToVectorTranslator.py | Traduz JSON → QgsVectorLayer |
| **AsyncPipelineEngine** | core/engine_tasks/AsyncPipelineEngine.py | Orquestrador assíncrono de steps |
| **ExecutionContext** | core/engine_tasks/ExecutionContext.py | Contexto compartilhado (atributos canônicos + results) |
| **ReportGenerationService** | core/services/ReportGenerationService.py | Geração de relatório HTML |
| **DroneCoordinatesRunner** | core/services/DroneCoordinatesRunner.py | Pipeline headless para MRK |
| **VectorLayerGeometry** | utils/vector/VectorLayerGeometry.py | Criação de layers Point/LineString |

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-04-20 | 1.0.0 | Criação inicial |
| 2026-05-13 | 1.1.0 | Documentação completa do sistema de relatórios |
| 2026-05-14 | 2.0.0 | Refatoração unificada: PhotoEnrichmentStep, CoordSource individual |
| 2026-06-03 | 2.1.0 | AlertManager refatorado para motor genérico |
| **2026-07-09** | **3.0.0** | **ExecutionContext canônico + Steps parametrizados**: Steps agora recebem configuração via `__init__` (não via context). Context tem atributos canônicos (`input_path`, `tool_key`, `files`, `json_path`) e `set_result/get_result` para comunicação entre steps. DroneCoordinates, Runner e PhotoVectorizationPlugin 100% convertidos. |
| **2026-07-09** | **3.1.0** | **MRK como agregado opcional**: Coordenadas SEMPRE das fotos (EXIF/XMP). MRK agora é apenas atributos de contexto (MrkFile, MrkPath, MrkFolder, FlightNumber). `_enrich_with_mrk()` não seta mais `CoordSource=MRK` nem `QUALITY_FLAG=OK`. `JsonToVectorTranslator._resolve_geometry()` usa apenas `GpsLatitude/GpsLongitude`. DroneCoordinates tem checkbox "Obter dados MRK". `_resolve_track_group_fields()` tem fallback sem MRK por FolderLevel1. |
| **2026-07-09** | **3.2.0** | **ReverseGeocodeStep integrado ao pipeline**: Pipeline agora executa `PhotoEnrichmentStep → ReverseGeocodeStep → JsonVectorizationStep → (ReportGenerationStep?)`. ReverseGeocodeStep lê json_path do context, extrai coordenadas da primeira foto do JSON, persiste dados de localização no cabeçalho do JSON (`geocode.municipio`, `geocode.state`, etc.) e timestamps `geocode_start`/`geocode_end`. Adicionado `JsonUtil.update_geocode_data()`. |
