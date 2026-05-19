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
    """Manipulador de informacoes gerais do conjunto de dados.
    
    Responsavel por extrair do conjunto de imagens todas as informacoes
    que nao sao de responsabilidade do estatistico (JsonMetadataManager),
    do agregador de voos (FlightAggregator) ou do analista de qualidade (AlertManager).
    
    Obtem do JsonMetadataManager os dados brutos do conjunto e responde:
    - Quais equipamentos foram usados?
    - Qual firmware estava rodando?
    - Qual datum GPS foi utilizado?
    - Qual o intervalo de datas de captura?
    - Qual camera tem o maior disparo (shutter count)?
    - Qual a area total estimada?
    - Como estao distribuidos os modelos por prefixo do filename?
    """

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

    # ===================================================================
    # INFORMACOES GERAIS
    # ===================================================================
    @staticmethod
    def compute_general_info(results: List[IMGMetadata]) -> Dict[str, Any]:
        """Extrai informacoes gerais do conjunto de imagens.
        
        Args:
            results: Lista de objetos IMGMetadata processados
            
        Returns:
            Dict com equipment_models, firmware_versions, gps_datum, gps_status,
            capture_start, capture_end, etc.
        """
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
    # TOP MODELS (agrupamento por prefixo do filename)
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