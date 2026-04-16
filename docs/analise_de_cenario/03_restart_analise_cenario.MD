# Análise de Cenário – Salvar, Fechar e Reabrir Projeto

**Visão Geral**

A ferramenta Restart QGIS automatiza o ciclo salvar-fechar-reabrir do projeto via script `.bat` temporário (Windows) ou equivalente (Linux/macOS). Fluxo sequencial: valida estado do projeto (salvo/não salvo), solicita caminho se necessário, grava alterações, cria script de restart, conecta callback `aboutToQuit`, fecha QGIS. Script executa com delay (PING 2 segundos) para evitar race condition entre shutdown e restart. Separação de responsabilidades: `ProjectUtils` valida projeto, `_RestartExecutor` gerencia script, `QgisMessageUtil` cuida de UI.

**Objetivo**

Permitir reinicialização rápida do QGIS sem perder alterações, útil em workflows que requerem reload de plugins/configurações ou reset de estado de sessão. Evitar necessidade de fechar manualmente → salvar → reabrir manualmente → reloading de camadas.

**Fluxo resumido**

- Entrada: usuário clica Menu → Cadmus → Salvar, Fechar e Reabrir Projeto.
- Validação 1: `QgsProject.instance().fileName()` verifica se projeto foi salvo.
  - Se **não salvo**: dialog "Deseja salvar agora?" → `getSaveFileName()` → `project.write(save_path)`.
  - Se **cancelado**: retorna sem fazer nada.
- Validação 2 (sempre): `project.write(project_path)` grava alterações atuais.
- Criação de script: `_RestartExecutor.create_restart_script(project_path)` gera `.bat` temporário com:
  ```bat
  @echo off
  PING 127.0.0.1 -n 2 >NUL
  start "" "C:\path\to\qgis.exe" "C:\path\to\project.qgz"
  ```
- Execução: `_RestartExecutor.execute_restart(bat_path)` conecta callback `app.aboutToQuit.connect(_run_script)`.
- Encerramento: `iface.mainWindow().close()` inicia shutdown; callback executa script; novo QGIS abre com projeto.
- Feedback: message bar "QGIS será reiniciado em alguns segundos..." (duration=2s).

**Cenários de Uso (exemplos)**

- Plugin carregado, precisa recarregar: usuario muda código em plugin → clica Restart → QGIS reabra e recarregue.
- Muitas camadas abertas, sessão "suja": usuário clica Restart → força reload de todas as camadas (limpa cache).
- Erro de estado: alguns plugins em estado inconsistente → Restart limpa memória e ressincrona.
- Teste de salvar projeto: usuário quer garantir que mudanças foram persistidas → Restart e verifica.
- Backup do projeto antes de operação arriscada: usuário clica Restart (força save) → abre com backup implícito.

**Operações envolvidas**

- `QgsProject.instance().fileName()`: obtém caminho atual do projeto.
- `project.write(path)`: escreve projeto em arquivo .qgz (atualiza timestamp).
- `QCoreApplication.applicationFilePath()`: obtém executável do QGIS (ex: `qgis.exe`).
- `subprocess.Popen(bat_path, shell=True)`: executa script `.bat` em shell.
- `QCoreApplication.instance().aboutToQuit.connect(callback)`: registra callback no sinal de shutdown.
- `iface.mainWindow().close()`: inicia graceful shutdown do QGIS.

**Impactos nos dados**

- Preservado: arquivo `.qgz` (escrito com `project.write()`), camadas, atributos, geometrias.
- Alterado: timestamp do arquivo `.qgz` (updated), estado de sessão (reset ao reabrir).
- Criado: arquivo `.bat` temporário em `%TEMP%\restart_qgis.bat` (deletado após execução).
- Não alterado: dados de camadas (alterações em edit buffer descarregadas se não commitadas antes de close).

**Riscos e controles**

