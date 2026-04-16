# 🔍 SKILL: Sistema de Logging Cadmus (LogUtils)

**Especialista:** JSON-based Logging | Logging Estruturado | Rastreamento de Sessão | Log Sincronização  
**Versão:** 1.0 | Abril 2026  
**Status:** Completo e Testado

---

## ⚡ TL;DR (60 segundos)

**LogUtils = Logging JSON estruturado com contexto automático**

```python
# 1️⃣ Inicializar (1x ao boot)
from pathlib import Path
from core.config.LogUtils import LogUtils

plugin_root = Path(__file__).parent.parent
LogUtils.init(plugin_root)  # Cria ~/.../Cadmus/log/cadmus_[timestamp]_pid[PID].log

# 2️⃣ Usar em cada classe
from core.config.LogUtils import LogUtils
from utils.ToolKeys import ToolKey

logger = LogUtils(tool=ToolKey.MINHA_FERRAMENTA, class_name="MeuPlugin")

# 3️⃣ Logar
logger.info("Operação iniciada", user_id=123, operation="process")
logger.error("Erro ao processar", file_path="/path/to/file")
logger.exception(exc)  # com traceback
```

**Saída em JSON (linha por evento):**
```json
{"ts":"2026-04-12T10:30:45","level":"INFO","tool":"minha_ferramenta","class":"MeuPlugin","msg":"Operação iniciada","data":{"user_id":123,"operation":"process"}}
```

---

## 🏗️ Arquitetura

### Componentes Principais

```
LogUtils (classe estatc)
├─ init(plugin_root)        ← Inicialização global
├─ LogUtils(tool, class)    ← Instância para cada classe
├─ log(), info(), error()   ← API pública
└─ _write_event()           ← Gravação em JSON

Log File
└─ ~/.../Cadmus/log/cadmus_YYYYMMDD_HHMMSS_pidXXXX.log
   └─ Uma linha JSON por evento

Estrutura JSON (automática)
├─ ts             ← Timestamp ISO
├─ level          ← DEBUG|INFO|WARNING|ERROR|CRITICAL
├─ plugin         ← "Cadmus"
├─ plugin_version ← Lido de metadata.txt
├─ session_id     ← UUID único por sessão QGIS
├─ pid            ← ID do processo
├─ thread         ← Nome da thread
├─ tool           ← ToolKey (minha_ferramenta)
├─ class          ← Nome da classe
├─ code           ← Código customizado (opcional)
├─ msg            ← Mensagem
└─ data           ← Dados customizados (kwargs)
```

### Fluxo

```
1. PluginBootstrap.startUp()
   └─ LogUtils.init(plugin_root)
      ├─ Cria session_id (UUID)
      ├─ Lê version de metadata.txt
      ├─ Cria arquivo log único (timestamp + pid)
      └─ Escreve "Log session started"

2. Plugin.__init__()
   └─ self.logger = LogUtils(tool=ToolKey.XXX, class_name="NomeClasse")
      └─ Logger ligado a sistema global

3. Plugin.execute()
   └─ self.logger.info("msg", key=value)
      └─ _write_event() → JSON → arquivo log
```

---

## 📊 Níveis de Log (5)

```python
LogUtils.DEBUG       # Informação de debug (detalhado)
LogUtils.INFO        # Informação geral (operação OK)
LogUtils.WARNING     # Aviso (algo inusitado mas OK)
LogUtils.ERROR       # Erro não-fatal (operação falhou mas continua)
LogUtils.CRITICAL    # Erro crítico (sistema instável)

# Ordem de severidade (índice)
LEVEL_ORDER = [DEBUG, INFO, WARNING, ERROR, CRITICAL]
# DEBUG (0) < INFO (1) < WARNING (2) < ERROR (3) < CRITICAL (4)
```

### Cores Automáticas

```python
LEVEL_COLORS = {
    "DEBUG": "#9CA3AF",      # Cinza
    "INFO": "#10B981",       # Verde
    "WARNING": "#F59E0B",    # Âmbar
    "ERROR": "#DC2626",      # Vermelho forte
    "CRITICAL": "#991B1B",   # Vermelho escuro
}
```

---

