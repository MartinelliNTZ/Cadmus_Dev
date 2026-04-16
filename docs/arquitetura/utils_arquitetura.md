# Utils do Cadmus — Arquitetura, Contratos e Boas Práticas

Data: 2026/03/12

Resumo
------
Este documento descreve de forma técnica o subsistema de utilitários (utils) do Cadmus:
- Estrutura, contratos, padrões de implementação, integração com plugins
- Regras obrigatórias, armadilhas, recomendações operacionais
- Análise detalhada de cada utilitário

Componentes Principais
----------------------
- **DependenciesManager**: Gerencia dependências externas (bibliotecas Python). Verifica, instala e valida módulos necessários.
- **ExplorerUtils**: Varredura de diretórios, identificação e carregamento de arquivos vetoriais/raster. Utilizado para operações de entrada de dados.
- **FormatUtils**: Conversão e formatação de valores (bytes, velocidade, duração, relógio). Usado para exibir informações técnicas.
- **LayoutsUtils**: Processamento de layouts QGIS, substituição de textos, manipulação de itens. Não depende de UI.
- **PDFUtils**: Manipulação de PDFs e imagens, merger de arquivos, logging detalhado.
- **Preferences**: Gerencia preferências do plugin, salva/carrega JSON local, fornece API para cada ferramenta.
- **ProjectUtils**: Operações relacionadas ao projeto QGIS (.qgz), backup, manipulação de camadas, clipboard, cálculo de tamanho.
- **QgisMessageUtil**: Exibe mensagens no QGIS, integra com message bar, modal, logging, feedback ao usuário.
- **StringUtils**: Filtros, drivers, nomes, utilitários de string para arquivos e camadas.
- **ToolKeys**: Enum de identificação de ferramentas/plugins, mapeamento de cores, integração com logging.

Contratos e Regras Obrigatórias
-------------------------------
- Utils devem ser usados por plugins para delegar operações técnicas
- Não devem depender de UI (exceto QgisMessageUtil)
- Devem ser modulares, reutilizáveis e documentados
- Devem evitar dependências diretas de widgets/core QGIS
- Devem garantir compatibilidade máxima
- Devem registrar logs via LogUtils quando aplicável

Fluxo de Execução
-----------------
1. Plugin aciona utilitário conforme necessidade (ex.: carregar camada, salvar prefs)
2. Utilitário executa operação técnica, retorna resultado ou status
3. Logging e feedback são feitos via LogUtils/QgisMessageUtil
4. Preferências são salvas/carregadas via Preferences

Padrões de Implementação
------------------------
- Utils devem ser estáticos ou de fácil instanciamento
- Devem documentar contratos de entrada/saída
- Devem persistir estado quando aplicável
- Devem evitar duplicidade de funções
- Devem ser testáveis e robustos

Erros Comuns e Armadilhas
-------------------------
- Duplicidade de funções entre utils
- Falta de logging em operações críticas
- Dependência de UI em utils não destinados a isso
- Falta de documentação de contratos

Boas Práticas de Uso
--------------------
- Delegar operações técnicas para utils
- Documentar contratos e exemplos de uso
- Garantir modularidade e reuso
- Registrar logs e feedback ao usuário
- Manter documentação técnica atualizada

Análise Detalhada dos Utils
---------------------------
### DependenciesManager
- Gerencia dependências externas (PyPDF2, Pillow)
- Verifica instalação, executa scripts de instalação, valida antes de processos
- Plugins devem usar para garantir dependências antes de operações

### ExplorerUtils
- Varre diretórios, identifica arquivos vetoriais/raster
- Carrega layers conforme extensão
- Usado para entrada de dados em plugins de importação/carregamento

### FormatUtils
- Converte bytes, velocidade, duração, relógio
- Usado para exibir informações técnicas em UI e logs

### LayoutsUtils
- Processa layouts QGIS, substitui textos, manipula itens
- Não depende de UI, usado por plugins de layout

### PDFUtils
- Manipula PDFs e imagens, merger de arquivos
- Logging detalhado, integração com DependenciesManager
- Usado por plugins de exportação e conversão

### Preferences
- Gerencia preferências do plugin, salva/carrega JSON local
- API para cada ferramenta (tool_key)
- Plugins devem usar para persistir estado/configuração

### ProjectUtils
- Operações com projeto QGIS (.qgz), backup, manipulação de camadas
- Clipboard, cálculo de tamanho, integração com camadas
- Plugins devem delegar operações de projeto/camadas

### QgisMessageUtil
- Exibe mensagens no QGIS, integra com message bar/modal/log
- Feedback ao usuário, logging, perguntas de conflito
- Plugins devem usar para exibir mensagens e resultados

### StringUtils
- Filtros, drivers, nomes, utilitários de string para arquivos/camadas
- Usado para padronizar nomes, filtros e drivers

### ToolKeys
- Enum de identificação de ferramentas/plugins
- Mapeamento de cores, integração com logging
- Plugins devem usar para identificação e logging

Recomendações Finais
--------------------
1. Delegar operações técnicas para utils
2. Documentar contratos e exemplos de uso
3. Garantir modularidade, reuso e compatibilidade
4. Registrar logs e feedback ao usuário
5. Manter documentação técnica atualizada
