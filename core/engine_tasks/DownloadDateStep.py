# -*- coding: utf-8 -*-
from .BaseStep import BaseStep

from ..task.DownloadDateTask import DownloadDateTask
from ...utils.ExplorerUtils import ExplorerUtils
from ...utils.ProjectUtils import ProjectUtils
from ...utils.raster.RasterLayerSource import RasterLayerSource


class DownloadDateStep(BaseStep):
    """Step de download/processamento das cenas de UMA data.

    create_task → DownloadDateTask (worker: download, clip, reprojeção, ÷10000).
    on_success  → main thread: apaga originais (se opção) e carrega as camadas
                  da data no grupo ``{source_label} {date}`` via ProjectUtils.
    """

    def __init__(self, date: str, source_label: str = "Sentinel-2"):
        super().__init__()
        self._date = date
        self._source_label = source_label

    def name(self) -> str:
        """Identificação do step."""
        return f"download_date_{self._date}"

    def create_task(self, context):
        """Fabrica a task de download de uma data."""
        return DownloadDateTask(context, self._date)

    def on_success(self, context, result) -> None:
        """Main thread: remove originais e carrega camadas da data no grupo."""
        logger = self._init_logger(context)
        if not result:
            return

        date = result.get("date", self._date)
        originals = result.get("originals_to_delete", []) or []
        delete_originals = bool(result.get("delete_originals", False))

        # 1. Apagar originais uint16 (main thread — ExplorerUtils)
        if delete_originals:
            for orig in originals:
                if orig:
                    ExplorerUtils.delete_file(orig, tool_key=context.tool_key)
            logger.info(
                f"Originais removidos para {date}: {len(originals)}",
                code="IMAGERY_DELETE_ORIGINALS_DONE",
                date=date,
            )

        # 2. Carregar camadas no grupo por data (ProjectUtils/RasterLayerSource)
        files = result.get("files", []) or []
        group = ProjectUtils.ensure_group(f"{self._source_label} {date}")
        rsource = RasterLayerSource()
        carregadas = 0
        for tif in files:
            if not tif:
                continue
            layer = rsource.load_raster_from_file(
                tif, external_tool_key=context.tool_key
            )
            if layer is not None:
                ProjectUtils.add_layer_to_group(layer, group)
                carregadas += 1

        context.set(f"download_result_{date}", result)
        logger.info(
            f"Camadas carregadas para {date}: {carregadas}",
            code="IMAGERY_LOADED_GROUP",
            date=date,
            group=f"{self._source_label} {date}",
            carregadas=carregadas,
        )