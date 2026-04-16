# Análise de Cenário – Obter Coordenadas de Drone (MRK)

**Visão Geral**

A ferramenta lê arquivos MRK (DJI) e gera camadas vetoriais de pontos (waypoints) e trajeto (rota) do voo. Opcionalmente, enriquece os pontos com metadados de fotos JPG do voo através da classe `PhotoMetadata`. Opera em modo **assíncrono** (via `DronePhotosTask`) para não travar o QGIS durante processamento de grandes volumes.

**Objetivo**

Extrair informações geoespaciais (coordenadas, altitude, ângulos de imagem) de arquivos MRK proprietários DJI e gerar produtos vetoriais reutilizáveis (pontos + trajeto) com opção de enriquecimento por metadados de fotos.

**Fluxo resumido**

- **Entrada:** Caminho para pasta (recursivo/não-recursivo) ou múltiplos arquivos `.mrk`
- **Parsing:** `MrkParser.parse_folder()` ou `MrkParser.parse_file()` extrai waypoints e segmentos de rota
- **Agregação:** Se "unir MRKs" ativo, todos os pontos fundem em `all_points[]`
- **Enriquecimento (opcional):** `PhotoMetadata.enrich()` executa em `DronePhotosTask` (async) buscando fotos JPG nas pastas
- **Criação de camadas:** `VectorLayerGeometry` cria pontos e linhas usando as classes helper `_create_points_layer()` e `_create_line_layer()`
- **Salvamento (opcional):** `VectorLayerSource.save_layer_to_path()` grava em arquivo (GPKG/SHAPEFILE/GeoJSON/KML) ou em memória
- **Aplicação de estilo:** `VectorLayerSource.save_and_load_layer()` aplica QML se fornecido
- **Adição ao projeto:** Camadas são automaticamente adicionadas ao QGIS

**Cenários de Uso (exemplos)**

### Cenário 1: Voo Simples sem Enriquecimento
- User seleciona 1 pasta com 1 arquivo `.mrk`
- "Vasculhar subpastas": desativado
- "Unir MRKs": não aplica (1 arquivo)
- "Cruzar com fotos": desativado
- Resultado: 1 camada de pontos + 1 camada de linhas (trajeto) em memória

### Cenário 2: Múltiplos Voos em Subpastas Unidas
- User seleciona pasta raiz com 5 subpastas, cada uma com um MRK
- "Vasculhar subpastas": ativado
- "Unir MRKs": ativado
- Resultado: Todos os waypoints agregados em 1 camada de pontos, 1 trajeto unificado

### Cenário 3: Processamento com Metadados de Foto
- User seleciona pasta + ativa "Cruzar com fotos"
- `DronePhotosTask` executa assincronamente, enriquecendo pontos com:
  - Nome da foto (file basename)
  - Dimensões da imagem (width × height)
  - Metadados EXIF (ISO, f-stop, focal_length, camera_make)
- Callback notifica plugin quando completo (progress bar atualizado)

### Cenário 4: Salvamento em Arquivo com Reprojeção KML
- User seleciona múltiplos MRKs + marca "Salvar em arquivo" (KML)
- Camadas são geradas em EPSG do projeto
- Antes do salvamento, reprojeção automática para EPSG:4326 (KML requer WGS84)
- Arquivo `.kml` criado em disco e carregado no QGIS

## Tipos de Geometria

- **Entrada:** N/A (apenas lê arquivo MRK)
- **Saída pontos:** QgsWkbTypes.PointGeometry (Point com M e Z)
- **Saída trajeto:** QgsWkbTypes.LineGeometry (LineString com M e Z)

## Impactos nos Dados

- **Preservado:**
  - CRS original (se especificado no MRK) ou CRS do projeto
  - Altitude (Z) em cada ponto
  - Sequência cronológica de waypoints
  - Nomes de fotos (se enriquecimento ativado)

- **Alterado:**
  - Criação de novos campos se enriquecimento de foto ativado (photo_name, photo_width, photo_height, photo_iso, etc.)
  - Possível reprojeção para EPSG:4326 se formato KML

