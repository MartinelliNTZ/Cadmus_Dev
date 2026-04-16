# Análise de Cenário – Coordenadas por Clique

**Visão Geral**

A ferramenta fornece informações geoespaciais a partir de um clique no mapa: coordenadas (WGS84/UTM), formatações (decimal/DMS), altimetria e geocodificação reversa. Opera de forma não destrutiva e usa tarefas assíncronas para consultas externas.

**Objetivo**

Permitir obtenção imediata e confiável de coordenadas e atributos descritivos de um ponto, sem alterar dados do projeto.

**Fluxo resumido**

- Captura do clique e determinação do ponto (respeitando snapping).
- Transformações: projeção para WGS84 e cálculo UTM conforme zona.
- Consultas assíncronas: altimetria (SRTM) e geocodificação reversa (opcionais).
- Atualização da UI com resultados; tasks anteriores são canceladas em cliques subsequentes.

**Cenários de Uso (exemplos)**

- Clique simples: exibe coordenadas e informações básicas.
- Cliques sucessivos: mantém diálogo aberto e atualiza apenas com o último resultado.
- Geocodificação/altimetria: resultados exibidos quando disponíveis; mensagens de erro em falhas.

**Tipos de dados**

- Aceita qualquer CRS do projeto; converte internamente para WGS84/UTM quando necessário.

**Impactos nos dados**

- Preservado: nenhum dado do projeto é modificado.
- Alterado: apenas exibição temporária e cópia para área de transferência (quando usada).

**Riscos e controles**

- Bloqueio da UI: mitigado com tarefas assíncronas (`QgsTask`).
- Concorrência de tasks: cancelamento automático de tarefas anteriores.
- Falha em APIs: tratamento de erros e mensagens amigáveis.
- Uso excessivo de requisições: execução sob demanda do usuário.

**Observações sobre classes-chave**

- Verificar cancelamento e limpeza de tarefas em `Task`-based implementations para evitar atualizações de UI após cancelamento.
- Conferir precisão de reprojeção e conversão UTM para pontos em zonas limites.

**Evoluções recomendadas**

- Cache local para resultados de geocodificação.
- Suporte a múltiplos provedores de altimetria.
- Opção de exportar histórico de pontos clicados.

**Conclusão**

Ferramenta enxuta e responsiva; mantém integridade dos dados do projeto e fornece informações relevantes de forma rápida. Focar em robustez do cancelamento de tasks e precisão de reprojeção para zonas limítrofes.
