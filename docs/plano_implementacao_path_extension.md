# 📋 Plano de Implementação: Ferramenta "Remover/Restaurar Extensão de Paths"

## Análise dos Requisitos

A ferramenta opera em 2 modos:
- **Cenário 1 - Eliminar Extensão**: `foto.jpg` → `fotojpg` (remove o `.` do nome do arquivo)
- **Cenário 2 - Restaurar Extensão**: `fotojpg` → `foto.jpg` (verifica no sistema de arquivos qual a extensão real e restaura)

**Características:**
- Recebe feições vetoriais de uma camada selecionada pelo usuário
- Atributo Path (default se existir, senão usuário seleciona)
- Cria/atualiza campo `NewPath` na camada ORIGINAL (sem copiar)
- Processamento em background via `AsyncPipelineEngine` (Step → Task)
- Registro como plugin DIALOG no `ToolRegistry` (categoria VECTOR) usando `_make_plugin_executor`
- UI via `WidgetFactory` conforme contrato
- Strings genéricas reutilizando STR existentes

---

## Arquivos a Criar/Modificar

### 1. 🔧 `utils/ToolKeys.py` — Adicionar ToolKey

```python
PATH_EXTENSION_TOOL = "path_extension_tool"
# Cor: #E67E22 (laranja)
```

### 2. 🔧 `i18n/Strings_pt_BR.py` — Apenas strings essenciais

Reaproveitar STR existentes: `INPUT_LAYER`, `ATTRIBUTES`, `OPTIONS`, `PROCESSING`, `SUCCESS_MESSAGE`, `ERROR`

Criar só:
```python
PATH_EXTENSION_TITLE = "Remover/Restaurar Extensão"
PATH_EXTENSION_TOOLTIP = "Remove ou restaura a extensão de arquivos nos paths das feições selecionadas"
MODE_REMOVE = "Remover extensão"
MODE_RESTORE = "Restaurar extensão"
```

### 3. 🔧 `resources/IconManager.py` — Adicionar ícone

```python
PATH_EXTENSION = "path_extension.ico"
```

### 4. 🆕 `plugins/PathExtensionPlugin.py` — Plugin DIALOG

Herda `BasePluginMTL`:
- `_build_ui()`: seletor de camada, combo de atributos, combo modo (remover/restaurar), botão executar
- `execute_tool()`: dispara pipeline assíncrona
- `_load_prefs()` / `_save_prefs()` herdados + implementação

### 5. 🆕 `core/engine_tasks/PathExtensionStep.py` — Step

Implementa `BaseStep`:
- `name()` → "path_extension"
- `create_task()` → `PathExtensionTask`
- `on_success()` → atualiza contexto

### 6. 🆕 `core/task/PathExtensionTask.py` — Task

Herda `BaseTask`, implementa `_run()`:
- Modo REMOVER: tira o `.` da extensão (ex: `foto.jpg` → `fotojpg`)
- Modo RESTAURAR: insere `.` no lugar correto (ex: `fotojpg` → `foto.jpg`)
- Cria campo `NewPath` se não existe, edita in-place
- Trata paths com espaços e caracteres especiais

### 7. 🔧 `core/config/ToolRegistry.py` — Registrar

Usar `_make_plugin_executor("...plugins.PathExtensionPlugin")` (já resolve DIALOG automaticamente).

---

## Fluxo

```
Menu/Toolbar → ToolRegistry._make_plugin_executor → PathExtensionPlugin.run(iface)
  → Dialog (seleciona camada, atributo, modo)
    → AsyncPipelineEngine([PathExtensionStep], context)
      → PathExtensionTask._run()
        → Edita NewPath in-place na camada original
```

## Contratos

- ✅ PLUGIN_CONTRACT (WidgetFactory, LogUtils, STR, ToolKey)
- ✅ SKILL_TOOLREGISTRY_PLUGINS (registro canônico, _make_plugin_executor)
- ✅ SKILL_WIDGET_ENGINE (UI via factory)
- ✅ BaseStep / BaseTask / AsyncPipelineEngine
- ✅ BasePluginMTL ciclo de vida