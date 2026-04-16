# Sistema de Logs — Arquitetura, Funcionamento e Boas Práticas

Data: 2026/03/12

Resumo
------
Este documento descreve de forma técnica o subsistema de logging do plugin:
estrutura, formato, sincronização, rotação/limpeza, integração com o QGIS e
os mecanismos de consumo (ex.: `logcat` UI). Inclui riscos, armadilhas e
recomendações operacionais.

Componentes Principais
----------------------
- `LogUtils` (`core/config/LogUtils.py`)
  - API de logging central do plugin. Estrutura de uso:
    - `LogUtils.init(plugin_root: Path)` — inicializa sessão, cria diretório
      `log/` e define arquivo de sessão (JSON Lines).
    - Instâncias: `LogUtils(tool=..., class_name=..., level=...)` e métodos
      `debug()`, `info()`, `warning()`, `error()`, `critical()`, `exception()`.
  - Características:
    - Escreve eventos em arquivo JSONL (`json.dump(event) + '\n'`).
    - Usa `LOG_FILE_LOCK` para sincronizar escrita concorrente em múltiplas
      threads (`core/config/log_sync.py`).
    - Mantém `session_id` e `pid` em cada evento para rastreabilidade.
    - Em níveis `ERROR` e `CRITICAL`, também encaminha mensagem ao
      `QgsMessageLog` (quando disponível) para visibilidade imediata no QGIS.

- `LogCleanupUtils` (`core/config/LogCleanupUtils.py`)
  - Ferramentas utilitárias para manter o diretório de logs:
    - `keep_last_n(plugin_root, keep=10)` — mantém apenas os últimos N logs
      por data de modificação.
    - `clear_all_logs(plugin_root)` — remove todos os logs.
    - `clear_current_session(plugin_root, session_id=None)` — deleta o log
      mais recente (ou de sessão específica se fornecida).

- `log_sync.LOG_FILE_LOCK` (`core/config/log_sync.py`)
  - Lock global (`threading.Lock`) usado por `LogUtils._write_event` para
    evitar corridas entre escrita de múltiplas threads.

- `logcat` plugin (`plugins/logcat/`)
  - UI e utilitários para carregar e filtrar logs gravados (model/view).
  - Consome os arquivos JSONL gerados por `LogUtils` e exibe na interface.

Formato do Evento
-----------------
Cada linha do arquivo de log contém um JSON com campos padronizados:

- `ts`: timestamp ISO (seconds)
- `level`: DEBUG|INFO|WARNING|ERROR|CRITICAL
- `plugin`: nome do plugin
- `plugin_version`: versão
- `session_id`: UUID da sessão de log
- `pid`: processo
- `thread`: nome da thread que gerou o evento
- `tool`: componente ou ferramenta origem
- `class`: classe que emitiu o log
- `code`: código lógico (opcional)
- `msg`: mensagem legível
- `data`: dict com metadados ad-hoc (e.g., payloads, IDs)

Exemplo de linha (JSONL):
{
  "ts": "2026-03-12T14:00:00",
  "level": "ERROR",
  "plugin": "Cadmus",
  "session_id": "...",
  "thread": "Thread-1",
  "tool": "coord_click",
  "class": "CoordClickTool",
  "msg": "Erro ao criar diálogo",
  "data": {"exception": {"type":"ValueError","message":"...","traceback":"..."}}
}

Sincronização e Thread-safety
-----------------------------
- Escrita concorrente: `LogUtils._write_event` usa `LOG_FILE_LOCK`.
  - Garantia: apenas uma thread por vez escreve no arquivo de sessão.
  - Risco: lock demasiado grosso pode serializar I/O em cargas intensas —
    porém evita corrupção de JSON lines.
- Leituras (logcat): leitura de arquivos deve usar mesma convenção de
  travamento se for editar/rotacionar logs durante leitura. O plugin usa
  leitura atômica (abrir/ler) e não escreve sobre arquivos existentes.

