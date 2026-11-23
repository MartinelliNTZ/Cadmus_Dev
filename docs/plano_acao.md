# Plano de ação — Tooltips do Cadmus

**Versão de referência:** `3.1.0.13`<br>
**Data:** 22/11/2026  
**Documento técnico:** desenvolvimento e manutenção das tooltips  
**Fonte do inventário:** [`mapa_ferramentas.html`](mapa_ferramentas.html)

## Objetivo

Criar tooltips simples, claras e instrutivas para que uma pessoa que não conhece o Cadmus consiga entender, ao passar o mouse, o que cada ferramenta, campo, opção e botão faz.

Este plano separa dois públicos:

- **Usuário:** lê a tooltip dentro do QGIS. O texto deve dizer o que o controle faz e, quando necessário, qual efeito a ação terá.
- **Desenvolvedor:** consulta o mapa de ferramentas para entender classes, widgets, fluxo, entradas, saídas e dependências. O texto técnico deste documento e do mapa não deve ser copiado automaticamente para a interface.

## Regras obrigatórias

### Tokens

1. Todo texto novo de tooltip ou `description` deve ser um token acessado por `STR`.
2. Os valores desta fase devem ser adicionados ou revisados somente em `i18n/Strings_pt_BR.py`.
3. O nome do token deve representar o significado reutilizável da mensagem, não o widget ou arquivo que o utiliza hoje.
4. Preferir nomes semânticos e genéricos, como:
   - `SELECT_ALL_LIST`
   - `OPEN_LOCATION`
   - `COPY_PATH`
   - `CHOOSE_FILE`
   - `CLOSE_WINDOW_WITHOUT_EXECUTING`
5. Usar o nome da ferramenta ou do widget somente quando o texto for realmente exclusivo daquele contexto. Exemplo: `EXPORT_ALL_LAYOUTS_TOOLTIP` identifica a entrada da ferramenta 01.
6. Antes de criar uma chave, pesquisar `Strings_pt_BR.py` para evitar duplicidade ou colisão com um token já existente.
7. Não criar duas chaves para o mesmo significado apenas porque os textos aparecem em widgets diferentes.
8. Manter as chaves em `UPPERCASE_WITH_UNDERSCORES` e preservar os tokens existentes que já estejam corretos.

### Responsabilidades

| Elemento | Responsabilidade pela tooltip |
|---|---|
| Entrada da ferramenta no `ToolRegistry` | A ferramenta fornece a tooltip geral da própria ferramenta. |
| Campo, checkbox, combo ou botão declarado no `config` da ferramenta | A ferramenta fornece a descrição contextual daquele item; cada item visível deve ter uma explicação, mesmo que breve. |
| Controle interno criado pelo widget | O widget fornece a tooltip genérica e reutilizável. |
| `GridCheckbox` | A ferramenta descreve cada checkbox declarado; o widget descreve os controles genéricos de seleção em lote. |
| `ComplexSelector` | A ferramenta descreve o campo/seleção; o widget descreve arquivo, pasta, camada, origem, projeto, Explorer, cópia e bloqueio. |
| `GridExecutionButtons` | A ferramenta descreve os botões declarados no `config`; o widget descreve Fechar, Configurações e Info. |
| `GridReadOnly` | A ferramenta descreve o título de cada bloco e cada campo; o widget aplica a descrição ao rótulo e ao valor, mantendo a cópia como controle interno. |
| `GridLabel` | A ferramenta descreve cada label informativo declarado no `config`. |
| Diálogo auxiliar | O chamador fornece o contexto dos itens; o diálogo preserva a descrição e o widget mantém os controles internos. |

## O que já foi feito

### Inventário técnico

- Criado o mapa de ferramentas em [`docs/mapa_ferramentas.html`](mapa_ferramentas.html).
- Catalogadas 40 ferramentas, numeradas de 01 a 40.
- Catalogados 39 widgets, com arquivo, camada de uso, responsabilidade e exemplo.
- Incluídas as famílias `Dialog`, `Instantâneo`, `Map tool` e `Processing`.
- Criado painel detalhado por ferramenta com finalidade, entradas, saídas, fluxo, widgets e dependências.
- Incluída a regra de manutenção do mapa para novas ferramentas, mudanças funcionais grandes e novos widgets.

