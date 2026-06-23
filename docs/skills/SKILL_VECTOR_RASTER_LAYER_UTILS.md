---
name: vector-raster-layer-utils
description: >
  Skill para utilização das classes principais de manipulação de camadas vetoriais e raster do Cadmus. Consulte antes de criar, modificar ou extrair dados de camadas QGIS.
---

# Vector & Raster Layer Utils

## Resumo Executivo

Este skill cobre as **11 classes principais** do diretório `utils/vector/` e `utils/raster/`, que orquestram toda a manipulação de camadas vetoriais e raster no Cadmus:

**Vetoriais (5 classes):**
| # | Classe | Arquivo | Responsabilidade |
|---|--------|---------|-----------------|
| 1 | **VectorLayerAttributes** | `utils/vector/VectorLayerAttributes.py` | Campos, atributos, dados tabulares |
| 2 | **VectorLayerGeometry** | `utils/vector/VectorLayerGeometry.py` | Transformações geométricas (buffer, explode, merge, criar linhas/pontos) |
| 3 | **VectorLayerMetrics** | `utils/vector/VectorLayerMetrics.py` | Métricas espaciais (comprimento, área, perímetro) |
| 4 | **VectorLayerProjection** | `utils/vector/VectorLayerProjection.py` | CRS, reprojeção, conversão de unidades |
| 5 | **VectorLayerSource** | `utils/vector/VectorLayerSource.py` | I/O, validação, salvamento e carregamento |

**Raster (6 classes):**
| # | Classe | Arquivo | Responsabilidade |
|---|--------|---------|-----------------|
| 6 | **RasterLayerMetrics** | `utils/raster/RasterLayerMetrics.py` | Estatísticas e cálculos analíticos (percentis, min/max) |
| 7 | **RasterLayerProcessing** | `utils/raster/RasterLayerProcessing.py` | Processamento pixel a pixel (extrair bandas, máscaras, composição) |
| 8 | **RasterLayerProjection** | `utils/raster/RasterLayerProjection.py` | CRS, resolução, alinhamento, reprojeção |
| 9 | **RasterLayerRendering** | `utils/raster/RasterLayerRendering.py` | Simbologia, estilo QML, rampas de cor, transparência |
| 10 | **RasterLayerSource** | `utils/raster/RasterLayerSource.py` | I/O, carregamento, basemaps Google |
| 11 | **RasterVectorBridge** | `utils/raster/RasterVectorBridge.py` | Conversão bidirecional raster↔vetor |

---

## Objetivo

Fornecer um guia completo de utilização das classes de camada, permitindo:
- Saber **qual classe usar** para cada operação
- Conhecer os **métodos estáticos principais** de cada classe
- Entender as **responsabilidades e limites** de cada classe
- Aplicar **logging padronizado** com `tool_key`
- Evitar violações arquiteturais (ex: usar classe errada para a operação)

---

## Entradas Comuns

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| layer | QgsVectorLayer / QgsRasterLayer | Sim | Camada a ser manipulada |
| tool_key / external_tool_key | str | Sim (logging) | Chave da ferramenta chamadora (`ToolKey.MEUREPOIO`) |
| output_path | str | Condicional | Caminho de saída para salvar/exportar |
| field_name | str | Condicional | Nome do campo de atributos |
| geometry | QgsGeometry | Condicional | Geometria para operações |

---

# 1. VectorLayerAttributes

**Arquivo:** `utils/vector/VectorLayerAttributes.py`

Responsável por campos e atributos de camadas vetoriais. Orquestra operações de dados tabulares sem transformar geometrias.

## Métodos Estáticos Principais

| Método | Descrição | Retorno |
|--------|-----------|---------|
| `ensure_fields(layer, field_specs, logger)` | Garante existência de campos. `field_specs` = `[(nome, tipo, len, prec), ...]` | `list[str]` (nomes adicionados) |
| `apply_updates_by_field_name(layer, updates_by_fid, logger)` | Aplica updates no buffer de edição. `updates_by_fid` = `{fid: {campo: valor}}` | `int` (total aplicado) |
| `generate_compatible_field_name(layer, base_name, max_length)` | Gera nome compatível com limite do provider (evita conflito) | `str` |
| `resolve_output_field_name(layer, base_name, conflict_resolver, max_length)` | Resolve nome final com callback de conflito (`"replace"`, `"rename"`, `"cancel"`) | `str` ou `None` |
| `delete_fields_by_names(layer, field_names, logger)` | Remove campos por nome | `int` (qtde removida) |
| `copy_attributes(target, source, field_names, conflict_resolver)` | Copia estrutura de atributos entre camadas | `bool` |
| `reorder_fields_alphabetically(layer)` | Cria nova layer com campos em ordem alfabética (case-insensitive) | `QgsVectorLayer` ou `None` |
| `create_point_coordinate_fields(layer, field_map, precision)` | Cria campos double para coordenadas X,Y,(Z) | `bool` |
| `update_point_xy_coordinates(layer, field_map, precision)` | Atualiza campos X,Y com coordenadas dos pontos | `None` |
| `update_feature_values(layer, z_values, z_field)` | Atualiza campo de altimetria com valores calculados | `None` |
| `generate_field_name_with_suffix(base_name, suffix, max_length)` | Gera nome de campo com sufixo respeitando limite (SHP=10) | `str` |
| `resolve_field_names_for_calculation(layer, base_name, calculation_mode, ...)` | Resolve nomes de campo baseado no modo de cálculo | `dict` |
| `get_field_options(layer, include_empty, empty_key, empty_label)` | Retorna opções para seletores de campo `{key: label}` | `dict` |
| `ensure_has_features(layer, logger)` | Valida se a camada tem feições | `bool` |

