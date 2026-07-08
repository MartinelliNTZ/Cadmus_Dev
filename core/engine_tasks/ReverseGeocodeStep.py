# -*- coding: utf-8 -*-
from typing import Optional

from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.ReverseGeocodeTask import ReverseGeocodeTask
from ..config.LogUtils import LogUtils


class ReverseGeocodeStep(BaseStep):
    """
    Step que executa reverse geocode para obter endereço a partir de coordenadas.

    Pula execução se lat/lon não estiverem disponíveis no contexto.
    Armazena resultado no ExecutionContext como "address_data".
    """

    def name(self) -> str:
        return "reverse_geocode"

    # --------------------------------------------------
    # Condicional
    # --------------------------------------------------
    def should_run(self, context: ExecutionContext) -> bool:
        """Só executa se lat e lon estiverem disponíveis."""
        return context.has("lat") and context.has("lon")

    # --------------------------------------------------
    # Task factory
    # --------------------------------------------------
    def create_task(self, context: ExecutionContext) -> Optional[ReverseGeocodeTask]:
        """Cria ReverseGeocodeTask com tool_key do contexto."""
        lat = context.get("lat")
        lon = context.get("lon")
        tool_key = context.get("tool_key", "untraceable")
        return ReverseGeocodeTask(lat, lon, tool_key=tool_key)

    # --------------------------------------------------
    # Sucesso
    # --------------------------------------------------
    def on_success(self, context: ExecutionContext, result) -> None:
        """Salva resultado no contexto e atualiza dialog."""
        logger = LogUtils(
            tool=context.get("tool_key", "untraceable"),
            class_name=self.__class__.__name__,
        )
        try:
            context.set("address_data", result)

            dialog = context.get("dialog")
            if dialog:
                dialog.set_address(result)

            logger.debug(f"Address data stored: {result}")

        except Exception as e:
            logger.error(f"ReverseGeocodeStep.on_success error: {e}")

    # --------------------------------------------------
    # Erro
    # --------------------------------------------------
    def on_error(self, context: ExecutionContext, exception: Exception) -> None:
        """Limpa endereço no dialog em caso de falha."""
        logger = LogUtils(
            tool=context.get("tool_key", "untraceable"),
            class_name=self.__class__.__name__,
        )
        try:
            dialog = context.get("dialog")
            if dialog:
                dialog.set_address(None)

            logger.warning(f"Reverse geocode failed: {exception}")

        except Exception as e:
            logger.error(f"ReverseGeocodeStep.on_error handler failed: {e}")