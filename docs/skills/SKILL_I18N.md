# 🧠 SKILL: I18N — Sistema de Internacionalização

## 📋 RESUMO EXECUTIVO

**Sistema I18N do Cadmus** gerencia:
- **Strings traduzíveis** (4 idiomas: pt_BR, en, es, de)
- **Instruções Markdown** (`.md` simples por locale)
- **Instruções HTML** (`.html` + Python com métodos interpolados)
- **Locale detector** (QStandardPaths, fallback pt_BR)

**Princípio cardinal:** `pt_BR` é a **lingua-pai**. Tudo inicia em pt_BR. Tradução é processo futuro e **semântico, não literal**.

**Logs são sempre em pt_BR e nunca traduzidos.**

**Instruções só geradas quando solicitadas (não durante desenvolvimento).**

---

## 🎯 OBJETIVO

Permitir que o plugin Cadmus funcione em múltiplos idiomas (4 principais: pt_BR, en, es, de) mantendo consistência e permitindo tradução semântica futura sem quebra de código.

---

## 📥 ENTRADAS

- **locale**: Identificador de idioma (pt_BR, en, es, de, ja, etc)
- **key**: Chave de string (string_key para lookup em Strings_*.py)
- **tool_key**: Identificador da ferramenta (ToolKey enum)
- **algorithm_name**: Nome do algoritmo (para buscar método em HtmlInstructions)

---

## 📤 SAÍDAS

1. **String traduzida** (em memória)
2. **Arquivo Markdown** (instruções simples)
3. **HTML renderizado** (instruções complexas com logo, autor, etc)

---

## ⚙️ PROCESSAMENTO

---

### **Componente 1: TranslationManager (Núcleo)**

**Localização:** [i18n/TranslationManager.py](../../i18n/TranslationManager.py)

**Responsabilidades:**
- Detectar locale do sistema (QStandardPaths)
- Carregar módulo Strings_* correto
- Fallback pt_BR se locale não disponível
- Cache de strings em memória

**API:**
```python
from i18n.TranslationManager import STR, LOCALE

# Propriedades
locale_code = LOCALE  # ex: "pt_BR", "en", "es"
string_value = STR.TITLE_VECTOR_FIELD  # atributo da instância Strings_*

# Exemplos:
STR.TITLE_VECTOR_FIELD  # retorna string traduzida para locale atual
LOCALE  # ex: "en"
```

**STR é instância de Strings_pt_BR (ou subclasse como Strings_en se existir). Se chave não existir na subclasse, herda de pt_BR. Locale fica no TranslationManager.**

**Padrão esperado em Strings_*.py:**
```python
# i18n/Strings_pt_BR.py
class Strings:
    TITLE_VECTOR_FIELD = "Campos Vetoriais"
    DESC_VECTOR_FIELD = "Calcula campos vetoriais a partir de geometrias"
    WIDTH = "Largura"
    # ... etc

# i18n/Strings_en.py (tradução futura)
class Strings:
    TITLE_VECTOR_FIELD = "Vector Fields"
    DESC_VECTOR_FIELD = "Calculate vector fields from geometries"
    WIDTH = "Width"
    # ... etc
```

---

### **Componente 2: InstructionsManager (Markdown)**

**Localização:** [resources/InstructionsManager.py](../../resources/InstructionsManager.py)

**Responsabilidades:**
- Carregar arquivos `.md` por locale usando ToolKey diretamente
- Resolver caminho: `instructions/<locale>/<tool_key>_help.md`
- Fallback pt_BR → standard.md
- Cache de caminhos

**API:**
```python
from resources.InstructionsManager import InstructionsManager as IM
from utils.ToolKeys import ToolKey

# Obter caminho do arquivo de instruções (usa ToolKey diretamente)
help_path = IM.get(tool_key=ToolKey.VECTOR_FIELD)
# Resultado: ".../instructions/pt_BR/vector_field_help.md"

# Ler conteúdo (manual, fora do escopo do InstructionsManager)
with open(help_path, "r", encoding="utf-8") as f:
    markdown_text = f.read()
```

**InstructionsManager é extensão do TranslationManager para instruções de plugins.**

**Estrutura de arquivos esperada:**
```
resources/
  instructions/
    pt_BR/
      vector_field_help.md
      generate_trail_help.md
      standard.md          # fallback
    en/
      vector_field_help.md
      generate_trail_help.md
    es/
      vector_field_help.md
    de/
      vector_field_help.md
```

---

### **Componente 3: HtmlInstructionsProvider (HTML Dinâmico)**

