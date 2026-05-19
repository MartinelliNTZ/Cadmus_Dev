# Análise de Classes - `utils/report`

## Visão Geral

O módulo `utils/report` é o núcleo do sistema de relatórios fotogramétricos. Ele contém 6 classes principais que trabalham em conjunto para: carregar metadados de imagens, classificar indicadores de qualidade, consolidar resultados, gerar alertas e renderizar o relatório HTML final.

### Arquitetura (após refatoração)

```
JSON (metadata)
  │
  ▼
JSONUtil.load_records()   ← APENAS v2.0, SEM legado
  │ List[Dict]
  ▼
IMGMetadata.__init__(record) → IMGMetadata.score()
  │ List[IMGMetadata] com levels, messages, overall_score
  ▼
┌─────────────────────────────────────────────────────┐
│ JSONUtil.compute_indicator_statistics()             │
│                                                     │
│ O ESTATÍSTICO PURO                                  │
│ ====================                                │
│ Só sabe calcular distribuições sobre atributos:     │
│ média, desvio, min, max, range, dist por nível,     │
│ PQI classification.                                 │
│                                                     │
│ Não sabe nada sobre: voos, equipamentos, gráficos,  │
│ alertas, recomendações.                             │
└─────────────────────────────────────────────────────┘
  │ indicator_stats (per_indicator, level_dist, pqi_*)
  ▼
┌─────────────────────────────────────────────────────┐
│ AggregateAnalyzer.analyze(results)                  │
│                                                     │
│ O OPERACIONAL                                       │
│ =============                                       │
│ Foco em:                                            │
│   ✓ Agrupamento por voo                             │
│   ✓ Métricas avançadas (RTK, Gimbal, Yaw, etc.)    │
│   ✓ Alertas (via AlertManager)                     │
│   ✓ Recomendações                                   │
│   ✓ Informações de equipamento                     │
│                                                     │
│ NÃO faz mais estatística pura - delegou ao          │
│ JSONUtil (Estatístico).                             │
└─────────────────────────────────────────────────────┘
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

## 1. `JSONUtil` (O Estatístico)

**Arquivo:** `utils/report/JSONUtil.py`

**Responsabilidade:** **Estatístico puro.** Processa N fichas (IMGMetadata) e devolve distribuições sobre atributos. Não sabe nada sobre voos, equipamentos, gráficos, alertas ou relatórios. Só sabe calcular: média, desvio, mínimo, máximo, distribuição por nível, séries temporais.

> 🎯 **Analogia:** Alguém recebe 5.000 fichas, cada uma com 40 atributos medidos, e responde: "para o atributo GSD, a média foi 3.2, o desvio foi 0.4, 80% das fotos ficaram no nível 4." Ele não sabe nada sobre voos, não sabe sobre equipamento, não sabe sobre gráficos. Ele só sabe calcular distribuições sobre atributos.

### Carga de Dados (APENAS v2.0, SEM legado)

| Método | Tipo | Descrição |
|--------|------|-----------|
| `load_json_file(json_path, tool_key)` | `@staticmethod` | Lê um arquivo JSON do disco e retorna o objeto desserializado. |
| `load_timestamps(json_path, tool_key)` | `@staticmethod` | Carrega apenas o bloco de timestamps do JSON v2.0 schema. |
| `load_json_metadata(json_path, tool_key)` | `@staticmethod` | Carrega metadados do JSON raiz: título, logotipo, generated_at. |
| `compute_processing_summary(timestamps)` | `@staticmethod` | Calcula tempos de processamento a partir do dicionário de timestamps. |
| `load_records(json_path, tool_key)` | `@staticmethod` | Carrega registros de metadata **exclusivamente via JSON v2.0**. Não suporta mais formatos legados. |

### Métodos Estatísticos Puros

| Método | Tipo | Descrição |
|--------|------|-----------|
| `compute_indicator_statistics(results)` | `@staticmethod` | **Método principal do Estatístico.** Calcula estatísticas PURAS sobre os indicadores. Retorna `per_indicator`, `level_distribution`, `pqi_mean`, `pqi_level_distribution`, `pqi_classification`, `indicator_catalog`. |
| `_is_zero_or_none(val)` | `@staticmethod` (privado) | Verifica se valor é None, zero ou vazio. |
| `_resolve_field_meta(indicator)` | `@staticmethod` (privado) | Resolve metadado de um indicador com fallback de aliases. |
| `_numeric_values_from_keys(results, keys)` | `@staticmethod` (privado) | Extrai série numérica de chaves candidatas. |
| `_first_numeric_from_result(r, keys)` | `@staticmethod` (privado) | Retorna primeiro valor numérico disponível em um resultado. |
| `_series_by_time(results, keys)` | `@staticmethod` (privado) | Monta série temporal ordenada de valores numéricos por data de captura. |
| `_level_ranges_from_threshold(indicator)` | `@staticmethod` (privado) | Traduz thresholds configurados para descrições textuais por nível (N1..N5). |

### Métodos Removidos (Legado)

| Método Removido | Motivo |
|-----------------|--------|
| `_normalize_record()` | Apenas usado por formatos legados. Removido com o suporte legado. |

### Fluxo de Uso do Estatístico
```
JSONUtil.compute_indicator_statistics(results)
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

