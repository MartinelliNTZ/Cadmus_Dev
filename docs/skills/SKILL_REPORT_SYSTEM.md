---
name: report-photogrammetric-system
description: >
  Sistema de relatório fotogramétrico que agrega metadados de imagens (EXIF/XMP/MRK),
  classifica indicadores por níveis (1-5), calcula PQI, gera alertas config-driven e
  renderiza HTML interativo com Chart.js e Leaflet. Use esta skill quando a tarefa
  envolver: adicionar/modificar alertas no config.yaml, estender o template HTML,
  adicionar novo indicador ao relatório, ou depurar o pipeline de agregação.
---

# Sistema de Relatório Fotogramétrico (Report Papeline)

## Resumo Executivo

O **Sistema de Relatório Fotogramétrico** é um pipeline que:

- **Agrega** metadados de milhares de imagens em métricas consolidadas
- **Classifica** cada indicador individual em níveis 1 (crítico) a 5 (excelente) via thresholds do `config.yaml`
- **Calcula** o Photogrammetry Quality Index (PQI) composto para cada imagem
- **Gera alertas** config-driven baseados nas definições do `config.yaml` (seção `alerts:`)
- **Renderiza** HTML interativo com Chart.js (gráficos), Leaflet (mapa) e tabelas dinâmicas

Processa de **centenas a milhares de imagens** em segundos, sem dependência de QGIS para a análise — apenas para renderização final.

---

## Arquitetura

```
IMGMetadata records (JSON v2.0)
    ↓
ReportPapelineManager.analyze(results)
    ├── JsonMetadataManager.compute_indicator_statistics()  → estatísticas por indicador
    ├── FlightAggregator.aggregate()                        → agrupamento por voo
    ├── AggregateAnalyzer.compute_general_info()             → equipamentos, firmware, GPS, datas
    ├── AggregateAnalyzer.compute_top_models()               → distribuição por prefixo filename
    ├── AggregateAnalyzer.compute_shutter_per_camera()       → último shutter count por câmera
    ├── AggregateAnalyzer.compute_light_source_analysis()    → fontes de luz
    ├── AggregateAnalyzer.compute_total_area()               → área total estimada
    ├── AggregateAnalyzer.compute_advanced_metrics()         → métricas avançadas (RTK, gimbal, yaw, etc)
    ├── AggregateAnalyzer.compute_rtk_classification()       → classificação RTK
    ├── AggregateAnalyzer.compute_quality_trends()           → tendências temporais de PQI
    ├── AggregateAnalyzer.compute_strip_analysis()           → análise de strips (faixas)
    ├── AlertManager.compute_recommendations(metrics)        → recomendações operacionais
    └── AlertManager.analyze(results, agg)                   → alertas config-driven
    ↓
RenderEngine (charts + mapa + template Jinja2)
    ↓
report_metadata_*.html
```

## Entradas

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `results` | `List[IMGMetadata]` | Sim | Lista de objetos IMGMetadata com `.score()` já chamado (níveis 1-5 + overall_score) |
| `agg` (para AlertManager) | `Dict[str, Any]` | Sim | Dict agregado com `general_info`, `per_flight`, `per_indicator`, etc. |

### Entrada Mínima Esperada

Cada `IMGMetadata` deve ter:
- `filename`, `flight_id`, `overall_score` (preenchidos por `.score()`)
- `values` (dict `{indicator_key: raw_value}`)
- `levels` (dict `{indicator_key: 1..5}`)
- `level5_values` (dict `{field_key: value}`) para campos de nível 5
- `messages` (dict `{indicator_key: "mensagem textual"}`)
- Métodos `get_indicator(key)` e atributos para campos de diagnóstico (`dewarp_flag`, `alt_mrk`, `absolute_altitude`, `shutter_count`, `equipment_model`, etc.)

---

