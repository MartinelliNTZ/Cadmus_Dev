# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Dict, Any, List

from ..config.LogUtils import LogUtils
from ...utils.ExplorerUtils import ExplorerUtils
from ...utils.ToolKeys import ToolKey
from ...utils.JsonUtil import JsonUtil
from ...utils.report.ReportPapelineManager import ReportPapelineManager
from ...utils.report.IMGMetadata import IMGMetadata
from ...utils.report.JsonMetadataManager import JsonMetadataManager
from ...utils.report.RenderEngine import RenderEngine
from ...utils.report.RangeMetadataManager import range_metadata_manager


class ReportGenerationService:
    """Servico de orquestracao para gerar relatorio HTML a partir de JSON de metadata."""

    def __init__(self, tool_key: str = ToolKey.UNTRACEABLE):
        self.tool_key = tool_key
        self.logger = LogUtils(tool=tool_key, class_name="ReportGenerationService")

    def generate_from_json(
        self,
        json_path: str,
        html_output_path: str = None,
    ) -> Dict[str, Any]:
        """Gera relatorio HTML e retorna metadados da execucao."""
        self.logger.info(f"Iniciando geracao de report a partir de: {json_path}")

        # Registra inicio da geracao do relatorio
        report_start = datetime.now().isoformat()

        range_metadata_manager.load(tool_key=self.tool_key)
        self.logger.debug("Carregando records do JSON...")
        records = JsonMetadataManager.load_records(json_path=json_path, tool_key=self.tool_key)
        self.logger.debug(f"Records carregados: {len(records)} registros. Amostra 1o registro keys: {list(records[0].keys())[:10] if records else 'VAZIO'}")
        
        self.logger.debug("Criando objetos IMGMetadata a partir dos records...")
        results: List[IMGMetadata] = []
        for i, record in enumerate(records):
            try:
                img = IMGMetadata(record).score()
                results.append(img)
            except Exception as e:
                self.logger.error(f"Erro ao processar record [{i}]: {e}, record keys={list(record.keys())[:10] if record else 'VAZIO'}")
                raise
        self.logger.debug(f"IMGMetadata criados e scored: {len(results)} objetos. flight_ids amostra: {[r.flight_id for r in results[:5]]}")

        # Carrega timestamps existentes do JSON e mescla com report_start atual
        timestamps = JsonMetadataManager.load_timestamps(json_path=json_path, tool_key=self.tool_key)
        timestamps["report_start"] = report_start
        processing_summary = JsonMetadataManager.compute_processing_summary(timestamps)

        # Carrega metadados do JSON raiz (titulo, logotipo, generated_at)
        json_meta = JsonMetadataManager.load_json_metadata(json_path=json_path, tool_key=self.tool_key)

        engine = RenderEngine(tool_key=self.tool_key)

        def _render(agg_extra: dict = None) -> str:
            """Renderiza o HTML com agg atual."""
            self.logger.debug("INICIANDO ReportPapelineManager.analyze...")
            agg = ReportPapelineManager.analyze(results)
            self.logger.debug("ReportPapelineManager.analyze CONCLUIDO. agg keys principais presentes: total_images={}, mean_overall={}".format(
                agg.get('total_images', 'N/A'), agg.get('mean_overall', 'N/A')
            ))
            agg['processing'] = processing_summary
            agg['timestamps'] = timestamps
            agg['json_meta'] = json_meta
            if agg_extra:
                agg.update(agg_extra)
            charts = engine.generate_charts(agg)
            map_data = engine.generate_map_data(results)
            return engine.render_report(
                results=results,
                agg=agg,
                charts=charts,
                map_data=map_data,
            )

        target_path = html_output_path or ExplorerUtils.build_temp_file_path(
            ExplorerUtils.REPORTS_TEMP_FOLDER,
            ExplorerUtils.REPORTS_HTML_FOLDER,
            tool_key=self.tool_key,
            prefix="report_metadata",
            extension=".html",
            file_stem_hint=ExplorerUtils.build_report_html_stem(json_path),
        )

        # Primeira renderizacao (pode ter "Relatorio" ausente ainda)
        self.logger.debug("PRIMEIRA RENDERIZACAO...")
        try:
            html = _render()
            self.logger.debug("Primeira renderizacao concluida. Salvando HTML...")
            engine.save_report(html, target_path)
            self.logger.debug(f"HTML salvo em: {target_path}")
        except Exception as e:
            self.logger.error(f"CRASH na primeira renderizacao/salvamento: {e}", code="CRASH_RENDER_1")
            import traceback
            self.logger.error(f"Traceback completo: {traceback.format_exc()}")
            raise

        # Registra fim e persiste timestamps no JSON
        report_end = datetime.now().isoformat()
        try:
            JsonUtil.update_timestamps(json_path, {
                "report_start": report_start,
                "report_end": report_end,
            })
            self.logger.debug(f"Timestamps de report salvos no JSON: {json_path}")
        except Exception as e:
            self.logger.warning(f"Nao foi possivel salvar timestamps de report no JSON: {e}")

        # Recarrega timestamps agora com report_end e re-renderiza
        self.logger.debug("SEGUNDA RENDERIZACAO (com report_end)...")
        try:
            timestamps = JsonMetadataManager.load_timestamps(json_path=json_path, tool_key=self.tool_key)
            processing_summary = JsonMetadataManager.compute_processing_summary(timestamps)
            self.logger.debug("Segunda analyze...")
            agg = ReportPapelineManager.analyze(results)
            agg['processing'] = processing_summary
            agg['timestamps'] = timestamps
            agg['json_meta'] = json_meta
            self.logger.debug("Segunda renderizacao charts...")
            charts = engine.generate_charts(agg)
            self.logger.debug("Segunda renderizacao map_data...")
            map_data = engine.generate_map_data(results)
            self.logger.debug("Segunda renderizacao template...")
            html = engine.render_report(
                results=results,
                agg=agg,
                charts=charts,
                map_data=map_data,
            )
            self.logger.debug("Segunda renderizacao save...")
            engine.save_report(html, target_path)
        except Exception as e:
            self.logger.error(f"CRASH na segunda renderizacao: {e}", code="CRASH_RENDER_2")
            import traceback
            self.logger.error(f"Traceback completo: {traceback.format_exc()}")
            raise

        payload = {
            "json_path": json_path,
            "html_path": target_path,
            "total_records": len(records),
            "total_scored": len(results),
            "report_start": report_start,
            "report_end": report_end,
        }
        self.logger.info(f"Report gerado com sucesso: {payload}")
        return payload