## 2. `RangeMetadataManager`

**Arquivo:** `utils/report/RangeMetadataManager.py`

**Responsabilidade:** Fonte única (Singleton) para configuração de thresholds e classificação de níveis (1 a 5) dos indicadores. Carrega do arquivo YAML `resources/reports/config.yaml`.

*(sem alterações - esta classe não foi modificada)*

---

## 3. `IMGMetadata`

**Arquivo:** `utils/report/IMGMetadata.py`

**Responsabilidade:** Modelo principal de imagem que encapsula todos os campos de MetadataFields, calcula scores, níveis e mensagens para cada indicador. É o resultado do processamento de cada foto.

*(sem alterações - esta classe não foi modificada)*

---

## 4. `AggregateAnalyzer` (O Operacional, não mais Deus)

**Arquivo:** `utils/report/AggregateAnalyzer.py`

**Responsabilidade:** **Operacional.** Agora foca exclusivamente em: agrupamento por voo, métricas avançadas, alertas (via `AlertManager`) e recomendações. A estatística pura de indicadores foi **delegada ao `JSONUtil` (Estatístico)**.

### O que foi removido do AggregateAnalyzer

| Método Removido | Movido Para | Motivo |
|-----------------|-------------|--------|
| `_numeric_values_from_keys()` | `JSONUtil._numeric_values_from_keys()` | É estatística pura sobre atributos |
| `_resolve_field_meta()` | `JSONUtil._resolve_field_meta()` | É resolução de metadados de atributos |
| `_level_ranges_from_threshold()` | `JSONUtil._level_ranges_from_threshold()` | É tradução de thresholds de atributos |
| `_is_zero_or_none()` | `JSONUtil._is_zero_or_none()` | É utilitário de verificação de valores |
| `_severity_entry()` | Removido (não era mais usado) | AlertManager.to_severity_entry() já fazia o papel |
| Lógica de `per_indicator` (antigo) | `JSONUtil.compute_indicator_statistics()` | Estatística pura delegada |
| Lógica de `pqi_classification` (antigo) | `JSONUtil.compute_indicator_statistics()` | Estatística pura delegada |
| Lógica de `indicator_catalog` (antigo) | `JSONUtil.compute_indicator_statistics()` | Estatística pura delegada |
| Lógica de `level_distribution` (antigo) | `JSONUtil.compute_indicator_statistics()` | Estatística pura delegada |
| `FIELD_FALLBACKS` | `JSONUtil._resolve_field_meta()` | Fallbacks dos atributos pertencem ao Estatístico |

### Métodos que PERMANECEM no AggregateAnalyzer

