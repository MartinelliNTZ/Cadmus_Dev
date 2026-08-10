---
name: instructions-system
description: >
  Agente especializado no sistema de instruções do Cadmus, que gerencia dois tipos de conteúdo:
  (1) arquivos .md em resources/instructions/<locale>/ resolvidos via InstructionsManager,
  (2) instruções HTML dinâmicas via HtmlInstructionsProvider + módulos HtmlInstructions_<locale>.py.
  Leia docs/skills/PLUGIN_CONTRACT.md antes de qualquer alteração.
---

# Sistema de Instruções do Cadmus

## Resumo Executivo

O **sistema de instruções** do Cadmus fornece conteúdo de ajuda para ferramentas e algoritmos através de dois mecanismos complementares:

1. **InstructionsManager** — Resolve arquivos `.md` em `resources/instructions/<locale>/<tool_key>_help.md`. Usado por plugins que herdam `BasePluginMTL` via `show_info_dialog()`.
2. **HtmlInstructionsProvider** — Carrega módulos Python dinâmicos `HtmlInstructions_<locale>.py` que geram HTML com logo, formatação e autor. Usado por algoritmos de processing e ferramentas que exibem ajuda em diálogos HTML.

Ambos os sistemas são orientados a locale e seguem o padrão: o desenvolvedor cria o conteúdo no locale ativo (pt_BR) e o sistema faz fallback automático.

---

## Objetivo

Centralizar e padronizar a criação de conteúdo de ajuda para todas as ferramentas do Cadmus, garantindo:
- Separação entre conteúdo (instruções) e apresentação (HTML vs Markdown)
- Resolução automática por locale com fallback para pt_BR
- Cache de resolução para evitar leitura repetida de arquivos
- Consistência visual nas instruções HTML (logo, cores, formatação)
- Mecanismo único de resolução: `tool_key` → arquivo/método de instrução
- **Rastreabilidade de cada arquivo .md** com versão, data de criação e data da última modificação

---

## InstructionsManager (Arquivos .md)

### Arquitetura

```
InstructionsManager (class methods)
├── BASE_DIR = resources/
├── _cache = {}  # cache de tool_key → path
│
├── _build_filename(tool_key) → f"{tool_key.lower()}_help.md"
│
└── get(tool_key) → str (path absoluto do arquivo)
    ├── 1. Verifica cache
    ├── 2. Constrói filename: <tool_key>_help.md
    ├── 3. Obtém locale via TM.locale
    ├── 4. Tenta: resources/instructions/<locale>/<filename>
    ├── 5. Fallback: resources/instructions/pt_BR/<filename>
    └── 6. Fallback final: resources/instructions/pt_BR/standard.md
```

### Regras de resolução de arquivo

| Ordem | Caminho | Condição |
|-------|---------|----------|
| 1 | `resources/instructions/<TM.locale>/<tool_key>_help.md` | Locale atual do usuário |
| 2 | `resources/instructions/pt_BR/<tool_key>_help.md` | Fallback para pt_BR |
| 3 | `resources/instructions/pt_BR/standard.md` | Fallback genérico |

### Como criar um novo arquivo .md

1. Identificar o `tool_key` da ferramenta (ex: `ToolKey.SAVE_TEMPORARY_LAYER` → `"save_temporary_layer"`)
2. Criar o arquivo em `resources/instructions/pt_BR/save_temporary_layer_help.md`
3. Seguir o padrão de conteúdo dos arquivos existentes
4. (Opcional) Criar traduções em `en/`, `es/`, `de/`, `ja/`

### Padrão de conteúdo dos arquivos .md

Todo arquivo .md de instrução **deve** conter o bloco de metadados no topo, com versão, data de criação e data da última modificação:

```markdown
<!--
Versao: 1.0.0
Data de criacao: 2026-08-10
Data da ultima modificacao: 2026-08-10
-->

# <Título da Ferramenta> — Guia Rapido

<Descrição de uma linha sobre o que a ferramenta faz>

## Como usar

1. <Passo 1>
2. <Passo 2>
3. <Passo 3>

## O que o plugin faz de verdade

- <Comportamento real baseado no código>
- <Detalhes de implementação>

## Comportamento importante

- <Comportamentos que o usuário precisa saber>
- <Casos de borda>

## Quando usar

Use esta ferramenta quando quiser:

- <Caso de uso 1>
- <Caso de uso 2>

## Cuidados

- <Cuidado 1>
- <Cuidado 2>
```

### Regras de metadados

