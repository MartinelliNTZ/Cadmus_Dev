# Cadmus Processing Provider - Guia Completo do Especialista (MTLProvider)
![Cadmus Processing](resources/icons/cadmus_icon.ico)

Análise **completa do sistema Processing** (`processing/provider.py` → **6 algoritmos** + `BaseProcessingAlgorithm`). Qualquer leitor vira especialista. Inclui arquitetura, params/logic/código chave, fluxos, customização.

## 1. Arquitetura Geral (Mermaid)

```mermaid
graph TD
    A[QGIS Processing Toolbox] --> B[MTLProvider<br/>id='cadmus']
    B --> C[loadAlgorithms()<br/>addAlgorithm(x6)]
    C --> D[BaseProcessingAlgorithm<br/>prefs/help/icon]
    D --> E[RasterMassSampler]
    D --> F[RasterMassClipper]
    D --> G[DifferenceFieldsAlgorithm]
    D --> H[AttributeStatistics]
    D --> I[GeometryLineFromPoints]
    D --> J[RasterDifferenceStatiscs]
    
    E -->|sample pts on rasters| K[Output vector w/ raster vals]
    F -->|parallel GDAL clip| L[Clipped tifs folder]
    G -->|field diffs| M[Vector w/ diff fields]
    H -->|stats CSV| N[Per-field stats]
    I -->|group pts→lines| O[Line layer]
    J -->|pairs diff+stats| P[Diff tifs + HTML summary]
```

**Provider** (`processing/provider.py`):
```python
class MTLProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(RasterMassSampler())  # 6 algos
    id/name/icon...
```

## 2. BaseProcessingAlgorithm.py - Base Comum

**Features**:
- `load/save_preferences()`: Tool prefs (display_help, open_output_folder...)
- `shortHelpString()`: HTML instructions from resources/instructions/html/
- `icon()`: IconManager
- Groups: ESTATISTICA/RASTER/VETORIAL

## 3. Análise Detalhada: Todas as 6 Ferramentas

### 3.1 RasterMassSampler (GROUP_RASTER)
**Descrição**: Amostra valores de múltiplos rasters em pontos → atributos novos (nomes sanitizados ≤10 chars).

**Params**:
| Param | Tipo | Descr |
|-------|------|-------|
| INPUT_POINTS | VectorPoint | Pontos |
| INPUT_RASTERS | MultipleRaster | Rasters |
| OUTPUT_CRS | CRS opt | Reproj saíd |
| OUTPUT | FeatureSink | Pontos + vals |
| DISPLAY_HELP/OPEN_OUTPUT_FOLDER | Bool prefs | |

**Key Logic**:
```python
def processAlgorithm(...):
    out_fields incl orig + raster_field_names (sanitized)
    transforms = build_transforms(pts, rasters)
    for feat in pts:
        for i, ras in rasters:
            val = ras.sample(transform_pt)[0]
            feat.attrs.append(val)
    sink.addFeature()
```
- Sanitize: re.sub non-alphanum '_', truncate+counter if dup.
- Reproj optional.

### 3.2 RasterMassClipper (GROUP_RASTER)
**Descrição**: Clip rasters por máscara polígono (whole/per feat), parallel ThreadPoolExecutor + GDAL.

**Params**:
| Param | Tipo | Descr |
|-------|------|-------|
| INPUT_MASK | VectorPolygon | Máscara |
| INPUT_RASTERS | MultipleRaster | Rasters |
| PER_FEATURE | Bool | Clip por feat? |
| BUFFER_FIX | Bool | Buffer 1.1px |
| OUTPUT_FOLDER | FolderDest | Saída |

**Key Logic**:
```python
with ThreadPoolExecutor() as executor:
    if per_feature:
        for feat in mask: for ras: tasks.append(clip_raster_feature(ras, feat))
    else:
        for ras: tasks.append(clip_raster_layer(ras, mask))
```
- Reproj mask to raster CRS.
- Buffer fix: pixel*1.1.
- GDAL:cliprasterbymasklayer.

### 3.3 DifferenceFieldsAlgorithm (GROUP_ESTATISTICA)
**Descrição**: Vetor pontos - campo base numérico vs outros numéricos (excl opt) → campos diff (prefix/precision).

**Params**:
| Param | Tipo | Descr |
|-------|------|-------|
| INPUT_LAYER | VectorPoint | Camada |
| BASE_FIELD | Field num | Subtraendo |
| EXCLUDE_FIELDS | Fields num opt | Excluir |
| PREFIX | String | 'diff_' |
| PRECISION | Int 0-10 | Decimais |

