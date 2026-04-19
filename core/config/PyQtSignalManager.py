# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QObject, pyqtSignal
from ...utils.ToolKeys import ToolKey
from .LogUtils import LogUtils


class _PluginSignalHub(QObject):
    """Barramento global de sinais PyQt usados pelo plugin."""

    plugin_instantiated = pyqtSignal(dict)
    plugin_finished = pyqtSignal(dict)


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
        self._signal_hub.plugin_finished.connect(self._on_plugin_finished)
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
            self._signal_hub.plugin_finished.disconnect(
                self._on_plugin_finished
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

    def _on_plugin_finished(self, payload):
        """
        Atualiza main_action e reconstrói toolbar quando um plugin é finalizado.

        Recebe um payload com:
        - tool_key: identificador da ferramenta
        - preferences: dicionário de preferências da ferramenta (com usages atualizado)
        """
        try:
            from ...utils.Preferences import Preferences
            from .MenuManager import MenuManager

            tool_key = payload.get("tool_key", ToolKey.UNTRACEABLE)
            preferences = payload.get("preferences", {})

            self.logger.debug(
                f"[_on_plugin_finished] Processando conclusão de plugin: {tool_key}"
            )

            # 1. Obter a categoria da ferramenta
            tool_category = preferences.get("category")
            if not tool_category:
                self.logger.warning(
                    f"[_on_plugin_finished] Categoria NÃO encontrada nas prefs "
                    f"de {tool_key}. Prefs keys: {list(preferences.keys())}. "
                    f"NÃO atualizando main_action."
                )
                return

            self.logger.info(
                f"[_on_plugin_finished] Tool={tool_key}, category={tool_category}"
            )

            # 2. Reseta main_action para False SOMENTE na categoria desta ferramenta
            self.logger.info(
                f"[_on_plugin_finished] Resetando main_action=False na "
                f"categoria '{tool_category}'"
            )
            modified = Preferences.set_value_for_all_tools(
                "main_action",
                False,
                filter_by={"category": tool_category}
            )
            self.logger.info(
                f"[_on_plugin_finished] {modified} ferramentas foram resetadas"
            )

            # 3. Seta esta ferramenta como main_action=True
            preferences["main_action"] = True
            self.logger.info(
                f"[_on_plugin_finished] Configurando {tool_key} main_action=True"
            )

            # 4. Salva as preferências desta ferramenta
            Preferences.save_tool_prefs(tool_key, preferences)
            self.logger.info(
                f"[_on_plugin_finished] Preferências de {tool_key} salvas"
            )

            # 5. Reconstrói a toolbar com a nova configuração
            menu_manager = MenuManager.get_instance()
            if menu_manager is not None:
                self.logger.info(
                    f"[_on_plugin_finished] Reconstruindo toolbar..."
                )
                menu_manager.reconstruct_toolbar()
                self.logger.info(
                    f"[_on_plugin_finished] ✓ Toolbar reconstruída com sucesso"
                )
            else:
                self.logger.warning(
                    f"[_on_plugin_finished] MenuManager é None, toolbar NÃO "
                    f"será reconstruída."
                )

        except Exception as e:
            self.logger.error(
                f"[_on_plugin_finished] Erro ao processar conclusão de plugin: {e}",
                exc_info=True
            )
