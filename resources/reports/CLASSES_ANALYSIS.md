# Análise de Classes - `utils/report`

## Visão Geral

O módulo `utils/report` é o núcleo do sistema de relatórios fotogramétricos. Ele contém **7 classes** que trabalham em conjunto para: carregar metadados de imagens, classificar indicadores de qualidade, consolidar resultados, gerar alertas e renderizar o relatório HTML final.

### Arquitetura Atual (3 Especialistas + 1 Orquestrador + 2 Utilitários + 1 Renderizador)

```
JSON (metadata v2.0)
  │
  ▼
JsonMetadataManager.load_records()    ← ESTATÍSTICO PURO
  │ List[Dict]                           Só calcula distribuições sobre atributos
  ▼
IMGMetadata.__init__(record) → IMGMetadata.score()
  │ List[IMGMetadata] com levels, messages, overall_score
  ▼
┌──────────────────────────────────────────────────────────────┐
│                    AggregateAnalyzer.analyze()                │
│                     ORQUESTRADOR CENTRAL                      │
│  Chama 3 especialistas + adiciona camada operacional final   │
│                                                              │
│  1. JsonMetadataManager.compute_indicator_statistics()       │
│     → per_indicator, level_distribution, pqi_*              │
│                                                              │
│  2. FlightAggregator().aggregate()                           │
│     → per_flight, flight_level5_columns, séries temporais   │
│                                                              │
│  3. (lógica própria) info geral, métricas avançadas,         │
│     status operacionais, recomendações                       │
│                                                              │
│  4. AlertManager.analyze()                                   │
│     → alerts, alerts_count, alerts_summary                  │
└──────────────────────────────────────────────────────────────┘
  │ agg completo
  ▼
RenderEngine.generate_charts(agg)
RenderEngine.generate_map_data(results)
RenderEngine.compute_column_visibility(agg)
  │
  ▼
RenderEngine.render_report(results, agg, charts, map_data)
  │
  ▼
template.html (Jinja2)
  │
  ▼
HTML final → RenderEngine.save_report()
```

---

## 1. `JsonMetadataManager` (O Estatístico)

**Arquivo:** `utils/report/JsonMetadataManager.py`

**Responsabilidade:** **Estatístico puro.** Processa N fichas (IMGMetadata) e devolve distribuições sobre atributos. Não sabe nada sobre voos, equipamentos, gráficos, alertas ou relatórios. Só sabe calcular: média, desvio, mínimo, máximo, distribuição por nível, séries temporais.

> 🎯 **Analogia:** Alguém recebe 5.000 fichas, cada uma com 40 atributos medidos, e responde: "para o atributo GSD, a média foi 3.2, o desvio foi 0.4, 80% das fotos ficaram no nível 4." Ele não sabe nada sobre voos, não sabe sobre equipamento, não sabe sobre gráficos. Ele só sabe calcular distribuições sobre atributos.

### Carga de Dados (APENAS v2.0, SEM legado)

| Método | Tipo | Descrição |
|--------|------|-----------|
| `load_json_file(json_path, tool_key)` | `@staticmethod` | Lê um arquivo JSON do disco e retorna o objeto desserializado. |
| `load_timestamps(json_path, tool_key)` | `@staticmethod` | Carrega apenas o bloco de timestamps do JSON v2.0 schema. |
| `load_json_metadata(json_path, tool_key)` | `@staticmethod` | Carrega metadados do JSON raiz: título, logotipo, generated_at. |
| `compute_processing_summary(timestamps)` | `@staticmethod` | Calcula tempos de processamento a partir do dicionário de timestamps. |
| `load_records(json_path, tool_key)` | `@staticmethod` | Carrega registros **exclusivamente via JSON v2.0**. Não suporta formatos legados. |

### Métodos Estatísticos Puros

| Método | Tipo | Descrição |
|--------|------|-----------|
| `compute_indicator_statistics(results)` | `@staticmethod` | **Método principal.** Calcula estatísticas PURAS sobre os indicadores. Retorna `per_indicator`, `level_distribution`, `pqi_mean`, `pqi_level_distribution`, `pqi_classification`, `indicator_catalog`. |
| `_is_zero_or_none(val)` | `@staticmethod` (privado) | Verifica se valor é None, zero ou vazio. |
| `_resolve_field_meta(indicator)` | `@staticmethod` (privado) | Resolve metadado de um indicador com fallback de aliases. |
| `_numeric_values_from_keys(results, keys)` | `@staticmethod` (privado) | Extrai série numérica de chaves candidatas. |
| `_first_numeric_from_result(r, keys)` | `@staticmethod` (privado) | Retorna primeiro valor numérico disponível em um resultado. |
| `_series_by_time(results, keys)` | `@staticmethod` (privado) | Monta série temporal ordenada de valores numéricos por data de captura. |
| `_level_ranges_from_threshold(indicator)` | `@staticmethod` (privado) | Traduz thresholds configurados para descrições textuais por nível (N1..N5). |

