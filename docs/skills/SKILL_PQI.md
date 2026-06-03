---
name: cadmus-photogrammetry-quality-index-scoring
description: >
  Sistema completo de pontuação e classificação da qualidade fotogramétrica (PQI 0-100),
  incluindo indicadores com pesos, thresholds do config.yaml, classificação por níveis (1-5),
  alertas de qualidade e interpretação de resultados.
---

# Cadmus Photogrammetry Quality Index (PQI) — Sistema de Pontuação e Notas

## Resumo Executivo

O **Photogrammetry Quality Index (PQI)** é uma métrica composta (0-100) que avalia a qualidade de cada foto individualmente, combinando **7 indicadores** com pesos configuráveis. Cada indicador é classificado em **nível 1 (crítico) a 5 (excelente)** via thresholds do `config.yaml`, e o nível é convertido em pontuação (0-100) e ponderado pelo peso do indicador.

O sistema possui 3 camadas integradas:

| Camada | Arquivo | Função |
|--------|---------|--------|
| **Cálculo custom** | `CustomPhotosFieldsUtil.py` | Calcula todos os campos derivados (GSD, overlap, RTK, etc.) |
| **PQI core** | `PqiUtil.py` | Orquestra indicadores, classifica, pondera e calcula PQI final |
| **Thresholds** | `RangeMetadataManager.py` | Lê `config.yaml`, classifica valores em níveis 1-5 |
| **Alertas** | `AlertManager.py` | Gera alertas críticos/de alerta/info por categoria |
| **Config** | `resources/reports/config.yaml` | 24 thresholds com mensagens e níveis |

---

## 1. Arquitetura do PQI

### Fluxo de Cálculo

```
CustomPhotosFieldsUtil.calculate_all_custom_fields()
  ↓  (calcula todos os campos EXIF/XMP/custom para cada foto)
  ↓
Pós-processamento: PqiUtil.calculate(item) para cada foto
  ↓
  1. Extrai valor de cada indicador (via metadata_key ou value_extractor)
  2. Classifica valor em nível 1-5 (via RangeMetadataManager ou bypass)
  3. Converte nível → score 0-100
  4. Pondera pelo peso do indicador
  5. Média ponderada = PQI final (0-100)
  ↓
Armazena como PhotogrammetryQualityIndex no record
```

### Configuração dos Indicadores (PQI_INDICATORS)

Em `PqiUtil.py`, os 7 indicadores que compõem o PQI:

```python
PQI_INDICATORS = [
    # INDICADORES QUE USAM CLASSIFICAÇÃO NORMAL (via RangeMetadataManager)
    {
        "name": "MotionBlurRisk",
        "metadata_key": MetadataFieldKey.MOTION_BLUR_RISK,
        "threshold_name": "motion_blur_risk",  # lower_better
        "weight": 0.25,
    },
    {
        "name": "FOverlap (PredictedOverlap)",
        "metadata_key": MetadataFieldKey.F_OVERLAP,
        "threshold_name": "predicted_overlap",  # higher_better
        "weight": 0.25,
    },
    {
        "name": "XYDifference",
        "metadata_key": MetadataFieldKey.XY_DIFFERENCE,
        "threshold_name": "xy_difference",  # lower_better
        "weight": 1.0,
    },
    {
        "name": "ZDifference",
        "metadata_key": MetadataFieldKey.Z_DIFFERENCE,
        "threshold_name": "z_difference",  # lower_better
        "weight": 1.0,
    },
    {
        "name": "RtkDiffAge",
        "metadata_key": MetadataFieldKey.RTK_DIFF_AGE,
        "threshold_name": "rtk_diff_age",  # lower_better
        "weight": 1.5,
    },

    # INDICADORES COM BYPASS (value_extractor já retorna nível 1-5)
    {
        "name": "RtkEffectivePrecision",
        "metadata_key": MetadataFieldKey.RTK_EFFECTIVE_PRECISION,
        "threshold_name": "rtk_effective_precision",
        "weight": 1.0,
        "value_extractor": lambda r: _extract_rtk_level(r),  # já classifica internamente
        "bypass_classify": True,
    },
    {
        "name": "DewarpFlag",
        "metadata_key": MetadataFieldKey.DEWARP_FLAG,
        "threshold_name": "dewarp_flag",
        "weight": 2.0,  # MAIOR PESO — dewarp é crítico
        "value_extractor": lambda r: _extract_dewarp_value(r),  # retorna nível direto
        "bypass_classify": True,
    },
]
```

