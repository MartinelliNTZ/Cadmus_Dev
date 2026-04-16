# Plugins do Cadmus — Arquitetura, Contratos e Boas Práticas

Data: 2026/03/12

Resumo
------
Este documento descreve de forma técnica o subsistema de plugins do Cadmus:
- Estrutura, contratos, padrões de implementação, integração com QGIS
- Regras obrigatórias, armadilhas, recomendações operacionais
- Tabela detalhada dos plugins
# 🧰 Cadmus

**Cadmus** é um conjunto de ferramentas avançadas para o QGIS voltado à **automação de layouts**, **processamento de dados vetoriais e raster** e **otimização de fluxos cartográficos** 🗺️⚙️  
O plugin reúne soluções para **exportação em lote**, **edição massiva de layouts**, **análises estatísticas**, **amostragem de rasters**, **cálculos automatizados de atributos** e **ferramentas interativas de apoio**, reduzindo etapas manuais e aumentando a produtividade no QGIS.

---

## 🚀 Ferramentas Principais

### 📤 Exportar Todos os Layouts
    Ferramenta para **exportação automática de todos os layouts do projeto** para PDF e/ou PNG.  
    Ideal para produção cartográfica em lote com controle e padronização.

    **O que ela faz:**
    - Exporta todos os layouts do projeto automaticamente
    - Permite definir pasta de saída e evitar sobrescrita
    - Opção para unir todos os PDFs em um único arquivo
    - Conversão opcional de múltiplos PNGs em PDF final
    - Controle de largura máxima na exportação
    - Exibe progresso e trata erros por layout
    - Salva preferências do usuário

---

### 🔁 Replace Text in Layouts
    Ferramenta para **substituição de textos em massa** em todos os layouts do projeto QGIS.  
    Indicada para padronização rápida de títulos, legendas e informações repetidas.

    **O que ela faz:**
    - Busca e substituição de textos em todos os layouts
    - Opção de diferenciar maiúsculas/minúsculas
    - Modo **chave**, substituindo todo o conteúdo do item
    - Cria **backup automático do projeto (.qgz)**
    - Gera **arquivo de log** das alterações
    - Salva preferências do usuário

---

### 🔄 Salvar, Fechar e Reabrir Projeto
    Ferramenta que **reinicia o QGIS mantendo o projeto atual aberto**.  
    Ideal para aplicar mudanças globais sem risco de perda de dados.

    **O que ela faz:**
    - Verifica se o projeto está salvo
    - Salva todas as alterações automaticamente
    - Fecha o QGIS de forma controlada
    - Reabre o QGIS com o mesmo projeto carregado

---

### 📂 Carregar Pasta de Arquivos
    Ferramenta para **carregamento automático de camadas a partir de pastas e subpastas**.  
    Indicada para projetos com grandes volumes de dados organizados em diretórios.

    **O que ela faz:**
    - Seleção de pasta raiz no disco
    - Suporte a múltiplos formatos vetoriais e raster
    - Opção para carregar apenas arquivos novos
    - Preserva estrutura de pastas em grupos
    - Cria backup do projeto antes da operação
    - Salva preferências de uso

---

### 🚜 Gerar Rastro de Implemento
    Ferramenta para **geração da faixa de cobertura de implementos agrícolas** a partir de linhas.  
    Indicada para planejamento agrícola e análise operacional.

    **O que ela faz:**
    - Usa camada de linhas como entrada
    - Gera o rastro com base na largura informada
    - Saída como camada temporária ou arquivo
    - Opção de aplicar estilo QML
    - Armazena preferências do usuário

---

### ℹ️ Sobre o Cadmus
    Janela informativa com **dados técnicos, autoria, versão e links oficiais** do plugin.  
    Utilizada como referência rápida e acesso a suporte.

---

### 📍 Consulta de Coordenadas e Altimetria
    Ferramenta que permite **obter coordenadas completas e altitude por clique no mapa**.  
    Ideal para conferência rápida e apoio a levantamentos de campo.

    **O que ela faz:**
    - Clique direto no mapa com suporte a snapping
    - Coordenadas em **WGS 84 (decimal e DMS)**
    - Coordenadas **UTM SIRGAS 2000** completas
    - Consulta automática de **altitude (SRTM 90 m)**
    - Execução em background
    - Cópia individual ou completa dos valores

---



## ⚙️ Ferramentas de Processamento

### 📊 Estatísticas de Atributos
    Ferramenta para **geração de estatísticas descritivas de campos numéricos**.  
    Indicada para análises exploratórias e relatórios técnicos.

    **O que ela faz:**
    - Analisa todos os campos numéricos
    - Permite excluir campos do cálculo
    - Calcula médias, desvios, percentis, variância e mais
    - Define precisão decimal
    - Gera arquivo **CSV**
    - Suporte a formato PT-BR
    - Carrega o CSV automaticamente no projeto
    - Salva preferências do usuário

---

