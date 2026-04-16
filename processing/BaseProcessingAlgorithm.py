# -*- coding: utf-8 -*-
import os

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.core import QgsProcessingAlgorithm

from ..core.config.LogUtils import LogUtils
from ..resources.HtmlInstructionsProvider import HtmlInstructionsProvider
from ..resources.IconManager import IconManager as im
from ..utils.Preferences import Preferences
from ..utils.ToolKeys import ToolKey
from ..i18n.TranslationManager import STR


class GroupProcessing:
    def __init__(self, id=None, name=None, icon_path="cadmus_icon.ico"):
        self.id = id
        self.name = name
        self.icon_path = icon_path


class BaseProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    Base class for processing algorithms in the Cadmus plugin.
    """

    GROUP_ESTATISTICA = GroupProcessing(id="estatistica", name=STR.STATISTICS)
    GROUP_RASTER = GroupProcessing(id="raster", name=STR.RASTER)
    GROUP_VETORIAL = GroupProcessing(id="vetorial", name=STR.VECTOR)
    prefs = {}  # para armazenar preferências carregadas
    INSTRUCTIONS_FILE = None
    TOOL_KEY = None
    ALGORITHM_NAME = None
    ALGORITHM_DISPLAY_NAME = None
    ALGORITHM_GROUP = GROUP_VETORIAL
    ICON = "cadmus_icon.ico"

    def shortHelpString(self):
        if self.prefs.get("display_help", True):  # self.INSTRUCTIONS_FILE:
            html = HtmlInstructionsProvider(self.TOOL_KEY)
            return html.get_instructions(self.ALGORITHM_NAME)  # valor padrão genérico
        else:
            return

    def icon(self):
        icon_path = im.icon_path(self.ICON) if self.ICON else None
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return QIcon()

    def createInstance(self):
        return self.__class__()

    def name(self):
        if self.ALGORITHM_NAME:
            return self.ALGORITHM_NAME
        raise NotImplementedError(
            "Algoritmo precisa definir ALGORITHM_NAME ou override name()."
        )

    def displayName(self):
        if self.ALGORITHM_DISPLAY_NAME:
            return self.ALGORITHM_DISPLAY_NAME
        raise NotImplementedError(
            "Algoritmo precisa definir ALGORITHM_DISPLAY_NAME ou override displayName()."
        )

    def group(self):
        return (
            self.ALGORITHM_GROUP.name
            if self.ALGORITHM_GROUP
            else self.GROUP_VETORIAL.name
        )

    def groupId(self):
        return (
            self.ALGORITHM_GROUP.id if self.ALGORITHM_GROUP else self.GROUP_VETORIAL.id
        )

    def load_preferences(self):
        """Carrega preferências usando Preferences.load_tool_prefs e armazena em self.prefs. Retorna dict de preferências ou vazio se falhar."""
        if not self.TOOL_KEY:
            return {}
        try:
            self.prefs = Preferences.load_tool_prefs(self.TOOL_KEY)
        except Exception as e:
            LogUtils(
                tool=ToolKey.UNTRACEABLE,
                class_name=self.__class__.__name__,
                level=LogUtils.WARNING,
            ).warning(f"Falha ao carregar preferências de {self.TOOL_KEY}: {e}")
            return {}

    def save_preferences(self):
        """Salva self.prefs usando Preferences.save_tool_prefs. Espera que self.prefs já esteja atualizada."""
        if not self.TOOL_KEY:
            return
        if self.prefs is None:
            self.prefs = {}
        Preferences.save_tool_prefs(self.TOOL_KEY, self.prefs)

    def open_folder_in_explorer(self, folder_path):
        if folder_path and os.path.exists(folder_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
