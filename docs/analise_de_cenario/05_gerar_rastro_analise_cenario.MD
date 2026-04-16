# Análise de Cenário – Gerar Rastro de Implemento

**Visão Geral**

A ferramenta converte trilhas/linhas em uma camada bufferizada que representa a faixa ocupada por um implemento. Opera em camadas do tipo linha, suporta processamento apenas de feições selecionadas e executa um pipeline assíncrono: Explode → Buffer → Save.

**Objetivo**

Gerar um produto vetorial (memória ou arquivo) que represente a área ocupada por um implemento definido em metros, convertido para as unidades da camada de entrada.

**Fluxo resumido**

- Entrada: camada de linhas (via UI).
- Conversão: `VectorLayerProjection.convert_distance_to_layer_units` aplica a transformação de metros → unidades da camada.
- Validação: `VectorLayerSource.validate_layer(..., expected_geometry=QgsWkbTypes.LineGeometry)`.
- Seleção: opcional, via `VectorLayerGeometry.get_selected_features`.
- Pipeline: `ExplodeStep` → `BufferStep` (buffer_distance = implement_lenght/2) → `SaveVectorStep`.
- Pós-processo: adiciona camada ao projeto e aplica QML se solicitado.

**Cenários de Uso (exemplos)**

- Execução sobre toda a camada: processa todas as feições.
- Execução sobre seleção: processa apenas feições selecionadas.
- Salvamento: grava em arquivo se `save_to_folder` válido; caso contrário mantém em memória.
- Aplicação de estilo: aplica `.qml` ao resultado quando fornecido.

**Tipos de geometria**

- Suporta exclusivamente `LineGeometry` na entrada.

**Impactos nos dados**

- Preservado: CRS e atributos (salvo comportamento explícito de `SaveVectorStep`).
- Alterado: criação de nova camada com geometrias bufferizadas; não modifica a camada original por padrão.

**Riscos e controles**

- Unidades incorretas: garantir conversão correta, especialmente para CRS em graus (EPSG:4326).
- Valor zero: operação abortada com mensagem.
- Falha no pipeline: `AsyncPipelineEngine` deve reportar erros via callback e logs.
- Caminho inválido: ferramenta força gravação em memória se o caminho de saída for inválido ou começa com "memory".

**Observações sobre classes-chave**

- `VectorLayerProjection.convert_distance_to_layer_units`: verificar comportamento para CRSs geográficos; considerar reprojeção temporária quando necessário.
- `VectorLayerGeometry.get_selected_features`: deve preservar CRS e esquema de campos.
- `SaveVectorStep`: confirmar preservação de atributos e comportamento ao sobrescrever arquivos.
- `AsyncPipelineEngine`: validar tratamento de cancelamento e exceções.

**Evoluções recomendadas**

- Reprojetar temporariamente para CRS métrico quando apropriado.
- Expor controle de dissolução de buffer na UI.
- Melhorar validação/feedback do caminho de saída.

**Conclusão**

Fluxo consistente e não bloqueante. Priorizar verificação da conversão de unidades para CRSs em graus e a preservação de atributos no `SaveVectorStep`.
