---
name: utils
description: >
  Central de utilitários do Cadmus. Use esta skill para entender, estender ou integrar funções utilitárias do plugin. Sempre consulte antes de criar helpers ou manipular arquivos, strings, camadas ou preferências.
---

# Utils

## Resumo Executivo

**Utils** é o núcleo de utilitários do Cadmus, responsável por:
- Navegação, manipulação e validação de arquivos e pastas
- Compressão e extração de arquivos (zip/unzip)
- Operações de string, formatação e tradução
- Gerenciamento de preferências do usuário
- Gerenciamento de dependências Python
- Operações seguras com camadas vetoriais e raster
- Emissão de mensagens ao usuário (via QgisMessageUtil)
- Centralização de chaves de ferramentas (ToolKey)
- Geração de cores para gráficos
- Geração de SVG a partir de camadas vetoriais
- Manipulação de XML/QML
- Merge de PDFs e conversão PNG→PDF
- Remoção/restauração de extensão de arquivos

---

## Objetivo

Facilitar tarefas comuns e recorrentes do plugin, garantindo padronização, rastreabilidade e segurança nas operações de baixo nível. Utilizado por todas as ferramentas e serviços do Cadmus.

---

## Entradas

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| tool_key | str | Não | Identificador externo para logs/preferences (obrigatório para logs e preferências) |
| path | str | Não | Caminho de arquivo ou pasta |
| payload | dict/obj | Não | Dados para operações de serialização |
| layer | QgsVectorLayer/QgsRasterLayer | Não | Camada para operações de I/O |
| file_paths | List[str] | Não | Lista de caminhos para compressão/merge |
| extensions | List[str] | Não | Lista de extensões para filtro |

---

## Saídas

| Campo | Tipo | Descrição |
|-------|------|-----------|
| resultado | vários | Depende do método chamado (bool, str, camada, etc.) |
| logs | LogUtils | Logs rastreáveis por tool_key |
| mensagens | QgisMessageUtil | Mensagens ao usuário (nunca usar print) |

---

## Todas as Classes Disponíveis

