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

Os 3 pipelines principais (DroneCoordinates, DroneCoordinatesRunner, PhotoVectorizationPlugin) seguem **exatamente o mesmo fluxo** após o MrkParseStep:

```
DroneCoordinates / Runner:
  MrkParseStep → (PhotoEnrichmentStep?) → JsonVectorizationStep → (ReportGenerationStep?)

PhotoVectorizationPlugin:
  (PhotoEnrichmentStep) → JsonVectorizationStep → (ReportGenerationStep?)
```

**PhotoEnrichmentStep** detecta automaticamente se há dados MRK (json_path no contexto) ou não:
- Com MRK → modo `"mrk+photo"` → cruza pontos MRK com EXIF+XMP+CustomFields
- Sem MRK → modo `"photo_only"` → extrai EXIF+XMP+CustomFields direto das fotos

**JsonVectorizationStep** usa `CoordSource` de cada registro para decidir geometria:
- `CoordSource=MRK` → LAT/LON (coordenadas originais do MRK)
- `CoordSource=XMP/EXIF` → GPS_LATITUDE/GPS_LONGITUDE (coordenadas enriquecidas das fotos)

---

## Entradas

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| paths | list[str] | Sim (MrkParseStep) | Lista de caminhos para arquivos MRK ou pasta raiz |
| recursive | bool | Não | Se True, busca MRKs recursivamente em subpastas (default: True) |
| base_folder | str | Sim (PhotoEnrichmentStep) | Pasta contendo imagens para extração de metadados |
| layer_name | str | Não | Nome da camada vetorial gerada (default: "Cadmus_Vector") |
| extra_fields | dict | Não | Campos customizados a adicionar à camada |
| tool_key | str | Sim | ToolKey para rastreamento de logs |
| iface | QgisInterface | Sim | Interface QGIS para adição de camadas ao projeto |
| selected_required_fields | list[str] | Não | Campos EXIF/XMP selecionados pelo usuário |
| selected_custom_fields | list[str] | Não | Campos custom selecionados pelo usuário |
| selected_mrk_fields | list[str] | Não | Campos MRK selecionados pelo usuário |
| html_output_path | str | Não | Diretório customizado para salvar relatório HTML |
| generate_report | bool | Não | Se True, executa `ReportGenerationStep` após processamento |

---

## Fluxo Completo do Pipeline

### Fase 1 — Inicialização de Contexto

```python
from core.engine_tasks.ExecutionContext import ExecutionContext
from core.engine_tasks.MrkParseStep import MrkParseStep
from core.engine_tasks.PhotoEnrichmentStep import PhotoEnrichmentStep
from core.engine_tasks.JsonVectorizationStep import JsonVectorizationStep
from core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine

context = ExecutionContext()
context.set("paths", ["/path/to/file.mrk"])
context.set("base_folder", "/path/to/photos")
context.set("recursive", False)
context.set("tool_key", ToolKey.DRONE_COORDINATES)
context.set("selected_required_fields", ["File", "GpsLatitude", "GpsLongitude", ...])
context.set("selected_custom_fields", ["GroundSampleDistanceCm", ...])
context.set("selected_mrk_fields", ["Foto", "MrkFile", ...])
context.set("generate_report", True)
context.set("iface", qgis_iface)
```

### Fase 2 — MrkParseStep (Leitura de MRK)

`MrkParseStep` executa `MrkParseTask` que:
- Lê arquivos MRK usando `MrkUtil` (parse de linhas com regex)
- Extrai lista de pontos: `{"foto": int, "lat": float, "lon": float, "alt": float, "flight_number": int, "flight_name": str, "mrk_folder": str, ...}`
- Gera JSON v2.0 via `JsonUtil.build()` com `source="mrk"`
- Salva JSON temporário via `JsonUtil.save()`

**on_success**: `context.set("json_path", path)`, `context.set("source", "mrk")`

### Fase 3 — PhotoEnrichmentStep (Enriquecimento de Metadata)

Step **unificado** que substitui os antigos `PhotoMetadataStep` e `PhotoVectorizationStep`.

**Funcionamento**:

1. Detecta modo automaticamente:
   - `json_path` presente no contexto → modo `"mrk+photo"`
   - `json_path` ausente → modo `"photo_only"`

