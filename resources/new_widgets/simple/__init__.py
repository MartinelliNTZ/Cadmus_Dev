# -*- coding: utf-8 -*-
"""
Simple widgets — uso INTERNO apenas.
Widgets aqui TEM versão grid (em resources/new_widgets/grid/).
NUNCA importados por plugins.
"""

from .SimpleLabel import SimpleLabel
from .SimpleButton import SimpleButton
from .SimpleIconButton import SimpleIconButton

__all__ = [
    "SimpleLabel",
    "SimpleButton",
    "SimpleIconButton",
]
