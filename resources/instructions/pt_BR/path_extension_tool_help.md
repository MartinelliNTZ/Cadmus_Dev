<!--
Versao: 1.0.0
Data de criacao: 2026-08-10
Data da ultima modificacao: 2026-08-10
-->

# Extensao de Path — Guia Rapido

Ferramenta para remover/restaurar a extensao de arquivos ou zipar/deszipar fotos nos paths armazenados em feicoes de uma camada vetorial.

Os caminhos dos arquivos sao lidos de um campo da camada e o resultado de cada operacao e gravado no campo `NewPath` (criado automaticamente).

## Modos de operacao

- `Remover Extensao` — remove o ponto e a extensao do path fisico. Exemplo: `C:/fotos/foto.jpg` vira `C:/fotos/fotojpg`. O arquivo no disco e renomeado.
- `Restaurar Extensao` — restaura o ponto e a extensao. Exemplo: o arquivo `C:/fotos/fotojpg` no disco volta a ser `C:/fotos/foto.jpg`.
- `Zipar` — agrupa as feicoes da mesma pasta e cria UM arquivo ZIP por pasta contendo os arquivos apontados pelas feicoes. Remove os arquivos originais apos a compressao.
- `Deszipar` — agrupa as feicoes da mesma pasta, extrai o ZIP da pasta e remove o ZIP apos a extracao.

## Como usar

1. Abra `Cadmus > Extensao de Path`.
2. Selecione a camada vetorial de entrada (ou um arquivo vetorial, se preferir).
3. Opcional: marque `Somente feicoes selecionadas` para processar apenas a selecao atual.
4. Selecione o campo que contem o caminho dos arquivos. Se a camada tiver um campo chamado `path`, ele e auto-selecionado.
5. Escolha o modo de operacao: Remover, Restaurar, Zipar ou Deszipar.
6. Clique em `Executar`.
7. Ao final, uma mensagem de sucesso e exibida na barra de mensagens com a quantidade de feicoes alteradas.

## O que o plugin faz de verdade

- Le a camada da interface e o campo de path escolhido.
- Valida que a camada e vetorial, que um atributo foi selecionado e que um modo foi escolhido.
- Executa uma pipeline assincrona (`AsyncPipelineEngine` com `PathExtensionStep`).
- A task processa os arquivos fisicos no disco sem tocar na camada:
  - `remove` e `restore` processam feicao por feicao via `ExplorerUtils`.
  - `zip` e `unzip` agrupam as feicoes por pasta e delegam a `FileCompressUtils`.
- O step adiciona o campo `NewPath` (texto) na camada, se ele ainda nao existir.
- Ao finalizar, o step grava no campo `NewPath` de cada feicao o novo caminho resultante (main thread) e repinta a camada.
- Exibe na barra de mensagens: `Processamento concluido: N feicoes alteradas`.
- Salva o ultimo modo usado nas preferencias da ferramenta.

## Comportamento importante

- O `NewPath` e criado na camada e recebe o novo path de cada feicao processada; feicoes ignoradas ou com erro nao sao alteradas.
- Modo `Zipar`: o ZIP e criado com o nome da pasta (ex: `C:/fotos/fotos.zip`) e contem apenas os arquivos apontados pelas feicoes — nao todos os arquivos da pasta.
- Modo `Deszipar`: o ZIP da pasta e extraido no proprio diretorio e o arquivo ZIP e removido em seguida.
- Se um path for vazio ou invalido, a feicao e contabilizada como erro.
- Arquivo inexistente ou permissao negada geram erro contabilizado, mas o processamento continua nas demais feicoes.
- O processamento e assincrono e a interface nao trava; e possivel cancelar a task durante a execucao.

## Quando usar

Use esta ferramenta quando quiser:

- normalizar paths de fotos removendo ou restaurando a extensao em lote;
- compactar em ZIP os arquivos referenciados pelas feicoes de uma camada;
- extrair ZIPs referenciados pelas feicoes, restaurando os arquivos originais.

## Cuidados

- O modo `Zipar` remove os arquivos originais apos criar o ZIP — faca backup se necessario.
- O modo `Deszipar` remove o ZIP apos a extracao.
- Confira se o campo selecionado realmente contem paths absolutos validos.
- Use `Somente feicoes selecionadas` para testar em um pequeno conjunto antes de processar a camada inteira.
- O processamento altera arquivos no disco; revise a pasta antes de executar.