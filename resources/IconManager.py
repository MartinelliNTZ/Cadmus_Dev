# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtGui import QIcon


class IconManager:
    """
    Gerenciador central de ícones do plugin.
    """

    BASE_PATH = os.path.join(os.path.dirname(__file__), "icons")
    # SYSTEM
    MTL_AGRO = "mtl_agro.ico"
    MTL_AGRO_PNG = "mtl_agro.png"
    CADMUS_ICON = "cadmus_icon.ico"
    CADMUS_PNG = "cadmus_icon.png"
    COPY_BUTTON = "copy.png"

    # Menus
    AGRICULTURE = "agriculture.ico"
    LAYER = "layer.ico"
    LAYOUT = "layout.ico"
    RASTER = "raster.ico"
    SYSTEM = "system.ico"
    VECTOR = "vector.ico"

    # Actions
    EXPORT_ALL_LAYOUTS = "export_icon.ico"
    REPLACE_IN_LAYOUTS = "replace_in_layouts.ico"
    RESTART_QGIS = "restart_qgis.ico"
    LOAD_FOLDER_LAYER = "load_folder.ico"
    GENERATE_TRAIL = "gerar_rastro.ico"
    ABOUT = "about.ico"
    LOGCAT = "logcat.ico"
    SETTINGS = "settings.ico"
    COORD_CLICK_TOOL = "coord.ico"
    VECTOR_FIELD = "vector_field.ico"
    DRONE_COORDINATES = "drone_cordinates.ico"
    VECTOR_MULTPART = "vector_multpart.ico"
    COPY_ATTRIBUTES = "copy_attributes.ico"
    DIVIDE_POINTS_BY_STRIPS = "vector.ico"
    CREATE_PROJECT = "create_project.ico"
    VECTOR_TO_SVG = "vector_to_svg.ico"

    # processing
    ATTRIBUTE_STATS = "attribute_stats.ico"
    FIELD_DIFFERENCE = "field_diference.ico"
    GEOMETRY_LINE_DIFFERENCE = "line_difference.ico"
    RASTER_MASS_SAMPLER = "raster_mass_sampler.ico"
    RASTER_MASS_CLIPPER = "raster_mass_clipper.ico"

    @classmethod
    def icon(cls, name: str) -> QIcon:
        """
        Retorna um QIcon a partir do nome do arquivo.
        """
        path = os.path.join(cls.BASE_PATH, name)
        return QIcon(path)

    @classmethod
    def icon_path(cls, name: str) -> str:
        """
        Retorna o caminho completo do ícone a partir do nome do arquivo.
        """
        return os.path.join(cls.BASE_PATH, name)
