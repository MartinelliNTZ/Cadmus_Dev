# Plano de Acao - Drag and Drop / Import de Arquivo `.mrk`

Data: 2026-03-23
Status: Planejamento
Escopo: interceptar `.mrk` arrastado para o QGIS ou importado por fluxo equivalente e converter automaticamente para pontos e linhas `.gpkg` na mesma pasta do arquivo de origem.

## Objetivo

Hoje, quando um arquivo `.mrk` e arrastado para o QGIS, o comportamento padrao tenta trata-lo como fonte de dados geoespacial nativa e retorna erro do tipo:

`Fonte de dados invalida ... .MRK nao e uma fonte de dados valida ou reconhecida`

O objetivo deste plano e substituir esse fracasso por um fluxo controlado do plugin Cadmus:

1. detectar que o arquivo arrastado/importado possui extensao `.mrk`;
2. impedir que o QGIS trate esse arquivo como camada vetorial/raster comum;
3. iniciar a cadeia ja existente da ferramenta Drone Coordinates;
4. executar parse do MRK e geracao de trilha;
5. salvar automaticamente:
   - pontos em `.gpkg`;
   - linhas em `.gpkg`;
6. gravar ambos na mesma pasta do arquivo `.mrk` original;
7. carregar os resultados no projeto QGIS.

## Cadeia Reutilizada do Sistema Atual

O plano foi desenhado para reutilizar o maximo possivel da arquitetura existente:

- `plugins/DroneCoordinates.py`
- `core/engine_tasks/AsyncPipelineEngine.py`
- `core/engine_tasks/MrkParseStep.py`
- `core/engine_tasks/PhotoMetadataStep.py`
- `core/task/MrkParseTask.py`
- `core/task/PhotoMetadataTask.py`
- `utils/mrk/MrkParser.py`
- `utils/mrk/PhotoMetadata.py`
- `utils/ExplorerUtils.py`
- `utils/vector/VectorLayerGeometry.py`
- `utils/vector/VectorLayerSource.py`

Observacao importante:

- A ferramenta atual e orientada a pasta, nao a arquivo isolado.
- O novo fluxo precisara adaptar essa cadeia para aceitar 1 arquivo `.mrk` como entrada principal sem quebrar o modo atual por pasta.

## Resultado Esperado

Ao arrastar um arquivo como:

`F:\PAULO\INPUT\Drone\IMG DJI MAVIC\DJI_202504131319_001_Export2025-04-131139\DJI_202504131319_001_Export2025-04-131139_Timestamp.MRK`

o plugin devera:

1. reconhecer a extensao `.MRK`;
2. derivar a pasta de origem do arquivo;
3. executar o parse;
4. gerar:
   - um arquivo de pontos `.gpkg`;
   - um arquivo de linhas `.gpkg`;
5. salvar ambos nessa mesma pasta;
6. adicionar as camadas resultantes ao projeto.

## Arquitetura Alvo

### 1. Captura de entrada `.mrk`

Precisamos criar um ponto de entrada do plugin para detectar arquivos `.mrk` antes que o QGIS finalize o fluxo padrao de abertura.

Opcoes tecnicas a investigar na implementacao:

- handler de drag and drop especifico do QGIS;
- hook de abertura/importacao de arquivo;
- watcher/event filter na janela principal;
- integracao via componente/plugin de drop handler, se o ambiente QGIS permitir.

Meta da etapa:

- centralizar a decisao em um componente proprio do Cadmus, com helpers pequenos reaproveitados em `utils/ExplorerUtils.py`.

Esse componente sera responsavel apenas por:

1. receber um ou mais paths;
2. filtrar extensoes `.mrk`;
3. encaminhar os arquivos validos para a orquestracao do fluxo de conversao.

### 2. Novo modo de execucao para arquivo unico

A ferramenta atual aceita `paths`, mas o comportamento principal foi desenhado com seletor de pasta.

Precisamos formalizar um novo modo de execucao:

- `source_mode = "folder"`: comportamento atual;
- `source_mode = "mrk_file"`: novo comportamento.

Dados minimos do contexto para `mrk_file`:

- `paths = [caminho_do_arquivo_mrk]`
- `source_mrk_file = caminho_absoluto`
- `source_folder = pasta_do_arquivo`
- `auto_save = True`
- `auto_load = True`
- `apply_photos = conforme decisao do produto`

### 3. Adaptacao do parse

Hoje `MrkParseTask` converte arquivo para pasta:

- se receber arquivo, usa `os.path.dirname(path)`;
- depois chama `MrkParser.parse_folder(base, ...)`.

Isso nao garante processar somente o arquivo arrastado.

Para o novo fluxo, o ideal e introduzir suporte explicito a:

