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
        """Gera relatorio HTML e retorna metadados da execucao.

        Renderiza o HTML UMA ÚNICA vez, APÓS ter todos os timestamps
        completos (report_start + report_end), eliminando a re-renderização
        duplicada que consumia ~18min extras.
        
        O report_end é registrado ANTES de renderizar, assim o template
        Jinja2 já exibe o tempo total de geração do relatório corretamente.
        """
        self.logger.info(f"Iniciando geracao de report a partir de: {json_path}")

        # Registra inicio e fim da geracao do relatorio
        report_start = datetime.now().isoformat()

        range_metadata_manager.load(tool_key=self.tool_key)
        self.logger.debug("Carregando records do JSON...")
        records = JsonMetadataManager.load_records(
            json_path=json_path, tool_key=self.tool_key
        )

        self.logger.debug("Criando objetos IMGMetadata a partir dos records...")
        results: List[IMGMetadata] = []
        for i, record in enumerate(records):
            try:
                img = IMGMetadata(record).score()
                results.append(img)
            except Exception as e:
                self.logger.error(
                    f"Erro ao processar record [{i}]: {e}"
                )
                raise

        # Carrega timestamps existentes do JSON
        timestamps = JsonMetadataManager.load_timestamps(
            json_path=json_path, tool_key=self.tool_key
        )
        timestamps["report_start"] = report_start

        # Carrega metadados do JSON raiz (titulo, logotipo, generated_at)
        json_meta = JsonMetadataManager.load_json_metadata(
            json_path=json_path, tool_key=self.tool_key
        )

        engine = RenderEngine(tool_key=self.tool_key)

        target_path = html_output_path or ExplorerUtils.build_temp_file_path(
            self.tool_key,
            ExplorerUtils.REPORTS_TEMP_FOLDER,
            ExplorerUtils.REPORTS_HTML_FOLDER,
            prefix="report_metadata",
            extension=".html",
            file_stem_hint=ExplorerUtils.build_report_html_stem(json_path),
        )

        # --- TODO o processamento pesado ACIMA. Abaixo: renderização ÚNICA ---

        # Persiste report_end no JSON ANTES de renderizar
        # para que o template Jinja2 exiba o tempo de geração corretamente
        report_end = datetime.now().isoformat()
        timestamps["report_end"] = report_end
        processing_summary = JsonMetadataManager.compute_processing_summary(timestamps)
        try:
            JsonUtil.update_timestamps(
                json_path,
                {
                    "report_start": report_start,
                    "report_end": report_end,
                },
            )
            self.logger.debug(f"Timestamps de report salvos no JSON: {json_path}")
        except Exception as e:
            self.logger.warning(
                f"Nao foi possivel salvar timestamps de report no JSON: {e}"
            )

        # Renderizacao ÚNICA (com report_end real)
        self.logger.debug("RENDERIZACAO UNICA (com report_end real)...")
        try:
            agg = ReportPapelineManager.analyze(results)
            agg["processing"] = processing_summary
            agg["timestamps"] = timestamps
            agg["json_meta"] = json_meta
            charts = engine.generate_charts(agg)
            map_data = engine.generate_map_data(results)
            html = engine.render_report(
                results=results,
                agg=agg,
                charts=charts,
                map_data=map_data,
            )
            engine.save_report(html, target_path)
            self.logger.debug(f"HTML salvo em: {target_path}")
        except Exception as e:
            self.logger.error(
                f"CRASH na renderizacao: {e}", code="CRASH_RENDER"
            )
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
