---
description: 'Skill de gerenciamento de licença — LicenseFileManager, LicenseManager, LicenseDialog, integração com SettingsPlugin.'
version: '3.0.0'
---

# 🔐 SKILL: Gerenciamento de Licença

## 📋 RESUMO EXECUTIVO

O sistema de licença do Cadmus é composto por:

1. **LicenseFileManager** (`utils/LicenseFileManager.py`) — persistência em arquivo ofuscado (`%TEMP%/cadmus/license.dat`) com HMAC e XOR
2. **LicenseManager** (`utils/LicenseManager.py`) — lógica de validação via servidor Supabase, cache, renovação (usa LicenseFileManager internamente)
3. **Security** (`core/config/Security.py`) — credenciais e URL do Supabase
4. **LicenseDialog** (`resources/widgets/LicenseDialog.py`) — diálogo modal para gerenciamento visual
5. **SettingsPlugin** — botão "Gerenciar Licença" que abre o LicenseDialog diretamente

---

## 🧠 LicenseManager — API Pública

### `is_license_valid() -> bool`
Verifica se a licença é válida com cache e renovação automática.
Consulta o Supabase para validar a chave quando necessário.

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

### `delete_license() -> None`
Remove o arquivo de licença ofuscado do disco.

---

## 🧩 Dependências

### Externas
- `requests` — usado para consultar a API REST do Supabase

### Internas (utils/)
- `LicenseFileManager` — persistência em arquivo ofuscado
- `BaseUtil` — classe base com logger
- `ExplorerUtils` — resolução de pastas temporárias
- `ToolKeys` — constantes de tool_key

### Apenas bibliotecas padrão Python (LicenseFileManager)
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

## 📦 Persistência (LicenseFileManager)

Os dados de licença são persistidos em arquivo ofuscado ao invés de Preferences.

### Arquivo
`{TEMP}/cadmus/license.dat`

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
- Chave `_HMAC_KEY` (32 bytes aleatórios) — usada exclusivamente para assinatura
- Assinatura removida antes de recalcular; comparada com `hmac.compare_digest()`
- Se HMAC não corresponder: licença considerada adulterada → None

### Ofuscação (XOR + SHA-256 keystream)
- Chave `_SECRET_KEY` (32 bytes aleatórios) — usada para gerar keystream
- Keystream: `SHA256(SECRET_KEY + counter)` para counter=0,1,2... até tamanho necessário
- XOR byte a byte com os dados comprimidos
- Resultado codificado em Base64 (ascii)

### Chaves criptográficas
- Geradas com `secrets.token_bytes(32)` na primeira inicialização
- Duas chaves distintas: SECRET_KEY (keystream) e HMAC_KEY (assinatura)
- Permanecem em memória durante o ciclo de vida do plugin

### Observações de segurança
- **Arquivo ilegível** no Bloco de Notas (Base64 + XOR + compressão)
- **Detecta adulteração** via HMAC
- **Não utiliza bibliotecas externas** (apenas módulos nativos Python)
- **Limitação**: XOR com SHA-256 é ofuscação, não substitui AES.
  Um atacante com engenharia reversa pode extrair as chaves do executável.

---

## 🚫 Proibições

- **Nunca** importar `LicenseDialog` em WidgetFactory (diálogo não é widget)
- **Nunca** manipular dados de licença manualmente — usar `LicenseManager`
- **Nunca** exibir chave completa na UI — usar `key_preview` (4 primeiros chars + "****")
- **Nunca** chamar `_query_server()` ou `_check_license()` diretamente — usar os métodos públicos
- **Nunca** usar `Preferences` para dados de licença — usar `LicenseFileManager` via `LicenseManager`

---

## 📜 Histórico

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-11 | 1.0.0 | Criação da skill |
| 2026-07-11 | 1.0.1 | Renomeado LicenseDialogWidget → LicenseDialog; removido factory method do WidgetFactory; strings genéricas |
| 2026-07-11 | 2.0.0 | Migração para validação via servidor Supabase; removido VALID_LICENSE_KEY local e tiers textuais; apenas nivel numérico 1-5 |
| 2026-07-11 | 3.0.0 | Migração de persistência de Preferences para LicenseFileManager (arquivo ofuscado %TEMP%/cadmus/license.dat); removida dependência de Preferences |