| Método | Tipo | Justificativa |
|--------|------|---------------|
| `analyze(results)` | `@staticmethod` | Orquestrador principal - usa JSONUtil para stats, faz o resto operacional |
| `_first_numeric_from_result(r, keys)` | `@staticmethod` (privado) | Usado para extrair valores específicos de um resultado individual (contexto de voo) |
| `_first_numeric_from_flight_values(results, keys)` | `@staticmethod` (privado) | **NOVO.** Extrai valores numéricos de todos os resultados para métricas operacionais de voo. Substitui o uso de `_numeric_values_from_keys` para este contexto. |
| `_debug_flight_area(items, flight_id, gsd_val, foverlap_val, estimated_area_ha)` | `@staticmethod` (privado) | Log de debug de voo (operacional) |
| `_to_pt_light_source_label(label)` | `@staticmethod` (privado) | Tradução de label de luz (operacional) |
| `_resolve_light_source_label(result)` | `@staticmethod` (privado) | Resolução de fonte de luz (operacional) |
| `_is_excluded_flight_field(field_key, field_label)` | `@staticmethod` (privado) | Filtro de campos de voo (operacional) |
| `_ignored_level5_keys_from_metadata_fields()` | `@staticmethod` (privado) | Chaves ignoradas em voo (operacional) |

### Constantes que PERMANECEM no AggregateAnalyzer

| Constante | Justificativa |
|-----------|---------------|
| `FLIGHT_STATS_ROUND_DECIMALS` | Específico de formatação de voo |
| `FLIGHT_EXCLUDE_KEYWORDS` | Específico de agrupamento de voo |
| `FLIGHT_IGNORE_LEVEL5_LABELS` | Específico de agrupamento de voo |
| `SPEED_RECOMMENDED_MIN_MS` | Recomendação operacional |
| `SPEED_RECOMMENDED_MAX_MS` | Recomendação operacional |
| `IDEAL_OVERLAP_PCT` | Recomendação operacional |
| `LIGHT_SOURCE_PT_LABELS` | Tradução operacional |

### Estrutura do Dict `agg` Retornado por `analyze()`

```
agg = {
    'total_images': int,
    'mean_overall': float,
    
    # Delegado ao JSONUtil (Estatístico):
    'per_indicator': { ... },
    'level_distribution': {1..5: count},
    'pqi_mean': float | None,
    'pqi_level_distribution': {1..5: count},
    'pqi_classification': { ... } | None,
    'indicator_catalog': [ ... ],
    
    # Operacional (AggregateAnalyzer):
    'general_info': { ... equipamentos, firmware, GPS, datas, voos, dewarp, altitude ... },
    'top_models': { ... },
    'per_flight': [ ... rows de voo ... ],
    'flight_level5_columns': [ ... ],
    'temp_chart_series': [ ... ],
    'lrf_chart_series': [ ... ],
    'temp_hourly_avg': [ ... ],
    'lrf_hourly_avg': [ ... ],
    'advanced_analysis': {
        'critical_alerts': [ ... ],
        'metrics': { ... RTK, gimbal, yaw, overlap, motion blur, luz ... },
        'quality_analysis': { strip_rows, problematic_strips },
        'recommendations': [ ... ]
    },
    'alerts': [ ... ],
    'alerts_count': int,
    'alerts_summary': { ... },
    'alerts_severity': { ... }
}
```

---

## 5. `AlertManager`

**Arquivo:** `utils/report/AlertManager.py`

**Responsabilidade:** Centraliza a geração de todos os alertas de qualidade do relatório fotogramétrico.

*(sem alterações - esta classe não foi modificada)*

---

## 6. `RenderEngine`

**Arquivo:** `utils/report/RenderEngine.py`

**Responsabilidade:** Renderiza o HTML final do relatório usando Jinja2, gera payloads de gráficos Chart.js, dados de mapa Leaflet e decide a visibilidade de colunas na tabela.

*(sem alterações - esta classe não foi modificada)*