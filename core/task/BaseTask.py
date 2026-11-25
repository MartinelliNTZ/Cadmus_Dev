from qgis.core import QgsTask, QgsMessageLog, Qgis
from qgis.PyQt.QtCore import pyqtSignal
from ..config.LogUtils import LogUtils


class BaseTask(QgsTask):
    """
    Classe base para todas as tasks do plugin.

    Responsabilidades:
    - Executar processamento pesado fora da UI
    - Capturar exceções de forma segura
    - Permitir cancelamento
    - Retornar resultado para o controller
    """

    stage_progress = pyqtSignal(object)

    def __init__(self, description: str, tool_key="untraceable"):
        super().__init__(description, QgsTask.CanCancel)
        self.tool_key = tool_key
        self.exception = None
        self.result = None
        self.logger = LogUtils(tool=self.tool_key, class_name=self.__class__.__name__)

        self.logger.debug("Task initialized")

        # callbacks
        self.on_success = None
        self.on_error = None

    def emit_stage_progress(self, stage: str, current: int, total: int, **data):
        """Emite progresso de etapa sem acessar objetos QGIS na thread worker."""
        payload = {
            "stage": str(stage),
            "current": max(0, int(current)),
            "total": max(0, int(total)),
        }
        payload.update(data)
        try:
            self.stage_progress.emit(payload)
        except RuntimeError:
            # A task pode ser destruída enquanto uma thread de download termina.
            self.logger.debug("Sinal de progresso descartado após destruição da task")

    def run(self) -> bool:
        self.logger.info("Task started")
        try:
            return self._run()
        except Exception as e:
            self.exception = e
            self.logger.critical(f"Unhandled exception in task: {e}")
            return False

    def finished(self, success: bool):
        if success:
            self.logger.info("Task finished successfully")
            if callable(self.on_success):
                self.on_success(self.result)
            return

        # erro
        self.logger.critical(f"Task finished with error: {self.exception}")
        if callable(self.on_error):
            self.on_error(self.exception)
        else:
            QgsMessageLog.logMessage(str(self.exception), self.tool_key, Qgis.Critical)

    def _run(self) -> bool:
        raise NotImplementedError
