---
name: toolregistry-plugins
description: >
  Criar, registrar, revisar ou refatorar ferramentas do tipo plugin no Cadmus
  usando a arquitetura ToolRegistry -> Tool -> MenuManager. Use esta skill
  quando a tarefa envolver adicionar uma nova ferramenta de menu/toolbar,
  corrigir registro de plugin, ajustar main_action/category/order/executor,
  ou garantir que um plugin dialog/map tool/instant siga o contrato do sistema.
  Esta skill cobre apenas ferramentas registradas como plugin no ToolRegistry;
  ferramentas provider/processing ficam fora do escopo.
---

# ToolRegistry Plugins

## Missão

Implementar ferramentas plugin do Cadmus do jeito correto, respeitando:

- registro canônico em `core/config/ToolRegistry.py`
- materialização de UI em menu/toolbar por `core/config/MenuManager.py`
- contrato de ferramenta em `core/model/Tool.py`
- contrato de plugin em `docs/skills/PLUGIN_CONTRACT.md`

Esta skill é para ferramentas de interface registradas no `ToolRegistry`.
Não usar para provider/processing.

## Ler Primeiro

Antes de alterar qualquer ferramenta, ler estes arquivos:

- `docs/skills/PLUGIN_CONTRACT.md`
- `core/config/ToolRegistry.py`
- `core/config/MenuManager.py`
- `core/model/Tool.py`
- `plugins/BasePlugin.py`
- `utils/ToolKeys.py`

Ler também, se necessário:

- `docs/skills/SKILL_WIDGET_ENGINE.md` para UI via `WidgetFactory`
- `docs/skills/SKILL_PREFERENCES.md` para persistência
- `docs/skills/SKILL_I18N.md` para `STR`

## Modelo Mental

Pensar em 4 camadas:

1. `ToolRegistry` define o catálogo oficial de ferramentas.
2. `Tool` carrega a metadata mínima para menu/toolbar.
3. `MenuManager` transforma esse catálogo em `QAction`, submenus e dropdowns da toolbar.
4. O plugin real executa pela função/classe chamada no `executor`.

Se a ferramenta não está no `ToolRegistry`, ela não existe para o menu/toolbar.

## Fluxo Real de Registro

### Fase 1 - Criar a identidade da ferramenta

Adicionar ou reutilizar:

- `ToolKey` em `utils/ToolKeys.py`
- strings `STR.*`
- ícone em `IconManager` se a ferramenta for nova

Sem `ToolKey`, não há rastreio de logs, prefs nem registro estável.

### Fase 2 - Implementar o plugin

Ferramentas plugin devem seguir o contrato normal:

- herdar de `BasePluginMTL` quando for dialog ou instant
- usar `self.init(...)`
- usar `WidgetFactory` para UI
- carregar/salvar prefs com `Preferences`
- expor ponto de entrada `run(iface)` para dialogs

Padrão esperado para dialog:

```python
def run(iface):
    dlg = MyPlugin(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg
```

Para ferramenta instantânea, o `ToolRegistry` pode instanciar a classe e chamar um método, mas o ciclo ainda deve passar por `BasePluginMTL`.

### Fase 3 - Registrar no ToolRegistry

Adicionar a `Tool(...)` na categoria correta dentro de `_create_tool_list()`.

Campos obrigatórios na prática:

- `tool_key`
- `name`
- `icon`
- `category`
- `tool_type`
- `main_action`
- `executor`
- `tooltip`
- `order`
- `show_in_toolbar`

Exemplo fiel ao padrão:

```python
my_tool = Tool(
    tool_key=ToolKey.MY_PLUGIN,
    name=STR.MY_PLUGIN_TITLE,
    icon=im.icon(im.MY_PLUGIN),
    category=self.VECTOR,
    tool_type=ToolTypeEnum.DIALOG,
    main_action=self._main_action_prefs.get(ToolKey.MY_PLUGIN, False),
    executor=self.run_my_plugin,
    tooltip=STR.MY_PLUGIN_TOOLTIP,
    order=70,
    show_in_toolbar=True,
)
tools.append(my_tool)
```

Depois criar o método executor em `ToolRegistry`:

```python
def run_my_plugin(self):
    try:
        from ...plugins.MyPlugin import run

        self.logger.info("Abrindo diálogo: Minha Ferramenta")
        self.my_plugin_dlg = run(self.iface)
        self.logger.info("Diálogo Minha Ferramenta aberto com sucesso")
    except Exception as e:
        self.logger.error(f"Erro ao executar Minha Ferramenta: {str(e)}")
        QgisMessageUtil.bar_critical(
            self.iface, f"Erro no plugin Minha Ferramenta:\n{str(e)}"
        )
```

### Fase 4 - Entender o que o MenuManager fará

`MenuManager`:

- cria uma `QAction` para cada `Tool`
- conecta `tool.action.triggered` ao `executor`
- adiciona todas as ferramentas ao submenu da categoria por `order`
- monta a toolbar usando a ferramenta `main_action=True` como botão principal
- coloca as outras da mesma categoria como dropdown secundário

Consequência: por categoria deve existir exatamente uma `main_action=True`.

## Regras de Registro

### Sempre

