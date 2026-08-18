# -*- coding: utf-8 -*-
import importlib.util
from pathlib import Path

from ..core.config.LogUtils import LogUtils
from ..i18n.TranslationManager import TM
from .IconManager import IconManager as im


class HtmlInstructionsProvider:
    logger = None
    logo = ""
    author_info = """"""
    BASE_DIR = Path(__file__).parent / "instructions" / "html"

    def __init__(self, tool_key: str):
        self.logger = LogUtils(
            tool=tool_key, class_name="HtmlInstructionsProvider", level="DEBUG"
        )
        self.logger.debug(f"HtmlInstructionsProvider initialized for tool: {tool_key}")
        self.author_info = f"""
            {self.transform_h(' Autor')}
            <h2 style="color:#ffffff;">
            Matheus A.S. Martinelli
            </h2>"""
        self.logo = f"{self._get_image(im.CADMUS_PNG, width=80)}"
        self.locale = TM.locale
        self.instructions = self._load_instructions()

    def _get_image(self, image_name: str, width: int = 100) -> str:
        path = im.icon_path(image_name)
        return f'<img src="{path}" alt="Cadmus Logo" width="{width}" style="display:block;margin-left:auto;margin-right:auto;align:center;">'

    def _normalize_locale(self):
        if self.locale == "en":
            return "en"
        if self.locale == "es":
            return "es"
        return "pt_BR"

    def _load_module(self, suffix: str):
        module_path = self.BASE_DIR / f"HtmlInstructions_{suffix}.py"
        spec = importlib.util.spec_from_file_location(
            f"cadmus_html_instructions_{suffix}", module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _load_instructions(self):
        suffix = self._normalize_locale()
        try:
            module = self._load_module(suffix)
            return module.HtmlInstructions(self)
        except Exception as e:
            self.logger.warning(f"Falha ao carregar HTML locale {suffix}: {e}")
            module = self._load_module("pt_BR")
            return module.HtmlInstructions(self)

    def get_instructions(self, tool_key: str) -> str:
        """
        Retorna as instruções HTML do algoritmo resolvido pela tool_key.

        Busca o método `get_<tool_key>_help` no módulo do locale carregado.
        Se nenhum método for encontrado, retorna mensagem genérica.
        """
        method_name = f"get_{tool_key}_help"
        method = getattr(self.instructions, method_name, None)
        if method is not None:
            self.logger.debug(f"Encontrado método de instruções: {method_name}")
            return method()
        self.logger.warning(
            f"Método de instruções não encontrado para tool_key: {tool_key}"
        )
        return "Instruções não disponíveis para este algoritmo."

    def transform_h(self, text="", level=2):
        return f'<h{level} style="color:#ffffff;">{text}</h{level}>'

    def transform_alert(self, text=""):
        return f'<h3 style="background-color:#ffcccc;color:#990000;padding:10px;border-radius:5px;margin:10px 0;">⚠️{text}</h3>'
