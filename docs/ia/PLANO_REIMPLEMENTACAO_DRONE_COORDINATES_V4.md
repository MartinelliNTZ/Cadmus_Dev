# Plano de Acao Detalhado - Reimplementacao DroneCoordinates (V4)

Data: 2026/04/07
Autor: Codex + Usuario
Escopo principal: Reestruturar o sistema DroneCoordinates completo (UI + pipeline + metadata + runner + persistencia), preservando compatibilidade com a arquitetura Cadmus.

## 1. Contexto e objetivo

O sistema atual de `DroneCoordinates` funciona, mas a camada de metadados de fotos esta desalinhada com o novo padrao definido pelo usuario. A diretriz agora e:

1. `PhotoMetadata.py` deixa de ser extrator pesado e vira orquestrador/manager.
2. Extracao de dados passa a usar as novas classes:
- `utils/mrk/ExifUtil.py`
- `utils/mrk/XmpUtil.py`
- `utils/mrk/CustomPhotosFieldsUtil.py`
- `utils/mrk/MetadataFields.py`
3. A UI do plugin precisa permitir selecao de campos por categoria (3 collapsibles com grid de checkbox).
4. O pipeline continua em Steps/Tasks (nao mexer no sistema de steps), mas o fluxo de dados da metadata sera refeito.
5. O `DroneCoordinatesRunner.py` deve usar as mesmas regras sem UI, lendo filtros via preferencias.

## 2. Requisitos funcionais consolidados (extraidos da conversa)

### 2.1 Reestruturacao de responsabilidade

- `PhotoMetadata.py` deve absorver a responsabilidade do `OBSOLETManager.py`.
- `OBSOLETManager.py` deixa de ser referencia de uso na cadeia ativa.
- `PhotoMetadata` deve atuar como manager/orquestrador de:
1. descoberta de fotos
2. extracao completa (EXIF + XMP + derivados custom)
3. persistencia temporaria de dados completos em JSON
4. filtro final por campos selecionados antes de aplicar no layer

### 2.2 Padrao de campos

- Campos solicitados para manter/migrar em padrao novo:
1. `dt_full` (`%Y%m%d%H%M`)
2. `dt_date` (`%Y%m%d`)
3. `dt_time` (`%H%M`)
4. `tipo_arq` renomeado para `FileType`
5. `flight_number`, `flight_name`, `folder_level1`, `folder_level2` com nomes padrao em ingles
- Esses campos devem entrar em `CUSTOM_FIELDS` com mesmo formato dos demais dicionarios.
- Campos vindos do MRK devem ser mantidos e ganhar dicionario proprio no mesmo formato de `MetadataFields.py` (novo bloco `MRK_FIELDS`).

### 2.3 Mudanca de UI

No `plugins/DroneCoordinates.py`:

- Criar 3 seÃ§Ãµes collapsible para parametros:
1. `REQUIRED_FIELDS`
2. `CUSTOM_FIELDS`
3. `MRK_FIELDS`
- Cada secao usa grid de checkbox.
- Dados exibidos no grid via `StringAdapter.py`.
- Tooltips dos checkboxes devem usar `description` dos dicionarios.
- Selecoes devem ser salvas e carregadas nas preferencias do plugin.

Mudancas de suporte:
- `resources/widgets/CheckboxGridWidget.py`:
1. suporte a novo formato de item (key/label/description)
2. tooltip por item
3. metodos para extrair chaves marcadas/desmarcadas
- `core/ui/WidgetFactory.py`:
1. suportar criacao do grid no formato antigo e novo
2. nao quebrar chamadas existentes de outros plugins

### 2.4 Processamento de metadata

- Durante execucao:
1. Receber lista de campos selecionados (checkboxes ou preferencias).
2. Buscar e extrair TODOS os dados das fotos (sem filtrar na extracao).
3. Salvar dataset completo em arquivo JSON temporario.
4. Aplicar filtro final para enviar ao shapefile/layer apenas campos selecionados.

### 2.5 Runner sem UI

- `core/services/DroneCoordinatesRunner.py` deve manter comportamento de conversao automatica.
- Lista de campos nao vem da UI: vem das preferencias persistidas do plugin.
- Resultado final do runner deve respeitar o mesmo filtro de campos.

### 2.6 Padronizacao e logging

- Adaptar classes novas de `utils/mrk` ao padrao Cadmus:
1. imports relativos corretos
2. `LogUtils` com `tool_key`
3. tratamento de excecao sem `print`
4. compatibilidade com arquitetura de utilitarios

## 3. Arquivos impactados (mapa inicial)