## Saídas

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `agg` | `Dict[str, Any]` | Dict completo com todas as agregações para o template |
| `charts` | `Dict[str, Any]` | Payload Chart.js (pie, bar, line charts) |
| `map_data` | `Dict[str, Any]` | Snippet Leaflet com marcadores e polilinha |
| `report_html` | `str` | HTML final renderizado por Jinja2 |

### Estrutura do `agg` (Dict de saída)

```
{
  'total_images': int,
  'mean_overall': float,
  'per_indicator': { indicator_key: { 'value_mean', 'value_std', 'value_max', 'value_min', 'value_range', 'dist': {1: N, ...}, 'level_ranges', 'label', 'description', 'threshold_type' } },
  'level_distribution': { 1: N, 2: N, 3: N, 4: N, 5: N },
  'pqi_mean': Optional[float],
  'pqi_level_distribution': { 1: N, ... },
  'pqi_classification': { 'score_display', 'label', 'level' },
  'indicator_catalog': List[Dict],
  'general_info': { 'equipment_models', 'camera_models', 'firmware_versions', 'gps_datum', 'capture_start', 'capture_end', 'total_flights', 'total_flight_time', 'dewarp_zero_count', 'dewarp_status_type', 'dewarp_status_message', 'missing_altitude_count', 'altitude_status_type', 'altitude_status_message', 'last_shutter_per_camera': [...] },
  'top_models': { model_name: { 'count', 'mean_score' } },
  'per_flight': [{ 'flight_id', 'images', 'start', 'end', 'flight_time', 'flight_seconds', 'avg_speed3d_kmh', 'avg_speed3d_ms', 'estimated_area_ha', 'avg_relative_altitude', 'avg_absolute_altitude', 'altitude_solo', 'avg_sensor_temperature', 'avg_iso', 'avg_shutter_speed_text', 'avg_white_balance_cct', 'avg_lrf_target_distance', 'avg_dist3d_previous', 'avg_flight_roll', 'avg_flight_yaw', 'avg_flight_pitch', 'level5_means': { ... } }],
  'temp_chart_series': [{ 'label', 'data': [(x, y)] }],
  'lrf_chart_series': [{ 'label', 'data': [(x, y)] }],
  'iso_chart_series': [{ 'label', 'data': [(x, y)] }],
  'temp_hourly_avg': [{ 'label', 'mean' }],
  'lrf_hourly_avg': [{ 'label', 'mean' }],
  'iso_hourly_avg': [{ 'label', 'mean' }],
  'advanced_analysis': {
    'critical_alerts': [{ 'severity', 'title', 'detail', 'impact', 'action' }],
    'metrics': { 'rtk_diff_age_mean', 'ground_elevation_mean', 'gimbal_offset_mean', 'overlap_below_ideal_pct', 'speed_ms_mean', 'motion_blur_mean', 'light_inconsistent_pct', 'yaw_inconsistent_pct', 'estimated_area_ha', 'light_source_predominant', 'rtk_stability_class', 'pqi_delta', 'morning_pqi_mean', 'midday_pqi_mean' },
    'quality_analysis': { 'strip_rows': [{ 'strip_id', 'images', 'mean_score', 'mean_overlap', 'overlap_below_ideal_pct' }], 'problematic_strips': [...] },
    'recommendations': ['string', ...]
  },
  'alerts': [{ AlertRecord dict }],
  'alerts_count': int,
  'alerts_summary': { category: { 'CRITICO': N, 'ALERTA': N, 'INFO': N, 'total': N } },
  'alerts_severity': { 'CRITICO': N, 'ALERTA': N, 'INFO': N }
}
```

---

## Processamento

### Fase 1 — Classificação Individual (IMGMetadata.score())

Antes da agregação, cada registro JSON é convertido em `IMGMetadata` e classificado:

```python
from .IMGMetadata import IMGMetadata
from .RangeMetadataManager import range_metadata_manager

range_metadata_manager.load()  # carrega config.yaml
results = [IMGMetadata(record).score() for record in records]
```