- **Alterações não commitadas**: usuário esquece de salvar camada em edição antes de clicker Restart → alterações perdidas. Controle: UI avisa "Salvar projeto?" antes de close; se há edit buffers abertos, `project.write()` não salva geometrias.
- **Caminho do executável não encontrado**: em ambientes portáveis ou instalação customizada, `QCoreApplication.applicationFilePath()` pode retornar string vazia. Controle: validação `if exe and os.path.exists(exe)` com fallback a error message.
- **Script `.bat` não criado**: permissão negada em `%TEMP%` ou espaço em disco. Controle: `try/except` com logging detalhado.
- **Race condition**: QGIS fecha antes do script executar. Controle: `PING 127.0.0.1 -n 2` cria delay de 2 segundos.
- **Projeto com espaços no caminho**: script `.bat` pode quebrar. Controle: paths envolvidos em `"quotes"`.
- **Windows Defender/Antivírus**: pode bloquear execução de `.bat` temporário. Controle: script é simples e local; confiar em whitelist do antivírus.
- **Múltiplas instâncias**: se 2 QGIS rodam, segundo Restart pode interferir. Controle: usar nome único para `.bat` (ex: `restart_qgis_{random_id}.bat`).

**Observações sobre classes-chave**

- `_RestartExecutor`: classe utilitária com 3 métodos estáticos (no state).
  - `get_qgis_executable()`: retorna caminho ou None; logging em cada cenário.
  - `create_restart_script()`: escreve `.bat` em `%TEMP%`; retorna path ou None.
  - `execute_restart()`: agenda callback via `aboutToQuit.connect()`; retorna void.
- `QgsProject.instance()`: singleton; sempre retorna mesma instância.
- `QgisMessageUtil.confirm()`, `.bar_warning()`, `.bar_info()`: wrappers de UI para exibir mensagens.
- `LogUtilsNew`: logging estruturado com `code=` para rastreamento (ex: `code="RESTART_NO_EXEC"`).
- `ProjectUtils`: classe reservada (não usada aqui, mencionada em docstring para ref futura).

**Fluxo de erros**

1. Nenhum QGIS executável encontrado
   → `create_restart_script()` retorna None
   → `modal_error()` exibido: "Não foi possível encontrar o executável do QGIS"
   → Função retorna sem fechar QGIS

2. Projeto não salvo + usuário clica "Não"
   → `bar_warning()`: "Sem salvar o projeto..."
   → Função retorna sem fazer nada

3. Erro ao salvar projeto
   → `project.write()` lança exceção
   → `except` captura, logs erro, `modal_error()` exibido
   → Função retorna sem fechar QGIS

4. Falha ao criar script
   → `open(bat_path, "w")` lança exceção
   → `except` captura, `create_restart_script()` retorna None
   → `modal_error()` exibido (cenário 1)

5. Sucesso: tudo OK
   → `about_to_quit` callback agendado
   → `iface.mainWindow().close()` executa
   → Callback executa `.bat`
   → Novo QGIS abre em 2+ segundos

**Evoluções recomendadas**

- Suporte multiplataforma: detectar SO e gerar script `.sh` (Linux) ou AppleScript (macOS) em vez de `.bat` (Windows).
- Preservar estado de edição: se camada está em edição, fazer `layer.commitChanges()` antes de close (evitar perda de dados).
- Opção de backup: oferecer checkbox "Criar backup antes de restart" → duplicar `.qgz` com timestamp.
- Delay configurável: permitir usuário ajustar PING delay (default 2s, custom range 0-10s).
- Plugin reloader: integrar com `importlib.reload()` para carregar plugins após restart sem fechar QGIS (apenas se possível).
- Log de sessions: salvar lista de últimos 10 Restarts com timestamp/projeto para auditoria.
- Sincronização de plugins: detectar `.py` modificados em pasta plugins e sugerir reload automático.

**Conclusão**

Ferramenta essencial para development/testing de plugins e gerenciamento de estado de sessão. Fluxo seguro com múltiplas validações e callbacks bem sincronizados. Suporta apenas Windows (`.bat`); recomendado estender para Linux/macOS. Garantir que alterações em edit buffers sejam commitadas antes de Restart ou implementar auto-commit/discard logic para evitar perda de dados.