| Campo | Formato | Obrigatório | Quando atualizar |
|-------|---------|-------------|------------------|
| `Versao` | `X.Y.Z` (semântico) | ✅ | A cada mudança de conteúdo |
| `Data de criacao` | `AAAA-MM-DD` | ✅ | Somente na criação do arquivo (nunca alterar) |
| `Data da ultima modificacao` | `AAAA-MM-DD` | ✅ | **SEMPRE** que o arquivo for editado |

**Regra crítica:** ao editar qualquer arquivo .md de instrução, **sempre** atualizar a `Data da ultima modificacao` para a data atual. A `Data de criacao` nunca deve ser alterada após a criação.

### Arquivos existentes

```
resources/instructions/pt_BR/
├── converter_multipart_help.md
├── coord_click_tool_help.md
├── copy_attributes_help.md
├── create_project_help.md
├── divide_points_by_strips_help.md
├── drone_coordinates_help.md
├── export_all_layouts_help.md
├── generate_trail_help.md
├── load_folder_layers_help.md
├── path_extension_tool_help.md
├── replace_in_layouts_help.md
├── restart_qgis_help.md
├── save_temporary_layer_help.md
├── settings_help.md
├── standard.md
├── vector_fields_help.md
└── vector_to_svg_help.md
```

Idiomas com pasta própria de instruções:

| Idioma | Pasta | Arquivos |
|--------|-------|----------|
| Português (Brasil) | `pt_BR/` | Referência completa (fallback universal) |
| Inglês | `en/` | Subconjunto traduzido |
| Espanhol | `es/` | Subconjunto traduzido |
| Alemão | `de/` | Subconjunto traduzido |
| Japonês | `ja/` | Subconjunto traduzido (coordenadas, SVG) |

### Integração com BasePluginMTL

Em `BasePluginMTL._build_ui()`:

```python
self.instructions_file = InstructionsManager.get(self.TOOL_KEY)
```

Em `BasePluginMTL.show_info_dialog()`:

```python
def show_info_dialog(self, title=f"📘 {STR.INSTRUCTIONS}"):
    if hasattr(self, "instructions_file"):
        title = f"📘 {STR.INSTRUCTIONS} – {self.PLUGIN_NAME}"
        InfoDialog(self.instructions_file, self, title).exec()
```

---

## HtmlInstructionsProvider (Instruções HTML)

### Arquitetura

```
HtmlInstructionsProvider
├── BASE_DIR = resources/instructions/html/
├── logger (LogUtils com tool_key)
├── logo (imagem Cadmus em base64)
├── author_info (créditos do autor)
├── locale (via TM.locale)
│
├── _normalize_locale() → "pt_BR" | "en" | "es"
├── _load_module(suffix) → módulo Python dinâmico
├── _load_instructions() → instância de HtmlInstructions
│
├── get_instructions(algorithm_name) → str HTML
│   ├── Concatena: "get_<algorithm_name>_help"
│   ├── Chama método no módulo carregado
│   └── Fallback: "Instruções não disponíveis"
│
├── transform_h(text, level=2) → <h2>text</h2> estilizado
└── transform_alert(text) → <div>⚠️text</div> estilizado
```

### Módulos de locale

```
resources/instructions/html/
├── HtmlInstructions_de.py
├── HtmlInstructions_en.py
├── HtmlInstructions_es.py
└── HtmlInstructions_pt_BR.py
```

### Estrutura de um módulo HtmlInstructions

```python
class HtmlInstructions:
    def __init__(self, provider):
        self.provider = provider

    def get_<algorithm_name>_help(self):
        return f"""
            {self.provider.logo}
            <descrição de uma linha>
            {self.provider.transform_h('Objetivo')}
            <objetivos em bullet>
            {self.provider.transform_h('Como usar')}
            <passos numerados>
            {self.provider.transform_h('Saídas')}
            <o que é gerado>
            {self.provider.transform_h('Atenções')}
            <cuidados e limitações>
            {self.provider.author_info}
        """
```

### Métodos auxiliares do provider

| Método | Descrição | Exemplo de saída |
|--------|-----------|------------------|
| `transform_h(text, level=2)` | Título estilizado | `<h2 style="color:#ffffff;">Objetivo</h2>` |
| `transform_alert(text)` | Alerta destacado | `<h3 style="background-color:#ffcccc;color:#990000;...">⚠️text</h3>` |
| `logo` | Imagem Cadmus | `<img src="..." width="80">` |
| `author_info` | Créditos do autor | `<h2>Matheus A.S. Martinelli</h2>` |

### Como criar instruções HTML para um novo algoritmo

