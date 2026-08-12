from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterString,
    QgsProcessingParameterBoolean,
    QgsProcessingException,
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsRasterLayer
)

import processing
import os
import tempfile
import shutil


class RasterMaskClipper(QgsProcessingAlgorithm):

    INPUT_RASTER = "INPUT_RASTER"
    INPUT_MASK = "INPUT_MASK"
    OUTPUT_FOLDER = "OUTPUT_FOLDER"
    PREFIX = "PREFIX"
    SUFFIX = "SUFFIX"
    SEPARATE_FEATURES = "SEPARATE_FEATURES"

    def tr(self, text):
        return QCoreApplication.translate("RasterMaskClipper", text)

    def createInstance(self):
        return RasterMaskClipper()

    def name(self):
        return "raster_mask_clipper"

    def displayName(self):
        return self.tr("Raster Mask Clipper")

    def group(self):
        return self.tr("Raster")

    def groupId(self):
        return "raster"

    def shortHelpString(self):
        return self.tr(
            "Recorta raster por máscara. "
            "Quando 'Separar feições' estiver marcado, gera um raster por feição. "
            "Quando desmarcado, gera apenas um raster usando toda a camada."
        )

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_RASTER,
                self.tr("Raster")
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_MASK,
                self.tr("Polígono"),
                [QgsProcessing.TypeVectorPolygon]
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_FOLDER,
                self.tr("Pasta de saída"),
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.PREFIX,
                self.tr("Prefixo"),
                defaultValue="",
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.SUFFIX,
                self.tr("Sufixo"),
                defaultValue="",
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SEPARATE_FEATURES,
                self.tr("Separar feições"),
                defaultValue=True
            )
        )

    # ---------------------------------------------------------------------

    def _sanitize(self, text):
        if text is None:
            return ""
        text = str(text).strip()
        for c in r'\/:*?"<>|':
            text = text.replace(c, "_")
        return text

    # ---------------------------------------------------------------------

    def _build_name(
        self,
        layer_name,
        prefix="",
        suffix="",
        feature_name=None,
        used_names=None
    ):
        parts = []

        prefix = self._sanitize(prefix)
        suffix = self._sanitize(suffix)
        layer_name = self._sanitize(layer_name)

        if prefix:
            parts.append(prefix)

        parts.append(layer_name)

        if feature_name:
            feature_name = self._sanitize(feature_name)
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

    # ---------------------------------------------------------------------

    def _create_single_feature_layer(self, feature, crs):

        tmp = QgsVectorLayer(
            f"Polygon?crs={crs.authid()}",
            "mask",
            "memory"
        )

        dp = tmp.dataProvider()
        dp.addAttributes([])
        tmp.updateFields()

        f = QgsFeature()
        f.setGeometry(feature.geometry())
        dp.addFeature(f)

        tmp.updateExtents()

        return tmp

    # ---------------------------------------------------------------------

    def processAlgorithm(self, parameters, context, feedback):

        raster = self.parameterAsRasterLayer(
            parameters,
            self.INPUT_RASTER,
            context
        )

        mask = self.parameterAsVectorLayer(
            parameters,
            self.INPUT_MASK,
            context
        )

        output_folder = self.parameterAsString(
            parameters,
            self.OUTPUT_FOLDER,
            context
        )

        prefix = self.parameterAsString(
            parameters,
            self.PREFIX,
            context
        ) or ""

        suffix = self.parameterAsString(
            parameters,
            self.SUFFIX,
            context
        ) or ""

        separate = self.parameterAsBool(
            parameters,
            self.SEPARATE_FEATURES,
            context
        )

        if raster is None:
            raise QgsProcessingException("Raster inválido.")

        if mask is None:
            raise QgsProcessingException("Máscara inválida.")

        if mask.featureCount() == 0:
            raise QgsProcessingException("A camada de máscara não possui feições.")

        raster_crs = raster.crs()
        vector_crs = mask.crs()

        # -----------------------------------------------------------------
        # Reprojetar se necessário
        # -----------------------------------------------------------------

        work_mask = mask

        if raster_crs != vector_crs:

            feedback.pushInfo(
                "Reprojetando vetor para o CRS do raster..."
            )

            reproj = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": mask,
                    "TARGET_CRS": raster_crs,
                    "OUTPUT": "memory:"
                },
                context=context,
                feedback=feedback
            )

            work_mask = reproj["OUTPUT"]

        # -----------------------------------------------------------------
        # Validar sobreposição
        # -----------------------------------------------------------------

        raster_extent_geom = QgsGeometry.fromRect(
            raster.extent()
        )

        overlap = False

        for feat in work_mask.getFeatures():
            if feat.geometry() and feat.geometry().intersects(raster_extent_geom):
                overlap = True
                break

        if not overlap:
            raise QgsProcessingException(
                "Raster e vetor não possuem sobreposição."
            )

        # -----------------------------------------------------------------
        # Pasta saída
        # -----------------------------------------------------------------

        save_to_disk = bool(output_folder)

        if save_to_disk:
            os.makedirs(output_folder, exist_ok=True)

        used_names = set()
        outputs = []

        layer_name = work_mask.name()

        # -----------------------------------------------------------------
        # MODO: UMA FEIÇÃO = UM RASTER
        # -----------------------------------------------------------------

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
                    used_names=used_names
                )

                if save_to_disk:
                    out_raster = os.path.join(
                        output_folder,
                        f"{file_name}.tif"
                    )
                else:
                    out_raster = os.path.join(
                        tempfile.gettempdir(),
                        f"{file_name}.tif"
                    )

                tmp_mask = self._create_single_feature_layer(
                    feat,
                    raster_crs
                )

                feedback.pushInfo(
                    f"Recortando {file_name}"
                )

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
                        "OUTPUT": out_raster
                    },
                    context=context,
                    feedback=feedback
                )

                outputs.append(out_raster)

                if not save_to_disk:
                    rl = QgsRasterLayer(
                        out_raster,
                        file_name
                    )

                    if rl.isValid():
                        QgsProject.instance().addMapLayer(rl)

                feedback.setProgress(
                    int((current / total) * 100)
                )

        # -----------------------------------------------------------------
        # MODO: TODA CAMADA = UM RASTER
        # -----------------------------------------------------------------

        else:

            file_name = self._build_name(
                layer_name=layer_name,
                prefix=prefix,
                suffix=suffix,
                feature_name=None,
                used_names=used_names
            )

            if save_to_disk:
                out_raster = os.path.join(
                    output_folder,
                    f"{file_name}.tif"
                )
            else:
                out_raster = os.path.join(
                    tempfile.gettempdir(),
                    f"{file_name}.tif"
                )

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
                    "OUTPUT": out_raster
                },
                context=context,
                feedback=feedback
            )

            outputs.append(out_raster)

            if not save_to_disk:
                rl = QgsRasterLayer(
                    out_raster,
                    file_name
                )

                if rl.isValid():
                    QgsProject.instance().addMapLayer(rl)

        return {
            "OUTPUTS": outputs
        }