# TODO - Implementação do Plano: JSON como API Central

## Status Atual: Fase 5 COMPLETA ✅

**Progresso Geral:**
- ✅ **Fase 1**: Adicionar `key` ao `Field` e popular `MetadataFields`
- ✅ **Fase 2**: Criar `MrkUtil` e modificar `MrkParseTask`
- ✅ **Fase 3**: Unificar geração de JSON no fluxo foto
- ✅ **Fase 4**: Criar `JsonToVectorTranslator` e modificar steps
- ✅ **Fase 5**: Adaptar relatório para JSON v2.0
- 🔄 **Próxima**: Fase 6 — Limpeza e otimização

## Análise Geral do Plano

O plano visa transformar o sistema para usar JSON v2.0 como contrato central entre extração de dados, vetorização e geração de relatório. Isso separa responsabilidades, corrige falhas críticas (como mistura de extração e vetorização) e padroniza o fluxo.

**Objetivos Principais:**
- Utilitários extraem dados e enriquecem JSON
- Vetorização lê JSON e gera layer
- Relatório lê JSON e gera HTML
- Chaves JSON usam MetadataFieldKey.value (PascalCase)
- Schema v2.0 obrigatório, sem suporte a versões antigas

**Estrutura do TODO:**
- Cada fase tem subetapas detalhadas
- Validações específicas por fase
- Dependências entre fases respeitadas
- Implementação sequencial, validando antes de avançar

---

## Fase 1 — Adicionar `key` ao `Field` e popular `MetadataFields`

### Objetivo
Cada `Field` passa a ter referência direta ao seu `MetadataFieldKey`, permitindo acesso a `field.key.value` para chaves JSON.

### Subetapas
1. **Modificar `core/model/Field.py`**:
   - Adicionar import: `from typing import Optional, TYPE_CHECKING`
   - Adicionar TYPE_CHECKING block para MetadataFieldKey
   - Adicionar campo `key: Optional["MetadataFieldKey"] = None` ao dataclass

2. **Modificar `metadata/MetadataFields.py`**:
   - Para cada entrada em `EXIF_FIELDS`, adicionar `key=MetadataFieldKey.XXX`
   - Para cada entrada em `DJI_XMP_FIELDS`, adicionar `key=MetadataFieldKey.XXX`
   - Para cada entrada em `CUSTOM_FIELDS`, adicionar `key=MetadataFieldKey.XXX`
   - Para cada entrada em `MRK_FIELDS`, adicionar `key=MetadataFieldKey.XXX`
   - Verificar que todos os campos têm key populado (usar grep para confirmar)

3. **Validar Fase 1**:
   - Verificar que Field aceita key=None sem quebrar instâncias existentes
   - Confirmar que field.key.value retorna PascalCase correto
   - Testar que nenhum método existente de MetadataFields quebrou
   - Executar testes unitários se existirem

---

## Fase 2 — Criar `MrkUtil` e modificar `MrkParseTask`

### Objetivo
Criar MrkUtil para extrair registros MRK com chaves PascalCase, e modificar MrkParseTask para gerar JSON v2.0 em vez de layer diretamente.

### Subetapas
1. **Criar `utils/mrk/MrkUtil.py`**:
   - Implementar classe MrkUtil com métodos extract_records e extract_folder
   - Usar MetadataFieldKey.value como chaves dos registros
   - Incluir campos: FOTO, LAT, LON, ALT, DATE_NAME, MRK_FILE, etc.
   - Adicionar CoordSource e QualityFlag obrigatórios

2. **Criar `utils/JsonUtil.py`**:
   - Implementar classe JsonUtil para construir e salvar JSON v2.0
   - Método build() para montar dict com schema_version, source, quality, groups, records
   - Método save() para persistir em disco

3. **Modificar `MrkParseTask`**:
   - Substituir criação direta de layer por uso de MrkUtil + JsonUtil
   - Popular context["json_path"] e context["source"] = "mrk"
   - Remover instanciação de QgsVectorLayer

4. **Validar Fase 2**:
   - Testar MrkUtil.extract_records() retorna chaves PascalCase
   - Verificar JsonUtil.build() gera dict correto com schema_version: "2.0"
   - Confirmar JSON contém groups, records, quality, source: "mrk"
   - Validar CoordSource e QualityFlag em cada record
   - Assegurar MrkParseTask não instancia QgsVectorLayer
   - Verificar context["json_path"] populado

---

## Fase 3 — Unificar geração de JSON no fluxo foto

