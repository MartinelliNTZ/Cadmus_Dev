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
        "metadata_key": MetadataFieldKey.MOTION_BLUR_RISK,
        "threshold_name": "motion_blur_risk",  # lower_better
        "weight": 0.25,
    },
    {
        "metadata_key": MetadataFieldKey.F_OVERLAP,
        "threshold_name": "predicted_overlap",  # higher_better
        "weight": 0.25,
    },
    {
        "metadata_key": MetadataFieldKey.XY_DIFFERENCE,
        "threshold_name": "xy_difference",  # lower_better
        "weight": 1.0,
    },
    {
        "metadata_key": MetadataFieldKey.Z_DIFFERENCE,
        "threshold_name": "z_difference",  # lower_better
        "weight": 1.0,
    },
    {
        "metadata_key": MetadataFieldKey.RTK_DIFF_AGE,
        "threshold_name": "rtk_diff_age",  # lower_better
        "weight": 1.5,
    },
    # INDICADORES COM BYPASS (value_extractor já retorna nível 1-5)
    {
        "metadata_key": MetadataFieldKey.RTK_EFFECTIVE_PRECISION,
        "threshold_name": "rtk_effective_precision",
        "weight": 1.0,
        "value_extractor": lambda r: _extract_rtk_level(r),
        "bypass_classify": True,
    },
    {
        "metadata_key": MetadataFieldKey.DEWARP_FLAG,
        "threshold_name": "dewarp_flag",
        "weight": 2.0,  # MAIOR PESO — dewarp é crítico
        "value_extractor": lambda r: _extract_dewarp_value(r),
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

> **DewarpFlag** tem o maior peso (2.0) porque fotos sem dewarp (Flag=0) comprometem **todo o bloco** fotogramétrico — distorção sistemática inviabiliza aerotriangulação.

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
| `categorical` | Mapeamento direto valor → nível | dewarp_flag: 0→1 (crítico) |

#### lower_better

```yaml
motion_blur_risk:
  type: lower_better
  levels: [1.5, 1.2, 0.7, 0.5, inf]
  messages:
    - "Motion blur critico"                  # nível 1
    - "Motion blur alto"                     # nível 2
    - "Motion blur moderado"                 # nível 3
    - "Motion blur baixo"                    # nível 4
    - "Motion blur minimo"                   # nível 5
```

**Lógica**: `level = sum(1 for cut in levels if vnum <= cut)`

#### higher_better

```yaml
predicted_overlap:
  type: higher_better
  levels: [20, 50, 75, 90, 97]
  messages:
    - "Sobreposicao critica"                # nível 1
    - "Sobreposicao baixa"                  # nível 2
    - "Sobreposicao OK"                     # nível 3
    - "Sobreposicao boa"                    # nível 4
    - "Sobreposicao excelente"              # nível 5
```

**Lógica**: `level = sum(1 for cut in levels if vnum >= cut)`

#### categorical — DewarpFlag (caso especial)

```yaml
dewarp_flag:
  type: categorical
  mapping:
    0: 1     # DewarpFlag=0 = SEM DEWARP = critico (nivel 1)
    # None/null/ausente = DEWARP APLICADO = excelente (nivel 5)
  messages:
    - "Dewarp nao aplicado (critico)"
    - "Dewarp ausente (indisponivel)"
    - "Dewarp aplicado (aceitavel)"
    - "Dewarp aplicado (bom)"
    - "Dewarp aplicado (excelente)"
```

**IMPORTANTE:** No padrão DJI XMP, NÃO existe valor `"1"`. Apenas `"0"` indica sem dewarp. Qualquer outro valor (None, null, vazio, ausente) significa dewarp aplicado.

#### range_best

```yaml
speed_3d_ms:
  type: range_best
  levels:
    - [0.0, 2.0]      # nível 1
    - [2.0, 4.0]      # nível 2
    - [4.0, 10.0]     # nível 3
    - [10.0, 15.0]    # nível 4
    - [16.0, inf]     # nível 5
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
# total_weighted_score = Σ(score_raw * weight)
# total_weight = Σ(weight)
# score_raw = _level_to_score(level)
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
| `ev_classification` | noite/escuro→1, ..., sol muito forte/neve→5 | noite/escuro | sol muito forte/neve |
| `dewarp_flag` | 0→1 (crítico). None/null/ausente = padrão → 5 | 0 (sem dewarp) | None/null/ausente (dewarp aplicado) |
| `light_source_classification` | Unknown→1, Fluorescent→3, Daylight→5 | Unknown | Daylight |

---

## 4. Extratores Customizados (Value Extractors)

### 4.1 RTK Effective Precision (`_extract_rtk_level`)

Busca os 3 STD do RTK (`RtkStdLon`, `RtkStdLat`, `RtkStdHgt`), calcula a média (`avg_std`), classifica via `RangeMetadataManager` e retorna o **nível** diretamente.

### 4.2 Dewarp Flag (`_extract_dewarp_value`)

**Convenção DJI XMP:**
- **`"0"`** = SEM DEWARP (imagem bruta/distorcida) → **nível 1 (crítico)**
- **`None/null/""/ausente`** = DEWARP APLICADO (imagem corrigida) → **nível 5 (excelente)**
- **Não existe valor `"1"` no padrão DJI** — se não é 0, é dewarp aplicado

| DewarpFlag | Nível | Significado |
|------------|-------|-------------|
| `"0"` | **1** | **Sem dewarp (crítico)** — 0 pontos. Imagem com distorção de lente, compromete aerotriangulação |
| `None/null/""` | **5** | **Dewarp aplicado (excelente)** — 100 pontos. Imagem corrigida, pronta para processamento |
| Ausente do registro | **5** | Considera-se dewarp aplicado |

---

## 5. Indicadores com Bypass (`bypass_classify: True`)

Indicadores cujo `value_extractor` já retorna o nível 1-5 diretamente, sem passar pelo `RangeMetadataManager`:

1. **RtkEffectivePrecision** — classifica internamente a média dos 3 STD
2. **DewarpFlag** — converte 0→1 (crítico), None/null/ausente→5 (excelente)

---

## 6. Sistema de Pontuação do PQI

### Classe PqiUtil

```python
class PqiUtil:
    _indicators = list(PQI_INDICATORS)

    @classmethod
    def calculate(record, tool_key="pqi_util") -> (pqi_score, details)
    @staticmethod
    def interpret(pqi_score) -> str
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

---

## 7. Sistema de Alertas (AlertManager)

`AlertManager.analyze(results, agg)` gera alertas em 3 severidades: `CRITICO`, `ALERTA`, `INFO`.

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
    title: str
    detail: str
    impact: str
    action: str
    affected_count: int
    total_count: int
    affected_pct: float
    threshold_value: float
    actual_value: float
    flight_ids: list
    photos: list           # Limitado a 20
```

---

## 8. Métricas Avançadas

`AlertManager.compute_advanced_metrics(results)` — RTK, Gimbal, Yaw, Overlap, Blur, Speed, Luz.

`AlertManager.compute_quality_trends(results)` — PQI por quartil temporal, delta, período do dia.

`AlertManager.compute_strip_analysis(results)` — análise por faixa (strip): score médio, overlap, % abaixo do ideal.

---

## 9. Integração no Pipeline

### Fluxo completo:

1. `CustomPhotosFieldsUtil.calculate_all_custom_fields()` — calcula GSD, overlap, RTK, estabilidade, diferenças MRK
2. No pós-processamento: `PqiUtil.calculate(item)` para cada foto → calcula PQI (0-100)
3. Classifica `AbruptChangeFlag` baseado na mediana de tempo/distância
4. `ReportGenerationService.generate_from_json()` → cria IMGMetadata, score, agrega, gera HTML

---

## 10. Regras de Ouro

1. **DewarpFlag=0 = SEM DEWARP = crítico** (peso 2.0, ~29% do PQI). Se DewarpFlag=None/null/ausente, considera-se dewarp aplicado (excelente). Não existe valor "1".
2. **Valores ausentes não penalizam excessivamente** — nível 3 (50 pontos) é o fallback padrão.
3. **RTK Effective Precision é indireto** — usa a média dos 3 STD (Lon/Lat/Hgt) para classificar.
4. **Alertas CRITICO bloqueiam** — dewarp desativado (Flag=0) ou RTK instável exigem ação antes do processamento.

---

## 11. Dependências

| Módulo | Caminho | Responsabilidade |
|--------|---------|-----------------|
| **PqiUtil** | utils/mrk/PqiUtil.py | Cálculo do PQI (indicadores, pesos, classificação) |
| **RangeMetadataManager** | utils/report/RangeMetadataManager.py | Singleton que carrega/lê config.yaml e classifica valores |
| **CustomPhotosFieldsUtil** | utils/mrk/CustomPhotosFieldsUtil.py | Cálculo de todos os campos derivados + orquestração do PQI |
| **AlertManager** | utils/report/AlertManager.py | Geração de alertas de qualidade por categoria |
| **MetadataFieldKey** | core/enum/MetadataFieldKey.py | Enum com todas as chaves de campo |
| **config.yaml** | resources/reports/config.yaml | 24 thresholds configuráveis com níveis e mensagens |

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-06-03 | 1.0.0 | Criação inicial |
| 2026-06-03 | 1.0.1 | Correção DewarpFlag: 0=sem dewarp (crítico). None/null/ausente=dewarp aplicado (excelente). Não existe valor "1" no padrão DJI XMP |