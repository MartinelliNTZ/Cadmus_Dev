# -*- coding: utf-8 -*-
"""
ThemeManager — Gerenciador central de temas
=============================================
Mantém a instância única do tema ativo através do padrão Singleton.
Qualquer módulo do sistema importa `theme_manager` deste manager
para acessar cores, fontes, dimensões e espaçamentos centralizados sem
acoplar diretamente a um tema concreto.

Uso:
    from resources.styles.ThemeManager import theme_manager as tm
    bg = tm.COLOR_BACKGROUND_MAIN
    btn_h = tm.BUTTON_HEIGHT

────── COMO ADICIONAR UM NOVO TEMA ────────────────────────────────
1. Crie um arquivo .py em resources/styles/ (ex: MeuTema.py)
   com uma classe que herde de BaseTheme e sobrescreva todos os tokens.

2. Importe a classe neste arquivo.

3. Adicione a entrada no dicionário THEMES com a chave desejada:
       "meu_tema": {
           "class":       MeuTema,
           "label":       "Meu Tema",
           "description": "Descrição visual do tema",
           "author":      "Seu Nome (opcional)",
           "version":     "1.0.0 (opcional)",
       }

4. Altere o valor salvo em System > "theme" no preferences.json para
   a chave do novo tema (ex: "meu_tema").
────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Any

from .BaseTheme import BaseTheme
from .CoffeTheme import CoffeTheme


# ═══════════════════════════════════════════════════════════════
# REGISTRO DE TEMAS
# ═══════════════════════════════════════════════════════════════
# Para adicionar um novo tema:
#   1. Crie a classe em resources/styles/ herdando de BaseTheme
#   2. Importe a classe neste arquivo
#   3. Adicione a entrada neste dicionário com a chave desejada
#   4. (Opcional) Altere a preferência "theme" em System para a nova chave
# ═══════════════════════════════════════════════════════════════

THEMES: dict[str, dict[str, Any]] = {
    "base": {
        "class":       BaseTheme,
        "label":       "Base Theme",
        "description": "Tema padrão base do Cadmus.",
        "author":      "Cadmus",
        "version":     "1.0.0",
    },
}

_DEFAULT_THEME_KEY: str = "base"
__CURRENT_THEME_KEY: str | None = None


def _resolve_current_theme_key() -> str:
    """
    Lê a chave do tema ativo das preferências do sistema (System > "theme").
    Se não existir configurado, retorna o padrão _DEFAULT_THEME_KEY.
    """
    global __CURRENT_THEME_KEY
    if __CURRENT_THEME_KEY is not None:
        return __CURRENT_THEME_KEY
    try:
        from ...utils.Preferences import Preferences
        from ...utils.ToolKeys import ToolKey
        sys_prefs = Preferences.load_tool_prefs(ToolKey.SYSTEM)
        __CURRENT_THEME_KEY = sys_prefs.get("theme", _DEFAULT_THEME_KEY)
    except Exception:
        __CURRENT_THEME_KEY = _DEFAULT_THEME_KEY
    return __CURRENT_THEME_KEY


def _build_theme_instance() -> BaseTheme:
    """Constrói e retorna a instância do tema definido nas preferências."""
    key = _resolve_current_theme_key()
    entry = THEMES.get(key)
    if entry is None:
        raise KeyError(
            f"[ThemeManager] Chave de tema '{key}' "
            f"não encontrada em THEMES. "
            f"Disponíveis: {list(THEMES.keys())}"
        )
    theme_class: type[BaseTheme] = entry["class"]
    return theme_class()


class ThemeManager:
    """
    Gerenciador singleton de tema.
    Mantém uma instância única do tema ativo e expõe seus tokens como
    atributos de instância, permitindo acesso desacoplado a partir de
    qualquer módulo do sistema.
    """

    _instance: ThemeManager | None = None

    def __new__(cls) -> ThemeManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._theme = _build_theme_instance()
            cls._instance._sync_attributes()
        return cls._instance

    # ── API pública ──────────────────────────────────────────────

    @property
    def current_key(self) -> str:
        """Chave do tema ativo no momento (lida das preferências)."""
        return _resolve_current_theme_key()

    @property
    def current_info(self) -> dict[str, Any]:
        """Metadados completos do tema ativo."""
        key = self.current_key
        return dict(THEMES[key])

    @classmethod
    def available_themes(cls) -> dict[str, dict[str, Any]]:
        """Retorna o dicionário completo de temas registrados (apenas metadados)."""
        return {key: dict(meta) for key, meta in THEMES.items()}

    @property
    def theme(self) -> BaseTheme:
        """Retorna a instância do tema atual."""
        return self._theme

    def reload_theme(self) -> None:
        """Recria a instância do tema a partir da chave nas preferências."""
        global __CURRENT_THEME_KEY
        __CURRENT_THEME_KEY = None   # força releitura da preferência
        self._theme = _build_theme_instance()
        self._sync_attributes()

    # ── Atributos dinâmicos (tokens do tema) ─────────────────────

    def _sync_attributes(self) -> None:
        """
        Sincroniza todos os tokens do tema atual como atributos diretos
        do ThemeManager, permitindo acesso via:
            theme_manager.COLOR_PRIMARY  (em vez de theme_manager.theme.COLOR_PRIMARY)
        """
        for attr_name in dir(self._theme):
            # Ignora métodos, dunder e atributos internos
            if attr_name.startswith("_"):
                continue
            attr_value = getattr(self._theme, attr_name)
            if callable(attr_value):
                continue
            setattr(self, attr_name, attr_value)


# ── Singleton pré-instanciado para importação direta ──────────────
# Uso: from resources.styles.ThemeManager import theme_manager
theme_manager: ThemeManager = ThemeManager()
"""
Instância singleton do ThemeManager.
Carregada sob demanda na primeira importação.
"""