# -*- coding: utf-8 -*-
from typing import List, Optional, Dict, Any
import os
import tempfile
from datetime import datetime

from .BaseTask import BaseTask
from ..config.LogUtils import LogUtils
from ...utils.mrk.MrkUtil import MrkUtil
from ...utils.JsonUtil import JsonUtil


class MrkParseTask(BaseTask):
    """Task para ler arquivos MRK e gerar JSON v2.0."""

    def __init__(
        self,
        paths: List[str],
        recursive: bool,
        extra_fields: Optional[Dict[str, Any]],
        tool_key: str,
    ):
        super().__init__("Lendo MRKs", tool_key)
        self.paths = paths
        self.recursive = recursive
        self.extra_fields = extra_fields or {}
        self.pipeline_start = None
        self.mrk_start = None
        self.mrk_end = None

    def set_pipeline_start(self, timestamp: str):
        """Define o timestamp de inicio do pipeline (setado externamente)."""
        self.pipeline_start = timestamp

    def _run(self) -> bool:
        if self.isCanceled():
            return False

        logger = LogUtils(tool=self.tool_key, class_name=self.__class__.__name__)
        logger.info(
            f"Iniciando leitura de MRKs (paths={self.paths}, recursive={self.recursive})"
        )

        # Registra inicio da extracao MRK
        self.mrk_start = datetime.now().isoformat()

        all_records = []
        for path in self.paths:
            base = path

            if os.path.isfile(path) and path.lower().endswith(".mrk"):
                base = os.path.dirname(path)
                records = MrkUtil.extract_records(path)
                logger.info(f"Encontrados {len(records)} registros no arquivo {path}")
            else:
                if os.path.isfile(path):
                    base = os.path.dirname(path)
                if not os.path.isdir(base):
                    continue

                records = MrkUtil.extract_folder(base, recursive=self.recursive)
                logger.info(f"Encontrados {len(records)} registros em {base}")

            all_records.extend(records)

        # Registra fim da extracao MRK
        self.mrk_end = datetime.now().isoformat()

        # Gera timestamps
        timestamps = {}
        if self.pipeline_start:
            timestamps["pipeline_start"] = self.pipeline_start
        timestamps["mrk_start"] = self.mrk_start
        timestamps["mrk_end"] = self.mrk_end

        # Gerar JSON v2.0
        first_path = self.paths[0] if self.paths else None
        base_folder = None
        if first_path:
            base_folder = (
                os.path.dirname(first_path) if os.path.isfile(first_path) else first_path
            )

        json_data = JsonUtil.build(
            records=all_records,
            source="mrk",
            base_folder=base_folder or "",
            tool_key=self.tool_key,
            recursive=self.recursive,
            timestamps=timestamps,
        )

        # Salvar JSON em arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_path = f.name

        JsonUtil.save(json_data, json_path)

        self.result = {
            "json_path": json_path,
            "source": "mrk",
            "base_folder": base_folder,
            "points": all_records,
            "timestamps": timestamps,
        }
        return True
