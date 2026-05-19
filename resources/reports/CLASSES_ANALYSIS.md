# Análise de Classes - `utils/report`

## Visão Geral

O módulo `utils/report` é o núcleo do sistema de relatórios fotogramétricos. Ele contém 6 classes principais que trabalham em conjunto para: carregar metadados de imagens, classificar indicadores de qualidade, consolidar resultados, gerar alertas e renderizar o relatório HTML final.

---

## 1. `JSONUtil`

**Arquivo:** `utils/report/JSONUtil.py`

**Responsabilidade:** Leitura, normalização e parsing de arquivos JSON de metadados. Suporta tanto o formato legado quanto o formato v2.0 com timestamps.

### Métodos

| Método | Tipo | Descrição |
|--------|------|-----------|
| `load_json_file(json_path, tool_key)` | `@staticmethod` | Lê um arquivo JSON do disco e retorna o objeto desserializado. |
| `load_timestamps(json_path, tool_key)` | `@staticmethod` | Carrega apenas o bloco de timestamps do JSON v2.0 schema. Retorna dict vazio se não houver. |
| `load_json_metadata(json_path, tool_key)` | `@staticmethod` | Carrega metadados do JSON raiz: título, logotipo, generated_at. |
| `compute_processing_summary(timestamps)` | `@staticmethod` | Calcula tempos de processamento a partir do dicionário de timestamps. Retorna total_seconds, total_formatted, stages (lista de etapas com duração), missing_stages. |
| `load_records(json_path, tool_key)` | `@staticmethod` | Carrega registros de metadata suportando JSON v2.0 e formatos legados. É o método principal de entrada dos dados. |
| `_get_logger(tool_key)` | `@staticmethod` (privado) | Retorna uma instância de LogUtils configurada. |
| `_normalize_record(record, group_path, file_key)` | `@staticmethod` (privado) | Normaliza um registro bruto para o formato canônico baseado em MetadataFields. |

### Fluxo de Uso
```
load_records() → lista de dicts normalizados
     ├── Tenta JsonUtil.load_records() (v2.0)
     ├── Fallback: formato legado com groups/raw_records
     └── Fallback: formato chave → registro
```

---

## 2. `RangeMetadataManager`

**Arquivo:** `utils/report/RangeMetadataManager.py`

**Responsabilidade:** Fonte única (Singleton) para configuração de thresholds e classificação de níveis (1 a 5) dos indicadores. Carrega do arquivo YAML `resources/reports/config.yaml`.

### Propriedades

| Propriedade | Tipo | Descrição |
|-------------|------|-----------|
| `_config` | `Dict` (privado) | Configuração carregada do YAML (thresholds + templates). Inicialmente `None`. |
| `DEFAULT_CONFIG_PATH` | `Path` | Caminho padrão: `resources/reports/config.yaml` |
| `range_metadata_manager` | Instância | Singleton global exportado no `__init__.py`. |

### Métodos

| Método | Tipo | Descrição |
|--------|------|-----------|
| `load(config_path, tool_key)` | instance | Carrega configurações de thresholds e mensagens a partir de arquivo YAML. |
| `get_thresholds(indicator)` | instance | Retorna a configuração de threshold de um indicador específico (type, levels, messages). |
| `get_templates()` | instance | Retorna configurações de templates definidas no YAML. |
| `classify(indicator, value)` | instance | **Método principal.** Classifica um valor em nível (1..5) e mensagem conforme regra do indicador. Suporta tipos: `higher_better`, `lower_better`, `range_best`, `categorical`. |
| `_parse_num(raw)` | `@staticmethod` (privado) | Converte valor textual/numérico em float com suporte a infinitos. |

### Tipos de Threshold Suportados

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| `higher_better` | Quanto maior o valor, melhor o nível. | PQI, Overlap |
| `lower_better` | Quanto menor o valor, melhor o nível. | GSD, Motion Blur |
| `range_best` | Faixas ótimas (intervalos min-max). | Speed, Incidence Angle |
| `categorical` | Mapeamento direto valor → nível. | Dewarp Flag, Light Source |

---

