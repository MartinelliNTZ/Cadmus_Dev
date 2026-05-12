# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime

from qgis.PyQt.QtCore import QVariant

from ...core.config.LogUtils import LogUtils
from ...core.enum import MetadataFieldKey
from ...core.enum.LightSourceEnum import LightSourceEnum
from ..ExplorerUtils import ExplorerUtils
from ..ToolKeys import ToolKey
from .CustomPhotosFieldsUtil import CustomPhotosFieldsUtil
from .ExifUtil import ExifUtil
from .MetadataFields import MetadataFields
from .XmpUtil import XmpUtil

TOOL_KEY = ToolKey.DRONE_COORDINATES


class PhotoMetadata:
    """Manager de metadata de fotos para o fluxo DroneCoordinates."""
    LAST_JSON_DUMP_PATH = None

    # Mantido para compatibilidade com chamadas existentes.
    FIELDS_PHOTO = {
        "nome_arq": QVariant.String,
        "tam_mb": QVariant.Double,
        "tipo_arq": QVariant.String,
        "dt_criacao": QVariant.String,
        "dt_full": QVariant.String,
        "dt_date": QVariant.String,
        "dt_time": QVariant.String,
        "cam_model": QVariant.String,
        "bit_depth": QVariant.Int,
        "larg_px": QVariant.Int,
        "alt_px": QVariant.Int,
        "res_h_dpi": QVariant.Double,
        "res_v_dpi": QVariant.Double,
        "focal_mm": QVariant.Double,
        "focal35mm": QVariant.Int,
        "iso": QVariant.Int,
        "abert_f": QVariant.Double,
    }

    DJI_RE = re.compile(r"_(\d{4})_[A-Z]\.JPG$", re.IGNORECASE)

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
    def _extract_gps_decimal_from_dms(value, ref):
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
                return float(num) / float(den)
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
    def _extract_position(merged_payload):
        canonical = MetadataFields.normalize_record_to_keys(merged_payload or {})
        lat = PhotoMetadata._to_float(canonical.get("GpsLatitude"))
        lon = PhotoMetadata._to_float(canonical.get("GpsLongitude"))
        if lat is not None and lon is not None:
            alt = PhotoMetadata._to_float(
                canonical.get("AbsoluteAltitude") or canonical.get("GPSAltitude")
            )
            has_dji_xmp_marker = any("drone-dji:" in str(k) for k in (merged_payload or {}).keys())
            source = "XMP" if has_dji_xmp_marker else "EXIF"
            return lat, lon, alt, source

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
        return None, None, alt, "NONE"

    @staticmethod
    def _has_xmp_data(merged_payload, canonical_payload):
        flag = str((merged_payload or {}).get("xmp_encontrado", "")).lower()
        if flag == "sim":
            return True
        if any("drone-dji:" in str(k) for k in (merged_payload or {}).keys()):
            return True
        xmp_markers = (
            MetadataFieldKey.ABSOLUTE_ALTITUDE.value,
            "RelativeAltitude",
            "GimbalYawDegree",
            "FlightYawDegree",
            "RtkFlag",
            "UTCAtExposure",
        )
        return any(canonical_payload.get(k) not in (None, "", "None", "null") for k in xmp_markers)

    @staticmethod
    def _dump_allowed_keys() -> list:
        """
        Campos permitidos no JSON de dump por foto.
        Inclui todos os campos catalogados no MetadataFields:
        EXIF + XMP + CUSTOM + MRK.
        """
        return (
            [k.value for k in MetadataFields.EXIF_FIELDS.keys()]
            + [k.value for k in MetadataFields.DJI_XMP_FIELDS.keys()]
            + [k.value for k in MetadataFields.CUSTOM_FIELDS.keys()]
            + [k.value for k in MetadataFields.MRK_FIELDS.keys()]
        )

    @staticmethod
    def _normalize_dump_records(raw_by_file: dict) -> dict:
        """
        Converte registros por arquivo para formato:
            { "ARQUIVO.JPG": {campo: valor, ...} }
        mantendo apenas campos permitidos no MetadataFields.
        """
        allowed_keys = PhotoMetadata._dump_allowed_keys()
        normalized = {}
        for fname, payload in (raw_by_file or {}).items():
            canonical_payload = MetadataFields.normalize_record_to_keys(payload or {})
            record = {}
            for key in allowed_keys:
                record[key] = canonical_payload.get(key)
            normalized[fname] = record
        return normalized

    @staticmethod
    def _extract_photo_sequence(file_name: str) -> str:
        """Extrai sequencia de 4 digitos do padrao DJI (..._0001_X.JPG)."""
        if not file_name:
            return None
        match = PhotoMetadata.DJI_RE.search(str(file_name))
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _build_mrk_context_by_sequence(folder_points: list) -> dict:
        """
        Indexa contexto MRK por sequencia de foto (0001, 0002, ...).
        """
        index = {}
        mrk_keys = [k.value for k in MetadataFields.MRK_FIELDS.keys()]
        for point in folder_points or []:
            canonical_point = MetadataFields.normalize_record_to_keys(point or {})
            foto = canonical_point.get("Foto")
            if foto is None:
                continue
            try:
                seq = f"{int(foto):04d}"
            except Exception:
                continue
            if seq in index:
                continue
            ctx = {key: canonical_point.get(key) for key in mrk_keys}
            index[seq] = ctx
        return index

    @staticmethod
    def _merge_mrk_into_dump_records(raw_records: dict, mrk_by_seq: dict) -> dict:
        """
        Mescla campos MRK no dump por arquivo, quando houver match de sequencia.
        """
        if not raw_records:
            return raw_records
        mrk_keys = [k.value for k in MetadataFields.MRK_FIELDS.keys()]
        for fname, record in raw_records.items():
            seq = PhotoMetadata._extract_photo_sequence(fname)
            if not seq:
                continue
            mrk_ctx = mrk_by_seq.get(seq)
            if not mrk_ctx:
                continue
            for key in mrk_keys:
                record[key] = mrk_ctx.get(key)
        return raw_records

    @staticmethod
    def _safe_parse_datetime(value):
        if not value:
            return None
        raw = str(value).strip()
        if not raw:
            return None

        # ISO-8601 (com/s/sem timezone e microssegundos)
        try:
            iso_raw = raw.replace("Z", "+00:00")
            return datetime.fromisoformat(iso_raw)
        except Exception:
            pass

        candidates = [
            ("%Y:%m:%d %H:%M:%S", raw),
            ("%Y-%m-%d %H:%M:%S", raw),
            ("%Y-%m-%dT%H:%M:%S", raw),
            ("%Y-%m-%dT%H:%M:%S.%f", raw),
            ("%Y-%m-%dT%H:%M:%S%z", raw),
            ("%Y-%m-%dT%H:%M:%S.%f%z", raw),
            ("%Y%m%d%H%M", raw),
            ("%Y%m%d", raw),
        ]
        for fmt, raw in candidates:
            try:
                return datetime.strptime(str(raw), fmt)
            except Exception:
                pass
        return None

    @staticmethod
    def _get_logger(tool_key: str = TOOL_KEY) -> LogUtils:
        return LogUtils(tool=tool_key, class_name="PhotoMetadata")

    @staticmethod
    def _translate_light_source_value(
        light_source_raw,
        logger: LogUtils,
        image_path: str = "",
    ) -> str:
        if light_source_raw in (None, "", "None", "null"):
            return None

        try:
            code = int(str(light_source_raw).strip())
        except Exception as exc:
            logger.error(
                "Falha ao converter LightSource para inteiro",
                code="LIGHT_SOURCE_PARSE_ERROR",
                data={
                    "image_path": image_path,
                    "light_source_raw": light_source_raw,
                    "error": str(exc),
                },
            )
            return None

        try:
            return LightSourceEnum.get_label(code)
        except Exception as exc:
            logger.error(
                "Falha ao traduzir LightSource com LightSourceEnum",
                code="LIGHT_SOURCE_TRANSLATE_ERROR",
                data={
                    "image_path": image_path,
                    "light_source_code": code,
                    "error": str(exc),
                },
            )
            return None

    @staticmethod
    def _format_dates(dt: datetime) -> dict:
        return {
            "dt_criacao": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "dt_full": dt.strftime("%Y%m%d%H%M"),
            "dt_date": dt.strftime("%Y%m%d"),
            "dt_time": dt.strftime("%H%M"),
        }

    @staticmethod
    def _extract_flight_context(point: dict) -> dict:
        canonical_point = MetadataFields.normalize_record_to_keys(point or {})
        return {
            MetadataFieldKey.FLIGHT_NUMBER.value: canonical_point.get(MetadataFieldKey.FLIGHT_NUMBER.value),
            MetadataFieldKey.FLIGHT_NAME.value: canonical_point.get(MetadataFieldKey.FLIGHT_NAME.value),
            MetadataFieldKey.FOLDER_LEVEL_1.value: canonical_point.get(MetadataFieldKey.FOLDER_LEVEL_1.value),
            MetadataFieldKey.FOLDER_LEVEL_2.value: canonical_point.get(MetadataFieldKey.FOLDER_LEVEL_2.value),
            MetadataFieldKey.MRK_FILE.value: canonical_point.get(MetadataFieldKey.MRK_FILE.value),
            MetadataFieldKey.MRK_PATH.value: canonical_point.get(MetadataFieldKey.MRK_PATH.value),
            MetadataFieldKey.MRK_FOLDER.value: canonical_point.get(MetadataFieldKey.MRK_FOLDER.value),
            MetadataFieldKey.DATE_NAME.value: canonical_point.get(MetadataFieldKey.DATE_NAME.value),
            MetadataFieldKey.FOTO.value: canonical_point.get(MetadataFieldKey.FOTO.value),
            MetadataFieldKey.LAT.value: canonical_point.get(MetadataFieldKey.LAT.value),
            MetadataFieldKey.LON.value: canonical_point.get(MetadataFieldKey.LON.value),
            MetadataFieldKey.ALT.value: canonical_point.get(MetadataFieldKey.ALT.value),
        }

    @staticmethod
    def _build_selected_keys(
        selected_required_fields=None,
        selected_custom_fields=None,
        selected_mrk_fields=None,
    ) -> set:
        selected = (
            set(selected_required_fields or [])
            | set(selected_custom_fields or [])
            | set(selected_mrk_fields or [])
        )
        known_keys = set(MetadataFields.all_fields().keys())
        return selected & known_keys

    @staticmethod
    def _filter_payload(payload: dict, selected_keys: set) -> dict:
        if not selected_keys:
            return payload
        return {key: value for key, value in payload.items() if key in selected_keys}

    @staticmethod
    def _extract_photo_payload(image_path: str, tool_key: str = TOOL_KEY) -> dict:
        logger = PhotoMetadata._get_logger(tool_key)

        os_data = ExifUtil.extract_metadata_os(image_path, tool_key=tool_key)
        image_data = ExifUtil.extract_metadata_image(image_path, tool_key=tool_key)
        exif_data = ExifUtil.extract_metadata_exif(image_path, tool_key=tool_key)
        xmp_data = XmpUtil.extract_metadata(image_path, tool_key=tool_key)

        payload = {}
        payload.update(os_data)
        payload.update(image_data)
        payload.update(exif_data)
        payload.update(xmp_data)

        # Aliases criticos para compatibilidade com campos esperados no calculo custom.
        alias_map = {
            "drone-dji:AltitudeType": "AltitudeType",
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
            "drone-dji:FocusDistance": "FocusDistance",
            "drone-dji:CameraSerialNumber": "CameraSerialNumber",
            "drone-dji:DroneSerialNumber": "DroneSerialNumber",
            "drone-dji:DroneModel": "DroneModel",
            "drone-dji:CaptureUUID": "CaptureUUID",
            "drone-dji:PictureQuality": "PictureQuality",
            "drone-dji:UTCAtExposure": "UTCAtExposure",
            "drone-dji:SensorTemperature": "SensorTemperature",
            "drone-dji:LensTemperature": "LensTemperature",
            "drone-dji:SensorFPS": "SensorFPS",
            "drone-dji:LensPosition": "LensPosition",
            "drone-dji:LRFStatus": "LRFStatus",
            "drone-dji:LRFTargetDistance": "LRFTargetDistance",
            "drone-dji:LRFTargetLon": "LRFTargetLon",
            "drone-dji:LRFTargetLat": "LRFTargetLat",
            "drone-dji:LRFTargetAlt": "LRFTargetAlt",
            "drone-dji:LRFTargetAbsAlt": "LRFTargetAbsAlt",
            "drone-dji:WhiteBalanceCCT": "WhiteBalanceCCT",
            "drone-dji:GpsStatus": "GpsStatus",
        }
        for source_key, target_key in alias_map.items():
            if target_key not in payload and source_key in payload:
                payload[target_key] = payload.get(source_key)

        canonical_payload = MetadataFields.normalize_record_to_keys(payload)
        light_source_label = PhotoMetadata._translate_light_source_value(
            canonical_payload.get(MetadataFieldKey.LIGHT_SOURCE.value),
            logger=logger,
            image_path=image_path,
        )
        if light_source_label:
            payload[MetadataFieldKey.LIGHT_SOURCE_CLASSIFICATION.value] = light_source_label

        # Campos solicitados no novo padrao
        payload["FileType"] = os.path.splitext(image_path)[1].upper()

        # dt_* deve priorizar metadado da foto (DateTimeOriginal), com fallback para DateTime (OS).
        dt = PhotoMetadata._safe_parse_datetime(payload.get(MetadataFieldKey.DATE_TIME_ORIGINAL.value))
        if dt is None:
            dt = PhotoMetadata._safe_parse_datetime(payload.get("DateTime"))
        if dt is None:
            dt = PhotoMetadata._safe_parse_datetime(payload.get(MetadataFieldKey.UTC_AT_EXPOSURE.value))
        if dt is None:
            dt = PhotoMetadata._safe_parse_datetime(payload.get(MetadataFieldKey.DT_FULL.value))
        if dt is not None:
            payload.update(PhotoMetadata._format_dates(dt))
            if payload.get(MetadataFieldKey.DATE_TIME_ORIGINAL.value) in (None, "", "None", "null"):
                payload[MetadataFieldKey.DATE_TIME_ORIGINAL.value] = dt.strftime("%Y:%m:%d %H:%M:%S")
        else:
            logger.debug(f"Falha ao obter datetime para dt_* em {image_path}")

        return payload

    @staticmethod
    def _index_photos_complete(
        base_folder: str,
        recursive: bool,
        tool_key: str = TOOL_KEY,
    ) -> tuple:
        logger = PhotoMetadata._get_logger(tool_key)

        photo_files = []
        walker = os.walk(base_folder) if recursive else [(base_folder, [], os.listdir(base_folder))]
        for root, _, files in walker:
            for fname in files:
                if not fname.lower().endswith(".jpg"):
                    continue
                if not PhotoMetadata.DJI_RE.search(fname):
                    continue
                photo_files.append(os.path.join(root, fname))

        raw_by_file = {}
        indexed_by_number = {}
        raw_dump_records = {}
        translated_light_source = 0
        missing_light_source = 0
        untranslated_light_source = 0

        for file_path in photo_files:
            fname = os.path.basename(file_path)
            seq_match = PhotoMetadata.DJI_RE.search(fname)
            if not seq_match:
                continue
            seq = seq_match.group(1)

            payload = PhotoMetadata._extract_photo_payload(file_path, tool_key=tool_key)
            raw_by_file[fname] = payload
            indexed_by_number[seq] = payload

            canonical_payload = MetadataFields.normalize_record_to_keys(payload)
            light_source_code = canonical_payload.get(MetadataFieldKey.LIGHT_SOURCE.value)
            light_source_label = canonical_payload.get(MetadataFieldKey.LIGHT_SOURCE_CLASSIFICATION.value)
            if light_source_code in (None, "", "None", "null"):
                missing_light_source += 1
            elif light_source_label in (None, "", "None", "null"):
                untranslated_light_source += 1
            else:
                translated_light_source += 1

        logger.info(
            "Indexacao completa de fotos finalizada",
            data={
                "base_folder": base_folder,
                "total_photos": len(photo_files),
                "indexed_keys": len(indexed_by_number),
                "light_source_translated": translated_light_source,
                "light_source_missing": missing_light_source,
                "light_source_untranslated": untranslated_light_source,
            },
        )
        raw_dump_records = PhotoMetadata._normalize_dump_records(raw_by_file)
        return indexed_by_number, raw_dump_records

    @staticmethod
    def enrich(
        points,
        base_folder,
        recursive=True,
        mrk_folder=None,
        selected_required_fields=None,
        selected_custom_fields=None,
        selected_mrk_fields=None,
        return_report=False,
    ):
        """
        Enriquecimento de metadados de fotos.
        Gera JSON v2.0 com source: "mrk+photo".
        Retorna caminho do JSON gerado.
        """
        from ...utils.JsonUtil import JsonUtil
        from ...core.enum import MetadataFieldKey

        logger = PhotoMetadata._get_logger(TOOL_KEY)
        selected_keys = PhotoMetadata._build_selected_keys(
            selected_required_fields=selected_required_fields,
            selected_custom_fields=selected_custom_fields,
            selected_mrk_fields=selected_mrk_fields,
        )
        if MetadataFieldKey.LIGHT_SOURCE.value in selected_keys and MetadataFieldKey.LIGHT_SOURCE_CLASSIFICATION.value not in selected_keys:
            selected_keys.add(MetadataFieldKey.LIGHT_SOURCE_CLASSIFICATION.value)
            logger.info(
                "Dependencia de campo aplicada para LightSource",
                code="LIGHT_SOURCE_DEPENDENCY_APPLIED",
                data={
                    "added_key": MetadataFieldKey.LIGHT_SOURCE_CLASSIFICATION.value,
                    "reason": f"{MetadataFieldKey.LIGHT_SOURCE.value} selecionado sem campo textual",
                },
            )

        logger.info(
            "Iniciando enriquecimento de metadados de fotos",
            code="PHOTO_ENRICH_START",
            data={
                "base_folder": base_folder,
                "recursive": recursive,
                "mrk_folder": mrk_folder,
                "total_points": len(points),
                "selected_keys_count": len(selected_keys),
                "selected_keys_sample": sorted(list(selected_keys))[:20],
                "has_light_source_key": MetadataFieldKey.LIGHT_SOURCE.value in selected_keys,
                "has_light_source_text_key": MetadataFieldKey.LIGHT_SOURCE_CLASSIFICATION.value in selected_keys,
            },
        )

        # Processar pontos e gerar registros enriquecidos
        all_records = []
        total_found = 0
        total_missing = 0

        points_by_folder = {}
        for point in points:
            folder = point.get("mrk_folder") or base_folder
            if folder and not os.path.isabs(folder) and base_folder:
                candidate = os.path.join(base_folder, folder)
                if os.path.isdir(candidate):
                    folder = candidate
            if folder and not os.path.isdir(folder) and base_folder:
                folder = base_folder
            points_by_folder.setdefault(folder, []).append(point)

        for folder, folder_points in points_by_folder.items():
            photo_index, raw_records = PhotoMetadata._index_photos_complete(
                folder,
                recursive=False,
                tool_key=TOOL_KEY,
            )
            mrk_by_seq = PhotoMetadata._build_mrk_context_by_sequence(folder_points)

            empty_filtered = 0
            for point in folder_points:
                foto = point.get("foto")
                if foto is None:
                    continue

                key = f"{int(foto):04d}"
                photo_payload = photo_index.get(key)
                if not photo_payload:
                    total_missing += 1
                    continue

                total_found += 1
                merged_payload = {}
                merged_payload.update(photo_payload)
                merged_payload.update(PhotoMetadata._extract_flight_context(point))
                # Normaliza aliases/snake_case para as chaves canonicas do MetadataFields
                merged_payload = MetadataFields.normalize_record_to_keys(merged_payload)
                has_xmp = PhotoMetadata._has_xmp_data(merged_payload, merged_payload)
                has_exif_gps = bool(merged_payload.get("GPSLatitude") and merged_payload.get("GPSLongitude"))
                lat, lon, alt, source = PhotoMetadata._extract_position(merged_payload)
                merged_payload[MetadataFieldKey.GPS_LATITUDE.value] = lat if lat is not None else merged_payload.get(MetadataFieldKey.GPS_LATITUDE.value)
                merged_payload["GpsLongitude"] = lon if lon is not None else merged_payload.get("GpsLongitude")
                merged_payload[MetadataFieldKey.ABSOLUTE_ALTITUDE.value] = (
                    alt if alt is not None else merged_payload.get(MetadataFieldKey.ABSOLUTE_ALTITUDE.value)
                )
                merged_payload["CoordSource"] = source
                merged_payload["HasXmp"] = has_xmp
                merged_payload["HasExifGps"] = has_exif_gps
                merged_payload["QualityFlag"] = "LOW" if source == "NONE" else "OK"

                # Converter para chaves PascalCase usando mapeamento explicito do catalogo.
                key_to_json_key = {
                    key: field.key.value
                    for key, field in MetadataFields.all_fields().items()
                    if field.key is not None
                }
                record = {}
                for key, value in merged_payload.items():
                    if isinstance(key, MetadataFieldKey):
                        record[key.value] = value
                        continue

                    canonical_key = MetadataFields.resolve_key(str(key))
                    mapped_key = key_to_json_key.get(canonical_key, canonical_key)
                    record[mapped_key] = value

                # Filtrar campos selecionados
                if selected_keys:
                    filtered_record = {}
                    for k, v in record.items():
                        if k in selected_keys or k in [
                            MetadataFieldKey.COORD_SOURCE.value,
                            MetadataFieldKey.QUALITY_FLAG.value,
                            "HasXmp",
                            "HasExifGps",
                        ]:
                            filtered_record[k] = v
                    if not filtered_record:
                        empty_filtered += 1
                        continue
                    record = filtered_record

                all_records.append(record)

            if selected_keys:
                logger.info(
                    "Resumo filtro grupo",
                    data={
                        "folder": folder,
                        "selected_keys_count": len(selected_keys),
                        "points_without_filtered_fields": empty_filtered,
                    },
                )

        # Calcular campos custom sobre os mesmos records JSON (PascalCase),
        # mantendo paridade com o fluxo photo_only.
        try:
            custom_ready = {
                key: value
                for key, value in zip(
                    [record.get(MetadataFieldKey.FILE.value) for record in all_records],
                    all_records,
                )
                if key and value.get(MetadataFieldKey.DATE_TIME_ORIGINAL.value) not in (None, "")
            }
            if custom_ready:
                enriched = CustomPhotosFieldsUtil.calculate_all_custom_fields(
                    custom_ready,
                    tool_key=TOOL_KEY,
                )
                for key, value in enriched.items():
                    for record in all_records:
                        if record.get(MetadataFieldKey.FILE.value) == key:
                            for custom_key, custom_value in value.items():
                                canonical_custom_key = MetadataFields.resolve_key(str(custom_key))
                                record[canonical_custom_key] = custom_value
                            break
        except Exception as exc:
            logger.warning(f"Falha ao calcular CUSTOM_FIELDS no enrich: {exc}")

        # Gerar JSON v2.0
        json_data = JsonUtil.build(
            records=all_records,
            source="mrk+photo",
            base_folder=base_folder,
            tool_key=TOOL_KEY,
            recursive=recursive
        )

        # Salvar JSON
        dump_path = ExplorerUtils.create_temp_json(
            json_data,
            tool_key=TOOL_KEY,
            prefix="DPM",
            subfolder=os.path.join(
                ExplorerUtils.REPORTS_TEMP_FOLDER,
                ExplorerUtils.REPORTS_JSON_FOLDER,
            ),
            file_stem_hint=ExplorerUtils.build_report_json_stem(
                base_folder=base_folder,
                points_total=len(points),
            ),
        )
        PhotoMetadata.LAST_JSON_DUMP_PATH = dump_path

        logger.info(
            "Enriquecimento concluido",
            code="PHOTO_ENRICH_COMPLETE",
            data={
                "total_points": len(points),
                "matched": total_found,
                "not_found": total_missing,
                "json_path": dump_path,
            },
        )

        return dump_path  # Retornar caminho do JSON em vez de points
