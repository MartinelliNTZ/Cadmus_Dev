# -*- coding: utf-8 -*-
"""
SimpleSPBJudge — Juiz Simplificado de Segmentação com lógica de score por blocos
================================================================================
Implementa a lógica descrita pelo usuário:
- Cada ponto olha N vizinhos para frente e para trás (N = max_desvio).
- Compara o azimute de cada vizinho com a direção de referência da reta atual.
- Agrupa vizinhos consecutivos que estão fora do limiar; cada grupo vale 1 ponto de score.
- Se score > max_desvio → quebra: ponto vira start de nova reta, score zerado.
- Segundo ponto de cada reta tem score = 2.
"""

import time
from typing import Optional, List, Dict, Tuple

from qgis.core import QgsVectorLayer, QgsWkbTypes

from ...core.config.LogUtils import LogUtils
from ...core.enum.OutputFieldKey import StripOutputFieldKey
from ..ToolKeys import ToolKey
from ..vector.VectorLayerGeometry import VectorLayerGeometry
from ..vector.VectorLayerSource import VectorLayerSource
from ..MathUtils import MathUtils
from ..StringManager import StringManager


class SimpleSPBJudge:

    DIVIDE_STRIP_FIELDS = StringManager.DIVIDE_STRIP_FIELDS

    def __init__(self, *, layer=None, source_path: str = "", tool_key: str = ToolKey.UNTRACEABLE):
        self.layer       = layer
        self.source_path = source_path or (layer.source() if layer is not None else "")
        self.tool_key    = tool_key
        self.logger      = LogUtils(tool=tool_key, class_name=self.__class__.__name__)
        self.JUDGEMENT_MODES = ["ANGLE", "DISTANCE"]
        self.JUDGEMENT_MODE = self.JUDGEMENT_MODES[0]

    # -------------------------------------------------------------------
    # Ponto de entrada público
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
        **kwargs,
    ):
        layer = self._load_layer()
        self._validate_layer(layer, field_id, field_time)

        ordered_points = self._load_ordered_points(layer, field_id, field_time)
        if not ordered_points:
            raise RuntimeError("Nenhum ponto válido encontrado.")

        field_name_map = self._resolve_output_fields(layer)

        self.logger.info(
            "Iniciando julgamento por score de blocos",
            features=len(ordered_points),
            max_desvio=max_desvio,
            threshold=severe_azimuth_threshold,
        )

        t0 = time.time()

        updates = self._compute_metrics_with_score(
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
            "total_shots": 0,       # pode ser calculado se necessário
            "valid_shots": 0,
            "invalid_shots": 0,
            "source_path": self.source_path,
            "field_name_map": field_name_map,
            "result_layer": result_layer,
        }
        self.logger.info(
            "Julgamento concluído",
            elapsed_seconds=round(time.time() - t0, 2),
        )
        return summary

    # -------------------------------------------------------------------
    # Nova implementação: julgamento por score de blocos
    # -------------------------------------------------------------------
    def _compute_metrics_with_score(
        self,
        ordered_points: List[dict],
        crs,
        severe_azimuth_threshold: float = 45.0,
        max_deviation_points: int = 2,
        minimum_point_count: int = 20,
        max_distance_meters: float = 0.0,
    ) -> Dict[int, dict]:
        """
        Aplica a lógica de score de blocos:
        - Cada ponto (com azimute definido) examina até max_deviation_points vizinhos
          para frente e para trás.
        - Compara cada vizinho com a direção de referência da reta atual.
        - Conta blocos consecutivos de vizinhos que divergem > severe_azimuth_threshold.
        - Score = número de blocos.
        - Se score > max_deviation_points → quebra: ponto vira start da nova reta.
        - Segundo ponto de cada reta tem score = 2.
        """
        n = len(ordered_points)
        if n == 0:
            return {}

        # ---- 1. Calcula azimutes brutos e distâncias ----
        raw_az: List[Optional[float]] = [None] * n
        distances: List[float] = [0.0] * n

        for i in range(1, n):
            p1, p2 = ordered_points[i-1]["point"], ordered_points[i]["point"]
            az = VectorLayerGeometry.calculate_point_azimuth(p1, p2)
            raw_az[i] = float(az) % 360.0
            distances[i] = VectorLayerGeometry.measure_distance_between_points(p1, p2, crs)

        # ---- 2. Estruturas para resultados ----
        # break_points[i] = True se há quebra ANTES do ponto i (i é início de novo shot)
        break_points = [False] * n
        break_points[0] = False  # primeiro ponto nunca é quebra
        shot_ids = [1] * n
        scores = [0] * n
        score_directions = [0] * n  # número de blocos (score principal)
        seg_types = [""] * n

        # ---- 3. Estado da caminhada ----
        current_shot = 1
        start_idx = 1      # índice do primeiro ponto da reta atual (com azimute)
        # Direção de referência: média circular dos azimutes dos pontos da reta atual
        current_direction = raw_az[1] if n > 1 else 0.0
        # Lista de índices dos pontos que pertencem à reta atual (para calcular média)
        current_shot_points = [1]

        # ============================================================
        # Loop para cada ponto a partir do índice 1 (primeiro com azimute)
        # ============================================================
        for i in range(1, n):
            # ----- Quebra por distância (prioridade) -----
            if max_distance_meters > 0.0 and distances[i] > max_distance_meters:
                break_points[i] = True
                seg_types[i] = "break_distance"
                # Re-inicializa a reta a partir deste ponto
                start_idx = i
                current_direction = raw_az[i]
                current_shot_points = [i]
                scores[i] = 0
                score_directions[i] = 0
                current_shot += 1
                shot_ids[i] = current_shot
                continue

            # ----- Determina se o ponto é start / second / normal -----
            if i == start_idx:
                # Já tratado como start (quando quebra ou início)
                seg_types[i] = "start"
                scores[i] = 0
                score_directions[i] = 0
                shot_ids[i] = current_shot
                continue

            if i == start_idx + 1:
                # Segundo ponto da reta: score = 2 por regra especial
                seg_types[i] = "second"
                scores[i] = 2
                score_directions[i] = 2  # ou número de blocos? Usamos 2 como valor fixo
                # Não quebra por score a menos que max_desvio < 2
                if scores[i] > max_deviation_points:
                    break_points[i] = True
                    # Re-inicia a reta neste ponto (ele vira start)
                    start_idx = i
                    current_direction = raw_az[i]
                    current_shot_points = [i]
                    scores[i] = 0
                    score_directions[i] = 0
                    current_shot += 1
                else:
                    # Atualiza direção de referência com média dos dois pontos
                    current_shot_points.append(i)
                    current_direction = MathUtils.circular_mean([raw_az[p] for p in current_shot_points])
                shot_ids[i] = current_shot
                continue

            # ----- Ponto normal: terceiro ou mais da reta -----
            # Janela de vizinhos: [i - window, i + window] excluindo i
            window = max_deviation_points
            left = max(1, i - window)      # não inclui índice 0 (sem azimute)
            right = min(n - 1, i + window)

            # Coleta os índices dos vizinhos
            neighbors = [j for j in range(left, right + 1) if j != i and raw_az[j] is not None]

            if not neighbors:
                # Sem vizinhos para comparar → sem score
                score = 0
                blocks = 0
            else:
                # Marca quais vizinhos estão diferentes da direção de referência
                different = [False] * len(neighbors)
                for idx, j in enumerate(neighbors):
                    diff = MathUtils.angular_diff(raw_az[j], current_direction)
                    different[idx] = (diff > severe_azimuth_threshold)

                # Conta blocos consecutivos de True
                blocks = 0
                in_block = False
                for diff_flag in different:
                    if diff_flag and not in_block:
                        blocks += 1
                        in_block = True
                    elif not diff_flag:
                        in_block = False
                score = blocks

            score_directions[i] = score
            scores[i] = score

            # Verifica quebra
            if score > max_deviation_points:
                break_points[i] = True
                seg_types[i] = "break"
                # Ponto i vira start da nova reta
                start_idx = i
                current_direction = raw_az[i]
                current_shot_points = [i]
                scores[i] = 0
                score_directions[i] = 0
                current_shot += 1
            else:
                seg_types[i] = "normal"
                # Atualiza direção de referência com a média de todos os pontos da reta atual
                current_shot_points.append(i)
                current_direction = MathUtils.circular_mean([raw_az[p] for p in current_shot_points])

            shot_ids[i] = current_shot

        # ---- 4. Atribui shot_id final com validação de tamanho mínimo ----
        shot_sizes = {}
        for i in range(1, n):
            sid = shot_ids[i]
            shot_sizes[sid] = shot_sizes.get(sid, 0) + 1

        validated_shot_ids = [0] * n
        # O primeiro ponto (índice 0) não tem azimute, atribuímos shot_id baseado no próximo?
        # Para simplificar, o primeiro ponto herda o shot_id do ponto 1 se houver.
        if n > 1:
            first_shot = shot_ids[1]
            validated_shot_ids[0] = first_shot if shot_sizes.get(first_shot, 0) >= minimum_point_count else 0
        for i in range(1, n):
            sid = shot_ids[i]
            validated_shot_ids[i] = sid if shot_sizes.get(sid, 0) >= minimum_point_count else 0

        # ---- 5. Monta dicionário de updates (mesma estrutura do código original) ----
        updates = {}
        for i in range(n):
            # Calcula azimutes instantâneo, anterior, próximo, etc.
            prev_segment_az = raw_az[i] if i >= 1 else None
            next_segment_az = raw_az[i+1] if i+1 < n else None
            dd = distances[i] if i >= 1 else 0.0

            # Azimute instantâneo (média dos dois lados quando disponível)
            if prev_segment_az is not None and next_segment_az is not None:
                az_instant = MathUtils.circular_mean([prev_segment_az, next_segment_az])
            elif prev_segment_az is not None:
                az_instant = prev_segment_az
            elif next_segment_az is not None:
                az_instant = next_segment_az
            else:
                az_instant = 0.0

            delta_prev = MathUtils.angular_diff(az_instant, prev_segment_az) if prev_segment_az is not None else 0.0
            delta_next = MathUtils.angular_diff(az_instant, next_segment_az) if next_segment_az is not None else 0.0

            # Tipo de segmento (seg_type)
            if i == 0:
                seg_type = "first_no_az"
            elif break_points[i]:
                if seg_types[i]:
                    seg_type = seg_types[i]
                else:
                    seg_type = "break_direction"
            elif validated_shot_ids[i] == 0:
                seg_type = "outlier"
            elif seg_types[i]:
                seg_type = seg_types[i]
            else:
                seg_type = "unknown"

            updates[ordered_points[i]["fid"]] = {
                StripOutputFieldKey.SHOT_ID.value:          str(validated_shot_ids[i]),
                StripOutputFieldKey.OLD_SHOT_ID.value:      str(shot_ids[i]),
                StripOutputFieldKey.SHOT_VALID.value:       0,
                StripOutputFieldKey.AZIMUTH_INSTANT.value:  float(az_instant),
                StripOutputFieldKey.AZIMUTH_MEAN.value:     float(az_instant),
                StripOutputFieldKey.AZIMUTH_PREV.value:     float(prev_segment_az) if prev_segment_az is not None else 0.0,
                StripOutputFieldKey.AZIMUTH_NEXT.value:     float(next_segment_az) if next_segment_az is not None else 0.0,
                StripOutputFieldKey.DELTA_AZ_PREV.value:    float(delta_prev),
                StripOutputFieldKey.DELTA_AZ_NEXT.value:    float(delta_next),
                StripOutputFieldKey.DELTA_DISTANCE.value:   float(dd),
                StripOutputFieldKey.SCORE.value:            int(scores[i]),
                StripOutputFieldKey.SCORE_DIRECTION.value:  int(score_directions[i]),
                StripOutputFieldKey.SCORE_CONTINUITY.value: 0,  # não utilizado
                StripOutputFieldKey.SEG_TYPE.value:         seg_type,
                StripOutputFieldKey.DELTA_TIME.value:       0.0,
                StripOutputFieldKey.VELOCITY_INSTANT.value: 0.0,
            }

        return updates

    # -------------------------------------------------------------------
    # Métodos auxiliares (mantidos do código original)
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
                ts = self._parse_timestamp(feature.attribute(field_time))
                timestamp = ts if ts is not None else 0.0
            ordered.append({
                "fid": feature.id(),
                "seq_id_sort": self._build_sort_key(feature.attribute(field_id)),
                "timestamp": timestamp,
                "point": point,
            })
        ordered.sort(key=lambda x: (x["seq_id_sort"], x["timestamp"], x["fid"]))
        self.logger.info("Pontos carregados", valid=len(ordered), elapsed=round(time.time() - t0, 2))
        return ordered

    def _resolve_output_fields(self, layer):
        resolved = {}
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
        for logical_key, field_spec in SimpleSPBJudge.DIVIDE_STRIP_FIELDS.items():
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
                idx = new_layer.fields().lookupField(resolved)
                if idx >= 0:
                    if attr_key == StripOutputFieldKey.SHOT_ID.value and attr_val is not None:
                        attr_val = str(attr_val)
                    new_feature.setAttribute(idx, attr_val)
            new_layer.addFeature(new_feature)
        new_layer.commitChanges()
        new_layer.updateFields()
        LogUtils(tool=ToolKey.UNTRACEABLE, class_name="SimpleSPBJudge").info(
            "Camada de memoria criada",
            features=new_layer.featureCount(),
            elapsed=round(time.time() - t0, 2),
        )
        return new_layer