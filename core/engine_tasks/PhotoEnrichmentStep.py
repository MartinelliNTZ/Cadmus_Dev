# -*- coding: utf-8 -*-

from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.PhotoEnrichmentTask import PhotoEnrichmentTask
from ..config.LogUtils import LogUtils


class PhotoEnrichmentStep(BaseStep):
    """
    Step unificado para enriquecer JSON com metadados de fotos.
    
    Funciona em 2 modos:
    - "mrk+photo": Quando há pontos MRK no contexto (via MrkParseStep)
      → Chama PhotoMetadata.enrich() para cruzar fotos com pontos MRK
    - "photo_only": Quando não há MRK (apenas pasta de fotos)
      → Chama PhotoFolderVectorizationService.extract_to_json()
    
    Em ambos os casos, a saída é um JSON v2.0 que será vetorizado
    pelo JsonVectorizationStep posteriormente.
    """

    def name(self) -> str:
        return "PhotoEnrichmentStep"

    def create_task(self, context: ExecutionContext):
        context.require(["base_folder", "recursive", "tool_key"])

        # Determina o modo baseado na existência de pontos MRK no contexto
        source = context.get("source", "")
        has_mrk_points = source == "mrk" or context.has("json_path")

        return PhotoEnrichmentTask(
            base_folder=context.get("base_folder"),
            recursive=context.get("recursive", True),
            # Dados MRK (opcional - se presentes, faz enrich mrk+photo)
            json_path=context.get("json_path") if has_mrk_points else None,
            source_points=context.get("points", []),
            layer_id=context.get("layer_id", ""),
            selected_required_fields=context.get("selected_required_fields", []),
            selected_custom_fields=context.get("selected_custom_fields", []),
            selected_mrk_fields=context.get("selected_mrk_fields", []),
            tool_key=context.get("tool_key"),
        )

    def on_success(self, context: ExecutionContext, result):
        logger = LogUtils(
            tool=context.get("tool_key"),
            class_name=self.__class__.__name__,
        )

        if not result or not isinstance(result, dict):
            logger.error("Resultado invalido do enriquecimento de fotos")
            return

        json_path = result.get("json_path")
        if not json_path:
            logger.error("json_path nao encontrado no resultado")
            return

        # Determina source baseado no tipo de enriquecimento
        was_mrk_enrich = result.get("source", "photo_only") == "mrk+photo"
        context.set("json_path", json_path)
        context.set("source", "mrk+photo" if was_mrk_enrich else "photo_only")

        logger.info(
            "JSON enriquecido com metadados de foto",
            data={
                "json_path": json_path,
                "source": context.get("source"),
                "total_points": result.get("total_points", 0),
            },
        )