### Pesos e Participação no PQI

O peso de cada indicador define sua importância relativa:

| Indicador | Peso | % do PQI (normalizado) |
|-----------|------|------------------------|
| DewarpFlag | 2.0 | **28.6%** |
| RtkDiffAge | 1.5 | **21.4%** |
| XYDifference | 1.0 | **14.3%** |
| ZDifference | 1.0 | **14.3%** |
| RtkEffectivePrecision | 1.0 | **14.3%** |
| MotionBlurRisk | 0.25 | **3.6%** |
| FOverlap | 0.25 | **3.6%** |
| **Total** | **7.0** | **100%** |

> **DewarpFlag** tem o maior peso (2.0) porque fotos sem dewarp comprometem **todo o bloco** fotogramétrico — distorção sistemática inviabiliza aerotriangulação.
> 
> **MotionBlurRisk e FOverlap** têm pesos baixos (0.25) por serem indicadores preditivos/estimados, não valores absolutos.

---

## 2. Sistema de Classificação por Níveis (1-5)

### Como funciona a classificação

`RangeMetadataManager` lê o `config.yaml` e classifica **qualquer valor numérico ou categórico** em nível 1-5:

#### Tipos de Threshold

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| `lower_better` | Quanto menor o valor, melhor | motion_blur_risk: níveis decrescentes |
| `higher_better` | Quanto maior o valor, melhor | predicted_overlap: níveis crescentes |
| `range_best` | Valor ideal está em uma faixa específica | speed_3d_ms: faixas contíguas |
| `categorical` | Mapeamento direto valor → nível | dewarp_flag: 0→1, 1→5 |

#### lower_better

```yaml
motion_blur_risk:
  type: lower_better
  levels: [1.5, 1.2, 0.7, 0.5, inf]        # pontos de corte (decrescentes)
  messages:
    - "Motion blur critico"                  # nível 1: value > 1.5
    - "Motion blur alto"                     # nível 2: 1.2 < value ≤ 1.5
    - "Motion blur moderado"                 # nível 3: 0.7 < value ≤ 1.2
    - "Motion blur baixo"                    # nível 4: 0.5 < value ≤ 0.7
    - "Motion blur minimo"                   # nível 5: value ≤ 0.5
```

**Lógica**: `level = sum(1 for cut in levels if vnum <= cut)`

- Testa cada `cut` nos levels. Se `vnum <= cut`, incrementa nível.
- Com `levels: [1.5, 1.2, 0.7, 0.5, inf]`:
  - value=2.0: 2.0<=1.5? NÃO → 2.0<=1.2? NÃO → 2.0<=0.7? NÃO → 2.0<=0.5? NÃO → 2.0<=inf? SIM → level=1
  - value=0.6: 0.6<=1.5? SIM(1) → 0.6<=1.2? SIM(2) → 0.6<=0.7? SIM(3) → 0.6<=0.5? NÃO → 0.6<=inf? SIM(4) → level=4
  - value=0.3: 0.3<=1.5? SIM(1) → 0.3<=1.2? SIM(2) → 0.3<=0.7? SIM(3) → 0.3<=0.5? SIM(4) → 0.3<=inf? SIM(5) → level=5

#### higher_better

```yaml
predicted_overlap:
  type: higher_better
  levels: [20, 50, 75, 90, 97]
  messages:
    - "Sobreposicao critica"                # nível 1: value < 20
    - "Sobreposicao baixa"                  # nível 2: 20 ≤ value < 50
    - "Sobreposicao OK"                     # nível 3: 50 ≤ value < 75
    - "Sobreposicao boa"                    # nível 4: 75 ≤ value < 90
    - "Sobreposicao excelente"              # nível 5: value ≥ 90
```