1. Abrir o módulo do locale desejado (ex: `HtmlInstructions_pt_BR.py`)
2. Adicionar um método `get_<algorithm_name>_help(self)` seguindo o padrão
3. O nome do método deve corresponder exatamente ao `algorithm_name` passado em `get_instructions(algorithm_name)`
4. Usar `self.provider.transform_h()`, `self.provider.transform_alert()`, `self.provider.logo` e `self.provider.author_info`

### Exemplo real de método de instrução HTML

```python
# Em HtmlInstructions_pt_BR.py
def get_ndvi_calculator_help(self):
    return f"""
        {self.provider.logo}
        Ferramenta do pacote Cadmus para calculo do NDVI a partir de dois rasters (NIR e RED).
        {self.provider.transform_h('Objetivo')}
        Calcular o indice de vegetacao NDVI entre dois rasters.
        Suportar selecao individual de bandas NIR e RED.
        {self.provider.transform_alert('As bandas padrao sao definidas como banda 1. Ajuste conforme o satelite de origem dos dados.')}
        {self.provider.transform_h('Como usar')}
        1. Selecione o raster NIR (Infravermelho Proximo).
        2. Selecione a banda NIR (padrao: banda 1).
        3. Selecione o raster RED (Vermelho).
        4. Selecione a banda RED (padrao: banda 1).
        5. Defina o caminho de saida e execute.
        {self.provider.transform_h('Saidas')}
        Raster NDVI (GeoTIFF) com valores entre -1 e 1.
        {self.provider.transform_h('Atencoes')}
        Os rasters NIR e RED precisam ter extensoes sobrepostas.
        Ambos os rasters devem estar no mesmo CRS.
        {self.provider.author_info}
    """
```

---

## Fluxo de resolução de instruções

```
Plugin chama show_info_dialog()
  └── BasePluginMTL._build_ui() já carregou:
        self.instructions_file = InstructionsManager.get(self.TOOL_KEY)
        ├── Retorna path do .md → InfoDialog abre arquivo markdown
        └── Se não encontrou → fallback standard.md

Algoritmo de processing chama get_instructions()
  └── HtmlInstructionsProvider.get_instructions("ndvi_calculator")
        ├── Carrega HtmlInstructions_<locale>.py
        ├── Chama método get_ndvi_calculator_help()
        └── Retorna string HTML formatada
```

---

## Regras

### ✅ Sempre:
- Criar arquivos .md em `resources/instructions/pt_BR/` seguindo o padrão `{tool_key}_help.md`
- Incluir o bloco de metadados (`Versao`, `Data de criacao`, `Data da ultima modificacao`) no topo de todo arquivo .md
- **Atualizar a `Data da ultima modificacao` sempre que editar um arquivo .md de instrução**
- Usar `InstructionsManager.get(tool_key)` para resolver caminhos, nunca hardcoded
- Usar `self.provider.transform_h()` e `self.provider.transform_alert()` nos métodos HTML
- Incluir `self.provider.logo` e `self.provider.author_info` em toda instrução HTML
- Nomear métodos HTML como `get_<algorithm_name>_help` (underscores, não hífens)
- Manter o locale pt_BR como fallback universal
- Usar acentos removidos nos arquivos .md (padrão do projeto)

### ❌ Nunca:
- Hardcodar caminhos de arquivos de instrução — sempre usar InstructionsManager
- Esquecer de adicionar o método no módulo HtmlInstructions_<locale>.py
- Usar HTML inline sem os helpers do provider (perde formatação padrão)
- Ignorar o fallback — sempre criar pelo menos em pt_BR
- Esquecer de registrar o tool_key em ToolKeys.py antes de criar instruções
- **Alterar a `Data de criacao` após a criação do arquivo**
- **Editar um arquivo .md sem atualizar a `Data da ultima modificacao`**

---

## Padrões de Uso

### Padrão 1 — Criar instrução .md para novo plugin

```python
# 1. Registrar tool_key em utils/ToolKeys.py
class ToolKey:
    MINHA_FERRAMENTA = "minha_ferramenta"

# 2. Criar resources/instructions/pt_BR/minha_ferramenta_help.md
# Seguindo o template markdown padrão (com metadados no topo)

# 3. O BasePluginMTL carrega automaticamente via:
#    self.instructions_file = InstructionsManager.get(self.TOOL_KEY)
```

### Padrão 2 — Criar instrução HTML para novo algoritmo

