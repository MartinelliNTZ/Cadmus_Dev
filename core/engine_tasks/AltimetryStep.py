# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.altimetry_task import AltimetriaTask
from ...utils.JsonUtil import JsonUtil


class AltimetryStep(BaseStep):
    """
    Step que executa altimetria (SRTM 90m) para obter altitude a partir de coordenadas.

    Modos de operação:
      1. report_metadata_mode=True  (pipeline de drone):
         Lê context.json_path, extrai Lat/Lon da primeira foto do JSON.
      2. report_metadata_mode=False (CoordClickTool):
         Usa lat/lon passados via __init__.
    """

    def __init__(
        self,
        *,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        report_metadata_mode: bool = False,
    ):
        super().__init__()
        self._lat = lat
        self._lon = lon
        self._report_metadata_mode = report_metadata_mode

    def name(self) -> str:
        return "altimetry"

    # --------------------------------------------------
    # Utilitários
    # --------------------------------------------------
    def _get_first_photo_coords(self, json_path: str) -> Optional[Dict[str, float]]:
        """
        Lê o JSON e retorna as coordenadas da primeira foto que possui Lat/Lon.
        """
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for group in data.get("groups", {}).values():
                for record in group.get("records", {}).values():
                    lat = record.get("Lat") or record.get("GpsLatitude") or record.get("GpsLat")
                    lon = record.get("Lon") or record.get("GpsLongitude") or record.get("GPSLong")
                    if lat is not None and lon is not None:
                        return {"lat": float(lat), "lon": float(lon)}
            return None
        except (json.JSONDecodeError, IOError, OSError, ValueError, KeyError) as e:
            if self.logger:
                self.logger.warning(
                    "AltimetryStep: erro ao ler coordenadas do JSON",
                    data={"json_path": json_path, "error": str(e)},
                )
            return None

    # --------------------------------------------------
    # Condicional
    # --------------------------------------------------
    def should_run(self, context: ExecutionContext) -> bool:
        self._init_logger(context)
        if self._report_metadata_mode:
            json_path = context.json_path
            if json_path and os.path.exists(json_path):
                coords = self._get_first_photo_coords(json_path)
                if coords:
                    return True
            return False
        return self._lat is not None and self._lon is not None

    # --------------------------------------------------
    # Task factory
    # --------------------------------------------------
    def create_task(self, context: ExecutionContext) -> Optional[AltimetriaTask]:
        self._init_logger(context)
        tool_key = context.tool_key

        if self._report_metadata_mode:
            json_path = context.json_path
            if json_path and os.path.exists(json_path):
                coords = self._get_first_photo_coords(json_path)
                if coords:
                    self.logger.info(
                        "AltimetryStep: coordenadas extraídas do JSON",
                        data={"lat": coords["lat"], "lon": coords["lon"], "json_path": json_path},
                    )
                    return AltimetriaTask(coords["lat"], coords["lon"], tool_key=tool_key)
            self.logger.info("AltimetryStep pulado: JSON sem coordenadas")
            return None

        if self._lat is not None and self._lon is not None:
            self.logger.info(
                "AltimetryStep: coordenadas diretas",
                data={"lat": self._lat, "lon": self._lon},
            )
            return AltimetriaTask(self._lat, self._lon, tool_key=tool_key)

        self.logger.info("AltimetryStep pulado: coordenadas indisponíveis")
        return None

    # --------------------------------------------------
    # Sucesso
    # --------------------------------------------------
    def on_success(self, context: ExecutionContext, result) -> None:
        self._init_logger(context)
        try:
            context.set_result("altitude", result)
            self.logger.info(
                "AltimetryStep: resultado armazenado",
                data={"altitude": result},
            )

            if self._report_metadata_mode and result is not None:
                json_path = context.json_path
                if json_path and os.path.exists(json_path):
                    alt_start = context.get_result("altimetry_start")
                    alt_end = datetime.now().isoformat()
                    if alt_start:
                        JsonUtil.update_timestamps(json_path, {
                            "altimetry_start": alt_start,
                            "altimetry_end": alt_end,
                        })
                        self.logger.info(
                            "Timestamps de altimetria salvos no JSON",
                            data={"json_path": json_path},
                        )

                    JsonUtil.update_altitude_data(json_path, float(result))
                    self.logger.info(
                        "Altitude adicionada ao JSON de metadados",
                        data={"json_path": json_path, "altitude": result},
                    )

        except Exception as e:
            self.logger.exception(e, code="ALTIMETRY_ON_SUCCESS_ERROR")

    # --------------------------------------------------
    # Erro
    # --------------------------------------------------
    def on_error(self, context: ExecutionContext, exception: Exception) -> None:
        self._init_logger(context)
        self.logger.warning(f"Altimetry failed: {exception}")
        if self._report_metadata_mode:
            json_path = context.json_path
            if json_path and os.path.exists(json_path):
                try:
                    JsonUtil.update_timestamps(json_path, {
                        "altimetry_error": str(exception),
                        "altimetry_end": datetime.now().isoformat(),
                    })
                except Exception as e:
                    self.logger.warning(f"Erro ao salvar timestamp de falha no JSON: {e}")