**Lógica**: `level = sum(1 for cut in levels if vnum >= cut)`

- value=85: 85>=20? SIM(1) → 85>=50? SIM(2) → 85>=75? SIM(3) → 85>=90? NÃO → level=3
- value=95: 95>=20? SIM(1) → 95>=50? SIM(2) → 95>=75? SIM(3) → 95>=90? SIM(4) → 95>=97? NÃO → level=4

#### categorical

```yaml
dewarp_flag:
  type: categorical
  mapping:
    0: 1     # valor 0 → nível 1 (crítico: sem dewarp)
    1: 5     # valor 1 → nível 5 (excelente: dewarp aplicado)
  messages:
    - "Dewarp nao aplicado (critico)"
    - "Dewarp ausente (indisponivel)"
    - "Dewarp aplicado (aceitavel)"
    - "Dewarp aplicado (bom)"
    - "Dewarp aplicado (excelente)"
```

#### range_best

```yaml
speed_3d_ms:
  type: range_best
  levels:
    - [0.0, 2.0]      # nível 1: velocidade muito baixa
    - [2.0, 4.0]      # nível 2: velocidade baixa
    - [4.0, 10.0]     # nível 3: OK
    - [10.0, 15.0]    # nível 4: boa
    - [16.0, inf]     # nível 5: alta estável
```

### Conversão Nível → Score

Em `PqiUtil._level_to_score()`:

```python
Nível 1 (crítico)    →  0 pontos
Nível 2 (ruim)       → 25 pontos
Nível 3 (regular)    → 50 pontos
Nível 4 (bom)        → 75 pontos
Nível 5 (excelente)  → 100 pontos
```

### Fórmula do PQI Final

```python
pqi_score = total_weighted_score / total_weight
# Onde:
#   total_weighted_score = Σ(score_raw * weight) para cada indicador
#   total_weight = Σ(weight) para cada indicador
#   score_raw = _level_to_score(level)
```

**Exemplo prático**:

| Indicador | Nível | Score Raw | Peso | Weighted |
|-----------|-------|-----------|------|----------|
| DewarpFlag | 5 | 100 | 2.0 | 200.0 |
| RtkDiffAge | 4 | 75 | 1.5 | 112.5 |
| XYDifference | 3 | 50 | 1.0 | 50.0 |
| ZDifference | 5 | 100 | 1.0 | 100.0 |
| RtkEffectivePrecision | 4 | 75 | 1.0 | 75.0 |
| MotionBlurRisk | 4 | 75 | 0.25 | 18.75 |
| FOverlap | 3 | 50 | 0.25 | 12.5 |

```
Total Weighted = 200 + 112.5 + 50 + 100 + 75 + 18.75 + 12.5 = 568.75
Total Weight   = 2.0 + 1.5 + 1.0 + 1.0 + 1.0 + 0.25 + 0.25 = 7.0
PQI            = 568.75 / 7.0 = 81.25 → "Muito boa"
```

---

## 3. Todos os Thresholds do Sistema (config.yaml)

### 3.1 Lower Better (quanto menor, melhor)

