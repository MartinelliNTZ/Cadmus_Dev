# Salvar Temporárias — Guia Rapido

Esta ferramenta salva camadas temporarias (memory) do projeto QGIS em arquivos permanentes no disco.

Vetores sao salvos em `<output>/vectors/` e rasters em `<output>/rasters/`.

## Como usar

1. Abra `Cadmus > Salvar Temporarias`.
2. Se quiser, preencha `Prefixo` e `Sufixo` para personalizar os nomes dos arquivos gerados.
3. Escolha a extensao para os arquivos vetoriais (.gpkg, .shp, .geojson, .kml, .dxf, .gml, .csv).
4. Escolha a extensao para os arquivos raster (.tif, .jp2, .png, .jpg).
5. Selecione a pasta de saida ou deixe em branco para usar a pasta do projeto salvo.
6. Clique em `Salvar`.

## O que o plugin faz de verdade

- Encontra todas as camadas temporarias do projeto:
  - camadas memory (providerType == "memory");
  - camadas com arquivo fonte em diretorio temporario (ex: processing_...\\OUTPUT.tif).
- Separa vetores e rasters em listas distintas.
- Para cada camada vetorial:
  - sai do modo edicao se necessario (salva ou descarta alteracoes);
  - salva o arquivo no disco via `VectorLayerSource.save_and_load_layer()`;
  - remove a camada memory do projeto e carrega a camada salva no mesmo grupo e posicao, preservando o renderer original.
- Para cada camada raster:
  - sai do modo edicao se necessario;
  - se a camada tem arquivo real em disco, copia direto via `ExplorerUtils.copy_file()`;
  - se a camada nao tem arquivo real (memory raster), usa `QgsRasterFileWriter.writeRasterLayer()`;
  - remove a camada temporaria e carrega a salva no mesmo grupo e posicao, preservando o estilo via QML temporario.

## Comportamento importante

- Se o campo saida estiver vazio e houver projeto salvo, o plugin usa a pasta do projeto como destino.
- As subpastas `vectors/` e `rasters/` sao criadas automaticamente dentro da pasta de saida.
- Cada arquivo segue o padrao: `{prefixo}{nome_da_camada}{sufixo}{extensao}`.
- Se o arquivo ja existir, `ExplorerUtils.get_unique_filepath()` gera um nome incremental para nao sobrescrever.
- Vaos temporarios com alteracoes nao salvas: o plugin pergunta se o usuario quer salvar ou descartar.
- O estilo original da camada e preservado durante a substituicao.
- Ao final, exibe um resumo com quantidade de camadas salvas e eventuais erros.

## Extensoes suportadas

### Vetor
- `.gpkg` — GeoPackage
- `.shp` — Shapefile
- `.geojson` — GeoJSON
- `.kml` — KML
- `.dxf` — DXF
- `.gml` — GML
- `.csv` — CSV

### Raster
- `.tif` — TIFF
- `.jp2` — JPEG 2000
- `.png` — PNG
- `.jpg` — JPEG

## Quando usar

Use esta ferramenta quando quiser:

- preservar camadas de memoria antes de fechar o projeto;
- salvar resultados de processamento que estao em camadas temporarias;
- converter camadas temporarias em arquivos permanentes para compartilhar ou reutilizar;
- substituir automaticamente as camadas temporarias pelas versoes salvas em arquivo, mantendo a organizacao do projeto.

## Cuidados

- O plugin substitui a camada temporaria pela permanente no mesmo grupo e posicao.
- Alteracoes nao salvas em camadas em modo edicao serao descartadas se voce optar por nao salvar.
- Camadas temporarias que nao sao memory nem estao em pasta temporaria podem nao ser detectadas.
- Para projetos grandes com muitas camadas temporarias, o salvamento pode levar alguns segundos.