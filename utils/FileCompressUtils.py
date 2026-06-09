# -*- coding: utf-8 -*-
import os
import zipfile
from typing import List, Tuple, Optional


class FileCompressUtils:
    """
    Utilitário para compressão e extração de arquivos.

    Responsabilidades:
    - Zipar arquivos (individual ou lote por diretório)
    - Deszipar arquivos
    - Verificar integridade de zips
    - Limpeza segura em caso de falha
    - Validação de conflitos (zip já existe)

    Métodos estáticos, sem dependência de QGIS.
    """

    @staticmethod
    def is_valid_zip(zip_path: str) -> bool:
        """Verifica se o arquivo é um zip válido e não está corrompido."""
        if not zip_path or not os.path.isfile(zip_path):
            return False
        try:
            with zipfile.ZipFile(zip_path, mode="r") as zf:
                # Testa se consegue ler o diretório central
                bad = zf.testzip()
                return bad is None
        except (zipfile.BadZipFile, Exception):
            return False

    @staticmethod
    def zip_files(
        file_paths: List[str],
        zip_path: str,
        tool_key: str,
        remove_originals: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Cria um arquivo zip contendo os arquivos informados.

        Args:
            file_paths: lista de caminhos absolutos dos arquivos a zipar
            zip_path: caminho absoluto de destino do .zip
            tool_key: para logging
            remove_originals: se True, remove os arquivos originais após zipar

        Returns:
            (True, zip_path) em caso de sucesso
            (False, mensagem_erro) em caso de falha
        """
        from ..core.config.LogUtils import LogUtils
        logger = LogUtils(tool=tool_key, class_name="FileCompressUtils")

        if os.path.isfile(zip_path):
            logger.warning(f"ZIP: zip já existe: '{zip_path}'")
            return False, "Arquivo zip já existe"

        # Validar arquivos de origem
        valid_paths = []
        for fp in file_paths:
            if os.path.isfile(fp):
                valid_paths.append(fp)
            else:
                logger.warning(f"ZIP: arquivo não encontrado, ignorado: '{fp}'")

        if not valid_paths:
            logger.warning("ZIP: nenhum arquivo válido para zipar")
            return False, "Nenhum arquivo válido encontrado"

        # Criar diretório pai se necessário
        parent = os.path.dirname(zip_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        try:
            with zipfile.ZipFile(
                zip_path, mode="w", compression=zipfile.ZIP_DEFLATED,
            ) as zf:
                for file_path in valid_paths:
                    # Adiciona cada arquivo com seu basename (sem caminho completo)
                    basename = os.path.basename(file_path)
                    zf.write(file_path, arcname=basename)

            # Remover arquivos originais se solicitado
            if remove_originals:
                for file_path in valid_paths:
                    os.remove(file_path)

            logger.info(
                f"ZIP: criado '{os.path.basename(zip_path)}' "
                f"com {len(valid_paths)} arquivo(s)"
            )
            return True, zip_path

        except zipfile.BadZipFile as e:
            logger.error(f"ZIP: erro ao criar zip: {e}")
            # Limpeza em caso de falha
            if os.path.isfile(zip_path):
                try:
                    os.remove(zip_path)
                except OSError:
                    pass
            return False, f"Erro ao criar zip: {e}"
        except Exception as e:
            logger.error(f"ZIP: erro inesperado: {e}")
            return False, f"Erro inesperado: {e}"

    @staticmethod
    def zip_directory(
        dir_path: str,
        tool_key: str,
        remove_originals: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Cria UM zip com todos os arquivos do diretório.
        Nome do zip = nome da pasta. Ex: C:/fotos/ → C:/fotos/fotos.zip

        Args:
            dir_path: diretório alvo
            tool_key: para logging
            remove_originals: se True, remove os arquivos originais após zipar

        Returns:
            (True, zip_path) em caso de sucesso
            (False, mensagem_erro) em caso de falha
        """
        from ..core.config.LogUtils import LogUtils
        logger = LogUtils(tool=tool_key, class_name="FileCompressUtils")

        if not os.path.isdir(dir_path):
            logger.warning(f"ZIP_DIR: diretório inválido: '{dir_path}'")
            return False, "Diretório inválido"

        folder_name = os.path.basename(dir_path) or "pasta"
        zip_path = os.path.join(dir_path, f"{folder_name}.zip")

        # Coletar todos os arquivos do diretório (não recursivo)
        file_paths = [
            os.path.join(dir_path, f)
            for f in os.listdir(dir_path)
            if os.path.isfile(os.path.join(dir_path, f))
            and f != f"{folder_name}.zip"
        ]

        if not file_paths:
            logger.warning(f"ZIP_DIR: diretório vazio: '{dir_path}'")
            return False, "Diretório vazio"

        return FileCompressUtils.zip_files(
            file_paths=file_paths,
            zip_path=zip_path,
            tool_key=tool_key,
            remove_originals=remove_originals,
        )

    @staticmethod
    def unzip_file(
        zip_path: str,
        extract_dir: str,
        tool_key: str,
        remove_zip: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Extrai o conteúdo de um arquivo zip para um diretório.

        Args:
            zip_path: caminho absoluto do arquivo .zip
            extract_dir: diretório de destino da extração
            tool_key: para logging
            remove_zip: se True, remove o zip após extração bem-sucedida

        Returns:
            (True, mensagem_sucesso) em caso de sucesso
            (False, mensagem_erro) em caso de falha
        """
        from ..core.config.LogUtils import LogUtils
        logger = LogUtils(tool=tool_key, class_name="FileCompressUtils")

        if not os.path.isfile(zip_path):
            logger.warning(f"UNZIP: zip não encontrado: '{zip_path}'")
            return False, "Arquivo zip não encontrado"

        if not os.path.isdir(extract_dir):
            logger.warning(f"UNZIP: diretório inválido: '{extract_dir}'")
            return False, "Diretório de extração inválido"

        try:
            with zipfile.ZipFile(zip_path, mode="r") as zf:
                # Verificar se zip não está vazio
                names = zf.namelist()
                if not names:
                    logger.warning(f"UNZIP: zip vazio: '{zip_path}'")
                    return False, "Arquivo zip vazio"

                # Verificar path traversal (segurança)
                for name in names:
                    normalized = os.path.normpath(name)
                    if normalized.startswith("..") or normalized.startswith("/"):
                        logger.error(
                            f"UNZIP: path traversal detectado em '{zip_path}': '{name}'"
                        )
                        return False, "Path traversal detectado no zip"

                # Extrair todos para o diretório
                zf.extractall(path=extract_dir)

            extract_dir
            logger.info(
                f"UNZIP: extraídos {len(names)} arquivo(s) de "
                f"'{os.path.basename(zip_path)}'"
            )

            # Remover o zip se solicitado
            if remove_zip:
                os.remove(zip_path)
                logger.info(
                    f"UNZIP: zip removido: '{os.path.basename(zip_path)}'"
                )

            return True, f"Extraídos {len(names)} arquivo(s) com sucesso"

        except zipfile.BadZipFile:
            logger.error(f"UNZIP: zip corrompido: '{zip_path}'")
            return False, "Arquivo zip corrompido"
        except Exception as e:
            logger.error(f"UNZIP: erro ao extrair '{zip_path}': {e}")
            return False, f"Erro ao extrair zip: {e}"

    @staticmethod
    def unzip_directory(
        dir_path: str,
        tool_key: str,
        remove_zip: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Extrai o zip de uma pasta (nome da pasta + .zip) e remove o zip.

        Args:
            dir_path: diretório alvo onde está o zip
            tool_key: para logging
            remove_zip: se True, remove o zip após extração

        Returns:
            (True, mensagem) em caso de sucesso
            (False, mensagem_erro) em caso de falha
        """
        from ..core.config.LogUtils import LogUtils
        logger = LogUtils(tool=tool_key, class_name="FileCompressUtils")

        if not os.path.isdir(dir_path):
            logger.warning(f"UNZIP_DIR: diretório inválido: '{dir_path}'")
            return False, "Diretório inválido"

        folder_name = os.path.basename(dir_path) or "pasta"
        zip_path = os.path.join(dir_path, f"{folder_name}.zip")

        if not os.path.isfile(zip_path):
            logger.warning(f"UNZIP_DIR: zip não encontrado: '{zip_path}'")
            return False, "Arquivo zip não encontrado no diretório"

        return FileCompressUtils.unzip_file(
            zip_path=zip_path,
            extract_dir=dir_path,
            tool_key=tool_key,
            remove_zip=remove_zip,
        )