| Threshold | Levels | Unidade | Nível 1 (crítico) | Nível 5 (excelente) |
|-----------|--------|---------|-------------------|-------------------|
| `gsd_cm` | [15, 10, 7, 5, inf] | cm/px | GSD > 15 | GSD ≤ 5 |
| `motion_blur_risk` | [1.5, 1.2, 0.7, 0.5, inf] | pixels | > 1.5 | ≤ 0.5 |
| `rtk_std_lon` | [0.050, 0.030, 0.020, 0.010, inf] | metros | > 0.050 | ≤ 0.010 |
| `rtk_std_lat` | [0.050, 0.030, 0.020, 0.010, inf] | metros | > 0.050 | ≤ 0.010 |
| `rtk_std_hgt` | [0.100, 0.060, 0.040, 0.020, inf] | metros | > 0.100 | ≤ 0.020 |
| `rtk_effective_precision` | [0.100, 0.050, 0.020, 0.010, inf] | metros | > 0.100 | ≤ 0.010 |
| `shutter_life_pct` | [60, 35, 20, 10, inf] | % | > 60% | ≤ 10% |
| `sensor_temp_c` | [48, 45, 43, 40, inf] | °C | > 48°C | ≤ 40°C |
| `vertical_stability` | [2.0, 0.8, 0.3, 0.1, inf] | metros | > 2.0 | ≤ 0.1 |
| `speed_variation_index` | [0.8, 0.4, 0.2, 0.05, inf] | - | > 0.8 | ≤ 0.05 |
| `gimbal_angular_velocity` | [80, 40, 20, 5, inf] | °/s | > 80 | ≤ 5 |
| `yaw_alignment_error` | [30, 15, 10, 5, inf] | ° | > 30° | ≤ 5° |
| `trajectory_smoothness` | [100, 50, 20, 5, inf] | ° | > 100° | ≤ 5° |
| `xy_difference` | [0.10, 0.05, 0.02, 0.0, inf] | metros | > 0.10 | = 0.0 |
| `z_difference` | [0.10, 0.05, 0.02, 0.0, inf] | metros | > 0.10 | = 0.0 |
| `abrupt_change_flag` | [3.0, 2.0, 1.5, 1.0, inf] | ratio | > 3.0x | ≤ 1.0x |
| `rtk_diff_age` | [5.0, 2.0, 1.0, 0.5, inf] | segundos | > 5.0 | ≤ 0.5 |

### 3.2 Higher Better (quanto maior, melhor)

| Threshold | Levels | Unidade | Nível 1 (crítico) | Nível 5 (excelente) |
|-----------|--------|---------|-------------------|-------------------|
| `photogrammetry_quality_index` | [45, 60, 75, 85, 95] | 0-100 | < 45 | ≥ 95 |
| `orthorectification_potential` | [35, 45, 55, 65, 72] | 0-100 | < 35 | ≥ 72 |
| `predicted_overlap` | [20, 50, 75, 90, 97] | % | < 20% | ≥ 97% |
| `capture_efficiency` | [0.05, 0.15, 0.30, 0.45, 0.55] | ratio | < 0.05 | ≥ 0.55 |
| `rtk_stability_score` | [90, 95, 98, 99, 99.9] | 0-100 | < 90 | ≥ 99.9 |

### 3.3 Range Best

| Threshold | Faixas | Nível 1 | Nível 5 (excelente) |
|-----------|--------|---------|-------------------|
| `speed_3d_ms` | [0-2], [2-4], [4-10], [10-15], [16-inf] | 0-2 m/s | 16+ m/s |
| `incidence_angle` | [0-80], [80-90], [90-98], [98-108], [108-120] | 0-80° | 108-120° |

### 3.4 Categorical

| Threshold | Mapeamento | Nível 1 | Nível 5 |
|-----------|------------|---------|---------|
| `light_consistency` | Unknown→1, Inconsistent→2, Consistent→5 | Unknown | Consistent |
| `is_valid_sequence_prev` | 0→1, 1→5 | 0 (inválida) | 1 (válida) |
| `is_valid_sequence_next` | 0→1, 1→5 | 0 (inválida) | 1 (válida) |
| `ev_classification` | noite/escuro→1, indoor/sombra→2, nublado→3, luz solar normal→4, sol muito forte/neve→5 | noite/escuro | sol muito forte/neve |
| `dewarp_flag` | 0→1, 1→5 | 0 (sem dewarp) | 1 (com dewarp) |
| `light_source_classification` | Unknown→1, Fluorescent→3, Daylight→5 | Unknown | Daylight |

---

## 4. Extratores Customizados (Value Extractors)

