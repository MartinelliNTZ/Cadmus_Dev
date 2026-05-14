# DroneCoordinates — Fluxo Completo do Sistema

> Documento gerado em 2026-05-14
>
> Mapeia o pipeline completo desde a coleta de dados MRK/Fotos até a geração de relatório HTML e criação de camadas vetoriais (pontos e trilhas).

---

## Sumário

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Classes do Ecossistema](#2-classes-do-ecossistema)
   - 2.1 [Plugins (Entry Points)](#21-plugins-entry-points)
   - 2.2 [Engine Tasks (Pipeline Steps)](#22-engine-tasks-pipeline-steps)
   - 2.3 [Core Tasks (Execução Assíncrona)](#23-core-tasks-execução-assíncrona)
   - 2.4 [Serviços Core](#24-serviços-core)
   - 2.5 [Utils de Metadados](#25-utils-de-metadados)
   - 2.6 [Utils de Vetor](#26-utils-de-vetor)
   - 2.7 [Utils de Relatório](#27-utils-de-relatório)
   - 2.8 [Utils Auxiliares](#28-utils-auxiliares)
   - 2.9 [Enums e Config](#29-enums-e-config)
3. [Fluxo de Dados Detalhado](#3-fluxo-de-dados-detalhado)
   - 3.1 [Pipeline Principal (DroneCoordinates Plugin)](#31-pipeline-principal-dronecoordinates-plugin)
   - 3.2 [Pipeline Runner (DroneCoordinatesRunner)](#32-pipeline-runner-dronecoordinatesrunner)
   - 3.3 [Pipeline PhotoVectorization (sem MRK)](#33-pipeline-photovectorization-sem-mrk)
   - 3.4 [Pipeline ReportMetadata (só relatório)](#34-pipeline-reportmetadata-só-relatório)
4. [Interações entre Classes](#4-interações-entre-classes)
5. [Fluxo de Metadados (EXIF/XMP/MRK/Custom)](#5-fluxo-de-metadados-exifxmpmrkcustom)
6. [Fluxo de Criação de Vetores](#6-fluxo-de-criação-de-vetores)
7. [Fluxo de Relatório HTML](#7-fluxo-de-relatório-html)
8. [Diagrama de Sequência (Texto)](#8-diagrama-de-sequência-texto)
9. [Anexo: Dependências entre Módulos](#9-anexo-dependências-entre-módulos)

---

## 1. Visão Geral da Arquitetura

O sistema DroneCoordinates segue uma **arquitetura de pipeline assíncrono** com 3 camadas principais:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         ENTRY POINTS (Plugins)                          │
│                                                                          │
│   DroneCoordinates (UI)    DroneCoordinatesRunner (sem UI)               │
│   PhotoVectorizationPlugin  ReportMetadataPlugin                         │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ Inicializa
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      PIPELINE ENGINE (Orquestrador)                      │
│                                                                          │
│   AsyncPipelineEngine ────► Steps [MrkParse, PhotoEnrichment,            │
│                              JsonVectorization, ReportGeneration]        │
│                                                                          │
│   ExecutionContext (compartilha dados entre steps)                       │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ Executa
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         TASKS (Execução Real)                            │
│                                                                          │
│   QgsTask → MrkParseTask         → lê MRK → JSON v2.0 (mrk)            │
│   QgsTask → PhotoEnrichmentTask  → enrich fotos + MRK → JSON v2.0      │
│            (modos: mrk+photo / photo_only, unificado)                   │
│   Inline  → JsonVectorizationStep → JSON → QgsVectorLayer              │
│   QgsTask → ReportGenerationTask → gera HTML                            │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ Usam
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         UTILS (Utilitários)                              │
│                                                                          │
│   MrkUtil  ExifUtil  XmpUtil  PhotoMetadata  MetadataFields              │
│   JsonUtil  VectorLayerGeometry  VectorLayerSource  VectorLayerAttributes│
│   CustomPhotosFieldsUtil  IMGMetadata  AggregateAnalyzer  RenderEngine   │
│   JsonToVectorTranslator  PhotoEnrichmentTask/Step                       │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Classes do Ecossistema

### 2.1 Plugins (Entry Points)

#### `DroneCoordinates` (`plugins/DroneCoordinates.py`)
- **Herda**: `BasePluginMTL`
- **ToolKey**: `ToolKey.DRONE_COORDINATES`
- **Função**: Plugin com UI completa para processar arquivos MRK:
  - Selecionar pasta/arquivo MRK
  - Opções: busca recursiva, aplicar metadados de fotos, gerar relatório
  - Seleção granular de campos EXIF, XMP, Custom e MRK
  - Salvamento de pontos e trilhas em GPKG
  - Aplicação de estilos QML
  - Persistência de preferências
- **Pipeline que monta**: `[MrkParseStep]` + opcional `[PhotoMetadataStep]` + `[JsonVectorizationStep]` + opcional `[ReportGenerationStep]`
- **Callback `_on_pipeline_finished`**: Reordena campos, salva GPKG, aplica QML, cria linha de trilha

#### `DroneCoordinatesRunner` (`core/services/DroneCoordinatesRunner.py`)
- **Função**: Executa o pipeline sem UI (drag-drop, automação)
- **Diferença do Plugin**: Não adiciona `JsonVectorizationStep`; o layer já vem do `MrkParseStep` (via lógica antiga do `MrkParseStep._create_point_layer`)
- **Gera**: Pontos + Trilha + Relatório opcional
- **Reutiliza GPKG existente** se já processado

#### `PhotoVectorizationPlugin` (`plugins/PhotoVectorizationPlugin.py`)
- **Função**: Vetoriza pasta de fotos **sem** arquivo MRK
- **Pipeline**: `[PhotoVectorizationStep]` + opcional `[ReportGenerationStep]`
- **ToolKey**: `ToolKey.PHOTO_VECTORIZATION`

#### `ReportMetadataPlugin` (`plugins/ReportMetadataPlugin.py`)
- **Função**: Regenera relatório HTML de JSON existente
- **Pipeline**: Apenas `[ReportGenerationStep]`
- **ToolKey**: `ToolKey.REPORT_METADATA`

### 2.2 Engine Tasks (Pipeline Steps)

#### `BaseStep` (`core/engine_tasks/BaseStep.py`)
- **Tipo**: ABC (Classe Abstrata)
- **Métodos abstratos**: `name()`, `create_task()`, `on_success()`
- **Métodos opcionais**: `should_run()`, `on_error()`, `rollback()`, `run_inline()`
- **Contrato**: Todo step pode:
  - Decidir se deve executar (`should_run`)
  - Criar uma `QgsTask` assíncrona (`create_task`)
  - Opcionalmente executar inline síncrono (`run_inline`)
  - Atualizar `ExecutionContext` após sucesso (`on_success`)

#### `MrkParseStep` (`core/engine_tasks/MrkParseStep.py`)
- **Responsabilidade**: Ler MRKs e gerar JSON base (sem vetorização)
- **Cria**: `MrkParseTask`
- **Contexto que consome**: `paths`, `recursive`, `tool_key`, `extra_fields`
- **Contexto que produz**: `json_path`, `source`, `base_folder`

#### `PhotoMetadataStep` (`core/engine_tasks/PhotoMetadataStep.py`)
- **Responsabilidade**: Enriquecer JSON com metadados de fotos (sem vetorização)
- **Cria**: `PhotoMetadataTask`
- **Contexto que consome**: `base_folder`, `recursive`, `tool_key`, `layer`, `json_path`, `selected_*_fields`
- **Contexto que produz**: `json_path` (atualizado), `source` → "mrk+photo"

#### `JsonVectorizationStep` (`core/engine_tasks/JsonVectorizationStep.py`)
- **Responsabilidade**: Criar camada vetorial a partir do JSON canônico
- **NÃO cria QgsTask**: Executa inline via `run_inline()`
- **Usa**: `JsonToVectorTranslator` para traduzir JSON → `QgsVectorLayer`
- **Contexto que consome**: `json_path`, `points_layer_name`, `source`
- **Contexto que produz**: `layer`, `total_points`

#### `PhotoVectorizationStep` (`core/engine_tasks/PhotoVectorizationStep.py`)
- **Responsabilidade**: Vetorizar fotos sem MRK, extraindo metadados direto
- **Cria**: `PhotoVectorizationTask`
- **Contexto que produz**: `layer`, `json_path`, `total_points`

#### `ReportGenerationStep` (`core/engine_tasks/ReportGenerationStep.py`)
- **Responsabilidade**: Gerar relatório HTML a partir de JSON de metadados
- **Cria**: `ReportGenerationTask`
- **Contexto que consome**: `json_path`, `html_output_path`, `tool_key`
- **Contexto que produz**: `report_payload` (contém `html_path`, `json_path`, etc.)
- **Abre HTML no navegador** após sucesso

#### `ExecutionContext` (`core/engine_tasks/ExecutionContext.py`)
- **Tipo**: Container de estado compartilhado
- **Métodos**: `set(key, value)`, `get(key)`, `has(key)`, `require(keys)`, `add_error()`, `cancel()`
- **Dados que transita**:
  - `paths` → caminhos MRK
  - `json_path` → caminho do JSON v2.0 (evolui a cada step)
  - `layer` → `QgsVectorLayer` gerado
  - `points` → lista de registros
  - `source` → "mrk" | "mrk+photo" | "photo_only"
  - `selected_*_fields` → filtros de campos
  - `tool_key` → rastreabilidade
  - `iface` → interface QGIS (para callbacks UI)

#### `AsyncPipelineEngine` (`core/engine_tasks/AsyncPipelineEngine.py`)
- **Tipo**: Orquestrador de steps
- **Funcionamento**:
  1. Cria `PipelineTask` (QgsTask) no Task Manager do QGIS
  2. Itera sobre steps em sequência
  3. Para cada step: verifica `should_run()`, cria task, adiciona ao Task Manager
  4. Quando task termina: chama `on_success()` do step, avança para próximo
  5. Quando todas tasks terminam: chama `_on_finished` (callback do plugin)
  6. Se erro: chama `_on_error` do step e do engine
- **PipelineTask**: QgsTask "viva" que mantém o engine rodando até o fim

### 2.3 Core Tasks (Execução Assíncrona)

Todas herdam de `BaseTask` e implementam `_run()`.

#### `MrkParseTask` (`core/task/MrkParseTask.py`)
- **Leitura**: Arquivos `.mrk` via `MrkUtil.extract_records()` ou `extract_folder()`
- **Geração**: JSON v2.0 via `JsonUtil.build()` + `JsonUtil.save()`
- **Resultado**: `{"json_path", "source": "mrk", "base_folder", "points"}`
- **Cria `QgsVectorLayer`** de pontos (lógica adicional além do JSON)

#### `PhotoMetadataTask` (`core/task/PhotoMetadataTask.py`)
- **Leitura**: Extrai pontos da camada existente (ou carrega do JSON)
- **Cruzamento**: Chama `PhotoMetadata.enrich()` para cruzar dados MRK + fotos
- **Resultado**: `{"updates": dict, "field_names": list, "json_path": str}`
- **Compatibilidade**: Suporta source_points (lista) e layer_id (QGIS layer)

#### `PhotoVectorizationTask` (`core/task/PhotoVectorizationTask.py`)
- **Vetorização**: Lê fotos de uma pasta, extrai metadata + GPS, cria JSON + layer
- **Resultado**: `{"layer": QgsVectorLayer, "json_path": str, "points": list}`

#### `ReportGenerationTask` (`core/task/ReportGenerationTask.py`)
- **Geração**: Executa `ReportGenerationService.generate_from_json()` em background
- **Resultado**: Payload do relatório

### 2.4 Serviços Core

#### `ReportGenerationService` (`core/services/ReportGenerationService.py`)
- **Responsabilidade**: Serviço síncrono para gerar relatório HTML
- **Pipeline interno**:
  1. Carrega thresholds: `RangeMetadataManager.load()`
  2. Carrega records: `JSONUtil.load_records()`
  3. Classifica: `[IMGMetadata(record).score() for record in records]`
  4. Analisa: `AggregateAnalyzer.analyze(results)`
  5. Renderiza gráficos: `RenderEngine.generate_charts(agg)`
  6. Renderiza mapa: `RenderEngine.generate_map_data(results)`
  7. Renderiza HTML: `RenderEngine.render_report()`
  8. Salva: `RenderEngine.save_report()`

#### `DroneCoordinatesRunner` (`core/services/DroneCoordinatesRunner.py`)
- **Responsabilidade**: Execução headless do pipeline (já detalhado em 2.1)

#### `PhotoFolderVectorizationService` (`core/services/PhotoFolderVectorizationService.py`)
- **Responsabilidade**: Lê pasta de fotos, extrai metadados, gera JSON e camada vetorial
- **Usado por**: `PhotoVectorizationTask`

### 2.5 Utils de Metadados

#### `MrkUtil` (`utils/mrk/MrkUtil.py`)
- **Responsabilidade**: Parsear arquivo `.MRK` de drone
- **Extração**: `extract_records(mrk_path)` → lê cada linha do MRK usando regex
- **Regex**: Captura `foto`, `lat`, `lon`, `alt` de cada linha
- **Campos extra**: FlightNumber, FlightName (do nome do arquivo), FolderLevel1/2 (da estrutura de pastas)
- **Output**: Lista de dicionários com chaves `MetadataFieldKey.*.value`

#### `ExifUtil` (`utils/mrk/ExifUtil.py`)
- **Responsabilidade**: Extrair metadados EXIF de imagens (via PIL/Pillow)
- **3 métodos de extração**:
  - `extract_metadata_os()` → dados do sistema (`File`, `Path`, `SizeMb`, `DateTime`)
  - `extract_metadata_image()` → dimensões/formato (`ExifImageWidth/Height`, `Format`, `DPI`)
  - `extract_metadata_exif()` → tags EXIF da imagem (ISO, FNumber, etc.)
- **Sanitização**: Filtra contra `MetadataFields.sanitize_field_name()`
- **Conversão**: Strings numéricas viram float/int

#### `XmpUtil` (`utils/mrk/XmpUtil.py`)
- **Responsabilidade**: Extrair metadados XMP do bloco DJI no JPEG
- **Extração**: Lê bytes brutos, encontra `<x:xmpmeta>`, faz parse XML
- **Namespaces**: Mapeia namespaces para prefixos (`drone-dji:`, `xmp:`, etc.)
- **Campos DJI**: AbsoluteAltitude, RelativeAltitude, GimbalYaw, FlightYaw, RtkFlag, RtkStd, DewarpFlag, ShutterCount, etc.
- **Sanitização**: Filtra contra `MetadataFields.sanitize_field_name()`

#### `PhotoMetadata` (`utils/mrk/PhotoMetadata.py`)
- **Responsabilidade**: Manager central de metadados de fotos para o fluxo DroneCoordinates
- **Método principal**: `enrich(points, base_folder, ...)` → cruza metadados e retorna JSON path
- **Sub-funções**:
  - `_extract_photo_payload()` → extrai metadados completos de uma foto (OS + PIL + EXIF + XMP + aliases)
  - `_index_photos_complete()` → indexa todas as fotos de uma pasta por sequência
  - `_extract_position()` → extrai GPS (lat/lon/alt) do merged payload (XMP ou EXIF)
  - `_build_mrk_context_by_sequence()` → indexa contexto MRK por número de foto
  - `_merge_mrk_into_dump_records()` → mescla campos MRK no dump por arquivo
  - `_filter_payload()` → filtra campos selecionados pelo usuário
  - `_safe_parse_datetime()` → converte múltiplos formatos de data
  - `_translate_light_source_value()` → traduz código EXIF LightSource para label
- **JSON v2.0**: Gera usando `JsonUtil.build()`
- **Campos calculados**: Invoca `CustomPhotosFieldsUtil.calculate_all_custom_fields()` sobre os records

#### `MetadataFields` (`utils/mrk/MetadataFields.py`)
- **Responsabilidade**: Catálogo central de todos os campos do sistema
- **4 catálogos**: `EXIF_FIELDS`, `DJI_XMP_FIELDS`, `CUSTOM_FIELDS`, `MRK_FIELDS`
- **Cada campo**: Objeto `Field` com `normalized` (nome canônico), `core` (exif/xmp/custom/mrk), `label`, `attribute` (nome no shapefile), `key` (MetadataFieldKey), `level`, `description`
- **Serviços**:
  - `sanitize_field_name()` → normaliza nome bruto para canônico
  - `normalize_record_to_keys()` → mapeia record para chaves MetadataFieldKey
  - `normalize_selected_keys()` → filtra lista de chaves contra allowlist
  - `resolve_output_name()` → converte chave canônica para nome de atributo (máx 9 chars)
  - `get_attribute()` → busca nome do atributo para uma chave
  - `all_fields()` → todos os campos do sistema

#### `CustomPhotosFieldsUtil` (`utils/mrk/CustomPhotosFieldsUtil.py`)
- **Responsabilidade**: Calcular campos custom derivados
- **Campos**: GroundSampleDistance, GimbalOffset, 3DSpeed, YawAlignmentError, MotionBlurRisk, PhotogrammetryQualityIndex, etc.
- **Sequência**: TimeSincePrevious, GeodesicDistance, Direction, StripId
- **Dependência**: Requer dados de pelo menos 2 fotos consecutivas para campos de sequência
- **Bug conhecido**: YawAlignmentError corrigido (inversão do bearing angle)

### 2.6 Utils de Vetor

#### `VectorLayerGeometry` (`utils/vector/VectorLayerGeometry.py`)
- **Responsabilidade**: Transformações geométricas de camadas
- **Métodos usados no fluxo**:
  - `create_point_layer_from_dicts()` → cria camada de pontos a partir de registros
  - `create_line_layer_from_points()` → cria linha(s) a partir de features de pontos (usado no callback `_on_pipeline_finished`)
  - `merge_memory_layers()` → mescla camadas de memória
  - `calculate_point_azimuth()`, `angular_difference_degrees()`, `circular_mean_degrees()`

#### `VectorLayerSource` (`utils/vector/VectorLayerSource.py`)
- **Responsabilidade**: Salvar/carregar vetores em GPKG
- **Métodos**: `save_and_load_layer()`, `load_existing_vector_layer()`

#### `VectorLayerAttributes` (`utils/vector/VectorLayerAttributes.py`)
- **Responsabilidade**: Manipular atributos de camadas
- **Métodos**: `reorder_fields_alphabetically()`

#### `JsonToVectorTranslator` (`core/translator/JsonToVectorTranslator.py`)
- **Responsabilidade**: Traduzir JSON canônico v2.0 para `QgsVectorLayer`
- **Funcionamento**:
  1. Carrega records via `JsonUtil.load_records()`
  2. Resolve geometria conforme source (mrk → LAT/LON, mrk+photo → GPS_LATITUDE/GPS_LONGITUDE)
  3. Constrói schema: mapeia campos JSON para atributos QGIS (respeitando `MetadataFields.field.attribute`)
  4. Chama `VectorLayerGeometry.create_point_layer_from_dicts()` para criar o layer

### 2.7 Utils de Relatório

#### `JSONUtil` (`utils/JsonUtil.py`)
- **Responsabilidade**: Construir, salvar e carregar JSON v2.0
- `build()` → monta estrutura com `schema_version`, `source`, `quality`, `groups`, `records`
- `load_records()` → extrai records do JSON, valida schema_version == "2.0"
- `save()` → escreve JSON em arquivo

#### `IMGMetadata` (`utils/report/IMGMetadata.py`)
- **Responsabilidade**: Modelo de imagem com scoring
- **Funcionamento**:
  1. Normaliza campos via `MetadataFields`
  2. Para cada indicador do config.yaml, chama `get_indicator()`
  3. Classifica usando `RangeMetadataManager.classify()`
  4. Score geral = média aritmética

#### `AggregateAnalyzer` (`utils/report/AggregateAnalyzer.py`)
- **Responsabilidade**: Coração da análise estatística do relatório
- **Gera**: `per_indicator`, `per_flight`, `general_info`, `advanced_analysis.metrics`, `critical_alerts`
- **Alertas**: Dewarp desativado, Overlap insuficiente, GPS/RTK ruim, Yaw inconsistente

#### `RangeMetadataManager` (`utils/report/RangeMetadataManager.py`)
- **Responsabilidade**: Singleton que gerencia thresholds do `config.yaml`
- **Tipos de threshold**: `higher_better`, `lower_better`, `range_best`, `categorical`

#### `RenderEngine` (`utils/report/RenderEngine.py`)
- **Responsabilidade**: Renderização HTML (Jinja2 + Chart.js + Leaflet)
- **Gera**: Gráficos (Chart.js), mapa interativo (Leaflet), HTML final com 8 seções

### 2.8 Utils Auxiliares

#### `ExplorerUtils` (`utils/ExplorerUtils.py`)
- Paths, folders, file operations, abertura em explorer

#### `Preferences` (`utils/Preferences.py`)
- `load_tool_prefs(tool_key)` → carrega preferências do usuário
- `save_tool_prefs(tool_key, prefs)` → salva preferências

#### `JsonUtil` (`utils/JsonUtil.py`)
- Já detalhado em 2.7

#### `QgisMessageUtil` (`utils/QgisMessageUtil.py`)
- Mensagens na UI do QGIS (barra de sucesso, erro, warning)

#### `ProjectUtils` (`utils/ProjectUtils.py`)
- `add_layer_if_missing()`, `remove_layer_from_project()`

#### `LogUtils` (`core/config/LogUtils.py`)
- Logging estruturado com `tool_key` e `class_name`

### 2.9 Enums e Config

#### `MetadataFieldKey` (`core/enum/MetadataFieldKey.py`)
- Enum com TODAS as chaves de campo: `FILE`, `PATH`, `GPS_LATITUDE`, `ABSOLUTE_ALTITUDE`, `GROUND_SAMPLE_DISTANCE_CM`, `MOTION_BLUR_RISK`, etc.

#### `ToolKey` (`utils/ToolKeys.py`)
- Enum: `DRONE_COORDINATES`, `PHOTO_VECTORIZATION`, `REPORT_METADATA`

#### `LightSourceEnum` (`core/enum/LightSourceEnum.py`)
- Mapeia código numérico EXIF LightSource para label textual

---

## 3. Fluxo de Dados Detalhado

### 3.1 Pipeline Principal (DroneCoordinates Plugin)

Este é o fluxo completo quando o usuário usa o plugin `DroneCoordinates`:

```
USUÁRIO (UI DroneCoordinates)
│
├─ 1. Seleciona pasta/arquivo MRK
├─ 2. Configura opções:
│      ├─ [x] Recursivo
│      ├─ [x] Aplicar metadados de fotos
│      └─ [x] Gerar relatório HTML
├─ 3. Seleciona campos EXIF/DJI/Custom/MRK desejados
├─ 4. Configura salvamento GPKG e estilos QML
└─ 5. Clica EXECUTAR
            │
            ▼
DroneCoordinates.execute_tool()
│
├─ Cria ExecutionContext com:
│   paths, base_folder, recursive, extra_fields,
│   selected_required_fields (EXIF + XMP),
│   selected_custom_fields, selected_mrk_fields,
│   generate_report, tool_key, iface, points_layer_name
│
├─ Monta steps:
│   [MrkParseStep, PhotoMetadataStep?, JsonVectorizationStep, ReportGenerationStep?]
│
└─ Inicia AsyncPipelineEngine
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: MrkParseStep                                               │
│                                                                     │
│ 1. Cria MrkParseTask                                                │
│ 2. task._run():                                                     │
│    a. Itera sobre paths                                             │
│    b. Para cada path:                                               │
│       - Se arquivo .mrk: MrkUtil.extract_records(path)              │
│       - Se pasta: MrkUtil.extract_folder(path, recursive)           │
│    c. Monta records com campos:                                     │
│       Foto, Lat, Lon, Alt, MrkFile, MrkPath, MrkFolder,            │
│       FlightNumber, FlightName, FolderLevel1/2, CoordSource="MRK"   │
│    d. JsonUtil.build(records, source="mrk") → JSON v2.0             │
│    e. JsonUtil.save(json_data, temp_file)                           │
│    f. Result: {json_path, source, base_folder, points}              │
│                                                                     │
│ 3. step.on_success():                                               │
│    context.set("json_path", json_path)                              │
│    context.set("source", "mrk")                                     │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: PhotoMetadataStep (se apply_photos=True)                   │
│                                                                     │
│ 1. Cria PhotoMetadataTask                                           │
│ 2. task._run():                                                     │
│    a. Extrai pontos da camada (ou JSON se não tem layer)            │
│    b. Para cada ponto, busca foto correspondente por sequência     │
│    c. Chama PhotoMetadata.enrich(pontos, base_folder, ...):        │
│       i.   Indexa fotos da pasta: PhotoMetadata._index_photos()     │
│       ii.  Para cada foto:                                          │
│            - ExifUtil.extract_metadata_os()                         │
│            - ExifUtil.extract_metadata_image()                      │
│            - ExifUtil.extract_metadata_exif()                       │
│            - XmpUtil.extract_metadata()                             │
│            - Mescla tudo em merged_payload                          │
│            - Extrai posição GPS (_extract_position)                 │
│            - Normaliza campos (MetadataFields)                      │
│            - Aplica filtro de campos selecionados                   │
│       iii. Mescla contexto MRK por sequência (_build_mrk_context)  │
│       iv.  Calcula custom fields (CustomPhotosFieldsUtil)          │
│       v.   JsonUtil.build(records, source="mrk+photo") → JSON v2   │
│       vi.  Salva JSON em arquivo temporário                         │
│    d. Result: {updates, field_names, json_path}                     │
│                                                                     │
│ 3. step.on_success():                                               │
│    context.set("json_path", json_path)                              │
│    context.set("source", "mrk+photo")                               │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: JsonVectorizationStep (síncrono, inline)                    │
│                                                                     │
│ 1. step.run_inline():                                               │
│    a. Lê json_path do contexto                                      │
│    b. Cria JsonToVectorTranslator                                   │
│    c. translator.translate(json_path, layer_name, source):          │
│       i.   JsonUtil.load_records(json_path) → lista de records      │
│       ii.  Para cada record, resolve geometria:                     │
│            - source "mrk" → LAT / LON                              │
│            - source "mrk+photo" → GPS_LATITUDE / GPS_LONGITUDE     │
│       iii. Constrói schema (mapeia campos → QgsField)              │
│       iv.  VectorLayerGeometry.create_point_layer_from_dicts()     │
│    d. QgsProject.instance().addMapLayer(layer)                      │
│    e. context.set("layer", layer)                                   │
│       context.set("total_points", layer.featureCount())              │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: ReportGenerationStep (se generate_report=True)              │
│                                                                     │
│ 1. Verifica should_run(): json_path existe? → sim                   │
│ 2. Cria ReportGenerationTask                                        │
│ 3. task._run():                                                     │
│    a. Carrega records do JSON                                       │
│    b. ReportGenerationService.generate_from_json():                 │
│       i.   RangeMetadataManager.load() → carrega config.yaml       │
│       ii.  [IMGMetadata(record).score() for record in records]     │
│       iii. AggregateAnalyzer.analyze(results)                       │
│       iv.  RenderEngine.generate_charts(agg)                        │
│       v.   RenderEngine.generate_map_data(results)                  │
│       vi.  RenderEngine.render_report(results, agg, charts, map)   │
│       vii. RenderEngine.save_report(html)                           │
│ 4. step.on_success():                                               │
│    a. context.set("report_payload", result)                         │
│    b. Tenta abrir HTML no navegador padrão                          │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                                 ▼
AsyncPipelineEngine._finish_success()
→ Chama DroneCoordinates._on_pipeline_finished(context)
            │
            ▼
DroneCoordinates._on_pipeline_finished()
│
├─ Reordena campos alfabeticamente (VectorLayerAttributes)
├─ Adiciona layer ao QGIS Project
├─ Se salvamento pontos ativado:
│     VectorLayerSource.save_and_load_layer(layer, out_path)
│     Aplica QML se configurado
├─ Cria camada de TRILHA:
│     VectorLayerGeometry.create_line_layer_from_points(
│         features, order_by="foto", group_by=["mrk_path","mrk_file"]
│     )
├─ Se salvamento trilha ativado:
│     VectorLayerSource.save_and_load_layer(line_layer, out_path)
│     Aplica QML se configurado
└─ QgisMessageUtil.bar_success("Concluído!")
```

### 3.2 Pipeline Runner (DroneCoordinatesRunner)

Fluxo headless, sem UI:

```
DroneCoordinatesRunner.run_mrk_file(file_path)
│
├─ Verifica se GPKG já existe → carrega direto (skip pipeline)
├─ Carrega preferências salvas
├─ Cria context e steps: [MrkParseStep] + [PhotoMetadataStep] (opcional)
├─ Executa AsyncPipelineEngine
│
└─ _on_pipeline_finished():
    ├─ Salva pontos em GPKG (auto_points_output_path)
    ├─ Cria trilha (create_line_layer_from_points)
    ├─ Salva trilha em GPKG (auto_track_output_path)
    ├─ Gera relatório se generate_report=True
    └─ QgisMessageUtil.bar_success
```

### 3.3 Pipeline PhotoVectorization (sem MRK)

```
PhotoVectorizationPlugin.execute_tool()
│
├─ Cria context: base_folder, recursive, generate_report, tool_key
├─ Steps: [PhotoVectorizationStep] + [ReportGenerationStep] (opcional)
│
└─ PhotoVectorizationStep:
    ├─ Cria PhotoVectorizationTask
    ├─ Lê fotos da pasta
    ├─ Extrai EXIF + XMP de cada foto
    ├─ Cria pontos a partir de GPS da foto
    ├─ Gera JSON v2.0 (source="photo_only")
    ├─ Cria QgsVectorLayer de pontos
    └─ context.set("layer"), context.set("json_path")
```

### 3.4 Pipeline ReportMetadata (só relatório)

```
ReportMetadataPlugin.execute_tool()
│
├─ Cria context: json_path, tool_key
├─ Steps: [ReportGenerationStep]
│
└─ ReportGenerationStep → ReportGenerationTask
    └─ Gera HTML do JSON existente
```

---

## 4. Interações entre Classes

### 4.1 Mapa de Dependências

```
DroneCoordinates
├── AsyncPipelineEngine
│   ├── BaseStep (ABC)
│   ├── ExecutionContext
│   └── PipelineTask (QgsTask)
│
├── MrkParseStep
│   └── MrkParseTask
│       ├── MrkUtil
│       │   └── MetadataFieldKey (enum)
│       └── JsonUtil
│
├── PhotoMetadataStep
│   └── PhotoMetadataTask
│       ├── PhotoMetadata
│       │   ├── ExifUtil
│       │   │   └── MetadataFields
│       │   ├── XmpUtil
│       │   │   └── MetadataFields
│       │   ├── CustomPhotosFieldsUtil
│       │   │   └── MetadataFields
│       │   ├── MetadataFields
│       │   │   └── Field, MetadataFieldKey
│       │   ├── LightSourceEnum
│       │   └── JsonUtil
│       └── MetadataFields (normalização)
│
├── JsonVectorizationStep
│   └── JsonToVectorTranslator
│       ├── JsonUtil
│       ├── MetadataFields
│       └── VectorLayerGeometry
│           └── LogUtils
│
├── ReportGenerationStep
│   └── ReportGenerationTask
│       └── ReportGenerationService
│           ├── RangeMetadataManager
│           │   └── config.yaml
│           ├── JSONUtil
│           ├── IMGMetadata
│           │   └── MetadataFields
│           ├── AggregateAnalyzer
│           └── RenderEngine
│               └── template.html
│
└── Callback _on_pipeline_finished:
    ├── VectorLayerAttributes
    ├── VectorLayerSource
    ├── VectorLayerGeometry
    │   └── MetadataFields
    └── MetadataFields
```

### 4.2 Contratos de Dados

#### ExecutionContext — Chaves transitadas entre steps

| Chave | Tipo | Setado por | Consumido por |
|-------|------|-----------|---------------|
| `paths` | list[str] | Plugin | MrkParseStep |
| `recursive` | bool | Plugin | MrkParseStep, PhotoMetadataStep |
| `base_folder` | str | Plugin / MrkParseStep | PhotoMetadataStep |
| `extra_fields` | dict\|None | Plugin | MrkParseStep |
| `selected_required_fields` | list[str] | Plugin | PhotoMetadataStep |
| `selected_custom_fields` | list[str] | Plugin | PhotoMetadataStep |
| `selected_mrk_fields` | list[str] | Plugin | PhotoMetadataStep |
| `generate_report` | bool | Plugin | Lógica de montagem |
| `tool_key` | str | Plugin | Todos os steps |
| `iface` | QgisInterface | Plugin | ReportGenerationStep |
| `points_layer_name` | str | Plugin | JsonVectorizationStep |
| `layer_name` | str | Plugin | JsonVectorizationStep |
| `json_path` | str | MrkParseStep | PhotoMetadataStep, JsonVectorizationStep, ReportGenerationStep |
| `source` | str | MrkParseStep / PhotoMetadataStep | JsonVectorizationStep |
| `layer` | QgsVectorLayer | JsonVectorizationStep | _on_pipeline_finished |
| `total_points` | int | JsonVectorizationStep | _on_pipeline_finished |
| `report_payload` | dict | ReportGenerationStep | _on_pipeline_finished |
| `html_output_path` | str\|None | Plugin | ReportGenerationStep |

---

## 5. Fluxo de Metadados (EXIF/XMP/MRK/Custom)

```
ARQUIVO MRK (.mrk)
    ↓
MrkUtil.extract_records()
    ├─ Parse linha → Foto, Lat, Lon, Alt
    ├─ Nome arquivo → FlightNumber, FlightName, DateName
    └─ Estrutura pastas → FolderLevel1/2
    ↓
Records MRK → JsonUtil.build() → JSON v2.0 (source: "mrk")
    ↓
    ↓ (se apply_photos=True)
    ↓
FOTO (arquivo .JPG)
    ↓
PhotoMetadata._extract_photo_payload()
    ├─ ExifUtil.extract_metadata_os()     → File, Path, SizeMb, DateTime
    ├─ ExifUtil.extract_metadata_image()  → Width/Height, Format, DPI
    ├─ ExifUtil.extract_metadata_exif()   → ISO, FNumber, DateTimeOriginal,
    │                                       GPSLatitude, GPSLongitude, LightSource...
    └─ XmpUtil.extract_metadata()         → AbsoluteAltitude, RelativeAltitude,
                                            GimbalYaw, FlightYaw, RtkFlag,
                                            ShutterCount, DewarpFlag, etc.
    ↓
Merged Payload → MetadataFields.normalize_record_to_keys() → PascalCase
    ↓
PhotoMetadata._extract_position() → lat, lon, alt, source (XMP|EXIF|NONE)
    ↓
Mescla contexto MRK por sequência (_build_mrk_context_by_sequence)
    ↓
PhotoMetadata._extract_flight_context() → FlightNumber, FlightName, MrkFile, MrkPath, MrkFolder
    ↓
CustomPhotosFieldsUtil.calculate_all_custom_fields() → GSD, GimbalOffset, etc.
    ↓
JsonUtil.build(records, source="mrk+photo") → JSON v2.0 enriquecido
    ↓
JsonToVectorTranslator.translate() → QgsVectorLayer (camada de pontos)
```

### Hierarquia de Fontes de Metadados (prioridade)

```
1. XMP (DJI)  → AbsoluteAltitude, RelativeAltitude, Gimbal*, Flight*, Rtk*, etc.
2. EXIF        → ISO, FNumber, DateTimeOriginal, GPS*, LightSource, etc.
3. MRK         → Coordenadas originais (se source="mrk"), FlightNumber, FlightName
4. Custom      → GSD, YawAlignmentError, MotionBlurRisk, etc. (calculados)
5. OS          → File, Path, SizeMb (sempre disponível)
```

### Normalização de Campos

```
Campo bruto (ex: "drone-dji:AbsoluteAltitude")
    ↓
MetadataFields.sanitize_field_name()
    ├─ Remove namespace (drone-dji:)
    ├─ Mapeia para nome canônico (ex: "AbsoluteAltitude")
    └─ Retorna None se não autorizado
    ↓
Nome canônico (ex: "AbsoluteAltitude")
    ↓
MetadataFields.resolve_key() → busca em EXIF/XMP/CUSTOM/MRK
    ↓
MetadataFields.all_fields[chave].attribute → nome do atributo QGIS (máx 9 chars)
    ↓
Atributo na camada vetorial (ex: "AbsAlt")
```

---

## 6. Fluxo de Criação de Vetores

### Camada de Pontos

```
JSON v2.0 (records com coordenadas)
    ↓
JsonToVectorTranslator.translate()
    ↓
1. Determina source: "mrk" | "mrk+photo" | "photo_only"
2. Para cada record:
   - Resolve geometria conforme source:
     - mrk:        MetadataFieldKey.LAT / LON
     - mrk+photo:  MetadataFieldKey.GPS_LATITUDE / GPS_LONGITUDE
3. Constrói schema:
   - Mapeia campos JSON → MetadataFields.field.attribute → nome QGIS
   - Infere tipo QVariant (Int, Double, String)
4. VectorLayerGeometry.create_point_layer_from_dicts()
   - Cria QgsVectorLayer memory (EPSG:4326)
   - Adiciona campos
   - Cria QgsFeature com QgsPointXY
   - Commit
```

### Camada de Trilha

```
Camada de Pontos (QgsVectorLayer com features Point)
    ↓
VectorLayerGeometry.create_line_layer_from_points()
    ↓
1. Ordena features por "foto" (ou campo configurado)
2. Agrupa por ["MrkPath", "MrkFile"] → cada grupo vira uma linha
3. Para cada grupo:
   - Extrai coordenadas das geometrias Point
   - Cria QgsGeometry.fromPolylineXY(vertices)
   - Cria feature LineString com atributos do primeiro ponto
4. Retorna QgsVectorLayer memory (LineString)
```

---

## 7. Fluxo de Relatório HTML

```
JSON v2.0 (enriquecido com metadados)
    ↓
ReportGenerationService.generate_from_json()
    ↓
┌──────────────────────────────────────────────────────────────────────┐
│ 1. RangeMetadataManager.load(tool_key)                              │
│     Carrega resources/reports/config.yaml → thresholds               │
│                                                                      │
│ 2. records = JSONUtil.load_records(json_path)                        │
│     Extrai registros do JSON v2.0                                    │
│                                                                      │
│ 3. results = [IMGMetadata(record).score() for record in records]    │
│     Para cada record:                                                │
│     a. Normaliza campos via MetadataFields                           │
│     b. Para cada indicador (24 indicadores do config.yaml):          │
│        - get_indicator(chave) → busca valor no record                │
│        - RangeMetadataManager.classify(indicator, value) → level 1-5│
│     c. Score geral = média aritmética                                │
│                                                                      │
│ 4. agg = AggregateAnalyzer.analyze(results)                          │
│     a. per_indicator → média, desvio, distribuição N1-N5, value_mean│
│     b. per_flight → médias por voo                                   │
│     c. general_info → equipamento, firmware, datas                   │
│     d. advanced_analysis.metrics → 50+ métricas                     │
│     e. critical_alerts → Dewarp, Overlap, RTK, Yaw                  │
│                                                                      │
│ 5. charts = RenderEngine.generate_charts(agg)                       │
│     Gráfico pie da distribuição de níveis (Chart.js)                 │
│                                                                      │
│ 6. map_data = RenderEngine.generate_map_data(results)               │
│     Marcadores + polyline (Leaflet)                                  │
│                                                                      │
│ 7. html = RenderEngine.render_report(results, agg, charts, map)    │
│     Template Jinja2 (resources/reports/template.html)                │
│     Seções: Header, Info Gerais, Métricas Avançadas, Distribuição,  │
│             Mapa, Alertas, Insights Agronômicos, Recomendações      │
│                                                                      │
│ 8. RenderEngine.save_report(html, target_path)                      │
│     Salva em "reports/html/report_metadata_*.html"                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 8. Diagrama de Sequência (Texto)

```
USUÁRIO           DroneCoordinates    AsyncPipelineEngine    MrkParseTask        PhotoMetadataTask      JsonVectorizationStep    ReportGenerationTask
   │                     │                     │                   │                     │                       │                     │
   │   Clica EXECUTAR    │                     │                   │                     │                       │                     │
   │────────────────────►│                     │                   │                     │                       │                     │
   │                     │                     │                   │                     │                       │                     │
   │                     │ Cria ExecutionContext│                   │                     │                       │                     │
   │                     │  (paths, options)    │                   │                     │                       │                     │
   │                     │ Cria steps list      │                   │                     │                       │                     │
   │                     │  [M, PM, JV, RG]     │                   │                     │                       │                     │
   │                     │                      │                   │                     │                       │                     │
   │                     │ engine.start()       │                   │                     │                       │                     │
   │                     │─────────────────────►│                   │                     │                       │                     │
   │                     │                      │                   │                     │                       │                     │
   │                     │                      │ _run_next_step()  │                     │                       │                     │
   │                     │                      │ (index=0)         │                     │                       │                     │
   │                     │                      │ should_run(Mrk)   │                     │                       │                     │
   │                     │                      │→ True             │                     │                       │                     │
   │                     │                      │ create_task()     │                     │                       │                     │
   │                     │                      │───────────────────│─ MrkParseTask() ──►│                       │                     │
   │                     │                      │                   │                     │                       │                     │
   │                     │                      │                   │  MrkUtil.read()    │                       │                     │
   │                     │                      │                   │  JsonUtil.build()  │                       │                     │
   │                     │                      │                   │  JsonUtil.save()   │                       │                     │
   │                     │                      │                   │──────result────────►                      │                     │
   │                     │                      │                   │                     │                       │                     │
   │                     │                      │ on_success(Mrk)   │                     │                       │                     │
   │                     │                      │ ← set(json_path)  │                     │                       │                     │
   │                     │                      │                   │                     │                       │                     │
   │                     │                      │ _run_next_step()  │                     │                       │                     │
   │                     │                      │ (index=1)         │                     │                       │                     │
   │                     │                      │ should_run(Photo) │                     │                       │                     │
   │                     │                      │→ True             │                     │                       │                     │
   │                     │                      │ create_task()     │                     │                       │                     │
   │                     │                      │──────────────────────────────────────────│─ PhotoMetadataTask()─►│                     │
   │                     │                      │                   │                     │                       │                     │
   │                     │                      │                   │                     │  PhotoMetadata.enrich()│                     │
   │                     │                      │                   │                     │  ExifUtil.extract()   │                     │
   │                     │                      │                   │                     │  XmpUtil.extract()    │                     │
   │                     │                      │                   │                     │  CustomFields.calc()  │                     │
   │                     │                      │                   │                     │  JsonUtil.build()     │                     │
   │                     │                      │                   │                     │──────result───────────►                    │
   │                     │                      │                   │                     │                       │                     │
   │                     │                      │ on_success(Photo) │                     │                       │                     │
   │                     │                      │ ← set(json_path)  │                     │                       │                     │
   │                     │                      │                   │                     │                       │                     │
   │                     │                      │ _run_next_step()  │                     │                       │                     │
   │                     │                      │ (index=2)         │                     │                       │                     │
   │                     │                      │ should_run(JsonV) │                     │                       │                     │
