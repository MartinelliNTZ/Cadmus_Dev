# 🧠 SKILL: Sistema de Comunicação — responsabilidades e padrões

## 📋 Objetivo desta Skill

Reestruturar e documentar, com clareza de responsabilidades, quais mecanismos de comunicação devem ser usados em cada cenário da base Cadmus: logs (dev), sinais (inter-componentes), mensagens ao usuário (UI) e quando usar IPC/fora do processo. A meta é evitar ambiguidade e padronizar comportamentos.

---

## 🔑 Resumo curto

- **Log (`LogUtils`)**: destinado ao desenvolvimento, auditoria e investigação. Todas as classes podem ter um logger; **`tool_key` é exclusivo para classes que representam ferramentas** (features/plugins). Classes que não são ferramentas NÃO devem declarar `TOOL_KEY` internamente — quando precisarem logar em contexto de uma ferramenta, devem receber `tool_key` como parâmetro na assinatura do método ou receber um `logger` pré-injetado.
- **SignalManager / PluginSignalHub / PyQtSignalManager**: meio para comunicação entre ferramentas e subsistemas complexos do plugin — usar com cautela; reservado para eventos de ciclo de vida, coordenação de UI e notificações internas entre componentes desacoplados.
- **QgisMessageUtil**: único canal para mensagens dirigidas ao usuário final (message bars, modais, progressos). Nunca usar `LogUtils` sozinho para UX.
- **IPC / Arquivo / Sockets**: apenas para comunicação entre processos ou scripts externos; não substituir sinais locais.

---

## 📚 Princípios e responsabilidades

- **Seja explícito sobre o público-alvo da mensagem**:
    - Desenvolvedor / Operador → `LogUtils` (arquivo JSON + QGIS log para erros críticos)
    - Outro componente / ferramenta → `PluginSignalHub` (sinais PyQt via `PyQtSignalManager` listeners)
    - Usuário final (UX) → `QgisMessageUtil`

- **Separação de responsabilidades**:
    - `LogUtils`: apenas gravação observacional e diagnóstico. Não controla fluxo de aplicação.
    - `SignalManager`: coordenação e injeção de eventos (ex.: rebuilds, atualização de ações). Não deve carregar lógica de negócio pesada — apenas notificar.
    - `QgisMessageUtil`: apresentar informação ao usuário. Deve receber mensagens de componentes que já tenham logado internamente.

- **ToolKey**: somente ferramentas (os itens do plugin que representam funcionalidades acionáveis pelo usuário) devem declarar uma `TOOL_KEY` e passá-la ao criar loggers. Classes utilitárias, modelos ou helpers não devem inventariar `tool_key`.

---

## 🧭 Quando usar cada mecanismo (cenários)

- Cenário: inicialização de plugin / registro de ferramenta
    - Use: `LogUtils` (INFO/DEBUG) para auditoria; emitir `plugin_instantiated` via `PluginSignalHub` para que `PyQtSignalManager` atualize menus/toolbars; `QgisMessageUtil` apenas se houver erro que o usuário precise ver.

- Cenário: tarefa de processamento assincrona longa (ex.: processamento raster)
    - Use: `LogUtils` para eventos internos e progresso; `QgisMessageUtil.show_progress_message_bar` para feedback ao usuário (via iface); se múltiplos componentes precisarem coordenar, emitir sinais específicos (payloads pequenos) via `PluginSignalHub`.

- Cenário: erro crítico que impede operação
    - Use: `LogUtils.exception()` para registrar traceback estruturado; chamar `QgisMessageUtil.modal_error` ou `bar_critical` para notificar usuário; emitir sinal se outros subsistemas precisarem reagir (ex.: limpar estado compartilhado).

- Cenário: comunicação entre ferramentas (ex.: Tool A altera dados que Tool B consome)
    - Use: `PluginSignalHub` com payloads mínimos (ids, paths, tool_key). Evitar passar objetos Qt/Widgets. Preferir notificações tipo `data_updated` com `resource_id`.

- Cenário: integração com processos externos ou múltiplos processos
    - Use: IPC (arquivo, socket, DB) — documentar contrato de mensagem. `PluginSignalHub` NÃO atravessa processos.

---

## 🧩 Contratos e formato de mensagens