- `MrkParser.parse_file(file_path, ...)`
- ou `MrkParser.parse_paths(paths, ...)`

Objetivo:

- quando o evento vier de 1 arquivo `.mrk`, processar exatamente esse arquivo;
- evitar parse acidental de outros `.mrk` da mesma pasta.

### 4. Orquestrador sem UI obrigatoria

Hoje o fluxo principal mora no dialog `DroneCordinates`.

Para suportar drag and drop corretamente, precisamos extrair a logica de execucao para um servico reutilizavel, por exemplo:

- `core/services/DroneCoordinatesRunner.py`

Responsabilidades desse runner:

1. montar `ExecutionContext`;
2. definir steps;
3. configurar callbacks;
4. decidir paths de saida;
5. salvar pontos e linhas automaticamente;
6. carregar resultado no projeto;
7. emitir mensagens para o usuario.

Com isso teremos dois clientes do mesmo fluxo:

- a janela `DroneCoordinates`;
- o novo interceptador de `.mrk`.

### 5. Padrao de nome dos arquivos de saida

O sistema precisa gerar nomes consistentes ao lado do arquivo de origem.

Proposta inicial:

- pontos: `<nome_base>_pontos.gpkg`
- linhas: `<nome_base>_trilha.gpkg`

Exemplo:

- `DJI_202504131319_001_Export2025-04-131139_Timestamp_pontos.gpkg`
- `DJI_202504131319_001_Export2025-04-131139_Timestamp_trilha.gpkg`

Se os arquivos ja existirem:

- usar politica `rename` ja suportada por `VectorLayerSource`.

### 6. Salvamento automatico

No fluxo drag and drop:

- o salvamento deve ser obrigatorio;
- o formato inicial sera `.gpkg`;
- os arquivos devem ser criados na mesma pasta do `.mrk`.

Isso significa que o runner deve popular automaticamente:

- `output_points_path`
- `output_track_path`

sem depender de `SelectorWidget` ou estado da UI.

### 7. Comportamento de metadados de fotos

Precisamos decidir se o fluxo automatico:

- sempre tenta cruzar fotos;
- nunca tenta cruzar fotos;
- ou pergunta ao usuario.

Como o drag and drop deve ser rapido e previsivel, a recomendacao inicial e:

- primeira versao: nao cruzar fotos por padrao;
- fase 2: opcao configuravel nas preferencias.

Motivo:

- reduz risco;
- reduz tempo de processamento;
- evita efeitos inesperados quando o usuario so quer abrir rapidamente o MRK.

### 8. Feedback ao usuario

Precisamos informar claramente o que ocorreu.

Mensagens previstas:

- `Arquivo MRK detectado pelo Cadmus`
- `Convertendo MRK para pontos e trilha`
- `Pontos salvos em: ...`
- `Trilha salva em: ...`
- `Falha ao converter MRK`

Canal sugerido:

- `QgisMessageUtil.bar_info / bar_success / modal_error`

## Fluxo de Execucao Proposto

1. Usuario arrasta um arquivo `.mrk` para o QGIS.
2. O Cadmus intercepta o path.
3. O handler valida a extensao.
4. O handler chama o runner da ferramenta.
5. O runner cria o contexto em modo `mrk_file`.
6. O parse processa somente o arquivo arrastado.
7. Sao geradas estruturas de pontos e trilha.
8. O runner salva automaticamente:
   - `<base>_pontos.gpkg`
   - `<base>_trilha.gpkg`
9. As camadas sao carregadas no projeto.
10. O usuario recebe confirmacao do sucesso.

## Mudancas Estruturais Recomendadas

### A. Nova classe de interceptacao

Criar uma classe nova para capturar/importar arquivos `.mrk`.

Responsabilidade unica:

- detectar e encaminhar eventos de entrada.

### B. Novo runner desacoplado da UI

Extrair a regra de negocio hoje dispersa em `DroneCoordinates.py` para um runner reutilizavel.

Beneficios:

- UI continua funcionando;
- drag and drop usa a mesma cadeia;
- testes ficam mais simples;
- reduz duplicacao.

### C. Suporte explicito a arquivo unico no parser/task

Evitar depender de parse por pasta quando a entrada real e um unico arquivo.

## Riscos Tecnicos

### 1. Ponto real de interceptacao no QGIS

O maior risco desta demanda e descobrir qual e o melhor ponto de extensao do QGIS para capturar:

- drag and drop;
- abrir/importar arquivo;

sem conflitar com o comportamento nativo.

Esse risco deve ser validado primeiro na implementacao.

### 2. Parse por pasta versus parse por arquivo

