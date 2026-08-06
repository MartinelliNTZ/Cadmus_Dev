# 📋 Plano de Ação — RasterSamplerTool (Map Tool de Amostragem de Rasters)

## 🎯 Objetivo

Criar uma **map tool** que permite ao usuário:

1. **Selecionar múltiplos rasters** (camadas raster do projeto) na dialog da ferramenta.
2. **Persistir** os rasters selecionados nas preferências (`Preferences`) e **recarregá-los** automaticamente ao reabrir a ferramenta.
3. Ao **clicar em um ponto no canvas**, a dialog exibe o **valor de cada raster** naquele ponto (ex: 3 rasters → 3 valores).

---

## 🧩 Arquitetura (padrão CoordClickTool)

```
ToolRegistry (MAP_TOOL)
  └─ executor: run_raster_sampler()
      └─ plugins/RasterSamplerTool.py (QgsMapTool)
          ├─ canvasReleaseEvent() → coleta ponto
          ├─ lê rasters selecionados (prefs + camadas do projeto)
          ├─ amostra valor de cada raster no ponto (main thread)
          └─ cria/atualiza plugins/RasterSamplerDialog.py (BasePluginMTL)
              └─ GridComplexSelector (seleção de rasters)
              └─ GridReadOnly (exibição dos valores)
```

**Fluxo (espelha `CoordClickTool`):**

1. Usuário ativa a ferramenta → `RasterSamplerTool` é setada no canvas (`setMapTool`).
2. A dialog `RasterSamplerDialog` (herda `BasePluginMTL`) abre com seletor de rasters.
3. Usuário seleciona N rasters → salvos em `Preferences` via `save_tool_prefs`.
4. Usuário clica no canvas → `canvasReleaseEvent()` captura o ponto.
5. Para cada raster selecionado, amostra o valor no ponto (via `QgsRasterLayer.dataProvider().sample()`).
6. Dialog atualiza os campos com os valores (ex: 3 rasters → 3 valores).

---

## 📁 Arquivos Envolvidos

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `utils/ToolKeys.py` | **Editar** | Adicionar `ToolKey.RASTER_SAMPLER` |
| `i18n/Strings_pt_BR.py` | **Editar** | Strings da ferramenta (título, tooltip) — reutilizar genéricas existentes |
| `plugins/RasterSamplerTool.py` | **Criar** | Map tool (herda `QgsMapTool`, padrão `CoordClickTool`) |
| `plugins/RasterSamplerDialog.py` | **Criar** | Dialog (herda `BasePluginMTL`, padrão `CoordResultDialog`) |
| `core/config/ToolRegistry.py` | **Editar** | Registrar `Tool(...)` com `tool_type=MAP_TOOL` + executor |
| `resources/IconManager.py` | **Editar** | Ícone da ferramenta (se necessário) |
| `docs/ia/changelog.txt` | **Editar** | Registrar mudança |

---

## 🛠️ Implementação

### 1. ToolKey

Em `utils/ToolKeys.py`:

```python
class ToolKey:
    RASTER_SAMPLER = "raster_sampler"
```

### 2. Strings (Strings_pt_BR)

**Reutilizar strings genéricas existentes** (não duplicar):

| String existente | Uso |
|------------------|-----|
| `STR.RASTERS` | Título do seletor de rasters |
| `STR.SAMPLED_VALUES` | Título do bloco de valores amostrados |
| `STR.INPUT_POINTS` | Descrição do seletor |
| `STR.LOADING` | Valor enquanto carrega |
| `STR.UNAVAILABLE` | Valor quando NoData/indisponível |
| `STR.CLOSE` / `STR.INFO` | Botões |

**Novas strings (apenas as específicas da ferramenta):**

```python
# plugins/RasterSamplerTool.py
RASTER_SAMPLER_TITLE = "Amostrar Valores de Rasters"
RASTER_SAMPLER_TOOLTIP = (
    "Seleciona camadas raster do projeto e permite clicar no mapa\n"
    "para consultar o valor de cada raster no ponto clicado.\n"
    "Os rasters selecionados são lembrados entre sessões\n"
    "e os valores são exibidos na dialog da ferramenta."
)
```

### 3. RasterSamplerDialog (BasePluginMTL)

Herda de `BasePluginMTL` (padrão `CoordResultDialog`), **não** `BaseDialog`:

```python
class RasterSamplerDialog(BasePluginMTL):
    TOOL_KEY = ToolKey.RASTER_SAMPLER

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.init(
            tool_key=self.TOOL_KEY, class_name="RasterSamplerDialog", build_ui=True
        )
```

**UI (`_build_ui`):**
- `GridComplexSelector` com `layer_filters=QgsMapLayerProxyModel.RasterLayer` + `multiple=True` para selecionar os rasters.
- `GridReadOnly` com um campo por raster selecionado (título = nome da camada, valor = valor amostrado).
- `GridExecutionButtons` (Fechar + Info).
- `_load_prefs()` / `_save_prefs()` para persistir os rasters selecionados (lista de `layer.id()`).

**API pública:**
- `set_raster_values(values: dict)` — atualiza os campos com `{layer_id: valor}`.
- `get_selected_raster_ids()` → `list[str]` — rasters selecionados.
- `set_selected_raster_ids(ids)` — restaura seleção das prefs.

### 4. RasterSamplerTool (QgsMapTool)