## 🔌 Inicialização Global

### Quando Fazer

**1x ao boot do plugin**, em `PluginBootstrap.startUp()`:

```python
# cadmus_plugin.py
from pathlib import Path
from core.config.LogUtils import LogUtils

class CadmusPlugin:
    def initGui(self):
        # ... código do plugin ...
        
        # ✅ Inicializar logging (IMPORTANTE!)
        plugin_root = Path(__file__).parent
        init_result = LogUtils.init(plugin_root)
        print(init_result)
        # Output: "LogUtils initialized. Log file: /path/to/cadmus_YYYYMMDD_HHMMSS_pidXXXX.log, Session ID: uuid-xxx. pid: 12345"
```

### Localização de Log

```
Windows:
C:\Users\{user}\AppData\Roaming\QGIS\QGIS3\Cadmus\log\
  └─ cadmus_20260412_103045_pid12345.log

Linux/Mac:
~/.local/share/QGIS/QGIS3/Cadmus/log/
  └─ cadmus_20260412_103045_pid12345.log
```

### Plugin Root Detection

```python
# Automático se não informado:
plugin_root = Path(__file__).resolve().parents[3]  # <plugin>/core/config/LogUtils.py

# Ou explícito:
plugin_root = Path("/path/to/Cadmus")
LogUtils.init(plugin_root)
```

### Fallbacks

Se pasta `<plugin>/log/` não for acessível:
1. Tenta `~/{user}/Cadmus/log/` (fallback no home)
2. Se ambas falhamm → `_log_file = None` (log gracioso falha)
3. Registra em `QgsMessageLog` (stderr no console) ao invés de arquivo

**Log nunca quebrará o plugin!**

---

## 💬 API de Instância

### Criar Logger

```python
from core.config.LogUtils import LogUtils
from utils.ToolKeys import ToolKey

class MeuPlugin:
    def __init__(self):
        self.logger = LogUtils(
            tool=ToolKey.MINHA_FERRAMENTA,      # ID da ferramenta
            class_name="MeuPlugin",              # Nome da classe
            level=LogUtils.DEBUG                 # Nível mínimo (opcional, default=INFO)
        )
```

### Métodos de Log

```python
# Informações gerais
logger.debug(msg, **data)      # Detalhes (só se level=DEBUG)
logger.info(msg, **data)       # Operação OK
logger.warning(msg, **data)    # Aviso (algo inusitado)
logger.error(msg, **data)      # Erro não-fatal
logger.critical(msg, **data)   # Erro crítico

# Exceções (com traceback)
logger.exception(exc, **data)  # Loga erro + traceback

# Genérico
logger.log(msg, level=INFO, code="CODE", **data)
```

### Exemplos de Uso

```python
# 1️⃣ Simples
logger.info("Iniciando processamento")

# 2️⃣ Com dados
logger.info("Camada processada", layer_name="buildings", feature_count=1234)

# 3️⃣ Com código customizado
logger.info("Validação OK", code="VAL_SUCCESS", layer_id=42)

# 4️⃣ Estruturado
logger.error(
    f"Falha ao processar arquivo",
    code="FILE_ERROR",
    file_path="/path/to/file.shp",
    error_type="IOError",
    file_size=1024
)

# 5️⃣ Exceção com traceback
try:
    result = risky_operation()
except Exception as e:
    logger.exception(e, code="RISKY_OP_FAILED")
    # Saída inclui: type, message, traceback completo
```

### Controle de Nível

```python
# Ao criar
logger = LogUtils(
    tool=ToolKey.XXX,
    class_name="MeuPlugin",
    level=LogUtils.WARNING  # Só WARNING, ERROR, CRITICAL aparecem
)

# Ou depois (runtime)
logger.set_level(LogUtils.DEBUG)  # Mudar para DEBUG
```

---

## 📋 Estrutura JSON Completa

### Campos Automáticos

