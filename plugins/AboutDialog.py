# -*- coding: utf-8 -*-
from ..core.config.LogUtils import LogUtils
from .BaseDialog import BaseDialog
from ..utils.ToolKeys import ToolKey
from ..i18n.TranslationManager import STR
from ..resources.new_widgets.grid.GridLabel import GridLabel
from ..resources.new_widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.new_widgets.grid.GridIconButton import GridIconButton
from ..resources.new_widgets.SeparatorWidget import SeparatorWidget
from ..resources.IconManager import IconManager
import webbrowser


class AboutDialog(BaseDialog):

    def __init__(self, iface):
        self.iface = iface
        try:
            super().__init__(iface.mainWindow())

            self.logger = LogUtils(
                tool=ToolKey.ABOUT_DIALOG,
                class_name=self.__class__.__name__,
                level=LogUtils.DEBUG,
            )
            self.logger.debug("Inicializando AboutDialog")

            self.setWindowTitle(STR.ABOUT_CADMUS)
            self._build_ui(
                title=STR.ABOUT_CADMUS, enable_scroll=False, minimum_size=(420, 520)
            )
            self.logger.debug("AboutDialog _build_ui concluído")

            info_text = self.tr(
                f"<b>{STR.VERSION}:</b> 3.0.0.3.2<br>"
                f"<b>{STR.UPDATED_ON}:</b> 20 / 07 / 2026<br>"
                f"<b>{STR.CREATED_ON}:</b> 9 / 12 / 2024<br>"
                f"<b>{STR.CREATOR}:</b> MTL Agricultura e Tecnologia<br>"
                f"<b>{STR.LOCATION}:</b> Palmas - Tocantins - Brasil<br>"
                '<b>Site:</b> <a href="https://github.com/MartinelliNTZ/Cadmus">github.com/MartinelliNTZ/Cadmus</a>'
            )

            # Labels via GridLabel com config dict
            self.grid_info = GridLabel(config={
                "app_name": {"text": f"<h2>{STR.APP_NAME}</h2>"},
                "info": {"text": info_text},
            }, parent=self)
            self.layout.addWidget(self.grid_info)
            self.logger.debug("Informações adicionadas via GridLabel")

            # Social icons via GridIconButton — cada item tem seu próprio callback
            self.social_buttons = GridIconButton(
                config={
                    "github": {
                        "label": "GitHub",
                        "icon": IconManager.GITHUB,
                        "callback": lambda: webbrowser.open("https://github.com/MartinelliNTZ"),
                        "description": "Visite o GitHub de Matheus Martinelli",
                    },
                    "linkedin": {
                        "label": "LinkedIn",
                        "icon": IconManager.LINKEDIN,
                        "callback": lambda: webbrowser.open("https://www.linkedin.com/in/matheus-martinelli-a82149108"),
                        "description": "Conecte-se no LinkedIn",
                    },
                    "instagram": {
                        "label": "Instagram",
                        "icon": IconManager.INSTAGRAM,
                        "callback": lambda: webbrowser.open("https://www.instagram.com/matheusmartinelli00"),
                        "description": "Siga no Instagram",
                    },
                    "email": {
                        "label": "E-mail",
                        "icon": IconManager.EMAIL,
                        "callback": lambda: webbrowser.open("mailto:martinelli.matheus11@gmail.com"),
                        "description": "Envie um e-mail",
                    },
                    "buymeacoffee": {
                        "label": "Buy Me a Coffee",
                        "icon": IconManager.BUY_ME_A_COFFEE,
                        "callback": lambda: webbrowser.open("https://buymeacoffee.com/martinelliNTZ"),
                        "description": "Apoie o desenvolvimento",
                    },
                },
                parent=self,
            )
            self.layout.addWidget(self.social_buttons)
            self.logger.debug("Ícones sociais adicionados via GridIconButton")

            # Separador antes do botão fechar
            self.layout.addWidget(SeparatorWidget())

            # Botão fechar via GridExecutionButtons
            self.action_buttons = GridExecutionButtons(
                enable_close_button=True,
                enable_info=False,
                parent=self,
            )
            self.layout.addWidget(self.action_buttons)
            self.logger.debug("Botão Fechar adicionado via GridExecutionButtons")

            self.logger.debug("AboutDialog UI construída com sucesso")
        except Exception as ex:
            if hasattr(self, "logger") and self.logger:
                self.logger.error(f"AboutDialog falhou na inicialização: {ex}")
            else:
                print(f"AboutDialog falhou na inicialização: {ex}")
            raise


def run(iface):
    dlg = AboutDialog(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg