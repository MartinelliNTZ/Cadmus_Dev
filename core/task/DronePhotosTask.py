# -*- coding: utf-8 -*-

from qgis.core import QgsTask
from ...utils.mrk.PhotoMetadata import PhotoMetadata
from ..config.LogUtils import LogUtils
from ...utils.ToolKeys import ToolKey


class DronePhotosTask(QgsTask):
    """
    [LEGADO - MANTIDO PARA COMPATIBILIDADE]
    
    Task legado que usava PhotoMetadata.enrich() diretamente.
    Agora delega para PhotoMetadata.run_pipeline() com flags completas.
    Esta task será removida em versões futuras.
    """

    TOOL_KEY = ToolKey.DRONE_COORDINATES

    def __init__(self, description, points, base_folder, recursive=True, callback=None):
        super().__init__(description, QgsTask.CanCancel)
        self._logger = LogUtils(tool=self.TOOL_KEY, class_name=self.__class__.__name__)
        self._logger.info(f"Inicializando task: {description}")
        self.points = points
        self.base_folder = base_folder
        self.recursive = recursive
        self.result_points = None
        self.callback = callback

    def run(self):
        self._logger.info(
            f"ENTRANDO NO RUN DA TASK: cruzando fotos em {self.base_folder}"
        )
        try:
            # Delegates for PhotoMetadata.run_pipeline() (novo pipeline)
            self.result_points, _ = PhotoMetadata.run_pipeline(
                base_folder=self.base_folder,
                points=self.points,
                recursive=self.recursive,
                tool_key=self.TOOL_KEY,
                enable_mrk=True,
                enable_exif=True,
                enable_xmp=True,
                enable_custom_fields=True,
            )
            self.setProgress(100)
            self._logger.info(
                f"Cruzamento concluído ({len(self.result_points)} pontos)"
            )
            self.finished(True)
            return True
        except Exception as e:
            self._logger.exception(e)
            return False

    def finished(self, result):
        self._logger.info(f"FINALIZANDO TASK: {self.description()}")
        if result and self.callback:
            self.callback(self.result_points)
        elif not result:
            self._logger.warning("O cruzamento de fotos falhou ou foi cancelado")