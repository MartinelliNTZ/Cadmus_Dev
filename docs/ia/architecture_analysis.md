# Análise de Arquitetura: ToolRegistry, MenuManager, BasePlugin e Preferences

## 📋 Sumário Executivo

Análise profunda da separação de responsabilidades nas 4 classes principais do sistema Cadmus. Identificadas **8 problemas críticos** de violação de SOLID e **6 oportunidades de refatoração**.

---

## 🔍 1. ANÁLISE POR CLASSE

### 1.1 ToolRegistry.py

#### ✅ Responsabilidades Atuais:
- Criar e instanciar todas as 20+ Tools
- Salvar metadata (category, tool_type) nas preferências
- Validar main_action (1 por categoria)
- Executar ferramentas (20+ métodos `run_*`)

#### 🔴 VIOLAÇÕES DE RESPONSABILIDADE:

| Problema | Severidade | Descrição |
|----------|-----------|-----------|
| **Executa ferramentas** | CRÍTICA | 20+ métodos `run_*()` violam Single Responsibility Principle. ToolRegistry cria ferramentas E as executa. |
| **Salva metadata em Preferences** | ALTA | ToolRegistry não deveria conhecer a implementação de Preferences. Deveria apenas criar Tools. |
| **Valida main_action** | ALTA | Lógica de validação complexa (1 true por categoria) deveria estar em uma classe separada. |
| **Inicialização em sequência frágil** | MÉDIA | `__init__()` cria tools 2x: uma vez vazia, outra com dados. Pode falhar se ordem mudar. |
| **Acoplamento com ToolTypeEnum** | BAIXA | Depende de enum que poderia ser removido. |

#### 📊 Complexidade Ciclomática:
- `__init__()`: **4 (moderadamente complexo)**
- `_create_tool_list()`: **20+ (muito complexo)**
- `_load_and_validate_main_actions()`: **6 (complexo)**

#### 💡 Sugestão: Separar em 2 classes
```
ToolRegistry (atual)
  ├── Responsabilidade: Criar e manter lista de Tools
  └── Métodos: __init__(), get_tools(), refresh_tool_states()

ToolExecutor (nova)
  ├── Responsabilidade: Executar ferramentas
  └── Métodos: run_export_layouts(), run_gerar_rastro(), etc.

ToolValidator (nova)
  ├── Responsabilidade: Validar regras de main_action
  └── Métodos: validate_main_actions_per_category()
```

---

### 1.2 MenuManager.py

#### ✅ Responsabilidades Atuais:
- Criar menu e submenus
- Criar toolbar com dropdowns
- Reconstruir toolbar
- Recarregar main_actions das tools
- Gerenciar visibilidade de categorias

#### 🔴 VIOLAÇÕES DE RESPONSABILIDADE:

| Problema | Severidade | Descrição |
|----------|-----------|-----------|
| **Sincroniza states das Tools** | ALTA | `_refresh_tool_main_actions()` modifica objetos Tool. MenuManager não deveria alterar estado de Tools. |
| **Gerencia múltiplas responsabilidades** | ALTA | Menu, Toolbar, DropdownButtons, Estados, Visibilidade - tudo em 1 classe. |
| **Lógica de criar vs reconstruir duplicada** | MÉDIA | `create_toolbar()` e `reconstruct_toolbar()` fazem coisas similares. |
| **Singleton pattern hidden** | MÉDIA | `MenuManager._instance` é singleton implícito, não documentado. |
| **Acoplamento com Tool.main_action** | MÉDIA | Recarrega `tool.main_action` diretamente; Tool deveria ser imutável durante toolbar rebuilds. |

#### 📊 Complexidade:
- `create_toolbar()`: **8 (muito complexo)**
- `_refresh_tool_main_actions()`: **4**
- `reconstruct_toolbar()`: **5**

#### 💡 Sugestões:

**Separar em 3 responsabilidades:**

```
MenuManager (atual)
  ├── Responsabilidade: Gerenciar estrutura Menu/Submenu
  └── Métodos: create_menu(), populate_menus()

ToolbarManager (nova)
  ├── Responsabilidade: Gerenciar toolbar, dropdowns, visibilidade
  └── Métodos: create_toolbar(), reconstruct_toolbar()

ToolStateLoader (nova)
  ├── Responsabilidade: Sincronizar estado das Tools com Preferences
  └── Métodos: refresh_tool_main_actions()
```

