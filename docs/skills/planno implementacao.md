# Plano de Implementação — JSON como API Central

## Contexto

O objetivo é fazer com que o JSON gerado pelo sistema se torne o contrato único entre
extração de dados, vetorização e geração de relatório.

Hoje o sistema mistura extração, criação de layer e geração de relatório dentro dos mesmos
componentes. A separação proposta é:

1. Utilitários extraem dados e **enriquecem o JSON**
2. Vetorização lê o JSON e gera o layer
3. Relatório lê o JSON e gera o HTML

O JSON usa `MetadataFieldKey.value` (PascalCase) como chaves dos registros.
 — `MetadataFieldKey` já é o catálogo de chaves.
`MetadataFields` é o dicionário que associa cada `MetadataFieldKey` a um `Field` com
`normalized`, `core`, `label`, `attribute`, `description`, `level` e agora `key`.

---

## Schema do JSON Canônico v2.0

```json
{
  "schema_version": "2.0",
  "source": "mrk | mrk+photo | photo_only",
  "tool_key": "drone_coordinates",
  "base_folder": "/path/to/base",
  "recursive": false,
  "generated_at": "2025-01-01T00:00:00Z",
  "quality": {
    "total_files": 120,
    "with_coords": 118,
    "without_coords": 2,
    "with_xmp": 118,
    "with_exif_gps": 2,
    "missing_xmp_and_exif": 0
  },
  "groups": {
    "/path/to/folder": {
      "MrkFile": "flight_001.mrk",
      "FlightName": "voo_01",
      "FlightNumber": 1,
      "points_count": 60,
      "indexed_count": 60,
      "records": {
        "DJI_0001.JPG": {
          "File": "DJI_0001.JPG",
          "Path": "/path/to/folder/DJI_0001.JPG",
          "GpsLatitude": -23.5,
          "GpsLongitude": -46.6,
          "AbsoluteAltitude": 120.3,
          "CoordSource": "XMP",
          "QualityFlag": "ok",
          "ShutterSpeedValue": "1/1000",
          "GimbalYawDegree": -45.2,
          "RtkFlag": 50,
          "FlightNumber": 1,
          "FlightName": "voo_01",
          "MrkFile": "flight_001.mrk",
          "Lat": -23.5,
          "Lon": -46.6,
          "Alt": 120.3,
          "Foto": 1
        }
      }
    }
  }
}
```

**Regras:**
- Todas as chaves de registro usam `MetadataFieldKey.value` (PascalCase)
- `CoordSource` e `QualityFlag` obrigatórios em todo registro, nos dois fluxos
- Campos MRK (`Lat`, `Lon`, `Alt`, `Foto`, `MrkFile`) presentes quando `source` inclui `mrk`
- `schema_version: "2.0"` obrigatório em todo JSON gerado pelo sistema novo
- JSONs antigos (DPM/PFM) não são suportados — se o usuário tentar usar um JSON antigo,
  o sistema lança erro claro pedindo para regenerar
- Caminho de obter via MRK file agora gera json inclusive para quando nao cruza dados com metadados de fotos, ou seja, o json é o contrato único para todo o fluxo, independente da fonte dos dados
e o vetor e gerado a partir dele dessa forma o fluxo e o mesmo obtem dados enriquece e depois vetoriza apartir do json gerado 
a diferença que dados a partir de mrk serao poucos ne mas estao no json e garante padronizacao 
MRKParser agora se torna MrkUtil. 
---

## Fluxo Unificado

```
FONTE DE DADOS
│
▼
┌──────────────────────────────────────┐
│        UTILITÁRIOS DE EXTRAÇÃO       │
│                                      │
│  MrkUtil         → campos MRK        │
│  ExifUtil        → campos EXIF       │
│  XmpUtil         → campos XMP        │
│  CustomFieldsUtil → campos derivados │
│                                      │
│  Todos enriquecem o mesmo JSON       │
└────────────────┬─────────────────────┘
                 │
                 ▼
         JSON Canônico v2.0
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌──────────────┐  ┌──────────────────┐
│ JsonToVector │  │ ReportGeneration │
│ Translator   │  │ Service          │
│              │  │                  │
│ JSON → layer │  │ JSON → HTML      │
└──────────────┘  └──────────────────┘
```

---

## Fase 1 — Adicionar `key` ao `Field` e popular `MetadataFields`

### Objetivo

