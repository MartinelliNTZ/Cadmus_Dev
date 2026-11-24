# Plano de ação — Tokenização global do Cadmus

**Versão de referência:** 3.1.0.35  
**Data:** 24/11/2026  
**Documento-base:** [plano_acao.md](plano_acao.md)  
**Escopo:** itens já revisados no plano de tooltips, com seus sub-itens visíveis e mensagens de execução

## 1. Objetivo

Este plano transforma a revisão de tooltips em um inventário de tokenização global. O objetivo é localizar tudo o que ainda pode aparecer para o usuário e que não está protegido por `STR.<TOKEN>`:

- rótulos, títulos, descrições, tooltips e textos auxiliares;
- botões, opções, filtros de arquivo e listas de seleção;
- mensagens de sucesso, aviso, erro, confirmação e progresso;
- exceções exibidas pelo Processing;
- catálogos dinâmicos de metadados, bandas, composições, temas e campos de saída;
- conteúdo gerado por relatórios e instruções, que precisa de uma estratégia de localização própria.

Tokenização não é tradução. Nesta etapa, o texto-base continua em `i18n/Strings_pt_BR.py`; a tradução para os demais idiomas fica para uma etapa posterior.

### Interpretação da exclusão solicitada

O plano original chama o item 04 de **Logcat Viewer** (`logcat`). Interpretei “LockCat” como esse item. Assim, ficam fora deste plano:

- **04 — Logcat Viewer / LockCat**;
- **25 — Developer Test Tool**.

O item 06 — About — continua listado apenas para registrar o débito, mas permanece sujeito ao fluxo protegido já definido no plano original.

## 2. Diagnóstico atual

O plano anterior concluiu a camada de tooltips de 40 ferramentas, mas isso não significa que todas as strings visíveis estejam tokenizadas. A auditoria estática desta etapa encontrou:

- **904 declarações** em `Strings_pt_BR.py`;
- **833 referências distintas** a `STR.<TOKEN>` no código;
- **0 referências a tokens inexistentes**;
- aproximadamente **62 ocorrências** de literais diretamente visíveis em UI, configurações e diálogos compartilhados;
- aproximadamente **139 ocorrências** de mensagens literais em `feedback.pushInfo`, `pushWarning`, `pushCritical` e saídas equivalentes do Processing;
- **167 definições de campos de metadata**, cada uma com `label` e `description` visíveis — potencialmente **334 valores** a catalogar;
- **17 labels** de campos de saída da divisão de pontos por faixas.

Os números acima são indicadores do levantamento estático, não critérios isolados de encerramento. O critério final será a inspeção dos pontos de exibição e a validação em execução.

## 3. Regras para a implementação futura

1. Todo texto estático que chega à interface deve usar `STR`, com o valor-base cadastrado somente em `Strings_pt_BR.py` nesta fase.
2. Os nomes dos tokens devem ser semânticos, em maiúsculas e sem depender do idioma atual.
3. Valores técnicos não devem ser traduzidos nem usados como texto de interface: nomes de atributos, chaves de API, extensões, códigos de banda, nomes de algoritmos, caminhos, CRS, fórmulas e identificadores internos.
4. Valores dinâmicos devem permanecer como placeholders dentro de um token. Exemplos: `{path}`, `{count}`, `{field_name}`, `{crs}` e `{error}`.
5. Mensagens enviadas ao usuário por `feedback` ou por exceções do Processing entram no escopo. Mensagens exclusivas de `logger` continuam em português-base, conforme as instruções do projeto.
6. Labels de catálogos dinâmicos devem separar **identificador estável** de **nome exibido**. Um texto traduzível não pode ser usado como chave de persistência, comparação ou chamada de API.
7. Os widgets compartilhados são donos dos próprios textos internos; as ferramentas são donas das descrições contextuais dos seus parâmetros.
8. Os arquivos de idiomas diferentes de `pt_BR` não serão alterados nesta fase.
9. `metadata.txt` e `plugins/AboutDialog.py` não devem ser editados manualmente; qualquer débito nesses arquivos segue o fluxo protegido do projeto.

## 4. Matriz de sub-itens pendentes por ferramenta

As linhas abaixo não afirmam que todos os textos da ferramenta estão pendentes. Elas identificam os pontos que precisam de auditoria/tokenização além da camada de tooltip já concluída.

