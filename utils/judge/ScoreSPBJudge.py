# -*- coding: utf-8 -*-
"""
SimpleSPBJudge — Juiz de Segmentação por Votação de Janela
===========================================================
Algoritmo "Voting Window Judge":

Para cada ponto i (centro da janela):
  1. Quebra forçada por distância tem prioridade absoluta.
  2. Se scores[i] >= max_desvio (e não é start) → quebra por direção.
     - Zera scores de todos os pontos futuros.
     - Ponto i vira "start", ponto i+1 vira "second".
  3. Se não é start/end: calcula baseline como circular_mean dos últimos N
     segmentos dentro do shot atual (limitado pela última quebra).
  4. Para cada ponto j na janela posterior [i+1 .. i+N]:
       diff = angular_diff(az_baseline, raw_az[j])
       se diff >= severe_threshold / N  →  scores[j] += score_inc
     onde score_inc = 2 se is_second[i], senão 1.
     (O "second" representa a si mesmo + o start que não pôde olhar à frente.)

Parâmetros:
  field_id:                   Campo de ID único/sequencial para ordenação
  severe_azimuth_threshold:   Limiar total de desvio angular (ex: 45°)
  minimum_point_count:        Nº mínimo de pontos por strip válida
  max_distance_meters:        Distância que força quebra (0 = desabilitado)
  max_desvio (max_deviation_points): Tamanho da janela N e limiar de score
"""

import time
from typing import Optional

from qgis.core import QgsVectorLayer, QgsWkbTypes
from collections import Counter
from ...core.config.LogUtils import LogUtils
from ...core.enum.OutputFieldKey import StripOutputFieldKey
from ..ToolKeys import ToolKey
from ..vector.VectorLayerGeometry import VectorLayerGeometry
from ..vector.VectorLayerSource import VectorLayerSource
from ..MathUtils import MathUtils