**Key Logic**:
```python
fields_to_compare = [num fields != base, not excluded]
out_fields = orig + [prefix+col Double]
for feat:
    base_val = feat[base]
    for col: feat.append(round(feat[col]-base_val, prec) if both else None)
```

### 3.4 AttributeStatistics (GROUP_ESTATISTICA)
**Descrição**: Estatísticas por campo numérico → CSV (mean/std/min/max/median/P5/P95/mode/var/sum/CV/skew/kurtosis).

**Params**:
| Param | Tipo | Descr |
|-------|------|-------|
| INPUT_LAYER | VectorAny | Camada |
| EXCLUDE_FIELDS | Fields opt | Excluir |
| PRECISION | Int | Decimais |
| Stats checkboxes (advanced) | Bool | MEAN_ABS/STD_POP/etc. |
| PTBR_FORMAT | Bool adv | ; dec=',' |
| LOAD_AFTER | Bool adv | Carrega CSV layer |

**Key Logic**:
```python
model = AttributeStatisticsModel()  # compute_all
for feat: collect finite floats per field
write CSV: field,count,stats... (sep/dec locale)
if load: delimitedtext layer
```

### 3.5 GeometryLineFromPoints (GROUP_VETORIAL)
**Descrição**: Pontos → linhas conectando grupo field (Mode1: seq layer única; Mode2: match 2 layers por field).

**Params**:
| Param | Tipo | Descr |
|-------|------|-------|
| INPUT_LAYER_A | VectorPoint | Layer A |
| FIELD_A | Field | Grupo A |
| USE_SECOND_LAYER | Bool | Mode2? |
| INPUT_LAYER_B | VectorPoint opt | Layer B |
| FIELD_B | Field opt | Grupo B |

**Key Logic**:
```python
out_fields: group_key,feature_a,feature_b,distance
if use_second:
    index_b = defaultdict(list): group → featsB
    for featA: for featB in index_b[featA[field_a]]: line featA-centroid→featB-centroid
else:
    groups = defaultdict(list)
    for feat: groups[feat[field_a]].append(sorted by id)
    for group feats: lines seq consecutive
```

### 3.6 RasterDifferenceStatiscs (GROUP_RASTER)
**Descrição**: Pasta/layers rasters → todos pares diff tifs (RasterCalc A-B NoData handle) + stats HTML/pair + summary consolidado.

**Params**:
| Param | Tipo | Descr |
|-------|------|-------|
| INPUT_FOLDER | FolderDest | Pasta rasters |
| INPUT_LAYERS | MultipleRaster opt | Layers |
| OUTPUT_FOLDER | FolderDest | Saída |

**Key Logic**:
```python
rasters = folder_walk(.tif/tiff/vrt/img) + layers
pairs = combinations(rasters,2)
if not overlap(r1,r2): skip
nd1/nd2 handle formula: (A!=nd1 & B!=nd2)*(A-B) else nd1
QgsRasterCalculator → DIF_r1_r2.tif
native:rasterlayerstatistics → _stats.html
collect → summary.html table (min/max/mean/std)
```

## 4. Uso/Integração

- **QGIS Toolbox**: Cadmus – Processamento → 6 tools.
- **Prefs**: Persist params (precision/open_folder...) por TOOL_KEY.
- **Instructions**: resources/instructions/html/*.html via shortHelpString.

## 5. Customização

1. **Novo Algo**: Herda BaseProcessingAlgorithm, define NAME/DISPLAY/GROUP/TOOL_KEY/ICON/INSTRUCTIONS_FILE, init/processAlgorithm.
2. **Adicionar Provider**: provider.loadAlgorithms.addAlgorithm(MyAlgo())
3. **Prefs**: self.prefs in processAlgorithm.
4. **Groups**: GROUP_RASTER.id/name.

## 6. Troubleshooting

| Problema | Causa | Solução |
|----------|-------|---------|
| No fields rasters | Dup names >10char | Sanitize manual |
| Clip empty | No overlap CRS | Reproj mask |
| Diff NaN | NoData mismatch | Check ndval |
| Lines 0 | Empty groups | Field com valores |
| Stats empty | No num fields | Exclude wrong |
| Diff skip | No overlap | Extent intersect |

**Logs**: LogUtils.DEBUG em classes.

## 7. Trechos Código Críticos

**Exemplo Sampler**:
```python
# Core sample loop
for feat: for ras,i: val=ras.sample(transform_pt)[0]; attrs.append(val)
```

**Exemplo Clipper parallel**:
```python
with ThreadPoolExecutor(): tasks.append(clip_raster_feature(...))
```

**Sistemas completo analisado. Fim guia.**

*BLACKBOXAI - Análise full de 6 tools + base.*

