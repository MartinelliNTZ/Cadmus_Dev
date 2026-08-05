# -*- coding: utf-8 -*-


from ...plugins.BaseDialog import BaseDialog
from ...i18n.TranslationManager import STR
from ..config.LogUtils import LogUtils
from ...utils.ToolKeys import ToolKey
from ..services.PackageManager import PackageManager
from ...resources.widgets.grid.GridInputFields import GridInputFields
from ...resources.widgets.grid.GridLabel import GridLabel
from ...resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ...resources.widgets.grid.GridComplexSelector import GridComplexSelector


class RegistryDialog(BaseDialog):
    """
    Diálogo modal para gerenciamento de registro e restauração.

    Layout:
    - GridInputFields para inserir chave
    - GridLabel: Nível, Validade, Status (com cor dinâmica)
    - GridExecutionButtons: Validar, Remover, Restaurar, Salvar, Fechar
    - GridComplexSelector para selecionar arquivo .dist
    """

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.logger = LogUtils(tool=ToolKey.SETTINGS, class_name="RegDialog")

        # Lazy import de RegistryManager — se foi compilado/removido = versão premium
        self.lic_mgr = self._init_lic_mgr()
        self._premium = self.lic_mgr is None

        self.setWindowTitle(STR.REG_TITLE)
        self.setMinimumWidth(400)
        self.setModal(True)

        self._input_key = None
        self._info_labels = None
        self._dist_grid = None
        self._action_buttons = None

        self._build_ui()
        self._refresh()

    @staticmethod
    def _init_lic_mgr():
        """
        Tenta importar RegistryManager com lazy/try.
        Se falhar (classe compilada/removida em distribuição), retorna None.
        None significa versão premium → não precisa de licença.
        """
        try:
            from ..config.RegistryManager import RegistryManager

            return RegistryManager(tool_key=ToolKey.SETTINGS)
        except ImportError:
            return None
        except Exception:
            return None

    # ----------------------------------------------------------------
    # UI
    # ----------------------------------------------------------------

    def _build_ui(self):
        super()._build_ui(
            title=STR.REG_TITLE,
            icon_path="cadmus_icon.ico",
            enable_scroll=True,
            minimum_size=(400, 400),
        )

        # ── Campo de Chave (GridInputFields) ─────────────────────
        self._input_key = GridInputFields(
            config={
                "lic_key": {
                    "label": f"{STR.LICENSE_KEY}:",
                    "description": "Insira a chave",
                    "default": "",
                },
            },
            parent=self,
        )
        self.layout.addWidget(self._input_key)

        # ── Labels de Info (GridLabel + opção color) ─────────────
        self._info_labels = GridLabel(
            config={
                "level": {"text": f"{STR.LEVEL}: -", "color": ""},
                "expiry": {"text": f"{STR.EXPIRATION_DATE}: -", "color": ""},
                "status": {
                    "text": f"{STR.STATUS}: {STR.INACTIVE}",
                    "color": "gray",
                },
            },
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self._info_labels)

        # ── Restaurar Registro (GridComplexSelector) ─────────────
        self._dist_grid = GridComplexSelector(
            config={
                "Registro": {
                    "label": f"📦 {STR.SELECT_FILE} (.dist):",
                    "description": "Selecione o arquivo de registro Cadmus",
                    "file_filter": "Registro Cadmus (*.dist);;Todos os arquivos (*)",
                    "mode_type": "input",
                    "allow_file": True,
                    "allow_folder": False,
                    "multiple": False,
                    "show_explorer_button": True,
                    "show_copy_button": False,
                },
            },
            tool_key=ToolKey.SETTINGS,
            title=STR.RESTORE_DISTRIBUTION,
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self._dist_grid)

        # Stretch para empurrar o conteúdo para cima
        self.layout.addStretch()

        # ── Botões de Ação (GridExecutionButtons) ────────────────
        self._action_buttons = GridExecutionButtons(
            config={
                "validate": {
                    "label": STR.VALIDATE,
                    "description": "Valida a chave",
                    "callback": self._on_validate,
                    "is_run_button": True,
                },
                "delete": {
                    "label": f"🗑️ {STR.REMOVE}",
                    "description": "Remove o registro atual",
                    "callback": self._on_delete,
                },
                "restore": {
                    "label": f"📦 {STR.MODE_RESTORE}",
                    "description": "Restaura o registro a partir do arquivo .dist",
                    "callback": self._on_restore_distribution,
                },
                "save": {
                    "label": f"💾 {STR.SAVE}",
                    "description": "Salva e valida a chave",
                    "callback": self._on_save,
                },
            },
            enable_close_button=True,
            enable_config_button=False,
            enable_info=False,
            tool_key=ToolKey.SETTINGS,
            parent=self,
        )
        self.layout.add_execution_buttons(self._action_buttons)

    # ----------------------------------------------------------------
    # Handlers
    # ----------------------------------------------------------------

    def _on_validate(self):
        self._do_save(show_message=False)

    def _on_save(self):
        self._do_save(show_message=True)

    def _do_save(self, show_message: bool):
        if self.lic_mgr is None:
            # Premium — não precisa de licença
            from ...utils.QgisMessageUtil import QgisMessageUtil

            QgisMessageUtil.modal_info(
                self.iface,
                message="Versão premium — registro não necessário.",
                title=STR.REG_TITLE,
            )
            self.accept()
            return

        key = self._input_key.get_value("lic_key").strip()
        if not key:
            self._refresh()
            if show_message:
                from ...utils.QgisMessageUtil import QgisMessageUtil

                QgisMessageUtil.modal_warning(
                    self.iface,
                    message=STR.REGISTRY_EMPTY,
                    title=STR.REG_TITLE,
                )
            return

        result = self.lic_mgr.save_lic_key(key)
        self._refresh()

        if show_message:
            from ...utils.QgisMessageUtil import QgisMessageUtil

            if result.get("success"):
                QgisMessageUtil.modal_info(
                    self.iface,
                    message=STR.REGISTRY_SAVED_SUCCESS,
                    title=STR.REG_TITLE,
                )
                self.accept()
            else:
                QgisMessageUtil.modal_warning(
                    self.iface,
                    message=result.get("message", STR.REGISTRY_INVALID),
                    title=STR.REG_TITLE,
                )

    def _on_delete(self):
        if self.lic_mgr is None:
            return
        self.lic_mgr.delete_lic()
        self._input_key.set_value("lic_key", "")
        self._refresh()
        from ...utils.QgisMessageUtil import QgisMessageUtil

        QgisMessageUtil.modal_info(
            self.iface,
            message=STR.REGISTRY_DELETED_SUCCESS,
            title=STR.REG_TITLE,
        )

    def _on_restore_distribution(self):
        """
        Restaura as classes do arquivo .dist selecionado para as pastas
        corretas. Delega a instalação para PackageManager.install_package().
        Se o pacote contiver uma chave de licença, ela é aplicada
        automaticamente via callback.
        """
        from ...utils.QgisMessageUtil import QgisMessageUtil
        from pathlib import Path

        # Obtém o caminho do arquivo do GridComplexSelector
        file_path = self._dist_grid.get_path("Registro")
        if not file_path:
            QgisMessageUtil.modal_warning(
                self.iface,
                message=STR.SELECT_DIST_FILE,
                title=STR.RESTORE_DISTRIBUTION,
            )
            return

        plugin_root = Path(__file__).resolve().parent.parent.parent

        # Callback para aplicar chave de licença
        def _on_key(key: str):
            self.logger.info(
                f"Chave de licença encontrada no pacote: " f"{key[:4]}****"
            )
            self._input_key.set_value("lic_key", key)
            # Re-inicializa _mgr — agora RegistryManager está disponível
            self.lic_mgr = self._init_lic_mgr()
            self._premium = self.lic_mgr is None

            if self.lic_mgr is not None:
                result = self.lic_mgr.save_lic_key(key)
                if result.get("success"):
                    self.logger.info("Licença do pacote aplicada com sucesso")
                else:
                    self.logger.warning(
                        f"Falha ao aplicar licença do pacote: "
                        f"{result.get('message')}"
                    )

            else:
                self.logger.warning(
                    "Chave encontrada no pacote mas RegistryManager "
                    "não pôde ser carregado após restauração"
                )
            self._refresh()

        # Delega para PackageManager
        result = PackageManager.install_package(
            dist_path=file_path,
            plugin_root=plugin_root,
            on_key_callback=_on_key,
            logger=self.logger,
        )

        if result["success"]:
            # Re-inicializa _lic_mgr
            self.lic_mgr = self._init_lic_mgr()
            self._premium = self.lic_mgr is None

            QgisMessageUtil.modal_info(
                self.iface,
                message=result["message"],
                title=STR.RESTORE_DISTRIBUTION,
            )

        else:
            QgisMessageUtil.modal_warning(
                self.iface,
                message=result["message"],
                title=STR.RESTORE_DISTRIBUTION,
            )
        self._refresh()

    def _refresh(self):
        self.logger.info(f"Iniciando refresh{self.lic_mgr}")
        if self.lic_mgr is None:
            # Premium — esconde campos de licença
            self.setWindowTitle(STR.REG_TITLE)
            self._input_key.setVisible(False)
            self._info_labels.setVisible(False)
            self.logger.info(f"Licensa nao encontrada {self.lic_mgr}")
            return

        info = self.lic_mgr.get_registry_info()

        has_key = info.get("has_key", False)
        is_active = info.get("is_active", False)
        is_valid = has_key and is_active

        nivel = info.get("nivel", 0)
        self._info_labels.set_text(
            "level",
            f"{STR.LEVEL}: {str(nivel) if is_valid and nivel > 0 else '-'}",
        )
        self._info_labels.set_text(
            "expiry",
            f"{STR.EXPIRATION_DATE}: {info.get('expiry') if is_valid else '-'}",
        )
        self.logger.info(
            f"Debug has lic: {has_key} lice manager: {self.lic_mgr}, is_valid: {is_valid},is active: {is_active}, info: {info}, nivel: {nivel}"
        )

        if is_valid:
            self.setWindowTitle(STR.REG_TITLE)
            days = info.get("days_remaining", 0)
            self._info_labels.set_config(
                {
                    "status": {
                        "text": f"{STR.STATUS}: {STR.ACTIVE} ({days} {STR.REMAINING_DAYS})",
                        "color": "green",
                    }
                }
            )
        else:
            self.setWindowTitle("")
            if not has_key:
                self._info_labels.set_config(
                    {
                        "status": {
                            "text": f"{STR.STATUS}: {STR.INACTIVE}",
                            "color": "gray",
                        }
                    }
                )
            else:
                self._info_labels.set_config(
                    {
                        "status": {
                            "text": f"{STR.STATUS}: {STR.INACTIVE}",
                            "color": "red",
                        }
                    }
                )