## Riscos e Controles

### Risco: MRK Inválido ou Corrompido
- **Controle:** `MrkParser.parse_file()` trata exceções e reporta via log; arquivo é pulado
- **Mitigation:** Log registra quantos MRKs foram processados com sucesso (Code="MRK_FILES_FOUND")

### Risco: Foto Não Encontrada
- **Controle:** `PhotoMetadata.enrich()` trata FileNotFoundError; ponto é criado sem metadados de foto
- **Mitigation:** Log registra quantas fotos foram encontradas vs esperadas

### Risco: Driver QGIS Incompatível
- **Controle:** Validação do caminho de saída; revert para memória se driver inválido
- **Mitigation:** `VectorLayerSource.save_layer_to_path()` encapsula lógica de fallback

### Risco: Travamento em Grandes Volumes
- **Controle:** `DronePhotosTask` executa em worker thread; UI nunca bloqueia
- **Mitigation:** Progress callback notifica interface de execução assíncrona

### Risco: CRS Inconsistente
- **Controle:** Se MRK não declara CRS, assume CRS do projeto QGIS
- **Mitigation:** Documentação instrui user a verificar CRS antes de salvar

## Observações sobre Classes-Chave

### MrkParser
- Método `parse_folder()` conhecido por bug: **processa apenas 1 arquivo em vez de múltiplos** [Bug conhecido 1.6.2]
- Workaround: selecionar arquivos manualmente via interface multi-seleção
- Método `parse_file()` é confiável para arquivos individuais

### PhotoMetadata.enrich()
- Busca fotos na mesma pasta ou subpastas (recursivo por padrão)
- Retorna lista de dicts com estrutura: `[{"coords": (lat, lon, alt), "photo_data": {...}}, ...]`
- Thread-safe para execução em DronePhotosTask

### DronePhotosTask (QgsTask)
- Herda de `QgsTask` para integração com progress bar do QGIS
- Método `run()` executa `PhotoMetadata.enrich()` assincronamente
- Callback `finished()` notifica plugin com resultado
- **Recentemente migrado para LogUtilsNew** (v1.6.2) para logging semântico

### VectorLayerGeometry
- Métodos estáticos `_create_points_layer()` e `_create_line_layer()` criam "caixa preta" das geometrias
- Preservam Z (altitude) e M (ordem) em geometrias multi-dimensionais
- CRS propagado automaticamente

### VectorLayerSource
- Método `save_layer_to_path()` encapsula lógica de flavor (GPKG vs SHAPEFILE vs GeoJSON vs KML)
- Renomeação automática se arquivo existente (rename_if_exists=True)
- Reprojeção automática para EPSG:4326 se destino é KML

## Evoluções Recomendadas

1. **Corrigir MrkParser.parse_folder()** para processar TODOS os MRKs (fix para bug 1.6.2)
2. **Cache de fotos:** Implementar índice em memória para evitar rescans filesystem em múltiplos enriquecimentos
3. **Filtrage de campos:** Permitir user seleção de quais metadados EXIF incluir (reduz tamanho de camada)
4. **Progress granular:** Desenhar progress bar separadamente para parsing vs enriquecimento
5. **Suporte a waypoint interpolation:** Interpolar coordenadas entre waypoints para "suavizar" trajeto

## Impacto de Thread-Safety

- **PhotoMetadata.enrich():** Thread-safe (apenas leitura de FS, sem estado compartilhado)
- **DronePhotosTask:** Thread-safe (worker thread não toca em QgsVectorLayer)
- **VectorLayerGeometry:** Must criar camadas subasequent in main thread via callback (✓ já implementado)

## Conclusão

Arquitetura sólida com processamento assíncrono. Priorizar:
1. Validação do path de saída (fallback para memória)
2. Tratamento de fotos faltantes (skip sem falhar)
3. Documentação de limitações de MrkParser.parse_folder() (usuário treinado sobre workaround)
4. Monitoramento de performance com >1000 waypoints