### Contratos e instruções

- Formalizada a separação entre tooltip contextual da ferramenta e tooltip de controles internos do widget.
- Registrada a regra de tokenização semântica em:
  - `docs/skills/SKILL_AGENT.md`
  - `docs/skills/SKILL_I18N.md`
  - `docs/skills/SKILL_WIDGETS2.md`
- Registrada a restrição de versionamento: o agente só pode editar manualmente `build_distribution.py: VERSION`.
- Registrada a proibição de editar manualmente `metadata.txt` e `plugins/AboutDialog.py`.

### Ferramenta 01 — Exportar Todos os Layouts

Concluída a primeira rodada de tooltips para:

- tooltip geral da ferramenta;
- exportação de PDF, PNG e SVG;
- DPI e georreferenciamento;
- união de PDFs e PNGs;
- substituição de arquivos existentes;
- largura máxima ao unir PNGs;
- pasta de saída;
- seleção de layouts;
- confirmação e execução.

Também foram ajustados os widgets usados pela ferramenta:

- `GridExecutionButtons`;
- `GridCheckbox`;
- `GridComplexSelector`;
- `ComplexSelector`;
- `ListSelectionDialog`.

O `ListSelectionDialog` agora preserva a descrição contextual dos itens recebidos pela ferramenta.

### Lote atual — ferramentas 02, 03, 05 e 06

- **02 — Substituir Texto em Layouts:** concluída a revisão da tooltip da ferramenta e das descrições dos campos, opções, backup, inversão e execução.
- **03 — Salvar, Fechar e Reabrir Projeto:** concluída a revisão da tooltip geral da ferramenta instantânea.
- **04 — Logcat Viewer:** não fazer agora; a revisão foi adiada por ser uma ferramenta mais complexa.
- **05 — Configurações Cadmus:** concluída a revisão da tooltip geral; as descrições dos campos já estavam tokenizadas e foram auditadas.
- **06 — Sobre o Cadmus:** concluída a revisão da tooltip de entrada. `plugins/AboutDialog.py` não foi editado, conforme a regra de proteção.
- **Validação extra de `GridInputFields`:** corrigida a separação entre `description` (tooltip) e `placeholder` (exemplo no fundo do campo); os campos de Substituir e os sufixos das Configurações agora usam placeholders explícitos.

### Lote seguinte — ferramentas 07, 08 e 09

- **07 — Carregar Pasta de Arquivos:** concluídas as tooltips da pasta, opções, tipos de arquivo e execução; os controles de seleção em lote usam tokens genéricos do widget.
- **08 — Novo Projeto:** concluídas as tooltips da entrada da ferramenta, da pasta padrão, do nome do projeto e das confirmações dos diálogos auxiliares.
- **09 — Conversor de Vetor para SVG:** concluídas as tooltips da camada, pasta de saída, cores, parâmetros de estilo, opções de geração e execução.

### Lote seguinte — ferramentas 10, 11, 12 e 13

- **10 — Calcular Campos Vetoriais:** concluída a revisão da tooltip geral no `ToolRegistry`; a ferramenta é instantânea e não possui janela própria.
- **11 — Remover Campos KML:** concluída a revisão da tooltip geral no `ToolRegistry`; a ferramenta é instantânea e não possui janela própria.
- **12 — Capturar Coordenadas:** concluída a revisão da tooltip do `ToolRegistry` e das descrições individuais de todas as seções, campos, informação UTM, endereço e botão de cópia da janela de resultados.
- **13 — Converter Multipart:** concluída a revisão da tooltip geral no `ToolRegistry`; a ferramenta é instantânea e não possui janela própria.

### Lote seguinte — ferramenta 14

- **14 — Copiar Atributos de Vetor:** concluídas as descrições das camadas de origem e destino, do grupo de atributos, do checkbox de seleção total, dos campos dinâmicos e da execução.
- Os botões internos de selecionar, remover e inverter permanecem com tooltip genérica fornecida pelo `GridAttributeSelector`.

