# -*- coding: utf-8 -*-
import os

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterBand,
    QgsProcessingMultiStepFeedback,
    QgsProcessing,
)
import processing

from ..core.config.LogUtils import LogUtils
from ..i18n.TranslationManager import STR
from ..utils.ToolKeys import ToolKey
from .BaseProcessingAlgorithm import BaseProcessingAlgorithm


class GliCalculator(BaseProcessingAlgorithm):
    """
    QgsProcessingAlgorithm: Calcula o GLI (Green Leaf Index)
    a partir de um mosaico RGB ou RGBA (3 ou 4 bandas).
    GLI = (2*G - R - B) / (2*G + R + B)

    Fluxo:
      [Opcional] Step 0: gdal:warpreproject (reamostragem)
      Step 1: gdal:translate (extrai so as 3 bandas RGB, descarta alpha)
      Step 2: gdal:rastercalculator (calculo GLI com Float32)
      Step 3: native:setlayerstyle (aplica QML pseudocolor)
    """

    TOOL_KEY = ToolKey.GLI_CALCULATOR
    ALGORITHM_NAME = "gli_calculator"
    ALGORITHM_DISPLAY_NAME = STR.GLI_CALCULATOR_TITLE
    ALGORITHM_GROUP = BaseProcessingAlgorithm.GROUP_RASTER
    ICON = "cadmus_icon.ico"
    INSTRUCTIONS_FILE = "gli_calculator.html"
    logger = LogUtils(tool=TOOL_KEY, class_name="GliCalculator", level="DEBUG")

    INPUT_RASTER = "INPUT_RASTER"
    BAND_RED = "BAND_RED"
    BAND_GREEN = "BAND_GREEN"
    BAND_BLUE = "BAND_BLUE"
    TARGET_RESOLUTION = "TARGET_RESOLUTION"
    OUTPUT = "OUTPUT"
    DISPLAY_HELP = BaseProcessingAlgorithm.PARAM_DISPLAY_HELP
    OPEN_OUTPUT_FOLDER = BaseProcessingAlgorithm.PARAM_OPEN_OUTPUT_FOLDER

    _STYLE_FILENAME = "gli_pseudocolor.qml"

    @staticmethod
    def _build_gli_qml_path() -> str:
        """Retorna o caminho completo para o arquivo QML do estilo GLI."""
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        style_dir = os.path.join(plugin_dir, "resources", "styles", "qml")
        os.makedirs(style_dir, exist_ok=True)
        return os.path.join(style_dir, GliCalculator._STYLE_FILENAME)

    @staticmethod
    def _generate_gli_qml(qml_path: str) -> bool:
        """
        Gera um arquivo QML de estilo pseudocolor para o GLI (-1 a 1)
        com rampa de cores: marrom -> laranja -> amarelo -> verde claro -> verde escuro.
        """
        try:
            import xml.etree.ElementTree as ET

            root = ET.Element("qgis", {
                "version": "3.34.12-Prizren",
                "styleCategories": "AllStyleCategories",
                "maxScale": "0",
                "hasScaleBasedVisibilityFlag": "0",
                "minScale": "1e+08",
                "autoRefreshMode": "Disabled",
                "autoRefreshTime": "0",
            })

            flags = ET.SubElement(root, "flags")
            ET.SubElement(flags, "Identifiable").text = "1"
            ET.SubElement(flags, "Removable").text = "1"
            ET.SubElement(flags, "Searchable").text = "1"
            ET.SubElement(flags, "Private").text = "0"

            temporal = ET.SubElement(root, "temporal", {
                "fetchMode": "0", "enabled": "0", "mode": "0"
            })
            fixed_range = ET.SubElement(temporal, "fixedRange")
            ET.SubElement(fixed_range, "start")
            ET.SubElement(fixed_range, "end")

            ET.SubElement(root, "elevation", {
                "zoffset": "0", "symbology": "Line", "enabled": "0",
                "band": "1", "zscale": "1"
            })

            pipe = ET.SubElement(root, "pipe")

            provider = ET.SubElement(pipe, "provider")
            ET.SubElement(provider, "resampling", {
                "zoomedOutResamplingMethod": "nearestNeighbour",
                "enabled": "false",
                "maxOversampling": "2",
                "zoomedInResamplingMethod": "nearestNeighbour",
            })

            renderer = ET.SubElement(pipe, "rasterrenderer", {
                "alphaBand": "-1",
                "blueBand": "-1",
                "type": "singlebandpseudocolor",
                "greenBand": "-1",
                "nodataColor": "",
                "band": "1",
                "redBand": "-1",
                "opacity": "1.0",
                "classificationMin": "-1",
                "classificationMax": "1",
            })

            ET.SubElement(renderer, "rasterTransparency")

            min_max = ET.SubElement(renderer, "minMaxOrigin")
            ET.SubElement(min_max, "limits").text = "None"
            ET.SubElement(min_max, "extent").text = "WholeRaster"
            ET.SubElement(min_max, "statAccuracy").text = "Estimated"
            ET.SubElement(min_max, "cumulativeCutLower").text = "0.02"
            ET.SubElement(min_max, "cumulativeCutUpper").text = "0.98"
            ET.SubElement(min_max, "stdDevFactor").text = "2"

            items = [
                ("-1.000000", "#8B4513", "-1.000000"),
                ("-0.500000", "#D2691E", "-0.500000"),
                ("-0.200000", "#EDC848", "-0.200000"),
                ("0.000000", "#FFFF00", "0.000000"),
                ("0.200000", "#ADFF2F", "0.200000"),
                ("0.400000", "#7CFC00", "0.400000"),
                ("0.600000", "#32CD32", "0.600000"),
                ("0.800000", "#228B22", "0.800000"),
                ("1.000000", "#006400", "1.000000"),
            ]

            color_palette = ET.SubElement(renderer, "colorPalette")
            for value, color, label in items:
                ET.SubElement(color_palette, "paletteEntry", {
                    "value": value,
                    "color": color,
                    "label": label,
                    "alpha": "255",
                })

            ce = ET.SubElement(renderer, "contrastEnhancement")
            ET.SubElement(ce, "minValue").text = "-1.0000000"
            ET.SubElement(ce, "maxValue").text = "1.0000000"
            ET.SubElement(ce, "algorithm").text = "StretchToMinimumMaximum"

            ET.SubElement(pipe, "brightnesscontrast", {
                "brightness": "0", "gamma": "1", "contrast": "0",
            })

            ET.SubElement(pipe, "huesaturation", {
                "colorizeGreen": "128", "grayscaleMode": "0",
                "invertColors": "0", "colorizeStrength": "100",
                "colorizeBlue": "128", "colorizeRed": "255",
                "saturation": "0", "colorizeOn": "0",
            })

            ET.SubElement(pipe, "rasterresampler", {"maxOversampling": "2"})
            ET.SubElement(pipe, "resamplingStage").text = "resamplingFilter"
            ET.SubElement(root, "blendMode").text = "0"

            from ..utils.XmlUtil import XmlUtil
            return XmlUtil.save_qml_style(root, qml_path)

        except Exception as e:
            GliCalculator.logger.warning(f"Falha ao gerar QML GLI: {e}")
            return False

    def initAlgorithm(self, config=None):
        self.logger.debug("Inicializando algoritmo GliCalculator...")
        self.load_preferences()

        self.addParameter(
            QgsProcessingParameterRasterLayer(self.INPUT_RASTER, STR.INPUT_RASTER_RGB_GLI)
        )

        self.addParameter(
            QgsProcessingParameterBand(
                self.BAND_RED,
                "Banda R (Red)",
                parentLayerParameterName=self.INPUT_RASTER,
                defaultValue=self.prefs.get("band_red", 1),
            )
        )

        self.addParameter(
            QgsProcessingParameterBand(
                self.BAND_GREEN,
                "Banda G (Green)",
                parentLayerParameterName=self.INPUT_RASTER,
                defaultValue=self.prefs.get("band_green", 2),
            )
        )

        self.addParameter(
            QgsProcessingParameterBand(
                self.BAND_BLUE,
                "Banda B (Blue)",
                parentLayerParameterName=self.INPUT_RASTER,
                defaultValue=self.prefs.get("band_blue", 3),
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.TARGET_RESOLUTION,
                "Reamostragem (resolucao alvo em metros, 0=original)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=self.prefs.get("target_resolution", 0.0),
                minValue=0.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT, STR.GLI)
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.OPEN_OUTPUT_FOLDER,
                self.PARAM_OPEN_OUTPUT_FOLDER_LABEL,
                defaultValue=self.prefs.get("open_output_folder", True),
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DISPLAY_HELP,
                self.PARAM_DISPLAY_HELP_LABEL,
                defaultValue=self.prefs.get("display_help", True),
            )
        )

    def processAlgorithm(self, params, context, feedback):
        self.logger.debug("Iniciando processAlgorithm do GliCalculator...")

        try:
            # --- Leitura dos parametros ---
            raster = self.parameterAsRasterLayer(params, self.INPUT_RASTER, context)
            if not raster or not raster.isValid():
                raise QgsProcessingException("Raster RGB invalido ou nao encontrado.")

            band_red = self.parameterAsInt(params, self.BAND_RED, context)
            band_green = self.parameterAsInt(params, self.BAND_GREEN, context)
            band_blue = self.parameterAsInt(params, self.BAND_BLUE, context)
            target_res = self.parameterAsDouble(params, self.TARGET_RESOLUTION, context)
            open_output_folder = self.parameterAsBool(params, self.OPEN_OUTPUT_FOLDER, context)
            display_help = self.parameterAsBool(params, self.DISPLAY_HELP, context)
            output_path = self.parameterAsOutputLayer(params, self.OUTPUT, context)

            needs_resample = target_res > 0.0

            # steps: warp(0), translate_rgb(1), calculator(2), setlayerstyle(3)
            steps = 4 if needs_resample else 3
            multi_feedback = QgsProcessingMultiStepFeedback(steps, feedback)

            # --- Banner inicial ---
            self._push_banner(feedback, "CALCULADORA GLI - CADMUS")
            feedback.pushInfo("")
            feedback.pushInfo("Formula: GLI = (2*G - R - B) / (2*G + R + B)")
            feedback.pushInfo("")
            self._push_info_line(feedback, "Raster de entrada", raster.source())
            self._push_info_line(feedback, "Banda R (Red)", str(band_red))
            self._push_info_line(feedback, "Banda G (Green)", str(band_green))
            self._push_info_line(feedback, "Banda B (Blue)", str(band_blue))
            if needs_resample:
                self._push_info_line(feedback, "Resolucao alvo", f"{target_res}m")
            else:
                feedback.pushInfo("Resolucao alvo: original (sem reamostragem)")
            self._push_info_line(feedback, "Output", output_path)
            feedback.pushInfo("")

            step_index = 0

            # ===================================================================
            # STEP 0 (opcional): Reamostragem via gdal:warpreproject
            # ===================================================================
            working_raster = raster.source()
            import tempfile
            temp_dir = tempfile.gettempdir()

            if needs_resample:
                multi_feedback.setCurrentStep(step_index)
                if multi_feedback.isCanceled():
                    return {}

                feedback.pushInfo(f"[Step {step_index + 1}/{steps}] Reamostrando para {target_res}m...")

                resampled_path = os.path.join(
                    temp_dir,
                    f"gli_resampled_{os.path.basename(raster.source())}"
                )

                warp_params = {
                    'INPUT': raster.source(),
                    'SOURCE_CRS': None,
                    'TARGET_CRS': None,
                    'RESAMPLING': 0,
                    'NODATA': None,
                    'TARGET_RESOLUTION': target_res,
                    'OPTIONS': '',
                    'DATA_TYPE': 0,
                    'TARGET_EXTENT': None,
                    'TARGET_EXTENT_CRS': None,
                    'MULTITHREADING': True,
                    'OUTPUT': resampled_path,
                }
                self.logger.debug(f"Reamostrando raster para resolucao {target_res}m...")
                warp_result = processing.run(
                    'gdal:warpreproject',
                    warp_params,
                    context=context,
                    feedback=multi_feedback,
                    is_child_algorithm=True,
                )
                working_raster = warp_result.get('OUTPUT', resampled_path)
                feedback.pushInfo(f"Raster reamostrado: {working_raster}")
                feedback.pushInfo("")
                step_index += 1

            # ===================================================================
            # STEP 1: Extrair so as 3 bandas RGB (gdal:translate)
            #   Descarta banda alpha (banda 4) se existir
            # ===================================================================
            multi_feedback.setCurrentStep(step_index)
            if multi_feedback.isCanceled():
                return {}

            feedback.pushInfo(f"[Step {step_index + 1}/{steps}] Extraindo bandas RGB (descartando alpha)...")

            rgb_path = os.path.join(temp_dir, f"gli_rgb_{os.path.basename(working_raster)}")

            # Pega o numero de bandas do raster de trabalho
            from osgeo import gdal
            ds = gdal.Open(working_raster, gdal.GA_ReadOnly)
            n_bands = ds.RasterCount if ds else 3
            ds = None

            # Se tem mais de 3 bandas (ex: RGBA), extrai so as 3 primeiras
            if n_bands > 3:
                band_list = [1, 2, 3]
                band_str = ",".join(str(b) for b in band_list)
                feedback.pushInfo(f"Raster tem {n_bands} bandas. Extraindo bandas {band_str} (RGB)...")

                translate_params = {
                    'INPUT': working_raster,
                    'TARGET_CRS': None,
                    'NODATA': None,
                    'COPY_SUBDATASETS': False,
                    'OPTIONS': '',
                    'EXTRA': f'-b 1 -b 2 -b 3',
                    'DATA_TYPE': 0,
                    'TARGET_EXTENT': None,
                    'TARGET_EXTENT_CRS': None,
                    'OUTPUT': rgb_path,
                }
                translate_result = processing.run(
                    'gdal:translate',
                    translate_params,
                    context=context,
                    feedback=multi_feedback,
                    is_child_algorithm=True,
                )
                working_raster = translate_result.get('OUTPUT', rgb_path)
                feedback.pushInfo(f"Raster RGB puro (3 bandas): {working_raster}")
            else:
                feedback.pushInfo(f"Raster ja tem {n_bands} bandas (RGB puro). Sem alpha para descartar.")

            feedback.pushInfo("")
            step_index += 1

            # ===================================================================
            # STEP 2: Calcular GLI via gdal:rastercalculator
            # ===================================================================
            multi_feedback.setCurrentStep(step_index)
            if multi_feedback.isCanceled():
                return {}

            feedback.pushInfo(f"[Step {step_index + 1}/{steps}] Calculando GLI via gdal:rastercalculator...")

            calc_params = {
                'INPUT_A': working_raster,
                'BAND_A': 1,
                'INPUT_B': working_raster,
                'BAND_B': 2,
                'INPUT_C': working_raster,
                'BAND_C': 3,
                'INPUT_D': None,
                'BAND_D': None,
                'INPUT_E': None,
                'BAND_E': None,
                'INPUT_F': None,
                'BAND_F': None,
                'FORMULA': '(B*2.0 - A - C) / (B*2.0 + A + C + 1e-10) * (abs(B*2.0 + A + C) > 1e-10)',
                'NO_DATA': None,
                'RTYPE': 5,  # Float32
                'EXTENT_OPT': 0,
                'PROJWIN': None,
                'OPTIONS': '',
                'EXTRA': '',
                'OUTPUT': output_path,
            }

            self.logger.debug("Executando gdal:rastercalculator para GLI...")
            calc_result = processing.run(
                'gdal:rastercalculator',
                calc_params,
                context=context,
                feedback=multi_feedback,
                is_child_algorithm=True,
            )

            calc_output = calc_result.get('OUTPUT', output_path)
            feedback.pushInfo("GLI calculado com sucesso!")
            feedback.pushInfo("")
            step_index += 1

            # --- Exibe interpretacao ---
            for line in STR.GLI_INTERPRETATION.split("\n"):
                feedback.pushInfo(line)
            feedback.pushInfo("")

            # ===================================================================
            # STEP 3: Aplicar estilo QML via native:setlayerstyle
            # ===================================================================
            multi_feedback.setCurrentStep(step_index)
            if multi_feedback.isCanceled():
                return {}

            feedback.pushInfo(f"[Step {step_index + 1}/{steps}] Gerando e aplicando estilo QML GLI...")

            qml_path = self._build_gli_qml_path()

            if not os.path.exists(qml_path):
                self.logger.debug(f"Gerando arquivo de estilo QML: {qml_path}")
                self._generate_gli_qml(qml_path)
                feedback.pushInfo(f"Arquivo QML gerado em: {qml_path}")
            else:
                feedback.pushInfo(f"Usando QML existente: {qml_path}")

            if qml_path and os.path.exists(qml_path) and os.path.exists(calc_output):
                style_params = {
                    'INPUT': calc_output,
                    'STYLE': qml_path,
                }
                self.logger.debug("Aplicando estilo QML via native:setlayerstyle...")
                processing.run(
                    'native:setlayerstyle',
                    style_params,
                    context=context,
                    feedback=multi_feedback,
                    is_child_algorithm=True,
                )
                feedback.pushInfo("Estilo QML GLI aplicado com sucesso!")

            feedback.pushInfo("")

            # --- Salva o caminho do QML nas preferencias ---
            self.prefs.update({
                "band_red": band_red,
                "band_green": band_green,
                "band_blue": band_blue,
                "target_resolution": target_res,
                "open_output_folder": open_output_folder,
                "display_help": display_help,
                "last_gli_style_path": qml_path,
            })
            self.save_preferences()

            # --- Abre pasta se solicitado ---
            if output_path and isinstance(output_path, str) and not output_path.startswith("memory:"):
                out_folder = os.path.dirname(output_path)
                if out_folder and open_output_folder:
                    self.open_folder_in_explorer(out_folder)

            feedback.pushInfo("Processamento concluido com sucesso.")
            self.logger.info("Processamento GLI concluido com sucesso.")
            return {self.OUTPUT: output_path}

        except QgsProcessingException:
            raise
        except Exception as e:
            msg = f"Erro nao tratado em processAlgorithm: {e}"
            self.logger.error(msg)
            raise QgsProcessingException(msg)