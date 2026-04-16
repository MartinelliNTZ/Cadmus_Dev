# 📚 LOGCAT VIEWER - Aula para Iniciantes

**Um guia MUITO simples (como se você fosse um cachorro!) para entender como funciona o sistema de logs do Cadmus**

---

## 🎬 Prólogo: Uma História para Começar

Imagina que você tem um **caderno gigante** onde você escreve TUDO que seu programa está fazendo:

- "9h30m: Abri a ferramenta Vector Fields"
- "9h30m10s: Selecionei a camada XYZ"
- "9h30m20s: Erro! Campo não existe"
- "9h30m30s: Tentei novamente, agora funcionou!"

Esse caderno é como um **BLACK BOX DE AVIÃO** - guarda tudo para você analisar depois.

Agora... esse caderno fica **GIGANTESCO** quando você usa QGIS por 8 horas... milhões de linhas. Como você encontra o erro que aconteceu às 2:45 da tarde entre 10 milhões de linhas?

**Resposta: LOGCAT VIEWER!** 🔍

É um programa que:
1. **Lê** esse caderno gigante
2. **Organiza** em uma tabela bonita
3. **Filtra** para mostrar só o que você quer
4. **Colore** diferente (erro em vermelho, aviso em amarelo, sucesso em verde)
5. **Deixa você buscar** como no Google

---

## 🏗️ Arquitetura: As Peças do Jogo

Imagine que LOGCAT é uma **máquina de café**. Ela tem várias partes:

```
┌─────────────────────────────────────────────────────┐
│                 LOGCAT VIEWER                       │
│              (Máquina de Café)                      │
└─────────────────────────────────────────────────────┘
           ↓          ↓          ↓
      ┌────────┬─────────┬─────────┬──────────┐
      │         │         │         │          │
   🔥 HEAT   💧 WATER  ☕ COFFEE 🚰 FILTER  🖨️ OUTPUT
   (Log    (Session  (Model/  (Filter  (UI/
   Files)  Manager)  Table)   Engine)   Table)
```

### Agora vamos entender cada peça:

---

## 🔥 PEÇA 1: LOG FILES (Os Arquivos de Log)

**O que é?** Pasta `plugins/Cadmus/log/` com arquivos `.jsonl` (JSON Line).

**Estrutura de um arquivo:**
```jsonl
{"ts":"2026-03-02T20:07:15.123", "level":"INFO", "plugin":"Cadmus", "tool":"vector_field", "msg":"Iniciando cálculo", "thread":"MainThread"}
{"ts":"2026-03-02T20:07:16.456", "level":"ERROR", "plugin":"Cadmus", "tool":"vector_field", "msg":"Feature count 0", "data":{"layer":"XYZ"}}
```

**Por que JSON Line?** 
- Cada linha é um **JSON completo independente** ✅
- Fácil de **ler incrementalmente** (não precisa carregar tudo na memória) ✅
- Não precisa de comma entre linhas ✅

**Analogia:** É como ter um **caderno onde cada página é completamente independente**, em vez de um livro inteiro onde tudo é relacionado.

---

## 💧 PEÇA 2: LOG SESSION MANAGER

**O que faz?** Gerencia **sessões de log**.

**Classe:** `LogSessionManager` (arquivo: `core/model/log_session_manager.py`)

**O que é uma "sessão"?** 

É como... imagina que você usa QGIS toda semana:
- **Segunda**: Você abre QGIS, faz um trabalho, fecha → SESSÃO 1
- **Terça**: Você abre QGIS novamente, faz outro trabalho → SESSÃO 2

Cada sessão é um **arquivo de log separado**:
```
plugins/log/
├── session_001_2026-03-02_09-00.jsonl
├── session_002_2026-03-02_14-00.jsonl
└── session_003_2026-03-03_08-30.jsonl
```

**O LogSessionManager faz:**
1. **Lista** todas as sessões 
2. **Carrega** a sessão que você quer
3. **Sabe** quando uma sessão começou e terminou
4. **Permite** você escolher entre "ontem" ou "hoje"

**Analogia:** É um **índice de um livro gigante**, onde cada capítulo é uma sessão.

```python
# Código real:
session_manager = LogSessionManager(log_dir)
sessions = session_manager.get_sessions()  # Lista todas
current = session_manager.load_session(sessions[0])  # Carrega primeira
```

---