### Lote seguinte — ferramentas 15 e 16

- **15 — Dividir Vetor de Pontos por Faixas:** concluídas as tooltips da introdução, camada de pontos, feições selecionadas, quatro seções, campos operacionais e de sensibilidade, modos de caminho, campos de saída, arquivos opcionais e execução.
- **16 — Salvar Temporárias:** concluídas as tooltips de prefixo, sufixo, extensões vetorial/raster, pasta de saída e salvamento.
- O contrato de `CollapsibleParametersWidget` agora aceita `title_description` para contextualizar seus headers, e `GridComplexSelector` aceita `features_check_description` para o checkbox de feições selecionadas.

### Versão e changelog

- Versão atual em `build_distribution.py`: `3.1.0.13`.
- Changelog correspondente: `[3.1.0.13][22/11/2026]`.
- `metadata.txt` e `plugins/AboutDialog.py` não foram editados manualmente.

## Execução daqui em diante

Para cada ferramenta, seguir esta ordem:

1. Ler somente o plugin, diálogo, registro, strings e widgets realmente usados pela ferramenta.
2. Conferir o comportamento real antes de escrever o texto; não inventar o que o controle faz.
3. Listar todos os pontos que precisam de tooltip: entrada da ferramenta, campos, opções, botões, diálogos auxiliares e controles internos.
4. Classificar o dono de cada mensagem: ferramenta, widget ou diálogo auxiliar.
5. Pesquisar tokens já existentes em `Strings_pt_BR.py`.
6. Criar somente os tokens novos necessários, com nomes semânticos e genéricos.
7. Substituir strings literais em `description=`, `tooltip=` e `setToolTip()` por `STR.TOKEN`.
8. Revisar o texto como usuário iniciante: explicar o que faz, o que deve ser informado e o efeito da opção.
9. Validar sintaxe, referências dos tokens, duplicidades e ausência de alteração funcional.
   Em janelas, considerar incompleta a revisão se qualquer campo, label informativo, seção ou botão declarado pela ferramenta ficar sem descrição contextual, salvo controles internos já documentados pelo widget.
10. Atualizar o mapa de ferramentas quando houver mudança funcional grande ou nova ferramenta/widget.
11. Quando houver mudança de código ou skill, incrementar somente `build_distribution.py: VERSION` e criar no changelog uma entrada com a **mesma versão**, no formato `[versão][data]`.
12. Nunca editar manualmente `metadata.txt` ou `plugins/AboutDialog.py`.

## Controle das ferramentas

