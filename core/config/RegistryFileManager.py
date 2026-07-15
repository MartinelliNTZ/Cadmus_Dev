# -*- coding: utf-8 -*-
"""
LicenseFileManager — Gerenciamento de arquivo de licença protegido
===================================================================
Armazena dados da licença em um arquivo ofuscado com HMAC para detecção
de adulteração.

Utiliza apenas bibliotecas padrão do Python:
    json, os, base64, hashlib, hmac, secrets, datetime, zlib

Pipeline de escrita:
    dict -> JSON -> HMAC -> compress -> XOR keystream -> Base64 -> license.dat

Pipeline de leitura:
    license.dat -> Base64 decode -> XOR keystream -> decompress -> JSON -> HMAC verify

Arquivo salvo em: {cadmus_temp_root}/license.dat

As chaves criptográficas são fixas na classe (constantes), garantindo que o
arquivo seja legível entre sessões do QGIS sem depender de Preferences.
"""

import json
import os
import base64
import hashlib
import hmac
import zlib
from typing import Optional

from ...utils.BaseUtil import BaseUtil
from ...utils.ExplorerUtils import ExplorerUtils


class RegistryFileManager(BaseUtil):
    """
    Gerencia um arquivo de licença ofuscado com integridade HMAC.

    Chaves criptográficas fixas (constantes da classe) para garantir
    persistência entre sessões.

    Constantes:
        _SECRET_KEY: bytes — usada para gerar o keystream (XOR)
        _HMAC_KEY: bytes — usada exclusivamente para assinatura HMAC
        LICENSE_VERSION: int — versão do formato do arquivo (1)
        COMPRESSION: bool — se True, aplica zlib.compress antes do XOR
        LICENSE_FILENAME: str — nome do arquivo de licença
    """

    # Chaves fixas (NÃO mudar entre versões ou arquivos existentes ficarão ilegíveis)
    _SECRET_KEY: bytes = b"C4dmu5_S3cr3t_K3y_2026!@#$%^&*()_+="
    _HMAC_KEY: bytes = b"C4dmu5_HM4c_K3y_2026!@#$%^&*()_+="

    LICENSE_VERSION: int = 1
    COMPRESSION: bool = True
    LICENSE_FILENAME: str = "A1GPCTR8.dat"

    # Nomes dos campos no dicionário
    FIELD_LICENSE_KEY: str = "license_key"
    FIELD_LEVEL: str = "level"
    FIELD_EXPIRE_DATE: str = "expire_date"
    FIELD_CREATED_AT: str = "created_at"
    FIELD_MACHINE_ID: str = "machine_id"
    FIELD_VERSION: str = "version"
    FIELD_SIGNATURE: str = "signature"

    def __init__(self, tool_key: str = BaseUtil.TOOL_KEY_UNTRACEABLE):
        super().__init__(tool_key)

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def save_lic(self, data: dict) -> bool:
        """
        Salva os dados da licença no arquivo ofuscado.

        Args:
            data: Dicionário com dados da licença.

        Returns:
            bool: True se salvou com sucesso.
        """
        try:
            # Garante campos obrigatórios
            if self.FIELD_VERSION not in data:
                data[self.FIELD_VERSION] = self.LICENSE_VERSION
            if self.FIELD_CREATED_AT not in data:
                from datetime import datetime
                data[self.FIELD_CREATED_AT] = datetime.now().isoformat()

            # Gera e adiciona assinatura HMAC
            signature = self.generate_hmac(data)
            data[self.FIELD_SIGNATURE] = signature

            # Serializa JSON
            json_str = json.dumps(
                data, ensure_ascii=False, separators=(",", ":"))

            # Converte para bytes
            json_bytes = json_str.encode("utf-8")

            # Comprime (opcional)
            if self.COMPRESSION:
                json_bytes = zlib.compress(json_bytes)

            # Gera keystream
            stream = self.generate_keystream(self._SECRET_KEY, len(json_bytes))

            # XOR
            encrypted = self.xor_data(json_bytes, stream)

            # Base64
            b64 = base64.b64encode(encrypted).decode("ascii")

            # Salva arquivo
            file_path = self._get_file_path()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="ascii") as f:
                f.write(b64)

            self.logger.info(
                f"Licença salva em: {file_path} "
                f"(version={data.get(self.FIELD_VERSION)}, "
                f"level={data.get(self.FIELD_LEVEL)})"
            )
            return True

        except Exception as e:
            self.logger.error(
                "Falha ao salvar licença",
                code="LIC_SAVE_ERR",
                error=str(e),
            )
            return False

    def load_lic(self) -> Optional[dict]:
        """
        Carrega e valida os dados da licença do arquivo ofuscado.

        Returns:
            Optional[dict]: Dicionário com dados da licença ou None se
                            arquivo não existe, adulterado ou inválido.
        """
        file_path = self._get_file_path()
        if not os.path.isfile(file_path):
            self.logger.debug(
                f"Arquivo de licença não encontrado: {file_path}")
            return None

        try:
            # Lê Base64 do arquivo
            with open(file_path, "r", encoding="ascii") as f:
                b64 = f.read().strip()

            # Base64 decode
            encrypted = base64.b64decode(b64)

            # Gera keystream (mesmo tamanho)
            stream = self.generate_keystream(self._SECRET_KEY, len(encrypted))

            # XOR
            json_bytes = self.xor_data(encrypted, stream)

            # Descompressão
            if self.COMPRESSION:
                json_bytes = zlib.decompress(json_bytes)

            # Parse JSON
            json_str = json_bytes.decode("utf-8")
            data = json.loads(json_str)

            # Valida HMAC
            if self.FIELD_SIGNATURE not in data:
                self.logger.warning(
                    "Licença sem assinatura HMAC", code="LIC_NO_SIG")
                return None

            stored_sig = data.pop(self.FIELD_SIGNATURE, "")

            if not self.verify_hmac(data, stored_sig):
                self.logger.warning(
                    "Licença adulterada (HMAC inválido)", code="LIC_TAMPERED")
                return None

            # Re-adiciona assinatura para consistência
            data[self.FIELD_SIGNATURE] = stored_sig

            self.logger.debug(
                f"Licença carregada: level={data.get(self.FIELD_LEVEL)}, "
                f"expire={data.get(self.FIELD_EXPIRE_DATE)}"
            )
            return data

        except (json.JSONDecodeError, zlib.error, ValueError, OSError) as e:
            self.logger.error(
                "Falha ao carregar licença",
                code="LIC_LOAD_ERR",
                error=str(e),
            )
            return None

    def validate_lic(self, data: Optional[dict] = None) -> bool:
        """
        Valida todos os critérios da licença.

        Verifica:
        - assinatura HMAC
        - data de expiração
        - estrutura dos campos obrigatórios
        - versão do arquivo

        Args:
            data: Dicionário com dados (se None, carrega do arquivo).

        Returns:
            bool: True se a licença é válida.
        """
        if data is None:
            data = self.load_lic()

        if data is None:
            return False

        # --- Estrutura dos campos ---
        required_fields = [
            self.FIELD_LICENSE_KEY,
            self.FIELD_LEVEL,
            self.FIELD_EXPIRE_DATE,
            self.FIELD_VERSION,
            self.FIELD_SIGNATURE,
        ]
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Campo obrigatório ausente: {field}")
                return False

        # --- Versão do arquivo ---
        if data.get(self.FIELD_VERSION) != self.LICENSE_VERSION:
            self.logger.warning(
                f"Versão do arquivo incompatível: "
                f"{data.get(self.FIELD_VERSION)} != {self.LICENSE_VERSION}"
            )
            return False

        # --- Assinatura HMAC ---
        stored_sig = data.get(self.FIELD_SIGNATURE, "")
        data_copy = dict(data)
        data_copy.pop(self.FIELD_SIGNATURE, None)

        if not self.verify_hmac(data_copy, stored_sig):
            self.logger.warning("HMAC inválido na validação")
            return False

        # --- Data de expiração ---
        from datetime import datetime
        expire_str = data.get(self.FIELD_EXPIRE_DATE, "")
        if expire_str:
            try:
                expire = datetime.strptime(expire_str, "%Y-%m-%d").date()
                today = datetime.now().date()
                if expire < today:
                    self.logger.warning(f"Licença expirada em {expire_str}")
                    return False
            except (ValueError, TypeError):
                self.logger.warning(
                    f"Data de expiração inválida: {expire_str}")
                return False

        # --- Level deve ser numérico ---
        level = data.get(self.FIELD_LEVEL)
        if not isinstance(level, int) or level < 1 or level > 5:
            self.logger.warning(f"Nível inválido: {level}")
            return False

        return True

    def delete_lic(self) -> bool:
        """
        Remove o arquivo de licença do disco.

        Returns:
            bool: True se removeu ou arquivo não existia.
        """
        file_path = self._get_file_path()
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                self.logger.debug(f"Arquivo de licença removido: {file_path}")
            return True
        except OSError as e:
            self.logger.error(
                "Falha ao remover arquivo de licença",
                code="LIC_DEL_ERR",
                error=str(e),
            )
            return False

    # ----------------------------------------------------------------
    # Cryptographic Helpers
    # ----------------------------------------------------------------

    @staticmethod
    def generate_keystream(key: bytes, size: int) -> bytes:
        """
        Gera um fluxo de bytes pseudoaleatório usando SHA-256.

        Fluxo:
            SHA256(key + counter) para counter=0,1,2,... até atingir size.

        Args:
            key: Chave secreta (bytes).
            size: Número de bytes desejado.

        Returns:
            bytes: Keystream de tamanho 'size'.
        """
        result = b""
        counter = 0
        while len(result) < size:
            chunk = hashlib.sha256(key + str(counter).encode("utf-8")).digest()
            result += chunk
            counter += 1
        return result[:size]

    @staticmethod
    def xor_data(data: bytes, keystream: bytes) -> bytes:
        """
        Aplica XOR byte a byte entre dados e keystream.

        Args:
            data: Dados de entrada.
            keystream: Keystream do mesmo tamanho.

        Returns:
            bytes: Dados transformados (XOR).
        """
        return bytes(a ^ b for a, b in zip(data, keystream))

    @staticmethod
    def generate_hmac(data: dict) -> str:
        """
        Gera assinatura HMAC-SHA256 hexadecimal dos dados.

        Args:
            data: Dicionário com dados (sem o campo 'signature').

        Returns:
            str: Assinatura HMAC em hexadecimal.
        """
        data_copy = dict(data)
        data_copy.pop(RegistryFileManager.FIELD_SIGNATURE, None)

        json_str = json.dumps(
            data_copy, ensure_ascii=False, separators=(",", ":"))
        json_bytes = json_str.encode("utf-8")

        sig = hmac.new(
            RegistryFileManager._HMAC_KEY,
            json_bytes,
            hashlib.sha256,
        ).hexdigest()
        return sig

    @staticmethod
    def verify_hmac(data: dict, signature: str) -> bool:
        """
        Verifica se a assinatura HMAC corresponde aos dados.

        Args:
            data: Dicionário com dados (sem o campo 'signature').
            signature: Assinatura HMAC esperada.

        Returns:
            bool: True se a assinatura é válida.
        """
        expected = RegistryFileManager.generate_hmac(data)
        return hmac.compare_digest(expected, signature)

    # ----------------------------------------------------------------
    # Internal Helpers
    # ----------------------------------------------------------------

    def _get_file_path(self) -> str:
        """
        Retorna o caminho completo do arquivo de licença.

        O arquivo fica na raiz temporária do Cadmus.
        """
        temp_root = ExplorerUtils.get_cadmus_temp_root(self.tool_key)
        file_path = os.path.join(temp_root, self.LICENSE_FILENAME)
        self.logger.debug(f"Caminho do arquivo de licença: {file_path}")
        return file_path

    @staticmethod
    def build_lic_dict(
        license_key: str,
        level: int,
        expire_date: str,
        machine_id: str = "",
    ) -> dict:
        """
        Constrói um dicionário de licença padronizado.

        Args:
            license_key: Chave de licença.
            level: Nível (1-5).
            expire_date: Data de expiração (YYYY-MM-DD).
            machine_id: Identificador da máquina (opcional).

        Returns:
            dict: Dicionário formatado.
        """
        from datetime import datetime
        return {
            RegistryFileManager.FIELD_LICENSE_KEY: license_key,
            RegistryFileManager.FIELD_LEVEL: level,
            RegistryFileManager.FIELD_EXPIRE_DATE: expire_date,
            RegistryFileManager.FIELD_CREATED_AT: datetime.now().isoformat(),
            RegistryFileManager.FIELD_MACHINE_ID: machine_id,
            RegistryFileManager.FIELD_VERSION: RegistryFileManager.LICENSE_VERSION,
        }
