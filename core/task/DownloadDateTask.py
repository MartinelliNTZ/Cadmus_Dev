# -*- coding: utf-8 -*-
from .BaseTask import BaseTask
from ..api.ImageryApi import ImageryApi
from ...utils.ExplorerUtils import ExplorerUtils


class DownloadDateTask(BaseTask):
    """Task de download/processamento das cenas de UMA data (worker thread).

    Lê do ExecutionContext: selected_scenes, bandas, options (clip/reproject/
    convert/delete), epsg_out, polygon_path e bbox_wgs84. Para cada cena da
    data, chama ``ImageryApi.process_item`` e agrega os arquivos gerados.
    """

    def __init__(self, context, date: str):
        super().__init__(f"Download {date}", tool_key=context.tool_key)
        self._context = context
        self._date = date

    def _run(self) -> bool:
        if self.isCanceled() or self._context.is_cancelled():
            self.logger.warning(
                "Task de download cancelada antes de iniciar",
                code="IMAGERY_TASK_CANCELLED",
            )
            return False

        api = ImageryApi(tool_key=self.tool_key)

        items = [
            s for s in self._context.get("selected_scenes", [])
            if s.get("date") == self._date
        ]
        if not items:
            self.result = {
                "date": self._date,
                "folder": "",
                "files": [],
                "originals_to_delete": [],
                "delete_originals": False,
                "bandas": [],
            }
            return True

        bandas = self._context.get("bandas", []) or []
        options = self._context.get("options", {}) or {}
        clip = bool(options.get("clip", False))
        polygon_path = self._context.get("polygon_path") or ""
        convert = bool(options.get("convert", False))
        delete_originals = bool(options.get("delete", False))
        epsg_out = self._context.get("epsg_out")

        if clip and polygon_path:
            clip_mode = "polygon"
            clip_geom = {"polygon_path": polygon_path}
        elif clip:
            clip_mode = "extent"
            clip_geom = {"extent_wgs84": self._context.get("bbox_wgs84") or []}
        else:
            clip_mode = None
            clip_geom = None

        output_folder = self._context.get("output_folder") or \
            ExplorerUtils.get_temp_folder(self.tool_key, "imagery")

        self.logger.info(
            f"Download de {len(items)} cena(s) na data {self._date}",
            code="IMAGERY_TASK_DOWNLOAD_START",
            date=self._date,
            cenas=len(items),
            bandas=len(bandas),
            clip_mode=clip_mode,
            epsg_out=epsg_out,
        )

        all_files = []
        all_delete = []
        total = len(items)
        for idx, item in enumerate(items):
            if self.isCanceled() or self._context.is_cancelled():
                self.logger.warning(
                    "Download cancelado pelo usuário",
                    code="IMAGERY_TASK_CANCELLED_RUN",
                )
                return False

            def _cb(part, base=(idx / total) * 100.0 if total else 0.0):
                try:
                    self.setProgress(int(base + (part / total) if total else 100))
                except Exception as e:
                    self.logger.warning(f"setProgress falhou: {e}")

            result = api.process_item(
                item,
                bandas,
                clip_mode,
                clip_geom,
                epsg_out,
                output_folder,
                convert_uint16=convert,
                delete_originals=delete_originals,
                progress_cb=_cb,
            )
            all_files.extend(result.get("files", []) or [])
            all_delete.extend(result.get("originals_to_delete", []) or [])
            self.setProgress(int(((idx + 1) / total) * 100))

        self.result = {
            "date": self._date,
            "folder": output_folder,
            "files": all_files,
            "originals_to_delete": all_delete,
            "delete_originals": delete_originals,
            "bandas": bandas,
        }
        self.setProgress(100)
        self.logger.info(
            f"Download concluído: {len(all_files)} arquivos em {self._date}",
            code="IMAGERY_TASK_DOWNLOAD_DONE",
            date=self._date,
            arquivos=len(all_files),
        )
        return True