# -*- coding: utf-8 -*-
"""Gerenciamento local de licenças do Cadmus.

A estrutura de registro permanece disponível para restauração futura, mas a
validação atual é totalmente offline. A licença genérica é persistida no mesmo
arquivo local assinado usado pelo registro original.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from ...utils.BaseUtil import BaseUtil
from ...utils.ToolKeys import ToolKey
from .RegistryFileManager import RegistryFileManager


class RegistryManager(BaseUtil):
    """Gerencia licença local genérica sem depender de serviços externos."""

    ENABLE_REGISTRY: bool = True
    OFFLINE_MODE: bool = True
    GENERIC_LICENSE_KEY: str = "CADMUS-OFFLINE-GENERIC"
    GENERIC_LICENSE_LEVEL: int = 5
    GENERIC_LICENSE_DAYS: int = 3650
    DATE_FORMAT: str = "%Y-%m-%d"

    def __init__(self, tool_key: str = ToolKey.UNTRACEABLE):
        """Inicializa o gerenciador usando o arquivo local de licença."""
        super().__init__(tool_key)
        self._file_mgr = RegistryFileManager(tool_key)

    def is_registry_valid(self) -> bool:
        """Verifica a licença local ou cria a licença genérica offline."""
        if not self.ENABLE_REGISTRY:
            self.logger.debug(
                "Registro desabilitado; licença considerada válida"
            )
            return True

        if not self.OFFLINE_MODE:
            self.logger.warning(
                "Validação remota não configurada; registro offline mantido"
            )
            return False

        lic_data = self._ensure_offline_license()
        return bool(lic_data and self._file_mgr.validate_lic(lic_data))

    def get_registry_info(self) -> dict:
        """Retorna o estado da licença local atualmente ativa."""
        lic_data = (
            self._ensure_offline_license()
            if self.OFFLINE_MODE
            else self._file_mgr.load_lic()
        )

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

        license_key = (
            lic_data.get(RegistryFileManager.FIELD_LICENSE_KEY) or ""
        ).strip()
        expire_str = lic_data.get(RegistryFileManager.FIELD_EXPIRE_DATE, "")
        level = lic_data.get(RegistryFileManager.FIELD_LEVEL, 0)
        is_active = self._file_mgr.validate_lic(lic_data)

        info = {
            "has_key": bool(license_key),
            "key_preview": (license_key[:4] + "****") if license_key else "",
            "status": "active" if is_active else "inactive",
            "expiry": expire_str,
            "nivel": int(level) if isinstance(level, int) else 0,
            "is_active": is_active,
            "days_remaining": -1,
        }

        if expire_str and is_active:
            expiry = self._parse_date(expire_str)
            if expiry is not None:
                info["days_remaining"] = (expiry - datetime.now().date()).days

        return info

    def save_lic_key(self, lic_key: str) -> dict:
        """Salva uma chave local com nível máximo e validade prolongada."""
        if not self.OFFLINE_MODE:
            return {
                "success": False,
                "message": "Validação remota não configurada.",
            }

        lic_key = (lic_key or "").strip()
        if not lic_key:
            self.logger.warning("Tentativa de salvar chave vazia")
            return {
                "success": False,
                "message": "Chave de licença não pode estar vazia.",
            }

        expiry = datetime.now().date() + timedelta(
            days=self.GENERIC_LICENSE_DAYS
        )
        lic_data = RegistryFileManager.build_lic_dict(
            license_key=lic_key,
            level=self.GENERIC_LICENSE_LEVEL,
            expire_date=expiry.strftime(self.DATE_FORMAT),
        )

        if not self._file_mgr.save_lic(lic_data):
            return {
                "success": False,
                "message": "Falha ao salvar arquivo de licença.",
            }

        self.logger.info(
            f"Licença local salva: nível={self.GENERIC_LICENSE_LEVEL}, "
            f"expira={expiry.strftime(self.DATE_FORMAT)}"
        )
        return {
            "success": True,
            "message": "Licença local salva com sucesso.",
        }

    def get_level(self) -> int:
        """Retorna o nível da licença local ativa."""
        return self.get_registry_info().get("nivel", 0)

    def has_minimum_level(self, min_level: int) -> bool:
        """Verifica se a licença local atende ao nível solicitado."""
        if not self.ENABLE_REGISTRY:
            return True
        return self.is_registry_valid() and self.get_level() >= min_level

    def delete_lic(self) -> None:
        """Remove o arquivo local de licença."""
        self._file_mgr.delete_lic()
        self.logger.debug("Arquivo local de licença removido")

    def _build_generic_license(self) -> dict:
        """Constrói os dados da licença genérica offline."""
        expiry = datetime.now().date() + timedelta(
            days=self.GENERIC_LICENSE_DAYS
        )
        return RegistryFileManager.build_lic_dict(
            license_key=self.GENERIC_LICENSE_KEY,
            level=self.GENERIC_LICENSE_LEVEL,
            expire_date=expiry.strftime(self.DATE_FORMAT),
        )

    def _ensure_offline_license(self) -> Optional[dict]:
        """Carrega ou cria a licença genérica local assinada."""
        lic_data = self._file_mgr.load_lic()
        if lic_data is not None and self._file_mgr.validate_lic(lic_data):
            current_level = lic_data.get(RegistryFileManager.FIELD_LEVEL, 0)
            if current_level >= self.GENERIC_LICENSE_LEVEL:
                return lic_data

        generic_data = self._build_generic_license()
        if not self._file_mgr.save_lic(generic_data):
            self.logger.error("Falha ao salvar licença genérica offline")
            return None

        saved_data = self._file_mgr.load_lic()
        if saved_data is None or not self._file_mgr.validate_lic(saved_data):
            self.logger.error("Licença genérica offline não pôde ser validada")
            return None

        self.logger.info(
            "Licença genérica offline ativa até "
            f"{saved_data.get(RegistryFileManager.FIELD_EXPIRE_DATE)}"
        )
        return saved_data

    @staticmethod
    def _parse_date(date_str: str) -> Optional[date]:
        """Converte uma data ISO para um objeto date."""
        try:
            return datetime.strptime(
                date_str, RegistryManager.DATE_FORMAT
            ).date()
        except (ValueError, TypeError):
            return None
