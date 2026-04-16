# Análise de Cenário – Copiar Atributos

**Visão Geral**

A ferramenta copia campos de uma camada origem para uma camada destino, oferecendo controle sobre quais campos copiar, resolução de conflitos e integração com o fluxo de edição do QGIS.

**Objetivo**

Permitir transferência segura de atributos entre camadas similares, preservando geometrias e CRS, e evitando operações irreversíveis sem confirmação do usuário.

**Fluxo resumido**

- Entrada: seleção de camada origem e destino na UI.
- Opções: copiar todos os atributos ou selecionar subset de campos.
- Conflitos: resolução interativa campo a campo quando necessário.
- Edição: respeita estado de edição da camada destino (mantém edição aberta ou solicita salvar/descartar).

**Cenários de Uso (exemplos)**

- Copiar subset de campos: usuário seleciona campos específicos e executa cópia.
- Copiar todos os campos: opção "Usar todos os atributos" ativa.
- Conflito de nomes: usuário decide sobrescrever/renomear/pular campo.

**Tipos de dados**

- Funciona com camadas vetoriais compatíveis em termos de atributos (campos compatíveis por tipo).

**Impactos nos dados**

- Preservado: geometrias, CRS, campos existentes não modificados (a menos que o usuário opte sobrescrever).
- Alterado: estrutura de campos da camada destino e valores dos campos copiados.

**Riscos e controles**

- Sobrescrita de campos: mitigado com confirmação interativa.
- Alterações acidentais: mantêm-se não salvas até confirmação do usuário.
- Erro de seleção: UI com feedback e possibilidade de reverter antes do salvamento.

**Observações sobre classes-chave**

- Validar compatibilidade de tipos entre campos origem e destino antes da cópia.
- Garantir que o processo respeite locks e estado de edição da camada destino.

**Evoluções recomendadas**

- Pré-visualização das alterações antes de aplicar.
- Execução em background para grandes volumes de feições.
- Relatório final com resumo de campos copiados e conflitos resolvidos.

**Conclusão**

Ferramenta prática e controlada para transferências de atributos; foco em validação de tipos e feedback ao usuário melhora segurança do processo.
