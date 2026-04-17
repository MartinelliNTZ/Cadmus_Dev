# -*- coding: utf-8 -*-
from .BaseDialog import BaseDialog
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsVectorLayer
import os
from typing import Optional
import time
from ..utils.FormatUtils import FormatUtils
from ..core.config.LogUtils import LogUtils
from ..core.config.MenuManager import MenuManager
from ..core.config.PyQtSignalManager import get_plugin_signal_hub
from ..core.ui.info_dialog import InfoDialog
from ..utils.Preferences import Preferences
from ..utils.ToolKeys import ToolKey
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.ProjectUtils import ProjectUtils
from ..resources.InstructionsManager import InstructionsManager
from ..i18n.TranslationManager import STR


# -------------------------------------------------------------
#  PLUGIN BasePluginMTL
# -------------------------------------------------------------
class BasePluginMTL(BaseDialog):
    plugin_instantiated = pyqtSignal(dict)
    APP_NAME = STR.APP_NAME
    TOOL_KEY = "base_plugin"  # Identificador padrão
    PLUGIN_NAME = ""
    prefs = None
    preferences = {}
    """Dicionario de status"""
    system_preferences = {}
    AUTO_SAVE_PREFS_ON_CLOSE = True  # Define se as preferências devem ser salvas automaticamente ao fechar o plugin
    """Preferências globais do aplicativo (Cadmus Settings)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plugin_signal_emitted = False
        self._plugin_signal_context = {
            "tool_key": self.TOOL_KEY,
            "class_name": self.__class__.__name__,
            "plugin_name": self.PLUGIN_NAME or self.__class__.__name__,
            "build_ui": False,
        }

    def init(
        self,
        tool_key="base_plugin",
        class_name="BasePluginMTL",
        load_system_prefs=False,
        build_ui=True,
    ):
        """Inicializa o plugin base.

        Parameters
        ----------
        tool_key : str
            Identificador único da ferramenta (padrão: base_plugin)
        class_name : str
            Nome da classe para logging (padrão: BasePluginMTL)
        load_settings_prefs : bool
            Se True, carrega preferências globais do Cadmus Settings (padrão: False)
        build_ui : bool
            Se True, constrói a interface de usuário (padrão: True)
        """
        self.TOOL_KEY = tool_key
        self.logger = LogUtils(
            tool=self.TOOL_KEY, class_name=class_name, level=LogUtils.DEBUG
        )

        self.preferences = {}
        self.preferences.clear()
        self.preferences = Preferences.load_tool_prefs(self.TOOL_KEY)
        self._plugin_signal_context = {
            "tool_key": self.TOOL_KEY,
            "class_name": class_name,
            "plugin_name": self.PLUGIN_NAME or class_name,
            "build_ui": bool(build_ui),
        }

        # Carregar preferências globais do Settings se solicitado
        if load_system_prefs:
            self.logger.debug("Carregando preferências globais do Cadmus Settings")
            self.system_preferences = Preferences.load_tool_prefs(ToolKey.SYSTEM)
            self.logger.debug(
                f"Preferências globais carregadas: {list(self.system_preferences.keys())}"
            )
        else:
            self.system_preferences = {}

        # Construir UI apenas se solicitado
        if build_ui:
            self.logger.debug("Construindo interface de usuário")
            self._build_ui()
            self.logger.debug("Carregando preferências do usuário")
            self._load_prefs()
            self.logger.info("Plugin inicializado com sucesso")
        else:
            self.logger.debug("Construção de UI desabilitada")

    def showEvent(self, event):
        """Emite o sinal uma Ãºnica vez quando a janela Ã© realmente aberta."""
        super().showEvent(event)

        if self._plugin_signal_emitted:
            return

        self._emit_plugin_instantiated_signal()
        self._plugin_signal_emitted = True

    def _emit_plugin_instantiated_signal(self):
        """Emite sinal quando uma instÃ¢ncia filha do BasePlugin Ã© iniciada."""
        payload = dict(self._plugin_signal_context)
        payload["tool_key"] = self.TOOL_KEY
        payload["plugin_name"] = self.PLUGIN_NAME or payload.get("class_name")

        try:
            self.plugin_instantiated.emit(payload)
            get_plugin_signal_hub().plugin_instantiated.emit(payload)
            self.logger.debug(
                f"[plugin_instantiated] Sinal emitido com payload: {payload}"
            )
        except Exception as e:
            self.logger.error(
                f"[plugin_instantiated] Erro ao emitir sinal de instanciaÃ§Ã£o: {e}"
            )

    """
    Classe base para plugins do Cadmus.

    Centraliza funcionalidades comuns aos plugins, como:
    - Criação de ações de menu
    - Recuperação da camada vetorial ativa
    - Validações básicas de edição e existência de feições

    Deve ser herdada por plugins específicos.
    """

    def _build_ui(
        self,
        title: Optional[str] = None,
        icon_path: Optional[str] = "cadmus_icon.ico",
        enable_scroll: bool = True,
        **kwargs,
    ):
        super()._build_ui(title=title, icon_path=icon_path, enable_scroll=enable_scroll)

        # instruções - resolvidas automaticamente via InstructionsManager.get(TOOL_KEY)
        self.instructions_file = InstructionsManager.get(self.TOOL_KEY)
        self.logger.debug(
            f"Instruções carregadas via InstructionsManager: {self.instructions_file}"
        )
        # Restaurar tamanho da janela se foi persistido
        self._restore_window_size()

    def _restore_window_size(self):
        """
        Restaura o tamanho da janela a partir das preferências.

        Se não houver tamanho persistido, usa 300x300 como padrão.
        """
        saved_width = self.preferences.get("window_width", 300)
        saved_height = self.preferences.get("window_height", 300)

        try:
            self.resize(int(saved_width), int(saved_height))
            self.logger.debug(
                f"Tamanho da janela restaurado: {saved_width}x{saved_height}"
            )
        except Exception as e:
            self.logger.warning(
                f"Erro ao restaurar tamanho da janela: {e}, usando padrão"
            )
            self.resize(300, 300)

    def _persist_window_size(self):
        """
        Persiste o tamanho atual da janela nas preferências.

        Deve ser chamado em closeEvent() ou ao finalizar a execução.
        """
        width = self.width()
        height = self.height()

        self.preferences["window_width"] = width
        self.preferences["window_height"] = height

        self.logger.debug(f"Tamanho da janela persistido: {width}x{height}")

    def closeEvent(self, event):
        """
        Override do evento de fechamento para persistir preferências.

        Salva tamanho da janela e demais preferências antes de fechar.
        """
        self.logger.debug("Fechando plugin, persistindo preferências")
        self._persist_window_size()
        self.on_finish_plugin()  # Incrementa o contador de uso ao fechar o plugin
        if self.AUTO_SAVE_PREFS_ON_CLOSE:
            self._save_prefs()

        super().closeEvent(event)


    def on_finish_plugin(self):
        """
        Callback executado ao fechar o plugin.
        Atualiza main_action para a ferramenta atual e reconstrói a toolbar.
        """
        try:
            # 1. Incrementar contador de uso
            valor_atual = self.preferences.get("usages", 0)
            self.preferences["usages"] = valor_atual + 1
            self.logger.debug(f"Usages incrementado: {valor_atual} → {valor_atual + 1}")

            # 2. Obter a categoria desta ferramenta da preferences
            tool_category = self.preferences.get("category")
            self.logger.info(
                f"[on_finish_plugin] Tool={self.TOOL_KEY}, category={tool_category}"
            )
            
            if not tool_category:
                self.logger.warning(
                    f"[on_finish_plugin] ✗ Categoria NÃO encontrada nas prefs de "
                    f"{self.TOOL_KEY}. Prefs keys: {list(self.preferences.keys())}. "
                    f"NÃO atualizando main_action."
                )
                return

            # 3. Reseta main_action para False SOMENTE na categoria desta ferramenta
            self.logger.info(
                f"[on_finish_plugin] Chamando set_value_for_all_tools para resetar "
                f"main_action=False na categoria '{tool_category}'"
            )
            modified = Preferences.set_value_for_all_tools(
                "main_action", 
                False,
                filter_by={"category": tool_category}
            )
            self.logger.info(
                f"[on_finish_plugin] ✓ set_value_for_all_tools retornou: "
                f"{modified} ferramentas modificadas"
            )

            # 4. Seta esta ferramenta como main_action=True
            self.preferences["main_action"] = True
            self.logger.info(
                f"[on_finish_plugin] Configurando {self.TOOL_KEY} main_action=True "
                f"(categoria: {tool_category})"
            )

            # 5. Salva as preferências desta ferramenta
            Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
            self.logger.info(
                f"[on_finish_plugin] ✓ Preferências de {self.TOOL_KEY} salvas"
            )

            # 6. Reconstrói a toolbar com a nova configuração
            menu_manager = MenuManager.get_instance()
            mgr = MenuManager.get_instance()
            if mgr:
                mgr.reconstruct_toolbar()
            if menu_manager is not None:
                self.logger.info(
                    f"[on_finish_plugin] MenuManager obtido, reconstruindo toolbar..."
                )
                menu_manager.reconstruct_toolbar()
                self.logger.info(
                    f"[on_finish_plugin] ✓ Toolbar reconstruída com sucesso"
                )
            else:
                self.logger.error(
                    f"[on_finish_plugin] ✗ MenuManager é None! Toolbar NÃO será reconstruída."
                )

        except Exception as e:
            self.logger.error(
                f"[on_finish_plugin] ✗ Erro: {e}",
                exc_info=True
            )

    def _save_prefs(self):
        """Salva preferências."""
        self.logger.debug("Salvando preferências")

    def start_stats(self, input_obj=None, modal_info="YES", total_files=None):
        try:
            self.preferences["t0"] = time.time()

            # Reset transient counters
            self.preferences.pop("current_size", None)
            self.preferences.pop("current_features", None)
            self.preferences.pop("current_files", None)
            self.preferences.pop("eta", None)
            self.preferences.pop("eta_files", None)

            # Aggregates (ensure exist)
            self.preferences["total_bytes"] = self.preferences.get("total_bytes", 0)
            self.preferences["total_time"] = self.preferences.get("total_time", 0)
            self.preferences["total_features"] = self.preferences.get(
                "total_features", 0
            )
            self.preferences["total_files"] = self.preferences.get("total_files", 0)
            self.preferences["total_time_features"] = self.preferences.get(
                "total_time_features", 0
            )
            self.preferences["total_time_files"] = self.preferences.get(
                "total_time_files", 0
            )

            # Metrics: files-based, features-based, or bytes-based
            if total_files is not None:
                # files metric
                self.preferences["current_files"] = int(total_files)
                avg_files = self.preferences.get("avg_speed_files", 0)
                if avg_files > 0:
                    self.preferences["eta_files"] = time.time() + (
                        self.preferences["current_files"] / avg_files
                    )
                else:
                    self.preferences["eta_files"] = 0
                TAM = f"{self.preferences['current_files']} files"
                msg = f"Iniciando: total files={self.preferences['current_files']}"

                self.logger.info(msg)

            else:
                # fallback: if vector-like, use features; else use size(bytes)
                if input_obj is not None and hasattr(input_obj, "featureCount"):
                    try:
                        self.preferences["current_features"] = input_obj.featureCount()
                    except Exception:
                        self.preferences["current_features"] = 0
                    avg_feat = self.preferences.get("avg_speed_features", 0)
                    if avg_feat > 0 and self.preferences["current_features"] > 0:
                        self.preferences["eta"] = time.time() + (
                            self.preferences["current_features"] / avg_feat
                        )
                    TAM = f"{self.preferences.get('current_features', 0)} feats"
                    msg = f"Iniciando: features={self.preferences.get('current_features', 0)}"

                    self.logger.info(msg)
                else:
                    # treat as raster/file
                    self.preferences["current_size"] = (
                        ProjectUtils.compute_size(input_obj) if input_obj else 0
                    )
                    avg_bytes = self.preferences.get("avg_speed", 0)
                    if avg_bytes > 0 and self.preferences["current_size"] > 0:
                        self.preferences["eta"] = time.time() + (
                            self.preferences["current_size"] / avg_bytes
                        )
                    TAM = FormatUtils.bytes(self.preferences.get("current_size", 0))
                    msg = f"Iniciando: size={TAM}"

                    self.logger.info(msg)
        except Exception as e:
            self.logger.error(e)

    def finish_stats(
        self, modal_info="YES", input_obj=None, start_time=None, total_files=None
    ):
        self.logger.debug("finish_stats")
        try:
            if start_time is None:
                start_time = self.preferences.get("t0", time.time())
            end_time = time.time()
            total_time = end_time - start_time

            # files-based completion
            if total_files is not None:
                self.preferences["total_files"] = self.preferences.get(
                    "total_files", 0
                ) + int(total_files)
                self.preferences["total_time_files"] = (
                    self.preferences.get("total_time_files", 0) + total_time
                )
                if self.preferences["total_time_files"] > 0:
                    self.preferences["avg_speed_files"] = self.preferences.get(
                        "total_files", 0
                    ) / self.preferences.get("total_time_files", 1)

            # features-based completion (if input supports it)
            current_features = 0
            if input_obj is not None and hasattr(input_obj, "featureCount"):
                try:
                    current_features = input_obj.featureCount()
                except Exception:
                    current_features = self.preferences.get("current_features", 0)
            self.preferences["total_features"] = (
                self.preferences.get("total_features", 0) + current_features
            )
            self.preferences["total_time_features"] = (
                self.preferences.get("total_time_features", 0) + total_time
            )
            if self.preferences["total_time_features"] > 0:
                self.preferences["avg_speed_features"] = self.preferences.get(
                    "total_features", 0
                ) / self.preferences.get("total_time_features", 1)

            # bytes/size-based completion
            current_size = (
                ProjectUtils.compute_size(input_obj)
                if input_obj
                else self.preferences.get("current_size", 0)
            )
            self.preferences["total_time"] = (
                self.preferences.get("total_time", 0) + total_time
            )
            self.preferences["total_bytes"] = (
                self.preferences.get("total_bytes", 0) + current_size
            )
            if self.preferences["total_time"] > 0:
                self.preferences["avg_speed"] = self.preferences.get(
                    "total_bytes", 0
                ) / self.preferences.get("total_time", 1)

            # Log summary
            try:
                msg = (
                    f"Tamanho: {FormatUtils.bytes(current_size)}\n"
                    f"Feições: {current_features}\n"
                    f"Velocidade média(bytes/s): {FormatUtils.speed(self.preferences.get('avg_speed', 0))}\n"
                    f"Velocidade média(feats/s): {FormatUtils.pretty(self.preferences.get('avg_speed_features', 0))}\n"
                    f"Velocidade média(files/s): {FormatUtils.pretty(self.preferences.get('avg_speed_files', 0))}\n"
                )
                self.logger.info(msg)
            except Exception as ex:
                self.logger.error(f"Erro ao gerar resumo de estatísticas: {ex}")

            # atualizar agregados de features e limpar dados transitórios antes de persistir
            self.preferences["total_features"] = self.preferences.get(
                "total_features", 0
            )

            # campos que não devem ser salvos entre execuções
            for key in (
                "t0",
                "current_size",
                "current_features",
                "eta",
                "avg_speed",
                "current_files",
                "eta_files",
            ):
                self.preferences.pop(key, None)
            try:
                Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
            except Exception as se:
                self.logger.debug(f"Falha ao salvar prefs estatísticas: {se}")
        except Exception as e:
            self.logger.error(f"Erro: {e} Preferences: {self.preferences}")

    # @abstractmethod
    def execute_tool(self):
        """
        Método principal a ser implementado por cada plugin específico.
        Ele é chamado quando o usuário aciona a funcionalidade do plugin (ex: clica em um botão).
        Deve conter a lógica de execução do plugin.
        """
        self.logger.debug(
            "execute_tool chamado - deve ser implementado pelo plugin específico"
        )

    def _on_pipeline_finished(self, context):
        """Callback para quando a pipeline é finalizada com sucesso."""
        self.logger.debug("Pipeline finalizada com sucesso")

    def _on_pipeline_error(self, errors):
        """Exibe um modal de erro genérico para a pipeline."""
        exc = errors[0] if errors else Exception("Erro desconhecido")

        QgisMessageUtil.modal_error(self.iface, f"Erro durante processamento:\n{exc}")


    def show_info_dialog(self, title=f"📘 {STR.INSTRUCTIONS}"):
        """Mostra diálogo de instruções do plugin.

        Recebe: title (str opcional).
        Retorna: None.
        Faz: abre `InfoDialog` com o arquivo de instruções, se existir.
        """
        self.logger.debug("Exibindo diálogo de informações")
        if hasattr(self, "instructions_file"):
            title = f"📘 {STR.INSTRUCTIONS} – {self.PLUGIN_NAME}"
            InfoDialog(self.instructions_file, self, title).exec()

    def apply_qml_style(self, layer: QgsVectorLayer, qml_path: str) -> bool:
        """Aplica um arquivo QML como estilo na camada.

        Recebe: layer (QgsVectorLayer), qml_path (str).
        Retorna: bool (sucesso).
        Faz: valida entrada, carrega estilo e repinta a camada.
        """
        self.logger.debug(
            f"Aplicando estilo QML à camada: {layer.name() if isinstance(layer, QgsVectorLayer) else 'inválida'}. Caminho: {qml_path}"
        )

        if not isinstance(layer, QgsVectorLayer):
            return False

        if not qml_path or not os.path.exists(qml_path):
            self.logger.debug(f"Caminho QML inválido ou não existe: {qml_path}")
            return False

        ok = layer.loadNamedStyle(qml_path)
        if isinstance(ok, tuple):
            ok = ok[0]

        if ok:
            layer.triggerRepaint()
            self.logger.debug("Estilo QML aplicado com sucesso")

        return bool(ok)