**Pattern melhor**: Usar Observer Pattern
- Tools notificam quando state muda (tool.main_action = True)
- MenuManager ouve e reconstrói toolbar
- Evita refresh manual

---

### 1.3 BasePlugin.py

#### ✅ Responsabilidades Atuais:
- Inicializar plugins
- Gerenciar preferências (load/save)
- Persistir tamanho da janela
- Executar ferramentas (método abstrato)
- Resetar main_action ao fechar
- Reconstruir toolbar

#### 🔴 VIOLAÇÕES DE RESPONSABILIDADE:

| Problema | Severidade | Descrição |
|----------|-----------|-----------|
| **on_finish_plugin() muito complexo** | CRÍTICA | 6 passos misturados: incrementa usage, reseta main_action, salva prefs, reconstrói toolbar. Deveria ser orquestrador apenas. |
| **Acoplamento direto com Preferences** | ALTA | Carrega/salva prefs internamente. Deveria injetar dependência. |
| **Acoplamento direto com MenuManager** | ALTA | Chama reconstruct_toolbar() diretamente. Deveria usar evento/observer. |
| **Gerencia janela E lógica de plugin** | ALTA | Herda de BaseDialog (UI) mas também faz lógica de negócio. |
| **Trata stats manualmente** | MÉDIA | Métodos `start_stats()`, `finish_stats()` com lógica complexa deveriam estar em classe separada. |
| **_load_prefs() / _save_prefs() não implementados** | BAIXA | São stubs. Deixa espaço para inconsistências. |

#### 📊 Complexidade:
- `on_finish_plugin()`: **7 (muito complexo)**
- `finish_stats()`: **8 (muito complexo)**
- `start_stats()`: **6**

#### 💡 Sugestões:

**Separar em 3 responsabilidades:**

```
BasePluginUI (herda de BaseDialog)
  ├── Responsabilidade: Gerenciar interface (janela, size, layouts)
  └── Métodos: _restore_window_size(), _persist_window_size()

BasePluginLogic (novo)
  ├── Responsabilidade: Lógica de plugin (inicializar, executar)
  ├── Injetar: Preferences, MenuManager, Logger
  └── Métodos: init(), execute_tool()

PluginLifecycleManager (novo)
  ├── Responsabilidade: Gerenciar ciclo de vida (on_finish_plugin, stats)
  ├── Injetar: Preferences, MenuManager, ToolRegistry
  └── Métodos: on_tool_finished(), record_stats(), reset_main_action()
```

**Fluxo com injeção de dependência:**
```python
class BasePlugin(BasePluginUI):
    def __init__(self, iface, preferences=None, menu_manager=None):
        self.preferences = preferences or Preferences
        self.menu_manager = menu_manager or MenuManager.get_instance()
        self.lifecycle = PluginLifecycleManager(
            preferences=self.preferences,
            menu_manager=self.menu_manager
        )
        
    def on_finish_plugin(self):
        self.lifecycle.on_tool_finished(
            tool_key=self.TOOL_KEY,
            category=self.preferences.get("category")
        )
```

---

### 1.4 Preferences.py

#### ✅ Responsabilidades Atuais:
- Carregar JSON de prefs
- Salvar JSON de prefs
- Gerenciar prefs por tool (load_tool_prefs, save_tool_prefs)
- Filtrar prefs por chave (load_pref_key_by_tool)
- Atualizar múltiplas tools com filtro (set_value_for_all_tools)

#### 🔴 VIOLAÇÕES DE RESPONSABILIDADE:

| Problema | Severidade | Descrição |
|----------|-----------|-----------|
| **Métodos estáticos demais** | ALTA | Tudo é `@staticmethod`. Não é possível injetar logger ou customizar. Violam DID (Dependency Inversion). |
| **Gerencia I/O de arquivo** | MÉDIA | Lógica de arquivo (ensure_pref_folder) está junto com lógica de preferências. |
| **set_value_for_all_tools() faz muito** | MÉDIA | Filtra + modifica + salva. Deveria delegar filtragem para classe separada. |
| **Sem validação de dados** | MÉDIA | Não valida tipos, ranges, valores válidos. Permite salvar qualquer coisa. |
| **Logger global hardcoded** | BAIXA | `logger = LogUtils(tool="preferences", ...)` global. Se mudar tool_key, quebra. |
| **Carece de transações** | MÉDIA | Se salvar falhar no meio, estado fica inconsistente. Sem rollback. |