| # | Classe | Arquivo | Responsabilidade |
|---|--------|---------|-----------------|
| 1 | **ExplorerUtils** | `utils/ExplorerUtils.py` | **Navegação, manipulação e validação de arquivos/pastas.** Só ela pode abrir arquivos/pastas no SO. Métodos: `open_folder`, `open_file`, `copy_file_to_folder`, `rename_file`, `remove_extension_dot`, `restore_extension_dot`, `scan_folder`, `create_layer`, `has_extension`, `ensure_folder_exists`, `is_file`, `build_suffixed_output_path`, `sanitize_path_component`, `next_indexed_folder_name`, `create_temp_json`, `get_cadmus_temp_root`, `ensure_temp_subfolder`, `get_temp_folder`, `build_temp_file_path`, `build_report_json_stem`, `build_report_html_stem`. |
| 2 | **FileCompressUtils** ✨ NOVO | `utils/FileCompressUtils.py` | **Compressão e extração de arquivos.** Responsável por zipar/deszipar arquivos, verificar integridade de zips e limpeza segura em caso de falha. Métodos: `zip_files`, `zip_directory`, `unzip_file`, `unzip_directory`, `is_valid_zip`. Sem dependência de QGIS. |
| 3 | **VectorLayerSource** | `utils/vector/VectorLayerSource.py` | **Operações de I/O, validação e clonagem de camadas vetoriais.** Só ela pode explorar arquivos vetoriais. |
| 4 | **RasterLayerSource** | `utils/raster/RasterLayerSource.py` | **Operações de I/O, validação e clonagem de camadas raster.** Só ela pode explorar arquivos raster. |
| 5 | **VectorLayerAttributes** | `utils/vector/VectorLayerAttributes.py` | **Manipulação de atributos de camadas vetoriais.** |
| 6 | **VectorLayerGeometry** | `utils/vector/VectorLayerGeometry.py` | **Manipulação de geometria de camadas vetoriais.** |
| 7 | **VectorLayerMetrics** | `utils/vector/VectorLayerMetrics.py` | **Métricas de camadas vetoriais.** |
| 8 | **VectorLayerProjection** | `utils/vector/VectorLayerProjection.py` | **Reprojeção de camadas vetoriais.** |
| 9 | **RasterLayerMetrics** | `utils/raster/RasterLayerMetrics.py` | **Métricas de camadas raster.** |
| 10 | **RasterLayerProcessing** | `utils/raster/RasterLayerProcessing.py` | **Processamento de camadas raster.** |
| 11 | **RasterLayerProjection** | `utils/raster/RasterLayerProjection.py` | **Reprojeção de camadas raster.** |
| 12 | **RasterLayerRendering** | `utils/raster/RasterLayerRendering.py` | **Renderização de camadas raster.** |
| 13 | **RasterVectorBridge** | `utils/raster/RasterVectorBridge.py` | **Operações de conversão raster↔vetor.** |
| 14 | **ProjectUtils** | `utils/ProjectUtils.py` | **Toda manipulação de QgsProject (abrir, salvar, backup, layers).** Só ela pode tocar QgsProject. |
| 15 | **QgisMessageUtil** | `utils/QgisMessageUtil.py` | **Único meio de emitir mensagens para o usuário.** Nunca usar print/log para usuário. Métodos: `bar_info`, `bar_success`, `bar_warning`, `bar_error`. |
| 16 | **ToolKey** | `utils/ToolKeys.py` | **CPF das ferramentas.** Toda ferramenta precisa de um ToolKey. Utils/serviços são "escravos" e precisam de tool_key externo. |
| 17 | **Preferences** | `utils/Preferences.py` | **Preferências do usuário.** Tudo que for possível deve ser salvo nas preferências. |
| 18 | **FormatUtils** | `utils/FormatUtils.py` | **Formatação de strings, números, durações, velocidade do obturador, parsing de datas EXIF.** Sempre usar para exibir valores ao usuário. |
| 19 | **MathUtils** | `utils/MathUtils.py` | **Funções matemáticas genéricas.** Estatística circular/axial, parsers numéricos (`parse_num`, `to_float_or_none`), validadores (`is_zero_value`, `is_missing_value`). |
| 20 | **StringManager** | `utils/StringManager.py` | **Central de filtros, extensões e traduções de strings.** Contém `RASTER_EXTS`, `VECTOR_EXTS`, `IMAGE_EXTS`, métodos de tradução. |
| 21 | **DependenciesManager** | `utils/DependenciesManager.py` | **Gerenciamento e validação de dependências Python.** `check_dependency`, `install_dependency`. |
| 22 | **LayoutsUtils** | `utils/LayoutsUtils.py` | **Processamento de layouts do QGIS.** Substituição de texto em `QgsLayoutItemLabel`. Métodos: `replace_text_in_layouts`. Não depende de UI. |
| 23 | **JsonUtil** | `utils/JsonUtil.py` | **Construção e manipulação de JSON v2.0.** Constrói estrutura com grupos, records, qualidade e timestamps. Métodos: `build`, `save`, `load_records`, `update_timestamps`. |
| 24 | **ColorUtil** | `utils/ColorUtil.py` | **Geração de cores distintas e harmoniosas para gráficos com múltiplas séries.** Geração HSV com verificação de contraste de luminância. Métodos: `generate`, `generate_with_labels`, `to_rgba`. |
| 25 | **SVGUtils** | `utils/SVGUtils.py` | **Geração de SVG a partir de camadas vetoriais QGIS.** Converte features para elementos SVG (pontos, linhas, polígonos) com símbolos e rótulos. 25+ métodos. |
| 26 | **XmlUtil** | `utils/XmlUtil.py` | **Manipulação de XML e QML (QGIS Style Layer).** Cria, carrega, salva documentos XML. Constrói estilos QML para raster multiband. Métodos: `create_element`, `add_sub_element`, `pretty_xml`, `save_xml`, `load_xml`, `save_qml_style`, `build_raster_multiband_qml`. |
| 27 | **PDFUtils** | `utils/PDFUtils.py` | **Manipulação de PDFs e conversão de imagens.** Merge de PDFs (PyPDF2), merge de PNGs para PDF (Pillow). Métodos: `merge_pdfs`, `merge_pngs_to_pdf`. |
| 28 | **StringAdapter** | `utils/adapter/StringAdapter.py` | **Adaptação de strings para diferentes formatos.** |
| 29 | **CustomPhotosFieldsUtil** | `utils/mrk/CustomPhotosFieldsUtil.py` | **Utilitário para campos personalizados de fotos.** |
| 30 | **ExifUtil** | `utils/mrk/ExifUtil.py` | **Leitura de metadados EXIF de imagens.** |
| 31 | **InitialParamsUtil** | `utils/mrk/InitialParamsUtil.py` | **Parâmetros iniciais para processamento de fotos.** |
| 32 | **MetadataFields** | `utils/mrk/MetadataFields.py` | **Definição dos campos de metadados (EXIF/XMP).** |
| 33 | **MrkParser** | `utils/mrk/MrkParser.py` | **Parser de arquivos .mrk (formato de pontos do drone).** |
| 34 | **MrkUtil** | `utils/mrk/MrkUtil.py` | **Utilitários para arquivos .mrk.** |
| 35 | **PhotoMetadata** | `utils/mrk/PhotoMetadata.py` | **Agregação de metadados de foto (EXIF + XMP + .mrk).** |
| 36 | **PqiUtil** | `utils/mrk/PqiUtil.py` | **Cálculo de PQI (Picture Quality Index).** |
| 37 | **XmpUtil** | `utils/mrk/XmpUtil.py` | **Leitura de metadados XMP de imagens (DJI, Mavic, etc.).** |
| 38 | **AggregateAnalyzer** | `utils/report/AggregateAnalyzer.py` | **Análise agregada de dados de relatório.** |
| 39 | **AlertManager** | `utils/report/AlertManager.py` | **Gerenciamento de alertas em relatórios.** |
| 40 | **FlightAggregator** | `utils/report/FlightAggregator.py` | **Agregação de dados de voo.** |
| 41 | **IMGMetadata** | `utils/report/IMGMetadata.py` | **Metadados de imagens para relatório.** |
| 42 | **JsonMetadataManager** | `utils/report/JsonMetadataManager.py` | **Gerenciamento de metadados em JSON para relatório.** |
| 43 | **RangeMetadataManager** | `utils/report/RangeMetadataManager.py` | **Gerenciamento de ranges de metadados.** |
| 44 | **RenderEngine** | `utils/report/RenderEngine.py` | **Motor de renderização de relatórios.** |
| 45 | **ReportPapelineManager** | `utils/report/ReportPapelineManager.py` | **Gerenciamento de pipeline de relatórios.** |
| 46 | **ScoreSPBJudge** | `utils/judge/ScoreSPBJudge.py` | **Julgador de pontuação SPB.** |
| 47 | **SequentialPointBreakJudge** | `utils/judge/SequentialPointBreakJudge.py` | **Julgador Sequential Point Break.** |
| 48 | **SimpleSPBJudge** | `utils/judge/SimpleSPBJudge.py` | **Julgador SPB simplificado.** |