```json
{
  "ts": "2026-04-12T10:30:45",       // Timestamp ISO (automático)
  "level": "ERROR",                  // DEBUG|INFO|WARNING|ERROR|CRITICAL
  "plugin": "Cadmus",                // Sempre "Cadmus"
  "plugin_version": "2.0.7",         // Lido de metadata.txt
  "session_id": "550e8400-e29b-41d4-a716-446655440000",  // UUID único por sessão
  "pid": 12345,                      // ID do processo
  "thread": "MainThread",            // Nome da thread
  "tool": "minha_ferramenta",        // ToolKey
  "class": "MeuPlugin",              // Nome da classe
  "code": "FILE_ERROR",              // Código customizado (opcional)
  "msg": "Falha ao processar",       // Mensagem
  "data": {                          // Dados customizados (kwargs)
    "file_path": "/path/to/file",
    "attempt": 3,
    "exception": {                   // Se logger.exception()
      "type": "IOError",
      "message": "File not found",
      "traceback": "Traceback (most recent call last):\n  ..."
    }
  }
}
```

### Exemplo Real 1: Info Normal

```json
{"ts":"2026-04-12T10:30:45","level":"INFO","plugin":"Cadmus","plugin_version":"2.0.7","session_id":"550e8400-e29b-41d4-a716-446655440000","pid":12345,"thread":"MainThread","tool":"vector_fields","class":"VectorFieldsCalculationPlugin","code":null,"msg":"Iniciando cálculo de campos","data":{"layer_name":"buildings","feature_count":1234,"geom_type":"Polygon"}}
```

### Exemplo Real 2: Erro com Exceção

```json
{"ts":"2026-04-12T10:31:20","level":"ERROR","plugin":"Cadmus","plugin_version":"2.0.7","session_id":"550e8400-e29b-41d4-a716-446655440000","pid":12345,"thread":"MainThread","tool":"vector_fields","class":"VectorFieldsCalculationPlugin","code":"CALC_FAILED","msg":"Unhandled exception","data":{"exception":{"type":"ZeroDivisionError","message":"division by zero","traceback":"Traceback (most recent call last):\n  File \"plugin.py\", line 42, in _process\n    result = 100 / area\nZeroDivisionError: division by zero"}}}
```

---

## 🎯 Padrões de Logging

### 1️⃣ Validação (Estruturado)

```python
def execute(self):
    self.logger.debug("Iniciando execute()")
    
    # Validar entrada
    layer = get_active_layer()
    if not layer:
        self.logger.warning("Nenhuma camada ativa", code="NO_ACTIVE_LAYER")
        return
    
    self.logger.debug("Camada encontrada", layer_name=layer.name())
    
    # Validar edição
    if not layer.isEditable():
        self.logger.warning(
            "Camada não está em modo edição",
            code="NOT_EDITABLE",
            layer_name=layer.name()
        )
        return
```

### 2️⃣ Operação Principal (Com Sucesso/Falha)

```python
def execute(self):
    self.logger.info("Iniciando processamento", operation="vector_fields")
    
    try:
        start_time = time.time()
        
        # Operação
        features_modified = self._process_layer(layer)
        
        elapsed = time.time() - start_time
        self.logger.info(
            "Processamento concluído",
            code="PROCESS_SUCCESS",
            features_modified=features_modified,
            elapsed_ms=int(elapsed * 1000)
        )
    except ValueError as e:
        # Erro esperado (validação)
        self.logger.warning(f"Erro de validação: {e}", code="VALIDATION_FAILED")
    except Exception as e:
        # Erro inesperado
        self.logger.error(f"Erro inesperado: {e}", code="UNKNOWN_ERROR")
        self.logger.exception(e)  # Com traceback
```

### 3️⃣ Operações em Loop (Contagem)

```python
def _process_features(self, layer):
    count_total = layer.featureCount()
    count_success = 0
    count_failed = 0
    
    self.logger.debug(
        "Processando features",
        code="LOOP_START",
        total=count_total
    )
    
    for feature in layer.getFeatures():
        try:
            self._process_feature(feature)
            count_success += 1
        except Exception as e:
            count_failed += 1
            self.logger.debug(f"Feature {feature.id()} falhou: {e}")
    
    self.logger.info(
        "Loop concluído",
        code="LOOP_END",
        total=count_total,
        success=count_success,
        failed=count_failed
    )
```

### 4️⃣ Async Tasks (Pipeline)

