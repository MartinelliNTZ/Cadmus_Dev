# Análise de Cenário – Converter Multipart

**Visão Geral**

A ferramenta separa geometrias multipart em feições individuais, preservando atributos e CRS. Pode operar sobre toda a camada ou apenas sobre feições selecionadas.

**Objetivo**

Transformar feições multipart em feições simples independentes, sem perda de atributos e respeitando o fluxo de edição do QGIS.

**Fluxo resumido**

- Entrada: camada vetorial (qualquer tipo que suporte multipart).
- Identificação: detectar feições multipart.
- Operação: dividir cada multipart em feições separadas, preservando campos.
- Finalização: manter edição aberta ou solicitar salvamento conforme estado inicial da camada.

**Cenários de Uso (exemplos)**

- Sem seleção: processa toda a camada e separa feições multipart.
- Com seleção: processa apenas feições selecionadas.
- Camada em edição: alterações ficam pendentes para revisão.
- Camada fora de edição: ferramenta inicia edição e solicita salvar/descartar ao final.

**Tipos de geometria**

- Suporta pontos, linhas e polígonos multipart onde aplicável.

**Impactos nos dados**

- Preservado: atributos, CRS e estrutura de campos.
- Alterado: número de feições e organização geométrica; pode aumentar significativamente o total de feições.

**Riscos e controles**

- Alteração indesejada em larga escala: confirmar ação antes de processar toda a camada.
- Processamento pesado: permitir cancelamento e apresentar aviso de tempo/impacto.
- Perda de dados: manter alterações só após confirmação do usuário.

**Observações sobre classes-chave**

- Confirmar que a implementação respeita o estado de edição da camada e que mantém o esquema de atributos intacto.

**Evoluções recomendadas**

- Execução em background para grandes camadas.
- Progresso visual e relatório de feições afetadas.

**Conclusão**

Ferramenta essencial para limpeza de geometrias multipart; design alinhado ao comportamento esperado do QGIS. Garantir controles de confirmação e feedback de progresso para grandes volumes.
