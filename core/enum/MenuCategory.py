from enum import Enum


class MenuCategory(str, Enum):
    SYSTEM = "SYSTEM"
    LAYOUTS = "LAYOUTS"
    FOLDER = "FOLDER"
    VECTOR = "VECTOR"
    AGRICULTURE = "AGRICULTURE"
    RASTER = "RASTER"
    DEVELOPER = "DEVELOPER"