---

## Processamento

### Fase 1 — Navegação e Manipulação de Arquivos

```python
# Exemplo: abrir pasta no SO
ExplorerUtils.open_folder(folder_path, tool_key=ToolKey.SYSTEM)
```

### Fase 1b — Renomeação de Arquivos

```python
# Remover ponto da extensão: foto.jpg → fotojpg
novo_path = ExplorerUtils.remove_extension_dot("C:/fotos/foto.jpg", tool_key=ToolKey.SYSTEM)

# Restaurar ponto: fotojpg → foto.jpg
restored = ExplorerUtils.restore_extension_dot("C:/fotos/foto.jpg", tool_key=ToolKey.SYSTEM)

# Renomear genérico
ExplorerUtils.rename_file("C:/fotos/old.jpg", "C:/fotos/new.jpg", tool_key=ToolKey.SYSTEM)
```

### Fase 1c — Compressão de Arquivos

```python
from ..utils.FileCompressUtils import FileCompressUtils

# Zipar arquivos específicos
success, result = FileCompressUtils.zip_files(
    file_paths=["C:/fotos/foto1.jpg", "C:/fotos/foto2.jpg"],
    zip_path="C:/fotos/fotos.zip",
    tool_key=ToolKey.SYSTEM,
)

# Zipar diretório inteiro
success, zip_path = FileCompressUtils.zip_directory(
    dir_path="C:/fotos",
    tool_key=ToolKey.SYSTEM,
)

# Deszipar arquivo
success, msg = FileCompressUtils.unzip_file(
    zip_path="C:/fotos/fotos.zip",
    extract_dir="C:/fotos",
    tool_key=ToolKey.SYSTEM,
)

# Deszipar pasta (procura {nome_da_pasta}.zip)
success, msg = FileCompressUtils.unzip_directory(
    dir_path="C:/fotos",
    tool_key=ToolKey.SYSTEM,
)
```