### 4.1 RTK Effective Precision (`_extract_rtk_level`)

Diferente dos outros indicadores, o **RTK Effective Precision** tem um extrator que:
1. Busca os 3 STD do RTK: `RtkStdLon`, `RtkStdLat`, `RtkStdHgt`
2. Calcula a média (`avg_std`)
3. Classifica via `RangeMetadataManager.classify("rtk_effective_precision", avg_std)` → nível 1-5
4. Retorna o **nível** diretamente (não o valor bruto)

```python
rtk_stds = []
for key in ["RtkStdLon", "RtkStdLat", "RtkStdHgt"]:
    raw = record.get(key)
    if raw is not None:
        rtk_stds.append(float(str(raw).replace(",", ".")))
if len(rtk_stds) >= 2:
    avg_std = sum(rtk_stds) / len(rtk_stds)
    level, _ = _range_manager.classify("rtk_effective_precision", avg_std)
    return float(level)
return 3.0  # fallback: nível médio
```

### 4.2 Dewarp Flag (`_extract_dewarp_value`)

Retorna nível direto baseado no valor do campo:

| DewarpFlag | Nível | Significado |
|------------|-------|-------------|
| `"0"` | 5 | Dewarp aplicado (excelente) |
| `"1"` | 1 | Sem dewarp (crítico) |
| `None`/ausente | 3 | Desconhecido (regular) |

---

## 5. Indicadores com Bypass (`bypass_classify: True`)

Quando um indicador tem `bypass_classify: True`, o PqiUtil **não** usa o `RangeMetadataManager` para classificar. Em vez disso, o `value_extractor` já retorna o **nível (1-5)** pronto:

```python
if bypass:
    # value já é o nível (1-5) — usa diretamente
    level = int(round(value))
    level = max(1, min(5, level))
    threshold_msg = f"Nivel {level} (bypass)"
```

Indicadores com bypass:
1. **RtkEffectivePrecision** — o extrator classifica internamente via RangeMetadataManager e retorna o nível
2. **DewarpFlag** — o extrator converte 0→5, 1→1, None→3

---

## 6. Sistema de Pontuação do PQI

### Classe PqiUtil

```python
class PqiUtil:
    _indicators = list(PQI_INDICATORS)  # configurável via configure()

    @classmethod
    def calculate(record, tool_key="pqi_util") -> (pqi_score, details):
        # details = [
        #   {"name": str, "level": int, "value": float,
        #    "score_raw": float, "score_weighted": float,
        #    "weight": float, "threshold_msg": str},
        #   ...
        # ]
        # pqi_score = weighted average (0-100)

    @staticmethod
    def interpret(pqi_score) -> str:
        # 90+  → "Excelente"
        # 80+  → "Muito boa"
        # 70+  → "Aceitável"
        # 50+  → "Risco moderado"
        # <50  → "Problemática"
```

### Interpretação textual

| Faixa PQI | Classificação | Ação recomendada |
|-----------|---------------|------------------|
| **90-100** | Excelente | Manter padrão operacional |
| **80-89** | Muito boa | Revisar indicadores individuais abaixo de 4 |
| **70-79** | Aceitável | Corrigir indicadores com nível ≤ 2 |
| **50-69** | Risco moderado | Repetir faixas problemáticas |
| **0-49** | Problemática | Reprocessar bloco, verificar dewarp/RTK |

### Tratamento de Valores Indisponíveis

Quando um indicador não tem valor disponível (`value is None`):
- Nível assume **3 (regular)**
- Score = 50 pontos
- Mensagem: "Indisponivel (OK default)"

Isso evita que fotos com dados parciais sejam penalizadas excessivamente.

---

## 7. Sistema de Alertas (AlertManager)

`AlertManager.analyze(results, agg)` gera alertas em 3 severidades:

| Severidade | Prioridade | Significado |
|------------|------------|-------------|
| `CRITICO` | Máxima | Bloqueia processamento, requer ação imediata |
| `ALERTA` | Média | Impacta qualidade, requer atenção |
| `INFO` | Baixa | Informativo, monitoramento |