2. Cria `PhotoEnrichmentTask` que:
   - Extrai pontos da fonte (camada QGIS, JSON ou lista fornecida)
   - Chama `PhotoMetadata.enrich()` (modo mrk+photo) ou `PhotoMetadata.extract_photos_only()` (photo_only)
   - **PhotoMetadata** é orquestrador puro: recebe pontos + pasta → retorna records enriquecidos
   - Aplica filtro de campos selecionados pelo usuário
   - Constrói JSON v2.0 via `JsonUtil.build()`
   - Salva JSON via `ExplorerUtils.create_temp_json()`

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
Retorna lista de records enriquecidos (sem JSON, sem filtro, sem save)
```

**on_success**: `context.set("json_path", path)`, `context.set("source", "mrk+photo"|"photo_only")`

### Fase 4 — JsonVectorizationStep (Vetorização do JSON)

Step **único** e **obrigatório** para todos os pipelines.

Executa inline (`run_inline()`, sem QgsTask) e:
1. Lê JSON v2.0 via `JsonUtil.load_records()`
2. Para cada record, resolve geometria usando `JsonToVectorTranslator._resolve_geometry()`:
   - **Regra**: usa `CoordSource` individual do registro como primary
     - `CoordSource=MRK` → LAT / LON (coordenadas originais do MRK)
     - `CoordSource=XMP` → GPS_LATITUDE / GPS_LONGITUDE (coordenadas das fotos)
     - `CoordSource=EXIF` → GPS_LATITUDE / GPS_LONGITUDE (coordenadas das fotos)
     - `CoordSource=NONE` → fallback para source global do pipeline
3. Constrói schema: mapeia campos JSON para atributos QGIS (`MetadataFields.field.attribute`)
4. Cria `QgsVectorLayer` via `VectorLayerGeometry.create_point_layer_from_dicts()`
5. Adiciona layer ao projeto: `QgsProject.instance().addMapLayer(layer)`

**on_success**: `context.set("layer", layer)`, `context.set("total_points", count)`

### Fase 5 — ReportGenerationStep (Geração de Relatório HTML)

Executado se JSON está disponível e `generate_report=True`:
- `ReportGenerationTask` chama `ReportGenerationService.generate_from_json(json_path)`:
  1. `RangeMetadataManager.load()` → carrega config.yaml (thresholds + alerts)
  2. `JSONUtil.load_records()` → carrega records do JSON v2.0
  3. `[IMGMetadata(record).score() for record in records]` → classifica cada imagem (1-5) via `RangeMetadataManager.classify()`
  4. `AggregateAnalyzer.analyze(results)` → estatísticas agregadas
  5. `AlertManager.analyze(results, agg)` → **motor genérico** que lê definições de alertas do `config.yaml` (seção `alerts:`) e gera alertas CRITICO/ALERTA/INFO sem thresholds hardcoded
  6. `RenderEngine.generate_charts(agg)` → Chart.js pie chart
  7. `RenderEngine.generate_map_data(results)` → Leaflet dados
  8. `RenderEngine.render_report(results, agg, charts, map)` → Jinja2 HTML
  9. `RenderEngine.save_report(html, path)` → salva em `reports/html/report_metadata_*.html`

**on_success**: Abre HTML no navegador, `context.set("report_payload", payload)`

> **Nota:** Alertas são totalmente configuráveis via `resources/reports/config.yaml` (seção `alerts:`). Para adicionar/modificar alertas, edite apenas o YAML — sem necessidade de alterar código Python. Consulte `docs/skills/SKILL_PQI.md` seção 8 para detalhes.


---

## Sistema de Metadados e Campos

### Arquitetura de Campos

O sistema possui 4 fontes de campos de metadados, todas registradas em `utils/mrk/MetadataFields.py`:

| Fonte | Classe | Origem | Nível |
|-------|--------|--------|-------|
| EXIF | `EXIF_FIELDS` | Tags EXIF da imagem (via PIL) | 3 |
| DJI XMP | `DJI_XMP_FIELDS` | Bloco XMP no JPEG (drone-dji:) | 3 |
| Custom | `CUSTOM_FIELDS` | Calculados pelo `CustomPhotosFieldsUtil` | 5 |
| MRK | `MRK_FIELDS` | Arquivo .MRK do drone | 5 |

Cada campo é objeto `Field` com: `normalized`, `core`, `label`, `attribute`, `description`, `level`, `key` (MetadataFieldKey).

### Campos Custom Calculados (`CustomPhotosFieldsUtil`)

- **Individuais**: ShutterLifePct, GroundSampleDistanceCm, TotalHeatIndex, MotionBlurRisk, ExposureValueEv
- **Gimbal/3D**: GimbalOffset, 3DSpeed, Speed3dKmh, YawAlignmentError
- **Qualidade**: RtkEffectivePrecision, IncidenceAngle, PredictedOverlap, OrthorectificationPotential, PhotogrammetryQualityIndex, RtkStabilityScore, CaptureEfficiency
- **Sequência**: TimeSincePrevious, GeodesicDistancePrevious, Distance3dPrevious, AvgVelocityBetweenPhotos, DisplacementDirection
- **Estabilidade**: VerticalStability, SpeedVariationIndex, TrajectorySmoothness, GimbalAngularVelocity
- **Luz**: LightSourceClassification, LightConsistency
- **Cobertura**: CoverageWidth, CoverageHeight, FOverlap
- **Solo**: GroundElevation (AbsoluteAltitude - RelativeAltitude)
- **Flags**: AbruptChangeFlag, IsIdealOverlap, StripId

---

## Contratos do ExecutionContext

| Chave | Setado Por | Consumido Por |
|-------|-----------|---------------|
| `paths` | Plugin | MrkParseStep |
| `recursive` | Plugin | MrkParseStep, PhotoEnrichmentStep |
| `base_folder` | Plugin | PhotoEnrichmentStep |
| `selected_required_fields` | Plugin | PhotoEnrichmentStep |
| `selected_custom_fields` | Plugin | PhotoEnrichmentStep |
| `selected_mrk_fields` | Plugin | PhotoEnrichmentStep |
| `generate_report` | Plugin | Lógica de montagem |
| `tool_key` | Plugin | Todos os steps |
| `iface` | Plugin | ReportGenerationStep |
| `json_path` | MrkParseStep | PhotoEnrichmentStep, JsonVectorizationStep, ReportGenerationStep |
| `source` | MrkParseStep / PhotoEnrichmentStep | JsonVectorizationStep |
| `layer` | JsonVectorizationStep | _on_pipeline_finished |
| `total_points` | JsonVectorizationStep | _on_pipeline_finished |
| `report_payload` | ReportGenerationStep | _on_pipeline_finished |

---

## Post-Pipeline (Criação da Trilha)

Após o pipeline (callback `_on_pipeline_finished`):
1. Reordena campos alfabeticamente (`VectorLayerAttributes.reorder_fields_alphabetically`)
2. Salva layer de PONTOS em GPKG se configurado
3. Aplica QML de PONTOS se configurado
4. Cria layer de TRILHA:
   - Ordena por `foto` (ou campo configurado)
   - Agrupa por `MrkPath` + `MrkFile`
   - `VectorLayerGeometry.create_line_layer_from_points()`
5. Salva layer de TRILHA em GPKG se configurado
6. Aplica QML de TRILHA se configurado

---

## Dependências (Atualizado)

| Módulo | Caminho | Responsabilidade |
|--------|---------|-----------------|
| **MrkParseStep** | core/engine_tasks/MrkParseStep.py | Parse de MRK → JSON v2.0 |
| **PhotoEnrichmentStep** | core/engine_tasks/PhotoEnrichmentStep.py | Enriquecimento unificado (mrk+photo / photo_only) |
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
| **ExecutionContext** | core/engine_tasks/ExecutionContext.py | Contexto compartilhado |
| **ReportGenerationService** | core/services/ReportGenerationService.py | Geração de relatório HTML |
| **DroneCoordinatesRunner** | core/services/DroneCoordinatesRunner.py | Pipeline headless para MRK |
| **VectorLayerGeometry** | utils/vector/VectorLayerGeometry.py | Criação de layers Point/LineString |

---

## Exemplos Completos

### Exemplo 1 — DroneCoordinates (Plugin com UI)

```python
from core.engine_tasks import (
    MrkParseStep, PhotoEnrichmentStep,
    JsonVectorizationStep, ReportGenerationStep,
    AsyncPipelineEngine, ExecutionContext
)

