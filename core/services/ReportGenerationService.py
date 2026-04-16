# -*- coding: utf-8 -*-
from typing import Dict, Any, List

from ..config.LogUtils import LogUtils
from ...utils.ExplorerUtils import ExplorerUtils
from ...utils.ToolKeys import ToolKey
from ...utils.report.AggregateAnalyzer import AggregateAnalyzer
from ...utils.report.IMGMetadata import IMGMetadata
from ...utils.report.JSONUtil import JSONUtil
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

        range_metadata_manager.load(tool_key=self.tool_key)
        records = JSONUtil.load_records(json_path=json_path, tool_key=self.tool_key)
        results: List[IMGMetadata] = [IMGMetadata(record).score() for record in records]

        agg = AggregateAnalyzer.analyze(results)
        engine = RenderEngine(tool_key=self.tool_key)
        charts = engine.generate_charts(agg)
        map_data = engine.generate_map_data(results)

        html = engine.render_report(
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
        engine.save_report(html, target_path)

        payload = {
            "json_path": json_path,
            "html_path": target_path,
            "total_records": len(records),
            "total_scored": len(results),
        }
        self.logger.info(f"Report gerado com sucesso: {payload}")
        return payload