### Fase 2 — Operações com Camadas

```python
# Exemplo: salvar camada vetorial
VectorLayerSource.save_vector_layer(layer, output_path=path, external_tool_key=ToolKey.EXPORT_ALL_LAYOUTS)
```

### Fase 3 — Preferências

```python
# Exemplo: salvar preferências
Preferences.save_tool_prefs(ToolKey.EXPORT_ALL_LAYOUTS, {"last_folder": folder})
```

### Fase 4 — Mensagens ao Usuário

```python
# Exemplo: exibir mensagem
QgisMessageUtil.bar_info(iface, "Processo concluído com sucesso!")
```

---

## Regras

### ✅ Sempre:
- Usar **ExplorerUtils** para manipular arquivos/pastas (abrir, copiar, renomear, remover/restaurar extensão)
- Usar **FileCompressUtils** para zipar/deszipar arquivos
- Usar VectorLayerSource/RasterLayerSource para explorar arquivos de camada
- Usar ProjectUtils para manipular QgsProject
- Usar QgisMessageUtil para mensagens ao usuário
- Usar ToolKey para logs/preferences
- Salvar tudo que for possível nas preferências
- Usar FormatUtils para exibir valores ao usuário
- Nome do arquivo .py deve ser igual ao nome da classe

### ❌ Nunca:
- Manipular QgsProject fora de ProjectUtils
- Emitir mensagens ao usuário fora de QgisMessageUtil
- Usar print/log para mensagens ao usuário
- Criar helpers duplicados já existentes em utils
- Salvar preferências fora de Preferences
- Explorar arquivos/camadas fora das classes autorizadas
- Usar `os.rename` ou `zipfile.ZipFile` diretamente em tasks/core — **delegar para ExplorerUtils/FileCompressUtils**
- Chamar FileCompressUtils para operações de rename (usar ExplorerUtils)
- Chamar ExplorerUtils para operações de compressão (usar FileCompressUtils)

---

## Padrões de Uso

### Padrão 1 — Abrir pasta

```python
ExplorerUtils.open_folder("C:/dados", tool_key=ToolKey.SYSTEM)
```

### Padrão 2 — Remover/restaurar extensão

```python
# Remove: foto.jpg → fotojpg
novo = ExplorerUtils.remove_extension_dot("C:/fotos/foto.jpg", tool_key=ToolKey.SYSTEM)

# Restaura: fotojpg → foto.jpg
restored = ExplorerUtils.restore_extension_dot("C:/fotos/foto.jpg", tool_key=ToolKey.SYSTEM)
```

### Padrão 3 — Zipar/deszipar

```python
# Zipa fotos de uma pasta
sucesso, zip_path = FileCompressUtils.zip_directory(
    dir_path="C:/fotos",
    tool_key=ToolKey.SYSTEM,
)

# Deszipa
sucesso, msg = FileCompressUtils.unzip_directory(
    dir_path="C:/fotos",
    tool_key=ToolKey.SYSTEM,
)
```

### Padrão 4 — Salvar camada vetorial