## Exemplo de Uso

```python
from qgis.PyQt.QtCore import QVariant
from ..utils.vector.VectorLayerAttributes import VectorLayerAttributes
from ..utils.ToolKeys import ToolKey
from ...core.config.LogUtils import LogUtils

logger = LogUtils(tool=ToolKey.MEU_ALGORITHM, class_name="MeuAlgoritmo")

# Garantir que campos existam
added = VectorLayerAttributes.ensure_fields(
    layer,
    [("area_ha", QVariant.Double, 16, 4), ("uso_solo", QVariant.String, 50)],
    logger=logger,
)

# Atualizar valores
VectorLayerAttributes.apply_updates_by_field_name(
    layer,
    {1: {"area_ha": 12.5}, 2: {"area_ha": 8.3}},
    logger=logger,
)

# Resolver nome sem conflito
field_name = VectorLayerAttributes.resolve_output_field_name(
    layer,
    "area_ha",
    conflict_resolver=lambda name: "rename",
)
```

## Limitações
- Não transforma geometrias (use `VectorLayerGeometry`)
- Não calcula métricas espaciais (use `VectorLayerMetrics`)
- Não reprojeta (use `VectorLayerProjection`)
- Não carrega/salva (use `VectorLayerSource`)
- Operações de edição exigem `layer.startEditing()` (a classe já faz internamente)

---

# 2. VectorLayerGeometry

**Arquivo:** `utils/vector/VectorLayerGeometry.py`

Responsável pelas transformações geométricas de camadas vetoriais. Altera geometrias, converte tipos, aplica operações topológicas.

## Métodos Estáticos Principais

| Método | Descrição | Retorno |
|--------|-----------|---------|
| `calculate_point_azimuth(point_a, point_b)` | Calcula azimute 0-360° (norte=0, leste=90) | `float` |
| `angular_difference_degrees(angle_a, angle_b)` | Menor diferença angular absoluta | `float` |
| `circular_mean_degrees(values)` | Média circular em graus | `float` |
| `measure_distance_between_points(point_a, point_b, crs)` | Distância entre pontos (elipsoidal se CRS informado) | `float` |
| `get_representative_point(geometry)` | Ponto representativo de Point/MultiPoint | `QgsPointXY` ou `None` |
| `create_point_layer_from_dicts(points, name, field_specs, geometry_keys, extra_fields, tool_key)` | Cria camada de pontos em memória a partir de dicts. `geometry_keys=(x_key, y_key)` | `QgsVectorLayer` ou `None` |
| `create_line_layer_from_points(points, order_by_field, name, group_by_fields, attribute_fields, ...)` | Cria linha(s) em memória a partir de QgsFeature Point | `QgsVectorLayer` ou `None` |
| `merge_memory_layers(layers, crs_authid, layer_name)` | Mescla camadas de memória em uma única camada | `QgsVectorLayer` ou `None` |
| `create_buffer_geometry(layer, distance, output_path, segments, dissolve, ...)` | Buffer ao redor das geometrias (via processing) | `QgsVectorLayer` ou `None` |
| `create_buffer_to_path_safe(input_path, output_path, distance, ...)` | Buffer usando arquivo físico (seguro para QgsTask) | `str` (output_path) |
| `explode_lines_to_path_safe(layer, output_path, ...)` | Explode linhas manualmente (thread-safe, compatível QgsTask) | `str` (output_path) |
| `get_layer_type(layer, tool_key)` | Retorna tipo da geometria (`QgsWkbTypes.PointGeometry` etc) | `int` ou `None` |
| `get_selected_features(layer, tool_key)` | Materializa feições selecionadas em nova camada | `(QgsVectorLayer, str)` |
| `singleparts_to_multparts(layer, feedback, only_selected, tool_key)` | Converte singlepart → multipart (processamento batch) | `bool` |

## Exemplo de Uso

