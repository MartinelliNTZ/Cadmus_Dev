# 🧠 SKILL: Preferences — Sistema de Persistência de Configurações

## 📋 RESUMO EXECUTIVO

**Preferences** é um sistema de persistência de configurações que:
- Armazena preferências em JSON estruturado por `tool_key`
- Permite carregar/salvar dados de forma simples e segura
- Suporta operações em lote com filtros
- Funciona com métodos estáticos em todo o código
- Integra com QGIS QStandardPaths para portabilidade Qt5/Qt6

---

## 🎯 OBJETIVO

Gerenciar preferências do plugin (configurações, estado de ferramentas, histórico) de forma centralizada, persistente e sem acoplamento ao QGIS.

---

## 📥 ENTRADAS

- **tool_key**: Identificador da ferramenta (string, ex: "vector_field", "processing")
- **pref_key**: Chave da preferência (string, ex: "main_action", "width")
- **values**: Dicionário com preferências `{chave: valor, ...}`
- **filter_by**: Filtro opcional `{chave_filtro: valor_filtro}`

---

## 📤 SAÍDAS

1. **Arquivo JSON** (`mtl_prefs.json` em `~/.config/MTLTools/`)
   - Estrutura: `{tool_key: {pref_key: valor, ...}, ...}`

2. **Dicionário Python em memória**
   - Retornado por métodos `load_*`

3. **Count de operações** (retornado por set/delete em lote)

---

## ⚙️ PROCESSAMENTO

### **Operação 1: Carregar Preferências Completas**

```python
from utils.Preferences import Preferences

# Carrega TODO o JSON de preferências
all_prefs = Preferences.load_prefs()

# Resultado:
# {
#     "vector_field": {"width": 2.5, "color": "red", "main_action": True},
#     "processing": {"enable_async": True, "thread_count": 4},
#     ...
# }
```

---

### **Operação 2: Carregar Preferências de Uma Ferramenta**

```python
# Carrega APENAS as prefs da ferramenta "vector_field"
vector_prefs = Preferences.load_tool_prefs("vector_field")

# Resultado:
# {"width": 2.5, "color": "red", "main_action": True}
```

---

### **Operação 3: Salvar Preferências de Uma Ferramenta**

```python
# Sobrescreve TODAS as prefs da ferramenta
new_prefs = {
    "width": 3.0,
    "color": "blue",
    "main_action": False,
    "opacity": 0.8
}
Preferences.save_tool_prefs("vector_field", new_prefs)
```

---

### **Operação 4: Carregar Um Valor Específico de Todas as Ferramentas**

```python
# Busca a chave "main_action" em TODAS as ferramentas
main_actions = Preferences.load_pref_key_by_tool("main_action")

# Resultado:
# {
#     "vector_field": True,
#     "processing": False,
#     "export": True
# }
```

---

### **Operação 5: Atualizar Uma Chave em Múltiplas Ferramentas (SEM FILTRO)**

```python
# Ativa "main_action" em TODAS as ferramentas
count = Preferences.set_value_for_all_tools("main_action", True)

# Resultado: modificou 5 ferramentas
# {
#     "vector_field": {..., "main_action": True},
#     "processing": {..., "main_action": True},
#     "export": {..., "main_action": True},
#     ...
# }
```

---

### **Operação 6: Atualizar Uma Chave com FILTRO**

```python
# Ativa "main_action" APENAS nas ferramentas que têm category=="VECTOR"
count = Preferences.set_value_for_all_tools(
    "main_action", 
    True,
    filter_by={"category": "VECTOR"}
)

# Resultado: modificou 2 ferramentas (apenas as que têm category=="VECTOR")
```

---

### **Operação 7: Deletar Uma Chave de Múltiplas Ferramentas (SEM FILTRO)**

```python
# Remove a chave "width" de TODAS as ferramentas
count = Preferences.delete_value_for_all_tools("width")

# Resultado: deletou de 3 ferramentas
```