## ☕ PEÇA 3: LOG ENTRY (O Modelo de Dados)

**O que é?** Uma **linha de log convertida em objeto Python**.

**Classe:** `LogEntry` (arquivo: `core/model/log_entry.py`)

**Exemplo:**
```python
# Uma linha JSON bruta:
'{"ts":"2026-03-02T20:07:15", "level":"INFO", "msg":"Iniciando"}'

# Vira um objeto Python:
entry = LogEntry(
    ts="2026-03-02T20:07:15",
    level="INFO",
    msg="Iniciando",
    plugin="Cadmus",
    tool="vector_field",
    thread="MainThread"
)
```

**Por que converter?**
- Mais **seguro** (você acessa `entry.level` em vez de `entry["level"]`)
- **Verificação de tipo** (IDE avisa se você errar)
- **Métodos úteis** (ex: `entry.formatted_time()`)

**Analogia:** É como ter um **formulário preenchido** em vez de uma folha de papel amassada.

---

## 🚰 PEÇA 4: LOG LOADER (Carregador de Logs)

**O que faz?** **Lê logs de um arquivo JSONL linha por linha** sem carregar tudo na memória.

**Classe:** `LogLoader` (arquivo: `core/io/log_loader.py`)

**O problema sem LogLoader:**
```python
# ❌ RUIM: Se arquivo tem 1 GB
with open("session.jsonl") as f:
    all_lines = f.readlines()  # Carrega TUDO na memória!
    # Seu programa trava!
```

**Solução com LogLoader:**
```python
# ✅ BOM: Lê incrementalmente
loader = LogLoader(session_file)
for entry in loader.load_incremental():  # Uma linha de cada vez!
    print(entry.msg)
```

**Analogia:** 
- **Sem LogLoader:** É como tentar ler um livro de 1000 páginas de uma vez (impossível!)
- **Com LogLoader:** Você lê página por página, conforme precisa

**Código real:**
```python
self.current_loader = LogLoader(current_session.file_path)
self.all_entries = list(self.current_loader.load_incremental())
```

---

## 🔎 PEÇA 5: LOG FILTER ENGINE (Motor de Filtros)

**O que faz?** Filtra logs por **critérios específicos**.

**Classe:** `LogFilterEngine` (arquivo: `core/filter/log_filter_engine.py`)

**Exemplos de filtros:**

1. **Por nível:** Mostrar só ERRORs
2. **Por tool:** Mostrar só Vector Field
3. **Por palavra-chave:** Mostrar só linhas com "KML"
4. **Por data:** Mostrar só logs das 14h às 16h
5. **Por thread:** Mostrar só da MainThread

**Código:**
```python
filter_engine = LogFilterEngine()

# Filtrar por nível
filter_engine.set_level_filter("ERROR")

# Filtrar por texto
filter_engine.set_text_filter("KML")

# Aplica o filtro a uma lista de entries
filtered = filter_engine.apply(all_entries)
```

**Analogia:** É como ter um **quebra-cabeça gigante e você pegar só as peças vermelhas** (ignorando azuis, verdes, etc).

---

## 🎨 PEÇA 6: LOG TABLE MODEL (Tabela de Dados)

**O que faz?** Converte lista de **LogEntry** em uma **tabela visual** que o Qt entende.

**Classe:** `LogTableModel` (arquivo: `ui/log_table_model.py`)

**Como funciona:**

Qt precisa de um "modelo" para saber:
- Quantas linhas tem?
- Quantas colunas tem?
- Qual é o valor de cada célula?
- Qual é a cor de cada célula?

```python
class LogTableModel(QAbstractTableModel):
    def rowCount(self):
        return len(self.entries)  # Quantas linhas?
    
    def columnCount(self):
        return 8  # ts, level, tool, msg, thread, plugin, etc
    
    def data(self, index):
        entry = self.entries[index.row()]
        column = index.column()
        if column == 0:
            return entry.ts
        elif column == 1:
            return entry.level
        # etc...
    
    def color_for_level(self, level):
        if level == "ERROR":
            return RED
        elif level == "WARNING":
            return YELLOW
        return GREEN
```

**Analogia:** É como montar uma **planilha do Excel automaticamente**. O Qt quer saber qual valor vai em cada célula.

---

## 🖼️ PEÇA 7: LOGCAT DIALOG (Interface Principal)

**O que faz?** É a **janela bonita** que você vê.