`.score()` faz:
1. Extrai indicadores via `get_indicator(key)` (suporta aliases, campos derivados como `speed_3d_ms` de km/h, `incidence_angle` de pitch)
2. Classifica cada indicador via `range_metadata_manager.classify(indicator, value)` → retorna (level 1-5, message)
3. Armazena em `self.values`, `self.levels`, `self.messages`, `self.level5_values`
4. Calcula `overall_score` como média aritmética dos níveis de todos os indicadores configurados

### Fase 2 — Orquestração (ReportPapelineManager.analyze())

```python
from .ReportPapelineManager import ReportPapelineManager

agg = ReportPapelineManager.analyze(results)
```

Delega na ordem:
1. `JsonMetadataManager.compute_indicator_statistics(results)` → stats por indicador
2. `statistics.mean(result.overall_score for result in results)` → PQI geral
3. `FlightAggregator.aggregate(results)` → per_flight + séries temporais (temp, LRF, ISO)
4. `AggregateAnalyzer.compute_general_info(results)` → equipamentos, firmware, GPS, datas
5. `AggregateAnalyzer.compute_top_models(results)` → modelos por prefixo filename
6. `AggregateAnalyzer.compute_shutter_per_camera(results)` → último shutter count
7. `AggregateAnalyzer.compute_light_source_analysis(results)` → fontes de luz
8. `AggregateAnalyzer.compute_total_area(per_flight)` → área total
9. `ReportPapelineManager._compute_dewarp_status(results)` → status dewarp
10. `ReportPapelineManager._compute_altitude_status(results)` → status altitude
11. `AggregateAnalyzer.compute_advanced_metrics(results)` → métricas avançadas
12. `AggregateAnalyzer.compute_rtk_classification(results)` → classificação RTK
13. `AggregateAnalyzer.compute_quality_trends(results)` → tendências PQI
14. `AggregateAnalyzer.compute_strip_analysis(results)` → análise de strips
15. `AlertManager.compute_recommendations(advanced_metrics)` → recomendações
16. `AlertManager.analyze(results, agg)` → alertas config-driven

### Fase 3 — Renderização (RenderEngine)

```python
from .RenderEngine import RenderEngine

engine = RenderEngine(tool_key=ToolKey.REPORT_METADATA)
charts = RenderEngine.generate_charts(agg)
map_data = RenderEngine.generate_map_data(results)
html = engine.render_report(results=results, agg=agg, charts=charts, map_data=map_data)
engine.save_report(html, output_path="relatorio.html")
```

---

## Classes e Responsabilidades

