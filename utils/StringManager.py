# -*- coding: utf-8 -*-
from ..core.enum.MenuCategory import MenuCategory
from ..core.enum.OutputFieldKey import StripOutputFieldKey
from ..core.model.Field import Field
from qgis.PyQt.QtCore import QVariant


import re
from ..i18n.TranslationManager import STR
from .BaseUtil import BaseUtil


class StringManager(BaseUtil):

    DIVIDE_STRIP_FIELDS = {
        StripOutputFieldKey.SHOT_ID: Field(
            label="Shot ID",
            attribute="shot_id",
            description=STR.SHOT_ID_FIELD_DESC,
            type=QVariant.String,
            length=50,
            precision=0,
        ),
        StripOutputFieldKey.OLD_SHOT_ID: Field(
            label="Old Shot ID",
            attribute="old_shot_id",
            description=STR.OLD_SHOT_ID_FIELD_DESC,
            type=QVariant.String,
            length=50,
            precision=0,
        ),
        StripOutputFieldKey.SHOT_VALID: Field(
            label="Shot Valid",
            attribute="shot_valid",
            description=STR.SHOT_VALID_FIELD_DESC,
            type=QVariant.Int,
            length=1,
            precision=0,
        ),
        StripOutputFieldKey.SCORE: Field(
            label="Score",
            attribute="score",
            description=STR.SCORE_FIELD_DESC,
            type=QVariant.Int,
            length=10,
            precision=0,
        ),
        StripOutputFieldKey.SCORE_DIRECTION: Field(
            label="Score Direction",
            attribute="score_direction",
            description=STR.SCORE_DIRECTION_FIELD_DESC,
            type=QVariant.Int,
            length=10,
            precision=0,
        ),
        StripOutputFieldKey.SCORE_CONTINUITY: Field(
            label="Score Continuity",
            attribute="score_continuity",
            description=STR.SCORE_CONTINUITY_FIELD_DESC,
            type=QVariant.Int,
            length=10,
            precision=0,
        ),
        StripOutputFieldKey.SEG_TYPE: Field(
            label="Segment Type",
            attribute="seg_type",
            description=STR.SEGMENT_TYPE_FIELD_DESC,
            type=QVariant.String,
            length=20,
            precision=0,
        ),
        StripOutputFieldKey.AZIMUTH_INSTANT: Field(
            label="Azimuth Instant",
            attribute="azimuth_instant",
            description=STR.INSTANT_AZIMUTH_FIELD_DESC,
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        StripOutputFieldKey.AZIMUTH_MEAN: Field(
            label="Azimuth Mean",
            attribute="azimuth_mean",
            description=STR.MEAN_AZIMUTH_FIELD_DESC,
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        StripOutputFieldKey.DELTA_AZIMUTH: Field(
            label="Delta Azimuth",
            attribute="delta_azimuth",
            description=STR.AZIMUTH_DELTA_FIELD_DESC,
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        StripOutputFieldKey.DELTA_TIME: Field(
            label="Delta Time",
            attribute="delta_time",
            description=STR.TIME_DELTA_FIELD_DESC,
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        StripOutputFieldKey.DELTA_DISTANCE: Field(
            label="Delta Distance",
            attribute="delta_distance",
            description=STR.DISTANCE_DELTA_FIELD_DESC,
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        StripOutputFieldKey.VELOCITY_INSTANT: Field(
            label="Velocity Instant",
            attribute="velocity_instant",
            description=STR.INSTANT_VELOCITY_FIELD_DESC,
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        StripOutputFieldKey.AZIMUTH_PREV: Field(
            label="Azimuth Prev",
            attribute="azimuth_prev",
            description=STR.PREVIOUS_AZIMUTH_FIELD_DESC,
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        StripOutputFieldKey.AZIMUTH_NEXT: Field(
            label="Azimuth Next",
            attribute="azimuth_next",
            description=STR.NEXT_AZIMUTH_FIELD_DESC,
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        StripOutputFieldKey.DELTA_AZ_PREV: Field(
            label="Delta Azimuth Prev",
            attribute="delta_az_prev",
            description=STR.PREVIOUS_AZIMUTH_DELTA_FIELD_DESC,
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        StripOutputFieldKey.DELTA_AZ_NEXT: Field(
            label="Delta Azimuth Next",
            attribute="delta_az_next",
            description=STR.NEXT_AZIMUTH_DELTA_FIELD_DESC,
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
    }

    MENU_CATEGORIES = {
        MenuCategory.SYSTEM: STR.MENU_SYSTEM,
        MenuCategory.LAYOUTS: STR.MENU_LAYOUTS,
        MenuCategory.FOLDER: STR.MENU_FOLDER,
        MenuCategory.VECTOR: STR.MENU_VECTOR,
        MenuCategory.AGRICULTURE: STR.MENU_AGRICULTURE,
        MenuCategory.RASTER: STR.MENU_RASTER,
        MenuCategory.DEVELOPER: STR.MENU_DEVELOPER,
    }

    KML_FIELDS = [
        "descriptio",
        "timestamp",
        "begin",
        "end",
        "altitudeMo",
        "tessellate",
        "extrude",
        "visibility",
        "drawOrder",
        "icon",
    ]

    # Filtros de arquivos
    FILTER_ALL = "All files (*.*)"
    FILTER_IMAGES = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff)"
    FILTER_VECTOR = "Shapefile (*.shp);;GeoPackage (*.gpkg);;GeoJSON (*.geojson *.json);;KML (*.kml);;CSV (*.csv)"
    FILTER_QGIS_STYLE = "QML files (*.qml)"
    SHP_EXTENSIONS = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".qix"]
    VECTOR_DRIVERS = {
        ".shp": "ESRI Shapefile",
        ".gpkg": "GPKG",
        ".geojson": "GeoJSON",
        ".json": "GeoJSON",
        ".kml": "KML",
    }
    AVAILABLE_LANGUAGES = {
        "none": "🔧 " + STR.AUTO_DETECT,
        "es": "ES Español",
        "en": "EN English",
        "pt_BR": "BR Português",
        "de": "DE Deutsch",
    }
    VECTOR_EXTS = {
        ".shp",
        ".geojson",
        ".json",
        ".kml",
        ".kmz",
        ".gpx",
        ".csv",
        ".tab",
        ".las",
        ".laz",
        ".gpkg",
    }
    RASTER_EXTS = {".tif", ".tiff", ".ecw", ".jp2", ".asc"}

    DIVIDE_POINTS_STRIP_TYPES = ["Curva", "Reta", "Ambas"]

    DIVIDE_POINTS_OPERATIONAL_FIELDS = {
        "threshold_azimute_grave": {
            "title": STR.SEVERE_AZIMUTH_DEVIATION_THRESHOLD,
            "description": STR.SEVERE_AZIMUTH_DEVIATION_THRESHOLD_DESC,
            "type": "float",
            "default": 45.0,
        },
        "n_minimo_pontos": {
            "title": STR.MINIMUM_POINT_COUNT,
            "description": STR.MINIMUM_POINT_COUNT_DESC,
            "type": "int",
            "default": 20,
        },
        "max_desvio": {
            "title": STR.MAX_DEVIATION_POINTS,
            "description": STR.MAX_DEVIATION_POINTS_DESC,
            "type": "int",
            "default": 2,
        },
        "max_distance": {
            "title": STR.MAX_DISTANCE_BETWEEN_POINTS,
            "description": STR.MAX_DISTANCE_BETWEEN_POINTS_DESC,
            "type": "int",
            "default": 150,
        },
    }
    DIVIDE_POINTS_SENSITIVITY_FIELDS = {
        "janela_azimute": {
            "title": STR.AZIMUTH_MOVING_WINDOW,
            "description": STR.AZIMUTH_MOVING_WINDOW_DESC,
            "type": "int",
            "default": 10,
        },
        "threshold_azimute_leve": {
            "title": STR.LIGHT_AZIMUTH_DEVIATION_THRESHOLD,
            "description": STR.LIGHT_AZIMUTH_DEVIATION_THRESHOLD_DESC,
            "type": "float",
            "default": 20.0,
        },
        "score_minimo_quebra": {
            "title": STR.MINIMUM_BREAK_SCORE,
            "description": STR.MINIMUM_BREAK_SCORE_DESC,
            "type": "int",
            "default": 3,
        },
        "tolerancia_tempo": {
            "title": STR.TIME_TOLERANCE_MULTIPLIER,
            "description": STR.TIME_TOLERANCE_MULTIPLIER_DESC,
            "type": "float",
            "default": 3.0,
        },
        "frequencia_pontos": {
            "title": STR.EXPECTED_POINT_FREQUENCY_SECONDS,
            "description": STR.EXPECTED_POINT_FREQUENCY_SECONDS_DESC,
            "type": "int",
            "default": 1,
        },
        "largura_tiro": {
            "title": STR.EXPECTED_LATERAL_WIDTH_METERS,
            "description": STR.EXPECTED_LATERAL_WIDTH_METERS_DESC,
            "type": "float",
            "default": 20.0,
        },
    }

    @staticmethod
    def _normalize_key(key: str) -> str:
        """Normaliza nomes de chaves para snake_case consistente."""
        if key is None:
            return ""
        key = re.sub(r"(?<!^)(?=[A-Z])", "_", str(key))
        key = key.replace(" ", "_").replace("-", "_").replace("/", "_")
        key = re.sub(r"_+", "_", key).strip("_")
        return key.lower()
