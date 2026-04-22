# -*- coding: utf-8 -*-
"""
MathUtils — Utilitários matemáticos para cálculos de azimute e estatísticas circulares
"""
import math

class MathUtils:
    @staticmethod
    def angular_diff(a: float, b: float) -> float:
        """Diferença angular mínima em [0, 180]."""
        d = abs(a - b) % 360.0
        return min(d, 360.0 - d)

    @staticmethod
    def circular_variance(angles: list[float]) -> float:
        """
        Variância circular (R-bar), em [0, 1].
        0 = todos iguais (mínima variância), 1 = máxima dispersão.
        Referência: Fisher (1993), Statistical Analysis of Circular Data.
        """
        if not angles:
            return 1.0
        n = len(angles)
        rad = [math.radians(a) for a in angles]
        s = sum(math.sin(r) for r in rad) / n
        c = sum(math.cos(r) for r in rad) / n
        r_bar = math.sqrt(s * s + c * c)
        return 1.0 - r_bar  # 0 = concentrado, 1 = disperso

    @staticmethod
    def circular_mean(angles: list[float]) -> float:
        """Média circular em graus."""
        if not angles:
            return 0.0
        rad = [math.radians(a) for a in angles]
        s = sum(math.sin(r) for r in rad)
        c = sum(math.cos(r) for r in rad)
        return math.degrees(math.atan2(s, c)) % 360.0

    @staticmethod
    def weighted_circular_mean(angles: list[float], weights: list[float]) -> float:
        """
        Média circular ponderada por velocidade.
        Pontos lentos (curva) têm peso menor, pontos rápidos (faixa) dominam.
        """
        if not angles:
            return 0.0
        total_w = sum(weights)
        if total_w == 0:
            return MathUtils.circular_mean(angles)
        rad = [math.radians(a) for a in angles]
        s = sum(math.sin(r) * w for r, w in zip(rad, weights)) / total_w
        c = sum(math.cos(r) * w for r, w in zip(rad, weights)) / total_w
        return math.degrees(math.atan2(s, c)) % 360.0
