---
name: skill-factory
description: >
  Documentador automático de sistemas. Use esta skill quando o usuário disser
  "gere uma skill para X", "documente o sistema Y", "crie a skill de Z" ou
  qualquer variante. A skill lê os arquivos do projeto, rastreia dependências,
  e ESCREVE O ARQUIVO .md em docs/skills/ com profundidade técnica real.
  Nunca exibe a skill no chat — sempre grava o arquivo diretamente.
  Nunca gera skill rasa — sempre lê o código antes de documentar.
---

# SKILL_FACTORY

## Missão

Receber o nome de um sistema → **ler o código real** → rastrear dependências → gerar e **gravar** a skill completa em `docs/skills/<nome>.md`.

A IA não inventa comportamentos. Ela lê o código. Documenta o que existe. Grava o arquivo.

---

## Protocolo de execução

### PASSO 1 — Localizar o arquivo principal

Buscar no projeto o arquivo central do sistema informado pelo usuário.

```
Padrões de busca (nesta ordem):
1. plugins/<NomeDoSistema>.py
2. core/services/<NomeDoSistema>.py
3. core/config/<NomeDoSistema>.py
4. utils/<NomeDoSistema>.py
5. Busca recursiva por nome similar
```

Se não encontrar → perguntar ao usuário o caminho exato. Nada mais.

---

### PASSO 2 — Rastrear dependências (OBRIGATÓRIO)

Após encontrar o arquivo principal, **ler todos os imports e identificar classes relacionadas**.

**Protocolo de rastreamento:**

```
Para cada import encontrado no arquivo principal:
  1. Verificar se é um módulo interno do projeto (não stdlib, não third-party)
  2. Se for interno → ler o arquivo
  3. Dentro desse arquivo → repetir o processo (1 nível de profundidade)

Limite: máximo 2 níveis de profundidade
Ignorar: os, sys, pathlib, typing, abc, datetime, json, re, threading
```

**Registrar internamente:**
```
ARQUIVO PRINCIPAL: <path>
DEPENDÊNCIAS LIDAS:
  - <path> → responsabilidade: <uma linha>
IGNORADOS: <libs externas/stdlib>
```

Não exibir isso ao usuário. Usar apenas para construir a skill.

---

### PASSO 3 — Extrair o conhecimento real

Com todos os arquivos lidos, extrair:

```
CORE:
  - O que o sistema realmente faz (baseado no código, não no nome)
  - Ponto de entrada principal (método/função)
  - Fluxo real de execução (ordem dos métodos chamados)

ENTRADAS:
  - Parâmetros reais dos métodos principais (com tipos reais do código)
  - Configurações lidas (preferências, config files)

SAÍDAS:
  - O que é retornado / gerado / salvo / emitido
  - Arquivos criados, camadas, sinais Qt, retornos

PADRÕES:
  - Padrões de uso correto encontrados no código
  - Anti-patterns que o código explicitamente evita
  - Convenções da codebase

EXEMPLOS REAIS:
  - Extrair exemplos de uso do próprio código (testes, docstrings, usages)
  - Se não houver, construir exemplo fiel ao padrão real

LIMITAÇÕES:
  - TODOs encontrados no código
  - Comentários de limitação
  - Comportamentos condicionais que podem falhar
```

---

### PASSO 4 — Gravar o arquivo

**Ação obrigatória:** gravar em `docs/skills/<nome-em-kebab-case>.md` usando o template abaixo.

**Regra de qualidade:** a skill gerada deve ter o mesmo nível de detalhe da skill de referência em `docs/skills/LogUtils.md` (se existir).

---

## Template obrigatório

