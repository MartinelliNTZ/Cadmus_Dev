# -*- coding: utf-8 -*-
"""
SequentialPointBreakJudge — Refactored
=======================================

DIAGNÓSTICO DOS PROBLEMAS DO ALGORITMO ANTERIOR
------------------------------------------------
Análise dos dados reais (VERDADEIRO vs shot_id) revelou três falhas estruturais:

1. CONTAMINAÇÃO DA MÉDIA CIRCULAR POR PONTOS DE CURVA
   O azimuth_mean acumula os ângulos da curva de retorno (~200–290°), fazendo
   com que os primeiros pontos da nova faixa (az ≈ 168° ou 348°) tenham delta_az
   alto artificialmente. O algoritmo os classifica como "quebra" quando na verdade
   são a ENTRADA da faixa.

2. SAÍDA DA FAIXA NÃO DETECTADA (score=0)
   O drone sai gradualmente em curva suave (delta_az ≈ 12–24° na saída),
   pontuação abaixo do limiar → a saída não é detectada. O shot_id correto
   continua sendo atribuído a pontos que já são turnaround.

3. ATRIBUIÇÃO TARDIA DO SHOT_ID (strip entry lag)
   Por causa dos problemas 1 e 2, o início real da faixa (pontos de assentamento)
   é perdido. Pontos fid=15,16,17 da faixa 9 ficam com shot_id=0.

NOVA ARQUITETURA: ESTABILIDADE FUTURA + PASSADO
-------------------------------------------------
O novo algoritmo tem dois estágios:

Estágio 1 — PASS FORWARD: Detecta transições usando janela BIDIRECIONAL
  • Calcula "estabilidade futura": quantos dos próximos K pontos têm az_instant
    dentro de ±threshold do az_instant atual → indica entrada de faixa
  • Calcula "estabilidade passada": quantos dos últimos K pontos tinham az_instant
    estável (variância baixa) → indica fim de faixa detectado retroativamente
  • Usa VELOCIDADE como âncora: pontos lentos (curva) têm peso reduzido na média
  • Detecta QUEBRA quando: estabilidade_passada alta → estabilidade_atual baixa
  • Detecta ENTRADA quando: estabilidade_futura converge para valor estável

Estágio 2 — RETROACTIVE RELABELING: Reassina os pontos de "assentamento"
  • Após identificar onde uma faixa se estabilizou, retroativamente move os N
    pontos anteriores (que tinham az crescendo em direção ao valor estável)
    para o mesmo shot_id da faixa

Estágio 3 — FUSÃO E VALIDAÇÃO (preservado e melhorado)

Métricas matemáticas adicionadas:
  • Variância circular dos últimos W pontos (detecta instabilidade)
  • Taxa de convergência de azimute (d(az)/dt)
  • Mediana ponderada por velocidade (resiste a outliers)
"""

from datetime import datetime

from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsField, QgsFeature

from ...core.config.LogUtils import LogUtils
from ...core.enum.OutputFieldKey import OutputFieldKey
from ...core.model.Field import Field
from ..ToolKeys import ToolKey
from ..vector.VectorLayerAttributes import VectorLayerAttributes
from ..vector.VectorLayerGeometry import VectorLayerGeometry
from ..vector.VectorLayerSource import VectorLayerSource

import math


# ---------------------------------------------------------------------------
# Funções matemáticas auxiliares (puras, sem dependência de QGIS)
# ---------------------------------------------------------------------------

def _angular_diff(a: float, b: float) -> float:
    """Diferença angular mínima em [0, 180]."""
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def _circular_variance(angles: list[float]) -> float:
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


def _circular_mean(angles: list[float]) -> float:
    """Média circular em graus."""
    if not angles:
        return 0.0
    rad = [math.radians(a) for a in angles]
    s = sum(math.sin(r) for r in rad)
    c = sum(math.cos(r) for r in rad)
    return math.degrees(math.atan2(s, c)) % 360.0


def _weighted_circular_mean(angles: list[float], weights: list[float]) -> float:
    """
    Média circular ponderada por velocidade.
    Pontos lentos (curva) têm peso menor, pontos rápidos (faixa) dominam.
    """
    if not angles:
        return 0.0
    total_w = sum(weights)
    if total_w == 0:
        return _circular_mean(angles)
    rad = [math.radians(a) for a in angles]
    s = sum(math.sin(r) * w for r, w in zip(rad, weights)) / total_w
    c = sum(math.cos(r) * w for r, w in zip(rad, weights)) / total_w
    return math.degrees(math.atan2(s, c)) % 360.0