### Categorias de Alerta

| Categoria | Gatilho | Severidade típica |
|-----------|---------|-------------------|
| **DEWARP** | Qualquer foto com DewarpFlag=0 | CRITICO |
| **RTK_FLAG** | Sinal não-fixo > 5% das fotos | CRITICO/ALERTA |
| **RTK** | RtkStdLat/Lon/Hgt acima do threshold | CRITICO/ALERTA |
| **MOTION_BLUR** | Blur > 0.5 (alerta) ou > 1.0 (crítico) | CRITICO/ALERTA |
| **GIMBAL** | GimbalOffset > 15° (alerta) ou > 30° (crítico) | CRITICO/ALERTA |
| **OVERLAP** | > 30% das fotos com overlap < 60% | CRITICO/ALERTA |
| **YAW** | > 5% das fotos com yaw oposto (> 150°) | ALERTA |
| **GSD_VARIATION** | Desvio padrão GSD > 0.5cm em um voo | ALERTA |
| **ALTITUDE** | Faltando altitude em > 10% das fotos | CRITICO/ALERTA/INFO |
| **TEMPERATURE** | Sensor > 45°C (alerta) ou > 48°C (crítico) | CRITICO/ALERTA |

### Estrutura do AlertRecord

```python
@dataclass
class AlertRecord:
    severity: str          # 'CRITICO', 'ALERTA', 'INFO'
    category: str          # 'DEWARP', 'RTK', 'GSD', etc.
    title: str             # Título curto
    detail: str            # Descrição com métricas
    impact: str            # Impacto no produto final
    action: str            # Ação recomendada
    affected_count: int    # Nº de imagens/voos afetados
    total_count: int       # Total analisado
    affected_pct: float    # Percentual afetado
    threshold_value: float # Limiar que disparou
    actual_value: float    # Valor medido
    flight_ids: list       # Voos afetados
    photos: list           # Fotos críticas (limitado a 20)
```

---

## 8. Métricas Avançadas (compute_advanced_metrics)

`AlertManager.compute_advanced_metrics(results)` calcula dezenas de métricas agregadas:

### RTK
| Métrica | Descrição |
|---------|-----------|
| `rtk_diff_age_mean` | Idade média do sinal RTK (segundos) |
| `rtk_diff_age_max` | Idade máxima do sinal RTK |
| `rtk_diff_age_p95` | Percentil 95 da idade RTK |
| `rtk_effective_precision_mean` | Precisão efetiva RTK média |
| `rtk_effective_precision_max` | Precisão efetiva RTK máxima |

### Gimbal & Yaw
| Métrica | Descrição |
|---------|-----------|
| `gimbal_offset_mean` | Desalinhamento médio do gimbal (°) |
| `gimbal_offset_std` | Desvio padrão do offset |
| `gimbal_offset_max` | Offset máximo |
| `gimbal_offset_over_1deg_pct` | % de fotos com offset > 1° |
| `yaw_inconsistent_pct` | % de fotos com yaw oposto |

### Overlap & Blur
| Métrica | Descrição |
|---------|-----------|
| `overlap_mean` | Overlap médio (%) |
| `overlap_below_ideal_pct` | % de fotos abaixo de 60% |
| `motion_blur_mean` | Motion blur médio |

### Velocidade e Variação
| Métrica | Descrição |
|---------|-----------|
| `speed_ms_mean` | Velocidade 3D média (m/s) |
| `speed_ms_recommended` | Faixa recomendada (5-10 m/s) |
| `speed_variation_mean` | Índice de variação de velocidade |

### Iluminação
| Métrica | Descrição |
|---------|-----------|
| `light_inconsistent_pct` | % de fotos com luz inconsistente |

### Estatísticas de Tendência (compute_quality_trends)

