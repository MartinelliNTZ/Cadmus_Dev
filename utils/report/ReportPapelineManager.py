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
from .FlightAggregator import FlightAggregator
from ...core.enum.LightSourceEnum import LightSourceEnum
from ...core.enum import MetadataFieldKey as MFK
from ...core.config.LogUtils import LogUtils
from ..ToolKeys import ToolKey


class ReportPapelineManager:
    logger = LogUtils(tool=ToolKey.REPORT_METADATA, class_name="ReportPapelineManager")
    logger.debug("ReportPapelineManager class carregada")
    """Orquestrador central do relatorio fotogrametrico.

    RESPONSABILIDADE: coordenar as 3 classes especializadas:
    - JsonMetadataManager # Estatistico (distribuicoes sobre atributos)
    - FlightAggregator   # Coordenador de missao (agrupamento por voo)
    - AlertManager       # Analista de qualidade (alertas)

    E adicionar as camadas operacionais finais:
    - Informacoes gerais (equipamentos, firmware, GPS, datas)
    - Metricas avancadas (RTK, Gimbal, Yaw, Overlap, Luz)
    - Recomendacoes
    - Status de dewarp, altitude, shutter count
    """
    
    FLIGHT_STATS_ROUND_DECIMALS = 2
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
        return ReportPapelineManager.LIGHT_SOURCE_PT_LABELS.get(text, text)

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
    def _numeric_from_flight_values(results: List[IMGMetadata], keys: List[str]) -> List[float]:
        """Extrai valores numericos de todos os resultados para as chaves informadas."""
        values = []
        for r in results:
            for key in keys:
                raw = r.level5_values.get(key)
                if raw is None:
                    raw = r.values.get(key)
                if raw is None:
                    raw = r.get_indicator(key)
                num = MathUtils.to_float_or_none(raw)
                if num is not None and num not in (float('inf'), float('-inf')):
                    values.append(num)
                    break
        return values

    @staticmethod
    def analyze(results: List[IMGMetadata]) -> Dict[str, Any]:
        """Executa a agregacao completa para alimentar todas as secoes do relatorio.
        
        DELEGA:
        - Estatistica pura ao JsonMetadataManager (Estatistico)
        - Agrupamento por voo ao FlightAggregator (Coordenador de Missao)
        - Alertas ao AlertManager (Analista de Qualidade)
        
        RESPONSAVEL:
        - Informacoes gerais (equipamentos, firmware, GPS, datas)
        - Status operacionais (dewarp, altitude, shutter count)
        - Metricas avancadas (RTK, Gimbal, Yaw, Overlap, Luz)
        - Recomendacoes
        - Orquestracao final do dict agg
        """
        if not results:
            ReportPapelineManager.logger.warning("analyze chamado com lista vazia de resultados")
            return {}

        if config._config is None:
            config.load()

        # ===================================================================
        # DELEGACAO 1: Estatistico (JsonMetadataManager)
        # ===================================================================
        indicator_stats = JsonMetadataManager.compute_indicator_statistics(results)

        # ===================================================================
        # OVERALL - media geral dos scores
        # ===================================================================
        overall = [r.overall_score for r in results]
        mean_overall = round(statistics.mean(overall), 2) if overall else 0.0

        # ===================================================================
        # DELEGACAO 2: Coordenador de Missao (FlightAggregator)
        # ===================================================================
        flight_aggregator = FlightAggregator()
        flight_data = flight_aggregator.aggregate(results)

        # ===================================================================
        # INFORMACOES GERAIS (operacional, propria do ReportPapelineManager)
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
            'top_models': defaultdict(list),
            # Delegado ao FlightAggregator:
            'per_flight': flight_data.get('per_flight', []),
            'flight_level5_columns': flight_data.get('flight_level5_columns', []),
            'temp_chart_series': flight_data.get('temp_chart_series', []),
            'lrf_chart_series': flight_data.get('lrf_chart_series', []),
            'temp_hourly_avg': flight_data.get('temp_hourly_avg', []),
            'lrf_hourly_avg': flight_data.get('lrf_hourly_avg', []),
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

        # Flight totals for general info.
        total_flights = len(agg['per_flight'])
        total_flight_seconds = sum(
            row['flight_seconds'] for row in agg['per_flight']
            if row.get('flight_seconds') is not None
        )
        agg['general_info']['total_flights'] = total_flights
        agg['general_info']['total_flight_time'] = FormatUtils.format_duration(total_flight_seconds)

        # ===================================================================
        # STATUS OPERACIONAIS
        # ===================================================================
        # Dewarp
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
                dewarp_status_message = f'Warning: {dewarp_zero_count} fotos sem dewarping no voo {flights_with_dewarp0[0]}.'
            else:
                dewarp_status_type = 'warn'
                dewarp_status_message = (
                    f'Warning: {dewarp_zero_count} fotos sem dewarping em {len(flights_with_dewarp0)} voos: '
                    + ', '.join(flights_with_dewarp0)
                )

        agg['general_info']['dewarp_zero_count'] = dewarp_zero_count
        agg['general_info']['dewarp_status_type'] = dewarp_status_type
        agg['general_info']['dewarp_status_message'] = dewarp_status_message

        # Missing altitude
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

        # Last shutter count per camera
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
        # METRICAS AVANCADAS
        # ===================================================================
        overlap_values = ReportPapelineManager._numeric_from_flight_values(
            results, [MFK.PREDICTED_OVERLAP.value, MFK.F_OVERLAP.value, 'predicted_overlap', 'f_overlap']
        )
        overlap_below_pct = 0.0
        if overlap_values:
            overlap_below_ideal = [v for v in overlap_values if v < ReportPapelineManager.IDEAL_OVERLAP_PCT]
            overlap_below_pct = (len(overlap_below_ideal) / len(overlap_values) * 100.0) if overlap_values else 0.0

        yaw_err_values = ReportPapelineManager._numeric_from_flight_values(
            results, [MFK.YAW_ALIGNMENT_ERROR.value, 'yaw_alignment_error']
        )
        yaw_opposite = [v for v in yaw_err_values if v >= 150.0] if yaw_err_values else []
        yaw_opposite_pct = (len(yaw_opposite) / len(yaw_err_values) * 100.0) if yaw_err_values else 0.0

        rtk_diff_age = ReportPapelineManager._numeric_from_flight_values(
            results, [MFK.RTK_DIFF_AGE.value, 'rtk_diff_age']
        )
        rtk_stab_score = ReportPapelineManager._numeric_from_flight_values(
            results, [MFK.RTK_STABILITY_SCORE.value, 'rtk_stability_score']
        )
        gimbal_offset = ReportPapelineManager._numeric_from_flight_values(
            results, [MFK.GIMBAL_OFFSET.value, 'gimbal_offset']
        )
        size_mb = ReportPapelineManager._numeric_from_flight_values(
            results, [MFK.SIZE_MB.value, 'size_mb']
        )
        motion_blur = ReportPapelineManager._numeric_from_flight_values(
            results, [MFK.MOTION_BLUR_RISK.value, 'motion_blur_risk']
        )
        speed_ms = ReportPapelineManager._numeric_from_flight_values(
            results, [MFK.THREE_D_SPEED.value, 'speed_3d_ms']
        )
        speed_var = ReportPapelineManager._numeric_from_flight_values(
            results, [MFK.SPEED_VARIATION_INDEX.value, 'speed_variation_index']
        )

        # Light consistency
        light_consistency_vals = [
            str(r.level5_values.get(MFK.LIGHT_CONSISTENCY.value) or r.values.get('light_consistency') or '').strip()
            for r in results
        ]
        light_inconsistent_pct = (
            sum(1 for v in light_consistency_vals if v.lower() == 'inconsistent') / len(light_consistency_vals) * 100.0
            if light_consistency_vals else 0.0
        )

        # Light source classification
        light_source_vals = []
        light_source_from_text = 0
        light_source_from_code = 0
        for r in results:
            label, source = ReportPapelineManager._resolve_light_source_label(r)
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
            light_source_classes.append({
                'label_raw': raw_label,
                'label_pt': ReportPapelineManager._to_pt_light_source_label(raw_label),
                'count': count,
                'pct': round(pct, 2),
            })
        if light_source_classes:
            predominant = light_source_classes[0]
            light_source_predominant = predominant['label_pt']
            light_source_predominant_count = predominant['count']
            light_source_predominant_pct = predominant['pct']
        else:
            light_source_predominant = None
            light_source_predominant_count = None
            light_source_predominant_pct = None

        # RTK classification
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

        # Temporal and quality trends (usa _series_by_time do Estatistico)
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
                ReportPapelineManager._first_numeric_from_result(it, [MFK.PREDICTED_OVERLAP.value, MFK.F_OVERLAP.value, 'predicted_overlap', 'f_overlap'])
                for it in items
            ]
            s_overlap_vals = [v for v in s_overlap_vals if v is not None]
            strip_rows.append({
                'strip_id': sid,
                'images': len(items),
                'mean_score': round(statistics.mean(s_scores), 2) if s_scores else None,
                'mean_overlap': round(statistics.mean(s_overlap_vals), 2) if s_overlap_vals else None,
                'overlap_below_ideal_pct': round(
                    (sum(1 for v in s_overlap_vals if v < ReportPapelineManager.IDEAL_OVERLAP_PCT) / len(s_overlap_vals) * 100.0), 2
                ) if s_overlap_vals else None
            })
        problematic_strips = [
            s for s in strip_rows
            if (s['mean_score'] is not None and s['mean_score'] < 3.0)
            or (s['overlap_below_ideal_pct'] is not None and s['overlap_below_ideal_pct'] > 30.0)
        ]

        # Area total (soma das areas de cada voo)
        area_ha = None
        if agg.get('per_flight'):
            flight_areas = [f.get('estimated_area_ha') for f in agg['per_flight'] if f.get('estimated_area_ha') is not None]
            if flight_areas:
                area_ha = sum(flight_areas)

        # RTK Effective Precision
        rtk_effective_precision = ReportPapelineManager._numeric_from_flight_values(
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
            'speed_ms_recommended': f'{ReportPapelineManager.SPEED_RECOMMENDED_MIN_MS:.0f}-{ReportPapelineManager.SPEED_RECOMMENDED_MAX_MS:.0f} m/s',
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
        # DELEGACAO 3: AlertManager
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

                ReportPapelineManager.logger.info(
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
            ReportPapelineManager.logger.error(
                f"Erro ao executar AlertManager.analyze: {e}",
                code="ALERT_MANAGER_ERROR",
            )
            agg['alerts'] = []
            agg['alerts_count'] = 0

        return agg