### Fluxo de Uso do Estatístico
```
JsonMetadataManager.compute_indicator_statistics(results)
  ├── Coleta todos os indicadores dos results
  ├── Para cada indicador:
  │     ├── levels dos resultados
  │     ├── field_meta via _resolve_field_meta
  │     ├── valores numéricos brutos
  │     ├── Estatísticas: mean, std, min, max, range, dist
  │     └── level_ranges via _level_ranges_from_threshold
  ├── PQI: valores, níveis, classificação
  ├── indicator_catalog
  └── Retorna dict com per_indicator, level_distribution,
      pqi_mean, pqi_level_distribution, pqi_classification,
      indicator_catalog
```

---

## 2. `FlightAggregator` (O Coordenador de Missão) — **NOVA**

**Arquivo:** `utils/report/FlightAggregator.py`

**Responsabilidade:** **Coordenador de missão.** Agrupa imagens por flight_id e produz um relatório de cada sortida. Ele tem uma lista de todos os voos e quer saber:

> - No voo F001, qual foi a velocidade média?
> - Quanto tempo durou?
> - Qual área foi coberta?
> - A temperatura do sensor subiu ao longo do voo?

Não sabe nada sobre thresholds, níveis, indicadores, alertas ou gráficos. Só sabe agrupar por voo e calcular métricas operacionais por sortida.

### Constantes de Classe

| Constante | Valor | Descrição |
|-----------|-------|-----------|
| `ROUND_DECIMALS` | `2` | Casas decimais para arredondamento das métricas de voo |
| `IGNORE_LEVEL5_LABELS` | `set` | Labels de nível 5 ignorados nas médias por voo |
| `EXCLUDE_KEYWORDS` | `set` | Palavras-chave para excluir campos de data/hora/GPS |

### Métodos

| Método | Tipo | Descrição |
|--------|------|-----------|
| `aggregate(results)` | instance | **Método principal.** Agrupa imagens por voo e produz métricas operacionais de cada sortida. Retorna `per_flight`, `flight_level5_columns`, `temp_chart_series`, `lrf_chart_series`, `temp_hourly_avg`, `lrf_hourly_avg`. |
| `_build_flight_row(flight_id, items, level5_fields)` | instance (privado) | Constrói uma linha de resumo para um único voo (velocidade, temperatura, LRF, altitude, ISO, WB, shutter, atitude, área). |
| `_estimate_area(items, level5_means)` | `@staticmethod` (privado) | Calcula área estimada coberta pelo voo em hectares. Fórmula: `(largura_px × gsd_m) × (altura_px × gsd_m) × (1-overlap)² × qtd_fotos / 10000`. |
| `_build_chart_series(flights, keys)` | `@staticmethod` (privado) | Monta série temporal de valores por voo para gráfico (temperatura, LRF). |
| `_build_hourly_averages(results)` | `@staticmethod` (privado) | Calcula médias por hora do dia (0h-23h) para temperatura e LRF. |
| `_get_numeric(r, keys)` | `@staticmethod` (privado) | Extrai o primeiro valor numérico de um resultado para as chaves informadas. |
| `_is_excluded_field(field_key, field_label)` | `@staticmethod` (privado) | Define se um campo deve ser ignorado no agrupamento por voo (ex: data/hora/GPS). |
| `_ignored_level5_keys()` | `@staticmethod` (privado) | Retorna chaves level 5 ignoradas nas médias por voo. |

### O que foi extraído do AggregateAnalyzer

| Funcionalidade | De | Para |
|----------------|----|------|
| Agrupamento por flight_id | `AggregateAnalyzer.analyze()` (linhas 245-488) | `FlightAggregator.aggregate()` |
| Cálculo de nível 5 columns | `AggregateAnalyzer.analyze()` (linhas 249-278) | `FlightAggregator.aggregate()` |
| Construção de linha de voo | `AggregateAnalyzer.analyze()` (linhas 280-486) | `FlightAggregator._build_flight_row()` |
| Cálculo de área (hectares) | `AggregateAnalyzer.analyze()` (linhas 397-417) | `FlightAggregator._estimate_area()` |
| Séries de temperatura/LRF | `AggregateAnalyzer.analyze()` (linhas 490-518) | `FlightAggregator._build_chart_series()` |
| Médias por hora do dia | `AggregateAnalyzer.analyze()` (linhas 520-551) | `FlightAggregator._build_hourly_averages()` |
| `_first_numeric_from_result()` | duplicado em AggregateAnalyzer | `FlightAggregator._get_numeric()` |
| `_is_excluded_flight_field()` | `AggregateAnalyzer` | `FlightAggregator._is_excluded_field()` |
| `_ignored_level5_keys_from_metadata_fields()` | `AggregateAnalyzer` | `FlightAggregator._ignored_level5_keys()` |

