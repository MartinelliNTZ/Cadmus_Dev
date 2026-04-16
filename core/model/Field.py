# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Optional
from PyQt5.QtCore import QVariant

@dataclass
class Field:
    normalized: Optional[str] = None
    core: Optional[str] = None
    label: Optional[str] = None
    attribute: Optional[str] = None
    description: Optional[str] = None
    level: Optional[int] = None
    type: Optional[QVariant] = None
    length: Optional[int] = None
    precision: Optional[int] = None