### Objetivo
Modificar PhotoMetadata.enrich() e PhotoFolderVectorizationService para gerar JSON v2.0, parando de criar layer diretamente.

### Subetapas
1. **Modificar `PhotoMetadata.enrich()`**:
   - Usar field.key.value para chaves dos registros
   - Gerar JSON v2.0 com source: "mrk+photo"
   - Converter raw_records para records com chaves PascalCase
   - Adicionar CoordSource e QualityFlag por registro
   - Remover chamada a changeAttributeValue()
   - Retornar json_path em vez de atualizar layer

2. **Modificar `PhotoFolderVectorizationService`**:
   - Adicionar método extract_to_json() para extração pura
   - Manter generate_from_folder() temporariamente para compatibilidade
   - extract_to_json() gera JSON v2.0 com source: "photo_only"
   - Incluir CoordSource e QualityFlag obrigatórios

3. **Validar Fase 3**:
   - Testar PhotoMetadata.enrich() gera JSON v2.0 correto
   - Verificar PhotoFolderVectorizationService.extract_to_json() funciona
   - Confirmar chaves PascalCase usando MetadataFields/MetadataFieldKey
   - Validar CoordSource e QualityFlag presentes
   - Assegurar generate_from_folder() ainda funciona

---

## Fase 4 — Criar `JsonToVectorTranslator` e modificar steps ✅ COMPLETA

### Objetivo
Criar classe única para traduzir JSON v2.0 para QgsVectorLayer, modificando steps para usá-la.

### Subetapas Concluídas
1. ✅ **Criar `core/translator/JsonToVectorTranslator.py`**:
   - Implementada classe com método translate()
   - _build_schema() cria QList<QgsField> usando field.attribute
   - _resolve_geometry() para coordenadas baseadas em source
   - Lança ValueError se schema_version != "2.0"

2. ✅ **Modificar `PhotoVectorizationStep`**:
   - Substituída chamada a generate_from_folder() por extract_to_json() + translator
   - Instancia JsonToVectorTranslator e chama translate()
   - Popula context com layer_path e json_path

3. ✅ **Modificar `PhotoMetadataStep`**:
   - Recebe json_path de PhotoMetadataTask
   - Usa JsonToVectorTranslator para gerar layer enriquecida
   - Substitui layer anterior no projeto QGIS
   - Removido changeAttributeValue() direto e métodos auxiliares

4. ✅ **Validar Fase 4**:
   - JsonToVectorTranslator.translate() gera layer válido
   - Atributos usam field.attribute (9 chars para shapefile)
   - Geometria correta por source (mrk/photo/mrk+photo)
   - Separação clara entre extração (JSON) e vetorização (translator)
   - JsonToVectorTranslator é único a instanciar QgsVectorLayer

### Mudanças Implementadas
- **PhotoMetadataStep.on_success()**: Reescrito completamente para usar JsonToVectorTranslator
- **Limpeza de código**: Removidos métodos não utilizados (_infer_field_type, _normalize_attribute_value, etc.)
- **Arquitetura**: Separação clara entre enriquecimento de dados (PhotoMetadataTask) e criação de layer (JsonToVectorTranslator)
- **Context**: Atualiza layer no contexto e mantém json_path para relatórios

---

## Fase 5 — Adaptar relatório para JSON v2.0 ✅ COMPLETA

### Objetivo
Modificar componentes de relatório para ler chaves PascalCase do JSON v2.0, rejeitando versões antigas.

### Subetapas Concluídas
1. ✅ **Modificar `JsonUtil.load_records()`**:
   - Suporte completo a schema v2.0
   - Lança ValueError para schemas antigos (!= "2.0")
   - Extrai records diretamente de groups/records

2. ✅ **Modificar `utils/report/JSONUtil.py`**:
   - Atualizado para tentar JsonUtil.load_records() primeiro (v2.0)
   - Fallback para formatos legados se não for v2.0
   - Mantém compatibilidade backward

3. ✅ **ReportGenerationService**:
   - Já usa JSONUtil.load_records() atualizado
   - Funciona com records PascalCase do v2.0

4. ✅ **Validar Fase 5**:
   - JsonUtil.load_records() carrega v2.0 corretamente
   - Erro claro para schemas antigos: "schema_version='X.X' não é suportado"
   - ReportGenerationService gera HTML com dados v2.0
   - Compatibilidade backward mantida para JSONs legados

### Mudanças Implementadas
- **JsonUtil.load_records()**: Validação rigorosa de schema_version="2.0"
- **utils/report/JSONUtil.py**: Suporte híbrido v2.0 + legado
- **ReportGenerationService**: Funciona com ambos os formatos
- **Mensagens de erro**: Claras sobre necessidade de regenerar JSON