### Resultado do `aggregate()`

```python
{
    'per_flight': [
        {
            'flight_id': str,           # "F001"
            'images': int,               # 120
            'mean_score': float,         # 4.2
            'start': str,                # "2024-01-15 08:30:00"
            'end': str,                  # "2024-01-15 09:15:00"
            'flight_seconds': int,       # 2700
            'flight_time': str,          # "45m 00s"
            'avg_speed3d_kmh': float,    # 36.5
            'avg_speed3d_ms': float,     # 10.14
            'avg_sensor_temperature': float,  # 42.3
            'avg_lrf_target_distance': float, # 120.5
            'avg_relative_altitude': float,   # 100.0
            'avg_absolute_altitude': float,   # 850.0
            'altitude_solo': float,      # 750.0
            'avg_iso': float,            # 200
            'avg_white_balance_cct': float,   # 5500
            'avg_shutter_speed_text': str,    # "1/1000"
            'shutter_speed_range_text': str,
            'avg_dist3d_previous': float,
            'avg_flight_roll': float,
            'avg_flight_yaw': float,
            'avg_flight_pitch': float,
            'estimated_area_ha': float,   # 15.3
            'level5_means': {
                'GroundSampleDistanceCm': 3.2,
                'MotionBlurRisk': 0.15,
                ...
            }
        }
    ],
    'flight_level5_columns': [{'key': str, 'label': str}],
    'temp_chart_series': [{'label': flight_id, 'data': [{'x', 'y'}]}],
    'lrf_chart_series': [{'label': flight_id, 'data': [{'x', 'y'}]}],
    'temp_hourly_avg': [{'hour', 'label', 'mean', 'count'}],
    'lrf_hourly_avg': [{'hour', 'label', 'mean', 'count'}]
}
```

---

## 3. `RangeMetadataManager`

**Arquivo:** `utils/report/RangeMetadataManager.py`

**Responsabilidade:** Fonte única (Singleton) para configuração de thresholds e classificação de níveis (1 a 5) dos indicadores. Carrega do arquivo YAML `resources/reports/config.yaml`.

*(sem alterações - esta classe não foi modificada)*

---

## 4. `IMGMetadata`

**Arquivo:** `utils/report/IMGMetadata.py`

**Responsabilidade:** Modelo principal de imagem que encapsula todos os campos de MetadataFields, calcula scores, níveis e mensagens para cada indicador. É o resultado do processamento de cada foto.

*(sem alterações - esta classe não foi modificada)*

---

## 5. `AggregateAnalyzer` (O Orquestrador)

**Arquivo:** `utils/report/AggregateAnalyzer.py`

**Responsabilidade:** **Orquestrador central.** Já não faz mais trabalho pesado — coordena os 3 especialistas:
- `JsonMetadataManager` → estatística pura
- `FlightAggregator` → agrupamento por voo
- `AlertManager` → alertas de qualidade

E adiciona a camada operacional final do relatório.

### O que foi REMOVIDO do AggregateAnalyzer

| Funcionalidade | Destino |
|----------------|---------|
| `_numeric_values_from_keys()` | `JsonMetadataManager._numeric_values_from_keys()` |
| `_resolve_field_meta()` | `JsonMetadataManager._resolve_field_meta()` |
| `_level_ranges_from_threshold()` | `JsonMetadataManager._level_ranges_from_threshold()` |
| `_is_zero_or_none()` | `JsonMetadataManager._is_zero_or_none()` |
| `_severity_entry()` | Removido (AlertManager.to_severity_entry() já cobria) |
| Lógica de `per_indicator` | `JsonMetadataManager.compute_indicator_statistics()` |
| Lógica de `pqi_classification` | `JsonMetadataManager.compute_indicator_statistics()` |
| Lógica de `indicator_catalog` | `JsonMetadataManager.compute_indicator_statistics()` |
| Lógica de `level_distribution` | `JsonMetadataManager.compute_indicator_statistics()` |
| `FIELD_FALLBACKS` | `JsonMetadataManager._resolve_field_meta()` |
| Agrupamento por voo (~150 lines) | `FlightAggregator.aggregate()` |
| `_debug_flight_area()` | `FlightAggregator` (removido) |
| `_is_excluded_flight_field()` | `FlightAggregator._is_excluded_field()` |
| `_ignored_level5_keys_from_metadata_fields()` | `FlightAggregator._ignored_level5_keys()` |