Cada `Field` passa a ter referência direta ao seu `MetadataFieldKey`.
Com isso qualquer componente que já tenha um `Field` consegue acessar
o valor da chave do registro JSON via `field.key.value`.

---

### `core/model/Field.py`

Adicionar o campo `key` como opcional para não quebrar instâncias existentes.

```python
# ANTES
@dataclass
class Field:
    normalized: str
    core: str
    label: str
    attribute: str
    description: str
    level: int

# DEPOIS
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from ...core.enum import MetadataFieldKey

@dataclass
class Field:
    normalized: str
    core: str
    label: str
    attribute: str
    description: str
    level: int
    key: Optional["MetadataFieldKey"] = None
```

---

### `metadata/MetadataFields.py`

Adicionar `key=MetadataFieldKey.XXX` em todas as entradas de
`EXIF_FIELDS`, `DJI_XMP_FIELDS`, `CUSTOM_FIELDS` e `MRK_FIELDS`.

```python
# Exemplo
MetadataFieldKey.ABSOLUTE_ALTITUDE: Field(
    normalized="xmp_bloco_1:drone-dji:AbsoluteAltitude",
    core="xmp_bloco_1",
    label="Absolute Altitude",
    attribute="AbsY",
    description="Altitude absoluta da aeronave. [AbsY]",
    level=3,
    key=MetadataFieldKey.ABSOLUTE_ALTITUDE,
),
```

Aplicar em **todos** os campos dos quatro dicionários sem exceção.

---

### Validação da Fase 1

- [ ] `Field` aceita `key=None` sem quebrar nenhuma instância existente
- [ ] Todos os campos de `EXIF_FIELDS`, `DJI_XMP_FIELDS`, `CUSTOM_FIELDS`, `MRK_FIELDS`
      têm `key` populado
- [ ] `field.key.value` retorna a string PascalCase correta
      (ex: `MetadataFieldKey.ABSOLUTE_ALTITUDE` → `"AbsoluteAltitude"`)
- [ ] Nenhum método existente de `MetadataFields` quebrado

---

## Fase 2 — Criar `MrkUtil` 

### Objetivo

`MrkUtil` extrai registros do arquivo MRK no mesmo padrão de `ExifUtil` e `XmpUtil`.
`MrkParseTask` para de criar layer diretamente e passa a gerar JSON.

---

### `utils/mrk/MrkUtil.py` (att antigo mrkparser )

```python
class MrkUtil:
    """
    Extrai campos de um arquivo MRK e retorna registros normalizados.
    Chaves dos registros usam MetadataFieldKey.value (PascalCase).
    Mesmo padrão de ExifUtil e XmpUtil.
    """

    @staticmethod
    def extract_records(mrk_path: str) -> List[Dict[str, object]]:
        """
        Lê um arquivo MRK e retorna lista de registros.
        Cada registro contém:
          - MetadataFieldKey.FOTO.value       → número da foto
          - MetadataFieldKey.LAT.value        → latitude MRK
          - MetadataFieldKey.LON.value        → longitude MRK
          - MetadataFieldKey.ALT.value        → altitude MRK
          - MetadataFieldKey.DATE_NAME.value  → data derivada do nome
          - MetadataFieldKey.MRK_FILE.value   → nome do arquivo MRK
          - MetadataFieldKey.MRK_PATH.value   → caminho absoluto do MRK
          - MetadataFieldKey.MRK_FOLDER.value → pasta do MRK
          - MetadataFieldKey.FLIGHT_NUMBER.value
          - MetadataFieldKey.FLIGHT_NAME.value
          - MetadataFieldKey.FOLDER_LEVEL_1.value
          - MetadataFieldKey.FOLDER_LEVEL_2.value
        """
        ...

    @staticmethod
    def extract_folder(mrk_folder: str, recursive: bool = False) -> List[Dict[str, object]]:
        """
        Varre pasta de arquivos MRK e agrega todos os registros.
        """
        ...
```

---

### `utils/JsonUtil.py` (novo)

```python
class JsonUtil:
    """
    Constrói o JSON e tambem responsavel por manipulacao do mesmo
    """


### Modificação: `MrkParseTask`

```python
# ANTES
# MrkParseTask lê MRK, cria pontos e layer diretamente

