# -*- coding: utf-8 -*-
"""
Helpers de compatibilidade Qt5/Qt6 para widgets do novo sistema.

Uso:
    from ..utils.qt_compat import (
        resolve_qframe_shape,
        resolve_qframe_shadow,
    )
    shape = resolve_qframe_shape("HLine")
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QFrame


def resolve_qt_enum(module, qt5_attribute_name: str, qt6_class_name: str, qt6_attribute_name: str):
    """Resolve enum Qt5 → Qt6 via try/except."""
    try:
        return getattr(getattr(module, qt6_class_name), qt6_attribute_name)
    except AttributeError:
        return getattr(module, qt5_attribute_name)


def resolve_qt_window_type(name: str):
    """Qt.WindowType.Dialog → Qt.Dialog"""
    return resolve_qt_enum(Qt, name, "WindowType", name)


def resolve_qt_widget_attribute(name: str):
    """Qt.WidgetAttribute.WA_TranslucentBackground → Qt.WA_TranslucentBackground"""
    return resolve_qt_enum(Qt, name, "WidgetAttribute", name)


def resolve_qt_alignment_flag(name: str):
    """Qt.AlignmentFlag.AlignLeft → Qt.AlignLeft"""
    return resolve_qt_enum(Qt, name, "AlignmentFlag", name)


def resolve_qframe_shape(name: str):
    """QFrame.Shape.HLine → QFrame.HLine"""
    try:
        return getattr(QFrame.Shape, name)
    except AttributeError:
        return getattr(QFrame, name)


def resolve_qframe_shadow(name: str):
    """QFrame.Shadow.Sunken → QFrame.Sunken"""
    try:
        return getattr(QFrame.Shadow, name)
    except AttributeError:
        return getattr(QFrame, name)


def resolve_qt_window_modality(name: str):
    """Qt.WindowModality.WindowModal → Qt.WindowModal"""
    return resolve_qt_enum(Qt, name, "WindowModality", name)
