# -*- coding: utf-8 -*-
import os
from collections import defaultdict
from typing import List, Tuple

from .BaseTask import BaseTask
from ..config.LogUtils import LogUtils
from ..utils.ExplorerUtils import ExplorerUtils
from ..utils.FileCompressUtils import FileCompressUtils


class PathExtensionTask(BaseTask):
    """
    Task para remover/restaurar extensão de arquivos físicos no disco
    ou zipar/deszipar arquivos.

    Modo REMOVE:
      - path da feature = C:/fotos/foto.jpg
      - ExplorerUtils.remove_extension_dot() → remove o ponto
      - NewPath = C:/fotos/fotojpg

    Modo RESTORE:
      - path da feature = C:/fotos/foto.jpg (TEM ponto)
      - arquivo no disco = C:/fotos/fotojpg
      - ExplorerUtils.restore_extension_dot() → restaura
      - NewPath = C:/fotos/foto.jpg

    Modo ZIP (lote por pasta):
      - Agrupa TODAS as features da MESMA pasta
      - FileCompressUtils.zip_directory() → Cria UM zip por pasta
      - Ex: C:/fotos/ → C:/fotos/fotos.zip contendo todas as fotos
      - Remove os arquivos originais
      - NewPath = C:/fotos/fotos.zip (todas as fids da pasta)

    Modo UNZIP (lote por pasta):
      - Agrupa TODAS as features da MESMA pasta
      - FileCompressUtils.unzip_directory() → Extrai o zip
      - Remove o zip após extração
      - NewPath = path original da foto (agora existe de novo)

    A Task NÃO toca em QgsVectorLayer.
    O Step.on_success aplica as mudanças no atributo NewPath (main thread).
    A Task DELEGA operações de arquivo para ExplorerUtils e FileCompressUtils.
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
    # Modo individual (remove / restore) — delegado ao ExplorerUtils
    # ---------------------------------------------------------------

    def _run_feature_by_feature(self, mode, logger):
        """Processa feature por feature (remove/restore) via ExplorerUtils."""
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
                if mode == "remove":
                    result = ExplorerUtils.remove_extension_dot(
                        file_path=path, tool_key=self.tool_key,
                    )
                else:  # restore
                    result = ExplorerUtils.restore_extension_dot(
                        file_path=path, tool_key=self.tool_key,
                    )

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
    # Modo ZIP — agrupa por pasta, delega ao FileCompressUtils
    # ---------------------------------------------------------------

    def _run_zip_mode(self, logger):
        """
        Agrupa features por diretório e cria UM zip por pasta.
        Delega a compressão para FileCompressUtils.zip_directory().
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
                # Para zip, não podemos usar zip_directory diretamente
                # porque só queremos zipar os arquivos das features,
                # não todos do diretório.
                # Usamos zip_files com paths específicos.
                file_paths = [path for _, path in items]
                folder_name = os.path.basename(dirname) or "pasta"
                zip_path = os.path.join(dirname, f"{folder_name}.zip")

                success, result = FileCompressUtils.zip_files(
                    file_paths=file_paths,
                    zip_path=zip_path,
                    tool_key=self.tool_key,
                    remove_originals=True,
                )

                if success:
                    zip_path_result = result  # result é o caminho do zip
                    fids_in_dir = [fid for fid, _ in items]
                    for fid in fids_in_dir:
                        changes[fid] = zip_path_result
                else:
                    # result é a mensagem de erro
                    logger.warning(f"ZIP: falha em '{dirname}': {result}")
                    skipped += len(items)

            except PermissionError:
                errors += len(items)
                logger.error(f"Permissão negada no diretório: '{dirname}'")
            except Exception as e:
                errors += len(items)
                logger.error(f"Erro ao zipar diretório '{dirname}': {e}")

        return changes, errors, skipped

    # ---------------------------------------------------------------
    # Modo UNZIP — agrupa por pasta, delega ao FileCompressUtils
    # ---------------------------------------------------------------

    def _run_unzip_mode(self, logger):
        """
        Agrupa features por diretório e extrai o zip da pasta.
        Delega a extração para FileCompressUtils.unzip_directory().
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
                success, result = FileCompressUtils.unzip_directory(
                    dir_path=dirname,
                    tool_key=self.tool_key,
                    remove_zip=True,
                )

                if success:
                    # Mapeia cada fid para seu path original (agora extraído)
                    for fid, path in items:
                        changes[fid] = path
                else:
                    logger.warning(f"UNZIP: falha em '{dirname}': {result}")
                    skipped += len(items)

            except PermissionError:
                errors += len(items)
                logger.error(f"Permissão negada no diretório: '{dirname}'")
            except Exception as e:
                errors += len(items)
                logger.error(f"Erro ao deszipar diretório '{dirname}': {e}")

        return changes, errors, skipped

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