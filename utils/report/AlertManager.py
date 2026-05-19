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
    RTK_EFFECTIVE_PRECISION_ALERT = 0.100  # RTK Effective Precision > 0.100 (critico)
    RTK_EFFECTIVE_PRECISION_WARN = 0.050   # RTK Effective Precision > 0.050 (alerta)

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
            # Dewarp é sempre CRITICO - qualquer imagem sem dewarp compromete o bloco
            severity = AlertManager.SEVERITY_CRITICAL
            flights_affected = []
            for r in results:
                try:
                    val = AlertManager._parse_num(r.dewarp_flag)
                    if val is not None and val == 0.0:
                        flights_affected.append(r.flight_id or 'unknown')
                except Exception:
                    pass
            flights_affected = sorted(set(flights_affected))

            flight_detail = f'Voo(s): {", ".join(flights_affected)}' if flights_affected else ''
            detail_msg = (
                f'{dewarp_zero_count}/{total_images} imagens com DewarpFlag=0. '
                f'{flight_detail}'
            )
            alerts.append(AlertManager._make_record(
                severity=AlertManager.SEVERITY_CRITICAL,
                category=AlertManager.CAT_DEWARP,
                title=f'Dewarp desativado em {dewarp_zero_count} foto(s) - CRITICO',
                detail=detail_msg,
                impact='Distorcao sistematica compromete aerotriangulacao, geometria e qualidade radiometrica da reconstrucao.',
                action='Reprocessar 100% das imagens com dewarping habilitado e validar calibracao interna da camera.',
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
        # 9. RTK STD - Sinal GPS/RTK com qualidade insuficiente (Lat/Lon/Hgt)
        # ===================================================================
        rtk_lat_vals = []
        rtk_lon_vals = []
        rtk_hgt_vals = []
        for r in results:
            lat = AlertManager._parse_num(r.level5_values.get(MFK.RTK_STD_LAT.value) or r.values.get('rtk_std_lat'))
            if lat is None:
                lat = r.get_indicator(MFK.RTK_STD_LAT.value) if hasattr(r, 'get_indicator') else None
                lat = AlertManager._parse_num(lat)
            if lat is not None:
                rtk_lat_vals.append(lat)

            lon = AlertManager._parse_num(r.level5_values.get(MFK.RTK_STD_LON.value) or r.values.get('rtk_std_lon'))
            if lon is None:
                lon = r.get_indicator(MFK.RTK_STD_LON.value) if hasattr(r, 'get_indicator') else None
                lon = AlertManager._parse_num(lon)
            if lon is not None:
                rtk_lon_vals.append(lon)

            hgt = AlertManager._parse_num(r.level5_values.get(MFK.RTK_STD_HGT.value) or r.values.get('rtk_std_hgt'))
            if hgt is None:
                hgt = r.get_indicator(MFK.RTK_STD_HGT.value) if hasattr(r, 'get_indicator') else None
                hgt = AlertManager._parse_num(hgt)
            if hgt is not None:
                rtk_hgt_vals.append(hgt)

        lat_thresh = config.get_thresholds('rtk_std_lat') if config._config else None
        lon_thresh = config.get_thresholds('rtk_std_lon') if config._config else None
        hgt_thresh = config.get_thresholds('rtk_std_hgt') if config._config else None
        lat_cut = AlertManager._parse_num(lat_thresh['levels'][0]) if lat_thresh and lat_thresh.get('levels') else 0.050
        lon_cut = AlertManager._parse_num(lon_thresh['levels'][0]) if lon_thresh and lon_thresh.get('levels') else 0.050
        hgt_cut = AlertManager._parse_num(hgt_thresh['levels'][0]) if hgt_thresh and hgt_thresh.get('levels') else 0.100

        poor_lat = [v for v in rtk_lat_vals if v > lat_cut] if lat_cut else []
        poor_lon = [v for v in rtk_lon_vals if v > lon_cut] if lon_cut else []
        poor_hgt = [v for v in rtk_hgt_vals if v > hgt_cut] if hgt_cut else []
        poor_lat_pct = (len(poor_lat) / len(rtk_lat_vals) * 100.0) if rtk_lat_vals else 0.0
        poor_lon_pct = (len(poor_lon) / len(rtk_lon_vals) * 100.0) if rtk_lon_vals else 0.0
        poor_hgt_pct = (len(poor_hgt) / len(rtk_hgt_vals) * 100.0) if rtk_hgt_vals else 0.0

        # Alerta combinado: se algum dos 3 componentes estiver degradado
        any_poor_rtk = (rtk_lat_vals and poor_lat_pct > AlertManager.RTK_STD_LAT_CRITICAL_PCT) or \
                       (rtk_lon_vals and poor_lon_pct > AlertManager.RTK_STD_LAT_CRITICAL_PCT) or \
                       (rtk_hgt_vals and poor_hgt_pct > AlertManager.RTK_STD_LAT_CRITICAL_PCT)
        if any_poor_rtk:
            lat_str = f'{lat_cut:.3f}' if lat_cut else 'N/A'
            lon_str = f'{lon_cut:.3f}' if lon_cut else 'N/A'
            hgt_str = f'{hgt_cut:.3f}' if hgt_cut else 'N/A'
            max_pct = max(
                poor_lat_pct if rtk_lat_vals else 0,
                poor_lon_pct if rtk_lon_vals else 0,
                poor_hgt_pct if rtk_hgt_vals else 0
            )
            severity = AlertManager.SEVERITY_CRITICAL if max_pct > 50.0 else AlertManager.SEVERITY_ALERT

            # Montar detail com apenas os componentes que tem dados
            detail_parts = []
            if rtk_lat_vals:
                detail_parts.append(f'RtkStdLat > {lat_str}: {poor_lat_pct:.2f}%')
            if rtk_lon_vals:
                detail_parts.append(f'RtkStdLon > {lon_str}: {poor_lon_pct:.2f}%')
            if rtk_hgt_vals:
                detail_parts.append(f'RtkStdHgt > {hgt_str}: {poor_hgt_pct:.2f}%')

            total_affected = len(poor_lat) + len(poor_lon) + len(poor_hgt)
            total_counted = len(rtk_lat_vals) + len(rtk_lon_vals) + len(rtk_hgt_vals)

            alerts.append(AlertManager._make_record(
                severity=severity,
                category=AlertManager.CAT_RTK,
                title='Sinal GPS/RTK com qualidade insuficiente',
                detail=' | '.join(detail_parts),
                impact='Reduz precisao posicional e pode degradar alinhamento, georreferenciamento e qualidade final do produto.',
                action='Validar base RTK, radio/link, visibilidade GNSS e repetir trechos com altos desvios padrao.',
                affected_count=total_affected,
                total_count=total_counted,
                threshold_value=lat_cut,
            ))

        # ===================================================================
        # 10. RTK EFFECTIVE PRECISION - Precisao efetiva do RTK
        # ===================================================================
        rtk_precision_vals = []
        rtk_precision_photos: List[str] = []
        rtk_precision_flights: List[str] = []
        for r in results:
            val = AlertManager._parse_num(r.level5_values.get(MFK.RTK_EFFECTIVE_PRECISION.value) or r.values.get('rtk_effective_precision'))
            if val is None:
                val = r.get_indicator(MFK.RTK_EFFECTIVE_PRECISION.value) if hasattr(r, 'get_indicator') else None
                val = AlertManager._parse_num(val)
            if val is not None:
                rtk_precision_vals.append(val)
                if val > AlertManager.RTK_EFFECTIVE_PRECISION_ALERT:
                    rtk_precision_photos.append(r.filename)
                    rtk_precision_flights.append(r.flight_id or 'unknown')

        if rtk_precision_vals:
            rtk_prec_mean = statistics.mean(rtk_precision_vals)
            rtk_prec_max = max(rtk_precision_vals)
            rtk_prec_alert_count = len(rtk_precision_photos)
            rtk_prec_warn_count = sum(1 for v in rtk_precision_vals if v > AlertManager.RTK_EFFECTIVE_PRECISION_WARN)

            if rtk_prec_alert_count > 0 or rtk_prec_warn_count > 0:
                severity = AlertManager.SEVERITY_CRITICAL if rtk_prec_alert_count > 0 else AlertManager.SEVERITY_ALERT
                rtk_precision_flights_unique = sorted(set(rtk_precision_flights))

                detail_parts = [
                    f'RTK Effective Precision medio: {rtk_prec_mean:.4f}.',
                    f'Maximo: {rtk_prec_max:.4f}.',
                ]
                if rtk_prec_warn_count > 0:
                    detail_parts.append(f'{rtk_prec_warn_count}/{len(rtk_precision_vals)} imagens com precisao > {AlertManager.RTK_EFFECTIVE_PRECISION_WARN} (alerta).')
                if rtk_prec_alert_count > 0:
                    detail_parts.append(f'{rtk_prec_alert_count} com precisao > {AlertManager.RTK_EFFECTIVE_PRECISION_ALERT} (critico).')
                if rtk_precision_flights_unique:
                    detail_parts.append(f'Voo(s): {", ".join(rtk_precision_flights_unique)}.')

                alerts.append(AlertManager._make_record(
                    severity=severity,
                    category=AlertManager.CAT_RTK,
                    title='Precisao efetiva do RTK degradada',
                    detail=' '.join(detail_parts),
                    impact='Precisao RTK efetiva alta indica perda de qualidade posicional que compromete o georreferenciamento.',
                    action='Verificar base RTK, qualidade do link de correcao e condicoes de visibilidade GNSS.',
                    affected_count=rtk_prec_alert_count,
                    total_count=len(rtk_precision_vals),
                    threshold_value=AlertManager.RTK_EFFECTIVE_PRECISION_ALERT,
                    actual_value=rtk_prec_mean,
                    flight_ids=rtk_precision_flights_unique,
                    photos=rtk_precision_photos[:20],
                ))

        # ===================================================================
        # 11. TEMPERATURE - Sensor com temperatura elevada
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

    # ===================================================================
    # QUALITY ANALYSIS - Analise de qualidade avancada (strip, PQI, RTK)
    # ===================================================================

    IDEAL_OVERLAP_PCT = 60.0
    SPEED_RECOMMENDED_MIN_MS = 5.0
    SPEED_RECOMMENDED_MAX_MS = 10.0

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
        from . import JsonMetadataManager
        from ...core.enum import MetadataFieldKey as MFK

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
                    (sum(1 for v in s_overlap_vals if v < AlertManager.IDEAL_OVERLAP_PCT) / len(s_overlap_vals) * 100.0), 2
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
        from ..FormatUtils import FormatUtils
        from . import JsonMetadataManager
        from ...core.enum import MetadataFieldKey as MFK

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
        from ...core.enum import MetadataFieldKey as MFK

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
        from ...core.enum import MetadataFieldKey as MFK
        from ..MathUtils import MathUtils

        # Overlap
        overlap_values = AlertManager._numeric_from_flight_values(
            results, [MFK.PREDICTED_OVERLAP.value, MFK.F_OVERLAP.value, 'predicted_overlap', 'f_overlap']
        )
        overlap_below_pct = 0.0
        if overlap_values:
            overlap_below_ideal = [v for v in overlap_values if v < AlertManager.IDEAL_OVERLAP_PCT]
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
            'speed_ms_recommended': f'{AlertManager.SPEED_RECOMMENDED_MIN_MS:.0f}-{AlertManager.SPEED_RECOMMENDED_MAX_MS:.0f} m/s',
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
