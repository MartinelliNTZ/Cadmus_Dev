# -*- coding: utf-8 -*-

from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.PhotoEnrichmentTask import PhotoEnrichmentTask
from ..config.LogUtils import LogUtils


class PhotoEnrichmentStep(BaseStep):
    """
    Step unificado para enriquecer JSON com metadados de fotos.

    Funciona em 2 modos, controlados pelo context.get("source"):
    - "mrk+photo": Quando há dados MRK no contexto
      → Chama pipeline com enable_mrk=True e usa context.get("paths")
    - "photo": Quando NÃO há MRK (apenas pasta de fotos)
      → Chama pipeline com enable_mrk=False

    O source é definido pelo plugin:
    - DroneCoordinates: source="mrk+photo", paths contem caminhos MRK
    - PhotoVectorization: source="photo" (padrao)

    As flags de pipeline (enable_mrk, enable_exif, etc.) podem ser
    sobrescritas via ExecutionContext.

    O PhotoMetadata é responsável por:
    - Fazer parsing MRK internamente se source="mrk+photo"
    - Executar pipeline completo de enriquecimento
    - Construir e salvar o JSON via build_and_save_json()

    A saída é um JSON v2.0 salvo em disco cujo caminho fica no
    contexto como "json_path", que será vetorizado pelo
    JsonVectorizationStep posteriormente.
    """

    def name(self) -> str:
        return "PhotoEnrichmentStep"

    def create_task(self, context: ExecutionContext):
        context.require(["base_folder", "recursive", "tool_key"])

        # O source determina o modo de operacao:
        #   "mrk+photo" → parsing MRK + enriquecimento completo
        #   "mrk"      → apenas parsing MRK + esqueleto (sem EXIF/XMP/custom)
        #   "photo"    → apenas fotos (sem MRK)
        source = context.get("source", "photo")

        # Se source tem "mrk", precisa de paths MRK do contexto
        has_mrk = "mrk" in source if source else False

        # Paths MRK (DroneCoordinates ja define "paths" no contexto)
        mrk_paths = context.get("paths", []) if has_mrk else []

        # Flags de pipeline baseadas no source
        enable_mrk = has_mrk
        enable_exif = context.get("enable_exif", source != "mrk")
        enable_xmp = context.get("enable_xmp", source != "mrk")
        enable_custom_fields = context.get("enable_custom_fields", source != "mrk")

        return PhotoEnrichmentTask(
            base_folder=context.get("base_folder"),
            recursive=context.get("recursive", True),
            source=source,
            paths=mrk_paths,
            json_path=context.get("json_path"),
            source_points=context.get("points", []),
            layer_id=context.get("layer_id", ""),
            selected_required_fields=context.get("selected_required_fields", []),
            selected_custom_fields=context.get("selected_custom_fields", []),
            selected_mrk_fields=context.get("selected_mrk_fields", []),
            tool_key=context.get("tool_key"),
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

        # Propaga resultados no contexto
        source = result.get("source", "photo")
        context.set("json_path", json_path)
        context.set("source", source)

        logger.info(
            "JSON enriquecido com metadados de foto",
            data={
                "json_path": json_path,
                "source": context.get("source"),
                "total_points": result.get("total_points", 0),
            },
        )