| Classe | Caminho | Responsabilidade |
|--------|---------|-----------------|
| **ReportPapelineManager** | `utils/report/ReportPapelineManager.py` | Orquestrador central. Monta o dict `agg` no formato do template. Delega toda análise para classes especializadas. Mantém métodos operacionais `_compute_dewarp_status()` e `_compute_altitude_status()` porque combinam `general_info` e dados brutos. |
| **IMGMetadata** | `utils/report/IMGMetadata.py` | Modelo de imagem + classificador interno. Recebe dict JSON, normaliza para campos canônicos via `MetadataFields`, extrai indicadores com suporte a aliases, classifica via `RangeMetadataManager` e calcula `overall_score`. |
| **RangeMetadataManager** | `utils/report/RangeMetadataManager.py` | Singleton que carrega e serve as configurações do `config.yaml`. Métodos: `load()`, `get_thresholds()`, `get_alerts()`, `get_alert()`, `resolve_indicator_levels()`, `classify()`. Singleton acessível via `range_metadata_manager`. |
| **JsonMetadataManager** | `utils/report/JsonMetadataManager.py` | "Estatístico" — calcula distribuições, médias, desvios, percentis de cada indicador. Gera `per_indicator`, `level_distribution`, `pqi_mean`, `indicator_catalog`. Método principal: `compute_indicator_statistics(results)`. |
| **FlightAggregator** | `utils/report/FlightAggregator.py` | "Agregador de voos" — agrupa imagens por `flight_id`, calcula médias, séries temporais (temp, LRF, ISO), médias por hora. Método principal: `aggregate(results)`. Gera `per_flight`, `temp_chart_series`, `lrf_chart_series`, `iso_chart_series`, `temp_hourly_avg`, `lrf_hourly_avg`, `iso_hourly_avg`. |
| **AggregateAnalyzer** | `utils/report/AggregateAnalyzer.py` | "Analisador agregado" — extrai info geral (equipamentos, firmware, GPS, datas), top models, shutter por câmera, análise de luz, área total, métricas avançadas, classificação RTK, tendências PQI, análise de strips. É a classe que contém TODAS as métricas derivadas. |
| **AlertManager** | `utils/report/AlertManager.py` | "Motor de alertas" — lê definições do `config.yaml` (seção `alerts:`), avalia cada alerta contra resultados e agregados, gera `AlertRecord` com severidade, categoria, detalhe, impacto e ação. Também gera recomendações operacionais via `compute_recommendations()`. |
| **RenderEngine** | `utils/report/RenderEngine.py` | "Renderizador" — carrega template Jinja2, gera charts Chart.js (pie, bar, line), gera mapa Leaflet com pontos e polilinha, renderiza HTML final, salva em disco. Também decide colunas visíveis na tabela de voos. |

---

## Sistema de Alertas (config-driven)

### Fluxo

```
AlertManager.analyze(results, agg)
  ↓
config.yaml (seção alerts:)
  ↓
Para cada alerta habilitado:
  ↓
_evaluate_one_alert(name, cfg, results, agg, per_flight, total_images)
  ↓
Modos: aggregate_field | threshold_levels | threshold_levels_multi | rtk_flag | aggregate_std
  ↓
Se alguma severity_rule "match" → gera AlertRecord
```

### Modos de Alerta

| Modo | Descrição | Uso típico |
|------|-----------|------------|
| `aggregate_field` | Lê campo do `agg`, compara condição (`gt`, `gte`, `eq`, `lt`) | dewarp, altitude |
| `threshold_levels` | Classifica cada foto via `RangeMetadataManager.classify()`, conta por nível | motion_blur, gimbal, overlap, temperatura, velocidade |
| `threshold_levels_multi` | Múltiplos indicadores combinados, qualquer um com % acima do limiar dispara | RTK std (lat+lon+hgt) |
| `rtk_flag` | Contagem de flags RTK fixa/float/single, comparadas a thresholds | qualidade do sinal RTK |
| `aggregate_std` | Desvio padrão de um indicador por voo | variação de GSD |

### Estrutura de um Alerta no config.yaml

```yaml
  motion_blur_risk:
    enabled: true
    mode: threshold_levels
    category: MOTION_BLUR
    indicator_ref: motion_blur_risk        # referencia thresholds.motion_blur_risk
    severity_rules:
      - severity: CRITICO
        when:
          type: any_at_level
          level: 1                          # nivel 1 do threshold = motion_blur > 1.5 pixels
      - severity: ALERTA
        when:
          type: any_at_level
          level: 2                          # nivel 2 = 1.2-1.5 pixels
    title_template: "Motion Blur elevado em {affected_count} foto(s)"
    impact: "Borramento reduz nitidez..."
    action: "Reduzir velocidade de voo..."
    max_photos_list: 20
```

### Tipos de severity_rule

| `type` | Parâmetros | Descrição |
|--------|-----------|-----------|
| `any_at_level` | `level: N` | Se existe **qualquer foto** naquele nível ou pior |
| `pct_at_level_or_worse` | `level: N`, `min_pct: X` | Se **% de fotos** naquele nível ou pior > `min_pct` |
| `fixed_pct_lt` | `value: X` | (rtk_flag) Se % de fotos com RTK Fixa < X |
| `non_fixed_pct_gt` | `value: X` | (rtk_flag) Se % de fotos não-fixas > X |
| `non_fixed_count_gt` | `value: X` | (rtk_flag) Se contagem de fotos não-fixas > X |
| `pct_gt` | `value: X` | (aggregate_field) Se % de imagens afetadas > X |

