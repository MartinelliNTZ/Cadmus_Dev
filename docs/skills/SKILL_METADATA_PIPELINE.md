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

## Sistema de Metadados e Campos

### Arquitetura de Campos

O sistema possui 4 fontes de campos de metadados, todas registradas em `utils/mrk/MetadataFields.py`:

| Fonte | Classe | Origem | Nível |
|-------|--------|--------|-------|
| EXIF | `EXIF_FIELDS` | Tags EXIF da imagem (via PIL) | 3 |
| DJI XMP | `DJI_XMP_FIELDS` | Bloco XMP no JPEG (drone-dji:) | 3 |
| Custom | `CUSTOM_FIELDS` | Calculados pelo `CustomPhotosFieldsUtil` | 5 |
| MRK | `MRK_FIELDS` | Arquivo .MRK do drone | 5 |

Cada campo é um objeto `Field` com:
- `normalized`: Nome canônico para o JSON de saída
- `core`: Fonte (exif, xmp_bloco_1, custom, mrk)
- `label`: Rótulo legível
- `attribute`: Nome do atributo na camada vetorial (11 chars no shapefile)
- `description`: Descrição com faixa de valores e referência
- `level`: Nível de importância (3=requerido, 5=custom)
- `key`: Enum `MetadataFieldKey`

### Enum MetadataFieldKey (`core/enum/MetadataFieldKey.py`)

Enum com todas as chaves de campo do sistema:

```python
class MetadataFieldKey(Enum):
    # REQUIRED_FIELDS
    FILE = "File"
    PATH = "Path"
    SIZE_MB = "SizeMb"
    GPS_LATITUDE = "GpsLatitude"
    GPS_LONGITUDE = "GpsLongitude"
    ABSOLUTE_ALTITUDE = "AbsoluteAltitude"
    RELATIVE_ALTITUDE = "RelativeAltitude"
    # ... mais campos EXIF/XMP

    # CUSTOM_FIELDS (calculados)
    GROUND_SAMPLE_DISTANCE_CM = "GroundSampleDistanceCm"
    GIMBAL_OFFSET = "GimbalOffset"
    THREE_D_SPEED = "3DSpeed"
    YAW_ALIGNMENT_ERROR = "YawAlignmentError"
    MOTION_BLUR_RISK = "MotionBlurRisk"
    PHOTOGRAMMETRY_QUALITY_INDEX = "PhotogrammetryQualityIndex"
    GROUND_ELEVATION = "GroundElevation"  # Altitude do solo (AbsAlt - RelAlt)
    # ... mais 40+ campos custom
```

### Campos Custom Calculados (`CustomPhotosFieldsUtil`)

Localizado em `utils/mrk/CustomPhotosFieldsUtil.py`, calcula todos os campos `CUSTOM_FIELDS`:

- **Campos Individuais**: `ShutterLifePct`, `GroundSampleDistanceCm`, `TotalHeatIndex`, `MotionBlurRisk`, `ExposureValueEv`
- **Campos de Gimbal/3D**: `GimbalOffset`, `3DSpeed`, `Speed3dKmh`, `YawAlignmentError`
- **Campos de Qualidade**: `RtkEffectivePrecision`, `IncidenceAngle`, `PredictedOverlap`, `OrthorectificationPotential`, `PhotogrammetryQualityIndex`, `RtkStabilityScore`, `CaptureEfficiency`
- **Campos de Sequência**: `TimeSincePrevious`, `GeodesicDistancePrevious`, `Distance3dPrevious`, `AvgVelocityBetweenPhotos`, `DisplacementDirection`
- **Campos de Estabilidade**: `VerticalStability`, `SpeedVariationIndex`, `TrajectorySmoothness`, `GimbalAngularVelocity`
- **Campos de Luz**: `LightSourceClassification`, `LightConsistency`
- **Campos de Cobertura**: `CoverageWidth`, `CoverageHeight`, `FOverlap`
- **Campos de Solo**: `GroundElevation` (AbsoluteAltitude - RelativeAltitude)
- **Flags**: `AbruptChangeFlag`, `IsIdealOverlap`, `StripId`

