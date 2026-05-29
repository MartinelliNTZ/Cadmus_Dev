from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import statistics
from datetime import datetime

from .IMGMetadata import IMGMetadata
from ..FormatUtils import FormatUtils
from ..MathUtils import MathUtils
from ..mrk.MetadataFields import MetadataFields
from ...core.enum import MetadataFieldKey as MFK
from ...core.config.LogUtils import LogUtils
from ..ToolKeys import ToolKey


class FlightAggregator:
    """Manipulador de grupos de voos: agrupa imagens por flight_id e calcula metricas.

    Recebe uma lista de todas as imagens e responde:
    - No voo F001, qual foi a velocidade media?
    - Quanto tempo durou?
    - Qual area foi coberta?
    - A temperatura do sensor subiu ao longo do voo?

    Nao sabe nada sobre thresholds, niveis, indicadores, alertas ou graficos.
    So sabe agrupar por voo e calcular metricas operacionais por sortida.

    Segue o padrao @staticmethod (igual ao JsonMetadataManager) - sem estado de instancia.
    """

    ROUND_DECIMALS = 2

    # Campos level5 a serem ignorados nas medias por voo
    IGNORE_LEVEL5_LABELS = {
        'Abrupt Change Flag',
        'Avg Velocity Between Photos',
        'Distance 3 D Previous',
        'Flight Number',
        'Geodesic Distance Previous',
        'Is Ideal Overlap',
        'Shutter Life Pct',
        'Strip ID',
    }

    # Palavras-chave para excluir campos de data/hora/GPS
    EXCLUDE_KEYWORDS = {
        'date', 'time', 'dt', 'lat', 'lon', 'latitude', 'longitude', 'gps',
    }

    # ===================================================================
    # METODOS AUXILIARES
    # ===================================================================
    @staticmethod
    def _get_numeric(r: IMGMetadata, keys: List[str]) -> Optional[float]:
        """Extrai o primeiro valor numerico de um resultado para as chaves informadas."""
        for key in keys:
            raw = r.level5_values.get(key)
            if raw is None:
                raw = r.values.get(key)
            if raw is None:
                raw = r.get_indicator(key)
            num = MathUtils.to_float_or_none(raw)
            if num is not None and num not in (float('inf'), float('-inf')):
                return num
        return None

    @staticmethod
    def _is_excluded_field(field_key: str, field_label: str) -> bool:
        """Define se um campo deve ser ignorado no agrupamento por voo."""
        text = f'{field_key} {field_label}'.lower()
        return any(keyword in text for keyword in FlightAggregator.EXCLUDE_KEYWORDS)

    @staticmethod
    def _ignored_level5_keys() -> set:
        """Retorna chaves level 5 ignoradas no quadro de medias por voo."""
        ignored = set()
        for key, field in MetadataFields.all_fields().items():
            if getattr(field, 'level', None) != 5:
                continue
            if str(getattr(field, 'label', '')).strip() in FlightAggregator.IGNORE_LEVEL5_LABELS:
                ignored.add(key)
        return ignored

    # ===================================================================
    # METODO PRINCIPAL
    # ===================================================================
    @staticmethod
    def aggregate(results: List[IMGMetadata]) -> Dict[str, Any]:
        """Agrupa imagens por voo e produz metricas operacionais de cada sortida.

        Args:
            results: Lista de objetos IMGMetadata processados

        Returns:
            Dict com:
                - per_flight: List[Dict] com resumo de cada voo
                - flight_level5_columns: List[Dict] com chave/label das colunas level5
                - temp_chart_series: List[Dict] com serie temporal de temperatura por voo
                - lrf_chart_series: List[Dict] com serie temporal de LRF por voo
                - temp_hourly_avg: List[Dict] com temperatura media por hora do dia
                - lrf_hourly_avg: List[Dict] com LRF medio por hora do dia
        """
        if not results:
            return {
                'per_flight': [],
                'flight_level5_columns': [],
                'temp_chart_series': [],
                'lrf_chart_series': [],
                'temp_hourly_avg': [{'hour': h, 'label': f'{h:02d}:00', 'mean': None, 'count': 0} for h in range(24)],
                'lrf_hourly_avg': [{'hour': h, 'label': f'{h:02d}:00', 'mean': None, 'count': 0} for h in range(24)],
            }

        # ===================================================================
        # GRUPO POR VOO
        # ===================================================================
        flights = defaultdict(list)
        for r in results:
            flights[r.flight_id or 'unknown'].append(r)

        # ===================================================================
        # COLUNAS LEVEL5
        # ===================================================================
        ignored_keys = FlightAggregator._ignored_level5_keys()
        level5_fields = [
            (key, field)
            for key, field in MetadataFields.all_fields().items()
            if getattr(field, 'level', None) == 5
            and key not in ignored_keys
            and not FlightAggregator._is_excluded_field(key, field.label)
        ]

        # Manter apenas campos numericos com pelo menos um valor no dataset
        numeric_level5 = []
        for key, field in level5_fields:
            for it in results:
                raw = it.level5_values.get(key)
                num = MathUtils.to_float_or_none(raw)
                if num is not None and num not in (float('inf'), float('-inf')):
                    numeric_level5.append((key, field))
                    break

        level5_fields = sorted(numeric_level5, key=lambda x: str(x[1].label).lower())
        flight_level5_columns = [
            {'key': key, 'label': field.label}
            for key, field in level5_fields
        ]

        # ===================================================================
        # LINHAS POR VOO
        # ===================================================================
        flight_rows = []
        for flight_id, items in flights.items():
            row = FlightAggregator._build_flight_row(flight_id, items, level5_fields)
            flight_rows.append(row)

        flight_rows.sort(key=lambda x: x['flight_id'].lower())

        # ===================================================================
        # SERIES TEMPORAIS POR VOO (para graficos) - com bucketizacao dinamica
        # ===================================================================
        temp_chart_series, temp_bucket_size = FlightAggregator._build_chart_series(
            flights, [MFK.SENSOR_TEMPERATURE.value, 'sensor_temp_c']
        )

        lrf_chart_series, lrf_bucket_size = FlightAggregator._build_chart_series(
            flights, [MFK.LRF_TARGET_DISTANCE.value, 'lrf_target_distance']
        )

        # Usa o mesmo bucket_size para ambos (vem do maior voo)
        chart_bucket_size = max(temp_bucket_size, lrf_bucket_size)

        # ===================================================================
        # MEDIAS POR HORA DO DIA
        # ===================================================================
        temp_hourly_avg, lrf_hourly_avg, hourly_interval_minutes = FlightAggregator._build_hourly_averages(results)

        return {
            'per_flight': flight_rows,
            'flight_level5_columns': flight_level5_columns,
            'temp_chart_series': temp_chart_series,
            'lrf_chart_series': lrf_chart_series,
            'chart_bucket_size': chart_bucket_size,
            'temp_hourly_avg': temp_hourly_avg,
            'lrf_hourly_avg': lrf_hourly_avg,
            'hourly_interval_minutes': hourly_interval_minutes,
        }

    # ===================================================================
    # CONSTRUCAO DE UMA LINHA DE VOO
    # ===================================================================
    @staticmethod
    def _build_flight_row(
        flight_id: str,
        items: List[IMGMetadata],
        level5_fields: List[Tuple[str, Any]],
    ) -> Dict[str, Any]:
        """Constroi uma linha de resumo para um unico voo."""
        # Datas
        dates = sorted([
            FormatUtils.parse_capture_datetime(it.capture_datetime)
            for it in items
            if FormatUtils.parse_capture_datetime(it.capture_datetime) is not None
        ])
        start_dt = dates[0] if dates else None
        end_dt = dates[-1] if dates else None
        duration = (end_dt - start_dt) if start_dt and end_dt else None
        total_seconds = int(duration.total_seconds()) if duration else None

        # Medias dos campos level5
        level5_means = {}
        for field_key, _field in level5_fields:
            vals = []
            for it in items:
                raw = it.level5_values.get(field_key)
                num = MathUtils.to_float_or_none(raw)
                if num is not None and num not in (float('inf'), float('-inf')):
                    vals.append(num)
            level5_means[field_key] = (
                round(statistics.mean(vals), FlightAggregator.ROUND_DECIMALS) if vals else None
            )

        # Velocidade (km/h e m/s)
        speed_kmh = [
            v for it in items
            if (v := FlightAggregator._get_numeric(it, [MFK.SPEED_3D_KMH.value, 'speed_3d_kmh'])) is not None
        ]

        # Temperatura do sensor
        sensor_temps = [
            v for it in items
            if (v := FlightAggregator._get_numeric(it, [MFK.SENSOR_TEMPERATURE.value, 'sensor_temp_c'])) is not None
        ]

        # LRF Target Distance
        lrf_dists = [
            v for it in items
            if (v := FlightAggregator._get_numeric(it, [MFK.LRF_TARGET_DISTANCE.value, 'lrf_target_distance'])) is not None
        ]

        # Altitudes
        rel_alts = [
            v for it in items
            if (v := FlightAggregator._get_numeric(it, [MFK.RELATIVE_ALTITUDE.value, 'relative_altitude'])) is not None
        ]
        abs_alts = [
            v for it in items
            if (v := FlightAggregator._get_numeric(it, [MFK.ABSOLUTE_ALTITUDE.value, 'absolute_altitude'])) is not None
        ]

        # ISO, White Balance CCT, Exposure
        isos = [
            v for it in items
            if (v := FlightAggregator._get_numeric(it, [MFK.ISO_SPEED_RATINGS.value, 'iso', MFK.RECOMMENDED_EXPOSURE_INDEX.value])) is not None
        ]
        wb_ccts = [
            v for it in items
            if (v := FlightAggregator._get_numeric(it, [MFK.WHITE_BALANCE_CCT.value, 'white_balance_cct'])) is not None
        ]
        exposures = [
            v for it in items
            if (v := FlightAggregator._get_numeric(it, [MFK.EXPOSURE_TIME.value, 'exposure_time'])) is not None and v > 0
        ]

        # Atitude do drone (roll, yaw, pitch)
        dist3d_prev = [
            abs(v) for it in items
            if (v := FlightAggregator._get_numeric(it, [MFK.DISTANCE_3D_PREVIOUS.value, 'distance_3d_previous'])) is not None
        ]
        rolls = [
            abs(v) for it in items
            if (v := FlightAggregator._get_numeric(it, [MFK.FLIGHT_ROLL_DEGREE.value, 'flight_roll_degree'])) is not None
        ]
        yaws = [
            abs(v) for it in items
            if (v := FlightAggregator._get_numeric(it, [MFK.FLIGHT_YAW_DEGREE.value, 'flight_yaw_degree'])) is not None
        ]
        pitches = [
            abs(v) for it in items
            if (v := FlightAggregator._get_numeric(it, [MFK.FLIGHT_PITCH_DEGREE.value, 'flight_pitch_degree'])) is not None
        ]

        # Altitude do solo (absoluta - relativa)
        solo_altitude = None
        if abs_alts and rel_alts:
            solo_altitude = statistics.mean(abs_alts) - statistics.mean(rel_alts)

        # Area estimada (hectares)
        estimated_area_ha = FlightAggregator._estimate_area(items, level5_means)

        # Shutter speed
        exposure_mean = statistics.mean(exposures) if exposures else None
        exposure_min = min(exposures) if exposures else None
        exposure_max = max(exposures) if exposures else None

        return {
            'flight_id': flight_id,
            'images': len(items),
            'mean_score': round(statistics.mean([it.overall_score for it in items]), 2),
            'start': start_dt.strftime('%Y-%m-%d %H:%M:%S') if start_dt else 'N/A',
            'end': end_dt.strftime('%Y-%m-%d %H:%M:%S') if end_dt else 'N/A',
            'flight_seconds': total_seconds,
            'flight_time': FormatUtils.format_duration(total_seconds),
            'avg_speed3d_kmh': (
                round(statistics.mean(speed_kmh), FlightAggregator.ROUND_DECIMALS) if speed_kmh else None
            ),
            'avg_speed3d_ms': (
                round(statistics.mean(speed_kmh) / 3.6, FlightAggregator.ROUND_DECIMALS) if speed_kmh else None
            ),
            'avg_sensor_temperature': (
                round(statistics.mean(sensor_temps), FlightAggregator.ROUND_DECIMALS) if sensor_temps else None
            ),
            'avg_lrf_target_distance': (
                round(statistics.mean(lrf_dists), FlightAggregator.ROUND_DECIMALS) if lrf_dists else None
            ),
            'avg_relative_altitude': (
                round(statistics.mean(rel_alts), FlightAggregator.ROUND_DECIMALS) if rel_alts else None
            ),
            'avg_absolute_altitude': (
                round(statistics.mean(abs_alts), FlightAggregator.ROUND_DECIMALS) if abs_alts else None
            ),
            'altitude_solo': round(solo_altitude, FlightAggregator.ROUND_DECIMALS) if solo_altitude is not None else None,
            'avg_iso': (
                round(statistics.mean(isos), FlightAggregator.ROUND_DECIMALS) if isos else None
            ),
            'avg_white_balance_cct': (
                round(statistics.mean(wb_ccts), FlightAggregator.ROUND_DECIMALS) if wb_ccts else None
            ),
            'avg_shutter_speed_text': FormatUtils.format_shutter_speed(exposure_mean),
            'shutter_speed_range_text': (
                f'entre {FormatUtils.format_shutter_speed(exposure_max)} e {FormatUtils.format_shutter_speed(exposure_min)}'
                if exposure_min is not None and exposure_max is not None
                else 'N/A'
            ),
            'avg_dist3d_previous': (
                round(statistics.mean(dist3d_prev), FlightAggregator.ROUND_DECIMALS) if dist3d_prev else None
            ),
            'avg_flight_roll': (
                round(statistics.mean(rolls), FlightAggregator.ROUND_DECIMALS) if rolls else None
            ),
            'avg_flight_yaw': (
                round(statistics.mean(yaws), FlightAggregator.ROUND_DECIMALS) if yaws else None
            ),
            'avg_flight_pitch': (
                round(statistics.mean(pitches), FlightAggregator.ROUND_DECIMALS) if pitches else None
            ),
            'estimated_area_ha': (
                round(estimated_area_ha, FlightAggregator.ROUND_DECIMALS) if estimated_area_ha is not None else None
            ),
            'level5_means': level5_means,
        }

    # ===================================================================
    # CALCULO DE AREA
    # ===================================================================
    @staticmethod
    def _estimate_area(items: List[IMGMetadata], level5_means: Dict[str, Any]) -> Optional[float]:
        """Calcula area estimada coberta pelo voo em hectares.

        Formula: area_foto = (largura_px * gsd_m) * (altura_px * gsd_m)
        Area efetiva = area_foto * (1 - overlap) * (1 - overlap)
        Total = area_efetiva * qtd_fotos / 10000
        """
        gsd_val = level5_means.get(MFK.GROUND_SAMPLE_DISTANCE_CM.value)
        foverlap_val = level5_means.get(MFK.F_OVERLAP.value)

        if gsd_val is None or gsd_val <= 0 or foverlap_val is None or not items:
            return None

        img_widths = []
        img_heights = []
        for it in items:
            w = MathUtils.to_float_or_none(it.get_indicator(MFK.EXIF_IMAGE_WIDTH.value))
            h = MathUtils.to_float_or_none(it.get_indicator(MFK.EXIF_IMAGE_HEIGHT.value))
            if w is not None and h is not None and w > 0 and h > 0:
                img_widths.append(w)
                img_heights.append(h)

        if not img_widths:
            return None

        avg_w = statistics.mean(img_widths)
        avg_h = statistics.mean(img_heights)
        gsd_m = gsd_val / 100.0
        overlap_dec = foverlap_val / 100.0

        photo_area_m2 = (avg_w * gsd_m) * (avg_h * gsd_m)
        effective_area_m2 = photo_area_m2 * (1.0 - overlap_dec) * (1.0 - overlap_dec)
        return (effective_area_m2 * len(items)) / 10000.0

    # ===================================================================
    # SERIES TEMPORAIS (com bucketizacao dinamica)
    # ===================================================================
    TARGET_SEGMENTS = 100  # Numero-alvo de pontos no grafico

    @staticmethod
    def _build_chart_series(
        flights: Dict[str, List[IMGMetadata]],
        keys: List[str],
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Monta serie temporal de valores por voo para grafico com bucketizacao.

        Diferente da abordagem anterior (1 ponto por foto), agora os dados
        sao agrupados em buckets para evitar extrapolacao em voos longos.

        Funcionamento:
        1. Encontra o voo com maior numero de fotos (max_photos)
        2. Define bucket_size = max(1, ceil(max_photos / TARGET_SEGMENTS))
        3. Para cada voo, agrupa as fotos em buckets de bucket_size fotos
        4. O valor Y de cada bucket e a MEDIA dos valores do bucket
        5. O valor X e o numero do bucket (1, 2, 3...)

        Returns:
            Tuple (series, bucket_size)
        """
        # Encontrar o voo com maior numero de fotos
        max_photos = 0
        for flight_id in flights:
            items = flights[flight_id]
            if len(items) > max_photos:
                max_photos = len(items)

        bucket_size = max(1, round(max_photos / FlightAggregator.TARGET_SEGMENTS))

        series = []
        for flight_id in sorted(flights.keys(), key=lambda x: x.lower()):
            items = flights[flight_id]
            # Agrupa valores em buckets
            buckets = []
            for idx, it in enumerate(items):
                v = FlightAggregator._get_numeric(it, keys)
                if v is not None:
                    bucket_idx = idx // bucket_size
                    if bucket_idx >= len(buckets):
                        buckets.append([])
                    buckets[bucket_idx].append(v)

            # Converte buckets em pontos (media de cada bucket)
            data = []
            for bidx, bvals in enumerate(buckets):
                if bvals:
                    data.append({'x': bidx + 1, 'y': round(statistics.mean(bvals), 2)})

            if data:
                series.append({'label': flight_id, 'data': data})

        return series, bucket_size

    @staticmethod
    def _get_interval_minutes(range_hours: float) -> int:
        """Define intervalo dinamico em minutos baseado na amplitude do horario dos dados.

        Regras:
          - range <= 0          -> 60 (fallback seguro, todos no mesmo horario)
          - 0 < range <= 1h     -> 10 min
          - 1h < range <= 3h    -> 15 min
          - 3h < range <= 10h   -> 30 min
          - range > 10h         -> 60 min (comportamento legado)
        """
        if range_hours <= 0.0:
            return 60
        elif range_hours <= 1.0:
            return 10
        elif range_hours <= 3.0:
            return 15
        elif range_hours <= 10.0:
            return 30
        else:
            return 60

    @staticmethod
    def _build_hourly_averages(
        results: List[IMGMetadata],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
        """Calcula medias por intervalo de hora do dia para temperatura e LRF.

        Returns:
            Tuple (temp_result, lrf_result, interval_minutes)

        Diferente da abordagem anterior (24 buckets fixos), agora o intervalo
        e DINAMICO: considera o horario minimo e maximo dos dados e define
        buckets de 10min, 15min, 30min ou 60min conforme a amplitude.

        IMPORTANTE: dados de dias diferentes sao agrupados pelo mesmo horario
        (ex: 08:30 do dia 1 e 08:30 do dia 2 caem no mesmo bucket), preservando
        o comportamento de analise horaria independente do dia.
        """
        # ------------------------------------------------------------------
        # 1. Extrair entradas com datetime e valores
        # ------------------------------------------------------------------
        entries = []
        for r in results:
            dt = FormatUtils.parse_capture_datetime(r.capture_datetime)
            if dt is None:
                continue
            hour_float = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
            v_temp = FlightAggregator._get_numeric(r, [MFK.SENSOR_TEMPERATURE.value, 'sensor_temp_c'])
            v_lrf = FlightAggregator._get_numeric(r, [MFK.LRF_TARGET_DISTANCE.value, 'lrf_target_distance'])
            if v_temp is not None or v_lrf is not None:
                entries.append({
                    'dt': dt,
                    'hour_float': hour_float,
                    'temp': v_temp,
                    'lrf': v_lrf,
                })

        if not entries:
            return [], [], 0

        # ------------------------------------------------------------------
        # 2. Calcular amplitude do horario (em horas)
        # ------------------------------------------------------------------
        hours = [e['hour_float'] for e in entries]
        min_hour = min(hours)
        max_hour = max(hours)
        range_hours = max_hour - min_hour

        # Caso raro: dados que cruzam meia-noite (ex: 23:00 a 01:00)
        # Neste caso usa 60min (legado) para simplicidade
        if range_hours < 0 or range_hours > 23:
            interval_minutes = 60
        else:
            interval_minutes = FlightAggregator._get_interval_minutes(range_hours)

        # ------------------------------------------------------------------
        # 3. Bucketing por intervalo
        # ------------------------------------------------------------------
        interval_hours = interval_minutes / 60.0

        temp_buckets = defaultdict(list)
        lrf_buckets = defaultdict(list)

        for e in entries:
            # Arredonda para o bucket mais proximo (ex: 08:17 com 15min -> bucket 08:15)
            bucket_key = round(e['hour_float'] / interval_hours) * interval_hours
            # Evita 24.0 que seria invalido como hora
            if bucket_key >= 24.0:
                bucket_key = 24.0 - interval_hours
            if e['temp'] is not None:
                temp_buckets[bucket_key].append(e['temp'])
            if e['lrf'] is not None:
                lrf_buckets[bucket_key].append(e['lrf'])

        # ------------------------------------------------------------------
        # 4. Montar resultado ordenado
        # ------------------------------------------------------------------
        all_keys = sorted(set(temp_buckets.keys()) | set(lrf_buckets.keys()))

        temp_result = []
        lrf_result = []
        for key in all_keys:
            hours_int = int(key)
            minutes_int = int(round((key - hours_int) * 60))
            label = f'{hours_int:02d}:{minutes_int:02d}'

            t_vals = temp_buckets.get(key, [])
            l_vals = lrf_buckets.get(key, [])

            temp_result.append({
                'hour': key,
                'label': label,
                'mean': round(statistics.mean(t_vals), 2) if t_vals else None,
                'count': len(t_vals),
            })
            lrf_result.append({
                'hour': key,
                'label': label,
                'mean': round(statistics.mean(l_vals), 2) if l_vals else None,
                'count': len(l_vals),
            })

        return temp_result, lrf_result, interval_minutes