| Nº | Ferramenta | Sub-itens que precisam ser tokenizados ou confirmados | Prioridade |
|---:|---|---|:---:|
| 01 | Export all layouts | **Concluído nesta etapa:** falha de instalação de dependência e texto dos resultados de PDF/PNG unidos passaram a reutilizar tokens existentes; wrappers de erro já estavam tokenizados. | ✅ |
| 02 | Replace text layouts | Mensagens de validação, ausência de seleção e resultados; confirmar se os textos vindos dos layouts são dados dinâmicos e não tokens. | P3 |
| 03 | Restart QGIS | Confirmação de salvamento, títulos de diálogo, filtro `*.qgz`, avisos de cancelamento, erros de salvamento, falha ao localizar o executável e status de reinício. | P1 |
| 05 | Settings | Nomes exibidos dos idiomas, nomes e descrições dos temas, além dos controles comuns do registro/licença. | P1 |
| 06 | About | Labels, descrições e ações dos links sociais e copiar conteúdo; executar somente pelo fluxo protegido do arquivo. | P3 / protegido |
| 07 | Load folder | Captions/labels dos filtros de arquivo e mensagens de seleção/abertura; separar o ID técnico do texto visível em `FILE_TYPES`. | P1 |
| 08 | New project | Texto auxiliar sobre a pasta padrão e mensagem de nome inválido. | P2 |
| 09 | Vector to SVG | Labels dos filtros de arquivo, mensagens de seleção, execução e erro que ainda estejam literais. | P2 |
| 10 | Vector fields | Mensagens de validação e conflito; confirmar que nomes de campos e expressões permanecem dinâmicos. | P3 |
| 11 | Remove KML fields | Mensagens de validação/resultado; manter os nomes técnicos em `StringManager.KML_FIELDS` fora da tradução. | P3 |
| 12 | Capture coords | Títulos de fallback de geocodificação, altimetria e pipeline; mensagens estáticas de falha. | P2 |
| 13 | Multipart | Mensagens de conflito, sobrescrita e seleção vindas das utilidades compartilhadas. | P2 |
| 14 | Copy attrs | Mensagens de seleção, conflito, sobrescrita e conclusão; os nomes de camadas/campos permanecem dinâmicos. | P2 |
| 15 | Divide points by strips | Aviso de licença, aviso de nenhum resultado, 17 labels de campos de saída, filtros de arquivo e opções de tipo de faixa. | P1 |
| 16 | Save temporary layers | Aviso de pasta/projeto, confirmação de alterações, ausência de camadas e resumos finais com contagens e caminhos. | P1 |
| 17 | Path extension | Caption e texto visível do filtro de arquivo, além das mensagens de seleção e processamento. | P2 |
| 18 | Drone coordinates | 167 definições de metadata usadas no formulário/saída, filtros de arquivo e mensagens de processamento. | P1 |
| 19 | Generate trail | Mensagens de seleção, execução, resultado e erro; confirmar uso das mensagens comuns de conflito. | P3 |
| 20 | Report metadata | Aviso de licença, labels/descriptions dos campos de metadata e conteúdo textual do relatório gerado. | P1 |
| 21 | Raster mass clipper | Exceções, reprojeção, progresso, conclusão e mensagens de erro repassadas diretamente ao usuário. | P1 |
| 22 | Raster mass sampler | Erros de entrada/sink, reprojeção, progresso, cancelamento e resumo final. | P1 |
| 23 | Raster sampler | Textos internos dos diálogos compartilhados, mensagens de seleção e wrappers de erro; valores amostrados permanecem dinâmicos. | P2 |
| 24 | Imagery downloader | Labels de fontes, bandas e composições; filtros de arquivo; wrappers de cena/data/nuvens; separar chaves da API dos nomes exibidos. | P1 |
| 26 | Raster mask clipper | Exceções de raster/máscara, ausência de feições, falta de sobreposição, reprojeção, progresso e conclusão. | P1 |
| 27 | Raster optimizer | Labels das opções de reamostragem, compressão e predictor; feedback, erros e relatório final; preservar os valores aceitos pelo GDAL. | P1 |
| 28 | Difference fields | Mensagens de entrada, conflito, resultado e erro do Processing. | P2 |
| 29 | Attribute statistics | Mensagens de entrada/resultado e cabeçalhos de estatística em saídas HTML ou relatórios. | P2 |
| 30 | Geometry line from points | Mensagens de validação, progresso, resultado e erros de geometria. | P2 |
| 31 | Raster difference statistics | Cabeçalhos HTML (`MIN`, `MAX`, `MEAN`, `STD_DEV`), mensagens de processamento e erros. | P1 |
| 32 | Raster weighted average | Erro de soma de pesos, progresso, fórmula, CRS, arquivo salvo, sucesso e falhas de processamento. | P1 |
| 33 | Grid generator | Exceção de camada inválida e mensagens de execução; opções já tokenizadas devem ser mantidas. | P2 |
| 34 | NDVI | Fórmula, bandas recomendadas, progresso, interpretação das faixas, aplicação de estilo, conclusão e erros de banda. | P1 |
| 35 | NDRE | Mesmo conjunto do NDVI, adaptado para Red Edge: fórmula, bandas, interpretação, estilo, conclusão e erros. | P1 |
| 36 | RGB mosaic | Fases do processo, bandas, alpha, min/max global, progresso, conclusão e erros. | P1 |
| 37 | RGB style standardizer | Erro de raster inválido, mensagens de aplicação e conclusão. | P2 |
| 38 | GLI | Fórmula, resolução, alpha/RGB, reprojeção, progresso, conclusão, estilo e erros. | P1 |
| 39 | CHM | Abertura/alinhamento de rasters, NoData, reprojeção, criação, progresso, estatísticas, overviews, conclusão e erros. | P1 |
| 40 | Raster mean adjust | Abertura, cálculo, valores atual/desejado, fator, criação, progresso, overviews, conclusão e erros. | P1 |

