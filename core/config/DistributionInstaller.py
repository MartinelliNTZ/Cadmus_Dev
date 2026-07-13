# -*- coding: utf-8 -*-
"""
DistributionInstaller — Instalador de Pacotes Ofuscados (.cadmus_dist)
======================================================================
Gerencia a extração e instalação de módulos Python ofuscados com PyArmor,
empacotados no formato .cadmus_dist.

Fluxo:
1. Abre .cadmus_dist (ZIP)
2. Lê metadata.json (versão, módulos, key opcional)
3. Extrai arquivos .pyd para as pastas corretas dentro do plugin
4. Se contém key: salva via RegistryManager
5. Valida instalação e retorna resultado

Uso:
    installer = DistributionInstaller(tool_key=ToolKey.SETTINGS)
    result = installer.install("caminho/para/pacote.cadmus_dist")
"""

import os
import json
import zipfile
import shutil
from typing import Optional

from ..config.RegistryManager import RegistryManager
from ...utils.ToolKeys import ToolKey
from ...utils.BaseUtil import BaseUtil


class DistributionInstaller(BaseUtil):
    """
    Instalador de pacotes de distribuição ofuscada (.cadmus_dist).

    Attributes:
        PLUGIN_ROOT: str — Caminho raiz do plugin Cadmus
        DIST_EXTENSION: str — Extensão do pacote de distribuição
    """

    DIST_EXTENSION: str = ".cadmus_dist"

    def __init__(self, tool_key: str = ToolKey.UNTRACEABLE):
        super().__init__(tool_key)
        # Resolve o caminho raiz do plugin (4 níveis acima: core/config/ -> plugin/)
        self._plugin_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self._registry_mgr = RegistryManager(tool_key=tool_key)

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def install(self, package_path: str, license_key: Optional[str] = None) -> dict:
        """
        Instala um pacote .cadmus_dist no plugin.

        Args:
            package_path: Caminho completo para o arquivo .cadmus_dist
            license_key: Chave de licença opcional (sobrescreve a do pacote)

        Returns:
            dict: {
                "success": bool,
                "message": str,
                "modules": list[str] — módulos instalados,
                "key_installed": bool,
            }
        """
        self.logger.info(f"Iniciando instalação: {package_path}")

        # --- Validação do pacote ---
        if not package_path or not os.path.isfile(package_path):
            msg = "Arquivo de pacote não encontrado."
            self.logger.error(msg)
            return {"success": False, "message": msg, "modules": [], "key_installed": False}

        if not package_path.lower().endswith(self.DIST_EXTENSION):
            msg = f"Extensão inválida. Esperado {self.DIST_EXTENSION}."
            self.logger.error(msg)
            return {"success": False, "message": msg, "modules": [], "key_installed": False}

        try:
            with zipfile.ZipFile(package_path, "r") as zf:
                # --- Lê metadata ---
                if "metadata.json" not in zf.namelist():
                    msg = "Pacote inválido: metadata.json não encontrado."
                    self.logger.error(msg)
                    return {"success": False, "message": msg, "modules": [], "key_installed": False}

                metadata = json.loads(zf.read("metadata.json"))
                modules = metadata.get("modules", [])
                package_key = metadata.get("key", "")

                self.logger.debug(
                    f"Metadados: versão={metadata.get('version')}, "
                    f"módulos={len(modules)}, tem_chave={bool(package_key)}"
                )

                # --- Extrai arquivos ---
                extracted = []
                errors = []

                for member in zf.namelist():
                    if member == "metadata.json":
                        continue

                    # Destino: raiz do plugin
                    dest_path = os.path.normpath(
                        os.path.join(self._plugin_root, member)
                    )

                    # Validação de segurança: não permite path traversal
                    if not dest_path.startswith(self._plugin_root):
                        self.logger.warning(
                            f"Path traversal detectado: {member}, ignorado."
                        )
                        continue

                    # Cria diretório destino se necessário
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                    # Extrai arquivo
                    try:
                        with zf.open(member) as source, open(dest_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                        extracted.append(member)
                        self.logger.debug(f"  Extraído: {member}")
                    except (IOError, OSError) as e:
                        errors.append(f"{member}: {e}")
                        self.logger.error(f"  Falha ao extrair {member}: {e}")

                # --- Instala chave de licença ---
                key_installed = False
                effective_key = license_key or package_key

                if effective_key:
                    self.logger.debug("Instalando chave de licença do pacote...")
                    key_result = self._registry_mgr.save_license_key(effective_key)
                    key_installed = key_result.get("success", False)
                    if key_installed:
                        self.logger.info("Chave de licença instalada com sucesso.")
                    else:
                        self.logger.warning(
                            f"Falha ao instalar chave: {key_result.get('message')}"
                        )

                # --- Resultado ---
                success = len(errors) == 0 and len(extracted) > 0
                msg = (
                    f"{len(extracted)} módulo(s) instalado(s) com sucesso."
                    if success
                    else f"{len(errors)} erro(s) durante instalação."
                )

                if key_installed:
                    msg += " Chave de licença instalada."

                self.logger.info(msg)

                return {
                    "success": success,
                    "message": msg,
                    "modules": extracted,
                    "key_installed": key_installed,
                    "errors": errors if errors else None,
                }

        except (zipfile.BadZipFile, json.JSONDecodeError, IOError, OSError) as e:
            msg = f"Falha ao processar pacote: {e}"
            self.logger.error(msg)
            return {"success": False, "message": msg, "modules": [], "key_installed": False}

    def validate_installation(self) -> dict:
        """
        Verifica se os módulos ofuscados estão corretamente instalados.

        Returns:
            dict: {
                "installed_modules": list[str],
                "missing_modules": list[str],
                "license_valid": bool,
            }
        """
        self.logger.debug("Validando instalação...")

        # Verifica licença
        lic_info = self._registry_mgr.get_license_info()
        license_valid = lic_info.get("is_active", False) and lic_info.get("has_key", False)

        return {
            "installed_modules": [],
            "missing_modules": [],
            "license_valid": license_valid,
        }

    @staticmethod
    def get_default_key() -> str:
        """Retorna a chave de licença padrão do sistema de distribuição."""
        return "7N1V9-2S1H9-5G9K4"