### 3.1 Core do fluxo DroneCoordinates
- `plugins/DroneCoordinates.py`
- `core/services/DroneCoordinatesRunner.py`
- `core/task/PhotoMetadataTask.py`
- `core/engine_tasks/PhotoMetadataStep.py`
- `utils/mrk/PhotoMetadata.py`
- `utils/mrk/MrkParser.py` (ajustes de contrato de campos MRK)

### 3.2 Novas classes de metadata (a adaptar)
- `utils/mrk/ExifUtil.py`
- `utils/mrk/XmpUtil.py`
- `utils/mrk/CustomPhotosFieldsUtil.py`
- `utils/mrk/MetadataFields.py`
- `utils/mrk/OBSOLETManager.py` (absorcao/deprecacao)

### 3.3 UI/Widget
- `resources/widgets/CheckboxGridWidget.py`
- `core/ui/WidgetFactory.py`
- `utils/adapter/StringAdapter.py`

### 3.4 Persistencia e suporte
- `utils/Preferences.py` (somente se precisar ampliar formato de pref)
- `utils/ExplorerUtils.py` (helper para criar JSON temporario)

### 3.5 Documentacao e controle
- `docs/ia/changelog.txt`
- `docs/ia/todo.txt`
- este plano (`docs/ia/PLANO_REIMPLEMENTACAO_DRONE_COORDINATES_V4.md`)

## 4. Estrategia de execucao por etapas (incremental e segura)

## Etapa 1 - Planejamento e trilha de execucao
Objetivo:
- consolidar plano tecnico e backlog executavel

Entregaveis:
- plano detalhado
- `todo.txt` com checklist
- changelog da etapa

Status:
- concluida nesta rodada

## Etapa 2 - Padronizacao das classes novas de metadata
Objetivo:
- tornar `ExifUtil`, `XmpUtil`, `CustomPhotosFieldsUtil`, `MetadataFields` aderentes ao padrao Cadmus

Acoes:
1. corrigir imports absolutos indevidos (ex: `from Strings import Strings`)
2. remover `print` e usar `LogUtils`
3. corrigir problemas de pacote/modulo
4. eliminar bloco `if __name__ == "__main__"` de utilitarios
5. garantir compatibilidade de Python/QGIS no contexto do plugin

Criterio de aceite:
- classes importaveis por `PhotoMetadata` sem erro
- sem dependencia de script externo

## Etapa 3 - Definicao oficial de campos por categoria
Objetivo:
- consolidar `REQUIRED_FIELDS`, `CUSTOM_FIELDS` e novo `MRK_FIELDS` em `MetadataFields.py`

Acoes:
1. criar `MRK_FIELDS` no mesmo schema:
- `normalized`
- `core`
- `label`
- `attribute`
- `description`
2. migrar/renomear campos solicitados (ingles + `FileType`)
3. incluir campos derivados de data (`dt_full`, `dt_date`, `dt_time`) em categoria correta (pedido do usuario: custom)
4. mapear campos de MRK mantidos e nomes de saida padrao

Criterio de aceite:
- dicionarios consistentes e consumiveis por UI/PhotoMetadata

## Etapa 4 - Refactor de `PhotoMetadata` para manager orquestrador
Objetivo:
- transferir responsabilidade de coordenacao de `OBSOLETManager` para `PhotoMetadata`

Acoes:
1. absorver logica de descoberta/coleta de metadata
2. extrair tudo (EXIF + XMP + CUSTOM + MRK context)
3. gerar JSON temporario com dataset completo
4. oferecer metodo de filtro por lista de campos selecionados
5. manter apenas responsabilidades permitidas no manager

Criterio de aceite:
- pipeline recebe updates filtrados corretamente
- json temporario gerado em toda execucao de metadata

## Etapa 5 - UI dos 3 grids de selecao de campos
Objetivo:
- permitir ao usuario escolher campos por categoria no DroneCoordinates

Acoes:
1. criar 3 collapsibles no plugin
2. montar grids usando `StringAdapter`
3. persistir estado das checkboxes por chave
4. restaurar preferencias ao abrir

Criterio de aceite:
- usuario seleciona/desmarca campos e estado persiste

## Etapa 6 - Evolucao do `CheckboxGridWidget` e `WidgetFactory` com retrocompatibilidade
Objetivo:
- suportar novo formato sem quebrar formato antigo

Acoes:
1. `CheckboxGridWidget` aceitar:
- dict antigo `key -> label`
- lista/dict novo com descricao
2. tooltip por item via `description`
3. metodos:
- `get_checked_keys()`
- `get_unchecked_keys()`
- `get_state_map()`
4. `WidgetFactory.create_checkbox_grid` com API compativel

