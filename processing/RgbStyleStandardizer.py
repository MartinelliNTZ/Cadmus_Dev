# -*- coding: utf-8 -*-
import os

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
)

from ..core.config.LogUtils import LogUtils
from ..i18n.TranslationManager import STR
from ..utils.ToolKeys import ToolKey
from ..utils.raster.RasterLayerMetrics import RasterLayerMetrics
from ..utils.raster.RasterLayerRendering import RasterLayerRendering
from ..utils.XmlUtil import XmlUtil
from .BaseProcessingAlgorithm import BaseProcessingAlgorithm


class RgbStyleStandardizer(BaseProcessingAlgorithm):
    """
    QgsProcessingAlgorithm: Padroniza o estilo de visualizacao de um
    raster RGB (multibanda) usando percentis 2%-98% para calcular
    o contraste de cada banda, gera um estilo QML sidecar e aplica
    diretamente na camada de entrada.

    Nao gera um novo raster, apenas ajusta o estilo da camada atual.
    Equivalente as fases 6.1 e 6.2 do RgbMosaicCreator.
    """

    TOOL_KEY = ToolKey.RGB_STYLE_STANDARDIZER
    ALGORITHM_NAME = "rgb_style_standardizer"
    ALGORITHM_DISPLAY_NAME = STR.RGB_STYLE_STANDARDIZER_TITLE
    ALGORITHM_GROUP = BaseProcessingAlgorithm.GROUP_RASTER
    ICON = "cadmus_icon.ico"
    INSTRUCTIONS_FILE = "rgb_style_standardizer.html"
    logger = LogUtils(tool=TOOL_KEY, class_name="RgbStyleStandardizer", level="DEBUG")

    INPUT_RASTER = "INPUT_RASTER"
    BAND_R = "BAND_R"
    BAND_G = "BAND_G"
    BAND_B = "BAND_B"
    BAND_ALPHA = "BAND_ALPHA"
    LOWER_PCT = "LOWER_PCT"
    UPPER_PCT = "UPPER_PCT"
    DISPLAY_HELP = BaseProcessingAlgorithm.PARAM_DISPLAY_HELP

    def initAlgorithm(self, config=None):
        self.logger.debug("Inicializando algoritmo RgbStyleStandardizer...")
        self.load_preferences()

        self.addParameter(
            QgsProcessingParameterRasterLayer(self.INPUT_RASTER, STR.INPUT_RASTER_RGB)
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.LOWER_PCT,
                "Percentil inferior (%)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=self.prefs.get("lower_pct", 2.0),
                minValue=0.0,
                maxValue=50.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.UPPER_PCT,
                "Percentil superior (%)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=self.prefs.get("upper_pct", 98.0),
                minValue=50.0,
                maxValue=100.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DISPLAY_HELP,
                self.PARAM_DISPLAY_HELP_LABEL,
                defaultValue=self.prefs.get("display_help", True),
            )
        )

        self.logger.debug("Iniciando processAlgorithm do RgbStyleStandardizer...")

        try:
            raster = self.parameterAsRasterLayer(params, self.INPUT_RASTER, context)
            if not raster or not raster.isValid():
                raise QgsProcessingException("Raster RGB invalido ou nao encontrado.")

            band_r = self.parameterAsInt(params, self.BAND_R, context)
            band_g = self.parameterAsInt(params, self.BAND_G, context)
            band_b = self.parameterAsInt(params, self.BAND_B, context)
            band_alpha = self.parameterAsInt(params, self.BAND_ALPHA, context)
            lower_pct = self.parameterAsDouble(params, self.LOWER_PCT, context)
            upper_pct = self.parameterAsDouble(params, self.UPPER_PCT, context)

            display_help = self.parameterAsBool(params, self.DISPLAY_HELP, context)

            raster_path = raster.source()

            # --- Banner inicial ---
            self._push_banner(feedback, "PADRONIZADOR DE ESTILO RGB - CADMUS")
            self._push_info_line(feedback, "Raster", raster_path)
            self._push_info_line(feedback, "Bandas R/G/B", f"{band_r} / {band_g} / {band_b}")
            self._push_info_line(feedback, "Banda Alpha", str(band_alpha))
            self._push_info_line(feedback, "Percentis", f"{lower_pct}% - {upper_pct}%")
            feedback.pushInfo("")

            # --- FASE 1: Calcular percentis de cada banda ---
            feedback.pushInfo("--- FASE 1: Calculando percentis das bandas ---")
            feedback.pushInfo(f"Percentis: {lower_pct}% a {upper_pct}%")

            def calc_band_percentiles(raster_path, band_index):
                p_low, p_high = RasterLayerMetrics.get_band_percentiles(
                    raster_path, band_index, lower_pct, upper_pct, tool_key=self.TOOL_KEY
                )
                feedback.pushInfo(
                    f"  Banda {band_index}: P{lower_pct:.0f}={p_low:.7f}  P{upper_pct:.0f}={p_high:.7f}"
                )
                return p_low, p_high

            p_low_r, p_high_r = calc_band_percentiles(raster_path, band_r)
            p_low_g, p_high_g = calc_band_percentiles(raster_path, band_g)
            p_low_b, p_high_b = calc_band_percentiles(raster_path, band_b)

            # Calcula min/max global entre as 3 bandas (para contraste unificado)
            global_min = min(p_low_r, p_low_g, p_low_b)
            global_max = max(p_high_r, p_high_g, p_high_b)
            feedback.pushInfo(
                f"Global min={global_min:.7f}  Global max={global_max:.7f}"
            )

            # --- FASE 2: Gerar estilo QML sidecar ---
            feedback.pushInfo("--- FASE 2: Gerando estilo QML ---")
            qml_root = XmlUtil.build_raster_multiband_qml(
                min_value=global_min,
                max_value=global_max,
                red_band=1,
                green_band=2,
                blue_band=3,
                alpha_band=band_alpha,
                opacity=1.0,
                algorithm="StretchToMinimumMaximum",
            )

            # Salva QML sidecar (mesma pasta do raster de entrada)
            qml_path = RasterLayerRendering.save_sidecar_style(
                raster_path, qml_root, tool_key=self.TOOL_KEY
            )
            if qml_path:
                feedback.pushInfo(f"[OK] Estilo QML salvo como sidecar: {qml_path}")
            else:
                feedback.pushInfo("[ERRO] Falha ao salvar estilo QML sidecar")

            # Backup QML em temp/styles
            output_base = os.path.splitext(os.path.basename(raster_path))[0]
            backup_path = RasterLayerRendering.save_qml_backup(
                qml_root, output_base, tool_key=self.TOOL_KEY
            )
            if backup_path:
                feedback.pushInfo(f"[BACKUP] Estilo salvo em temp/styles: {backup_path}")

            # --- FASE 3: Aplicar estilo diretamente na camada de entrada ---
            feedback.pushInfo("--- FASE 3: Aplicando estilo na camada de entrada ---")
            if qml_path and os.path.isfile(qml_path):
                style_applied = raster.loadNamedStyle(qml_path)
                if style_applied:
                    raster.triggerRepaint()
                    feedback.pushInfo("[OK] Estilo aplicado diretamente na camada de entrada com sucesso.")
                else:
                    feedback.pushInfo("[AVISO] loadNamedStyle retornou False. QML sidecar disponivel para carregamento manual.")
            else:
                feedback.pushInfo("[AVISO] Nenhum QML disponivel para aplicar estilo.")

            # --- Salvar preferencias ---
            self.prefs.update({
                "band_r": band_r,
                "band_g": band_g,
                "band_b": band_b,
                "band_alpha": band_alpha,
                "lower_pct": lower_pct,
                "upper_pct": upper_pct,
                "display_help": display_help,
            })
            self.save_preferences()

            feedback.pushInfo("Estilo padronizado com sucesso na camada atual.")
            return {}

        except QgsProcessingException:
            raise
        except ImportError as e:
            msg = f"Biblioteca necessaria nao disponivel: {e}"
            self.logger.error(msg)
            raise QgsProcessingException(msg)
        except Exception as e:
            msg = f"Erro nao tratado em processAlgorithm: {e}"
            self.logger.error(msg)
            raise QgsProcessingException(msg)