def _future_stability_score(
    ordered_points: list,
    current_index: int,
    lookahead: int,
    az_threshold: float,
) -> tuple[float, float]:
    """
    Analisa os próximos `lookahead` pontos e retorna:
      (stability_ratio, converged_azimuth)

    stability_ratio ∈ [0,1]: fração de pontos que concordam com o az futuro médio.
    converged_azimuth: valor para o qual os pontos futuros convergem.

    Algoritmo:
      1. Coleta az_instant dos próximos K pontos
      2. Calcula a média circular desses pontos futuros
      3. Conta quantos estão dentro de ±threshold dessa média → ratio
    """
    n = len(ordered_points)
    future_azs = []
    for k in range(current_index + 1, min(current_index + 1 + lookahead, n)):
        prev = ordered_points[k - 1]
        curr = ordered_points[k]
        az = VectorLayerGeometry.calculate_point_azimuth(prev["point"], curr["point"])
        future_azs.append(az)

    if not future_azs:
        return 0.0, 0.0

    conv_az = _circular_mean(future_azs)
    agreed = sum(1 for a in future_azs if _angular_diff(a, conv_az) <= az_threshold)
    ratio = agreed / len(future_azs)
    return ratio, conv_az


def _past_stability(az_history: list[float], window: int) -> float:
    """
    Variância circular dos últimos `window` azimuths do histórico.
    Retorna 0 (muito estável) → 1 (muito disperso).
    """
    recent = az_history[-window:] if az_history else []
    if len(recent) < 2:
        return 1.0
    return _circular_variance(recent)


def _az_convergence_rate(az_history: list[float], window: int) -> float:
    """
    Taxa de mudança do azimute instantâneo nos últimos `window` pontos.
    Alta taxa → em curva ou saída de faixa.
    Baixa taxa → estável na faixa.
    """
    recent = az_history[-window:]
    if len(recent) < 2:
        return 0.0
    diffs = [_angular_diff(recent[i], recent[i - 1]) for i in range(1, len(recent))]
    return sum(diffs) / len(diffs)


# ---------------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------------