### ➖ Gerador de Diferenças entre Campos
    Ferramenta para **criação automática de campos com diferenças numéricas**.  
    Indicada para análises comparativas e validação de dados.

    **O que ela faz:**
    - Utiliza camada de pontos
    - Define um campo base
    - Calcula diferenças para todos os campos numéricos
    - Cria novos campos com prefixo configurável
    - Controla precisão decimal
    - Gera nova camada de saída
    - Salva preferências do usuário

---

### 🌐 Amostragem Massiva de Rasters
    Ferramenta para **extração automática de valores de múltiplos rasters** em pontos.  
    Indicada para análises ambientais, agrícolas e geoespaciais.

    **O que ela faz:**
    - Usa camada de pontos como base
    - Permite selecionar múltiplos rasters
    - Extrai valores automaticamente
    - Cria novos campos por raster
    - Gera nova camada vetorial
    - Opção de reprojeção da saída
    - Armazena preferências de saída


Componentes Principais
----------------------
- **BasePluginMTL**: Classe base obrigatória para todos os plugins. Garante padronização, persistência, logging e integração.
- **WidgetFactory**: Fábrica central de widgets, layouts e componentes UI. Plugins devem construir UI exclusivamente via WidgetFactory, garantindo padronização, modularidade e compatibilidade.
- **MainLayout**: Layout principal dos dialogs, encapsula scroll, bordas, AppBar.
- **AppBarWidget**: Barra superior com título, botões de ação (Executar, Info, Fechar).
- **BottomActionButtonsWidget**: Botões inferiores padronizados (Executar, Fechar, Info).
- **AttributeSelectorWidget**: Widget exclusivo para seleção de atributos/campos.
- **Styles**: Centraliza temas visuais, define estilos globais, checkbox, radio, label, etc.
- **InfoDialog**: Diálogo padronizado para exibir instruções técnicas, renderiza Markdown nativamente ou converte para HTML.
- **ToolKey**: Enum de identificação de cada ferramenta/plugin.
- **Preferences**: API para salvar/carregar preferências de cada plugin.
- **ProjectUtils**: Responsável por operações com projeto QGIS (carregar, salvar, manipular camadas). Plugins não devem acessar QgsProject/QgsApplication diretamente.
- **AsyncPipelineEngine**: Plugins não criam tasks diretamente; usam steps/pipeline para processamento assíncrono.

Integração com Resources
-----------------------
Plugins devem usar recursos padronizados para UI, estilos e instruções:
- WidgetFactory: construção de UI modular, compatível e padronizada
- Styles: aplicação de temas visuais
- InfoDialog: exibição de instruções técnicas, Markdown/HTML
- resources/widgets: widgets exclusivos para cada função
- resources/icons: ícones padronizados
- resources/instructions: arquivos de instruções para cada plugin

Recomendações técnicas:
- Plugins devem construir UI exclusivamente via WidgetFactory
- Estilos devem ser aplicados via Styles
- InfoDialog deve ser usado para exibir instruções técnicas
- Widgets devem ser modulares, reutilizáveis e compatíveis
- Arquivos de instruções devem ser mantidos e atualizados para cada plugin

Para detalhes, consulte [docs/resources_arquitetura.md](docs/resources_arquitetura.md)

Integração com Utils
--------------------
Plugins dependem fortemente dos utilitários (utils) para delegar operações técnicas:
- **DependenciesManager**: Garantia de dependências externas antes de operações (ex.: PDF, imagens)
- **ExplorerUtils**: Entrada de dados, varredura de diretórios, identificação de arquivos
- **FormatUtils**: Conversão e exibição de valores técnicos (bytes, duração, velocidade)
- **LayoutsUtils**: Processamento de layouts, substituição de textos
- **PDFUtils**: Manipulação de PDFs/imagens, logging
- **Preferences**: Persistência de estado/configuração
- **ProjectUtils**: Backup, manipulação de camadas, clipboard
- **QgisMessageUtil**: Exibição de mensagens, feedback ao usuário
- **StringUtils**: Filtros, drivers, nomes padronizados
- **ToolKeys**: Enum de identificação, cores, integração com logging

Recomendações técnicas:
- Plugins devem delegar operações técnicas para utils sempre que possível
- Utils devem ser documentados, modulares e compatíveis
- Plugins devem registrar logs via LogUtils e exibir feedback via QgisMessageUtil
- Preferências e estado devem ser persistidos via Preferences
- Operações de projeto/camadas devem ser feitas via ProjectUtils

Para detalhes, consulte [docs/utils_arquitetura.md](docs/utils_arquitetura.md)

Contratos e Regras Obrigatórias
-------------------------------
- Todos os plugins devem:
  - Herdar de BasePluginMTL
  - Usar WidgetFactory para UI (não acessar /QWidget/QPushButton etc. diretamente)
  - Declarar ToolKey único
  - Salvar preferências via Preferences
  - Integrar ProjectUtils para manipulação de projeto/camadas
  - Ter arquivo de instruções em resources/instructions
  - Ter análise de cenário em docs/analisecenario
  - Ser declarados em Cadmus_plugin.py
  - Implementar método de abertura padrão (exemplo):
    ```python
    def run_copy_attributes(iface):
        dlg = CopyAttributes(iface)
        dlg.setModal(False)
        dlg.show()
        return dlg
    ```
  - Seguir Clean Code e boas práticas
  - Garantir compatibilidade QGIS 3.16 a 4.0
  - Não adicionar tasks diretamente; usar AsyncPipelineEngine