- Registrar ferramentas plugin apenas em `ToolRegistry._create_tool_list()`.
- Usar `ToolTypeEnum` compatível com o comportamento real.
- Manter `order` estável e sem colisões desnecessárias na mesma categoria.
- Guardar a referência do dialog/plugin em `self.<nome>` dentro do executor do registry.
- Usar `run(iface)` para dialogs, porque o registry espera esse padrão em várias ferramentas.
- Deixar `main_action` vir de `self._main_action_prefs.get(...)`.
- Garantir `show_in_toolbar=True` somente se a ferramenta deve aparecer no dropdown da categoria.
- Tratar erro no executor com `logger` + `QgisMessageUtil.bar_critical(...)`.

### Nunca

- Não registrar plugin direto no `MenuManager`.
- Não criar `QAction` manual para ferramenta nova fora do fluxo `ToolRegistry -> MenuManager`.
- Não usar string solta no lugar de `ToolKey`.
- Não marcar duas ferramentas da mesma categoria como `main_action=True` por padrão.
- Não esquecer o método executor correspondente no `ToolRegistry`.
- Não chamar o plugin no `executor` sem manter referência em `self`, principalmente dialogs e map tools.
- Não misturar ferramenta plugin com provider/processing nesta skill.

## Como Escolher o `tool_type`

- `ToolTypeEnum.DIALOG`: janela/dialog comum. É o caso mais frequente.
- `ToolTypeEnum.INSTANT`: ação imediata sem dialog principal.
- `ToolTypeEnum.MAP_TOOL`: ferramenta que ativa interação no canvas.

Se a ferramenta abre dialog, use `DIALOG`.
Se a ferramenta troca o estado do mapa, use `MAP_TOOL`.
Se a ferramenta executa diretamente, use `INSTANT`.

## Como Escolher a Categoria

Usar somente categorias vindas de `StringManager.MENU_CATEGORIES`, refletidas em:

- `ToolRegistry.SYSTEM`
- `ToolRegistry.LAYOUTS`
- `ToolRegistry.FOLDER`
- `ToolRegistry.VECTOR`
- `ToolRegistry.AGRICULTURE`
- `ToolRegistry.RASTER`

A categoria define:

- submenu onde a ação aparece
- agrupamento na toolbar
- escopo de `main_action`
- persistência de preferências por categoria

## Contrato de `main_action`

`ToolRegistry` é a fonte da verdade do botão principal de cada categoria.

O fluxo é:

1. cria lista inicial de tools
2. salva metadata (`category`, `tool_type`) nas prefs
3. valida prefs de `main_action`
4. recria a lista já com `main_action` corrigido

`_load_and_validate_main_actions_strict()` força exatamente uma ferramenta principal por categoria.

`MenuManager.create_toolbar()` depende disso para escolher o botão principal do dropdown.

Se a ferramenta abrir e precisar virar principal da categoria, usar `ToolRegistry.update_tool_main_action(...)` e depois reconstruir a toolbar pelo `MenuManager`.

## Checklist de Implementação

- Criar `ToolKey`
- Criar strings `STR`
- Garantir ícone
- Implementar plugin com `BasePluginMTL`
- Expor `run(iface)` se for dialog
- Registrar `Tool(...)` em `_create_tool_list()`
- Criar `run_<tool>()` no `ToolRegistry`
- Confirmar categoria, `tool_type`, `order`, `main_action`
- Confirmar que a ferramenta aparece no submenu correto
- Confirmar que a toolbar da categoria continua com uma única main action

## Checklist de Revisão

Ao revisar uma nova ferramenta, procurar estes erros primeiro:

- `ToolKey` inexistente ou string hardcoded
- `executor` aponta para método inexistente
- plugin sem `run(iface)` quando o executor espera isso
- `main_action` hardcoded fora de `self._main_action_prefs.get(...)`
- categoria errada
- `tool_type` não bate com o comportamento real
- dialog sem referência persistida em `self`
- UI criada fora do `WidgetFactory`
- prefs/logs fora dos contratos

## Exemplo de Fluxo Completo

```python
# 1. ToolKeys.py
class ToolKey:
    MY_PLUGIN = "my_plugin"
```

```python
# 2. plugins/MyPlugin.py
class MyPlugin(BasePluginMTL):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.init(ToolKey.MY_PLUGIN, "MyPlugin")

def run(iface):
    dlg = MyPlugin(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg
```

```python
# 3. ToolRegistry.py
my_tool = Tool(
    tool_key=ToolKey.MY_PLUGIN,
    name=STR.MY_PLUGIN_TITLE,
    icon=im.icon(im.MY_PLUGIN),
    category=self.VECTOR,
    tool_type=ToolTypeEnum.DIALOG,
    main_action=self._main_action_prefs.get(ToolKey.MY_PLUGIN, False),
    executor=self.run_my_plugin,
    tooltip=STR.MY_PLUGIN_TOOLTIP,
    order=70,
    show_in_toolbar=True,
)
tools.append(my_tool)

def run_my_plugin(self):
    from ...plugins.MyPlugin import run
    self.my_plugin_dlg = run(self.iface)
```

## Escopo Deliberadamente Fora

Esta skill não cobre:

- algoritmos provider/processing
- provider registration
- `processing.execAlgorithmDialog(...)`
- contratos específicos de `BaseProcessingAlgorithm`

Se a demanda cair em processing, usar outra skill/documentação apropriada.

## Critério de Sucesso

A skill foi seguida corretamente quando a nova ferramenta:

- aparece no submenu certo
- aparece corretamente na toolbar da categoria
- não quebra a unicidade de `main_action`
- usa o ciclo de vida padrão de plugin
- registra logs/prefs com `ToolKey`
- pode ser mantida sem exceções arquiteturais
