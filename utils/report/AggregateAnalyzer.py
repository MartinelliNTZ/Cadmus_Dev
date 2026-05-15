from typing import List, Dict, Any, Optional
from .IMGMetadata import IMGMetadata
from collections import defaultdict
import statistics
from datetime import datetime
import math

from ..adapter.StringAdapter import StringAdapter
from ..mrk.MetadataFields import MetadataFields
from .RangeMetadataManager import range_metadata_manager as config
from .AlertManager import AlertManager, AlertRecord
from ...core.enum.LightSourceEnum import LightSourceEnum
from ...core.enum import MetadataFieldKey as MFK
from ...core.config.LogUtils import LogUtils
from ..ToolKeys import ToolKey


class AggregateAnalyzer:
    logger = LogUtils(tool=ToolKey.REPORT_METADATA, class_name="AggregateAnalyzer")
    logger.debug("AggregateAnalyzer class carregada")
    """Consolida resultados por indicador e gera visoes operacionais do relatorio."""
    
    @staticmethod
    def _debug_flight_area(items: List[Any], flight_id: str, gsd_val: Any, foverlap_val: Any, estimated_area_ha: Any):
        """Log detalhado do calculo de area por voo para debug."""
        AggregateAnalyzer.logger.debug(
            f"CALC AREA VOO [{flight_id}]: gsd_val={gsd_val}, foverlap_val={foverlap_val}, "
            f"estimated_area_ha={estimated_area_ha}, images={len(items)}",
            code="FLIGHT_AREA_ESTIMATE"
        )
        if items:
            w = AggregateAnalyzer._to_float_or_none(items[0].get_indicator(MFK.EXIF_IMAGE_WIDTH.value))
            h = AggregateAnalyzer._to_float_or_none(items[0].get_indicator(MFK.EXIF_IMAGE_HEIGHT.value))
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
    def _resolve_field_meta(indicator: str):
        """Resolve metadado de um indicador com fallback de aliases conhecidos."""
        for alias in [indicator, *AggregateAnalyzer.FIELD_FALLBACKS.get(indicator, [])]:
            for candidate in MetadataFields.resolve_candidates(alias):
                field = MetadataFields.get_field(candidate)
                if field is not None:
                    return field
        return None

    @staticmethod
    def _parse_capture_datetime(raw: str):
        """Converte texto de data/hora de captura para datetime quando possivel."""
        if not raw:
            return None
        text = str(raw).strip()
        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            pass
        for fmt in (
            '%Y:%m:%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y%m%d%H%M',
        ):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_num(value: Any) -> float:
        """Converte valores numericos/strings em float com suporte a infinitos."""
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().lower()
        if text in {'inf', '+inf', 'infinity', '+infinity', "float('inf')", 'float("inf")'}:
            return math.inf
        if text in {'-inf', '-infinity', "float('-inf')", 'float("-inf")'}:
            return -math.inf
        return float(text)

    @staticmethod
    def _fmt_num(value: float) -> str:
        """Formata numero para exibicao compacta em textos de faixa de nivel."""
        if value == math.inf:
            return 'inf'
        if value == -math.inf:
            return '-inf'
        if float(value).is_integer():
            return str(int(value))
        return f'{value:.4f}'.rstrip('0').rstrip('.')

    @staticmethod
    def _to_float_or_none(value: Any):
        """Converte para float retornando None quando nao for possivel."""
        try:
            return AggregateAnalyzer._parse_num(value)
        except Exception:
            return None

    @staticmethod
    def _is_excluded_flight_field(field_key: str, field_label: str) -> bool:
        """Define se um campo deve ser ignorado no agrupamento por voo."""
        text = f'{field_key} {field_label}'.lower()
        return any(keyword in text for keyword in AggregateAnalyzer.FLIGHT_EXCLUDE_KEYWORDS)

    @staticmethod
    def _format_duration(seconds: Optional[int]) -> str:
        """Formata duracao em segundos para HH:MM:SS."""
        if seconds is None:
            return 'N/A'
        hh = seconds // 3600
        mm = (seconds % 3600) // 60
        ss = seconds % 60
        return f'{hh:02d}:{mm:02d}:{ss:02d}'

    @staticmethod
    def _format_shutter_speed(seconds: Optional[float]) -> str:
        """Formata tempo de exposicao em notacao de obturador (ex.: 1/500s)."""
        if seconds is None or seconds <= 0:
            return 'N/A'
        if seconds >= 1:
            return f'{seconds:.2f}s'
        denom = round(1.0 / seconds)
        if denom <= 0:
            return 'N/A'
        return f'1/{denom}s'

    @staticmethod
    def _is_dewarp_zero(value: Any) -> bool:
        """Indica se o valor representa dewarp desabilitado (zero)."""
        if value is None:
            return False
        text = str(value).strip()
        if text == '':
            return False
        try:
            return float(text) == 0.0
        except Exception:
            return text == '0'

    @staticmethod
    def _is_missing_value(value: Any) -> bool:
        """Indica se o valor deve ser tratado como ausente."""
        if value is None:
            return True
        text = str(value).strip().lower()
        return text in {'', 'none', 'null', 'nan'}

    @staticmethod
    def _numeric_values_from_keys(results: List[IMGMetadata], keys: List[str]) -> List[float]:
        """Extrai serie numerica de um conjunto de chaves candidatas."""
        values = []
        for r in results:
            for key in keys:
                raw = r.level5_values.get(key)
                if raw is None:
                    raw = r.values.get(key)
                if raw is None:
                    raw = r.get_indicator(key)
                num = AggregateAnalyzer._to_float_or_none(raw)
                if num is not None and num not in (math.inf, -math.inf):
                    values.append(num)
                    break
        return values

    @staticmethod
    def _first_numeric_from_result(r: IMGMetadata, keys: List[str]):
        """Retorna o primeiro valor numerico disponivel em um resultado para as chaves informadas."""
        for key in keys:
            raw = r.level5_values.get(key)
            if raw is None:
                raw = r.values.get(key)
            if raw is None:
                raw = r.get_indicator(key)
            num = AggregateAnalyzer._to_float_or_none(raw)
            if num is not None and num not in (math.inf, -math.inf):
                return num
        return None

    @staticmethod
    def _series_by_time(results: List[IMGMetadata], keys: List[str]) -> List[tuple[datetime, float]]:
        """Monta serie temporal ordenada de valores numericos por data de captura."""
        series = []
        for r in results:
            dt = AggregateAnalyzer._parse_capture_datetime(r.capture_datetime)
            if dt is None:
                continue
            value = AggregateAnalyzer._first_numeric_from_result(r, keys)
            if value is None:
                continue
            series.append((dt, value))
        return sorted(series, key=lambda x: x[0])

    @staticmethod
    def _severity_entry(severity: str, title: str, detail: str, impact: str, action: str) -> Dict[str, str]:
        """Cria estrutura padronizada de alerta de severidade."""
        return {
            'severity': severity,
            'title': title,
            'detail': detail,
            'impact': impact,
            'action': action,
        }

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
    def _level_ranges_from_threshold(indicator: str) -> Dict[str, str]:
        """Traduz thresholds configurados para descricoes textuais por nivel (N1..N5)."""
        thresh = config.get_thresholds(indicator) if config._config else None
        if not thresh:
            return {}

        ttype = thresh.get('type')
        levels = thresh.get('levels', [])

        if ttype == 'categorical':
            mapping = thresh.get('mapping', {})
            grouped: Dict[int, List[str]] = defaultdict(list)
            for key, lvl in mapping.items():
                try:
                    grouped[int(lvl)].append(str(key))
                except Exception:
                    continue
            return {str(i): ', '.join(grouped.get(i, [])) or '-' for i in range(1, 6)}

        if ttype == 'range_best':
            out: Dict[str, str] = {}
            for i, interval in enumerate(levels[:5], start=1):
                if isinstance(interval, list) and len(interval) >= 2:
                    lo = AggregateAnalyzer._fmt_num(AggregateAnalyzer._parse_num(interval[0]))
                    hi = AggregateAnalyzer._fmt_num(AggregateAnalyzer._parse_num(interval[1]))
                    out[str(i)] = f'{lo}..{hi}'
                elif isinstance(interval, list) and len(interval) == 1:
                    lo = AggregateAnalyzer._fmt_num(AggregateAnalyzer._parse_num(interval[0]))
                    out[str(i)] = f'>={lo}'
                else:
                    out[str(i)] = '-'
            for i in range(1, 6):
                out.setdefault(str(i), '-')
            return out

        cuts: List[float] = []
        for raw in levels:
            try:
                cuts.append(AggregateAnalyzer._parse_num(raw))
            except Exception:
                continue

        if len(cuts) < 2:
            return {str(i): '-' for i in range(1, 6)}

        if ttype == 'higher_better':
            # Must mirror ReferenceRanges.classify semantics exactly:
            # level = clamp(sum(v >= cut), 1..5)
            # which means level 1 includes count 0 and 1.
            if len(cuts) >= 5:
                c2, c3, c4, c5 = cuts[1], cuts[2], cuts[3], cuts[4]
                return {
                    '1': f'<{AggregateAnalyzer._fmt_num(c2)}',
                    '2': f'>={AggregateAnalyzer._fmt_num(c2)} e <{AggregateAnalyzer._fmt_num(c3)}',
                    '3': f'>={AggregateAnalyzer._fmt_num(c3)} e <{AggregateAnalyzer._fmt_num(c4)}',
                    '4': f'>={AggregateAnalyzer._fmt_num(c4)} e <{AggregateAnalyzer._fmt_num(c5)}',
                    '5': f'>={AggregateAnalyzer._fmt_num(c5)}',
                }
            if len(cuts) == 4:
                c2, c3, c4 = cuts[1], cuts[2], cuts[3]
                return {
                    '1': f'<{AggregateAnalyzer._fmt_num(c2)}',
                    '2': f'>={AggregateAnalyzer._fmt_num(c2)} e <{AggregateAnalyzer._fmt_num(c3)}',
                    '3': f'>={AggregateAnalyzer._fmt_num(c3)} e <{AggregateAnalyzer._fmt_num(c4)}',
                    '4': f'>={AggregateAnalyzer._fmt_num(c4)}',
                    '5': '-',
                }
            if len(cuts) == 3:
                c2, c3 = cuts[1], cuts[2]
                return {
                    '1': f'<{AggregateAnalyzer._fmt_num(c2)}',
                    '2': f'>={AggregateAnalyzer._fmt_num(c2)} e <{AggregateAnalyzer._fmt_num(c3)}',
                    '3': f'>={AggregateAnalyzer._fmt_num(c3)}',
                    '4': '-',
                    '5': '-',
                }
            c2 = cuts[1]
            return {
                '1': f'<{AggregateAnalyzer._fmt_num(c2)}',
                '2': f'>={AggregateAnalyzer._fmt_num(c2)}',
                '3': '-',
                '4': '-',
                '5': '-',
            }

        if ttype == 'lower_better':
            # Must mirror ReferenceRanges.classify semantics exactly:
            # level = clamp(sum(v <= cut), 1..5)
            # usually configured with 5 cuts where last is +inf.
            if len(cuts) >= 4:
                c1, c2, c3, c4 = cuts[0], cuts[1], cuts[2], cuts[3]
                return {
                    '1': f'>{AggregateAnalyzer._fmt_num(c1)}',
                    '2': f'<={AggregateAnalyzer._fmt_num(c1)} e >{AggregateAnalyzer._fmt_num(c2)}',
                    '3': f'<={AggregateAnalyzer._fmt_num(c2)} e >{AggregateAnalyzer._fmt_num(c3)}',
                    '4': f'<={AggregateAnalyzer._fmt_num(c3)} e >{AggregateAnalyzer._fmt_num(c4)}',
                    '5': f'<={AggregateAnalyzer._fmt_num(c4)}',
                }
            if len(cuts) == 3:
                c1, c2, c3 = cuts[0], cuts[1], cuts[2]
                return {
                    '1': f'>{AggregateAnalyzer._fmt_num(c1)}',
                    '2': f'<={AggregateAnalyzer._fmt_num(c1)} e >{AggregateAnalyzer._fmt_num(c2)}',
                    '3': f'<={AggregateAnalyzer._fmt_num(c2)} e >{AggregateAnalyzer._fmt_num(c3)}',
                    '4': f'<={AggregateAnalyzer._fmt_num(c3)}',
                    '5': '-',
                }
            c1, c2 = cuts[0], cuts[1]
            return {
                '1': f'>{AggregateAnalyzer._fmt_num(c1)}',
                '2': f'<={AggregateAnalyzer._fmt_num(c1)} e >{AggregateAnalyzer._fmt_num(c2)}',
                '3': f'<={AggregateAnalyzer._fmt_num(c2)}',
                '4': '-',
                '5': '-',
            }

        return {str(i): '-' for i in range(1, 6)}

    @staticmethod
    def analyze(results: List[IMGMetadata]) -> Dict[str, Any]:
        """Executa a agregacao completa para alimentar todas as secoes do relatorio."""
        if not results:
            AggregateAnalyzer.logger.warning("analyze chamado com lista vazia de resultados")
            return {}

        if config._config is None:
            config.load()

        all_inds = set()
        for r in results:
            all_inds.update(r.levels.keys())

        stats = {}
        level_dist = defaultdict(int)

        for ind in all_inds:
            levels = [r.levels.get(ind, 3) for r in results]
            field_meta = AggregateAnalyzer._resolve_field_meta(ind)
            thresh = config.get_thresholds(ind) if config._config else {}
            numeric_values = []
            for r in results:
                if ind in r.values:
                    num = AggregateAnalyzer._to_float_or_none(r.values.get(ind))
                    if num is not None and num not in (math.inf, -math.inf):
                        numeric_values.append(num)

            if numeric_values:
                value_mean = statistics.mean(numeric_values)
                value_std = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0.0
                value_min = min(numeric_values)
                value_max = max(numeric_values)
                value_range = value_max - value_min
            else:
                value_mean = value_std = value_min = value_max = value_range = None

            stats[ind] = {
                'label': field_meta.label if field_meta else ind,
                'description': field_meta.description if field_meta else '',
                'threshold_type': (thresh or {}).get('type', 'unknown'),
                'level_ranges': AggregateAnalyzer._level_ranges_from_threshold(ind),
                'mean': round(statistics.mean(levels), 2),
                'std': round(statistics.stdev(levels) if len(levels) > 1 else 0, 2),
                'value_mean': round(value_mean, 4) if value_mean is not None else None,
                'value_std': round(value_std, 4) if value_std is not None else None,
                'value_min': round(value_min, 4) if value_min is not None else None,
                'value_max': round(value_max, 4) if value_max is not None else None,
                'value_range': round(value_range, 4) if value_range is not None else None,
                'dist': {1: levels.count(1), 2: levels.count(2), 3: levels.count(3), 4: levels.count(4), 5: levels.count(5)}
            }
            for lvl in levels:
                level_dist[lvl] += 1

        # Keep a deterministic and readable order in the report.
        stats = dict(
            sorted(
                stats.items(),
                key=lambda item: (str(item[1].get('label') or item[0])).lower()
            )
        )

        overall = [r.overall_score for r in results]
        
        # Compute PQI-based score for overall quality display (PQI-based classification).
        pqi_values = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.PHOTOGRAMMETRY_QUALITY_INDEX.value, 'photogrammetry_quality_index'])
        pqi_mean = statistics.mean(pqi_values) if pqi_values else None
        pqi_levels = []
        pqi_thresh = config.get_thresholds('photogrammetry_quality_index') if config._config else None
        if pqi_thresh and pqi_values:
            for v in pqi_values:
                try:
                    # count how many thresholds are met, then offset by +1
                    # count=0 → level=1, count=1 → level=2, count=2 → level=3, etc.
                    pqi_count = sum(1 for cut in pqi_thresh.get('levels', []) if v >= float(cut))
                    pqi_level = max(1, min(5, pqi_count + 1))
                except Exception:
                    pqi_level = 3
                pqi_levels.append(pqi_level)
        else:
            pqi_levels = [3] * len(results)
        pqi_level_dist = defaultdict(int)
        for lvl in pqi_levels:
            pqi_level_dist[lvl] += 1
        
        agg = {
            'total_images': len(results),
            'mean_overall': round(statistics.mean(overall), 2),
            'pqi_mean': round(pqi_mean, 2) if pqi_mean is not None else None,
            'pqi_level_distribution': dict(pqi_level_dist),
            'level_distribution': dict(level_dist),
            'per_indicator': stats,
            'top_models': defaultdict(list)
        }

        # Add PQI-based classification message
        if pqi_mean is not None:
            # Classify PQI: count how many thresholds are met, then map to level.
            # With higher_better levels [45, 60, 75, 85, 95]:
            #   count=0 → level=1 (Critica: v < 45)
            #   count=1 → level=2 (Baixa: 45 <= v < 60)
            #   count=2 → level=3 (OK: 60 <= v < 75)
            #   count=3 → level=4 (Boa: 75 <= v < 85)
            #   count=4+ → level=5 (Excelente: v >= 85)
            pqi_cuts = [float(c) for c in (pqi_thresh.get('levels', []) if pqi_thresh else [])]
            count = sum(1 for cut in pqi_cuts if pqi_mean >= cut)
            # Offset by +1 because level=1 encompasses both count=0 AND count=1
            pqi_classify_level = max(1, min(5, count + 1))
            pqi_classify_level = max(1, min(5, pqi_classify_level))
            pqi_messages = pqi_thresh.get('messages', []) if pqi_thresh else []
            pqi_label = pqi_messages[pqi_classify_level - 1] if pqi_classify_level - 1 < len(pqi_messages) else f'Nivel {pqi_classify_level}'
            agg['pqi_classification'] = {
                'level': pqi_classify_level,
                'label': pqi_label,
                'score_display': f'{pqi_mean:.0f}/100'
            }
        else:
            agg['pqi_classification'] = None
        indicator_meta_source = {
            key: AggregateAnalyzer._resolve_field_meta(key)
            for key in stats.keys()
            if AggregateAnalyzer._resolve_field_meta(key) is not None
        }
        agg['indicator_catalog'] = StringAdapter.to_key_label_description(indicator_meta_source)

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
        parsed_dates = [AggregateAnalyzer._parse_capture_datetime(r.capture_datetime) for r in results]
        parsed_dates = sorted([d for d in parsed_dates if d is not None])

        # GPS Datum e GPS Status (valores unicos)
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

        agg['general_info'] = {
            'equipment_models': equipment_models,
            'equipment_serial_numbers': equipment_serial_numbers,
            'camera_models': camera_models,
            'camera_serial_numbers': camera_serial_numbers,
            'firmware_versions': firmware_versions,
            'gps_datum': gps_datum_values,
            'gps_status': gps_status_values,
            'capture_start': parsed_dates[0].strftime('%Y-%m-%d %H:%M:%S') if parsed_dates else 'N/A',
            'capture_end': parsed_dates[-1].strftime('%Y-%m-%d %H:%M:%S') if parsed_dates else 'N/A'
        }

        models = defaultdict(list)
        for r in results:
            model = r.filename.split('_')[0] if '_' in r.filename else 'unknown'
            models[model].append(r.overall_score)

        for model, scores in models.items():
            agg['top_models'][model] = {
                'count': len(scores),
                'mean_score': round(statistics.mean(scores), 2)
            }

        # Group by flight_id derived from MrkFile.
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
                num = AggregateAnalyzer._to_float_or_none(raw)
                if num is not None and num not in (math.inf, -math.inf):
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
                    AggregateAnalyzer._parse_capture_datetime(it.capture_datetime)
                    for it in items
                    if AggregateAnalyzer._parse_capture_datetime(it.capture_datetime) is not None
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
                    num = AggregateAnalyzer._to_float_or_none(raw)
                    if num is not None and num not in (math.inf, -math.inf):
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
                if v_speed is not None and v_speed not in (math.inf, -math.inf):
                    speed3d_kmh_vals.append(v_speed)

                v_sensor = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.SENSOR_TEMPERATURE.value, 'sensor_temp_c']
                )
                if v_sensor is not None and v_sensor not in (math.inf, -math.inf):
                    sensor_temp_vals.append(v_sensor)

                v_lrf = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.LRF_TARGET_DISTANCE.value, 'lrf_target_distance']
                )
                if v_lrf is not None and v_lrf not in (math.inf, -math.inf):
                    lrf_target_distance_vals.append(v_lrf)

                v_rel_alt = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.RELATIVE_ALTITUDE.value, 'relative_altitude']
                )
                if v_rel_alt is not None and v_rel_alt not in (math.inf, -math.inf):
                    relative_altitude_vals.append(v_rel_alt)

                v_abs_alt = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.ABSOLUTE_ALTITUDE.value, 'absolute_altitude']
                )
                if v_abs_alt is not None and v_abs_alt not in (math.inf, -math.inf):
                    absolute_altitude_vals.append(v_abs_alt)

                v_iso = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.ISO_SPEED_RATINGS.value, 'iso', MFK.RECOMMENDED_EXPOSURE_INDEX.value]
                )
                if v_iso is not None and v_iso not in (math.inf, -math.inf):
                    iso_vals.append(v_iso)

                v_cct = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.WHITE_BALANCE_CCT.value, 'white_balance_cct']
                )
                if v_cct is not None and v_cct not in (math.inf, -math.inf):
                    white_balance_cct_vals.append(v_cct)

                v_exposure = AggregateAnalyzer._first_numeric_from_result(
                    it, [MFK.EXPOSURE_TIME.value, 'exposure_time']
                )
                if v_exposure is not None and v_exposure not in (math.inf, -math.inf) and v_exposure > 0:
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
                if v is not None and v not in (math.inf, -math.inf):
                    dist3d_prev_vals.append(v)
                v = AggregateAnalyzer._first_numeric_from_result(it, [MFK.FLIGHT_ROLL_DEGREE.value, 'flight_roll_degree'])
                if v is not None and v not in (math.inf, -math.inf):
                    flight_roll_vals.append(abs(v))
                v = AggregateAnalyzer._first_numeric_from_result(it, [MFK.FLIGHT_YAW_DEGREE.value, 'flight_yaw_degree'])
                if v is not None and v not in (math.inf, -math.inf):
                    flight_yaw_vals.append(abs(v))
                v = AggregateAnalyzer._first_numeric_from_result(it, [MFK.FLIGHT_PITCH_DEGREE.value, 'flight_pitch_degree'])
                if v is not None and v not in (math.inf, -math.inf):
                    flight_pitch_vals.append(abs(v))

            # Calcular altitude do solo (absoluta - relativa)
            solo_altitude = None
            if absolute_altitude_vals and relative_altitude_vals:
                abs_mean = statistics.mean(absolute_altitude_vals)
                rel_mean = statistics.mean(relative_altitude_vals)
                solo_altitude = abs_mean - rel_mean

            # Calcular area estimada por voo (hectares)
            # Formula: area_foto = (largura_px * gsd_m) * (altura_px * gsd_m) / 10000
            # Com sobreposicao: area_efetiva = area_foto * (1 - overlap) * (1 - overlap)
            estimated_area_ha = None
            gsd_val = level5_means.get(MFK.GROUND_SAMPLE_DISTANCE_CM.value)
            foverlap_val = level5_means.get(MFK.F_OVERLAP.value)
            if gsd_val is not None and gsd_val > 0 and foverlap_val is not None and items:
                # Dimensoes medias das imagens (EXIF) via get_indicator (acesso interno _data)
                img_widths = []
                img_heights = []
                for it in items:
                    w = AggregateAnalyzer._to_float_or_none(it.get_indicator(MFK.EXIF_IMAGE_WIDTH.value))
                    h = AggregateAnalyzer._to_float_or_none(it.get_indicator(MFK.EXIF_IMAGE_HEIGHT.value))
                    if w is not None and h is not None and w > 0 and h > 0:
                        img_widths.append(w)
                        img_heights.append(h)
                if img_widths:
                    avg_width_px = statistics.mean(img_widths)
                    avg_height_px = statistics.mean(img_heights)
                    gsd_m = gsd_val / 100.0
                    overlap_dec = foverlap_val / 100.0
                    # Area no solo de cada foto (m²)
                    photo_area_m2 = (avg_width_px * gsd_m) * (avg_height_px * gsd_m)
                    # Area efetiva considerando sobreposicao frontal e lateral (assume mesma %)
                    effective_area_m2 = photo_area_m2 * (1.0 - overlap_dec) * (1.0 - overlap_dec)
                    # Total do voo em hectares
                    estimated_area_ha = (effective_area_m2 * len(items)) / 10000.0
            
            # Debug log
            AggregateAnalyzer._debug_flight_area(items, flight_id, gsd_val, foverlap_val, estimated_area_ha)

            flight_rows.append({
                'estimated_area_ha': round(estimated_area_ha, AggregateAnalyzer.FLIGHT_STATS_ROUND_DECIMALS) if estimated_area_ha is not None else None,
                'flight_id': flight_id,
                'images': len(items),
                'mean_score': round(statistics.mean([it.overall_score for it in items]), 2),
                'start': start_dt.strftime('%Y-%m-%d %H:%M:%S') if start_dt else 'N/A',
                'end': end_dt.strftime('%Y-%m-%d %H:%M:%S') if end_dt else 'N/A',
                'flight_seconds': total_seconds,
                'flight_time': AggregateAnalyzer._format_duration(total_seconds),
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
                'avg_shutter_speed_text': AggregateAnalyzer._format_shutter_speed(exposure_mean),
                'shutter_speed_range_text': (
                    f'entre {AggregateAnalyzer._format_shutter_speed(exposure_max)} e {AggregateAnalyzer._format_shutter_speed(exposure_min)}'
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
                if v is not None and v not in (math.inf, -math.inf):
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
                if v is not None and v not in (math.inf, -math.inf):
                    series.append({'x': idx + 1, 'y': round(v, 2)})
            if series:
                lrf_chart_series.append({
                    'label': flight_id,
                    'data': series
                })
        agg['lrf_chart_series'] = lrf_chart_series

        def _is_zero_or_none(val):
            """Check if a value is None, zero, or empty."""
            if val is None:
                return True
            if isinstance(val, (int, float)):
                return val == 0.0
            if isinstance(val, str):
                return val.strip() in ('', 'N/A')
            return False

        # Compute column visibility: hide columns where ALL flights have None or 0 for that field
        if agg['per_flight']:
            all_none_speed3d = all(_is_zero_or_none(f.get('avg_speed3d_kmh')) for f in agg['per_flight'])
            all_none_sensor_temp = all(_is_zero_or_none(f.get('avg_sensor_temperature')) for f in agg['per_flight'])
            all_none_lrf = all(_is_zero_or_none(f.get('avg_lrf_target_distance')) for f in agg['per_flight'])
            all_none_rel_alt = all(_is_zero_or_none(f.get('avg_relative_altitude')) for f in agg['per_flight'])
            all_none_abs_alt = all(_is_zero_or_none(f.get('avg_absolute_altitude')) for f in agg['per_flight'])
            all_none_iso = all(_is_zero_or_none(f.get('avg_iso')) for f in agg['per_flight'])
            all_none_shutter = all(
                f.get('avg_shutter_speed_text') in (None, '', 'N/A')
                for f in agg['per_flight']
            )
            all_none_wb_cct = all(_is_zero_or_none(f.get('avg_white_balance_cct')) for f in agg['per_flight'])
            all_none_dist3d = all(_is_zero_or_none(f.get('avg_dist3d_previous')) for f in agg['per_flight'])
            all_none_flight_roll = all(_is_zero_or_none(f.get('avg_flight_roll')) for f in agg['per_flight'])
            all_none_flight_yaw = all(_is_zero_or_none(f.get('avg_flight_yaw')) for f in agg['per_flight'])
            all_none_flight_pitch = all(_is_zero_or_none(f.get('avg_flight_pitch')) for f in agg['per_flight'])

            agg['show_column_speed3d_kmh'] = not all_none_speed3d
            agg['show_column_sensor_temp'] = not all_none_sensor_temp
            agg['show_column_lrf'] = not all_none_lrf
            agg['show_column_rel_alt'] = not all_none_rel_alt
            agg['show_column_abs_alt'] = not all_none_abs_alt
            agg['show_column_iso'] = not all_none_iso
            agg['show_column_shutter'] = not all_none_shutter
            agg['show_column_wb_cct'] = not all_none_wb_cct
            agg['show_column_dist3d'] = not all_none_dist3d
            agg['show_column_flight_roll'] = not all_none_flight_roll
            agg['show_column_flight_yaw'] = not all_none_flight_yaw
            agg['show_column_flight_pitch'] = not all_none_flight_pitch

            # level5 columns: hide if all flights have None or 0 for that field
            level5_keys = [col['key'] for col in agg.get('flight_level5_columns', [])]
            for col_key in level5_keys:
                all_zero_or_none = all(
                    _is_zero_or_none(f.get('level5_means', {}).get(col_key))
                    for f in agg['per_flight']
                )
                agg[f'show_column_level5_{col_key}'] = not all_zero_or_none
        else:
            agg['show_column_speed3d_kmh'] = True
            agg['show_column_sensor_temp'] = True
            agg['show_column_lrf'] = True
            agg['show_column_rel_alt'] = True
            agg['show_column_abs_alt'] = True
            agg['show_column_iso'] = True
            agg['show_column_shutter'] = True
            agg['show_column_wb_cct'] = True

        # Flight totals for general info.
        total_flights = len(agg['per_flight'])
        total_flight_seconds = sum(
            row['flight_seconds'] for row in agg['per_flight']
            if row.get('flight_seconds') is not None
        )

        # Dewarp warning logic.
        dewarp_zero_items = [r for r in results if AggregateAnalyzer._is_dewarp_zero(r.dewarp_flag)]
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
        agg['general_info']['total_flight_time'] = AggregateAnalyzer._format_duration(total_flight_seconds)
        agg['general_info']['dewarp_zero_count'] = dewarp_zero_count
        agg['general_info']['dewarp_status_type'] = dewarp_status_type
        agg['general_info']['dewarp_status_message'] = dewarp_status_message

        # Missing altitude checks (MRK Alt and AbsoluteAltitude both missing).
        # When source is photo_only (no MRK), alt_mrk is None, but AbsoluteAltitude may exist.
        # Only flag if AMBAS as fontes de altitude estao ausentes.
        missing_alt_items = [
            r for r in results
            if AggregateAnalyzer._is_missing_value(r.alt_mrk)
            and AggregateAnalyzer._is_missing_value(r.absolute_altitude)
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
                sc = AggregateAnalyzer._to_float_or_none(it.shutter_count)
                if sc is None:
                    continue
                dt = AggregateAnalyzer._parse_capture_datetime(it.capture_datetime)
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

        # Advanced analysis (only complementary items not already in existing sections).
        critical_alerts = []

        # 1) Dewarp critical rule.
        if dewarp_zero_count == len(results) and len(results) > 0:
            critical_alerts.append(
                AggregateAnalyzer._severity_entry(
                    'CRITICO',
                    'Dewarp desativado em 100% das imagens',
                    f'{dewarp_zero_count}/{len(results)} imagens com DewarpFlag=0.',
                    'Risco elevado de distorcao sistematica e degradacao da aerotriangulacao.',
                    'Reprocessar com dewarping habilitado e validar calibracao interna da camera.'
                )
            )

        # 2) Overlap critical rule (<60 in >30%).
        overlap_values = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.PREDICTED_OVERLAP.value, MFK.F_OVERLAP.value, 'predicted_overlap', 'f_overlap'])
        overlap_below_ideal = [v for v in overlap_values if v < AggregateAnalyzer.IDEAL_OVERLAP_PCT]
        overlap_below_pct = (len(overlap_below_ideal) / len(overlap_values) * 100.0) if overlap_values else 0.0
        if overlap_values and overlap_below_pct > 30.0:
            critical_alerts.append(
                AggregateAnalyzer._severity_entry(
                    'CRITICO',
                    'Overlap insuficiente para reconstrucao robusta',
                    f'{overlap_below_pct:.2f}% das imagens com overlap < {AggregateAnalyzer.IDEAL_OVERLAP_PCT:.0f}%.',
                    'Pode causar lacunas, alinhamento fraco e aumento de ruído no modelo 3D.',
                    'Aumentar sobreposicao longitudinal/lateral e refazer as faixas criticas.'
                )
            )

        # 3) RTK signal quality using thresholds from config.yaml (lower_better level 1 cutoff).
        rtk_std_lat_vals = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.RTK_STD_LAT.value, 'rtk_std_lat'])
        rtk_std_hgt_vals = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.RTK_STD_HGT.value, 'rtk_std_hgt'])
        lat_thresh = config.get_thresholds('rtk_std_lat') if config._config else None
        hgt_thresh = config.get_thresholds('rtk_std_hgt') if config._config else None
        lat_cut = lat_thresh['levels'][0] if lat_thresh and lat_thresh.get('levels') else 0.011
        hgt_cut = hgt_thresh['levels'][0] if hgt_thresh and hgt_thresh.get('levels') else 0.026
        poor_lat = [v for v in rtk_std_lat_vals if v > float(AggregateAnalyzer._parse_num(lat_cut))]
        poor_hgt = [v for v in rtk_std_hgt_vals if v > float(AggregateAnalyzer._parse_num(hgt_cut))]
        poor_lat_pct = (len(poor_lat) / len(rtk_std_lat_vals) * 100.0) if rtk_std_lat_vals else 0.0
        poor_hgt_pct = (len(poor_hgt) / len(rtk_std_hgt_vals) * 100.0) if rtk_std_hgt_vals else 0.0
        if rtk_std_lat_vals and rtk_std_hgt_vals and (poor_lat_pct > 20.0 or poor_hgt_pct > 20.0):
            lat_str = AggregateAnalyzer._fmt_num(AggregateAnalyzer._parse_num(lat_cut))
            hgt_str = AggregateAnalyzer._fmt_num(AggregateAnalyzer._parse_num(hgt_cut))
            critical_alerts.append(
                AggregateAnalyzer._severity_entry(
                    'CRITICO',
                    'Sinal GPS/RTK com qualidade insuficiente',
                    (
                        f'RtkStdLat > {lat_str} em {poor_lat_pct:.2f}% das imagens '
                        f'e RtkStdHgt > {hgt_str} em {poor_hgt_pct:.2f}% das imagens.'
                    ),
                    'Reduz precisao posicional e pode degradar alinhamento, georreferenciamento e qualidade final do produto.',
                    'Validar base RTK, radio/link, visibilidade GNSS e repetir trechos com altos desvios padrao.'
                )
            )

        # 4) Yaw direction inconsistency near opposite direction.
        yaw_err_values = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.YAW_ALIGNMENT_ERROR.value, 'yaw_alignment_error'])
        yaw_opposite = [v for v in yaw_err_values if v >= 150.0]
        yaw_opposite_pct = (len(yaw_opposite) / len(yaw_err_values) * 100.0) if yaw_err_values else 0.0
        if yaw_err_values and yaw_opposite_pct > 5.0:
            critical_alerts.append(
                AggregateAnalyzer._severity_entry(
                    'ALERTA',
                    'Inconsistencia de direcao de voo (yaw)',
                    f'{yaw_opposite_pct:.2f}% das imagens com YawAlignmentError >= 150°.',
                    'Direcoes conflitantes podem reduzir matching e gerar faixas desalinhadas.',
                    'Revisar planejamento de heading e evitar trechos em sentido oposto sem controle de bloco.'
                )
            )

        # Advanced metrics block.
        rtk_diff_age = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.RTK_DIFF_AGE.value, 'rtk_diff_age'])
        rtk_stab_score = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.RTK_STABILITY_SCORE.value, 'rtk_stability_score'])
        gimbal_offset = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.GIMBAL_OFFSET.value, 'gimbal_offset'])
        size_mb = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.SIZE_MB.value, 'size_mb'])
        motion_blur = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.MOTION_BLUR_RISK.value, 'motion_blur_risk'])
        speed_ms = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.THREE_D_SPEED.value, 'speed_3d_ms'])
        speed_var = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.SPEED_VARIATION_INDEX.value, 'speed_variation_index'])
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
        pqi_series = AggregateAnalyzer._series_by_time(results, [MFK.PHOTOGRAMMETRY_QUALITY_INDEX.value, 'photogrammetry_quality_index'])
        pqi_first = statistics.mean([v for _, v in pqi_series[:max(1, len(pqi_series)//4)]]) if pqi_series else None
        pqi_last = statistics.mean([v for _, v in pqi_series[-max(1, len(pqi_series)//4):]]) if pqi_series else None
        pqi_delta = (pqi_last - pqi_first) if pqi_first is not None and pqi_last is not None else None

        # Morning vs midday using local capture hour.
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

        # Agronomic context: area estimate from per-flight calculation (soma das areas de cada voo)
        area_ha = None
        if agg.get('per_flight'):
            flight_areas = [f.get('estimated_area_ha') for f in agg['per_flight'] if f.get('estimated_area_ha') is not None]
            if flight_areas:
                area_ha = sum(flight_areas)

        # RTK Effective Precision para metricas avancadas
        rtk_effective_precision = AggregateAnalyzer._numeric_values_from_keys(results, [MFK.RTK_EFFECTIVE_PRECISION.value, 'rtk_effective_precision'])

        advanced_metrics = {
            'rtk_diff_age_mean': round(statistics.mean(rtk_diff_age), 4) if rtk_diff_age else None,
            'rtk_diff_age_max': round(max(rtk_diff_age), 4) if rtk_diff_age else None,
            'rtk_diff_age_p95': round(sorted(rtk_diff_age)[int(0.95*(len(rtk_diff_age)-1))], 4) if rtk_diff_age else None,
            'rtk_stability_mean': round(mean_rtk_stab, 4) if mean_rtk_stab is not None else None,
            'rtk_stability_class': rtk_class,
            'rtk_effective_precision_mean': round(statistics.mean(rtk_effective_precision), 4) if rtk_effective_precision else None,
            'rtk_effective_precision_max': round(max(rtk_effective_precision), 4) if rtk_effective_precision else None,
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
            'critical_alerts': critical_alerts,
            'metrics': advanced_metrics,
            'quality_analysis': {
                'strip_rows': strip_rows,
                'problematic_strips': problematic_strips,
            },
            'recommendations': recommendations,
        }

        # ===================================================================
        # ALERTAS CENTRALIZADOS - AlertManager
        # Processa todos os alertas unificados e adiciona ao agg para auditoria
        # ===================================================================
        try:
            unified_alerts = AlertManager.analyze(results, agg)
            if unified_alerts:
                # Converter para dict list para serializacao
                alerts_dict_list = AlertManager.to_dict_list(unified_alerts)
                agg['alerts'] = alerts_dict_list
                agg['alerts_count'] = len(unified_alerts)
                agg['alerts_summary'] = AlertManager.summary_by_category(unified_alerts)

                # Contagem por severidade
                severity_counts = defaultdict(int)
                for a in unified_alerts:
                    severity_counts[a.severity] += 1
                agg['alerts_severity'] = dict(severity_counts)

                # Log do total de alertas gerados
                AggregateAnalyzer.logger.info(
                    f"AlertManager gerou {len(unified_alerts)} alertas unificados",
                    code="ALERT_MANAGER_ANALYSIS",
                    data={
                        "total_alerts": len(unified_alerts),
                        "severity": dict(severity_counts),
                        "categories": list(set(a.category for a in unified_alerts)),
                    }
                )

                # Manter compatibilidade com template legado via critical_alerts
                # Adicionar alertas que ainda nao estao no critical_alerts original
                existing_titles = {a.get('title') for a in critical_alerts}
                for alert in unified_alerts:
                    legacy_entry = AlertManager.to_severity_entry(alert)
                    if legacy_entry['title'] not in existing_titles:
                        critical_alerts.append(legacy_entry)
                        existing_titles.add(legacy_entry['title'])

                agg['advanced_analysis']['critical_alerts'] = critical_alerts
        except Exception as e:
            AggregateAnalyzer.logger.error(
                f"Erro ao executar AlertManager.analyze: {e}",
                code="ALERT_MANAGER_ERROR",
            )
            agg['alerts'] = []
            agg['alerts_count'] = 0

        return agg