## 3. `IMGMetadata`

**Arquivo:** `utils/report/IMGMetadata.py`

**Responsabilidade:** Modelo principal de imagem que encapsula todos os campos de MetadataFields, calcula scores, níveis e mensagens para cada indicador. É o resultado do processamento de cada foto.

### Atributos Principais

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `_data` | `Dict` | Dicionário interno com chaves canônicas de MetadataFields. |
| `_extras` | `Dict` | Campos extras não catalogados. |
| `filename` | `str` | Nome do arquivo da imagem. |
| `mrk_file` | `str` | Nome do arquivo MRK associado. |
| `flight_id` | `str` | Identificador de voo derivado do MRK. |
| `dewarp_flag` | `Any` | Flag de dewarping (0 = aplicado, 1 = não). |
| `alt_mrk` | `Any` | Altitude do MRK. |
| `absolute_altitude` | `Any` | Altitude absoluta. |
| `shutter_count` | `Any` | Contagem de disparos. |
| `equipment_model` | `str` | Modelo do equipamento/drone. |
| `camera_model` | `str` | Modelo da câmera. |
| `capture_datetime` | `str` | Data e hora da captura. |
| `values` | `Dict[str, Any]` | Valores brutos dos indicadores. |
| `level5_values` | `Dict[str, Any]` | Valores de campos nível 5 (MetadataFields.level == 5). |
| `levels` | `Dict[str, int]` | Níveis classificados (1..5) para cada indicador. |
| `messages` | `Dict[str, str]` | Mensagens descritivas para cada indicador. |
| `overall_score` | `float` | Score geral (média dos níveis, 0.0–5.0). |

### Métodos

| Método | Tipo | Descrição |
|--------|------|-----------|
| `__init__(json_record)` | Constructor | Inicializa a partir de um registro JSON normalizado, preenchendo campos canônicos e extras. |
| `score()` | instance | **Método principal.** Calcula níveis, mensagens e score geral. Preenche todos os atributos de análise. Retorna `self`. |
| `get_indicator(key)` | instance | Obtém o valor de um indicador com suporte a aliases e campos derivados (ex: speed_3d_ms, incidence_angle, sensor_temp_c, gsd_cm). |
| `to_json()` | instance | Exporta o estado completo em formato de dicionário serializável. |
| `_is_present(value)` | `@staticmethod` (privado) | Verifica se um valor pode ser considerado preenchido para análise. |
| `_to_float(value)` | `@staticmethod` (privado) | Converte valor para float com tolerância a nulos. |
| `_first_value(names)` | instance (privado) | Retorna o primeiro valor encontrado entre nomes candidatos e aliases de metacampos. |
| `_derive_speed_3d_ms()` | instance (privado) | Deriva velocidade 3D em m/s usando campo explícito ou conversão de km/h. |
| `_derive_incidence_angle()` | instance (privado) | Deriva ângulo de incidência a partir do campo explícito ou do pitch do gimbal. |
| `_derive_flight_id(mrk_file_value)` | `@staticmethod` (privado) | Gera identificador de voo padronizado baseado no nome do arquivo MRK. |

### Fluxo de Classificação (método `score()`)
```
1. Carrega config (se necessário)
2. Extrai campos base (filename, mrk_file, flight_id, dewarp_flag, etc.)
3. Para cada indicador nos thresholds:
   a. Obtém valor via get_indicator()
   b. Classifica via range_metadata_manager.classify()
   c. Armazena level e message
4. Para cada campo level5:
   a. Armazena valor em level5_values
5. Calcula overall_score = média dos níveis
```

---

## 4. `AggregateAnalyzer`

**Arquivo:** `utils/report/AggregateAnalyzer.py`

**Responsabilidade:** Classe central de consolidação. Recebe a lista de `IMGMetadata` processados e gera o dicionário `agg` completo que alimenta o relatório. Contém toda a lógica de agregação por voo, métricas avançadas, análises de qualidade e recomendações.

### Constantes de Classe

