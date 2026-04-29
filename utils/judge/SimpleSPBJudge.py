# -*- coding: utf-8 -*-
"""
SimpleSPBJudge — Juiz Simplificado de Segmentação
==================================================
Versão leve focada em retas. Apenas calcula métricas de azimute 
por ponto, sem lógica de julgamento de quebra (ainda).

Parâmetros de entrada:
  - field_id:            Campo de ID único/sequencial para ordenação
  - severe_azimuth_threshold: Limiar grave de desvio angular (ex: 45°)
  - minimum_point_count: Número mínimo de pontos por strip válida
  - max_distance_meters: Distância máxima que força quebra (0 = desabilitado)

Lógica (versão atual — apenas cálculo, sem julgamento):
  1. Grupos são divididos e processados isoladamente (pelo plugin caller).
  2. Para cada ponto do grupo, calcula:
     - azimuth_instant: bearing bruto do segmento i-1 → i
     - azimuth_mean:    média axial entre o azimute anterior e o próximo
                        (suavização local de 3 pontos)
     - azimuth_prev:    azimute do segmento anterior (i-2 → i-1)
     - azimuth_next:    azimute do segmento seguinte (i → i+1)
     - delta_az_prev:   diferença axial entre instant e prev
     - delta_az_next:   diferença axial entre instant e next
     - delta_distance:  distância entre pontos consecutivos (m)

  Atributos de saída (disponíveis no grid de atributos):
     shot_id, old_shot_id, shot_valid, azimuth_instant, azimuth_mean,
     azimuth_prev, azimuth_next, delta_az_prev, delta_az_next,
     delta_distance
"""

import time
from typing import Optional

from qgis.core import QgsVectorLayer, QgsWkbTypes

from ...core.config.LogUtils import LogUtils
from ...core.enum.OutputFieldKey import StripOutputFieldKey
from ..ToolKeys import ToolKey
from ..vector.VectorLayerGeometry import VectorLayerGeometry
from ..vector.VectorLayerSource import VectorLayerSource
from ..MathUtils import MathUtils


