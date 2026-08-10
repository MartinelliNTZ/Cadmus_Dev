<!--
Versao: 1.0.0
Data de criacao: 2026-08-10
Data da ultima modificacao: 2026-08-10
-->

# Relatorio de Metadata — Guia Rapido

Ferramenta para regerar relatorios HTML e vetorizar voos a partir de JSONs temporarios gerados pelo pipeline de metadados.

A lista de JSONs disponiveis e carregada automaticamente da pasta temporaria de relatorios, ordenada do mais recente para o mais antigo.

## O que a ferramenta faz

- **Gerar relatorio** — gera um relatorio HTML a partir do JSON selecionado e abre o arquivo automaticamente.
- **Vetorizar voo** — cria uma camada de pontos (`Flight_...`) a partir do JSON e gera a camada de rastro (linha) correspondente.
- **Botao de refresh** — atualiza a lista de JSONs temporarios disponiveis.
- **Abrir pastas** — abre a pasta de JSONs temporarios ou a pasta de relatorios HTML.

## Como usar

1. Abra `Cadmus > Relatorio de Metadata`.
2. Selecione um arquivo JSON temporario na lista (do mais recente para o mais antigo).
3. Escolha uma acao:
   - Clique em `Gerar Relatorio` para gerar e abrir o relatorio HTML.
   - Clique em `Vetorizar Voo` para criar as camadas de pontos e rastro no projeto.
4. Use os botoes auxiliares se necessario:
   - `Atualizar lista` — recarrega os JSONs disponiveis.
   - `Abrir pasta de JSONs` — abre a pasta onde ficam os arquivos JSON temporarios.
   - `Abrir pasta de relatorios` — abre a pasta onde ficam os relatorios HTML gerados.

## O que o plugin faz de verdade

- Le os arquivos `.json` da pasta temporaria de relatorios (`REPORTS_TEMP_FOLDER` + `REPORTS_JSON_FOLDER`), ordenados pela data de modificacao (mais recente primeiro).
- O combo mostra o nome de cada arquivo JSON; a selecao fica salva nas preferencias da ferramenta.
- **Gerar relatorio**:
  - Valida que um JSON foi selecionado e que o arquivo existe.
  - Verifica se a licenca tem nivel minimo 3 (`RegistryManager.has_minimum_level`).
  - Usa `ReportGenerationService.generate_from_json()` para gerar o HTML e obtem o caminho no payload.
  - Abre o HTML automaticamente com `ExplorerUtils.open_file()`.
- **Vetorizar voo**:
  - Usa `JsonToVectorTranslator.translate()` para criar a camada de pontos.
  - O nome da camada e `Flight_<titulo>` (campo `titulo` do JSON) ou `Flight_<nome do arquivo>` como fallback.
  - A fonte de coordenadas e lida do campo `source` do JSON (padrao `mrk+photo`).
  - Os campos da camada sao reordenados alfabeticamente.
  - A camada de pontos e adicionada ao projeto.
  - Gera a camada de rastro (linha) a partir dos pontos, ordenada por campo de foto (Foto/PhotoNum/id) e agrupada por `MrkPath` + `MrkFile`.
  - Exibe na barra: `Voo vetorizado: N pontos e rastro gerados.`

## Comportamento importante

- A geracao de relatorio exige licenca nivel 3 ou superior; sem ela, a ferramenta exibe um aviso.
- Se nenhum JSON estiver selecionado ou o arquivo nao existir, a ferramenta exibe um aviso (`Selecione um arquivo` / `Arquivo nao encontrado`).
- A lista de JSONs pode estar vazia — use `Atualizar lista` depois de gerar novos JSONs no pipeline.
- O relatorio HTML gerado e aberto automaticamente; se falhar ao abrir, uma barra de aviso e exibida.
- O JSON temporario contem os metadados do voo (titulo, fonte de coordenadas, fotos e marcaes) usados tanto pelo relatorio quanto pela vetorizacao.

## Quando usar

Use esta ferramenta quando quiser:

- regerar um relatorio HTML de um voo sem reprocessar o pipeline completo;
- vetorizar um voo ja processado, recriando as camadas de pontos e rastro;
- acessar rapidamente as pastas de JSONs temporarios e de relatorios HTML.

## Cuidados

- A vetorizacao adiciona camadas ao projeto — verifique se ja nao existem camadas com o mesmo nome.
- A geracao de relatorio abre o HTML no navegador; confira se a pasta de relatorios existe.
- A lista de JSONs so e atualizada manualmente (botao `Atualizar lista`) ou ao abrir a ferramenta.
- O licenciamento: gerar relatorios requer nivel 3; a vetorizacao nao exige esse nivel.