```python
def on_success(self, context):
    self.logger.info(
        "Pipeline concluída com sucesso",
        code="PIPELINE_SUCCESS",
        steps=context.get("steps_executed"),
        exec_time=context.get("exec_time_ms")
    )

def on_error(self, context, errors):
    first_error = errors[0] if errors else "Unknown"
    self.logger.error(
        f"Pipeline falhou: {first_error}",
        code="PIPELINE_FAILED",
        steps=context.get("steps_executed"),
        error_count=len(errors)
    )
    self.logger.exception(errors[0]) if errors else None
```

### 5️⃣ File Operations (I/O)

```python
def load_file(self, file_path):
    self.logger.debug(f"Lendo arquivo: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.logger.info(
            "Arquivo lido com sucesso",
            code="FILE_READ_OK",
            file_path=file_path,
            file_size=len(content),
            lines=content.count('\n')
        )
        return content
    except FileNotFoundError:
        self.logger.warning(
            f"Arquivo não encontrado: {file_path}",
            code="FILE_NOT_FOUND"
        )
    except Exception as e:
        self.logger.error(f"Erro ao ler arquivo: {e}")
        self.logger.exception(e)
```

---

## 🔍 Análise de Logs (Scripts Úteis)

### 1️⃣ Read & Parse (Python)

```python
import json
from pathlib import Path

log_file = Path.home() / "Cadmus" / "log" / "cadmus_20260412_103045_pid12345.log"

events = []
for line in log_file.read_text(encoding='utf-8').split('\n'):
    if line.strip():
        try:
            event = json.loads(line)
            events.append(event)
        except json.JSONDecodeError:
            pass

# Filtrar por nível
errors = [e for e in events if e['level'] == 'ERROR']
print(f"Total erros: {len(errors)}")

# Filtrar por tool
vector_logs = [e for e in events if e['tool'] == 'vector_fields']
print(f"Logs de vector_fields: {len(vector_logs)}")

# Timeline
for e in events:
    print(f"{e['ts']} [{e['level']:8}] {e['tool']:20} {e['msg']}")
```

### 2️⃣ Find Errors (Shell)

```bash
# Windows PowerShell
$logFile = "$env:APPDATA\QGIS\QGIS3\Cadmus\log\cadmus_*.log"
Get-Content -Path $logFile | ConvertFrom-Json | Where-Object {$_.level -eq "ERROR"} | Select-Object ts, tool, msg

# Linux/Mac
grep '"level":"ERROR"' ~/.local/share/QGIS/QGIS3/Cadmus/log/cadmus_*.log | jq '.tool, .msg'
```

### 3️⃣ Session Tracking

```python
import json
from pathlib import Path
from collections import Counter

log_dir = Path.home() / "Cadmus" / "log"

for log_file in log_dir.glob("cadmus_*.log"):
    session_id = None
    tool_counts = Counter()
    level_counts = Counter()
    
    for line in log_file.read_text(encoding='utf-8').split('\n'):
        if line.strip():
            try:
                event = json.loads(line)
                session_id = event.get('session_id')
                tool_counts[event['tool']] += 1
                level_counts[event['level']] += 1
            except:
                pass
    
    print(f"\n=== {log_file.name} ===")
    print(f"Session: {session_id}")
    print(f"Eventos por nível: {dict(level_counts)}")
    print(f"Top tools: {tool_counts.most_common(3)}")
```

---

## ⚙️ Troubleshooting LogUtils

### ❌ "Arquivo de log não criado"

**Diagnóstico:**
1. LogUtils foi inicializado? (`LogUtils.init()` chamado?)
2. Pasta `log/` tem permissão de escrita?
3. Disco cheio?

**Resolução:**
```python
# Verificar se inicializado
if LogUtils._initialized:
    print(f"Log file: {LogUtils._log_file}")
else:
    print("LogUtils NÃO foi inicializado!")

# Testar inicialização
from pathlib import Path
plugin_root = Path(__file__).parent.parent
result = LogUtils.init(plugin_root)
print(result)  # Deve conter caminho do arquivo
```

**Fallback automático:**
- Se falhar em `<plugin>/log/` → tenta `~/{user}/Cadmus/log/`
- Se ambas falharem → log via `QgsMessageLog` (stderr)

