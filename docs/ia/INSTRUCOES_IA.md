# instrucoes_ia.md

## 1. Visão Geral do Plugin

O Cadmus é um plugin avançado para QGIS, focado em automação, processamento de dados geoespaciais, manipulação de layouts, integração de logs e execução de pipelines assíncronos. Resolve problemas de travamento, manipulação massiva de dados e padronização de UI, usando arquitetura modular e contratos claros entre componentes.

## 2. Estrutura de Pastas

```
Cadmus/
│
├── core/                # Engine, contratos, UI, configuração, logging
│   ├── config/          # LogUtils, LogCleanupUtils, locks, estilos
│   ├── engine_tasks/    # Steps, ParallelStep, ExecutionContext
│   ├── task/            # BaseTask, tarefas de processamento
│   ├── ui/              # WidgetFactory, ProgressDialog, InfoDialog
│
├── plugins/             # Plugins principais, dialogs, wrappers
│   ├── logcat/          # UI e modelagem de logs
│   ├── ...              # Plugins de ferramentas
│
├── utils/               # Utilitários: ProjectUtils, Preferences, QgisMessageUtil, etc.
│   ├── vector/          # Manipulação vetorial
│   ├── raster/          # Manipulação raster
│   ├── mrk/             # Manipulação MRK (metadados de drone)
│
├── resources/           # Widgets, estilos, ícones, instruções
│   ├── widgets/         # Widgets exclusivos (AppBar, MainLayout, etc.)
│   ├── styles/          # Temas visuais
│   ├── instructions/    # Arquivos de instruções para plugins
│
├── docs/                # Documentação técnica e arquitetural
│   ├── arquitetura/     # Documentos de arquitetura, contratos, padrões
│   ├── ia/              # instrucoes_ia.md (este arquivo)
│
└── log/                 # Logs de execução
```

## 3. Principais Módulos do Sistema

### Contratos Técnicos e Regras

- **BasePluginMTL**: Classe base obrigatória para todos os plugins. Garante padronização, persistência, logging e integração. Plugins devem herdar e implementar métodos padrão (`_build_ui`, `run`, `ToolKey`).
- **WidgetFactory**: Fábrica central de widgets, layouts e componentes UI. Plugins devem construir UI exclusivamente via WidgetFactory, garantindo padronização, modularidade e compatibilidade.
- **MainLayout**: Layout principal dos dialogs, encapsula scroll, bordas, AppBar.
- **AppBarWidget**: Barra superior com título, botões de ação (Executar, Info, Fechar).
- **BottomActionButtonsWidget**: Botões inferiores padronizados (Executar, Fechar, Info).
- **AttributeSelectorWidget**: Widget exclusivo para seleção de atributos/campos.
- **Styles**: Centraliza temas visuais, define estilos globais, checkbox, radio, label, etc.
- **InfoDialog**: Diálogo padronizado para exibir instruções técnicas, renderiza Markdown nativamente ou converte para HTML.
- **ToolKey**: Enum de identificação de cada ferramenta/plugin.
- **Preferences**: API para salvar/carregar preferências de cada plugin.
- **ProjectUtils**: Responsável por operações com projeto QGIS (carregar, salvar, manipular camadas). Plugins não devem acessar QgsProject/QgsApplication diretamente.
- **AsyncPipelineEngine**: Plugins não criam tasks diretamente; usam steps/pipeline para processamento assíncrono.

### Integração com Resources

- WidgetFactory: construção de UI modular, compatível e padronizada
- Styles: aplicação de temas visuais
- InfoDialog: exibição de instruções técnicas, Markdown/HTML
- resources/widgets: widgets exclusivos para cada função
- resources/icons: ícones padronizados
- resources/instructions: arquivos de instruções para cada plugin

### Integração com Utils

- **DependenciesManager**: Garantia de dependências externas antes de operações (ex.: PDF, imagens)
- **ExplorerUtils**: Entrada de dados, varredura de diretórios, identificação de arquivos
- **FormatUtils**: Conversão e exibição de valores técnicos (bytes, duração, velocidade)
- **LayoutsUtils**: Processamento de layouts, substituição de textos
- **PDFUtils**: Manipulação de PDFs/imagens, logging
- **Preferences**: Persistência de estado/configuração
- **ProjectUtils**: Backup, manipulação de camadas, clipboard
- **QgisMessageUtil**: Exibição de mensagens, feedback ao usuário
- **StringUtils**: Filtros, drivers, nomes padronizados
- **ToolKeys**: Enum de identificação, cores, integração com logging

