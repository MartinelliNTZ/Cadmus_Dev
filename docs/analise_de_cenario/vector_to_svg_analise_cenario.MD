# Analise de Cenario - Vector To SVG

**Visao Geral**

A ferramenta exporta geometrias vetoriais do projeto QGIS para arquivos SVG, com suporte a exportacao unica ou por feicao, controle de fundo, borda e rotulos.

**Objetivo**

Gerar arquivos SVG reutilizaveis a partir de camadas vetoriais do QGIS, preservando a estrutura geometrica principal e aplicando configuracoes basicas de representacao visual.

**Fluxo resumido**

- Entrada: camada vetorial valida com feicoes.
- Filtragem opcional: uso apenas das feicoes selecionadas.
- Preparacao: leitura das geometrias, reprojecao para WGS84 e calculo da extensao.
- Renderizacao: montagem do documento SVG com fundo, geometrias e rotulos.
- Saida: gravacao em disco de um arquivo unico ou de um arquivo por feicao.

**Cenarios de uso**

- Exportacao unica da camada inteira para produzir um unico SVG consolidado.
- Exportacao por feicao para gerar ativos separados para web, layout ou automacao.
- Uso apenas das feicoes selecionadas para gerar SVGs de um subconjunto do layer.
- Rotulagem baseada na configuracao da camada no QGIS, com fallbacks tecnicos quando o labeling nao estiver diretamente acessivel.

**Regras relevantes**

- Se `Somente feicoes selecionadas` estiver ativo, somente a selecao deve ser exportada.
- Se `Fundo transparente` estiver ativo, o SVG nao deve receber fundo preenchido.
- Se `Mostrar Borda` estiver desativado, as geometrias devem ser desenhadas sem stroke.
- Se `Mostrar Rotulo` estiver desativado, nenhum texto deve ser exportado.
- Na exportacao por feicao, o nome do arquivo deve priorizar o campo `Name`; se nao houver valor, usar o nome da camada com indice incremental.

**Impactos nos dados**

- Nao altera a camada original.
- Gera apenas arquivos derivados em disco.
- Pode produzir muitos arquivos quando usado por feicao em camadas grandes.

**Riscos e controles**

- Ausencia de rotulo: depende da configuracao de labeling, `displayExpression` ou campo `Name`; o plugin deve registrar fallbacks em log.
- Sobrescrita de arquivo: controlada por geracao de nome incremental.
- Volume de saida elevado: exportacao por feicao pode criar centenas ou milhares de arquivos.
- Aparencia simplificada: o SVG final representa uma versao utilitaria da camada, nao uma copia completa de todo o renderer do QGIS.

**Observacoes sobre implementacao**

- A interface deve manter configuracoes explicitas de borda e rotulo para reduzir dependencia da simbologia do projeto.
- O utilitario `SVGUtils` concentra a geracao generica do documento e o plugin fica responsavel pela orquestracao da ferramenta.
- A nomenclatura das instrucoes deve seguir o `ToolKey.VECTOR_TO_SVG`.

**Evolucoes recomendadas**

- Adicionar preview simples do SVG antes da exportacao.
- Permitir escolha opcional de familia da fonte e alinhamento do rotulo.
- Ampliar compatibilidade com cenarios mais complexos de labeling do QGIS.

**Conclusao**

Ferramenta util para transformar vetores do projeto em ativos SVG leves e reaproveitaveis. O principal ponto de atencao esta na compatibilidade da rotulagem entre diferentes configuracoes e versoes do QGIS.
