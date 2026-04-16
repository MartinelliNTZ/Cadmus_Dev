# -*- coding: utf-8 -*-
"""Utility helpers for Cadmus.

Este __init__ expõe apenas submódulos seguros que não causam
importação circular com `core.config.LogUtils`.

Não incluir módulos que importam `LogUtils` (ex.: `LayoutsUtils`,
`PDFUtils`, `ProjectUtils`, `ExplorerUtils`) para evitar ciclos durante
o carregamento do pacote.
"""

# Apenas exportar utilitários seguros (sem dependência direta de LogUtils)
from .ToolKeys import ToolKey
from .QgisMessageUtil import QgisMessageUtil
from .DependenciesManager import DependenciesManager
from .FormatUtils import FormatUtils
from .StringManager import StringManager

__all__ = [
    "ToolKey",
    "QgisMessageUtil",
    "DependenciesManager",
    "FormatUtils",
    "StringManager",
]
