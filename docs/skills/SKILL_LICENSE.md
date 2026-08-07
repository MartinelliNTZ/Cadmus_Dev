---
description: 'Skill de gerenciamento de licença — RegistryManager, RegistryFileManager, LicenseDialog, integração com SettingsPlugin, filtro por license_level no ToolRegistry, verificação de nível mínimo para relatórios, build_distribution.'
version: '5.0.0'
---

# 🔐 SKILL: Gerenciamento de Licença

## 📋 RESUMO EXECUTIVO

O sistema de licença do Cadmus é composto por:

1. **RegistryFileManager** (`core/config/RegistryFileManager.py`) — persistência em arquivo ofuscado (`%TEMP%/cadmus/A1GPCTR8.dat`) com HMAC e XOR
2. **RegistryManager** (`core/config/RegistryManager.py`) — lógica de validação via servidor Supabase, cache, renovação, verificação de nível mínimo (usa RegistryFileManager internamente)
3. **Security** (`core/config/Security.py`) — credenciais e URL do Supabase
4. **LicenseDialog** (`resources/widgets/LicenseDialog.py`) — diálogo modal para gerenciamento visual
5. **SettingsPlugin** — botão "Gerenciar Licença" que abre o LicenseDialog diretamente
6. **ToolRegistry** — filtro automático de ferramentas por `license_level` baseado no nível atual da licença
7. **DroneCoordinates** — constante `LICENSE_LEVEL = 3`; controla exibição de itens premium (logo, título, relatório) na UI; usa `has_minimum_level()` em vez de `is_license_valid()`
8. **DronePipelineService** — constante `LICENSE_LEVEL = 3`; verifica nível mínimo antes de adicionar ReportGenerationStep
9. **ReportMetadataPlugin** — constante `LICENSE_LEVEL = 3`; verifica nível mínimo antes de gerar relatórios
10. **DividePointsByStripsPlugin** — constante `LICENSE_LEVEL = 3` (premium nível 3+); protegido via verificação em `execute_tool()` com `has_minimum_level(3)`; compilado e empacotado via build_distribution junto com os 3 judges (`SimpleSPBJudge`, `ScoreSPBJudge`, `SequentialPointBreakJudge`)
11. **build_distribution.py** — empacota módulos em `.dist`; módulos de relatório e segmentação (DividePointsByStrips + judges) só são acessíveis se licença for válida

---

## 🧠 RegistryManager — API Pública

### Constante `ENABLE_REGISTRY`

```python
ENABLE_REGISTRY: bool = False
```

- `True`: sistema de licença ativo — valida chaves no Supabase, filtra ferramentas por nível.
- `False` (padrão atual): **sistema de licença desabilitado** — nenhuma requisição ao servidor é feita, todas as ferramentas ficam liberadas (modo free total).
- Quando `False`:
  - `is_registry_valid()` → sempre `True`
  - `has_minimum_level(n)` → sempre `True`
  - `save_lic_key()` → recusa salvar com aviso "Sistema de registro desabilitado no momento."
  - `_query_server()` → retorna `None` sem fazer HTTP

> ⚠️ Deixar `False` até o servidor Supabase ser restaurado (domínio `ynlameyuhvmesozcuanh.supabase.co` não existe mais).

### `is_license_valid() -> bool`
Verifica se a licença é válida com cache e renovação automática.
Consulta o Supabase para validar a chave quando necessário.
Retorna `True` imediatamente se `ENABLE_REGISTRY=False`.

### `get_license_info() -> dict`
Retorna informações completas da licença:
```python
{
    "has_key": bool,
    "key_preview": str,       # "A7B2****"
    "status": str,            # "active" | "inactive" | ""
    "expiry": str,            # "YYYY-MM-DD" ou ""
    "nivel": int,             # 1-5 (0 se sem chave)
    "is_active": bool,
    "days_remaining": int,
}
```

### `save_license_key(license_key: str) -> dict`
Valida a chave no servidor Supabase e salva. Retorna `{"success": bool, "message": str}`.
- Se inválida ou servidor offline: NÃO salva, retorna erro
- Se válida: salva chave, status "active", expiry (+30 dias), nivel (1-5 numérico)

### `get_level() -> int`
Retorna o nível atual da licença (1-5). Retorna 0 se sem chave ou inválida.