**Localização:** [resources/HtmlInstructionsProvider.py](../../resources/HtmlInstructionsProvider.py)

**Responsabilidades:**
- Carregar módulo `HtmlInstructions_<locale>.py` dinamicamente usando ToolKey
- Interpolar logo, autor, strings traduzidas
- Cache de instruções em memória
- Métodos auxiliares para HTML (headings, alerts)

**API:**
```python
from resources.HtmlInstructionsProvider import HtmlInstructionsProvider
from utils.ToolKeys import ToolKey

# Inicializar para uma ferramenta (usa ToolKey)
provider = HtmlInstructionsProvider(tool_key=ToolKey.VECTOR_FIELD)

# Obter HTML de um algoritmo (usa ToolKey para algoritmo, não string hardcoded)
html_content = provider.get_instructions(algorithm_name=ToolKey.GRID_GENERATOR)
```

**HtmlInstructionsProvider é extensão do TranslationManager para instruções HTML.**

**Estrutura de arquivos esperada:**
```
resources/
  instructions/
    html/
      HtmlInstructions_pt_BR.py    # Classe com métodos get_*_help()
      HtmlInstructions_en.py
      HtmlInstructions_es.py
      HtmlInstructions_de.py
```

**Exemplo de HtmlInstructions_pt_BR.py:**
```python
class HtmlInstructions:
    def __init__(self, provider):
        self.provider = provider
    
    def get_grid_generator_help(self):
        """Retorna HTML para Grid Generator"""
        return f"""
        {self.provider.logo}
        {self.provider.transform_h("Grid Generator", 1)}
        <p>Este algoritmo gera uma grade regular de pontos.</p>
        <h3>Parâmetros:</h3>
        <ul>
            <li><strong>Tamanho da célula:</strong> Define o espaçamento entre pontos</li>
        </ul>
        {self.provider.author_info}
        """
```

---

## 📏 REGRAS

### ✅ **SEMPRE:**

- **Criar novo conteúdo em pt_BR primeiro**
  - Strings em `i18n/Strings_pt_BR.py`
  - Instruções em `resources/instructions/pt_BR/<tool_key>_help.md`
  - HTML em `resources/instructions/html/HtmlInstructions_pt_BR.py`

- **Usar STR (TranslationManager) para todas as strings**
  ```python
  from i18n.TranslationManager import STR
  label = STR.WIDTH  # NUNCA hardcode strings
  ```

- **Usar chaves de string UPPERCASE_WITH_UNDERSCORES (padrão inglês)**
  - Facilita busca e refatoração
  - Exemplo: `TITLE_VECTOR_FIELD = "Campos Vetoriais"` (chave em inglês, valor em pt_BR)

- **Estruturar Strings_*.py por categoria**
  ```python
  # i18n/Strings_pt_BR.py
  
  # ===== VECTOR FIELD =====
  TITLE_VECTOR_FIELD = "Campos Vetoriais"
  DESC_VECTOR_FIELD = "Calcula campos vetoriais..."
  WIDTH = "Largura"
  
  # ===== PROCESSING =====
  TITLE_PROCESSING = "Processamento"
  DESC_PROCESSING = "Processamento de dados..."
  ```

- **Usar fallback pt_BR em caso de erro**
  - Garante que o plugin sempre funcionará em pt_BR
  - Outras línguas são "nice-to-have"

- **Documentar chaves de string com comentários**
  ```python
  # i18n/Strings_pt_BR.py
  
  # Context: usado em diálogos de configuração
  # Category: VECTOR
  WIDTH = "Largura"
  ```

- **Tradução é semântica, não literal**
  - Adaptar para cada idioma: significado, contexto, convenções
  - Não usar tradutores automáticos diretos
  - Revisar com falantes nativos

- **Sempre usar ToolKey enum**
  ```python
  from utils.ToolKeys import ToolKey
  tool_key = ToolKey.VECTOR_FIELD  # NUNCA string hardcoded
  ```

- **Verificar duplicidade antes de criar variável**
  - Se já existe `INPUT = "Entrada"`, reutilizar
  - Para formatação: `f"{STR.INPUT}:"`

- **Usar variáveis genéricas**
  - Ruim: `LABEL_WIDTH = "Largura"`
  - Bom: `WIDTH = "Largura"` + `f"{STR.WIDTH} (mm)"`

### ❌ **NUNCA:**

- Não hardcode strings em código Python
  - Sempre usar `STR.KEY`
  
- Não traduzir durante codificação
  - Tradução é processo separado e futuro
  
- Não misturar pt_BR com outras línguas em um arquivo
  - Cada arquivo é para um locale específico

