# 🛰️ Downloader de Imagens de Satélite

Busca e baixa cenas do **Sentinel-2 L2A** (catálogo STAC Earth Search) por
extensão, período e % máxima de nuvens. As bandas/composições podem receber
processamento opcional e as camadas são carregadas no QGIS agrupadas por data.

---

## 1. Extensão da busca (Bounding Box)

Escolha a origem da extensão:

- **Camada raster** — usa a extensão da camada raster selecionada.
- **Camada vetorial** — usa a extensão da camada vetorial selecionada.
- **Tela (canvas)** — usa a extensão atual da tela do QGIS.

A extensão é reprojetada para **EPSG:4326 (WGS84)** antes de consultar o STAC.

## 2. Período

Informe a **data inicial** e a **data final** (`AAAA-MM-DD`). A busca usa o
intervalo `data_inicial/data_final` do catálogo.

## 3. % Máximo de Nuvens

Filtro `eo:cloud_cover <= máximo`. Cenas com cobertura de nuvens acima do
valor escolhido não aparecem nos resultados.

## 4. Bandas e Composições

Selecione **bandas** individuais (B01–B12, B8A, SCL) ou **composições
prontas** (RGB Natural, Falsa Cor, SWIR, Agricultura, Índice Urbano, Todas).

Ao marcar uma composição, as bandas correspondentes são marcadas
automaticamente. O botão **Selecionar Todos** marca tudo.

## 5. Opções de Processamento

- **Recortar pelo polígono** — recorta pela camada de polígono selecionada.
  Sem polígono (extensão de raster/vetor/tela), recorta pelo **boundary** da
  extensão.
- **Reprojetar saída** — reprojeta apenas se o CRS da cena diferir do EPSG
  de saída escolhido.
- **Converter uint16 (÷10000 → float32)** — divide os valores por 10000 e
  grava `_refl.tif` (banda SCL não é convertida).
- **Apagar originais** — remove os arquivos uint16 após a conversão.

## 6. EPSG de saída

- **UTM (nativo da cena)** — mantém o CRS original de cada cena.
- Ou escolha um EPSG fixo (ex.: **EPSG:31983**).

## 7. Pasta de saída

Se estiver vazia, os arquivos são salvos na **pasta temporária do Cadmus**
(`%TEMP%\cadmus\imagery\`). Cada cena é gravada em `{data}_{tile}_{plataforma}/`
com `{prefixo}_{banda}.tif` e um `metadata.json`.

## 8. Modelo de execução

O download roda em **steps + tasks** (AsyncPipelineEngine). Com **2 ou mais
datas independentes**, todas são baixadas **em paralelo (ParallelStep)** — uma
task por data. Com apenas **1 data**, a execução é **sequencial**. O progresso
de cada task é exibido no gerenciador de tasks do QGIS.

Ao concluir cada data, as camadas são carregadas no projeto em um grupo
**`Sentinel-2 {data}`** (ProjectUtils).