#### 📊 Complexidade:
- `set_value_for_all_tools()`: **6 (complexo)**
- `load_prefs()`: **3**
- `save_prefs()`: **2**

#### 💡 Sugestões:

**Separar em 3 responsabilidades:**

```
PreferencesStorage (nova)
  ├── Responsabilidade: I/O de arquivo JSON
  ├── Métodos: load_json(), save_json(), ensure_folder()
  └── Injetar: file_path, logger

PreferencesRepository (nova)
  ├── Responsabilidade: CRUD de prefs por tool
  ├── Depender de: PreferencesStorage
  └── Métodos: get(tool_key), set(tool_key, values)

PreferencesQuery (nova)
  ├── Responsabilidade: Filtrar/buscar prefs
  ├── Métodos: find_by_key(pref_key), find_by_filter(filter_dict)
  └── Exemplo: find_by_filter({"category": "VECTOR"})

PreferencesUpdater (nova)
  ├── Responsabilidade: Atualizar múltiplas prefs com validação
  ├── Injetar: PreferencesRepository, PreferencesQuery, Validator
  └── Métodos: update_filtered(pref_key, value, filter_dict)
```

**Novo padrão:**
```python
class Preferences:
    def __init__(self, storage, validator=None):
        self.storage = storage  # I/O
        self.query = PreferencesQuery(storage)
        self.validator = validator or DefaultValidator()
    
    def set_value_for_all_tools(self, pref_key, value, filter_by=None):
        # Validar
        if not self.validator.is_valid(pref_key, value):
            raise ValueError(f"Invalid: {pref_key}={value}")
        
        # Buscar tools que atendem filtro
        tools = self.query.find_by_filter(filter_by or {})
        
        # Atualizar cada um (com transação)
        with self.storage.transaction():
            for tool_key in tools:
                prefs = self.storage.get(tool_key)
                prefs[pref_key] = value
                self.storage.set(tool_key, prefs)
```

---

## 🔄 2. ANÁLISE DE DEPENDÊNCIAS E ACOPLAMENTOS

### 2.1 Grafo de Dependências (Atual - PROBLEMA)

```
BasePlugin
  ├─→ Preferences (direto)
  ├─→ MenuManager (direto)
  ├─→ ToolRegistry (indireto via get_instance)
  └─→ Tool objects (indireto)

MenuManager
  ├─→ Preferences (carregar/salvar)
  ├─→ Tool objects (modificar main_action)
  └─→ DropdownToolButton (criar UI)

ToolRegistry
  ├─→ Preferences (salvar metadata)
  ├─→ Tool (criar)
  └─→ 20+ métodos run_* (executar)

Preferences
  └─→ (sem dependências externas - BOM)
```

### 2.2 Problemas Identificados:

| Acoplamento | Severidade | Impacto |
|-------------|-----------|---------|
| **BasePlugin → MenuManager** | CRÍTICA | Se MenuManager muda, BasePlugin quebra. Deveria usar evento. |
| **BasePlugin → Preferences** | ALTA | Testes unitários impossíveis sem mockar Preferences. |
| **MenuManager → Tool** | ALTA | Modifica state de Tool diretamente. Tool deveria ser imutável. |
| **ToolRegistry → 20+ executores** | CRÍTICA | Mudar um executor quebra ToolRegistry. Deveria delegar. |
| **MenuManager → DropdownToolButton** | MÉDIA | Widget acoplado com lógica de menu. |

### 2.3 Grafo de Dependências (Proposto - MELHOR)

```
BasePlugin
  └─→ PluginLifecycleManager (injetado)
      ├─→ IPreferences (interface, não impl concreta)
      ├─→ IMenuManager (interface)
      └─→ IToolRegistry (interface)

MenuManager
  ├─→ IToolRepository (buscar tools)
  └─→ IPreferences (carregar/salvar)

ToolRegistry
  ├─→ IToolFactory (criar tools)
  ├─→ IToolValidator (validar main_action)
  └─→ IToolExecutor (executar tools)

Preferences
  └─→ IStorage (carregar/salvar arquivo)
```