Inicialização de Sessão
----------------------
- `LogUtils.init(plugin_root)` é chamada uma vez por processo. Ela:
  - gera `session_id` (UUID) e nome de arquivo `cadmus_<ts>_pid<pid>.log`;
  - cria diretório `log/` se necessário;
  - grava um evento inicial `LOG_START`.
- Se `init()` não for chamada, `LogUtils` cria uma sessão fallback com `Path.cwd()`.

Integração com QGIS
-------------------
- Para erros críticos a mensagem também é enviada a `QgsMessageLog.logMessage()`
  para que o usuário veja notificações no QGIS.
- `LogUtils` detecta disponibilidade do QGIS (ImportError) e funciona em modo
  “fallback” quando QGIS não está presente (útil em testes fora do QGIS).

Rotação e Limpeza de Logs
-------------------------
- Política atual: `LogCleanupUtils.keep_last_n(..., keep=10)` por padrão.
- Recomendações operacionais:
  - Agendar limpeza periódica (ex.: ao iniciar plugin) para evitar disco
    cheio em ambientes com muitas execuções.
  - Para instalações com alta frequência, considerar compactação
    incremental antes de remoção (não implementado atualmente).

Consumo / Ferramentas de Visualização (logcat)
---------------------------------------------
- O `plugins/logcat` fornece:
  - loaders (`io/log_loader.py`) que leem linhas JSON e as convertem em
    `LogEntry` objetos (ver `model/log_entry.py`).
  - UI (`ui/logcat_dialog.py`, `log_table_model.py`) para filtrar, agrupar,
    e inspecionar detalhes.
- Recomendações para `logcat`:
  - Abrir arquivo em modo leitura somente; não tentar truncar enquanto em uso.
  - Ao detectar append (tail), reabrir arquivo para evitar inconsistências.

Tratamento de Exceções e Stacktraces
-----------------------------------
- `LogUtils.exception(exc)` captura traceback completo e o coloca em
  `data['exception']` com `type`, `message` e `traceback` (string). Isso
  é essencial para análise posterior sem depender do console.

Privacidade e Dados Sensíveis
-----------------------------
- Evitar gravar PII (endereço completo, tokens, credenciais) em `data`.
- Recomenda-se redigir dados sensíveis antes de enviar aos logs ou usar
  chaves de máscara (ex.: substituir valores por `***`).

Erros e Armadilhas Comuns
-------------------------
- Escrita sem lock → arquivos JSON corrompidos (linhas incompletas). Use
  sempre `LOG_FILE_LOCK` ao escrever.
- Não inicializar `LogUtils` → arquivos com caminho errôneo; garantir
  `init()` em startup do plugin.
- Rotacionar logs enquanto `LogUtils` escreve → pode causar perda de eventos;
  usar estratégias seguras (move/rename atômico) se necessário.
- Leitura concorrente sem consistência → `logcat` deve tolerar linhas inválidas
  (ignorar ou logar parsing error) em vez de crash.

Boas Práticas de Uso
--------------------
- Use níveis de log apropriados: `debug` para desenvolvimento, `info` para
  eventos relevantes, `warning` para condições recuperáveis, `error`/`critical`
  para falhas.
- Padronizar `code` para eventos recorrentes (ex.: `GEOLOOKUP_TIMEOUT`) para
  facilitar análise automatizada.
- Registrar contexto mínimo necessário (IDs, tool_key, lat/lon reduzido),
  evitando payloads massivos.

Exemplo rápido de uso
---------------------
```python
from core.config.LogUtils import LogUtils

# Em init do plugin
LogUtils.init(plugin_root)

# Em classes
logger = LogUtils(tool="coord_click", class_name="CoordClickTool")
logger.debug("Creating dialog")
try:
    do_something()
except Exception as exc:
    logger.exception(exc, code="DIALOG_CREATE_FAIL")
```

Conclusão
---------
O subsistema de logs foi desenhado para ser leve, thread-safe e compatível
com consumo via UI (`logcat`). Seguir as regras de lock, inicialização e
privacidade garante logs úteis e robustos para depuração e operação.
