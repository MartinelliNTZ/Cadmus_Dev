# -*- coding: utf-8 -*-
from .BaseTask import BaseTask
from ..api.ImageryApi import ImageryApi


class ImagerySearchTask(BaseTask):
    """Task de busca de cenas no catálogo STAC (roda em worker thread).

    Lê os parâmetros de busca do ExecutionContext (bbox_wgs84, date_from,
    date_to, max_cloud, source) e retorna a lista de cenas normalizadas.
    """

    def __init__(self, context):
        super().__init__("Busca de cenas (STAC)", tool_key=context.tool_key)
        self._context = context
        self._api = ImageryApi(tool_key=context.tool_key)

    def _run(self) -> bool:
        bbox = self._context.get("bbox_wgs84") or []
        date_from = self._context.get("date_from", "")
        date_to = self._context.get("date_to", "")
        max_cloud = self._context.get("max_cloud", 100)
        source = self._context.get("source", "sentinel2")

        if not bbox or not date_from or not date_to:
            raise ValueError("Parâmetros de busca incompletos (bbox e datas)")

        self.logger.info(
            f"Busca STAC iniciada em task: {date_from} -> {date_to}",
            code="IMAGERY_TASK_SEARCH_START",
            bbox=bbox,
            max_cloud=max_cloud,
        )
        self.setProgress(10)

        scenes = self._api.search_scenes(
            bbox,
            date_from=date_from,
            date_to=date_to,
            max_cloud=max_cloud,
            source=source,
        )

        self.setProgress(100)
        self.result = scenes
        self.logger.info(
            f"Busca STAC concluída: {len(scenes)} cenas",
            code="IMAGERY_TASK_SEARCH_DONE",
            total=len(scenes),
        )
        return self.result is not None