**Classe:** `LogcatDialog` (arquivo: `ui/logcat_dialog.py`)

**Componentes na tela:**
```
┌─────────────────────────────────────────────┐
│ LogCat Viewer - Cadmus                   │
├─────────────────────────────────────────────┤
│ [Sessão: ▼] [Nível: ERROR ▼] [Buscar: ___] │  ← Filtros
├─────────────────────────────────────────────┤
│ ts    | level | tool  | msg        | thread  │  ← Headers
├─────────────────────────────────────────────┤
│ 20:07 | ERROR | Vec   | KML não ed | Main    │  ← Linhas
│ 20:08 | WARN  | Buf   | Lento      | Work-1  │
│ 20:09 | INFO  | Vec   | OK         | Main    │
└─────────────────────────────────────────────┘
```

**Responsabilidades:**
1. Carregar sessão quando você escolhe
2. Aplicar filtros quando você digita
3. Atualizar tabela quando há novos logs
4. Mostrar cores (vermelho = erro, amarelo = aviso)
5. Deixar você clicar em uma linha para ver detalhes

**Código (resumido):**
```python
class LogcatDialog(QDialog):
    def __init__(self, parent=None):
        # Criar UI
        self.table_view = QTableView()
        self.search_box = QLineEdit()
        self.level_combo = QComboBox()
        
        # Conectar signals
        self.search_box.textChanged.connect(self._apply_filters)
        self.level_combo.currentTextChanged.connect(self._apply_filters)
        self.table_view.doubleClicked.connect(self._show_details)
    
    def _apply_filters(self):
        """Quando usuário digita algo, aplicar filtro"""
        text = self.search_box.text()
        level = self.level_combo.currentText()
        
        # Filtrar usando LogFilterEngine
        filtered = self.filter_engine.filter(
            all_entries, 
            text=text, 
            level=level
        )
        
        # Atualizar tabela
        self.table_model.set_entries(filtered)
        self.table_view.update()
```

---

## 🔄 PEÇA 8: LOG FILE WATCHER (Observador de Mudanças)

**O que faz?** **Observa o arquivo de log** e avisa quando tem coisas novas.

**Classe:** `LogFileWatcher` (arquivo: `core/io/log_file_watcher.py`)

**Problema:** Se você tiver o Logcat aberto e o QGIS escribendo novos logs, como o Logcat sabe que há novos logs?

**Solução:** Uma **thread separada** que fica verificando:
```python
while True:
    arquivo_mudou?
    se sim:
        emitir sinal "file_changed"
```

**Analogia:** É como ter um **amigo vigiando a porta** e gritando "Ei! Alguém chegou!" quando alguém entra.

**Código (bem resumido):**
```python
class LogFileWatcher(QThread):
    file_changed = pyqtSignal()  # Sinal: "arquivo mudou!"
    
    def run(self):
        while True:
            if arquivo_mudou():
                self.file_changed.emit()  # Grita!
            time.sleep(1)  # Verifica a cada 1 segundo
```

---

## 🎬 O FLUXO COMPLETO: Passo a Passo

**Você clica em "Abrir Logcat":**

```
┌─────────────────────────────────────────────────────────┐
│ 1. User clica Menu → Logcat                             │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ 2. logcat_plugin.py → run() cria LogcatDialog           │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ 3. LogcatDialog.__init__()                              │
│    ├─ Cria SessionManager (lista arquivos de log)       │
│    ├─ Cria FilterEngine (preparado para filtrar)        │
│    ├─ Cria TableModel (pronto para mostrar dados)       │
│    └─ Cria UI (botões, caixa de busca, tabela)          │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Você seleciona uma sessão no dropdown                │
│    └─ LogSessionManager carrega arquivo .jsonl          │
│    └─ LogLoader lê linha por linha sem travar           │
│    └─ Cada linha vira um LogEntry                       │
│    └─ Armazena em all_entries[]                         │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ 5. LogTableModel pega all_entries e cria tabela visual  │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ 6. Tabela aparece na tela com CORES!                    │
│    (vermelho = ERROR, amarelo = WARNING, etc)           │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ 7. Você digita "KML" na caixa de busca                  │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ 8. LogFilterEngine filtra (mostra só linhas com "KML")  │
│    └─ Apenas 3 linhas aparecem (em vez de 10000)        │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ 9. Você clica duplo em uma linha                        │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ 10. LogDetailDialog abre mostrando TODOS os detalhes:   │
│     ├─ Timestamp completo (20:07:15.123)                │
│     ├─ Thread que executou (MainThread)                 │
│     ├─ Plugin que gerou o log (Cadmus)               │
│     ├─ Ferramenta específica (vector_field)             │
│     └─ JSON completo (para debug)                       │
└─────────────────────────────────────────────────────────┘
```

