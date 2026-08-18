# -*- coding: utf-8 -*-
import os
import tempfile

import processing
from qgis.core import (
    QgsFeature,
    QgsGeometry,
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorLayer,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)

from ..core.config.LogUtils import LogUtils
from ..i18n.TranslationManager import STR
from ..utils.ToolKeys import ToolKey
from .BaseProcessingAlgorithm import BaseProcessingAlgorithm


class RasterMaskClipper(BaseProcessingAlgorithm):
    """
    Recorta um raster usando uma camada poligonal como máscara.

    Quando 'Separar feições' está marcado, gera um raster por feição,
    usando o campo 'name' (quando existir) para nomear os arquivos.
    Quando desmarcado, gera apenas um raster usando toda a camada.
    Suporta prefixo e sufixo personalizados na nomenclatura.
    """

    TOOL_KEY = ToolKey.RASTER_MASK_CLIPPER
    ALGORITHM_DISPLAY_NAME = STR.RASTER_MASK_CLIPPER_TITLE
    ALGORITHM_GROUP = BaseProcessingAlgorithm.GROUP_RASTER
    logger = LogUtils(tool=TOOL_KEY, class_name="RasterMaskClipper", level="DEBUG")

    INPUT_RASTER = "INPUT_RASTER"
    INPUT_MASK = "INPUT_MASK"
    OUTPUT_FOLDER = "OUTPUT_FOLDER"
    PREFIX = "PREFIX"
    SUFFIX = "SUFFIX"
    SEPARATE_FEATURES = "SEPARATE_FEATURES"
    DISPLAY_HELP = "DISPLAY_HELP"
    OPEN_OUTPUT_FOLDER = "OPEN_OUTPUT_FOLDER"

    def initAlgorithm(self, config=None):
        self.logger.debug("Inicializando algoritmo RasterMaskClipper...")
        self.load_preferences()

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_RASTER,
                STR.RASTER,
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_MASK,
                STR.INPUT_MASK_POLYGON_LAYER,
                [QgsProcessing.TypeVectorPolygon],
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_FOLDER,
                STR.OUTPUT_FOLDER,
                optional=True,
                defaultValue=self.prefs.get("last_output_folder", ""),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.PREFIX,
                STR.PREFIX,
                defaultValue="",
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.SUFFIX,
                STR.SUFFIX,
                defaultValue="",
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SEPARATE_FEATURES,
                STR.SEPARATE_FEATURES,
                defaultValue=self.prefs.get("separate_features", True),
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

    # ------------------------------------------------------------------
    # Helpers de nomenclatura
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize(text):
        """Remove caracteres inválidos para nomes de arquivo."""
        if text is None:
            return ""
        text = str(text).strip()
        for c in r'\/:*?"<>|':
            text = text.replace(c, "_")
        return text

    @staticmethod
    def _build_name(layer_name, prefix="", suffix="", feature_name=None, used_names=None):
        """Monta o nome do arquivo com prefixo, camada, feição e sufixo."""
        parts = []

        prefix = RasterMaskClipper._sanitize(prefix)
        suffix = RasterMaskClipper._sanitize(suffix)
        layer_name = RasterMaskClipper._sanitize(layer_name)

        if prefix:
            parts.append(prefix)

        parts.append(layer_name)

        if feature_name:
            feature_name = RasterMaskClipper._sanitize(feature_name)
            if feature_name:
                parts.append(feature_name)

        if suffix:
            parts.append(suffix)

        base = "_".join(parts)

        if used_names is None:
            return base

        if base not in used_names:
            used_names.add(base)
            return base

        i = 1
        while f"{base}_{i}" in used_names:
            i += 1

        final_name = f"{base}_{i}"
        used_names.add(final_name)

        return final_name

    # ------------------------------------------------------------------
    # Helpers de geometria
    # ------------------------------------------------------------------

    @staticmethod
    def _create_single_feature_layer(feature, crs):
        """Cria uma camada memory com uma única feição no CRS informado."""
        tmp = QgsVectorLayer(
            f"Polygon?crs={crs.authid()}",
            "mask",
            "memory",
        )

        dp = tmp.dataProvider()
        dp.addAttributes([])
        tmp.updateFields()

        f = QgsFeature()
        f.setGeometry(feature.geometry())
        dp.addFeature(f)

        tmp.updateExtents()

        return tmp

    @staticmethod
    def _reproject_layer(layer, target_crs, context, feedback):
        """Reprojetar a camada vetorial para o CRS alvo via processing."""
        feedback.pushInfo(
            f"Reprojetando vetor para o CRS do raster ({target_crs.authid()})..."
        )

        reproj = processing.run(
            "native:reprojectlayer",
            {
                "INPUT": layer,
                "TARGET_CRS": target_crs,
                "OUTPUT": "memory:",
            },
            context=context,
            feedback=feedback,
        )

        return reproj["OUTPUT"]

    # ------------------------------------------------------------------
    # Processamento
    # ------------------------------------------------------------------

    def processAlgorithm(self, params, context, feedback):
        self.logger.debug("Iniciando processAlgorithm...")

        try:
            raster = self.parameterAsRasterLayer(params, self.INPUT_RASTER, context)
            mask = self.parameterAsVectorLayer(params, self.INPUT_MASK, context)
            output_folder = self.parameterAsString(params, self.OUTPUT_FOLDER, context)
            prefix = self.parameterAsString(params, self.PREFIX, context) or ""
            suffix = self.parameterAsString(params, self.SUFFIX, context) or ""
            separate = self.parameterAsBool(params, self.SEPARATE_FEATURES, context)
            open_output_folder = self.parameterAsBool(
                params, self.OPEN_OUTPUT_FOLDER, context
            )
            display_help = self.parameterAsBool(params, self.DISPLAY_HELP, context)

            if raster is None:
                msg = "Raster inválido."
                self.logger.error(msg)
                raise QgsProcessingException(msg)

            if mask is None:
                msg = "Máscara inválida."
                self.logger.error(msg)
                raise QgsProcessingException(msg)

            if mask.featureCount() == 0:
                msg = "A camada de máscara não possui feições."
                self.logger.error(msg)
                raise QgsProcessingException(msg)

            raster_crs = raster.crs()
            vector_crs = mask.crs()

            # Reprojetar se necessário
            work_mask = mask
            if raster_crs != vector_crs:
                work_mask = self._reproject_layer(
                    mask, raster_crs, context, feedback
                )

            # Validar sobreposição
            raster_extent_geom = QgsGeometry.fromRect(raster.extent())
            overlap = False

            for feat in work_mask.getFeatures():
                if feat.geometry() and feat.geometry().intersects(raster_extent_geom):
                    overlap = True
                    break

            if not overlap:
                msg = "Raster e vetor não possuem sobreposição."
                self.logger.error(msg)
                raise QgsProcessingException(msg)

            # Pasta de saída
            save_to_disk = bool(output_folder)

            if save_to_disk:
                os.makedirs(output_folder, exist_ok=True)

            used_names = set()
            outputs = []

            layer_name = work_mask.name()

            # MODO: UMA FEIÇÃO = UM RASTER
            if separate:
                total = work_mask.featureCount()
                current = 0

                for feat in work_mask.getFeatures():
                    current += 1

                    if feedback.isCanceled():
                        break

                    geom = feat.geometry()

                    if not geom:
                        continue

                    if not geom.intersects(raster_extent_geom):
                        continue

                    feature_name = None
                    idx = feat.fields().indexOf("name")
                    if idx >= 0:
                        feature_name = feat["name"]

                    file_name = self._build_name(
                        layer_name=layer_name,
                        prefix=prefix,
                        suffix=suffix,
                        feature_name=feature_name,
                        used_names=used_names,
                    )

                    if save_to_disk:
                        out_raster = os.path.join(output_folder, f"{file_name}.tif")
                    else:
                        out_raster = os.path.join(
                            tempfile.gettempdir(), f"{file_name}.tif"
                        )

                    tmp_mask = self._create_single_feature_layer(feat, raster_crs)

                    feedback.pushInfo(f"Recortando {file_name}")

                    processing.run(
                        "gdal:cliprasterbymasklayer",
                        {
                            "INPUT": raster.source(),
                            "MASK": tmp_mask,
                            "SOURCE_CRS": None,
                            "TARGET_CRS": None,
                            "NODATA": None,
                            "ALPHA_BAND": False,
                            "CROP_TO_CUTLINE": True,
                            "KEEP_RESOLUTION": True,
                            "SET_RESOLUTION": False,
                            "MULTITHREADING": True,
                            "OPTIONS": "",
                            "DATA_TYPE": 0,
                            "EXTRA": "",
                            "OUTPUT": out_raster,
                        },
                        context=context,
                        feedback=feedback,
                    )

                    outputs.append(out_raster)

                    if not save_to_disk:
                        rl = QgsRasterLayer(out_raster, file_name)
                        if rl.isValid():
                            QgsProject.instance().addMapLayer(rl)

                    feedback.setProgress(int((current / total) * 100))

            # MODO: TODA CAMADA = UM RASTER
            else:
                file_name = self._build_name(
                    layer_name=layer_name,
                    prefix=prefix,
                    suffix=suffix,
                    feature_name=None,
                    used_names=used_names,
                )

                if save_to_disk:
                    out_raster = os.path.join(output_folder, f"{file_name}.tif")
                else:
                    out_raster = os.path.join(
                        tempfile.gettempdir(), f"{file_name}.tif"
                    )

                feedback.pushInfo(f"Recortando {file_name}")

                processing.run(
                    "gdal:cliprasterbymasklayer",
                    {
                        "INPUT": raster.source(),
                        "MASK": work_mask,
                        "SOURCE_CRS": None,
                        "TARGET_CRS": None,
                        "NODATA": None,
                        "ALPHA_BAND": False,
                        "CROP_TO_CUTLINE": True,
                        "KEEP_RESOLUTION": True,
                        "SET_RESOLUTION": False,
                        "MULTITHREADING": True,
                        "OPTIONS": "",
                        "DATA_TYPE": 0,
                        "EXTRA": "",
                        "OUTPUT": out_raster,
                    },
                    context=context,
                    feedback=feedback,
                )

                outputs.append(out_raster)

                if not save_to_disk:
                    rl = QgsRasterLayer(out_raster, file_name)
                    if rl.isValid():
                        QgsProject.instance().addMapLayer(rl)

            self.prefs.update(
                {
                    "last_output_folder": output_folder,
                    "separate_features": bool(separate),
                    "display_help": bool(display_help),
                    "open_output_folder": bool(open_output_folder),
                }
            )
            self.save_preferences()

            if save_to_disk and open_output_folder:
                self.open_folder_in_explorer(output_folder)

            feedback.pushInfo(
                f"Processamento concluído. {len(outputs)} raster(s) gerado(s)."
            )

            return {"OUTPUTS": outputs}

        except QgsProcessingException as e:
            self.logger.error(f"Erro de processamento: {e}")
            raise
        except Exception as e:
            msg = f"Erro não tratado em processAlgorithm: {e}"
            self.logger.error(msg)
            raise QgsProcessingException(msg)
