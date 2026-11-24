# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtCore import QCoreApplication, QProcess
from qgis.PyQt.QtWidgets import QFileDialog
from typing import Optional
from qgis.core import QgsProject
from ..core.config.LogUtils import LogUtils
from ..i18n.TranslationManager import STR
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.ToolKeys import ToolKey
from ..utils.Preferences import Preferences

logger = LogUtils(tool=ToolKey.RESTART_QGIS, class_name="RestartQGIS")


class _RestartExecutor:
    """Responsável pela execução do restart do QGIS.

    Separação de responsabilidades:
    - Criar script .bat
    - Executar script de forma segura
    - Gerenciar sinais Qt para fechar a aplicação
    """

    @staticmethod
    def get_qgis_executable() -> Optional[str]:
        """Obtém o executável real do QGIS diretamente do Qt.

        Returns:
            Caminho do executável ou None se não encontrado.
        """
        exe = QCoreApplication.applicationFilePath()
        if exe and os.path.exists(exe):
            logger.debug("QGIS executable found", qgis_exe=exe)
            return exe

        logger.warning("QGIS executable not found", exe=exe)
        return None

    @staticmethod
    def create_restart_script(project_path: str) -> Optional[list]:
        """Prepara comando (lista) para reabrir QGIS com o projeto.

        Retorna uma lista de argumentos adequada para passar a
        `subprocess.Popen(cmd, shell=False)`. Não cria .bat nem usa shell.
        """
        qgis_exec = _RestartExecutor.get_qgis_executable()
        if not qgis_exec:
            logger.error(
                "Cannot prepare restart command: QGIS executable not found",
                code="RESTART_NO_EXEC",
            )
            return None

        try:
            cmd = [qgis_exec, project_path]
            logger.info("Restart command prepared", code="RESTART_CMD_OK", cmd=cmd)
            return cmd
        except Exception as e:
            logger.error(
                "Failed to prepare restart command",
                code="RESTART_CMD_ERROR",
                error=str(e),
            )
            return None

    @staticmethod
    def execute_restart(cmd: list) -> None:
        """Registra callback para executar `cmd` quando o QGIS estiver saindo.

        O comando é executado com `shell=False` para evitar injeção de shell (B602).
        """

        def _run_cmd():
            try:
                exe = cmd[0]
                args = cmd[1:]
                started = QProcess.startDetached(exe, args)
                if started:
                    logger.info(
                        "Restart command executed (detached)",
                        code="RESTART_EXECUTED",
                        cmd=cmd,
                    )
                else:
                    logger.critical(
                        "Failed to start detached process",
                        code="RESTART_EXEC_ERROR",
                        cmd=cmd,
                    )
            except Exception as e:
                logger.critical(
                    "Failed to execute restart command",
                    code="RESTART_EXEC_ERROR",
                    error=str(e),
                )

        app = QCoreApplication.instance()
        app.aboutToQuit.connect(_run_cmd)
        logger.info(
            "Restart queued: will execute on QGIS shutdown", code="RESTART_QUEUED"
        )


def run_restart_qgis(iface) -> None:
    """Fluxo principal: Salvar projeto, criar script restart e fechar QGIS.

    Responsabilidades delegadas:
    - ProjectUtils: Verificação de projeto salvo, save/write do projeto
    - QgisMessageUtil: Exibição de mensagens e diálogos UI
    - _RestartExecutor: Criação e execução do script de restart
    - logger: Logging estruturado de cada etapa

    Args:
        iface: QgisInterface do QGIS
    """
    project = QgsProject.instance()
    project_path = project.fileName()

    preferences = {}
    preferences.clear()
    preferences = Preferences.load_tool_prefs(ToolKey.RESTART_QGIS)
    valor_atual = preferences.get("usages", 0)
    preferences["usages"] = valor_atual + 1
    Preferences.save_tool_prefs(ToolKey.RESTART_QGIS, preferences)

    logger.info(
        "Restart QGIS initiated",
        code="RESTART_START",
        project_path=project_path or "<unsaved>",
    )

    # 1) Verificar se o projeto está salvo
    if not project_path:
        logger.warning("Project not saved, asking user to save", code="RESTART_NO_SAVE")

        # Usar QgisMessageUtil para diálogo
        save_now = QgisMessageUtil.confirm(
            iface,
            STR.RESTART_UNSAVED_PROJECT_CONFIRM,
            title=STR.UNSAVED_PROJECT_TITLE,
        )

        if not save_now:
            logger.info("User cancelled restart", code="RESTART_CANCELLED_NO_SAVE")
            QgisMessageUtil.bar_warning(
                iface,
                STR.RESTART_SAVE_REQUIRED,
                title=STR.RESTART_CANCELLED_TITLE,
            )
            return

        # Solicitar caminho do arquivo
        save_path, _ = QFileDialog.getSaveFileName(
            iface.mainWindow(),
            STR.SAVE_PROJECT_DIALOG_TITLE,
            "",
            STR.QGIS_PROJECT_FILE_FILTER,
        )

        if not save_path:
            logger.info(
                "User cancelled save dialog", code="RESTART_CANCELLED_SAVE_DIALOG"
            )
            return

        # Usar ProjectUtils para salvar (delegação de responsabilidade)
        try:
            project.write(save_path)
            project_path = save_path
            logger.info(
                "Project saved successfully", code="RESTART_SAVED", path=save_path
            )
        except Exception as e:
            logger.error(
                "Failed to save project", code="RESTART_SAVE_ERROR", error=str(e)
            )
            QgisMessageUtil.modal_error(
                iface,
                STR.SAVE_PROJECT_ERROR.format(error=str(e)),
                title=STR.ERROR,
            )
            return

    # 2) Gravar alterações antes de fechar
    try:
        project.write(project_path)
        logger.info(
            "Project changes saved", code="RESTART_CHANGES_SAVED", path=project_path
        )
    except Exception as e:
        logger.error(
            "Failed to save project changes",
            code="RESTART_SAVE_CHANGES_ERROR",
            error=str(e),
        )
        QgisMessageUtil.modal_error(
            iface,
            STR.SAVE_PROJECT_CHANGES_ERROR.format(error=str(e)),
            title=STR.ERROR,
        )
        return

    # 3) Criar script .bat para reabrir QGIS
    cmd = _RestartExecutor.create_restart_script(project_path)

    if not cmd:
        logger.critical(
            "Cannot restart: failed to prepare restart command", code="RESTART_NO_CMD"
        )
        QgisMessageUtil.modal_error(
            iface,
            STR.QGIS_EXECUTABLE_NOT_FOUND,
            title=STR.ERROR,
        )
        return

    # 4) Executar restart (agendado para aboutToQuit)
    logger.info(
        "Executing restart sequence (scheduled)", code="RESTART_EXECUTING", cmd=cmd
    )
    _RestartExecutor.execute_restart(cmd)

    # 5) Fechar QGIS
    logger.info("Closing QGIS to start restart", code="RESTART_CLOSING")
    QgisMessageUtil.bar_info(
        iface,
        STR.QGIS_RESTARTING_MESSAGE,
        title=STR.QGIS_RESTARTING_TITLE,
        duration=2,
    )
    iface.mainWindow().close()


def run(iface):
    run_restart_qgis(iface)