---

### **Operação 8: Deletar Uma Chave com FILTRO**

```python
# Remove "width" APENAS de ferramentas com category=="RASTER"
count = Preferences.delete_value_for_all_tools(
    "width",
    filter_by={"category": "RASTER"}
)

# Resultado: deletou de 1 ferramenta
```

---

## 📏 REGRAS

### ✅ **SEMPRE:**

- Usar métodos **estáticos** da classe `Preferences` (não instanciar)
- Usar `tool_key` consistente em todas as operações de uma ferramenta
- Armazenar apenas dados **JSON-serializáveis** (str, int, bool, list, dict)
- Validar dados **antes** de salvar (conversão de tipos)
- Usar `load_tool_prefs()` se precisar apenas de uma ferramenta
- Usar `save_tool_prefs()` para atualizar preferências inteiras
- Usar `set_value_for_all_tools()` para mudanças em lote
- Usar filtro `filter_by` para operações **seletivas** em lote

### ❌ **NUNCA:**

- Não instanciar `Preferences()` — usar estáticos
- Não armazenar objetos complexos (ex: QgsLayer, Logger, função)
- Não mixar acesso direto ao arquivo com métodos da classe
- Não deixar preferences desincronizadas entre instâncias (sempre usar Preferences)
- Não ignorar erros de I/O — tratar exceções ao carregar/salvar
- Não confiar que o arquivo existe sempre — use `_ensure_pref_folder()`

---

## 📦 DEPENDÊNCIAS

```python
from utils.Preferences import Preferences
```

**Importações internas:**
- `QStandardPaths` (QGIS PyQt) — para compatibilidade Qt5/Qt6
- `LogUtils` — para logging de operações
- `json` — para serialização

---

## 🔧 EXEMPLOS

### **Exemplo 1: Ferramenta Inicializando Preferências**

```python
# plugins/VectorFieldPlugin.py
from utils.Preferences import Preferences
from utils.ToolKeys import ToolKey
from core.config.LogUtils import LogUtils

class VectorFieldPlugin:
    TOOL_KEY = ToolKey.VECTOR_FIELD
    
    def __init__(self):
        self.logger = LogUtils(tool=self.TOOL_KEY, class_name="VectorFieldPlugin")
        self._load_or_create_prefs()
    
    def _load_or_create_prefs(self):
        """Carrega prefs ou cria padrão"""
        prefs = Preferences.load_tool_prefs(self.TOOL_KEY)
        
        # Se não existem, criar padrão
        if not prefs:
            prefs = {
                "width": 2.0,
                "color": "red",
                "main_action": True,
                "opacity": 1.0
            }
            Preferences.save_tool_prefs(self.TOOL_KEY, prefs)
            self.logger.info("Preferências padrão criadas")
        
        self.prefs = prefs
        self.logger.debug("Preferências carregadas", count=len(prefs))
    
    def set_width(self, width):
        """Atualiza a largura"""
        self.prefs["width"] = width
        Preferences.save_tool_prefs(self.TOOL_KEY, self.prefs)
        self.logger.info("Largura atualizada", value=width)
```

---

### **Exemplo 2: Operação em Lote com Filtro**

```python
# Desativar "main_action" em TODAS as ferramentas da categoria VECTOR
from utils.Preferences import Preferences

count = Preferences.set_value_for_all_tools(
    "main_action",
    False,
    filter_by={"category": "VECTOR"}
)

print(f"Desativadas {count} ferramentas de categoria VECTOR")
```

---

### **Exemplo 3: Buscar Configuração Global**

```python
# Buscar qual é o thread_count em cada ferramenta
thread_counts = Preferences.load_pref_key_by_tool("thread_count")

for tool_key, count in thread_counts.items():
    print(f"{tool_key}: {count} threads")

# Resultado:
# processing: 4 threads
# export: 2 threads
# import: 2 threads
```

