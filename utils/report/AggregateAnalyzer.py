from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import statistics

from .IMGMetadata import IMGMetadata
from ..FormatUtils import FormatUtils
from ..MathUtils import MathUtils
from ..mrk.MetadataFields import MetadataFields
from ...core.enum.LightSourceEnum import LightSourceEnum
from ...core.enum import MetadataFieldKey as MFK
from ...core.config.LogUtils import LogUtils
from ..ToolKeys import ToolKey


class AggregateAnalyzer:
    """Manipulador de analises agregadas do conjunto de dados.

    Responsavel por extrair do conjunto de imagens todas as metricas
    e informacoes agregadas que nao sao de responsabilidade do estatistico
    (JsonMetadataManager) ou do agregador de voos (FlightAggregator).

    Responde:
    - Quais equipamentos foram usados?
    - Qual firmware estava rodando?
    - Qual datum GPS foi utilizado?
    - Qual o intervalo de datas de captura?
    - Qual camera tem o maior disparo (shutter count)?
    - Como estao distribuidos os modelos por prefixo do filename?
    - Qual a area total estimada?
    - Como estao distribuidos os LightSource?
    - Qual a media/p5/p95 de qualquer campo numerico?
    - Qual a qualidade por strips?
    - Qual a classificacao RTK?
    - Qual a tendencia temporal de PQI?
    """

    _OVERLAP_IDEAL = 60.0
    _SPEED_RECOMMENDED_MIN_MS = 5.0
    _SPEED_RECOMMENDED_MAX_MS = 10.0

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        """Converte valor para float com seguranca."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().lower()
        if text in {'', 'none', 'null', 'nan', 'inf', '+inf', '-inf', 'infinity'}:
            return None
        try:
            return float(text)
        except Exception:
            return None

    @staticmethod
    def _parse_num(value: Any) -> Optional[float]:
        """Converte valor para float com seguranca (mesmo que _to_float)."""
        return AggregateAnalyzer._to_float(value)

    # ===================================================================
    # METODOS GENERICOS DE EXTRACAO
    # ===================================================================

    @staticmethod
    def _numeric_from_flight_values(results: List[Any], keys: List[str]) -> List[float]:
        """Extrai valores numericos de todos os resultados para as chaves informadas."""
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
                num = AggregateAnalyzer._parse_num(raw)
                if num is not None and num not in (float('inf'), float('-inf')):
                    values.append(num)
                    break
        return values

    @staticmethod
    def _first_numeric_from_result(r: Any, keys: List[str]):
        """Retorna o primeiro valor numerico disponivel em um resultado para as chaves informadas."""
        for key in keys:
            raw = None
            if hasattr(r, 'level5_values'):
                raw = r.level5_values.get(key)
            if raw is None and hasattr(r, 'values'):
                raw = r.values.get(key)
            if raw is None and hasattr(r, 'get_indicator'):
                raw = r.get_indicator(key)
            num = AggregateAnalyzer._parse_num(raw)
            if num is not None and num not in (float('inf'), float('-inf')):
                return num
        return None

    @staticmethod
    def compute_percentile_stats(values: List[float]) -> Dict[str, Optional[float]]:
        """Calcula estatisticas de percentil para uma lista de valores numericos.
        
        Args:
            values: Lista de valores numericos
            
        Returns:
            Dict com mean, p5, p95, range
        """
        if not values:
            return {'mean': None, 'p5': None, 'p95': None, 'range': None}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            'mean': round(statistics.mean(values), 2),
            'p5': round(sorted_vals[int(0.05 * (n - 1))], 2),
            'p95': round(sorted_vals[int(0.95 * (n - 1))], 2),
            'range': round(sorted_vals[int(0.95 * (n - 1))] - sorted_vals[int(0.05 * (n - 1))], 2),
        }

    # ===================================================================
    # INFORMACOES GERAIS
    # ===================================================================
    @staticmethod
    def compute_general_info(results: List[IMGMetadata]) -> Dict[str, Any]:
        """Extrai informacoes gerais do conjunto de imagens."""
        equipment_models = sorted({
            r.equipment_model for r in results
            if r.equipment_model and r.equipment_model != 'unknown'
        })
        equipment_serial_numbers = sorted({
            r.equipment_serial_number for r in results
            if r.equipment_serial_number and r.equipment_serial_number != 'unknown'
        })
        camera_models = sorted({
            r.camera_model for r in results
            if r.camera_model and r.camera_model != 'unknown'
        })
        camera_serial_numbers = sorted({
            r.camera_serial_number for r in results
            if r.camera_serial_number and r.camera_serial_number != 'unknown'
        })

        firmware_versions = sorted({
            str(r.get_indicator(MFK.SOFTWARE.value) or r.get_indicator('Firmware') or '').strip()
            for r in results
            if str(r.get_indicator(MFK.SOFTWARE.value) or r.get_indicator('Firmware') or '').strip()
            and str(r.get_indicator(MFK.SOFTWARE.value) or r.get_indicator('Firmware') or '').strip().lower()
            not in {'unknown', 'none', 'null'}
        })

        parsed_dates = [
            FormatUtils.parse_capture_datetime(r.capture_datetime)
            for r in results
        ]
        parsed_dates = sorted([d for d in parsed_dates if d is not None])

        gps_datum_values = sorted({
            str(r.get_indicator(MFK.GPS_MAP_DATUM.value) or r.get_indicator('gps_map_datum') or '').strip()
            for r in results
            if str(r.get_indicator(MFK.GPS_MAP_DATUM.value) or r.get_indicator('gps_map_datum') or '').strip()
            and str(r.get_indicator(MFK.GPS_MAP_DATUM.value) or r.get_indicator('gps_map_datum') or '').strip().lower()
            not in {'', 'none', 'null'}
        })
        gps_status_values = sorted({
            str(r.get_indicator(MFK.GPS_STATUS.value) or r.get_indicator('gps_status') or '').strip()
            for r in results
            if str(r.get_indicator(MFK.GPS_STATUS.value) or r.get_indicator('gps_status') or '').strip()
            and str(r.get_indicator(MFK.GPS_STATUS.value) or r.get_indicator('gps_status') or '').strip().lower()
            not in {'', 'none', 'null'}
        })

        return {
            'equipment_models': equipment_models,
            'equipment_serial_numbers': equipment_serial_numbers,
            'camera_models': camera_models,
            'camera_serial_numbers': camera_serial_numbers,
            'firmware_versions': firmware_versions,
            'gps_datum': gps_datum_values,
            'gps_status': gps_status_values,
            'capture_start': (
                parsed_dates[0].strftime('%Y-%m-%d %H:%M:%S')
                if parsed_dates else 'N/A'
            ),
            'capture_end': (
                parsed_dates[-1].strftime('%Y-%m-%d %H:%M:%S')
                if parsed_dates else 'N/A'
            ),
        }

    # ===================================================================
    # TOP MODELS
    # ===================================================================
    @staticmethod
    def compute_top_models(results: List[IMGMetadata]) -> Dict[str, Dict[str, Any]]:
        """Agrupa imagens por prefixo do filename e calcula score medio."""
        models = defaultdict(list)
        for r in results:
            model = r.filename.split('_')[0] if '_' in r.filename else 'unknown'
            models[model].append(r.overall_score)

        top_models = {}
        for model, scores in models.items():
            top_models[model] = {
                'count': len(scores),
                'mean_score': round(statistics.mean(scores), 2),
            }
        return top_models

    # ===================================================================
    # SHUTTER COUNT POR CAMERA
    # ===================================================================
    @staticmethod
    def compute_shutter_per_camera(results: List[IMGMetadata]) -> List[Dict[str, Any]]:
        """Encontra o ultimo shutter count registrado para cada camera."""
        camera_groups = defaultdict(list)
        for r in results:
            cam = r.camera_serial_number or 'unknown'
            camera_groups[cam].append(r)

        camera_last = []
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

        return camera_last

    # ===================================================================
    # FONTE DE LUZ
    # ===================================================================
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
        """Traduz label de fonte de luz para portugues."""
        text = str(label or '').strip()
        if not text:
            return 'Desconhecida'
        return AggregateAnalyzer.LIGHT_SOURCE_PT_LABELS.get(text, text)

    @staticmethod
    def _resolve_light_source_label(result: IMGMetadata) -> Tuple[str, str]:
        """Resolve o label e a origem (texto ou codigo) da fonte de luz."""
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
    def compute_light_source_analysis(results: List[IMGMetadata]) -> Dict[str, Any]:
        """Analisa a distribuicao de fontes de luz nas imagens."""
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
            light_source_classes.append({
                'label_raw': raw_label,
                'label_pt': AggregateAnalyzer._to_pt_light_source_label(raw_label),
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

        return {
            'light_source_predominant': light_source_predominant,
            'light_source_predominant_count': light_source_predominant_count,
            'light_source_predominant_pct': light_source_predominant_pct,
            'light_source_total_classified': light_source_total,
            'light_source_classes': light_source_classes,
            'light_source_from_text': light_source_from_text,
            'light_source_from_code': light_source_from_code,
        }

    # ===================================================================
    # AREA TOTAL
    # ===================================================================
    @staticmethod
    def compute_total_area(per_flight: List[Dict[str, Any]]) -> Optional[float]:
        """Soma as areas estimadas de todos os voos."""
        if not per_flight:
            return None
        flight_areas = [
            f.get('estimated_area_ha')
            for f in per_flight
            if f.get('estimated_area_ha') is not None
        ]
        return round(sum(flight_areas), 2) if flight_areas else None

    # ===================================================================
    # METRICAS AVANCADAS (movidas do AlertManager - aqui e o local correto)
    # ===================================================================

    @staticmethod
    def compute_advanced_metrics(results: List[Any]) -> Dict[str, Any]:
        """Calcula metricas avancadas de qualidade: RTK, Gimbal, Yaw, Overlap, Luz, Blur, etc."""

        # Overlap
        overlap_values = AggregateAnalyzer._numeric_from_flight_values(
            results, [MFK.PREDICTED_OVERLAP.value, MFK.F_OVERLAP.value, 'predicted_overlap', 'f_overlap']
        )
        overlap_below_pct = 0.0
        if overlap_values:
            overlap_below_ideal = [v for v in overlap_values if v < AggregateAnalyzer._OVERLAP_IDEAL]
            overlap_below_pct = (len(overlap_below_ideal) / len(overlap_values) * 100.0) if overlap_values else 0.0
        overlap_mean = statistics.mean(overlap_values) if overlap_values else None

        # Yaw
        yaw_err_values = AggregateAnalyzer._numeric_from_flight_values(
            results, [MFK.YAW_ALIGNMENT_ERROR.value, 'yaw_alignment_error']
        )
        yaw_opposite = [v for v in yaw_err_values if v >= 150.0] if yaw_err_values else []
        yaw_opposite_pct = (len(yaw_opposite) / len(yaw_err_values) * 100.0) if yaw_err_values else 0.0

        # RTK Diff Age
        rtk_stats = AggregateAnalyzer.compute_percentile_stats(
            AggregateAnalyzer._numeric_from_flight_values(
                results, [MFK.RTK_DIFF_AGE.value, 'rtk_diff_age']
            )
        )

        # Ground Elevation
        ground_stats = AggregateAnalyzer.compute_percentile_stats(
            AggregateAnalyzer._numeric_from_flight_values(
                results, [MFK.GROUND_ELEVATION.value, 'ground_elevation']
            )
        )

        # Gimbal
        gimbal_offset = AggregateAnalyzer._numeric_from_flight_values(
            results, [MFK.GIMBAL_OFFSET.value, 'gimbal_offset']
        )
        gimbal_offset_mean = statistics.mean(gimbal_offset) if gimbal_offset else None
        gimbal_offset_std = (
            statistics.stdev(gimbal_offset) if len(gimbal_offset) > 1 else 0.0
        ) if gimbal_offset else None
        gimbal_offset_max = max(gimbal_offset) if gimbal_offset else None
        gimbal_offset_high_pct = (
            sum(1 for v in gimbal_offset if abs(v) > 1.0) / len(gimbal_offset) * 100.0
            if gimbal_offset else 0.0
        )

        # Size MB
        size_mb = AggregateAnalyzer._numeric_from_flight_values(
            results, [MFK.SIZE_MB.value, 'size_mb']
        )
        size_mb_mean = statistics.mean(size_mb) if size_mb else None
        size_mb_std = (
            statistics.stdev(size_mb) if len(size_mb) > 1 else 0.0
        ) if size_mb else None
        size_cv = (
            (statistics.stdev(size_mb) / statistics.mean(size_mb))
            if len(size_mb) > 1 and statistics.mean(size_mb) != 0 else 0.0
        ) if size_mb else None

        # Speed
        speed_ms = AggregateAnalyzer._numeric_from_flight_values(
            results, [MFK.THREE_D_SPEED.value, 'speed_3d_ms']
        )
        motion_blur = AggregateAnalyzer._numeric_from_flight_values(
            results, [MFK.MOTION_BLUR_RISK.value, 'motion_blur_risk']
        )
        speed_var = AggregateAnalyzer._numeric_from_flight_values(
            results, [MFK.SPEED_VARIATION_INDEX.value, 'speed_variation_index']
        )

        # Relative Altitude (Altura de voo)
        relative_altitude = AggregateAnalyzer._numeric_from_flight_values(
            results, [MFK.RELATIVE_ALTITUDE.value, 'relative_altitude']
        )
        relative_altitude_stats = AggregateAnalyzer.compute_percentile_stats(relative_altitude) if relative_altitude else {'mean': None, 'p5': None, 'p95': None, 'range': None}

        # Light consistency
        light_consistency_vals = []
        for r in results:
            raw = None
            if hasattr(r, 'level5_values'):
                raw = r.level5_values.get(MFK.LIGHT_CONSISTENCY.value)
            if raw is None and hasattr(r, 'values'):
                raw = r.values.get('light_consistency')
            if raw is not None:
                light_consistency_vals.append(str(raw).strip())

        light_inconsistent_pct = (
            sum(1 for v in light_consistency_vals if v.lower() == 'inconsistent')
            / len(light_consistency_vals) * 100.0
            if light_consistency_vals else 0.0
        )

        # RTK Effective Precision
        rtk_effective_precision = AggregateAnalyzer._numeric_from_flight_values(
            results, [MFK.RTK_EFFECTIVE_PRECISION.value, 'rtk_effective_precision']
        )
        rtk_effective_raw = set()
        for r in results:
            raw = None
            if hasattr(r, 'level5_values'):
                raw = r.level5_values.get(MFK.RTK_EFFECTIVE_PRECISION.value)
            if raw is None and hasattr(r, 'values'):
                raw = r.values.get('rtk_effective_precision')
            if raw is not None and str(raw).strip() and str(raw).strip().lower() not in {'', 'none', 'null', 'nan'}:
                try:
                    float(str(raw).strip())
                except (ValueError, TypeError):
                    rtk_effective_raw.add(str(raw).strip())

        return {
            'rtk_diff_age_mean': rtk_stats['mean'],
            'rtk_diff_age_p5': rtk_stats['p5'],
            'rtk_diff_age_p95': rtk_stats['p95'],
            'rtk_diff_age_range': rtk_stats['range'],
            'ground_elevation_mean': ground_stats['mean'],
            'ground_elevation_p5': ground_stats['p5'],
            'ground_elevation_p95': ground_stats['p95'],
            'ground_elevation_range': ground_stats['range'],
            'rtk_effective_precision_mean': round(statistics.mean(rtk_effective_precision), 4) if rtk_effective_precision else None,
            'rtk_effective_precision_max': round(max(rtk_effective_precision), 4) if rtk_effective_precision else None,
            'rtk_effective_precision_raw': ', '.join(sorted(rtk_effective_raw)) if rtk_effective_raw else None,
            'gimbal_offset_mean': round(gimbal_offset_mean, 4) if gimbal_offset_mean is not None else None,
            'gimbal_offset_std': round(gimbal_offset_std, 4) if gimbal_offset_std is not None else None,
            'gimbal_offset_max': round(gimbal_offset_max, 4) if gimbal_offset_max is not None else None,
            'gimbal_offset_over_1deg_pct': round(gimbal_offset_high_pct, 2) if gimbal_offset else None,
            'yaw_inconsistent_pct': round(yaw_opposite_pct, 2) if yaw_err_values else None,
            'size_mb_mean': round(size_mb_mean, 4) if size_mb_mean is not None else None,
            'size_mb_std': round(size_mb_std, 4) if size_mb_std is not None else None,
            'size_mb_cv': round(size_cv, 4) if size_cv is not None else None,
            'overlap_below_ideal_pct': round(overlap_below_pct, 2) if overlap_values else None,
            'overlap_mean': round(overlap_mean, 2) if overlap_mean is not None else None,
            'speed_ms_mean': round(statistics.mean(speed_ms), 4) if speed_ms else None,
            'speed_ms_recommended': f'{AggregateAnalyzer._SPEED_RECOMMENDED_MIN_MS:.0f}-{AggregateAnalyzer._SPEED_RECOMMENDED_MAX_MS:.0f} m/s',
            'relative_altitude_mean': relative_altitude_stats['mean'],
            'relative_altitude_p5': relative_altitude_stats['p5'],
            'relative_altitude_p95': relative_altitude_stats['p95'],
            'relative_altitude_range': relative_altitude_stats['range'],
            'motion_blur_mean': round(statistics.mean(motion_blur), 4) if motion_blur else None,
            'speed_variation_mean': round(statistics.mean(speed_var), 4) if speed_var else None,
            'light_inconsistent_pct': round(light_inconsistent_pct, 2),
        }

    # ===================================================================
    # CLASSIFICACAO RTK
    # ===================================================================
    @staticmethod
    def compute_rtk_classification(results: List[Any]) -> Dict[str, Any]:
        """Classifica a estabilidade do sinal RTK com base no RTK Stability Score."""
        rtk_stab_score = AggregateAnalyzer._numeric_from_flight_values(
            results, [MFK.RTK_STABILITY_SCORE.value, 'rtk_stability_score']
        )
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

        return {
            'rtk_stability_mean': round(mean_rtk_stab, 4) if mean_rtk_stab is not None else None,
            'rtk_stability_class': rtk_class,
        }

    # ===================================================================
    # QUALITY TRENDS
    # ===================================================================
    @staticmethod
    def compute_quality_trends(results: List[Any]) -> Dict[str, Any]:
        """Analisa tendencias temporais de qualidade PQI."""
        from . import JsonMetadataManager

        pqi_series = JsonMetadataManager._series_by_time(
            results, [MFK.PHOTOGRAMMETRY_QUALITY_INDEX.value, 'photogrammetry_quality_index']
        )

        pqi_first = statistics.mean([v for _, v in pqi_series[:max(1, len(pqi_series)//4)]]) if pqi_series else None
        pqi_last = statistics.mean([v for _, v in pqi_series[-max(1, len(pqi_series)//4):]]) if pqi_series else None
        pqi_delta = (pqi_last - pqi_first) if pqi_first is not None and pqi_last is not None else None

        morning_values = [v for dt, v in pqi_series if dt.hour < 11]
        midday_values = [v for dt, v in pqi_series if 11 <= dt.hour < 15]
        morning_mean = statistics.mean(morning_values) if morning_values else None
        midday_mean = statistics.mean(midday_values) if midday_values else None

        return {
            'pqi_first_quartile_mean': round(pqi_first, 2) if pqi_first is not None else None,
            'pqi_last_quartile_mean': round(pqi_last, 2) if pqi_last is not None else None,
            'pqi_delta': round(pqi_delta, 2) if pqi_delta is not None else None,
            'morning_pqi_mean': round(morning_mean, 2) if morning_mean is not None else None,
            'midday_pqi_mean': round(midday_mean, 2) if midday_mean is not None else None,
        }

    # ===================================================================
    # STRIP ANALYSIS
    # ===================================================================
    @staticmethod
    def compute_strip_analysis(results: List[Any]) -> Dict[str, Any]:
        """Analisa as strips (faixas) do voo, agrupando por StripID.

        Args:
            results: Lista de objetos IMGMetadata

        Returns:
            Dict com strip_rows e problematic_strips
        """
        strip_buckets = defaultdict(list)
        for r in results:
            strip = None
            if hasattr(r, 'level5_values'):
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
                AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.PREDICTED_OVERLAP.value, MFK.F_OVERLAP.value, 'predicted_overlap', 'f_overlap']
                )
                for it in items
            ]
            s_overlap_vals = [v for v in s_overlap_vals if v is not None]
            strip_rows.append({
                'strip_id': sid,
                'images': len(items),
                'mean_score': round(statistics.mean(s_scores), 2) if s_scores else None,
                'mean_overlap': round(statistics.mean(s_overlap_vals), 2) if s_overlap_vals else None,
                'overlap_below_ideal_pct': round(
                    (sum(1 for v in s_overlap_vals if v < AggregateAnalyzer._OVERLAP_IDEAL) / len(s_overlap_vals) * 100.0), 2
                ) if s_overlap_vals else None,
            })

        problematic_strips = [
            s for s in strip_rows
            if (s['mean_score'] is not None and s['mean_score'] < 3.0)
            or (s['overlap_below_ideal_pct'] is not None and s['overlap_below_ideal_pct'] > 30.0)
        ]

        return {
            'strip_rows': strip_rows,
            'problematic_strips': problematic_strips,
        }