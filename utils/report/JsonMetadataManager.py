import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import statistics
from datetime import datetime

from ...core.config.LogUtils import LogUtils
from ..ToolKeys import ToolKey
from ..adapter.StringAdapter import StringAdapter
from ..mrk.MetadataFields import MetadataFields
from ..FormatUtils import FormatUtils
from ..MathUtils import MathUtils
from .RangeMetadataManager import range_metadata_manager as config


class JsonMetadataManager:
    """Estatistico puro: processa N fichas (IMGMetadata) e devolve distribuicoes sobre atributos.
    
    Nao sabe nada sobre voos, equipamentos, graficos, alertas ou relatorios.
    So sabe calcular: media, desvio, minimo, maximo, distribuicao por nivel, series temporais.
    """

    @staticmethod
    def _get_logger(tool_key: str = ToolKey.UNTRACEABLE) -> LogUtils:
        return LogUtils(tool=tool_key, class_name="JsonMetadataManager")

    # ===================================================================
    # CARGA DE DADOS (APENAS v2.0, SEM LEGADO)
    # ===================================================================
    @staticmethod
    def load_json_file(json_path: str, tool_key: str = ToolKey.UNTRACEABLE) -> Any:
        """Le um arquivo JSON do disco e retorna o objeto desserializado."""
        logger = JsonMetadataManager._get_logger(tool_key)
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"JSON nao encontrado: {json_path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"JSON carregado: {json_path}")
        return data

    @staticmethod
    def load_timestamps(
        json_path: str,
        tool_key: str = ToolKey.UNTRACEABLE,
    ) -> Dict[str, str]:
        """Carrega apenas o bloco de timestamps do JSON v2.0.
        Retorna dict vazio se nao houver timestamps ou se o JSON nao for v2.0.
        """
        logger = JsonMetadataManager._get_logger(tool_key)
        try:
            path = Path(json_path)
            if not path.exists():
                logger.warning(f"JSON nao encontrado para extrair timestamps: {json_path}")
                return {}

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            version = data.get("schema_version")
            if version != "2.0":
                logger.debug(f"JSON com schema_version='{version}' nao possui timestamps v2.0")
                return {}

            timestamps = data.get("timestamps", {})
            if not isinstance(timestamps, dict) or not timestamps:
                logger.debug("Nenhum timestamp encontrado no JSON")
                return {}

            logger.info(f"Timestamps carregados: {len(timestamps)} entradas")
            return dict(timestamps)

        except Exception as e:
            logger.warning(f"Erro ao carregar timestamps: {e}")
            return {}

    @staticmethod
    def load_json_metadata(json_path: str, tool_key: str = ToolKey.UNTRACEABLE) -> Dict[str, Any]:
        """Carrega metadados do JSON raiz: titulo, logotipo, generated_at.
        Args:
            json_path: Caminho do arquivo JSON
        Returns:
            Dict com 'titulo', 'logotipo', 'generated_at' (se existirem no JSON)
        """
        logger = JsonMetadataManager._get_logger(tool_key)
        meta: Dict[str, Any] = {}
        try:
            data = JsonMetadataManager.load_json_file(json_path, tool_key=tool_key)
            if isinstance(data, dict):
                if data.get("titulo"):
                    meta["titulo"] = data["titulo"]
                if data.get("logotipo"):
                    meta["logotipo"] = data["logotipo"]
                if data.get("generated_at"):
                    raw = str(data["generated_at"])
                    meta["generated_at_raw"] = raw
                    try:
                        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                        meta["generated_at"] = dt.strftime("%d/%m/%Y %H:%M:%S")
                    except (ValueError, TypeError):
                        meta["generated_at"] = raw
            logger.debug(f"Metadados carregados: {meta}")
        except Exception as e:
            logger.warning(f"Erro ao carregar metadados do JSON: {e}")
        return meta

    @staticmethod
    def compute_processing_summary(timestamps: Dict[str, str]) -> Dict[str, Any]:
        """Calcula tempos de processamento a partir do dicionario de timestamps.
        Args:
            timestamps: Dict com chaves como pipeline_start, mrk_start, mrk_end, etc.
        Returns:
            Dict com total_seconds, total_formatted, stages, all_present, missing_stages
        """
        def _parse_ts(ts_str: str) -> Optional[datetime]:
            if not ts_str:
                return None
            try:
                return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return None

        stage_defs = [
            ("initial_start", "initial_end", "Varredura"),
            ("mrk_start", "mrk_end", "MRK"),
            ("exif_start", "exif_end", "EXIF"),
            ("xmp_start", "xmp_end", "XMP"),
            ("custom_start", "custom_end", "Custom"),
            ("vectorization_start", "vectorization_end", "Vetorizacao"),
            ("report_start", "report_end", "Relatorio"),
        ]

        parsed = {k: _parse_ts(v) for k, v in timestamps.items()}
        stages = []
        missing_stages = []
        total_stage_seconds = 0.0

        for start_key, end_key, label in stage_defs:
            start_dt = parsed.get(start_key)
            end_dt = parsed.get(end_key)
            if start_dt is None or end_dt is None:
                missing_stages.append(label)
                stages.append({
                    "label": label,
                    "start": timestamps.get(start_key, ""),
                    "end": timestamps.get(end_key, ""),
                    "duration_seconds": None,
                    "duration_formatted": "N/A",
                    "present": False,
                })
                continue
            duration = (end_dt - start_dt).total_seconds()
            total_stage_seconds += duration
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = duration % 60
            if hours > 0:
                dur_fmt = f"{hours}h {minutes:02d}m {seconds:05.2f}s"
            elif minutes > 0:
                dur_fmt = f"{minutes}m {seconds:05.2f}s"
            else:
                dur_fmt = f"{seconds:.2f}s"
            stages.append({
                "label": label,
                "start": timestamps.get(start_key, ""),
                "end": timestamps.get(end_key, ""),
                "duration_seconds": round(duration, 3),
                "duration_formatted": dur_fmt,
                "present": True,
            })

        pipeline_start = parsed.get("pipeline_start")
        report_end = parsed.get("report_end")
        if pipeline_start and report_end:
            total_seconds = (report_end - pipeline_start).total_seconds()
        else:
            total_seconds = total_stage_seconds if total_stage_seconds > 0 else None

        if total_seconds is not None:
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            secs = total_seconds % 60
            if hours > 0:
                total_formatted = f"{hours}h {minutes:02d}m {secs:05.2f}s"
            elif minutes > 0:
                total_formatted = f"{minutes}m {secs:05.2f}s"
            else:
                total_formatted = f"{secs:.2f}s"
        else:
            total_formatted = "N/A"

        formatted_individual = {}
        for key, dt in parsed.items():
            if dt is not None:
                formatted_individual[key] = dt.strftime("%H:%M:%S.%f")[:-3]
            else:
                formatted_individual[key] = timestamps.get(key, "N/A")

        return {
            "total_seconds": round(total_seconds, 3) if total_seconds is not None else None,
            "total_formatted": total_formatted,
            "stages": stages,
            "missing_stages": missing_stages,
            "all_present": len(missing_stages) == 0,
            "pipeline_start": timestamps.get("pipeline_start", ""),
            "pipeline_end": timestamps.get("report_end", ""),
            "formatted_individual": formatted_individual,
        }

    @staticmethod
    def load_records(
        json_path: str = "metadata_completa_custom.json",
        tool_key: str = ToolKey.UNTRACEABLE,
    ) -> List[Dict[str, Any]]:
        """Carrega registros de metadata exclusivamente via JSON v2.0.
        
        Usa JsonUtil.load_records() que valida schema_version='2.0'.
        Nao suporta mais formatos legados.
        """
        from ..JsonUtil import JsonUtil
        logger = JsonMetadataManager._get_logger(tool_key)

        records = JsonUtil.load_records(json_path)
        logger.info(f"load_records: carregadas {len(records)} imagens de JSON v2.0")
        return records

    # ===================================================================
    # METODOS ESTATISTICOS PUROS
    # ===================================================================
    @staticmethod
    def _is_zero_or_none(val) -> bool:
        """Check if a value is None, zero, or empty."""
        if val is None:
            return True
        if isinstance(val, (int, float)):
            return val == 0.0
        if isinstance(val, str):
            return val.strip() in ('', 'N/A')
        return False

    @staticmethod
    def _resolve_field_meta(indicator: str):
        """Resolve metadado de um indicador com fallback de aliases conhecidos."""
        # Fallbacks usados internamente pelo estatistico
        field_fallbacks = {
            'gsd_cm': ['GroundSampleDistanceCm'],
            'speed_3d_ms': ['3DSpeed', 'Speed3dKmh'],
            'sensor_temp_c': ['SensorTemperature', 'LensTemperature'],
        }
        for alias in [indicator, *field_fallbacks.get(indicator, [])]:
            for candidate in MetadataFields.resolve_candidates(alias):
                field = MetadataFields.get_field(candidate)
                if field is not None:
                    return field
        return None

    @staticmethod
    def _numeric_values_from_keys(results: List[Any], keys: List[str]) -> List[float]:
        """Extrai serie numerica de um conjunto de chaves candidatas.
        
        Args:
            results: Lista de objetos IMGMetadata
            keys: Lista de chaves candidatas a buscar
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
            num = MathUtils.to_float_or_none(raw)
            if num is not None and num not in (float('inf'), float('-inf')):
                return num
        return None

    @staticmethod
    def _series_by_time(results: List[Any], keys: List[str]) -> List[Tuple[datetime, float]]:
        """Monta serie temporal ordenada de valores numericos por data de captura.
        
        Args:
            results: Lista de objetos IMGMetadata
            keys: Lista de chaves candidatas
        Returns:
            Lista de tuplas (datetime, float) ordenadas por data
        """
        series = []
        for r in results:
            dt = None
            if hasattr(r, 'capture_datetime'):
                dt = FormatUtils.parse_capture_datetime(r.capture_datetime)
            if dt is None:
                continue
            value = JsonMetadataManager._first_numeric_from_result(r, keys)
            if value is None:
                continue
            series.append((dt, value))
        return sorted(series, key=lambda x: x[0])

    @staticmethod
    def _level_ranges_from_threshold(indicator: str) -> Dict[str, str]:
        """Traduz thresholds configurados para descricoes textuais por nivel (N1..N5).
        
        Args:
            indicator: Nome do indicador
        Returns:
            Dict com chaves '1'..'5' e descricoes textuais
        """
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
                    lo = FormatUtils.fmt_num(MathUtils.parse_num(interval[0]))
                    hi = FormatUtils.fmt_num(MathUtils.parse_num(interval[1]))
                    out[str(i)] = f'{lo}..{hi}'
                elif isinstance(interval, list) and len(interval) == 1:
                    lo = FormatUtils.fmt_num(MathUtils.parse_num(interval[0]))
                    out[str(i)] = f'>={lo}'
                else:
                    out[str(i)] = '-'
            for i in range(1, 6):
                out.setdefault(str(i), '-')
            return out

        cuts: List[float] = []
        for raw in levels:
            try:
                cuts.append(MathUtils.parse_num(raw))
            except Exception:
                continue

        if len(cuts) < 2:
            return {str(i): '-' for i in range(1, 6)}

        if ttype == 'higher_better':
            if len(cuts) >= 5:
                c2, c3, c4, c5 = cuts[1], cuts[2], cuts[3], cuts[4]
                return {
                    '1': f'<{FormatUtils.fmt_num(c2)}',
                    '2': f'>={FormatUtils.fmt_num(c2)} e <{FormatUtils.fmt_num(c3)}',
                    '3': f'>={FormatUtils.fmt_num(c3)} e <{FormatUtils.fmt_num(c4)}',
                    '4': f'>={FormatUtils.fmt_num(c4)} e <{FormatUtils.fmt_num(c5)}',
                    '5': f'>={FormatUtils.fmt_num(c5)}',
                }
            if len(cuts) == 4:
                c2, c3, c4 = cuts[1], cuts[2], cuts[3]
                return {
                    '1': f'<{FormatUtils.fmt_num(c2)}',
                    '2': f'>={FormatUtils.fmt_num(c2)} e <{FormatUtils.fmt_num(c3)}',
                    '3': f'>={FormatUtils.fmt_num(c3)} e <{FormatUtils.fmt_num(c4)}',
                    '4': f'>={FormatUtils.fmt_num(c4)}',
                    '5': '-',
                }
            if len(cuts) == 3:
                c2, c3 = cuts[1], cuts[2]
                return {
                    '1': f'<{FormatUtils.fmt_num(c2)}',
                    '2': f'>={FormatUtils.fmt_num(c2)} e <{FormatUtils.fmt_num(c3)}',
                    '3': f'>={FormatUtils.fmt_num(c3)}',
                    '4': '-',
                    '5': '-',
                }
            if len(cuts) >= 2:
                c2 = cuts[1]
                return {'1': f'<{FormatUtils.fmt_num(c2)}', '2': f'>={FormatUtils.fmt_num(c2)}', '3': '-', '4': '-', '5': '-'}
            return {str(i): '-' for i in range(1, 6)}

        if ttype == 'lower_better':
            if len(cuts) >= 4:
                c1, c2, c3, c4 = cuts[0], cuts[1], cuts[2], cuts[3]
                return {
                    '1': f'>{FormatUtils.fmt_num(c1)}',
                    '2': f'<={FormatUtils.fmt_num(c1)} e >{FormatUtils.fmt_num(c2)}',
                    '3': f'<={FormatUtils.fmt_num(c2)} e >{FormatUtils.fmt_num(c3)}',
                    '4': f'<={FormatUtils.fmt_num(c3)} e >{FormatUtils.fmt_num(c4)}',
                    '5': f'<={FormatUtils.fmt_num(c4)}',
                }
            if len(cuts) == 3:
                c1, c2, c3 = cuts[0], cuts[1], cuts[2]
                return {
                    '1': f'>{FormatUtils.fmt_num(c1)}',
                    '2': f'<={FormatUtils.fmt_num(c1)} e >{FormatUtils.fmt_num(c2)}',
                    '3': f'<={FormatUtils.fmt_num(c2)} e >{FormatUtils.fmt_num(c3)}',
                    '4': f'<={FormatUtils.fmt_num(c3)}',
                    '5': '-',
                }
            if len(cuts) >= 2:
                c1, c2 = cuts[0], cuts[1]
                return {'1': f'>{FormatUtils.fmt_num(c1)}', '2': f'<={FormatUtils.fmt_num(c1)} e >{FormatUtils.fmt_num(c2)}', '3': f'<={FormatUtils.fmt_num(c2)}', '4': '-', '5': '-'}
            return {str(i): '-' for i in range(1, 6)}

        return {str(i): '-' for i in range(1, 6)}

    # ===================================================================
    # METODO PRINCIPAL DO ESTATISTICO
    # ===================================================================
    @staticmethod
    def compute_indicator_statistics(results: List[Any]) -> Dict[str, Any]:
        """Calcula estatisticas PURAS sobre os indicadores das imagens.
        
        Este e o metodo principal do Estatistico. Ele recebe N fichas (IMGMetadata)
        e devolve APENAS distribuicoes sobre atributos. Nao sabe nada sobre voos,
        equipamentos, graficos ou alertas.
        
        Args:
            results: Lista de objetos IMGMetadata ja processados (score() chamado)
            
        Returns:
            Dict com:
                - total_images: int
                - per_indicator: Dict com estatisticas por indicador
                - level_distribution: Dict com contagem por nivel (1..5)
                - pqi_mean: float | None
                - pqi_level_distribution: Dict com contagem PQI por nivel
                - pqi_classification: Dict com level, label, score_display | None
                - indicator_catalog: List de key-label-description
        """
        if not results:
            return {
                'total_images': 0,
                'per_indicator': {},
                'level_distribution': {},
                'pqi_mean': None,
                'pqi_level_distribution': {},
                'pqi_classification': None,
                'indicator_catalog': [],
            }

        if config._config is None:
            config.load()

        # Coletar todos os indicadores presentes nos resultados
        all_inds = set()
        for r in results:
            if hasattr(r, 'levels'):
                all_inds.update(r.levels.keys())

        stats = {}
        level_dist = defaultdict(int)

        for ind in all_inds:
            levels = [r.levels.get(ind, 3) for r in results]
            field_meta = JsonMetadataManager._resolve_field_meta(ind)
            thresh = config.get_thresholds(ind) if config._config else {}

            # Valores numericos brutos do indicador
            numeric_values = []
            for r in results:
                if hasattr(r, 'values') and ind in r.values:
                    num = MathUtils.to_float_or_none(r.values.get(ind))
                    if num is not None and num not in (float('inf'), float('-inf')):
                        numeric_values.append(num)

            if numeric_values:
                value_mean = statistics.mean(numeric_values)
                value_std = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0.0
                sorted_vals = sorted(numeric_values)
                n = len(sorted_vals)
                value_p5 = sorted_vals[int(0.05 * (n - 1))]
                value_p95 = sorted_vals[int(0.95 * (n - 1))]
                value_min = min(numeric_values)
                value_max = max(numeric_values)
                value_range = value_max - value_min
                value_percentile_range = value_p95 - value_p5
            else:
                value_mean = value_std = value_p5 = value_p95 = value_min = value_max = value_range = value_percentile_range = None

            stats[ind] = {
                'label': field_meta.label if field_meta else ind,
                'description': field_meta.description if field_meta else '',
                'threshold_type': (thresh or {}).get('type', 'unknown'),
                'level_ranges': JsonMetadataManager._level_ranges_from_threshold(ind),
                'mean': round(statistics.mean(levels), 2),
                'std': round(statistics.stdev(levels) if len(levels) > 1 else 0, 2),
                'value_mean': round(value_mean, 4) if value_mean is not None else None,
                'value_std': round(value_std, 4) if value_std is not None else None,
                'value_p5': round(value_p5, 4) if value_p5 is not None else None,
                'value_p95': round(value_p95, 4) if value_p95 is not None else None,
                'value_min': round(value_min, 4) if value_min is not None else None,
                'value_max': round(value_max, 4) if value_max is not None else None,
                'value_range': round(value_range, 4) if value_range is not None else None,
                'value_percentile_range': round(value_percentile_range, 4) if value_percentile_range is not None else None,
                'dist': {1: levels.count(1), 2: levels.count(2), 3: levels.count(3), 4: levels.count(4), 5: levels.count(5)}
            }
            for lvl in levels:
                level_dist[lvl] += 1

        # Ordenar deterministicamente
        stats = dict(
            sorted(
                stats.items(),
                key=lambda item: (str(item[1].get('label') or item[0])).lower()
            )
        )

        # ===================================================================
        # PQI - Photogrammetry Quality Index
        # ===================================================================
        pqi_values = JsonMetadataManager._numeric_values_from_keys(
            results,
            ['PhotogrammetryQualityIndex', 'photogrammetry_quality_index']
        )
        pqi_mean = statistics.mean(pqi_values) if pqi_values else None

        pqi_levels = []
        pqi_thresh = config.get_thresholds('photogrammetry_quality_index') if config._config else None
        if pqi_thresh and pqi_values:
            for v in pqi_values:
                try:
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

        # Classificacao PQI
        pqi_classification = None
        if pqi_mean is not None:
            pqi_cuts = [float(c) for c in (pqi_thresh.get('levels', []) if pqi_thresh else [])]
            count = sum(1 for cut in pqi_cuts if pqi_mean >= cut)
            pqi_classify_level = max(1, min(5, count + 1))
            pqi_messages = pqi_thresh.get('messages', []) if pqi_thresh else []
            pqi_label = pqi_messages[pqi_classify_level - 1] if pqi_classify_level - 1 < len(pqi_messages) else f'Nivel {pqi_classify_level}'
            pqi_classification = {
                'level': pqi_classify_level,
                'label': pqi_label,
                'score_display': f'{pqi_mean:.0f}/100'
            }

        # Catalogo de indicadores
        indicator_meta_source = {
            key: JsonMetadataManager._resolve_field_meta(key)
            for key in stats.keys()
            if JsonMetadataManager._resolve_field_meta(key) is not None
        }
        indicator_catalog = StringAdapter.to_key_label_description(indicator_meta_source)

        return {
            'total_images': len(results),
            'per_indicator': stats,
            'level_distribution': dict(level_dist),
            'pqi_mean': round(pqi_mean, 2) if pqi_mean is not None else None,
            'pqi_level_distribution': dict(pqi_level_dist),
            'pqi_classification': pqi_classification,
            'indicator_catalog': indicator_catalog,
        }