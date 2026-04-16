# PLANO DE IMPLEMENTACAO - SISTEMA DE REPORT METADATA (Drone Coordinates + Ferramenta de Regeracao)

## 1. Objetivo
Implementar no Cadmus o sistema de geracao de relatorio HTML baseado no JSON temporario produzido pelo fluxo de Drone Coordinates, migrando com seguranca os componentes da pasta `photo_report` para os modulos definitivos do projeto, sem quebrar o comportamento atual.

Escopo principal:
- Integrar geracao de report no fluxo atual do `DroneCoordinates` quando `Generate Report` estiver marcado.
- Criar nova ferramenta em Agricultura (tipo dialog) para:
  - listar JSONs temporarios disponiveis,
  - regerar HTML a partir de JSON selecionado,
  - abrir pasta de relatorios gerados,
  - gerar camada vetorial a partir de fotos sem MRK.
- Estruturar armazenamento temporario em subpastas dedicadas dentro de `temp`.
- Reduzir acoplamento entre extracao EXIF/XMP/custom para facilitar suporte futuro a drones nao DJI.

## 2. Premissas e Decisoes
1. `photo_report` e area de referencia temporaria; codigo final deve ficar nas pastas oficiais (`core`, `utils`, `plugins`, `resources`).
2. `MetadataFields` e fonte central de campos; nenhum fluxo novo cria campos fora dela.
3. Todos os novos modulos devem usar `LogUtils` com `ToolKey` adequado.
4. `DroneCoordinatesRunner` tambem participa do fluxo de report (nao apenas dialog).
5. JSON temporario passara a ficar em pasta dedicada (ex.: `temp/cadmus/reports/json`).
6. Relatorios HTML gerados ficarao em pasta dedicada (ex.: `temp/cadmus/reports/html`).
7. Interface de listagem de JSON seguira UX semelhante ao `SettingsPlugin` para selecao/listagem.
8. Quando metadados essenciais faltarem (EXIF/XMP), sistema deve continuar, mas com diagnostico de qualidade explicito.

## 3. Estado Atual Validado
- `DroneCoordinates` ja tem checkbox `generate_report` e persistencia de preferencia.
- `ExplorerUtils.create_temp_json` gera JSON no diretio raiz do temp (a evoluir para subpasta dedicada).
- Existe sistema completo de referencia em `photo_report`:
  - `RenderEngine`, `AggregateAnalyzer`, `IMGMetadata`, `JSONUtil`, `RangeMetadataManager`, `template.html`, `config.yaml`, etc.
- Existem classes duplicadas entre `photo_report` e projeto atual:
  - `CustomPhotosFieldsUtil`, `MetadataFields`, `StringAdapter`, `Field`.

Observacao de contexto:
- O arquivo solicitado `photo_report/ESTRUTURA_PROJETO.md` nao foi encontrado no workspace; a referencia usada para arquitetura foi `photo_report/Report_Metadata_System.md`.

## 4. Arquitetura Alvo
### 4.1 Modulos alvo (destino no projeto)
- `utils/report/JSONUtil.py` (novo)
- `utils/report/RangeMetadataManager.py` (novo)
- `utils/report/IMGMetadata.py` (novo)
- `utils/report/AggregateAnalyzer.py` (novo)
- `utils/report/RenderEngine.py` (novo)
- `utils/report/MetadataRecord.py` (opcional, somente se necessario)
- `resources/reports/template.html` (novo)
- `resources/reports/config.yaml` (novo)
- `plugins/ReportMetadataPlugin.py` (novo dialog em Agricultura)
- `core/services/ReportGenerationService.py` (novo servico de orquestracao)

### 4.2 Modulos a adaptar
- `plugins/DroneCoordinates.py`
- `core/services/DroneCoordinatesRunner.py`
- `core/config/ToolRegistry.py`
- `utils/ExplorerUtils.py`
- `utils/StringManager.py` (incluir `_normalize_key` solicitado)
- `core/ui/WidgetFactory.py` (novo helper para botao de abrir relatorios)
- `utils/ToolKeys.py`
- i18n (`Strings_pt_BR`, `Strings_en`, `TranslationManager` conforme necessidade)

### 4.3 Diretorios temporarios padrao
- JSON de entrada do report: `%TEMP%/cadmus/reports/json`
- HTML de saida: `%TEMP%/cadmus/reports/html`
- (Opcional futuro) `%TEMP%/cadmus/reports/assets`

## 5. Estrategia de Migracao do `photo_report`
Migrar por camada, nunca por copia cega.

### 5.1 Camada de dominio/report
- Migrar classes com revisao de imports para padrao do plugin.
- Adequar logging para `LogUtils`.
- Remover dependencias locais de `main.py` standalone.
- Expor API de servico reutilizavel (entrada: json_path; saida: html_path + resumo).