---

### ❌ "Logs aparecem em QgsMessageLog mas não em arquivo"

**Causa:** Arquivo de log inacessível

**Resolução:**
1. Verificar permissões em `~/.../Cadmus/log/`
2. Verificar espaço em disco
3. Ver `QgsMessageLog` entrada com "Falha ao gravar log"

---

### ❌ "Encoding issues (caracteres acentuados viram ?)"

**Resolução:**
```python
# Adicionar no início do arquivo
# -*- coding: utf-8 -*-

# LogUtils já usa utf-8, mas garantir encoding:
message = "Mensagem com acentuação: áéíóú"
logger.info(message)  # ✅ Funciona
```

---

### ❌ "Logger.exception() gera erro SyntaxError"

**Causa:** `exception()` recebe `Exception`, não string

**❌ Errado:**
```python
try:
    risky_op()
except Exception as e:
    logger.exception(str(e))  # ❌ String!
```

**✅ Correto:**
```python
try:
    risky_op()
except Exception as e:
    logger.exception(e)  # ✅ Exception object!
```

---

### ⚠️ "Session ID é None"

**Causa:** `LogUtils.init()` foi chamado mas não completou

**Diagnóstico:**
```python
print(f"Session ID: {LogUtils._session_id}")
print(f"Initialized: {LogUtils._initialized}")
print(f"Log file: {LogUtils._log_file}")
```

**Resolução:** Chamar `LogUtils.init()` explicitamente

---

## 📚 Boas Práticas

### ✅ Fazer

```python
# 1️⃣ Inicializar ao boot
LogUtils.init(plugin_root)

# 2️⃣ Logger com tool_key e class_name
logger = LogUtils(tool=ToolKey.XXX, class_name="MeuPlugin")

# 3️⃣ Dados estruturados
logger.info("Sucesso", file_count=10, duration_ms=500)

# 4️⃣ Código customizado para rastreamento
logger.info("OK", code="VALIDATION_SUCCESS")

# 5️⃣ Exceção com traceback
logger.exception(exc)

# 6️⃣ Diferentes níveis por situação
logger.warning("Aviso")    # Algo inusitado
logger.error("Erro")       # Operação falhou
logger.critical("CRÍTICO") # Sistema quebrado
```

### ❌ Não Fazer

```python
# ❌ Não hardcode strings
logger.info("Camada processada")

# ❌ Não use strings de exceção
try:
    op()
except Exception as e:
    logger.error(str(e))  # Perde traceback

# ❌ Não misture níveis
logger.error("Aviso")  # Confunde análise

# ❌ Não logar dados sensíveis
logger.info("Senha", password="abc123")  # ❌ Segurança!

# ❌ Não inicialize múltiplas vezes
LogUtils.init(root1)
LogUtils.init(root2)  # ❌ Reinicia session
```

---

## 🔌 Sincronização (Thread-Safety)

### LOG_FILE_LOCK

LogUtils usa `LOG_FILE_LOCK` (thread-safe lock) para múltiplas threads:

```python
from core.config.log_sync import LOG_FILE_LOCK

with LOG_FILE_LOCK:
    # Escrita segura ao arquivo
    with open(cls._log_file, "a") as f:
        json.dump(event, f)
```

**Garante:**
- Sem corrupção de arquivo em multi-thread
- Sem race conditions
- Eventos sempre completos (1 linha = 1 evento)

---

## 📊 Exemplo Completo de Plugin