### Cálculo do YawAlignmentError

**Bug conhecido e corrigido (2026-05-13):**
No método `_calculate_sequence_fields()`, o `bearing_angle()` estava calculando o azimute da **foto atual para a anterior** (direção inversa do voo). Isso causava `YawAlignmentError ~= 180°` na maioria das imagens, gerando alertas falsos.

**Correção aplicada:**
```python
# direction="prev": bearing from PREVIOUS photo to CURRENT (flight direction)
if direction == "prev":
    dir_displ = bearing_angle(lat_other, lon_other, lat_curr, lon_curr)
else:  # direction="next"
    dir_displ = bearing_angle(lat_curr, lon_curr, lat_other, lon_other)
```

---

## Sistema de Relatórios

### Pipeline do Relatório HTML

O relatório segue 4 estágios:

```
JSON de Metadados (entrada bruta via JSON v2.0 ou legado)
    ↓
[1] JSONUtil.load_records() → Carrega e normaliza registros
    ↓
[2] IMGMetadata.score() → Classifica cada imagem com thresholds do config.yaml
    ↓
[3] AggregateAnalyzer.analyze() → Consolida dados estatísticos e gera alertas
    ↓
[4] RenderEngine.render_report() → Jinja2 + Chart.js + Leaflet → HTML final
    ↓
relatorio.html (saída com tema Dark Premium / Light Classic)
```

### Componentes do Report

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| `RangeMetadataManager` | `utils/report/RangeMetadataManager.py` | Singleton que carrega e gerencia thresholds do config.yaml |
| `IMGMetadata` | `utils/report/IMGMetadata.py` | Modelo de imagem: normaliza campos, calcula score (1-5) |
| `AggregateAnalyzer` | `utils/report/AggregateAnalyzer.py` | Coração da análise: ~50+ métricas, alertas, recomendações |
| `JSONUtil` | `utils/report/JSONUtil.py` | Leitura e normalização de JSONs de metadados (v2.0 e legado) |
| `RenderEngine` | `utils/report/RenderEngine.py` | Renderização HTML com Jinja2 + Chart.js + Leaflet |

### IMGMetadata e Fluxo de Classificação

`IMGMetadata` normaliza todos os campos via `MetadataFields` e implementa o cálculo de score:

1. **Recebe** registro JSON → normaliza para chaves canônicas
2. **Para cada indicador** no `config.yaml`, chama `get_indicator(chave)`:
   - Busca em `level5_values` → `values` → `get_indicator()` (dados brutos)
   - `get_indicator()` tem mapeamentos explícitos para campos derivados:
     ```python
     if norm == "speed_3d_ms": return derive_speed_3d_ms()
     if norm == "gsd_cm": return self._to_float(self._first_value(["GroundSampleDistanceCm", "gsd_cm"]))
     if norm == "sensor_temp_c": return self._to_float(self._first_value(["SensorTemperature", "LensTemperature"]))
     if norm == "incidence_angle": return derive_incidence_angle()
     ```
3. **Classifica** cada valor usando `RangeMetadataManager.classify(indicator, value)` → retorna `(level, message)`
4. **Score geral** = média aritmética de todos os níveis (1-5)

### Configuração de Thresholds (`config.yaml`)

Localizado em `resources/reports/config.yaml`, define as regras de classificação para cada indicador.

#### 4 Tipos de Threshold:

**1. higher_better**: Quanto maior o valor, melhor.
```yaml
photogrammetry_quality_index:
  type: higher_better
  levels: [45, 60, 75, 85, 95]  # Cutoffs
```
Level = `clamp(sum(value >= cut), 1, 5)`. value=80: 80>=45 ✓ + 80>=60 ✓ + 80>=75 ✓ + 80>=85 ✗ = Level 3.