class SequentialPointBreakJudge:
    """
    Juiz de segmentação de sequências de pontos em faixas de voo.

    Algoritmo bidirecional com análise de estabilidade futura e passada.
    """

    OUTPUT_FIELDS = {
        OutputFieldKey.SHOT_ID: Field(
            label="Shot ID",
            attribute="shot_id",
            description="Identificador único do segmento de tiro/faixa.",
            type=QVariant.Int,
            length=10,
            precision=0,
        ),
        OutputFieldKey.SHOT_VALID: Field(
            label="Shot Valid",
            attribute="shot_valid",
            description="Indica se o tiro possui pontos suficientes para ser válido.",
            type=QVariant.Int,
            length=1,
            precision=0,
        ),
        OutputFieldKey.SCORE: Field(
            label="Score",
            attribute="score",
            description="Pontuação de quebra (direção + continuidade).",
            type=QVariant.Int,
            length=10,
            precision=0,
        ),
        OutputFieldKey.SCORE_DIRECTION: Field(
            label="Score Direction",
            attribute="score_direction",
            description="Componente de quebra por mudança de direção.",
            type=QVariant.Int,
            length=10,
            precision=0,
        ),
        OutputFieldKey.SCORE_CONTINUITY: Field(
            label="Score Continuity",
            attribute="score_continuity",
            description="Componente de quebra por descontinuidade temporal/espacial.",
            type=QVariant.Int,
            length=10,
            precision=0,
        ),
        OutputFieldKey.SEG_TYPE: Field(
            label="Segment Type",
            attribute="seg_type",
            description="Tipo: 'faixa' ou 'bordadura'.",
            type=QVariant.String,
            length=20,
            precision=0,
        ),
        OutputFieldKey.AZIMUTH_INSTANT: Field(
            label="Azimuth Instant",
            attribute="azimuth_instant",
            description="Azimute instantâneo entre pontos consecutivos.",
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        OutputFieldKey.AZIMUTH_MEAN: Field(
            label="Azimuth Mean",
            attribute="azimuth_mean",
            description="Média circular ponderada por velocidade.",
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        OutputFieldKey.DELTA_AZIMUTH: Field(
            label="Delta Azimuth",
            attribute="delta_azimuth",
            description="Diferença angular entre azimute instantâneo e média.",
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        OutputFieldKey.DELTA_TIME: Field(
            label="Delta Time",
            attribute="delta_time",
            description="Diferença de tempo entre pontos consecutivos (s).",
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        OutputFieldKey.DELTA_DISTANCE: Field(
            label="Delta Distance",
            attribute="delta_distance",
            description="Distância entre pontos consecutivos (m).",
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
        OutputFieldKey.VELOCITY_INSTANT: Field(
            label="Velocity Instant",
            attribute="velocity_instant",
            description="Velocidade instantânea (m/s).",
            type=QVariant.Double,
            length=20,
            precision=8,
        ),
    }

    def __init__(
        self,
        *,
        layer=None,
        source_path: str = "",
        tool_key: str = ToolKey.UNTRACEABLE,
    ):
        self.layer = layer
        self.source_path = source_path or (layer.source() if layer is not None else "")
        self.tool_key = tool_key
        self.logger = LogUtils(tool=tool_key, class_name=self.__class__.__name__)

    # ------------------------------------------------------------------
    # Ponto de entrada público
    # ------------------------------------------------------------------

    def judge(
        self,
        *,
        field_id: str,
        field_time: str,
        point_frequency_seconds: float,
        strip_width_meters: float,
        # Janela para média circular (histórico de azimuths passados)
        azimuth_window: int = 10,
        # Thresholds de azimute para score de direção
        light_azimuth_threshold: float = 20.0,
        severe_azimuth_threshold: float = 45.0,
        # Score mínimo para candidatar quebra
        minimum_break_score: int = 3,
        # Mínimo de pontos para faixa válida
        minimum_point_count: int = 20,
        # Multiplicador de tolerância de tempo
        time_tolerance_multiplier: float = 3.0,
        # Janela de confirmação prospectiva (quantos pontos futuros devem confirmar)
        confirmation_window: int = 5,
        min_confirmed: int = 2,
        # Parâmetros de bordadura (mantidos)
        border_azimuth_threshold: float = 90.0,
        border_speed_threshold: float = 1.0,
        border_distance_threshold: float = 5.0,
        # ---------------------------------------------------------------
        # NOVOS PARÂMETROS
        # ---------------------------------------------------------------
        # Lookahead para detecção de estabilidade futura
        future_stability_window: int = 8,
        # Limiar de estabilidade futura: se ratio >= este valor, é entrada de faixa
        future_stability_threshold: float = 0.75,
        # Limiar de az para considerar ponto "dentro" do cluster futuro
        future_az_cluster_threshold: float = 15.0,
        # Variância circular máxima para considerar histórico "estável"
        past_stability_max_variance: float = 0.08,
        # Janela de variância passada
        past_stability_window: int = 6,
        # Taxa de convergência máxima (°/ponto) para considerar estável
        convergence_rate_threshold: float = 10.0,
        # Janela retroativa: quantos pontos anteriores reatribuir ao novo shot
        retroactive_relabel_window: int = 5,
        # Peso mínimo de velocidade (evita divisão por zero em pontos parados)
        min_velocity_weight: float = 0.5,
        # Tolerância de azimute para fusão de tiros pequenos
        fusion_azimuth_tolerance: float = 10.0,
        # Número máximo de pontos de desvio a ignorar (outlier skip)
        max_desvio: int = 3,
        conflict_resolver=None,
    ):
        """Executa o julgamento bidirecional de segmentação."""
        layer = self._load_layer()
        self._validate_layer(layer, field_id, field_time)
        field_name_map = self._resolve_output_fields(layer, conflict_resolver=conflict_resolver)

        ordered = self._load_ordered_points(layer, field_id, field_time)
        if not ordered:
            raise RuntimeError("Nenhum ponto válido encontrado.")

        self.logger.info(
            "Iniciando julgamento bidirecional",
            source_path=self.source_path,
            features=len(ordered),
        )

        import time
        t0 = time.time()

        # Estágio 1: Avaliação bidirecional
        updates = self._evaluate_bidirectional(
            ordered_points=ordered,
            layer=layer,
            point_frequency_seconds=point_frequency_seconds,
            strip_width_meters=strip_width_meters,
            azimuth_window=azimuth_window,
            light_azimuth_threshold=light_azimuth_threshold,
            severe_azimuth_threshold=severe_azimuth_threshold,
            minimum_break_score=minimum_break_score,
            time_tolerance_multiplier=time_tolerance_multiplier,
            confirmation_window=confirmation_window,
            min_confirmed=min_confirmed,
            border_azimuth_threshold=border_azimuth_threshold,
            border_speed_threshold=border_speed_threshold,
            border_distance_threshold=border_distance_threshold,
            future_stability_window=future_stability_window,
            future_stability_threshold=future_stability_threshold,
            future_az_cluster_threshold=future_az_cluster_threshold,
            past_stability_max_variance=past_stability_max_variance,
            past_stability_window=past_stability_window,
            convergence_rate_threshold=convergence_rate_threshold,
            retroactive_relabel_window=retroactive_relabel_window,
            min_velocity_weight=min_velocity_weight,
            max_desvio=max_desvio,
        )

        # Estágio 2: Marcar validade, fusão, órfãos
        updates = self._postprocess(updates, minimum_point_count, fusion_azimuth_tolerance)

        result_layer = self._create_memory_layer_with_updates(layer, updates, field_name_map)

        shot_sizes = {}
        for v in updates.values():
            sid = v[OutputFieldKey.SHOT_ID.value]
            shot_sizes[sid] = shot_sizes.get(sid, 0) + 1

        valid_shots = sum(1 for s, sz in shot_sizes.items() if sz >= minimum_point_count and s != 0)
        summary = {
            "total_points": len(ordered),
            "total_shots": len(shot_sizes),
            "valid_shots": valid_shots,
            "invalid_shots": len(shot_sizes) - valid_shots,
            "source_path": self.source_path,
            "field_name_map": field_name_map,
            "result_layer": result_layer,
        }
        self.logger.info(
            "Julgamento concluído",
            elapsed_seconds=round(time.time() - t0, 2),
            summary=summary,
        )
        return summary

    # ------------------------------------------------------------------
    # Estágio 1: Avaliação bidirecional
    # ------------------------------------------------------------------

    def _evaluate_bidirectional(
        self,
        *,
        ordered_points,
        layer,
        point_frequency_seconds,
        strip_width_meters,
        azimuth_window,
        light_azimuth_threshold,
        severe_azimuth_threshold,
        minimum_break_score,
        time_tolerance_multiplier,
        confirmation_window,
        min_confirmed,
        border_azimuth_threshold,
        border_speed_threshold,
        border_distance_threshold,
        future_stability_window,
        future_stability_threshold,
        future_az_cluster_threshold,
        past_stability_max_variance,
        past_stability_window,
        convergence_rate_threshold,
        retroactive_relabel_window,
        min_velocity_weight,
        max_desvio,
    ):
        """
        Loop principal com lógica bidirecional.

        Para cada ponto i, avalia:
          PASSADO: variância circular dos últimos K azimuths (estabilidade histórica)
          FUTURO: ratio de convergência dos próximos K azimuths (estabilidade prospectiva)

        Regras de quebra:
          R1 (break claro): score >= limiar E passado era estável E futuro NÃO converge
              → drone saiu da faixa e está em curva
          R2 (não-break por entrada de faixa): score >= limiar MAS futuro converge
              → drone está entrando em nova faixa (az ainda não estabilizou)
              → NÃO quebra; retroativamente reatribui pontos de assentamento

        Regra de relabeling retroativo:
          Quando detectamos que estamos DENTRO de uma faixa estável (past_variance baixa
          E future_stability alta), verificamos se os N pontos anteriores tinham az
          "a caminho" do az atual → se sim, reatribuímos ao shot atual.
        """
        import time
        t0 = time.time()

        n = len(ordered_points)
        updates = {}
        az_history: list[float] = []          # azimuths instantâneos acumulados
        vel_history: list[float] = []          # velocidades acumuladas (para peso)
        current_shot_id = 1
        shot_start_index = 0  # índice onde o shot atual começou

        # Pré-calcula azimuths instantâneos para toda a sequência (rápido, evita
        # recalcular nas janelas de lookahead)
        precomputed_az: list[float] = [0.0]  # índice 0 não tem predecessor
        for i in range(1, n):
            az = VectorLayerGeometry.calculate_point_azimuth(
                ordered_points[i - 1]["point"], ordered_points[i]["point"]
            )
            precomputed_az.append(az)

        # Pré-calcula deltas de tempo e distância
        precomputed_dt: list[float] = [0.0]
        precomputed_dd: list[float] = [0.0]
        precomputed_vel: list[float] = [0.0]
        for i in range(1, n):
            dt = max(0.0, ordered_points[i]["timestamp"] - ordered_points[i - 1]["timestamp"])
            dd = VectorLayerGeometry.measure_distance_between_points(
                ordered_points[i - 1]["point"], ordered_points[i]["point"], layer.crs()
            )
            vel = dd / dt if dt > 0 else 0.0
            precomputed_dt.append(dt)
            precomputed_dd.append(dd)
            precomputed_vel.append(vel)

        # Primeiro ponto
        updates[ordered_points[0]["fid"]] = self._build_default_output(current_shot_id)

        progress_interval = max(1, n // 10)

        for i in range(1, n):
            if i % progress_interval == 0:
                self.logger.info(
                    f"Processando {i}/{n} ({100*i/n:.0f}%)",
                    shot_id=current_shot_id,
                )

            instant_az = precomputed_az[i]
            delta_time = precomputed_dt[i]
            delta_distance = precomputed_dd[i]
            instant_speed = precomputed_vel[i]

            # --- Média circular ponderada por velocidade (histórico) ---
            w = max(min_velocity_weight, instant_speed)
            recent_az = az_history[-azimuth_window:] if az_history else []
            recent_vel = vel_history[-azimuth_window:] if vel_history else []
            mean_az = (
                _weighted_circular_mean(recent_az, [max(min_velocity_weight, v) for v in recent_vel])
                if recent_az else instant_az
            )
            delta_azimuth = _angular_diff(instant_az, mean_az)

            # --- Métricas de estabilidade ---
            past_var = _past_stability(az_history, past_stability_window)
            past_stable = past_var <= past_stability_max_variance

            conv_rate = _az_convergence_rate(az_history, past_stability_window)
            past_converging = conv_rate > convergence_rate_threshold

            # Lookahead: estabilidade futura usando az pré-computados
            future_azs = precomputed_az[i + 1: i + 1 + future_stability_window]
            future_az_mean = _circular_mean(future_azs) if future_azs else instant_az
            future_stable_count = sum(
                1 for a in future_azs
                if _angular_diff(a, future_az_mean) <= future_az_cluster_threshold
            )
            future_ratio = future_stable_count / len(future_azs) if future_azs else 0.0
            future_stable = future_ratio >= future_stability_threshold

            # --- Scores ---
            score_direction = 0
            if delta_azimuth > light_azimuth_threshold:
                score_direction += 1
            if delta_azimuth > severe_azimuth_threshold:
                score_direction += 2

            score_continuity = self._apply_time_score(
                score=0,
                delta_time=delta_time,
                point_frequency_seconds=point_frequency_seconds,
                time_tolerance_multiplier=time_tolerance_multiplier,
            )
            if delta_distance > float(strip_width_meters) * 0.8:
                score_continuity += 1

            total_score = score_direction + score_continuity

            # --- Tipo de segmento ---
            is_border = (
                delta_azimuth > border_azimuth_threshold
                and instant_speed < border_speed_threshold
                and delta_distance < border_distance_threshold
            )
            seg_type = "bordadura" if is_border else "faixa"

            # -------------------------------------------------------------------
            # LÓGICA CENTRAL DE QUEBRA (bidirecional)
            # -------------------------------------------------------------------
            should_break = False

            if total_score >= minimum_break_score:
                if future_stable:
                    # R2: Estamos ENTRANDO em nova faixa, não quebrando aleatoriamente.
                    # O alto score é ruído de transição; a nova faixa já está convergindo.
                    # → Quebramos normalmente (nova faixa), mas rotulamos corretamente.
                    should_break = True
                    # Relabeling retroativo: pontos de assentamento vão para o novo shot
                    # (tratado após incrementar shot_id abaixo)
                elif past_stable and not past_converging:
                    # R1: Saímos de uma faixa estável e não há convergência futura clara.
                    # → Quebra por saída de faixa.
                    # Confirmar com janela prospectiva
                    confirmed = 0
                    for j in range(i + 1, min(i + 1 + confirmation_window, n)):
                        conf_az = precomputed_az[j]
                        conf_delta = _angular_diff(conf_az, mean_az)
                        conf_score = 0
                        if conf_delta > light_azimuth_threshold:
                            conf_score += 1
                        if conf_delta > severe_azimuth_threshold:
                            conf_score += 2
                        if conf_score >= minimum_break_score:
                            confirmed += 1
                    if confirmed >= min_confirmed:
                        should_break = True
                else:
                    # Caso ambíguo: score alto mas passado não era estável e futuro
                    # não converge → provavelmente meio da curva, ignorar.
                    # Tentar outlier skip
                    for skip in range(1, max_desvio + 1):
                        si = i + skip
                        if si < n:
                            skip_az = precomputed_az[si]
                            skip_delta = _angular_diff(skip_az, mean_az)
                            skip_score_dir = 0
                            if skip_delta > light_azimuth_threshold:
                                skip_score_dir += 1
                            if skip_delta > severe_azimuth_threshold:
                                skip_score_dir += 2
                            skip_dt = max(0.0, ordered_points[si]["timestamp"] - ordered_points[i - 1]["timestamp"])
                            skip_score_cont = self._apply_time_score(
                                score=0,
                                delta_time=skip_dt,
                                point_frequency_seconds=point_frequency_seconds,
                                time_tolerance_multiplier=time_tolerance_multiplier,
                            )
                            if skip_score_dir + skip_score_cont < minimum_break_score:
                                break  # não precisa quebrar

            # Quebra confirmada: incrementa shot e aplica relabeling retroativo
            if should_break:
                current_shot_id += 1
                shot_start_index = i

                # RELABELING RETROATIVO
                # Se o futuro é estável (R2), os pontos imediatamente antes de `i`
                # podem ser "assentamento" da mesma nova faixa.
                # Reatribuímos pontos anteriores cujo az_instant já estava a caminho
                # de future_az_mean ao novo shot_id.
                if future_stable and retroactive_relabel_window > 0:
                    relabel_count = 0
                    for back in range(1, retroactive_relabel_window + 1):
                        bi = i - back
                        if bi < 0:
                            break
                        back_fid = ordered_points[bi]["fid"]
                        if back_fid not in updates:
                            break
                        back_az = precomputed_az[bi] if bi > 0 else 0.0
                        back_diff = _angular_diff(back_az, future_az_mean)
                        # Reatribuir se o az já estava "na direção" da nova faixa
                        # (diferença aceitável e decrescente em direção ao alvo)
                        if back_diff <= future_az_cluster_threshold * 2.0:
                            updates[back_fid][OutputFieldKey.SHOT_ID.value] = current_shot_id
                            relabel_count += 1
                        else:
                            break  # Para ao encontrar ponto muito longe
                    if relabel_count > 0:
                        self.logger.debug(
                            f"Relabeling retroativo: {relabel_count} pontos → shot {current_shot_id}"
                        )

            updates[ordered_points[i]["fid"]] = {
                OutputFieldKey.SHOT_ID.value: current_shot_id,
                OutputFieldKey.SHOT_VALID.value: 0,
                OutputFieldKey.SCORE.value: int(total_score),
                OutputFieldKey.SCORE_DIRECTION.value: int(score_direction),
                OutputFieldKey.SCORE_CONTINUITY.value: int(score_continuity),
                OutputFieldKey.SEG_TYPE.value: seg_type,
                OutputFieldKey.AZIMUTH_INSTANT.value: float(instant_az),
                OutputFieldKey.AZIMUTH_MEAN.value: float(mean_az),
                OutputFieldKey.DELTA_AZIMUTH.value: float(delta_azimuth),
                OutputFieldKey.DELTA_TIME.value: float(delta_time),
                OutputFieldKey.DELTA_DISTANCE.value: float(delta_distance),
                OutputFieldKey.VELOCITY_INSTANT.value: float(instant_speed),
            }

            az_history.append(instant_az)
            vel_history.append(instant_speed)

        self.logger.info(
            "Avaliação bidirecional concluída",
            elapsed=round(time.time() - t0, 2),
            final_shot_id=current_shot_id,
        )
        return updates

    # ------------------------------------------------------------------
    # Estágio 2: Pós-processamento
    # ------------------------------------------------------------------

    def _postprocess(self, updates, minimum_point_count, fusion_azimuth_tolerance):
        """Fusão de pequenos shots + marcação de validade + órfãos → shot_id=0."""

        def shot_sizes(upd):
            sizes = {}
            for v in upd.values():
                sid = v[OutputFieldKey.SHOT_ID.value]
                sizes[sid] = sizes.get(sid, 0) + 1
            return sizes

        # Fusão de tiros pequenos consecutivos com az similar
        updates = self._fuse_small_shots(updates, minimum_point_count, fusion_azimuth_tolerance)

        sizes = shot_sizes(updates)

        # Marcar válidos e órfãos
        for fid, values in updates.items():
            sid = values[OutputFieldKey.SHOT_ID.value]
            sz = sizes.get(sid, 0)
            if sz < minimum_point_count:
                values[OutputFieldKey.SHOT_ID.value] = 0
                values[OutputFieldKey.SHOT_VALID.value] = 0
            else:
                values[OutputFieldKey.SHOT_VALID.value] = 1

        return updates

    def _fuse_small_shots(self, updates, minimum_point_count, fusion_azimuth_tolerance):
        """Funde tiros pequenos consecutivos com azimute médio similar."""
        if not updates:
            return updates

        shots: dict[int, list] = {}
        for fid, values in updates.items():
            sid = values[OutputFieldKey.SHOT_ID.value]
            shots.setdefault(sid, []).append((fid, values))

        shot_stats = {}
        for sid, features in shots.items():
            azs = [v[OutputFieldKey.AZIMUTH_MEAN.value] for _, v in features if v[OutputFieldKey.AZIMUTH_MEAN.value] > 0]
            shot_stats[sid] = {
                "size": len(features),
                "mean_az": _circular_mean(azs) if azs else 0.0,
            }

        sorted_ids = sorted(shot_stats)
        fusions = []
        for i in range(len(sorted_ids) - 1):
            a, b = sorted_ids[i], sorted_ids[i + 1]
            if (shot_stats[a]["size"] < minimum_point_count and
                    shot_stats[b]["size"] < minimum_point_count):
                if _angular_diff(shot_stats[a]["mean_az"], shot_stats[b]["mean_az"]) <= fusion_azimuth_tolerance:
                    fusions.append((a, b))

        for from_id, to_id in fusions:
            if from_id in shots:
                for _, values in shots[from_id]:
                    values[OutputFieldKey.SHOT_ID.value] = to_id

        self.logger.info("Fusão de tiros pequenos", fusions=len(fusions))
        return updates

    # ------------------------------------------------------------------
    # Métodos de infraestrutura (inalterados, levemente limpos)
    # ------------------------------------------------------------------

    def _load_layer(self):
        if self.layer is not None:
            return self.layer
        layer = VectorLayerSource.load_vector_layer_from_source_path(
            self.source_path, external_tool_key=self.tool_key
        )
        if not layer:
            raise RuntimeError("Não foi possível carregar a camada.")
        return layer

    def _validate_layer(self, layer, field_id, field_time):
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            raise RuntimeError("Camada vetorial inválida.")
        if layer.geometryType() != QgsWkbTypes.PointGeometry:
            raise RuntimeError("A camada deve ser do tipo ponto.")
        if layer.fields().lookupField(field_id) == -1:
            raise RuntimeError(f"Campo de ID não encontrado: {field_id}")
        if layer.fields().lookupField(field_time) == -1:
            raise RuntimeError(f"Campo de timestamp não encontrado: {field_time}")

    def _load_ordered_points(self, layer, field_id, field_time):
        import time
        t0 = time.time()
        ordered = []
        for feature in layer.getFeatures():
            geometry = feature.geometry()
            if not geometry or geometry.isEmpty():
                continue
            point = VectorLayerGeometry.get_representative_point(geometry)
            if point is None:
                continue
            timestamp = self._parse_timestamp(feature.attribute(field_time))
            if timestamp is None:
                continue
            ordered.append({
                "fid": feature.id(),
                "seq_id_sort": self._build_sort_key(feature.attribute(field_id)),
                "timestamp": timestamp,
                "point": point,
            })
        ordered.sort(key=lambda x: (x["seq_id_sort"], x["timestamp"], x["fid"]))
        self.logger.info(
            "Pontos carregados",
            valid=len(ordered),
            elapsed=round(time.time() - t0, 2),
        )
        return ordered

    def _resolve_output_fields(self, layer, *, conflict_resolver=None):
        max_length = 10 if self.source_path.lower().endswith(".shp") else 255
        resolved = {}
        for logical_key, field_spec in self.OUTPUT_FIELDS.items():
            field_name = VectorLayerAttributes.resolve_output_field_name(
                layer, field_spec.attribute,
                conflict_resolver=conflict_resolver,
                max_length=max_length,
            )
            if field_name is None:
                raise RuntimeError("Operação cancelada pelo usuário.")
            resolved[logical_key] = field_name
        return resolved

    def _build_default_output(self, shot_id: int) -> dict:
        return {
            OutputFieldKey.SHOT_ID.value: shot_id,
            OutputFieldKey.SHOT_VALID.value: 0,
            OutputFieldKey.SCORE.value: 0,
            OutputFieldKey.SCORE_DIRECTION.value: 0,
            OutputFieldKey.SCORE_CONTINUITY.value: 0,
            OutputFieldKey.SEG_TYPE.value: "faixa",
            OutputFieldKey.AZIMUTH_INSTANT.value: 0.0,
            OutputFieldKey.AZIMUTH_MEAN.value: 0.0,
            OutputFieldKey.DELTA_AZIMUTH.value: 0.0,
            OutputFieldKey.DELTA_TIME.value: 0.0,
            OutputFieldKey.DELTA_DISTANCE.value: 0.0,
            OutputFieldKey.VELOCITY_INSTANT.value: 0.0,
        }

    @staticmethod
    def _apply_time_score(*, score, delta_time, point_frequency_seconds, time_tolerance_multiplier):
        threshold = float(point_frequency_seconds) * float(time_tolerance_multiplier)
        if delta_time > threshold:
            score += 1
        if delta_time > threshold * 3.0:
            score += 3
        return score

    @staticmethod
    def _build_sort_key(value):
        try:
            return (0, int(value))
        except Exception:
            try:
                return (0, float(value))
            except Exception:
                return (1, str(value or "").strip().lower())

    @staticmethod
    def _parse_timestamp(value):
        if value is None:
            return None
        if hasattr(value, "toSecsSinceEpoch"):
            try:
                return float(value.toSecsSinceEpoch())
            except Exception:
                pass
        if isinstance(value, datetime):
            return float(value.timestamp())
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return None
        for parser in (
            lambda x: datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp(),
            lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S").timestamp(),
            lambda x: datetime.strptime(x, "%d/%m/%Y %H:%M:%S").timestamp(),
            lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S").timestamp(),
            lambda x: datetime.strptime(x, "%Y%m%d%H%M%S").timestamp(),
            lambda x: datetime.strptime(x, "%Y%m%d_%H%M%S").timestamp(),
        ):
            try:
                return float(parser(text))
            except Exception:
                continue
        digits = "".join(ch for ch in text if ch.isdigit())
        if len(digits) == 14:
            try:
                return float(datetime.strptime(digits, "%Y%m%d%H%M%S").timestamp())
            except Exception:
                pass
        try:
            return float(text)
        except Exception:
            return None

    @staticmethod
    def _create_memory_layer_with_updates(layer, updates, field_name_map):
        import time
        t0 = time.time()

        uri = f"Point?crs={layer.crs().authid()}"
        new_layer = QgsVectorLayer(uri, f"{layer.name()}_segmentado", "memory")
        if not new_layer.isValid():
            raise RuntimeError("Falha ao criar camada de memória.")

        new_fields = layer.fields()
        for logical_key, field_spec in SequentialPointBreakJudge.OUTPUT_FIELDS.items():
            field_name = field_name_map[logical_key]
            if new_fields.lookupField(field_name) == -1:
                new_fields.append(
                    QgsField(field_name, field_spec.type,
                             len=field_spec.length, prec=field_spec.precision)
                )

        new_layer.dataProvider().addAttributes(new_fields)
        new_layer.updateFields()
        new_layer.startEditing()

        for feature in layer.getFeatures():
            fid = feature.id()
            if fid not in updates:
                continue
            new_feature = QgsFeature(new_layer.fields())
            new_feature.setGeometry(feature.geometry())
            for field in feature.fields():
                new_feature.setAttribute(field.name(), feature.attribute(field.name()))
            for attr_key, attr_val in updates[fid].items():
                resolved = field_name_map.get(attr_key, attr_key)
                idx = new_layer.fields().lookupField(resolved)
                if idx >= 0:
                    new_feature.setAttribute(idx, attr_val)
            new_layer.addFeature(new_feature)

        new_layer.commitChanges()
        new_layer.updateFields()

        LogUtils(tool=ToolKey.UNTRACEABLE, class_name="SequentialPointBreakJudge").info(
            "Camada de memória criada",
            features=new_layer.featureCount(),
            elapsed=round(time.time() - t0, 2),
        )
        return new_layer