# DEPOIS
# 1. Usa MrkUtil.extract_folder() para obter registros
# 2. Usa JsonUtil.build() para montar o JSON v2.0
# 3. Usa JsonUtil.save() para salvar em disco
# 4. Popula context["json_path"] com o caminho do JSON gerado
# 5. Popula context["source"] = "mrk"
# NÃO cria QgsVectorLayer — isso passa para o JsonToVectorTranslator (Fase 4)
```

---

### Validação da Fase 2

- [ ] `MrkUtil.extract_records()` retorna lista com chaves PascalCase corretas
- [ ] `JsonUtil.build()` gera dict com `schema_version: "2.0"`
- [ ] JSON gerado contém `groups`, `records`, `quality`, `source: "mrk"`
- [ ] `CoordSource: ` presente em cada record
- [ ] `QualityFlag` presente em cada record
- [ ] `MrkParseTask` não instancia `QgsVectorLayer`
- [ ] `context["json_path"]` populado ao final do step

---

## Fase 3 — Unificar geração de JSON no fluxo foto

### Objetivo

`PhotoMetadata.enrich()` e `PhotoFolderVectorizationService` passam a gerar
JSON v2.0 .
`PhotoFolderVectorizationService` para de criar layer diretamente.

---

### Modificação: `PhotoMetadata.enrich()`

```python
# ANTES
# Gera DPM*.json com raw_records e chaves mistas
# Atualiza layer via changeAttributeValue()

# DEPOIS
# Usa field.key.value para montar as chaves de cada registro
# Gera ou usa json existente JSON v2.0 com source: "mrk+photo"
# raw_records → records MetadataFieldKey.value como chave
# CoordSource e QualityFlag adicionados por registro
# NÃO chama changeAttributeValue() — retorna json_path
# O layer é responsabilidade do JsonToVectorTranslator (Fase 4)
```

---

### Modificação: `PhotoFolderVectorizationService`

```python
# Novo método — extração pura, sem layer:
def extract_to_json(
    self,
    base_folder: str,
    recursive: bool,
    tool_key: str,
    selected_fields: List[str],
) -> str:
    """
    Extrai metadata das fotos e salva JSON v2.0.
    Não cria QgsVectorLayer.
    Retorna caminho do JSON gerado.
    source: "photo_only"
    CoordSource e QualityFlag obrigatórios em cada registro.
    """
    ...

# generate_from_folder() mantida sem alteração para não quebrar
# callers existentes enquanto a Fase 4 não estiver validada.
# Será removida na Fase 6.
```

---

### Validação da Fase 3

- [ ] `PhotoMetadata.enrich()` gera JSON v2.0 com `source: "mrk+photo"`
- [ ] `PhotoFolderVectorizationService.extract_to_json()` gera JSON v2.0 com `source: "photo_only"`
- [ ] Ambos os JSONs têm chaves PascalCase usando sempre os catalogos MetadataFields e MetadataFieldkey nos records nao usar stringhardcode para as chaves
- [ ] `CoordSource` e `QualityFlag` presentes nos dois fluxos
- [ ] `generate_from_folder()` continua funcionando sem alteração

---

## Fase 4 — Criar `JsonToVectorTranslator`

### Objetivo

Uma única classe responsável por ler JSON v2.0 e gerar `QgsVectorLayer`.
É o único componente do sistema que instancia `QgsVectorLayer`.
Usa `field.attribute` de `MetadataFields` para garantir nomes de 9 chars no shapefile.

---

### `core/translator/JsonToVectorTranslator.py` (novo)

```python
class JsonToVectorTranslator:
    """
    Traduz JSON canônico v2.0 para QgsVectorLayer.

    Para cada registro:
    - busca o Field em MetadataFields via field.key
    - usa field.attribute como nome do atributo no layer (máx 9 chars)
    - usa field.label para documentação interna

    Geometria:
    - source "mrk":        usa MetadataFieldKey.LAT / LON / ALT(mesmo campos usados hj para vetorizar a partir do MRK)
    - source "mrk+photo":  usa MetadataFieldKey.GPS_LATITUDE / GPS_LONGITUDE / ABSOLUTE_ALTITUDE (mesmos campos usados hj )
    - source "photo_only": usa MetadataFieldKey.GPS_LATITUDE / GPS_LONGITUDE / ABSOLUTE_ALTITUDE(mesmos campos usados hj )
    - fallback:            qualquer campo de coordenada válido presente no registro
    """

    def translate(
        self,
        json_path: str,
        layer_name: str,
        selected_keys: Optional[List[str]] = None,
    ) -> QgsVectorLayer:
        """
        Lê o JSON v2.0, monta schema de campos, cria features com
        geometria Point e retorna o layer.
        Lança ValueError se schema_version != "2.0".
        """
        ...

    def _build_schema(
        self,
        sample_record: Dict,
        selected_keys: Optional[List[str]],
    ) -> List[QgsField]:
        """
        Para cada chave do registro, busca o Field em MetadataFields
        e usa field.attribute como nome do QgsField.
        Chaves sem Field catalogado usam a própria chave truncada a 9 chars.
        """
        ...

    def _resolve_geometry(self, record: Dict, source: str) -> Optional[QgsPointXY]:
        """
        Resolve coordenadas conforme source e CoordSource do registro.
        """
        ...
