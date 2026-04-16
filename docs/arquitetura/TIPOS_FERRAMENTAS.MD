# Tipos de Ferramentas — Contratos Técnicos e Padrões

Data: 2026/03/12

## Ferramentas Instantâneas
- Executam automaticamente ao serem acionadas
- Exibem mensagens de confirmação/sucesso/erro/info conforme cenário
- Possuem análise de cenário (docs/analisecenario)
- Não abrem janela de configuração
- Entrada: contexto do projeto ou camada
- Saída: alteração direta ou mensagem
- Persistem preferências mínimas (se aplicável)
- Devem usar QgisMessageUtil para feedback
- Não devem acessar widgets/core QGIS diretamente
- Devem delegar operações para ProjectUtils
- Risco: manipulação direta de projeto/camadas

## Ferramentas Instantâneas com Janela de Resultados
- Executam automaticamente
- Exibem mensagens de confirmação/sucesso/erro/info
- Possuem análise de cenário
- Abrem janela/dialog com resultado (WidgetFactory)
- Entrada: contexto do projeto/canvas
- Saída: janela de resultado (ex.: diálogo)
- Persistem preferências de exibição
- Devem implementar método run padrão para abrir diálogo
- Devem usar WidgetFactory para UI
- Não devem acessar widgets/core QGIS diretamente
- Devem delegar operações para ProjectUtils
- Risco: travamento de task ou UI

## Ferramentas de Janela com Saída QGIS
- Abrem janela ao executar (WidgetFactory)
- Exigem ação do usuário para iniciar processamento
- Exibem mensagens de sucesso/erro/info
- Possuem análise de cenário
- Podem ter múltiplos widgets (checkbox, input, etc.)
- Salvam preferências de configuração e estado da janela
- Devem ter botão de instruções (arquivo em resources/instructions)
- Podem obter dados do explorador de arquivos
- Podem salvar QGZ como backup
- Devem usar ProjectUtils para manipulação de camadas/projeto
- Devem persistir estado e opções
- Devem implementar método run padrão para abrir diálogo
- Devem garantir compatibilidade QGIS 3.16 a 4.0
- Risco: alteração de projeto/camadas

## Ferramentas de Janela sem Saída QGIS
- Abrem janela ao executar (WidgetFactory)
- Exigem ação do usuário para iniciar processamento
- Exibem mensagens de sucesso/erro/info
- Possuem análise de cenário
- Podem ter múltiplos widgets (checkbox, input, etc.)
- Salvam preferências de configuração e estado da janela
- Devem ter botão de instruções (arquivo em resources/instructions)
- Podem obter dados do explorador de arquivos
- Podem salvar QGZ como backup
- Devem persistir estado e opções
- Podem gerar arquivos de saída no QGIS ou explorador
- Podem aplicar estilos às camadas de saída (Styles)
- Devem implementar método run padrão para abrir diálogo
- Devem garantir compatibilidade QGIS 3.16 a 4.0
- Risco: manipulação de arquivos/camadas

## Contratos Técnicos e Recomendações
- UI deve ser construída via WidgetFactory
- Plugins não devem acessar widgets/core QGIS diretamente
- Operações de projeto/camadas devem ser delegadas a ProjectUtils
- Preferências devem ser salvas/carregadas via Preferences
- Todos os plugins devem ter ToolKey único
- Todos os plugins devem ser filhos de BasePluginMTL
- Plugins devem ter arquivo de instruções e análise de cenário
- Plugins devem implementar método run padrão para abertura
- Plugins devem garantir compatibilidade máxima
- Plugins devem documentar contratos de entrada/saída
- Plugins devem persistir estado de UI e opções
- Plugins devem seguir Clean Code e boas práticas