```markdown
---
name: <nome-do-sistema>
description: >
  <Uma frase direta: o que é e quando usar.
  Ser "pushy" — mencionar contextos específicos para garantir trigger correto.>
---

# <Nome do Sistema>

## Resumo Executivo

**<NomeDoSistema>** é um sistema que:
- <bullet 1: responsabilidade principal>
- <bullet 2: integração chave>
- <bullet 3: contexto de uso>

---

## Objetivo

<2–3 frases descrevendo o problema que resolve e para quem.>

---

## Entradas

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| <campo real do código> | <tipo real> | Sim/Não | <descrição real> |

---

## Saídas

| Campo | Tipo | Descrição |
|-------|------|-----------|
| <saída real> | <tipo real> | <descrição real> |

---

## Processamento

### Fase 1 — <Nome da fase real>

<Descrição do que acontece nesta fase>

```python
# Exemplo real extraído do código ou fiel ao padrão
<código>
```

### Fase 2 — <Nome da fase real>

<Continuar para todas as fases reais do sistema>

---

## Regras

### ✅ Sempre:
- <regra extraída do código — não inventada>

### ❌ Nunca:
- <anti-pattern encontrado no código ou comentários>

---

## Padrões de Uso

### Padrão 1 — <Nome do padrão principal>

```python
# Contexto: <quando usar este padrão>
<código real e completo, não placeholder>
```

### Padrão 2 — <Nome do padrão alternativo>

```python
<código real>
```

---

## Casos de Uso

- Quando <situação real> → o sistema faz <ação real>
- Quando <situação real> → o sistema faz <ação real>

---

## Dependências

| Módulo | Caminho | Responsabilidade |
|--------|---------|-----------------|
| <NomeClasse> | <path/real.py> | <uma linha> |

---

## Exemplos Completos

### Exemplo 1 — <Caso de uso principal>

```python
# Contexto: <onde este código viveria no projeto>
<código completo e funcional>
```

### Exemplo 2 — <Edge case ou uso avançado>

```python
<código completo>
```

---

## Limitações

- <limitação real encontrada no código ou TODOs>

---

## Validação

| Critério | Status |
|----------|--------|
| Reutilizável? | ✅/⚠️ <justificativa> |
| Clara? | ✅/⚠️ <justificativa> |
| Independente de contexto oculto? | ✅/⚠️ <justificativa> |

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| <data real> | 1.0.0 | Criação via SKILL_FACTORY — lidos: <lista de arquivos lidos> |
```

---

## PASSO 5 — Confirmar ao usuário

Após gravar, exibir **apenas**:

```
✅ Skill gerada: docs/skills/<nome>.md
📂 Arquivos lidos: <lista dos arquivos rastreados>
```

Nada mais.

---

## Regras absolutas

| Regra | Detalhe |
|-------|---------|
| ❌ Nunca inventar comportamento | Se não está no código, não está na skill |
| ❌ Nunca gerar skill sem ler o código | Ler sempre antes de documentar |
| ❌ Nunca exibir a skill no chat | Sempre gravar o arquivo |
| ❌ Nunca pular o rastreamento de dependências | Sempre ler os imports internos |
| ❌ Nunca usar placeholders genéricos | Todo campo usa dado real do código |
| ✅ Sempre incluir código real nos exemplos | Não usar `# faz algo...` |
| ✅ Sempre registrar arquivos lidos no Histórico | Para rastreabilidade |
| ✅ Sempre usar kebab-case no nome do arquivo | `log-utils.md`, `drone-coordinates.md` |
| ✅ Sempre ler `docs/skills/PLUGIN_CONTRACT.md` se existir | Para contratos do sistema |

---

## Quando atualizar uma skill existente

Se o arquivo já existe em `docs/skills/`, perguntar:

```
✅ Skill existente encontrada: docs/skills/<nome>.md
Deseja: [A] Atualizar versão atual  [B] Criar nova versão (<nome>-v2.md)
```

---

## Critério de qualidade mínima

Antes de gravar, verificar internamente:

```
[ ] A skill tem exemplos de código reais (não placeholders)?
[ ] A skill lista dependências com caminho real?
[ ] As regras foram extraídas do código (não inventadas)?
[ ] As entradas e saídas têm tipos reais?
[ ] O fluxo de processamento reflete a ordem real dos métodos?
```

Se qualquer item for ❌ → reler os arquivos e corrigir antes de gravar.

---

## 📏 REGRAS GLOBAIS

* Respostas curtas e estruturadas
* Sem explicações desnecessárias
* Sem “pensamento em voz alta”
* Foco total na etapa atual
* Não invente regras
* Não pule etapas
* Alucine menos
* Não invente classes.
* Leia sempre docs/skills/PLUGIN_CONTRACT.md para entender o contrato exclusivo do plugin de implementação.
* Sempre que identificar um contrato, incremente em docs/skills/PLUGIN_CONTRACT.md, seguindo o formato:
* Não é necessario criar uma skill para cada contrato identificado, mas é obrigatório registrar o contrato em docs/skills/PLUGIN_CONTRACT.md, mesmo que seja apenas um nome e descrição breve.
* Não é necessario solicitar confirmação do usuário para registrar um contrato, nem para criar o .md da skill solicitada. 