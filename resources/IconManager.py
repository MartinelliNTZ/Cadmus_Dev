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
    INFO = "info.ico"
    SUGESTION = "sugest.ico"
    PROJECT = "project.ico"
    PROJECT2 = "project2.ico"
    PROJECT_FOLDER1 = "project_folder1.ico"
    PROJECT_FOLDER2 = "project_folder2.ico"
    FOLDER = "folder.ico"
    FILE1 = "file1.ico"
    FILE2 = "file2.ico"
    EXPLORER = "explorer.ico"
    CONFIG = "config.ico"
    CONFIG1 = "config1.ico"
    CONFIG2 = "config2.ico"
    CONFIG3 = "config3.ico"
    COPY2 = "copy2.ico"
    ORIGIN = "origin.ico"
    LAYER2 = "layer2.ico"
    LOCK = "lock.ico"
    UNLOCK = "unlock.ico"

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
    DIVIDE_POINTS_BY_STRIPS = "divide_points_by_strips.ico"
    CREATE_PROJECT = "create_project.ico"
    VECTOR_TO_SVG = "vector_to_svg.ico"
    PHOTO_VECTORIZATION = "photo_vectorization.ico"
    REPORT_METADATA = "report_metadata.ico"
    REMOVE_KML_FIELDS = "remove_kml_fields.ico"
    DIFFERENCE_BETWEEN_LINES = "difference_between_lines.ico"
    SAVE_TEMPORARY_LAYER = "save_temporary_layer.ico"
    PATH_EXTENSION = "path_extension_tool.ico"
    PATH_EXTENSION_DIALOG = "path_extension.ico"
    FILE_CONVERTER = "file_converter.ico"
    DEVELOPER_TEST_TOOL = "mtl_agro.ico"

    # Social icons
    GITHUB = "GithubIcon.ico"
    INSTAGRAM = "InstagramIcon.ico"
    EMAIL = "Email.ico"
    LINKEDIN = "LinkedinIcon.ico"
    BUY_ME_A_COFFEE = "BuyMeaCoffe.ico"

    # processing
    ATTRIBUTE_STATS = "attribute_stats.ico"
    FIELD_DIFFERENCE = "field_diference.ico"
    GEOMETRY_LINE_DIFFERENCE = "line_difference.ico"
    RASTER_MASS_SAMPLER = "raster_mass_sampler.ico"
    RASTER_MASS_CLIPPER = "raster_mass_clipper.ico"
    GRID_GENERATOR = "grid_generator.ico"
    RASTER_WEIGHTED_AVERAGE = "raster_weighted_average.ico"
    RASTER_OPTIMIZER = "raster_mass.ico"
    RASTER_DIFFERENCE_STATISTICS = "raster_diference_statistics.ico"
    NDVI_CALCULATOR = "ndvi_calculator.ico"
    NDRE_CALCULATOR = "ndre_calculator.ico"
    GLI_CALCULATOR = "gli_calculator.ico"
    RGB_MOSAIC_CREATOR = "rgb_mosaic_creator.ico"
    RGB_STYLE_STANDARDIZER = "rgb_style_standardizer.ico"

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

    @classmethod
    def icon_path_by_tool_key(cls, tool_key: str) -> str:
        """
        Retorna o caminho do ícone baseado na tool_key.

        Se existir '{tool_key}.ico' na pasta de ícones, retorna esse
        caminho; caso contrário, retorna o caminho do cadmus_icon.
        """
        if tool_key:
            candidate = os.path.join(cls.BASE_PATH, f"{tool_key}.ico")
            if os.path.exists(candidate):
                return candidate
        return os.path.join(cls.BASE_PATH, cls.CADMUS_ICON)

    @classmethod
    def icon_by_tool_key(cls, tool_key: str) -> QIcon:
        """
        Retorna um QIcon baseado na tool_key.

        O ícone é resolvido por `icon_path_by_tool_key`: se não existir
        '{tool_key}.ico', retorna o cadmus_icon como fallback.
        """
        return QIcon(cls.icon_path_by_tool_key(tool_key))
