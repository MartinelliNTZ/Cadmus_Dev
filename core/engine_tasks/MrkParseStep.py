# -*- coding: utf-8 -*-
from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.MrkParseTask import MrkParseTask
from ..config.LogUtils import LogUtils
from ...utils.vector.VectorLayerGeometry import VectorLayerGeometry
from ...utils.mrk.MetadataFields import MetadataFields
from qgis.core import QgsProject
from qgis.PyQt.QtCore import QVariant


class MrkParseStep(BaseStep):
    """Step responsavel por ler MRKs e criar camada de pontos inicial."""

    def name(self) -> str:
        return "MrkParseStep"

    def create_task(self, context: ExecutionContext):
        context.require(["paths", "recursive", "tool_key"])

        return MrkParseTask(
            paths=context.get("paths"),
            recursive=context.get("recursive", True),
            extra_fields=context.get("extra_fields"),
            tool_key=context.get("tool_key"),
        )

    def on_success(self, context: ExecutionContext, result):
        logger = LogUtils(
            tool=context.get("tool_key"),
            class_name=self.__class__.__name__,
        )

        points = result.get("points", []) if isinstance(result, dict) else []
        base_folder = result.get("base_folder") if isinstance(result, dict) else None
        if base_folder:
            context.set("base_folder", base_folder)

        if not points:
            logger.error(
                "Nenhum ponto encontrado apos leitura de MRKs",
                code="MRK_PARSE_NO_POINTS",
                data={"base_folder": base_folder},
            )
            raise RuntimeError("Nenhum ponto MRK encontrado para gerar a camada.")

        layer_name = context.get("points_layer_name", "MRK_Pontos")
        field_specs = [
            ("foto", QVariant.Int, MetadataFields.resolve_output_name("foto")),
            ("alt", QVariant.Double, MetadataFields.resolve_output_name("alt")),
            ("date_name", QVariant.String, MetadataFields.resolve_output_name("date_name")),
            ("flight_number", QVariant.String, MetadataFields.resolve_output_name("flight_number")),
            ("flight_name", QVariant.String, MetadataFields.resolve_output_name("flight_name")),
            ("folder_level1", QVariant.String, MetadataFields.resolve_output_name("folder_level1")),
            ("folder_level2", QVariant.String, MetadataFields.resolve_output_name("folder_level2")),
            ("mrk_folder", QVariant.String, MetadataFields.resolve_output_name("mrk_folder")),
        ]
        layer = VectorLayerGeometry.create_point_layer_from_dicts(
            points=points,
            name=layer_name,
            field_specs=field_specs,
            geometry_keys=("lon", "lat"),
            extra_fields=context.get("extra_fields"),
        )

        if layer and layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            context.set("layer", layer)
            context.set("points", points)
            context.set("base_folder", base_folder)
            return

        logger.error(
            "Falha ao criar camada de pontos a partir dos MRKs",
            code="MRK_PARSE_LAYER_CREATE_FAILED",
            data={"base_folder": base_folder, "points_count": len(points)},
        )
        raise RuntimeError("Falha ao criar camada de pontos a partir dos MRKs.")