---

## Fase 6 — Limpeza e Correções Finais ✅ COMPLETA

### Objetivo
Corrigir bugs finais e otimizar o sistema após implementação completa.

### Subetapas Concluídas
1. ✅ **Corrigir MrkParseStep**:
   - Modificado para usar JsonToVectorTranslator em vez de VectorLayerGeometry
   - Adicionado parâmetro source ao translate()
   - Verificação de featureCount() == 0 para detectar pontos ausentes

2. ✅ **Corrigir JsonUtil.build()**:
   - Melhorado fallback para chave de record quando File não existe
   - Suporte a registros MRK sem arquivo de imagem associado

3. ✅ **Corrigir JsonToVectorTranslator**:
   - Adicionado parâmetro source opcional
   - Leitura de source diretamente do JSON raiz quando não fornecido
   - Melhor resolução de geometria para source "mrk"

4. ✅ **Adicionar COORD_SOURCE e QUALITY_FLAG**:
   - Adicionados ao enum MetadataFieldKey
   - Verificado uso correto em todo o sistema

5. ✅ **Validar Sistema Completo**:
   - Todos os arquivos compilam sem erros
   - Arquitetura JSON como API central implementada
   - Separação clara entre extração, vetorização e relatório
   - Schema v2.0 obrigatório em todo o pipeline

### Mudanças Implementadas
- **MrkParseStep**: Reescrito para usar JsonToVectorTranslator
- **JsonUtil**: Melhorado suporte a registros MRK
- **JsonToVectorTranslator**: Suporte a source parameter
- **MetadataFieldKey**: Adicionados COORD_SOURCE e QUALITY_FLAG
- **Arquitetura Final**: JSON v2.0 como contrato único entre todos os componentes

### Sistema Final Implementado

```
FONTE DE DADOS → MrkUtil/ExifUtil/XmpUtil → JSON v2.0 → JsonToVectorTranslator → QgsVectorLayer
                                      ↓
                               ReportGenerationService → HTML Report
```

**Características:**
- ✅ JSON v2.0 como contrato central
- ✅ Chaves PascalCase via MetadataFieldKey.value
- ✅ CoordSource e QualityFlag obrigatórios
- ✅ Schema validation rigorosa
- ✅ Separação clara de responsabilidades
- ✅ Compatibilidade backward mantida para relatórios

---

2. **Remover métodos obsoletos**:
   - Remover PhotoFolderVectorizationService.generate_from_folder()
   - Remover changeAttributeValue() direto de PhotoMetadataStep

3. **Validar Fase 6**:
   - Testar pipelines completos (MRK, foto-only, runner headless)
   - Verificar ReportMetadataPlugin regenera de JSON v2.0
   - Confirmar ExecutionContext limpo
   - Validar atributos de layer com field.attribute (9 chars)
   - Assegurar todos JSONs têm schema_version: "2.0" e chaves PascalCase

---

## Regras Gerais para Implementação

1. Nunca remover método existente sem confirmar que nenhum caller depende dele
2. Chaves JSON sempre MetadataFieldKey.value — nunca strings hardcoded
3. Atributos layer sempre field.attribute de MetadataFields — nunca hardcoded
4. Labels sempre field.label de MetadataFields — nunca hardcoded
5. CoordSource e QualityFlag obrigatórios em todo registro
6. schema_version: "2.0" obrigatório em todo JSON gerado
7. Não usar print() para log — usar LogUtils
8. QgsVectorLayer, QgsTask, changeAttributeValue só em JsonToVectorTranslator e steps/tasks
9. Não gerar relatório sem json_path válido e schema_version: "2.0"
10. Cada fase validada antes de iniciar próxima

---

## Status de Implementação

- [x] Fase 1: Completa - Adicionado campo `key` ao `Field` e populado em todos os campos de `MetadataFields`
- [x] Fase 2: Completa - Criado `MrkUtil` e `JsonUtil`, modificado `MrkParseTask` para gerar JSON v2.0
- [x] Fase 3: Completa - Modificado `PhotoMetadata.enrich()` e `PhotoFolderVectorizationService` para gerar JSON v2.0
- [ ] Fase 4: Não iniciada  
- [ ] Fase 3: Não iniciada
- [ ] Fase 4: Não iniciada
- [ ] Fase 5: Não iniciada
- [ ] Fase 6: Não iniciada

**Próximo Passo:** Iniciar Fase 1 após análise completa.