| Constante | Valor | Descrição |
|-----------|-------|-----------|
| `FLIGHT_STATS_ROUND_DECIMALS` | `2` | Casas decimais para estatísticas de voo. |
| `FIELD_FALLBACKS` | `Dict` | Mapeamento de fallbacks para campos (ex: gsd_cm, speed_3d_ms). |
| `FLIGHT_EXCLUDE_KEYWORDS` | `Set` | Palavras-chave para excluir campos do agrupamento por voo. |
| `FLIGHT_IGNORE_LEVEL5_LABELS` | `Set` | Labels de nível 5 ignorados nas médias por voo. |
| `SPEED_RECOMMENDED_MIN_MS` | `5.0` | Velocidade mínima recomendada (m/s). |
| `SPEED_RECOMMENDED_MAX_MS` | `10.0` | Velocidade máxima recomendada (m/s). |
| `IDEAL_OVERLAP_PCT` | `60.0` | Sobreposição ideal (%). |
| `LIGHT_SOURCE_PT_LABELS` | `Dict` | Mapeamento de labels de fonte de luz para português. |

### Métodos

| Método | Tipo | Descrição |
|--------|------|-----------|
| `analyze(results)` | `@staticmethod` | **Método principal.** Executa a agregação completa. Retorna dict `agg` com todas as seções do relatório. |
| `_debug_flight_area(items, flight_id, gsd_val, foverlap_val, estimated_area_ha)` | `@staticmethod` (privado) | Log detalhado do cálculo de área por voo para debug. |
| `_to_pt_light_source_label(label)` | `@staticmethod` (privado) | Traduz label de fonte de luz para português. |
| `_resolve_light_source_label(result)` | `@staticmethod` (privado) | Resolve label de fonte de luz (texto ou código). |
| `_resolve_field_meta(indicator)` | `@staticmethod` (privado) | Resolve metadado de um indicador com fallback de aliases. |
| `_is_excluded_flight_field(field_key, field_label)` | `@staticmethod` (privado) | Verifica se campo deve ser ignorado no agrupamento por voo. |
| `_is_zero_or_none(val)` | `@staticmethod` (privado) | Verifica se valor é None, zero ou vazio. |
| `_numeric_values_from_keys(results, keys)` | `@staticmethod` (privado) | Extrai série numérica de chaves candidatas. |
| `_first_numeric_from_result(r, keys)` | `@staticmethod` (privado) | Retorna primeiro valor numérico disponível em um resultado. |
| `_series_by_time(results, keys)` | `@staticmethod` (privado) | Monta série temporal ordenada de valores numéricos por data de captura. |
| `_severity_entry(severity, title, detail, impact, action)` | `@staticmethod` (privado) | Cria estrutura padronizada de alerta. |
| `_ignored_level5_keys_from_metadata_fields()` | `@staticmethod` (privado) | Retorna chaves level 5 ignoradas no quadro de médias por voo. |
| `_level_ranges_from_threshold(indicator)` | `@staticmethod` (privado) | Traduz thresholds configurados para descrições textuais por nível (N1..N5). |

### Estrutura do Dict `agg` Retornado por `analyze()`

