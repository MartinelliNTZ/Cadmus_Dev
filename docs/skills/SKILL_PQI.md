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

Em `PqiUtil.py`, os 7 indicadores que compõem o PQI com seus pesos e tipos:

| Indicador | Peso | % PQI | Tipo threshold |
|-----------|------|-------|----------------|
| DewarpFlag | 2.0 | 28.6% | categorical (bypass) |
| RtkDiffAge | 1.5 | 21.4% | lower_better |
| XYDifference | 1.0 | 14.3% | lower_better |
| ZDifference | 1.0 | 14.3% | lower_better |
| RtkEffectivePrecision | 1.0 | 14.3% | lower_better (bypass) |
| MotionBlurRisk | 0.25 | 3.6% | lower_better |
| FOverlap | 0.25 | 3.6% | higher_better |
| **Total** | **7.0** | **100%** | |

---

## 2. Sistema de Classificação por Níveis (1-5)

### Tipos de Threshold

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| `lower_better` | Quanto menor o valor, melhor | motion_blur, speed, temperatura |
| `higher_better` | Quanto maior o valor, melhor | overlap, PQI |
| `range_best` | Valor ideal em faixa específica | incidence_angle |
| `categorical` | Mapeamento direto valor → nível | dewarp, EV, luz |

### Proteção contra Nível 0

No `RangeMetadataManager.classify()`, após classificar o nível, há uma proteção:
```python
level = max(1, min(5, level))
```
Isso garante que mesmo que a lógica `higher_better` ou `lower_better` retorne 0 (ex: overlap=10% com thresholds [20,50,75,90,97]), o nível mínimo é sempre **1**.

### lower_better — Lógica

```yaml
motion_blur_risk:
  type: lower_better
  levels: [1.5, 1.2, 0.7, 0.5, inf]
```

`level = sum(1 for cut in levels if vnum <= cut)`

Exemplo com value=0.3:
- 0.3<=1.5? SIM → level=1
- 0.3<=1.2? SIM → level=2
- 0.3<=0.7? SIM → level=3
- 0.3<=0.5? SIM → level=4
- 0.3<=inf? SIM → level=5

### higher_better — Lógica

```yaml
predicted_overlap:
  type: higher_better
  levels: [20, 50, 75, 90, 97]
```

`level = sum(1 for cut in levels if vnum >= cut)`

Exemplo com value=85:
- 85>=20? SIM → level=1
- 85>=50? SIM → level=2
- 85>=75? SIM → level=3
- 85>=90? NÃO → level=3

Exemplo com value=10 (abaixo de todos os cuts):
- 10>=20? NÃO → level=0 → `max(1, 0)` = nível **1**

### Categorical — DewarpFlag (caso especial)

`DewarpFlag=0` aparece no JSON → **SEM DEWARP** = crítico (nível 1).
Quando o campo **não existe** no JSON (None/ausente) → **DEWARP APLICADO** = excelente (nível 5).
**Não existe valor "1" no padrão DJI XMP.**

### Conversão Nível → Score

```python
Nível 1 (crítico)    →  0 pontos
Nível 2 (ruim)       → 25 pontos
Nível 3 (regular)    → 50 pontos
Nível 4 (bom)        → 75 pontos
Nível 5 (excelente)  → 100 pontos
```

### Fórmula do PQI Final

```python
pqi_score = Σ(score_raw * weight) / Σ(weight)
```

---

## 3. Todos os Thresholds do Sistema (config.yaml)

### 3.1 Lower Better (quanto menor, melhor)

| Threshold | Levels | Unidade | Nível 1 (crítico) | Nível 5 (excelente) |
|-----------|--------|---------|-------------------|-------------------|
| `gsd_cm` | [15, 10, 7, 5, inf] | cm/px | GSD > 15 | GSD ≤ 5 |
| `motion_blur_risk` | [1.5, 1.2, 0.7, 0.5, inf] | pixels | > 1.5 | ≤ 0.5 |
| `speed_3d_ms` | [22, 18, 14, 8, inf] | m/s | > 22 | ≤ 8 |
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

| Threshold | Faixas | Nível 1 | Nível 5 |
|-----------|--------|---------|---------|
| `incidence_angle` | [0-80], [80-90], [90-98], [98-108], [108-120] | 0-80° | 108-120° |

### 3.4 Categorical

| Threshold | Mapeamento |
|-----------|------------|
| `light_consistency` | Unknown→1, Inconsistent→2, Consistent→5 |
| `is_valid_sequence_prev` | 0→1, 1→5 |
| `is_valid_sequence_next` | 0→1, 1→5 |
| `ev_classification` | noite/escuro→1, sol muito forte/neve→2, indoor/sombra→3, luz solar normal→4, **nublado→5** |
| `dewarp_flag` | 0→1 (sem dewarp). None/ausente→5 (dewarp aplicado, padrão) |
| `light_source_classification` | Unknown→1, Fluorescent→3, Daylight→5 |

---

## 4. DewarpFlag — Caso Especial e Crucial

### Comportamento no JSON do DJI XMP

No JSON extraído das imagens DJI:
- **`"DewarpFlag": 0`** aparece → **SEM DEWARP** = imagem bruta/distorcida (nível 1, crítico)
- **Campo DewarpFlag NÃO existe** (None/ausente) → **DEWARP APLICADO** = imagem corrigida (nível 5, excelente)
- **Não existe valor 1** no padrão DJI XMP

### Implementação no Código

**Em `PqiUtil._extract_dewarp_value()`**:
```python
# None/ausente = dewarp aplicado = nivel 5
# "0" = sem dewarp = nivel 1
if raw is None:
    return 5.0
if str(raw).strip() == "0":
    return 1.0
return 5.0  # qualquer outro = dewarp aplicado
```