class ScoreSPBJudge:
    """
    Juiz de segmentação de faixas por votação de janela.

    Lógica:
      - Cada ponto central olha N pontos atrás (baseline) e N à frente (candidatos).
      - Candidatos com azimute discrepante acumulam score.
      - Quando score >= max_desvio: quebra de shot.
      - Segundo ponto de cada shot contribui com peso 2 para a votação.
    """

    

    from ..StringManager import StringManager
    DIVIDE_STRIP_FIELDS = StringManager.DIVIDE_STRIP_FIELDS

    def __init__(self, *, layer=None, source_path: str = "", tool_key: str = ToolKey.UNTRACEABLE):
        self.layer       = layer
        self.source_path = source_path or (layer.source() if layer is not None else "")
        self.tool_key    = tool_key
        self.logger      = LogUtils(tool=tool_key, class_name=self.__class__.__name__)
        self.JUDGEMENT_MODES = ["ANGLE", "DISTANCE"]
        self.JUDGEMENT_MODE = self.JUDGEMENT_MODES[0]
        

    # -------------------------------------------------------------------
    # Ponto de entrada público (mesma assinatura simplificada)
    # -------------------------------------------------------------------

    def judge(
        self,
        *,
        field_id: str,
        field_time: str = None,
        severe_azimuth_threshold: float = 45.0,
        minimum_point_count: int = 20,
        max_distance_meters: float = 0.0,
        max_desvio: int = 2,
        **kwargs,  # absorve parâmetros não utilizados do juiz complexo
    ):
        layer = self._load_layer()
        self._validate_layer(layer, field_id, field_time)

        ordered_points = self._load_ordered_points(layer, field_id, field_time)
        if not ordered_points:
            raise RuntimeError("Nenhum ponto válido encontrado.")

        # Resolve nomes de campos de saída
        field_name_map = self._resolve_output_fields(layer)

        self.logger.info(
            "Iniciando cálculo simples de métricas",
            features=len(ordered_points),
            mode="simple",
        )

        t0 = time.time()

        # Fase única: cálculo de métricas + atribuição de shot_id por grupo simples
        updates = self._compute_metrics(
            ordered_points,
            layer.crs(),
            severe_azimuth_threshold=severe_azimuth_threshold,
            max_deviation_points=max_desvio,
            minimum_point_count=minimum_point_count,
            max_distance_meters=max_distance_meters,
        )

        result_layer = self._create_memory_layer(layer, updates, field_name_map)

        summary = {
            "total_points": len(ordered_points),
            "total_shots": 0,       # sem julgamento ainda
            "valid_shots": 0,
            "invalid_shots": 0,
            "source_path": self.source_path,
            "field_name_map": field_name_map,
            "result_layer": result_layer,
        }
        self.logger.info(
            "Cálculo simples concluído",
            elapsed_seconds=round(time.time() - t0, 2),
        )
        return summary

    # -------------------------------------------------------------------
    # Cálculo de métricas (sem julgamento)
    # -------------------------------------------------------------------
    def _compute_metrics(
        self,
        ordered_points,
        crs,
        severe_azimuth_threshold: float = 45.0,
        max_deviation_points: int = 3,
        minimum_point_count: int = 20,
        max_distance_meters: float = 0.0,
    ) -> dict:
        """
        Calcula métricas e atribui shot_ids usando o algoritmo de votação
        por janela deslizante.

        Parâmetros
        ----------
        severe_azimuth_threshold : limiar total de desvio (ex: 45°).
            O sub-limiar por comparação individual é threshold / N.
        max_deviation_points (N) : tamanho da janela E limiar de score para quebra.
        minimum_point_count : shots com menos pontos recebem shot_id "0" (inválido).
        max_distance_meters : se > 0, força quebra quando dist[i] excede este valor.
        """
        n = len(ordered_points)
        if n == 0:
            return {}

        N             = max_deviation_points
        # Limiar individual: um candidato é "diferente" se desviar mais que este valor
        sub_threshold = severe_azimuth_threshold / max(N, 1)

        # ── Pré-computa azimutes brutos e distâncias ─────────────────────────
        # raw_az[i]   = azimute do segmento (i-1) → i   (None para i=0)
        # distances[i]= distância do segmento (i-1) → i (0.0 para i=0)
        raw_az:    list[Optional[float]] = [None] * n
        distances: list[float]           = [0.0]  * n

        for i in range(1, n):
            p1, p2 = ordered_points[i - 1], ordered_points[i]
            raw_az[i]    = float(VectorLayerGeometry.calculate_point_azimuth(
                p1["point"], p2["point"]
            )) % 360.0
            distances[i] = VectorLayerGeometry.measure_distance_between_points(
                p1["point"], p2["point"], crs
            )

        # ── Arrays de estado ─────────────────────────────────────────────────
        scores    = [0]       * n   # votos acumulados (candidato a quebra)
        shot_ids  = [1]       * n   # id do shot original (antes de validar min)
        seg_types = ["noisy"] * n   # tipo semântico do segmento
        is_start  = [False]   * n   # True: ponto inicia um novo shot
        is_second = [False]   * n   # True: segundo ponto do shot (sem prev completo)

        # Ponto 0 é sempre o início do shot 1
        is_start[0]  = True
        if n > 1:
            is_second[1] = True

        current_shot       = 1
        current_shot_start = 0   # índice do início do shot atual

        # ── Passagem principal ───────────────────────────────────────────────
        for i in range(n):

            # ── (A) Quebra forçada por distância ─────────────────────────────
            # Prioridade máxima: avaliada antes da quebra por score.
            if (
                i > 0
                and not is_start[i]
                and max_distance_meters > 0.0
                and distances[i] > max_distance_meters
            ):
                current_shot      += 1
                current_shot_start = i
                is_start[i]        = True
                is_second[i]       = False          # cancela eventual "second" anterior
                if i + 1 < n:
                    is_second[i + 1] = True
                for j in range(i + 1, n):           # zera todos os scores futuros
                    scores[j] = 0
                shot_ids[i]  = current_shot
                seg_types[i] = "break_distance"
                continue                             # não processa mais nada para este ponto

            # ── (B) Quebra por score acumulado ───────────────────────────────
            # ── (B) Quebra por score acumulado ───────────────────────────────
            if i > 0 and not is_start[i] and scores[i] >= max_deviation_points:
                next_score = scores[i + 1] if i + 1 < n else 0
                prev_score = scores[i - 1] if i - 1 >= 0 else 0
                if next_score == 0 and prev_score == 0:
                    seg_types[i] = "outlier"
                    LogUtils(tool=self.tool_key, class_name=self.__class__.__name__).debug(
                        f"Ponto marcado como outlier por score alto {next_score} → {prev_score} namas sem suporte de vizinhos",
                        index=i,
                        score=scores[i],
                    )
                else:
                    current_shot      += 1
                    current_shot_start = i
                    is_start[i]        = True
                    if i + 1 < n:
                        is_second[i + 1] = True
                    for j in range(i + 1, n):       # zera todos os scores futuros
                        scores[j] = 0
                    # seg_type será "break_direction" — definido abaixo após atribuir shot_id

            # ── Classifica e decide se este ponto vota na janela posterior ───

            if is_start[i]:
                # Starts (inclusive os de quebra por direção) não têm baseline válido
                seg_types[i] = "start" if i == 0 else "break_direction"
                continue

            if i == n - 1:
                # Último ponto: sem janela posterior para votar
                seg_types[i] = "end"
                continue

            if is_second[i]:
                seg_types[i] = "second"
                # Continua para computar baseline e votar (não usa continue)

            # ── Baseline: circular_mean dos últimos N segmentos do shot atual ─
            # Segmentos considerados: raw_az[prev_start] … raw_az[i]
            # onde prev_start garante que não cruzamos a fronteira do shot.
            prev_start   = max(current_shot_start + 1, i - N + 1)
            prev_az_list = [
                raw_az[j]
                for j in range(prev_start, i + 1)
                if raw_az[j] is not None
            ]
            if not prev_az_list:
                continue

            az_baseline = MathUtils.circular_mean(prev_az_list)

            # ── Votação na janela posterior ──────────────────────────────────
            # O "second" representa a si mesmo + o start (que não pôde olhar à frente).
            # Por isso seu voto vale 2, acelerando a detecção logo após uma quebra.
            score_inc = 2 if is_second[i] else 1

            for j in range(i + 1, min(n, i + N + 1)):
                if raw_az[j] is not None:
                    diff = MathUtils.angular_diff(az_baseline, raw_az[j])
                    if diff >= sub_threshold:
                        scores[j] += score_inc

        # ── Valida tamanho mínimo de shot ────────────────────────────────────
        shot_sizes        = Counter(shot_ids)
        validated_shot_ids = [
            sid if shot_sizes[sid] >= minimum_point_count else 0
            for sid in shot_ids
        ]

        # ── Refina seg_types para pontos "normais" (ainda "noisy") ───────────
        SPECIAL_TYPES = {"start", "break_direction", "break_distance", "end", "second"}
        for i in range(n):
            if seg_types[i] in SPECIAL_TYPES:
                continue

            if validated_shot_ids[i] == 0:
                seg_types[i] = "outlier"
                continue

            # Classifica por variação local de azimute (prev↔next)
            prev_az = raw_az[i]
            next_az = raw_az[i + 1] if i + 1 < n else None

            if prev_az is None or next_az is None:
                seg_types[i] = "straight"
                continue

            local_var = MathUtils.angular_diff(prev_az, next_az)

            # Também verifica suspeita de gap (quase-quebra por distância)
            if max_distance_meters > 0.0 and distances[i] > max_distance_meters * 0.7:
                seg_types[i] = "gap_suspect"
            elif local_var < 5.0:
                seg_types[i] = "straight"
            elif local_var < 15.0:
                seg_types[i] = "smooth_turn"
            elif local_var < severe_azimuth_threshold:
                seg_types[i] = "sharp_turn"
            elif local_var >= severe_azimuth_threshold:
                seg_types[i] = "zigzag" if scores[i] > 0 else "noisy"

        # ── Constrói dicionário de atualizações ──────────────────────────────
        updates: dict[int, dict] = {}

        for i in range(n):
            prev_az = raw_az[i]           if i >= 1     else None
            next_az = raw_az[i + 1]       if i + 1 < n  else None
            dd      = distances[i]

            # az_instant: média axial entre segmento de chegada e de saída
            if prev_az is not None and next_az is not None:
                az_instant = MathUtils.circular_mean([prev_az, next_az])
            elif prev_az is not None:
                az_instant = prev_az
            elif next_az is not None:
                az_instant = next_az
            else:
                az_instant = 0.0

            # Deltas locais (ângulo entre az_instant e cada segmento adjacente)
            delta_prev = (
                MathUtils.angular_diff(az_instant, prev_az)
                if prev_az is not None else 0.0
            )
            delta_next = (
                MathUtils.angular_diff(az_instant, next_az)
                if next_az is not None else 0.0
            )

            updates[ordered_points[i]["fid"]] = {
                StripOutputFieldKey.SHOT_ID.value:           str(validated_shot_ids[i]),
                StripOutputFieldKey.OLD_SHOT_ID.value:       str(shot_ids[i]),
                StripOutputFieldKey.SHOT_VALID.value:        1 if validated_shot_ids[i] != 0 else 0,
                StripOutputFieldKey.AZIMUTH_INSTANT.value:   float(az_instant),
                StripOutputFieldKey.AZIMUTH_MEAN.value:      float(az_instant),
                StripOutputFieldKey.AZIMUTH_PREV.value:      float(prev_az)  if prev_az is not None else 0.0,
                StripOutputFieldKey.AZIMUTH_NEXT.value:      float(next_az)  if next_az is not None else 0.0,
                StripOutputFieldKey.DELTA_AZ_PREV.value:     float(delta_prev),
                StripOutputFieldKey.DELTA_AZ_NEXT.value:     float(delta_next),
                StripOutputFieldKey.DELTA_DISTANCE.value:    float(dd),
                StripOutputFieldKey.SCORE.value:             scores[i],
                StripOutputFieldKey.SCORE_DIRECTION.value:   scores[i],
                StripOutputFieldKey.SCORE_CONTINUITY.value:  0,
                StripOutputFieldKey.SEG_TYPE.value:          seg_types[i],
                StripOutputFieldKey.DELTA_TIME.value:        0.0,
                StripOutputFieldKey.VELOCITY_INSTANT.value:  0.0,
            }

        return updates

    # -------------------------------------------------------------------
    # Infraestrutura (similar ao SequentialPointBreakJudge)
    # -------------------------------------------------------------------

    def _load_layer(self):
        if self.layer is not None:
            return self.layer
        layer = VectorLayerSource.load_vector_layer_from_source_path(
            self.source_path, external_tool_key=self.tool_key
        )
        if not layer:
            raise RuntimeError("Nao foi possivel carregar a camada.")
        return layer

    def _validate_layer(self, layer, field_id, field_time):
        if not isinstance(layer, QgsVectorLayer) or not layer.isValid():
            raise RuntimeError("Camada vetorial invalida.")
        if layer.geometryType() != QgsWkbTypes.PointGeometry:
            raise RuntimeError("A camada deve ser do tipo ponto.")
        if layer.fields().lookupField(field_id) == -1:
            raise RuntimeError(f"Campo de ID nao encontrado: {field_id}")
        if field_time and layer.fields().lookupField(field_time) == -1:
            raise RuntimeError(f"Campo de timestamp '{field_time}' nao encontrado na camada.")

    def _load_ordered_points(self, layer, field_id, field_time):
        from datetime import datetime

        t0       = time.time()
        ordered  = []
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
                ts = self._parse_timestamp(feature.attribute(field_time))
                timestamp = ts if ts is not None else 0.0
            ordered.append({
                "fid":          feature.id(),
                "seq_id_sort":  self._build_sort_key(feature.attribute(field_id)),
                "timestamp":    timestamp,
                "point":        point,
            })
        ordered.sort(key=lambda x: (x["seq_id_sort"], x["timestamp"], x["fid"]))
        self.logger.info("Pontos carregados (simples)", valid=len(ordered), elapsed=round(time.time() - t0, 2))
        return ordered

    def _resolve_output_fields(self, layer):
        resolved   = {}
        for logical_key, field_spec in self.DIVIDE_STRIP_FIELDS.items():
            resolved[logical_key] = field_spec.attribute
        return resolved

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
        from datetime import datetime
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
    def _create_memory_layer(layer, updates, field_name_map):
        from qgis.core import QgsVectorLayer, QgsField, QgsFeature

        t0 = time.time()
        uri = f"Point?crs={layer.crs().authid()}"
        new_layer = QgsVectorLayer(uri, f"{layer.name()}_segmentado", "memory")
        if not new_layer.isValid():
            raise RuntimeError("Falha ao criar camada de memoria.")

        new_fields = layer.fields()
        for logical_key, field_spec in ScoreSPBJudge.DIVIDE_STRIP_FIELDS.items():
            field_name = field_name_map[logical_key]
            if new_fields.lookupField(field_name) == -1:
                new_fields.append(
                    QgsField(field_name, field_spec.type, len=field_spec.length, prec=field_spec.precision)
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
                idx      = new_layer.fields().lookupField(resolved)
                if idx >= 0:
                    if attr_key == StripOutputFieldKey.SHOT_ID.value and attr_val is not None:
                        attr_val = str(attr_val)
                    new_feature.setAttribute(idx, attr_val)
            new_layer.addFeature(new_feature)

        new_layer.commitChanges()
        new_layer.updateFields()

        LogUtils(tool=ToolKey.UNTRACEABLE, class_name="SimpleSPBJudge").info(
            "Camada de memoria criada (simples)",
            features=new_layer.featureCount(),
            elapsed=round(time.time() - t0, 2),
        )
        return new_layer


