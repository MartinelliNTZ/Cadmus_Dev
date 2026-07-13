# Plugin: LoadFolderLayers

## 📌 Visão Geral

O **LoadFolderLayers** é uma ferramenta do Cadmus para QGIS que permite carregar **múltiplas camadas** a partir de arquivos armazenados em uma **pasta raiz** e suas subpastas. O plugin oferece filtros por tipo de arquivo, preservação da estrutura de diretórios como grupos no painel de camadas, execução síncrona/assíncrona conforme o volume de arquivos, e criação de backup do projeto antes da operação.

---

## 🧩 Arquitetura.

- **Classe principal:** `LoadFolderLayersDialog`
- **Base:** `BasePluginMTL` (fornece `init()`, `preferences`, `logger`, `layout`, `start_stats()`/`finish_stats()`, `show_info_dialog()`, etc.)
- **Função pública:** `run(iface)` — cria e exibe o diálogo não-modal

### Dependências principais

| Módulo | Função |
|---|---|
| `ExplorerUtils` | Escaneamento recursivo da pasta e criação de layers |
| `ProjectUtils` | Normalização de fonte, backup do projeto, adição de layers/grupos |
| `WidgetFactory` | Criação de componentes de UI (checkboxes, seletor de pasta, botões) |
| `Preferences` | Persistência do estado da UI entre sessões |
| `QgisMessageUtil` | Exibição de mensagens (barra, modal, info, erro) |
| `AsyncPipelineEngine` + `LoadFilesStep` | Pipeline assíncrona para carregamento em background |
| `ExecutionContext` | Contexto compartilhado entre steps da pipeline |
| `STR` | Strings internacionalizadas via `TranslationManager` |

---

## ⚙️ Funcionalidades

### 1. Seleção de pasta raiz
- Seletor de pasta integrado via `WidgetFactory.create_path_selector(mode="folder")`

### 2. Filtro por tipos de arquivo
Seção colapsável com checkboxes organizados em grid (2 por linha), com botões "marcar todos" / "desmarcar todos". Tipos suportados:

| Tipo | Extensões |
|---|---|
| GeoPackage | `.gpkg` |
| Shapefile | `.shp` |
| GeoJSON | `.geojson`, `.json` |
| KML | `.kml` |
| KMZ | `.kmz` |
| TIFF/GeoTIFF | `.tif`, `.tiff` |
| ECW | `.ecw` |
| JPEG2000 | `.jp2` |
| ASCII GRID | `.asc` |
| GPX | `.gpx` |
| CSV | `.csv` |
| MapInfo TAB | `.tab` |
| LAS/LAZ | `.las`, `.laz` |

### 3. Opções de carregamento

| Opção | Comportamento |
|---|---|
| **Carregar apenas arquivos não carregados** | Omite camadas já presentes no projeto (comparação por fonte normalizada) |
| **Preservar estrutura de pastas** | Cria grupos no painel de camadas espelhando a hierarquia de diretórios |
| **Não agrupar última pasta** | Quando "preservar estrutura" está ativo, remove o nível mais profundo da hierarquia (check dependente: só pode ser marcado se "preservar" estiver ativo) |
| **Criar backup do projeto** | Gera uma cópia de segurança do `.qgs`/`.qgz` antes de modificar (desabilitado se o projeto não foi salvo) |

### 4. Execução adaptativa (síncrona vs assíncrona)

- **Limiar (`ASYNC_THRESHOLD`):** 19 arquivos
- **≤ 19 arquivos:** execução síncrona direta (`_run_sync_pipeline`)
- **> 19 arquivos:** delega para `AsyncPipelineEngine` + `LoadFilesStep` em background (`_run_async_pipeline`)

---

## 🧠 Fluxo de Execução

```
execute_tool()
  │
  ├─ Valida pasta
  ├─ Backup opcional
  ├─ Coleta extensões selecionadas
  ├─ scan_folder() via ExplorerUtils → records[]
  │
  ├─ count > ASYNC_THRESHOLD?
  │   ├─ SIM → _run_async_pipeline()
  │   │         ├─ Cria ExecutionContext
  │   │         ├─ AsyncPipelineEngine([LoadFilesStep()]).start()
  │   │         ├─ on_finished → _on_async_finished()
  │   │         └─ on_error → _on_async_error()
  │   │
  │   └─ NÃO → _run_sync_pipeline()
  │               ├─ Filtra missing_only (se ativo)
  │               ├─ Para cada record:
  │               │   ├─ ExplorerUtils.create_layer()
  │               │   ├─ Preserva estrutura (grupos) ou adiciona à raiz
  │               │   └─ last_folder: remove último nível da hierarquia
  │               └─ Exibe resultado com modal_info
```