### AlertRecord

```python
@dataclass
class AlertRecord:
    severity: str                # 'CRITICO' | 'ALERTA' | 'INFO'
    category: str                # Categoria do config.yaml
    title: str                   # Titulo do alerta
    detail: str                  # Descricao com metricas
    impact: str                  # Impacto na qualidade
    action: str                  # Acao recomendada
    affected_count: int = 0
    total_count: int = 0
    affected_pct: float = 0.0
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    flight_ids: List[str] = field(default_factory=list)
    photos: List[str] = field(default_factory=list)
```

---

## Regras

### ✅ Sempre:

- **Novos indicadores**: adicionar threshold em `config.yaml` (seção `thresholds:`) e, se desejar alerta, adicionar entrada em `alerts:` — **zero Python**
- **Alertas**: sempre configurar `enabled: true`, `mode`, `category`, `severity_rules` (pelo menos 1), `title_template`, `impact`, `action`
- **Templates**: usar `{affected_count}` e `{total_count}` em `title_template` para interpolação
- **max_photos_list**: limitar a 20-50 para não poluir o relatório
- **Config**: sempre recarregar `range_metadata_manager.load()` se acabou de editar o YAML
- **Orquestração**: deixar no `ReportPapelineManager` — nunca pular a camada de orquestração
- **IMGMetadata.score()**: chamar para cada record ANTES de passar para o orquestrador
- **RenderEngine.compute_column_visibility()**: o template depende disso para decidir colunas visíveis

### ❌ Nunca:

- **Não hardcodear thresholds de alerta no Python** — tudo no `config.yaml`
- **Não chamar `AlertManager.analyze()` sem config carregado** — `range_metadata_manager.load()` deve ser chamado
- **Não modificar o template HTML sem testar** — Jinja2 não valida variáveis ausentes
- **Não misturar responsabilidades**: `AggregateAnalyzer` calcula métricas; `AlertManager` avalia alertas — não duplicar
- **Não esquecer de chamar `.score()` antes do orquestrador** — `overall_score` fica 0.0 se não classificar

---

## Padrões de Uso

### Padrão 1 — Pipeline Completo (Orquestrado)

```python
from .IMGMetadata import IMGMetadata
from .RangeMetadataManager import range_metadata_manager
from .ReportPapelineManager import ReportPapelineManager
from .RenderEngine import RenderEngine

# 1. Carregar config
range_metadata_manager.load()

# 2. Carregar records do JSON e classificar
records = JsonUtil.load_records(json_path)  # JSON v2.0
results = [IMGMetadata(rec).score() for rec in records]

# 3. Agregar
agg = ReportPapelineManager.analyze(results)

# 4. Renderizar
engine = RenderEngine(tool_key=ToolKey.REPORT_METADATA)
charts = RenderEngine.generate_charts(agg)
map_data = RenderEngine.generate_map_data(results)
html = engine.render_report(results=results, agg=agg, charts=charts, map_data=map_data)
engine.save_report(html, "relatorio.html")
```

### Padrão 2 — Adicionar Alerta via config.yaml (sem Python)

```yaml
# resources/reports/config.yaml
alerts:
  motion_blur_risk:
    enabled: true
    mode: threshold_levels
    category: MOTION_BLUR
    indicator_ref: motion_blur_risk      # referencia threshold existente
    severity_rules:
      - severity: CRITICO
        when:
          type: any_at_level
          level: 1
      - severity: ALERTA
        when:
          type: any_at_level
          level: 2
    title_template: "Motion Blur elevado em {affected_count} foto(s)"
    impact: "Borramento reduz nitidez das imagens..."
    action: "Reduzir velocidade de voo..."
    max_photos_list: 20
```