### 5.2 Camada de recursos
- Mover `template.html` e `config.yaml` para `resources/reports/`.
- Garantir leitura de recurso por caminho robusto (relativo ao plugin root).

### 5.3 Camada de integracao com pipeline
- Ligar `DroneCoordinates`/`Runner` ao servico de report usando caminho do JSON temp.
- Se `generate_report=False`, nao executar servico.
- Se `generate_report=True` e JSON invalido/ausente, logar erro e manter camada vetorial.

### 5.4 Camada de ferramentas de usuario
- Nova ferramenta em Agricultura para regeracao manual.
- Listagem de JSONs em pasta dedicada com nome amigavel e metadados (data, tamanho, origem).

## 6. Analise de Conflitos de Classes Duplicadas
Para cada classe duplicada, aplicar matriz de decisao:
1. Existe versao oficial no projeto?
2. Versao `photo_report` tem comportamento novo?
3. Mudanca e compativel com `MetadataFields` central?
4. Mudanca impacta schema de saida?

Resultado esperado:
- Nao manter duplicidade no final.
- Se diferencas forem uteis, portar para classe oficial existente.
- Evitar regressao nas rotinas atuais de MRK/metadata.

## 7. Fluxos Funcionais Alvo
### 7.1 Fluxo A - DroneCoordinates com report automatico
1. Usuario roda Drone Coordinates.
2. Pipeline gera JSON temp em pasta dedicada.
3. Se `generate_report` marcado, chama `ReportGenerationService`.
4. Service gera HTML em pasta de reports.
5. Sistema exibe feedback de sucesso/erro sem interromper camada vetorial.

### 7.2 Fluxo B - Nova ferramenta de report (regeracao)
1. Usuario abre ferramenta de report em Agricultura.
2. Sistema lista JSONs disponiveis no temp dedicado.
3. Usuario escolhe JSON e clica em gerar relatorio.
4. HTML e gerado novamente.
5. Botao adicional abre pasta de relatorios.

### 7.3 Fluxo C - Vetorial sem MRK (fotos puras)
1. Usuario seleciona pasta de fotos.
2. Sistema indexa EXIF/XMP/custom desacoplado.
3. Gera camada de pontos com diagnostico de completude.
4. Se faltarem dados essenciais, alerta de qualidade ruim.
5. Pode gerar report do mesmo conjunto.

## 8. Requisitos de Qualidade e Compatibilidade
- Compatibilidade QGIS 3.16+ (Qt5/Qt6) e Python 3.10+.
- Zero quebra no fluxo atual de Drone Coordinates.
- Logs estruturados com `tool`, `class`, `code` quando relevante.
- Tratamento de erro com mensagens acionaveis para usuario.
- Testes manuais guiados por checklist por fluxo.

## 9. Riscos e Mitigacoes
1. Risco: divergencia de schema JSON entre versoes.
   - Mitigacao: normalizador unico em `JSONUtil` + validacao de campos obrigatorios.
2. Risco: acoplamento forte em DJI/XMP.
   - Mitigacao: separar extratores EXIF, XMP e calculados em camadas independentes.
3. Risco: nomes de campos inconsistentes.
   - Mitigacao: resolver sempre via `MetadataFields` + normalizacao por `StringManager`.
4. Risco: explosao de nulos em custom fields.
   - Mitigacao: classificar null por causa (dado ausente vs calculo indisponivel).
5. Risco: poluicao do `%TEMP%`.
   - Mitigacao: subpastas dedicadas + convencao de nome + limpeza futura controlada.

## 10. Criterios de Aceite por Macroentrega
1. Report automatico funciona no Drone Coordinates com checkbox ativo.
2. JSON e HTML sao salvos em pastas temporarias dedicadas.
3. Nova ferramenta aparece em Agricultura e consegue regerar HTML de JSON escolhido.
4. Botao para abrir pasta de relatorios funciona.
5. Fluxo sem MRK gera camada vetorial e diagnostico util.
6. Classes de `photo_report` foram absorvidas para locais corretos.
7. Duplicidades removidas ou reconciliadas com justificativa tecnica.
8. Changelog atualizado por lote de alteracoes.

## 11. Ordem de Implementacao Recomendada
1. Base tecnica (pastas temp, service de report, recursos html/config).
2. Integracao no DroneCoordinates e Runner.
3. Nova ferramenta de regeracao.
4. Fluxo vetorial sem MRK.
5. Desacoplamento EXIF/XMP/custom e hardening.
6. Limpeza final de duplicidades e consolidacao.

## 12. Entregaveis Documentais
- Plano detalhado (este arquivo).
- `docs/ia/todo.txt` com tarefas executaveis por etapa.
- Atualizacoes de changelog por cada bloco de implementacao concluido.

## 13. Fora de Escopo Nesta Fase
- Implementacao de suporte completo a fabricantes nao DJI.
- Persistencia definitiva de relatorios fora do temp.
- Interface de analytics avancada alem do HTML proposto.
