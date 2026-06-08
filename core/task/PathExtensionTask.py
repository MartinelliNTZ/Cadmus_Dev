# -*- coding: utf-8 -*-
import os
from typing import List, Tuple
from .BaseTask import BaseTask
from ..config.LogUtils import LogUtils


class PathExtensionTask(BaseTask):
    """
    Task para remover ou restaurar extensão de arquivos físicos no disco.

    Modo REMOVE:
      - path da feature = C:/fotos/foto.jpg (TEM o ponto)
      - arquivo no disco = C:/fotos/foto.jpg
      - os.rename(foto.jpg, fotojpg) → remove o ponto da extensão
      - retorna novo caminho para salvar em NewPath

    Modo RESTORE:
      - path da feature = C:/fotos/foto.jpg (TEM o ponto, EX: atributo Path original)
      - arquivo no disco = C:/fotos/fotojpg  (foi renomeado pelo REMOVE anterior)
      - calcular flat_name = fotojpg
      - procurar no diretório por arquivo com esse nome flat
      - os.rename(fotojpg, foto.jpg) → restaura o ponto
      - retorna o path original (que agora é o correto)

    A Task NÃO toca em QgsVectorLayer.
    O Step.on_success aplica as mudanças no atributo NewPath (main thread).
    """

    def __init__(self, features_data: List[Tuple[int, str]], mode: str, tool_key: str):
        """
        Args:
            features_data: lista de (fid, path_completo_do_arquivo)
                          SEMPRE terá o ponto (ex: C:/fotos/foto.jpg)
                          mesmo que o arquivo no disco já esteja sem extensão
            mode: "remove" | "restore"
            tool_key: para logging
        """
        super().__init__(
            description="Renomeando arquivos físicos no disco",
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
        changes = {}  # {fid: novo_path_apos_rename}
        total = len(self._features_data)
        errors = 0

        for fid, path_original in self._features_data:
            if self.isCanceled():
                logger.warning("Task cancelada pelo usuário")
                return False

            if not path_original or not isinstance(path_original, str):
                errors += 1
                continue

            path = str(path_original).strip()
            if not path:
                errors += 1
                continue

            try:
                dirname = os.path.dirname(path)
                basename = os.path.basename(path)
                stem, ext = os.path.splitext(basename)

                # --- MODO REMOVE ---
                if mode == "remove":
                    # foto.jpg → fotojpg
                    if not os.path.isfile(path):
                        logger.warning(f"REMOVE: arquivo não encontrado: '{path}'")
                        continue

                    ext_sem_ponto = ext.replace(".", "")
                    novo_basename = stem + ext_sem_ponto
                    novo_path = os.path.join(dirname, novo_basename)

                    os.rename(path, novo_path)
                    logger.info(f"REMOVE: '{basename}' → '{novo_basename}'")
                    changes[fid] = novo_path

                # --- MODO RESTORE ---
                elif mode == "restore":
                    # Foto.jpg → o arquivo no disco pode ser "Fotojpg"
                    # Precisamos achar o arquivo no diretório que corresponde
                    # ao flat_name (stem + ext sem ponto)

                    # se o arquivo já existe COM o ponto, ótimo, mantém
                    if os.path.isfile(path):
                        logger.info(f"RESTORE: '{basename}' já existe no disco, mantendo")
                        changes[fid] = path
                        continue

                    # O arquivo COM ponto NÃO existe no disco
                    # Calcular flat_name: foto.jpg → fotojpg
                    ext_sem_ponto = ext.replace(".", "")
                    flat_name = stem + ext_sem_ponto

                    target_dir = dirname if dirname else os.getcwd()
                    if not os.path.isdir(target_dir):
                        logger.warning(f"RESTORE: diretório inválido: '{target_dir}'")
                        continue

                    # Procurar no diretório por arquivo com nome = flat_name
                    arquivo_encontrado = None
                    for f_name in os.listdir(target_dir):
                        f_path = os.path.join(target_dir, f_name)
                        if not os.path.isfile(f_path):
                            continue
                        if f_name == flat_name:
                            arquivo_encontrado = f_name
                            break

                    if arquivo_encontrado:
                        os.rename(
                            os.path.join(target_dir, arquivo_encontrado),
                            path
                        )
                        logger.info(
                            f"RESTORE: '{arquivo_encontrado}' → '{basename}'"
                        )
                        changes[fid] = path
                    else:
                        logger.warning(
                            f"RESTORE: nenhum arquivo '{flat_name}' encontrado "
                            f"em '{target_dir}'"
                        )

            except PermissionError:
                errors += 1
                logger.error(f"Permissão negada ao renomear: '{path}'")
            except FileNotFoundError:
                errors += 1
                logger.error(f"Arquivo não encontrado ao renomear: '{path}'")
            except Exception as e:
                errors += 1
                logger.error(f"Erro ao renomear '{path}': {e}")

        logger.info(
            f"PathExtension {mode}: {len(changes)} arquivos renomeados, "
            f"{errors} erros, {total} total"
        )

        self.result = {
            "changes": changes,
            "processed": len(changes),
            "errors": errors,
            "total": total,
            "mode": mode,
        }
        return True