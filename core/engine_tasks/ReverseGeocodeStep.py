# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.ReverseGeocodeTask import ReverseGeocodeTask
from ...utils.JsonUtil import JsonUtil


class ReverseGeocodeStep(BaseStep):
    """
    Step que executa reverse geocode para obter endereço a partir de coordenadas.

    Modos de operação:
      1. report_metadata_mode=True  (pipeline de drone):
         Lê coordenadas do context (setadas pelo FirstPhotoCoordStep).
         Nunca busca a primeira foto diretamente.
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
        return "reverse_geocode"

    # --------------------------------------------------
    # Condicional
    # --------------------------------------------------
    def should_run(self, context: ExecutionContext) -> bool:
        self._init_logger(context)
        if self._report_metadata_mode:
            # Coordenadas vêm do FirstPhotoCoordStep via context
            lat = context.get_result("first_photo_lat")
            lon = context.get_result("first_photo_lon")
            if lat is not None and lon is not None:
                return True
            self.logger.info(
                "ReverseGeocodeStep pulado: first_photo_lat/lon não disponíveis no context"
            )
            return False
        return self._lat is not None and self._lon is not None

    # --------------------------------------------------
    # Task factory
    # --------------------------------------------------
    def create_task(self, context: ExecutionContext) -> Optional[ReverseGeocodeTask]:
        self._init_logger(context)
        tool_key = context.tool_key

        if self._report_metadata_mode:
            lat = context.get_result("first_photo_lat")
            lon = context.get_result("first_photo_lon")
            if lat is not None and lon is not None:
                self.logger.info(
                    "ReverseGeocodeStep: coordenadas do context (via FirstPhotoCoordStep)",
                    data={"lat": lat, "lon": lon},
                )
                return ReverseGeocodeTask(lat, lon, tool_key=tool_key)
            self.logger.info("ReverseGeocodeStep pulado: sem coordenadas no context")
            return None

        if self._lat is not None and self._lon is not None:
            self.logger.info(
                "ReverseGeocodeStep: coordenadas diretas",
                data={"lat": self._lat, "lon": self._lon},
            )
            return ReverseGeocodeTask(self._lat, self._lon, tool_key=tool_key)

        self.logger.info("ReverseGeocodeStep pulado: coordenadas indisponíveis")
        return None

    # --------------------------------------------------
    # Sucesso
    # --------------------------------------------------
    def on_success(self, context: ExecutionContext, result) -> None:
        self._init_logger(context)
        try:
            context.set_result("address_data", result)
            self.logger.info(
                "ReverseGeocodeStep: resultado armazenado",
                data={"address_data": result},
            )

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
                        self.logger.info(
                            "Timestamps de geocode salvos no JSON",
                            data={"json_path": json_path},
                        )

                    geocode_payload = {
                        "municipio": result.get("municipio", ""),
                        "state_district": result.get("state_district", ""),
                        "state": result.get("state", ""),
                        "region": result.get("region", ""),
                        "country": result.get("country", ""),
                    }
                    JsonUtil.update_geocode_data(json_path, geocode_payload)
                    self.logger.info(
                        "Geocode adicionado ao JSON de metadados",
                        data={"json_path": json_path, **geocode_payload},
                    )

        except Exception as e:
            self.logger.exception(e, code="REVERSE_GEOCODE_ON_SUCCESS_ERROR")

    # --------------------------------------------------
    # Erro
    # --------------------------------------------------
    def on_error(self, context: ExecutionContext, exception: Exception) -> None:
        self._init_logger(context)
        self.logger.warning(f"Reverse geocode failed: {exception}")
        if self._report_metadata_mode:
            json_path = context.json_path
            if json_path and os.path.exists(json_path):
                try:
                    JsonUtil.update_timestamps(json_path, {
                        "geocode_error": str(exception),
                        "geocode_end": datetime.now().isoformat(),
                    })
                except Exception as e:
                    self.logger.warning(f"Erro ao salvar timestamp de falha no JSON: {e}")