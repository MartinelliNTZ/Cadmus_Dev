# -*- coding: utf-8 -*-
"""
LicenseManager — Gerenciamento de licença com cache e renovação automática
===========================================================================
Gerencia validação de licença com consulta ao servidor Supabase e cache de status.

Regras de validação:
- Se a licença está ativa e dentro do prazo (> 7 dias restantes) -> retorna True (cache)
- Se faltam 0-7 dias para expirar -> tenta validar no servidor, mas retorna True
  mesmo se falhar (offline/erro)
- Se expirou -> valida obrigatoriamente; se inválida, salva como inativa e retorna False
- Chave válida é consultada no Supabase via Security.SUPABASE_*
"""

from datetime import datetime, timedelta
from typing import Optional

import requests

from ..core.config.Security import Security
from .BaseUtil import BaseUtil
from .Preferences import Preferences
from .ToolKeys import ToolKey


class LicenseManager(BaseUtil):
    """
    Gerenciador de licença com cache mensal e renovação antecipada.

    Constantes:
        RENEWAL_WINDOW_DAYS: int — dias antes do vencimento para tentar renovar (7)

    Preferências utilizadas (system_preferences):
        license_key: str — chave de licença fornecida pelo usuário
        license_status: str — "active" | "inactive" | ""
        license_expiry: str — data de expiração no formato "YYYY-MM-DD"
        license_tier: str — tier da licença "BASIC" | "PRO" | "ENTERPRISE" | ""
    """

    RENEWAL_WINDOW_DAYS: int = 7

    DATE_FORMAT: str = "%Y-%m-%d"

    LICENSE_TIER_BASIC: str = "BASIC"
    LICENSE_TIER_PRO: str = "PRO"
    LICENSE_TIER_ENTERPRISE: str = "ENTERPRISE"
    LICENSE_TIER_PREMIUM: str = "PREMIUM"
    LICENSE_TIER_MASTER: str = "MASTER"

    def __init__(self, tool_key: str = ToolKey.UNTRACEABLE):
        """
        Inicializa o gerenciador de licença.

        Args:
            tool_key: Chave da ferramenta para rastreamento de logs.
        """
        super().__init__(tool_key)

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def is_license_valid(self) -> bool:
        """
        Verifica se a licença é válida, respeitando cache e renovação.

        Fluxo:
        1. Carrega license_key das preferências do sistema
        2. Se não há license_key -> False
        3. Se há cache ativo (status="active" + expiry no futuro com margem > 7 dias) -> True
        4. Se está no período de renovação (0-7 dias antes do fim) -> tenta validar
           no servidor, mas retorna True mesmo em falha (atualiza expiry se conseguir)
        5. Se expirou -> valida obrigatoriamente no servidor; se inválida marca como
           inativa -> False

        Returns:
            bool: True se a licença é válida, False caso contrário
        """
        prefs = Preferences.load_tool_prefs(ToolKey.SYSTEM)
        license_key = (prefs.get("license_key") or "").strip()

        if not license_key:
            self.logger.debug("Nenhuma chave de licença configurada")
            return False

        status = prefs.get("license_status", "")
        expiry_str = prefs.get("license_expiry", "")

        today = datetime.now().date()

        # --- Caso 1: Cache ativo com expiry válido ---
        if status == "active" and expiry_str:
            expiry = self._parse_date(expiry_str)
            if expiry is not None:
                days_remaining = (expiry - today).days

                if days_remaining > self.RENEWAL_WINDOW_DAYS:
                    # Cache válido, ainda muito tempo -> retorna True sem verificar
                    self.logger.debug(
                        f"Licença em cache ativa, expira em {days_remaining} dias"
                    )
                    return True

                elif days_remaining >= 0:
                    # Período de renovação (0-7 dias restantes)
                    self.logger.debug(
                        f"Licença em renovação ({days_remaining} dias restantes), "
                        f"tentando validar no servidor..."
                    )
                    return self._try_renew(license_key, prefs, today)

                else:
                    # Expirada -> valida obrigatoriamente
                    self.logger.debug(
                        f"Licença expirada há {-days_remaining} dias, "
                        f"validando no servidor..."
                    )
                    return self._validate_and_update(license_key, prefs, today)

        # --- Caso 2: Sem cache -> valida do zero ---
        self.logger.debug("Nenhum cache de licença encontrado, validando...")
        return self._validate_and_update(license_key, prefs, today)

    def get_license_info(self) -> dict:
        """
        Retorna informações completas da licença cadastrada.

        Returns:
            dict: {
                "has_key": bool,
                "key_preview": str (primeiros 4 chars + "****"),
                "status": str ("active" | "inactive" | ""),
                "expiry": str (data formatada ou ""),
                "tier": str ("BASIC" | "PRO" | "ENTERPRISE" | "PREMIUM" | "MASTER" | ""),
                "level": str ("Básico" | "Profissional" | "Enterprise" | "Premium" | "Master" | ""),
                "is_active": bool,
                "days_remaining": int,
            }
        """
        prefs = Preferences.load_tool_prefs(ToolKey.SYSTEM)
        license_key = (prefs.get("license_key") or "").strip()
        status = prefs.get("license_status", "")
        expiry_str = prefs.get("license_expiry", "")
        tier = prefs.get("license_tier", "")

        info = {
            "has_key": bool(license_key),
            "key_preview": (license_key[:4] + "****") if license_key else "",
            "status": status,
            "expiry": expiry_str,
            "tier": tier,
            "level": self._tier_to_label(tier) if tier else "",
            "is_active": False,
            "days_remaining": -1,
        }

        if status == "active" and expiry_str:
            expiry = self._parse_date(expiry_str)
            if expiry is not None:
                today = datetime.now().date()
                days = (expiry - today).days
                info["days_remaining"] = days
                info["is_active"] = days >= 0

        return info

    def save_license_key(self, license_key: str) -> dict:
        """
        Salva e valida uma chave de licença junto ao servidor.

        Fluxo:
        1. Valida a chave no Supabase
        2. Se válida: salva chave, status "active", expiry (+30 dias), tier
        3. Se inválida: NÃO salva, retorna erro

        Args:
            license_key: Chave de licença a ser salva.

        Returns:
            dict: {"success": bool, "message": str}
        """
        license_key = license_key.strip()
        if not license_key:
            self.logger.warning("Tentativa de salvar chave vazia")
            return {"success": False, "message": "Chave de licença não pode estar vazia."}

        is_valid, tier = self._validate_and_get_tier(license_key)

        if not is_valid:
            self.logger.warning("Tentativa de salvar chave inválida")
            return {"success": False, "message": "Chave de licença inválida."}

        today = datetime.now().date()
        new_expiry = today + timedelta(days=30)

        prefs = Preferences.load_tool_prefs(ToolKey.SYSTEM)
        prefs["license_key"] = license_key
        prefs["license_status"] = "active"
        prefs["license_expiry"] = new_expiry.strftime(self.DATE_FORMAT)
        prefs["license_tier"] = tier
        Preferences.save_tool_prefs(ToolKey.SYSTEM, prefs)

        self.logger.debug(
            f"Licença salva com sucesso: tier={tier}, "
            f"expira={new_expiry.strftime(self.DATE_FORMAT)}"
        )
        return {"success": True, "message": "Licença salva e validada com sucesso."}

    def delete_license(self) -> None:
        """
        Remove todos os dados de licença das preferências.
        """
        prefs = Preferences.load_tool_prefs(ToolKey.SYSTEM)
        prefs["license_key"] = ""
        prefs["license_status"] = ""
        prefs["license_expiry"] = ""
        prefs["license_tier"] = ""
        Preferences.save_tool_prefs(ToolKey.SYSTEM, prefs)

        self.logger.debug("Licença removida das preferências")

    # ----------------------------------------------------------------
    # Internal Methods
    # ----------------------------------------------------------------

    @staticmethod
    def _validate_and_get_tier(license_key: str) -> tuple:
        """
        Valida a chave no servidor Supabase e retorna (is_valid, tier).

        Args:
            license_key: Chave de licença.

        Returns:
            tuple: (bool, str)
        """
        result = LicenseManager._query_server(license_key)

        if result is not None:
            # Servidor respondeu
            ativo = result.get("ativo", False)
            if ativo:
                nivel = result.get("nivel", 1)
                tier = LicenseManager._nivel_to_tier(nivel)
                return True, tier
            return False, ""

        # Servidor indisponível — falha segura
        return False, ""

    @staticmethod
    def _query_server(license_key: str) -> Optional[dict]:
        """
        Consulta a chave no Supabase.

        Args:
            license_key: Chave a consultar.

        Returns:
            Optional[dict]: Registro da chave (com 'nivel', 'ativo') ou None se
                            não encontrada ou erro de conexão.
        """
        try:
            url = f"{Security.SUPABASE_URL}/rest/v1/{Security.SUPABASE_LICENSE_TABLE}"
            params = {
                "api_key": f"eq.{license_key}",
                "select": "*",
            }
            resp = requests.get(
                url,
                headers=Security.SUPABASE_HEADERS,
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list) and len(data) > 0:
                return data[0]

            return None  # Não encontrou a chave

        except requests.RequestException as e:
            # Log silencioso — não quebra fluxo em caso de offline
            import logging
            logging.getLogger(__name__).warning(
                f"Falha ao consultar servidor de licença: {e}"
            )
            return None

    @staticmethod
    def _nivel_to_tier(nivel: int) -> str:
        """Converte nível numérico (1-5) para tier string."""
        mapping = {
            1: LicenseManager.LICENSE_TIER_BASIC,
            2: LicenseManager.LICENSE_TIER_PRO,
            3: LicenseManager.LICENSE_TIER_ENTERPRISE,
            4: LicenseManager.LICENSE_TIER_PREMIUM,
            5: LicenseManager.LICENSE_TIER_MASTER,
        }
        return mapping.get(nivel, LicenseManager.LICENSE_TIER_BASIC)

    @staticmethod
    def _tier_to_label(tier: str) -> str:
        """Converte tier code para label amigável."""
        labels = {
            LicenseManager.LICENSE_TIER_BASIC: "Básico",
            LicenseManager.LICENSE_TIER_PRO: "Profissional",
            LicenseManager.LICENSE_TIER_ENTERPRISE: "Enterprise",
            LicenseManager.LICENSE_TIER_PREMIUM: "Premium",
            LicenseManager.LICENSE_TIER_MASTER: "Master",
        }
        return labels.get(tier, "")

    @staticmethod
    def _check_license(license_key: str) -> bool:
        """
        Valida a chave de licença no servidor Supabase.

        Args:
            license_key: Chave de licença a ser validada.

        Returns:
            bool: True se a chave é válida, False caso contrário.
        """
        result = LicenseManager._query_server(license_key)

        if result is not None:
            ativo = result.get("ativo", False)
            return bool(ativo)

        # Servidor indisponível — retorna False para validações críticas
        return False

    def _try_renew(self, license_key: str, prefs: dict, today: datetime.date) -> bool:
        """
        Tenta renovar a licença no período de janela (0-7 dias antes do fim).

        Se a validação no servidor for bem-sucedida, atualiza a data de expiração.
        Se falhar (offline/erro), ainda retorna True (período de graça).

        Args:
            license_key: Chave de licença.
            prefs: Preferências do sistema atuais.
            today: Data de hoje.

        Returns:
            bool: Sempre True (período de graça).
        """
        is_valid = self._check_license(license_key)

        if is_valid:
            new_expiry = today + timedelta(days=30)
            self._save_license_cache(prefs, "active", new_expiry)
            self.logger.debug(
                f"Licença renovada com sucesso até "
                f"{new_expiry.strftime(self.DATE_FORMAT)}"
            )
        else:
            self.logger.warning(
                "Falha na renovação da licença (período de graça ativo)"
            )

        # Mesmo inválida, retorna True durante o período de renovação
        return True

    def _validate_and_update(
        self, license_key: str, prefs: dict, today: datetime.date
    ) -> bool:
        """
        Valida a licença no servidor e atualiza o cache nas preferências.

        Args:
            license_key: Chave de licença.
            prefs: Preferências do sistema atuais.
            today: Data de hoje.

        Returns:
            bool: True se a licença é válida, False caso contrário.
        """
        is_valid = self._check_license(license_key)

        if is_valid:
            new_expiry = today + timedelta(days=30)
            self._save_license_cache(prefs, "active", new_expiry)
            self.logger.debug(
                f"Licença validada com sucesso até "
                f"{new_expiry.strftime(self.DATE_FORMAT)}"
            )
            return True
        else:
            self._save_license_cache(prefs, "inactive", None)
            self.logger.warning("Chave de licença inválida")
            return False

    def _save_license_cache(
        self,
        prefs: dict,
        status: str,
        expiry: Optional[datetime.date],
    ) -> None:
        """
        Salva o status da licença nas preferências do sistema.

        Args:
            prefs: Preferências do sistema atuais.
            status: "active" | "inactive".
            expiry: Data de expiração (None para inativa).
        """
        prefs["license_status"] = status
        if expiry is not None:
            prefs["license_expiry"] = expiry.strftime(self.DATE_FORMAT)
        else:
            prefs["license_expiry"] = ""
        Preferences.save_tool_prefs(ToolKey.SYSTEM, prefs)

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime.date]:
        """
        Converte string de data para date.

        Args:
            date_str: Data no formato "YYYY-MM-DD".

        Returns:
            date ou None se inválida.
        """
        try:
            return datetime.strptime(date_str, LicenseManager.DATE_FORMAT).date()
        except (ValueError, TypeError):
            return None