# Resources do Cadmus — Arquitetura, Widgets, Estilos e Dialogs

Data: 2026/03/12

Resumo
------
Este documento descreve de forma técnica o subsistema de resources do Cadmus:
- Estrutura, contratos, padrões de implementação, integração com plugins
- Papel da WidgetFactory, InfoDialog, estilos e widgets
- Recomendações operacionais e armadilhas

Componentes Principais
----------------------
- **WidgetFactory**: Fábrica central de widgets, layouts e componentes UI. Garante padronização, modularidade e compatibilidade.
- **MainLayout**: Layout principal dos dialogs, encapsula scroll, bordas, AppBar.
- **AppBarWidget**: Barra superior com título, botões de ação (Executar, Info, Fechar).
- **BottomActionButtonsWidget**: Botões inferiores padronizados (Executar, Fechar, Info).
- **AttributeSelectorWidget**: Widget exclusivo para seleção de atributos/campos.
- **Styles**: Centraliza temas visuais, define estilos globais, checkbox, radio, label, etc.
- **InfoDialog**: Diálogo padronizado para exibir instruções técnicas, renderiza Markdown nativamente ou converte para HTML.
- **resources/icons/**: Ícones padronizados para UI.
- **resources/instructions/**: Arquivos de instruções para cada plugin, exibidos via InfoDialog.
- **resources/widgets/**: Implementação modular de widgets, cada um com responsabilidade única.

Contratos e Regras Obrigatórias
-------------------------------
- Plugins devem construir UI exclusivamente via WidgetFactory
- Widgets devem ser modulares, reutilizáveis e compatíveis
- Estilos devem ser aplicados via Styles
- InfoDialog deve ser usado para exibir instruções técnicas
- Arquivos de instruções devem ser mantidos e atualizados para cada plugin
- Widgets devem evitar lógica de negócio, focar apenas em UI
- Recomenda-se documentação técnica de cada widget

Fluxo de Execução
-----------------
1. Plugin instancia WidgetFactory para construir UI
2. Widgets são adicionados ao MainLayout, AppBar, BottomActionButtons
3. Estilos são aplicados via Styles
4. InfoDialog exibe instruções técnicas ao usuário
5. Preferências de UI são salvas/carregadas via Preferences

Padrões de Implementação
------------------------
- Widgets devem ser instanciados via WidgetFactory
- Layouts devem ser compostos por MainLayout, AppBar, BottomActionButtons
- Estilos devem ser centralizados em Styles
- InfoDialog deve renderizar Markdown ou HTML conforme versão do QGIS
- Widgets devem ser testáveis e documentados

Erros Comuns e Armadilhas
-------------------------
- Construir UI manualmente sem WidgetFactory (violação de contrato)
- Falta de documentação de widgets e instruções
- Estilos inconsistentes por não usar Styles
- InfoDialog sem instruções técnicas atualizadas

Boas Práticas de Uso
--------------------
- Usar WidgetFactory para toda construção de UI
- Manter documentação técnica e instruções de cada plugin
- Centralizar estilos em Styles
- Garantir modularidade e reuso de widgets
- Usar InfoDialog para instruções técnicas e ajuda

Análise Detalhada dos Principais Recursos
-----------------------------------------
### WidgetFactory
- Fábrica central de widgets, layouts, componentes UI
- Garante padronização, modularidade, compatibilidade QGIS 3.16 a 4.0
- Plugins devem usar para toda construção de UI

### MainLayout
- Layout principal dos dialogs, encapsula scroll, bordas, AppBar
- Permite composição flexível de widgets

### AppBarWidget
- Barra superior com título, botões de ação (Executar, Info, Fechar)
- Integrado ao MainLayout

### BottomActionButtonsWidget
- Botões inferiores padronizados (Executar, Fechar, Info)
- Facilita callbacks e integração com ToolKey

### AttributeSelectorWidget
- Widget exclusivo para seleção de atributos/campos
- Permite seleção múltipla, "usar todos", integração com preferências

### Styles
- Centraliza temas visuais, define estilos globais, checkbox, radio, label, etc.
- Plugins devem aplicar estilos via Styles

### InfoDialog
- Diálogo padronizado para exibir instruções técnicas
- Renderiza Markdown nativamente (Qt >= 5.14) ou converte para HTML (QGIS 3.16)
- Plugins devem usar para exibir instruções de cada ferramenta

### resources/icons/
- Ícones padronizados para UI, integrados via WidgetFactory

### resources/instructions/
- Arquivos de instruções para cada plugin, exibidos via InfoDialog
- Devem ser mantidos e atualizados conforme evolução das ferramentas

### resources/widgets/
- Implementação modular de widgets, cada um com responsabilidade única
- Permite composição flexível e reuso

Recomendações Finais
--------------------
1. Plugins devem construir UI exclusivamente via WidgetFactory
2. Widgets devem ser modulares, reutilizáveis e compatíveis
3. Estilos devem ser aplicados via Styles
4. InfoDialog deve ser usado para exibir instruções técnicas
5. Arquivos de instruções devem ser mantidos e atualizados para cada plugin
6. Documentação técnica de cada widget é recomendada