| Métrica | Descrição |
|---------|-----------|
| `pqi_first_quartile_mean` | PQI médio do primeiro quartil temporal |
| `pqi_last_quartile_mean` | PQI médio do último quartil temporal |
| `pqi_delta` | Variação do PQI ao longo do tempo |
| `morning_pqi_mean` | PQI médio das fotos da manhã (< 11h) |
| `midday_pqi_mean` | PQI médio das fotos do meio-dia (11-15h) |

### Análise por Strip (compute_strip_analysis)

Para cada faixa (strip) do voo:
| Métrica | Descrição |
|---------|-----------|
| `strip_id` | ID da faixa |
| `images` | Nº de imagens na faixa |
| `mean_score` | Score médio (nível 1-5) |
| `mean_overlap` | Overlap médio (%) |
| `overlap_below_ideal_pct` | % abaixo do ideal |

Strips problemáticas: `mean_score < 3.0` ou `overlap_below_ideal_pct > 30%`

---

## 9. Integração no Pipeline

### 1. CustomPhotosFieldsUtil.calculate_all_custom_fields()

Este é o **ponto de entrada** principal que:
1. Para cada foto, calcula todos os campos individuais (GSD, shutter, blur, EV)
2. Calcula campos de sequência (time_since, distância, velocidade, direção)
3. Calcula campos de qualidade (RTK, overlap, ortho score, estabilidade)
4. Calcula diferenças MRK vs metadados (XY/Z diff)
5. **Pós-processamento**: para cada foto, chama `PqiUtil.calculate(item)` para obter o PQI
6. Também classifica `AbruptChangeFlag` baseado na mediana de tempo/distância

```python
# Pós-processamento
for filename, item in result.items():
    # 1. Calcula PQI
    pqi_score, pqi_details = PqiUtil.calculate(item, tool_key=tool_key)
    item[MetadataFieldKey.PHOTOGRAMMETRY_QUALITY_INDEX.value] = pqi_score

    # 2. Classifica AbruptChangeFlag
    abrupt_ratio = max(time_ratio, geo_ratio)
    _, abrupt_label = range_metadata_manager.classify("abrupt_change_flag", abrupt_ratio)
    item[MetadataFieldKey.ABRUPT_CHANGE_FLAG.value] = abrupt_label
```

### 2. ReportGenerationService.generate_from_json()

No pipeline de relatório:
1. Carrega JSON v2.0
2. Cria `IMGMetadata(record)` para cada foto
3. Chama `record.score()` para classificar cada indicador em nível 1-5
4. `AggregateAnalyzer.analyze(results)` → estatísticas agregadas + alertas
5. Gera gráficos (Chart.js), mapa (Leaflet) e relatório HTML (Jinja2)

---

## 10. Exemplos Completos

### Exemplo 1: Calculando PQI manualmente

```python
from utils.mrk.PqiUtil import PqiUtil

# Record com dados de uma foto
record = {
    "MotionBlurRisk": 0.35,      # nível 5 (≤ 0.5)
    "FOverlap": 82.5,             # nível 4 (75 ≤ 82.5 < 90)
    "RtkStdLon": 0.008,           # usado pelo extrator RTK
    "RtkStdLat": 0.012,
    "RtkStdHgt": 0.015,
    "XYDifference": 0.03,         # nível 4 (0.02 < 0.03 ≤ 0.05)
    "ZDifference": 0.01,          # nível 4 (0.0 < 0.01 ≤ 0.02)
    "DewarpFlag": "0",            # valor 0 → nível 5 (excelente)
    "RtkDiffAge": 0.8,            # nível 4 (0.5 < 0.8 ≤ 1.0)
}

pqi_score, details = PqiUtil.calculate(record)

print(f"PQI: {pqi_score}")  # Exemplo: 87.5
print(f"Interpretação: {PqiUtil.interpret(pqi_score)}")  # "Muito boa"

for d in details:
    print(f"{d['name']}: nível {d['level']}, score {d['score_raw']}, "
          f"peso {d['weight']}, ponderado {d['score_weighted']}")
```

### Exemplo 2: Analisando alertas de qualidade

