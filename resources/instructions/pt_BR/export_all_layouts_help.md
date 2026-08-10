# Exportar Todos os Layouts — Guia Rapido

Exporta todos os layouts do projeto atual em PDF, PNG e/ou SVG, com opcoes de georreferenciamento, DPI de saida, uniao de arquivos finais e selecao individual de layouts.

## Formatos de saida

Selecione pelo menos um formato:

- `Export PDF` — gera um PDF por layout. Com `Georeference PDF` marcado, o PDF recebe georreferenciamento.
- `Export PNG` — gera uma imagem PNG por layout.
- `Export SVG` — gera um SVG vetorial por layout.

A exportacao e bloqueada se nenhum formato for marcado.

## Opcoes gerais

- `DPI de saida` — define a resolucao dos arquivos exportados. Valor `0` (padrao) usa o DPI configurado no layout. Valores maiores aplicam um DPI fixo aos PDFs, PNGs e SVGs.
- `Max Width` — largura maxima em pixels usada quando os PNGs sao unidos em um PDF final.
- `Pasta de saida` — local de destino dos arquivos. O padrao e `exports` dentro do diretorio do projeto, criada automaticamente se nao existir.

## Selecao de layouts

- Clique em `Layouts` para escolher quais layouts exportar.
- A selecao fica salva para as proximas execucoes da ferramenta.
- Se nenhum layout for selecionado, todos os layouts do projeto sao exportados.
- Se o projeto nao tiver layouts, a ferramenta exibe um aviso.

## Uniao de arquivos

- `Merge PDF` — une todos os PDFs exportados em um unico `_PDF_UNICO_FINAL.pdf`.
- `Merge PNG` — converte todos os PNGs exportados em um unico `_PNG_MERGED_FINAL.pdf`, respeitando o `Max Width`.

As unioes dependem de bibliotecas opcionais: `PyPDF2` (PDFs) e `Pillow` (PNGs). Se a biblioteca estiver faltando, a ferramenta pergunta se deseja instala-la; recusando, a uniao e ignorada e a exportacao segue normalmente.

## Nomes de arquivo

- Caracteres invalidos para o sistema de arquivos (`< > : " / \ | ? *`) sao removidos do nome de cada layout.
- Com `Replace Existing` desmarcado (padrao), arquivos com nome ja existente ganham sufixo numerico (`Layout_1`, `Layout_2`...).
- Com `Replace Existing` marcado, arquivos existentes sao substituidos sem criar copias numeradas.

## Como usar

1. Abra `Cadmus > Export All Layouts`.
2. Marque pelo menos um formato: PDF, PNG e/ou SVG.
3. Ajuste `DPI`, `Georeference PDF`, `Max Width` e as unioes conforme necessario.
4. Escolha a pasta de saida (padrao `.../exports`).
5. Opcional: clique em `Layouts` e selecione os layouts desejados.
6. Clique em `Export` e acompanhe a barra de progresso (e possivel cancelar).
7. Ao final, um resumo mostra sucessos, erros e pasta de destino; os arquivos unidos sao indicados.

## O que o plugin faz de verdade

- Le os layouts do projeto via `layoutManager().layouts()` e filtra pela selecao feita em `Layouts`.
- Valida que pelo menos um formato esta marcado antes de iniciar.
- Cria a pasta de saida automaticamente se ela nao existir.
- Exporta cada layout com `QgsLayoutExporter` nos formatos marcados, aplicando `dpi` quando maior que zero.
- Aplica georreferenciamento apenas ao PDF quando `Georeference PDF` esta marcado.
- Gera nomes unicos com sufixo numerico quando `Replace Existing` esta desmarcado.
- Conta sucesso se ao menos um formato foi exportado com sucesso para o layout.
- Exibe `ProgressDialog`, permite cancelamento e interrompe o loop no ponto atual.
- Ao final, executa as unioes solicitadas (`_PDF_UNICO_FINAL.pdf` e/ou `_PNG_MERGED_FINAL.pdf`).
- Salva automaticamente as preferencias (formatos, DPI, Max Width, pasta, layouts selecionados) ao fechar a janela.

## Comportamento importante

- Pelo menos um formato (PDF, PNG ou SVG) deve estar marcado.
- Se um layout falhar em um formato mas funcionar em outro, ele e contado como sucesso e o erro aparece no resumo.
- Cancelar a exportacao mantem os arquivos ja exportados na pasta.
- O `DPI` com valor 0 delega ao layout; valores positivos sobrescrevem o DPI dos arquivos gerados.

## Quando usar

Use esta ferramenta quando precisar exportar rapidamente todos os layouts de um projeto sem abrir e salvar um por um.

E especialmente util para:

- entregar um conjunto completo de pranchas;
- gerar revisoes em lote;
- consolidar saidas PDF ou PNG em um unico arquivo final;
- gerar versoes vetoriais (SVG) dos layouts.

## Cuidados

- Revise a pasta de saida antes de executar, principalmente se `Replace Existing` estiver marcado.
- Confira os arquivos gerados quando houver layouts com nomes parecidos.
- Para projetos grandes, exporte primeiro sem uniao para validar o resultado.
- `Merge PNG` pode gerar PDFs grandes dependendo do numero de imagens e do `Max Width` definido.