### Padrão 3 — Adicionar Threshold Novo (sem Python)

```yaml
# resources/reports/config.yaml
thresholds:
  meu_novo_indicador:
    type: lower_better
    levels: [10.0, 5.0, 2.0, 1.0, inf]
    messages:
      - "Nivel 1 - critico"
      - "Nivel 2 - ruim"
      - "Nivel 3 - OK"
      - "Nivel 4 - bom"
      - "Nivel 5 - excelente"
```

### Padrão 4 — Customizar Severidade por Percentual

```yaml
  altitude_missing:
    enabled: true
    mode: aggregate_field
    category: ALTITUDE
    aggregate_field: general_info.missing_altitude_count
    condition:
      type: gt
      value: 0
    severity_rules:
      - severity: CRITICO
        when:
          type: pct_gt
          value: 50.0          # > 50% das imagens → CRITICO
      - severity: ALERTA
        when:
          type: pct_gt
          value: 10.0          # > 10% → ALERTA
      - severity: INFO
        when:
          type: pct_gt
          value: 0.0           # qualquer → INFO
    title_template: "{affected_count} foto(s) sem altitude completa"
    impact: "Afeta consistencia altimetrica..."
    action: "Corrigir captura de Alt..."
```

---

## Casos de Uso

- Quando adicionar **novo indicador** → editar `config.yaml` (thresholds) + opcionalmente `alerts`
- Quando **modificar severidade de alerta** → editar `severity_rules` no YAML
- Quando **adicionar gráfico novo** → modificar `FlightAggregator` (série) + `RenderEngine` (chart) + `template.html`
- Quando **mudar layout do relatório** → editar `template.html` (Jinja2) + manter compatibilidade com keys do `agg`
- Quando **depurar alerta não disparando** → verificar `enabled: true`, `mode` correto, `indicator_ref` existe em thresholds
- Quando **calibragem de thresholds** → ajustar `levels` no YAML — afeta classificação E alertas simultaneamente

---

## Dependências

| Módulo | Caminho | Responsabilidade |
|--------|---------|-----------------|
| **ReportPapelineManager** | `utils/report/ReportPapelineManager.py` | Orquestrador central |
| **IMGMetadata** | `utils/report/IMGMetadata.py` | Modelo + classificador individual |
| **RangeMetadataManager** | `utils/report/RangeMetadataManager.py` | Singleton de thresholds/config |
| **JsonMetadataManager** | `utils/report/JsonMetadataManager.py` | Estatísticas por indicador |
| **FlightAggregator** | `utils/report/FlightAggregator.py` | Agrupamento por voo + séries |
| **AggregateAnalyzer** | `utils/report/AggregateAnalyzer.py` | Métricas avançadas, strips, RTK, tendências, luz |
| **AlertManager** | `utils/report/AlertManager.py` | Motor de alertas config-driven + recomendações |
| **RenderEngine** | `utils/report/RenderEngine.py` | Renderização Jinja2 + charts + mapa |
| **MetadataFields** | `utils/mrk/MetadataFields.py` | Catálogo de campos para normalização |
| **MathUtils** | `utils/MathUtils.py` | Utilitários _to_float, is_zero_value, is_missing_value |
| **FormatUtils** | `utils/FormatUtils.py` | Formatação de duração, datas |
| **ColorUtil** | `utils/ColorUtil.py` | Geração de cores para gráficos |
| **config.yaml** | `resources/reports/config.yaml` | Thresholds + alertas (fonte única da verdade) |
| **template.html** | `resources/reports/template.html` | Template Jinja2 do relatório |

---

## Exemplos Completos

### Exemplo 1 — Pipeline via ReportGenerationService

```python
from core.services.ReportGenerationService import ReportGenerationService

service = ReportGenerationService(tool_key=ToolKey.REPORT_METADATA)
html = service.generate_from_json(json_path="/tmp/metadata_v2.json")
```

