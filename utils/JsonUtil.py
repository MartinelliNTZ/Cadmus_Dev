# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime
from typing import List, Dict, Any

from ..core.config.LogUtils import LogUtils


class JsonUtil:
    """
    Constrói o JSON e também é responsável por manipulação do mesmo.
    """

    @staticmethod
    def build(
        records: List[Dict[str, Any]],
        source: str,
        base_folder: str,
        tool_key: str,
        recursive: bool = False
    ) -> Dict[str, Any]:
        """
        Monta o JSON canônico v2.0 a partir de registros.

        Args:
            records: Lista de registros com chaves PascalCase
            source: "mrk" | "mrk+photo" | "photo_only"
            base_folder: Pasta base
            tool_key: Chave da ferramenta
            recursive: Se foi recursivo

        Returns:
            Dict representando o JSON v2.0
        """
        logger = LogUtils(tool=tool_key, class_name="JsonUtil")

        # Agrupar por pasta
        groups = {}
        quality = {
            "total_files": len(records),
            "with_coords": len([r for r in records if r.get("CoordSource")]),
            "without_coords": len([r for r in records if not r.get("CoordSource")]),
            "with_xmp": 0,  # Será populado no fluxo foto
            "with_exif_gps": 0,  # Será populado no fluxo foto
            "missing_xmp_and_exif": 0,  # Será populado no fluxo foto
        }

        for record in records:
            # Usar MrkFolder ou Path como chave do grupo
            folder_key = record.get("MrkFolder") or os.path.dirname(record.get("Path", ""))
            if folder_key not in groups:
                groups[folder_key] = {
                    "MrkFile": record.get("MrkFile", ""),
                    "FlightName": record.get("FlightName", ""),
                    "FlightNumber": record.get("FlightNumber", 0),
                    "points_count": 0,
                    "indexed_count": 0,
                    "records": {}
                }

            # Usar File como chave do record, ou fallback para registros MRK
            file_key = record.get("File")
            if not file_key:
                # Para registros MRK que não têm arquivo de imagem associado
                foto = record.get("Foto")
                if foto is not None:
                    file_key = f"foto_{foto}"
                else:
                    file_key = f"record_{len(groups[folder_key]['records'])}"
            groups[folder_key]["records"][file_key] = record
            groups[folder_key]["points_count"] += 1
            groups[folder_key]["indexed_count"] += 1

        json_data = {
            "schema_version": "2.0",
            "source": source,
            "tool_key": tool_key,
            "base_folder": base_folder,
            "recursive": recursive,
            "generated_at": datetime.now().isoformat(),
            "quality": quality,
            "groups": groups
        }

        logger.debug(f"Built JSON v2.0 with {len(groups)} groups and {len(records)} records")
        return json_data

    @staticmethod
    def save(json_data: Dict[str, Any], output_path: str) -> str:
        """
        Salva o JSON em disco.

        Args:
            json_data: Dados do JSON
            output_path: Caminho onde salvar

        Returns:
            Caminho do arquivo salvo
        """
        logger = LogUtils(tool=json_data.get("tool_key", "json_util"), class_name="JsonUtil")

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved JSON to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error saving JSON to {output_path}: {e}")
            raise

    @staticmethod
    def load_records(json_path: str) -> List[Dict[str, Any]]:
        """
        Carrega registros do JSON v2.0.

        Args:
            json_path: Caminho do JSON

        Returns:
            Lista plana de registros

        Raises:
            ValueError: Se schema_version != "2.0"
        """
        logger = LogUtils(tool="json_util", class_name="JsonUtil")

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            version = data.get("schema_version")
            if version != "2.0":
                raise ValueError(
                    f"JSON com schema_version='{version}' não é suportado. "
                    "Regenere o JSON usando a versão atual do plugin."
                )

            records = []
            for group in data.get("groups", {}).values():
                for record in group.get("records", {}).values():
                    records.append(record)

            logger.debug(f"Loaded {len(records)} records from {json_path}")
            return records

        except Exception as e:
            logger.error(f"Error loading records from {json_path}: {e}")
            raise