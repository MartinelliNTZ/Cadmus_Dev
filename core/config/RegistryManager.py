# -*- coding: utf-8 -*-
"""
LicenseManager — Gerenciamento de licença com cache e renovação automática
===========================================================================
Gerencia validação de licença com consulta ao servidor Supabase e cache em
arquivo ofuscado via LicenseFileManager.

Regras de validação:
- Se a licença está ativa e dentro do prazo (> 7 dias restantes) -> retorna True (cache)
- Se faltam 0-7 dias para expirar -> tenta validar no servidor, mas retorna True
  mesmo se falhar (offline/erro)
- Se expirou -> valida obrigatoriamente; se inválida, salva como inativa e retorna False
- Chave válida é consultada no Supabase via Security.SUPABASE_*

A persistência dos dados de licença é feita via LicenseFileManager em arquivo
ofuscado (%TEMP%/cadmus/license.dat). As chaves criptográficas são persistidas
em Preferences, garantindo que o arquivo seja legível entre sessões do QGIS.
"""

from datetime import datetime, timedelta
from typing import Optional

import requests

from .Security import Security
from ...utils.BaseUtil import BaseUtil
from .RegistryFileManager import RegistryFileManager
from ...utils.ToolKeys import ToolKey


class RegistryManager(BaseUtil):
    """
    Gerenciador de licença com cache mensal e renovação antecipada.

    A persistência é feita via LicenseFileManager em arquivo ofuscado.
    As chaves criptográficas são persistidas em Preferences.

    Constantes:
        ENABLE_REGISTRY: bool — habilita/desabilita o sistema de licença.
                          Quando False, nenhuma solicitação de registro é feita
                          e a licença é considerada válida (modo free total).
        RENEWAL_WINDOW_DAYS: int — dias antes do vencimento para tentar renovar (7)
    """

    ENABLE_REGISTRY: bool = False

    RENEWAL_WINDOW_DAYS: int = 7

    DATE_FORMAT: str = "%Y-%m-%d"

    def __init__(self, tool_key: str = ToolKey.UNTRACEABLE):
        super().__init__(tool_key)
        self._file_mgr = RegistryFileManager(tool_key)

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def is_registry_valid(self) -> bool:
        """
        Verifica se a licença é válida, respeitando cache e renovação.

        Fluxo:
        1. Carrega license_key do arquivo de licença ofuscado
        2. Se não há license_key -> False
        3. Se há cache ativo (expiry no futuro com margem > 7 dias) -> True
        4. Se está no período de renovação (0-7 dias antes do fim) -> tenta validar
           no servidor, mas retorna True mesmo em falha (atualiza expiry se conseguir)
        5. Se expirou -> valida obrigatoriamente no servidor; se inválida marca como
           inativa -> False

        Returns:
            bool: True se a licença é válida, False caso contrário
        """
        if not self.ENABLE_REGISTRY:
            self.logger.debug(
                "Registro desabilitado (ENABLE_REGISTRY=False) — licença considerada válida"
            )
            return True

        lic_data = self._file_mgr.load_lic()
        if lic_data is None:
            self.logger.debug("Nenhum cache de licença encontrado")
            return False

        license_key = (lic_data.get(
            RegistryFileManager.FIELD_LICENSE_KEY) or "").strip()

        if not license_key:
            self.logger.debug("Nenhuma chave de licença configurada")
            return False

        expire_str = lic_data.get(RegistryFileManager.FIELD_EXPIRE_DATE, "")
        today = datetime.now().date()

        # --- Caso 1: Cache ativo com expiry válido ---
        if expire_str:
            expiry = self._parse_date(expire_str)
            if expiry is not None:
                days_remaining = (expiry - today).days

                if days_remaining > self.RENEWAL_WINDOW_DAYS:
                    self.logger.debug(
                        f"Licença em cache ativa, expira em {days_remaining} dias"
                    )
                    return True

                elif days_remaining >= 0:
                    self.logger.debug(
                        f"Licença em renovação ({days_remaining} dias restantes), "
                        f"tentando validar no servidor..."
                    )
                    return self._try_renew(license_key, today)

                else:
                    self.logger.debug(
                        f"Licença expirada há {-days_remaining} dias, "
                        f"validando no servidor..."
                    )
                    return self._validate_and_update(license_key, today)

        # --- Caso 2: Sem cache válido -> valida do zero ---
        self.logger.debug("Nenhum cache de licença encontrado, validando...")
        return self._validate_and_update(license_key, today)

    def get_registry_info(self) -> dict:
        """
        Retorna informações completas da licença cadastrada.

        Returns:
            dict: {
                "has_key": bool,
                "key_preview": str (primeiros 4 chars + "****"),
                "status": str ("active" | "inactive" | ""),
                "expiry": str (data formatada ou ""),
                "nivel": int (nível 1-5, 0 se sem chave),
                "is_active": bool,
                "days_remaining": int,
            }
        """
        lic_data = self._file_mgr.load_lic()

        if lic_data is None:
            return {
                "has_key": False,
                "key_preview": "",
                "status": "",
                "expiry": "",
                "nivel": 0,
                "is_active": False,
                "days_remaining": -1,
            }

        license_key = (lic_data.get(
            RegistryFileManager.FIELD_LICENSE_KEY) or "").strip()
        expire_str = lic_data.get(RegistryFileManager.FIELD_EXPIRE_DATE, "")
        level = lic_data.get(RegistryFileManager.FIELD_LEVEL, 0)

        # Verifica validade do cache
        is_cached = self._file_mgr.validate_lic(lic_data)

        info = {
            "has_key": bool(license_key),
            "key_preview": (license_key[:4] + "****") if license_key else "",
            "status": "active" if is_cached else "inactive",
            "expiry": expire_str,
            "nivel": int(level) if isinstance(level, int) else 0,
            "is_active": is_cached,
            "days_remaining": -1,
        }

        if expire_str and is_cached:
            expiry = self._parse_date(expire_str)
            if expiry is not None:
                today = datetime.now().date()
                days = (expiry - today).days
                info["days_remaining"] = days
                info["is_active"] = days >= 0

        return info

    def save_lic_key(self, lic_key: str) -> dict:
        """
        Salva e valida uma chave de licença junto ao servidor.

        Fluxo:
        1. Valida a chave no Supabase
        2. Se válida: salva chave, status "active", expiry (+30 dias), nivel
           em arquivo ofuscado via LicFileManager
        3. Se inválida: NÃO salva, retorna erro

        Args:
            lic_key: Chave de licença a ser salva.

        Returns:
            dict: {"success": bool, "message": str}
        """
        if not self.ENABLE_REGISTRY:
            self.logger.debug(
                "Registro desabilitado (ENABLE_REGISTRY=False) — chave não salva"
            )
            return {
                "success": False,
                "message": "Sistema de registro desabilitado no momento.",
            }

        lic_key = lic_key.strip()
        if not lic_key:
            self.logger.warning("Tentativa de salvar chave vazia")
            return {"success": False, "message": "Chave de licença não pode estar vazia."}

        is_valid, nivel = self._validate_and_get_nivel(lic_key)

        if not is_valid:
            self.logger.warning("Tentativa de salvar chave inválida")
            return {"success": False, "message": "Chave de licença inválida."}

        today = datetime.now().date()
        new_expiry = today + timedelta(days=30)

        lic_data = RegistryFileManager.build_lic_dict(
            license_key=lic_key,
            level=nivel,
            expire_date=new_expiry.strftime(self.DATE_FORMAT),
        )

        saved = self._file_mgr.save_lic(lic_data)
        if not saved:
            return {"success": False, "message": "Falha ao salvar arquivo de licença."}

        self.logger.debug(
            f"Licença salva com sucesso: nivel={nivel}, "
            f"expira={new_expiry.strftime(self.DATE_FORMAT)}"
        )
        return {"success": True, "message": "Licença salva e validada com sucesso."}

    def get_level(self) -> int:
        """
        Retorna o nível atual da licença.

        Returns:
            int: Nível 1-5 se licença válida, 0 se sem chave ou inválida.
        """
        lic_info = self.get_registry_info()
        return lic_info.get("nivel", 0)

    def has_minimum_level(self, min_level: int) -> bool:
        """
        Verifica se o nível da licença atual é >= min_level.

        A licença precisa ser válida (is_license_valid()) E ter nível
        suficiente.

        Args:
            min_level: Nível mínimo exigido (ex: 3).

        Returns:
            bool: True se a licença é válida e tem nível >= min_level.
        """
        if not self.ENABLE_REGISTRY:
            return True

        if not self.is_registry_valid():
            return False

        current_level = self.get_level()
        return current_level >= min_level

    def delete_lic(self) -> None:
        """
        Remove o arquivo de licença ofuscado do disco.
        """
        self._file_mgr.delete_lic()
        self.logger.debug("Licença removida do arquivo ofuscado")

    # ----------------------------------------------------------------
    # Internal Methods
    # ----------------------------------------------------------------

    @staticmethod
    def _validate_and_get_nivel(license_key: str) -> tuple:
        """
        Valida a chave no servidor Supabase e retorna (is_valid, nivel).

        Args:
            license_key: Chave de licença.

        Returns:
            tuple: (bool, int) — nivel 1-5 se válida, 0 se inválida
        """
        result = RegistryManager._query_server(license_key)

        if result is not None:
            ativo = result.get("ativo", False)
            if ativo:
                nivel = result.get("nivel", 1)
                return True, int(nivel)
            return False, 0

        return False, 0

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
        if not RegistryManager.ENABLE_REGISTRY:
            return None

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

            return None

        except requests.RequestException as e:
            from .LogUtils import LogUtils
            LogUtils(tool=ToolKey.SYSTEM, class_name="RegistryManager").warning(
                f"Falha ao consultar servidor de licença: {e}"
            )
            return None

    @staticmethod
    def _check_license(license_key: str) -> bool:
        """
        Valida a chave de licença no servidor Supabase.

        Args:
            license_key: Chave de licença a ser validada.

        Returns:
            bool: True se a chave é válida, False caso contrário.
        """
        result = RegistryManager._query_server(license_key)

        if result is not None:
            ativo = result.get("ativo", False)
            return bool(ativo)

        return False

    def _try_renew(self, license_key: str, today: datetime.date) -> bool:
        """
        Tenta renovar a licença no período de janela (0-7 dias antes do fim).

        Se a validação no servidor for bem-sucedida, atualiza a data de expiração
        no arquivo ofuscado.
        Se falhar (offline/erro), ainda retorna True (período de graça).

        Args:
            license_key: Chave de licença.
            today: Data de hoje.

        Returns:
            bool: Sempre True (período de graça).
        """
        is_valid = self._check_license(license_key)

        if is_valid:
            new_expiry = today + timedelta(days=30)
            lic_data = RegistryFileManager.build_lic_dict(
                license_key=license_key,
                level=1,
                expire_date=new_expiry.strftime(self.DATE_FORMAT),
            )
            # Tenta carregar dados existentes para preservar nível
            existing = self._file_mgr.load_lic()
            if existing and isinstance(existing.get(RegistryFileManager.FIELD_LEVEL), int):
                lic_data[RegistryFileManager.FIELD_LEVEL] = existing[RegistryFileManager.FIELD_LEVEL]

            self._file_mgr.save_lic(lic_data)
            self.logger.debug(
                f"Licença renovada com sucesso até "
                f"{new_expiry.strftime(self.DATE_FORMAT)}"
            )
        else:
            self.logger.warning(
                "Falha na renovação da licença (período de graça ativo)"
            )

        return True

    def _validate_and_update(
        self, license_key: str, today: datetime.date
    ) -> bool:
        """
        Valida a licença no servidor e atualiza o cache no arquivo ofuscado.

        Args:
            license_key: Chave de licença.
            today: Data de hoje.

        Returns:
            bool: True se a licença é válida, False caso contrário.
        """
        is_valid = self._check_license(license_key)

        if is_valid:
            new_expiry = today + timedelta(days=30)
            lic_data = RegistryFileManager.build_lic_dict(
                license_key=license_key,
                level=1,
                expire_date=new_expiry.strftime(self.DATE_FORMAT),
            )
            # Tenta carregar dados existentes para preservar nível
            existing = self._file_mgr.load_lic()
            if existing and isinstance(existing.get(RegistryFileManager.FIELD_LEVEL), int):
                lic_data[RegistryFileManager.FIELD_LEVEL] = existing[RegistryFileManager.FIELD_LEVEL]

            self._file_mgr.save_lic(lic_data)
            self.logger.debug(
                f"Licença validada com sucesso até "
                f"{new_expiry.strftime(self.DATE_FORMAT)}"
            )
            return True
        else:
            self._file_mgr.delete_lic()
            self.logger.warning("Chave de licença inválida, cache removido")
            return False

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
            return datetime.strptime(date_str, RegistryManager.DATE_FORMAT).date()
        except (ValueError, TypeError):
            return None