```

---

### Modificação: `PhotoVectorizationStep`

```python
# ANTES
# Chama PhotoFolderVectorizationService.generate_from_folder() que cria layer

# DEPOIS
# 1. Chama PhotoFolderVectorizationService.extract_to_json() → json_path
# 2. Instancia JsonToVectorTranslator
# 3. Chama translator.translate(json_path, layer_name) → layer - layer_path
# 4. Coloca layer_path e json_path no contexto
```

---

### Modificação: `PhotoMetadataStep`

```python
# ANTES
# on_success() chama changeAttributeValue() diretamente no layer

# DEPOIS
# on_success() recebe json_path gerado por PhotoMetadataTask
# Instancia JsonToVectorTranslator
# Gera novo layer a partir do JSON enriquecido
# Substitui o layer anterior no contexto
# Não chama changeAttributeValue() diretamente
```

---

### Validação da Fase 4

- [ ] `JsonToVectorTranslator.translate()` gera layer válido a partir de JSON v2.0
- [ ] Atributos do layer usam `field.attribute` (9 chars)
- [ ] Geometria correta para `source: "mrk"` (Lat/Lon)
- [ ] Geometria correta para `source: "photo_only"` e `"mrk+photo"` (GpsLatitude/GpsLongitude)
- [ ] Layer gerado é equivalente ao layer atual (mesmos campos, mesmas geometrias)
- [ ] `PhotoVectorizationStep` não chama mais `generate_from_folder()` diretamente
- [ ] `PhotoMetadataStep` não chama mais `changeAttributeValue()` diretamente
- [ ] `JsonToVectorTranslator` é o único lugar do sistema que instancia `QgsVectorLayer`

---

## Fase 5 — Adaptar relatório para JSON v2.0

### Objetivo

`ReportGenerationService`, `IMGMetadata` e `JSONUtil` passam a ler
chaves PascalCase do JSON v2.0.
JSONs antigos não são suportados — erro claro ao tentar usar.

---

### Modificação: `JSONUtil.load_records()`

```python
def load_records(json_path: str) -> List[dict]:
    with open(json_path) as f:
        data = json.load(f)

    version = data.get("schema_version")

    if version == "2.0":
        return _load_v2(data)

    raise ValueError(
        f"JSON com schema_version='{version}' não é suportado. "
        "Regenere o JSON usando a versão atual do plugin."
    )

def _load_v2(data: dict) -> List[dict]:
    """
    Lê groups/records do schema v2.0 e retorna lista plana de registros.
    Registros já chegam com chaves PascalCase (MetadataFieldKey.value).
    """
    records = []
    for group in data.get("groups", {}).values():
        for record in group.get("records", {}).values():
            records.append(record)
    return records
```

---

### Modificação: `IMGMetadata`

```python
# ANTES
# Resolve campos por aliases e normalized strings mistas

# DEPOIS
# Resolve campos diretamente por MetadataFieldKey.value (PascalCase)
# Ex: record.get(MetadataFieldKey.ABSOLUTE_ALTITUDE.value)
# Usa field.label via MetadataFields para display no HTML
```

---

### Modificação: `ReportGenerationService`

```python
# Sem mudança estrutural.
# Records já chegam com chaves PascalCase via JSONUtil.load_records().
# Labels para display buscados via MetadataFields (field.label).
```

---

### Validação da Fase 5

- [ ] `JSONUtil.load_records()` carrega JSON v2.0 corretamente
- [ ] `JSONUtil.load_records()` lança `ValueError` claro para JSONs sem `schema_version: "2.0"`
- [ ] `IMGMetadata.score()` resolve todos os campos por PascalCase
- [ ] Relatório HTML gerado com labels corretos
- [ ] `ReportMetadataPlugin` funciona end-to-end com JSON v2.0

---

## Fase 6 — Limpeza

### Objetivo

Remover código que existia apenas por compatibilidade e simplificar `ExecutionContext`.

---

### `ExecutionContext` — remover após confirmação de que nenhum caller usa

```python
# Remover:
# "points"                   → substituído por json_path
# "photo_metadata_json_path" → unificado em json_path
# "report_json_path"         → unificado em json_path
# "total_points"             → vem de quality.total_files no JSON

