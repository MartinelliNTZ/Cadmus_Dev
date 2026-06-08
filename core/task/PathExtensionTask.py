# -*- coding: utf-8 -*-
import os
import zipfile
from collections import defaultdict
from typing import List, Tuple
from .BaseTask import BaseTask
from ..config.LogUtils import LogUtils


class PathExtensionTask(BaseTask):
    """
    Task para remover/restaurar extensão de arquivos físicos no disco
    ou zipar/deszipar arquivos.

    Modo REMOVE:
      - path da feature = C:/fotos/foto.jpg
      - os.rename(foto.jpg, fotojpg) → remove o ponto
      - NewPath = C:/fotos/fotojpg

    Modo RESTORE:
      - path da feature = C:/fotos/foto.jpg (TEM ponto)
      - arquivo no disco = C:/fotos/fotojpg
      - os.rename(fotojpg, foto.jpg) → restaura
      - NewPath = C:/fotos/foto.jpg

    Modo ZIP (lote por pasta):
      - Agrupa TODAS as features da MESMA pasta
      - Cria UM zip por pasta: {dirname}/{nome_da_pasta}.zip
      - Ex: C:/fotos/ → C:/fotos/fotos.zip contendo todas as fotos
      - Remove os arquivos originais
      - NewPath = C:/fotos/fotos.zip (todas as fids da pasta)

    Modo UNZIP (lote por pasta):
      - Agrupa TODAS as features da MESMA pasta
      - Localiza {dirname}/{nome_da_pasta}.zip
      - Extrai todo o conteúdo do zip para o diretório
      - Remove o zip após extração
      - NewPath = path original da foto (agora existe de novo)

    A Task NÃO toca em QgsVectorLayer.
    O Step.on_success aplica as mudanças no atributo NewPath (main thread).
    """

    def __init__(self, features_data: List[Tuple[int, str]], mode: str, tool_key: str):
        """
        Args:
            features_data: lista de (fid, path_completo_do_arquivo)
            mode: "remove" | "restore" | "zip" | "unzip"
            tool_key: para logging
        """
        super().__init__(
            description="Processando arquivos físicos no disco",
            tool_key=tool_key,
        )
        self._features_data = features_data
        self._mode = mode

    def _run(self) -> bool:
        logger = LogUtils(
            tool=self.tool_key,
            class_name=self.__class__.__name__,
        )

        mode = self._mode
        total = len(self._features_data)

        if mode == "zip":
            changes, errors, skipped = self._run_zip_mode(logger)
        elif mode == "unzip":
            changes, errors, skipped = self._run_unzip_mode(logger)
        else:
            changes, errors, skipped = self._run_feature_by_feature(mode, logger)

        logger.info(
            f"PathExtension {mode}: {len(changes)} arquivos processados, "
            f"{errors} erros, {skipped} ignorados, {total} total"
        )

        self.result = {
            "changes": changes,
            "processed": len(changes),
            "errors": errors,
            "skipped": skipped,
            "total": total,
            "mode": mode,
        }
        return True

    # ---------------------------------------------------------------
    # Modo individual (remove / restore) — igual ao original
    # ---------------------------------------------------------------

    def _run_feature_by_feature(self, mode, logger):
        """Processa feature por feature (remove/restore)."""
        changes = {}
        errors = 0
        skipped = 0

        for fid, path_original in self._features_data:
            if self.isCanceled():
                logger.warning("Task cancelada pelo usuário")
                return {}, errors, skipped

            path = self._normalize_path(path_original)
            if path is None:
                errors += 1
                continue

            try:
                dirname = os.path.dirname(path)
                basename = os.path.basename(path)
                stem, ext = os.path.splitext(basename)

                if mode == "remove":
                    result = self._do_remove(path, dirname, basename, stem, ext, logger)
                else:  # restore
                    result = self._do_restore(path, dirname, basename, stem, ext, logger)

                if result is not None:
                    changes[fid] = result
                else:
                    skipped += 1

            except PermissionError:
                errors += 1
                logger.error(f"Permissão negada: '{path}'")
            except FileNotFoundError:
                errors += 1
                logger.error(f"Arquivo não encontrado: '{path}'")
            except Exception as e:
                errors += 1
                logger.error(f"Erro ao processar '{path}': {e}")

        return changes, errors, skipped

    # ---------------------------------------------------------------
    # Modo ZIP — agrupa por pasta, cria UM zip por pasta
    # ---------------------------------------------------------------

    def _run_zip_mode(self, logger):
        """
        Agrupa features por diretório e cria UM zip por pasta.
        O zip tem o nome da pasta. NewPath de todas fids aponta para o zip.
        """
        changes = {}
        errors = 0
        skipped = 0

        if self.isCanceled():
            logger.warning("Task cancelada")
            return changes, errors, skipped

        # 1. Agrupar paths válidos por diretório
        dir_groups = defaultdict(list)  # dirname → [(fid, path), ...]
        for fid, path_original in self._features_data:
            path = self._normalize_path(path_original)
            if path is None:
                errors += 1
                continue
            dirname = os.path.dirname(path)
            dir_groups[dirname].append((fid, path))

        # 2. Processar cada diretório
        for dirname, items in dir_groups.items():
            if self.isCanceled():
                logger.warning("Task cancelada pelo usuário")
                return changes, errors, skipped

            try:
                zip_result = self._do_zip_dir(dirname, items, logger)
                if zip_result is not None:
                    zip_path, fid_list = zip_result
                    for fid in fid_list:
                        changes[fid] = zip_path
                else:
                    skipped += len(items)
            except PermissionError:
                errors += len(items)
                logger.error(f"Permissão negada no diretório: '{dirname}'")
            except Exception as e:
                errors += len(items)
                logger.error(f"Erro ao zipar diretório '{dirname}': {e}")

        return changes, errors, skipped

    @staticmethod
    def _do_zip_dir(dirname, items, logger):
        """
        Cria UM zip com todas as fotos do diretório.
        Nome do zip = nome da pasta. Ex: C:/fotos/ → C:/fotos/fotos.zip

        Args:
            dirname: diretório alvo
            items: lista de (fid, path_completo)

        Returns:
            (zip_path, [fid1, fid2, ...]) ou None se falhar
        """
        if not os.path.isdir(dirname):
            logger.warning(f"ZIP: diretório inválido: '{dirname}'")
            return None

        folder_name = os.path.basename(dirname) or "pasta"
        zip_path = os.path.join(dirname, f"{folder_name}.zip")

        if os.path.isfile(zip_path):
            logger.warning(
                f"ZIP: zip já existe no diretório: '{zip_path}'"
            )
            return None

        # Coletar paths dos arquivos que realmente existem
        file_paths = []
        fids = []
        for fid, path in items:
            if os.path.isfile(path):
                file_paths.append(path)
                fids.append(fid)
            else:
                logger.warning(f"ZIP: arquivo não encontrado, ignorado: '{path}'")

        if not file_paths:
            logger.warning(f"ZIP: nenhum arquivo válido em '{dirname}'")
            return None

        try:
            with zipfile.ZipFile(
                zip_path, mode="w", compression=zipfile.ZIP_DEFLATED,
            ) as zf:
                for file_path in file_paths:
                    # Adiciona cada foto com seu basename (sem caminho completo)
                    basename = os.path.basename(file_path)
                    zf.write(file_path, arcname=basename)

            # Remover todos os arquivos originais
            for file_path in file_paths:
                os.remove(file_path)

            logger.info(
                f"ZIP: '{folder_name}.zip' criado com {len(file_paths)} arquivos "
                f"em '{dirname}'"
            )
            return zip_path, fids

        except zipfile.BadZipFile:
            logger.error(f"ZIP: erro ao criar zip em '{dirname}'")
            if os.path.isfile(zip_path):
                try:
                    os.remove(zip_path)
                except OSError:
                    pass
            return None

    # ---------------------------------------------------------------
    # Modo UNZIP — agrupa por pasta, extrai UM zip por pasta
    # ---------------------------------------------------------------

    def _run_unzip_mode(self, logger):
        """
        Agrupa features por diretório e extrai o zip da pasta.
        Remove o zip após extração. NewPath = path original das fotos.
        """
        changes = {}
        errors = 0
        skipped = 0

        if self.isCanceled():
            logger.warning("Task cancelada")
            return changes, errors, skipped

        # 1. Agrupar paths por diretório
        dir_groups = defaultdict(list)  # dirname → [(fid, path), ...]
        for fid, path_original in self._features_data:
            path = self._normalize_path(path_original)
            if path is None:
                errors += 1
                continue
            dirname = os.path.dirname(path)
            dir_groups[dirname].append((fid, path))

        # 2. Processar cada diretório
        for dirname, items in dir_groups.items():
            if self.isCanceled():
                logger.warning("Task cancelada pelo usuário")
                return changes, errors, skipped

            try:
                unzip_result = self._do_unzip_dir(dirname, items, logger)
                if unzip_result is not None:
                    # Mapeia cada fid para seu path original (agora extraído)
                    for fid, path in items:
                        changes[fid] = path
                else:
                    skipped += len(items)
            except PermissionError:
                errors += len(items)
                logger.error(f"Permissão negada no diretório: '{dirname}'")
            except Exception as e:
                errors += len(items)
                logger.error(f"Erro ao deszipar diretório '{dirname}': {e}")

        return changes, errors, skipped

    @staticmethod
    def _do_unzip_dir(dirname, items, logger):
        """
        Extrai o zip de uma pasta e remove o zip.

        Args:
            dirname: diretório alvo
            items: lista de (fid, path_completo)
                   (usado apenas para log, não para extração em si)

        Returns:
            True se sucesso, None se falha
        """
        if not os.path.isdir(dirname):
            logger.warning(f"UNZIP: diretório inválido: '{dirname}'")
            return None

        folder_name = os.path.basename(dirname) or "pasta"
        zip_path = os.path.join(dirname, f"{folder_name}.zip")

        if not os.path.isfile(zip_path):
            logger.warning(
                f"UNZIP: zip não encontrado: '{zip_path}'"
            )
            return None

        try:
            with zipfile.ZipFile(zip_path, mode="r") as zf:
                # Listar conteúdo
                names = zf.namelist()
                if not names:
                    logger.warning(f"UNZIP: zip vazio: '{zip_path}'")
                    return None

                # Extrair todos para o diretório
                zf.extractall(path=dirname)

                logger.info(
                    f"UNZIP: extraídos {len(names)} arquivo(s) de "
                    f"'{os.path.basename(zip_path)}'"
                )

            # Remover o zip
            os.remove(zip_path)
            logger.info(
                f"UNZIP: zip removido: '{os.path.basename(zip_path)}'"
            )

            return True

        except zipfile.BadZipFile:
            logger.error(f"UNZIP: zip corrompido: '{zip_path}'")
            return None
        except Exception as e:
            logger.error(f"UNZIP: erro ao extrair '{zip_path}': {e}")
            return None

    # ---------------------------------------------------------------
    # Utilitários
    # ---------------------------------------------------------------

    @staticmethod
    def _normalize_path(path_original):
        """Valida e normaliza um path."""
        if not path_original or not isinstance(path_original, str):
            return None
        path = str(path_original).strip()
        if not path:
            return None
        return path

    # ---------------------------------------------------------------
    # Modos individuais (preservados)
    # ---------------------------------------------------------------

    @staticmethod
    def _do_remove(path, dirname, basename, stem, ext, logger):
        """Remove o ponto da extensão: foto.jpg → fotojpg"""
        if not os.path.isfile(path):
            logger.warning(f"REMOVE: arquivo não encontrado: '{path}'")
            return None

        ext_sem_ponto = ext.replace(".", "")
        novo_basename = stem + ext_sem_ponto
        novo_path = os.path.join(dirname, novo_basename)

        os.rename(path, novo_path)
        logger.info(f"REMOVE: '{basename}' → '{novo_basename}'")
        return novo_path

    @staticmethod
    def _do_restore(path, dirname, basename, stem, ext, logger):
        """Restaura o ponto na extensão: fotojpg → foto.jpg"""
        if os.path.isfile(path):
            logger.info(f"RESTORE: '{basename}' já existe no disco, mantendo")
            return path

        ext_sem_ponto = ext.replace(".", "")
        flat_name = stem + ext_sem_ponto

        target_dir = dirname if dirname else os.getcwd()
        if not os.path.isdir(target_dir):
            logger.warning(f"RESTORE: diretório inválido: '{target_dir}'")
            return None

        arquivo_encontrado = None
        for f_name in os.listdir(target_dir):
            f_path = os.path.join(target_dir, f_name)
            if not os.path.isfile(f_path):
                continue
            if f_name == flat_name:
                arquivo_encontrado = f_name
                break

        if arquivo_encontrado:
            src = os.path.join(target_dir, arquivo_encontrado)
            os.rename(src, path)
            logger.info(f"RESTORE: '{arquivo_encontrado}' → '{basename}'")
            return path
        else:
            logger.warning(
                f"RESTORE: nenhum arquivo '{flat_name}' encontrado "
                f"em '{target_dir}'"
            )
            return None