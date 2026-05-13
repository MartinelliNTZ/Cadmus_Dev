# -*- coding: utf-8 -*-
from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..config.LogUtils import LogUtils


class JsonVectorizationStep(BaseStep):
    """Step que cria camada vetorial exclusivamente a partir do JSON canônico."""

    def name(self) -> str:
        return "JsonVectorizationStep"

    def create_task(self, context: ExecutionContext):
        # Vetorizacao ocorre no on_success (sincrono), sem QgsTask dedicado.
        return None

    def should_run(self, context: ExecutionContext) -> bool:
        return bool(context.get("json_path"))

    def on_success(self, context: ExecutionContext, result):
        # Nao utilizado; a execucao real acontece em run_inline().
        pass

    def run_inline(self, context: ExecutionContext):
        logger = LogUtils(tool=context.get("tool_key"), class_name=self.__class__.__name__)
        json_path = context.get("json_path")
        if not json_path:
            raise ValueError("JsonVectorizationStep: json_path ausente no contexto")

        from ..translator.JsonToVectorTranslator import JsonToVectorTranslator
        from qgis.core import QgsProject

        layer_name = (
            context.get("points_layer_name")
            or context.get("layer_name")
            or "Cadmus_Vector"
        )
        source = context.get("source")
        translator = JsonToVectorTranslator(tool_key=context.get("tool_key"))
        layer = translator.translate(
            json_path=json_path,
            layer_name=layer_name,
            selected_keys=None,
            source=source,
        )
        if not layer or not layer.isValid():
            raise RuntimeError("Falha ao criar camada via JsonToVectorTranslator")

        QgsProject.instance().addMapLayer(layer)
        context.set("layer", layer)
        context.set("total_points", int(layer.featureCount()))

        logger.info(
            "Camada vetorial criada a partir do JSON",
            data={
                "layer_name": layer.name(),
                "json_path": json_path,
                "total_points": int(layer.featureCount()),
                "source": source,
            },
        )