- Não criar novos locales sem aprovação
  - Manter estrutura com 4 principais: pt_BR, en, es, de

- Não usar chaves genéricas
  - Ruim: `TITLE`, `DESC`
  - Bom: `TITLE_VECTOR_FIELD`, `DESC_VECTOR_FIELD`

- Não confiar em STR.locale para strings em métodos estáticos
  - Pode mudar durante execução; usar cache ou parâmetro

- Não usar string para tool_key
  - Sempre `ToolKey.VECTOR_FIELD`

- Não criar templates HTML opcionais
  - Tudo deve ser gerado dinamicamente

- Não usar QtWidgets diretamente
  - Usar widget factory e widgets customizados

---

## 📦 DEPENDÊNCIAS

```python
from i18n.TranslationManager import STR
from resources.InstructionsManager import InstructionsManager as IM
from resources.HtmlInstructionsProvider import HtmlInstructionsProvider
from utils.ToolKeys import ToolKey
```

**Dependências internas:**
- `QStandardPaths` (QGIS PyQt) — detect locale
- `Path` (pathlib) — file resolution
- `importlib.util` — dynamic module loading
- `LogUtils` — logging (em HtmlInstructionsProvider)

---

## 🔧 EXEMPLOS

### **Exemplo 1: Adicionar Nova String (pt_BR)**

```python
# i18n/Strings_pt_BR.py

# Verificar duplicidade: INPUT já existe? Se sim, reutilizar
# Se não, adicionar:

# ===== DRONE COORDINATES =====
TITLE_DRONE_COORDINATES = "Coordenadas de Drone"
DESC_DRONE_COORDINATES = "Importa coordenadas de voo de drone"
LATITUDE = "Latitude"
LONGITUDE = "Longitude"
ALTITUDE = "Altitude"
ERROR_INVALID_COORDS = "Coordenadas inválidas"
```

**Uso em código:**
```python
from i18n.TranslationManager import STR

class DronePlugin:
    def get_title(self):
        return STR.TITLE_DRONE_COORDINATES
    
    def validate_coords(self, lat, lon):
        if not isinstance(lat, float):
            raise ValueError(STR.ERROR_INVALID_COORDS)
        return True
```

---

### **Exemplo 2: Adicionar Instruções Markdown (pt_BR)**

```markdown
# Coordenadas de Drone

## Descrição
Este algoritmo importa coordenadas de voo de drone de um arquivo CSV.

## Parâmetros
- **Arquivo CSV**: Caminho para arquivo com colunas lat, lon, alt
- **EPSG**: Código EPSG do SRC (padrão: 4326)

## Saída
Camada vetorial com pontos de waypoint.

## Exemplo
```
lat,lon,alt
-30.0,-51.0,50
-30.1,-51.0,60
```

## Avisos
- ⚠️ Sempre validar coordenadas antes de usar em navegação
- ⚠️ Certifique-se que SRC está correto
```

**Salvar em:** `resources/instructions/pt_BR/drone_coordinates_help.md`

---

### **Exemplo 3: Adicionar Instruções HTML (pt_BR)**

```python
# resources/instructions/html/HtmlInstructions_pt_BR.py

class HtmlInstructions:
    def __init__(self, provider):
        self.provider = provider
    
    def get_drone_coordinates_help(self):
        """Retorna HTML para Drone Coordinates"""
        return f"""
        {self.provider.logo}
        {self.provider.transform_h("Coordenadas de Drone", 1)}
        
        <h2>Descrição</h2>
        <p>Importa coordenadas de voo de drone de um arquivo CSV.</p>
        
        <h2>Parâmetros</h2>
        <ul>
            <li><strong>Arquivo CSV:</strong> Caminho para arquivo com colunas lat, lon, alt</li>
            <li><strong>EPSG:</strong> Código EPSG do SRC (padrão: 4326)</li>
        </ul>
        
        <h2>Saída</h2>
        <p>Camada vetorial com pontos de waypoint.</p>
        
        {self.provider.transform_alert("Sempre validar coordenadas antes de usar em navegação")}
        
        {self.provider.author_info}
        """
```

---

### **Exemplo 4: Usar STR em Widget Customizado**

