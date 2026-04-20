# 🧠 SKILL: LogUtils — Sistema de Logging Estruturado

## 📋 RESUMO EXECUTIVO

**LogUtils** é um sistema de logging estruturado que:
- Centraliza toda saída de eventos em JSON estruturado
- Funciona em **métodos de instância** e **métodos estáticos**
- Integra com QGIS MessageLog (UI) + arquivo de log
- Rastreia **contexto completo** (tool, class, session, thread, etc)

---

## 🎯 OBJETIVO

Fornecer logging consistente, rastreável e sem acoplamento, funcionando em qualquer contexto (normal, estático, assíncrono).

---

## 📥 ENTRADAS

- **tool**: Identificador único do plugin/funcionalidade (ToolKey)
- **class_name**: Nome da classe que está logando
- **msg**: Mensagem legível
- **level**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **code**: Código de evento (opcional, para rastreamento)
- **data**: Dados estruturados adicionais (kwargs)
- **exc**: Exception (para logging de erros)

---

## 📤 SAÍDAS

1. **Arquivo JSON** (`cadmus_<timestamp>_pid<pid>.log`)
   - Uma linha JSON por evento
   - Estrutura completa: ts, level, plugin, session_id, thread, tool, class, msg, data

2. **QGIS MessageLog** (para ERROR e CRITICAL)
   - Visível na UI do QGIS

3. **Stderr** (fallback)
   - Se arquivo não disponível

---

## ⚙️ PROCESSAMENTO

### **FASE 1: Inicialização Global (Execute UMA VEZ)**

```python
from pathlib import Path
from core.config.LogUtils import LogUtils

# Na inicialização do plugin (cadmus_plugin.py)
plugin_root = Path(__file__).parent
LogUtils.init(plugin_root)
```

**Resultado:**
- Session ID único gerado
- Arquivo de log criado
- Sistema pronto para uso

---

### **FASE 2: Logging em Métodos de Instância**

**PADRÃO RECOMENDADO:**

```python
from core.config.LogUtils import LogUtils
from utils.ToolKeys import ToolKey

class MyPlugin:
    TOOL_KEY = ToolKey.MY_PLUGIN
    
    def __init__(self):
        self.logger = LogUtils(
            tool=self.TOOL_KEY,
            class_name=self.__class__.__name__,
            level=LogUtils.INFO
        )
    
    def do_something(self):
        self.logger.info("Iniciando processamento", code="PROCESS_START")
        
        try:
            result = self._process_data()
            self.logger.info(
                "Processamento concluído",
                code="PROCESS_END",
                result_type=type(result).__name__,
                result_size=len(result)
            )
            return result
        except Exception as e:
            self.logger.exception(e, code="PROCESS_ERROR", input_data="...")
            raise
    
    def _process_data(self):
        # Privado — também logado
        self.logger.debug("Processando dados internos")
        return [1, 2, 3]
```

**Métodos disponíveis:**
- `logger.debug(msg, code=None, **data)`
- `logger.info(msg, code=None, **data)`
- `logger.warning(msg, code=None, **data)`
- `logger.error(msg, code=None, **data)`
- `logger.critical(msg, code=None, **data)`
- `logger.exception(exc, code=None, **data)`

---

### **FASE 3: Logging em Métodos Estáticos**

**PADRÃO RECOMENDADO:**

```python
from core.config.LogUtils import LogUtils
from utils.ToolKeys import ToolKey

class UtilityClass:
    """Classe com métodos estáticos puros"""
    
    @staticmethod
    def format_data(data, *, tool_key=None):
        """
        Formata dados. Requer tool_key porque é estático.
        
        Args:
            data: Dados a formatar
            tool_key: Identificador do plugin (OBRIGATÓRIO)
        """
        logger = LogUtils(
            tool=tool_key or ToolKey.SYSTEM,
            class_name="UtilityClass",
            level=LogUtils.DEBUG
        )
        
        logger.debug("Iniciando formatação")
        
        try:
            formatted = ", ".join(str(x) for x in data)
            logger.info("Formatação bem-sucedida", output_length=len(formatted))
            return formatted
        except Exception as e:
            logger.exception(e, code="FORMAT_ERROR")
            raise

# Uso:
UtilityClass.format_data([1, 2, 3], tool_key=ToolKey.MY_PLUGIN)
```

**ALTERNATIVA: Passando logger como parâmetro:**

```python
class UtilityClass:
    @staticmethod
    def process(data, logger):
        """
        Usa logger pré-existente.
        
        Args:
            data: Dados
            logger: Instância de LogUtils
        """
        logger.debug("Processando")
        return [x * 2 for x in data]

# Uso:
logger = LogUtils(tool=ToolKey.MY_PLUGIN, class_name="MyClass")
result = UtilityClass.process([1, 2, 3], logger)
```

---

### **FASE 4: Tratamento de Exceções**

**REGRA:** Sempre capturar `Exception` (nunca bare `except:`), logar e relancar ou tratar.

```python
def risky_operation(self):
    try:
        result = self._do_something_risky()
        self.logger.info("Operação bem-sucedida", result=result)
        return result
    except ValueError as e:
        # Erro esperado — convertido
        self.logger.warning(f"Valor inválido: {e}", code="INVALID_VALUE")
        return None
    except Exception as e:
        # Erro não esperado — logar traceback completo
        self.logger.exception(e, code="UNEXPECTED_ERROR")
        raise
```