```python
from ..utils.vector.VectorLayerGeometry import VectorLayerGeometry
from ..utils.ToolKeys import ToolKey

# Criar camada de pontos a partir de dicionários
point_layer = VectorLayerGeometry.create_point_layer_from_dicts(
    points=[
        {"id": 1, "lon": -46.63, "lat": -23.55, "nome": "Ponto A"},
        {"id": 2, "lon": -46.64, "lat": -23.56, "nome": "Ponto B"},
    ],
    name="Meus_Pontos",
    field_specs=[
        ("id", QVariant.Int),
        ("nome", QVariant.String),
    ],
    geometry_keys=("lon", "lat"),
    tool_key=ToolKey.MEU_ALGORITHM,
)

# Criar linha ordenada por campo 'sequencia'
line_layer = VectorLayerGeometry.create_line_layer_from_points(
    points=list(features),
    order_by_field="sequencia",
    name="Trilha",
    group_by_fields=["rota_id"],
    tool_key=ToolKey.MEU_ALGORITHM,
)

# Buffer
buffer_layer = VectorLayerGeometry.create_buffer_geometry(
    layer=input_layer,
    distance=100,
    segments=10,
    dissolve=True,
    external_tool_key=ToolKey.MEU_ALGORITHM,
)
```

## Limitações
- Não calcula métricas (use `VectorLayerMetrics`)
- Não reprojeta (use `VectorLayerProjection`)
- Não manipula atributos (use `VectorLayerAttributes`)
- Não carrega/salva (use `VectorLayerSource`)
- Métodos que usam `processing.run()` NÃO são thread-safe (exceto `*_to_path_safe`)

---

# 3. VectorLayerMetrics

**Arquivo:** `utils/vector/VectorLayerMetrics.py`

Responsável pela leitura e cálculos espaciais. NÃO altera dados, apenas mede.

## Métodos Estáticos Principais

| Método | Descrição | Retorno |
|--------|-----------|---------|
| `calculate_line_length(layer, field_name, use_ellipsoidal, precision)` | Calcula comprimento de linhas (elipsoidal ou cartesiano) | `None` (atualiza campo) |
| `calculate_polygon_area(layer, field_name, use_ellipsoidal, precision)` | Calcula área de polígonos em hectares | `None` (atualiza campo) |

## Exemplo de Uso

```python
from ..utils.vector.VectorLayerMetrics import VectorLayerMetrics

# Comprimento elipsoidal
VectorLayerMetrics.calculate_line_length(
    layer=line_layer,
    field_name="comp_eli",
    use_ellipsoidal=True,
    precision=4,
)

# Área em hectares (cartesiana)
VectorLayerMetrics.calculate_polygon_area(
    layer=poly_layer,
    field_name="area_ha",
    use_ellipsoidal=False,
    precision=2,
)
```

## Limitações
- Não transforma geometrias (use `VectorLayerGeometry`)
- Não reprojeta (use `VectorLayerProjection`)
- Não manipula atributos (use `VectorLayerAttributes`)
- Não carrega/salva (use `VectorLayerSource`)
- Métodos estáticos criam campo automaticamente se não existir

---

# 4. VectorLayerProjection

**Arquivo:** `utils/vector/VectorLayerProjection.py`

Responsável por CRS, conversão de unidades e reprojeção de camadas vetoriais.

## Métodos Estáticos Principais

| Método | Descrição | Retorno |
|--------|-----------|---------|
| `convert_distance_to_layer_units(layer, distance_meters)` | Converte distância em metros para unidade da camada | `float` |
| `reproject_layer(layer, target_crs)` | Cria nova camada em memória reprojetada | `QgsVectorLayer` ou `None` |
| `ensure_crs(layer, target_crs)` | Garante CRS desejado (reprojeta se necessário) | `QgsVectorLayer` ou `None` |
| `is_geographic_crs(layer)` | Verifica se CRS é geográfico (lat/lon) | `bool` |
| `reproject_features(features, source_crs, target_crs, context)` | Reprojeta lista de features | `list[QgsFeature]` |
| `get_coordinate_info(point, canvas_crs)` | Informações de coordenada em múltiplos formatos (WGS84, DMS, UTM) | `dict` |

## Exemplo de Uso

```python
from qgis.core import QgsCoordinateReferenceSystem
from ..utils.vector.VectorLayerProjection import VectorLayerProjection

target_crs = QgsCoordinateReferenceSystem("EPSG:31983")

# Reprojetar
reprojected = VectorLayerProjection.reproject_layer(
    layer=input_layer,
    target_crs=target_crs,
)

# Garantir CRS (só reprojeta se diferente)
layer_garantido = VectorLayerProjection.ensure_crs(
    layer=input_layer,
    target_crs=target_crs,
)
```

## Limitações
- Não salva camada em disco
- Não valida regras de negócio
- Não altera atributos

---

# 5. VectorLayerSource

**Arquivo:** `utils/vector/VectorLayerSource.py`

Responsável por I/O de camadas vetoriais: carregar, salvar, validar, clonar.

## Métodos Estáticos Principais