**2. lower_better**: Quanto menor, melhor.
```yaml
gsd_cm:
  type: lower_better
  levels: [15.0, 10.0, 7.0, 5.0, inf]  # Último = inf
```
Level = `clamp(sum(value <= cut), 1, 5)`. value=3.5: 3.5<=15 ✓ + 3.5<=10 ✓ + 3.5<=7 ✓ + 3.5<=5 ✓ = Level 4.

**3. range_best**: Melhor dentro de uma faixa.
```yaml
speed_3d_ms:
  type: range_best
  levels:
    - [0.0, 2.0]
    - [2.0, 4.0]
    - [4.0, 10.0]
```
Level = primeiro range que contém o valor.

**4. categorical**: Mapeamento discreto valor → nível.
```yaml
light_consistency:
  type: categorical
  mapping:
    Unknown: 1
    Inconsistent: 2
    Consistent: 5
```

#### Indicadores configurados (24 indicadores):

- GSD, MotionBlur, PhotogrammetryQualityIndex, OrthorectificationPotential
- RTK Std (lon/lat/hgt), RTK Diff Age, RTK Stability Score
- ShutterLifePct, SensorTemp, Speed3D, IncidenceAngle
- LightConsistency, LightSourceClassification
- PredictedOverlap, VerticalStability, SpeedVariationIndex
- GimbalAngularVelocity, TrajectorySmoothness, CaptureEfficiency
- IsValidSequence (prev/next), AbruptChangeFlag

### AggregateAnalyzer — Métricas e Alertas

O `AggregateAnalyzer.analyze()` gera:

#### Estrutura de Saída:
- `per_indicator`: Dict com estatísticas por indicador (mean, std, dist N1-N5, value_mean, level_ranges)
- `per_flight`: Lista com médias por voo (altitude, velocidade, temperatura, ISO, shutter, etc.)
- `general_info`: Equipamento, firmware, datas, voos, dewarp/altitude status
- `advanced_analysis.metrics`: ~50+ métricas avançadas
- `advanced_analysis.critical_alerts`: Alertas automáticos

#### Alertas Implementados:

| Alerta | Gatilho | Severidade |
|---|---|---|
| **Dewarp desativado** | 100% das imagens com DewarpFlag=0 | CRITICO |
| **Overlap insuficiente** | >30% com overlap < 60% | CRITICO |
| **GPS/RTK ruim** | Thresholds lidos do config.yaml dinamicamente | CRITICO |
| **Yaw inconsistente** | >5% com YawAlignmentError >= 150° | ALERTA |

**Importante:** O alerta RTK lê os thresholds diretamente do config.yaml em vez de valores fixos:
```python
lat_thresh = config.get_thresholds('rtk_std_lat')
lat_cut = lat_thresh['levels'][0]  # N1 cutoff
poor_lat = [v for v in rtk_std_lat_vals if v > float(lat_cut)]
```

**Importante:** O alerta de altitude verifica se AMBAS as fontes (`alt_mrk` AND `absolute_altitude`) estão ausentes, evitando falso positivo quando `source=photo_only` (sem MRK).

### Template HTML

Localizado em `resources/reports/template.html`, usa Jinja2 com:
- **Chart.js** para gráfico de distribuição de níveis (pie chart)
- **Leaflet** para mapa interativo com marcadores
- **2 temas**: Dark Premium / Light Classic (via CSS variables + localStorage)
- **Cards expansíveis** com `<details>/<summary>` em todas as seções

#### Seções do Relatório (8 seções):

1. **Header** — Título, total de imagens, score médio com estrelas ★★★★★, logos, theme switcher
2. **Informações Gerais** — Nomes intuitivos: Modelo do drone, Numero de serie, Versao do firmware, Tempo total de voo, Ultimo disparo por camera
3. **Métricas Avançadas** — GSD medio, Idade do sinal RTK, Estabilidade RTK, Altura de voo media, Altitude do solo media, Desalinhamento do gimbal, Direcao de voo inconsistente, Sobreposicao frontal (abaixo de 60% + media), Velocidade media
4. **Distribuição de Níveis** — Pie chart Chart.js com % N1-N5
5. **Mapa** — Leaflet com marcadores + polyline + fit bounds
6. **Alertas Críticos** — Tabela com severidade colorida
7. **Insights Agronômicos** — Área (ha), inconsistência de luz, fonte de luz
8. **Recomendações** — Lista ordenada automática

