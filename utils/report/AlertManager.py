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
    category: str                # 'DEWARP', 'RTK', 'GSD', 'MOTION_BLUR', 'GIMBAL', 'ALTITUDE', 'OVERLAP', 'YAW', 'GSD_VARIATION', 'RTK_FLAG'
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
    """Centraliza a geracao de todos os alertas de qualidade do relatorio fotogrametrico."""

    SEVERITY_CRITICAL = 'CRITICO'
    SEVERITY_ALERT = 'ALERTA'
    SEVERITY_INFO = 'INFO'

    # Categorias de alerta
    CAT_DEWARP = 'DEWARP'
    CAT_RTK = 'RTK'
    CAT_GSD = 'GSD'
    CAT_GSD_VARIATION = 'GSD_VARIATION'
    CAT_MOTION_BLUR = 'MOTION_BLUR'
    CAT_GIMBAL = 'GIMBAL'
    CAT_ALTITUDE = 'ALTITUDE'
    CAT_OVERLAP = 'OVERLAP'
    CAT_YAW = 'YAW'
    CAT_RTK_FLAG = 'RTK_FLAG'
    CAT_TEMPERATURE = 'TEMPERATURE'
    CAT_ILLUMINATION = 'ILLUMINATION'
    CAT_SPEED = 'SPEED'
    CAT_SHUTTER = 'SHUTTER'
    CAT_GENERAL = 'GENERAL'

    # Limiares configurados
    BLUR_ALERT_THRESHOLD = 0.5       # MotionBlurRisk > 0.5
    BLUR_CRITICAL_THRESHOLD = 1.0    # MotionBlurRisk > 1.0
    GIMBAL_OFFSET_ALERT = 15.0       # GimbalOffset > 15 graus
    GIMBAL_OFFSET_CRITICAL = 30.0    # GimbalOffset > 30 graus
    GSD_VARIATION_THRESHOLD = 0.5    # Variacao GSD > 0.5cm indica irregularidade
    RTK_FLAG_FIXED = 50              # Flag 50 = RTK fixa
    RTK_FLAG_FLOAT = 34              # Flag 34 = flutuante
    RTK_FLAG_SINGLE = 16             # Flag 16 = single
    OVERLAP_CRITICAL_PCT = 30.0      # % de imagens com overlap < 60%
    YAW_OPPOSITE_THRESHOLD = 150.0   # Yaw alignment error para direcao oposta
    YAW_CRITICAL_PCT = 5.0           # % maxima aceitavel de yaw oposto
    RTK_STD_LAT_CRITICAL_PCT = 20.0  # % maxima aceitavel de lat com desvio alto
    ALTITUDE_MISSING_WARN_PCT = 10.0 # % maxima aceitavel de altitude ausente

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

    @staticmethod
    def analyze(results: List[Any], agg: Dict[str, Any]) -> List[AlertRecord]:
        """Executa todas as analises e retorna lista centralizada de alertas."""
        alerts: List[AlertRecord] = []
        total_images = len(results)

        if total_images == 0:
            return alerts

        # Extrair flights do agg para analises por voo
        per_flight = agg.get('per_flight', [])

        # ===================================================================
        # 1. DEWARP - Dewarp desabilitado
        # ===================================================================
        dewarp_zero_count = agg.get('general_info', {}).get('dewarp_zero_count', 0)
        if dewarp_zero_count > 0:
            severity = AlertManager.SEVERITY_CRITICAL if dewarp_zero_count == total_images else AlertManager.SEVERITY_ALERT
            flights_affected = []
            for r in results:
                try:
                    val = AlertManager._parse_num(r.dewarp_flag)
                    if val is not None and val == 0.0:
                        flights_affected.append(r.flight_id or 'unknown')
                except Exception:
                    pass
            flights_affected = sorted(set(flights_affected))

            if dewarp_zero_count == total_images:
                alerts.append(AlertManager._make_record(
                    severity=AlertManager.SEVERITY_CRITICAL,
                    category=AlertManager.CAT_DEWARP,
                    title='Dewarp desativado em 100% das imagens',
                    detail=f'{dewarp_zero_count}/{total_images} imagens com DewarpFlag=0.',
                    impact='Risco elevado de distorcao sistematica e degradacao da aerotriangulacao.',
                    action='Reprocessar com dewarping habilitado e validar calibracao interna da camera.',
                    affected_count=dewarp_zero_count,
                    total_count=total_images,
                    threshold_value=1,
                    actual_value=0,
                    flight_ids=flights_affected,
                ))
            else:
                flight_detail = f'Voo(s): {", ".join(flights_affected)}' if flights_affected else ''
                alerts.append(AlertManager._make_record(
                    severity=AlertManager.SEVERITY_ALERT,
                    category=AlertManager.CAT_DEWARP,
                    title=f'{dewarp_zero_count} foto(s) sem dewarping',
                    detail=f'{dewarp_zero_count}/{total_images} imagens com DewarpFlag=0. {flight_detail}',
                    impact='Distorcao localizada pode comprometer precisao geometrica nas areas afetadas.',
                    action='Reprocessar imagens afetadas com dewarping habilitado.',
                    affected_count=dewarp_zero_count,
                    total_count=total_images,
                    threshold_value=1,
                    actual_value=0,
                    flight_ids=flights_affected,
                ))

        # ===================================================================
        # 2. ALTITUDE - Altitude incompleta
        # ===================================================================
        missing_alt_count = agg.get('general_info', {}).get('missing_altitude_count', 0)
        if missing_alt_count > 0:
            flights_affected = []
            for r in results:
                try:
                    alt_mrk_missing = AlertManager._parse_num(r.alt_mrk) is None
                    alt_abs_missing = AlertManager._parse_num(r.absolute_altitude) is None
                    if alt_mrk_missing and alt_abs_missing:
                        flights_affected.append(r.flight_id or 'unknown')
                except Exception:
                    pass
            flights_affected = sorted(set(flights_affected))
            missing_pct = (missing_alt_count / total_images) * 100.0

            severity = AlertManager.SEVERITY_CRITICAL if missing_pct > 50.0 else (
                AlertManager.SEVERITY_ALERT if missing_pct > AlertManager.ALTITUDE_MISSING_WARN_PCT else AlertManager.SEVERITY_INFO
            )
            flight_detail = f'Voo(s): {", ".join(flights_affected)}' if flights_affected else ''
            alerts.append(AlertManager._make_record(
                severity=severity,
                category=AlertManager.CAT_ALTITUDE,
                title=f'{missing_alt_count} foto(s) sem altitude completa',
                detail=f'{missing_alt_count}/{total_images} imagens sem Alt (MRK) e AbsoluteAltitude. {flight_detail}',
                impact='Afeta consistencia altimetrica, calculo de GSD e sobreposicao prevista.',
                action='Corrigir captura de Alt (MRK) e AbsoluteAltitude antes do processamento.',
                affected_count=missing_alt_count,
                total_count=total_images,
                actual_value=missing_pct,
                flight_ids=flights_affected,
            ))

        # ===================================================================
        # 3. MOTION BLUR - Fotos com blur > 0.5
        # ===================================================================
        blur_values = []
        blur_photos: List[str] = []
        blur_flights: List[str] = []
        blur_high_photos: List[str] = []
        for r in results:
            val = AlertManager._parse_num(r.messages.get('motion_blur_risk') or r.level5_values.get(MFK.MOTION_BLUR_RISK.value))
            if val is None:
                # Tenta obter pelo campo MotionBlurRisk
                for key in [MFK.MOTION_BLUR_RISK.value, 'motion_blur_risk']:
                    raw = r.level5_values.get(key) or r.values.get(key)
                    if key.startswith('Motion'):
                        val = AlertManager._parse_num(raw)
                        if val is not None:
                            break
            if val is not None:
                blur_values.append(val)
                if val > AlertManager.BLUR_ALERT_THRESHOLD:
                    blur_photos.append(r.filename)
                    blur_flights.append(r.flight_id or 'unknown')
                    if val > AlertManager.BLUR_CRITICAL_THRESHOLD:
                        blur_high_photos.append(r.filename)
            else:
                # Tenta via get_indicator
                val_raw = r.get_indicator(MFK.MOTION_BLUR_RISK.value) if hasattr(r, 'get_indicator') else None
                if val_raw is not None:
                    val = AlertManager._parse_num(val_raw)
                    if val is not None:
                        blur_values.append(val)
                        if val > AlertManager.BLUR_ALERT_THRESHOLD:
                            blur_photos.append(r.filename)
                            blur_flights.append(r.flight_id or 'unknown')
                            if val > AlertManager.BLUR_CRITICAL_THRESHOLD:
                                blur_high_photos.append(r.filename)

        blur_count = len(blur_photos)
        blur_high_count = len(blur_high_photos)
        blur_mean = statistics.mean(blur_values) if blur_values else None
        blur_max = max(blur_values) if blur_values else None

        if blur_count > 0:
            blur_flights_unique = sorted(set(blur_flights))
            # Fotos com blur > 0.5 (alerta)
            severity = AlertManager.SEVERITY_CRITICAL if blur_high_count > 0 else AlertManager.SEVERITY_ALERT
            detail_parts = [
                f'{blur_count}/{len(blur_values)} imagens com MotionBlur > {AlertManager.BLUR_ALERT_THRESHOLD}.'
            ]
            if blur_high_count > 0:
                detail_parts.append(f'Sendo {blur_high_count} com blur critico > {AlertManager.BLUR_CRITICAL_THRESHOLD}.')
            if blur_mean is not None:
                detail_parts.append(f'Blur medio: {blur_mean:.3f}.')
            if blur_max is not None:
                detail_parts.append(f'Blur maximo: {blur_max:.3f}.')
            if blur_flights_unique:
                detail_parts.append(f'Voo(s) afetados: {", ".join(blur_flights_unique)}.')

            alerts.append(AlertManager._make_record(
                severity=severity,
                category=AlertManager.CAT_MOTION_BLUR,
                title=f'Motion Blur elevado em {blur_count} foto(s)',
                detail=' '.join(detail_parts),
                impact='Borramento reduz nitidez das imagens, compromete matching, DSM e ortofoto.',
                action='Reduzir velocidade de voo, ajustar taxa de obturação e evitar vento forte.',
                affected_count=blur_count,
                total_count=len(blur_values) or total_images,
                threshold_value=AlertManager.BLUR_ALERT_THRESHOLD,
                actual_value=blur_max,
                flight_ids=blur_flights_unique,
                photos=blur_photos[:20],  # Limita a 20 fotos
            ))

        # ===================================================================
        # 4. GIMBAL OFFSET - Desalinhamento > 15°
        # ===================================================================
        gimbal_values = []
        gimbal_photos: List[str] = []
        gimbal_flights: List[str] = []
        for r in results:
            val = AlertManager._parse_num(r.level5_values.get(MFK.GIMBAL_OFFSET.value) or r.values.get('gimbal_offset'))
            if val is None:
                val = r.get_indicator(MFK.GIMBAL_OFFSET.value) if hasattr(r, 'get_indicator') else None
                val = AlertManager._parse_num(val)
            if val is not None:
                gimbal_values.append(abs(val))  # Usar valor absoluto
                if abs(val) > AlertManager.GIMBAL_OFFSET_ALERT:
                    gimbal_photos.append(r.filename)
                    gimbal_flights.append(r.flight_id or 'unknown')

        gimbal_alert_count = len(gimbal_photos)
        gimbal_critical_count = sum(1 for v in gimbal_values if abs(v) > AlertManager.GIMBAL_OFFSET_CRITICAL) if gimbal_values else 0
        gimbal_mean = statistics.mean(gimbal_values) if gimbal_values else None
        gimbal_max = max(gimbal_values) if gimbal_values else None

        if gimbal_alert_count > 0:
            gimbal_flights_unique = sorted(set(gimbal_flights))
            severity = AlertManager.SEVERITY_CRITICAL if gimbal_critical_count > 0 else AlertManager.SEVERITY_ALERT
            detail_parts = [
                f'{gimbal_alert_count}/{len(gimbal_values)} imagens com GimbalOffset > {AlertManager.GIMBAL_OFFSET_ALERT}°.'
            ]
            if gimbal_critical_count > 0:
                detail_parts.append(f'Sendo {gimbal_critical_count} com offset critico > {AlertManager.GIMBAL_OFFSET_CRITICAL}°.')
            if gimbal_mean is not None:
                detail_parts.append(f'Offset medio: {gimbal_mean:.2f}°.')
            if gimbal_max is not None:
                detail_parts.append(f'Offset maximo: {gimbal_max:.2f}°.')
            if gimbal_flights_unique:
                detail_parts.append(f'Voo(s) afetados: {", ".join(gimbal_flights_unique)}.')

            alerts.append(AlertManager._make_record(
                severity=severity,
                category=AlertManager.CAT_GIMBAL,
                title=f'Gimbal desalinhado em {gimbal_alert_count} foto(s)',
                detail=' '.join(detail_parts),
                impact='Desalinhamento do gimbal causa rotacao na imagem, afetando matching e orientacao.',
                action='Recalibrar gimbal, verificar fixacao e realizar voo de calibracao.',
                affected_count=gimbal_alert_count,
                total_count=len(gimbal_values) or total_images,
                threshold_value=AlertManager.GIMBAL_OFFSET_ALERT,
                actual_value=gimbal_max,
                flight_ids=gimbal_flights_unique,
                photos=gimbal_photos[:20],
            ))

        # ===================================================================
        # 5. RTK FLAG - Monitoramento de qualidade do sinal RTK por foto
        # ===================================================================
        rtk_fixed_count = 0
        rtk_float_count = 0
        rtk_single_count = 0
        rtk_unknown_count = 0
        rtk_non_fixed_photos: List[str] = []
        rtk_non_fixed_flights: List[str] = []

        for r in results:
            rtk_flag = AlertManager._to_int_or_none(r.level5_values.get(MFK.RTK_FLAG.value) or r.values.get('rtk_flag'))
            if rtk_flag is None:
                rtk_flag = AlertManager._to_int_or_none(
                    r.get_indicator(MFK.RTK_FLAG.value) if hasattr(r, 'get_indicator') else None
                )
            if rtk_flag is None:
                # Tenta encontrar nos dados crus
                for key in [MFK.RTK_FLAG.value, 'RtkFlag', 'rtk_flag']:
                    raw = r.level5_values.get(key) or r.values.get(key) or (r._data.get(key) if hasattr(r, '_data') else None)
                    rtk_flag = AlertManager._to_int_or_none(raw)
                    if rtk_flag is not None:
                        break

            if rtk_flag is None:
                rtk_unknown_count += 1
                continue

            if rtk_flag == AlertManager.RTK_FLAG_FIXED:
                rtk_fixed_count += 1
            elif rtk_flag == AlertManager.RTK_FLAG_FLOAT:
                rtk_float_count += 1
                rtk_non_fixed_photos.append(r.filename)
                rtk_non_fixed_flights.append(r.flight_id or 'unknown')
            elif rtk_flag == AlertManager.RTK_FLAG_SINGLE:
                rtk_single_count += 1
                rtk_non_fixed_photos.append(r.filename)
                rtk_non_fixed_flights.append(r.flight_id or 'unknown')
            else:
                rtk_unknown_count += 1
                rtk_non_fixed_photos.append(r.filename)
                rtk_non_fixed_flights.append(r.flight_id or 'unknown')

        rtk_total_classified = rtk_fixed_count + rtk_float_count + rtk_single_count + rtk_unknown_count
        rtk_non_fixed_count = len(rtk_non_fixed_photos)
        rtk_fixed_pct = (rtk_fixed_count / rtk_total_classified * 100.0) if rtk_total_classified > 0 else 0.0
        rtk_non_fixed_pct = (rtk_non_fixed_count / rtk_total_classified * 100.0) if rtk_total_classified > 0 else 0.0

        if rtk_non_fixed_count > 0:
            rtk_non_fixed_flights_unique = sorted(set(rtk_non_fixed_flights))
            severity = AlertManager.SEVERITY_CRITICAL if rtk_fixed_pct < 80.0 else (
                AlertManager.SEVERITY_ALERT if rtk_non_fixed_pct > 5.0 else AlertManager.SEVERITY_INFO
            )
            detail_parts = [
                f'RTK Fixa (Flag 50): {rtk_fixed_count}/{rtk_total_classified} ({rtk_fixed_pct:.1f}%).',
                f'RTK Flutuante (Flag 34): {rtk_float_count}.',
                f'RTK Single (Flag 16): {rtk_single_count}.',
            ]
            if rtk_unknown_count > 0:
                detail_parts.append(f'Desconhecido: {rtk_unknown_count}.')
            if rtk_non_fixed_flights_unique:
                detail_parts.append(f'Voo(s) com sinal nao-fixo: {", ".join(rtk_non_fixed_flights_unique)}.')

            alerts.append(AlertManager._make_record(
                severity=severity,
                category=AlertManager.CAT_RTK_FLAG,
                title='Queda na qualidade do sinal RTK detectada',
                detail=' '.join(detail_parts),
                impact='Sinal RTK nao-fixo reduz precisao posicional e pode degradar o georreferenciamento direto.',
                action='Verificar base RTK, radio link, visibilidade GNSS e configuracao do receptor.',
                affected_count=rtk_non_fixed_count,
                total_count=rtk_total_classified,
                threshold_value=AlertManager.RTK_FLAG_FIXED,
                actual_value=rtk_fixed_pct,
                flight_ids=rtk_non_fixed_flights_unique,
                photos=rtk_non_fixed_photos[:20],
            ))

        if rtk_unknown_count == total_images:
            alerts.append(AlertManager._make_record(
                severity=AlertManager.SEVERITY_INFO,
                category=AlertManager.CAT_RTK_FLAG,
                title='Flag RTK nao disponivel',
                detail='Nenhuma imagem possui o campo RtkFlag. Nao foi possivel avaliar a qualidade do sinal RTK.',
                impact='Sem informacao de qualidade do sinal RTK para auditoria.',
                action='Garantir que o metadata RtkFlag seja capturado durante o voo.',
                affected_count=rtk_unknown_count,
                total_count=total_images,
            ))

        # ===================================================================
        # 6. GSD VARIATION por voo - Variacao > 0.5cm indica irregularidade de altitude
        # ===================================================================
        gsd_variation_alerts = 0
        gsd_variation_flights: List[str] = []
        for flight in per_flight:
            flight_id = flight.get('flight_id', 'unknown')
            gsd_mean = flight.get('level5_means', {}).get(MFK.GROUND_SAMPLE_DISTANCE_CM.value)
            if gsd_mean is not None:
                gsd_mean = AlertManager._parse_num(gsd_mean)
            if gsd_mean is None:
                continue

            # Calcular variacao do GSD para este voo a partir dos resultados
            gsd_values = []
            for r in results:
                if r.flight_id != flight_id:
                    continue
                val = AlertManager._parse_num(r.values.get('gsd_cm') or r.level5_values.get(MFK.GROUND_SAMPLE_DISTANCE_CM.value))
                if val is None:
                    val = r.get_indicator('gsd_cm') if hasattr(r, 'get_indicator') else None
                    val = AlertManager._parse_num(val)
                if val is not None:
                    gsd_values.append(val)

            if len(gsd_values) >= 2:
                gsd_std = statistics.stdev(gsd_values)
                gsd_var = gsd_std  # desvio padrao ja representa variacao
                if gsd_var > AlertManager.GSD_VARIATION_THRESHOLD:
                    gsd_variation_alerts += 1
                    gsd_variation_flights.append(flight_id)

        if gsd_variation_alerts > 0:
            gsd_variation_flights_unique = sorted(set(gsd_variation_flights))
            alerts.append(AlertManager._make_record(
                severity=AlertManager.SEVERITY_ALERT,
                category=AlertManager.CAT_GSD_VARIATION,
                title=f'Variacao de GSD acima do limiar em {gsd_variation_alerts} voo(s)',
                detail=(
                    f'{gsd_variation_alerts} voo(s) apresentaram variacao de GSD (desvio padrao) '
                    f'> {AlertManager.GSD_VARIATION_THRESHOLD}cm, indicando possivel irregularidade de altitude. '
                    f'Voo(s): {", ".join(gsd_variation_flights_unique)}.'
                ),
                impact='Variacao de GSD indica irregularidade de altitude que compromete a consistencia do produto final.',
                action='Verificar estabilidade de altitude do drone e condicoes de vento durante o voo.',
                affected_count=gsd_variation_alerts,
                total_count=len(per_flight),
                threshold_value=AlertManager.GSD_VARIATION_THRESHOLD,
                flight_ids=gsd_variation_flights_unique,
            ))

        # ===================================================================
        # 7. OVERLAP - Sobreposicao insuficiente
        # ===================================================================
        overlap_values = []
        for r in results:
            val = AlertManager._parse_num(r.level5_values.get(MFK.PREDICTED_OVERLAP.value) or r.values.get('predicted_overlap'))
            if val is None:
                val = AlertManager._parse_num(r.level5_values.get(MFK.F_OVERLAP.value) or r.values.get('f_overlap'))
            if val is None:
                val = r.get_indicator(MFK.PREDICTED_OVERLAP.value) if hasattr(r, 'get_indicator') else None
                val = AlertManager._parse_num(val)
            if val is not None:
                overlap_values.append(val)

        OVERLAP_IDEAL = 60.0
        overlap_below = [v for v in overlap_values if v < OVERLAP_IDEAL]
        overlap_below_pct = (len(overlap_below) / len(overlap_values) * 100.0) if overlap_values else 0.0
        overlap_mean = statistics.mean(overlap_values) if overlap_values else None

        if overlap_values and overlap_below_pct > AlertManager.OVERLAP_CRITICAL_PCT:
            severity = AlertManager.SEVERITY_CRITICAL if overlap_below_pct > 50.0 else AlertManager.SEVERITY_ALERT
            alerts.append(AlertManager._make_record(
                severity=severity,
                category=AlertManager.CAT_OVERLAP,
                title='Overlap insuficiente para reconstrucao robusta',
                detail=(
                    f'{overlap_below_pct:.2f}% das imagens com overlap < {OVERLAP_IDEAL:.0f}%. '
                    f'Overlap medio: {overlap_mean:.1f}%.'
                ),
                impact='Pode causar lacunas, alinhamento fraco e aumento de ruido no modelo 3D.',
                action='Aumentar sobreposicao longitudinal/lateral e refazer as faixas criticas.',
                affected_count=len(overlap_below),
                total_count=len(overlap_values),
                threshold_value=OVERLAP_IDEAL,
                actual_value=overlap_mean,
            ))

        # ===================================================================
        # 8. YAW - Inconsistencia de direcao de voo
        # ===================================================================
        yaw_values = []
        for r in results:
            val = AlertManager._parse_num(r.level5_values.get(MFK.YAW_ALIGNMENT_ERROR.value) or r.values.get('yaw_alignment_error'))
            if val is None:
                val = r.get_indicator(MFK.YAW_ALIGNMENT_ERROR.value) if hasattr(r, 'get_indicator') else None
                val = AlertManager._parse_num(val)
            if val is not None:
                yaw_values.append(val)

        yaw_opposite = [v for v in yaw_values if v >= AlertManager.YAW_OPPOSITE_THRESHOLD]
        yaw_opposite_pct = (len(yaw_opposite) / len(yaw_values) * 100.0) if yaw_values else 0.0

        if yaw_values and yaw_opposite_pct > AlertManager.YAW_CRITICAL_PCT:
            alerts.append(AlertManager._make_record(
                severity=AlertManager.SEVERITY_ALERT,
                category=AlertManager.CAT_YAW,
                title='Inconsistencia de direcao de voo (yaw)',
                detail=f'{yaw_opposite_pct:.2f}% das imagens com YawAlignmentError >= {AlertManager.YAW_OPPOSITE_THRESHOLD}°.',
                impact='Direcoes conflitantes podem reduzir matching e gerar faixas desalinhadas.',
                action='Revisar planejamento de heading e evitar trechos em sentido oposto sem controle de bloco.',
                affected_count=len(yaw_opposite),
                total_count=len(yaw_values),
                threshold_value=AlertManager.YAW_OPPOSITE_THRESHOLD,
                actual_value=max(yaw_values) if yaw_values else None,
            ))

        # ===================================================================
        # 9. RTK STD - Sinal GPS/RTK com qualidade insuficiente
        # ===================================================================
        rtk_lat_vals = []
        rtk_hgt_vals = []
        for r in results:
            lat = AlertManager._parse_num(r.level5_values.get(MFK.RTK_STD_LAT.value) or r.values.get('rtk_std_lat'))
            if lat is None:
                lat = r.get_indicator(MFK.RTK_STD_LAT.value) if hasattr(r, 'get_indicator') else None
                lat = AlertManager._parse_num(lat)
            if lat is not None:
                rtk_lat_vals.append(lat)

            hgt = AlertManager._parse_num(r.level5_values.get(MFK.RTK_STD_HGT.value) or r.values.get('rtk_std_hgt'))
            if hgt is None:
                hgt = r.get_indicator(MFK.RTK_STD_HGT.value) if hasattr(r, 'get_indicator') else None
                hgt = AlertManager._parse_num(hgt)
            if hgt is not None:
                rtk_hgt_vals.append(hgt)

        lat_thresh = config.get_thresholds('rtk_std_lat') if config._config else None
        hgt_thresh = config.get_thresholds('rtk_std_hgt') if config._config else None
        lat_cut = AlertManager._parse_num(lat_thresh['levels'][0]) if lat_thresh and lat_thresh.get('levels') else 0.050
        hgt_cut = AlertManager._parse_num(hgt_thresh['levels'][0]) if hgt_thresh and hgt_thresh.get('levels') else 0.100

        poor_lat = [v for v in rtk_lat_vals if v > lat_cut] if lat_cut else []
        poor_hgt = [v for v in rtk_hgt_vals if v > hgt_cut] if hgt_cut else []
        poor_lat_pct = (len(poor_lat) / len(rtk_lat_vals) * 100.0) if rtk_lat_vals else 0.0
        poor_hgt_pct = (len(poor_hgt) / len(rtk_hgt_vals) * 100.0) if rtk_hgt_vals else 0.0

        if rtk_lat_vals and rtk_hgt_vals and (poor_lat_pct > AlertManager.RTK_STD_LAT_CRITICAL_PCT or poor_hgt_pct > AlertManager.RTK_STD_LAT_CRITICAL_PCT):
            lat_str = f'{lat_cut:.3f}' if lat_cut else 'N/A'
            hgt_str = f'{hgt_cut:.3f}' if hgt_cut else 'N/A'
            severity = AlertManager.SEVERITY_CRITICAL if (poor_lat_pct > 50.0 or poor_hgt_pct > 50.0) else AlertManager.SEVERITY_ALERT
            alerts.append(AlertManager._make_record(
                severity=severity,
                category=AlertManager.CAT_RTK,
                title='Sinal GPS/RTK com qualidade insuficiente',
                detail=(
                    f'RtkStdLat > {lat_str} em {poor_lat_pct:.2f}% '
                    f'e RtkStdHgt > {hgt_str} em {poor_hgt_pct:.2f}% das imagens.'
                ),
                impact='Reduz precisao posicional e pode degradar alinhamento, georreferenciamento e qualidade final do produto.',
                action='Validar base RTK, radio/link, visibilidade GNSS e repetir trechos com altos desvios padrao.',
                affected_count=len(poor_lat) + len(poor_hgt),
                total_count=len(rtk_lat_vals) + len(rtk_hgt_vals),
                threshold_value=lat_cut,
                actual_value=max(poor_lat + poor_hgt) if (poor_lat or poor_hgt) else None,
            ))

        # ===================================================================
        # 10. TEMPERATURE - Sensor com temperatura elevada
        # ===================================================================
        temp_values = []
        for r in results:
            val = AlertManager._parse_num(r.values.get('sensor_temp_c') or r.level5_values.get(MFK.SENSOR_TEMPERATURE.value))
            if val is None:
                val = r.get_indicator('sensor_temp_c') if hasattr(r, 'get_indicator') else None
                val = AlertManager._parse_num(val)
            if val is not None:
                temp_values.append(val)

        TEMP_ALERT = 45.0
        TEMP_CRITICAL = 48.0
        temp_high = [v for v in temp_values if v > TEMP_ALERT]
        temp_critical = [v for v in temp_values if v > TEMP_CRITICAL]
        if temp_high:
            severity = AlertManager.SEVERITY_CRITICAL if temp_critical else AlertManager.SEVERITY_ALERT
            temp_mean = statistics.mean(temp_values)
            temp_max = max(temp_values)
            alerts.append(AlertManager._make_record(
                severity=severity,
                category=AlertManager.CAT_TEMPERATURE,
                title=f'Temperatura do sensor elevada em {len(temp_high)} foto(s)',
                detail=(
                    f'{len(temp_high)}/{len(temp_values)} imagens com temperatura do sensor > {TEMP_ALERT}°C. '
                    f'Temperatura media: {temp_mean:.1f}°C. Maxima: {temp_max:.1f}°C.'
                ),
                impact='Temperatura elevada aumenta ruido termico, degrada qualidade radiometrica e pode causar artefatos.',
                action='Pausar voo para resfriamento, reduzir taxa de captura ou operar em horarios mais amenos.',
                affected_count=len(temp_high),
                total_count=len(temp_values),
                threshold_value=TEMP_ALERT,
                actual_value=temp_max,
            ))

        # ===================================================================
        # Ordenar alertas: CRITICO primeiro, depois ALERTA, depois INFO
        # ===================================================================
        severity_order = {AlertManager.SEVERITY_CRITICAL: 0, AlertManager.SEVERITY_ALERT: 1, AlertManager.SEVERITY_INFO: 2}
        alerts.sort(key=lambda a: (severity_order.get(a.severity, 99), a.category, -a.affected_pct))

        return alerts

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