### `has_minimum_level(min_level: int) -> bool`
Verifica se a licença é válida E tem nível >= `min_level`.

```python
from ..config.RegistryManager import RegistryManager
license_mgr = RegistryManager(tool_key=self.TOOL_KEY)
if license_mgr.has_minimum_level(3):
    # Só executa se licença válida e nível >= 3
```

### `delete_license() -> None`
Remove o arquivo de licença ofuscado do disco.

---

## 🧩 Dependências

### Externas
- `requests` — usado para consultar a API REST do Supabase

### Internas (core/config/)
- `RegistryFileManager` — persistência em arquivo ofuscado
- `Security` — credenciais do Supabase

### Internas (utils/)
- `BaseUtil` — classe base com logger
- `ExplorerUtils` — resolução de pastas temporárias
- `ToolKeys` — constantes de tool_key

### Apenas bibliotecas padrão Python (RegistryFileManager)
- `json`, `os`, `base64`, `hashlib`, `hmac`, `secrets`, `zlib`, `datetime`

---

## 🌐 Validação via Servidor (Supabase)

A validação é feita consultando a tabela `api_keys` no Supabase:

```
GET https://ynlameyuhvmesozcuanh.supabase.co/rest/v1/api_keys?api_key=eq.{chave}&select=*
```

### Headers:
```python
{
    "apikey": Security.SUPABASE_API_KEY,
    "Authorization": f"Bearer {Security.SUPABASE_API_KEY}"
}
```

### Resposta esperada:
```json
[
    {
        "id": 1,
        "api_key": "A7B2C-H6B8D-L9B4X",
        "nivel": 1,
        "ativo": true,
        "criado_em": "2026-07-11T18:00:36.579253"
    }
]
```

### Níveis:
O campo `nivel` do servidor (1-5) é salvo diretamente no campo `level` do arquivo ofuscado.
Não existem tiers textuais — apenas o número do nível.

---

## 🔄 Validação (cache + renovação)

- **> 7 dias restantes**: True (cache — sem consultar servidor)
- **0–7 dias restantes**: tenta renovar no servidor, True mesmo se falhar (graça offline)
- **Expirada**: valida obrigatoriamente no servidor; se inválida ou offline -> inativa -> False
- **Sem chave**: False

### Comportamento offline
- `_query_server()` retorna `None` em caso de `RequestException`
- `_check_license()` interpreta `None` como inválido (False)
- `_try_renew()` (período de graça) retorna True mesmo se `_check_license()` falhar

---

## 🖥️ LicenseDialog

Diálogo modal (`QDialog`) em `resources/widgets/LicenseDialog.py`:

- **QLineEdit** para inserir chave
- **Botão 🔑** para validar (tooltip `STR.VALIDATE`)
- **Grid de labels**: Nível (`STR.LEVEL`), Validade (`STR.EXPIRATION_DATE`), Status (`STR.STATUS`)
  - Nível exibe o número (1-5) ou "-"
  - Cores: verde=ativa, vermelho=inativa, cinza=sem chave
- **Botão 🗑️ REMOVE** — apaga a licença (texto via `STR.REMOVE`)
- **Botão 💾 SAVE** — salva (texto via `STR.SAVE`)
- **Botão CLOSE** — fecha (texto via `STR.CLOSE`)

### Fluxo de Salvamento
1. Usuário digita chave
2. Clica em 💾 Salvar
3. `RegistryManager.save_license_key()` valida no Supabase
4. Se válida: salva, modal sucesso, fecha diálogo
5. Se inválida ou offline: modal aviso, não salva, diálogo permanece

### Fluxo de Apagar
1. Usuário clica em 🗑️ REMOVE
2. `RegistryManager.delete_license()` remove dados
3. Display atualizado para "sem chave"

---

## ⚙️ SettingsPlugin

- Botão "🔑 Gerenciar Licença" substitui o antigo InputFieldsWidget
- Ao clicar: `from ..resources.widgets.LicenseDialog import LicenseDialog` + `dialog.exec_()`
- Licença NÃO é mais salva em `_save_prefs()` — LicenseDialog salva diretamente via RegistryManager

---

## 📦 Persistência (RegistryFileManager)