- Regras gerais de payload:
    - Payloads devem ser JSON-serializáveis (dicts com strings, números, lists, booleans).
    - Evitar referências diretas a QObjects, handlers, ou dados binários.
    - Campos recomendados: `event` (string), `tool_key` (quando aplicável), `timestamp` (ISO), `actor` (opcional), `id`/`resource`.

- Exemplo padrão de payload mínimo:

```json
{
    "event": "plugin_instantiated",
    "tool_key": "processing",
    "timestamp": "2026-06-09T12:34:56Z",
    "meta": { "user": "alice" }
}
```

---

## ✍️ Políticas de logging (LogUtils)

- Escopo: diagnóstico e auditoria.
- Quem pode ter logger: qualquer classe pode ter um logger, mas **somente classes que representam ferramentas** devem declarar `TOOL_KEY` e instanciar `LogUtils` com `tool=ToolKey.X`.
- Para utilitários e helpers: **não** declarar `TOOL_KEY`. Se o utilitário precisa registrar eventos ligados a uma ferramenta, use uma das abordagens abaixo:
    1. Receber `tool_key` como parâmetro na assinatura do método (ex.: `def process(data, *, tool_key):`) e criar `LogUtils(tool=tool_key, class_name=...)` dentro do método.
    2. Receber um `logger` já instanciado como argumento (ex.: `def process(data, logger):`) e usar este logger diretamente.
    3. Evitar definir `ToolKey` internamente em utilitários; se for imprescindível usar um valor genérico, documente explicitamente essa escolha.
- Convenção: classes que representam ferramentas públicas devem declarar `TOOL_KEY = ToolKey.X` como constante de classe.
- Exceções: sempre use `logger.exception(e, code=...)` para erros não tratados.
- Dados sensíveis: nunca logar credenciais ou PII; sanitizar antes de registrar.

---

## 🔔 SignalManager (PluginSignalHub / PyQtSignalManager)

- Propósito: servir de barramento interno para eventos entre subsistemas do plugin (menu/toolbar updates, lifecycle events, sync notifications).
- Uso restrito: deve ser tratado como recurso compartilhado com impacto em toda a aplicação — **emitir com cuidado**. Antes de adicionar um novo sinal, avaliar se não existe alternativa local (call/callback).
- Design recomendado:
    - Sinais nomeados por domínio: `plugin_instantiated`, `plugin_finished`, `data_changed`, `toolbar_category_visibility_changed`, `resource_locked`
    - Handlers devem ser idempotentes e rápidos; evitar longas tarefas no slot (delegar a thread/process worker).
    - Emitir apenas dados leves (ids, paths, enums).

---

## 🧑‍💻 QgisMessageUtil — regras UX

- Único responsável por mensagens ao usuário no QGIS.
- Padrões:
    - Mensagens informativas de rotina → `bar_info`/`bar_success` (não modal).
    - Erros críticos → `modal_error` (bloqueante) + log.
    - Perguntas → `confirm`/`ask_overwrite` (usar padrões existentes).
- Sempre logar o evento correspondente com `LogUtils` antes/ao mostrar a UI.

---

## 🧪 Testes e validação

- Unit tests:
    - Testar que emissões de sinais chegam aos listeners (usar `get_plugin_signal_hub()` isolado);
    - Testar que `LogUtils` grava eventos com `session_id` constante;
    - Testar que `QgisMessageUtil` é chamado apenas para mensagens ao usuário (mock iface em testes).

- Teste de integração:
    - Simular fluxo: plugin inicia → emit `plugin_instantiated` → `PyQtSignalManager` atualiza menu → checar que log e UI foram acionados.

---

## ⚠️ Limitações e riscos

- `PluginSignalHub` não atravessa processos. Use IPC quando houver múltiplos processos.
- Sinais podem poluir se usados indiscriminadamente; prefira contratos claros e nomes estáveis.
- Logs crescem indefinidamente — implementar `LogCleanupUtils` ou rotação se necessário.

---

## ✅ Conclusão (resumo de responsabilidades)

- `LogUtils` = desenvolvedor / auditoria (todas as classes podem usar, `tool_key` só para ferramentas).
- `PluginSignalHub` / `PyQtSignalManager` = comunicação entre ferramentas / subsistemas complexos (usar com cuidado).
- `QgisMessageUtil` = todas as mensagens ao usuário final.
- IPC/Arquivo/Sockets = apenas para comunicação entre processos.

---

Se aprovar este rework, aplico uma entrada de changelog e crio exemplos de testes unitários e um diagrama Mermaid resumo.
