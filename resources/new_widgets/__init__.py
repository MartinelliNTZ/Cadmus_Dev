# -*- coding: utf-8 -*-
"""
New Widgets — Novo sistema de widgets autoconfiguráveis.

Organização:
- grid/      → Widget TEM versão grid (plugins SEMPRE usam esta)
- simple/    → Widget TEM versão grid (uso INTERNO, NUNCA por plugins)
- (raiz)     → Widget SEM versão grid

Uso em plugins:
    from ..resources.new_widgets.grid.GridLabel import GridLabel
    from ..resources.new_widgets.grid.GridButton import GridButton
    from ..resources.new_widgets.SeparatorWidget import SeparatorWidget
    from ..resources.new_widgets.MainLayout import MainLayout
"""
