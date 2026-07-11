---
description: 'Skill de gerenciamento de licença — LicenseManager, LicenseDialog, integração com SettingsPlugin.'
version: '1.0.1'
---

# 🔐 SKILL: Gerenciamento de Licença

## 📋 RESUMO EXECUTIVO

O sistema de licença do Cadmus é composto por:

1. **LicenseManager** (`utils/LicenseManager.py`) — lógica de validação, cache, renovação e persistência
2. **LicenseDialog** (`resources/widgets/LicenseDialog.py`) — diálogo modal para gerenciamento visual
3. **SettingsPlugin** — botão "Gerenciar Licença" que abre o LicenseDialog diretamente

---

## 🧠 LicenseManager — API Pública

### `is_license_valid() -> bool`
Verifica se a licença é válida com cache e renovação automática.

### `get_license_info() -> dict`
Retorna informações completas da licença:
```python
{
    "has_key": bool,
    "key_preview": str,       # "1234****"
    "status": str,            # "active" | "inactive" | ""
    "expiry": str,            # "YYYY-MM-DD" ou ""
    "tier": str,              # "BASIC" | "PRO" | "ENTERPRISE" | ""
    "level": str,             # "Básico" | "Profissional" | "Enterprise" | ""
    "is_active": bool,
    "days_remaining": int,
}
```

### `save_license_key(license_key: str) -> dict`
Valida e salva a chave. Retorna `{"success": bool, "message": str}`.
- Se inválida: NÃO salva, retorna erro
- Se válida: salva chave, status "active", expiry (+30 dias), tier

### `delete_license() -> None`
Remove todos os dados de licença das preferências.

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
3. `LicenseManager.save_license_key()` valida
4. Se válida: salva, modal sucesso, fecha diálogo
5. Se inválida: modal aviso, não salva, diálogo permanece

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
| `license_tier` | str | "BASIC" \| "PRO" \| "ENTERPRISE" \| "" |

---

## 🔄 Validação (cache + renovação)

- **> 7 dias restantes**: True (cache)
- **0–7 dias restantes**: tenta renovar, True mesmo se falhar (graça)
- **Expirada**: valida obrigatoriamente; se inválida → inativa → False
- **Sem chave**: False

---

## 🚫 Proibições

- **Nunca** importar `LicenseDialog` em WidgetFactory (diálogo não é widget)
- **Nunca** manipular preferências de licença manualmente — usar `LicenseManager`
- **Nunca** exibir chave completa na UI — usar `key_preview` (4 primeiros chars + "****")

---

## 📜 Histórico

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-11 | 1.0.0 | Criação da skill |
| 2026-07-11 | 1.0.1 | Renomeado LicenseDialogWidget → LicenseDialog; removido factory method do WidgetFactory; strings genéricas |