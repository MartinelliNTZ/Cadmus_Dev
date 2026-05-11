# -*- coding: utf-8 -*-
from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.MrkParseTask import MrkParseTask
from ..config.LogUtils import LogUtils


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

        # Novo fluxo: usar JsonToVectorTranslator
        json_path = result.get("json_path")
        if not json_path:
            logger.error("json_path não encontrado no resultado do MrkParseTask")
            raise RuntimeError("Nenhum JSON gerado pelos MRKs.")

        # Instanciar JsonToVectorTranslator
        from ..translator.JsonToVectorTranslator import JsonToVectorTranslator
        translator = JsonToVectorTranslator(tool_key=context.get("tool_key"))

        # Traduzir JSON para layer
        layer_name = context.get("points_layer_name", "MRK_Pontos")
        try:
            layer = translator.translate(
                json_path=json_path,
                layer_name=layer_name,
                selected_keys=None,  # Usar todos os campos por padrão
                source=result.get("source", "mrk")
            )

            if layer and layer.isValid():
                # Adicionar ao projeto QGIS
                from qgis.core import QgsProject
                QgsProject.instance().addMapLayer(layer)

                context.set("layer", layer)
                context.set("json_path", json_path)
                context.set("source", result.get("source", "mrk"))
                context.set("base_folder", result.get("base_folder"))

                logger.info("Camada MRK criada via JsonToVectorTranslator", data={
                    "layer_name": layer.name(),
                    "json_path": json_path,
                    "total_features": layer.featureCount()
                })

                # Verificar se há pontos na layer
                if layer.featureCount() == 0:
                    logger.error(
                        "Nenhum ponto encontrado apos tradução do JSON MRK",
                        code="MRK_PARSE_NO_POINTS",
                        data={"json_path": json_path},
                    )
                    raise RuntimeError("Nenhum ponto MRK encontrado para gerar a camada.")
            else:
                logger.error("Falha ao criar layer MRK via JsonToVectorTranslator")
                raise RuntimeError("Falha ao criar camada de pontos a partir dos MRKs.")

        except Exception as e:
            logger.error(f"Erro no JsonToVectorTranslator: {e}")
            raise