```python
# 1. Em resources/instructions/html/HtmlInstructions_pt_BR.py:
class HtmlInstructions:
    # ... métodos existentes ...

    def get_meu_algoritmo_help(self):
        return f"""
            {self.provider.logo}
            Descricao do algoritmo.
            {self.provider.transform_h('Objetivo')}
            Objetivo 1.
            Objetivo 2.
            {self.provider.transform_h('Como usar')}
            1. Passo 1.
            2. Passo 2.
            {self.provider.transform_h('Saidas')}
            O que e gerado.
            {self.provider.transform_h('Atencoes')}
            Cuidado 1.
            {self.provider.author_info}
        """

# 2. O provider carrega automaticamente via:
#    provider = HtmlInstructionsProvider(tool_key)
#    html = provider.get_instructions("meu_algoritmo")
```

---

## Casos de Uso

- Quando um novo plugin é criado → criar `resources/instructions/pt_BR/<tool_key>_help.md` seguindo o padrão markdown (com metadados)
- Quando um novo algoritmo de processing é criado → adicionar método `get_<algorithm_name>_help` em `HtmlInstructions_<locale>.py`
- Quando um locale novo é adicionado → criar `HtmlInstructions_<locale>.py` com todos os métodos existentes
- Quando o conteúdo de ajuda precisa ser atualizado → editar o arquivo .md ou o método HTML correspondente, **atualizando a `Data da ultima modificacao`**
- Quando a ferramenta muda de comportamento → atualizar os arquivos .md em todos os locales existentes (`pt_BR`, `en`, `es`, `de`, `ja`), **atualizando a `Data da ultima modificacao` de cada um**

---

## Dependências

| Módulo | Caminho | Responsabilidade |
|--------|---------|-----------------|
| `InstructionsManager` | `resources/InstructionsManager.py` | Resolução de arquivos .md por tool_key e locale |
| `HtmlInstructionsProvider` | `resources/HtmlInstructionsProvider.py` | Carregamento dinâmico de módulos HTML e helpers de formatação |
| `HtmlInstructions_pt_BR` | `resources/instructions/html/HtmlInstructions_pt_BR.py` | Métodos de instrução HTML para locale pt_BR |
| `IconManager` | `resources/IconManager.py` | Resolução de caminhos de imagens (logo) |
| `LogUtils` | `core/config/LogUtils.py` | Logging estruturado |
| `TM` | `i18n/TranslationManager.py` | Locale atual do usuário |
| `BasePluginMTL` | `plugins/BasePlugin.py` | Integração com show_info_dialog() |
| `InfoDialog` | `core/ui/info_dialog.py` | Exibição de instruções .md em diálogo |

---

## Limitações

- `InstructionsManager` só busca no locale atual e pt_BR — não há fallchain completa para todos os locales
- `HtmlInstructionsProvider` requer que o método `get_<name>_help` exista exatamente com o nome esperado — sem isso, retorna fallback genérico
- Não há validação automática de que todo tool_key tem um arquivo .md correspondente
- O cache de `InstructionsManager` não é invalidado durante a sessão — se o arquivo for criado após o primeiro acesso, não será detectado
- Os metadados (versão, datas) são manuais — não há validação automática de que foram atualizados

---

## Validação

| Critério | Status |
|----------|--------|
| Reutilizável? | ✅ Sistema genérico, qualquer ferramenta pode usar ambos os mecanismos |
| Clara? | ✅ Separação clara: .md para plugins, HTML para algoritmos |
| Independente de contexto oculto? | ✅ Depende apenas de tool_key e locale, ambos explícitos |

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-20 | 1.0.0 | Criação via SKILL_FACTORY — lidos: resources/InstructionsManager.py, resources/HtmlInstructionsProvider.py, resources/instructions/html/HtmlInstructions_pt_BR.py, plugins/BasePlugin.py |
| 2026-08-07 | 1.1.0 | Instruções do ExportAllLayouts atualizadas (seleção de layouts, DPI, SVG) em pt_BR, en, es, de + novo arquivo ja/export_all_layouts_help.md. |
| 2026-08-10 | 1.3.0 | Adicionada regra de metadados obrigatórios nos arquivos .md (Versao, Data de criacao, Data da ultima modificacao). Instruções do ExportAllLayouts atualizadas com metadados em todos os locales. |
| 2026-08-10 | 1.4.0 | Novas instruções do PathExtension (path_extension_tool_help.md) em pt_BR, en, es, de, ja — lidos: plugins/PathExtensionPlugin.py, core/engine_tasks/PathExtensionStep.py, core/task/PathExtensionTask.py, docs/plano_acao_path_extension.md |
