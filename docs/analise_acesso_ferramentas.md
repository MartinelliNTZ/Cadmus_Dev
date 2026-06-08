# Análise de Arquitetura: Sistema de Níveis de Acesso para Ferramentas Cadmus

> **Data:** 2026-06-08  
> **Versão:** 1.0  
> **Objetivo:** Analisar a arquitetura atual e propor o melhor método para implementar níveis de acesso (access_level) às ferramentas do plugin Cadmus, com suporte a API key para distribuição condicional de ferramentas e graceful degradation.

---

## Sumário

1. [Contexto e Objetivos](#1-contexto-e-objetivos)
2. [Análise da Arquitetura Atual](#2-análise-da-arquitetura-atual)
3. [Estratégia Proposta: Sistema de Níveis de Acesso](#3-estratégia-proposta-sistema-de-níveis-de-acesso)
4. [Integração com API para Distribuição de Ferramentas](#4-integração-com-api-para-distribuição-de-ferramentas)
5. [Implementação no Model Tool](#5-implementação-no-model-tool)
6. [Implementação no ToolRegistry](#6-implementação-no-toolregistry)
7. [Implementação no MenuManager](#7-implementação-no-menumanager)
8. [Implementação no ReportMetadata / DroneCoordinates](#8-implementação-no-reportmetadata--dronecoordinates)
9. [Graceful Degradation (Ferramentas Ausentes)](#9-graceful-degradation-ferramentas-ausentes)
10. [API para Distribuição de Ferramentas](#10-api-para-distribuição-de-ferramentas)
11. [Fluxo Completo de Carregamento](#11-fluxo-completo-de-carregamento)
12. [Considerações sobre Armazenamento e Cache](#12-considerações-sobre-armazenamento-e-cache)
13. [Riscos e Mitigações](#13-riscos-e-mitigações)
14. [Recomendações Finais](#14-recomendações-finais)

---

## 1. Contexto e Objetivos

### 1.1 Situação Atual

O plugin Cadmus atualmente gerencia suas ferramentas através de um **ToolRegistry** (singleton) que cria instâncias da classe `Tool` com os seguintes atributos:

- `tool_key`, `name`, `icon`, `category`, `tool_type`, `main_action`, `executor`, `tooltip`, `order`, `show_in_toolbar`
- `action` (QAction, criado pelo MenuManager)

Todas as ferramentas são carregadas localmente no momento da inicialização do plugin e exibidas no menu e toolbar sem qualquer filtro de acesso.

### 1.2 Objetivos

1. **Implementar níveis de acesso** (access_level 1-5) para cada ferramenta
2. **Criar sistema de verificação por API key** para baixar ferramentas de níveis superiores
3. **Graveful degradation** — o plugin deve funcionar mesmo sem as ferramentas de níveis mais altos
4. **Filtrar relatórios** do DroneCoordinates/ReportMetadata com base no nível de acesso
5. **Persistência** do nível de acesso do usuário
6. **Interface de configuração** no SettingsPlugin ou dialog dedicado

---

## 2. Análise da Arquitetura Atual

### 2.1 Diagrama de Componentes Atual

```
cadmus_plugin.py (bootstrap)
    │
    ├──► ToolRegistry (singleton)
    │       ├── _create_tool_list() → lista de Tool[]
    │       ├── _save_tool_metadata() → salva category + tool_type nas prefs
    │       ├── _load_and_validate_main_actions_strict()
    │       └── get_tools() → retorna Tool[]
    │
    ├──► MenuManager
    │       ├── create_menu() → submenus por categoria
    │       ├── create_toolbar() → DropdownToolButton por categoria
    │       ├── populate_menus() → actions nos submenus
    │       └── reconstruct_toolbar() → rebuild dinâmico
    │
    └──► Processing Provider (algoritmos Processing)
```

### 2.2 Fluxo de Inicialização

1. `cadmus_plugin.py::initGui()` cria `ToolRegistry(iface)`
2. ToolRegistry constrói lista de `Tool` em `_create_tool_list()`
3. `MenuManager(iface, tools)` recebe tools e cria actions
4. `create_menu()`, `create_toolbar()`, `populate_menus()` montam UI
5. Preferences salva/recupera estado no arquivo `mtl_prefs.json`

### 2.3 Classe Tool (core/model/Tool.py)

```python
class Tool:
    def __init__(self, tool_key, name, icon, category, tool_type,
                 main_action=False, executor=None, tooltip=None,
                 order=100, show_in_toolbar=True):
        self.tool_key = tool_key
        self.name = name
        self.icon = icon
        self.category = category
        self.tool_type = tool_type
        self.main_action = main_action
        self.executor = executor
        self.tooltip = tooltip
        self.order = order
        self.show_in_toolbar = show_in_toolbar
        self.action = None  # QAction, criado pelo MenuManager
```

**Observação crucial:** Não há campo `access_level` nem `available` (disponível/não disponível).

### 2.4 ToolRegistry (core/config/ToolRegistry.py)

- Singleton armazenado em `_instance`
- `_create_tool_list()` cria ~25 ferramentas manualmente com `Tool(...)`
- Cada ferramenta tem `executor` que importa dinamicamente o módulo do plugin:
  - `_make_plugin_executor("...plugins.ExportAllLayouts")` → importa módulo e chama `run(iface)`
  - `_make_provider_executor("cadmus:raster_mass_clipper", nome)` → `processing.execAlgorithmDialog()`
- `get_tools()` retorna lista de tools

### 2.5 MenuManager (core/config/MenuManager.py)

- `_create_actions_for_tools()`: para cada tool, cria QAction e conecta `tool.executor` ao signal
- `create_toolbar()`: filtra por `t.main_action and t.show_in_toolbar` para criar dropdowns
- `populate_menus()`: adiciona todas as tools nos submenus
- `reconstruct_toolbar()`: recombina toolbar com novos estados
- **Importante:** atualmente NÃO há filtro por nível de acesso

### 2.6 CadmusPlugin (cadmus_plugin.py)

```python
self.tool_registry = ToolRegistry(self.iface)
tools = self.tool_registry.tools
self.menu_manager = MenuManager(self.iface, tools, self.logger)
self.menu_manager.create_menu()
self.menu_manager.create_toolbar()
self.menu_manager.populate_menus()
```

### 2.7 Preferences (utils/Preferences.py)

- JSON único: `{tool_key: {pref1: val1, ...}, ...}`
- `save_tool_prefs(tool_key, dict)` / `load_tool_prefs(tool_key)`
- `set_value_for_all_tools(pref_key, value, filter_by)` — já suporta filtro por `category`

---

## 3. Estratégia Proposta: Sistema de Níveis de Acesso

### 3.1 Definição dos Níveis

| Nível | Nome | Descrição | Exemplos de Ferramentas |
|-------|------|-----------|------------------------|
| 1 | **FREE / Básico** | Ferramentas core, sempre disponíveis | Export All Layouts, Replace In Layouts, Settings, Restart QGIS, About, Load Folder Layers |
| 2 | **STANDARD / Padrão** | Funcionalidades intermediárias | Vector Fields, Coord Click, Copy Attributes, Convert Multipart, Remove KML Fields |
| 3 | **PRO / Avançado** | Ferramentas especializadas | Divide Points By Strips, Drone Coordinates, Generate Trail, Photo Vectorization |
| 4 | **ENTERPRISE / Corporativo** | Análises complexas | Report Metadata, Vector To SVG, Create Project, Raster Mass Clipper |
| 5 | **PREMIUM / Premium** | Máximo nível | Raster Mass Sampler, (futuras ferramentas exclusivas) |

### 3.2 Esquema de Classificação Sugerido

#### Nível 1 — FREE (sempre local, sem API key necessária)
- ExportAllLayouts
- ReplaceInLayouts
- Settings
- RestartQgis
- AboutDialog
- LoadFolderLayers
- Logcat

#### Nível 2 — STANDARD
- VectorFieldsCalculation
- RemoveKmlFields
- Coord Click (map tool)
- CopyAttributes
- ConvertMultipart
- VectorToSvg

#### Nível 3 — PRO
- **DividePointsByStrips** ← mencionado explicitamente
- DroneCoordinates
- GenerateTrail
- PhotoVectorization

#### Nível 4 — ENTERPRISE
- ReportMetadata (geração de relatório)
- CreateProject
- RasterMassClipper

#### Nível 5 — PREMIUM
- RasterMassSampler
- (ferramentas futuras premium)

---

## 4. Integração com API para Distribuição de Ferramentas

### 4.1 Arquitetura da API

```
Usuário
   │
   ▼
SettingsPlugin (ou dialog de API Key)
   │  Informa API Key
   ▼
AccessLevelManager (novo serviço)
   │
   ├──► Valida API Key via HTTP
   │       POST https://api.cadmus.com/v1/validate-key
   │       { "api_key": "sk-xxx" }
   │       ← { "level": 3, "expires": "2026-12-31", "features": [...] }
   │
   ├──► Persiste nível em Preferences (access_level + api_key_hash)
   │
   └──► Disponibiliza nível via singleton para ToolRegistry/MenuManager
```

### 4.2 Endpoints Sugeridos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/v1/validate-key` | Valida API key, retorna nível de acesso + metadados |
| GET | `/v1/tools/{level}` | Lista ferramentas disponíveis para determinado nível |
| GET | `/v1/tool/{tool_key}/download` | Download do .py da ferramenta (criptografado ou raw) |
| POST | `/v1/offline-sync` | Sincroniza ferramentas offline por período |

### 4.3 Exemplo de Resposta da API

```json
{
  "status": "valid",
  "level": 3,
  "level_name": "PRO",
  "expires_at": "2026-12-31T23:59:59Z",
  "features": ["divide_points_by_strips", "drone_coordinates", "generate_trail"],
  "allowed_tools": [
    {"tool_key": "divide_points_by_strips", "download_url": "https://.../DividePointsByStripsPlugin.py"},
    {"tool_key": "drone_coordinates", "download_url": "https://.../DroneCoordinates.py"},
    {"tool_key": "generate_trail", "download_url": "https://.../GenerateTrailPlugin.py"}
  ],
  "metadata": {
    "organization": "ACME Corp",
    "max_users": 10,
    "support_level": "standard"
  }
}
```

---

## 5. Implementação no Model Tool

### 5.1 Classe Tool Atualizada

```python
# core/model/Tool.py

class Tool:
    def __init__(
        self,
        tool_key,
        name,
        icon,
        category,
        tool_type,
        main_action=False,
        executor=None,
        tooltip=None,
        order=100,
        show_in_toolbar=True,
        access_level=1,                  # NOVO: nível de acesso requerido (1-5)
        available=True,                  # NOVO: se está disponível localmente
        download_url=None,               # NOVO: URL para download se não disponível
        requires_api_key=False,          # NOVO: se requer API key validada
    ):
        # ... atributos existentes ...
        self.access_level = access_level
        self.available = available
        self.download_url = download_url
        self.requires_api_key = requires_api_key
        self.action = None
```

### 5.2 AccessLevelManager (novo serviço)

```python
# core/services/AccessLevelManager.py

import hashlib
import requests
from ..config.LogUtils import LogUtils
from ...utils.Preferences import Preferences
from ...utils.ToolKeys import ToolKey


class AccessLevelManager:
    """Gerencia níveis de acesso e validação de API keys."""
    
    _instance = None
    VALIDATION_URL = "https://api.cadmus.com/v1/validate-key"
    PREF_API_KEY_HASH = "api_key_hash"
    PREF_ACCESS_LEVEL = "access_level"
    PREF_ACCESS_EXPIRES = "access_expires_at"
    PREF_CACHED_TOOLS = "cached_allowed_tools"
    
    def __init__(self):
        self.logger = LogUtils(tool=ToolKey.SYSTEM, class_name="AccessLevelManager")
        self._level = 1  # default FREE
        self._api_key_hash = None
        self._allowed_tools_cache = {}
        self._load_state()
        AccessLevelManager._instance = self
    
    @classmethod
    def get_instance(cls):
        return cls._instance
    
    def _load_state(self):
        """Carrega estado salvo do Preferences."""
        prefs = Preferences.load_tool_prefs(ToolKey.SYSTEM)
        self._level = prefs.get(self.PREF_ACCESS_LEVEL, 1)
        self._api_key_hash = prefs.get(self.PREF_API_KEY_HASH)
        self._allowed_tools_cache = prefs.get(self.PREF_CACHED_TOOLS, {})
        self.logger.info(f"AccessLevelManager carregado: level={self._level}")
    
    def _save_state(self):
        """Persiste estado no Preferences."""
        prefs = Preferences.load_tool_prefs(ToolKey.SYSTEM)
        prefs[self.PREF_ACCESS_LEVEL] = self._level
        prefs[self.PREF_API_KEY_HASH] = self._api_key_hash
        prefs[self.PREF_CACHED_TOOLS] = self._allowed_tools_cache
        Preferences.save_tool_prefs(ToolKey.SYSTEM, prefs)
    
    @property
    def level(self):
        return self._level
    
    @level.setter
    def level(self, value):
        self._level = max(1, min(5, int(value)))
        self._save_state()
    
    def has_access_to(self, tool_access_level):
        """Verifica se o usuário tem acesso a uma ferramenta de determinado nível."""
        return self._level >= tool_access_level
    
    def is_tool_allowed(self, tool_key):
        """Verifica se tool_key específica está na lista de permitidas pela API."""
        if not self._allowed_tools_cache:
            return self._level >= 1  # se não há cache, usa regra geral
        return tool_key in self._allowed_tools_cache
    
    def validate_api_key(self, api_key, iface=None):
        """
        Valida API key via HTTP.
        Retorna (success: bool, level: int, message: str).
        """
        try:
            response = requests.post(
                self.VALIDATION_URL,
                json={"api_key": api_key},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                self._level = data.get("level", 1)
                self._api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
                self._allowed_tools_cache = {
                    t["tool_key"]: t
                    for t in data.get("allowed_tools", [])
                }
                self._save_state()
                return True, self._level, "API key validada com sucesso"
            else:
                return False, 1, f"Falha na validação: HTTP {response.status_code}"
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro ao validar API key: {e}")
            return False, self._level, f"Erro de conexão: {e}"
    
    def invalidate(self):
        """Reseta para nível FREE (1) e limpa cache."""
        self._level = 1
        self._api_key_hash = None
        self._allowed_tools_cache = {}
        self._save_state()
```

---

## 6. Implementação no ToolRegistry

### 6.1 Atualização do `_create_tool_list()`

Cada ferramenta ganha o parâmetro `access_level`:

```python
# Exemplo: DividePointsByStripsPlugin com access_level=3
divide_points_by_strips = Tool(
    tool_key=ToolKey.DIVIDE_POINTS_BY_STRIPS,
    name=STR.DIVIDE_POINTS_BY_STRIPS_TITLE,
    icon=im.icon(im.DIVIDE_POINTS_BY_STRIPS),
    category=self.VECTOR,
    tool_type=ToolTypeEnum.DIALOG,
    main_action=self._main_action_prefs.get(ToolKey.DIVIDE_POINTS_BY_STRIPS, False),
    executor=self._make_plugin_executor("...plugins.DividePointsByStripsPlugin"),
    tooltip=STR.DIVIDE_POINTS_BY_STRIPS_TOOLTIP,
    order=60,
    show_in_toolbar=True,
    access_level=3,              # NOVO
    available=FILE_EXISTS,       # NOVO: verifica se .py existe
    requires_api_key=True,       # NOVO
)
```

### 6.2 Método `get_accessible_tools()`

```python
def get_accessible_tools(self):
    """Retorna apenas ferramentas que o usuário tem acesso."""
    access_mgr = AccessLevelManager.get_instance()
    if access_mgr is None:
        return self.tools  # fallback: mostra todas se não inicializado
    
    return [
        tool for tool in self.tools
        if access_mgr.has_access_to(tool.access_level)
        and tool.available  # apenas ferramentas que existem localmente
    ]

def get_tools_for_menu(self):
    """
    Retorna ferramentas filtradas por acesso + disponibilidade.
    Usado pelo MenuManager para construir UI.
    """
    access_mgr = AccessLevelManager.get_instance()
    if access_mgr is None:
        return self.tools
    
    return [
        tool for tool in self.tools
        if self._is_tool_accessible(tool)
    ]

def _is_tool_accessible(self, tool):
    """Regra de acesso completa para uma ferramenta."""
    access_mgr = AccessLevelManager.get_instance()
    if access_mgr is None:
        return True
    
    # Ferramentas nível 1 são sempre acessíveis (FREE)
    if tool.access_level <= 1:
        return tool.available
    
    # Níveis superiores requerem API key válida
    return (
        access_mgr.has_access_to(tool.access_level)
        and tool.available
        and access_mgr.is_tool_allowed(tool.tool_key)
    )
```

### 6.3 Verificação de Disponibilidade dos Arquivos

```python
import os
from pathlib import Path

def _check_file_available(self, module_name):
    """
    Verifica se o arquivo .py da ferramenta existe.
    Retorna (available: bool, download_url: str or None).
    """
    # Mapeia module_name para path físico
    # Ex: "...plugins.DividePointsByStripsPlugin" → "plugins/DividePointsByStripsPlugin.py"
    plugin_path = self._resolve_plugin_path(module_name)
    
    if plugin_path and os.path.isfile(plugin_path):
        return True, None
    
    # Se não existe, pode ser baixado da API
    return False, self._build_download_url(module_name)

def _resolve_plugin_path(self, module_path):
    """Resolve caminho físico do módulo."""
    parts = module_path.replace("...", "").split(".")
    plugin_dir = Path(__file__).resolve().parent.parent.parent / "plugins"
    return str(plugin_dir / f"{parts[-1]}.py")

def _build_download_url(self, module_name):
    """Constrói URL de download baseada no tool_key."""
    # Mapeamento module_name → tool_key
    return f"https://api.cadmus.com/v1/tool/{module_name}/download"
```

---

## 7. Implementação no MenuManager

### 7.1 Filtragem ao Criar Actions

```python
def _create_actions_for_tools(self):
    """Cria QActions APENAS para ferramentas acessíveis e disponíveis."""
    accessible_tools = self._get_accessible_tools()
    
    for tool in accessible_tools:
        tool.action = QAction(tool.icon, tool.name, self.iface.mainWindow())
        tool.action.setToolTip(tool.tooltip or tool.name)
        tool.action.setData(tool)
        if tool.executor is not None:
            tool.action.triggered.connect(tool.executor)
    
    self.logger.debug(
        f"Actions criadas para {len(accessible_tools)}/{len(self.tools)} ferramentas "
        f"({len(self.tools) - len(accessible_tools)} bloqueadas por nível de acesso)"
    )

def _get_accessible_tools(self):
    """Filtra tools por access_level usando AccessLevelManager."""
    from .ToolRegistry import ToolRegistry
    
    registry = ToolRegistry.get_instance()
    if registry is None:
        return self.tools
    
    return registry.get_tools_for_menu()
```

### 7.2 Toolbar com Indicadores de Bloqueio

```python
def create_toolbar(self):
    """Cria toolbar com indicação visual de ferramentas bloqueadas."""
    # ... código existente ...
    
    for category in StringManager.MENU_CATEGORIES:
        # ... filtros existentes ...
        
        # NOVO: verificar se main_tool está acessível
        if not self._is_tool_accessible(main_tool):
            # Adicionar botão "bloqueado" com opção de desbloquear
            locked_button = self._create_locked_tool_button(category, main_tool)
            dropdown_buttons.append(locked_button)
            continue
        
        # ... código existente para ferramentas acessíveis ...
        
        # Filtrar secondary_tools por acesso
        accessible_secondary = [
            t for t in secondary_tools
            if self._is_tool_accessible(t)
        ]
        
        dropdown = DropdownToolButton(
            iface=self.iface,
            title=main_tool.name,
            main_action=main_tool.action,
            secondary_actions=[t.action for t in accessible_secondary],
            icon=main_tool.icon,
        )
        dropdown_buttons.append(dropdown)

def _create_locked_tool_button(self, category, tool):
    """Cria botão que indica ferramenta bloqueada com opção de upgrade."""
    from qgis.PyQt.QtWidgets import QPushButton
    
    btn = QPushButton(f"🔒 {tool.name}")
    btn.setToolTip(
        f"Ferramenta de nível {tool.access_level}. "
        f"Seu nível atual: {self._access_level}. "
        "Clique para fazer upgrade."
    )
    btn.clicked.connect(lambda: self._prompt_upgrade(category))
    return btn

def _prompt_upgrade(self, category):
    """Abre dialog de upgrade ou configuração de API key."""
    from ...utils.QgisMessageUtil import QgisMessageUtil
    
    QgisMessageUtil.modal_info(
        self.iface,
        f"Para desbloquear ferramentas da categoria '{category}', "
        f"insira uma API key válida nas configurações (Settings)."
    )
```

### 7.3 Submenus com Ferramentas Faltantes

```python
def populate_menus(self):
    for category in StringManager.MENU_CATEGORIES:
        if category not in self.submenus:
            continue
        
        sorted_tools = sorted(
            [t for t in self.tools if t.category == category],
            key=lambda x: x.order
        )
        
        for tool in sorted_tools:
            if self._is_tool_accessible(tool):
                self.submenus[category].addAction(tool.action)
            else:
                # Adicionar ação "fantasma" indicando bloqueio
                self._add_locked_action(self.submenus[category], tool)
    
    self.logger.debug("Submenus populados com ferramentas (acessíveis + bloqueadas)")

def _add_locked_action(self, menu, tool):
    """Adiciona ação placeholder para ferramenta bloqueada."""
    from qgis.PyQt.QtWidgets import QAction
    
    locked_action = QAction(
        f"🔒 {tool.name} (Nível {tool.access_level})",
        self.iface.mainWindow()
    )
    locked_action.setEnabled(False)
    locked_action.setToolTip(
        f"Disponível no nível {tool.access_level}. "
        f"Configure sua API key em Settings para desbloquear."
    )
    menu.addAction(locked_action)
```

---

## 8. Implementação no ReportMetadata / DroneCoordinates

### 8.1 DroneCoordinates — Controle de Relatório por Nível

```python
# plugins/DroneCoordinates.py

class DroneCordinates(BasePluginMTL):
    
    def execute_tool(self):
        """Executa pipeline com verificação de nível de acesso."""
        
        # NOVO: verificar nível de acesso para geração de relatório
        generate_report = self.checkbox_map["generate_report"].isChecked()
        
        if generate_report:
            # Verificar se tem nível para relatório
            if not self._can_generate_report():
                QgisMessageUtil.modal_warning(
                    self.iface,
                    "Geração de relatório requer nível de acesso 4 (Enterprise). "
                    "Os pontos serão processados, mas o relatório HTML não será gerado."
                )
                self.checkbox_map["generate_report"].setChecked(False)
                generate_report = False
        
        # ... código existente do pipeline ...
        context.set("generate_report", generate_report)
        # CONTINUA PROCESSANDO PONTOS, MESMO SEM RELATÓRIO

    def _can_generate_report(self):
        """Verifica se o nível de acesso permite geração de relatórios."""
        from ..core.services.AccessLevelManager import AccessLevelManager
        
        access_mgr = AccessLevelManager.get_instance()
        if access_mgr is None:
            return True  # fallback: permite se manager não disponível
        
        # Relatório requer nível 4
        REPORT_ACCESS_LEVEL = 4
        return access_mgr.level >= REPORT_ACCESS_LEVEL
```

### 8.2 ReportMetadataPlugin — Controle de Geração

```python
# plugins/ReportMetadataPlugin.py

class ReportMetadataPlugin(BasePluginMTL):
    REPORT_ACCESS_LEVEL = 4  # nível necessário para regerar relatórios
    
    def execute_tool(self):
        """Executa com verificação de acesso."""
        
        # NOVO: verificar nível de acesso
        if not self._has_report_access():
            QgisMessageUtil.modal_warning(
                self.iface,
                f"Geração de relatórios requer nível de acesso "
                f"{self.REPORT_ACCESS_LEVEL} (Enterprise). "
                f"Seu nível atual: {self._get_current_level()}."
            )
            return
        
        # ... código existente ...
    
    def _has_report_access(self):
        from ..core.services.AccessLevelManager import AccessLevelManager
        access_mgr = AccessLevelManager.get_instance()
        if access_mgr is None:
            return True
        return access_mgr.level >= self.REPORT_ACCESS_LEVEL
    
    def _get_current_level(self):
        from ..core.services.AccessLevelManager import AccessLevelManager
        access_mgr = AccessLevelManager.get_instance()
        return access_mgr.level if access_mgr else 1
    
    def _build_ui(self, **kwargs):
        # NOVO: se não tem acesso, desabilita botão e mostra aviso
        super()._build_ui(...)
        
        if not self._has_report_access():
            # Desabilitar botão de gerar relatório
            # Mostrar aviso na UI
            from ..core.ui.WidgetFactory import WidgetFactory
            warning_label = WidgetFactory.create_label(
                text=f"🔒 Geração de relatórios requer nível {self.REPORT_ACCESS_LEVEL}. "
                     f"Configure sua API key em Settings.",
                word_wrap=True,
                parent=self,
            )
            self.layout.add_item(warning_label, position=0)
```

### 8.3 Metadata Pipeline — Filtragem no ReportGenerationStep

```python
# core/engine_tasks/ReportGenerationStep.py

class ReportGenerationStep:
    REPORT_ACCESS_LEVEL = 4
    
    def execute(self, context):
        """Executa geração de relatório apenas se nível de acesso permitir."""
        
        # NOVO: verificar nível antes de executar
        generate_report = context.get("generate_report", False)
        
        if not generate_report:
            self.logger.info("Geração de relatório desabilitada pelo usuário")
            return context
        
        if not self._check_access(context):
            self.logger.warning(
                "Geração de relatório bloqueada: nível de acesso insuficiente"
            )
            # Graceful: não crasha, apenas não gera relatório
            context.set("report_payload", None)
            context.set("report_blocked", True)
            return context
        
        # ... código existente de geração ...
    
    def _check_access(self, context):
        from ..services.AccessLevelManager import AccessLevelManager
        access_mgr = AccessLevelManager.get_instance()
        if access_mgr is None:
            return True
        return access_mgr.level >= self.REPORT_ACCESS_LEVEL
```

---

## 9. Graceful Degradation (Ferramentas Ausentes)

### 9.1 Estratégia

Quando um arquivo `.py` de ferramenta de nível superior não existe localmente:

1. **ToolRegistry** marca `tool.available = False`
2. **MenuManager** mostra indicador visual (cadeado 🔒) no lugar da ferramenta
3. Ao clicar, exibe dialog com opção de inserir API key
4. **Executor** verifica disponibilidade antes de executar

### 9.2 Verificação no Executor

```python
def _make_plugin_executor(self, module_path: str, run_func: str = "run"):
    """
    Executor com verificação de disponibilidade.
    Se o módulo não existe, mostra mensagem de upgrade.
    """
    import re
    module_name = module_path.split(".")[-1]
    snake = re.sub(r'(?<!^)(?=[A-Z])', '_', module_name).lower()
    attr_name = f"{snake}_dlg"
    log_name = re.sub(r'(?<!^)(?=[A-Z])', ' ', module_name)

    def executor():
        try:
            import importlib
            # Verificar se o módulo existe antes de importar
            spec = importlib.util.find_spec(module_path, package=self._package)
            if spec is None:
                # Módulo não encontrado → graceful degradation
                self.logger.warning(
                    f"Módulo não encontrado: {module_path}. "
                    f"Pulando execução de {log_name}"
                )
                self._prompt_missing_tool(module_name, log_name)
                return
            
            module = importlib.import_module(module_path, package=self._package)
            fn = getattr(module, run_func)
            self.logger.info(f"Abrindo diálogo: {log_name}")
            result = fn(self.iface)
            setattr(self, attr_name, result)
            self.logger.info(f"Diálogo {log_name} aberto com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao executar {log_name}: {str(e)}")
            QgisMessageUtil.bar_critical(
                self.iface, f"Erro no plugin {log_name}:\n{str(e)}"
            )

    return executor

def _prompt_missing_tool(self, module_name, log_name):
    """
    Mostra dialog amigável quando ferramenta não está disponível.
    """
    from ...utils.QgisMessageUtil import QgisMessageUtil
    
    # Encontrar access_level da tool pelo tool_key
    tool_key = self._resolve_tool_key_from_module(module_name)
    access_level = self._get_tool_access_level(tool_key)
    
    msg = (
        f"A ferramenta '{log_name}' (Nível {access_level}) "
        f"não está instalada.\n\n"
        f"Isso pode ocorrer porque:\n"
        f"1. Você não possui o nível de acesso necessário\n"
        f"2. O arquivo foi removido intencionalmente\n\n"
        f"Configure sua API key no menu Settings "
        f"para baixar ferramentas adicionais."
    )
    
    QgisMessageUtil.modal_info(self.iface, msg)
```

---

## 10. API para Distribuição de Ferramentas

### 10.1 Serviço de Download

```python
# core/services/ToolDownloadService.py

import os
import requests
import hashlib
from pathlib import Path
from ...utils.Preferences import Preferences
from ...utils.ToolKeys import ToolKey


class ToolDownloadService:
    """Serviço para baixar ferramentas da API."""
    
    API_BASE = "https://api.cadmus.com/v1"
    
    def __init__(self):
        self.logger = LogUtils(tool=ToolKey.SYSTEM, class_name="ToolDownloadService")
    
    def download_tool(self, tool_key, api_key):
        """
        Baixa o .py de uma ferramenta específica.
        
        Returns:
            (success: bool, file_path: str or None, error: str or None)
        """
        try:
            # Obter URL de download
            response = requests.get(
                f"{self.API_BASE}/tool/{tool_key}/download",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            )
            
            if response.status_code != 200:
                return False, None, f"HTTP {response.status_code}"
            
            # Determinar path de destino
            plugin_dir = self._get_plugins_dir()
            file_name = self._resolve_file_name(tool_key)
            file_path = os.path.join(plugin_dir, file_name)
            
            # Salvar arquivo
            with open(file_path, "wb") as f:
                f.write(response.content)
            
            self.logger.info(f"Ferramenta baixada: {file_path}")
            return True, file_path, None
            
        except requests.exceptions.RequestException as e:
            return False, None, str(e)
    
    def sync_allowed_tools(self, api_key):
        """
        Baixa todas as ferramentas permitidas de uma vez.
        
        Returns:
            list of (tool_key, success, error)
        """
        results = []
        
        access_mgr = AccessLevelManager.get_instance()
        if access_mgr is None:
            return results
        
        for tool_key, tool_meta in access_mgr._allowed_tools_cache.items():
            success, path, error = self.download_tool(tool_key, api_key)
            results.append((tool_key, success, error))
        
        return results
    
    def _get_plugins_dir(self):
        """Retorna o diretório plugins/ do Cadmus."""
        return str(Path(__file__).resolve().parent.parent.parent.parent / "plugins")
    
    def _resolve_file_name(self, tool_key):
        """Mapeia tool_key para nome de arquivo .py."""
        MAPPING = {
            ToolKey.DIVIDE_POINTS_BY_STRIPS: "DividePointsByStripsPlugin.py",
            ToolKey.DRONE_COORDINATES: "DroneCoordinates.py",
            ToolKey.GENERATE_TRAIL: "GenerateTrailPlugin.py",
            ToolKey.PHOTO_VECTORIZATION: "PhotoVectorizationPlugin.py",
            ToolKey.REPORT_METADATA: "ReportMetadataPlugin.py",
            # ... outros mappings
        }
        return MAPPING.get(tool_key, f"{tool_key}.py")
```

### 10.2 Atualização Dinâmica sem Reiniciar Plugin

```python
def reload_tool_after_download(self, tool_key):
    """
    Após download, recarrega a tool sem reiniciar QGIS.
    """
    # 1. Atualizar Tool no registry
    registry = ToolRegistry.get_instance()
    if registry is None:
        return False
    
    for tool in registry.tools:
        if tool.tool_key == tool_key:
            tool.available = True
            # Recriar executor com módulo agora disponível
            tool.executor = registry._make_plugin_executor(
                self._resolve_module_path(tool_key)
            )
            break
    
    # 2. Atualizar action no MenuManager
    menu_mgr = MenuManager.get_instance()
    if menu_mgr is None:
        return False
    
    # Remover action antiga, criar nova
    menu_mgr.reconstruct_toolbar()
    menu_mgr.populate_menus()
    
    return True
```

---

## 11. Fluxo Completo de Carregamento

### 11.1 Inicialização com Níveis de Acesso

```
cadmus_plugin.py::initGui()
    │
    ├──► PluginBootstrap.bootstrap()
    │
    ├──► AccessLevelManager()  ← NOVO: carrega nível salvo
    │       └── Preferences → level=1 (default)
    │
    ├──► ToolRegistry(iface)
    │       ├── _check_tools_availability()  ← NOVO
    │       │       └── verifica se cada .py existe
    │       ├── _create_tool_list()  ← com access_level
    │       └── get_tools_for_menu() → filtra por acesso
    │
    ├──► MenuManager(iface, filtered_tools)
    │       ├── _create_actions_for_tools() → só acessíveis
    │       ├── create_menu() → com placeholders bloqueados
    │       ├── create_toolbar() → com botões 🔒 bloqueados
    │       └── populate_menus() → filtrado
    │
    └──► Processing provider (não afetado)
```

### 11.2 Configuração de API Key pelo Usuário

```
SettingsPlugin.abrir()
    │
    ├──► UI atual + novo campo "API Key"
    │       └── Input de texto + botão "Validar"
    │
    ├──► Usuário insere "sk-abc123..."
    │
    ├──► SettingsPlugin.execute_tool()
    │       └── AccessLevelManager.validate_api_key(api_key)
    │               ├── POST /v1/validate-key → {level: 3}
    │               ├── Persiste level + api_key_hash
    │               └── Baixa ferramentas do nível via ToolDownloadService
    │
    ├──► MenuManager.reconstruct_toolbar() → recria UI
    │
    └──► Mensagem de sucesso: "Acesso nível 3 (PRO) ativado!"
```

### 11.3 Execução de Ferramenta com Verificação

```
Usuário clica em "Divide Points By Strips"
    │
    ├──► tool.executor()
    │       ├── Verificar: tool.available?
    │       │   └── Se False → dialog "Faça upgrade" → STOP
    │       ├── Verificar: access_level <= user_level?
    │       │   └── Se False → dialog "Nível insuficiente" → STOP
    │       ├── Verificar: importlib.find_spec()?
    │       │   └── Se None → dialog "Módulo não encontrado" → STOP
    │       └── Importar módulo → executar
    │
    └── Pipeline normal (DroneCoordinates)
            ├── PhotoEnrichmentStep → OK
            ├── JsonVectorizationStep → OK
            └── ReportGenerationStep?
                    ├── access_level >= 4? → gera relatório
                    └── access_level < 4? → pula relatório, continua pontos
```

---

## 12. Considerações sobre Armazenamento e Cache

### 12.1 Onde Persistir o Nível de Acesso

| Dado | Onde | Chave |
|------|------|-------|
| Access Level | `Preferences` (ToolKey.SYSTEM) | `access_level` |
| API Key Hash | `Preferences` (ToolKey.SYSTEM) | `api_key_hash` |
| Expiração | `Preferences` (ToolKey.SYSTEM) | `access_expires_at` |
| Cache de Tools Permitidas | `Preferences` (ToolKey.SYSTEM) | `cached_allowed_tools` |
| Download Status | `Preferences` (cada tool_key) | `downloaded` |

### 12.2 Cache Offline

```python
def should_refresh_from_api(self):
    """Verifica se deve revalidar com a API."""
    prefs = Preferences.load_tool_prefs(ToolKey.SYSTEM)
    expires_at = prefs.get("access_expires_at")
    
    if not expires_at:
        return True  # nunca validou
    
    try:
        from datetime import datetime
        expires = datetime.fromisoformat(expires_at)
        return datetime.now() > expires
    except:
        return True
```

---

## 13. Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| **Crash se .py não existe** | Verificação `importlib.util.find_spec()` antes de importar. Todo executor tem try/except. |
| **API offline** | Cache local do último nível validado. Continua funcionando com nível salvo. |
| **API key expirada** | Aviso na toolbar + notificação. Não bloqueia, apenas perde funcionalidades de níveis superiores. |
| **Remoção manual de .py** | ToolRegistry detecta disponibilidade na inicialização. Plugin funciona com ferramentas restantes. |
| **Troca de nível no meio da execução** | Verificação é feita por execução (não por sessão). Pipeline longo verifica no início. |
| **Compatibilidade com Processing Provider** | Algorithms Processing não são afetados — podem ser filtrados separadamente. |
| **Performance na inicialização** | `os.path.isfile()` para todos os plugins é rápido (<10ms para 30 arquivos). |
| **Usuário sem internet** | Modo offline com último cache. Aviso sutil "API não disponível, modo offline". |

### 13.1 Plugins que NÃO Devem Ser Removidos (Nível 1 — FREE)

Estes são os arquivos essenciais que SEMPRE devem existir:

```
plugins/BasePlugin.py          → classe base para todos plugins
plugins/BaseDialog.py          → classe base para dialogs
plugins/SettingsPlugin.py      → configurações (inclui campo de API key)
plugins/RestartQgis.py         → restart
plugins/AboutDialog.py         → sobre
plugins/ExportAllLayouts.py    → exportação
plugins/ReplaceInLayouts.py    → replace
plugins/LoadFolderLayers.py    → carregar pastas
plugins/CoordClickTool.py      → map tool
plugins/ReportMetadataPlugin.py → regerar relatórios (mas requer level 4)
```

**Nota:** O `ReportMetadataPlugin.py` pode existir localmente, mas sua função de gerar relatório é controlada pelo `access_level` no executor. O arquivo existe, mas a funcionalidade premium é bloqueada.

---

## 14. Recomendações Finais

### 14.1 Ordem de Implementação Sugerida

1. **Fase 1 — Modelo de Dados**
   - Adicionar `access_level`, `available`, `download_url`, `requires_api_key` ao `Tool`
   - Criar `AccessLevelManager` (serviço singleton)
   - Atualizar `ToolRegistry._create_tool_list()` com níveis

2. **Fase 2 — Filtragem na UI**
   - Atualizar `MenuManager` para filtrar por `access_level`
   - Adicionar placeholders de bloqueio (🔒)
   - Adicionar campo de API key no `SettingsPlugin`

3. **Fase 3 — API e Download**
   - Criar `ToolDownloadService`
   - Implementar `validate_api_key()` com HTTP
   - Testar download e recarga dinâmica de ferramentas

4. **Fase 4 — Report Metadata**
   - Adicionar verificação de nível no `DroneCoordinates.execute_tool()`
   - Adicionar verificação no `ReportMetadataPlugin.execute_tool()`
   - Atualizar `ReportGenerationStep` no pipeline

5. **Fase 5 — Graceful Degradation**
   - Testar remoção de arquivos .py de nível 3+
   - Verificar que plugin funciona sem crashes
   - Testar recarga após download

### 14.2 Exemplo: Como Definir Níveis no ToolRegistry

```python
# NOVO parâmetro no _create_tool_list:
# access_level  → nível requerido (1-5)
# available     → se o arquivo .py existe
# requires_api_key → se precisa de API key validada

# Nível 1 - FREE (sempre disponível)
export_layouts = Tool(..., access_level=1, requires_api_key=False)
replace_layouts = Tool(..., access_level=1, requires_api_key=False)
settings = Tool(..., access_level=1, requires_api_key=False)
restart = Tool(..., access_level=1, requires_api_key=False)
about = Tool(..., access_level=1, requires_api_key=False)
load_folder = Tool(..., access_level=1, requires_api_key=False)

# Nível 2 - STANDARD
vector_fields = Tool(..., access_level=2, requires_api_key=True)
coord_click = Tool(..., access_level=2, requires_api_key=True)
copy_attrs = Tool(..., access_level=2, requires_api_key=True)
multipart = Tool(..., access_level=2, requires_api_key=True)

# Nível 3 - PRO
divide_points = Tool(
    ..., access_level=3, requires_api_key=True,
    available=os.path.isfile(PLUGINS_DIR / "DividePointsByStripsPlugin.py")
)
drone_coords = Tool(
    ..., access_level=3, requires_api_key=True,
    available=os.path.isfile(PLUGINS_DIR / "DroneCoordinates.py")
)
generate_trail = Tool(..., access_level=3, requires_api_key=True)
photo_vectorization = Tool(..., access_level=3, requires_api_key=True)

# Nível 4 - ENTERPRISE
report_metadata = Tool(
    ..., access_level=4, requires_api_key=True,
    available=os.path.isfile(PLUGINS_DIR / "ReportMetadataPlugin.py")
)
create_project = Tool(..., access_level=4, requires_api_key=True)
raster_clipper = Tool(..., access_level=4, requires_api_key=True)

# Nível 5 - PREMIUM
raster_sampler = Tool(..., access_level=5, requires_api_key=True)
```

### 14.3 Verificação Final: Plugin Funciona sem Arquivos de Nível 3+

```python
# Teste automatizado sugerido:
def test_graceful_degradation():
    """
    1. Remover DividePointsByStripsPlugin.py
    2. Remover DroneCoordinates.py
    3. Remover GenerateTrailPlugin.py
    4. Inicializar plugin
    5. Verificar que NÃO crasha
    6. Verificar que ferramentas nível 1-2 funcionam
    7. Verificar que ferramentas nível 3+ mostram cadeado
    8. Re-adicionar arquivos e testar recarga
    """
```

---

## Conclusão

O sistema de níveis de acesso proposto é **não intrusivo, extensível e seguro**. Ele se aproveita da arquitetura existente (ToolRegistry, MenuManager, Preferences) e adiciona:

1. **Modelo de dados** com `access_level` no Tool
2. **Serviço de validação** (AccessLevelManager) com cache e API
3. **UI adaptativa** com indicadores visuais de bloqueio
4. **Graceful degradation** sem crashes quando arquivos estão ausentes
5. **Download sob demanda** via ToolDownloadService
6. **Pipeline consciente** — ReportGenerationStep respeita nível de acesso

O custo de implementação é baixo (2 novos serviços, modificações mínimas nas classes existentes) e o benefício é alto: permite monetização, distribuição seletiva e flexibilidade sem comprometer a estabilidade do plugin.