# -*- coding: utf-8 -*-
from qgis.core import QgsField, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant
from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.PathExtensionTask import PathExtensionTask
from ..config.LogUtils import LogUtils
from ...utils.QgisMessageUtil import QgisMessageUtil


class PathExtensionStep(BaseStep):
    """
    Step da pipeline para remover/restaurar extensão de arquivos.

    Responsabilidades:
    - create_task: extrai dados da camada (main thread) e cria a task
    - on_success: aplica mudanças na camada (main thread) e exibe mensagem
    """

    def name(self) -> str:
        return "path_extension"

    def create_task(self, context: ExecutionContext):
        context.require(["layer", "attribute", "mode", "tool_key"])

        layer = context.get("layer")
        attribute = context.get("attribute")
        mode = context.get("mode")
        tool_key = context.get("tool_key")

        logger = LogUtils(tool=tool_key, class_name=self.__class__.__name__)

        if not isinstance(layer, QgsVectorLayer):
            raise RuntimeError("layer não é QgsVectorLayer")

        # Extrair dados na main thread (thread-safe)
        fields = layer.fields()
        field_idx = fields.lookupField(attribute)
        if field_idx < 0:
            raise RuntimeError(f"Atributo '{attribute}' não encontrado na camada")

        # Garantir campo NewPath na main thread
        new_field_idx = fields.lookupField("NewPath")
        if new_field_idx < 0:
            new_field = QgsField("NewPath", QVariant.String)
            layer.dataProvider().addAttributes([new_field])
            layer.updateFields()

        features_data = []
        for feature in layer.getFeatures():
            path_value = feature.attribute(attribute)
            features_data.append((feature.id(), str(path_value) if path_value else ""))

        logger.info(
            f"Criando task: layer={layer.name()}, "
            f"attribute={attribute}, mode={mode}, "
            f"features={len(features_data)}"
        )

        # Salvar layer no contexto pro on_success usar
        context.set("_layer", layer)
        context.set("_attribute", attribute)

        return PathExtensionTask(
            features_data=features_data,
            mode=mode,
            tool_key=tool_key,
        )

    def on_success(self, context: ExecutionContext, result):
        logger = LogUtils(
            tool=context.get("tool_key"),
            class_name=self.__class__.__name__,
        )
        iface = context.get("iface", None)
        layer = context.get("_layer")
        attribute = context.get("_attribute")
        changes = result.get("changes", {})
        processed = result.get("processed", 0)

        logger.info(
            f"PathExtension concluído: {processed} feições alteradas"
        )

        # Aplicar mudanças na main thread
        if changes and isinstance(layer, QgsVectorLayer):
            fields = layer.fields()
            new_field_idx = fields.lookupField("NewPath")
            if new_field_idx < 0:
                logger.error("Campo NewPath não encontrado na camada")
                return

            dp = layer.dataProvider()
            attr_changes = {}
            for fid, new_path in changes.items():
                attr_changes[fid] = {new_field_idx: new_path}

            dp.changeAttributeValues(attr_changes)
            layer.triggerRepaint()

            logger.info(f"{len(changes)} feições atualizadas com NewPath")

        # Exibir mensagem de sucesso
        if iface:
            msg = (
                f"Processamento concluído: {processed} feições alteradas"
            )
            QgisMessageUtil.bar_success(iface, msg)
            logger.info("Mensagem de sucesso exibida na barra")

        context.set("path_extension_result", result)