**LogUtils.exception() automáticamente inclui:**
- Tipo da exceção
- Mensagem
- Traceback completo

---

### **FASE 5: Níveis de Log**

```python
# DEBUG — informação detalhada para diagnóstico
logger.debug("Variável x = 10", x=10)

# INFO — evento normal bem-sucedido
logger.info("Arquivo carregado", file="data.csv", rows=1000)

# WARNING — comportamento inesperado mas não crítico
logger.warning("Retry necessário", attempt=2, max_attempts=3)

# ERROR — erro que impede operação
logger.error("Falha ao conectar", code="CONNECTION_FAILED", host="server.com")

# CRITICAL — falha do sistema
logger.critical("Plugin não inicializou", code="INIT_FAILED")
```

---

## 📏 REGRAS

### ✅ **SEMPRE:**

- Inicializar LogUtils UMA VEZ na startup: `LogUtils.init(plugin_root)`
- Usar `tool_key` correto (enum de ToolKeys)
- Incluir `class_name` (para rastreamento)
- Usar `code` para eventos importantes (facilita busca posterior)
- Passar dados estruturados como kwargs: `logger.info("msg", key1=val1, key2=val2)`
- Logar exceções com `logger.exception(e, code=...)`

### ❌ **NUNCA:**

- Não criar múltiplas instâncias LogUtils com init à cada operação
- Não usar bare `except:` — sempre capturar Exception
- Não silenciar exceções com `pass`
- Não misturar print() com logger — usar logger em produção
- Não passar dados não-serializáveis (objetos complexos direto; converter para string/dict primeiro)

---

## 📦 DEPENDÊNCIAS

```python
from core.config.LogUtils import LogUtils
from utils.ToolKeys import ToolKey
```

**ToolKeys disponíveis:** (verificar [ToolKeys.py](../../utils/ToolKeys.py))

```python
class ToolKey:
    SYSTEM = "system"
    PROCESSING = "processing"
    VECTOR_FIELD = "vector_field"
    # ... etc
```

---

## 🔧 EXEMPLOS

### **Exemplo 1: Plugin Simples**

```python
# plugins/MyPlugin.py
from core.config.LogUtils import LogUtils
from utils.ToolKeys import ToolKey

class MyPlugin:
    TOOL_KEY = ToolKey.PROCESSING
    
    def __init__(self):
        self.logger = LogUtils(tool=self.TOOL_KEY, class_name=self.__class__.__name__)
    
    def execute(self):
        self.logger.info("Iniciando execução", task="main")
        # ... fazer algo
        self.logger.info("Execução concluída")
```

### **Exemplo 2: Classe de Utilidade com Státicos**

```python
# utils/DataProcessor.py
from core.config.LogUtils import LogUtils
from utils.ToolKeys import ToolKey

class DataProcessor:
    @staticmethod
    def validate(data, *, tool_key):
        logger = LogUtils(tool=tool_key, class_name="DataProcessor")
        
        if not isinstance(data, list):
            logger.warning("Tipo inesperado", expected="list", got=type(data).__name__)
            return False
        
        logger.info("Validação bem-sucedida", count=len(data))
        return True
```

### **Exemplo 3: Tratamento de Erro em Pipeline**

```python
def process_pipeline(self, items):
    self.logger.info("Pipeline iniciado", item_count=len(items))
    
    results = []
    for i, item in enumerate(items):
        try:
            result = self._process_item(item)
            results.append(result)
            self.logger.debug(f"Item {i} processado", index=i, success=True)
        except Exception as e:
            self.logger.exception(e, code="ITEM_PROCESS_ERROR", index=i, item_id=item.get("id"))
            results.append(None)  # ou relancar se crítico
    
    self.logger.info("Pipeline finalizado", total=len(items), successful=sum(1 for r in results if r))
    return results
```

---

## ⚠️ LIMITAÇÕES

- **JSON estruturado:** dados complexos precisam ser serializáveis (use `.to_dict()`, converter objetos)
- **Sem async context:** logger é thread-safe mas context pode se misturar em async — use thread_name para rastrear
- **Arquivo único por PID:** se multiple processes abrem simultânea, haverá múltiplos arquivos (esperado)
- **Sem rotação automática:** arquivos de log crescem indefinidamente (implementar LogCleanupUtils)

---

## 🔍 VALIDAÇÃO

| Critério | Status |
|----------|--------|
| **Reutilizável?** | ✅ SIM — usado em toda a codebase |
| **Clara?** | ✅ SIM — API simples e documentada |
| **Independente?** | ✅ SIM — funciona com/sem QGIS, com/sem arquivo |

---

## 🎓 CONCLUSÃO

**LogUtils é a forma correta e única de fazer log no Cadmus.**

- **Instância normal:** `self.logger = LogUtils(...)`
- **Estático:** criar nova instância com `tool_key` ou passar logger
- **Sempre inicializar:** `LogUtils.init(plugin_root)` na startup
- **Exceções:** usar `logger.exception(e, code=...)`

Qualquer log fora deste padrão será desconsiderado na análise de eventos.
