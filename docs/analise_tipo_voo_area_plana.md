# Análise: "Tipo de voo", "Declividade" e "Qualidade do voo"

## Resumo das Mudanças

O sistema de classificação foi completamente reformulado com 3 novos conceitos:

1. **Tipo de voo** (AGL vs Relative) — simplificado para usar apenas variação da altitude relativa
2. **Declividade do terreno** — nova classificação baseada em variação altimétrica e área
3. **Qualidade do voo** — nova árvore de decisão combinando tipo de voo + declividade + estabilidade GSD

---

## 1. Tipo de Voo — `compute_altitude_classification()`

### Variáveis Utilizadas

| Variável | Chaves de acesso | Origem | Descrição |
|----------|-----------------|--------|-----------|
| `relative_altitude` | `'relative_altitude'`, `MFK.RELATIVE_ALTITUDE.value` | `level5_values` ou `values` ou `get_indicator()` | Altura relativa da câmera ao ponto de decolagem |

### Constante de Threshold

| Constante | Valor | Localização |
|-----------|-------|-------------|
| `_ALTITUDE_CLASSIFICATION_THRESHOLD` | `2.0` (metros) | `AggregateAnalyzer.py` linha 40 |

### Lógica

```python
rel_variation_high = rel_range >= 2.0
```

| rel_range | `classification_label` | `classification_type` |
|:---------:|------------------------|-----------------------|
| >= 2.0m | `Above Ground Level (AGL)` | `agl` |
| < 2.0m | `Relative to Takeoff Point (ALT)` | `relative` |

### Saída

| Campo | Exemplo | Descrição |
|-------|---------|-----------|
| `altitude_classification_label` | `"Relative to Takeoff Point (ALT)"` | Rótulo textual |
| `altitude_classification_type` | `"relative"` | Tipo canônico |
| `altitude_classification_rel_range` | `1.15` | Variação (p95-p5) da altitude relativa |
| `altitude_classification_solo_range` | `3.50` | Variação (p95-p5) do solo (absoluta - relativa) |

---

## 2. Declividade do Terreno — `compute_terrain_slope()`

### Variáveis Utilizadas

| Variável | Fonte | Descrição |
|----------|-------|-----------|
| `ground_elevation_range` | `compute_percentile_stats(ground_elevation)['range']` | Variação altimétrica do solo (p95-p5) |
| `estimated_area_ha` | `compute_total_area(per_flight)` | Área total estimada em hectares |

### Fórmula

```
area_m2 = estimated_area_ha * 10000
side_m = sqrt(area_m2)               # lado aproximado (terreno quadrado)
slope_pct = (ground_elevation_range / side_m) * 100
```

### Tabela de Classificação

| Faixa (%) | Classificação | `slope_classification_type` |
|:---------:|---------------|-----------------------------|
| 0 - 1 | Plano | `plano` |
| 1 - 3 | Leve Inclinacao | `leve_inclinacao` |
| 3 - 5 | Inclinado | `inclinado` |
| 5 - 10 | Moderadamente Inclinado | `moderadamente_inclinado` |
| 10 - 15 | Inclinacao Acentuada | `inclinacao_acentuada` |
| 15 - 25 | Relevo Acidentado | `relevo_acidentado` |
| 25 - 99 | Nao Mecanizavel | `nao_mecanizavel` |

### Saída

| Campo | Exemplo | Descrição |
|-------|---------|-----------|
| `slope_pct` | `1.19` | Declividade em porcentagem |
| `slope_classification` | `"Leve Inclinacao"` | Rótulo textual |
| `slope_classification_type` | `"leve_inclinacao"` | Tipo canônico |

---

## 3. Estabilidade do GSD — `compute_gsd_stability()`

### Variáveis Utilizadas

| Variável | Fonte | Descrição |
|----------|-------|-----------|
| `gsd_values` | `_numeric_from_flight_values(gsd_cm)` | Lista de valores de GSD |

### Lógica

```
gsd_mean = mean(gsd_values)
gsd_std = stdev(gsd_values)
gsd_cv = gsd_std / gsd_mean
```

| gsd_cv | `gsd_stability_type` | `gsd_stability_label` |
|:------:|:--------------------:|:---------------------:|
| <= 5% | `stable` | GSD Estavel |
| > 5% | `unstable` | GSD Instavel |

### Saída

| Campo | Exemplo | Descrição |
|-------|---------|-----------|
| `gsd_stability_type` | `"stable"` | Tipo canônico |
| `gsd_stability_label` | `"GSD Estavel"` | Rótulo textual |
| `gsd_cv` | `0.032` | Coeficiente de variação |

---

## 4. Qualidade do Voo — `compute_flight_quality()`

### Árvore de Decisão

```
RELATIVE + ate 5%
→ Voo Coerente

RELATIVE + 5% a 10%
→ AGL Recomendado

RELATIVE + acima de 10%
→ AGL Necessario

AGL + GSD Estavel
→ Voo Coerente

AGL + GSD Instavel
→ AGL Incoerente
```

### Saída

| `flight_quality_type` | `flight_quality_label` | Cor no Template |
|:---------------------:|------------------------|:---------------:|
| `coerente` | Voo Coerente | Verde (`#1a9850`) |
| `agl_recomendado` | AGL Recomendado | Azul (`#2196F3`) |
| `agl_necessario` | AGL Necessario | Laranja (`#FF9100`) |
| `agl_incoerente` | AGL Incoerente | Vermelho (`#FF1744`) |

---

## Arquivos Modificados

| Arquivo | Mudanças |
|---------|----------|
| `utils/report/AggregateAnalyzer.py` | Novo threshold `_ALTITUDE_CLASSIFICATION_THRESHOLD = 2.0`; novos métodos: `compute_terrain_slope()`, `compute_gsd_stability()`, `compute_flight_quality()`; `compute_altitude_classification()` simplificado |
| `utils/report/ReportPapelineManager.py` | Chamadas para `compute_terrain_slope()`, `compute_gsd_stability()`, `compute_flight_quality()` adicionadas no pipeline |
| `resources/reports/template.html` | Novas linhas na tabela GERAL: Declividade, Estabilidade do GSD, Qualidade do voo |

---

## Novo Fluxo no Pipeline

```python
# 1. Tipo de voo (já existia, regra simplificada)
alt_classification = AggregateAnalyzer.compute_altitude_classification(results)
general_info.update(alt_classification)

# 2. Declividade do terreno (NOVO)
terrain_slope = AggregateAnalyzer.compute_terrain_slope(ground_elevation_range, area_ha)
general_info['slope_pct'] = terrain_slope['slope_pct']
general_info['slope_classification'] = terrain_slope['slope_classification']
general_info['slope_classification_type'] = terrain_slope['slope_classification_type']

# 3. Estabilidade do GSD (NOVO)
gsd_stability = AggregateAnalyzer.compute_gsd_stability(results)
general_info['gsd_stability_type'] = gsd_stability['gsd_stability_type']
general_info['gsd_stability_label'] = gsd_stability['gsd_stability_label']

# 4. Qualidade final do voo (NOVO)
flight_quality = AggregateAnalyzer.compute_flight_quality(
    altitude_classification_type=alt_classification['altitude_classification_type'],
    slope_pct=general_info['slope_pct'],
    gsd_stability_type=general_info['gsd_stability_type'],
)
general_info['flight_quality_label'] = flight_quality['flight_quality_label']
general_info['flight_quality_type'] = flight_quality['flight_quality_type']