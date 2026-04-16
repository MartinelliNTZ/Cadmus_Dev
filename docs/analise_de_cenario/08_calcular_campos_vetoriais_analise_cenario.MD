# Análise de Cenário – Calcular Campos Vetoriais

**Visão Geral**

A ferramenta calcula atributos geométricos automáticos (área para polígonos, comprimento para linhas, coordenadas X/Y/Z para pontos) com suporte a múltiplos modos de cálculo: Elipsoidal (precisão geodésica), Cartesiana (coordenadas projetadas) ou Ambos (dual-mode com fallback automático para CRS geográfico). Detecta e valida o sistema de coordenadas, criando campos adequados com limite de 10 caracteres para compatibilidade com SHP.

**Objetivo**

Automatizar a geração de atributos geométricos padrão, eliminando cálculos manuais e garantindo consistência de unidades conforme o CRS da camada. Prover modo automático para CRS geográficos onde cálculos cartesianos resultariam em graus² (inválido).

**Fluxo resumido**

- Entrada: camada vetorial editável (ponto, linha ou polígono via UI).
- **Validação KML**: Detecta se a camada é arquivo KML (não editável); se verdadeiro, bloqueia execução com mensagem: "Arquivos KML não são editáveis. Converta para GeoPackage (.gpkg) ou Shapefile (.shp)".
- Validação: `VectorLayerProjection.is_geographic_crs(layer)` detecta CRS geográfico.
- Resolução de modo: se CRS geográfico + modo Cartesiana solicitado, muda automaticamente para "Ambos" com aviso.
- Resolução de conflito: verifica nomes de campo existentes via `layer.fields().lookupField()`.
- Criação de campos: `VectorLayerAttributes.create_point_coordinate_fields()` com limite SHP 10-char via `generate_field_name_with_suffix()`.
- Cálculo: delega a `VectorLayerMetrics.calculate_*()` com parâmetro `use_ellipsoidal=True/False` conforme modo.
- Pós-processo: layer mantém edição aberta (sem commitChanges), mensagem de sucesso exibida apenas se modo não foi alterado automaticamente.

**Cenários de Uso (exemplos)**

- Polígonos com CRS métrico + modo Elipsoidal: calcula área elipsoidal precisa em m².
- Linhas com CRS geográfico (EPSG:4326) + modo Cartesiana solicitado: sistema alerta e executa modo "Ambos" (comprimento_eli + comprimento_car).
- Pontos com altimetria: cria X, Y e invoca `AltimetriaTask` para Z (assíncrono).
- Modo "Ambos": gera ambos os campos (_eli, _car) para comparação dual-mode.

**Tipos de geometria**

- Pontos: calcula X, Y e opcionalmente Z (altimetria via SRTM).
- Linhas: calcula comprimento (length).
- Polígonos: calcula área.
- Multipart: preservado conforme estado geométrico original.

**Impactos nos dados**

- Preservado: geometrias, CRS, campos existentes, estrutura original de atributos.
- Alterado: adição de novos campos (_eli, _car ou base_name conforme modo); preenchimento de valores calculados nas feições existentes.
- Não alterado: layer permanece em modo edição; sem commitChanges() automático.

**Riscos e controles**

- **Arquivo KML**: validação detecta extensão .kml na fonte; bloqueia execução com aviso ao usuário para converter para .gpkg ou .shp (formato editável).
- Colisão de nomes: confirmação interativa ao usuário (sobrescrever/renomear/cancelar).
- CRS geográfico + Cartesiana: validação automática com fallback + aviso ao usuário.
- Altimetria em larga escala: `AltimetriaTask` assíncrona; verificar limite de requisições SRTM para > 5000 feições.
- Unidades inválidas: CRS projetado garante m/m², CRS geográfico faz cálculo em graus (sempre em modo "Ambos").
- Arquivo SHP com campos > 10 char: truncagem via `generate_field_name_with_suffix(max_length=10)`.

**Observações sobre classes-chave**

- `VectorLayerProjection.is_geographic_crs(layer)`: verificar se usa `crs.isGeographic()` corretamente (falha em alguns CRS desatualizados).
- `VectorLayerAttributes.generate_field_name_with_suffix()`: garantir que _eli/_car não ultrapassem limite SHP (ex: "area_eli" = 8 chars, OK; "cumprimento_car" = 15, truncado para "cumpr_car").
- `VectorLayerMetrics.calculate_line_length()` / `calculate_polygon_area()`: validar que parâmetro `use_ellipsoidal=True` usa `QgsDistanceArea.ellipsoidalDistance()` e não projeção temporária.
- `AltimetriaTask`: task assíncrona; cancelamento deve ser respeitado se usuário clicar novo ponto antes de conclusão.
- `BasePlugin.settings_preferences`: verifica se "calculation_method" foi carregado via `init(..., load_settings_prefs=True)`.

**Evoluções recomendadas**

- Permitir seleção de subset de feições para cálculo (ex: apenas selecionadas).
- Reprojetar temporariamente para CRS métrico se CRS origem for geográfico e modo for Cartesiana (em vez de apenas alertar).
- Cache local de altimetria para evitar requisições repetidas (mesmas coordenadas).
- Progresso visual para Altimetria em larga escala (barra com % de conclusão).
- Exportar relatório de tempo médio de cálculo por tipo de geometria e modo.
- Interface para substituir provider de altimetria (SRTM → outros DTM).

**Conclusão**

Ferramenta essencial para padronização de atributos geométricos; fluxo não destrutivo com validações automáticas e avisos inteligentes para CRS problemáticos. Garantir truncagem correta de nomes para SHP e precisão de `VectorLayerMetrics` para modos Elipsoidal/Cartesiana. Altimetria em background é recomendada para camadas > 5000 feições.
