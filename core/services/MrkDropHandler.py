# -*- coding: utf-8 -*-
from qgis.gui import QgsCustomDropHandler

from ...i18n.TranslationManager import STR
from ...utils.ExplorerUtils import ExplorerUtils
from ...utils.QgisMessageUtil import QgisMessageUtil
from .DroneCoordinatesRunner import DroneCoordinatesRunner


class MrkDropHandler(QgsCustomDropHandler):
    PROVIDER_KEY = "cadmus_mrk"

    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.runner = DroneCoordinatesRunner(iface)

    def handleFileDrop(self, file):
        if not ExplorerUtils.has_extension(file, [".mrk"]):
            return False

        QgisMessageUtil.bar_info(self.iface, STR.MRK_DROP_START, duration=3)
        return bool(self.runner.run_mrk_file(file))

    def customUriProviderKey(self):
        return self.PROVIDER_KEY

    def handleCustomUriDrop(self, uri):
        if not uri:
            return False
        return self.handleFileDrop(uri.uri)
