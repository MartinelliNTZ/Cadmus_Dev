# Sistema de Drag and Drop de MRK

Este documento descreve exatamente como funciona o sistema de drag and drop/importacao de arquivos `.mrk` no Cadmus.

## Visao Geral

O sistema foi dividido em duas camadas:

- `core/services/MrkDropHandler.py`
- `core/services/DroneCoordinatesRunner.py`

Esses arquivos nao fazem a mesma coisa.

## Arquitetura atual

### 1. `core/services/MrkDropHandler.py`

Este e o handler real do QGIS.

Responsabilidades:

- herdar de `QgsCustomDropHandler`;
- receber o arquivo arrastado;
- decidir se o Cadmus vai assumir o processamento;
- encaminhar a execucao para o runner.

Em resumo:

- `services` = integracao com QGIS.

### 2. `core/services/DroneCoordinatesRunner.py`

Este e o executor da conversao.

Responsabilidades:

- receber o arquivo `.mrk`;
- montar os caminhos de saida;
- disparar a pipeline;
- salvar e carregar os resultados.

## Onde ficaram os helpers pequenos

Os helpers pequenos de extensao/path ficaram em:

- `utils/ExplorerUtils.py`

Eles sao metodos utilitarios, nao uma terceira classe de orquestracao do fluxo.

## Fluxo Completo

### Caso 1. Arquivo `.mrk` arrastado de fora para dentro do QGIS

1. O usuario arrasta um arquivo `.mrk` ou `.MRK` para o QGIS.
2. O QGIS chama o `QgsCustomDropHandler` registrado pelo Cadmus.
3. `core/services/MrkDropHandler.py` recebe o path em `handleFileDrop(...)`.
4. O handler usa `ExplorerUtils.has_extension(...)` para validar a extensao.
5. Se nao for `.mrk`, retorna `False` e o QGIS segue seu comportamento normal.
6. Se for `.mrk`, o Cadmus mostra uma mensagem rapida:
   - `STR.MRK_DROP_START`
7. O handler chama `DroneCoordinatesRunner.run_mrk_file(...)`.

## O que o Runner faz

Arquivo:

- `core/services/DroneCoordinatesRunner.py`

Responsabilidades:

1. Receber o caminho do arquivo `.mrk`.
2. Usar `ExplorerUtils` para montar os caminhos de saida:
   - `<base>_<STR.POINTS.lower()>.gpkg`
   - `<base>_<STR.TRACK.lower()>.gpkg`
3. Verificar se esses arquivos ja existem.
4. Se os dois ja existirem:
   - carregar ambos;
   - nao reprocessar o `.mrk`;
   - mostrar `STR.LOADED_EXISTING_GPKG`.
5. Se nao existirem:
   - montar `ExecutionContext`;
   - definir:
     - `paths = [arquivo_mrk]`
     - `recursive = False`
     - `extra_fields = None`
     - `points_layer_name = STR.POINTS`
     - `track_layer_name = STR.TRACK`
   - disparar `AsyncPipelineEngine`.

## Como a conversao acontece

### Etapa 1. Parse do arquivo

Arquivo:

- `core/task/MrkParseTask.py`

Comportamento atual:

- se o path for um arquivo `.mrk`, usa `MrkParser.parse_file(...)`;
- se o path for uma pasta, usa `MrkParser.parse_folder(...)`.

Isso garante que no drag and drop:

- somente o arquivo arrastado seja processado.

### Etapa 2. Criacao da camada de pontos

Arquivo:

- `core/engine_tasks/MrkParseStep.py`

O step recebe o resultado do parse e cria a camada de pontos em memoria.

### Etapa 3. Criacao da trilha

Arquivo:

- `core/services/DroneCoordinatesRunner.py`

Depois do parse:

- o runner usa `VectorLayerGeometry.create_line_layer_from_points(...)`
- gera a linha de trilha a partir dos pontos do arquivo.

### Etapa 4. Salvamento

Arquivo:

- `utils/vector/VectorLayerSource.py`

O runner salva:

- pontos em `.gpkg`
- trilha em `.gpkg`

na mesma pasta do `.mrk`.

## Regras de negocio fechadas

- extensoes aceitas:
  - `.mrk`
  - `.MRK`
- processamento:
  - automatico
  - sem confirmacao
- escopo:
  - apenas o arquivo arrastado/importado
- fotos:
  - cruzamento desligado por padrao
- se saidas ja existem:
  - carregar as existentes
- quando varios `.mrk` forem arrastados:
  - cada arquivo deve ser tratado separadamente pelo mecanismo de drop do QGIS
- feedback:
  - mensagem rapida nao modal

## O que nao e o papel do sistema atual

Neste corte, a parte de drag and drop nao foi criada para:

- substituir a ferramenta de janela `DroneCoordinates`;
- adicionar preferencias novas;
- mudar o comportamento antigo por pasta;
- habilitar cruzamento automatico com fotos.

## Resumo da Arquitetura

- `core/services/MrkDropHandler.py`
  - ponto oficial do QGIS
  - integra com drag/drop
- `core/services/DroneCoordinatesRunner.py`
  - orquestra conversao e salvamento
- `utils/ExplorerUtils.py`
  - helpers genericos de extensao/path
- `core/task/MrkParseTask.py`
  - seleciona parse por arquivo ou pasta
- `utils/mrk/MrkParser.py`
  - parse real do `.mrk`

## Regra pratica para lembrar

Se precisar responder rapidamente:

- `services/MrkDropHandler.py` recebe o drop;
- `DroneCoordinatesRunner.py` executa a conversao;
- `ExplorerUtils.py` ajuda com extensao/path;
- `MrkParser.parse_file(...)` garante que apenas o `.mrk` arrastado seja processado.