```
agg = {
    'total_images': int,
    'mean_overall': float,
    'pqi_mean': float | None,
    'pqi_level_distribution': {1: int, 2: int, 3: int, 4: int, 5: int},
    'level_distribution': {1: int, 2: int, 3: int, 4: int, 5: int},
    'per_indicator': {
        indicator_key: {
            'label', 'description', 'threshold_type', 'level_ranges',
            'mean', 'std', 'value_mean', 'value_std', 'value_min',
            'value_max', 'value_range', 'dist': {1..5: count}
        }
    },
    'pqi_classification': {'level', 'label', 'score_display'} | None,
    'indicator_catalog': [...],
    'general_info': {
        'equipment_models', 'equipment_serial_numbers',
        'camera_models', 'camera_serial_numbers',
        'firmware_versions', 'gps_datum', 'gps_status',
        'capture_start', 'capture_end',
        'total_flights', 'total_flight_time',
        'dewarp_zero_count', 'dewarp_status_type', 'dewarp_status_message',
        'missing_altitude_count', 'altitude_status_type', 'altitude_status_message',
        'last_shutter_per_camera': [...]
    },
    'top_models': {model: {'count', 'mean_score'}},
    'per_flight': [
        {
            'flight_id', 'images', 'mean_score',
            'start', 'end', 'flight_seconds', 'flight_time',
            'estimated_area_ha', 'altitude_solo',
            'avg_speed3d_kmh', 'avg_speed3d_ms',
            'avg_sensor_temperature', 'avg_lrf_target_distance',
            'avg_relative_altitude', 'avg_absolute_altitude',
            'avg_iso', 'avg_white_balance_cct',
            'avg_shutter_speed_text', 'shutter_speed_range_text',
            'avg_dist3d_previous', 'avg_flight_roll',
            'avg_flight_yaw', 'avg_flight_pitch',
            'level5_means': {field_key: float}
        }
    ],
    'temp_chart_series': [{'label': flight_id, 'data': [{'x', 'y'}]}],
    'lrf_chart_series': [{'label': flight_id, 'data': [{'x', 'y'}]}],
    'temp_hourly_avg': [{'hour', 'label', 'mean', 'count'}],
    'lrf_hourly_avg': [{'hour', 'label', 'mean', 'count'}],
    'flight_level5_columns': [{'key', 'label'}],
    'advanced_analysis': {
        'critical_alerts': [{'severity', 'title', 'detail', 'impact', 'action'}],
        'metrics': {
            'rtk_diff_age_mean', 'rtk_diff_age_max', 'rtk_diff_age_p95',
            'rtk_stability_mean', 'rtk_stability_class',
            'rtk_effective_precision_mean', 'rtk_effective_precision_max',
            'gimbal_offset_mean', 'gimbal_offset_std', 'gimbal_offset_max',
            'gimbal_offset_over_1deg_pct', 'yaw_inconsistent_pct',
            'size_mb_mean', 'size_mb_std', 'size_mb_cv',
            'overlap_below_ideal_pct', 'overlap_mean',
            'speed_ms_mean', 'speed_ms_recommended',
            'motion_blur_mean', 'speed_variation_mean',
            'pqi_first_quartile_mean', 'pqi_last_quartile_mean', 'pqi_delta',
            'morning_pqi_mean', 'midday_pqi_mean',
            'light_inconsistent_pct', 'light_source_predominant',
            'light_source_predominant_count', 'light_source_predominant_pct',
            'light_source_total_classified', 'light_source_classes',
            'light_source_from_text', 'light_source_from_code',
            'estimated_area_ha', 'problematic_strips'
        },
        'quality_analysis': {
            'strip_rows': [{'strip_id', 'images', 'mean_score', 'mean_overlap', 'overlap_below_ideal_pct'}],
            'problematic_strips': [strip_row with score < 3 or overlap < 30%]
        },
        'recommendations': [str]
    },
    'alerts': [AlertRecord as dict],
    'alerts_count': int,
    'alerts_summary': {category: {severity: count, 'total': count}},
    'alerts_severity': {'CRITICO': int, 'ALERTA': int, 'INFO': int}
}
```

### Seções Calculadas pelo `analyze()`

| Seção | Descrição |
|-------|-----------|
| **Estatísticas por indicador** | Média, desvio, min, max, range, distribuição por nível |
| **Classificação PQI** | Score baseado em PhotogrammetryQualityIndex com estrelas |
| **Informações gerais** | Equipamentos, câmeras, firmware, GPS, datas, voos |
| **Agrupamento por voo** | Médias de speed, temperatura, LRF, altitude, ISO, shutter, WB, atitude do drone |
| **Área estimada** | Cálculo de hectares por voo usando GSD × dimensões da imagem × overlap |
| **Séries temporais** | Temperatura e LRF por foto ao longo do tempo |
| **Médias por hora** | Temperatura e LRF agregados por hora do dia |
| **Alertas unificados** | Delegado ao `AlertManager.analyze()` |
| **Métricas avançadas** | RTK, gimbal, yaw, overlap, motion blur, luz, strips problemáticas |
| **Recomendações** | Baseadas em thresholds: overlap, yaw, gimbal, RTK, iluminação |