```python
from widgets.WidgetFactory import WidgetFactory
from i18n.TranslationManager import STR
from utils.ToolKeys import ToolKey

class DroneCoordinatesWidget:
    def __init__(self):
        self.factory = WidgetFactory(tool_key=ToolKey.DRONE_COORDINATES)
        self.init_ui()
    
    def init_ui(self):
        # WidgetFactory tem métodos estáticos para criar widgets
        self.title_label = WidgetFactory.create_label(STR.TITLE_DRONE_COORDINATES)
        self.lat_label = WidgetFactory.create_label(f"{STR.LATITUDE}:")
        self.lon_label = WidgetFactory.create_label(f"{STR.LONGITUDE}:")
        self.alt_label = WidgetFactory.create_label(f"{STR.ALTITUDE}:")
        
        self.lat_input = WidgetFactory.create_line_edit()
        self.lon_input = WidgetFactory.create_line_edit()
        self.alt_input = WidgetFactory.create_line_edit()
        
        # ... layout usando factory
```

---

### **Exemplo 5: Tradução Futura (Semântica, não Literal)**

**Original (pt_BR):**
```python
WIDTH = "Largura"
ERROR_NO_LAYER = "Nenhuma camada selecionada"
```

**Tradução Inglês (SEMÂNTICA):**
```python
WIDTH = "Width"  # equivalente direto
ERROR_NO_LAYER = "No layer selected"  # adaptado para idioma natural inglês
```

**❌ NÃO fazer:**
```python
ERROR_NO_LAYER = "None layer selected"  # Literal, incorreto em inglês
```

---

### **Exemplo 6: Categorizar Strings Complexas**

```python
# i18n/Strings_pt_BR.py

# ===== GRID GENERATOR =====
TITLE_GRID_GENERATOR = "Gerador de Grade"
DESC_GRID_GENERATOR = "Cria uma grade regular de pontos ou células"

# Parâmetros
CELL_SIZE = "Tamanho da célula"
CELL_SIZE_DESC = "Espaçamento entre pontos (em unidades do projeto)"
GRID_TYPE = "Tipo de grade"
GRID_TYPE_POINTS = "Pontos"
GRID_TYPE_HEXAGON = "Hexágono"
GRID_TYPE_RECT = "Retângulo"

# Erros
ERROR_CELL_SIZE_INVALID = "Tamanho de célula deve ser > 0"
ERROR_EXTENT_INVALID = "Extensão deve ter área válida"

# Mensagens
MSG_GRID_CREATED = "Grade criada com sucesso"
MSG_GRID_FEATURES = "Total de feições criadas: {count}"
```

---

## 📋 FLUXO DE TRADUÇÃO (FUTURO)

**Quando solicitado (ex: "traduzir para inglês"):**

1. ✅ Ler todas as chaves em Strings_pt_BR.py
2. ✅ Adaptar semanticamente para inglês (revisar idiomatismos)
3. ✅ Traduzir arquivos Markdown em `instructions/en/`
4. ✅ Traduzir método em `HtmlInstructions_en.py`
5. ✅ Testar com falante nativo se possível

**Exemplo de mudança semântica:**
- pt_BR: "Pontos da barra lateral" → en: "Sidebar markers" (não "Points of sidebar")
- pt_BR: "Camada ativa" → en: "Active layer" (não "Layer active")

---

## ⚠️ LIMITAÇÕES

- **4 idiomas principais:** pt_BR, en, es, de (extender requer setup)
- **Sem versioning de strings:** mudança de chave quebra compatibilidade
- **Sem pluralização automática:** criar chaves separadas (ITEM, ITEMS)
- **Sem contexto dinâmico:** strings não interpolam variáveis automaticamente
- **Cache em memória:** mudança de locale durante execução não recarrega strings

---

## 🔍 VALIDAÇÃO

| Critério | Status |
|----------|--------|
| **Reutilizável?** | ✅ SIM — usado em toda UI e algoritmos |
| **Clara?** | ✅ SIM — 3 componentes bem definidos |
| **Independente?** | ✅ SIM — funciona com/sem QGIS |
| **Extensível?** | ✅ SIM — adicionar novo locale é trivial |

---

## 🎓 CONCLUSÃO

**I18N no Cadmus segue 3 camadas:**

1. **Strings** → `STR.KEY` em código Python
2. **Markdown** → `InstructionsManager.get(tool_key=ToolKey.X)`
3. **HTML** → `HtmlInstructionsProvider(tool_key=ToolKey.X).get_instructions(algorithm)`

**Processo de desenvolvimento:**

1. ✅ Criar em **pt_BR** (sempre)
2. ✅ Usar **STR.KEY** para acesso
3. ✅ Documentar **chaves uppercase**
4. ⏸️ Tradução = **processo futuro separado**
5. 🌍 Tradução = **semântica, não literal**

**Nunca** misturar idiomas, hardcode strings ou traduzir durante codificação. **Logs sempre em pt_BR.**

