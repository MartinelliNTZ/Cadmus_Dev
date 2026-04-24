# -*- coding: utf-8 -*-
"""
SequentialPointBreakJudge — Professional Refactoring
=======================================
Arquitetura modularizada usando JudgeConfig e Ways Engine para processamento adaptativo.
"""

import math
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Any

from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsField, QgsFeature
from qgis.PyQt.QtCore import QVariant

from ...core.config.LogUtils import LogUtils
from ...core.enum.OutputFieldKey import StripOutputFieldKey
from ..ToolKeys import ToolKey
from ..vector.VectorLayerAttributes import VectorLayerAttributes
from ..vector.VectorLayerGeometry import VectorLayerGeometry
from ..vector.VectorLayerSource import VectorLayerSource
from ..MathUtils import MathUtils

# ---------------------------------------------------------------------------
# Enums e Modelos de Dados
# ---------------------------------------------------------------------------

class JudgeScenario(Enum):
    STRAIGHT_TIME = auto()
    CURVE_TIME = auto()
    BOTH_TIME = auto()
    STRAIGHT_NO_TIME = auto()
    CURVE_NO_TIME = auto()
    BOTH_NO_TIME = auto()


@dataclass
class JudgeConfig:
    """Encapsula parâmetros de sensibilidade e operacionais do julgamento."""
    point_frequency_seconds: float = 1.0
    strip_width_meters: float = 20.0
    azimuth_window: int = 10
    light_azimuth_threshold: float = 20.0
    severe_azimuth_threshold: float = 45.0
    minimum_break_score: int = 3
    minimum_point_count: int = 20
    time_tolerance_multiplier: float = 3.0
    confirmation_window: int = 3
    min_confirmed: int = 2
    max_desvio: int = 3
    future_stability_window: int = 8
    future_stability_threshold: float = 0.75
    future_az_cluster_threshold: float = 15.0
    past_stability_max_variance: float = 0.08
    past_stability_window: int = 6
    convergence_rate_threshold: float = 10.0
    retroactive_relabel_window: int = 5
    min_velocity_weight: float = 0.5
    fusion_azimuth_tolerance: float = 10.0
    border_azimuth_threshold: float = 90.0
    border_speed_threshold: float = 1.0
    border_distance_threshold: float = 5.0
    path_mode: str = "both"
    use_time: bool = True


@dataclass
class PointMetrics:
    """Dados pré-calculados para um ponto na sequência."""
    az: float = 0.0
    dt: float = 0.0
    dd: float = 0.0
    vel: float = 0.0


# ---------------------------------------------------------------------------
# Componentes Internos (Módulos de Responsabilidade)
# ---------------------------------------------------------------------------

class ScenarioResolver:
    """Identifica e valida o cenário de processamento."""

    @staticmethod
    def resolve(path_mode: str, has_time: bool) -> JudgeScenario:
        mode = path_mode.lower()
        if has_time:
            if "straight" in mode: return JudgeScenario.STRAIGHT_TIME
            if "curve" in mode: return JudgeScenario.CURVE_TIME
            return JudgeScenario.BOTH_TIME
        else:
            if "straight" in mode: return JudgeScenario.STRAIGHT_NO_TIME
            if "curve" in mode: return JudgeScenario.CURVE_NO_TIME
            return JudgeScenario.BOTH_NO_TIME


class ParameterTuner:
    """Ajusta thresholds com base no cenário (Adaptive Ways Engine)."""

    @staticmethod
    def tune(config: JudgeConfig, scenario: JudgeScenario):
        if scenario in (JudgeScenario.STRAIGHT_TIME, JudgeScenario.STRAIGHT_NO_TIME):
            config.light_azimuth_threshold *= 0.8  # Mais sensível
            config.min_confirmed = 1
        elif scenario in (JudgeScenario.CURVE_TIME, JudgeScenario.CURVE_NO_TIME):
            config.light_azimuth_threshold *= 1.4  # Mais tolerante
            config.minimum_break_score += 1
            config.past_stability_max_variance *= 1.5


def _future_stability_score(precomputed_az: list[float], current_index: int, window: int, cluster_threshold: float) -> tuple[float, float]:
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
    future_azs = precomputed_az[current_index + 1: current_index + 1 + window]
    if not future_azs:
        return 0.0, 0.0
    conv_az = MathUtils.circular_mean(future_azs)
    agreed = sum(1 for a in future_azs if MathUtils.angular_diff(a, conv_az) <= cluster_threshold)
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
    return MathUtils.circular_variance(recent)


def _az_convergence_rate(az_history: list[float], window: int) -> float:
    """
    Taxa de mudança do azimute instantâneo nos últimos `window` pontos.
    Alta taxa → em curva ou saída de faixa.
    Baixa taxa → estável na faixa.
    """
    recent = az_history[-window:]
    if len(recent) < 2:
        return 0.0
    diffs = [MathUtils.angular_diff(recent[i], recent[i - 1]) for i in range(1, len(recent))]
    return sum(diffs) / len(diffs)


class SequentialPointBreakJudge:
    """
    Juiz de segmentação de sequências de pontos em faixas de voo.
    Refatorado para suportar o Ways Engine (Cenários Adaptativos).
    """
    
    from ..StringManager import StringManager
    # Campos de saída definidos centralmente no StringManager
    DIVIDE_STRIP_FIELDS = StringManager.DIVIDE_STRIP_FIELDS

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

    # -------------------------------------------------------------------
    # ORCHESTRATOR (Judge Orchestrator)
    # -------------------------------------------------------------------
    def judge(    
        self,
        *,
        field_id: str,
        field_time: str = None,
        point_frequency_seconds: float,
        strip_width_meters: float,
        azimuth_window: int = 10,
        light_azimuth_threshold: float = 20.0,
        severe_azimuth_threshold: float = 45.0,
        minimum_break_score: int = 3,
        minimum_point_count: int = 20,
        time_tolerance_multiplier: float = 3.0,
        confirmation_window: int = 5,
        min_confirmed: int = 2,
        border_azimuth_threshold: float = 90.0,
        border_speed_threshold: float = 1.0,
        border_distance_threshold: float = 5.0,
        future_stability_window: int = 8,
        future_stability_threshold: float = 0.75,
        future_az_cluster_threshold: float = 15.0,
        past_stability_max_variance: float = 0.08,
        past_stability_window: int = 6,
        convergence_rate_threshold: float = 10.0,
        retroactive_relabel_window: int = 5,
        min_velocity_weight: float = 0.5,
        fusion_azimuth_tolerance: float = 10.0,
        max_desvio: int = 3,
        conflict_resolver=None,
        recap: bool = False,
        path_mode: str = "both",
    ):
        """Executa o julgamento bidirecional de segmentação, com repescagem opcional."""
        layer = self._load_layer()
        self._validate_layer(layer, field_id, field_time)
        field_name_map = self._resolve_output_fields(layer, conflict_resolver=conflict_resolver)

        ordered_points = self._load_ordered_points(layer, field_id, field_time)
        if not ordered_points:
            raise RuntimeError("Nenhum ponto válido encontrado.")

        # Configuração e Ways Engine
        config = JudgeConfig(
            point_frequency_seconds=point_frequency_seconds,
            strip_width_meters=strip_width_meters,
            azimuth_window=azimuth_window,
            light_azimuth_threshold=light_azimuth_threshold,
            severe_azimuth_threshold=severe_azimuth_threshold,
            minimum_break_score=minimum_break_score,
            minimum_point_count=minimum_point_count,
            time_tolerance_multiplier=time_tolerance_multiplier,
            confirmation_window=confirmation_window,
            min_confirmed=min_confirmed,
            future_stability_window=future_stability_window,
            future_stability_threshold=future_stability_threshold,
            future_az_cluster_threshold=future_az_cluster_threshold,
            past_stability_max_variance=past_stability_max_variance,
            past_stability_window=past_stability_window,
            convergence_rate_threshold=convergence_rate_threshold,
            retroactive_relabel_window=retroactive_relabel_window,
            min_velocity_weight=min_velocity_weight,
            fusion_azimuth_tolerance=fusion_azimuth_tolerance,
            max_desvio=max_desvio,
            border_azimuth_threshold=border_azimuth_threshold,
            border_speed_threshold=border_speed_threshold,
            border_distance_threshold=border_distance_threshold,
            path_mode=path_mode,
            use_time=bool(field_time)
        )

        scenario = ScenarioResolver.resolve(path_mode, config.use_time)
        ParameterTuner.tune(config, scenario)

        self.logger.info(
            f"Iniciando julgamento bidirecional {path_mode}",
            source_path=self.source_path,
            features=len(ordered_points),
            scenario=scenario.name
        )

        t0 = time.time()
        updates = self._evaluate_bidirectional(ordered_points, layer.crs(), config)
        updates = self._postprocess(updates, config.minimum_point_count, config.fusion_azimuth_tolerance)

        if not recap:
            updates = self._handle_recap(ordered_points, layer, updates, config)

        result_layer = self._create_memory_layer_with_updates(layer, updates, field_name_map)

        shot_sizes = {}
        for v in updates.values():
            sid = v[StripOutputFieldKey.SHOT_ID.value]
            shot_sizes[sid] = shot_sizes.get(sid, 0) + 1

        valid_shots = sum(1 for s, sz in shot_sizes.items() if sz >= minimum_point_count and s != 0)
        summary = {
            "total_points": len(ordered_points),
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

    def _handle_recap(self, ordered_points, layer, updates, config):
        """Reavalia pontos lixo (shot_id=0) para tentar salvar faixas pequenas perdidas."""
        lixo_fids = [fid for fid, v in updates.items() if v[StripOutputFieldKey.SHOT_ID.value] == 0]
        if not lixo_fids:
            return updates
        
        self.logger.info(f"Repescagem: {len(lixo_fids)} pontos serão reavaliados.")
        ordered_lixo = [p for p in ordered_points if p["fid"] in lixo_fids]
        recap_updates = self._evaluate_bidirectional(ordered_lixo, layer.crs(), config)
        
        for fid, v in recap_updates.items():
            updates[fid] = v
        return self._postprocess(updates, config.minimum_point_count, config.fusion_azimuth_tolerance)

    # -------------------------------------------------------------------
    # DETECTOR (Break Detector & PreComputer)
    # -------------------------------------------------------------------

    def _evaluate_bidirectional(self, ordered_points, crs, config: JudgeConfig):
        """Loop principal de avaliação usando pre-computação e regras bidirecionais."""
        n = len(ordered_points)
        if n == 0: return {}

        pre_az, pre_metrics = self._precompute_metrics(ordered_points, crs)
        
        updates = {}
        az_history: list[float] = []
        vel_history: list[float] = []
        current_shot_id = 1
        updates[ordered_points[0]["fid"]] = self._build_default_output(current_shot_id)

        for i in range(1, n):
            m = pre_metrics[i]
            instant_az = pre_az[i]
            
            # Média Circular Ponderada (apenas se tiver tempo)
            recent_az = az_history[-config.azimuth_window:] if az_history else []
            recent_vel = vel_history[-config.azimuth_window:] if vel_history else []
            
            mean_az = MathUtils.circular_mean(recent_az) if recent_az else instant_az
            if config.use_time and recent_vel:
                weights = [max(config.min_velocity_weight, v) for v in recent_vel]
                mean_az = MathUtils.weighted_circular_mean(recent_az, weights)
            
            delta_azimuth = MathUtils.angular_diff(instant_az, mean_az)

            # Estabilidades
            past_var = _past_stability(az_history, config.past_stability_window)
            past_stable = past_var <= config.past_stability_max_variance
            conv_rate = _az_convergence_rate(az_history, config.past_stability_window)
            past_converging = conv_rate > config.convergence_rate_threshold

            f_ratio, f_az_mean = _future_stability_score(pre_az, i, config.future_stability_window, config.future_az_cluster_threshold)
            future_stable = f_ratio >= config.future_stability_threshold

            # Scores
            score_dir = (1 if delta_azimuth > config.light_azimuth_threshold else 0) + (2 if delta_azimuth > config.severe_azimuth_threshold else 0)
            score_cont = self._apply_time_score(
                score=0, 
                delta_time=m.dt, 
                point_frequency_seconds=config.point_frequency_seconds, 
                time_tolerance_multiplier=config.time_tolerance_multiplier
            ) if config.use_time else 0
            if m.dd > float(config.strip_width_meters) * 0.8: score_cont += 1
            
            total_score = score_dir + score_cont

            # Segmentação adaptativa
            should_break = False
            if total_score >= config.minimum_break_score:
                if future_stable:
                    should_break = True # R2: Entrada de faixa
                elif past_stable and not past_converging:
                    # R1: Saída de faixa estável - Confirmar prospectivamente
                    confirmed = 0
                    for j in range(i + 1, min(i + 1 + config.confirmation_window, n)):
                        conf_delta = MathUtils.angular_diff(pre_az[j], mean_az)
                        if conf_delta > config.light_azimuth_threshold: confirmed += 1
                    if confirmed >= config.min_confirmed: should_break = True

            if should_break:
                current_shot_id += 1
                if future_stable and config.retroactive_relabel_window > 0:
                    self._apply_retroactive_relabel(i, updates, pre_az, f_az_mean, current_shot_id, config, ordered_points)

            is_border = (delta_azimuth > config.border_azimuth_threshold and (not config.use_time or m.vel < config.border_speed_threshold) and m.dd < config.border_distance_threshold)
            seg_type = "bordadura" if is_border else "faixa"

            updates[ordered_points[i]["fid"]] = self._build_point_output(current_shot_id, total_score, score_dir, score_cont, seg_type, instant_az, mean_az, delta_azimuth, m)

            az_history.append(instant_az)
            vel_history.append(m.vel)

        return updates

    def _precompute_metrics(self, ordered_points, crs) -> tuple[list[float], list[PointMetrics]]:
        """Otimização: Pré-calcula geometria e física de toda a trilha de uma vez."""
        n = len(ordered_points)
        pre_az = [0.0] * n
        metrics = [PointMetrics()] * n
        for i in range(1, n):
            p1, p2 = ordered_points[i - 1], ordered_points[i]
            pre_az[i] = VectorLayerGeometry.calculate_point_azimuth(p1["point"], p2["point"])
            dt = max(0.0, p2["timestamp"] - p1["timestamp"])
            dd = VectorLayerGeometry.measure_distance_between_points(p1["point"], p2["point"], crs)
            metrics[i] = PointMetrics(az=pre_az[i], dt=dt, dd=dd, vel=(dd/dt if dt > 0 else 0.0))
        return pre_az, metrics

    def _apply_retroactive_relabel(self, i, updates, pre_az, f_az_mean, shot_id, config: JudgeConfig, ordered_points):
        """Move pontos de 'assentamento' da entrada da faixa para o novo Shot ID."""
        for back in range(1, config.retroactive_relabel_window + 1):
            bi = i - back
            if bi < 0: break
            point_data = updates.get(ordered_points[bi]["fid"])
            if not point_data: break
            diff = MathUtils.angular_diff(pre_az[bi] if bi > 0 else 0.0, f_az_mean)
            if diff <= config.future_az_cluster_threshold * 2.0:
                updates[ordered_points[bi]["fid"]][StripOutputFieldKey.SHOT_ID.value] = shot_id
            else: break

    # -------------------------------------------------------------------
    # POST PROCESSOR (Post Processor)
    # -------------------------------------------------------------------

    def _postprocess(self, updates, minimum_point_count, fusion_azimuth_tolerance):
        """Fusão de pequenos shots + marcação de validade + órfãos → shot_id=0."""

        def shot_sizes(upd):
            sizes = {}
            for v in upd.values():
                sid = v[StripOutputFieldKey.SHOT_ID.value]
                sizes[sid] = sizes.get(sid, 0) + 1
            return sizes

        # Fusão de tiros pequenos consecutivos com az similar
        updates = self._fuse_small_shots(updates, minimum_point_count, fusion_azimuth_tolerance)

        sizes = shot_sizes(updates)

        # Marcar válidos e órfãos
        for fid, values in updates.items():
            sid = values[StripOutputFieldKey.SHOT_ID.value]
            sz = sizes.get(sid, 0)
            if sz < minimum_point_count:
                values[StripOutputFieldKey.SHOT_ID.value] = 0
                values[StripOutputFieldKey.SHOT_VALID.value] = 0
            else:
                values[StripOutputFieldKey.SHOT_VALID.value] = 1

        return updates

    def _fuse_small_shots(self, updates, minimum_point_count, fusion_azimuth_tolerance):
        """Funde tiros pequenos consecutivos com azimute médio similar."""
        if not updates:
            return updates

        shots: dict[int, list] = {}
        for fid, values in updates.items():
            sid = values[StripOutputFieldKey.SHOT_ID.value]
            shots.setdefault(sid, []).append((fid, values))

        shot_stats = {}
        for sid, features in shots.items():
            azs = [v[StripOutputFieldKey.AZIMUTH_MEAN.value] for _, v in features if v[StripOutputFieldKey.AZIMUTH_MEAN.value] > 0]
            shot_stats[sid] = {
                "size": len(features),
                "mean_az": MathUtils.circular_mean(azs) if azs else 0.0,
            }

        sorted_ids = sorted(shot_stats)
        fusions = []
        for i in range(len(sorted_ids) - 1):
            a, b = sorted_ids[i], sorted_ids[i + 1]
            if (shot_stats[a]["size"] < minimum_point_count and
                    shot_stats[b]["size"] < minimum_point_count):
                if MathUtils.angular_diff(shot_stats[a]["mean_az"], shot_stats[b]["mean_az"]) <= fusion_azimuth_tolerance:
                    fusions.append((a, b))

        for from_id, to_id in fusions:
            if from_id in shots:
                for _, values in shots[from_id]:
                    values[StripOutputFieldKey.SHOT_ID.value] = to_id

        self.logger.info("Fusão de tiros pequenos", fusions=len(fusions))
        return updates

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
        if field_time and layer.fields().lookupField(field_time) == -1:
            # Se o usuário informou um nome de campo, ele deve existir. Se não informou (None), ignoramos.
            raise RuntimeError(f"Campo de timestamp '{field_time}' não encontrado na camada.")

    def _load_ordered_points(self, layer, field_id, field_time):
        import time
        t0 = time.time()
        ordered = []
        use_time = bool(field_time)
        for feature in layer.getFeatures():
            geometry = feature.geometry()
            if not geometry or geometry.isEmpty():
                continue
            point = VectorLayerGeometry.get_representative_point(geometry)
            if point is None:
                continue
            
            timestamp = 0.0
            if use_time:
                timestamp = self._parse_timestamp(feature.attribute(field_time))
                if timestamp is None:
                    timestamp = 0.0

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
        for logical_key, field_spec in self.DIVIDE_STRIP_FIELDS.items():
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
            StripOutputFieldKey.SHOT_ID.value: shot_id,
            StripOutputFieldKey.SHOT_VALID.value: 0,
            StripOutputFieldKey.SCORE.value: 0,
            StripOutputFieldKey.SCORE_DIRECTION.value: 0,
            StripOutputFieldKey.SCORE_CONTINUITY.value: 0,
            StripOutputFieldKey.SEG_TYPE.value: "faixa",
            StripOutputFieldKey.AZIMUTH_INSTANT.value: 0.0,
            StripOutputFieldKey.AZIMUTH_MEAN.value: 0.0,
            StripOutputFieldKey.DELTA_AZIMUTH.value: 0.0,
            StripOutputFieldKey.DELTA_TIME.value: 0.0,
            StripOutputFieldKey.DELTA_DISTANCE.value: 0.0,
            StripOutputFieldKey.VELOCITY_INSTANT.value: 0.0,
        }

    def _build_point_output(self, shot_id, score, s_dir, s_cont, s_type, az, mean, d_az, m: PointMetrics) -> dict:
        return {
            StripOutputFieldKey.SHOT_ID.value: shot_id,
            StripOutputFieldKey.SHOT_VALID.value: 0,
            StripOutputFieldKey.SCORE.value: int(score),
            StripOutputFieldKey.SCORE_DIRECTION.value: int(s_dir),
            StripOutputFieldKey.SCORE_CONTINUITY.value: int(s_cont),
            StripOutputFieldKey.SEG_TYPE.value: s_type,
            StripOutputFieldKey.AZIMUTH_INSTANT.value: float(az),
            StripOutputFieldKey.AZIMUTH_MEAN.value: float(mean),
            StripOutputFieldKey.DELTA_AZIMUTH.value: float(d_az),
            StripOutputFieldKey.DELTA_TIME.value: float(m.dt),
            StripOutputFieldKey.DELTA_DISTANCE.value: float(m.dd),
            StripOutputFieldKey.VELOCITY_INSTANT.value: float(m.vel),
        }


    @staticmethod
    def _apply_time_score(*, score, delta_time, point_frequency_seconds, time_tolerance_multiplier):
        if not delta_time:
            return score
            
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
        for logical_key, field_spec in SequentialPointBreakJudge.DIVIDE_STRIP_FIELDS.items():
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