---

## 5. `AlertManager`

**Arquivo:** `utils/report/AlertManager.py`

**Responsabilidade:** Centraliza a geração de todos os alertas de qualidade do relatório fotogramétrico. Analisa cada aspecto da qualidade e produz `AlertRecord` com severidade, categoria, detalhes, impacto e ação recomendada.

### Data Class: `AlertRecord`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `severity` | `str` | 'CRITICO', 'ALERTA', 'INFO' |
| `category` | `str` | Categoria do alerta (ex: 'DEWARP', 'RTK', 'GSD') |
| `title` | `str` | Título curto do alerta |
| `detail` | `str` | Descrição detalhada com métricas |
| `impact` | `str` | Impacto na qualidade do produto final |
| `action` | `str` | Ação recomendada |
| `affected_count` | `int` | Número de imagens/voos afetados |
| `total_count` | `int` | Total de imagens/voos analisados |
| `affected_pct` | `float` | Percentual de itens afetados |
| `threshold_value` | `float \| None` | Valor do limiar que disparou o alerta |
| `actual_value` | `float \| None` | Valor medido atual |
| `flight_ids` | `List[str]` | Voos afetados |
| `photos` | `List[str]` | Fotos críticas (limitado a 20) |

### Constantes de Classe (Thresholds)

| Constante | Valor | Descrição |
|-----------|-------|-----------|
| `SEVERITY_CRITICAL` | `'CRITICO'` | Severidade crítica |
| `SEVERITY_ALERT` | `'ALERTA'` | Severidade alerta |
| `SEVERITY_INFO` | `'INFO'` | Severidade informativa |
| `BLUR_ALERT_THRESHOLD` | `0.5` | MotionBlurRisk > 0.5 |
| `BLUR_CRITICAL_THRESHOLD` | `1.0` | MotionBlurRisk > 1.0 |
| `GIMBAL_OFFSET_ALERT` | `15.0` | GimbalOffset > 15° |
| `GIMBAL_OFFSET_CRITICAL` | `30.0` | GimbalOffset > 30° |
| `GSD_VARIATION_THRESHOLD` | `0.5` | Variação GSD > 0.5cm |
| `OVERLAP_CRITICAL_PCT` | `30.0` | % de imagens com overlap < 60% |
| `YAW_OPPOSITE_THRESHOLD` | `150.0` | Yaw alignment error para direção oposta |
| `ALTITUDE_MISSING_WARN_PCT` | `10.0` | % máxima aceitável de altitude ausente |
| `RTK_EFFECTIVE_PRECISION_ALERT` | `0.100` | RTK Effective Precision crítica |
| `RTK_EFFECTIVE_PRECISION_WARN` | `0.050` | RTK Effective Precision alerta |

### Categorias de Alerta

| Categoria | Constante | Descrição |
|-----------|-----------|-----------|
| `DEWARP` | `CAT_DEWARP` | Dewarp desabilitado |
| `RTK` | `CAT_RTK` | Qualidade do sinal RTK/GPS |
| `RTK_FLAG` | `CAT_RTK_FLAG` | Flag RTK não-fixa |
| `GSD` | `CAT_GSD` | GSD fora do esperado |
| `GSD_VARIATION` | `CAT_GSD_VARIATION` | Variação de GSD |
| `MOTION_BLUR` | `CAT_MOTION_BLUR` | Motion blur elevado |
| `GIMBAL` | `CAT_GIMBAL` | Gimbal desalinhado |
| `ALTITUDE` | `CAT_ALTITUDE` | Altitude incompleta |
| `OVERLAP` | `CAT_OVERLAP` | Sobreposição insuficiente |
| `YAW` | `CAT_YAW` | Inconsistência de direção |
| `TEMPERATURE` | `CAT_TEMPERATURE` | Temperatura do sensor elevada |
| `ILLUMINATION` | `CAT_ILLUMINATION` | Iluminação inconsistente |
| `SPEED` | `CAT_SPEED` | Velocidade inadequada |
| `SHUTTER` | `CAT_SHUTTER` | Obturação inadequada |
| `GENERAL` | `CAT_GENERAL` | Alertas gerais |

