---
name: utils
description: >
  Central de utilitários do Cadmus. Use esta skill para entender, estender ou integrar funções utilitárias do plugin. Sempre consulte antes de criar helpers ou manipular arquivos, strings, camadas ou preferências.
---

# Utils

## Resumo Executivo

**Utils** é o núcleo de utilitários do Cadmus, responsável por:
- Navegação, manipulação e validação de arquivos e pastas
- Operações de string, formatação e tradução
- Gerenciamento de preferências do usuário
- Gerenciamento de dependências Python
- Operações seguras com camadas vetoriais e raster
- Emissão de mensagens ao usuário (via QgisMessageUtil)
- Centralização de chaves de ferramentas (ToolKey)

---

## Objetivo

Facilitar tarefas comuns e recorrentes do plugin, garantindo padronização, rastreabilidade e segurança nas operações de baixo nível. Utilizado por todas as ferramentas e serviços do Cadmus.

---

## Entradas

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| tool_key | str | Não | Identificador externo para logs/preferences (obrigatório para logs e preferências) |
| path | str | Não | Caminho de arquivo ou pasta |
| payload | dict/obj | Não | Dados para operações de serialização |
| layer | QgsVectorLayer/QgsRasterLayer | Não | Camada para operações de I/O |

---

## Saídas

| Campo | Tipo | Descrição |
|-------|------|-----------|
| resultado | vários | Depende do método chamado (bool, str, camada, etc.) |
| logs | LogUtils | Logs rastreáveis por tool_key |
| mensagens | QgisMessageUtil | Mensagens ao usuário (nunca usar print) |

---

## Classes e Responsabilidades

| Classe | Responsabilidade |
|--------|-----------------|
| ExplorerUtils | Navegação, manipulação e validação de arquivos/pastas. Só ela pode abrir arquivos/pastas no SO. |
| VectorLayerSource | Operações de I/O, validação e clonagem de camadas vetoriais. Só ela pode explorar arquivos vetoriais. |
| RasterLayerSource | Operações de I/O, validação e clonagem de camadas raster. Só ela pode explorar arquivos raster. |
| ProjectUtils | Toda manipulação de QgsProject (abrir, salvar, backup, layers). Só ela pode tocar QgsProject. |
| QgisMessageUtil | Único meio de emitir mensagens para o usuário. Nunca usar print/log para usuário. |
| ToolKey | CPF das ferramentas. Toda ferramenta precisa de um ToolKey. Utils/serviços são "escravos" e precisam de tool_key externo. |
| Preferences | Preferências do usuário. Tudo que for possível deve ser salvo nas preferências. |
| FormatUtils | Formatação de strings, tamanhos, tempo, velocidade. Sempre usar para exibir valores ao usuário. |
| StringManager | Central de filtros, extensões e traduções de strings. |
| DependenciesManager | Gerenciamento e validação de dependências Python. |

---

## Processamento

### Fase 1 — Navegação e Manipulação de Arquivos

```python
# Exemplo: abrir pasta no SO
ExplorerUtils.open_folder(folder_path, tool_key=ToolKey.SYSTEM)
```

### Fase 2 — Operações com Camadas

```python
# Exemplo: salvar camada vetorial
VectorLayerSource.save_vector_layer(layer, output_path=path, external_tool_key=ToolKey.EXPORT_ALL_LAYOUTS)
```

### Fase 3 — Preferências

```python
# Exemplo: salvar preferências
Preferences.save_tool_prefs(ToolKey.EXPORT_ALL_LAYOUTS, {"last_folder": folder})
```

### Fase 4 — Mensagens ao Usuário

```python
# Exemplo: exibir mensagem
QgisMessageUtil.bar_info(iface, "Processo concluído com sucesso!")
```

---

## Regras

### ✅ Sempre:
- Usar ExplorerUtils para manipular arquivos/pastas
- Usar VectorLayerSource/RasterLayerSource para explorar arquivos de camada
- Usar ProjectUtils para manipular QgsProject
- Usar QgisMessageUtil para mensagens ao usuário
- Usar ToolKey para logs/preferences
- Salvar tudo que for possível nas preferências
- Usar FormatUtils para exibir valores ao usuário
- Nome do arquivo .py deve ser igual ao nome da classe

### ❌ Nunca:
- Manipular QgsProject fora de ProjectUtils
- Emitir mensagens ao usuário fora de QgisMessageUtil
- Usar print/log para mensagens ao usuário
- Criar helpers duplicados já existentes em utils
- Salvar preferências fora de Preferences
- Explorar arquivos/camadas fora das classes autorizadas

