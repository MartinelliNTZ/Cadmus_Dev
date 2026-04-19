# -*- coding: utf-8 -*-
from qgis.core import (
    QgsProcessing,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterBoolean,
    QgsProcessingException,
)
import processing

from ..core.config.LogUtils import LogUtils
from ..i18n.TranslationManager import STR
from ..utils.ToolKeys import ToolKey
from .BaseProcessingAlgorithm import BaseProcessingAlgorithm


class CriarGradeV1(BaseProcessingAlgorithm):
    TOOL_KEY = ToolKey.CREATE_GRID_V1
    ALGORITHM_NAME = "create_grid_v1"
    ALGORITHM_DISPLAY_NAME = STR.CREATE_GRID_V1_TITLE
    ALGORITHM_GROUP = BaseProcessingAlgorithm.GROUP_VETORIAL
    ICON = "cadmus_icon.ico"
    INSTRUCTIONS_FILE = "create_grid_v1.html"
    INPUT_LAYER = "INPUT_LAYER"
    HORIZONTAL_SPACING = "HORIZONTAL_SPACING"
    VERTICAL_SPACING = "VERTICAL_SPACING"
    GRID_TYPE = "GRID_TYPE"
    OUTPUT_GRID = "OUTPUT_GRID"
    VERBOSE_LOG = "VERBOSE_LOG"
    DISPLAY_HELP = "DISPLAY_HELP"

    logger = LogUtils(tool=TOOL_KEY, class_name="CriarGradeV1", level=LogUtils.DEBUG)

    def initAlgorithm(self, config=None):
        self.load_preferences()
        self.logger.debug(f"Preferências carregadas: {self.prefs}")
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_LAYER, STR.CREATE_GRID_INPUT_LAYER, [QgsProcessing.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.HORIZONTAL_SPACING, STR.HORIZONTAL_SPACING,
                type=QgsProcessingParameterNumber.Double, minValue=0.000001, defaultValue=15
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.VERTICAL_SPACING, STR.VERTICAL_SPACING,
                type=QgsProcessingParameterNumber.Double, minValue=0.000001, defaultValue=15
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.GRID_TYPE, STR.GRID_TYPE,
                options=['Ponto', 'Linha', 'Retângulo (Polígono)'], defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT_GRID, STR.OUTPUT_GRID)
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.VERBOSE_LOG, STR.VERBOSE_LOG,
                defaultValue=self.prefs.get("verbose_log", False)
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DISPLAY_HELP, STR.DISPLAY_HELP_FIELD,
                defaultValue=self.prefs.get("display_help", True)
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        input_layer = self.parameterAsSource(parameters, self.INPUT_LAYER, context)
        if input_layer is None:
            raise QgsProcessingException("Camada de entrada inválida")
        extent = input_layer.sourceExtent()
        h_spacing = self.parameterAsDouble(parameters, self.HORIZONTAL_SPACING, context)
        v_spacing = self.parameterAsDouble(parameters, self.VERTICAL_SPACING, context)
        grid_type = self.parameterAsEnum(parameters, self.GRID_TYPE, context)
        verbose = self.parameterAsBool(parameters, self.VERBOSE_LOG, context)
        display_help = self.parameterAsBool(parameters, self.DISPLAY_HELP, context)

        if verbose:
            self.logger.info(f"Criando grade com extent: {extent}, h_spacing: {h_spacing}, v_spacing: {v_spacing}, type: {grid_type}")

        # Criar grade usando native:creategrid
        alg_params = {
            'CRS': input_layer.sourceCrs(),
            'EXTENT': extent,
            'HOVERLAY': 0,
            'HSPACING': h_spacing,
            'TYPE': grid_type,
            'VOVERLAY': 0,
            'VSPACING': v_spacing,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        grid_result = processing.run('native:creategrid', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        # Extrair por localização
        extract_params = {
            'INPUT': grid_result['OUTPUT'],
            'INTERSECT': parameters[self.INPUT_LAYER],
            'PREDICATE': [0],  # intersects
            'OUTPUT': parameters[self.OUTPUT_GRID]
        }
        extract_result = processing.run('native:extractbylocation', extract_params, context=context, feedback=feedback, is_child_algorithm=True)

        self.prefs.update({"verbose_log": verbose, "display_help": display_help})
        self.save_preferences()
        return {self.OUTPUT_GRID: extract_result['OUTPUT']}