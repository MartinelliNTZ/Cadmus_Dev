# -*- coding: utf-8 -*-
from enum import Enum
from typing import Tuple


class EvClassEnum(Enum):
    """Classificação textual do Exposure Value (EV) para fotografia aérea."""

    NOITE_ESCURO = (0, 4, "noite/escuro")
    INDOOR_SOMBRA = (5, 8, "indoor/sombra")
    NUBLADO = (9, 12, "nublado")
    LUZ_SOLAR_NORMAL = (12, 14, "luz solar normal")
    SOL_MUITO_FORTE = (15, 999, "sol muito forte/neve")

    def __init__(self, min_ev: int, max_ev: int, label: str):
        self.min_ev = min_ev
        self.max_ev = max_ev
        self.label = label

    @classmethod
    def get_label(cls, ev_value: float) -> str:
        """
        Retorna a classificação textual para um dado valor de EV.

        Args:
            ev_value: Valor de Exposure Value (EV)

        Returns:
            String com a classificação textual (ex: "luz solar normal")
        """
        if ev_value is None or ev_value < 0:
            return "Unknown"

        for ev_class in cls:
            if ev_class.min_ev <= ev_value <= ev_class.max_ev:
                return ev_class.label

        return "Unknown"

    @classmethod
    def get_level(cls, ev_value: float) -> int:
        """
        Retorna o nível (1-5) para um dado valor de EV.
        1=noite/escuro, 2=indoor/sombra, 3=nublado, 4=luz solar normal, 5=sol muito forte

        Args:
            ev_value: Valor de Exposure Value (EV)

        Returns:
            Inteiro de 1 a 5 representando o nível
        """
        if ev_value is None or ev_value < 0:
            return 3

        for i, ev_class in enumerate(cls):
            if ev_class.min_ev <= ev_value <= ev_class.max_ev:
                return i + 1

        return 3