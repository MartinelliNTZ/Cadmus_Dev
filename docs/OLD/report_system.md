# Cadmus Report System - Guia Completo do Especialista
![Cadmus](resources/icons/cadmus.png) ![MTL Agro](resources/icons/mtl_agro.png)

Este documento contém **TODO o sistema de Reports do Cadmus** - de ponta a ponta. Qualquer um que ler se torna especialista. Não mede esforço: arquitetura, fluxos, código fonte, configs, customização, troubleshooting.

## 1. Arquitetura Geral (Diagrama Mermaid)

```mermaid
graph TD
    A[Fotos + MRK] --> B[PhotoMetadata.py<br/>PhotoFolderVectorizationService.py]
    B --> C[JSON dump<br/>cadmus/reports/json/*.json<br/>JSONUtil.load_records()]
    C --> D[IMGMetadata.score()<br/>RangeMetadataManager<br/>config.yaml thresholds]
    D --> E[AggregateAnalyzer.analyze()<br/>Stats/Flights/Alerts/Charts/Map data]
    E --> F[RenderEngine.render_report()<br/>Jinja2 template.html<br/>Chart.js + Leaflet]
    F --> G[HTML<br/>cadmus/reports/html/*.html]
    H[AsyncPipelineEngine<br/>ReportGenerationStep/Task] --> C
    I[Plugins:<br/>DroneCoordinates.py<br/>PhotoVectorizationPlugin.py<br/>ReportMetadataPlugin.py] --> H
    J[ReportGenerationService<br/>generate_from_json()] -.->|Orchestrates| D & E & F
```

## 2. Estrutura de Pastas Temporárias (ExplorerUtils.py)

```
%TEMP%/cadmus/reports/
├── json/          # JSONs de metadata (PhotoMetadata.dump)
│   ├── DPM_*.json (Drone Points Metadata)
│   └── PFM_*.json (Photo Folder Metadata)
└── html/          # Relatórios HTML gerados
    └── report_metadata_*.html
```

**Códigos chave** (ExplorerUtils):
```python
REPORTS_TEMP_FOLDER = 'reports'
REPORTS_JSON_FOLDER = 'json'
REPORTS_HTML_FOLDER = 'html'

def get_temp_folder(tool_key, *subfolders):
    return ensure_temp_subfolder(os.path.join(*subfolders), tool_key)

def build_temp_file_path(*subfolders, prefix, extension='.html', file_stem_hint=''):
    # Ex: cadmus/reports/html/report_metadata_DJI_M3E_001_2024.html
```

## 3. Geração de JSON (PhotoMetadata.py + JSONUtil.py)

**Fluxo**:
1. Extrai EXIF/OS/Image/XMP/MRK/Custom fields
2. CustomPhotosFieldsUtil.calculate_all_custom_fields()
3. Dump para JSON com `groups: {folder: {raw_records: {file.jpg: {...}}}}`
4. JSONUtil.load_records() normaliza com MetadataFields.keys()

**Exemplo JSON structure**:
```json
{
  \"base_folder\": \"/path/to/photos\",
  \"points_total\": 167,
  \"groups\": {
    \"DJI_001_M3E\": {
      \"points\": 167,
      \"raw_records\": {
        \"DJI_0010_W.JPG\": {
          \"File\": \"DJI_0010_W.JPG\",
          \"GpsLatitude\": -10.217,
          \"GsdCm\": 4.2,
          \"AbsoluteAltitude\": 120.5,
          // ... todos MetadataFields + custom
        }
      }
    }
  }
}
```

**Chave PhotoMetadata.enrich()**:
```python
# Extrai + merge MRK + custom + filter selected fields + dump
points = PhotoMetadata.enrich(points, base_folder, recursive, mrk_folder, 
                              selected_required_fields, selected_custom_fields, selected_mrk_fields)
```

## 4. Motor de Scoring (IMGMetadata.py + RangeMetadataManager.py)

**IMGMetadata.score()** - Heart do sistema:
```python
def score(self):
    self.filename = ...
    self.flight_id = derive_flight_id(self.mrk_file)
    # Extrai values/levels para TODOS indicators de config.yaml
    for indicator in config.thresholds.keys():
        value = self.get_indicator(indicator)  # aliases/derived (speed_3d_ms, incidence_angle)
        level, msg = range_metadata_manager.classify(indicator, value)
        self.levels[indicator] = level
        self.messages[indicator] = msg
    self.overall_score = mean(levels)
```

**RangeMetadataManager.classify() tipos**:
- `higher_better`: level = count(v >= thresholds)
- `lower_better`: level = count(v <= thresholds)
- `range_best`: interval match
- `categorical`: mapping[value]

**FULL config.yaml** (resources/reports/config.yaml):
```
thresholds:
  gsd_cm:
    type: lower_better
    levels: [15.0, 10.0, 7.0, 5.0, inf]
    messages: [\"GSD critico\", \"GSD alto\", ...]
  # 25+ indicators: motion_blur_risk, pqi, rtk_std_*, shutter_life_pct, speed_3d_ms (range_best), etc.
```

## 5. Análise Avançada (AggregateAnalyzer.py)

**analyze(results: List[IMGMetadata]) -> agg dict** para template:
- `per_indicator`: mean/std/min/max/dist por indicator
- `level_distribution`: pie chart %
- `per_flight`: table voos (mean_score, duration, level5_means)
- `general_info`: equipment, dates, dewarp/altitude status
- `advanced_analysis`: RTK stats, gimbal, overlap, PQI trends, area estimate, critical_alerts (dewarp100%, overlap<60%, yaw>150°)
- `quality_analysis`: strips com low score/overlap
- `recommendations`: baseadas em thresholds