### Métodos

| Método | Tipo | Descrição |
|--------|------|-----------|
| `analyze(results, agg)` | `@staticmethod` | **Método principal.** Executa todas as análises e retorna lista centralizada de `AlertRecord`. |
| `to_dict(alert)` | `@staticmethod` | Converte `AlertRecord` para dicionário serializável (via `dataclasses.asdict`). |
| `to_dict_list(alerts)` | `@staticmethod` | Converte lista de `AlertRecord` para lista de dicionários. |
| `to_severity_entry(alert)` | `@staticmethod` | Converte para formato legado compatível com template antigo (`severity`, `title`, `detail`, `impact`, `action`). |
| `summary_by_category(alerts)` | `@staticmethod` | Gera sumário de contagem de alertas por categoria e severidade. |
| `_parse_num(value)` | `@staticmethod` (privado) | Converte valor para float com segurança (trata None, NaN, Inf). |
| `_fmt_pct(value)` | `@staticmethod` (privado) | Formata percentual com 2 casas decimais. |
| `_fmt_num(value, decimals)` | `@staticmethod` (privado) | Formata número com casas decimais. |
| `_to_int_or_none(value)` | `@staticmethod` (privado) | Converte para int ou None. |
| `_make_record(severity, category, title, detail, impact, action, ...)` | `@staticmethod` (privado) | Cria um `AlertRecord` com cálculo automático de percentual. |

### Análises Realizadas pelo `analyze()`

| # | Análise | Gatilho | Severidade |
|---|---------|---------|------------|
| 1 | **DEWARP** | `dewarp_zero_count > 0` | CRITICO |
| 2 | **ALTITUDE** | `missing_alt_count > 0` | CRITICO se >50%, ALERTA se >10%, INFO caso contrário |
| 3 | **MOTION BLUR** | `blur > 0.5` | CRITICO se blur > 1.0, ALERTA caso contrário |
| 4 | **GIMBAL OFFSET** | `offset > 15°` | CRITICO se offset > 30°, ALERTA caso contrário |
| 5 | **RTK FLAG** | sinal não-fixo | CRITICO se fixa < 80%, ALERTA se > 5%, INFO caso contrário |
| 6 | **GSD VARIATION** | desvio > 0.5cm | ALERTA |
| 7 | **OVERLAP** | overlap < 60% em > 30% das imagens | CRITICO se > 50%, ALERTA caso contrário |
| 8 | **YAW** | yaw oposto > 5% | ALERTA |
| 9 | **RTK STD (GPS)** | lat/lon/hgt com desvio alto | CRITICO se > 50%, ALERTA caso contrário |
| 10 | **RTK EFFECTIVE PRECISION** | precisão > 0.100 | CRITICO se > 0.100, ALERTA se > 0.050 |
| 11 | **TEMPERATURE** | sensor > 45°C | CRITICO se > 48°C, ALERTA caso contrário |

---

## 6. `RenderEngine`

**Arquivo:** `utils/report/RenderEngine.py`

**Responsabilidade:** Renderiza o HTML final do relatório usando Jinja2, gera payloads de gráficos Chart.js, dados de mapa Leaflet e decide a visibilidade de colunas na tabela.

### Métodos

| Método | Tipo | Descrição |
|--------|------|-----------|
| `__init__(tool_key)` | Constructor | Inicializa ambiente Jinja2, carrega o template `resources/reports/template.html`. |
| `generate_charts(agg_data)` | `@staticmethod` | Monta payload de gráficos consumido pelo template (Chart.js). Gera: level_pie (pie), indicator_bar (bar), temp_line (line), lrf_line (line), temp_hourly_line (line), lrf_hourly_line (line). |
| `compute_column_visibility(agg)` | `@staticmethod` | Decide colunas visíveis na tabela de voos com base nos dados presentes. Modifica `agg` in-place (`show_column_*` flags). |
| `generate_map_data(results)` | `@staticmethod` | Gera snippet Leaflet com pontos reais (lat/lon) das imagens. Inclui markers, polyline, bounds, popups. |
| `render_report(results, agg, charts, map_data)` | instance | Renderiza o HTML final do relatório com dados agregados e detalhes por imagem. Ordena piores resultados (menor overall_score). |
| `save_report(html, output_path)` | instance | Salva o HTML renderizado no caminho de saída definido. |
| `_to_float(value)` | `@staticmethod` (privado) | Converte valor para float com tolerância a strings vazias. |
| `_extract_lat_lon(result)` | `@staticmethod` (privado) | Extrai lat/lon reais a partir do resultado da imagem (tenta múltiplos formatos). |

