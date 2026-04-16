# -*- coding: utf-8 -*-
from typing import List, Optional, Dict, Any
import os

from .BaseTask import BaseTask
from ..config.LogUtils import LogUtils
from ...utils.mrk.MrkParser import MrkParser


class MrkParseTask(BaseTask):
    """Task para ler arquivos MRK e extrair pontos."""

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

    def _run(self) -> bool:
        if self.isCanceled():
            return False

        logger = LogUtils(tool=self.tool_key, class_name=self.__class__.__name__)
        logger.info(
            f"Iniciando leitura de MRKs (paths={self.paths}, recursive={self.recursive})"
        )

        all_points = []
        for path in self.paths:
            base = path
            points = []

            if os.path.isfile(path) and path.lower().endswith(".mrk"):
                base = os.path.dirname(path)
                points = MrkParser.parse_file(
                    path,
                    base_folder=base,
                    extra_fields=self.extra_fields,
                    tool_key=self.tool_key,
                )
                logger.info(f"Encontrados {len(points)} pontos no arquivo {path}")
            else:
                if os.path.isfile(path):
                    base = os.path.dirname(path)
                if not os.path.isdir(base):
                    continue

                points = MrkParser.parse_folder(
                    base,
                    recursive=self.recursive,
                    extra_fields=self.extra_fields,
                    tool_key=self.tool_key,
                )
                logger.info(f"Encontrados {len(points)} pontos em {base}")

            # 🔴 CRÍTICO: Rastrear pasta específica de cada ponto
            # MrkParser.parse_folder() retorna folder_name e folder_path
            # Usamos folder_path para fornecer path absoluto ao PhotoMetadata
            if points:
                for p in points:
                    # Usa path absoluto para cruzamento de metadados
                    p["mrk_folder"] = p.get("folder_path", base)
                all_points.extend(points)

        first_path = self.paths[0] if self.paths else None
        base_folder = None
        if first_path:
            base_folder = (
                os.path.dirname(first_path) if os.path.isfile(first_path) else first_path
            )

        self.result = {
            "points": all_points,
            "base_folder": base_folder,
        }
        return True