| Método | Descrição | Retorno |
|--------|-----------|---------|
| `save_vector_layer(layer, save_to_folder, output_path, output_name, decision, external_tool_key)` | Salva camada (memória ou disco). `decision`: `"rename"` ou `"overwrite"` | `QgsVectorLayer` ou `None` |
| `save_layer_to_path(layer, output_path, tool_key, decision)` | Salva e retorna caminho efetivo | `str` ou `None` |
| `save_and_load_layer(layer, output_path, tool_key, decision)` | Salva e retorna camada carregada | `QgsVectorLayer` ou `None` |
| `load_existing_vector_layer(file_path, tool_key)` | Carrega camada de arquivo existente | `QgsVectorLayer` ou `None` |
| `get_layer_file_size(layer, tool_key)` | Tamanho do datasource em bytes | `int` |
| `get_extension(path, tool_key)` | Extensão normalizada do caminho | `str` |
| `export_temp_layer(layer, prefix, external_tool_key)` | Exporta para GPKG temporário | `str` ou `None` |
| `delete_shapefile_set(base_path, retries, delay, tool_key)` | Remove conjunto de arquivos SHP | `bool` |
| `generate_incremental_path(path, tool_key)` | Gera caminho incremental (arquivo_1, _2, ...) | `str` |
| `validate_layer(layer, expected_geometry, require_editable, tool_key)` | Valida camada com regras padronizadas | `(bool, str)` |

## Exemplo de Uso

```python
from qgis.core import QgsWkbTypes
from ..utils.vector.VectorLayerSource import VectorLayerSource
from ..utils.ToolKeys import ToolKey

# Validar antes de processar
ok, msg = VectorLayerSource.validate_layer(
    layer,
    expected_geometry=QgsWkbTypes.PolygonGeometry,
    require_editable=True,
    tool_key=ToolKey.MEU_ALGORITHM,
)
if not ok:
    raise RuntimeError(msg)

# Salvar em disco com rename automático
saved = VectorLayerSource.save_vector_layer(
    layer,
    save_to_folder=True,
    output_path="C:/dados/resultado.gpkg",
    decision="rename",
    external_tool_key=ToolKey.MEU_ALGORITHM,
)
```

## Limitações
- Não é thread-safe para `processing.run()` (exceto `*_to_path_safe`)
- Extensões suportadas definidas em `StringManager.VECTOR_DRIVERS`

---

# 6. RasterLayerMetrics

**Arquivo:** `utils/raster/RasterLayerMetrics.py`

Responsável por estatísticas e cálculos analíticos de rasters. NÃO altera dados.

## Métodos Estáticos Principais

| Método | Descrição | Retorno |
|--------|-----------|---------|
| `get_band_percentiles(raster_path, band_index, lower_pct, upper_pct, tool_key)` | Calcula percentis de uma banda (usando numpy) | `(float, float)` |
| `get_global_min_max(values, tool_key)` | Min/max global a partir de lista de tuplas `(min, max)` | `(float, float)` |
| `get_global_min_max_from_rasters(raster_band_tuples, lower_pct, upper_pct, tool_key)` | Min/max global de múltiplos rasters | `(float, float)` |

## Exemplo de Uso

```python
from ..utils.raster.RasterLayerMetrics import RasterLayerMetrics
from ..utils.ToolKeys import ToolKey

# Percentis de uma banda
p_low, p_high = RasterLayerMetrics.get_band_percentiles(
    raster_path="C:/dados/mosaico.tif",
    band_index=1,
    lower_pct=2.0,
    upper_pct=98.0,
    tool_key=ToolKey.MEU_ALGORITHM,
)

# Min/max global de múltiplas bandas (RGB)
global_min, global_max = RasterLayerMetrics.get_global_min_max_from_rasters(
    raster_band_tuples=[
        ("C:/dados/mosaico.tif", 1),  # Red
        ("C:/dados/mosaico.tif", 2),  # Green
        ("C:/dados/mosaico.tif", 3),  # Blue
    ],
    lower_pct=2.0,
    upper_pct=98.0,
    tool_key=ToolKey.MEU_ALGORITHM,
)
```

## Limitações
- Não processa pixels (use `RasterLayerProcessing`)
- Não reprojeta (use `RasterLayerProjection`)
- Não modifica visualização (use `RasterLayerRendering`)
- Não carrega/salva (use `RasterLayerSource`)
- Depende de `numpy` e `gdal`

---

# 7. RasterLayerProcessing

**Arquivo:** `utils/raster/RasterLayerProcessing.py`

Responsável pelo processamento raster destrutivo e operações pixel a pixel.

## Métodos Estáticos Principais

| Método | Descrição | Retorno |
|--------|-----------|---------|
| `extract_band(raster_path, band_num, output_path, tool_key)` | Extrai banda específica para GeoTIFF | `str` (output_path) |
| `create_alpha_mask(raster_path, nodata_value, output_path, tool_key)` | Cria máscara alpha (byte: 0/255) a partir de NoData | `str` (output_path) |
| `compose_multiband_raster(band_files, output_path, create_alpha, alpha_band_path, creation_options, tool_key)` | Compõe múltiplos GeoTIFFs em raster multibanda | `str` (output_path) |

## Exemplo de Uso