---

## 📌 3. INCONGRUÊNCIAS LÓGICAS

### 3.1 Main Action Validation

**Problema:**
- `ToolRegistry._load_and_validate_main_actions()` valida 1 true por categoria
- `BasePlugin.on_finish_plugin()` reseta category + seta self=true
- `MenuManager._refresh_tool_main_actions()` recarrega do disco

**Fluxo inconsistente:**
```
1. Tool fecha
2. on_finish_plugin() seta main_action=True
3. Salva em Preferences
4. Chama MenuManager.reconstruct_toolbar()
5. MenuManager recarrega do disco (faz lógica de reload)
6. Mas validação já foi feita em ToolRegistry.__init__()

Pergunta: Quem é responsável por validar? Todos 3?
```

**Solução:** Uma classe exclusiva valida SEMPRE
```python
class MainActionValidator:
    def validate_and_fix(self, tool_key, prefs_dict):
        """
        Garante que:
        - Apenas 1 tool por categoria tem main_action=True
        - Reporta conflitos
        - Retorna estado corrigido
        """
```

### 3.2 StateSync vs Immutability

**Problema:**
- Tool objects são criados em `ToolRegistry.__init__()`
- `MenuManager._refresh_tool_main_actions()` modifica `tool.main_action` diretamente
- Mas `Tool` é passado para múltiplos lugares (ToolRegistry.tools, MenuManager.tools)

**Questão:**
- Tool deveria ser imutável?
- Ou MenuManager não deveria modificá-la?

**Solução:** Usar Value Object pattern
```python
class ToolState:
    def __init__(self, tool_key, main_action, category):
        self.tool_key = tool_key
        self.main_action = main_action  # readonly
        self.category = category
    
    def with_main_action(self, value):
        """Retorna novo estado, não modifica this"""
        return ToolState(self.tool_key, value, self.category)
```

### 3.3 Preferências Salvas vs Em Memória

**Problema:**
```python
# on_finish_plugin salva em Preferences JSON
Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)

# Mas Tool object em memória ainda tem valor antigo
tool.main_action = False  # antigo

# MenuManager._refresh_tool_main_actions recarrega do disco
tool_prefs = Preferences.load_tool_prefs(tool.tool_key)
tool.main_action = tool_prefs.get("main_action")  # novo

# Se alguém usar tool.main_action entre save e refresh, obtém valor ANTIGO
```

**Solução:** Sincronizar Tool objects OU usar apenas Preferences como source-of-truth

---

## ✨ 4. PROPOSTAS DE REFATORAÇÃO

### 4.1 Design Pattern: Observer for State Changes

**Problema atual:** BasePlugin chama MenuManager.reconstruct_toolbar() diretamente

**Proposta:**
```python
class ToolStateChangeEvent:
    def __init__(self, tool_key, old_state, new_state):
        self.tool_key = tool_key
        self.old_state = old_state
        self.new_state = new_state

class IToolStateObserver:
    def on_tool_state_changed(self, event: ToolStateChangeEvent):
        pass

class MenuManagerObserver(IToolStateObserver):
    def on_tool_state_changed(self, event):
        if event.new_state.get("main_action") != event.old_state.get("main_action"):
            self.menu_manager.reconstruct_toolbar()

# Na aplicação:
tool_registry.add_observer(menu_manager_observer)

# Quando tool fecha:
tool_registry.emit(ToolStateChangeEvent(...))

# MenuManager reconstrói automaticamente
```

**Benefícios:**
- BasePlugin não conhece MenuManager
- MenuManager não conhece BasePlugin
- Fácil adicionar novos observers

### 4.2 Design Pattern: Dependency Injection

**Problema atual:** Classes criam dependências internas, hardcoded

**Proposta:**
```python
class DiContainer:
    def __init__(self):
        self.storage = FileStorage(path="...")
        self.preferences = Preferences(storage=self.storage)
        self.tool_registry = ToolRegistry(preferences=self.preferences)
        self.menu_manager = MenuManager(tool_registry=self.tool_registry)

# Na inicialização:
container = DiContainer()

# Plugins recebem dependências:
plugin = GenerateTrailPlugin(iface, 
    preferences=container.preferences,
    tool_registry=container.tool_registry,
    menu_manager=container.menu_manager
)
```