---

## Padrões de Uso

### Padrão 1 — Abrir pasta

```python
ExplorerUtils.open_folder("C:/dados", tool_key=ToolKey.SYSTEM)
```

### Padrão 2 — Salvar camada vetorial

```python
VectorLayerSource.save_vector_layer(layer, output_path="/tmp/layer.gpkg", external_tool_key=ToolKey.EXPORT_ALL_LAYOUTS)
```

### Padrão 3 — Mensagem ao usuário

```python
QgisMessageUtil.bar_info(iface, "Arquivo salvo com sucesso!")
```

---

## Casos de Uso

- Quando uma ferramenta precisa abrir pasta/arquivo → usar ExplorerUtils
- Quando precisa salvar/caregar camada vetorial → usar VectorLayerSource
- Quando precisa salvar/caregar camada raster → usar RasterLayerSource
- Quando precisa manipular projeto QGIS → usar ProjectUtils
- Quando precisa exibir mensagem ao usuário → usar QgisMessageUtil
- Quando precisa salvar preferências → usar Preferences
- Quando precisa formatar valores → usar FormatUtils

---

## Dependências

| Módulo | Caminho | Responsabilidade |
|--------|---------|-----------------|
| ExplorerUtils | utils/ExplorerUtils.py | Navegação e manipulação de arquivos/pastas |
| VectorLayerSource | utils/vector/VectorLayerSource.py | I/O de camadas vetoriais |
| RasterLayerSource | utils/raster/RasterLayerSource.py | I/O de camadas raster |
| ProjectUtils | utils/ProjectUtils.py | Manipulação de QgsProject |
| QgisMessageUtil | utils/QgisMessageUtil.py | Mensagens ao usuário |
| ToolKey | utils/ToolKeys.py | Identificação de ferramentas |
| Preferences | utils/Preferences.py | Preferências do usuário |
| FormatUtils | utils/FormatUtils.py | Formatação de strings |
| StringManager | utils/StringManager.py | Tradução e filtros de strings |
| DependenciesManager | utils/DependenciesManager.py | Dependências Python |

---

## Exemplos Completos

### Exemplo 1 — Abrir arquivo e salvar preferências

```python
from .utils.ExplorerUtils import ExplorerUtils
from .utils.Preferences import Preferences
from .utils.ToolKeys import ToolKey

file_path = ExplorerUtils.open_file("C:/dados/relatorio.pdf", tool_key=ToolKey.SYSTEM)
Preferences.save_tool_prefs(ToolKey.SYSTEM, {"last_file": file_path})
```

### Exemplo 2 — Salvar camada vetorial e exibir mensagem

```python
from .utils.vector.VectorLayerSource import VectorLayerSource
from .utils.QgisMessageUtil import QgisMessageUtil
from .utils.ToolKeys import ToolKey

saved = VectorLayerSource.save_vector_layer(layer, output_path="/tmp/layer.gpkg", external_tool_key=ToolKey.EXPORT_ALL_LAYOUTS)
if saved:
    QgisMessageUtil.bar_success(iface, "Camada salva com sucesso!")
```

---

## Limitações

- Não manipula lógica de negócio, apenas operações utilitárias
- Não deve ser usada para criar helpers duplicados
- Não manipula QgsProject fora de ProjectUtils
- Não emite mensagens ao usuário fora de QgisMessageUtil

---

## Validação

| Critério | Status |
|----------|--------|
| Reutilizável? | ✅ Sempre chamada por ferramentas/serviços |
| Clara? | ✅ Responsabilidades explícitas por classe |
| Independente de contexto oculto? | ✅ Não depende de contexto externo |

---

## Histórico de Mudanças

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-04-20 | 1.0.0 | Criação via SKILL_FACTORY — lidos: utils/ExplorerUtils.py, utils/vector/VectorLayerSource.py, utils/raster/RasterLayerSource.py, utils/ProjectUtils.py, utils/QgisMessageUtil.py, utils/ToolKeys.py, utils/Preferences.py, utils/FormatUtils.py, utils/StringManager.py, utils/DependenciesManager.py |


CONTINUAR
otimo otimo, porem vc so excreveu oque eu disse nochat, vc precisa de contexto, enriqueca esse .md com dados direto das classes, leia os arquivos da pasyta crie um campo com todas as classes disponiveies e suas responsabilidades definidas