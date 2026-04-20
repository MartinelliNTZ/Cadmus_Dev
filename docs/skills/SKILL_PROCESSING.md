---
name: processing-algorithm-pattern
description: >
  Padrão Cadmus para criação de algoritmos de processamento QGIS: carrega/salva preferências, usa STR para labels, configura instruções e ícone, nunca traduz strings durante dev, e só gera instruções ao final.
---

# Padrão de Algoritmo de Processamento Cadmus

## Resumo Executivo

**processing-algorithm-pattern** é um padrão para criar algoritmos de processamento no Cadmus que:
- Garante consistência visual e funcional entre ferramentas
- Centraliza carregamento/salvamento de preferências
- Usa STR para labels, mas só adiciona variáveis em Strings_pt_BR
- Configura arquivo de instruções e ícone, mas só gera instruções ao final
- Facilita extensão e manutenção de novos algoritmos

---

## Objetivo

Permitir que qualquer nova ferramenta de processamento siga um padrão robusto, garantindo integração com o ecossistema Cadmus, rastreabilidade de preferências, internacionalização futura e documentação consistente.

---

## Entradas

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| params | dict | Sim | Parâmetros do algoritmo, vindos do QGIS |
| context | QgsProcessingContext | Sim | Contexto de execução QGIS |
| feedback | QgsProcessingFeedback | Sim | Interface de feedback QGIS |

---

## Saídas

| Campo | Tipo | Descrição |
|-------|------|-----------|
| outputs | dict | Dicionário com saídas do algoritmo (paths, camadas, etc) |

---

## Processamento

### Fase 1 — Definição de Metadados

- Definir `TOOL_KEY` único em ToolKeys.py
- Definir `ALGORITHM_NAME`, `ALGORITHM_DISPLAY_NAME`, `ALGORITHM_GROUP`, `ICON`, `INSTRUCTIONS_FILE`
- Sempre usar STR para labels, mas adicionar variáveis apenas em Strings_pt_BR
- Configurar ícone com `cadmus_icon.ico` ou específico

```python
class MyAlgorithm(BaseProcessingAlgorithm):
    TOOL_KEY = ToolKey.MY_ALGORITHM
    ALGORITHM_NAME = "my_algorithm"
    ALGORITHM_DISPLAY_NAME = STR.MY_ALGORITHM_TITLE
    ALGORITHM_GROUP = BaseProcessingAlgorithm.GROUP_RASTER
    ICON = "cadmus_icon.ico"
```

### Fase 2 — Carregamento de Preferências

- Sempre chamar `self.load_preferences()` no início de `initAlgorithm`
- Preferências são lidas/salvas via `Preferences.load_tool_prefs` e `Preferences.save_tool_prefs`
- Nunca salvar preferências fora do método padrão

```python
def initAlgorithm(self, config=None):
    self.load_preferences()
    # ...definição dos parâmetros...
```

### Fase 3 — Definição de Parâmetros

- Usar STR para todos os labels de parâmetros
- Adicionar variáveis apenas em Strings_pt_BR durante desenvolvimento
- Não traduzir labels manualmente em outros idiomas

```python
self.addParameter(QgsProcessingParameterFeatureSource(
    self.INPUT_LAYER, STR.INPUT_LAYER_LABEL, [QgsProcessing.TypeVectorPoint]
))
```

### Fase 4 — Execução e Salvamento de Preferências

- Atualizar self.prefs ao final do processamento
- Salvar preferências com `self.save_preferences()`

```python
self.prefs.update({"last_output_folder": out_folder})
self.save_preferences()
```

### Fase 5 — Instruções e Ícone

- Configurar `ICON` na classe
- Nunca gerar ou editar arquivo de instruções durante o desenvolvimento
- Só criar/atualizar instruções ao finalizar e sob demanda
- Sempre usar `cadmus_icon.ico` ou ícone específico do algoritmo

---

## Regras

### ✅ Sempre:
- Definir TOOL_KEY único em ToolKeys.py
- Usar STR para labels, mas adicionar variáveis só em Strings_pt_BR
- Carregar/salvar preferências via métodos padrão
- Configurar ICON
- Usar BaseProcessingAlgorithm como base

