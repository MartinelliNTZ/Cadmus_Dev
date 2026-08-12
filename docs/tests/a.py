
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterRasterDestination,
    QgsProcessingException,
)
from osgeo import gdal
import numpy as np


class CalculateCHM(QgsProcessingAlgorithm):
    """
    Calcula o CHM (Canopy Height Model) = max(MDS - MDT, 0).

    Garantias desta versão:
      1) Alinhamento robusto: se MDS e MDT não tiverem exatamente a mesma
         grade (linhas/colunas/extensão/resolução), o MDT é reamostrado
         com gdal.Warp forçando width/height EXATOS do MDS (parâmetros
         `width=` e `height=`, não `xRes`/`yRes`), o que elimina o
         arredondamento de 1 pixel que causava o erro
         "Dimensions of file ... are different from other files".
         Todo o cálculo é feito por leitura/escrita em blocos via GDAL/
         numpy (sem gdal_calc/VRT intermediários), então não há como a
         etapa de cálculo falhar por dimensões diferentes: os dois
         arrays lidos em cada bloco SEMPRE têm o mesmo shape.
      2) NoData de SAÍDA é sempre -9999, nunca 0 - pois no CHM o valor 0
         é um resultado válido (solo exposto / altura de vegetação
         zero) e não pode ser confundido com "sem dado". O NoData de
         ENTRADA de cada raster (MDS e MDT) é lido individualmente e
         pode ser 0, -9999, outro valor, ou não estar definido; onde
         qualquer um dos dois estiver em NoData, a saída recebe -9999.
      3) Feedback detalhado: mensagens de cada etapa, NoData detectado
         em cada entrada, e progresso percentual real durante o cálculo
         por blocos.
    """

    INPUT_MDS = "INPUT_MDS"
    INPUT_MDT = "INPUT_MDT"
    OUTPUT = "OUTPUT"

    NODATA_OUT = -9999.0
    BLOCK = 1024  # tamanho do bloco (px) para leitura/escrita em memória

    def tr(self, text):
        return QCoreApplication.translate("Processing", text)

    def createInstance(self):
        return CalculateCHM()

    def name(self):
        return "calculate_chm"

    def displayName(self):
        return self.tr("Calcular CHM (MDS - MDT)")

    def group(self):
        return self.tr("Raster")

    def groupId(self):
        return "raster"

    def shortHelpString(self):
        return self.tr(
            "Calcula o CHM (Canopy Height Model) = MDS - MDT, limitado a um mínimo de 0.\n\n"
            "- Se MDS e MDT não tiverem exatamente a mesma grade (extensão, resolução, "
            "número de linhas/colunas), o MDT é reamostrado (bilinear) para a grade "
            "EXATA do MDS antes do cálculo, eliminando erros de diferença de 1 pixel.\n"
            "- O cálculo é feito em blocos via GDAL/numpy (sem gdal_calc/VRT), garantindo "
            "que as dimensões nunca divirjam durante o processamento.\n"
            "- O NoData de SAÍDA é sempre -9999, nunca 0 (pois 0 é um valor válido de "
            "CHM - solo exposto / ausência de vegetação).\n"
            "- O NoData dos rasters de ENTRADA (MDS/MDT) é respeitado e propagado "
            "corretamente para -9999 na saída, seja qual for o valor original "
            "(0, -9999, não definido, etc.)."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterRasterLayer(self.INPUT_MDS, self.tr("Raster MDS"))
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(self.INPUT_MDT, self.tr("Raster MDT"))
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT, self.tr("Raster CHM"))
        )

    def processAlgorithm(self, parameters, context, feedback):

        mds_layer = self.parameterAsRasterLayer(parameters, self.INPUT_MDS, context)
        mdt_layer = self.parameterAsRasterLayer(parameters, self.INPUT_MDT, context)

        if mds_layer is None or mdt_layer is None:
            raise QgsProcessingException("Erro ao abrir os rasters de entrada.")

        mds_path = mds_layer.source()
        mdt_path = mdt_layer.source()

        feedback.pushInfo("Abrindo raster MDS...")
        ds_mds = gdal.Open(mds_path, gdal.GA_ReadOnly)
        if ds_mds is None:
            raise QgsProcessingException(f"Não foi possível abrir o MDS: {mds_path}")

        feedback.pushInfo("Abrindo raster MDT...")
        ds_mdt_raw = gdal.Open(mdt_path, gdal.GA_ReadOnly)
        if ds_mdt_raw is None:
            raise QgsProcessingException(f"Não foi possível abrir o MDT: {mdt_path}")

        gt_mds = ds_mds.GetGeoTransform()
        proj_mds = ds_mds.GetProjection()
        cols_mds = ds_mds.RasterXSize
        rows_mds = ds_mds.RasterYSize

        # Bounding box do MDS (xmin, ymin, xmax, ymax) a partir do geotransform
        xmin = gt_mds[0]
        ymax = gt_mds[3]
        xmax = xmin + gt_mds[1] * cols_mds
        ymin = ymax + gt_mds[5] * rows_mds

        gt_mdt = ds_mdt_raw.GetGeoTransform()
        cols_mdt = ds_mdt_raw.RasterXSize
        rows_mdt = ds_mdt_raw.RasterYSize
        proj_mdt = ds_mdt_raw.GetProjection()

        same_grid = (
            cols_mds == cols_mdt
            and rows_mds == rows_mdt
            and abs(gt_mds[0] - gt_mdt[0]) < 1e-6
            and abs(gt_mds[3] - gt_mdt[3]) < 1e-6
            and abs(gt_mds[1] - gt_mdt[1]) < 1e-9
            and abs(gt_mds[5] - gt_mdt[5]) < 1e-9
            and proj_mds == proj_mdt
        )

        if same_grid:
            feedback.pushInfo(
                f"MDS e MDT já possuem a mesma grade ({cols_mds} x {rows_mds} px). "
                f"Alinhamento não é necessário."
            )
            ds_mdt = ds_mdt_raw
        else:
            feedback.pushInfo(
                f"Grades diferentes detectadas -> MDS: {cols_mds} x {rows_mds} px | "
                f"MDT: {cols_mdt} x {rows_mdt} px. Reamostrando o MDT para a grade "
                f"EXATA do MDS (bilinear)..."
            )

            warp_options = gdal.WarpOptions(
                format="MEM",
                width=cols_mds,      # força nº exato de colunas do MDS
                height=rows_mds,     # força nº exato de linhas do MDS
                outputBounds=(xmin, ymin, xmax, ymax),
                outputBoundsSRS=proj_mds,
                dstSRS=proj_mds,
                resampleAlg=gdal.GRA_Bilinear,
                multithread=True,
            )

            ds_mdt = gdal.Warp("", mdt_path, options=warp_options)
            ds_mdt_raw = None  # dataset original não é mais necessário

            if ds_mdt is None:
                raise QgsProcessingException("Falha ao reamostrar o MDT para a grade do MDS.")

            if ds_mdt.RasterXSize != cols_mds or ds_mdt.RasterYSize != rows_mds:
                raise QgsProcessingException(
                    f"Falha no alinhamento: MDT reamostrado ficou com "
                    f"{ds_mdt.RasterXSize} x {ds_mdt.RasterYSize} px, "
                    f"esperado {cols_mds} x {rows_mds} px."
                )

            feedback.pushInfo(
                f"MDT alinhado com sucesso para {ds_mdt.RasterXSize} x {ds_mdt.RasterYSize} px."
            )

        band_mds = ds_mds.GetRasterBand(1)
        band_mdt = ds_mdt.GetRasterBand(1)

        nodata_mds = band_mds.GetNoDataValue()
        nodata_mdt = band_mdt.GetNoDataValue()

        feedback.pushInfo(
            "NoData de entrada -> MDS: "
            f"{nodata_mds if nodata_mds is not None else 'não definido'} | "
            "MDT: "
            f"{nodata_mdt if nodata_mdt is not None else 'não definido'}"
        )
        feedback.pushInfo(f"NoData de saída (fixo, independente da entrada): {self.NODATA_OUT}")

        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        driver = gdal.GetDriverByName("GTiff")
        creation_options = [
            "COMPRESS=LZW",
            "ZLEVEL=2",
            "TILED=YES",
            "BIGTIFF=IF_SAFER",
        ]

        feedback.pushInfo(f"Criando raster de saída: {output_path}")
        ds_out = driver.Create(
            output_path, cols_mds, rows_mds, 1, gdal.GDT_Float32, options=creation_options
        )
        if ds_out is None:
            raise QgsProcessingException(f"Não foi possível criar o raster de saída em '{output_path}'.")

        ds_out.SetGeoTransform(gt_mds)
        ds_out.SetProjection(proj_mds)
        band_out = ds_out.GetRasterBand(1)
        band_out.SetNoDataValue(self.NODATA_OUT)

        feedback.pushInfo("Calculando CHM em blocos (MDS - MDT, mínimo 0)...")

        block = self.BLOCK
        n_blocks_x = (cols_mds + block - 1) // block
        n_blocks_y = (rows_mds + block - 1) // block
        total_blocks = n_blocks_x * n_blocks_y
        processed = 0
        last_pct_logged = -1

        for by in range(n_blocks_y):
            y_off = by * block
            y_size = min(block, rows_mds - y_off)

            for bx in range(n_blocks_x):
                if feedback.isCanceled():
                    ds_out = None
                    raise QgsProcessingException("Processamento cancelado pelo usuário.")

                x_off = bx * block
                x_size = min(block, cols_mds - x_off)

                arr_mds = band_mds.ReadAsArray(x_off, y_off, x_size, y_size).astype(np.float32)
                arr_mdt = band_mdt.ReadAsArray(x_off, y_off, x_size, y_size).astype(np.float32)

                # Máscara de NoData considerando o valor original de CADA raster
                # (podem ser diferentes: ex. MDS sem NoData definido e MDT com 0)
                mask_nodata = np.isnan(arr_mds) | np.isnan(arr_mdt)
                if nodata_mds is not None:
                    mask_nodata |= np.isclose(arr_mds, nodata_mds, rtol=0, atol=1e-4)
                if nodata_mdt is not None:
                    mask_nodata |= np.isclose(arr_mdt, nodata_mdt, rtol=0, atol=1e-4)

                chm = np.maximum(arr_mds - arr_mdt, 0.0)
                chm[mask_nodata] = self.NODATA_OUT

                band_out.WriteArray(chm, x_off, y_off)

                processed += 1
                pct = int(100 * processed / total_blocks)
                feedback.setProgress(pct)
                if pct != last_pct_logged and pct % 10 == 0:
                    feedback.pushInfo(f"Progresso do cálculo: {pct}% ({processed}/{total_blocks} blocos)")
                    last_pct_logged = pct

        band_out.FlushCache()

        feedback.pushInfo("Calculando estatísticas da banda de saída...")
        band_out.ComputeStatistics(False)

        feedback.pushInfo("Gerando overviews internas (2, 4, 8, 16, 32, 64, 128)...")
        gdal.SetConfigOption("COMPRESS_OVERVIEW", "LZW")
        gdal.SetConfigOption("ZLEVEL_OVERVIEW", "2")
        ds_out.BuildOverviews("NEAREST", [2, 4, 8, 16, 32, 64, 128])

        ds_out.FlushCache()
        ds_out = None
        ds_mds = None
        ds_mdt = None

        feedback.pushInfo("CHM calculado com sucesso. NoData de saída = -9999; 0 = solo exposto (valor válido).")

        return {self.OUTPUT: output_path}