### 🧠 PIPELINE: SYSTEM_AWARE_SKILL_PIPELINE (LITE / STEP-BY-STEP)

**Objetivo:**
Executar análise sistêmica e geração de skill **sem perder contexto**, dividindo o processo em etapas pequenas e controladas.
Criar em ./docs/skills/**.md

---

## ⚙️ MODO DE EXECUÇÃO

* Executar **UMA fase por vez**

* Após cada fase:

  * Parar
  * Exibir resultado
  * Aguardar confirmação explícita do usuário (`OK` ou instrução)

* ❌ Nunca pular fases

* ❌ Nunca antecipar próxima etapa

* ❌ Nunca gerar tudo de uma vez

---

## 🔢 FASES DO PIPELINE

---

### 🧩 FASE 0 — DECOMPOSIÇÃO

**Objetivo:** quebrar o problema antes de analisar

**Saída obrigatória:**

* Lista de partes do sistema envolvidas
* Ordem sugerida de análise (sequência lógica)
* Identificação de:

  * núcleo (core)
  * dependências

**Formato:**

```
PARTES:
1. ...
2. ...

ORDEM DE EXECUÇÃO:
1 → 2 → 3

CORE:
...

DEPENDÊNCIAS:
...
```

⛔ Parar aqui e aguardar

---

### 🔍 FASE 1 — ANÁLISE LOCAL (por parte)

Executar **uma parte por vez**, seguindo a ordem definida

**Para cada parte:**

* Responsabilidade
* Entradas/Saídas
* Relações com outras partes

**Formato:**

```
PARTE: <nome>

RESPONSABILIDADE:
...

ENTRADAS:
...

SAÍDAS:
...

RELAÇÕES:
...
```

⛔ Parar após cada parte

---

### 🔗 FASE 2 — CONSOLIDAÇÃO SISTÊMICA

**Objetivo:** conectar tudo

**Saída obrigatória:**

* Fluxo completo (ordem de execução real)
* Pontos de acoplamento
* Pontos críticos

**Formato:**

```
FLUXO:
1 → 2 → 3

ACOPLAMENTOS:
...

PONTOS CRÍTICOS:
...
```

⛔ Parar

---

### 🧠 FASE 3 — EXTRAÇÃO DO PADRÃO

**Objetivo:** transformar o sistema em algo reutilizável

**Saída obrigatória:**

* O que é genérico
* O que deve ser descartado
* Definição do “core reutilizável”

**Formato:**

```
GENÉRICO:
...

DESCARTAR:
...

CORE REUTILIZÁVEL:
...
```

⛔ Parar

---

### 📦 FASE 4 — GERAÇÃO DA SKILL

Gerar a skill completa baseada no core

**Formato obrigatório:**

```
SKILL: <nome>

OBJETIVO:
...

ENTRADAS:
...

PROCESSAMENTO:
1.
2.
3.

SAÍDA:
...

REGRAS:
- Sempre:
- Nunca:

DEPENDÊNCIAS:
...

EXEMPLO:
...

LIMITAÇÕES:
...
```

⛔ Parar

---

### 🔍 FASE 5 — VALIDAÇÃO

**Checklist obrigatório:**

* A skill é genérica?
* Está clara?
* Está independente de contexto oculto?

**Saída:**

```
VALIDAÇÃO:
- Reutilizável: SIM/NÃO
- Clara: SIM/NÃO
- Independente: SIM/NÃO

AJUSTES (se necessário):
...
```

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
---