**Exemplo alerts**:
```python
if dewarp_zero_count == len(results):  # CRITICO
if overlap_below_pct > 30:  # overlap <60%
# etc.
```

## 6. Renderização (RenderEngine.py)

**generate_charts(agg)**: Chart.js payloads (pie levels, bar indicators)
**generate_map_data(results)**: Leaflet markers + polyline dos lat/lon reais
**render_report()**: Jinja2 com:
```python
template.render(
    results=results, agg=agg, charts=charts, map_snippet=leaflet_html,
    total_images, mean_overall, per_indicator, icons...
)
```
**template.html Jinja vars principais**:
- `results[:20]` (tabela top imagens)
- `agg.per_flight` (voos table)
- `per_indicator` (stats table + dist-stack bars)
- `charts.level_pie` / `indicator_bar`
- `map_snippet` (Leaflet full HTML)
- `agg.advanced_analysis.critical_alerts`

**Features template**: Dark/Light theme, responsive, level colors, dist bars com %/ranges hover.

## 7. Orquestração Central (ReportGenerationService.py)

```python
def generate_from_json(self, json_path):
    records = JSONUtil.load_records(json_path)
    results = [IMGMetadata(record).score() for record in records]  # Paralelo!
    agg = AggregateAnalyzer.analyze(results)
    charts = RenderEngine.generate_charts(agg)
    map_data = RenderEngine.generate_map_data(results)
    html = RenderEngine(tool_key).render_report(results, agg, charts, map_data)
    html_path = build_temp_file_path(REPORTS_TEMP_FOLDER, REPORTS_HTML_FOLDER, ...)
    engine.save_report(html, html_path)
    return {'json_path': json_path, 'html_path': html_path, 'total_records': len(records)}
```

## 8. Integração Pipeline QGIS (ReportGenerationStep.py + Task.py)

**Em AsyncPipelineEngine** (DroneCoordinates, PhotoVectorization):
```python
steps = [MrkParseStep(), PhotoMetadataStep(), ReportGenerationStep()]
engine = AsyncPipelineEngine(steps, context)
```
**Step**:
- `should_run()`: if context.has('json_path')
- `create_task()`: ReportGenerationTask(json_path)
- `on_success()`: context.set('report_payload'), open HTML

## 9. Plugins que usam o Sistema

**ReportMetadataPlugin.py** (UI regenerate):
- Lista JSONs em cadmus/reports/json/
- `ReportGenerationService.generate_from_json(selected_json)` 
- Abre HTML auto

**DroneCoordinates.py / PhotoVectorizationPlugin.py**:
- Pipeline com `generate_report` checkbox -> ReportGenerationStep

## 10. Recursos (Templates/Config)

**config.yaml FULL** acima.

**template.html**: HTML5 + Chart.js + Leaflet + CSS vars theme switch. Full código acima.

## 11. Guia de Customização

1. **Novo Indicator**: Adicione em config.yaml:
   ```
   meu_indicator:
     type: higher_better
     levels: [10, 20, 30, 40, 50]
     messages: [...]
   ```
   - Auto detectado em IMGMetadata.score()

2. **Custom Field**: Adicione em CustomPhotosFieldsUtil ou EXIF/XMP/MRK parsers.

3. **Template**: Edite resources/reports/template.html Jinja2 vars disponíveis em RenderEngine.render_report().

4. **Novo Alert**: Em AggregateAnalyzer._severity_entry() + if conditions.

5. **Novo Chart**: RenderEngine.generate_charts() + canvas no template.

## 12. Troubleshooting

| Problema | Causa | Solução |
|----------|-------|---------|
| No JSONs listados | Pasta vazia | Rode DroneCoordinates com generate_report |
| Score sempre 3 | config.yaml ausente | range_metadata_manager.load() |
| Map vazio | Sem lat/lon validos | Cheque GpsLatitude/GpsLongitude !=0 |
| HTML não abre | ExplorerUtils.open_file fail | Manual %TEMP%/cadmus/reports/html/ |
| Pipeline pula ReportStep | No 'json_path' em context | Ative photos/generate_report |

**Logs**: LogUtils em TODAS classes - cheque QGIS log panel.

## 13. Trechos de Código Críticos (Copy-Paste Ready)

**Regen Report**:
```python
from core.services.ReportGenerationService import ReportGenerationService
service = ReportGenerationService('mytool')
payload = service.generate_from_json('/path/to/metadata.json')
print(payload['html_path'])  # Abra manual
```

**Score Manual**:
```python
from utils.report.IMGMetadata import IMGMetadata
from utils.report.RangeMetadataManager import range_metadata_manager
range_metadata_manager.load()
img = IMGMetadata({'GsdCm': 3.2, 'RtkStdLon': 0.005})
img.score()
print(img.overall_score, img.levels)
```

**Análise Completa**:
```python
from utils.report import AggregateAnalyzer, JSONUtil
records = JSONUtil.load_records('json_path.json')
results = [IMGMetadata(r).score() for r in records]
agg = AggregateAnalyzer.analyze(results)
print(agg['per_flight'], agg['advanced_analysis']['critical_alerts'])
```

**Sistema completo entendido. Fim do guia.**

*Gerado por BLACKBOXAI - Todos os detalhes do sistema incluídos.*