Fluxo de Execução
-----------------
1. Plugin é instanciado via método run padrão
2. UI é construída via WidgetFactory (se aplicável)
3. Preferências são carregadas/salvas automaticamente
4. Operações de projeto/camadas são delegadas a ProjectUtils
5. Processamento pesado é feito via steps/pipeline (AsyncPipelineEngine)
6. Logging é feito via LogUtils
7. Resultados, erros e mensagens são exibidos via QgisMessageUtil

Padrões de Implementação
------------------------
- Plugins de janela devem implementar _build_ui() usando WidgetFactory
- Plugins instantâneos podem omitir UI, mas devem exibir mensagens de status
- Plugins devem evitar dependências diretas de QGIS widgets/core
- Plugins devem persistir estado da janela, opções e preferências
- Plugins devem ter instruções e análise de cenário documentadas

Erros Comuns e Armadilhas
-------------------------
- Acessar widgets/core(possivel mas tente evitar) do QGIS diretamente (violação de contrato)
- Não usar WidgetFactory para UI
- Não persistir preferências corretamente
- Adicionar tasks diretamente (deve usar pipeline)
- Falta de compatibilidade com versões antigas do QGIS
- Não documentar instruções ou análise de cenário

Boas Práticas de Uso
--------------------
- Seguir padrões de BasePluginMTL e WidgetFactory
- Documentar contratos de entrada/saída de cada plugin
- Usar ToolKey para identificação e logging
- Persistir preferências e estado de UI
- Delegar operações de projeto/camadas para ProjectUtils
- Garantir compatibilidade máxima
- Manter documentação técnica e instruções atualizadas

Tabela Detalhada dos Plugins
----------------------------
| Nº  | Nome                          | Tipo                        | Classe Plugin              | Usa Task | Tipo de Entrada | Tipo de Saída | Risco |
|-----|-------------------------------|-----------------------------|----------------------------|----------|-----------------|---------------|-------|
| 01  | Exportar Todos os Layouts     | Janela                      | ExportAllLayoutsDialog     | Não      | Projeto QGIS    | PDF/PNG       | Substituir produtos antigos |
| 02  | Substituir Textos nos Layouts | Janela                      | ReplaceInLayoutsDialog     | Não      | Layouts QGIS    | Layouts QGIS  | Crítico/alteração QGZ |
| 03  | Salvar, Fechar e Reabrir      | Instantânea                 | _RestartExecutor           | Não      | Projeto QGIS    | Projeto QGIS  | Crítico/alteração QGZ |
| 04  | Carregar Pasta de Arquivos    | Janela                      | LoadFolderLayersDialog     | Sim      | Arquivos        | Camadas QGIS  | Alteração QGZ |
| 05  | Gerar Rastro de Implemento    | Janela                      | GenerateTrailPlugin        | Sim      | Camada Vetorial | Camada Vetorial| Nenhum |
| 06  | Sobre o Cadmus             | Janela                      | AboutDialog                | Não      | Nenhum          | Informações   | Nenhum |
| 07  | Capturar Coordenadas          | Instantânea+Resultado        | CoordClickTool             | Sim      | Canvas QGIS     | Diálogo       | Travamento da task |
| 08  | Calcular Campos Vetoriais     | Instantânea                 | VectorFieldsCalculationPlugin | Sim  | Camada Vetorial | Camada Vetorial| Manipulação de vetores |
| 09  | Obter Coordenadas de Drone    | Janela                      | DroneCordinates            | Sim      | Arquivos MRK    | Camada Vetorial| Travamento por excesso de dados |
| 10  | Converter Multipart           | Instantânea                 | VectorMultipartPlugin      | Não      | Camada Vetorial | Camada Vetorial| Manipulação de vetores |
| 11  | Copiar Atributos de Vetores   | Janela                      | CopyAttributes             | Não      | Camada Vetorial | Camada Vetorial| Manipulação de vetores |
| 12  | LogCat Viewer                 | Janela (multithread)        | LogcatDialog               | Não      | Logs            | Diálogo       | Nenhum |
| 13  | SettingsPlugin                | Janela                      | SettingsPlugin             | Não      | Preferências    | Preferências  | Nenhum |

Recomendações Finais
--------------------
1. Seguir contratos de BasePluginMTL, WidgetFactory, ProjectUtils, Preferences
2. Garantir documentação técnica, instruções e análise de cenário
3. Manter compatibilidade máxima com QGIS
4. Evitar dependências diretas de widgets/core QGIS
5. Usar pipeline para processamento assíncrono
6. Persistir preferências e estado de UI
7. Documentar riscos e contratos de cada plugin