**Em `CustomPhotosFieldsUtil._calculate_quality_scores()`** (Ortho score):
```python
# So pontua (+20) se NAO for "0" (ou seja, dewarp aplicado)
if str(dewarp_val).strip() != "0":
    score += 20
```

**No `AlertManager`**:
- DewarpFlag=0 → **CRITICO** — sempre alerta como crítico, pois qualquer imagem sem dewarp compromete o bloco.

---

## 5. Speed 3D (Velocidade de Voo) — Corrigido

A velocidade de voo agora é classificada como **lower_better** (quanto menor, melhor):

```yaml
speed_3d_ms:
  type: lower_better
  levels: [22.0, 18.0, 14.0, 8.0, inf]
  messages:
    - "Velocidade critica"      # > 22 m/s
    - "Velocidade alta"         # 18–22 m/s
    - "Velocidade OK"           # 14–18 m/s
    - "Velocidade boa"          # 8–14 m/s
    - "Velocidade ideal"        # ≤ 8 m/s
```

Justificativa: Velocidades acima de 8 m/s aumentam o risco de **motion blur e rolling shutter**. O ideal para fotogrametria é manter velocidade moderada (≤ 8 m/s). Velocidades > 22 m/s produzem imagens inutilizáveis.

---

## 6. EV Classification (Exposição) — Corrigido

A classificação de exposição foi reordenada baseada na qualidade para fotogrametria:

| Nível | Classificação | EV Range | Problema |
|-------|---------------|----------|----------|
| **5** | **Nublado** | 9-12 | **Melhor para fotogrametria** — luz difusa, sem sombras, textura uniforme |
| 4 | Luz solar normal | 12-14 | Bom, mas sombras podem atrapalhar matching |
| 3 | Indoor/sombra | 5-8 | Subexposição, ruído |
| 2 | **Sol muito forte/neve** | 15-999 | **Pior cenário** — sombras duras, superexposição, neve sem textura |
| 1 | Noite/escuro | 0-4 | Inviável |

**Por que "nublado" é nível 5?** Luz difusa elimina sombras projetadas no terreno, facilitando a extração de tie points e gerando ortofotos mais homogêneas. "Sol muito forte" e "neve" são os piores casos — contraste extremo e superfícies sem textura (neve) ou sombras profundas.

---

## 7. Sistema de Pontuação do PQI

### Classe PqiUtil

```python
class PqiUtil:
    @classmethod
    def calculate(record, tool_key="pqi_util") -> (pqi_score: float, details: list)
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
- Nível assume **3 (regular)** — score = 50 pontos
- Mensagem: "Indisponivel (OK default)"

Isso evita que fotos com dados parciais sejam penalizadas excessivamente.

---

## 8. Sistema de Alertas (AlertManager)

`AlertManager.analyze(results, agg)` gera alertas em 3 severidades: `CRITICO`, `ALERTA`, `INFO`.

### Categorias de Alerta

| Categoria | Gatilho | Severidade típica |
|-----------|---------|-------------------|
| **DEWARP** | Qualquer foto com DewarpFlag=0 | CRITICO |
| **RTK_FLAG** | Sinal não-fixo > 5% das fotos | CRITICO/ALERTA |
| **RTK** | RtkStdLat/Lon/Hgt acima do threshold | CRITICO/ALERTA |
| **MOTION_BLUR** | Blur > 0.5 (alerta) ou > 1.0 (crítico) | CRITICO/ALERTA |
| **GIMBAL** | GimbalOffset > 15° (alerta) | CRITICO/ALERTA |
| **OVERLAP** | > 30% das fotos com overlap < 60% | CRITICO/ALERTA |
| **YAW** | > 5% das fotos com yaw oposto | ALERTA |
| **GSD_VARIATION** | Desvio padrão GSD > 0.5cm | ALERTA |
| **ALTITUDE** | Faltando altitude em > 10% | CRITICO/ALERTA/INFO |
| **TEMPERATURE** | Sensor > 45°C | CRITICO/ALERTA |

---

## 9. Regras de Ouro

1. **DewarpFlag=0 = SEM DEWARP = crítico** (peso 2.0, ~29% do PQI). Se o campo não existe no JSON, considera-se dewarp aplicado (nota 5).
2. **Velocidade ideal ≤ 8 m/s** — quanto menor, melhor para fotogrametria.
3. **Nublado é a melhor condição de luz** — luz difusa sem sombras é ideal para matching.
4. **Nível 0 nunca ocorre** — `max(1, ...)` protege no RangeMetadataManager.
5. **Valores ausentes = nível 3 (neutro)** — não penalizam o PQI.
6. **Alertas CRITICO bloqueiam** — dewarp desativado ou RTK instável exigem ação.

---

## 10. Dependências

| Módulo | Caminho |
|--------|---------|
| **PqiUtil** | utils/mrk/PqiUtil.py |
| **RangeMetadataManager** | utils/report/RangeMetadataManager.py |
| **CustomPhotosFieldsUtil** | utils/mrk/CustomPhotosFieldsUtil.py |
| **AlertManager** | utils/report/AlertManager.py |
| **MetadataFieldKey** | core/enum/MetadataFieldKey.py |
| **EvClassEnum** | core/enum/EvClassEnum.py |
| **config.yaml** | resources/reports/config.yaml |

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-06-03 | 1.0.0 | Criação inicial |
| 2026-06-03 | 1.0.1 | Correção DewarpFlag: 0=sem dewarp (crítico). None/ausente=dewarp aplicado |
| 2026-06-03 | 1.0.2 | Speed 3D: mudado de `range_best` para `lower_better` (≤8 m/s=ideal). EV Classification: nublado→5 (melhor), sol muito forte→2 (pior). Proteção nível 0 documentada |