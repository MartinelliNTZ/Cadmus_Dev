# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.ReverseGeocodeTask import ReverseGeocodeTask
from ..config.LogUtils import LogUtils
from ...utils.JsonUtil import JsonUtil


class ReverseGeocodeStep(BaseStep):
    """
    Step que executa reverse geocode para obter endereço a partir de coordenadas.

    Modos de operação:
      1. report_metadata_mode=True  (pipeline de drone):
         Lê context.json_path, extrai Lat/Lon da primeira foto do JSON.
      2. report_metadata_mode=False (CoordClickTool):
         Usa lat/lon passados via __init__.

    Uso na pipeline de drone:
        steps = [
            PhotoEnrichmentStep(...),
            ReverseGeocodeStep(report_metadata_mode=True),
            JsonVectorizationStep(...),
            ReportGenerationStep(),
        ]

    Uso no CoordClickTool:
        steps = [
            ReverseGeocodeStep(lat=-23.5, lon=-46.6),
        ]
    """

    def __init__(
        self,
        *,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        report_metadata_mode: bool = False,
    ):
        """
        Args:
            lat: Latitude para geocode (modo clicktool)
            lon: Longitude para geocode (modo clicktool)
            report_metadata_mode: True = lê coordenadas do context.json_path
        """
        self._lat = lat
        self._lon = lon
        self._report_metadata_mode = report_metadata_mode

    def name(self) -> str:
        return "reverse_geocode"

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
        except Exception:
            return None

    # --------------------------------------------------
    # Condicional
    # --------------------------------------------------
    def should_run(self, context: ExecutionContext) -> bool:
        """Só executa se houver coordenadas disponíveis."""
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
    def create_task(self, context: ExecutionContext) -> Optional[ReverseGeocodeTask]:
        """Cria ReverseGeocodeTask com coordenadas resolvidas."""
        tool_key = context.tool_key
        if not tool_key:
            raise KeyError("ExecutionContext.tool_key não definido")

        if self._report_metadata_mode:
            json_path = context.json_path
            if json_path and os.path.exists(json_path):
                coords = self._get_first_photo_coords(json_path)
                if coords:
                    return ReverseGeocodeTask(coords["lat"], coords["lon"], tool_key=tool_key)
            return None

        if self._lat is not None and self._lon is not None:
            return ReverseGeocodeTask(self._lat, self._lon, tool_key=tool_key)

        return None

    # --------------------------------------------------
    # Sucesso
    # --------------------------------------------------
    def on_success(self, context: ExecutionContext, result) -> None:
        """
        Persiste resultado no ExecutionContext e no JSON de metadados (se for report mode).
        """
        tool_key = context.tool_key
        logger = LogUtils(
            tool=tool_key,
            class_name=self.__class__.__name__,
        )
        try:
            context.set_result("address_data", result)
            logger.debug(f"Address data stored: {result}")

            # Se for report mode, persiste geocode no JSON de metadados
            if self._report_metadata_mode and result:
                json_path = context.json_path
                if json_path and os.path.exists(json_path):
                    geocode_start = context.get_result("geocode_start")
                    geocode_end = datetime.now().isoformat()
                    if geocode_start:
                        JsonUtil.update_timestamps(json_path, {
                            "geocode_start": geocode_start,
                            "geocode_end": geocode_end,
                        })

                    geocode_payload = {
                        "municipio": result.get("municipio", ""),
                        "state_district": result.get("state_district", ""),
                        "state": result.get("state", ""),
                        "region": result.get("region", ""),
                        "country": result.get("country", ""),
                    }
                    JsonUtil.update_geocode_data(json_path, geocode_payload)
                    logger.info(
                        "Geocode adicionado ao JSON de metadados",
                        data={"json_path": json_path, **geocode_payload},
                    )

        except Exception as e:
            logger.error(f"ReverseGeocodeStep.on_success error: {e}")

    # --------------------------------------------------
    # Erro
    # --------------------------------------------------
    def on_error(self, context: ExecutionContext, exception: Exception) -> None:
        """Registra falha no log — sem acoplamento de UI."""
        tool_key = context.tool_key
        logger = LogUtils(
            tool=tool_key,
            class_name=self.__class__.__name__,
        )
        logger.warning(f"Reverse geocode failed: {exception}")