```python
from ..utils.raster.RasterLayerProcessing import RasterLayerProcessing
from ..utils.ToolKeys import ToolKey

# Extrair banda
band_path = RasterLayerProcessing.extract_band(
    raster_path="C:/dados/mosaico.tif",
    band_num=1,
    tool_key=ToolKey.MEU_ALGORITHM,
)

# Criar máscara alpha
alpha_path = RasterLayerProcessing.create_alpha_mask(
    raster_path="C:/dados/mosaico.tif",
    nodata_value=-9999,
    tool_key=ToolKey.MEU_ALGORITHM,
)

# Compor RGB (bandas 4, 2, 1)
rgb_path = RasterLayerProcessing.compose_multiband_raster(
    band_files=[band4_path, band2_path, band1_path],
    output_path="C:/dados/rgb_composite.tif",
    create_alpha=True,
    alpha_band_path=alpha_path,
    tool_key=ToolKey.MEU_ALGORITHM,
)
```

## Limitações
- Não reprojeta (use `RasterLayerProjection`)
- Não calcula estatísticas (use `RasterLayerMetrics`)
- Não altera visualização (use `RasterLayerRendering`)
- Não carrega/salva (use `RasterLayerSource`)
- Depende de `gdal` e `numpy`

---

# 8. RasterLayerProjection

**Arquivo:** `utils/raster/RasterLayerProjection.py`

Responsável por CRS, resolução, alinhamento e extent de rasters.

## Métodos Estáticos Principais

| Método | Descrição | Retorno |
|--------|-----------|---------|
| `get_raster_crs(raster, external_tool_key)` | Obtém CRS do raster (QgsRasterLayer ou caminho string) | `QgsCoordinateReferenceSystem` ou `None` |
| `reproject_raster_to_crs(raster_path, target_crs, resampling_method, ..., output_path, target_resolution, ...)` | Reprojeta/reamostra raster via `gdal:warpreproject` | `str` (output_path) |

## Parâmetros Detalhados do `reproject_raster_to_crs`

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `raster_path` | str | obrigatório | Caminho do raster de entrada |
| `target_crs` | str/QgsCRS | obrigatório | CRS de destino |
| `resampling_method` | ResamplingMethod | `CUBICO_SUAVIZADO` | Método de reamostragem |
| `nodata_value` | float | `None` | Valor NoData (herdado se None) |
| `target_resolution` | float | `None` | Resolução de destino (pula reamostragem se None) |
| `output_path` | str | tempdir | Caminho de saída |
| `multithreading` | bool | `False` | Processamento multi-thread |
| `creation_options` | str | `""` | Opções GDAL extras |

## Exemplo de Uso

```python
from ..utils.raster.RasterLayerProjection import RasterLayerProjection
from ...core.enum.ResamplingMethod import ResamplingMethod
from ..utils.ToolKeys import ToolKey

# Reprojetar com reamostragem
output = RasterLayerProjection.reproject_raster_to_crs(
    raster_path="C:/dados/mosaico.tif",
    target_crs="EPSG:31983",
    resampling_method=ResamplingMethod.CUBICO_SUAVIZADO,
    target_resolution=0.5,
    output_path="C:/dados/mosaico_reprojetado.tif",
    external_tool_key=ToolKey.MEU_ALGORITHM,
)
```

## Limitações
- Não altera valores de pixels (use `RasterLayerProcessing`)
- Não calcula estatísticas (use `RasterLayerMetrics`)
- Não carrega/salva (use `RasterLayerSource`)
- Não modifica visualização (use `RasterLayerRendering`)

---

# 9. RasterLayerRendering

**Arquivo:** `utils/raster/RasterLayerRendering.py`

Responsável pela simbologia e visualização de rasters (estilo QML).

## Métodos Estáticos Principais

| Método | Descrição | Retorno |
|--------|-----------|---------|
| `save_sidecar_style(raster_path, qml_root, tool_key)` | Salva QML sidecar (mesma pasta do raster) | `str` ou `None` |
| `apply_qml_inplace(layer, qml_path, feedback, tool_key)` | Aplica QML em camada raster existente | `bool` |
| `apply_qml_to_layer(raster_path, qml_path, context, feedback, layer_name, tool_key)` | Carrega raster + aplica QML + registra no context | `bool` |
| `generate_percentil_multiband_style(raster_path, band_indices, lower_pct, upper_pct, min_value, max_value, alpha_band, opacity, algorithm, layer, feedback, tool_key)` | Pipeline completo: calcula percentis → gera QML → salva sidecar → salva backup → aplica estilo | `dict` |
| `save_qml_backup(qml_root, output_base, tool_key)` | Salva backup do QML em temp/styles | `str` ou `None` |

## `generate_percentil_multiband_style` retorna:

```python
{
    "qml_path": "C:/dados/mosaico.qml",       # Sidecar
    "backup_path": "C:/temp/styles/mosaico.qml", # Backup
    "style_applied": True,                       # Se aplicado na layer
    "global_min": 0.05,                          # Valor mínimo
    "global_max": 0.85,                          # Valor máximo
}
```

## Exemplo de Uso

