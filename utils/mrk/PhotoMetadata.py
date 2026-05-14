# -*- coding: utf-8 -*-
import os
import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from ...core.config.LogUtils import LogUtils
from ...core.enum import MetadataFieldKey
from .CustomPhotosFieldsUtil import CustomPhotosFieldsUtil
from .ExifUtil import ExifUtil
from .MetadataFields import MetadataFields
from .XmpUtil import XmpUtil


class PhotoMetadata:
    """
    Orquestrador puro de metadados de fotos.

    RESPONSABILIDADE ÚNICA:
    Receber pontos (MRK ou vazios) + pasta de fotos → extrair metadados das fotos
    → fazer match por sequência → mesclar dados → retornar records enriquecidos.

    NÃO faz:
    - Field filtering (responsabilidade do VectorLayerAttributes / pipeline)
    - JSON building (responsabilidade do JsonUtil / pipeline)
    - JSON saving (responsabilidade do ExplorerUtils / pipeline)
    - Vetorização (responsabilidade do JsonVectorizationStep)
    """

    DJI_RE = re.compile(r"_(\d{4})_[A-Z]\.JPG$", re.IGNORECASE)

    # Cache de timestamps de extracao (preenchido apos enrich/extract_photos_only)
    _timestamps: Dict[str, str] = {}

    @staticmethod
    def get_timestamps() -> Dict[str, str]:
        """Retorna os timestamps capturados na ultima operacao."""
        return dict(PhotoMetadata._timestamps)

    @staticmethod
    def clear_timestamps():
        """Limpa os timestamps."""
        PhotoMetadata._timestamps = {}

    @staticmethod
    def _get_logger(tool_key: str) -> LogUtils:
        return LogUtils(tool=tool_key, class_name="PhotoMetadata")

    # ─────────────────────────────────────────────
    # API PÚBLICA
    # ─────────────────────────────────────────────

    @staticmethod
    def enrich(
        points: List[Dict[str, Any]],
        base_folder: str,
        recursive: bool = True,
        tool_key: str = "drone_coordinates",
    ) -> List[Dict[str, Any]]:
        """
        Cruza pontos MRK com metadados de fotos.

        1. Indexa fotos da pasta por sequência (0001, 0002...)
        2. Extrai EXIF + XMP + GPS de cada foto
        3. Faz match com pontos MRK por número da foto
        4. Mescla metadados das fotos com contexto MRK
        5. Calcula campos custom (CustomPhotosFieldsUtil)
        6. Retorna lista de records enriquecidos (sem JSON, sem filtro, sem save)
        """
        logger = PhotoMetadata._get_logger(tool_key)

        logger.info(
            "Iniciando enrich de metadados",
            data={
                "base_folder": base_folder,
                "recursive": recursive,
                "total_points": len(points),
            },
        )

        # Timestamps: inicio da extracao de metadados das fotos (EXIF + XMP)
        exif_start = datetime.now().isoformat()

        # Indexa fotos da pasta (chama _extract_photo_payload que faz EXIF + XMP)
        photo_index = PhotoMetadata._index_photos(base_folder, recursive, tool_key)

        # Timestamps: fim da extracao de metadados (EXIF + XMP)
        xmp_end = datetime.now().isoformat()

        # Indexa contexto MRK por sequência
        mrk_by_seq = PhotoMetadata._build_mrk_context_by_sequence(points)

        # Para cada ponto MRK, busca foto correspondente e mescla
        all_records = []
        total_found = 0
        total_missing = 0

        for point in points:
            foto = point.get("foto")
            if foto is None:
                continue

            seq = f"{int(foto):04d}"

            # Tenta busca por chave composta: mrk_folder_rel (relativo a base_folder)::seq
            mrk_folder_abs = str(point.get("MrkFolder") or point.get("mrk_folder") or "").strip()
            if mrk_folder_abs:
                # Normaliza o caminho para relativo ao base_folder
                mrk_folder_rel = os.path.relpath(mrk_folder_abs, base_folder).replace("\\", "/")
                composite_key = f"{mrk_folder_rel}::{seq}"
                photo_payload = photo_index.get(composite_key)
            else:
                photo_payload = None

            # Fallback: busca por sequencia simples (legado)
            if not photo_payload:
                photo_payload = photo_index.get(seq)

            if not photo_payload:
                total_missing += 1
                continue

            total_found += 1

            # Mescla payload da foto com contexto MRK
            merged = dict(photo_payload)
            merged.update(PhotoMetadata._extract_flight_context(point))

            # Normaliza tudo para chaves canônicas
            merged = MetadataFields.normalize_record_to_keys(merged)

            # Resolve posição GPS
            lat, lon, alt, coord_source = PhotoMetadata._extract_position(merged)
            merged[MetadataFieldKey.GPS_LATITUDE.value] = lat
            merged[MetadataFieldKey.GPS_LONGITUDE.value] = lon
            merged[MetadataFieldKey.ABSOLUTE_ALTITUDE.value] = alt or merged.get(
                MetadataFieldKey.ABSOLUTE_ALTITUDE.value
            )
            merged[MetadataFieldKey.COORD_SOURCE.value] = coord_source
            merged[MetadataFieldKey.QUALITY_FLAG.value] = "OK" if coord_source != "NONE" else "LOW"

            # Detecta XMP
            has_xmp = any(
                k in merged
                for k in [
                    MetadataFieldKey.ABSOLUTE_ALTITUDE.value,
                    MetadataFieldKey.RELATIVE_ALTITUDE.value,
                    MetadataFieldKey.GIMBAL_YAW_DEGREE.value,
                    MetadataFieldKey.RTK_FLAG.value,
                ]
            )
            merged["HasXmp"] = has_xmp
            merged["HasExifGps"] = bool(lat is not None and lon is not None)

            all_records.append(merged)

        # Timestamps: inicio calculo campos custom
        custom_start = datetime.now().isoformat()

        # Calcula campos custom em lote
        try:
            custom_ready = {
                r.get(MetadataFieldKey.FILE.value): r
                for r in all_records
                if r.get(MetadataFieldKey.DATE_TIME_ORIGINAL.value) not in (None, "")
            }
            if custom_ready:
                enriched = CustomPhotosFieldsUtil.calculate_all_custom_fields(
                    custom_ready, tool_key=tool_key
                )
                for fname, custom_values in enriched.items():
                    for record in all_records:
                        if record.get(MetadataFieldKey.FILE.value) == fname:
                            record.update(custom_values)
                            break
        except Exception as exc:
            logger.warning(f"Falha ao calcular campos custom no enrich: {exc}")

        # Timestamps: fim calculo campos custom
        custom_end = datetime.now().isoformat()

        logger.info(
            "Enrich concluido",
            data={
                "total_points": len(points),
                "matched": total_found,
                "not_found": total_missing,
            },
        )

        # Armazena timestamps para consumo externo
        PhotoMetadata._timestamps = {
            "exif_start": exif_start,
            "exif_xmp_end": xmp_end,
            "custom_start": custom_start,
            "custom_end": custom_end,
        }

        return all_records

    @staticmethod
    def extract_photos_only(
        base_folder: str,
        recursive: bool = True,
        tool_key: str = "drone_coordinates",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Extrai metadados de fotos SEM pontos MRK (modo photo_only).

        Retorna (records, quality_stats).
        """
        logger = PhotoMetadata._get_logger(tool_key)

        # Timestamps: inicio extracao EXIF + XMP
        exif_start = datetime.now().isoformat()

        photo_index = PhotoMetadata._index_photos(base_folder, recursive, tool_key)

        # Timestamps: fim extracao EXIF + XMP
        xmp_end = datetime.now().isoformat()

        # Extrai o indice simples por sequencia do photo_index composto
        seq_only = photo_index.pop("__seq_only__", {})
        if not seq_only:
            # Fallback: se nao tem __seq_only__, usa o proprio photo_index
            seq_only = photo_index

        all_records = []
        quality = {
            "total_files": len(seq_only),
            "with_coords": 0,
            "without_coords": 0,
            "with_xmp": 0,
            "with_exif_gps": 0,
            "missing_xmp_and_exif": 0,
        }

        for seq, payload in seq_only.items():
            if not payload:
                continue

            merged = MetadataFields.normalize_record_to_keys(payload)

            lat, lon, alt, coord_source = PhotoMetadata._extract_position(merged)
            merged[MetadataFieldKey.GPS_LATITUDE.value] = lat
            merged[MetadataFieldKey.GPS_LONGITUDE.value] = lon
            merged[MetadataFieldKey.ABSOLUTE_ALTITUDE.value] = alt or merged.get(
                MetadataFieldKey.ABSOLUTE_ALTITUDE.value
            )
            merged[MetadataFieldKey.COORD_SOURCE.value] = coord_source
            merged[MetadataFieldKey.QUALITY_FLAG.value] = "OK" if coord_source != "NONE" else "LOW"

            has_xmp = any(
                k in merged
                for k in [
                    MetadataFieldKey.ABSOLUTE_ALTITUDE.value,
                    MetadataFieldKey.RELATIVE_ALTITUDE.value,
                    MetadataFieldKey.GIMBAL_YAW_DEGREE.value,
                    MetadataFieldKey.RTK_FLAG.value,
                ]
            )
            has_exif_gps = bool(lat is not None and lon is not None)

            merged["HasXmp"] = has_xmp
            merged["HasExifGps"] = has_exif_gps

            if coord_source == "NONE":
                quality["without_coords"] += 1
                if not has_xmp and not has_exif_gps:
                    quality["missing_xmp_and_exif"] += 1
            else:
                quality["with_coords"] += 1
            if has_xmp:
                quality["with_xmp"] += 1
            if has_exif_gps:
                quality["with_exif_gps"] += 1

            all_records.append(merged)

        # Timestamps: inicio calculo campos custom
        custom_start = datetime.now().isoformat()

        # Campos custom em lote
        try:
            custom_ready = {
                r.get(MetadataFieldKey.FILE.value): r
                for r in all_records
                if r.get(MetadataFieldKey.DATE_TIME_ORIGINAL.value) not in (None, "")
            }
            if custom_ready:
                enriched = CustomPhotosFieldsUtil.calculate_all_custom_fields(
                    custom_ready, tool_key=tool_key
                )
                for fname, custom_values in enriched.items():
                    for record in all_records:
                        if record.get(MetadataFieldKey.FILE.value) == fname:
                            record.update(custom_values)
                            break
        except Exception as exc:
            logger.warning(f"Falha ao calcular campos custom: {exc}")

        # Timestamps: fim calculo campos custom
        custom_end = datetime.now().isoformat()

        logger.info(
            "Extracao de fotos concluida",
            data={"total": len(all_records), "quality": quality},
        )

        # Armazena timestamps para consumo externo
        PhotoMetadata._timestamps = {
            "exif_start": exif_start,
            "exif_xmp_end": xmp_end,
            "custom_start": custom_start,
            "custom_end": custom_end,
        }

        return all_records, quality

    # ─────────────────────────────────────────────
    # MÉTODOS INTERNOS
    # ─────────────────────────────────────────────

    @staticmethod
    def _extract_photo_payload(image_path: str, tool_key: str) -> dict:
        """Extrai metadados completos de uma foto (OS + PIL + EXIF + XMP + aliases)."""
        logger = PhotoMetadata._get_logger(tool_key)

        payload = {}
        payload.update(ExifUtil.extract_metadata_os(image_path, tool_key=tool_key))
        payload.update(ExifUtil.extract_metadata_image(image_path, tool_key=tool_key))
        payload.update(ExifUtil.extract_metadata_exif(image_path, tool_key=tool_key))
        payload.update(XmpUtil.extract_metadata(image_path, tool_key=tool_key))

        # Aliases DJI para compatibilidade
        alias_map = {
            "drone-dji:AbsoluteAltitude": "AbsoluteAltitude",
            "drone-dji:RelativeAltitude": "RelativeAltitude",
            "drone-dji:GimbalRollDegree": "GimbalRollDegree",
            "drone-dji:GimbalYawDegree": "GimbalYawDegree",
            "drone-dji:GimbalPitchDegree": "GimbalPitchDegree",
            "drone-dji:FlightRollDegree": "FlightRollDegree",
            "drone-dji:FlightYawDegree": "FlightYawDegree",
            "drone-dji:FlightPitchDegree": "FlightPitchDegree",
            "drone-dji:FlightXSpeed": "FlightXSpeed",
            "drone-dji:FlightYSpeed": "FlightYSpeed",
            "drone-dji:FlightZSpeed": "FlightZSpeed",
            "drone-dji:RtkFlag": "RtkFlag",
            "drone-dji:RtkStdLon": "RtkStdLon",
            "drone-dji:RtkStdLat": "RtkStdLat",
            "drone-dji:RtkStdHgt": "RtkStdHgt",
            "drone-dji:RtkDiffAge": "RtkDiffAge",
            "drone-dji:DewarpFlag": "DewarpFlag",
            "drone-dji:ShutterCount": "ShutterCount",
            "drone-dji:DroneModel": "DroneModel",
            "drone-dji:DroneSerialNumber": "DroneSerialNumber",
            "drone-dji:CameraSerialNumber": "CameraSerialNumber",
            "drone-dji:CaptureUUID": "CaptureUUID",
            "drone-dji:UTCAtExposure": "UTCAtExposure",
            "drone-dji:SensorTemperature": "SensorTemperature",
            "drone-dji:LensTemperature": "LensTemperature",
            "drone-dji:WhiteBalanceCCT": "WhiteBalanceCCT",
            "drone-dji:GpsStatus": "GpsStatus",
            "drone-dji:GpsLatitude": "GpsLatitude",
            "drone-dji:GpsLongitude": "GpsLongitude",
        }
        for src_key, tgt_key in alias_map.items():
            if tgt_key not in payload and src_key in payload:
                payload[tgt_key] = payload.get(src_key)

        payload["FileType"] = os.path.splitext(image_path)[1].upper()

        # Datetime
        dt = PhotoMetadata._safe_parse_datetime(
            payload.get("DateTimeOriginal")
            or payload.get("DateTime")
            or payload.get("UTCAtExposure")
        )
        if dt is not None:
            if payload.get("DateTimeOriginal") in (None, "", "None", "null"):
                payload["DateTimeOriginal"] = dt.strftime("%Y:%m:%d %H:%M:%S")

        return payload

    @staticmethod
    def _index_photos(
        base_folder: str, recursive: bool, tool_key: str
    ) -> Dict[str, dict]:
        """
        Indexa fotos de uma pasta por chave combinada (pasta_relativa::sequencia).
        Ex: "DJI_202605101003_001_IRIA01::0001".
        Isso permite múltiplos voos com a mesma sequência 0001 em subpastas diferentes.
        Retorna {key_composite: payload_merged}.
        Também cria "__seq_only__" com índice simples por sequência para modo photo_only.
        """
        logger = PhotoMetadata._get_logger(tool_key)
        photo_files = []

        walker = os.walk(base_folder) if recursive else [(base_folder, [], os.listdir(base_folder))]
        for root, _, files in walker:
            for fname in files:
                if not fname.lower().endswith(".jpg"):
                    continue
                match = PhotoMetadata.DJI_RE.search(fname)
                if not match:
                    continue
                # Chave composta: pasta_relativa::sequencia
                rel_folder = os.path.relpath(root, base_folder).replace("\\", "/")
                composite_key = f"{rel_folder}::{match.group(1)}"
                photo_files.append((composite_key, os.path.join(root, fname)))

        indexed = {}
        for composite_key, file_path in photo_files:
            if composite_key not in indexed:
                indexed[composite_key] = PhotoMetadata._extract_photo_payload(file_path, tool_key)

        # Indice simples por sequencia (para modo photo_only)
        seq_only_index = {}
        for composite_key, file_path in photo_files:
            seq = composite_key.split("::", 1)[-1]
            if seq not in seq_only_index:
                seq_only_index[seq] = (
                    indexed[composite_key]
                    if composite_key in indexed
                    else PhotoMetadata._extract_photo_payload(file_path, tool_key)
                )

        indexed["__seq_only__"] = seq_only_index

        logger.info(
            "Fotos indexadas",
            data={
                "base_folder": base_folder,
                "total_composite": len(indexed) - 1,  # exclui __seq_only__
                "files_scanned": len(photo_files),
                "unique_seqs": len(seq_only_index),
            },
        )

        return indexed

    @staticmethod
    def _build_mrk_context_by_sequence(points: List[Dict]) -> Dict[str, Dict]:
        """Indexa contexto MRK por sequência de foto."""
        index = {}
        for point in points or []:
            foto = point.get("foto")
            if foto is None:
                continue
            try:
                seq = f"{int(foto):04d}"
            except Exception:
                continue
            if seq not in index:
                canonical = MetadataFields.normalize_record_to_keys(point)
                index[seq] = canonical
        return index

    @staticmethod
    def _extract_flight_context(point: dict) -> dict:
        """Extrai contexto de voo de um ponto MRK."""
        canonical = MetadataFields.normalize_record_to_keys(point or {})
        return {
            MetadataFieldKey.FLIGHT_NUMBER.value: canonical.get(MetadataFieldKey.FLIGHT_NUMBER.value),
            MetadataFieldKey.FLIGHT_NAME.value: canonical.get(MetadataFieldKey.FLIGHT_NAME.value),
            MetadataFieldKey.FOLDER_LEVEL_1.value: canonical.get(MetadataFieldKey.FOLDER_LEVEL_1.value),
            MetadataFieldKey.FOLDER_LEVEL_2.value: canonical.get(MetadataFieldKey.FOLDER_LEVEL_2.value),
            MetadataFieldKey.MRK_FILE.value: canonical.get(MetadataFieldKey.MRK_FILE.value),
            MetadataFieldKey.MRK_PATH.value: canonical.get(MetadataFieldKey.MRK_PATH.value),
            MetadataFieldKey.MRK_FOLDER.value: canonical.get(MetadataFieldKey.MRK_FOLDER.value),
            MetadataFieldKey.DATE_NAME.value: canonical.get(MetadataFieldKey.DATE_NAME.value),
            MetadataFieldKey.FOTO.value: canonical.get(MetadataFieldKey.FOTO.value),
            MetadataFieldKey.LAT.value: canonical.get(MetadataFieldKey.LAT.value),
            MetadataFieldKey.LON.value: canonical.get(MetadataFieldKey.LON.value),
            MetadataFieldKey.ALT.value: canonical.get(MetadataFieldKey.ALT.value),
        }

    # ─────────────────────────────────────────────
    # UTILITÁRIOS
    # ─────────────────────────────────────────────

    @staticmethod
    def _extract_position(merged_payload: dict) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
        """Extrai posição GPS do payload mesclado. Retorna (lat, lon, alt, source)."""
        canonical = MetadataFields.normalize_record_to_keys(merged_payload or {})
        lat = PhotoMetadata._to_float(canonical.get(MetadataFieldKey.GPS_LATITUDE.value))
        lon = PhotoMetadata._to_float(canonical.get(MetadataFieldKey.GPS_LONGITUDE.value))
        if lat is not None and lon is not None:
            alt = PhotoMetadata._to_float(
                canonical.get(MetadataFieldKey.ABSOLUTE_ALTITUDE.value)
                or canonical.get("GPSAltitude")
            )
            has_dji = any("drone-dji:" in str(k) for k in (merged_payload or {}).keys())
            return lat, lon, alt, "XMP" if has_dji else "EXIF"

        lat = PhotoMetadata._extract_gps_decimal_from_dms(
            merged_payload.get("GPSLatitude"),
            merged_payload.get("GPSLatitudeRef"),
        )
        lon = PhotoMetadata._extract_gps_decimal_from_dms(
            merged_payload.get("GPSLongitude"),
            merged_payload.get("GPSLongitudeRef"),
        )
        alt = PhotoMetadata._to_float(merged_payload.get("GPSAltitude"))
        if lat is not None and lon is not None:
            return lat, lon, alt, "EXIF"

        return None, None, None, "NONE"

    @staticmethod
    def _extract_gps_decimal_from_dms(value, ref):
        """Converte GPS DMS para decimal."""
        if value is None:
            return None
        parts = list(value) if isinstance(value, (list, tuple)) else None
        if not parts or len(parts) < 3:
            return None

        def _part_to_float(p):
            if isinstance(p, (int, float)):
                return float(p)
            text = str(p).strip()
            if "/" in text:
                num, den = text.split("/", 1)
                return float(num) / float(den) if float(den) != 0 else 0.0
            return float(text)

        try:
            deg = _part_to_float(parts[0])
            minute = _part_to_float(parts[1])
            sec = _part_to_float(parts[2])
            dec = deg + (minute / 60.0) + (sec / 3600.0)
            ref_txt = str(ref or "").strip().upper()
            if ref_txt in ("S", "W"):
                dec = -dec
            return dec
        except Exception:
            return None

    @staticmethod
    def _to_float(value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace("+", "")
        if text in ("", "None", "null"):
            return None
        try:
            return float(text)
        except Exception:
            return None

    @staticmethod
    def _safe_parse_datetime(value):
        if not value:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            pass
        formats = [
            "%Y:%m:%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y%m%d%H%M",
            "%Y%m%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(str(raw), fmt)
            except Exception:
                pass
        return None