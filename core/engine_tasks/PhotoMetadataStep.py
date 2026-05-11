# -*- coding: utf-8 -*-

from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.PhotoMetadataTask import PhotoMetadataTask
from ..config.LogUtils import LogUtils


class PhotoMetadataStep(BaseStep):
    """Step para aplicar metadados de fotos diretamente na camada."""

    def name(self) -> str:
        return "PhotoMetadataStep"

    def create_task(self, context: ExecutionContext):
        context.require(["layer", "base_folder", "recursive", "tool_key"])

        layer = context.get("layer")
        return PhotoMetadataTask(
            layer_id=layer.id() if layer else "",
            base_folder=context.get("base_folder"),
            recursive=context.get("recursive", True),
            source_points=context.get("points", []),
            selected_required_fields=context.get("selected_required_fields", []),
            selected_custom_fields=context.get("selected_custom_fields", []),
            selected_mrk_fields=context.get("selected_mrk_fields", []),
            tool_key=context.get("tool_key"),
        )

    def on_success(self, context: ExecutionContext, result):
        if not result or not isinstance(result, dict):
            return

        layer = context.get("layer")
        if layer is None:
            LogUtils(
                tool=context.get("tool_key"),
                class_name=self.__class__.__name__,
            ).error("Camada ausente no contexto durante aplicação de metadados")
            return

        # Novo fluxo: usar JsonToVectorTranslator em vez de aplicar updates na layer existente
        json_path = result.get("json_path") or result.get("json_dump_path")
        if not json_path:
            LogUtils(
                tool=context.get("tool_key"),
                class_name=self.__class__.__name__,
            ).error("json_path não encontrado no resultado do PhotoMetadataTask")
            return

        # Instanciar JsonToVectorTranslator
        from ..translator.JsonToVectorTranslator import JsonToVectorTranslator
        translator = JsonToVectorTranslator(tool_key=context.get("tool_key"))

        # Traduzir JSON para nova layer (com metadados enriquecidos)
        old_layer_id = layer.id()
        old_layer_name = layer.name()
        layer_name = f"{old_layer_name}_enriquecida" if old_layer_name else "Fotos_Enriquecidas"
        try:
            new_layer = translator.translate(
                json_path=json_path,
                layer_name=layer_name,
                selected_keys=None  # Usar todos os campos por padrão
            )

            if new_layer and new_layer.isValid():
                # Substituir a layer antiga pela nova no projeto QGIS
                from qgis.core import QgsProject
                project = QgsProject.instance()

                # Remover a layer antiga se ela estiver no projeto
                if old_layer_id in project.mapLayers():
                    project.removeMapLayer(old_layer_id)

                # Adicionar a nova layer
                project.addMapLayer(new_layer)

                # Atualizar contexto com a nova layer
                context.set("layer", new_layer)
                context.set("json_path", json_path)
                context.set("photo_metadata_json_path", json_path)

                LogUtils(
                    tool=context.get("tool_key"),
                    class_name=self.__class__.__name__,
                ).info(
                    "Camada vetorial enriquecida criada via JsonToVectorTranslator",
                    data={
                        "old_layer_name": old_layer_name,
                        "old_layer_id": old_layer_id,
                        "new_layer_name": new_layer.name(),
                        "json_path": json_path,
                        "total_features": new_layer.featureCount()
                    },
                )
            else:
                LogUtils(
                    tool=context.get("tool_key"),
                    class_name=self.__class__.__name__,
                ).error("Falha ao criar layer enriquecida via JsonToVectorTranslator")

        except Exception as e:
            LogUtils(
                tool=context.get("tool_key"),
                class_name=self.__class__.__name__,
            ).error(f"Erro no JsonToVectorTranslator: {e}")
            raise