```python
from ..utils.raster.RasterLayerRendering import RasterLayerRendering
from ..utils.ToolKeys import ToolKey

# Pipeline completo: percentis → QML → sidecar → backup → aplicar
result = RasterLayerRendering.generate_percentil_multiband_style(
    raster_path="C:/dados/mosaico.tif",
    band_indices=[1, 2, 3],  # RGB
    lower_pct=2.0,
    upper_pct=98.0,
    alpha_band=-1,           # Sem alpha
    opacity=1.0,
    layer=my_raster_layer,   # Opcional: aplicar in-place
    feedback=feedback,
    tool_key=ToolKey.MEU_ALGORITHM,
)
```

## Limitações
- Não processa pixels (use `RasterLayerProcessing`)
- Não salva/carrega rasters (use `RasterLayerSource`)
- Não calcula estatísticas (use `RasterLayerMetrics`)
- Não altera dados raster

---

# 10. RasterLayerSource

**Arquivo:** `utils/raster/RasterLayerSource.py`

Responsável pelo carregamento, salvamento e criação de camadas raster.

## Métodos Principais

| Método | Descrição | Retorno |
|--------|-----------|---------|
| `load_raster_from_file(file_path, external_tool_key)` | Carrega raster de arquivo (GeoTIFF, IMG, etc) | `QgsRasterLayer` ou `None` |
| `load_raster_from_url(url, cache_directory, external_tool_key, layer_name, provider_key)` | Carrega raster remoto (XYZ/WMS) | `QgsRasterLayer` ou `None` |
| `add_google_basemap(project, basemap_style, external_tool_key, layer_name)` | Adiciona camada base Google (hybrid/satellite/road) evitando duplicidade | `QgsRasterLayer` ou `None` |

## `GOOGLE_BASEMAP_VARIANTS`

| Estilo | `lyrs` | Label |
|--------|--------|-------|
| `"hybrid"` | `y` | Google Hybrid |
| `"satellite"` | `s` | Google Satellite |
| `"road"` | `m` | Google Road |

## Exemplo de Uso

```python
from ..utils.raster.RasterLayerSource import RasterLayerSource
from ..utils.ToolKeys import ToolKey

# Carregar do disco
raster = RasterLayerSource().load_raster_from_file(
    file_path="C:/dados/mosaico.tif",
    external_tool_key=ToolKey.MEU_ALGORITHM,
)

# Adicionar Google Satellite ao projeto (evita duplicidade)
basemap = RasterLayerSource().add_google_basemap(
    project=QgsProject.instance(),
    basemap_style="satellite",
    external_tool_key=ToolKey.MEU_ALGORITHM,
)
```

## Limitações
- Não reprojeta (use `RasterLayerProjection`)
- Não processa pixels (use `RasterLayerProcessing`)
- Não calcula estatísticas (use `RasterLayerMetrics`)
- Não altera visualização (use `RasterLayerRendering`)

---

# 11. RasterVectorBridge

**Arquivo:** `utils/raster/RasterVectorBridge.py`

Responsável pela integração bidirecional entre rasters e vetores.

## Métodos (stubs — implementar conforme necessidade)

| Método | Descrição | Entrada | Saída |
|--------|-----------|---------|-------|
| `rasterize_vector_layer(vector_layer, attribute_field, output_raster_path, pixel_size, ...)` | Converte vetor → raster | Camada vetorial + campo | Caminho raster |
| `polygonize_raster(raster, band_index, output_vector_path, ...)` | Converte raster → polígonos | Raster + banda | Caminho vetor |
| `extract_zonal_statistics(raster, vector_layer, statistics_type, ...)` | Estatísticas zonais | Raster + polígonos | Tabela/camada |
| `clip_raster_by_vector(raster, vector_layer, output_raster_path, ...)` | Recorta raster por máscara vetorial | Raster + vetor | Caminho raster |
| `sample_raster_at_points(raster, point_layer, output_field_name, ...)` | Amostra raster nos pontos | Raster + pontos | Camada atualizada |
| `convert_raster_to_point_cloud(raster, sample_density, ...)` | Raster → nuvem de pontos | Raster | Camada de pontos |

## Exemplo de Uso

```python
from ..utils.raster.RasterVectorBridge import RasterVectorBridge

bridge = RasterVectorBridge()

# Rasterizar (quando implementado)
bridge.rasterize_vector_layer(
    vector_layer=my_polygons,
    attribute_field="classe",
    output_raster_path="C:/dados/classificacao.tif",
    pixel_size=0.5,
    external_tool_key=ToolKey.MEU_ALGORITHM,
)

# Poligonizar (quando implementado)
bridge.polygonize_raster(
    raster=my_raster,
    band_index=1,
    output_vector_path="C:/dados/poligonos.gpkg",
    external_tool_key=ToolKey.MEU_ALGORITHM,
)
```

## Limitações
- **Métodos ainda não implementados** (stubs). Implementar sob demanda seguindo padrão das outras classes.
- Não processa rasters isoladamente (use `RasterLayerProcessing`)
- Não transforma vetores isoladamente (use `VectorLayerGeometry`)

---

# Padrões de Uso

## Padrão 1 — Logging com ToolKey

Todas as classes aceitam `external_tool_key` ou `tool_key` para rastreabilidade:

