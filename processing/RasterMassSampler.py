# -*- coding: utf-8 -*-
import os
import re

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsProcessing,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterCrs,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterMultipleLayers,
)

from ..i18n.TranslationManager import STR
from ..resources.IconManager import IconManager as im
from ..utils.ToolKeys import ToolKey
from ..utils.vector.VectorLayerProjection import VectorLayerProjection
from .BaseProcessingAlgorithm import BaseProcessingAlgorithm


class RasterMassSampler(BaseProcessingAlgorithm):
    """
    QgsProcessingAlgorithm: Amostragem massiva de rasters para pontos.
    """

    TOOL_KEY = ToolKey.RASTER_MASS_SAMPLER
    ALGORITHM_NAME = "raster_mass_sampler"
    ALGORITHM_DISPLAY_NAME = STR.RASTER_MASS_SAMPLER_TITLE
    ALGORITHM_GROUP = BaseProcessingAlgorithm.GROUP_RASTER
    ICON = im.RASTER_MASS_SAMPLER
    INSTRUCTIONS_FILE = "raster_mass_sampler.html"

    INPUT_POINTS = "INPUT_POINTS"
    INPUT_RASTERS = "INPUT_RASTERS"
    OUTPUT_CRS = "OUTPUT_CRS"
    OUTPUT = "OUTPUT"
    DISPLAY_HELP = "DISPLAY_HELP"
    OPEN_OUTPUT_FOLDER = "OPEN_OUTPUT_FOLDER"

    def initAlgorithm(self, config=None):
        self.load_preferences()

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_POINTS,
                STR.INPUT_POINTS,
                [QgsProcessing.TypeVectorPoint],
            )
        )

        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.INPUT_RASTERS,
                STR.RASTERS,
                QgsProcessing.TypeRaster,
            )
        )

        self.addParameter(
            QgsProcessingParameterCrs(
                self.OUTPUT_CRS,
                STR.REPROJECT_OUTPUT_LAYER_OPTIONAL,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, STR.SAMPLED_VALUES)
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
        pts = self.parameterAsSource(params, self.INPUT_POINTS, context)
        rasters = self.parameterAsLayerList(params, self.INPUT_RASTERS, context)
        open_output_folder = self.parameterAsBool(params, self.OPEN_OUTPUT_FOLDER, context)
        display_help = self.parameterAsBool(params, self.DISPLAY_HELP, context)

        output_crs = self.parameterAsCrs(params, self.OUTPUT_CRS, context)
        if not output_crs.isValid():
            output_crs = None

        feedback.pushInfo(
            f"{STR.OUTPUT_CRS_LABEL} {output_crs.authid() if output_crs else STR.NONE}"
        )

        out_fields, raster_fields = self.build_output_fields(pts, rasters)
        transforms = self.build_transforms(pts, rasters, context)
        features = self.sample_features(pts, rasters, transforms, out_fields, feedback)

        if output_crs:
            source_crs = pts.sourceCrs()
            features = VectorLayerProjection.reproject_features(
                features, source_crs, output_crs, context
            )

        final_crs = output_crs if output_crs else pts.sourceCrs()

        sink, dest = self.parameterAsSink(
            params, self.OUTPUT, context, out_fields, pts.wkbType(), final_crs
        )

        for f in features:
            sink.addFeature(f, QgsFeatureSink.FastInsert)

        self.prefs.update(
            {
                "display_help": bool(display_help),
                "open_output_folder": bool(open_output_folder),
            }
        )

        if dest and isinstance(dest, str) and not dest.startswith("memory:"):
            out_folder = os.path.dirname(dest)
            feedback.pushInfo(f"{STR.FILE_SAVED_IN} {out_folder}")
            self.prefs.update(
                {"last_output_folder": out_folder, "last_output_file": dest}
            )
            if open_output_folder:
                self.open_folder_in_explorer(out_folder)

        self.save_preferences()
        return {self.OUTPUT: dest}

    def build_output_fields(self, pts, rasters, max_len: int = 10):
        out_fields = QgsFields()
        try:
            for f in pts.fields():
                out_fields.append(f)
        except Exception:
            if isinstance(pts, QgsFields):
                for f in pts:
                    out_fields.append(f)

        raster_fields = []
        for ras in rasters:
            layer_name = ras.name() if hasattr(ras, "name") else str(ras)
            candidate = self._sanitize_field_name(
                layer_name, raster_fields, max_len=max_len
            )
            raster_fields.append(candidate)
            out_fields.append(QgsField(candidate, QVariant.Double))

        return out_fields, raster_fields

    def _sanitize_field_name(
        self, layer_name: str, existing: list, max_len: int = 10
    ) -> str:
        field_base = re.sub(r"[^0-9A-Za-z_]", "_", layer_name)
        candidate = field_base[:max_len]
        if candidate in existing:
            i = 1
            while True:
                suffix = f"_{i}"
                avail_len = max_len - len(suffix)
                new_candidate = (
                    (field_base[:avail_len] + suffix)
                    if avail_len > 0
                    else (field_base[:max_len])
                )
                if new_candidate not in existing:
                    candidate = new_candidate
                    break
                i += 1
        return candidate

    def build_transforms(self, pts, rasters, context):
        effective_pts_crs = None
        try:
            effective_pts_crs = pts.sourceCrs()
        except Exception:
            effective_pts_crs = None

        transforms = []
        for ras in rasters:
            transforms.append(
                QgsCoordinateTransform(
                    effective_pts_crs, ras.crs(), context.transformContext()
                )
            )
        return transforms

    def sample_features(self, pts, rasters, transforms, out_fields, feedback):
        result = []
        for feat in pts.getFeatures():
            geom = feat.geometry()
            if geom is None:
                continue

            out_feat = QgsFeature(out_fields)
            out_feat.setGeometry(geom)
            attrs = feat.attributes()

            for i, ras in enumerate(rasters):
                try:
                    pt = transforms[i].transform(geom.asPoint())
                    val = ras.dataProvider().sample(pt, 1)[0]
                except Exception:
                    val = None

                feedback.pushInfo(
                    f"[DEBUG] Ponto {feat.id()}, Raster {ras.name()} = {val}"
                )
                attrs.append(float(val) if val is not None else None)

            out_feat.setAttributes(attrs)
            result.append(out_feat)

        return result

    def write_sink(self, params, context, out_fields, features, pts, feedback):
        sink, dest = self.parameterAsSink(
            params, self.OUTPUT, context, out_fields, pts.wkbType(), pts.sourceCrs()
        )

        for f in features:
            sink.addFeature(f, QgsFeatureSink.FastInsert)

        if dest and isinstance(dest, str) and not dest.startswith("memory:"):
            out_folder = os.path.dirname(dest)
            feedback.pushInfo(f"{STR.FILE_SAVED_IN} {out_folder}")

            display_help = (
                bool(self.parameterAsBool(params, self.DISPLAY_HELP, context))
                if self.DISPLAY_HELP in params
                else False
            )
            open_output_folder = (
                bool(self.parameterAsBool(params, self.OPEN_OUTPUT_FOLDER, context))
                if self.OPEN_OUTPUT_FOLDER in params
                else True
            )
            self.prefs.update(
                {
                    "last_output_folder": out_folder,
                    "last_output_file": dest,
                    "display_help": display_help,
                    "open_output_folder": open_output_folder,
                }
            )
            self.save_preferences()

            if open_output_folder:
                self.open_folder_in_explorer(out_folder)

        return {self.OUTPUT: dest}