## 4. Contratos Importantes

### BaseStep (`core/engine_tasks/BaseStep.py`)
- Métodos: `name`, `should_run`, `create_task`, `on_success`, `on_error`
- Regras: nunca modificar camadas QGIS em worker thread; aplicar mudanças em batch na thread principal.
- Armadilhas: acessar objetos C++ fora do escopo, não documentar contratos de resultado.

### BaseTask (`core/task/BaseTask.py`)
- Métodos: `_run`, `on_success`, `on_error`, `finished`, `setProgress`
- Regras: nunca tocar camadas QGIS; retornar dict/list; usar setProgress.
- Armadilhas: não checar `isCanceled`, não capturar exceções corretamente.

### ExecutionContext (`core/engine_tasks/ExecutionContext.py`)
- Métodos: `set`, `get`, `require`, `add_error`, `get_errors`, `cancel`, `is_cancelled`
- Regras: não armazenar objetos C/C++ fora do escopo; guardar referências leves.

### AsyncPipelineEngine (`core/engine_tasks/AsyncPipelineEngine.py`)
- Métodos: `start`, `cancel`, `is_running`
- Regras: tasks nunca tocam camadas; steps aplicam mudanças em batch.
- Armadilhas: não propagar cancelamento, não tratar erros em on_success.

### ParallelStep (`core/engine_tasks/ParallelStep.py`)
- Métodos: `create_task`, `on_success`, `on_error`
- Regras: executar steps independentes em paralelo, propagar erros/cancelamento.

## 5. Fluxo de Execução do Sistema

### Passo a Passo
1. Plugin é iniciado (ex.: via run padrão)
2. UI é construída via WidgetFactory
3. Preferências são carregadas via Preferences
4. Usuário aciona processamento
5. AsyncPipelineEngine é criado, steps são registrados
6. Para cada step:
   - create_task() retorna task (worker thread)
   - task executa processamento, retorna resultado serializável
   - on_success() aplica mudanças em batch na thread principal
   - processEvents() garante UI responsiva
7. Resultados são exibidos via QgisMessageUtil
8. Logs são registrados via LogUtils
9. Preferências e estado de UI são salvos

### Cancelamento e Erros
- Cancelamento deve usar break, nunca return, para garantir cleanup
- Tasks devem checar `isCanceled` periodicamente
- Erros em tasks são capturados e propagados para o contexto
- Steps devem validar shape do resultado antes de aplicar

## 6. Padrões de Arquitetura Utilizados

- **Pipeline Pattern**: Orquestra steps sequenciais/paralelos
- **Step/Task Pattern**: Separação clara entre orquestração (step) e processamento (task)
- **Separation of Concerns**: UI, lógica, processamento, logging, persistência são separados
- **Factory Pattern**: WidgetFactory para construção de UI modular
- **Dependency Inversion**: Plugins dependem de interfaces/contratos, não de implementações diretas
- **Thread Safety**: Tasks nunca tocam camadas QGIS; mudanças aplicadas na thread principal

## 7. Plugins — Estrutura, Fluxo, Armadilhas e Boas Práticas

- Herdar de BasePluginMTL
- Usar WidgetFactory para UI (não acessar widgets/core QGIS diretamente)
- Declarar ToolKey único
- Salvar preferências via Preferences
- Integrar ProjectUtils para manipulação de projeto/camadas
- Ter arquivo de instruções em resources/instructions
- Ter análise de cenário em docs/analisecenario
- Implementar método de abertura padrão (exemplo):
```python
def run_copy_attributes(iface):
    dlg = CopyAttributes(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg
```
- Garantir compatibilidade QGIS 3.16 a 4.0
- Não adicionar tasks diretamente; usar AsyncPipelineEngine
- Documentar instruções e análise de cenário

### Armadilhas Comuns
- Acessar widgets/core do QGIS diretamente
- Não usar WidgetFactory para UI
- Não persistir preferências corretamente
- Adicionar tasks diretamente (deve usar pipeline)
- Falta de compatibilidade com versões antigas do QGIS
- Não documentar instruções ou análise de cenário

## 8. Utils — Análise Detalhada, Contratos, Armadilhas