```python
# Vetoriais (parâmetro: external_tool_key ou tool_key)
VectorLayerGeometry.create_buffer_geometry(
    layer=layer,
    distance=100,
    external_tool_key=ToolKey.MEU_ALGORITHM,
)

# Raster (parâmetro: tool_key ou external_tool_key)
RasterLayerMetrics.get_band_percentiles(
    raster_path="mosaico.tif",
    band_index=1,
    tool_key=ToolKey.MEU_ALGORITHM,
)
```

## Padrão 2 — Pipeline Vetorial Completo

```python
from ..utils.vector.VectorLayerSource import VectorLayerSource
from ..utils.vector.VectorLayerAttributes import VectorLayerAttributes
from ..utils.vector.VectorLayerGeometry import VectorLayerGeometry
from ..utils.vector.VectorLayerMetrics import VectorLayerMetrics
from ..utils.vector.VectorLayerProjection import VectorLayerProjection
from ..utils.ToolKeys import ToolKey

# 1. Carregar
layer = VectorLayerSource.load_existing_vector_layer(
    "C:/dados/entrada.gpkg", tool_key=ToolKey.MEU_ALGORITHM,
)

# 2. Validar
ok, msg = VectorLayerSource.validate_layer(layer, tool_key=ToolKey.MEU_ALGORITHM)

# 3. Reprojetar se necessário
layer = VectorLayerProjection.ensure_crs(
    layer, QgsCoordinateReferenceSystem("EPSG:31983"),
)

# 4. Garantir campos
VectorLayerAttributes.ensure_fields(
    layer, [("area_ha", QVariant.Double, 16, 4)],
)

# 5. Calcular métricas
VectorLayerMetrics.calculate_polygon_area(layer, "area_ha", use_ellipsoidal=True)

# 6. Salvar
saved = VectorLayerSource.save_vector_layer(
    layer, save_to_folder=True, output_path="C:/dados/saida.gpkg",
    decision="rename", external_tool_key=ToolKey.MEU_ALGORITHM,
)
```

## Padrão 3 — Pipeline Raster Completo

```python
from ..utils.raster.RasterLayerSource import RasterLayerSource
from ..utils.raster.RasterLayerProjection import RasterLayerProjection
from ..utils.raster.RasterLayerMetrics import RasterLayerMetrics
from ..utils.raster.RasterLayerProcessing import RasterLayerProcessing
from ..utils.raster.RasterLayerRendering import RasterLayerRendering
from ..utils.ToolKeys import ToolKey

# 1. Carregar
raster = RasterLayerSource().load_raster_from_file("C:/dados/mosaico.tif")

# 2. Reprojetar
proj_path = RasterLayerProjection.reproject_raster_to_crs(
    "C:/dados/mosaico.tif", "EPSG:31983",
    external_tool_key=ToolKey.MEU_ALGORITHM,
)

# 3. Extrair banda
band_path = RasterLayerProcessing.extract_band(
    proj_path, 1, tool_key=ToolKey.MEU_ALGORITHM,
)

# 4. Calcular percentis
p_low, p_high = RasterLayerMetrics.get_band_percentiles(
    proj_path, 1, tool_key=ToolKey.MEU_ALGORITHM,
)

# 5. Gerar e aplicar estilo QML
result = RasterLayerRendering.generate_percentil_multiband_style(
    raster_path=proj_path,
    band_indices=[1, 2, 3],
    lower_pct=2.0, upper_pct=98.0,
    tool_key=ToolKey.MEU_ALGORITHM,
)
```

## Padrão 4 — Criação de Camadas a partir de Dados Externos

```python
from ..utils.vector.VectorLayerGeometry import VectorLayerGeometry
from ..utils.ToolKeys import ToolKey

# A partir de dicionários (API, CSV, etc)
records = [
    {"id": 1, "lon": -46.63, "lat": -23.55, "altura": 120.5},
    {"id": 2, "lon": -46.64, "lat": -23.56, "altura": 130.2},
]
point_layer = VectorLayerGeometry.create_point_layer_from_dicts(
    points=records,
    name="Torres",
    field_specs=[("id", QVariant.Int), ("altura", QVariant.Double)],
    geometry_keys=("lon", "lat"),
    tool_key=ToolKey.MEU_ALGORITHM,
)
```

---

# Regras e Boas Práticas

## ✅ Sempre:
- Usar `external_tool_key` ou `tool_key` para logging (rastreabilidade)
- Validar camada com `VectorLayerSource.validate_layer()` antes de processar
- Preferir métodos estáticos (sem instanciar classe)
- Usar `decision="rename"` ao salvar para evitar sobrescrita acidental
- Delegar operações para a classe correta (não misturar responsabilidades)

## ❌ Nunca:
- Usar `processing.run()` diretamente em tasks (não é thread-safe)
- Usar `VectorLayerGeometry` para manipular atributos
- Usar `VectorLayerAttributes` para transformar geometrias
- Usar `RasterLayerMetrics` para alterar pixels
- Usar `RasterLayerRendering` para salvar rasters
- Usar `VectorLayerSource` para transformar geometrias
- Chamar métodos de instância passando `external_tool_key` quando o método é estático
- Esquecer de passar `tool_key/external_tool_key` para logging