O fluxo atual pode expandir o escopo sem querer se continuarmos convertendo arquivo para pasta automaticamente.

### 3. Thread-safety

Ha pontos da cadeia atual que ainda merecem ajuste posterior para respeitar melhor a regra de nao acessar certas estruturas QGIS dentro de task.

Nao bloqueia o plano, mas deve ser observado na implementacao.

### 4. Nomes de arquivo longos

Arquivos DJI podem gerar nomes finais grandes demais.

Talvez precisemos de normalizacao de nomes na etapa de implementacao.

## Fases de Implementacao

### Fase 1 - Descoberta tecnica

1. localizar o melhor hook do QGIS para drag and drop/import de arquivo;
2. validar como impedir o erro padrao de datasource invalido;
3. provar captura de `.mrk` com log simples.

### Fase 2 - Runner reutilizavel

1. extrair a execucao da ferramenta para uma classe servico;
2. manter compatibilidade total com a UI atual;
3. suportar entrada por arquivo unico.

### Fase 3 - Parse dedicado de arquivo

1. introduzir `parse_file()` ou equivalente;
2. garantir que apenas o `.mrk` arrastado seja processado;
3. preservar cadeia atual por pasta.

### Fase 4 - Salvamento automatico

1. gerar nomes de saida;
2. salvar pontos e trilha em `.gpkg`;
3. carregar no projeto.

### Fase 5 - Acabamento

1. mensagens ao usuario;
2. logs semanticos;
3. ajustes de preferencias;
4. documentacao da nova funcionalidade.

## Criterios de Aceitacao

- arrastar 1 arquivo `.mrk` nao deve mais terminar apenas com erro de fonte invalida;
- o Cadmus deve reconhecer o arquivo e iniciar o processamento;
- o parse deve considerar apenas o arquivo arrastado;
- devem ser gerados 2 `.gpkg` na mesma pasta do `.mrk`;
- os `.gpkg` devem ser carregados no QGIS;
- o fluxo atual da janela Drone Coordinates deve continuar funcionando;
- o sistema deve lidar com arquivo de saida existente via renomeacao.

## Perguntas Para Alinhamento Antes da Implementacao

Responder estas perguntas antes de codar:

1. Quando o usuario arrastar um `.mrk`, voce quer:
   - processar automaticamente sem perguntar nada;
   - ou mostrar uma confirmacao antes de iniciar?

2. No modo drag and drop, devemos:
   - processar somente o arquivo arrastado;
   - ou processar todos os `.mrk` da mesma pasta?

3. O cruzamento com fotos deve, nessa primeira versao:
   - ficar desligado por padrao;
   - ficar ligado por padrao;
   - ou perguntar a cada arquivo?

4. O nome final dos arquivos `.gpkg` pode seguir este padrao?
   - `<nome_base>_pontos.gpkg`
   - `<nome_base>_trilha.gpkg`

5. Se os `.gpkg` ja existirem na pasta, voce prefere:
   - renomear automaticamente;
   - sobrescrever automaticamente;
   - ou pedir decisao ao usuario?

6. Quando varios `.mrk` forem arrastados de uma vez, voce quer:
   - processar cada um separadamente;
   - ignorar multisselecao por enquanto;
   - ou agrupar todos em uma unica saida?

7. Alem do drag and drop, voce quer que o mesmo fluxo aconteca tambem quando o usuario usar:
   - `Layer > Add Layer...`
   - Browser Panel
   - duplo clique no arquivo no Browser do QGIS
   - ou apenas drag and drop por enquanto?

8. No sucesso, voce prefere:
   - apenas carregar as camadas;
   - carregar as camadas e mostrar uma barra de sucesso;
   - carregar as camadas e abrir uma janela resumo com os caminhos salvos?

## Decisoes Fechadas

1. O processamento sera automatico, sem confirmacao.
2. Apenas o arquivo `.mrk` arrastado/importado sera processado.
3. O cruzamento com fotos ficara desligado por padrao neste ciclo.
4. Os nomes de saida usarao sufixos localizados via i18n.
5. Se os `.gpkg` ja existirem, o sistema deve carregar as saidas existentes.
6. Multiplos `.mrk` devem ser tratados separadamente.
7. O alvo e cobrir drag and drop e tambem o fluxo equivalente no Browser/importacao suportada pelo ponto oficial do QGIS.
8. No sucesso, o sistema deve carregar as camadas e exibir apenas uma mensagem rapida nao modal.

## Proximo Passo

Apos voce responder as perguntas acima, a implementacao deve seguir esta ordem:

1. prova de interceptacao do `.mrk`;
2. extracao do runner compartilhado;
3. suporte a parse por arquivo unico;
4. salvamento automatico;
5. acabamento e testes manuais.