#### Convenções de Formatação:

- **Todas as métricas com unidades**: cm, s, %, °, m/s
- **2 casas decimais** para valores numéricos
- **Nomes intuitivos** (sem maiúsculas, termos técnicos traduzidos)
- **Acesso a dicionários no Jinja2**: Usar colchetes `dict['key']`, não ponto `dict.key`

#### Exemplo de métrica formatada:
```html
<th>GSD medio</th>
<td>{% if per_indicator.get('gsd_cm') and per_indicator['gsd_cm'].get('value_mean') is not none %}
    {{ '%.2f'|format(per_indicator['gsd_cm']['value_mean']) }} cm
{% else %} - {% endif %}</td>
```

---

## Problemas Conhecidos e Correções

### 1. GSD zerado nas Métricas Avançadas

**Causa:** `get_indicator("gsd_cm")` não tinha mapeamento para `GroundSampleDistanceCm` (campo real no JSON). O método só resolvia chaves que correspondiam exatamente aos nomes dos thresholds.

**Correção:** Adicionado mapeamento explícito em `IMGMetadata.get_indicator()` (julho 2026):
```python
if norm == "gsd_cm":
    return self._to_float(self._first_value(["GroundSampleDistanceCm", "gsd_cm"]))
```

### 2. RTK diff age zerado

**Causa:** `rtk_diff_age` não estava no `config.yaml`, então `IMGMetadata.score()` não processava o campo e ele não entrava em `r.values`. O `AggregateAnalyzer` buscava em `r.values` e não encontrava.

**Correção:** Adicionado `rtk_diff_age` ao `config.yaml` (threshold lower_better) + fallback `get_indicator()` nas funções de extração do `AggregateAnalyzer`.

### 3. Alerta falso de altitude no photo_only

**Causa:** Usava `or` entre `alt_mrk` e `absolute_altitude`. Quando `source=photo_only`, `alt_mrk` é sempre None, mesmo com `AbsoluteAltitude` presente no JSON.

**Correção:** Mudado para `and`:
```python
if _is_missing_value(r.alt_mrk) and _is_missing_value(r.absolute_altitude):
```

### 4. YawAlignmentError falso (95.59%)

**Causa:** `bearing_angle(lat_curr, lon_curr, lat_other, lon_other)` calculava o azimute da foto **atual para a anterior** — direção inversa do voo. flight_yaw ~80°, displacement_dir ~260°, diferença ~180°.

**Correção:** Invertida ordem dos argumentos do bearing para direction="prev":
```python
if direction == "prev":
    dir_displ = bearing_angle(lat_other, lon_other, lat_curr, lon_curr)
```

### 5. GSD ainda zerado no template

**Causa:** Sintaxe Jinja2 `per_indicator.gsd_cm.value_mean` (dot notation) não funciona para dicionários.

**Correção:** Usar colchetes: `per_indicator['gsd_cm']['value_mean']`

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
- Usar `AggregateAnalyzer.logger` para debug/warning no processo de análise
- Ler thresholds do config.yaml dinamicamente para alertas (não hardcodar valores de cutoff)

### ❌ Nunca:

- Chamar `.start()` em `AsyncPipelineEngine` se já está rodando (`is_running() == True`)
- Escrever logs com `print()` ou `sys.stderr.write()` — usar `LogUtils` sempre
- Hardcodar nomes de campos ou tipos QGIS — usar `MetadataFields` para normalização
- Criar camada sem validação (`if not layer or not layer.isValid()`)
- Gerar relatório sem JSON válido — `ReportGenerationStep.should_run()` valida primeiro
- Ignorar exceções — sempre capturar e logar com `logger.exception(e, code="...")`
- Assumir que geometria GPS existe em imagem — validar antes de criar ponto
- Usar `or` para checagem de altitude quando só uma fonte pode estar disponível (photo_only)
- Assumir que `bearing_angle()` entre fotos consecutivas está na direção correta — verificar se é `anterior→atual` (não `atual→anterior`)

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
| MetadataFields | utils/mrk/MetadataFields.py | Registro de campos EXIF/XMP/MRK/CUSTOM com normalização |
| MetadataFieldKey | core/enum/MetadataFieldKey.py | Enum com todas as chaves de campo do sistema |
| CustomPhotosFieldsUtil | utils/mrk/CustomPhotosFieldsUtil.py | Cálculo de campos custom derivados (GSD, overlap, etc.) |
| IMGMetadata | utils/report/IMGMetadata.py | Modelo de imagem com scoring embedado |
| AggregateAnalyzer | utils/report/AggregateAnalyzer.py | Consolidação estatística e alertas do relatório |
| RangeMetadataManager | utils/report/RangeMetadataManager.py | Singleton de thresholds/config |
| RenderEngine | utils/report/RenderEngine.py | Engine de renderização HTML (Jinja2 + Chart.js + Leaflet) |
| JSONUtil | utils/report/JSONUtil.py | Leitura e normalização de JSONs de metadados |
| RangeMetadataManager | utils/report/RangeMetadataManager.py | Singleton de thresholds/config |
| config.yaml | resources/reports/config.yaml | 24 thresholds de classificação (higher/lower/range/categorical) |
| template.html | resources/reports/template.html | Template Jinja2 do relatório HTML |
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

### Exemplo 3 — Reprocessar relatório de JSON existente

```python
from core.services.ReportGenerationService import ReportGenerationService
from utils.ToolKeys import ToolKey

service = ReportGenerationService(tool_key=ToolKey.REPORT_METADATA)
payload = service.generate_from_json(
    json_path="/path/to/existing/metadata.json",
)
print(f"Relatório gerado: {payload['html_path']}")
```

---

## Limitações

- **JSON intermediário obrigatório**: `ReportGenerationStep` não funciona sem JSON de metadata válido. Se etapa anterior falhar ao gerar JSON, step é pulado (mas sem erro) conforme `should_run()`.
- **GPS em imagem não garantido**: Fotos podem não ter EXIF GPS válido. `PhotoVectorizationTask` filtra e reporta silenciosamente.
- **Type inference ambíguo**: Campos com valores mistos (string "123" vs int 123) enfocam heurística in `PhotoMetadataStep._infer_field_type()`. Lista `_FORCE_STRING_FIELDS` força tipos mas não cobre todos os casos.
- **Reutilização de layer em memória**: Se MRK já foi processado e GPKG existe, runner reutiliza arquivo mas pode usar layer em memória desatualizado se projeto foi modificado.
- **Sem validação de CRS**: Camadas criadas assumem EPSG:4326. Se MRK/fotos estão em CRS diferente, geometria estará incorreta.
- **ReportGenerationService é síncrono**: `generate_from_json()` bloqueia até completar renderização HTML. Para grandes JSONs, pode congelar UI se chamado em thread principal.
- **YawAlignmentError depende de ordenação correta**: O bearing entre fotos consecutivas assume que a ordem cronológica corresponde à ordem de voo. Se fotos estiverem fora de ordem, o cálculo fica incorreto.
- **Campos sem threshold no config.yaml não aparecem em r.values**: O `IMGMetadata.score()` só popula `r.values` com chaves que existem em `thresholds`. Para métricas como `rtk_diff_age` e `rtk_stability_score`, é necessário adicioná-las ao config.yaml.

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
| 2026-05-13 | 1.1.0 | Documentação completa do sistema de relatórios: pipeline, thresholds, IMGMetadata, AggregateAnalyzer, RenderEngine, template HTML, bugs conhecidos e correções |