context = ExecutionContext()
context.set("paths", ["/flight.mrk"])
context.set("base_folder", "/photos")
context.set("recursive", False)
context.set("selected_required_fields", ["File", "GpsLatitude", "GpsLongitude", "Iso"])
context.set("selected_custom_fields", ["GroundSampleDistanceCm"])
context.set("selected_mrk_fields", ["Foto", "MrkFile"])
context.set("generate_report", True)
context.set("tool_key", ToolKey.DRONE_COORDINATES)
context.set("iface", iface)

steps = [MrkParseStep()]
if apply_photos:
    steps.append(PhotoEnrichmentStep())
steps.append(JsonVectorizationStep())
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
# [MrkParseStep, PhotoEnrichmentStep?, JsonVectorizationStep, ReportGenerationStep?]
```

### Exemplo 3 — PhotoVectorizationPlugin (sem MRK)

```python
context = ExecutionContext()
context.set("base_folder", "/photos")
context.set("recursive", True)
context.set("generate_report", True)
context.set("tool_key", ToolKey.PHOTO_VECTORIZATION)
context.set("iface", iface)

steps = [PhotoEnrichmentStep(), JsonVectorizationStep()]
if generate_report:
    steps.append(ReportGenerationStep())

engine = AsyncPipelineEngine(steps=steps, context=context, ...)
engine.start()
```

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-04-20 | 1.0.0 | Criação inicial |
| 2026-05-13 | 1.1.0 | Documentação completa do sistema de relatórios |
| **2026-05-14** | **2.0.0** | **Refatoração unificada:** PhotoMetadataStep + PhotoVectorizationStep → PhotoEnrichmentStep. CoordSource individual por registro. JsonVectorizationStep obrigatório em todos os pipelines. Runner alinhado com Plugin. |
| **2026-06-03** | **2.1.0** | **AlertManager refatorado para motor genérico:** Alertas agora lidos do `config.yaml` (seção `alerts:`). Fim dos thresholds hardcoded. Para adicionar/modificar alertas, edite apenas o YAML. |