```python
# plugins/MeuPlugin.py
# -*- coding: utf-8 -*-

from ..core.config.LogUtils import LogUtils
from ..utils.ToolKeys import ToolKey
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.ProjectUtils import ProjectUtils
from ..i18n.TranslationManager import STR

class MeuPlugin:
    TOOL_KEY = ToolKey.MINHA_FERRAMENTA
    
    def __init__(self, iface):
        self.iface = iface
        
        # ✅ Criar logger com contexto
        self.logger = LogUtils(
            tool=self.TOOL_KEY,
            class_name="MeuPlugin",
            level=LogUtils.DEBUG
        )
        self.logger.debug("MeuPlugin inicializado")
    
    def execute(self):
        self.logger.info("Iniciando execução", operation="process")
        
        # 1️⃣ VALIDAÇÃO
        layer = ProjectUtils.get_active_vector_layer(
            self.iface.activeLayer(),
            self.logger
        )
        if not layer:
            self.logger.warning("Nenhuma camada selecionada", code="NO_LAYER")
            QgisMessageUtil.bar_critical(self.iface, STR.SELECT_VECTOR_LAYER)
            return
        
        self.logger.debug(f"Camada selecionada", layer=layer.name(), features=layer.featureCount())
        
        # 2️⃣ LÓGICA
        try:
            import time
            start = time.time()
            
            result = self._process_layer(layer)
            
            elapsed = time.time() - start
            
            self.logger.info(
                "Processamento concluído",
                code="PROCESS_SUCCESS",
                result=result,
                elapsed_ms=int(elapsed * 1000)
            )
        except Exception as e:
            self.logger.error(f"Erro durante processamento: {e}")
            self.logger.exception(e, code="PROCESS_FAILED")
            QgisMessageUtil.bar_critical(self.iface, f"Erro: {e}")
            return
        
        # 3️⃣ FEEDBACK
        QgisMessageUtil.bar_success(self.iface, f"Pronto! {result}")
    
    def _process_layer(self, layer):
        self.logger.debug("Iniciando _process_layer", layer=layer.name())
        
        count = 0
        for feature in layer.getFeatures():
            try:
                # Processar feature
                count += 1
            except Exception as e:
                self.logger.debug(
                    f"Feature {feature.id()} falhou",
                    feature_id=feature.id(),
                    error=str(e)
                )
        
        self.logger.debug("_process_layer concluído", features_processed=count)
        return count
```

---

## 🎓 Checklist de Implementação

```
[ ] 1. LogUtils.init() chamado em PluginBootstrap.startUp()
[ ] 2. self.logger = LogUtils(tool=ToolKey.XXX, class_name="Y") em __init__
[ ] 3. logger.info() para operações OK
[ ] 4. logger.warning() para situações inusitadas
[ ] 5. logger.error() para erros não-fatais
[ ] 6. logger.exception(exc) em except Exception
[ ] 7. Dados estruturados em logs: logger.info("msg", key=value)
[ ] 8. Códigos customizados para rastreamento: code="CODE"
[ ] 9. Arquivos UTF-8: # -*- coding: utf-8 -*-
[ ] 10. Testar: Abrir QGIS, executar, verificar logs
```

---

## 📈 Performance

### Overhead Minimal

LogUtils é **otimizado** para baixo overhead:

```python
# Verificação de nível (antes de processar dados)
if not self._allow(level):
    return  # Retorna sem fazer nada se level < configurado

# JSON encoding (eficiente)
json.dump(event, f)  # Nativo Python

# Thread-safe write (rápido)
with LOG_FILE_LOCK:
    f.write(...)  # Uma operação única
```

**Benchmark (estimado):**
- log.info() simples: < 1ms
- log.info() com 10 kwargs: < 2ms
- log.exception(): < 5ms (inclui traceback)
- Sem impacto visível em UI

---

## 🚀 Quick Reference

```python
# Inicializar (1x)
LogUtils.init(Path(__file__).parent.parent)

# Criar logger
logger = LogUtils(tool=ToolKey.XXX, class_name="MeuPlugin")

# Logar
logger.debug("Debug")
logger.info("Info")
logger.warning("Aviso")
logger.error("Erro")
logger.critical("CRÍTICO")
logger.exception(exc)

# Com dados
logger.info("msg", key1=value1, key2=value2)

# Com código
logger.info("msg", code="MY_CODE")

# Mudar nível
logger.set_level(LogUtils.DEBUG)

# Acessar contexto (raro)
print(f"Session: {LogUtils._session_id}")
print(f"Log file: {LogUtils._log_file}")
print(f"Initialized: {LogUtils._initialized}")
```

---

**Especialista em:** JSON-based Logging | Structured Logging | Session Tracking | Thread-Safe Logging  
**Compatível:** QGIS 3.16+, Qt5 ↔ Qt6, Python 3.10+  
**Status:** ✅ Completo e Pronto