| Nº | Ferramenta | Identificador | Situação |
|---:|---|---|---|
| 01 | Exportar Todos os Layouts | `export_all_layouts` | **Concluída** |
| 02 | Substituir Texto em Layouts | `replace_in_layouts` | **Concluída** |
| 03 | Salvar, Fechar e Reabrir Projeto | `restart_qgis` | **Concluída** |
| 04 | Logcat Viewer | `logcat` | Não fazer agora — ferramenta complexa |
| 05 | Configurações Cadmus | `settings` | **Concluída** |
| 06 | Sobre o Cadmus | `about_dialog` | **Concluída — arquivo protegido** |
| 07 | Carregar Pasta de Arquivos | `load_folder_layers` | **Concluída** |
| 08 | Novo Projeto | `create_project` | **Concluída** |
| 09 | Conversor de Vetor para SVG | `vector_to_svg` | **Concluída** |
| 10 | Calcular Campos Vetoriais | `vector_fields` | **Concluída** |
| 11 | Remover Campos KML | `remove_kml_fields` | **Concluída** |
| 12 | Capturar Coordenadas | `coord_click_tool` | **Concluída** |
| 13 | Converter Multipart | `converter_multipart` | **Concluída** |
| 14 | Copiar Atributos de Vetor | `copy_attributes` | **Concluída** |
| 15 | Dividir Vetor de Pontos por Faixas | `divide_points_by_strips` | **Concluída** |
| 16 | Salvar Temporárias | `save_temporary_layer` | **Concluída** |
| 17 | Remover/Restaurar Extensão | `path_extension_tool` | A fazer |
| 18 | DJI Coordenadas de Drone | `drone_coordinates` | A fazer |
| 19 | Gerar Rastro de Máquinas | `generate_trail` | A fazer |
| 20 | Relatório de Metadata | `report_metadata` | A fazer |
| 21 | Recorte Massivo de Rasters | `raster_mass_clipper` | A fazer |
| 22 | Amostragem Massiva de Rasters | `raster_mass_sampler` | A fazer |
| 23 | Amostrar Valores de Rasters | `raster_sampler` | A fazer |
| 24 | Downloader de Imagens de Satélite | `imagery_downloader` | A fazer |
| 25 | Developer Test Tool | `developer_test_tool` | A fazer |
| 26 | Recortar Raster por Máscara de Feições | `raster_mask_clipper` | A fazer |
| 27 | Otimizar Raster (Overviews) | `raster_optimizer` | A fazer |
| 28 | Gerador de Diferenças entre Campos | `difference_fields` | A fazer |
| 29 | Estatísticas de Atributos | `attribute_statistics` | A fazer |
| 30 | Linha de Diferença entre Pontos | `geometry_line_from_points` | A fazer |
| 31 | Processar Diferença de Rasters | `raster_difference_statistics` | A fazer |
| 32 | Média Ponderada de Rasters | `raster_weighted_average` | A fazer |
| 33 | Gerador de Grade | `grid_generator` | A fazer |
| 34 | Calculadora NDVI | `ndvi_calculator` | A fazer |
| 35 | Calculadora NDRE (Red Edge) | `ndre_calculator` | A fazer |
| 36 | Criador de Mosaico RGB | `rgb_mosaic_creator` | A fazer |
| 37 | Padronizar Estilo RGB (Percentil) | `rgb_style_standardizer` | A fazer |
| 38 | Calculadora GLI (Green Leaf Index) | `gli_calculator` | A fazer |
| 39 | Calcular CHM (MDS - MDT) | `calculate_chm` | A fazer |
| 40 | Ajustar Média Raster | `raster_mean_adjust` | A fazer |

## Backlog transversal de widgets

O inventário completo já está no mapa. A revisão de tooltips dos widgets seguirá este backlog:

- Revisar os controles internos de `ComplexSelector` e manter tokens genéricos.
- Revisar `GridExecutionButtons`, `GridCheckbox` e `GridModernButtons`.
- Revisar seletores de arquivo, pasta, camada, CRS e extensão.
- Revisar widgets de valores: data, número, slider, combo e radio.
- Revisar widgets de resultado, somente leitura, labels, cor e cenas.
- Revisar botões internos de widgets compostos, sem transferir essa responsabilidade para cada ferramenta.
- Usar descrições fornecidas pela ferramenta somente nos itens declarados em `config`.

## Critério de conclusão

O plano será concluído quando:

- as 40 ferramentas tiverem tooltip geral revisada;
- todos os controles declarados pelas ferramentas tiverem descrição contextual quando necessário;
- os controles internos dos widgets reutilizáveis tiverem tooltip própria e tokenizada;
- não houver nova tooltip literal nos arquivos trabalhados;
- os tokens forem semanticamente reutilizáveis e sem colisões;
- o mapa de ferramentas continuar refletindo o sistema real;
- cada mudança de código/skill tiver versão correspondente no `BuildDistribution` e no changelog;
- `metadata.txt` e `plugins/AboutDialog.py` permanecerem fora de edição manual.

## Arquivos de controle

- [Mapa de ferramentas](mapa_ferramentas.html)
- [Agente](skills/SKILL_AGENT.md)
- [Contrato de internacionalização](skills/SKILL_I18N.md)
- [Contrato de widgets](skills/SKILL_WIDGETS2.md)
- [Changelog](ia/changelog.txt)
- `build_distribution.py` — única fonte manual da versão de distribuição
