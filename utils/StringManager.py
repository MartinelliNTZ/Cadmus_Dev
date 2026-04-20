# -*- coding: utf-8 -*-
import re
from ..i18n.TranslationManager import STR


class StringManager:
    MENU_CATEGORIES = {
        "SYSTEM": STR.MENU_SYSTEM,
        "LAYOUTS": STR.MENU_LAYOUTS,
        "FOLDER": STR.MENU_FOLDER,
        "VECTOR": STR.MENU_VECTOR,
        "AGRICULTURE": STR.MENU_AGRICULTURE,
        "RASTER": STR.MENU_RASTER,
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

    DIVIDE_POINTS_OPERATIONAL_FIELDS = {
        "frequencia_pontos": {
            "title": STR.EXPECTED_POINT_FREQUENCY_SECONDS,
            "type": "int",
            "default": 1,
        },
        "largura_tiro": {
            "title": STR.EXPECTED_LATERAL_WIDTH_METERS,
            "type": "float",
            "default": 20.0,
        },
    }

    DIVIDE_POINTS_SENSITIVITY_FIELDS = {
        "janela_azimute": {
            "title": STR.AZIMUTH_MOVING_WINDOW,
            "description": "Numero de pontos usados para calcular a direcao media antes de detectar mudanca de rumo.",
            "type": "int",
            "default": 10,
        },
        "threshold_azimute_leve": {
            "title": STR.LIGHT_AZIMUTH_DEVIATION_THRESHOLD,
            "description": "Desvio leve de azimute que inicia a identificacao de uma possivel quebra.",
            "type": "float",
            "default": 20.0,
        },
        "threshold_azimute_grave": {
            "title": STR.SEVERE_AZIMUTH_DEVIATION_THRESHOLD,
            "description": "Desvio alto de azimute que indica uma mudanca de direcao clara.",
            "type": "float",
            "default": 45.0,
        },
        "score_minimo_quebra": {
            "title": STR.MINIMUM_BREAK_SCORE,
            "description": "Pontos necessarios para que o desvio seja considerado uma quebra real.",
            "type": "int",
            "default": 3,
        },
        "n_minimo_pontos": {
            "title": STR.MINIMUM_POINT_COUNT,
            "description": "Menor quantidade de pontos que um trecho precisa para ser aceito.",
            "type": "int",
            "default": 20,
        },
        "tolerancia_tempo": {
            "title": STR.TIME_TOLERANCE_MULTIPLIER,
            "description": "Multiplica a diferenca de tempo permitida entre fotos para evitar quebra por pequenas variacoes.",
            "type": "float",
            "default": 3.0,
        },
        "max_desvio": {
            "title": "Numero max de pontos desvio",
            "description": "Maximo de pontos fora do padrao que serao ignorados antes de confirmar a quebra.",
            "type": "int",
            "default": 5,
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