class SimpleSPBJudge:
    """
    Juiz simplificado para segmentação de faixas retas.

    Versão atual apenas calcula métricas; o julgamento (quebra) será
    implementado em fase posterior.
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
        conflict_resolver = None,
        **kwargs,  # absorve parâmetros não utilizados do juiz complexo
    ):
        layer = self._load_layer()
        self._validate_layer(layer, field_id, field_time)

        ordered_points = self._load_ordered_points(layer, field_id, field_time)
        if not ordered_points:
            raise RuntimeError("Nenhum ponto válido encontrado.")

        # Resolve nomes de campos de saída
        field_name_map = self._resolve_output_fields(layer, conflict_resolver=conflict_resolver)

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
        max_deviation_points: int = 2,
        minimum_point_count: int = 20,
    ) -> dict:
        """
        Calcula métricas de azimute e atribui shot_id baseado em janela de pontos.

        Nova lógica:
        - max_deviation_points = N (janela)
        - Para cada ponto i, compara o azimute médio dos N segmentos anteriores
        com o azimute médio dos N segmentos posteriores.
        - Se a diferença axial ultrapassar severe_azimuth_threshold, marca quebra.
        - Pontos no início/fim da trilha usam janela reduzida (o que estiver disponível).
        """
        n = len(ordered_points)
        if n == 0:
            return {}

        # Pré-computa azimutes brutos e distâncias entre pontos consecutivos
        raw_az: list[Optional[float]] = [None] * n
        distances: list[float] = [0.0] * n

        for i in range(1, n):
            p1, p2 = ordered_points[i - 1], ordered_points[i]
            az = VectorLayerGeometry.calculate_point_azimuth(p1["point"], p2["point"])
            raw_az[i] = MathUtils.normalize_bearing(az)
            distances[i] = VectorLayerGeometry.measure_distance_between_points(
                p1["point"], p2["point"], crs
            )

        # Determina onde ocorrem as quebras
        break_points = [False] * n  # break_points[i] = True se há quebra ANTES do ponto i
        # (i.e., o ponto i inicia um novo shot)

        # O primeiro ponto nunca é quebra (início da trilha)
        break_points[0] = False

        for i in range(1, n):  # i é o índice do ponto de chegada do segmento
            # Janela para trás: segmentos [i - window, i-1] (chegando em i)
            # Janela para frente: segmentos [i, i + window - 1] (saindo de i)
            window = max_deviation_points

            # Coleta azimutes anteriores (que chegam em i)
            prev_az_list = []
            for j in range(max(1, i - window), i):  # segmento (j-1 -> j)
                if raw_az[j] is not None:
                    prev_az_list.append(raw_az[j])

            # Coleta azimutes posteriores (que saem de i)
            next_az_list = []
            for j in range(i, min(n, i + window)):  # segmento (j -> j+1)
                if j + 1 < n and raw_az[j + 1] is not None:
                    next_az_list.append(raw_az[j + 1])

            # Se não houver dados suficientes em um dos lados, mantém continuação (sem quebra)
            if not prev_az_list or not next_az_list:
                break_points[i] = False
                continue

            # Calcula azimute médio anterior (direção de chegada)
            az_prev_mean = MathUtils.axial_mean(prev_az_list)
            # Calcula azimute médio posterior (direção de saída)
            az_next_mean = MathUtils.axial_mean(next_az_list)

            # Diferença entre as direções média
            diff = MathUtils.axial_diff(az_prev_mean, az_next_mean)

            # Se a diferença exceder o limiar, marca quebra antes do ponto i
            break_points[i] = diff > severe_azimuth_threshold

        # Atribui shot_id com base nos break_points
        original_shot_ids = [1] * n
        current_shot = 1
        for i in range(1, n):
            if break_points[i]:
                current_shot += 1
            original_shot_ids[i] = current_shot

        # Validação de tamanho mínimo de grupo: grupos menores recebem shot_id=0
        shot_sizes: dict[int, int] = {}
        for shot in original_shot_ids:
            shot_sizes[shot] = shot_sizes.get(shot, 0) + 1

        validated_shot_ids = [
            shot if shot_sizes.get(shot, 0) >= minimum_point_count else 0
            for shot in original_shot_ids
        ]

        # constrói updates (igual ao original)
        updates: dict[int, dict] = {}

        for i in range(n):
            prev_segment_az = raw_az[i] if i >= 1 else None
            next_segment_az = raw_az[i + 1] if i + 1 < n else None
            dd = distances[i]

            if prev_segment_az is not None and next_segment_az is not None:
                az_instant = MathUtils.axial_mean([prev_segment_az, next_segment_az])
            elif prev_segment_az is not None:
                az_instant = prev_segment_az
            elif next_segment_az is not None:
                az_instant = next_segment_az
            else:
                az_instant = 0.0

            delta_prev = (
                MathUtils.axial_diff(az_instant, prev_segment_az)
                if prev_segment_az is not None
                else 0.0
            )
            delta_next = (
                MathUtils.axial_diff(az_instant, next_segment_az)
                if next_segment_az is not None
                else 0.0
            )

            updates[ordered_points[i]["fid"]] = {
                StripOutputFieldKey.SHOT_ID.value:          str(validated_shot_ids[i]),
                StripOutputFieldKey.OLD_SHOT_ID.value:      str(original_shot_ids[i]),
                StripOutputFieldKey.SHOT_VALID.value:       0,
                StripOutputFieldKey.AZIMUTH_INSTANT.value:  float(az_instant),
                StripOutputFieldKey.AZIMUTH_MEAN.value:     float(az_instant),
                StripOutputFieldKey.AZIMUTH_PREV.value:     float(prev_segment_az) if prev_segment_az is not None else 0.0,
                StripOutputFieldKey.AZIMUTH_NEXT.value:     float(next_segment_az) if next_segment_az is not None else 0.0,
                StripOutputFieldKey.DELTA_AZ_PREV.value:    float(delta_prev),
                StripOutputFieldKey.DELTA_AZ_NEXT.value:    float(delta_next),
                StripOutputFieldKey.DELTA_DISTANCE.value:   float(dd),
                StripOutputFieldKey.SCORE.value:            0,
                StripOutputFieldKey.SCORE_DIRECTION.value:  0,
                StripOutputFieldKey.SCORE_CONTINUITY.value: 0,
                StripOutputFieldKey.SEG_TYPE.value:         "",
                StripOutputFieldKey.DELTA_TIME.value:       0.0,
                StripOutputFieldKey.VELOCITY_INSTANT.value: 0.0,
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

    def _resolve_output_fields(self, layer, *, conflict_resolver=None):
        from ..vector.VectorLayerAttributes import VectorLayerAttributes

        max_length = 10 if self.source_path.lower().endswith(".shp") else 255
        resolved   = {}
        for logical_key, field_spec in self.DIVIDE_STRIP_FIELDS.items():
            field_name = VectorLayerAttributes.resolve_output_field_name(
                layer, field_spec.attribute,
                conflict_resolver=conflict_resolver,
                max_length=max_length,
            )
            if field_name is None:
                raise RuntimeError("Operacao cancelada pelo usuario.")
            resolved[logical_key] = field_name
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