---

### **Exemplo 4: Método Estático que Usa Preferences**

```python
# utils/VectorUtils.py
from utils.Preferences import Preferences
from utils.ToolKeys import ToolKey
from core.config.LogUtils import LogUtils

class VectorUtils:
    @staticmethod
    def get_default_width():
        """Retorna largura padrão da ferramenta"""
        logger = LogUtils(tool=ToolKey.SYSTEM, class_name="VectorUtils")
        
        prefs = Preferences.load_tool_prefs(ToolKey.VECTOR_FIELD)
        width = prefs.get("width", 2.0)
        
        logger.debug("Largura obtida", value=width)
        return width

# Uso:
width = VectorUtils.get_default_width()
```

---

### **Exemplo 5: Migração de Preferências (Update em Lote)**

```python
# Migrate: adicionar categoria em todas as ferramentas
prefs = Preferences.load_prefs()

for tool_key in prefs:
    prefs[tool_key]["category"] = "UNKNOWN"  # padrão

Preferences.save_prefs(prefs)

# Depois usar filtro:
Preferences.set_value_for_all_tools("enabled", True, filter_by={"category": "VECTOR"})
```

---

### **Exemplo 6: Atualizar Parcial (Merge)**

```python
# Atualizar APENAS algumas chaves mantendo outras
tool_key = "vector_field"

# Carregar atuais
current = Preferences.load_tool_prefs(tool_key)

# Fazer merge (Python 3.9+)
updated = current | {"width": 3.0, "opacity": 0.5}

# Salvar
Preferences.save_tool_prefs(tool_key, updated)

# Resultado: width e opacity mudaram, color mantém valor antigo
```

---

## 📋 ESTRUTURA DO ARQUIVO JSON

**Localização:** `~/.config/MTLTools/mtl_prefs.json` (ou equivalente em Qt6)

**Formato:**
```json
{
    "vector_field": {
        "width": 2.5,
        "color": "red",
        "main_action": true,
        "opacity": 1.0,
        "category": "VECTOR"
    },
    "processing": {
        "enable_async": true,
        "thread_count": 4,
        "category": "PROCESSING",
        "main_action": true
    },
    "export": {
        "format": "shapefile",
        "compress": false,
        "category": "IO",
        "main_action": false
    }
}
```

---

## ⚠️ LIMITAÇÕES

- **Dados por tool:** estrutura é `{tool_key: {prefs}}`, sem nested profundo
- **Sem versionamento:** não há track de histórico de mudanças
- **Sem validação automática:** tipos não são validados (sua responsabilidade)
- **Sem transações:** se salvar falhar, pode perder dados parciais
- **Sem lock de acesso:** múltiplos processos podem criar race condition
- **String-based:** chaves de filtro precisam match exato (case-sensitive)

---

## 🔍 VALIDAÇÃO

| Critério | Status |
|----------|--------|
| **Reutilizável?** | ✅ SIM — usado globalmente para toda persistência |
| **Clara?** | ✅ SIM — 8 operações bem definidas |
| **Independente?** | ✅ SIM — funciona sem dependências do plugin |

---

## 🎓 CONCLUSÃO

**Preferences é o ponto único de acesso a configurações persistentes no Cadmus.**

**Operações principais:**
- `load_prefs()` — tudo
- `load_tool_prefs(tool_key)` — uma ferramenta
- `save_tool_prefs(tool_key, values)` — atualizar uma ferramenta
- `load_pref_key_by_tool(pref_key)` — um valor em todas
- `set_value_for_all_tools(key, value, filter_by)` — lote com filtro
- `delete_value_for_all_tools(key, filter_by)` — remover em lote

**Padrão recomendado:**
1. Inicializar prefs na `__init__` da ferramenta
2. Usar métodos estáticos em qualquer lugar
3. Sempre usar `tool_key` consistente
4. Armazenar apenas JSON-serializáveis
