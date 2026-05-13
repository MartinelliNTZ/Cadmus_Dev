# -*- coding: utf-8 -*-
"""
Utilities para extracao de metadados EXIF/OS/PIL de imagens.
"""

import os
from datetime import datetime

from PIL import ExifTags, Image

from ...core.config.LogUtils import LogUtils
from ..ToolKeys import ToolKey
from .MetadataFields import MetadataFields


class ExifUtil:
    """Utilitario para extrair metadados de arquivo de imagem."""

    @staticmethod
    def _get_logger(tool_key: str = ToolKey.UNTRACEABLE) -> LogUtils:
        return LogUtils(tool=tool_key, class_name="ExifUtil")

    @staticmethod
    def extract_metadata_os(
        image_path: str, tool_key: str = ToolKey.UNTRACEABLE
    ) -> dict:
        """
        Extrai metadados do sistema operacional.
        
        Retorna campos CANONICOS (legalizados em MetadataFields):
        - File: nome do arquivo (era "file")
        - Path: caminho completo (era "path")
        - SizeMb: tamanho em MB (era "size_mb")
        - DateTime: data do sistema operacional (era "os_date")
        """
        logger = ExifUtil._get_logger(tool_key)
        data = {}
        try:
            stat = os.stat(image_path)
            data["File"] = os.path.basename(image_path)
            data["Path"] = image_path
            data["SizeMb"] = round(stat.st_size / (1024 * 1024), 2)
            data["DateTime"] = datetime.fromtimestamp(stat.st_ctime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except Exception as exc:
            logger.error(
                f"Erro ao extrair metadados do sistema para {image_path}: {exc}"
            )
        return data

    @staticmethod
    def extract_metadata_image(
        image_path: str, tool_key: str = ToolKey.UNTRACEABLE
    ) -> dict:
        """
        Extrai metadados de dimensao/formato/dpi via PIL.
        
        Retorna campos CANONICOS (legalizados em MetadataFields):
        - ExifImageWidth: largura em pixels (era "width_px")
        - ExifImageHeight: altura em pixels (era "height_px")
        - Format: formato_modo (era "format")
        - DPIWidth: DPI horizontal (era "dpi")
        """
        logger = ExifUtil._get_logger(tool_key)
        data = {}
        try:
            with Image.open(image_path) as img:
                data["ExifImageWidth"], data["ExifImageHeight"] = img.size
                data["Format"] = f"{img.format}_{img.mode}"
                dpi = img.info.get("dpi")
                if dpi:
                    dpi_x, dpi_y = dpi
                    data["DPIWidth"] = dpi_x
                    data["DPIHeight"] = dpi_y
        except Exception as exc:
            logger.error(f"Erro ao extrair metadados PIL para {image_path}: {exc}")
        return data

    @staticmethod
    def _to_numeric(value):
        """
        Tenta converter valor string para int ou float.
        Mantem tipo original se ja for numerico ou se falhar.
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return value
        if not isinstance(value, str):
            return value
            
        raw = value.strip().replace("+", "")
        if not raw or raw.lower() in ("none", "null", "nan", "inf"):
            return value
        
        # Tenta int primeiro
        if "." not in raw:
            try:
                return int(raw)
            except (ValueError, TypeError):
                pass
        
        # Tenta float
        try:
            return float(raw)
        except (ValueError, TypeError):
            return value

    @staticmethod
    def extract_metadata_exif(
        image_path: str, tool_key: str = ToolKey.UNTRACEABLE
    ) -> dict:
        """
        Extrai e sanitiza campos EXIF disponiveis.
        
        Apenas campos autorizados em MetadataFields sao retornados.
        Campos nao autorizados sao descartados (log em DEBUG).
        Valores numericos em string sao convertidos para float/int.
        """
        logger = ExifUtil._get_logger(tool_key)
        data = {}
        try:
            with Image.open(image_path) as img:
                exif_raw = img._getexif() or {}
                exif = {ExifTags.TAGS.get(k, k): v for k, v in exif_raw.items()}
                
                # Expande GPSInfo para chaves individuais (GPSLatitude, GPSLongitude, GPSMapDatum, etc.).
                gps_info = exif.get("GPSInfo")
                if isinstance(gps_info, dict):
                    gps_named = {
                        ExifTags.GPSTAGS.get(k, k): v for k, v in gps_info.items()
                    }
                    for gk, gv in gps_named.items():
                        exif[gk] = gv
                
                # SANITIZA campos EXIF contra MetadataFields
                for key, value in exif.items():
                    canonical_name = MetadataFields.sanitize_field_name(str(key))
                    if canonical_name:
                        # Converte string numerica para float/int
                        data[canonical_name] = ExifUtil._to_numeric(value)
                    else:
                        # Campo nao autorizado - log em DEBUG
                        logger.debug(f"Campo EXIF rejeitado (nao autorizado): {key}")
                        
        except Exception as exc:
            logger.warning(f"Erro ao extrair EXIF de {image_path}: {exc}")
        
        return data
