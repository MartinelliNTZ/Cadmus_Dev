from typing import List, Dict, Any, Optional, Callable
from collections import defaultdict
from dataclasses import dataclass, field, asdict
import statistics
import math

from ..mrk.MetadataFields import MetadataFields
from .RangeMetadataManager import range_metadata_manager as config
from ...core.enum import MetadataFieldKey as MFK


@dataclass
class AlertRecord:
    """Estrutura unificada de alerta para auditoria."""
    severity: str                # 'CRITICO', 'ALERTA', 'INFO'
    category: str                # Categoria definida no config.yaml
    title: str                   # Titulo curto do alerta
    detail: str                  # Descricao detalhada com metricas
    impact: str                  # Impacto na qualidade do produto final
    action: str                  # Acao recomendada
    affected_count: int = 0      # Numero de imagens/voos afetados
    total_count: int = 0         # Total de imagens/voos analisados
    affected_pct: float = 0.0    # Percentual de itens afetados
    threshold_value: Optional[float] = None  # Valor do limiar que disparou o alerta
    actual_value: Optional[float] = None     # Valor medido atual
    flight_ids: List[str] = field(default_factory=list)  # Voos afetados
    photos: List[str] = field(default_factory=list)      # Fotos criticas (limitado)


class AlertManager:
    """Motor generico de alertas. Le as definicoes do config.yaml (secao alerts:)."""

    SEVERITY_CRITICAL = 'CRITICO'
    SEVERITY_ALERT = 'ALERTA'
    SEVERITY_INFO = 'INFO'

    SEVERITY_ORDER = {SEVERITY_CRITICAL: 0, SEVERITY_ALERT: 1, SEVERITY_INFO: 2}

    # Constantes internas (nao expostas como config)
    _OVERLAP_IDEAL = 60.0
    _SPEED_RECOMMENDED_MIN_MS = 5.0
    _SPEED_RECOMMENDED_MAX_MS = 10.0

    # ===================================================================
    # Metodos utilitarios (mantidos para compatibilidade)
    # ===================================================================

    @staticmethod
    def _parse_num(value: Any) -> Optional[float]:
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
    def _fmt_pct(value: float) -> str:
        """Formata percentual com 2 casas decimais."""
        return f'{value:.2f}%'

    @staticmethod
    def _fmt_num(value: float, decimals: int = 2) -> str:
        """Formata numero com casas decimais."""
        return f'{value:.{decimals}f}'

    @staticmethod
    def _to_int_or_none(value: Any) -> Optional[int]:
        """Converte para int ou None."""
        f = AlertManager._parse_num(value)
        if f is None:
            return None
        return int(f)

    @staticmethod
    def _get_field_from_result(r: Any, field_path: str) -> Any:
        """Extrai um campo de um resultado, suportando aninhamento com '.'.

        Exemplo: 'level5_values.MotionBlurRisk' ou 'values.gsd_cm' ou 'flight_id'
        """
        parts = field_path.split('.')
        obj = r
        for part in parts:
            if obj is None:
                return None
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict):
                obj = obj.get(part)
            elif isinstance(obj, list) and isinstance(part, int):
                obj = obj[part] if part < len(obj) else None
            else:
                return None
        return obj

    @staticmethod
    def _get_value_from_result(r: Any, cfg: Dict[str, Any]) -> Optional[float]:
        """Extrai valor numerico de um resultado conforme config do alerta."""
        # Tenta field_path direto
        field_path = cfg.get('field_path')
        if field_path:
            raw = AlertManager._get_field_from_result(r, field_path)
            num = AlertManager._parse_num(raw)
            if num is not None:
                return num

        # Tenta level5_values por MFK
        indicator = cfg.get('indicator_ref')
        if indicator:
            # Mapeia indicator_ref para MFK
            mfk_key = AlertManager._indicator_to_mfk(indicator)
            if mfk_key:
                raw = AlertManager._get_field_from_result(r, f'level5_values.{mfk_key}')
                num = AlertManager._parse_num(raw)
                if num is not None:
                    return num

            # Tenta values por nome direto
            raw = AlertManager._get_field_from_result(r, f'values.{indicator}')
            num = AlertManager._parse_num(raw)
            if num is not None:
                return num

            # Tenta get_indicator
            if hasattr(r, 'get_indicator'):
                raw = r.get_indicator(indicator)
                num = AlertManager._parse_num(raw)
                if num is not None:
                    return num

        return None

    @staticmethod
    def _indicator_to_mfk(indicator: str) -> Optional[str]:
        """Converte nome de indicador para chave MetadataFieldKey."""
        mfk_map = {
            'motion_blur_risk': MFK.MOTION_BLUR_RISK.value,
            'gsd_cm': MFK.GROUND_SAMPLE_DISTANCE_CM.value,
            'photogrammetry_quality_index': MFK.PHOTOGRAMMETRY_QUALITY_INDEX.value,
            'predicted_overlap': MFK.PREDICTED_OVERLAP.value,
            'f_overlap': MFK.F_OVERLAP.value,
            'yaw_alignment_error': MFK.YAW_ALIGNMENT_ERROR.value,
            'gimbal_angular_velocity': MFK.GIMBAL_ANGULAR_VELOCITY.value,
            'gimbal_offset': MFK.GIMBAL_OFFSET.value,
            'rtk_std_lat': MFK.RTK_STD_LAT.value,
            'rtk_std_lon': MFK.RTK_STD_LON.value,
            'rtk_std_hgt': MFK.RTK_STD_HGT.value,
            'rtk_effective_precision': MFK.RTK_EFFECTIVE_PRECISION.value,
            'rtk_flag': MFK.RTK_FLAG.value,
            'rtk_diff_age': MFK.RTK_DIFF_AGE.value,
            'rtk_stability_score': MFK.RTK_STABILITY_SCORE.value,
            'sensor_temp_c': MFK.SENSOR_TEMPERATURE.value,
            'sensor_temperature': MFK.SENSOR_TEMPERATURE.value,
            'xy_difference': MFK.XY_DIFFERENCE.value,
            'z_difference': MFK.Z_DIFFERENCE.value,
            'strip_id': MFK.STRIP_ID.value,
            'ground_sample_distance_cm': MFK.GROUND_SAMPLE_DISTANCE_CM.value,
            'three_d_speed': MFK.THREE_D_SPEED.value,
            'speed_variation_index': MFK.SPEED_VARIATION_INDEX.value,
            'light_consistency': MFK.LIGHT_CONSISTENCY.value,
            'size_mb': MFK.SIZE_MB.value,
        }
        return mfk_map.get(indicator)

    @staticmethod
    def _make_record(
        severity: str,
        category: str,
        title: str,
        detail: str,
        impact: str,
        action: str,
        affected_count: int = 0,
        total_count: int = 0,
        threshold_value: Optional[float] = None,
        actual_value: Optional[float] = None,
        flight_ids: Optional[List[str]] = None,
        photos: Optional[List[str]] = None,
    ) -> AlertRecord:
        """Cria um AlertRecord com calculo automatico de percentual."""
        pct = (affected_count / total_count * 100.0) if total_count > 0 else 0.0
        return AlertRecord(
            severity=severity,
            category=category,
            title=title,
            detail=detail,
            impact=impact,
            action=action,
            affected_count=affected_count,
            total_count=total_count,
            affected_pct=round(pct, 2),
            threshold_value=threshold_value,
            actual_value=actual_value,
            flight_ids=flight_ids or [],
            photos=photos or [],
        )

    # ===================================================================
    # MOTOR GENERICO DE ANALISE
    # ===================================================================

    @staticmethod
    def analyze(results: List[Any], agg: Dict[str, Any]) -> List[AlertRecord]:
        """Executa todas as analises usando definicoes do config.yaml.

        Args:
            results: Lista de objetos IMGMetadata
            agg: Dict com agregados (general_info, per_flight, etc.)

        Returns:
            Lista de AlertRecords ordenados por severidade
        """
        alerts: List[AlertRecord] = []
        total_images = len(results)

        if total_images == 0:
            return alerts

        # Garantir que config esteja carregado
        if config._config is None:
            config.load()

        # Obter definicoes de alertas do config.yaml
        alert_defs = config.get_alerts()
        per_flight = agg.get('per_flight', [])

        for alert_name, alert_cfg in alert_defs.items():
            try:
                alert = AlertManager._evaluate_one_alert(
                    alert_name, alert_cfg, results, agg, per_flight, total_images
                )
                if alert:
                    if isinstance(alert, list):
                        alerts.extend(alert)
                    else:
                        alerts.append(alert)
            except Exception as e:
                # Log silencioso - nao quebra o relatorio
                pass

        # Ordenar: CRITICO primeiro, depois ALERTA, depois INFO
        alerts.sort(key=lambda a: (
            AlertManager.SEVERITY_ORDER.get(a.severity, 99),
            a.category,
            -a.affected_pct
        ))

        return alerts

    @staticmethod
    def _evaluate_one_alert(
        name: str,
        cfg: Dict[str, Any],
        results: List[Any],
        agg: Dict[str, Any],
        per_flight: List[Dict[str, Any]],
        total_images: int,
    ) -> Optional[AlertRecord]:
        """Avalia UMA definicao de alerta e retorna AlertRecord ou None."""
        mode = cfg.get('mode')

        if mode == 'aggregate_field':
            return AlertManager._eval_aggregate_field(name, cfg, results, agg, total_images)
        elif mode == 'threshold_levels':
            return AlertManager._eval_threshold_levels(name, cfg, results, total_images)
        elif mode == 'threshold_levels_multi':
            return AlertManager._eval_threshold_levels_multi(name, cfg, results, total_images)
        elif mode == 'rtk_flag':
            return AlertManager._eval_rtk_flag(name, cfg, results, total_images)
        elif mode == 'aggregate_std':
            return AlertManager._eval_aggregate_std(name, cfg, results, per_flight)
        else:
            return None

    @staticmethod
    def _eval_aggregate_field(
        name: str, cfg: Dict[str, Any], results: List[Any],
        agg: Dict[str, Any], total_images: int
    ) -> Optional[AlertRecord]:
        """Avalia alerta modo aggregate_field: le campo do agg e compara condicao."""
        field_path = cfg.get('aggregate_field', '')
        if not field_path:
            return None

        # Navegar pelo agg para obter o valor (ex: general_info.dewarp_zero_count)
        parts = field_path.split('.')
        current = agg
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, 0)
            else:
                return None

        field_value = current
        if not isinstance(field_value, (int, float)):
            field_value = AlertManager._parse_num(field_value)
            if field_value is None:
                field_value = 0

        cond = cfg.get('condition', {})
        cond_type = cond.get('type', 'gt')
        cond_value = cond.get('value', 0)

        # Avaliar condicao
        match = False
        if cond_type == 'gt':
            match = field_value > cond_value
        elif cond_type == 'gte':
            match = field_value >= cond_value
        elif cond_type == 'eq':
            match = field_value == cond_value
        elif cond_type == 'lt':
            match = field_value < cond_value

        if not match:
            return None

        # Determinar severidade
        severity = cfg.get('severity')
        if not severity:
            # Tentar severity_rules com pct_gt
            rules = cfg.get('severity_rules', [])
            pct = (field_value / total_images * 100.0) if total_images > 0 else 0.0
            for rule in rules:
                rule_when = rule.get('when', {})
                if rule_when.get('type') == 'pct_gt':
                    if pct > rule_when.get('value', 0):
                        severity = rule.get('severity')
                        break
            if not severity:
                return None

        af_count = int(field_value)

        # Lista de voos afetados (opcional)
        photos_field = cfg.get('photos_field')
        photos_condition = cfg.get('photos_condition')
        flight_ids = []
        if photos_field:
            for r in results:
                val = AlertManager._get_field_from_result(r, photos_field)
                if val is not None:
                    if photos_condition == '== 0.0' and val == 0.0:
                        flight_ids.append(getattr(r, 'flight_id', 'unknown') or 'unknown')
                    elif photos_condition == 'is None' and val is None:
                        flight_ids.append(getattr(r, 'flight_id', 'unknown') or 'unknown')

        flight_ids = sorted(set(flight_ids)) if flight_ids else []

        # Montar titulo
        title = cfg.get('title_template', f'Alerta: {name}').format(
            affected_count=af_count,
            total_count=total_images,
        )

        return AlertManager._make_record(
            severity=severity,
            category=cfg.get('category', 'GENERAL'),
            title=title,
            detail=f'{af_count}/{total_images} imagens afetadas.' if not flight_ids else
                   f'{af_count}/{total_images} imagens afetadas. Voo(s): {", ".join(flight_ids)}.',
            impact=cfg.get('impact', ''),
            action=cfg.get('action', ''),
            affected_count=af_count,
            total_count=total_images,
            flight_ids=flight_ids,
        )

    @staticmethod
    def _eval_threshold_levels(
        name: str, cfg: Dict[str, Any], results: List[Any], total_images: int
    ) -> Optional[AlertRecord]:
        """Avalia alerta modo threshold_levels: classifica cada resultado e conta por nivel."""
        indicator = cfg.get('indicator_ref')
        if not indicator:
            return None

        # Classificar cada resultado
        level_counts = defaultdict(int)
        level_photos = defaultdict(list)
        level_flights = defaultdict(list)
        total_classified = 0

        for r in results:
            val = AlertManager._get_value_from_result(r, cfg)
            if val is None:
                continue

            try:
                level, _ = config.classify(indicator, val)
            except Exception:
                continue

            level_counts[level] += 1
            total_classified += 1
            level_photos[level].append(getattr(r, 'filename', 'unknown'))
            level_flights[level].append(getattr(r, 'flight_id', 'unknown') or 'unknown')

        if total_classified == 0:
            return None

        max_photos = cfg.get('max_photos_list', 0)

        # Avaliar regras de severidade
        rules = cfg.get('severity_rules', [])
        for rule in rules:
            rule_when = rule.get('when', {})
            rule_type = rule_when.get('type')
            rule_level = rule_when.get('level')

            match = False
            affected_count = 0
            threshold_val = None
            actual_val = None
            photos_list = []
            flights_list = []

            if rule_type == 'any_at_level':
                # Qualquer foto naquele nivel ou pior
                count = sum(level_counts.get(lvl, 0) for lvl in range(1, rule_level + 1))
                if count > 0:
                    match = True
                    affected_count = count
                    # Coletar fotos e voos
                    for lvl in range(1, rule_level + 1):
                        photos_list.extend(level_photos.get(lvl, []))
                        flights_list.extend(level_flights.get(lvl, []))
                    # Threshold = level do config
                    levels_raw = config.resolve_indicator_levels(indicator)
                    if levels_raw and rule_level <= len(levels_raw):
                        threshold_val = AlertManager._parse_num(levels_raw[rule_level - 1])
                    actual_val = threshold_val  # valor aproximado do limiar

            elif rule_type == 'pct_at_level_or_worse':
                # % de fotos naquele nivel ou pior
                min_pct = rule_when.get('min_pct', 0)
                count = sum(level_counts.get(lvl, 0) for lvl in range(1, rule_level + 1))
                pct = (count / total_classified * 100.0) if total_classified > 0 else 0.0
                if pct > min_pct:
                    match = True
                    affected_count = count
                    for lvl in range(1, rule_level + 1):
                        photos_list.extend(level_photos.get(lvl, []))
                        flights_list.extend(level_flights.get(lvl, []))
                    levels_raw = config.resolve_indicator_levels(indicator)
                    if levels_raw and rule_level <= len(levels_raw):
                        threshold_val = AlertManager._parse_num(levels_raw[rule_level - 1])
                    actual_val = pct

            if not match:
                continue

            # Se chegou aqui, a regra match
            severity = rule.get('severity')

            # Limitar fotos
            if max_photos > 0:
                photos_list = photos_list[:max_photos]
            flights_list = sorted(set(flights_list)) if flights_list else []

            # Montar titulo
            title = cfg.get('title_template', f'Alerta: {name}').format(
                affected_count=affected_count,
                total_count=total_classified,
            )

            # Detail
            detail_parts = [
                f'{affected_count}/{total_classified} imagens com {indicator} no nivel {rule_level}.'
            ]
            if flights_list:
                detail_parts.append(f'Voo(s): {", ".join(flights_list)}.')

            return AlertManager._make_record(
                severity=severity,
                category=cfg.get('category', 'GENERAL'),
                title=title,
                detail=' '.join(detail_parts),
                impact=cfg.get('impact', ''),
                action=cfg.get('action', ''),
                affected_count=affected_count,
                total_count=total_classified,
                threshold_value=threshold_val,
                actual_value=actual_val,
                flight_ids=flights_list,
                photos=photos_list if max_photos > 0 else [],
            )

        return None

    @staticmethod
    def _eval_threshold_levels_multi(
        name: str, cfg: Dict[str, Any], results: List[Any], total_images: int
    ) -> Optional[AlertRecord]:
        """Avalia alerta modo threshold_levels_multi: multi-indicadores combinados."""
        indicators = cfg.get('indicators', [])
        if not indicators:
            return None

        # Para cada indicador, classificar cada resultado
        indicator_stats = {}
        total_classified = 0

        for indicator in indicators:
            level_counts = defaultdict(int)
            for r in results:
                val = AlertManager._get_value_from_result(r, {'indicator_ref': indicator})
                if val is None:
                    continue
                try:
                    level, _ = config.classify(indicator, val)
                except Exception:
                    continue
                level_counts[level] += 1
                total_classified += 1

            indicator_stats[indicator] = {
                'level_counts': dict(level_counts),
                'total': sum(level_counts.values()),
            }

        if total_classified == 0:
            return None

        # Avaliar regras de severidade
        rules = cfg.get('severity_rules', [])
        for rule in rules:
            rule_when = rule.get('when', {})
            rule_type = rule_when.get('type')
            rule_level = rule_when.get('level')
            min_pct = rule_when.get('min_pct', 0)

            if rule_type != 'any_indicator_pct_at_level':
                continue

            # Verificar se algum indicador tem % no nivel ou pior acima de min_pct
            worst_pct = 0.0
            worst_indicator = None
            for indicator, stats in indicator_stats.items():
                lvl_counts = stats['level_counts']
                count_at_level = sum(
                    cnt for lvl, cnt in lvl_counts.items() if lvl <= rule_level
                )
                pct = (count_at_level / stats['total'] * 100.0) if stats['total'] > 0 else 0.0
                if pct > worst_pct:
                    worst_pct = pct
                    worst_indicator = indicator

            if worst_pct < min_pct:
                continue

            severity = rule.get('severity')
            total_affected = sum(
                sum(cnt for lvl, cnt in s['level_counts'].items() if lvl <= rule_level)
                for s in indicator_stats.values()
            )

            title = cfg.get('title_template', f'Alerta: {name}').format(
                affected_count=total_affected,
                total_count=total_classified,
            )

            # Detail com stats por indicador
            detail_parts = []
            for indicator, stats in indicator_stats.items():
                lvl_counts = stats['level_counts']
                count_poor = sum(cnt for lvl, cnt in lvl_counts.items() if lvl <= rule_level)
                pct = (count_poor / stats['total'] * 100.0) if stats['total'] > 0 else 0.0
                levels_raw = config.resolve_indicator_levels(indicator)
                cutoff = AlertManager._fmt_num(levels_raw[rule_level - 1], 3) if levels_raw and rule_level <= len(levels_raw) else 'N/A'
                detail_parts.append(f'{indicator} > {cutoff}: {pct:.2f}%')

            return AlertManager._make_record(
                severity=severity,
                category=cfg.get('category', 'GENERAL'),
                title=title,
                detail=' | '.join(detail_parts),
                impact=cfg.get('impact', ''),
                action=cfg.get('action', ''),
                affected_count=total_affected,
                total_count=total_classified,
                threshold_value=AlertManager._parse_num(
                    config.resolve_indicator_levels(indicators[0])[rule_level - 1]
                ) if indicators and config.resolve_indicator_levels(indicators[0]) and rule_level <= len(config.resolve_indicator_levels(indicators[0])) else None,
            )

        return None

    @staticmethod
    def _eval_rtk_flag(
        name: str, cfg: Dict[str, Any], results: List[Any], total_images: int
    ) -> Optional[AlertRecord]:
        """Avalia alerta modo rtk_flag: analisa flags RTK."""
        flag_fixed = cfg.get('flag_fixed', 50)
        flag_float = cfg.get('flag_float', 34)
        flag_single = cfg.get('flag_single', 16)

        rtk_fixed_count = 0
        rtk_float_count = 0
        rtk_single_count = 0
        rtk_unknown_count = 0
        rtk_non_fixed_photos = []
        rtk_non_fixed_flights = []

        for r in results:
            rtk_flag = AlertManager._to_int_or_none(
                AlertManager._get_field_from_result(r, f'level5_values.{MFK.RTK_FLAG.value}')
                or AlertManager._get_field_from_result(r, 'values.rtk_flag')
            )
            if rtk_flag is None and hasattr(r, 'get_indicator'):
                rtk_flag = AlertManager._to_int_or_none(r.get_indicator(MFK.RTK_FLAG.value))

            if rtk_flag is None:
                rtk_unknown_count += 1
                continue

            if rtk_flag == flag_fixed:
                rtk_fixed_count += 1
            elif rtk_flag == flag_float:
                rtk_float_count += 1
                rtk_non_fixed_photos.append(getattr(r, 'filename', 'unknown'))
                rtk_non_fixed_flights.append(getattr(r, 'flight_id', 'unknown') or 'unknown')
            elif rtk_flag == flag_single:
                rtk_single_count += 1
                rtk_non_fixed_photos.append(getattr(r, 'filename', 'unknown'))
                rtk_non_fixed_flights.append(getattr(r, 'flight_id', 'unknown') or 'unknown')
            else:
                rtk_unknown_count += 1
                rtk_non_fixed_photos.append(getattr(r, 'filename', 'unknown'))
                rtk_non_fixed_flights.append(getattr(r, 'flight_id', 'unknown') or 'unknown')

        rtk_total = rtk_fixed_count + rtk_float_count + rtk_single_count + rtk_unknown_count
        rtk_non_fixed_count = len(rtk_non_fixed_photos)
        rtk_fixed_pct = (rtk_fixed_count / rtk_total * 100.0) if rtk_total > 0 else 0.0
        rtk_non_fixed_pct = (rtk_non_fixed_count / rtk_total * 100.0) if rtk_total > 0 else 0.0

        if rtk_non_fixed_count == 0 and rtk_unknown_count == 0:
            return None

        # Caso especial: nenhuma flag RTK disponivel
        if rtk_unknown_count == total_images:
            return AlertManager._make_record(
                severity=AlertManager.SEVERITY_INFO,
                category=cfg.get('category', 'RTK_FLAG'),
                title='Flag RTK nao disponivel',
                detail='Nenhuma imagem possui o campo RtkFlag. Nao foi possivel avaliar a qualidade do sinal RTK.',
                impact='Sem informacao de qualidade do sinal RTK para auditoria.',
                action='Garantir que o metadata RtkFlag seja capturado durante o voo.',
                affected_count=rtk_unknown_count,
                total_count=total_images,
            )

        # Avaliar regras de severidade
        rules = cfg.get('severity_rules', [])
        for rule in rules:
            rule_when = rule.get('when', {})
            rule_type = rule_when.get('type')
            rule_value = rule_when.get('value', 0)

            match = False
            if rule_type == 'fixed_pct_lt' and rtk_fixed_pct < rule_value:
                match = True
            elif rule_type == 'non_fixed_pct_gt' and rtk_non_fixed_pct > rule_value:
                match = True
            elif rule_type == 'non_fixed_count_gt' and rtk_non_fixed_count > rule_value:
                match = True

            if not match:
                continue

            severity = rule.get('severity')
            max_photos = cfg.get('max_photos_list', 20)

            detail_parts = [
                f'RTK Fixa (Flag {flag_fixed}): {rtk_fixed_count}/{rtk_total} ({rtk_fixed_pct:.1f}%).',
                f'RTK Flutuante (Flag {flag_float}): {rtk_float_count}.',
                f'RTK Single (Flag {flag_single}): {rtk_single_count}.',
            ]
            if rtk_unknown_count > 0:
                detail_parts.append(f'Desconhecido: {rtk_unknown_count}.')

            flights_unique = sorted(set(rtk_non_fixed_flights))
            if flights_unique:
                detail_parts.append(f'Voo(s): {", ".join(flights_unique)}.')

            return AlertManager._make_record(
                severity=severity,
                category=cfg.get('category', 'RTK_FLAG'),
                title=cfg.get('title_template', 'Queda na qualidade do sinal RTK detectada'),
                detail=' '.join(detail_parts),
                impact=cfg.get('impact', ''),
                action=cfg.get('action', ''),
                affected_count=rtk_non_fixed_count,
                total_count=rtk_total,
                threshold_value=float(flag_fixed),
                actual_value=rtk_fixed_pct,
                flight_ids=flights_unique,
                photos=rtk_non_fixed_photos[:max_photos],
            )

        # Se nenhuma regra match, nao gera alerta
        return None

    @staticmethod
    def _eval_aggregate_std(
        name: str, cfg: Dict[str, Any], results: List[Any],
        per_flight: List[Dict[str, Any]]
    ) -> Optional[AlertRecord]:
        """Avalia alerta modo aggregate_std: desvio padrao de indicador por voo."""
        indicator = cfg.get('indicator_ref')
        std_threshold = cfg.get('std_threshold', 0.5)
        if not indicator or not per_flight:
            return None

        gsd_variation_alerts = 0
        gsd_variation_flights = []

        for flight in per_flight:
            flight_id = flight.get('flight_id', 'unknown')

            # Calcular desvio padrao do indicador para este voo
            values = []
            for r in results:
                if getattr(r, 'flight_id', None) != flight_id:
                    continue
                val = AlertManager._get_value_from_result(r, cfg)
                if val is not None:
                    values.append(val)

            if len(values) >= 2:
                std = statistics.stdev(values)
                if std > std_threshold:
                    gsd_variation_alerts += 1
                    gsd_variation_flights.append(flight_id)

        if gsd_variation_alerts == 0:
            return None

        severity = cfg.get('severity', 'ALERTA')
        flights_unique = sorted(set(gsd_variation_flights))

        title = cfg.get('title_template', f'Variacao de {indicator} acima do limiar').format(
            affected_count=gsd_variation_alerts,
            total_count=len(per_flight),
        )

        return AlertManager._make_record(
            severity=severity,
            category=cfg.get('category', 'GENERAL'),
            title=title,
            detail=(
                f'{gsd_variation_alerts} voo(s) com desvio padrao de {indicator} > {std_threshold}. '
                f'Voo(s): {", ".join(flights_unique)}.'
            ),
            impact=cfg.get('impact', ''),
            action=cfg.get('action', ''),
            affected_count=gsd_variation_alerts,
            total_count=len(per_flight),
            threshold_value=std_threshold,
            flight_ids=flights_unique,
        )

    # ===================================================================
    # Metodos de conversao (mantidos para compatibilidade)
    # ===================================================================

    @staticmethod
    def to_dict(alert: AlertRecord) -> Dict[str, Any]:
        """Converte AlertRecord para dicionario serializavel."""
        return asdict(alert)

    @staticmethod
    def to_dict_list(alerts: List[AlertRecord]) -> List[Dict[str, Any]]:
        """Converte lista de AlertRecords para lista de dicionarios."""
        return [AlertManager.to_dict(a) for a in alerts]

    @staticmethod
    def to_severity_entry(alert: AlertRecord) -> Dict[str, str]:
        """Converte para formato legado compatível com template antigo."""
        return {
            'severity': alert.severity,
            'title': alert.title,
            'detail': alert.detail,
            'impact': alert.impact,
            'action': alert.action,
        }

    @staticmethod
    def summary_by_category(alerts: List[AlertRecord]) -> Dict[str, Dict[str, int]]:
        """Gera sumario de contagem de alertas por categoria e severidade."""
        summary: Dict[str, Dict[str, int]] = {}
        for alert in alerts:
            if alert.category not in summary:
                summary[alert.category] = {}
            cat = summary[alert.category]
            cat[alert.severity] = cat.get(alert.severity, 0) + 1
            cat['total'] = cat.get('total', 0) + 1
        return summary

    # ===================================================================
    # QUALITY ANALYSIS - Metodos avancados mantidos
    # ===================================================================

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
            num = AlertManager._parse_num(raw)
            if num is not None and num not in (float('inf'), float('-inf')):
                return num
        return None

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
                num = AlertManager._parse_num(raw)
                if num is not None and num not in (float('inf'), float('-inf')):
                    values.append(num)
                    break
        return values

    @staticmethod
    def compute_strip_analysis(results: List[Any]) -> Dict[str, Any]:
        """Analisa as strips (faixas) do voo, agrupando por StripID.

        Args:
            results: Lista de objetos IMGMetadata

        Returns:
            Dict com strip_rows e problematic_strips
        """
        from collections import defaultdict

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
                AlertManager._first_numeric_from_result(
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
                    (sum(1 for v in s_overlap_vals if v < AlertManager._OVERLAP_IDEAL) / len(s_overlap_vals) * 100.0), 2
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

    @staticmethod
    def compute_quality_trends(results: List[Any]) -> Dict[str, Any]:
        """Analisa tendencias temporais de qualidade PQI.

        Args:
            results: Lista de objetos IMGMetadata

        Returns:
            Dict com pqi_first_quartile_mean, pqi_last_quartile_mean, pqi_delta,
            morning_pqi_mean, midday_pqi_mean
        """
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

    @staticmethod
    def compute_rtk_classification(results: List[Any]) -> Dict[str, Any]:
        """Classifica a estabilidade do sinal RTK com base no RTK Stability Score.

        Args:
            results: Lista de objetos IMGMetadata

        Returns:
            Dict com rtk_stability_mean e rtk_stability_class
        """
        rtk_stab_score = AlertManager._numeric_from_flight_values(
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

    @staticmethod
    def compute_advanced_metrics(results: List[Any]) -> Dict[str, Any]:
        """Calcula metricas avancadas de qualidade: RTK, Gimbal, Yaw, Overlap, Luz, Blur, etc.

        Args:
            results: Lista de objetos IMGMetadata

        Returns:
            Dict com todas as metricas avancadas
        """
        from ..MathUtils import MathUtils

        # Overlap
        overlap_values = AlertManager._numeric_from_flight_values(
            results, [MFK.PREDICTED_OVERLAP.value, MFK.F_OVERLAP.value, 'predicted_overlap', 'f_overlap']
        )
        overlap_below_pct = 0.0
        if overlap_values:
            overlap_below_ideal = [v for v in overlap_values if v < AlertManager._OVERLAP_IDEAL]
            overlap_below_pct = (len(overlap_below_ideal) / len(overlap_values) * 100.0) if overlap_values else 0.0
        overlap_mean = statistics.mean(overlap_values) if overlap_values else None

        # Yaw
        yaw_err_values = AlertManager._numeric_from_flight_values(
            results, [MFK.YAW_ALIGNMENT_ERROR.value, 'yaw_alignment_error']
        )
        yaw_opposite = [v for v in yaw_err_values if v >= 150.0] if yaw_err_values else []
        yaw_opposite_pct = (len(yaw_opposite) / len(yaw_err_values) * 100.0) if yaw_err_values else 0.0

        # RTK Diff Age
        rtk_diff_age = AlertManager._numeric_from_flight_values(
            results, [MFK.RTK_DIFF_AGE.value, 'rtk_diff_age']
        )
        rtk_diff_age_mean = statistics.mean(rtk_diff_age) if rtk_diff_age else None
        rtk_diff_age_max = max(rtk_diff_age) if rtk_diff_age else None
        rtk_diff_age_p95 = (
            sorted(rtk_diff_age)[int(0.95 * (len(rtk_diff_age) - 1))]
            if rtk_diff_age else None
        )

        # Gimbal
        gimbal_offset = AlertManager._numeric_from_flight_values(
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
        size_mb = AlertManager._numeric_from_flight_values(
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
        speed_ms = AlertManager._numeric_from_flight_values(
            results, [MFK.THREE_D_SPEED.value, 'speed_3d_ms']
        )
        motion_blur = AlertManager._numeric_from_flight_values(
            results, [MFK.MOTION_BLUR_RISK.value, 'motion_blur_risk']
        )
        speed_var = AlertManager._numeric_from_flight_values(
            results, [MFK.SPEED_VARIATION_INDEX.value, 'speed_variation_index']
        )

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
        rtk_effective_precision = AlertManager._numeric_from_flight_values(
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
            'rtk_diff_age_mean': round(rtk_diff_age_mean, 4) if rtk_diff_age_mean is not None else None,
            'rtk_diff_age_max': round(rtk_diff_age_max, 4) if rtk_diff_age_max is not None else None,
            'rtk_diff_age_p95': round(rtk_diff_age_p95, 4) if rtk_diff_age_p95 is not None else None,
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
            'speed_ms_recommended': f'{AlertManager._SPEED_RECOMMENDED_MIN_MS:.0f}-{AlertManager._SPEED_RECOMMENDED_MAX_MS:.0f} m/s',
            'motion_blur_mean': round(statistics.mean(motion_blur), 4) if motion_blur else None,
            'speed_variation_mean': round(statistics.mean(speed_var), 4) if speed_var else None,
            'light_inconsistent_pct': round(light_inconsistent_pct, 2),
        }

    @staticmethod
    def compute_recommendations(advanced_metrics: Dict[str, Any]) -> List[str]:
        """Gera recomendacoes operacionais com base nas metricas avancadas.

        Args:
            advanced_metrics: Dict com metricas avancadas

        Returns:
            Lista de strings com recomendacoes
        """
        recommendations = []

        overlap_below_pct = advanced_metrics.get('overlap_below_ideal_pct')
        if overlap_below_pct is not None and overlap_below_pct > 30:
            recommendations.append('Aumentar overlap para >=70% nas proximas missoes e repetir faixas com baixa sobreposicao.')

        yaw_inconsistent_pct = advanced_metrics.get('yaw_inconsistent_pct')
        if yaw_inconsistent_pct is not None and yaw_inconsistent_pct > 5:
            recommendations.append('Padronizar heading e evitar alternancia de sentido sem estrategia de bloco.')

        gimbal_offset_over_1deg_pct = advanced_metrics.get('gimbal_offset_over_1deg_pct')
        if gimbal_offset_over_1deg_pct is not None and gimbal_offset_over_1deg_pct > 20:
            recommendations.append('Recalibrar gimbal e validar alinhamento antes da decolagem.')

        rtk_diff_age_max = advanced_metrics.get('rtk_diff_age_max')
        if rtk_diff_age_max is not None and rtk_diff_age_max > 2:
            recommendations.append('Melhorar vinculacao RTK/base e reduzir idade de correcao RTK durante o voo.')

        light_inconsistent_pct = advanced_metrics.get('light_inconsistent_pct')
        if light_inconsistent_pct is not None and light_inconsistent_pct > 20:
            recommendations.append('Planejar janelas de luz mais estaveis e reduzir mudancas bruscas de iluminacao.')

        if not recommendations:
            recommendations.append('Parametros principais estaveis. Manter padrao operacional atual e monitorar indicadores criticos.')

        return recommendations