# -*- coding: utf-8 -*-
import os

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
)
from osgeo import gdal
import numpy as np

from ..core.config.LogUtils import LogUtils
from ..i18n.TranslationManager import STR
from ..utils.ToolKeys import ToolKey
from .BaseProcessingAlgorithm import BaseProcessingAlgorithm


class RasterMeanAdjust(BaseProcessingAlgorithm):
    """
    Ajusta a média dos valores de um raster para um valor desejado.

    Calcula o fator = media_desejada / media_atual e multiplica todos os
    pixels válidos por esse fator. Pixels NoData são preservados.
    O processamento é feito em blocos via GDAL/numpy (sem gdal_calc),
    preservando georreferenciamento, projeção e NoData do raster original.
    """

    TOOL_KEY = ToolKey.RASTER_MEAN_ADJUST
    ALGORITHM_NAME = "raster_mean_adjust"
    ALGORITHM_DISPLAY_NAME = STR.RASTER_MEAN_ADJUST_TITLE
    ALGORITHM_GROUP = BaseProcessingAlgorithm.GROUP_RASTER
    INSTRUCTIONS_FILE = "raster_mean_adjust.html"
    logger = LogUtils(tool=TOOL_KEY, class_name="RasterMeanAdjust", level="DEBUG")

    INPUT = "INPUT"
    TARGET_MEAN = "TARGET_MEAN"
    OUTPUT = "OUTPUT"
    DISPLAY_HELP = "DISPLAY_HELP"
    OPEN_OUTPUT_FOLDER = "OPEN_OUTPUT_FOLDER"

    BLOCK = 1024  # tamanho do bloco (px) para leitura/escrita em memória

    def initAlgorithm(self, config=None):
        self.logger.debug("Inicializando algoritmo RasterMeanAdjust...")
        self.load_preferences()

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT, STR.RASTER_MEAN_ADJUST_INPUT
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.TARGET_MEAN,
                STR.RASTER_MEAN_ADJUST_TARGET_MEAN,
                type=QgsProcessingParameterNumber.Double,
                defaultValue=self.prefs.get("target_mean", 100.0),
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT, STR.RASTER_MEAN_ADJUST_OUTPUT
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.OPEN_OUTPUT_FOLDER,
                STR.OPEN_OUTPUT_FOLDER,
                defaultValue=self.prefs.get("open_output_folder", True),
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DISPLAY_HELP,
                STR.DISPLAY_HELP_FIELD,
                defaultValue=self.prefs.get("display_help", True),
            )
        )

    def processAlgorithm(self, params, context, feedback):
        self.logger.debug("Iniciando processAlgorithm...")

        try:
            raster_layer = self.parameterAsRasterLayer(params, self.INPUT, context)

            if raster_layer is None:
                msg = "Raster inválido."
                self.logger.error(msg)
                raise QgsProcessingException(msg)

            target_mean = self.parameterAsDouble(params, self.TARGET_MEAN, context)
            open_output_folder = self.parameterAsBool(
                params, self.OPEN_OUTPUT_FOLDER, context
            )
            display_help = self.parameterAsBool(params, self.DISPLAY_HELP, context)
            output_path = self.parameterAsOutputLayer(params, self.OUTPUT, context)

            raster_path = raster_layer.source()

            feedback.pushInfo(f"Abrindo raster: {raster_path}")
            ds = gdal.Open(raster_path, gdal.GA_ReadOnly)
            if ds is None:
                msg = f"Não foi possível abrir o raster: {raster_path}"
                self.logger.error(msg)
                raise QgsProcessingException(msg)

            band = ds.GetRasterBand(1)
            nodata = band.GetNoDataValue()

            feedback.pushInfo("Calculando média atual da banda 1...")
            stats = band.ComputeStatistics(False)
            current_mean = stats[2]

            feedback.pushInfo(f"Média atual: {current_mean:.6f}")
            feedback.pushInfo(f"Média desejada: {target_mean:.6f}")

            if current_mean == 0:
                msg = "Média do raster é zero. Não é possível calcular o fator de ajuste."
                self.logger.error(msg)
                raise QgsProcessingException(msg)

            factor = target_mean / current_mean
            feedback.pushInfo(f"Fator de ajuste: {factor:.6f}")

            gt = ds.GetGeoTransform()
            proj = ds.GetProjection()
            cols = ds.RasterXSize
            rows = ds.RasterYSize

            driver = gdal.GetDriverByName("GTiff")
            creation_options = [
                "COMPRESS=LZW",
                "ZLEVEL=2",
                "TILED=YES",
                "BIGTIFF=IF_SAFER",
            ]

            feedback.pushInfo(f"Criando raster de saída: {output_path}")
            ds_out = driver.Create(
                output_path, cols, rows, 1, gdal.GDT_Float32,
                options=creation_options,
            )
            if ds_out is None:
                msg = f"Não foi possível criar o raster de saída em '{output_path}'."
                self.logger.error(msg)
                raise QgsProcessingException(msg)

            ds_out.SetGeoTransform(gt)
            ds_out.SetProjection(proj)
            band_out = ds_out.GetRasterBand(1)

            if nodata is not None:
                band_out.SetNoDataValue(nodata)

            feedback.pushInfo("Ajustando média em blocos...")

            block = self.BLOCK
            n_blocks_x = (cols + block - 1) // block
            n_blocks_y = (rows + block - 1) // block
            total_blocks = n_blocks_x * n_blocks_y
            processed = 0
            last_pct_logged = -1

            for by in range(n_blocks_y):
                y_off = by * block
                y_size = min(block, rows - y_off)

                for bx in range(n_blocks_x):
                    if feedback.isCanceled():
                        ds_out = None
                        msg = "Processamento cancelado pelo usuário."
                        self.logger.warning(msg)
                        raise QgsProcessingException(msg)

                    x_off = bx * block
                    x_size = min(block, cols - x_off)

                    arr = band.ReadAsArray(
                        x_off, y_off, x_size, y_size
                    ).astype(np.float32)

                    mask_nodata = np.isnan(arr)
                    if nodata is not None:
                        mask_nodata |= np.isclose(
                            arr, nodata, rtol=0, atol=1e-4
                        )

                    arr[~mask_nodata] *= factor

                    band_out.WriteArray(arr, x_off, y_off)

                    processed += 1
                    pct = int(100 * processed / total_blocks)
                    feedback.setProgress(pct)
                    if pct != last_pct_logged and pct % 10 == 0:
                        feedback.pushInfo(
                            f"Progresso do ajuste: {pct}% "
                            f"({processed}/{total_blocks} blocos)"
                        )
                        last_pct_logged = pct

            band_out.FlushCache()

            feedback.pushInfo("Calculando estatísticas da banda de saída...")
            band_out.ComputeStatistics(False)

            feedback.pushInfo(
                "Gerando overviews internas (2, 4, 8, 16, 32, 64, 128)..."
            )
            gdal.SetConfigOption("COMPRESS_OVERVIEW", "LZW")
            gdal.SetConfigOption("ZLEVEL_OVERVIEW", "2")
            ds_out.BuildOverviews("NEAREST", [2, 4, 8, 16, 32, 64, 128])

            ds_out.FlushCache()
            ds_out = None
            ds = None

            self.prefs.update(
                {
                    "target_mean": float(target_mean),
                    "display_help": bool(display_help),
                    "open_output_folder": bool(open_output_folder),
                }
            )
            self.save_preferences()

            if output_path and isinstance(output_path, str) and not output_path.startswith("memory:"):
                out_folder = os.path.dirname(output_path)
                if out_folder:
                    feedback.pushInfo(f"Arquivo salvo em: {out_folder}")
                    if open_output_folder:
                        self.open_folder_in_explorer(out_folder)

            feedback.pushInfo(
                f"Ajuste concluído. Média do raster ajustada para {target_mean:.6f}."
            )

            return {self.OUTPUT: output_path}

        except QgsProcessingException as e:
            self.logger.error(f"Erro de processamento: {e}")
            raise
        except Exception as e:
            msg = f"Erro não tratado em processAlgorithm: {e}"
            self.logger.error(msg)
            raise QgsProcessingException(msg)


