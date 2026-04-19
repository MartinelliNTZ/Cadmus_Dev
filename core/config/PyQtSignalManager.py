# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QObject, pyqtSignal
from ...utils.ToolKeys import ToolKey
from .LogUtils import LogUtils


class _PluginSignalHub(QObject):
    """Barramento global de sinais PyQt usados pelo plugin."""

    plugin_instantiated = pyqtSignal(dict)


_plugin_signal_hub = None


def get_plugin_signal_hub():
    """Retorna singleton do barramento global de sinais."""
    global _plugin_signal_hub
    if _plugin_signal_hub is None:
        _plugin_signal_hub = _PluginSignalHub()
    return _plugin_signal_hub


class PyQtSignalManager(QObject):
    """Escuta sinais globais do plugin e registra eventos relevantes no log."""


    def create_menu_manager(self, iface, tools, logger):
        """Cria e retorna uma instância de MenuManager, menus e toolbar."""
        from .MenuManager import MenuManager
        menu_manager = MenuManager(iface, tools, logger)
        menu_manager.create_menu()
        logger.debug("Criando toolbar para o plugin via PyQtSignalManager")
        menu_manager.create_toolbar()
        menu_manager.populate_menus()
        logger.info(f"MenuManager criado e menus/toolbars populados via PyQtSignalManager: {menu_manager}.")
        return menu_manager

    def __init__(self, tool_key=ToolKey.UNTRACEABLE, parent=None):
        super().__init__(parent)
        self.tool_key = tool_key or ToolKey.UNTRACEABLE
        self.logger = LogUtils(
            tool=self.tool_key,
            class_name="PyQtSignalManager",
            level=LogUtils.DEBUG,
        )
        self._signal_hub = get_plugin_signal_hub()
        self._is_connected = False

    def start(self):
        """Conecta handlers aos sinais globais."""
        if self._is_connected:
            self.logger.debug("[start] PyQtSignalManager jÃ¡ conectado")
            return

        self._signal_hub.plugin_instantiated.connect(self._on_plugin_instantiated)
        self._is_connected = True
        self.logger.info("[start] PyQtSignalManager conectado ao hub de sinais")

    def stop(self):
        """Desconecta handlers dos sinais globais."""
        if not self._is_connected:
            return

        try:
            self._signal_hub.plugin_instantiated.disconnect(
                self._on_plugin_instantiated
            )
            self.logger.info("[stop] PyQtSignalManager desconectado do hub de sinais")
        except Exception as e:
            self.logger.error(
                f"[stop] Erro ao desconectar PyQtSignalManager do hub: {e}"
            )
        finally:
            self._is_connected = False

    def _on_plugin_instantiated(self, payload):
        """Registra no log quando um plugin baseado em BasePlugin Ã© instanciado."""
        try:
            event_tool_key = payload.get("tool_key", ToolKey.UNTRACEABLE)
            class_name = payload.get("class_name", "UnknownPlugin")
            plugin_name = payload.get("plugin_name", class_name)
            build_ui = payload.get("build_ui", False)

            self.logger.info(
                "[plugin_instantiated] "
                f"tool_key={event_tool_key}, class_name={class_name}, "
                f"plugin_name={plugin_name}, build_ui={build_ui}"
            )
        except Exception as e:
            self.logger.error(
                f"[_on_plugin_instantiated] Erro ao processar sinal recebido: {e}"
            )
