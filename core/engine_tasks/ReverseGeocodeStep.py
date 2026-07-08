# -*- coding: utf-8 -*-
from typing import Optional

from .BaseStep import BaseStep
from .ExecutionContext import ExecutionContext
from ..task.ReverseGeocodeTask import ReverseGeocodeTask
from ..config.LogUtils import LogUtils


class ReverseGeocodeStep(BaseStep):
    """
    Step que executa reverse geocode para obter endereço a partir de coordenadas.

    Totalmente desacoplado de UI — apenas persiste o resultado no ExecutionContext
    como "address_data". O consumidor da pipeline (qualquer plugin) lê o contexto
    via callback on_finished da engine para atualizar sua própria UI.

    Uso em qualquer pipeline:
        context = ExecutionContext({"lat": -23.5, "lon": -46.6, "tool_key": "meu_plugin"})
        engine = AsyncPipelineEngine([ReverseGeocodeStep()], context)
        engine.on_finished = lambda ctx: meu_dialog.set_address(ctx.get("address_data"))
        engine.start()
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
        """
        Persiste resultado do reverse geocode no ExecutionContext.

        O resultado fica disponível como "address_data" para qualquer
        consumidor da pipeline ler via context.get("address_data").
        """
        logger = LogUtils(
            tool=context.get("tool_key", "untraceable"),
            class_name=self.__class__.__name__,
        )
        try:
            context.set("address_data", result)
            logger.debug(f"Address data stored: {result}")
        except Exception as e:
            logger.error(f"ReverseGeocodeStep.on_success error: {e}")

    # --------------------------------------------------
    # Erro
    # --------------------------------------------------
    def on_error(self, context: ExecutionContext, exception: Exception) -> None:
        """Registra falha no log — sem acoplamento de UI."""
        logger = LogUtils(
            tool=context.get("tool_key", "untraceable"),
            class_name=self.__class__.__name__,
        )
        logger.warning(f"Reverse geocode failed: {exception}")
