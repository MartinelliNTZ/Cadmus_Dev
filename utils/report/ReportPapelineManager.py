from typing import List, Dict, Any, Optional
from collections import defaultdict
import statistics

from .IMGMetadata import IMGMetadata
from ..FormatUtils import FormatUtils
from ..MathUtils import MathUtils
from .RangeMetadataManager import range_metadata_manager as config
from .AlertManager import AlertManager, AlertRecord
from .JsonMetadataManager import JsonMetadataManager
from .FlightAggregator import FlightAggregator
from .AggregateAnalyzer import AggregateAnalyzer
from ...core.config.LogUtils import LogUtils
from ..ToolKeys import ToolKey


class ReportPapelineManager:
    """Orquestrador central do relatorio fotogrametrico.

    O chefe nao trabalha - ele manda os outros fazerem:
    - JsonMetadataManager: Estatistico - distribuições sobre atributos
    - FlightAggregator: Agregador de voos - agrupa imagens por flight_id
    - AggregateAnalyzer: Analisador agregado - metricas, strips, tendencias, luz, etc.
    - AlertManager: Gerador de alertas + recomendacoes
    - RangeMetadataManager: Fornecedor de ranges - thresholds configurados
    - RenderEngine: Renderizador burro - so exibe

    ReportPapelineManager apenas orquestra as chamadas e monta o dict agg
    no formato esperado pelo template. Nao executa analise propria.
    """

    logger = LogUtils(tool=ToolKey.REPORT_METADATA, class_name="ReportPapelineManager")
    logger.debug("ReportPapelineManager class carregada")

    @staticmethod
    def analyze(results: List[IMGMetadata]) -> Dict[str, Any]:
        """Orquestra a agregacao completa delegando para classes especializadas.

        DELEGA TUDO:
        - Estatistica pura ao JsonMetadataManager
        - Agrupamento por voo ao FlightAggregator
        - Informacoes gerais + metricas avancadas ao AggregateAnalyzer
        - Alertas ao AlertManager
        - Recomendacoes ao AlertManager

        APENAS MONTA o dict agg no formato esperado pelo template.
        """
        if not results:
            ReportPapelineManager.logger.warning("analyze chamado com lista vazia de resultados")
            return {}

        if config._config is None:
            config.load()

        # ===================================================================
        # 1. Estatistico: JsonMetadataManager
        # ===================================================================
        ReportPapelineManager.logger.debug("DELEGANDO para JsonMetadataManager.compute_indicator_statistics...")
        try:
            indicator_stats = JsonMetadataManager.compute_indicator_statistics(results)
            ReportPapelineManager.logger.debug(
                f"JsonMetadataManager OK: {len(indicator_stats.get('per_indicator', {}))} indicadores, "
                f"{indicator_stats.get('total_images')} imagens"
            )
        except Exception as e:
            ReportPapelineManager.logger.error(f"CRASH em JsonMetadataManager.compute_indicator_statistics: {e}", code="CRASH_INDICATOR_STATS")
            raise

        # ===================================================================
        # 2. Media geral dos scores
        # ===================================================================
        overall = [r.overall_score for r in results]
        ReportPapelineManager.logger.debug(f"Overall scores: {len(overall)} valores, min={min(overall) if overall else 'N/A'}, max={max(overall) if overall else 'N/A'}")
        try:
            mean_overall = round(statistics.mean(overall), 2) if overall else 0.0
        except Exception as e:
            ReportPapelineManager.logger.error(f"CRASH ao calcular mean_overall: {e}, overall={overall[:5]}...")
            raise

        # ===================================================================
        # 3. Agregador de voos: FlightAggregator
        # ===================================================================
        ReportPapelineManager.logger.debug("DELEGANDO para FlightAggregator.aggregate...")
        try:
            flight_data = FlightAggregator.aggregate(results)
            per_flight_check = flight_data.get('per_flight', [])
            ReportPapelineManager.logger.debug(
                f"FlightAggregator OK: {len(per_flight_check)} voos, "
                f"{len(flight_data.get('temp_chart_series', []))} series temp, "
                f"{len(flight_data.get('lrf_chart_series', []))} series lrf"
            )
        except Exception as e:
            ReportPapelineManager.logger.error(f"CRASH em FlightAggregator.aggregate: {e}", code="CRASH_FLIGHT_AGG")
            raise

        # ===================================================================
        # 4. Informacoes gerais: AggregateAnalyzer
        # ===================================================================
        ReportPapelineManager.logger.debug("DELEGANDO para AggregateAnalyzer.compute_general_info...")
        try:
            general_info = AggregateAnalyzer.compute_general_info(results)
            ReportPapelineManager.logger.debug(f"AggregateAnalyzer.general_info OK: capture_start={general_info.get('capture_start')}")
        except Exception as e:
            ReportPapelineManager.logger.error(f"CRASH em AggregateAnalyzer.compute_general_info: {e}", code="CRASH_GENERAL_INFO")
            raise

        ReportPapelineManager.logger.debug("DELEGANDO para AggregateAnalyzer.compute_top_models...")
        try:
            top_models = AggregateAnalyzer.compute_top_models(results)
            ReportPapelineManager.logger.debug(f"AggregateAnalyzer.top_models OK: {len(top_models)} modelos")
        except Exception as e:
            ReportPapelineManager.logger.error(f"CRASH em AggregateAnalyzer.compute_top_models: {e}", code="CRASH_TOP_MODELS")
            raise

        ReportPapelineManager.logger.debug("DELEGANDO para AggregateAnalyzer.compute_shutter_per_camera...")
        try:
            shutter_per_camera = AggregateAnalyzer.compute_shutter_per_camera(results)
            ReportPapelineManager.logger.debug(f"AggregateAnalyzer.shutter_per_camera OK: {len(shutter_per_camera)} cameras")
        except Exception as e:
            ReportPapelineManager.logger.error(f"CRASH em AggregateAnalyzer.compute_shutter_per_camera: {e}", code="CRASH_SHUTTER")
            raise

        ReportPapelineManager.logger.debug("DELEGANDO para AggregateAnalyzer.compute_light_source_analysis...")
        try:
            light_source_analysis = AggregateAnalyzer.compute_light_source_analysis(results)
            ReportPapelineManager.logger.debug(f"AggregateAnalyzer.light_source OK: predominant={light_source_analysis.get('light_source_predominant')}")
        except Exception as e:
            ReportPapelineManager.logger.error(f"CRASH em AggregateAnalyzer.compute_light_source_analysis: {e}", code="CRASH_LIGHT_SOURCE")
            raise

        ReportPapelineManager.logger.debug("DELEGANDO para AggregateAnalyzer.compute_total_area...")
        area_ha = AggregateAnalyzer.compute_total_area(flight_data.get('per_flight', []))
        ReportPapelineManager.logger.debug(f"AggregateAnalyzer.total_area OK: {area_ha}")

        # ===================================================================
        # STATUS OPERACIONAIS (dewarp, altitude) - aqui no orquestrador
        # pois combinam general_info e dados brutos
        # ===================================================================
        dewarp_info = ReportPapelineManager._compute_dewarp_status(results)
        altitude_info = ReportPapelineManager._compute_altitude_status(results)

        general_info.update(dewarp_info)
        general_info.update(altitude_info)
        general_info['last_shutter_per_camera'] = shutter_per_camera

        # Classificacao de altitude (AGL vs Relative)
        ReportPapelineManager.logger.debug("DELEGANDO para AggregateAnalyzer.compute_altitude_classification...")
        try:
            alt_classification = AggregateAnalyzer.compute_altitude_classification(results)
            ReportPapelineManager.logger.debug(f"AggregateAnalyzer.altitude_classification OK: {alt_classification.get('altitude_classification_label')}")
        except Exception as e:
            ReportPapelineManager.logger.error(f"CRASH em AggregateAnalyzer.compute_altitude_classification: {e}", code="CRASH_ALT_CLASS")
            alt_classification = {
                'altitude_classification_label': 'Indisponivel',
                'altitude_classification_type': 'unavailable',
                'altitude_classification_rel_range': None,
                'altitude_classification_solo_range': None,
            }
        general_info.update(alt_classification)

        # Totals de voo
        per_flight = flight_data.get('per_flight', [])
        total_flights = len(per_flight)
        total_flight_seconds = sum(
            row['flight_seconds'] for row in per_flight
            if row.get('flight_seconds') is not None
        )
        general_info['total_flights'] = total_flights
        general_info['total_flight_time'] = FormatUtils.format_duration(total_flight_seconds)

        # ===================================================================
        # MONTA AGG BASE
        # ===================================================================
        agg = {
            'total_images': len(results),
            'mean_overall': mean_overall,
            'per_indicator': indicator_stats.get('per_indicator', {}),
            'level_distribution': indicator_stats.get('level_distribution', {}),
            'pqi_mean': indicator_stats.get('pqi_mean'),
            'pqi_level_distribution': indicator_stats.get('pqi_level_distribution', {}),
            'pqi_classification': indicator_stats.get('pqi_classification'),
            'indicator_catalog': indicator_stats.get('indicator_catalog', []),
            'general_info': general_info,
            'top_models': top_models,
            # Delegado ao FlightAggregator:
            'per_flight': per_flight,
            'flight_level5_columns': flight_data.get('flight_level5_columns', []),
            'temp_chart_series': flight_data.get('temp_chart_series', []),
            'lrf_chart_series': flight_data.get('lrf_chart_series', []),
            'iso_chart_series': flight_data.get('iso_chart_series', []),
            'temp_hourly_avg': flight_data.get('temp_hourly_avg', []),
            'lrf_hourly_avg': flight_data.get('lrf_hourly_avg', []),
            'iso_hourly_avg': flight_data.get('iso_hourly_avg', []),
        }

        # ===================================================================
        # 5. Metricas avancadas + tendencias + strips: AggregateAnalyzer
        # ===================================================================
        ReportPapelineManager.logger.debug("DELEGANDO para AggregateAnalyzer.compute_advanced_metrics...")
        try:
            advanced_metrics = AggregateAnalyzer.compute_advanced_metrics(results)
            ReportPapelineManager.logger.debug(f"AggregateAnalyzer.advanced_metrics OK: {len(advanced_metrics)} metricas")
        except Exception as e:
            ReportPapelineManager.logger.error(f"CRASH em AggregateAnalyzer.compute_advanced_metrics: {e}", code="CRASH_ADV_METRICS")
            raise
        advanced_metrics['estimated_area_ha'] = area_ha
        advanced_metrics['light_source_predominant'] = light_source_analysis.get('light_source_predominant')
        advanced_metrics['light_source_predominant_count'] = light_source_analysis.get('light_source_predominant_count')
        advanced_metrics['light_source_predominant_pct'] = light_source_analysis.get('light_source_predominant_pct')
        advanced_metrics['light_source_total_classified'] = light_source_analysis.get('light_source_total_classified')
        advanced_metrics['light_source_classes'] = light_source_analysis.get('light_source_classes')
        advanced_metrics['light_source_from_text'] = light_source_analysis.get('light_source_from_text')
        advanced_metrics['light_source_from_code'] = light_source_analysis.get('light_source_from_code')

        # RTK classification
        ReportPapelineManager.logger.debug("DELEGANDO para AggregateAnalyzer.compute_rtk_classification...")
        try:
            rtk_classification = AggregateAnalyzer.compute_rtk_classification(results)
            ReportPapelineManager.logger.debug(f"AggregateAnalyzer.rtk_classification OK: class={rtk_classification.get('rtk_stability_class')}")
        except Exception as e:
            ReportPapelineManager.logger.error(f"CRASH em AggregateAnalyzer.compute_rtk_classification: {e}", code="CRASH_RTK_CLASS")
            raise
        advanced_metrics['rtk_stability_mean'] = rtk_classification.get('rtk_stability_mean')
        advanced_metrics['rtk_stability_class'] = rtk_classification.get('rtk_stability_class')

        # Quality trends
        ReportPapelineManager.logger.debug("DELEGANDO para AggregateAnalyzer.compute_quality_trends...")
        try:
            quality_trends = AggregateAnalyzer.compute_quality_trends(results)
            ReportPapelineManager.logger.debug(f"AggregateAnalyzer.quality_trends OK: delta={quality_trends.get('pqi_delta')}")
        except Exception as e:
            ReportPapelineManager.logger.error(f"CRASH em AggregateAnalyzer.compute_quality_trends: {e}", code="CRASH_QUALITY_TRENDS")
            raise
        advanced_metrics['pqi_first_quartile_mean'] = quality_trends.get('pqi_first_quartile_mean')
        advanced_metrics['pqi_last_quartile_mean'] = quality_trends.get('pqi_last_quartile_mean')
        advanced_metrics['pqi_delta'] = quality_trends.get('pqi_delta')
        advanced_metrics['morning_pqi_mean'] = quality_trends.get('morning_pqi_mean')
        advanced_metrics['midday_pqi_mean'] = quality_trends.get('midday_pqi_mean')

        # Strip analysis
        ReportPapelineManager.logger.debug("DELEGANDO para AggregateAnalyzer.compute_strip_analysis...")
        try:
            strip_analysis = AggregateAnalyzer.compute_strip_analysis(results)
            ReportPapelineManager.logger.debug(f"AggregateAnalyzer.strip_analysis OK: {len(strip_analysis.get('strip_rows', []))} strips")
        except Exception as e:
            ReportPapelineManager.logger.error(f"CRASH em AggregateAnalyzer.compute_strip_analysis: {e}", code="CRASH_STRIP_ANALYSIS")
            raise

        # Recommendations (ainda no AlertManager - usa only advanced_metrics)
        ReportPapelineManager.logger.debug("DELEGANDO para AlertManager.compute_recommendations...")
        recommendations = AlertManager.compute_recommendations(advanced_metrics)
        ReportPapelineManager.logger.debug(f"AlertManager.recommendations OK: {len(recommendations)} recomendacoes")

        agg['advanced_analysis'] = {
            'critical_alerts': [],
            'metrics': advanced_metrics,
            'quality_analysis': {
                'strip_rows': strip_analysis.get('strip_rows', []),
                'problematic_strips': strip_analysis.get('problematic_strips', []),
            },
            'recommendations': recommendations,
        }

        # ===================================================================
        # 6. Alertas: AlertManager
        # ===================================================================
        ReportPapelineManager.logger.debug("DELEGANDO para AlertManager.analyze...")
        try:
            unified_alerts = AlertManager.analyze(results, agg)
            ReportPapelineManager.logger.debug(f"AlertManager.analyze OK: {len(unified_alerts)} alertas")
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

    # ===================================================================
    # METODOS OPERACIONAIS (dewarp, altitude)
    # ===================================================================
    @staticmethod
    def _compute_dewarp_status(results: List[IMGMetadata]) -> Dict[str, Any]:
        """Calcula status de dewarp para general_info."""
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

        return {
            'dewarp_zero_count': dewarp_zero_count,
            'dewarp_status_type': dewarp_status_type,
            'dewarp_status_message': dewarp_status_message,
        }

    @staticmethod
    def _compute_altitude_status(results: List[IMGMetadata]) -> Dict[str, Any]:
        """Calcula status de altitude para general_info."""
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

        return {
            'missing_altitude_count': missing_alt_count,
            'altitude_status_type': altitude_status_type,
            'altitude_status_message': altitude_status_message,
        }