```python
VectorLayerSource.save_vector_layer(layer, output_path="/tmp/layer.gpkg", external_tool_key=ToolKey.EXPORT_ALL_LAYOUTS)
```

### Padrão 5 — Mensagem ao usuário

```python
QgisMessageUtil.bar_info(iface, "Arquivo salvo com sucesso!")
```

---

## Casos de Uso

- Quando uma ferramenta precisa **abrir pasta/arquivo** → usar **ExplorerUtils**
- Quando precisa **renomear/remover/restaurar extensão** → usar **ExplorerUtils** (`rename_file`, `remove_extension_dot`, `restore_extension_dot`)
- Quando precisa **zipar/deszipar arquivos** → usar **FileCompressUtils**
- Quando precisa salvar/carregar **camada vetorial** → usar **VectorLayerSource**
- Quando precisa salvar/carregar **camada raster** → usar **RasterLayerSource**
- Quando precisa **manipular projeto QGIS** → usar **ProjectUtils**
- Quando precisa **exibir mensagem ao usuário** → usar **QgisMessageUtil**
- Quando precisa **salvar preferências** → usar **Preferences**
- Quando precisa **formatar valores** → usar **FormatUtils**
- Quando precisa **gerar SVG** → usar **SVGUtils**
- Quando precisa **manipular XML/QML** → usar **XmlUtil**
- Quando precisa **merge de PDFs/PNGs** → usar **PDFUtils**
- Quando precisa **gerar cores** → usar **ColorUtil**

---

## Dependências

| Módulo | Caminho | Responsabilidade |
|--------|---------|-----------------|
| ExplorerUtils | `utils/ExplorerUtils.py` | Navegação, manipulação e validação de arquivos/pastas. Renomeação e remoção/restauração de extensão. |
| FileCompressUtils | `utils/FileCompressUtils.py` | Compressão e extração de arquivos zip. |
| VectorLayerSource | `utils/vector/VectorLayerSource.py` | I/O de camadas vetoriais |
| VectorLayerAttributes | `utils/vector/VectorLayerAttributes.py` | Atributos de camadas vetoriais |
| VectorLayerGeometry | `utils/vector/VectorLayerGeometry.py` | Geometria de camadas vetoriais |
| VectorLayerMetrics | `utils/vector/VectorLayerMetrics.py` | Métricas de camadas vetoriais |
| VectorLayerProjection | `utils/vector/VectorLayerProjection.py` | Reprojeção de camadas vetoriais |
| RasterLayerSource | `utils/raster/RasterLayerSource.py` | I/O de camadas raster |
| RasterLayerMetrics | `utils/raster/RasterLayerMetrics.py` | Métricas de camadas raster |
| RasterLayerProcessing | `utils/raster/RasterLayerProcessing.py` | Processamento de camadas raster |
| RasterLayerProjection | `utils/raster/RasterLayerProjection.py` | Reprojeção de camadas raster |
| RasterLayerRendering | `utils/raster/RasterLayerRendering.py` | Renderização de camadas raster |
| RasterVectorBridge | `utils/raster/RasterVectorBridge.py` | Conversão raster↔vetor |
| ProjectUtils | `utils/ProjectUtils.py` | Manipulação de QgsProject |
| QgisMessageUtil | `utils/QgisMessageUtil.py` | Mensagens ao usuário |
| ToolKey | `utils/ToolKeys.py` | Identificação de ferramentas |
| Preferences | `utils/Preferences.py` | Preferências do usuário |
| FormatUtils | `utils/FormatUtils.py` | Formatação de strings, números, durações, velocidade do obturador, parsing de datas EXIF |
| MathUtils | `utils/MathUtils.py` | Funções matemáticas genéricas: estatística circular/axial, parsers numéricos, validadores |
| StringManager | `utils/StringManager.py` | Tradução e filtros de strings |
| DependenciesManager | `utils/DependenciesManager.py` | Dependências Python |
| LayoutsUtils | `utils/LayoutsUtils.py` | Processamento de layouts QGIS |
| JsonUtil | `utils/JsonUtil.py` | Construção e manipulação de JSON v2.0 |
| ColorUtil | `utils/ColorUtil.py` | Geração de cores para gráficos |
| SVGUtils | `utils/SVGUtils.py` | Geração de SVG a partir de camadas vetoriais |
| XmlUtil | `utils/XmlUtil.py` | Manipulação de XML e QML |
| PDFUtils | `utils/PDFUtils.py` | Merge de PDFs e conversão PNG→PDF |