# Manter:
# "json_path"     → contrato central entre os blocos
# "layer"         → output do JsonToVectorTranslator
# "source"        → "mrk" | "mrk+photo" | "photo_only"
# "tool_key"      → rastreio de logs
# "report_payload"→ output do relatório
# "html_path"     → caminho do HTML gerado
```

---

### Remover após Fase 4 validada e estável

- `PhotoFolderVectorizationService.generate_from_folder()` — substituída por `extract_to_json()` + `JsonToVectorTranslator`
- `changeAttributeValue()` direto em `PhotoMetadataStep` — substituído por `JsonToVectorTranslator`

---

### Validação Final

- [ ] Pipeline MRK completo (extração + vetor + relatório) funciona end-to-end
- [ ] Pipeline foto-only completo funciona end-to-end
- [ ] Runner headless funciona end-to-end
- [ ] `ReportMetadataPlugin` regenera HTML a partir de JSON v2.0
- [ ] `ExecutionContext` sem keys obsoletas
- [ ] Todo layer gerado tem atributos com `field.attribute` (9 chars)
- [ ] Todo JSON gerado tem `schema_version: "2.0"` e chaves PascalCase

---

## Tabela de Classes por Fase

| Fase | Classe | Ação |
|------|--------|------|
| 1 | `Field` | Adiciona campo `key: Optional[MetadataFieldKey]` |
| 1 | `MetadataFields` | Popula `key` em todos os fields dos quatro dicionários |
| 2 | `MrkUtil` | Criar — extrai registros MRK com chaves PascalCase |
| 2 | `JsonUtil` | Criar — monta e salva JSON v2.0 a partir de registros MRK |
| 2 | `MrkParseTask` | Modificar — usa MrkUtil + JsonUtil, não cria layer |
| 3 | `PhotoMetadata` | Modificar — gera JSON v2.0, remove changeAttributeValue |
| 3 | `PhotoFolderVectorizationService` | Adicionar `extract_to_json()`, manter `generate_from_folder()` |
| 4 | `JsonToVectorTranslator` | Criar — único responsável por JSON → QgsVectorLayer |
| 4 | `PhotoVectorizationStep` | Modificar — usa `extract_to_json()` + tradutor |
| 4 | `PhotoMetadataStep` | Modificar — usa tradutor, remove changeAttributeValue |
| 5 | `JSONUtil` | Modificar — suporte a v2.0, erro para schemas antigos |
| 5 | `IMGMetadata` | Modificar — resolve por PascalCase |
| 5 | `ReportGenerationService` | Adaptar para records com chaves PascalCase |
| 6 | `ExecutionContext` | Remover keys obsoletas |
| 6 | `PhotoFolderVectorizationService` | Remover `generate_from_folder()` |

---

## Regras para Implementação

1. Nunca remover um método existente antes de confirmar que nenhum caller depende dele.
2. Chaves nos registros JSON são sempre `MetadataFieldKey.value` — nunca strings inventadas.
3. Nome do atributo no layer sempre via `field.attribute` de `MetadataFields` — nunca hardcode.
4. Label para display sempre via `field.label` de `MetadataFields` — nunca hardcode.
5. Cada fase deve estar validada antes de iniciar a próxima.
6. `CoordSource` e `QualityFlag` obrigatórios em todo record, independente de source.
7. `schema_version: "2.0"` obrigatório em todo JSON gerado.
8. Não usar `print()` para log — usar `LogUtils`.
9. `QgsVectorLayer`, `QgsTask` e `changeAttributeValue` só dentro de `JsonToVectorTranslator`
   e dos steps/tasks do pipeline — nunca dentro de utilitários de extração.
10. Não gerar relatório sem `json_path` válido e com `schema_version: "2.0"` no contexto.