## Sobre Thread-Safety:
- Métodos que usam `processing.run()` NÃO são thread-safe
- Métodos `*_to_path_safe` (ex: `explode_lines_to_path_safe`, `create_buffer_to_path_safe`) são seguros para `QgsTask`
- Para operações thread-safe com vetores: usar `QgsVectorFileWriter` diretamente (como em `explode_lines_to_path_safe`)
- Para operações thread-safe com rasters: usar GDAL diretamente (como em `extract_band`, `compose_multiband_raster`)

---

# Casos de Uso

| Situação | Classe | Método |
|----------|--------|--------|
| Garantir que campos existam na camada | VectorLayerAttributes | `ensure_fields()` |
| Atualizar valores de atributos em lote | VectorLayerAttributes | `apply_updates_by_field_name()` |
| Criar campos de coordenadas X,Y | VectorLayerAttributes | `create_point_coordinate_fields()` |
| Resolver nome de campo sem conflito | VectorLayerAttributes | `resolve_output_field_name()` |
| Calcular azimute entre dois pontos | VectorLayerGeometry | `calculate_point_azimuth()` |
| Criar camada de pontos a partir de dict | VectorLayerGeometry | `create_point_layer_from_dicts()` |
| Criar linha a partir de pontos ordenados | VectorLayerGeometry | `create_line_layer_from_points()` |
| Aplicar buffer nas geometrias | VectorLayerGeometry | `create_buffer_geometry()` |
| Explodir linhas em segmentos | VectorLayerGeometry | `explode_lines_to_path_safe()` |
| Calcular comprimento de linhas | VectorLayerMetrics | `calculate_line_length()` |
| Calcular área de polígonos em hectares | VectorLayerMetrics | `calculate_polygon_area()` |
| Reprojetar camada vetorial | VectorLayerProjection | `reproject_layer()` |
| Converter distância para unidade da camada | VectorLayerProjection | `convert_distance_to_layer_units()` |
| Obter info de coordenada em múltiplos formatos | VectorLayerProjection | `get_coordinate_info()` |
| Salvar camada vetorial em disco | VectorLayerSource | `save_vector_layer()` |
| Validar camada antes de processar | VectorLayerSource | `validate_layer()` |
| Calcular percentis de banda raster | RasterLayerMetrics | `get_band_percentiles()` |
| Calcular min/max global de múltiplas bandas | RasterLayerMetrics | `get_global_min_max_from_rasters()` |
| Extrair banda específica para GeoTIFF | RasterLayerProcessing | `extract_band()` |
| Criar máscara alpha a partir de NoData | RasterLayerProcessing | `create_alpha_mask()` |
| Compor múltiplas bandas em um RGB | RasterLayerProcessing | `compose_multiband_raster()` |
| Reprojetar raster | RasterLayerProjection | `reproject_raster_to_crs()` |
| Gerar e aplicar estilo QML percentil | RasterLayerRendering | `generate_percentil_multiband_style()` |
| Aplicar QML em camada existente | RasterLayerRendering | `apply_qml_inplace()` |
| Carregar raster do disco | RasterLayerSource | `load_raster_from_file()` |
| Adicionar Google Satellite ao projeto | RasterLayerSource | `add_google_basemap()` |
| Converter vetor → raster | RasterVectorBridge | `rasterize_vector_layer()` (stub) |
| Converter raster → polígonos | RasterVectorBridge | `polygonize_raster()` (stub) |

---

# Dependências

| Módulo | Caminho | Usado por |
|--------|---------|-----------|
| LogUtils | `core/config/LogUtils.py` | Todas as classes (logging) |
| ToolKey | `utils/ToolKeys.py` | Todas as classes (identificação) |
| ProjectUtils | `utils/ProjectUtils.py` | VectorLayerSource, VectorLayerProjection |
| StringManager | `utils/StringManager.py` | VectorLayerSource (drivers, extensões) |
| ExplorerUtils | `utils/ExplorerUtils.py` | RasterLayerRendering (temp folders) |
| XmlUtil | `utils/XmlUtil.py` | RasterLayerRendering (QML) |
| MetadataFields | `utils/mrk/MetadataFields.py` | VectorLayerGeometry (nomes de campos) |
| ResamplingMethod | `core/enum/ResamplingMethod.py` | RasterLayerProjection |

---

# Validação

| Critério | Status |
|----------|--------|
| Reutilizável? | ✅ Classes são stateless, aceitam tool_key externo |
| Clara? | ✅ Responsabilidades explícitas por classe |
| Independente de contexto oculto? | ✅ Não depende de variáveis globais |
| Thread-safe? | ⚠️ Parcial: métodos `*_to_path_safe` sim, `processing.run()` não |
| Logging padronizado? | ✅ Todas usam LogUtils com tool_key |

---

# Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-06-23 | 1.0.0 | Criação — análise completa de utils/vector (5 classes) e utils/raster (6 classes). Documentação de todos os métodos estáticos principais, exemplos, padrões e limitações. |