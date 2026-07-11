---
description: 'Skill de gerenciamento de licença — LicenseManager, LicenseDialog, integração com SettingsPlugin.'
version: '2.0.0'
---

# 🔐 SKILL: Gerenciamento de Licença

## 📋 RESUMO EXECUTIVO

O sistema de licença do Cadmus é composto por:

1. **LicenseManager** (`utils/LicenseManager.py`) — lógica de validação via servidor Supabase, cache, renovação e persistência
2. **Security** (`core/config/Security.py`) — credenciais e URL do Supabase
3. **LicenseDialog** (`resources/widgets/LicenseDialog.py`) — diálogo modal para gerenciamento visual
4. **SettingsPlugin** — botão "Gerenciar Licença" que abre o LicenseDialog diretamente

---

## 🧠 LicenseManager — API Pública

### `is_license_valid() -> bool`
Verifica se a licença é válida com cache e renovação automática.
Consulta o SupABASE para validar a chave quando necessário.

### `get_license_info() -> dict`
Retorna informações completas da licença:
```python
{
    "has_key": bool,
    "key_preview": str,       # "A7B2****"
    "status": str,            # "active" | "inactive" | ""
    "expiry": str,            # "YYYY-MM-DD" ou ""
    "tier": str,              # "BASIC" | "PRO" | "ENTERPRISE" | "PREMIUM" | "MASTER" | ""
    "level": str,             # "Básico" | "Profissional" | "Enterprise" | "Premium" | "Master" | ""
    "is_active": bool,
    "days_remaining": int,
}
```

### `save_license_key(license_key: str) -> dict`
Valida a chave no servidor Supabase e salva. Retorna `{"success": bool, "message": str}`.
- Se inválida ou servidor offline: NÃO salva, retorna erro
- Se válida: salva chave, status "active", expiry (+30 dias), tier (mapeado do `nivel` do servidor)

### `delete_license() -> None`
Remove todos os dados de licença das preferências.

---

## 🧩 Dependências Externas

- `requests` — usado para consultar a API REST do Supabase
- `core.config.Security` — contém URL, API Key, headers e nome da tabela

---

## 🌐 Validação via Servidor (Supabase)

A validação agora é feita consultando a tabela `api_keys` no Supabase:

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

### Mapeamento nivel (1-5) -> tier:
| nivel | tier        | label          |
|-------|-------------|----------------|
| 1     | BASIC       | Básico         |
| 2     | PRO         | Profissional   |
| 3     | ENTERPRISE  | Enterprise     |
| 4     | PREMIUM     | Premium        |
| 5     | MASTER      | Master         |

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
  - Cores: verde=ativa, vermelho=inativa, cinza=sem chave
- **Botão 🗑️ REMOVE** — apaga a licença (texto via `STR.REMOVE`)
- **Botão 💾 SAVE** — salva (texto via `STR.SAVE`)
- **Botão CLOSE** — fecha (texto via `STR.CLOSE`)

### Fluxo de Salvamento
1. Usuário digita chave
2. Clica em 💾 Salvar
3. `LicenseManager.save_license_key()` valida no Supabase
4. Se válida: salva, modal sucesso, fecha diálogo
5. Se inválida ou offline: modal aviso, não salva, diálogo permanece

### Fluxo de Apagar
1. Usuário clica em 🗑️ REMOVE
2. `LicenseManager.delete_license()` remove dados
3. Display atualizado para "sem chave"

---

## ⚙️ SettingsPlugin

- Botão "🔑 Gerenciar Licença" substitui o antigo InputFieldsWidget
- Ao clicar: `from ..resources.widgets.LicenseDialog import LicenseDialog` + `dialog.exec_()`
- Licença NÃO é mais salva em `_save_prefs()` — LicenseDialog salva diretamente via LicenseManager

---

## 📦 Preferências (system_preferences)

| Chave | Tipo | Descrição |
|-------|------|-----------|
| `license_key` | str | Chave de licença |
| `license_status` | str | "active" \| "inactive" \| "" |
| `license_expiry` | str | Data "YYYY-MM-DD" |
| `license_tier` | str | "BASIC" \| "PRO" \| "ENTERPRISE" \| "PREMIUM" \| "MASTER" \| "" |

---

## 🚫 Proibições

- **Nunca** importar `LicenseDialog` em WidgetFactory (diálogo não é widget)
- **Nunca** manipular preferências de licença manualmente — usar `LicenseManager`
- **Nunca** exibir chave completa na UI — usar `key_preview` (4 primeiros chars + "****")
- **Nunca** chamar `_query_server()` ou `_check_license()` diretamente — usar os métodos públicos

---

## 📜 Histórico

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-11 | 1.0.0 | Criação da skill |
| 2026-07-11 | 1.0.1 | Renomeado LicenseDialogWidget → LicenseDialog; removido factory method do WidgetFactory; strings genéricas |
| 2026-07-11 | 2.0.0 | Migração para validação via servidor Supabase; removido VALID_LICENSE_KEY local; adicionado Security como fonte de credenciais |