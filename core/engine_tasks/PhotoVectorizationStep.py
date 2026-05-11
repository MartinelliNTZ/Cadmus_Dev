# -*- coding: utf-8 -*-
from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.PhotoVectorizationTask import PhotoVectorizationTask
from ..config.LogUtils import LogUtils
from ...utils.ExplorerUtils import ExplorerUtils
from ...utils.QgisMessageUtil import QgisMessageUtil
from ...i18n.TranslationManager import STR


class PhotoVectorizationStep(BaseStep):
    """Step para gerar camada vetorial a partir de pasta de fotos (sem MRK)."""

    def name(self) -> str:
        return "PhotoVectorizationStep"

    def create_task(self, context: ExecutionContext):
        context.require(["base_folder", "recursive", "layer_name", "tool_key"])

        return PhotoVectorizationTask(
            base_folder=context.get("base_folder"),
            recursive=context.get("recursive", True),
            layer_name=context.get("layer_name", "Fotos_Sem_MRK"),
            tool_key=context.get("tool_key"),
        )

    def on_success(self, context: ExecutionContext, result):
        logger = LogUtils(
            tool=context.get("tool_key"),
            class_name=self.__class__.__name__,
        )

        if not result or not isinstance(result, dict):
            logger.error("Resultado inválido da vetorização de fotos")
            return

        # Novo fluxo: usar JsonToVectorTranslator
        json_path = result.get("json_path")
        if not json_path:
            logger.error("json_path não encontrado no resultado")
            return

        # Instanciar JsonToVectorTranslator
        from ..translator.JsonToVectorTranslator import JsonToVectorTranslator
        translator = JsonToVectorTranslator(tool_key=context.get("tool_key"))

        # Traduzir JSON para layer
        layer_name = context.get("layer_name", "Fotos_Sem_MRK")
        try:
            layer = translator.translate(
                json_path=json_path,
                layer_name=layer_name,
                selected_keys=None  # Usar todos os campos por padrão
            )

            if layer and layer.isValid():
                # Adicionar ao projeto QGIS
                from qgis.core import QgsProject
                QgsProject.instance().addMapLayer(layer)

                context.set("layer", layer)
                context.set("json_path", json_path)
                context.set("report_payload", result.get("report_payload"))
                total_points = int(layer.featureCount())
                context.set("total_points", total_points)
                context.set("quality", result.get("quality", {}))

                logger.info("Camada vetorial criada via JsonToVectorTranslator", data={
                    "layer_name": layer.name(),
                    "json_path": json_path,
                    "total_points": total_points
                })

                # Abrir relatório HTML se foi gerado
                report_payload = result.get("report_payload")
                if report_payload and isinstance(report_payload, dict):
                    html_path = report_payload.get("html_path")
                    if html_path and context.get("iface"):
                        if not ExplorerUtils.open_file(html_path, context.get("tool_key")):
                            QgisMessageUtil.bar_warning(
                                context.get("iface"),
                                f"{STR.WARNING}: não foi possível abrir o HTML automaticamente.",
                            )
            else:
                logger.error("Falha ao criar layer via JsonToVectorTranslator")

        except Exception as e:
            logger.error(f"Erro no JsonToVectorTranslator: {e}")
            raise
