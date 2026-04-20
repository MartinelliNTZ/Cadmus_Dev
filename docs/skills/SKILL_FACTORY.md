---
name: skill-factory
description: >
  Documentador automático de sistemas. Use esta skill quando o usuário disser
  "gere uma skill para X", "documente o sistema Y", "crie a skill de Z" ou
  qualquer variante. A skill analisa o sistema descrito, extrai o padrão
  reutilizável e ESCREVE O ARQUIVO .md em docs/skills/ sem esperar confirmação.
  Nunca exibe a skill no chat — sempre grava o arquivo diretamente.
---

# SKILL_FACTORY

## Missão

Receber o nome de um sistema → analisar → gerar e **gravar** a skill em `docs/skills/<nome-do-sistema>.md`.

A IA não exibe a skill no chat. Ela escreve o arquivo. Ponto.

---

## Protocolo de execução

Quando o usuário disser `"gere uma skill para [SISTEMA]"`:

### 1. Coletar contexto (somente se ausente)

Se o usuário não descreveu o sistema, faça **uma única pergunta**:

> "Me descreve o que o [SISTEMA] faz: entradas, saídas e regras principais."

Se o sistema já foi descrito na conversa, **não pergunte nada** — vá direto para o passo 2.

---

### 2. Analisar internamente (sem exibir no chat)

Execute mentalmente, **sem mostrar ao usuário**:

```
CORE:        O que o sistema realmente faz (verbo + objeto)
ENTRADAS:    O que ele recebe
SAÍDAS:      O que ele produz
REGRAS:      O que ele sempre faz / nunca faz
CONTEXTO:    Onde/quando é usado
DEPENDÊNCIAS: Outros sistemas que ele usa ou que dependem dele
```

---

### 3. Gravar o arquivo

**Ação obrigatória:** usar a ferramenta de criação de arquivo para gravar em:

```
docs/skills/<nome-do-sistema-em-kebab-case>.md
```

Usar o template abaixo. Preencher **todos os campos** com base na análise.  
Campos desconhecidos → marcar como `[A DEFINIR]`.

---

## Template obrigatório da skill gerada

```markdown
---
name: <nome-do-sistema>
description: >
  <Uma frase: o que é, quando usar. Ser direto e "pushy" para garantir trigger correto.>
---

# <Nome do Sistema>

## O que é

<Descrição em 2–4 frases. O que resolve, para quem, em qual contexto.>

## Entradas

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| ...   | ...  | Sim/Não     | ...       |

## Saídas

| Campo | Tipo | Descrição |
|-------|------|-----------|
| ...   | ...  | ...       |

## Fluxo de execução

1. <Passo 1>
2. <Passo 2>
3. <Passo 3>
...

## Regras

**Sempre:**
- ...

**Nunca:**
- ...

## Casos de uso

- Quando o usuário fizer X → o sistema faz Y
- Quando o estado for Z → o sistema faz W

## Dependências

- <Sistema ou módulo que este sistema usa>
- <Sistema que depende deste>

## Exemplo

**Entrada:**
```
<exemplo real de entrada>
```

**Saída esperada:**
```
<exemplo real de saída>
```

## Limitações conhecidas

- ...

## Histórico de mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| <hoje> | 1.0.0 | Criação inicial via SKILL_FACTORY |
```

---

## 4. Confirmar ao usuário

Após gravar o arquivo, exibir **apenas**:

```
✅ Skill gerada: docs/skills/<nome>.md
```

Nada mais. Sem explicações. Sem repetir o conteúdo da skill no chat.

---

## Regras absolutas

| Regra | Detalhe |
|-------|---------|
| ❌ Nunca exibir a skill no chat | Sempre gravar o arquivo |
| ❌ Nunca pedir confirmação para gravar | Gravar diretamente |
| ❌ Nunca inventar comportamentos do sistema | Marcar como `[A DEFINIR]` |
| ❌ Nunca criar campos extras não previstos no template | Seguir o template exatamente |
| ✅ Sempre usar kebab-case no nome do arquivo | `sistema-de-preferencias.md` |
| ✅ Sempre preencher a data real em Histórico de mudanças | |
| ✅ Sempre ler `docs/skills/PLUGIN_CONTRACT.md` se existir | Para identificar contratos do sistema |

---

## Quando atualizar uma skill existente

Se o arquivo já existe em `docs/skills/`, **não sobrescrever** — perguntar:

> "Já existe uma skill para esse sistema. Deseja atualizar ou criar uma versão nova?"

- **Atualizar:** editar o arquivo existente e incrementar a versão
- **Nova versão:** criar `<nome>-v2.md`

---

## Compatibilidade de modelos

Esta skill foi escrita para funcionar com:
- Claude (Sonnet / Opus)
- GPT-4.1
- Minimax M2.5
- Qualquer modelo com acesso a ferramenta de escrita de arquivo

**Para garantir compatibilidade:**
- Instruções são imperativas e diretas ("gravar o arquivo", não "você pode gravar")
- Nenhuma etapa depende de memória entre sessões
- O template é autoexplicativo — o modelo preenche sem precisar inferir estrutura