---

## 🧠 Resumo Executivo (Diagrama Mental)

```
LOGCAT = Máquina de Organizar Cadernos Gigantes

Entrada (Input):
  └─ Arquivo .jsonl com 1 milhão de linhas de log

Processamento (Processing):
  ├─ SessionManager: "Qual sessão você quer? Segunda ou Terça?"
  ├─ LogLoader: "Vou ler linha por linha sem travar"
  ├─ LogEntry: "Vou transformar JSON em objeto Python"
  ├─ FilterEngine: "Você quer só ERRORs? OK, filtrando..."
  └─ TableModel: "Vou mostrar como tabela no Excel"

Saída (Output):
  └─ Tabela bonita e colorida na tela
```

---

## 🎓 As 4 Regras Ouro do Logcat

### Regra 1: **Cada arquivo é uma sessão**
Não misture logs de segunda com logs de terça. São **completamente separados**.

### Regra 2: **Cada linha é um JSON independente**
Não precisa ler tudo de uma vez. Você lê **linha por linha** (como um livro).

### Regra 3: **Filtros são não-destrutivos**
Quando você filtra, os logs originais **não são deletados**. É como botar um óculos que deixa só vermelho aparecer.

### Regra 4: **Tudo é thread-safe**
LogFileWatcher roda em **outra thread** para não travar a UI. Usa signals (como um "altofalante") para avisar.

---

## 🔴 Erros Comuns e Como Evitar

### ❌ ERRO 1: "Logcat trava quando arquivo é grande"

**Causa:** Alguém tentou carregar arquivo de 1 GB inteiro na memória.

**Solução:** Use `LogLoader.load_incremental()` em vez de `readlines()`.

```python
# ❌ ERRADO
with open(file) as f:
    lines = f.readlines()  # Trava com arquivo grande!

# ✅ CORRETO
loader = LogLoader(file)
for entry in loader.load_incremental():
    # Processa uma de cada vez
    pass
```

### ❌ ERRO 2: "Filtro não funciona"

**Causa:** Filtro aplicado ao all_entries, mas TableModel não atualizado.

**Solução:**
```python
# ✅ CORRETO
filtered = self.filter_engine.apply(self.all_entries)
self.table_model.set_entries(filtered)  # Atualizar modelo!
self.table_view.update()  # Redesenhar tabela!
```

### ❌ ERRO 3: "Janela desaparece depois de alguns segundos"

**Causa:** Referência ao diálogo foi deletada (garbage collection).

**Solução:**
```python
# Em logcat_plugin.py
def run(iface):
    dlg = LogcatDialog(iface.mainWindow())
    dlg.setModal(False)
    dlg.show()
    return dlg  # ✅ ESSENCIAL: manter referência viva!
```

---

## 🎯 Conclusão

**Logcat é um exemplo PERFEITO de boa arquitetura:**

1. ✅ **Separação de responsabilidades** (cada classe faz UMA coisa)
2. ✅ **Padrão Model-View** (dados separados da interface)
3. ✅ **Eficiência** (não carrega tudo na memória)
4. ✅ **Thread-safe** (múltiplas threads trabalhando juntas)
5. ✅ **Fácil de manter** (se um arquivo muda, outros não afetam)

---

## 📚 Próximos Passos para Aprender

Se você quer entender mais:

1. Leia `core/model/log_entry.py` (entender a estrutura de dados)
2. Leia `core/io/log_loader.py` (entender leitura eficiente)
3. Leia `core/filter/log_filter_engine.py` (entender filtros)
4. Leia `ui/log_table_model.py` (entender como converter dados em UI)
5. Leia `ui/logcat_dialog.py` (entender como tudo se conecta)

**Dica:** Leia nessa ordem! Começa pelo simples (dados) e vai pro complexo (UI).

---

**Espero ter deixado claro! Se ainda tem dúvidas, é porque meu texto foi ruim (desculpa!).** 😊

Agora você pode dizer com confiança: **"Eu entendo como o Logcat funciona!"** 🚀