- **DependenciesManager**: Garantia de dependências externas antes de operações (ex.: PDF, imagens)
- **ExplorerUtils**: Entrada de dados, varredura de diretórios, identificação de arquivos
- **FormatUtils**: Conversão e exibição de valores técnicos (bytes, duração, velocidade)
- **LayoutsUtils**: Processamento de layouts, substituição de textos
- **PDFUtils**: Manipulação de PDFs/imagens, logging
- **Preferences**: Persistência de estado/configuração
- **ProjectUtils**: Backup, manipulação de camadas, clipboard
- **QgisMessageUtil**: Exibição de mensagens, feedback ao usuário
- **StringUtils**: Filtros, drivers, nomes padronizados
- **ToolKeys**: Enum de identificação, cores, integração com logging

## 9. Resources — Widgets, Estilos, InfoDialog, Modularidade

- **WidgetFactory**: Fábrica central de widgets, layouts e componentes UI
- **Styles**: Centraliza temas visuais, define estilos globais, checkbox, radio, label, etc.
- **InfoDialog**: Diálogo padronizado para exibir instruções técnicas, renderiza Markdown nativamente ou converte para HTML
- **resources/widgets**: Widgets exclusivos para cada função
- **resources/icons**: Ícones padronizados
- **resources/instructions**: Arquivos de instruções para cada plugin

## 10. Logging — Formato, Thread Safety, Integração, Exemplos

- **LogUtils**: API central, grava eventos em JSONL, usa lock global para thread safety
- **LogCleanupUtils**: Limpeza e rotação de logs
- **logcat**: UI para leitura e análise de logs
- **Formato**: cada linha é um JSON com ts, level, plugin, session_id, thread, tool, class, msg, data
- **Thread safety**: lock global para escrita concorrente
- **Integração**: erros críticos enviados ao QGIS MessageLog
- **Exemplo**:
```python
from core.config.LogUtils import LogUtils
LogUtils.init(plugin_root)
logger = LogUtils(tool="coord_click", class_name="CoordClickTool")
logger.debug("Creating dialog")
try:
    do_something()
except Exception as exc:
    logger.exception(exc, code="DIALOG_CREATE_FAIL")
```
- **Armadilhas**: não inicializar LogUtils, escrita sem lock, rotacionar logs durante escrita
- **Boas práticas**: usar níveis apropriados, padronizar code, registrar contexto mínimo

## 11. Pipeline — AsyncPipelineEngine, ParallelStep, ExecutionContext

- Separação clara entre cálculo pesado (worker thread) e aplicação de mudanças (thread principal)
- Contratos: ExecutionContext, BaseTask, BaseStep, AsyncPipelineEngine, ParallelStep
- Fluxo sequencial: engine.start() → steps → tasks → on_success → UI
- Fluxo paralelo: ParallelStep cria grupo de tasks, agrega resultados, propaga erros/cancelamento
- Cancelamento: tasks checam isCanceled, steps usam break para cleanup
- Erros: capturados em BaseTask, propagados para contexto, engine aborta pipeline
- Documentar contrato de cada task é obrigatório

## 12. Padronização de Código

- Convenções de nomes: snake_case para funções, CamelCase para classes
- Classes organizadas por responsabilidade: core, plugins, utils, resources
- UI construída via WidgetFactory; layouts compostos por MainLayout, AppBar, BottomActionButtons
- Cada plugin deve implementar método run padrão para abertura de diálogo
- Novos módulos devem seguir contratos existentes (BaseStep, BaseTask, etc.)
- Documentação técnica e instruções devem ser mantidas e atualizadas

## 13. Como uma IA Deve Interagir com o Projeto

- Lógica de negócio: core/engine_tasks, core/task, utils/
- Steps: core/engine_tasks/
- Tasks: core/task/
- Widgets/UI: resources/widgets/, core/ui/WidgetFactory.py
- Configurações: utils/Preferences.py, core/config/
- Para adicionar novas funcionalidades:
  - Criar novo step/task seguindo contratos
  - Construir UI via WidgetFactory
  - Registrar logs via LogUtils
  - Salvar preferências via Preferences
  - Documentar contratos, instruções e análise de cenário
  - Garantir compatibilidade e modularidade

---

Qualquer IA pode entender a arquitetura, contratos, padrões, fluxos, armadilhas, recomendações e integração do Cadmus lendo apenas este arquivo.


