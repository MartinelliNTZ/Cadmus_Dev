# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime

from qgis.PyQt.QtCore import QVariant

from ...core.config.LogUtils import LogUtils
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
            "FlightNumber": canonical_point.get("FlightNumber"),
            "FlightName": canonical_point.get("FlightName"),
            "FolderLevel1": canonical_point.get("FolderLevel1"),
            "FolderLevel2": canonical_point.get("FolderLevel2"),
            "MrkFile": canonical_point.get("MrkFile"),
            "MrkPath": canonical_point.get("MrkPath"),
            "MrkFolder": canonical_point.get("MrkFolder"),
            "DateName": canonical_point.get("DateName"),
            "Foto": canonical_point.get("Foto"),
            "Lat": canonical_point.get("Lat"),
            "Lon": canonical_point.get("Lon"),
            "Alt": canonical_point.get("Alt"),
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

        # Mapeamento direto: valor enum -> chave enum (ex: "GPSMapDatum" -> MetadataFieldKey.GPS_MAP_DATUM)
        from ...core.enum import MetadataFieldKey as MFK
        enum_value_to_key = {key.value: key for key in MFK}

        for source_key, source_val in list(payload.items()):
            source_str = str(source_key)
            # Tenta encontrar a chave enum correspondente ao valor
            target_key = enum_value_to_key.get(source_str)
            if target_key and target_key not in payload:
                payload[target_key] = source_val

        canonical_payload = MetadataFields.normalize_record_to_keys(payload)
        light_source_label = PhotoMetadata._translate_light_source_value(
            canonical_payload.get("LightSource"),
            logger=logger,
            image_path=image_path,
        )
        if light_source_label:
            payload["LightSourceClassification"] = light_source_label

        # Campos solicitados no novo padrao
        payload["FileType"] = os.path.splitext(image_path)[1].upper()

        # dt_* deve priorizar metadado da foto (DateTimeOriginal), com fallback para DateTime (OS).
        dt = PhotoMetadata._safe_parse_datetime(payload.get("DateTimeOriginal"))
        if dt is None:
            dt = PhotoMetadata._safe_parse_datetime(payload.get("DateTime"))
        if dt is None:
            dt = PhotoMetadata._safe_parse_datetime(payload.get("UTCAtExposure"))
        if dt is None:
            dt = PhotoMetadata._safe_parse_datetime(payload.get("DtFull"))
        if dt is not None:
            payload.update(PhotoMetadata._format_dates(dt))
            if payload.get("DateTimeOriginal") in (None, "", "None", "null"):
                payload["DateTimeOriginal"] = dt.strftime("%Y:%m:%d %H:%M:%S")
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
            light_source_code = canonical_payload.get("LightSource")
            light_source_label = canonical_payload.get("LightSourceClassification")
            if light_source_code in (None, "", "None", "null"):
                missing_light_source += 1
            elif light_source_label in (None, "", "None", "null"):
                untranslated_light_source += 1
            else:
                translated_light_source += 1

        # Tenta enriquecer com campos custom quando o dataset possui base minima.
        try:
            required_for_custom = [
                "DateTimeOriginal",
                "AbsoluteAltitude",
                "FlightXSpeed",
                "FlightYSpeed",
                "FlightZSpeed",
                "GimbalYawDegree",
                "FlightYawDegree",
                "GimbalPitchDegree",
                "FlightPitchDegree",
            ]
            missing_summary = {}
            for _, payload in raw_by_file.items():
                for req_key in required_for_custom:
                    if payload.get(req_key) in (None, ""):
                        missing_summary[req_key] = missing_summary.get(req_key, 0) + 1
            if missing_summary:
                logger.debug(
                    "Campos ausentes antes do calculo custom",
                    data={"missing_summary": missing_summary},
                )

            custom_enriched = CustomPhotosFieldsUtil.calculate_all_custom_fields(
                raw_by_file,
                tool_key=tool_key,
            )
            raw_by_file = custom_enriched
            for fname, payload in custom_enriched.items():
                seq_match = PhotoMetadata.DJI_RE.search(fname)
                if not seq_match:
                    continue
                indexed_by_number[seq_match.group(1)] = payload
        except Exception as exc:
            logger.warning(
                f"Falha ao calcular CUSTOM_FIELDS para pasta {base_folder}: {exc}"
            )

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
        logger = PhotoMetadata._get_logger(TOOL_KEY)
        selected_keys = PhotoMetadata._build_selected_keys(
            selected_required_fields=selected_required_fields,
            selected_custom_fields=selected_custom_fields,
            selected_mrk_fields=selected_mrk_fields,
        )
        if "LightSource" in selected_keys and "LightSourceClassification" not in selected_keys:
            selected_keys.add("LightSourceClassification")
            logger.info(
                "Dependencia de campo aplicada para LightSource",
                code="LIGHT_SOURCE_DEPENDENCY_APPLIED",
                data={
                    "added_key": "LightSourceClassification",
                    "reason": "LightSource selecionado sem campo textual",
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
                "has_light_source_key": "LightSource" in selected_keys,
                "has_light_source_text_key": "LightSourceClassification" in selected_keys,
            },
        )

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

        full_dump_payload = {
            "base_folder": base_folder,
            "recursive": recursive,
            "points_total": len(points),
            "groups": {},
        }

        total_found = 0
        total_missing = 0

        for folder, folder_points in points_by_folder.items():
            photo_index, raw_records = PhotoMetadata._index_photos_complete(
                folder,
                recursive=False,
                tool_key=TOOL_KEY,
            )
            mrk_by_seq = PhotoMetadata._build_mrk_context_by_sequence(folder_points)
            raw_records = PhotoMetadata._merge_mrk_into_dump_records(raw_records, mrk_by_seq)

            full_dump_payload["groups"][folder] = {
                "points": len(folder_points),
                "indexed": len(photo_index),
                "raw_records": raw_records,
            }
            first_record = next(iter(raw_records.values()), None) if raw_records else None
            sample_keys = sorted(list(first_record.keys()))[:40] if first_record else []
            logger.debug(
                "Grupo indexado",
                data={
                    "folder": folder,
                    "points_count": len(folder_points),
                    "indexed_count": len(photo_index),
                    "mrk_indexed_count": len(mrk_by_seq),
                    "sample_keys": sample_keys,
                },
            )

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
                # antes do filtro para nao perder campos custom apos mudanca de nomenclatura.
                merged_payload = MetadataFields.normalize_record_to_keys(merged_payload)

                filtered_payload = PhotoMetadata._filter_payload(merged_payload, selected_keys)
                if selected_keys and not filtered_payload:
                    empty_filtered += 1
                point.update(filtered_payload)

            if selected_keys:
                logger.info(
                    "Resumo filtro grupo",
                    data={
                        "folder": folder,
                        "selected_keys_count": len(selected_keys),
                        "points_without_filtered_fields": empty_filtered,
                    },
                )

        dump_path = ExplorerUtils.create_temp_json(
            full_dump_payload,
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
                "json_dump_path": dump_path,
            },
        )

        if return_report:
            return {
                "points": points,
                "json_dump_path": dump_path,
                "matched": total_found,
                "not_found": total_missing,
                "total_points": len(points),
            }
        return points