### ❌ Nunca:
- Traduzir labels manualmente em outros idiomas durante dev
- Salvar preferências fora dos métodos padrão
- Gerar instruções antes da finalização
- Usar ícone fora do padrão Cadmus

---

## Padrões de Uso

### Padrão 1 — Novo Algoritmo

```python
from .BaseProcessingAlgorithm import BaseProcessingAlgorithm
from ..utils.ToolKeys import ToolKey
from ..i18n.TranslationManager import STR

class MyAlgorithm(BaseProcessingAlgorithm):
    TOOL_KEY = ToolKey.MY_ALGORITHM
    ALGORITHM_NAME = "my_algorithm"
    ALGORITHM_DISPLAY_NAME = STR.MY_ALGORITHM_TITLE
    ALGORITHM_GROUP = BaseProcessingAlgorithm.GROUP_RASTER
    ICON = "cadmus_icon.ico"
    INSTRUCTIONS_FILE = "my_algorithm.html"

    def initAlgorithm(self, config=None):
        self.load_preferences()
        self.addParameter(...)

    def processAlgorithm(self, params, context, feedback):
        # ...processamento...
        self.prefs.update({"last_output_folder": out_folder})
        self.save_preferences()
        return {self.OUTPUT: out_path}
```

---

## Casos de Uso

- Quando criar nova ferramenta → seguir este padrão para garantir integração
- Quando adicionar parâmetro → criar label só em Strings_pt_BR
- Quando finalizar ferramenta → gerar instruções HTML e traduzir

---

## Dependências

| Módulo | Caminho | Responsabilidade |
|--------|---------|-----------------|
| BaseProcessingAlgorithm | processing/BaseProcessingAlgorithm.py | Classe base, carrega/salva prefs, configura ícone/instruções |
| Preferences | utils/Preferences.py | Gerencia prefs por tool_key |
| ToolKeys | utils/ToolKeys.py | Enum de tool_keys únicos |
| STR | i18n/TranslationManager.py | Centraliza labels, usa Strings_pt_BR |
| IconManager | resources/IconManager.py | Resolve caminho do ícone |

---

## Exemplos Completos

### Exemplo 1 — Algoritmo Mínimo

```python
from .BaseProcessingAlgorithm import BaseProcessingAlgorithm
from ..utils.ToolKeys import ToolKey
from ..i18n.TranslationManager import STR

class MyAlgorithm(BaseProcessingAlgorithm):
    TOOL_KEY = ToolKey.MY_ALGORITHM
    ALGORITHM_NAME = "my_algorithm"
    ALGORITHM_DISPLAY_NAME = STR.MY_ALGORITHM_TITLE
    ALGORITHM_GROUP = BaseProcessingAlgorithm.GROUP_RASTER
    ICON = "cadmus_icon.ico"
    INSTRUCTIONS_FILE = "my_algorithm.html"

    def initAlgorithm(self, config=None):
        self.load_preferences()
        self.addParameter(...)

    def processAlgorithm(self, params, context, feedback):
        # ...processamento...
        self.prefs.update({"last_output_folder": out_folder})
        self.save_preferences()
        return {self.OUTPUT: out_path}
```

---

## Limitações

- Não cobre lógica de processamento, apenas padrão estrutural
- Não garante qualidade dos algoritmos, só padronização
- Instruções e traduções só ao final

---

## Validação

| Critério | Status |
|----------|--------|
| Reutilizável? | ✅ Sempre que seguir BaseProcessingAlgorithm |
| Clara? | ✅ Padrão explícito, exemplos reais |
| Independente de contexto oculto? | ✅ Não depende de variáveis globais |

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-04-20 | 1.0.0 | Criação via SKILL_FACTORY — lidos: provider.py, RasterMassClipper.py, RasterMassSampler.py, BaseProcessingAlgorithm.py, Preferences.py, ToolKeys.py, Strings_pt_BR.py, IconManager.py |
