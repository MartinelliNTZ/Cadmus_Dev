# -*- coding: utf-8 -*-
from pathlib import Path
from ..i18n.TranslationManager import TM


class InstructionsManager:
    """
    Gerencia a resolução de arquivos de instrução (.md) por tool_key e locale.

    Cadeia de resolução (fallback):
        1. resources/instructions/<locale>/<tool_key>_help.md  (locale atual)
        2. resources/instructions/pt_BR/<tool_key>_help.md     (fallback pt_BR)
        3. resources/instructions/pt_BR/standard.md            (fallback genérico)

    O locale é normalizado antes da busca (ex: en_US -> en, pt_PT -> pt_BR)
    e o cache é indexado por tool_key + locale, garantindo que uma mudança
    de idioma durante a sessão resolva corretamente o novo caminho.
    """

    BASE_DIR = Path(__file__).parent
    FALLBACK_LOCALE = "pt_BR"
    FALLBACK_FILE = "standard.md"
    # Idiomas com pasta própria de instruções
    SUPPORTED_LANGUAGES = {"en", "es", "de", "ja"}
    _cache = {}

    @classmethod
    def _normalize_locale(cls, locale: str) -> str:
        """
        Normaliza um locale para o formato esperado pelas pastas de instrução.

        Args:
            locale: Locale bruto (ex: 'en_US', 'pt-BR', 'de', 'ja').

        Returns:
            Locale normalizado (ex: 'en', 'pt_BR', 'de', 'ja').
        """
        if not locale:
            return cls.FALLBACK_LOCALE

        clean = str(locale).replace("-", "_")
        language = clean.split("_")[0]

        # Português (Brasil ou Portugal) usa a pasta pt_BR
        if language == "pt":
            return cls.FALLBACK_LOCALE

        # Locales com variante regional usam apenas o idioma (en_US -> en)
        if language in cls.SUPPORTED_LANGUAGES:
            return language

        return clean

    @classmethod
    def _build_filename(cls, tool_key: str) -> str:
        """
        Constrói o nome do arquivo de instrução a partir do tool_key.

        Args:
            tool_key: Identificador da ferramenta (ex: 'export_all_layouts').

        Returns:
            Nome do arquivo (ex: 'export_all_layouts_help.md').
        """
        return f"{tool_key.lower()}_help.md"

    @classmethod
    def _candidates(cls, tool_key: str, locale: str):
        """
        Gera a cadeia de caminhos candidatos para resolução da instrução.

        Args:
            tool_key: Identificador da ferramenta.
            locale: Locale bruto do usuário.

        Returns:
            Lista de Paths a serem testados em ordem de prioridade.
        """
        filename = cls._build_filename(tool_key)
        locale = cls._normalize_locale(locale)

        candidates = [
            cls.BASE_DIR / "instructions" / locale / filename,
            cls.BASE_DIR / "instructions" / cls.FALLBACK_LOCALE / filename,
        ]

        # Evita duplicidade quando o locale já é o fallback
        if locale == cls.FALLBACK_LOCALE:
            candidates = candidates[:1]

        return candidates

    @classmethod
    def get(cls, tool_key: str) -> str:
        """
        Resolve o caminho absoluto do arquivo de instrução do tool_key.

        Args:
            tool_key: Identificador da ferramenta.

        Returns:
            Caminho absoluto do arquivo de instrução (.md).
        """
        locale = cls._normalize_locale(TM.locale)
        cache_key = f"{tool_key}|{locale}"

        if cache_key in cls._cache:
            return cls._cache[cache_key]

        for path in cls._candidates(tool_key, locale):
            if path.exists():
                cls._cache[cache_key] = str(path)
                return cls._cache[cache_key]

        # fallback final genérico
        fallback = (
            cls.BASE_DIR
            / "instructions"
            / cls.FALLBACK_LOCALE
            / cls.FALLBACK_FILE
        )
        cls._cache[cache_key] = str(fallback)
        return cls._cache[cache_key]

    @classmethod
    def has_instructions(cls, tool_key: str, locale: str = None) -> bool:
        """
        Verifica se existe um arquivo de instrução específico para o tool_key.

        Args:
            tool_key: Identificador da ferramenta.
            locale: Locale opcional (padrão: locale atual via TM).

        Returns:
            True se existir arquivo específico no locale ou no fallback pt_BR.
        """
        locale = cls._normalize_locale(locale or TM.locale)
        return any(
            path.exists() for path in cls._candidates(tool_key, locale)[:2]
        )

    @classmethod
    def clear_cache(cls) -> None:
        """
        Limpa o cache de resolução de instruções.

        Útil após criar novos arquivos de instrução durante a sessão.
        """
        cls._cache.clear()