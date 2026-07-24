# -*- coding: utf-8 -*-
"""
TextBrowser — QTextBrowser com AppStyles.text_browser().
Widget raiz (sem versão grid) — usado diretamente pelo InfoDialog.

Características:
- Renderização Markdown nativa (setMarkdown) com fallback Qt5/Qt6
- Links externos abrem no navegador padrão
- Read-only por padrão
"""

from qgis.PyQt.QtWidgets import QTextBrowser
from ..styles.AppStyles import AppStyles


class TextBrowser(QTextBrowser):
    """
    QTextBrowser com estilo AppStyles.text_browser().

    Parâmetros
    ----------
    open_external_links : bool, optional
        Abrir links externos no navegador (padrão True).
    read_only : bool, optional
        Read-only (padrão True).
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        open_external_links: bool = True,
        read_only: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.setOpenExternalLinks(open_external_links)
        self.setReadOnly(read_only)
        self._apply_styles()

    def _apply_styles(self):
        """Aplica estilos globais de text browser."""
        combined = self._get_global_style() + self._specific_style()
        self.setStyleSheet(combined)

    def _get_global_style(self) -> str:
        return AppStyles.text_browser()

    def _specific_style(self) -> str:
        return ""

    def set_markdown(self, text: str) -> None:
        """
        Define conteudo Markdown com fallback Qt5/Qt6.

        Usa setMarkdown se disponivel (Qt >= 5.14),
        caso contrario converte para HTML.
        """
        doc = self.document()
        if hasattr(doc, "setMarkdown"):
            doc.setMarkdown(text)
        else:
            html = self._markdown_to_html(text)
            self.setHtml(html)

    @staticmethod
    def _markdown_to_html(text: str) -> str:
        """
        Conversao simples de Markdown para HTML.
        Compativel com QGIS 3.16 (sem setMarkdown).
        """
        import re

        html = text

        # Titulos
        html = re.sub(r"^###### (.*)", r"<h6>\1</h6>", html, flags=re.MULTILINE)
        html = re.sub(r"^##### (.*)", r"<h5>\1</h5>", html, flags=re.MULTILINE)
        html = re.sub(r"^#### (.*)", r"<h4>\1</h4>", html, flags=re.MULTILINE)
        html = re.sub(r"^### (.*)", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.*)", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.*)", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        # Negrito
        html = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", html)

        # Italico
        html = re.sub(r"\*(.*?)\*", r"<i>\1</i>", html)

        # Quebra de linha
        html = html.replace("\n", "<br>")

        return f"<html><body>{html}</body></html>"