Os dados de licença são persistidos em arquivo ofuscado ao invés de Preferences.

### Arquivo
`{TEMP}/cadmus/A1GPCTR8.dat`

### Pipeline de escrita
```
dict → JSON → HMAC-SHA256 → zlib compress → XOR keystream → Base64 → arquivo
```

### Pipeline de leitura
```
arquivo → Base64 decode → XOR keystream → zlib decompress → JSON → HMAC verify → dict
```

### Dicionário armazenado
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `license_key` | str | Chave de licença |
| `level` | int | Nível 1-5 |
| `expire_date` | str | Data "YYYY-MM-DD" |
| `created_at` | str | ISO datetime de criação |
| `machine_id` | str | ID da máquina (opcional) |
| `version` | int | Versão do formato (1) |
| `signature` | str | HMAC-SHA256 hexadecimal |

### Integridade (HMAC)
- Chave `_HMAC_KEY` fixa (constante da classe) — usada exclusivamente para assinatura
- Assinatura removida antes de recalcular; comparada com `hmac.compare_digest()`
- Se HMAC não corresponder: licença considerada adulterada → None

### Ofuscação (XOR + SHA-256 keystream)
- Chave `_SECRET_KEY` fixa (constante da classe) — usada para gerar keystream
- Keystream: `SHA256(SECRET_KEY + counter)` para counter=0,1,2... até tamanho necessário
- XOR byte a byte com os dados comprimidos
- Resultado codificado em Base64 (ascii)

### Chaves criptográficas
- Fixas na classe (`RegistryFileManager._SECRET_KEY` e `RegistryFileManager._HMAC_KEY`)
- Permanecem em memória durante o ciclo de vida do plugin
- **IMPORTANTE**: chaves NÃO podem mudar entre versões ou arquivos existentes ficarão ilegíveis

### Observações de segurança
- **Arquivo ilegível** no Bloco de Notas (Base64 + XOR + compressão)
- **Detecta adulteração** via HMAC
- **Não utiliza bibliotecas externas** (apenas módulos nativos Python)
- **Limitação**: XOR com SHA-256 é ofuscação, não substitui AES.
  Um atacante com engenharia reversa pode extrair as chaves do executável.

---

## 🎯 Verificação de Nível Mínimo para Relatórios

Relatórios HTML exigem licença com nível >= 3.

Cada ferramenta que exige nível mínimo de licença define sua própria constante `LICENSE_LEVEL`:

- **DroneCoordinates**: `LICENSE_LEVEL = 3` — controla UI (logo, título, checkbox relatório)
- **DronePipelineService**: `LICENSE_LEVEL = 3` — controla steps do pipeline
- **ReportMetadataPlugin**: `LICENSE_LEVEL = 3` — controla geração manual de relatórios

### DroneCoordinates._build_ui()

No método `_build_ui()`, a verificação de licença controla quais elementos da UI são exibidos:

```python
class DroneCordinates(BasePluginMTL):
    LICENSE_LEVEL: int = 3

    def _build_ui(self, **kwargs):
        ...
        license_mgr = RegistryManager(tool_key=self.TOOL_KEY)
        is_license_valid = license_mgr.has_minimum_level(self.LICENSE_LEVEL)

        # LOGO / IMAGE SELECTOR (só se licença válida)
        if is_license_valid:
            logo_layout, self.logo_selector = WidgetFactory.create_save_file_selector(...)
            self.opts_collapsible.add_content_layout(logo_layout)

        # PROJETO TITLE (só se licença válida)
        if is_license_valid:
            title_layout, self.title_input = WidgetFactory.create_input_fields_widget(...)
            self.opts_collapsible.add_content_layout(title_layout)

        # Monta checkboxes — remove generate_report se licença inválida
        checkbox_options = dict(self.CHECKBOX_OPTIONS)
        if not is_license_valid:
            checkbox_options.pop("generate_report", None)
```

### DronePipelineService.execute()

No método `execute()`, ao montar os steps do pipeline:

