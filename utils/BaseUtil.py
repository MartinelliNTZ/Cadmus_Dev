# -*- coding: utf-8 -*-
"""
BaseUtil — Classe base para todos os utilitários do sistema
=============================================================
Centraliza o método `_get_logger` para todas as classes em `utils/`,
garantindo logging consistente com ToolKey em todas as chamadas.

Toda classe em `utils/` DEVE herdar de `BaseUtil` e usar
`BaseUtil._get_logger(tool_key, class_name)` para obter um logger,
em vez de instanciar `LogUtils` diretamente.

Uso:
    from utils.BaseUtil import BaseUtil

    class MinhaUtil(BaseUtil):
        @staticmethod
        def meu_metodo(tool_key: str = ToolKey.UNTRACEABLE.value):
            logger = BaseUtil._get_logger(tool_key, "MinhaUtil")
            logger.info("Executando", code="EXEC")
"""

from typing import Optional

from ..core.config.LogUtils import LogUtils
from .ToolKeys import ToolKey


class BaseUtil:
    """
    Classe base para utilitários do sistema.

    Fornece:
        _get_logger(tool_key, class_name) — logger centralizado
    """

    @classmethod
    def _get_logger(cls, tool_key: str = ToolKey.UNTRACEABLE.value, class_name: Optional[str] = None) -> LogUtils:
        """
        Retorna uma instância de LogUtils para a classe e tool especificadas.

        Args:
            tool_key: Chave da ferramenta (ex: ToolKey.CONSOLE.value).
            class_name: Nome da classe (opcional; usa cls.__name__ se omitido).

        Returns:
            Instância de LogUtils configurada.
        """
        if class_name is None:
            class_name = cls.__name__
        return LogUtils(tool=tool_key, class_name=class_name)