---

## Exemplos Completos

### Exemplo 1 — Abrir arquivo e salvar preferências

```python
from .utils.ExplorerUtils import ExplorerUtils
from .utils.Preferences import Preferences
from .utils.ToolKeys import ToolKey

file_path = ExplorerUtils.open_file("C:/dados/relatorio.pdf", tool_key=ToolKey.SYSTEM)
Preferences.save_tool_prefs(ToolKey.SYSTEM, {"last_file": file_path})
```

### Exemplo 2 — Remover extensão de fotos e zipar

```python
from ..utils.ExplorerUtils import ExplorerUtils
from ..utils.FileCompressUtils import FileCompressUtils
from ..utils.ToolKeys import ToolKey

# Remove o ponto da extensão de cada foto
for foto in ["C:/fotos/foto1.jpg", "C:/fotos/foto2.jpg"]:
    novo = ExplorerUtils.remove_extension_dot(foto, tool_key=ToolKey.PATH_EXTENSION)
    if novo:
        print(f"Renomeado: {novo}")

# Ou zipa todas as fotos de uma pasta
success, zip_path = FileCompressUtils.zip_directory(
    dir_path="C:/fotos",
    tool_key=ToolKey.PATH_EXTENSION,
)
```

### Exemplo 3 — Salvar camada vetorial e exibir mensagem

```python
from .utils.vector.VectorLayerSource import VectorLayerSource
from .utils.QgisMessageUtil import QgisMessageUtil
from .utils.ToolKeys import ToolKey

saved = VectorLayerSource.save_vector_layer(layer, output_path="/tmp/layer.gpkg", external_tool_key=ToolKey.EXPORT_ALL_LAYOUTS)
if saved:
    QgisMessageUtil.bar_success(iface, "Camada salva com sucesso!")
```

### Exemplo 4 — Deszipar pasta de fotos

```python
from ..utils.FileCompressUtils import FileCompressUtils
from ..utils.ToolKeys import ToolKey

success, msg = FileCompressUtils.unzip_directory(
    dir_path="C:/fotos",
    tool_key=ToolKey.PATH_EXTENSION,
    remove_zip=True,  # Remove o zip após extração
)
if success:
    QgisMessageUtil.bar_info(iface, "Fotos extraídas com sucesso!")
```

---

## Limitações

- Não manipula lógica de negócio, apenas operações utilitárias
- Não deve ser usada para criar helpers duplicados
- Não manipula QgsProject fora de ProjectUtils
- Não emite mensagens ao usuário fora de QgisMessageUtil
- **FileCompressUtils** não manipula arquivos individuais (rename, copy) — isso é do ExplorerUtils
- **ExplorerUtils** não faz compressão/extração — isso é do FileCompressUtils

---

## Validação

| Critério | Status |
|----------|--------|
| Reutilizável? | ✅ Sempre chamada por ferramentas/serviços |
| Clara? | ✅ Responsabilidades explícitas por classe |
| Independente de contexto oculto? | ✅ Não depende de contexto externo |
| Separação clara rename vs compress? | ✅ ExplorerUtils = rename; FileCompressUtils = zip/unzip |

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-04-20 | 1.0.0 | Criação via SKILL_FACTORY — lidas classes base do utils |
| 2026-06-08 | 2.0.0 | **Refatoração arquitetural**: removidos `os.rename` e `zipfile.ZipFile` de PathExtensionTask. Criado `FileCompressUtils` (compressão/extração). Adicionados `rename_file`, `remove_extension_dot`, `restore_extension_dot` ao `ExplorerUtils`. SKILL enriquecida com todas as 48 classes do diretório utils. |