### O que PERMANECE no AggregateAnalyzer

| Funcionalidade | Justificativa |
|----------------|---------------|
| `analyze(results)` | Método orquestrador principal |
| `_first_numeric_from_result(r, keys)` | Usado internamente para strip analysis |
| `_numeric_from_flight_values(results, keys)` | Método auxiliar para métricas avançadas |
| `_resolve_light_source_label(result)` | Lógica específica de classificação de luz |
| `_to_pt_light_source_label(label)` | Tradução operacional |
| Informações gerais (equipamentos, firmware, GPS, datas) | Operacional |
| Status operacionais (dewarp, altitude, shutter count) | Operacional |
| Métricas avançadas (RTK, Gimbal, Yaw, Overlap, Luz) | Operacional |
| Recomendações | Operacional |
| Strip analysis | Operacional |

### Fluxo do `analyze()` (reduzido de 961 para ~350 lines)

```
1. indicator_stats = JsonMetadataManager.compute_indicator_statistics(results)
2. mean_overall = média dos overall_score
3. flight_data = FlightAggregator().aggregate(results)
4. Coleta info de equipamentos, firmware, GPS, datas
5. Monta agg com indicator_stats + flight_data
6. Calcula top_models
7. Flight totals (total_flights, total_flight_time)
8. Status dewarp, altitude, shutter count
9. Métricas avançadas (overlap, yaw, RTK, gimbal, size_mb, motion_blur, luz)
10. PQI trends, strip analysis
11. Recomendações
12. AlertManager.analyze(results, agg) → alerts
13. Retorna agg
```

### Constantes

| Constante | Descrição |
|-----------|-----------|
| `FLIGHT_STATS_ROUND_DECIMALS` | Arredondamento padrão (2) |
| `SPEED_RECOMMENDED_MIN_MS` | Velocidade mínima recomendada (5.0 m/s) |
| `SPEED_RECOMMENDED_MAX_MS` | Velocidade máxima recomendada (10.0 m/s) |
| `IDEAL_OVERLAP_PCT` | Sobreposição ideal (60%) |
| `LIGHT_SOURCE_PT_LABELS` | Mapeamento de labels de luz para português |

---

## 6. `AlertManager`

**Arquivo:** `utils/report/AlertManager.py`

**Responsabilidade:** Centraliza a geração de todos os alertas de qualidade do relatório fotogramétrico.

*(sem alterações - esta classe não foi modificada)*

---

## 7. `RenderEngine`

**Arquivo:** `utils/report/RenderEngine.py`

**Responsabilidade:** Renderiza o HTML final do relatório usando Jinja2, gera payloads de gráficos Chart.js, dados de mapa Leaflet e decide a visibilidade de colunas na tabela.

*(sem alterações - esta classe não foi modificada)*

---

## Resumo das Mudanças

| Classe | Status | Lines Antes | Lines Depois | Δ |
|--------|--------|-------------|--------------|---|
| `JSONUtil.py` | Renomeado → `JsonMetadataManager.py` | ~180 | ~580 | +400 (recebeu métodos estatísticos) |
| `JsonMetadataManager.py` | **NOVO NOME** | — | 580 | Novo |
| `FlightAggregator.py` | **NOVA CLASSE** | — | ~300 | Nova |
| `AggregateAnalyzer.py` | Refatorado (perdeu ~600 lines) | ~960 | ~350 | -610 |
| `AlertManager.py` | Intocado | — | — | 0 |
| `RenderEngine.py` | Intocado | — | — | 0 |
| `IMGMetadata.py` | Intocado | — | — | 0 |
| `RangeMetadataManager.py` | Intocado | — | — | 0 |
| `__init__.py` | Atualizado (add FlightAggregator) | — | — | +1 linha |

### Diagrama de Responsabilidades

```
                     ┌─────────────────────────┐
                     │   AggregateAnalyzer     │
                     │      ORQUESTRADOR       │
                     └───────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │JsonMetadataMgr  │ │FlightAggregator │ │  AlertManager   │
    │  ESTATÍSTICO    │ │COORD. MISSÃO    │ │ANALISTA QUALID. │
    │                 │ │                 │ │                 │
    │• média          │ │• voo F001       │ │• DEWARP         │
    │• desvio         │ │• velocidade     │ │• RTK            │
    │• min/max        │ │• duração        │ │• GIMBAL         │
    │• distribuição   │ │• área (ha)      │ │• MOTION BLUR    │
    │  por nível      │ │• temperatura    │ │• OVERLAP        │
    │• PQI            │ │• séries tempor. │ │• YAW            │
    │• catalog        │ │• hora do dia    │ │• TEMPERATURE    │
    └─────────────────┘ └─────────────────┘ └─────────────────┘