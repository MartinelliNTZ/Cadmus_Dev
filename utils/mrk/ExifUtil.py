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
    def _dms_to_decimal(dms_tuple, ref):
        """
        Converte tupla DMS (graus, minutos, segundos) para decimal com sinal.

        Args:
            dms_tuple: Tupla/list com 3 valores (graus, minutos, segundos)
            ref: Referencia 'N'/'S' para latitude ou 'E'/'W' para longitude

        Returns:
            float: Valor decimal com sinal (negativo para S/W), ou None se invalido
        """
        if dms_tuple is None:
            return None
        try:
            parts = list(dms_tuple)
            if len(parts) < 3:
                return None

            def _to_float(p):
                if isinstance(p, (int, float)):
                    return float(p)
                text = str(p).strip()
                if "/" in text:
                    num, den = text.split("/", 1)
                    return float(num) / float(den) if float(den) != 0 else 0.0
                return float(text)

            deg = _to_float(parts[0])
            minute = _to_float(parts[1])
            sec = _to_float(parts[2])
            decimal = deg + (minute / 60.0) + (sec / 3600.0)

            ref_txt = str(ref or "").strip().upper()
            if ref_txt in ("S", "W"):
                decimal = -decimal
            return decimal
        except Exception:
            return None

    @staticmethod
    def extract_all_metadata(
        image_path: str, tool_key: str = ToolKey.UNTRACEABLE
    ) -> dict:
        """
        Extrai metadados EXIF/OS/Image em UMA ÚNICA abertura do arquivo.

        Substitui as chamadas separadas extract_metadata_exif(), extract_metadata_os()
        e extract_metadata_image() que abriam o mesmo arquivo JPG 3 vezes.

        Converte automaticamente coordenadas DMS (GPSLatitude/GPSLongitude) para
        decimal com sinal, armazenando o resultado em GpsLatitudeRef/GpsLongitudeRef.

        Campos retornados:
        - File, Path, SizeMb, DateTime (OS)
        - ExifImageWidth, ExifImageHeight, Format, DPIWidth, DPIHeight (Image)
        - GpsLatitude, GpsLatitudeRef, GpsLongitude, GpsLongitudeRef, ISO, etc. (EXIF)

        Apenas campos autorizados em MetadataFields sao retornados.
        """
        logger = ExifUtil._get_logger(tool_key)
        data = {}
        try:
            # OS metadata (stat, sem abrir arquivo)
            stat = os.stat(image_path)
            data["File"] = os.path.basename(image_path)
            data["Path"] = image_path
            data["SizeMb"] = round(stat.st_size / (1024 * 1024), 2)
            data["DateTime"] = datetime.fromtimestamp(stat.st_ctime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # Abre a imagem UMA ÚNICA vez para EXIF + Image metadata
            with Image.open(image_path) as img:
                # Image metadata
                data["ExifImageWidth"], data["ExifImageHeight"] = img.size
                data["Format"] = f"{img.format}_{img.mode}"
                dpi = img.info.get("dpi")
                if dpi:
                    data["DPIWidth"] = dpi[0]
                    data["DPIHeight"] = dpi[1]

                # EXIF metadata
                exif_raw = img._getexif() or {}
                exif = {ExifTags.TAGS.get(k, k): v for k, v in exif_raw.items()}

                # Expande GPSInfo para chaves individuais
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
                        data[canonical_name] = ExifUtil._to_numeric(value)
                    else:
                        logger.debug(f"Campo EXIF rejeitado (nao autorizado): {key}")

                # ── Converte DMS → decimal com sinal ──
                lat_raw = data.get("GpsLat")
                lat_ref = data.get("GpsLatRef", "")
                lon_raw = data.get("GPSLong")
                lon_ref = data.get("GpsLongRef", "")

                if isinstance(lat_raw, (list, tuple)):
                    dec_lat = ExifUtil._dms_to_decimal(lat_raw, lat_ref)
                    if dec_lat is not None:
                        data["GpsLatRef"] = dec_lat
                if isinstance(lon_raw, (list, tuple)):
                    dec_lon = ExifUtil._dms_to_decimal(lon_raw, lon_ref)
                    if dec_lon is not None:
                        data["GpsLongRef"] = dec_lon

        except Exception as exc:
            logger.warning(f"Erro ao extrair metadados de {image_path}: {exc}")

        return data

    # Mantém extract_metadata_exif como alias para compatibilidade
    extract_metadata_exif = extract_all_metadata