Criterio de aceite:
- plugins antigos continuam funcionando
- DroneCoordinates usa recurso novo

## Etapa 7 - Integracao pipeline (Step/Task sem romper arquitetura)
Objetivo:
- manter steps existentes e alterar apenas contrato de dados

Acoes:
1. `PhotoMetadataTask` passa lista de campos selecionados ao manager
2. `PhotoMetadataStep` aplica apenas campos filtrados
3. preservar fluxo AsyncPipelineEngine

Criterio de aceite:
- sem regressao no pipeline
- updates aplicados somente para campos selecionados

## Etapa 8 - Integracao com `DroneCoordinatesRunner`
Objetivo:
- runner usar preferencias para filtro de campos

Acoes:
1. ler preferencias salvas pelo dialog
2. montar lista efetiva de campos
3. repassar para contexto/pipeline
4. manter comportamento atual de salvar/layer/style

Criterio de aceite:
- drag-and-drop e runner respeitam filtro de campos

## Etapa 9 - Persistencia robusta e schema de preferencias
Objetivo:
- garantir formato estavel de configuracao

Acoes:
1. definir chaves de preferencia para cada grupo:
- `required_fields_selected`
- `custom_fields_selected`
- `mrk_fields_selected`
2. fallback para defaults quando prefs ausentes
3. migracao leve de prefs legadas se necessario

Criterio de aceite:
- upgrade sem quebrar usuario antigo

## Etapa 10 - Validacao tecnica e fechamento
Objetivo:
- validar execucao ponta a ponta

Acoes:
1. smoke test sintatico dos modulos alterados
2. revisao de logs
3. validar cenarios:
- com e sem fotos
- com e sem filtros
- com runner e dialog
4. atualizar documentacao final/changelog por etapa

Criterio de aceite:
- fluxo completo funcional e rastreavel

## 5. Contrato de dados proposto (alvo)

### 5.1 Saida completa intermediaria (JSON temporario)
Estrutura sugerida:
- indice por foto (nome ou id)
- bloco `raw` (todos os dados extraidos)
- bloco `mrk_context`
- bloco `derived_custom`

### 5.2 Saida filtrada para layer
- apenas campos selecionados pelo usuario
- respeitando nomes/aliases definidos em `MetadataFields`

### 5.3 Regras de merge
- MRK continua fonte principal de:
1. coordenadas
2. `foto`
3. dados de voo
- Metadata de foto enriquece atributos sem sobrescrever chaves essenciais de geometria

## 6. Riscos e mitigacoes

1. Quebra de plugins antigos por alteracao do checkbox grid.
- Mitigacao: manter assinatura antiga e criar adaptador interno.

2. Divergencia entre nomes novos de campos e campos historicos.
- Mitigacao: mapa de aliases em `MetadataFields`.

3. Custo de processamento de metadata em lotes grandes.
- Mitigacao: extracao full + cache temporario JSON + filtro posterior.

4. Problemas de thread-safety.
- Mitigacao: manter extracao em Task; aplicar update no Step.

5. Falhas por imports nao padronizados nas classes novas.
- Mitigacao: etapa dedicada de padronizacao antes da integracao.

## 7. Decisoes de arquitetura aprovadas nesta conversa

1. Nao alterar o mecanismo geral de Steps/AsyncPipelineEngine.
2. `PhotoMetadata` vira manager/orquestrador.
3. `Runner` herda preferencias do plugin para filtros.
4. UI tera 3 grupos de campos selecionaveis.
5. Campos de metadata antigos considerados insuficientes e substituidos pelo novo padrao.

## 8. Checklist de rastreabilidade

Cada etapa concluida deve:
1. atualizar `docs/ia/todo.txt`
2. atualizar `docs/ia/changelog.txt`
3. registrar arquivos alterados
4. registrar impactos e proximos passos

## 9. Perguntas em aberto para alinhar antes das etapas de codigo pesado

1. Para os campos MRK em ingles, qual nomenclatura final voce quer para cada um destes:
- `flight_number`
- `flight_name`
- `folder_level1`
- `folder_level2`
2. O campo `FileType` deve manter o valor atual de extensao (ex: `.JPG`) ou formato expandido (ex: `JPEG_RGB`)?
3. O JSON temporario deve ser:
- sempre sobrescrito por execucao, ou
- manter historico por timestamp?

Estas respostas nao bloqueiam a etapa 2 (padronizacao tecnica), mas vao orientar a etapa 3/4 sem retrabalho.


