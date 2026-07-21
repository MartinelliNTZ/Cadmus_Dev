# -*- coding: utf-8 -*-
"""
BaseTheme — Classe base abstrata para todos os temas
======================================================
Define o contrato mínimo de tokens visuais que cada tema deve implementar.
Qualquer tema concreto (CoffeTheme, DarkCharcoalTheme, etc.) deve herdar
desta classe e sobrescrever todos os atributos.

Uso:
    class MeuTema(BaseTheme):
        COLOR_PRIMARY = "#ff6600"
        ...
"""

from __future__ import annotations


class BaseTheme:
    """
    Classe base para temas visuais.
    Contém todos os tokens que um tema deve definir.
    Os valores aqui são placeholders — temas concretos devem sobrescrevê-los.
    """

    # ════════════════════════════════════════════════════════════
    # UTILITÁRIO DE COR
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def rgba(hex_color: str, alpha: int) -> str:
        """
        Converte HEX + alpha para rgba().
        Exemplo:
        rgba("#a6784f", 120) -> "rgba(166,120,79,120)"
        """
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

  