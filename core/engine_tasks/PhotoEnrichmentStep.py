# -*- coding: utf-8 -*-

from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.PhotoEnrichmentTask import PhotoEnrichmentTask
from ..config.LogUtils import LogUtils


class PhotoEnrichmentStep(BaseStep):
    """
    Step unificado para enriquecer JSON com metadados de fotos.
    
    Funciona em 3 modos:
    - "mrk+photo": Quando há pontos MRK no contexto (via MrkParseStep)
      → Chama pipeline com enable_mrk=True
    - "photo": Quando não há MRK (apenas pasta de fotos)
      → Chama pipeline com enable_mrk=False
    - "skeleton" (ESBOÇO): Apenas esqueleto inicial + MRK (sem EXIF/XMP/custom)
      → Chama pipeline com enable_mrk=True, enable_exif=False, enable_xmp=False, enable_custom_fields=False
    
    As flags de pipeline são propagadas do ExecutionContext para permitir
    que o plugin/ferramenta controle quais etapas executar.
    
    Em todos os casos, a saída é um JSON v2.0 que será vetorizado
    pelo JsonVectorizationStep posteriormente.
    """

    def name(self) -> str:
        return "PhotoEnrichmentStep"

    def create_task(self, context: ExecutionContext):
        context.require(["base_folder", "recursive", "tool_key"])

        # Determina se há dados MRK
        source = context.get("source", "")
        has_mrk_points = source == "mrk" or context.has("json_path")

        # Flags de pipeline: permite controle externo via context
        # Se não definidas, usa comportamento padrão (herdado)
        enable_mrk = context.get("enable_mrk", has_mrk_points)
        enable_exif = context.get("enable_exif", True)
        enable_xmp = context.get("enable_xmp", True)
        enable_custom_fields = context.get("enable_custom_fields", True)

        # Obtem timestamps existentes do contexto (propagados pelo MrkParseStep)
        existing_timestamps = context.get("timestamps", {})

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
            existing_timestamps=existing_timestamps,
            # Flags de pipeline
            enable_mrk=enable_mrk,
            enable_exif=enable_exif,
            enable_xmp=enable_xmp,
            enable_custom_fields=enable_custom_fields,
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
        source = result.get("source", "photo")
        context.set("json_path", json_path)
        context.set("source", source)

        # Propaga timestamps atualizados no contexto
        timestamps = result.get("timestamps", {})
        if timestamps:
            context.set("timestamps", timestamps)

        logger.info(
            "JSON enriquecido com metadados de foto",
            data={
                "json_path": json_path,
                "source": context.get("source"),
                "total_points": result.get("total_points", 0),
            },
        )