## 5. Sub-itens compartilhados que devem ser tratados uma única vez

### 5.1 Diálogos e widgets comuns

Prioridade alta porque uma correção beneficia várias ferramentas:

- `BaseDialog.py`: título padrão `Cadmus`;
- `QgisMessageUtil.py`: títulos padrão de informação, sucesso, aviso, erro, debug e confirmação;
- conflitos de campo: título, pergunta e botões `Substituir`/`Renomear`;
- sobrescrita de arquivo: título, pergunta e botões `Sobrescrever`/`Renomear`/`Cancelar`;
- `ComplexColorPicker.py`: escolha de cor e copiar valor hexadecimal;
- `ComplexCrsSelector.py`: seleção de SRC;
- `ComplexSelector.py`: título do Explorer e mensagem de caminho inválido;
- `CollapsibleParametersWidget.py`: título padrão de configurações avançadas;
- `GridBBoxSelector.py`: botões padrão `Tela` e `Desenhar`;
- `LayoutsSelectionDialog.py`: descrição do botão de confirmação;
- `ProjectNameDialog.py`: texto auxiliar sobre a pasta padrão;
- `RegistryDialog.py`: placeholders e descrições de validar, remover, restaurar e salvar;
- `InfoDialog.py`: links sociais e ação de copiar conteúdo.

Depois que essa camada estiver pronta, as ferramentas devem apenas fornecer tokens contextuais quando o texto não for responsabilidade do widget.

### 5.2 Mensagens comuns de núcleo

Tokenizar os wrappers estáticos e manter os dados dinâmicos como placeholders:

- inicialização crítica do plugin;
- falha ao carregar/abrir uma ferramenta no Processing;
- erro ao executar ferramentas registradas;
- pasta, caminho, camada, campo, CRS e exceção retornados pelo processo;
- mensagens de instalação de dependência;
- mensagens de salvamento e reinício do QGIS.

### 5.3 Catálogo de metadata

`utils/mrk/MetadataFields.py` contém 167 definições. O trabalho deve separar:

- **tokenizável:** `label` e `description` exibidos ao usuário;
- **não tokenizável:** `normalized`, `core`, `attribute`, chaves técnicas, nomes de tags e identificadores usados para leitura/escrita;
- **validação:** garantir que o token não quebre a associação entre o label exibido e a chave técnica do metadata.

A recomendação é criar uma tabela semântica de tokens por grupo (`EXIF`, `DJI_XMP`, `INITIAL`, `CUSTOM`, `MRK`) sem alterar os identificadores que alimentam o processamento.

### 5.4 Campos da divisão de pontos

`utils/StringManager.py` mantém 17 labels de `DIVIDE_STRIP_FIELDS`. Cada item deve ter uma chave estável e um label obtido por `STR`. O atributo técnico deve permanecer independente do idioma.

Também devem ser revisados:

- `DIVIDE_POINTS_STRIP_TYPES` (`Curva`, `Reta`, `Ambas`), confirmando primeiro se ainda é usado;
- filtros `FILTER_ALL`, `FILTER_IMAGES`, `FILTER_VECTOR` e `FILTER_QGIS_STYLE`, separando caption traduzível de padrão de extensão;
- lista `AVAILABLE_LANGUAGES`, separando o código (`pt_BR`, `en`, `es`, `de`) do nome exibido.

### 5.5 Temas e catálogo de imagens

Em `ThemeManager.py`, os nomes e descrições dos temas são dados visíveis e devem ser separados do identificador do tema.

Em `ImageryApi.py`, nomes como bandas, fontes e composições precisam seguir a mesma regra:

- preservar chave, código da banda, resolução, extensão e parâmetros da API;
- tokenizar ou mapear apenas o nome apresentado ao usuário;
- preservar dados externos como data, plataforma, cobertura de nuvens e valores numéricos;
- não usar o nome traduzido para montar requisições ou comparar chaves.

## 6. Conteúdo que não deve ser convertido diretamente para `STR`

### 6.1 Relatórios HTML