```python
class DronePipelineService:
    LICENSE_LEVEL: int = 3

    @staticmethod
    def execute(...):
        ...
        from ..config.RegistryManager import RegistryManager
        license_mgr = RegistryManager(tool_key=ToolKey.DRONE_COORDINATES)
        if license_mgr.has_minimum_level(DronePipelineService.LICENSE_LEVEL):
            from ..engine_tasks.ReportGenerationStep import ReportGenerationStep
            steps.append(ReportGenerationStep())
        else:
            logger.warning(
                f"Licença sem nível mínimo {DronePipelineService.LICENSE_LEVEL} — "
                f"relatório não será gerado"
            )
```

### DronePipelineService._on_pipeline_finished()

No callback de sucesso, o mesmo padrão é repetido para gerar relatório no pós-processamento:

```python
if license_mgr.has_minimum_level(DronePipelineService.LICENSE_LEVEL):
    from .ReportGenerationService import ReportGenerationService
    report_payload = ReportGenerationService(
        tool_key=ToolKey.DRONE_COORDINATES
    ).generate_from_json(json_path)
else:
    logger.warning(
        f"Licença sem nível mínimo {DronePipelineService.LICENSE_LEVEL} — "
        f"relatório não será gerado no pós-processamento"
    )
```

### ReportMetadataPlugin.execute_tool()

No plugin manual de relatórios, o usuário vê um aviso se não tiver nível suficiente:

```python
class ReportMetadataPlugin(BasePluginMTL):
    LICENSE_LEVEL: int = 3

    def execute_tool(self):
        ...
        license_mgr = RegistryManager(tool_key=self.TOOL_KEY)
        if not license_mgr.has_minimum_level(self.LICENSE_LEVEL):
            QgisMessageUtil.modal_warning(
                self.iface,
                f"Relatório requer licença nível {self.LICENSE_LEVEL} ou superior."
            )
            return
```

---

## 🧩 Integração com ToolRegistry — Filtro por Nível de Licença

O `ToolRegistry` filtra automaticamente ferramentas cujo `license_level` é maior que o nível atual da licença.

### Atributo `license_level` em `Tool`

A classe `Tool` (`core/model/Tool.py`) possui o atributo opcional `license_level`:

```python
Tool(
    ...
    license_level=None,  # None = livre para todos os níveis
)
```

- `license_level=None` (padrão): ferramenta visível para todos os usuários, independente de licença.
- `license_level=1`: ferramenta visível apenas se o nível da licença atual for >= 1.
- `license_level=N`: ferramenta visível apenas se o nível da licença atual for >= N.

### Método `_filter_tools_by_license()` em `ToolRegistry`

Chamado automaticamente no final de `ToolRegistry.__init__()`, após a criação e validação da lista de ferramentas:

```python
def _filter_tools_by_license(self):
    license_mgr = RegistryManager(ToolKey.SYSTEM)
    lic_info = license_mgr.get_license_info()
    current_level = lic_info.get("nivel", 0)

    self.tools = [
        tool for tool in self.tools
        if tool.license_level is None or current_level >= tool.license_level
    ]
```

### Comportamento

- Se não há chave de licença: `current_level = 0` → ferramentas com `license_level >= 1` são removidas.
- Se a licença é nível 1: ferramentas com `license_level=1` ficam visíveis; `license_level=2+` são removidas.
- Se a licença é nível 5: todas as ferramentas ficam visíveis (5 >= qualquer license_level).

### Exemplo

```python
# Apenas visível com licença nível 1+
divide_points_by_strips = Tool(
    ...
    license_level=1,
)
```

---

## 📦 build_distribution.py

O script `build_distribution.py` compila e empacota módulos em um arquivo `.dist`.

### Módulos no MODULES (compilados e empacotados)

O dicionário `MODULES` inclui todos os módulos que devem ser compilados e empacotados no `.dist`:

```python
MODULES = {
    "plugins": [
        "PathExtensionPlugin.py",
        "ReportMetadataPlugin.py",        # Plugin de relatório (nível 3+)
        "DividePointsByStripsPlugin.py",   # Segmentação premium (nível 3+)
    ],
    "core/config": [
        "RegistryManager.py",
    ],
    "core/services": [
        "ReportGenerationService.py",     # Serviço de relatório
    ],
    "core/task": [
        "PathExtensionTask.py",
        "ReportGenerationTask.py",
    ],
    "core/engine_tasks": [
        "PathExtensionStep.py",
        "ReportGenerationStep.py",
    ],
    "utils/judge": [
        "SimpleSPBJudge.py",              # Judge simplificado (nível 1+)
        "ScoreSPBJudge.py",               # Judge por score (nível 1+)
        "SequentialPointBreakJudge.py",   # Judge sequencial complexo (nível 1+)
    ],
    "utils/report": [
        "__init__.py",
        "AggregateAnalyzer.py",
        "AlertManager.py",
        ...
    ],
}
```

### Mecanismo de proteção em modo free

Embora os módulos estejam no `MODULES` e sejam compilados/empacotados, a proteção em modo free ocorre em **tempo de execução** via import lazy:

1. Os imports dos módulos de relatório (`ReportGenerationService`, `ReportGenerationStep`) são feitos dentro de funções/métodos (não no topo do arquivo)
2. Antes de cada import, uma verificação de licença é feita com `has_minimum_level(LICENSE_LEVEL)`
3. Se a licença não for válida ou o nível for insuficiente, o import nunca acontece

Isso significa que:
- O **DronePipelineService** funciona completamente em modo free sem os módulos de relatório
- O **ReportMetadataPlugin** abre a UI, mas o botão de gerar relatório exibe aviso se não tiver nível >= 3
- O **build_distribution** pode compilar tudo sem problemas — a proteção está no runtime

### Fluxo no modo free

```
DronePipelineService.execute()
  → has_minimum_level(3)? → NÃO → log warning, pipeline sem ReportGenerationStep
  → pipeline executa normalmente: fotos, coordenadas, vetorização
  → relatório NÃO é gerado

ReportMetadataPlugin.execute_tool()
  → has_minimum_level(3)? → NÃO → modal warning "Relatório requer licença nível 3+"
  → relatório NÃO é gerado
```

---

## 🚫 Proibições

- **Nunca** importar `LicenseDialog` em WidgetFactory (diálogo não é widget)
- **Nunca** manipular dados de licença manualmente — usar `RegistryManager`
- **Nunca** exibir chave completa na UI — usar `key_preview` (4 primeiros chars + "****")
- **Nunca** chamar `_query_server()` ou `_check_license()` diretamente — usar os métodos públicos
- **Nunca** usar `Preferences` para dados de licença — usar `RegistryFileManager` via `RegistryManager`
- **Nunca** fazer import global de módulos de relatório — usar import lazy dentro de funções com verificação de licença
- **Nunca** remover módulos de relatório do `build_distribution.MODULES` — a proteção é em runtime, não em compile time

---

## 📜 Histórico

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-11 | 1.0.0 | Criação da skill |
| 2026-07-11 | 1.0.1 | Renomeado LicenseDialogWidget → LicenseDialog; removido factory method do WidgetFactory; strings genéricas |
| 2026-07-11 | 2.0.0 | Migração para validação via servidor Supabase; removido VALID_LICENSE_KEY local e tiers textuais; apenas nivel numérico 1-5 |
| 2026-07-11 | 3.0.0 | Migração de persistência de Preferences para RegistryFileManager (arquivo ofuscado %TEMP%/cadmus/A1GPCTR8.dat); removida dependência de Preferences |
| 2026-07-11 | 4.0.0 | Adicionado atributo `license_level` em `Tool` e filtro `_filter_tools_by_license()` em `ToolRegistry`; ferramentas com `license_level` maior que o nível atual da licença são removidas da lista; `divide_points_by_strips` configurado com `license_level=1` |
| 2026-07-13 | 5.0.0 | Adicionado método `get_level()` e `has_minimum_level()` no RegistryManager; constante `LICENSE_LEVEL=3` movida para cada ferramenta (DroneCoordinates, ReportMetadataPlugin e DronePipelineService); documentado build_distribution com proteção em runtime via import lazy |
| 2026-07-13 | 5.1.0 | Adicionado `DividePointsByStripsPlugin.py` (license_level=1) e judges `SimpleSPBJudge.py`, `ScoreSPBJudge.py`, `SequentialPointBreakJudge.py` ao MODULES do build_distribution; documentado na skill |
| 2026-08-07 | 5.2.0 | Adicionada constante `ENABLE_REGISTRY` no RegistryManager (padrão `False`); quando `False`, nenhuma requisição ao servidor é feita e todas as features ficam liberadas; documentado na skill |
