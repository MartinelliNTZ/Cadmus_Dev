# -*- coding: utf-8 -*-
import os

from .BaseTask import BaseTask
from ..api.ImageryApi import ImageryApi
from ...utils.ExplorerUtils import ExplorerUtils


class DownloadDateTask(BaseTask):
    """Task de download/processamento das cenas de UMA data (worker thread).

    Lê do ExecutionContext: selected_scenes, bandas, options (clip/reproject/
    convert/delete), epsg_out, bbox_wgs84 e clip_data (do GridBBoxSelector).
    Para cada cena da data, chama ``ImageryApi.process_item`` e agrega os
    arquivos gerados.
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
        compositions = self._context.get("compositions", []) or []
        options = self._context.get("options", {}) or {}
        clip = bool(options.get("clip", False))
        convert = bool(options.get("convert", False))
        delete_originals = bool(options.get("delete", False))
        epsg_out = self._context.get("epsg_out")
        output_folder = self._context.get("output_folder") or \
            ExplorerUtils.get_temp_folder(self.tool_key, "imagery")

        # Recorte vem do GridBBoxSelector via clip_data:
        #   "polygon"  -> camada de polígono (polygon_path) ou polígono
        #                 desenhado (polygon_wkt -> máscara GPKG temporária)
        #   "extent"   -> boundary WGS84 (clip por extensão no CRS da cena)
        clip_data = self._context.get("clip_data") or {}
        clip_mode = None
        clip_geom = None
        if clip and clip_data:
            if clip_data.get("mode") == "polygon":
                polygon_path = clip_data.get("polygon_path") or ""
                if polygon_path:
                    clip_mode = "polygon"
                    clip_geom = {"polygon_path": polygon_path}
                elif clip_data.get("polygon_wkt"):
                    mask_path = api.create_polygon_mask(
                        clip_data["polygon_wkt"],
                        os.path.join(
                            output_folder,
                            f"_recorte_desenhado_mask_{self._date}.gpkg",
                        ),
                    )
                    clip_mode = "polygon"
                    clip_geom = {"polygon_path": mask_path}
            elif clip_data.get("mode") == "extent" and (
                clip_data.get("extent_wgs84")
            ):
                clip_mode = "extent"
                clip_geom = {"extent_wgs84": clip_data["extent_wgs84"]}

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
        falhas = 0
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

            try:
                result = api.process_item(
                    item,
                    bandas,
                    clip_mode,
                    clip_geom,
                    epsg_out,
                    output_folder,
                    convert_uint16=convert,
                    delete_originals=delete_originals,
                    compositions=compositions,
                    progress_cb=_cb,
                )
            except Exception as exc:  # noqa: BLE001 - 1 cena não pode derrubar a data
                import traceback

                falhas += 1
                self.logger.error(
                    f"Falha ao processar cena, pulando: {exc}",
                    code="IMAGERY_ITEM_FAILED",
                    item=item.get("id"),
                    date=self._date,
                    traceback=traceback.format_exc(),
                )
                self.setProgress(int(((idx + 1) / total) * 100))
                continue

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