# -*- coding: utf-8 -*-
"""
Re-exports principais para o package `resources`.

Este arquivo expõe as classes mais usadas presentes em
`resources.widgets` e `resources.styles` para importações
como `from Cadmus.resources import AppBarWidget`.
"""


# Styles
from .styles.BaseStyles import BaseStyles
from .styles.Styles import Styles
from .styles.CoffeTheme import CoffeTheme

# Widgets
from .widgets.AppBarWidget import AppBarWidget
from .widgets.AttributeSelectorWidget import AttributeSelectorWidget
from .widgets.BottomActionButtonsWidget import BottomActionButtonsWidget
from .widgets.grid.GridCheckboxWidget import GridCheckboxWidget, DependentCheckBox
from .widgets.CollapsibleParametersWidget import CollapsibleParametersWidget
from .widgets.grid.GridInputFieldsWidget import GridInputFieldsWidget
from .widgets.LayerInputWidget import LayerInputWidget
from .widgets.MainLayout import MainLayout
from .widgets.RadioButtonGridWidget import RadioButtonGridWidget
from .widgets.ReadOnlyFieldWidget import ReadOnlyFieldWidget
from .widgets.ScrollWidget import ScrollWidget
from .widgets.simple.SelectorWidget import SelectorWidget
from .widgets.SimpleButtonWidget import SimpleButtonWidget

__all__ = [
    # styles
    "BaseStyles",
    "Styles",
    "CoffeTheme",
    # widgets
    "AppBarWidget",
    "AttributeSelectorWidget",
    "BottomActionButtonsWidget",
    "GridCheckboxWidget",
    "DependentCheckBox",
    "CollapsibleParametersWidget",
    "GridInputFieldsWidget",
    "LayerInputWidget",
    "MainLayout",
    "RadioButtonGridWidget",
    "ReadOnlyFieldWidget",
    "ScrollWidget",
    "SelectorWidget",
    "SimpleButtonWidget",
]
