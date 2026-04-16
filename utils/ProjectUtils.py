# -*- coding: utf-8 -*-
import os
import shutil
from datetime import datetime
from pathlib import Path
from qgis.PyQt.QtCore import QCoreApplication, QProcess
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsMapLayer,
    QgsVectorLayer,
)

from ..core.config.LogUtils import LogUtils
from typing import Union, Optional


class ProjectUtils:
    @staticmethod
    def get_active_vector_layer(layer, logger=None, require_editable=False):
        """Valida camada vetorial ativa.
        Recebe: layer, logger, require_editable (bool).
        Retorna: QgsVectorLayer ou None.
        NÃ£o acessa iface nem exibe mensagens.
        """

        if logger:
            logger.debug(
                f"Validando camada vetorial ativa. Require editable: {require_editable}"
            )
        if not layer or not isinstance(layer, QgsVectorLayer):
            if logger:
                logger.debug("Camada ativa invÃ¡lida ou nÃ£o Ã© vetorial")
            return None
        if require_editable and not ProjectUtils.ensure_editable(layer, logger):
            return None
        return layer

    @staticmethod
    def ensure_editable(layer, logger=None):
        """Verifica se a camada estÃ¡ em modo ediÃ§Ã£o.
        Recebe: layer (QgsVectorLayer), logger.
        Retorna: bool.
        NÃ£o acessa iface nem exibe mensagens.
        """
        if logger:
            logger.debug(
                f"Verificando se camada estÃ¡ em ediÃ§Ã£o: {layer.name()}. EditÃ¡vel: {layer.isEditable()}"
            )
        return layer.isEditable()

    @staticmethod
    def get_project_instance() -> QgsProject:
        """Retorna a instÃ¢ncia do projeto QGIS aberto."""
        return QgsProject.instance()

    @staticmethod
    def create_project_instance() -> QgsProject:
        """Cria uma nova instância de projeto QGIS."""
        return QgsProject()

    @staticmethod
    def is_project_empty(project: QgsProject) -> bool:
        return len(project.mapLayers()) == 0

    @staticmethod
    def get_project_file_name(project: QgsProject) -> str:
        return project.fileName() or ""

    @staticmethod
    def set_project_home_path(project: QgsProject, folder_path: str):
        if hasattr(project, "setPresetHomePath"):
            project.setPresetHomePath(folder_path)

    @staticmethod
    def set_project_file_name(project: QgsProject, file_path: str):
        project.setFileName(file_path)

    @staticmethod
    def write_project(project: QgsProject, file_path: str) -> bool:
        return bool(project.write(file_path))

    @staticmethod
    def set_project_crs(project: QgsProject, crs):
        project.setCrs(crs)

    @staticmethod
    def resolve_valid_crs(
        authid: str,
        fallback_authid: str = "EPSG:4326",
        tool_key: str = "untraceable",
    ) -> QgsCoordinateReferenceSystem:
        """Resolve CRS válido a partir de authid com fallback seguro."""
        logger = LogUtils(tool=tool_key, class_name="ProjectUtils")
        crs = QgsCoordinateReferenceSystem(authid or fallback_authid)
        if crs.isValid():
            return crs

        logger.warning(
            f"SRC invalido: '{authid}'. Usando fallback {fallback_authid}"
        )
        return QgsCoordinateReferenceSystem(fallback_authid)

    @staticmethod
    def project_layers(project: Optional[QgsProject] = None) -> dict:
        resolved_project = project or QgsProject.instance()
        return resolved_project.mapLayers()

    @staticmethod
    def project_layer_names(project: Optional[QgsProject] = None) -> list:
        return [layer.name() for layer in ProjectUtils.project_layers(project).values()]

    @staticmethod
    def get_qgis_executable_path() -> str:
        executable = QCoreApplication.applicationFilePath()
        if executable and os.path.exists(executable):
            return executable
        return ""

    @staticmethod
    def open_project_in_new_window(
        project_file: str, extent: Optional[tuple] = None
    ) -> bool:
        executable = ProjectUtils.get_qgis_executable_path()
        if not executable:
            return False

        args = []
        if extent is not None and len(extent) == 4:
            args.extend(["--extent", ",".join(str(v) for v in extent)])
        args.append(str(project_file))

        started = QProcess.startDetached(executable, args)
        if isinstance(started, tuple):
            started = started[0]
        return bool(started)

    @staticmethod
    def is_project_saved(project: QgsProject) -> bool:
        return bool(project.fileName())

    @staticmethod
    def get_project_dir(project: QgsProject) -> str:
        """
        Retorna diretÃ³rio do projeto salvo ou homePath como fallback.
        """
        if project.fileName():
            return str(Path(project.fileName()).parent)
        return project.homePath() or os.path.expanduser("~")

    @staticmethod
    def set_clipboard_text(text: str) -> bool:
        """Define o texto do clipboard via Qt. Retorna True se bem-sucedido."""
        try:
            from qgis.PyQt.QtGui import QGuiApplication

            QGuiApplication.clipboard().setText("" if text is None else str(text))
            return True
        except Exception as e:
            logger = LogUtils(tool="project_utils", class_name="ProjectUtils")
            logger.error(f"Erro ao copiar para clipboard: {e}")
            return False

    @staticmethod
    def create_project_backup(project: QgsProject) -> str:
        """
        Cria backup do .qgz em subpasta 'backup'.
        Retorna caminho do arquivo criado.
        LanÃ§a exceÃ§Ã£o se projeto nÃ£o estiver salvo.
        """
        project_file = project.fileName()
        if not project_file:
            raise RuntimeError("Projeto nÃ£o estÃ¡ salvo. Backup impossÃ­vel.")

        project_path = Path(project_file)
        project_dir = project_path.parent

        backup_folder = project_dir / "backup"
        backup_folder.mkdir(exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        base_name = project_path.stem[:100]
        backup_name = f"{base_name}_{ts}{project_path.suffix}"

        backup_path = backup_folder / backup_name
        shutil.copy2(project_file, backup_path)

        return str(backup_path)

    @staticmethod
    def compute_size(obj: Optional[Union[str, Path, QgsMapLayer]]) -> int:
        if obj is None:
            return 0

        # QgsMapLayer
        if isinstance(obj, QgsMapLayer):
            src = obj.source() or ""

            # memory layer â†’ estimar
            if src.startswith("memory:"):
                try:
                    feat_count = obj.featureCount()
                    # estimativa simples: 200 bytes por feature + geometria
                    return feat_count * 200
                except Exception as e:
                    logger = LogUtils(tool="project_utils", class_name="ProjectUtils")
                    logger.error(f"Erro estimando tamanho de memÃ³ria: {e}")
                    return 0

            # arquivo real
            if "|" in src:
                src = src.split("|", 1)[0]

            obj = src

        p = Path(str(obj))
        if not p.exists():
            return 0

        if p.is_dir():
            total = 0
            for f in p.rglob("*"):
                if f.is_file():
                    try:
                        total += f.stat().st_size
                    except Exception as e:
                        logger = LogUtils(
                            tool="project_utils", class_name="ProjectUtils"
                        )
                        logger.error(f"Erro ao ler arquivo durante compute_size: {e}")
                        return total

        if p.suffix.lower() == ".shp":
            total = 0
            for ext in (".shp", ".dbf", ".shx", ".prj", ".cpg", ".qix", ".sbn", ".sbx"):
                f = p.with_suffix(ext)
                if f.exists():
                    total += f.stat().st_size
            return total

        return p.stat().st_size

    @staticmethod
    def is_layer_in_project(layer: QgsMapLayer) -> bool:
        """
        Verifica se a camada informada estÃ¡ presente no projeto QGIS aberto.

        :param layer: QgsMapLayer selecionada (ex: cmb_layers.currentLayer())
        :return: True se estiver no projeto, False caso contrÃ¡rio
        """
        try:
            if layer is None:
                return False

            project = QgsProject.instance()
            return layer.id() in project.mapLayers()

        except Exception as e:
            logger = LogUtils(tool="project_utils", class_name="ProjectUtils")
            logger.error(f"Erro ao verificar camada no projeto: {e}")
            return False

    @staticmethod
    def remove_layer_from_project(layer: QgsMapLayer) -> bool:
        """
        Remove a camada informada do projeto QGIS aberto.

        :param layer: QgsMapLayer a ser removida
        :return: True se removida com sucesso, False em erro
        """
        try:
            if layer is None:
                return False

            project = QgsProject.instance()

            if layer.id() not in project.mapLayers():
                return False

            project.removeMapLayer(layer.id())
            return True

        except Exception as e:
            logger = LogUtils(tool="project_utils", class_name="ProjectUtils")
            logger.error(f"Erro ao remover camada do projeto: {e}")
            return False

    @staticmethod
    def is_file_in_project(file_path: str) -> bool:
        """
        Verifica se existe uma camada no projeto cujo source corresponde ao arquivo informado.
        """
        try:
            if not file_path:
                return False

            target = Path(file_path).resolve()

            for layer in QgsProject.instance().mapLayers().values():
                source = layer.source()

                if not source:
                    continue

                # Normaliza o path da layer (remove |layername= etc)
                layer_path = source.split("|")[0]

                if Path(layer_path).resolve() == target:
                    return True

            return False

        except Exception as e:
            logger = LogUtils(tool="project_utils", class_name="ProjectUtils")
            logger.error(f"Erro ao verificar arquivo no projeto: {e}")
            return False

    @staticmethod
    def remove_file_from_project(file_path: str) -> bool:
        """
        Remove do projeto a camada cujo source corresponde ao arquivo informado.
        """
        try:
            if not file_path:
                return False

            target = Path(file_path).resolve()
            project = QgsProject.instance()

            for layer_id, layer in project.mapLayers().items():
                source = layer.source()
                if not source:
                    continue

                layer_path = source.split("|")[0]

                if Path(layer_path).resolve() == target:
                    project.removeMapLayer(layer_id)
                    return True

            return False

        except Exception as e:
            logger = LogUtils(tool="project_utils", class_name="ProjectUtils")
            logger.error(f"Erro ao remover arquivo do projeto: {e}")
            return False

    # ------------------------------------------------------------------
    # Helpers adicionais para LoadFolderLayers refactor
    # ------------------------------------------------------------------
    @staticmethod
    def normalize_layer_source(src: str) -> str:
        """Normaliza a source de uma layer (remove parÃ¢metros e resolve path)."""
        if not src:
            return ""
        if "|" in src:
            src = src.split("|", 1)[0]
        try:
            return str(Path(src).resolve())
        except Exception as e:
            logger = LogUtils(tool="project_utils", class_name="ProjectUtils")
            logger.error(f"Erro normalizando source de layer: {e}")
            return os.path.normpath(src)

    @staticmethod
    def ensure_group(rel_path: str):
        """Garante a existÃªncia de um grupo aninhado a partir de um caminho relativo.

        Retorna o QgsLayerTreeGroup criado/encontrado.
        """
        project = QgsProject.instance()
        root = project.layerTreeRoot()

        parts = rel_path.split(os.sep)
        current = root

        for part in parts:
            found = current.findGroup(part)
            if not found:
                found = current.addGroup(part)
            current = found

        return current

    @staticmethod
    def add_layer(
        layer, add_to_root: bool = True, project: Optional[QgsProject] = None
    ):
        """Adiciona uma layer ao projeto; retorna a layer adicionada ou None."""
        try:
            resolved_project = project or QgsProject.instance()
            if add_to_root:
                resolved_project.addMapLayer(layer, True)
            else:
                resolved_project.addMapLayer(layer, False)
            return layer
        except Exception as e:
            logger = LogUtils(tool="project_utils", class_name="ProjectUtils")
            logger.error(f"Erro ao adicionar camada ao projeto: {e}")
            return None

    @staticmethod
    def add_layer_if_missing(layer):
        """Adiciona a layer ao projeto apenas se ainda nao estiver registrada."""
        try:
            if layer is None:
                return None

            project = QgsProject.instance()
            if layer.id() not in project.mapLayers():
                project.addMapLayer(layer)
            return layer
        except Exception as e:
            logger = LogUtils(tool="project_utils", class_name="ProjectUtils")
            logger.error(f"Erro ao adicionar camada se ausente: {e}")
            return None

    @staticmethod
    def add_layer_to_group(layer, group):
        """Adiciona uma camada jÃ¡ registrada no projeto dentro de um grupo (QgsLayerTreeGroup)."""
        try:
            project = QgsProject.instance()
            # garante que layer estÃ¡ no projeto sem inserir na root
            project.addMapLayer(layer, False)
            group.insertLayer(0, layer)
            return layer
        except Exception as e:
            logger = LogUtils(tool="project_utils", class_name="ProjectUtils")
            logger.error(f"Erro ao inserir layer no grupo: {e}")
            return None

    @staticmethod
    def center_canvas_on_file_extent(
        iface,
        file_path: str,
        project: Optional[QgsProject] = None,
        layer_name: str = "",
        tool_key: str = "untraceable",
    ) -> bool:
        """Centraliza o map canvas na extensao da camada vinculada ao arquivo informado."""
        logger = LogUtils(tool=tool_key, class_name="ProjectUtils")
        try:
            if iface is None:
                logger.warning("Iface ausente ao tentar centralizar canvas por arquivo")
                return False

            if not file_path:
                logger.warning("file_path vazio ao tentar centralizar canvas")
                return False

            project = project or QgsProject.instance()
            target = ProjectUtils.normalize_layer_source(file_path)

            target_layer = None
            for layer in project.mapLayers().values():
                source = ProjectUtils.normalize_layer_source(layer.source())
                if source != target:
                    continue
                if layer_name and layer.name() != layer_name:
                    continue
                target_layer = layer
                break

            if target_layer is None:
                logger.warning(
                    f"Nenhuma camada correspondente ao arquivo foi encontrada: {file_path}"
                )
                return False

            extent = target_layer.extent()
            if extent is None or extent.isEmpty():
                logger.warning(
                    f"Extent vazio para camada associada ao arquivo: {file_path}"
                )
                return False

            canvas = iface.mapCanvas() if hasattr(iface, "mapCanvas") else None
            if canvas is None:
                logger.warning("Map canvas indisponivel para centralizacao")
                return False

            canvas.setExtent(extent)
            canvas.refresh()
            logger.debug(
                f"Canvas centralizado no extent do arquivo: {file_path} "
                f"({extent.xMinimum()}, {extent.yMinimum()}, "
                f"{extent.xMaximum()}, {extent.yMaximum()})"
            )
            return True

        except Exception as e:
            logger.error(f"Erro ao centralizar canvas na extensao do arquivo: {e}")
            return False

