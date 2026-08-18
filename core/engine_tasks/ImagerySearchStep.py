# -*- coding: utf-8 -*-
from .BaseStep import BaseStep

from ..task.ImagerySearchTask import ImagerySearchTask


class ImagerySearchStep(BaseStep):
    """Step de busca de cenas no catálogo STAC (engine 1).

    create_task → ImagerySearchTask (roda em worker e retorna a lista de cenas).
    on_success → grava ``scenes`` no ExecutionContext.
    """

    def __init__(self):
        super().__init__()

    def name(self) -> str:
        """Identificação do step."""
        return "imagery_search"

    def create_task(self, context):
        """Fabrica a task de busca."""
        return ImagerySearchTask(context)

    def on_success(self, context, result) -> None:
        """Armazena as cenas encontradas no contexto."""
        context.set("scenes", result or [])