Herda `QgsMapTool` (padrão `CoordClickTool`):

```python
class RasterSamplerTool(QgsMapTool):
    def __init__(self, iface):
        super().__init__(iface.mapCanvas())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.dialog = None
        self.logger = LogUtils(
            tool=ToolKey.RASTER_SAMPLER, class_name="RasterSamplerTool"
        )
```

**`canvasReleaseEvent(event)`:**
1. Converte `event.pos()` → coordenadas do mapa (`toMapCoordinates`).
2. Obtém os rasters selecionados da dialog (`get_selected_raster_ids()`).
3. Para cada raster, converte o ponto para o CRS do raster (`QgsCoordinateTransform`) e chama `raster.dataProvider().sample(point, 1)`.
4. Atualiza a dialog com `set_raster_values({layer_id: valor})`.
5. Se a dialog não existe/não está visível, cria/atualiza (padrão `CoordClickTool`).

**Amostragem no main thread** — operação leve (< 1s), manipula objetos C++ do QGIS. **Não** usar pipeline assíncrona.

### 5. ToolRegistry

```python
raster_sampler = Tool(
    tool_key=ToolKey.RASTER_SAMPLER,
    name=STR.RASTER_SAMPLER_TITLE,
    icon=im.icon(im.RASTER_SAMPLER),
    category=self.RASTER,
    tool_type=ToolTypeEnum.MAP_TOOL,
    main_action=self._main_action_prefs.get(ToolKey.RASTER_SAMPLER, False),
    executor=self.run_raster_sampler,
    tooltip=STR.RASTER_SAMPLER_TOOLTIP,
    order=80,
    show_in_toolbar=True,
)
tools.append(raster_sampler)
```

Executor (mantém referência em `self`):

```python
def run_raster_sampler(self):
    try:
        from ...plugins.RasterSamplerTool import RasterSamplerTool
        self.logger.info("Ativando ferramenta: Amostrar Valores de Rasters")
        self.raster_sampler_tool = RasterSamplerTool(self.iface)
        self.iface.mapCanvas().setMapTool(self.raster_sampler_tool)
        self.logger.info("Map tool Amostrar Valores de Rasters ativada")
    except Exception as e:
        self.logger.error(f"Erro ao ativar Amostrar Valores de Rasters: {str(e)}")
        QgisMessageUtil.bar_critical(
            self.iface, f"Erro na ferramenta Amostrar Valores de Rasters:\n{str(e)}"
        )
```

---

## 📌 Contratos Respeitados

| Contrato | Como |
|----------|------|
| UI via widgets | `GridComplexSelector` + `GridReadOnly` + `GridExecutionButtons` (nunca QtWidgets direto) |
| Logging | `LogUtils` com `ToolKey.RASTER_SAMPLER` (nunca print) |
| Strings | `STR.*` — reutilizar genéricas (`RASTERS`, `SAMPLED_VALUES`, `LOADING`, `UNAVAILABLE`) |
| ToolKey | Enum `ToolKey.RASTER_SAMPLER` (nunca string) |
| Estilos | Widgets autoconfiguráveis (nunca setStyleSheet) |
| Exceções | `logger.exception` (nunca `except: pass`) |
| Configurações | `Preferences.load_tool_prefs` / `save_tool_prefs` |
| Registro | `ToolRegistry._create_tool_list()` |
| Executor | Mantém referência em `self.raster_sampler_tool` |
| Map tool | Herda `QgsMapTool` (padrão `CoordClickTool`) |
| Dialog | Herda `BasePluginMTL` (padrão `CoordResultDialog`) |

---

## ⚠️ Considerações Técnicas

- **Amostragem no main thread**: `QgsRasterLayer.dataProvider().sample()` é operação leve (< 1s) e deve rodar no main thread (dentro de `canvasReleaseEvent`), pois manipula objetos C++ do QGIS. **Não** usar pipeline assíncrona.
- **Persistência**: salvar os rasters selecionados como lista de `layer.id()` nas prefs. Ao reabrir, validar se as camadas ainda existem no projeto (`QgsProject.instance().mapLayer(id)`).
- **CRS**: converter o ponto clicado para o CRS de cada raster antes de amostrar (`QgsCoordinateTransform`).
- **Valores NoData**: tratar `None`/NoData como `STR.UNAVAILABLE` no campo.
- **Compatibilidade**: QGIS 3.16+ até 4.99, Qt5/Qt6, Python 3.10+.

---

## ✅ Checklist de Implementação

- [ ] Criar `ToolKey.RASTER_SAMPLER`
- [ ] Criar strings `STR.RASTER_SAMPLER_TITLE` + `STR.RASTER_SAMPLER_TOOLTIP` (reutilizar genéricas)
- [ ] Garantir ícone em `IconManager`
- [ ] Criar `RasterSamplerDialog` (BasePluginMTL + GridComplexSelector + GridReadOnly)
- [ ] Criar `RasterSamplerTool` (QgsMapTool + canvasReleaseEvent + sample)
- [ ] Registrar `Tool(...)` em `_create_tool_list()` (MAP_TOOL, categoria RASTER)
- [ ] Criar `run_raster_sampler()` no `ToolRegistry`
- [ ] Persistir/carregar rasters selecionados via `Preferences`
- [ ] Atualizar `docs/ia/changelog.txt`
- [ ] Atualizar skill relevante (se necessário)