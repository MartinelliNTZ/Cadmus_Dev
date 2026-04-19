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
        """
        Executado quando um plugin é instanciado (aberto).
        Responsável por reconstruir a toolbar com novo main_action.
        """
        try:
            event_tool_key = payload.get("tool_key", ToolKey.UNTRACEABLE)
            class_name = payload.get("class_name", "UnknownPlugin")
            plugin_name = payload.get("plugin_name", class_name)
            build_ui = payload.get("build_ui", False)

            self.logger.info(
                "[_on_plugin_instantiated] Plugin aberto: "
                f"tool_key={event_tool_key}, class_name={class_name}, "
                f"plugin_name={plugin_name}, build_ui={build_ui}"
            )

            # ✅ RECONSTRUIR TOOLBAR ao plugin abrir
            # Primeira, atualizar main_action da ferramenta que abriu
            from ...utils.Preferences import Preferences
            from .MenuManager import MenuManager

            tool_prefs = Preferences.load_tool_prefs(event_tool_key)
            tool_category = tool_prefs.get("category")

            if not tool_category:
                self.logger.warning(
                    f"[_on_plugin_instantiated] Categoria NÃO encontrada para {event_tool_key}. "
                    f"Toolbar NÃO será reconstruída."
                )
                return

            self.logger.info(
                f"[_on_plugin_instantiated] Atualizando main_action para {event_tool_key} "
                f"(categoria: {tool_category})"
            )

            # Resetar main_action em todas as ferramentas da categoria
            modified = Preferences.set_value_for_all_tools(
                "main_action",
                False,
                filter_by={"category": tool_category}
            )
            self.logger.info(
                f"[_on_plugin_instantiated] {modified} ferramentas resetadas na categoria"
            )

            # Setar main_action=True para esta ferramenta
            tool_prefs["main_action"] = True
            Preferences.save_tool_prefs(event_tool_key, tool_prefs)
            self.logger.info(
                f"[_on_plugin_instantiated] Configurado main_action=True para {event_tool_key}"
            )

            # ✅ RECONSTRUIR TOOLBAR
            menu_manager = MenuManager.get_instance()
            if menu_manager is not None:
                self.logger.info(
                    f"[_on_plugin_instantiated] Reconstruindo toolbar..."
                )
                menu_manager.reconstruct_toolbar()
                self.logger.info(
                    f"[_on_plugin_instantiated] ✓ Toolbar reconstruída com sucesso"
                )
            else:
                self.logger.warning(
                    f"[_on_plugin_instantiated] MenuManager é None, toolbar NÃO "
                    f"será reconstruída."
                )

        except Exception as e:
            self.logger.error(
                f"[_on_plugin_instantiated] Erro ao processar sinal: {e}",
                exc_info=True
            )

    def _on_plugin_finished(self, payload):
        """
        Executado quando um plugin é finalizado (fechado).
        Apenas atualiza main_action para a categoria, SEM reconstruir toolbar.
        (Toolbar é reconstruída quando outro plugin abre via _on_plugin_instantiated)
        """
        try:
            from ...utils.Preferences import Preferences

            tool_key = payload.get("tool_key", ToolKey.UNTRACEABLE)
            preferences = payload.get("preferences", {})

            self.logger.info(
                f"[_on_plugin_finished] Plugin fechado: {tool_key}"
            )

            # Obter a categoria da ferramenta
            tool_category = preferences.get("category")
            if not tool_category:
                self.logger.warning(
                    f"[_on_plugin_finished] Categoria NÃO encontrada nas prefs "
                    f"de {tool_key}. Prefs keys: {list(preferences.keys())}. "
                    f"Main action NÃO será resetado."
                )
                return

            self.logger.debug(
                f"[_on_plugin_finished] Tool={tool_key}, category={tool_category}"
            )

            # Reseta main_action para False SOMENTE na categoria desta ferramenta
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

            # Seta esta ferramenta como main_action=True
            preferences["main_action"] = True
            self.logger.debug(
                f"[_on_plugin_finished] Configurando {tool_key} main_action=True"
            )

            # Salva as preferências desta ferramenta
            Preferences.save_tool_prefs(tool_key, preferences)
            self.logger.info(
                f"[_on_plugin_finished] ✓ Preferências de {tool_key} salvas"
            )

            # ✅ IMPORTANTE: NÃO reconstruir toolbar aqui!
            # A toolbar será reconstruída quando outro plugin for aberto
            self.logger.info(
                f"[_on_plugin_finished] ⓘ Toolbar NÃO será reconstruída ao fechar. "
                f"Será reconstruída quando próximo plugin abrir."
            )

        except Exception as e:
            self.logger.error(
                f"[_on_plugin_finished] Erro ao processar finalização de plugin: {e}",
                exc_info=True
            )
