# Criar Projeto CADMUS — Guia Rapido

Esta ferramenta cria a estrutura de pastas e o arquivo `.qgz` de um novo projeto QGIS seguindo o padrao Cadmus.

Ela tambem pode:

- definir a pasta padrao onde os projetos serao criados;
- sugerir nomes automaticamente (NovoProjeto_1, NovoProjeto_2...);
- criar subpastas `vectors/` e `rasters/` dentro da pasta do projeto;
- adicionar um basemap Google ao projeto;
- carregar uma camada de referencia line.gpkg;
- salvar o projeto atual em novo destino ou abrir em nova janela.

## Como usar

1. Abra `Cadmus > Criar Projeto`.
2. Confira a pasta padrao exibida na interface.
3. Se quiser alterar a pasta padrao, clique em `Configuracoes`.
4. Clique em `Criar Projeto`.
5. Confirme ou altere o nome sugerido para o projeto.
6. A ferramenta cria a estrutura e o arquivo `.qgz` automaticamente.

## O que o plugin faz de verdade

- Le a pasta padrao das preferencias do sistema (`projects_folder`).
- Se nao houver pasta padrao definida, pergunta ao usuario e persiste a escolha.
- Sugere um nome automatico baseado em `NovoProjeto_1`, `NovoProjeto_2`...
- Cria a estrutura: `<pasta>/<nome_do_projeto>/vectors/`, `rasters/` e `<nome>.qgz`.
- Detecta o cenario do projeto atual:
  - **Nao salvo sem conteudo:** salva o projeto atual no novo caminho e adiciona basemap + camada de referencia.
  - **Nao salvo com conteudo:** salva o projeto atual no novo caminho.
  - **Salvo:** abre o projeto em uma nova janela do QGIS.
- Aplica o SRC padrao configurado nas preferencias (padrao: EPSG:4326).
- Adiciona automaticamente um basemap Google (estilo hybrid).
- Copia e carrega a camada de referencia `line.gpkg` na pasta `vectors/` do novo projeto.
- Centraliza o canvas na extensao da camada de referencia quando aplicavel.

## Comportamento importante

- Se a pasta do projeto ja existir, o plugin pergunta se deseja continuar.
- Se o projeto atual ja estiver salvo em disco, o plugin abre uma nova janela do QGIS.
- Se o projeto atual nao estiver salvo, o plugin reutiliza a janela atual e salva no novo destino.
- O basemap Google e a camada de referencia sao adicionados apenas em projetos novos (sem arquivo anterior).
- A pasta padrao e persistida nas configuracoes do sistema (`ToolKey.SYSTEM`).

## Pasta padrao

- A pasta padrao inicial e `C:/QgisProjects`.
- Pode ser alterada nas `Configuracoes Cadmus`.
- O campo na interface mostra a pasta atualmente configurada.

## Quando usar

Use esta ferramenta quando quiser:

- criar um novo projeto QGIS com a estrutura padrao do Cadmus;
- padronizar a organizacao de pastas entre projetos;
- iniciar um projeto ja com basemap e camada de referencia;
- abrir o novo projeto em uma janela separada mantendo o atual aberto.

## Cuidados

- Se o projeto atual tiver alteracoes nao salvas, salve-as antes de executar.
- Projetos criados em pasta ja existente podem sobrescrever arquivos se confirmado.
- A camada de referencia `line.gpkg` e copiada para o vetors/ do novo projeto.
- O basemap Google requer conexao com internet para carregar.