```python
from utils.report.AlertManager import AlertManager

results = [IMGMetadata(record) for record in records]
agg = AggregateAnalyzer.analyze(results)

alerts = AlertManager.analyze(results, agg)

for alert in alerts:
    print(f"[{alert.severity}] {alert.category}: {alert.title}")
    print(f"  {alert.detail}")
    print(f"  Impacto: {alert.impact}")
    print(f"  Ação: {alert.action}")
    print(f"  Afetados: {alert.affected_count}/{alert.total_count} ({alert.affected_pct:.1f}%)")
    print()
```

### Exemplo 3: Métricas avançadas e recomendações

```python
advanced = AlertManager.compute_advanced_metrics(results)
trends = AlertManager.compute_quality_trends(results)
strip_analysis = AlertManager.compute_strip_analysis(results)
recommendations = AlertManager.compute_recommendations(advanced)

print(f"PQI inicial: {trends['pqi_first_quartile_mean']}")
print(f"PQI final: {trends['pqi_last_quartile_mean']}")
print(f"Tendência: {trends['pqi_delta']:+.2f} pontos")

for rec in recommendations:
    print(f"→ {rec}")
```

### Exemplo 4: Strips problemáticas

```python
strip_data = AlertManager.compute_strip_analysis(results)
for s in strip_data['problematic_strips']:
    print(f"Strip {s['strip_id']}: {s['images']} fotos, "
          f"score médio {s['mean_score']}, "
          f"overlap baixo: {s['overlap_below_ideal_pct']}%")
```

---

## 11. Resumo de Conceitos-Chave

| Conceito | O que é | Faixa |
|----------|---------|-------|
| **Valor bruto** | Valor original do campo (ex: MotionBlurRisk=0.35) | Variável |
| **Threshold** | Pontos de corte no config.yaml que definem os níveis | Configurável |
| **Nível (1-5)** | Classificação do valor contra os thresholds | 1 (crítico) a 5 (excelente) |
| **Score raw (0-100)** | Conversão do nível para pontuação linear | 0, 25, 50, 75, 100 |
| **Score weighted** | Score raw × peso do indicador | 0 a 200 (peso máximo 2.0) |
| **PQI final** | Média ponderada de todos os scores | 0-100 |
| **Alerta** | Disparado quando métricas ultrapassam limiares operacionais | CRITICO/ALERTA/INFO |

### Regras de Ouro

1. **DewarpFlag é o indicador mais importante** (peso 2.0, ~29% do PQI) — sem dewarp, o bloco inteiro é comprometido
2. **Valores ausentes não penalizam excessivamente** — nível 3 (50 pontos) é o fallback padrão
3. **RTK Effective Precision é indireto** — usa a média dos 3 STD (Lon/Lat/Hgt) para classificar
4. **Lower Better vs Higher Better** — sempre verificar o `type` no config.yaml para interpretar corretamente
5. **Alertas CRITICO bloqueiam** — dewarp desativado ou RTK instável geram alertas que exigem ação antes do processamento

---

## 12. Dependências

| Módulo | Caminho | Responsabilidade |
|--------|---------|-----------------|
| **PqiUtil** | utils/mrk/PqiUtil.py | Cálculo do PQI (indicadores, pesos, classificação) |
| **RangeMetadataManager** | utils/report/RangeMetadataManager.py | Singleton que carrega/lê config.yaml e classifica valores |
| **CustomPhotosFieldsUtil** | utils/mrk/CustomPhotosFieldsUtil.py | Cálculo de todos os campos derivados + orquestração do PQI |
| **AlertManager** | utils/report/AlertManager.py | Geração de alertas de qualidade por categoria |
| **MetadataFieldKey** | core/enum/MetadataFieldKey.py | Enum com todas as chaves de campo (EXIF, XMP, Custom, MRK) |
| **config.yaml** | resources/reports/config.yaml | 24 thresholds configuráveis com níveis e mensagens |

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-06-03 | 1.0.0 | Criação inicial: documentação completa do PQI, thresholds, alertas e scoring |