### Gráficos Gerados

| Chave | Tipo | Descrição |
|-------|------|-----------|
| `level_pie` | pie | Distribuição dos níveis de qualidade (PQI ou geral) |
| `indicator_bar` | bar | Média dos níveis por indicador (top 10) |
| `temp_line` | line | Temperatura do sensor por foto (°C), por voo |
| `lrf_line` | line | LRF Target Distance ao longo do voo (m), por voo |
| `temp_hourly_line` | line | Temperatura média por hora do dia (°C) |
| `lrf_hourly_line` | line | LRF Target Distance médio por hora do dia (m) |

### Colunas Dinâmicas (compute_column_visibility)

O método `compute_column_visibility` decide quais colunas mostrar na tabela de voos:

| Flag | Coluna | Oculto quando |
|------|--------|---------------|
| `show_column_speed3d_kmh` | Velocidade (km/h) | Todos os voos sem valor |
| `show_column_sensor_temp` | Temperatura Sensor | Todos os voos sem valor |
| `show_column_lrf` | Distância Solo (LRF) | Todos os voos sem valor |
| `show_column_rel_alt` | Altitude Relativa | Todos os voos sem valor |
| `show_column_abs_alt` | Altitude Absoluta | Todos os voos sem valor |
| `show_column_iso` | ISO | Todos os voos sem valor |
| `show_column_shutter` | Obturador | Todos os voos sem valor |
| `show_column_wb_cct` | Temp Cor (K) | Todos os voos sem valor |
| `show_column_dist3d` | Distância 3D | Todos os voos sem valor |
| `show_column_flight_roll` | Drone Roll | Todos os voos sem valor |
| `show_column_flight_yaw` | Drone Yaw | Todos os voos sem valor |
| `show_column_flight_pitch` | Drone Pitch | Todos os voos sem valor |

---

## Diagrama de Fluxo do Sistema de Relatório

```
JSON (metadata)
  │
  ▼
JSONUtil.load_records()
  │ List[Dict]
  ▼
IMGMetadata.__init__(record) → IMGMetadata.score()
  │ List[IMGMetadata] com levels, messages, overall_score
  ▼
AggregateAnalyzer.analyze(results)
  │
  ├── Per indicator stats (média, desvio, distribuição)
  ├── General info (equipamentos, firmware, GPS, datas)
  ├── Per flight grouping (médias por voo)
  ├── Temperature/LRF series (charts)
  ├── Strip analysis
  │
  ├── AlertManager.analyze(results, agg)
  │     ├── DEWARP, ALTITUDE, MOTION_BLUR
  │     ├── GIMBAL, RTK_FLAG, GSD_VARIATION
  │     ├── OVERLAP, YAW, RTK_STD, RTK_PRECISION
  │     └── TEMPERATURE
  │
  └── Dict agg (completo)
      │
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

## `__init__.py` - Exportações

```python
from .JSONUtil import JSONUtil
from .RangeMetadataManager import RangeMetadataManager, range_metadata_manager
from .IMGMetadata import IMGMetadata
from .AggregateAnalyzer import AggregateAnalyzer
from .RenderEngine import RenderEngine
from .AlertManager import AlertManager, AlertRecord

__all__ = [
    "JSONUtil",
    "RangeMetadataManager",
    "range_metadata_manager",
    "IMGMetadata",
    "AggregateAnalyzer",
    "RenderEngine",
    "AlertManager",
    "AlertRecord",
]