Internamente faz:
1. `RangeMetadataManager.load()`
2. `JsonUtil.load_records(json_path)`
3. `[IMGMetadata(r).score() for r in records]`
4. `ReportPapelineManager.analyze(results)`
5. `RenderEngine.generate_charts(agg)`
6. `RenderEngine.generate_map_data(results)`
7. `engine.render_report(...)`

### Exemplo 2 — Apenas Alertas (sem renderizar)

```python
from .RangeMetadataManager import range_metadata_manager
from .AlertManager import AlertManager, AlertRecord

range_metadata_manager.load()
alerts = AlertManager.analyze(results, agg)
for a in alerts:
    print(f"[{a.severity}] {a.category}: {a.title} ({a.affected_count}/{a.total_count})")
```

### Exemplo 3 — Apenas Métricas Avançadas (sem alertas)

```python
from .AggregateAnalyzer import AggregateAnalyzer

metrics = AggregateAnalyzer.compute_advanced_metrics(results)
print(f"Overlap abaixo do ideal: {metrics['overlap_below_ideal_pct']}%")
print(f"Gimbal offset medio: {metrics['gimbal_offset_mean']}°")
print(f"RTK diff age p95: {metrics['rtk_diff_age_p95']}s")
```

### Exemplo 4 — Apenas Estatísticas por Indicador

```python
from .JsonMetadataManager import JsonMetadataManager

stats = JsonMetadataManager.compute_indicator_statistics(results)
for ind, data in stats.get('per_indicator', {}).items():
    print(f"{ind}: media={data['value_mean']}, dist={data['dist']}")
```

### Exemplo 5 — Adicionar Indicador ao config.yaml e Ver no Relatório

1. Editar `resources/reports/config.yaml`:

```yaml
thresholds:
  meu_score:
    type: higher_better
    levels: [10, 30, 50, 70, 90]
    messages:
      - "Score critico"
      - "Score baixo"
      - "Score OK"
      - "Score bom"
      - "Score excelente"
```

2. Garantir que `IMGMetadata.get_indicator("meu_score")` retorna o valor (criar aliases em `MetadataFields` se necessário)

3. Pronto — aparece em `per_indicator`, nos gráficos, na classificação individual

---

## Limitações

- **Alertas dependem do config.yaml**: se o YAML não for carregado ou tiver erro de sintaxe, `get_alerts()` retorna vazio e nenhum alerta é gerado
- **Sem alertas dinâmicos runtime**: não é possível adicionar alertas programaticamente — tudo via YAML
- **max_photos_list**: fotos listadas em alertas são limitadas — se precisar de mais, aumentar no YAML
- **ReportPapelineManager não valida**: se um step lança exceção, o orquestrador relança — não há fallback
- **IMGMetadata.score() é blocking**: classifica todos os indicadores sequencialmente — para grandes datasets (>10k imagens), pode ser lento
- **RenderEngine depende de Jinja2 e Chart.js**: o HTML final requer internet para carregar Chart.js e Leaflet de CDN

---

## Validação

| Critério | Status |
|----------|--------|
| Config-driven? | ✅ Alertas e thresholds 100% via `config.yaml` |
| Reutilizável? | ✅ Pipeline separado em etapas independentes |
| Clara? | ✅ Cada classe tem responsabilidade única definida |
| Testável? | ✅ Cada componente pode ser testado isoladamente |
| Extensível? | ✅ Novo indicador = editar YAML; novo alerta = editar YAML; novo gráfico = editar FlightAggregator + RenderEngine |

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-06-03 | 1.0.0 | Criação via SKILL_FACTORY — lidos: ReportPapelineManager.py, AggregateAnalyzer.py, AlertManager.py, IMGMetadata.py, RangeMetadataManager.py, RenderEngine.py, JsonMetadataManager.py, FlightAggregator.py, config.yaml, template.html |