### Síncrono (`_run_sync_pipeline`)
- Itera registro a registro no **thread principal**
- Cria camada via `ExplorerUtils.create_layer()`
- Adiciona ao grupo apropriado (ou raiz) via `ProjectUtils`
- Exibe modal informativo ao final com a contagem de arquivos carregados

### Assíncrono (`_run_async_pipeline`)
- Constrói `ExecutionContext` com todas as opções serializadas
- Instancia `AsyncPipelineEngine` com um único step: `LoadFilesStep`
- Exibe mensagem na barra de notificação informando que o carregamento iniciou
- Callbacks:
  - `_on_async_finished`: exibe contagem na barra de informações
  - `_on_async_error`: exibe modal de erro

---

## 💾 Persistência de Preferências

O estado da UI é salvo automaticamente via `Preferences.save_tool_prefs()` e restaurado em `_load_prefs()`.

**Dados persistidos:**
- `folder` — última pasta selecionada
- `types` — lista de tipos de arquivo marcados
- `missing_only`, `preserve`, `lastfolder`, `backup` — estados dos checkboxes
- `window_width`, `window_height` — dimensões da janela
- `types_expanded` — estado da seção colapsável de tipos

**Regra especial:** O checkbox de backup é forçado a `False` e desabilitado se o projeto atual não tiver um arquivo salvo (`QgsProject.instance().fileName()` vazio).

---

## 🧾 Internacionalização

Todas as strings visíveis ao usuário são obtidas via `STR.<CHAVE>` do `TranslationManager`, permitindo tradução para os idiomas suportados (pt_BR, en, es, de).

---

## 📐 UI — Estrutura do Layout

```
┌──────────────────────────────────────────┐
│  [Seletor de pasta raiz]                 │
├──────────────────────────────────────────┤
│  ▶ Tipos de arquivo (colapsável)        │
│    □ GeoPackage   □ Shapefile           │
│    □ GeoJSON      □ KML                 │
│    ...                                  │
├──────────────────────────────────────────┤
│  ☐ Carregar apenas arquivos não carreg. │
│  ☐ Preservar estrutura de pastas       │
│  ☐ Não agrupar última pasta             │
│  ☐ Criar backup do projeto              │
├──────────────────────────────────────────┤
│  [Carregar]  [Fechar]  [Informações]    │
└──────────────────────────────────────────┘
```

- Seção de tipos de arquivo é colapsável (inicia recolhida)
- Grid de checkboxes de tipos: 2 colunas, com botões "marcar todos" / "desmarcar todos"
- Opções em coluna única
- `chk_last_folder` é dependente de `chk_preserve_structure` (desabilitado se preserve estiver desligado)

---

## 🚨 Tratamento de Erros

- Pasta inválida → `bar_warning`
- Nenhum tipo selecionado → `bar_warning`
- Falha no backup → logado como erro, execução continua sem backup
- Falha na pipeline assíncrona → `bar_critical` e log de erro
- Falha ao carregar/salvar preferências → logado como erro, UI continua funcional com defaults
- Camada inválida (`layer.isValid()` falso) → ignorada silenciosamente

---

## 🔍 Observações Técnicas

1. **Comparação de camadas já carregadas:** Usa `ProjectUtils.normalize_layer_source()` para normalizar caminhos antes de comparar, evitando duplicatas por diferenças de formatação de path.
2. **LastFolder logic:** Quando ativo, remove o último segmento do caminho relativo. Exemplo: `pasta/sub1/sub2/arquivo.shp` → grupo criado é `pasta/sub1` (sub2 não é criado).
3. **Contagem de arquivos:** `start_stats(folder)` e `finish_stats()` são chamados para métricas de desempenho (herdados de `BasePluginMTL`).
4. **Janela não-modal:** `setModal(False)` permite interagir com o QGIS enquanto o diálogo está aberto.