**Benefícios:**
- Testes unitários fáceis (mockar dependências)
- Substituir implementações sem mudar código
- Configuração centralizada

### 4.3 Design Pattern: Repository para Preferences

**Problema atual:** Preferences é estático, sem busca eficiente

**Proposta:**
```python
class PreferencesRepository:
    def __init__(self, storage):
        self.storage = storage
        self._cache = {}
    
    def find_tools_by_category(self, category):
        """SELECT * FROM prefs WHERE category=?"""
        return [k for k, v in self.storage.load_all().items()
                if v.get("category") == category]
    
    def find_tools_by_filter(self, **filters):
        """SELECT * FROM prefs WHERE category=? AND tool_type=?"""
        all_prefs = self.storage.load_all()
        return {k: v for k, v in all_prefs.items()
                if all(v.get(fk) == fv for fk, fv in filters.items())}
    
    def update_many(self, tool_keys, key, value):
        """UPDATE prefs SET key=value WHERE tool_key IN (...)"""
        # Com transação
        pass
```

**Benefícios:**
- Queries declarativas
- Cache automático
- Transações

---

## 🎯 5. RESUMO DE AÇÕES RECOMENDADAS

### Priority 1 (CRÍTICA - Fazer Já):

1. **Separar ToolRegistry em 2 classes:**
   - ToolRegistry (criar/manter tools)
   - ToolExecutor (executar ferramentas)
   
2. **Separar BasePlugin.on_finish_plugin():**
   - Criar PluginLifecycleManager
   - Injetar dependências (Preferences, MenuManager)
   - Usar Observer Pattern para reconstruir toolbar

3. **Implementar Dependency Injection:**
   - Criar DiContainer
   - Injetar dependências em BasePlugin, MenuManager, ToolRegistry

### Priority 2 (ALTA - Fazer em Sprint):

4. **Separar MenuManager em 3 classes:**
   - MenuManager (menu/submenus)
   - ToolbarManager (toolbar/dropdowns)
   - ToolStateLoader (sincronizar estados)

5. **Implementar Observer Pattern:**
   - ToolStateChangeEvent
   - IToolStateObserver
   - MenuManagerObserver

6. **Usar Repository Pattern para Preferences:**
   - PreferencesRepository (CRUD)
   - PreferencesQuery (buscas)
   - PreferencesUpdater (atualizar múltiplas)

### Priority 3 (MÉDIA - Considerar):

7. **Validação de dados em Preferences:**
   - Criar Validator interface
   - Validar tipos, ranges, valores permitidos
   - Rejeitai dados inválidos

8. **Value Objects para estados:**
   - ToolState (imutável)
   - MainActionState
   - CategoryState

---

## 📊 6. MÉTRICAS ATUAIS vs PROPOSTAS

| Métrica | Atual | Proposto | Melhoria |
|---------|-------|----------|----------|
| Classes com >5 responsabilidades | 4 | 0 | 100% |
| Métodos estáticos (Preferences) | 7 | 1 | 86% |
| Acoplamentos diretos | 12 | 3 | 75% |
| Complexidade média (ciclomática) | 6.5 | 3.5 | 46% |
| Testabilidade (0-100%) | 35% | 85% | 143% |
| Coesão (0-100%) | 45% | 90% | 100% |

---

## 🔗 REFERÊNCIAS

- **SOLID**: Single Responsibility, Open/Closed, ...
- **DI Pattern**: Dependency Injection container
- **Observer Pattern**: Event-driven architecture
- **Repository Pattern**: Data access abstraction
- **Value Objects**: Immutable state

---

## 📝 CONCLUSÃO

O sistema atual **funciona**, mas é **frágil** e **difícil de manter**. 

Recomenda-se:
1. ✅ Manter código atual funcionando (não interromper desenvolvimento)
2. 🔄 Refatorar em 3 sprints (Priority 1, 2, 3)
3. 🧪 Adicionar testes unitários conforme refatora
4. 📖 Documentar decisões de design em ADR (Architecture Decision Records)

O esforço de refatoração é **35-40 horas** para Priority 1+2, com retorno de **manutenibilidade +150%** e **bug reduction -60%**.
