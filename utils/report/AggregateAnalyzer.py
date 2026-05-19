from typing import List, Dict, Any, Optional
from .IMGMetadata import IMGMetadata
from collections import defaultdict
import statistics
from datetime import datetime

from ..adapter.StringAdapter import StringAdapter
from ..FormatUtils import FormatUtils
from ..MathUtils import MathUtils
from ..mrk.MetadataFields import MetadataFields
from .RangeMetadataManager import range_metadata_manager as config
from .AlertManager import AlertManager, AlertRecord
from .JsonMetadataManager import JsonMetadataManager
from ...core.enum.LightSourceEnum import LightSourceEnum
from ...core.enum import MetadataFieldKey as MFK
from ...core.config.LogUtils import LogUtils
from ..ToolKeys import ToolKey


class AggregateAnalyzer:
    logger = LogUtils(tool=ToolKey.REPORT_METADATA, class_name="AggregateAnalyzer")
    logger.debug("AggregateAnalyzer class carregada")
    """Consolida resultados por voo e gera visoes operacionais do relatorio.

    RESPONSABILIDADE: operacional - agrupamento por voo, metricas avancadas,
    alertas (via AlertManager), recomendacoes. NAO faz mais estatistica pura
    de indicadores - isso foi delegado ao JSONUtil (Estatistico).
    """
    
    @staticmethod
    def _debug_flight_area(items: List[Any], flight_id: str, gsd_val: Any, foverlap_val: Any, estimated_area_ha: Any):
        """Log detalhado do calculo de area por voo para debug."""
        AggregateAnalyzer.logger.debug(
            f"CALC AREA VOO [{flight_id}]: gsd_val={gsd_val}, foverlap_val={foverlap_val}, "
            f"estimated_area_ha={estimated_area_ha}, images={len(items)}",
            code="FLIGHT_AREA_ESTIMATE"
        )
        if items:
            w = MathUtils.to_float_or_none(items[0].get_indicator(MFK.EXIF_IMAGE_WIDTH.value))
            h = MathUtils.to_float_or_none(items[0].get_indicator(MFK.EXIF_IMAGE_HEIGHT.value))
            AggregateAnalyzer.logger.debug(
                f"CALC AREA VOO [{flight_id}]: sample width={w}, height={h}",
                code="FLIGHT_AREA_SAMPLE_DIMS"
            )

    FLIGHT_STATS_ROUND_DECIMALS = 2
    FIELD_FALLBACKS = {
        'gsd_cm': [MFK.GROUND_SAMPLE_DISTANCE_CM.value],
        'speed_3d_ms': [MFK.THREE_D_SPEED.value, MFK.SPEED_3D_KMH.value],
        'sensor_temp_c': [MFK.SENSOR_TEMPERATURE.value, MFK.LENS_TEMPERATURE.value],
    }
    FLIGHT_EXCLUDE_KEYWORDS = {
        'date', 'time', 'dt', 'lat', 'lon', 'latitude', 'longitude', 'gps',
    }
    # Ignore list for flight grouping averages (resolved from MetadataFields level=5 labels).
    FLIGHT_IGNORE_LEVEL5_LABELS = {
        'Abrupt Change Flag',
        'Avg Velocity Between Photos',
        'Distance 3 D Previous',
        'Flight Number',
        'Geodesic Distance Previous',
        'Is Ideal Overlap',
        'Shutter Life Pct',
        'Strip ID',
    }
    SPEED_RECOMMENDED_MIN_MS = 5.0
    SPEED_RECOMMENDED_MAX_MS = 10.0
    IDEAL_OVERLAP_PCT = 60.0
    LIGHT_SOURCE_PT_LABELS = {
        'Unknown': 'Desconhecida',
        'Daylight': 'Luz do dia',
        'Fluorescent': 'Fluorescente',
        'Tungsten': 'Tungstenio',
        'Flash': 'Flash',
        'Fine Weather': 'Tempo claro',
        'Cloudy Weather': 'Nublado',
        'Shade': 'Sombra',
        'Daylight Fluorescent': 'Fluorescente luz do dia',
        'Day White Fluorescent': 'Fluorescente branco dia',
        'Cool White Fluorescent': 'Fluorescente branco frio',
        'White Fluorescent': 'Fluorescente branco',
        'Warm White Fluorescent': 'Fluorescente branco quente',
        'Standard Light A': 'Luz padrao A',
        'Standard Light B': 'Luz padrao B',
        'Standard Light C': 'Luz padrao C',
        'D55': 'D55',
        'D65': 'D65',
        'D75': 'D75',
        'D50': 'D50',
        'ISO Studio Tungsten': 'Tungstenio estudio ISO',
        'Other Light Source': 'Outra fonte de luz',
    }

    @staticmethod
    def _to_pt_light_source_label(label: str) -> str:
        text = str(label or '').strip()
        if not text:
            return 'Desconhecida'
        return AggregateAnalyzer.LIGHT_SOURCE_PT_LABELS.get(text, text)

    @staticmethod
    def _resolve_light_source_label(result: IMGMetadata) -> tuple[str, str]:
        text_label = str(
            result.level5_values.get(MFK.LIGHT_SOURCE_CLASSIFICATION.value)
            or result.values.get('light_source_classification')
            or ''
        ).strip()
        if text_label:
            return text_label, 'text'

        raw_code = result.get_indicator(MFK.LIGHT_SOURCE.value)
        if raw_code in (None, '', 'None', 'null'):
            return '', 'missing'

        try:
            code = int(float(str(raw_code).strip()))
            return LightSourceEnum.get_label(code), 'code'
        except Exception:
            return '', 'missing'

    @staticmethod
    def _is_excluded_flight_field(field_key: str, field_label: str) -> bool:
        """Define se um campo deve ser ignorado no agrupamento por voo."""
        text = f'{field_key} {field_label}'.lower()
        return any(keyword in text for keyword in AggregateAnalyzer.FLIGHT_EXCLUDE_KEYWORDS)

    @staticmethod
    def _ignored_level5_keys_from_metadata_fields() -> set[str]:
        """Retorna chaves level 5 ignoradas no quadro de medias por voo."""
        ignored = set()
        for key, field in MetadataFields.all_fields().items():
            if getattr(field, 'level', None) != 5:
                continue
            if str(getattr(field, 'label', '')).strip() in AggregateAnalyzer.FLIGHT_IGNORE_LEVEL5_LABELS:
                ignored.add(key)
        return ignored

    @staticmethod
    def _first_numeric_from_result(r: IMGMetadata, keys: List[str]):
        """Retorna o primeiro valor numerico disponivel em um resultado para as chaves informadas."""
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
    def analyze(results: List[IMGMetadata]) -> Dict[str, Any]:
        """Executa a agregacao completa para alimentar todas as secoes do relatorio.
        
        DELEGA a estatistica pura ao JSONUtil (Estatistico).
        Foca no operacional: voos, metricas, alertas, recomendacoes.
        """
        if not results:
            AggregateAnalyzer.logger.warning("analyze chamado com lista vazia de resultados")
            return {}

        if config._config is None:
            config.load()

        # ===================================================================
        # DELEGACAO: Estatistico calcula distribuicoes sobre atributos
        # ===================================================================
        indicator_stats = JsonMetadataManager.compute_indicator_statistics(results)

        # ===================================================================
        # OVERALL - media geral dos scores
        # ===================================================================
        overall = [r.overall_score for r in results]
        mean_overall = round(statistics.mean(overall), 2) if overall else 0.0

        # ===================================================================
        # GERAL - equipamentos, firmware, GPS, datas (operacional)
        # ===================================================================
        equipment_models = sorted({r.equipment_model for r in results if r.equipment_model and r.equipment_model != 'unknown'})
        equipment_serial_numbers = sorted({r.equipment_serial_number for r in results if r.equipment_serial_number and r.equipment_serial_number != 'unknown'})
        camera_models = sorted({r.camera_model for r in results if r.camera_model and r.camera_model != 'unknown'})
        camera_serial_numbers = sorted({r.camera_serial_number for r in results if r.camera_serial_number and r.camera_serial_number != 'unknown'})
        firmware_versions = sorted(
            {
                str(r.get_indicator(MFK.SOFTWARE.value) or r.get_indicator('Firmware') or '').strip()
                for r in results
                if str(r.get_indicator(MFK.SOFTWARE.value) or r.get_indicator('Firmware') or '').strip()
                and str(r.get_indicator(MFK.SOFTWARE.value) or r.get_indicator('Firmware') or '').strip().lower() not in {'unknown', 'none', 'null'}
            }
        )
        parsed_dates = [FormatUtils.parse_capture_datetime(r.capture_datetime) for r in results]
        parsed_dates = sorted([d for d in parsed_dates if d is not None])

        gps_datum_values = sorted({
            str(r.get_indicator(MFK.GPS_MAP_DATUM.value) or r.get_indicator('gps_map_datum') or '').strip()
            for r in results
            if str(r.get_indicator(MFK.GPS_MAP_DATUM.value) or r.get_indicator('gps_map_datum') or '').strip()
            and str(r.get_indicator(MFK.GPS_MAP_DATUM.value) or r.get_indicator('gps_map_datum') or '').strip().lower() not in {'', 'none', 'null'}
        })
        gps_status_values = sorted({
            str(r.get_indicator(MFK.GPS_STATUS.value) or r.get_indicator('gps_status') or '').strip()
            for r in results
            if str(r.get_indicator(MFK.GPS_STATUS.value) or r.get_indicator('gps_status') or '').strip()
            and str(r.get_indicator(MFK.GPS_STATUS.value) or r.get_indicator('gps_status') or '').strip().lower() not in {'', 'none', 'null'}
        })

        agg = {
            'total_images': len(results),
            'mean_overall': mean_overall,
            'per_indicator': indicator_stats.get('per_indicator', {}),
            'level_distribution': indicator_stats.get('level_distribution', {}),
            'pqi_mean': indicator_stats.get('pqi_mean'),
            'pqi_level_distribution': indicator_stats.get('pqi_level_distribution', {}),
            'pqi_classification': indicator_stats.get('pqi_classification'),
            'indicator_catalog': indicator_stats.get('indicator_catalog', []),
            'general_info': {
                'equipment_models': equipment_models,
                'equipment_serial_numbers': equipment_serial_numbers,
                'camera_models': camera_models,
                'camera_serial_numbers': camera_serial_numbers,
                'firmware_versions': firmware_versions,
                'gps_datum': gps_datum_values,
                'gps_status': gps_status_values,
                'capture_start': parsed_dates[0].strftime('%Y-%m-%d %H:%M:%S') if parsed_dates else 'N/A',
                'capture_end': parsed_dates[-1].strftime('%Y-%m-%d %H:%M:%S') if parsed_dates else 'N/A'
            },
            'top_models': defaultdict(list)
        }

        # Top models
        models = defaultdict(list)
        for r in results:
            model = r.filename.split('_')[0] if '_' in r.filename else 'unknown'
            models[model].append(r.overall_score)
        for model, scores in models.items():
            agg['top_models'][model] = {
                'count': len(scores),
                'mean_score': round(statistics.mean(scores), 2)
            }

        # ===================================================================
        # AGRUPAMENTO POR VOO (operacional, nao e estatistica pura)
        # ===================================================================
        flights = defaultdict(list)
        for r in results:
            flights[r.flight_id or 'unknown'].append(r)

        level5_fields = [
            (key, field)
            for key, field in MetadataFields.all_fields().items()
            if getattr(field, 'level', None) == 5
        ]
        ignored_level5_keys = AggregateAnalyzer._ignored_level5_keys_from_metadata_fields()
        level5_fields = [
            (key, field)
            for key, field in level5_fields
            if key not in ignored_level5_keys and not AggregateAnalyzer._is_excluded_flight_field(key, field.label)
        ]

        # Keep only numeric fields that have at least one numeric value in the dataset.
        numeric_level5_fields = []
        for key, field in level5_fields:
            found_numeric = False
            for it in results:
                raw = it.level5_values.get(key)
                num = MathUtils.to_float_or_none(raw)
                if num is not None and num not in (float('inf'), float('-inf')):
                    found_numeric = True
                    break
            if found_numeric:
                numeric_level5_fields.append((key, field))

        level5_fields = sorted(numeric_level5_fields, key=lambda x: str(x[1].label).lower())
        agg['flight_level5_columns'] = [
            {'key': key, 'label': field.label}
            for key, field in level5_fields
        ]

        flight_rows = []
        for flight_id, items in flights.items():
            dates = sorted(
                [
                    FormatUtils.parse_capture_datetime(it.capture_datetime)
                    for it in items
                    if FormatUtils.parse_capture_datetime(it.capture_datetime) is not None
                ]
            )
            start_dt = dates[0] if dates else None
            end_dt = dates[-1] if dates else None
            duration = (end_dt - start_dt) if start_dt and end_dt else None
            total_seconds = int(duration.total_seconds()) if duration else None

            level5_means = {}
            for field_key, _field in level5_fields:
                vals = []
                for it in items:
                    raw = it.level5_values.get(field_key)
                    num = MathUtils.to_float_or_none(raw)
                    if num is not None and num not in (float('inf'), float('-inf')):
                        vals.append(num)
                level5_means[field_key] = (
                    round(statistics.mean(vals), AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if vals else None
                )

            speed3d_kmh_vals = []
            sensor_temp_vals = []
            lrf_target_distance_vals = []
            relative_altitude_vals = []
            absolute_altitude_vals = []
            iso_vals = []
            white_balance_cct_vals = []
            exposure_time_vals = []
            for it in items:
                v_speed = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.SPEED_3D_KMH.value, 'speed_3d_kmh']
                )
                if v_speed is not None and v_speed not in (float('inf'), float('-inf')):
                    speed3d_kmh_vals.append(v_speed)

                v_sensor = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.SENSOR_TEMPERATURE.value, 'sensor_temp_c']
                )
                if v_sensor is not None and v_sensor not in (float('inf'), float('-inf')):
                    sensor_temp_vals.append(v_sensor)

                v_lrf = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.LRF_TARGET_DISTANCE.value, 'lrf_target_distance']
                )
                if v_lrf is not None and v_lrf not in (float('inf'), float('-inf')):
                    lrf_target_distance_vals.append(v_lrf)

                v_rel_alt = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.RELATIVE_ALTITUDE.value, 'relative_altitude']
                )
                if v_rel_alt is not None and v_rel_alt not in (float('inf'), float('-inf')):
                    relative_altitude_vals.append(v_rel_alt)

                v_abs_alt = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.ABSOLUTE_ALTITUDE.value, 'absolute_altitude']
                )
                if v_abs_alt is not None and v_abs_alt not in (float('inf'), float('-inf')):
                    absolute_altitude_vals.append(v_abs_alt)

                v_iso = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.ISO_SPEED_RATINGS.value, 'iso', MFK.RECOMMENDED_EXPOSURE_INDEX.value]
                )
                if v_iso is not None and v_iso not in (float('inf'), float('-inf')):
                    iso_vals.append(v_iso)

                v_cct = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.WHITE_BALANCE_CCT.value, 'white_balance_cct']
                )
                if v_cct is not None and v_cct not in (float('inf'), float('-inf')):
                    white_balance_cct_vals.append(v_cct)

                v_exposure = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.EXPOSURE_TIME.value, 'exposure_time']
                )
                if v_exposure is not None and v_exposure not in (float('inf'), float('-inf')) and v_exposure > 0:
                    exposure_time_vals.append(v_exposure)

            exposure_mean = (
                statistics.mean(exposure_time_vals)
                if exposure_time_vals else None
            )
            exposure_min = min(exposure_time_vals) if exposure_time_vals else None
            exposure_max = max(exposure_time_vals) if exposure_time_vals else None

            # Novos campos por voo
            dist3d_prev_vals = []
            flight_roll_vals = []
            flight_yaw_vals = []
            flight_pitch_vals = []
            for it in items:
                v = AggregateAnalyzer._first_numeric_from_result(it, [MFK.DISTANCE_3D_PREVIOUS.value, 'distance_3d_previous'])
                if v is not None and v not in (float('inf'), float('-inf')):
                    dist3d_prev_vals.append(v)
                v = AggregateAnalyzer._first_numeric_from_result(it, [MFK.FLIGHT_ROLL_DEGREE.value, 'flight_roll_degree'])
                if v is not None and v not in (float('inf'), float('-inf')):
                    flight_roll_vals.append(abs(v))
                v = AggregateAnalyzer._first_numeric_from_result(it, [MFK.FLIGHT_YAW_DEGREE.value, 'flight_yaw_degree'])
                if v is not None and v not in (float('inf'), float('-inf')):
                    flight_yaw_vals.append(abs(v))
                v = AggregateAnalyzer._first_numeric_from_result(it, [MFK.FLIGHT_PITCH_DEGREE.value, 'flight_pitch_degree'])
                if v is not None and v not in (float('inf'), float('-inf')):
                    flight_pitch_vals.append(abs(v))

            # Calcular altitude do solo (absoluta - relativa)
            solo_altitude = None
            if absolute_altitude_vals and relative_altitude_vals:
                abs_mean = statistics.mean(absolute_altitude_vals)
                rel_mean = statistics.mean(relative_altitude_vals)
                solo_altitude = abs_mean - rel_mean

            # Calcular area estimada por voo (hectares)
            estimated_area_ha = None
            gsd_val = level5_means.get(MFK.GROUND_SAMPLE_DISTANCE_CM.value)
            foverlap_val = level5_means.get(MFK.F_OVERLAP.value)
            if gsd_val is not None and gsd_val > 0 and foverlap_val is not None and items:
                img_widths = []
                img_heights = []
                for it in items:
                    w = MathUtils.to_float_or_none(it.get_indicator(MFK.EXIF_IMAGE_WIDTH.value))
                    h = MathUtils.to_float_or_none(it.get_indicator(MFK.EXIF_IMAGE_HEIGHT.value))
                    if w is not None and h is not None and w > 0 and h > 0:
                        img_widths.append(w)
                        img_heights.append(h)
                if img_widths:
                    avg_width_px = statistics.mean(img_widths)
                    avg_height_px = statistics.mean(img_heights)
                    gsd_m = gsd_val / 100.0
                    overlap_dec = foverlap_val / 100.0
                    photo_area_m2 = (avg_width_px * gsd_m) * (avg_height_px * gsd_m)
                    effective_area_m2 = photo_area_m2 * (1.0 - overlap_dec) * (1.0 - overlap_dec)
                    estimated_area_ha = (effective_area_m2 * len(items)) / 10000.0

            AggregateAnalyzer._debug_flight_area(items, flight_id, gsd_val, foverlap_val, estimated_area_ha)

            flight_rows.append({
                'estimated_area_ha': round(estimated_area_ha, AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS) if estimated_area_ha is not None else None,
                'flight_id': flight_id,
                'images': len(items),
                'mean_score': round(statistics.mean([it.overall_score for it in items]), 2),
                'start': start_dt.strftime('%Y-%m-%d %H:%M:%S') if start_dt else 'N/A',
                'end': end_dt.strftime('%Y-%m-%d %H:%M:%S') if end_dt else 'N/A',
                'flight_seconds': total_seconds,
                'flight_time': FormatUtils.format_duration(total_seconds),
                'altitude_solo': round(solo_altitude, AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS) if solo_altitude is not None else None,
                'avg_dist3d_previous': (
                    round(statistics.mean(dist3d_prev_vals), AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if dist3d_prev_vals else None
                ),
                'avg_flight_roll': (
                    round(statistics.mean(flight_roll_vals), AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if flight_roll_vals else None
                ),
                'avg_flight_yaw': (
                    round(statistics.mean(flight_yaw_vals), AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if flight_yaw_vals else None
                ),
                'avg_flight_pitch': (
                    round(statistics.mean(flight_pitch_vals), AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if flight_pitch_vals else None
                ),
                'avg_speed3d_kmh': (
                    round(statistics.mean(speed3d_kmh_vals), AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if speed3d_kmh_vals else None
                ),
                'avg_speed3d_ms': (
                    round(statistics.mean(speed3d_kmh_vals) / 3.6, AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if speed3d_kmh_vals else None
                ),
                'avg_sensor_temperature': (
                    round(statistics.mean(sensor_temp_vals), AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if sensor_temp_vals else None
                ),
                'avg_lrf_target_distance': (
                    round(statistics.mean(lrf_target_distance_vals), AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if lrf_target_distance_vals else None
                ),
                'avg_relative_altitude': (
                    round(statistics.mean(relative_altitude_vals), AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if relative_altitude_vals else None
                ),
                'avg_absolute_altitude': (
                    round(statistics.mean(absolute_altitude_vals), AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if absolute_altitude_vals else None
                ),
                'avg_iso': (
                    round(statistics.mean(iso_vals), AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if iso_vals else None
                ),
                'avg_white_balance_cct': (
                    round(statistics.mean(white_balance_cct_vals), AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS)
                    if white_balance_cct_vals else None
                ),
                'avg_shutter_speed_text': FormatUtils.format_shutter_speed(exposure_mean),
                'shutter_speed_range_text': (
                    f'entre {FormatUtils.format_shutter_speed(exposure_max)} e {FormatUtils.format_shutter_speed(exposure_min)}'
                    if exposure_min is not None and exposure_max is not None
                    else 'N/A'
                ),
                'level5_means': level5_means,
            })

        agg['per_flight'] = sorted(flight_rows, key=lambda x: x['flight_id'].lower())

        # Temperature series per flight (for chart)
        temp_chart_series = []
        for flight_id, items in sorted(flights.items(), key=lambda kv: kv[0].lower()):
            series = []
            for idx, it in enumerate(items):
                v = AggregateAnalyzer._first_numeric_from_result(it, [MFK.SENSOR_TEMPERATURE.value, 'sensor_temp_c'])
                if v is not None and v not in (float('inf'), float('-inf')):
                    series.append({'x': idx + 1, 'y': round(v, 2)})
            if series:
                temp_chart_series.append({
                    'label': flight_id,
                    'data': series
                })
        agg['temp_chart_series'] = temp_chart_series

        # LRF Target Distance series per flight (for chart)
        lrf_chart_series = []
        for flight_id, items in sorted(flights.items(), key=lambda kv: kv[0].lower()):
            series = []
            for idx, it in enumerate(items):
                v = AggregateAnalyzer._first_numeric_from_result(it, [MFK.LRF_TARGET_DISTANCE.value, 'lrf_target_distance'])
                if v is not None and v not in (float('inf'), float('-inf')):
                    series.append({'x': idx + 1, 'y': round(v, 2)})
            if series:
                lrf_chart_series.append({
                    'label': flight_id,
                    'data': series
                })
        agg['lrf_chart_series'] = lrf_chart_series

        # Medias por hora do dia (0h-23h) para temperatura e LRF
        temp_by_hour = defaultdict(list)
        lrf_by_hour = defaultdict(list)
        for r in results:
            dt = FormatUtils.parse_capture_datetime(r.capture_datetime)
            if dt is None:
                continue
            hour = dt.hour
            v_temp = AggregateAnalyzer._first_numeric_from_result(r, [MFK.SENSOR_TEMPERATURE.value, 'sensor_temp_c'])
            if v_temp is not None and v_temp not in (float('inf'), float('-inf')):
                temp_by_hour[hour].append(v_temp)
            v_lrf = AggregateAnalyzer._first_numeric_from_result(r, [MFK.LRF_TARGET_DISTANCE.value, 'lrf_target_distance'])
            if v_lrf is not None and v_lrf not in (float('inf'), float('-inf')):
                lrf_by_hour[hour].append(v_lrf)
        temp_hourly_avg = []
        lrf_hourly_avg = []
        for h in range(24):
            t_vals = temp_by_hour.get(h, [])
            l_vals = lrf_by_hour.get(h, [])
            temp_hourly_avg.append({
                'hour': h,
                'label': f'{h:02d}:00',
                'mean': round(statistics.mean(t_vals), 2) if t_vals else None,
                'count': len(t_vals),
            })
            lrf_hourly_avg.append({
                'hour': h,
                'label': f'{h:02d}:00',
                'mean': round(statistics.mean(l_vals), 2) if l_vals else None,
                'count': len(l_vals),
            })
        agg['temp_hourly_avg'] = temp_hourly_avg
        agg['lrf_hourly_avg'] = lrf_hourly_avg

        # Flight totals for general info.
        total_flights = len(agg['per_flight'])
        total_flight_seconds = sum(
            row['flight_seconds'] for row in agg['per_flight']
            if row.get('flight_seconds') is not None
        )

        # Dewarp warning logic.
        dewarp_zero_items = [r for r in results if MathUtils.is_zero_value(r.dewarp_flag)]
        dewarp_zero_count = len(dewarp_zero_items)
        all_flight_ids = {r.flight_id or 'unknown' for r in results}
        flights_with_dewarp0 = sorted({r.flight_id or 'unknown' for r in dewarp_zero_items})

        if dewarp_zero_count == 0:
            dewarp_status_type = 'ok'
            dewarp_status_message = 'Voo feito 100% com dewarping.'
        elif all_flight_ids and set(flights_with_dewarp0) == all_flight_ids:
            dewarp_status_type = 'critical'
            dewarp_status_message = 'Mapeamento feito 100% sem dewarping (todos os voos tiveram fotos com DewarpFlag=0).'
        elif dewarp_zero_count == 1:
            item = dewarp_zero_items[0]
            dewarp_status_type = 'warn'
            dewarp_status_message = f'Warning: 1 foto sem dewarping. Foto: {item.filename} | Voo: {item.flight_id}'
        else:
            if len(flights_with_dewarp0) == 1:
                dewarp_status_type = 'warn'
                dewarp_status_message = (
                    f'Warning: {dewarp_zero_count} fotos sem dewarping no voo {flights_with_dewarp0[0]}.'
                )
            else:
                dewarp_status_type = 'warn'
                dewarp_status_message = (
                    f'Warning: {dewarp_zero_count} fotos sem dewarping em {len(flights_with_dewarp0)} voos: '
                    + ', '.join(flights_with_dewarp0)
                )

        agg['general_info']['total_flights'] = total_flights
        agg['general_info']['total_flight_time'] = FormatUtils.format_duration(total_flight_seconds)
        agg['general_info']['dewarp_zero_count'] = dewarp_zero_count
        agg['general_info']['dewarp_status_type'] = dewarp_status_type
        agg['general_info']['dewarp_status_message'] = dewarp_status_message

        # Missing altitude checks (MRK Alt and AbsoluteAltitude both missing).
        missing_alt_items = [
            r for r in results
            if MathUtils.is_missing_value(r.alt_mrk)
            and MathUtils.is_missing_value(r.absolute_altitude)
        ]
        missing_alt_count = len(missing_alt_items)
        flights_with_missing_alt = sorted({r.flight_id or 'unknown' for r in missing_alt_items})
        if missing_alt_count == 0:
            altitude_status_type = 'ok'
            altitude_status_message = 'Todas as fotos possuem Alt (MRK) e AbsoluteAltitude.'
        elif missing_alt_count == 1:
            item = missing_alt_items[0]
            altitude_status_type = 'warn'
            altitude_status_message = (
                f'Warning: 1 foto sem altitude completa. Foto: {item.filename} | Voo: {item.flight_id}'
            )
        else:
            altitude_status_type = 'warn'
            if len(flights_with_missing_alt) == 1:
                altitude_status_message = (
                    f'Warning: {missing_alt_count} fotos sem altitude completa no voo {flights_with_missing_alt[0]}.'
                )
            else:
                altitude_status_message = (
                    f'Warning: {missing_alt_count} fotos sem altitude completa em {len(flights_with_missing_alt)} voos: '
                    + ', '.join(flights_with_missing_alt)
                )

        agg['general_info']['missing_altitude_count'] = missing_alt_count
        agg['general_info']['altitude_status_type'] = altitude_status_type
        agg['general_info']['altitude_status_message'] = altitude_status_message

        # Last shutter count per camera (latest by capture datetime, fallback by max count).
        camera_last = []
        camera_groups = defaultdict(list)
        for r in results:
            cam = r.camera_serial_number or 'unknown'
            camera_groups[cam].append(r)

        for cam, items in sorted(camera_groups.items(), key=lambda kv: kv[0]):
            candidates = []
            for it in items:
                sc = MathUtils.to_float_or_none(it.shutter_count)
                if sc is None:
                    continue
                dt = FormatUtils.parse_capture_datetime(it.capture_datetime)
                candidates.append((dt, sc, it))
            if not candidates:
                continue

            with_dt = [c for c in candidates if c[0] is not None]
            if with_dt:
                best = max(with_dt, key=lambda c: c[0])
            else:
                best = max(candidates, key=lambda c: c[1])

            _dt, sc, it = best
            camera_last.append({
                'camera_serial': cam,
                'last_shutter_count': int(sc) if float(sc).is_integer() else round(sc, 2),
                'flight_id': it.flight_id,
                'file': it.filename,
            })

        agg['general_info']['last_shutter_per_camera'] = camera_last

        # ===================================================================
        # METRICAS AVANCADAS (operacional, usa _first_numeric_from_result)
        # ===================================================================
        overlap_values = AggregateAnalyzer._first_numeric_from_flight_values(
            results, [MFK.PREDICTED_OVERLAP.value, MFK.F_OVERLAP.value, 'predicted_overlap', 'f_overlap']
        )
        overlap_below_pct = 0.0
        if overlap_values:
            overlap_below_ideal = [v for v in overlap_values if v < AggregateAnalyzer.IDEAL_OVERLAP_PCT]
            overlap_below_pct = (len(overlap_below_ideal) / len(overlap_values) * 100.0) if overlap_values else 0.0

        yaw_err_values = AggregateAnalyzer._first_numeric_from_flight_values(
            results, [MFK.YAW_ALIGNMENT_ERROR.value, 'yaw_alignment_error']
        )
        yaw_opposite = [v for v in yaw_err_values if v >= 150.0] if yaw_err_values else []
        yaw_opposite_pct = (len(yaw_opposite) / len(yaw_err_values) * 100.0) if yaw_err_values else 0.0

        # Advanced metrics block.
        rtk_diff_age = AggregateAnalyzer._first_numeric_from_flight_values(
            results, [MFK.RTK_DIFF_AGE.value, 'rtk_diff_age']
        )
        rtk_stab_score = AggregateAnalyzer._first_numeric_from_flight_values(
            results, [MFK.RTK_STABILITY_SCORE.value, 'rtk_stability_score']
        )
        gimbal_offset = AggregateAnalyzer._first_numeric_from_flight_values(
            results, [MFK.GIMBAL_OFFSET.value, 'gimbal_offset']
        )
        size_mb = AggregateAnalyzer._first_numeric_from_flight_values(
            results, [MFK.SIZE_MB.value, 'size_mb']
        )
        motion_blur = AggregateAnalyzer._first_numeric_from_flight_values(
            results, [MFK.MOTION_BLUR_RISK.value, 'motion_blur_risk']
        )
        speed_ms = AggregateAnalyzer._first_numeric_from_flight_values(
            results, [MFK.THREE_D_SPEED.value, 'speed_3d_ms']
        )
        speed_var = AggregateAnalyzer._first_numeric_from_flight_values(
            results, [MFK.SPEED_VARIATION_INDEX.value, 'speed_variation_index']
        )
        light_consistency_vals = [str(r.level5_values.get(MFK.LIGHT_CONSISTENCY.value) or r.values.get('light_consistency') or '').strip() for r in results]
        light_inconsistent_pct = (
            sum(1 for v in light_consistency_vals if v.lower() == 'inconsistent') / len(light_consistency_vals) * 100.0
            if light_consistency_vals else 0.0
        )
        light_source_vals = []
        light_source_from_text = 0
        light_source_from_code = 0
        for r in results:
            label, source = AggregateAnalyzer._resolve_light_source_label(r)
            if not label:
                continue
            light_source_vals.append(label)
            if source == 'text':
                light_source_from_text += 1
            elif source == 'code':
                light_source_from_code += 1
        light_source_counts = defaultdict(int)
        for v in light_source_vals:
            light_source_counts[v] += 1
        light_source_total = sum(light_source_counts.values())
        light_source_classes = []
        for raw_label, count in sorted(
            light_source_counts.items(),
            key=lambda item: (-item[1], str(item[0]).lower()),
        ):
            pct = (count / light_source_total * 100.0) if light_source_total else 0.0
            light_source_classes.append(
                {
                    'label_raw': raw_label,
                    'label_pt': AggregateAnalyzer._to_pt_light_source_label(raw_label),
                    'count': count,
                    'pct': round(pct, 2),
                }
            )
        if light_source_classes:
            predominant = light_source_classes[0]
            light_source_predominant = predominant['label_pt']
            light_source_predominant_count = predominant['count']
            light_source_predominant_pct = predominant['pct']
        else:
            light_source_predominant = None
            light_source_predominant_count = None
            light_source_predominant_pct = None

        if rtk_stab_score:
            mean_rtk_stab = statistics.mean(rtk_stab_score)
            if mean_rtk_stab >= 95:
                rtk_class = 'Estavel'
            elif mean_rtk_stab >= 85:
                rtk_class = 'Moderado'
            else:
                rtk_class = 'Instavel'
        else:
            mean_rtk_stab = None
            rtk_class = 'Indisponivel'

        gimbal_offset_high_pct = (
            sum(1 for v in gimbal_offset if v > 1.0) / len(gimbal_offset) * 100.0
            if gimbal_offset else 0.0
        )
        size_cv = (statistics.stdev(size_mb) / statistics.mean(size_mb)) if len(size_mb) > 1 and statistics.mean(size_mb) != 0 else 0.0

        # Temporal and quality trends
        pqi_series = JsonMetadataManager._series_by_time(results, [MFK.PHOTOGRAMMETRY_QUALITY_INDEX.value, 'photogrammetry_quality_index'])
        pqi_first = statistics.mean([v for _, v in pqi_series[:max(1, len(pqi_series)//4)]]) if pqi_series else None
        pqi_last = statistics.mean([v for _, v in pqi_series[-max(1, len(pqi_series)//4):]]) if pqi_series else None
        pqi_delta = (pqi_last - pqi_first) if pqi_first is not None and pqi_last is not None else None

        morning_values = [v for dt, v in pqi_series if dt.hour < 11]
        midday_values = [v for dt, v in pqi_series if 11 <= dt.hour < 15]
        morning_mean = statistics.mean(morning_values) if morning_values else None
        midday_mean = statistics.mean(midday_values) if midday_values else None

        # Strip analysis
        strip_buckets = defaultdict(list)
        for r in results:
            strip = r.level5_values.get(MFK.STRIP_ID.value)
            try:
                strip_id = int(float(strip))
            except Exception:
                continue
            strip_buckets[strip_id].append(r)
        strip_rows = []
        for sid, items in sorted(strip_buckets.items()):
            s_scores = [it.overall_score for it in items]
            s_overlap_vals = [
                AggregateAnalyzer._first_numeric_from_result(it, [MFK.PREDICTED_OVERLAP.value, MFK.F_OVERLAP.value, 'predicted_overlap', 'f_overlap'])
                for it in items
            ]
            s_overlap_vals = [v for v in s_overlap_vals if v is not None]
            strip_rows.append({
                'strip_id': sid,
                'images': len(items),
                'mean_score': round(statistics.mean(s_scores), 2) if s_scores else None,
                'mean_overlap': round(statistics.mean(s_overlap_vals), 2) if s_overlap_vals else None,
                'overlap_below_ideal_pct': round(
                    (sum(1 for v in s_overlap_vals if v < AggregateAnalyzer.IDEAL_OVERLAP_PCT) / len(s_overlap_vals) * 100.0), 2
                ) if s_overlap_vals else None
            })
        problematic_strips = [
            s for s in strip_rows
            if (s['mean_score'] is not None and s['mean_score'] < 3.0)
            or (s['overlap_below_ideal_pct'] is not None and s['overlap_below_ideal_pct'] > 30.0)
        ]

        # Agronomic context: area estimate from per-flight calculation
        area_ha = None
        if agg.get('per_flight'):
            flight_areas = [f.get('estimated_area_ha') for f in agg['per_flight'] if f.get('estimated_area_ha') is not None]
            if flight_areas:
                area_ha = sum(flight_areas)

        # RTK Effective Precision
        rtk_effective_precision = AggregateAnalyzer._first_numeric_from_flight_values(
            results, [MFK.RTK_EFFECTIVE_PRECISION.value, 'rtk_effective_precision']
        )
        rtk_effective_raw = set()
        for r in results:
            raw = r.level5_values.get(MFK.RTK_EFFECTIVE_PRECISION.value) or r.values.get('rtk_effective_precision')
            if raw is not None and str(raw).strip() and str(raw).strip().lower() not in {'', 'none', 'null', 'nan'}:
                try:
                    float(str(raw).strip())
                except (ValueError, TypeError):
                    rtk_effective_raw.add(str(raw).strip())

        advanced_metrics = {
            'rtk_diff_age_mean': round(statistics.mean(rtk_diff_age), 4) if rtk_diff_age else None,
            'rtk_diff_age_max': round(max(rtk_diff_age), 4) if rtk_diff_age else None,
            'rtk_diff_age_p95': round(sorted(rtk_diff_age)[int(0.95*(len(rtk_diff_age)-1))], 4) if rtk_diff_age else None,
            'rtk_stability_mean': round(mean_rtk_stab, 4) if mean_rtk_stab is not None else None,
            'rtk_stability_class': rtk_class,
            'rtk_effective_precision_mean': round(statistics.mean(rtk_effective_precision), 4) if rtk_effective_precision else None,
            'rtk_effective_precision_max': round(max(rtk_effective_precision), 4) if rtk_effective_precision else None,
            'rtk_effective_precision_raw': ', '.join(sorted(rtk_effective_raw)) if rtk_effective_raw else None,
            'gimbal_offset_mean': round(statistics.mean(gimbal_offset), 4) if gimbal_offset else None,
            'gimbal_offset_std': round(statistics.stdev(gimbal_offset), 4) if len(gimbal_offset) > 1 else 0.0 if gimbal_offset else None,
            'gimbal_offset_max': round(max(gimbal_offset), 4) if gimbal_offset else None,
            'gimbal_offset_over_1deg_pct': round(gimbal_offset_high_pct, 2) if gimbal_offset else None,
            'yaw_inconsistent_pct': round(yaw_opposite_pct, 2) if yaw_err_values else None,
            'size_mb_mean': round(statistics.mean(size_mb), 4) if size_mb else None,
            'size_mb_std': round(statistics.stdev(size_mb), 4) if len(size_mb) > 1 else 0.0 if size_mb else None,
            'size_mb_cv': round(size_cv, 4) if size_mb else None,
            'overlap_below_ideal_pct': round(overlap_below_pct, 2) if overlap_values else None,
            'overlap_mean': round(statistics.mean(overlap_values), 2) if overlap_values else None,
            'speed_ms_mean': round(statistics.mean(speed_ms), 4) if speed_ms else None,
            'speed_ms_recommended': f'{AggregateAnalyzer.SPEED_RECOMMENDED_MIN_MS:.0f}-{AggregateAnalyzer.SPEED_RECOMMENDED_MAX_MS:.0f} m/s',
            'motion_blur_mean': round(statistics.mean(motion_blur), 4) if motion_blur else None,
            'speed_variation_mean': round(statistics.mean(speed_var), 4) if speed_var else None,
            'pqi_first_quartile_mean': round(pqi_first, 2) if pqi_first is not None else None,
            'pqi_last_quartile_mean': round(pqi_last, 2) if pqi_last is not None else None,
            'pqi_delta': round(pqi_delta, 2) if pqi_delta is not None else None,
            'morning_pqi_mean': round(morning_mean, 2) if morning_mean is not None else None,
            'midday_pqi_mean': round(midday_mean, 2) if midday_mean is not None else None,
            'light_inconsistent_pct': round(light_inconsistent_pct, 2),
            'light_source_predominant': light_source_predominant,
            'light_source_predominant_count': light_source_predominant_count,
            'light_source_predominant_pct': light_source_predominant_pct,
            'light_source_total_classified': light_source_total,
            'light_source_classes': light_source_classes,
            'light_source_from_text': light_source_from_text,
            'light_source_from_code': light_source_from_code,
            'estimated_area_ha': round(area_ha, 2) if area_ha is not None else None,
            'problematic_strips': problematic_strips,
        }

        recommendations = []
        if overlap_values and overlap_below_pct > 30:
            recommendations.append('Aumentar overlap para >=70% nas proximas missoes e repetir faixas com baixa sobreposicao.')
        if yaw_err_values and yaw_opposite_pct > 5:
            recommendations.append('Padronizar heading e evitar alternancia de sentido sem estrategia de bloco.')
        if gimbal_offset and gimbal_offset_high_pct > 20:
            recommendations.append('Recalibrar gimbal e validar alinhamento antes da decolagem.')
        if rtk_diff_age and max(rtk_diff_age) > 2:
            recommendations.append('Melhorar vinculacao RTK/base e reduzir idade de correcao RTK durante o voo.')
        if light_inconsistent_pct > 20:
            recommendations.append('Planejar janelas de luz mais estaveis e reduzir mudancas bruscas de iluminacao.')
        if not recommendations:
            recommendations.append('Parametros principais estaveis. Manter padrao operacional atual e monitorar indicadores criticos.')

        agg['advanced_analysis'] = {
            'critical_alerts': [],
            'metrics': advanced_metrics,
            'quality_analysis': {
                'strip_rows': strip_rows,
                'problematic_strips': problematic_strips,
            },
            'recommendations': recommendations,
        }

        # ===================================================================
        # ALERTAS CENTRALIZADOS - AlertManager
        # ===================================================================
        try:
            unified_alerts = AlertManager.analyze(results, agg)
            if unified_alerts:
                alerts_dict_list = AlertManager.to_dict_list(unified_alerts)
                agg['alerts'] = alerts_dict_list
                agg['alerts_count'] = len(unified_alerts)
                agg['alerts_summary'] = AlertManager.summary_by_category(unified_alerts)

                severity_counts = defaultdict(int)
                for a in unified_alerts:
                    severity_counts[a.severity] += 1
                agg['alerts_severity'] = dict(severity_counts)

                AggregateAnalyzer.logger.info(
                    f"AlertManager gerou {len(unified_alerts)} alertas unificados",
                    code="ALERT_MANAGER_ANALYSIS",
                    data={
                        "total_alerts": len(unified_alerts),
                        "severity": dict(severity_counts),
                        "categories": list(set(a.category for a in unified_alerts)),
                    }
                )

                critical_alerts = [
                    AlertManager.to_severity_entry(a)
                    for a in unified_alerts
                ]
                agg['advanced_analysis']['critical_alerts'] = critical_alerts
        except Exception as e:
            AggregateAnalyzer.logger.error(
                f"Erro ao executar AlertManager.analyze: {e}",
                code="ALERT_MANAGER_ERROR",
            )
            agg['alerts'] = []
            agg['alerts_count'] = 0

        return agg

    @staticmethod
    def _first_numeric_from_flight_values(results: List[IMGMetadata], keys: List[str]) -> List[float]:
        """Extrai valores numericos de todos os resultados para as chaves informadas.
        
        Diferenca de _numeric_values_from_keys (que estava em AggregateAnalyzer e agora
        esta em JSONUtil): este metodo e usado APENAS para metricas operacionais de voo,
        que sao concernentes ao AggregateAnalyzer e nao ao Estatistico.
        
        Args:
            results: Lista de IMGMetadata
            keys: Lista de chaves candidatas
        Returns:
            Lista de valores numericos validos
        """
        values = []
        for r in results:
            for key in keys:
                raw = None
                if hasattr(r, 'level5_values'):
                    raw = r.level5_values.get(key)
                if raw is None and hasattr(r, 'values'):
                    raw = r.values.get(key)
                if raw is None and hasattr(r, 'get_indicator'):
                    raw = r.get_indicator(key)
                num = MathUtils.to_float_or_none(raw)
                if num is not None and num not in (float('inf'), float('-inf')):
                    values.append(num)
                    break
        return values