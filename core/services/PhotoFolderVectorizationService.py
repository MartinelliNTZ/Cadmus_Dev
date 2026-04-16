# -*- coding: utf-8 -*-
import os
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsProject

from ..config.LogUtils import LogUtils
from .ReportGenerationService import ReportGenerationService
from ...utils.ExplorerUtils import ExplorerUtils
from ...utils.ToolKeys import ToolKey
from ...utils.mrk.ExifUtil import ExifUtil
from ...utils.mrk.MetadataFields import MetadataFields
from ...utils.mrk.CustomPhotosFieldsUtil import CustomPhotosFieldsUtil
from ...utils.mrk.XmpUtil import XmpUtil
from ...utils.vector.VectorLayerGeometry import VectorLayerGeometry


class PhotoFolderVectorizationService:
    """Gera camada vetorial e diagnostico a partir de pasta de fotos (sem MRK)."""
    DJI_PHOTO_RE = re.compile(r"_(\d{4})_[A-Z]\.JPG$", re.IGNORECASE)
    FLIGHT_FOLDER_RE = re.compile(
        r"DJI_\d+_(?P<flight_number>\d+?)_(?P<flight_name>[^_\\\/]+)",
        re.IGNORECASE,
    )

    def __init__(self, tool_key: str = ToolKey.REPORT_METADATA):
        self.tool_key = tool_key
        self.logger = LogUtils(tool=tool_key, class_name="PhotoFolderVectorizationService")

    @staticmethod
    def _to_float(value: Any):
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
    def _normalize_attr_value(value: Any) -> Any:
        """Normaliza valores para escrita segura em atributos QGIS."""
        if isinstance(value, (list, tuple, dict)):
            try:
                return json.dumps(value, ensure_ascii=False)
            except Exception:
                return str(value)
        return value

    def _build_output_record_from_catalog(self, canonical: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monta registro de saida somente com campos catalogados em MetadataFields,
        garantindo mesmo padrao de atributos do DroneCoordinates.
        """
        output_record: Dict[str, Any] = {}
        mrk_keys = set(MetadataFields.mrk_keys())
        for key in MetadataFields.all_fields().keys():
            if key in mrk_keys:
                continue
            attr_name = MetadataFields.resolve_output_name(key)
            output_record[attr_name] = self._normalize_attr_value(canonical.get(key))
        return output_record

    @staticmethod
    def _filter_out_mrk_fields(record: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(record, dict):
            return {}

        mrk_keys = set(MetadataFields.mrk_keys())
        filtered: Dict[str, Any] = {}
        for key, value in record.items():
            normalized_key = MetadataFields.resolve_key(str(key))
            if normalized_key in mrk_keys:
                continue
            filtered[key] = value
        return filtered

    @staticmethod
    def _safe_parse_datetime(value: Any) -> datetime:
        if value in (None, ""):
            return None
        text = str(value).strip()
        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except Exception:
                continue
        return None

    @staticmethod
    def _format_dates(dt: datetime) -> Dict[str, str]:
        return {
            "dt_criacao": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "dt_full": dt.strftime("%Y%m%d%H%M"),
            "dt_date": dt.strftime("%Y%m%d"),
            "dt_time": dt.strftime("%H%M"),
        }

    def _extract_photo_number(self, file_path: str) -> Any:
        fname = os.path.basename(file_path)
        match = self.DJI_PHOTO_RE.search(fname)
        if not match:
            return None
        try:
            return int(match.group(1))
        except Exception:
            return None

    def _extract_flight_context(self, file_path: str, base_folder: str) -> Dict[str, Any]:
        folder_path = os.path.dirname(file_path)
        folder_level_1 = os.path.basename(folder_path) or ""
        folder_level_2 = os.path.basename(os.path.dirname(folder_path)) or ""

        if not folder_level_1 and os.path.isdir(base_folder):
            folder_level_1 = os.path.basename(base_folder)

        return {
            "FolderLevel1": folder_level_1,
            "FolderLevel2": folder_level_2,
        }

    def _extract_photo_payload(self, image_path: str) -> Dict[str, Any]:
        """
        Extracao de metadados no mesmo padrao do fluxo DroneCoordinates.
        """
        os_data = ExifUtil.extract_metadata_os(image_path, tool_key=self.tool_key)
        image_data = ExifUtil.extract_metadata_image(image_path, tool_key=self.tool_key)
        exif_data = ExifUtil.extract_metadata_exif(image_path, tool_key=self.tool_key)
        xmp_data = XmpUtil.extract_metadata(image_path, tool_key=self.tool_key)

        payload: Dict[str, Any] = {}
        payload.update(os_data)
        payload.update(image_data)
        payload.update(exif_data)
        payload.update(xmp_data)

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
            "drone-dji:GpsLatitude": "GpsLatitude",
            "drone-dji:GpsLongitude": "GpsLongitude",
        }
        for source_key, target_key in alias_map.items():
            if target_key not in payload and source_key in payload:
                payload[target_key] = payload.get(source_key)

        payload["FileType"] = os.path.splitext(image_path)[1].upper()
        dt = self._safe_parse_datetime(
            payload.get("DateTimeOriginal") or payload.get("DateTime") or payload.get("os_date")
        )
        if dt is not None:
            payload.update(self._format_dates(dt))
            payload["DateTimeOriginal"] = dt.strftime("%Y:%m:%d %H:%M:%S")

        return payload

    @staticmethod
    def _extract_gps_decimal_from_dms(value, ref):
        if value is None:
            return None

        parts = []
        if isinstance(value, (list, tuple)):
            parts = list(value)
        else:
            return None

        if len(parts) < 3:
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
            ref_txt = str(ref or "").upper().strip()
            if ref_txt in ("S", "W"):
                dec = -dec
            return dec
        except Exception:
            return None

    def _extract_position(self, merged_payload: Dict[str, Any]) -> Tuple[Any, Any, Any, str]:
        """Retorna lat/lon/alt e fonte principal usada."""
        # Prioridade 1: XMP DJI decimal
        lat = self._to_float(merged_payload.get("drone-dji:GpsLatitude") or merged_payload.get("GpsLatitude"))
        lon = self._to_float(merged_payload.get("drone-dji:GpsLongitude") or merged_payload.get("GpsLongitude"))
        if lat is not None and lon is not None:
            alt = self._to_float(
                merged_payload.get("drone-dji:AbsoluteAltitude")
                or merged_payload.get("AbsoluteAltitude")
                or merged_payload.get("GPSAltitude")
            )
            return lat, lon, alt, "XMP"

        # Prioridade 2: EXIF DMS
        lat = self._extract_gps_decimal_from_dms(
            merged_payload.get("GPSLatitude"),
            merged_payload.get("GPSLatitudeRef"),
        )
        lon = self._extract_gps_decimal_from_dms(
            merged_payload.get("GPSLongitude"),
            merged_payload.get("GPSLongitudeRef"),
        )
        alt = self._to_float(merged_payload.get("GPSAltitude"))
        if lat is not None and lon is not None:
            return lat, lon, alt, "EXIF"

        return None, None, alt, "NONE"

    @staticmethod
    def _date_name_from_payload(payload: Dict[str, Any]) -> str:
        raw = payload.get("DateTimeOriginal") or payload.get("DateTime")
        if not raw:
            return ""
        text = str(raw).strip()
        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y%m%d")
            except Exception:
                pass
        return ""

    def _list_photo_files(self, base_folder: str, recursive: bool) -> List[str]:
        output = []
        if not os.path.isdir(base_folder):
            return output

        if recursive:
            walker = os.walk(base_folder)
            for root, _, files in walker:
                for name in files:
                    if name.lower().endswith((".jpg", ".jpeg")):
                        output.append(os.path.join(root, name))
        else:
            for name in os.listdir(base_folder):
                full_path = os.path.join(base_folder, name)
                if os.path.isfile(full_path) and name.lower().endswith((".jpg", ".jpeg")):
                    output.append(full_path)

        return sorted(output)

    def generate_from_folder(
        self,
        base_folder: str,
        recursive: bool = True,
        generate_report: bool = True,
        layer_name: str = "Fotos_Sem_MRK",
    ) -> Dict[str, Any]:
        if not os.path.isdir(base_folder):
            raise ValueError(f"Pasta invalida: {base_folder}")

        files = self._list_photo_files(base_folder, recursive)
        self.logger.info(
            "Iniciando vetorizacao por fotos sem MRK",
            data={"base_folder": base_folder, "recursive": recursive, "total_files": len(files)},
        )

        points = []
        raw_records = {}
        quality = {
            "total_files": len(files),
            "with_coords": 0,
            "without_coords": 0,
            "with_xmp": 0,
            "with_exif_gps": 0,
            "missing_xmp_and_exif": 0,
        }
        x_geom_key = MetadataFields.resolve_output_name("GpsLongitude")
        y_geom_key = MetadataFields.resolve_output_name("GpsLatitude")

        for file_path in files:
            merged = self._extract_photo_payload(file_path)

            has_xmp = str(merged.get("xmp_encontrado", "nao")).lower() == "sim"
            if has_xmp:
                quality["with_xmp"] += 1
            has_exif_gps = bool(merged.get("GPSLatitude") and merged.get("GPSLongitude"))
            if has_exif_gps:
                quality["with_exif_gps"] += 1

            lat, lon, alt, source = self._extract_position(merged)
            if source == "NONE":
                quality["without_coords"] += 1
                if (not has_xmp) and (not has_exif_gps):
                    quality["missing_xmp_and_exif"] += 1
            else:
                quality["with_coords"] += 1

            canonical = MetadataFields.normalize_record_to_keys(merged)
            canonical.update(self._extract_flight_context(file_path, base_folder))
            canonical["GpsLatitude"] = lat if lat is not None else canonical.get("GpsLatitude")
            canonical["GpsLongitude"] = lon if lon is not None else canonical.get("GpsLongitude")
            canonical["AbsoluteAltitude"] = (
                alt if alt is not None else canonical.get("AbsoluteAltitude")
            )
            canonical["CoordSource"] = source
            canonical["HasXmp"] = has_xmp
            canonical["HasExifGps"] = has_exif_gps
            canonical["QualityFlag"] = "LOW" if source == "NONE" else "OK"

            canonical = self._filter_out_mrk_fields(canonical)
            file_key = os.path.basename(file_path)
            raw_records[file_key] = canonical

        # Calcula campos custom em lote para manter paridade com DroneCoordinates.
        try:
            custom_ready = {
                key: value
                for key, value in raw_records.items()
                if value.get("DateTimeOriginal") not in (None, "")
            }
            if custom_ready:
                enriched = CustomPhotosFieldsUtil.calculate_all_custom_fields(
                    custom_ready,
                    tool_key=self.tool_key,
                )
                for key, value in enriched.items():
                    raw_records[key].update(value)
        except Exception as exc:
            self.logger.warning(f"Falha ao calcular CUSTOM_FIELDS no modo sem MRK: {exc}")

        for key, value in list(raw_records.items()):
            raw_records[key] = MetadataFields.normalize_record_to_keys(value or {})

        for canonical in raw_records.values():
            canonical = self._filter_out_mrk_fields(canonical)
            lat = self._to_float(canonical.get("GpsLatitude"))
            lon = self._to_float(canonical.get("GpsLongitude"))
            if lat is None or lon is None:
                continue

            output_record = self._build_output_record_from_catalog(canonical)
            # Garantir chaves de geometria exatamente no nome esperado pela camada.
            output_record[x_geom_key] = lon
            output_record[y_geom_key] = lat
            points.append(output_record)

        schema = []
        if points:
            sample = points[0]
            for key, value in sample.items():
                if key in ("Lat", "Lon"):
                    continue
                if isinstance(value, (int, float)):
                    qtype = QVariant.Double
                else:
                    qtype = QVariant.String
                schema.append((key, qtype, key))

        layer = None
        if points:
            layer = VectorLayerGeometry.create_point_layer_from_dicts(
                points=points,
                name=layer_name,
                field_specs=schema,
                geometry_keys=(x_geom_key, y_geom_key),
                tool_key=self.tool_key,
            )
            if layer and layer.isValid():
                QgsProject.instance().addMapLayer(layer)

        full_dump_payload = {
            "base_folder": base_folder,
            "recursive": recursive,
            "points_total": len(points),
            "quality": quality,
            "groups": {
                base_folder: {
                    "points": len(points),
                    "indexed": len(raw_records),
                    "raw_records": raw_records,
                }
            },
        }

        json_path = ExplorerUtils.create_temp_json(
            full_dump_payload,
            tool_key=self.tool_key,
            prefix="PFM",
            subfolder=os.path.join(
                ExplorerUtils.REPORTS_TEMP_FOLDER,
                ExplorerUtils.REPORTS_JSON_FOLDER,
            ),
            file_stem_hint=ExplorerUtils.build_report_json_stem(
                base_folder=base_folder,
                points_total=len(points),
            ),
        )

        report_payload = None
        if generate_report and json_path:
            report_payload = ReportGenerationService(tool_key=self.tool_key).generate_from_json(
                json_path
            )

        if quality["with_coords"] == 0:
            self.logger.warning(
                "Nenhuma foto com coordenada valida encontrada",
                data={"quality": quality, "base_folder": base_folder},
            )

        payload = {
            "layer": layer,
            "json_path": json_path,
            "report_payload": report_payload,
            "quality": quality,
            "total_points": len(points),
            "total_files": len(files),
        }
        self.logger.info("Vetorizacao sem MRK concluida", data=payload)
        return payload