`resources/reports/template.html` contém uma interface própria de relatório, com títulos, navegação, métricas, cabeçalhos de tabela, labels de acessibilidade e nomes de temas. A estratégia recomendada é separar o texto do template dos dados traduzíveis — por exemplo, um dicionário/locale do relatório — em vez de espalhar chamadas `STR` dentro do HTML.

Esse trabalho deve ser tratado como trilha própria, com teste visual de PDF/HTML, porque uma alteração de token pode afetar layout, acessibilidade e exportação.

### 6.2 Instruções e ajuda

`resources/instructions/html/HtmlInstructions_pt_BR.py` e `resources/instructions/pt_BR/*.md` são conteúdo editorial localizado. Não devem ser transformados frase a frase em tokens globais. A etapa futura deve criar/revisar os arquivos equivalentes de `en`, `es` e `de`, mantendo a separação por locale.

### 6.3 Dados técnicos e conteúdo dinâmico

Não tokenizar automaticamente:

- nomes de camadas, arquivos, pastas e campos fornecidos pelo projeto;
- chaves de atributos e tags EXIF/XMP;
- códigos de bandas, extensões, formatos e opções consumidas por GDAL/API;
- fórmulas, valores numéricos, CRS e nomes de provedores externos;
- mensagens exclusivas de log de desenvolvimento.

## 7. Ordem recomendada de execução

### Fase 0 — Inventário e contrato

1. Congelar esta matriz como backlog.
2. Criar uma lista de tokens candidatos com arquivo, linha, ferramenta e contexto de exibição.
3. Classificar cada literal como `UI`, `feedback`, `exception`, `catalog`, `report`, `help`, `technical` ou `dynamic`.

### Fase 1 — Base compartilhada

1. Tokenizar `QgisMessageUtil`, `BaseDialog` e widgets compartilhados.
2. Revisar `RegistryDialog`, `InfoDialog`, `ProjectNameDialog` e seletores.
3. Reutilizar tokens existentes antes de criar novos.

### Fase 2 — Ferramentas e diálogos próprios

1. Corrigir Restart QGIS, Save Temporary Layers, Load Folder e Settings.
2. Corrigir avisos de licença, validação, seleção e conflito nas ferramentas.
3. Separar captions de filtros dos padrões técnicos de extensão.

### Fase 3 — Catálogos dinâmicos

1. MetadataFields.
2. Campos da divisão de pontos.
3. Idiomas e temas.
4. Bandas, fontes e composições de imagens.
5. Opções do Raster Optimizer.

### Fase 4 — Feedback do Processing

1. Tokenizar wrappers, progresso, resumos, sucesso e erros.
2. Preservar valores dinâmicos como placeholders.
3. Revisar HTML de estatísticas e saídas intermediárias.

### Fase 5 — Relatórios e instruções

1. Definir o modelo de locale do relatório HTML.
2. Criar a estratégia de tradução das instruções.
3. Validar visualmente as saídas antes de considerar a fase encerrada.

## 8. Critérios de conclusão

Uma ferramenta só deve ser marcada como tokenizada quando:

- não restarem literais estáticos visíveis fora do mecanismo definido para o artefato;
- mensagens de `feedback` e exceções exibidas ao usuário estiverem cobertas;
- listas e opções tiverem valores técnicos separados dos labels traduzíveis;
- nomes de campos, camadas, arquivos, CRS e resultados continuarem dinâmicos;
- todos os tokens usados existirem em `Strings_pt_BR.py`;
- a interface continuar funcional com filtros, chaves e parâmetros originais;
- a inspeção visual confirmar que textos maiores não quebram os diálogos;
- os testes principais da ferramenta forem executados no QGIS.

## 9. Validação técnica sugerida

Antes de cada entrega, executar buscas direcionadas por:

- `QLabel(`, `setText(`, `setToolTip(`, `setDescription(`, `setHelp(`;
- `pushInfo`, `pushWarning`, `pushCritical`, `modal_error`, `QgsProcessingException`;
- dicionários de opções, filtros, temas, bandas e campos;
- `f"..."`, `"..."` e `'''...'''` em pontos de apresentação;
- referências `STR.<TOKEN>` sem correspondente em `Strings_pt_BR.py`;
- uso de label traduzido como chave técnica ou valor persistido.

O resultado desta etapa deve ser anexado ao changelog técnico da implementação, mas este documento permanece como plano de ação e não altera versão, `metadata.txt` ou arquivos protegidos.

## 10. Resultado esperado

Ao final da Fase 4, as 38 ferramentas do escopo terão suas camadas de interface, feedback e catálogos dinâmicos preparadas para tradução global. Relatórios e instruções ficarão com uma trilha de localização própria, evitando misturar textos editoriais e templates HTML ao sistema de tokens da interface QGIS.

