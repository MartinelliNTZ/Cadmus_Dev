# Análise de Cenário – Load Folder Layers

**Visão Geral**

Ferramenta para carregar em lote arquivos vetoriais/raster de uma pasta, possivelmente preservando a estrutura de pastas como grupos no projeto QGIS, com opções para evitar duplicatas, criar backup e executar carregamento assíncrono quando necessário.

**Objetivo**

Automatizar o carregamento de grandes volumes de arquivos geoespaciais, minimizando duplicação, mantendo organização de grupos e fornecendo feedback ao usuário.

**Fluxo resumido**

1. UI: usuário seleciona pasta raiz, tipos de arquivo e opções (preservar estrutura, carregar apenas ausentes, backup).
2. Descoberta: lista recursiva de arquivos filtrando por extensões selecionadas.
3. Filtragem: se `missing_only` ativado, filtra arquivos já presentes no projeto.
4. Execução: decide modo síncrono/assíncrono (threshold) e dispara pipeline de carregamento.
5. Grupos: cria grupos aninhados conforme estrutura da pasta (opcionalmente ignorando a última pasta).
6. Registro: logs e resumo final com contagem de arquivos/carregamentos.

**Componentes principais**

- `LoadFolderLayersDialog` (_plugins_): UI padronizada com `BasePluginMTL` + `WidgetFactory`.
- `WidgetFactory`: `create_collapsible_parameters`, `create_checkbox_grid`, `create_path_selector`, `create_bottom_action_buttons`.
- `ExplorerUtils` / `ProjectUtils`: funções utilitárias para carregar camadas e garantir grupos.
- `AsyncPipelineEngine` / `LoadFilesStep`: pipeline assíncrono para evitar travar a UI.

**Cenários de Uso**

- Carregar pasta com 100s de shapefiles preservando a hierarquia de pastas como grupos.
- Carregar apenas arquivos não presentes no projeto para evitar duplicação.
- Carregar grandes conjuntos em modo assíncrono para manter responsividade.

**Riscos e controles**

- Bloqueio de UI se operação síncrona em muitos arquivos → usar threshold e AsyncPipelineEngine.
- Erro ao criar grupos ou adicionar camada: log e continuar.
- Permissões de leitura: avisar usuário e pular arquivos problemáticos.

**Observações de implementação**

- `FILE_TYPES` deve ser centralizado e sincronizado com `ExplorerUtils.VECTOR_EXTS`.
- `ensure_group()` deve usar path split por `os.sep` para criar grupos aninhados corretamente.
- `missing_only` precisa filtrar antes de adicionar ao projeto para evitar recarregamento.
- Persistir estado dos collapsibles e preferências via `load_tool_prefs` / `save_tool_prefs`.

**Evoluções recomendadas**

- Pré-visualização de arquivos detectados antes do carregamento.
- Checkpoints de progresso (por lotes) e estimativa de tempo restante.
- Integração com um índice interno para detectar alterações incrementais na pasta.
