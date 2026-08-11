from __future__ import annotations

import math
import re

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..StringManager import StringManager
from ..FormatUtils import FormatUtils
from ..mrk.MetadataFields import MetadataFields
from .RangeMetadataManager import range_metadata_manager


def _normalize_key(key: str) -> str:
    """Normaliza nomes de chaves via utilitario central do projeto."""
    return StringManager._normalize_key(key)


class IMGMetadata:
    """Modelo principal de imagem com todos os campos de MetadataFields e score embutido."""

    def __init__(self, json_record: Optional[Dict[str, Any]] = None):
        """Inicializa o objeto a partir de um registro JSON, preenchendo campos canonicos e extras."""
        all_keys = [k.value if hasattr(k, 'value') else str(k) for k in MetadataFields.all_fields().keys()]
        self._data: Dict[str, Any] = {key: None for key in all_keys}
        self._extras: Dict[str, Any] = {}

        normalized = MetadataFields.normalize_record_to_keys(json_record or {})
        for key, value in normalized.items():
            if key in self._data:
                self._data[key] = value
            else:
                self._extras[key] = value

        self._normalized_lookup = {
            _normalize_key(k): v for k, v in {**self._data, **self._extras}.items()
        }

        # Campos de analise (equivalentes ao antigo DiagnosisResult)
        self.filename: str = "unknown"
        self.mrk_file: str = ""
        self.flight_id: str = "unknown"
        self.dewarp_flag: Any = None
        self.alt_mrk: Any = None
        self.absolute_altitude: Any = None
        self.shutter_count: Any = None
        self.equipment_model: str = "unknown"
        self.equipment_serial_number: str = "unknown"
        self.camera_model: str = "unknown"
        self.camera_serial_number: str = "unknown"
        self.capture_datetime: str = ""
        self.values: Dict[str, Any] = {}
        self.level5_values: Dict[str, Any] = {}
        self.levels: Dict[str, int] = {}
        self.messages: Dict[str, str] = {}
        self.overall_score: float = 0.0

    @staticmethod
    def _is_present(value: Any) -> bool:
        """Indica se um valor pode ser considerado preenchido para analise."""
        if value is None:
            return False
        return str(value).strip().lower() not in {"", "none", "null", "nan"}

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        """Converte valor para float com tratamento de nulos, bytes e strings vazias."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        # Trata bytes objects
        if isinstance(value, bytes):
            try:
                text = value.decode("utf-8", errors="replace")
            except Exception:
                text = str(value)
            text = "".join(c if c.isprintable() or c in " \t" else "" for c in text)
            text = text.strip()
            if not text or text.lower() in {"", "none", "null", "nan"}:
                return None
            try:
                return float(text)
            except (ValueError, TypeError):
                return None
        text = str(value).strip().replace("+", "")
        # Remove caracteres nulos
        text = text.replace("\x00", "")
        if text.lower() in {"", "none", "null", "nan"}:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _first_value(self, names: List[str]) -> Any:
        """Retorna o primeiro valor encontrado entre nomes candidatos e aliases de metacampos."""
        for name in names:
            for candidate in MetadataFields.resolve_candidates(name):
                if candidate in self._data and self._is_present(self._data[candidate]):
                    return self._data[candidate]
                attr = MetadataFields.get_attribute(candidate)
                if attr and attr in self._data and self._is_present(self._data[attr]):
                    return self._data[attr]

            resolved = MetadataFields.resolve_key(name)
            if resolved in self._data and self._is_present(self._data[resolved]):
                return self._data[resolved]

            norm = _normalize_key(name)
            if norm in self._normalized_lookup and self._is_present(self._normalized_lookup[norm]):
                return self._normalized_lookup[norm]
        return None

    # ===================================================================
    # DERIVACOES DE INDICADORES (API 3 - relatorio)
    # ===================================================================
    # O JSON v2.0 (API 1) pode nao conter os campos custom derivados
    # (3DSpeed, MotionBlurRisk, PredictedOverlap, etc.) quando o usuario
    # nao seleciona todos os campos custom no filtro. O relatorio (API 3)
    # deriva esses indicadores a partir dos campos brutos EXIF/XMP/MRK
    # presentes no JSON, garantindo que metricas e alertas funcionem.
    # ===================================================================

    def _sensor_width_mm(self) -> Optional[float]:
        """Retorna a largura do sensor em mm com base no modelo da camera."""
        model = str(self.get_indicator("Model") or "").strip()
        specs = MetadataFields.CAMERA_MODEL_PARAMS.get(model)
        if specs:
            return specs.get("sensor_width_mm")
        return None

    def _sensor_height_mm(self) -> Optional[float]:
        """Retorna a altura do sensor em mm com base no modelo da camera."""
        model = str(self.get_indicator("Model") or "").strip()
        specs = MetadataFields.CAMERA_MODEL_PARAMS.get(model)
        if specs:
            return specs.get("sensor_height_mm")
        return None

    def _derive_speed_3d_ms(self) -> Optional[float]:
        """Deriva velocidade 3D em m/s usando campo explicito ou conversao de km/h."""
        explicit_ms = self._to_float(self._first_value(["3DSpeed", "speed_3d_ms"]))
        if explicit_ms is not None:
            return explicit_ms
        kmh = self._to_float(self._first_value(["Speed3dKmh", "speed_3d_kmh"]))
        if kmh is None:
            return None
        return kmh / 3.6

    def _derive_speed_3d_kmh(self) -> Optional[float]:
        """Deriva velocidade 3D em km/h a partir de m/s."""
        ms = self._derive_speed_3d_ms()
        return ms * 3.6 if ms is not None else None

    def _derive_incidence_angle(self) -> Optional[float]:
        """Deriva angulo de incidencia a partir do campo explicito ou do pitch do gimbal."""
        explicit = self._to_float(self._first_value(["IncidenceAngle", "incidence_angle"]))
        if explicit is not None:
            return explicit
        pitch = self._to_float(self._first_value(["GimbalPitchDegree", "gimbal_pitch_degree"]))
        return abs(pitch) if pitch is not None else None

    def _derive_gsd_cm(self) -> Optional[float]:
        """Deriva GSD em cm/pixel: (sensor_width_mm * altitude_m * 100) / (focal_mm * image_width_px)."""
        alt = self._to_float(
            self._first_value(
                ["RelativeAltitude", "relative_altitude", "FlightAltitude", "flight_altitude", "Alt", "alt"]
            )
        )
        focal = self._to_float(self._first_value(["FocalLength", "focal_length"]))
        width = self._to_float(self._first_value(["ExifImageWidth", "exif_image_width"]))
        sensor_w = self._sensor_width_mm()
        if None in (alt, focal, width, sensor_w) or focal <= 0 or width <= 0:
            return None
        return round((sensor_w * alt * 100.0) / (focal * width), 4)

    def _derive_motion_blur_risk(self) -> Optional[float]:
        """Deriva risco de motion blur em pixels: speed_mps * exposure_s / pixel_size_mm."""
        speed = self._derive_speed_3d_ms()
        exp = self._to_float(self._first_value(["ExposureTime", "exposure_time"]))
        width = self._to_float(self._first_value(["ExifImageWidth", "exif_image_width"]))
        sensor_w = self._sensor_width_mm()
        if None in (speed, exp, width, sensor_w) or width <= 0 or sensor_w <= 0:
            return None
        pixel_size_mm = sensor_w / width
        return round(speed * exp / pixel_size_mm, 4)

    def _derive_gimbal_offset(self) -> Optional[float]:
        """Deriva desalinhamento do gimbal: menor angulo entre GimbalYaw e FlightYaw."""
        gimbal_yaw = self._to_float(self._first_value(["GimbalYawDegree", "gimbal_yaw_degree"]))
        flight_yaw = self._to_float(self._first_value(["FlightYawDegree", "flight_yaw_degree"]))
        if gimbal_yaw is None or flight_yaw is None:
            return None
        diff = abs(gimbal_yaw - flight_yaw - 180.0) % 360.0
        if diff > 180.0:
            diff = 360.0 - diff
        return round(diff, 4)

    def _derive_yaw_alignment_error(self) -> Optional[float]:
        """Deriva erro de alinhamento yaw: menor angulo entre GimbalYaw e FlightYaw."""
        gimbal_yaw = self._to_float(self._first_value(["GimbalYawDegree", "gimbal_yaw_degree"]))
        flight_yaw = self._to_float(self._first_value(["FlightYawDegree", "flight_yaw_degree"]))
        if gimbal_yaw is None or flight_yaw is None:
            return None
        diff = abs(gimbal_yaw - flight_yaw) % 360.0
        if diff > 180.0:
            diff = 360.0 - diff
        return round(diff, 4)

    def _derive_yaw_relative_error(self) -> Optional[float]:
        """Deriva erro de yaw relativo: (GimbalYaw - FlightYaw) % 360."""
        gimbal_yaw = self._to_float(self._first_value(["GimbalYawDegree", "gimbal_yaw_degree"]))
        flight_yaw = self._to_float(self._first_value(["FlightYawDegree", "flight_yaw_degree"]))
        if gimbal_yaw is None or flight_yaw is None:
            return None
        return round((gimbal_yaw - flight_yaw) % 360.0, 4)

    def _derive_rtk_effective_precision(self) -> Optional[float]:
        """Deriva precisao efetiva do RTK: media dos desvios padrao lat/lon/hgt."""
        lat = self._to_float(self._first_value(["RtkStdLat", "rtk_std_lat"]))
        lon = self._to_float(self._first_value(["RtkStdLon", "rtk_std_lon"]))
        hgt = self._to_float(self._first_value(["RtkStdHgt", "rtk_std_hgt"]))
        vals = [v for v in (lat, lon, hgt) if v is not None]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 4)

    def _derive_rtk_type(self) -> Optional[str]:
        """Deriva tipo de sinal RTK a partir do RtkFlag."""
        flag = self._to_float(self._first_value(["RtkFlag", "rtk_flag"]))
        if flag is None:
            return None
        if flag == 0:
            return "Sem GPS"
        if flag == 16:
            return "RTK Single"
        if flag == 34:
            return "RTK Float"
        if flag == 50:
            return "RTK Fixed"
        return "RTK Desconhecido"

    def _derive_rtk_stability_score(self) -> Optional[float]:
        """Deriva score de estabilidade RTK a partir do RtkDiffAge."""
        age = self._to_float(self._first_value(["RtkDiffAge", "rtk_diff_age"]))
        if age is None:
            return None
        if age <= 0.5:
            return 100.0
        if age <= 1.0:
            return 99.0
        if age <= 2.0:
            return 98.0
        if age <= 5.0:
            return 95.0
        return 90.0

    def _derive_xy_difference(self) -> Optional[float]:
        """Deriva diferenca planimetrica (m) entre MRK e metadados XMP (Haversine)."""
        mrk_lat = self._to_float(self._first_value(["Lat", "lat"]))
        mrk_lon = self._to_float(self._first_value(["Lon", "lon"]))
        xmp_lat = self._to_float(self._first_value(["GpsLatitudeXmp", "gps_latitude_xmp"]))
        xmp_lon = self._to_float(self._first_value(["GpsLongitudeXmp", "gps_longitude_xmp"]))
        if None in (mrk_lat, mrk_lon, xmp_lat, xmp_lon):
            return None
        return round(self._haversine(mrk_lat, mrk_lon, xmp_lat, xmp_lon), 4)

    def _derive_z_difference(self) -> Optional[float]:
        """Deriva diferenca altimetrica (m) entre Alt (MRK) e AbsoluteAltitude."""
        alt = self._to_float(self._first_value(["Alt", "alt"]))
        abs_alt = self._to_float(self._first_value(["AbsoluteAltitude", "absolute_altitude"]))
        if alt is None or abs_alt is None:
            return None
        return round(abs(alt - abs_alt), 4)

    def _derive_ground_elevation(self) -> Optional[float]:
        """Deriva altitude do solo (MSL): AbsoluteAltitude - RelativeAltitude."""
        abs_alt = self._to_float(self._first_value(["AbsoluteAltitude", "absolute_altitude"]))
        rel_alt = self._to_float(self._first_value(["RelativeAltitude", "relative_altitude"]))
        if abs_alt is None or rel_alt is None:
            return None
        return round(abs_alt - rel_alt, 4)

    def _derive_flight_altitude(self) -> Optional[float]:
        """Deriva altitude de voo efetiva: LRF corrigido ou RelativeAltitude."""
        lrf = self._to_float(self._first_value(["LRFTargetDistance", "lrf_target_distance"]))
        if lrf is not None and lrf > 0:
            inc = self._derive_incidence_angle()
            if inc is not None:
                return round(lrf * math.cos(math.radians(inc)), 4)
        return self._to_float(self._first_value(["RelativeAltitude", "relative_altitude"]))

    def _derive_coverage_width(self) -> Optional[float]:
        """Deriva largura da cobertura no solo (m): alt * sensor_w / focal."""
        alt = self._derive_flight_altitude()
        focal = self._to_float(self._first_value(["FocalLength", "focal_length"]))
        sensor_w = self._sensor_width_mm()
        if None in (alt, focal, sensor_w) or focal <= 0:
            return None
        return round(alt * sensor_w / focal, 4)

    def _derive_coverage_height(self) -> Optional[float]:
        """Deriva altura da cobertura no solo (m): alt * sensor_h / focal."""
        alt = self._derive_flight_altitude()
        focal = self._to_float(self._first_value(["FocalLength", "focal_length"]))
        sensor_h = self._sensor_height_mm()
        if None in (alt, focal, sensor_h) or focal <= 0:
            return None
        return round(alt * sensor_h / focal, 4)

    def _derive_predicted_overlap(self) -> Optional[float]:
        """Deriva sobreposicao frontal (%): (1 - dist / coverage_width) * 100."""
        dist = self._to_float(self._first_value(["Distance3dPrevious", "distance_3d_previous"]))
        cov_w = self._derive_coverage_width()
        if dist is None or cov_w is None or cov_w <= 0:
            return None
        return round(max(0.0, min(100.0, (1.0 - dist / cov_w) * 100.0)), 4)

    def _derive_f_overlap(self) -> Optional[float]:
        """Deriva alias de sobreposicao frontal (PredictedOverlap)."""
        return self._derive_predicted_overlap()

    def _derive_is_ideal_overlap(self) -> Optional[bool]:
        """Deriva se sobreposicao >= 60%."""
        overlap = self._derive_predicted_overlap()
        if overlap is None:
            return None
        return overlap >= 60.0

    def _derive_light_source_classification(self) -> Optional[str]:
        """Deriva classificacao da fonte de luz a partir do codigo EXIF LightSource."""
        text = self._first_value(["LightSourceClassification", "light_source_classification"])
        if text and str(text).strip():
            return str(text).strip()
        code = self._to_float(self._first_value(["LightSource", "light_source"]))
        if code is None:
            return None
        mapping = {
            1: "Daylight",
            2: "Fluorescent",
            3: "Tungsten",
            4: "Flash",
            9: "Fine Weather",
            10: "Cloudy Weather",
            11: "Shade",
        }
        return mapping.get(int(code))

    def _derive_light_consistency(self) -> Optional[str]:
        """Deriva consistencia de luz (alias de LightSourceClassification)."""
        return self._derive_light_source_classification()

    def _derive_ev(self) -> Optional[float]:
        """Deriva Exposure Value (EV): log2(N^2 / t)."""
        fnum = self._to_float(self._first_value(["FNumber", "f_number"]))
        exp = self._to_float(self._first_value(["ExposureTime", "exposure_time"]))
        if fnum is None or exp is None or exp <= 0:
            return None
        return round(math.log2(fnum**2 / exp), 4)

    def _derive_light_value(self) -> Optional[float]:
        """Deriva Light Value (LV): EV + log2(ISO/100)."""
        ev = self._derive_ev()
        iso = self._to_float(self._first_value(["ISOSpeedRatings", "iso_speed_ratings"]))
        if ev is None or iso is None or iso <= 0:
            return None
        return round(ev + math.log2(iso / 100.0), 4)

    def _derive_ev_classification(self) -> Optional[str]:
        """Deriva classificacao de exposicao a partir do EV ou LightSource."""
        ev = self._to_float(self._first_value(["ExposureValueEv", "exposure_value_ev"]))
        if ev is None:
            ev = self._derive_ev()
        if ev is not None:
            if ev < 6:
                return "noite/escuro"
            if ev < 10:
                return "indoor/sombra"
            if ev < 12:
                return "nublado"
            if ev < 15:
                return "luz solar normal"
            return "sol muito forte/neve"
        ls = self._derive_light_source_classification()
        if ls == "Daylight":
            return "luz solar normal"
        if ls == "Fluorescent":
            return "indoor/sombra"
        if ls == "Cloudy Weather":
            return "nublado"
        return None

    def _derive_focal_length_35efl(self) -> Optional[float]:
        """Deriva distancia focal equivalente 35mm."""
        focal = self._to_float(self._first_value(["FocalLength", "focal_length"]))
        sensor_w = self._sensor_width_mm()
        if focal is None or sensor_w is None or sensor_w <= 0:
            return None
        return round(focal * 36.0 / sensor_w, 4)

    def _derive_fov(self) -> Optional[float]:
        """Deriva Field of View (graus): 2 * atan(diagonal / (2 * focal))."""
        focal = self._to_float(self._first_value(["FocalLength", "focal_length"]))
        sensor_w = self._sensor_width_mm()
        sensor_h = self._sensor_height_mm()
        if None in (focal, sensor_w, sensor_h) or focal <= 0:
            return None
        diag = math.sqrt(sensor_w**2 + sensor_h**2)
        return round(2.0 * math.degrees(math.atan(diag / (2.0 * focal))), 4)

    def _derive_circle_of_confusion(self) -> Optional[float]:
        """Deriva Circle of Confusion (mm): diagonal_sensor / 1730."""
        sensor_w = self._sensor_width_mm()
        sensor_h = self._sensor_height_mm()
        if sensor_w is None or sensor_h is None:
            return None
        diag = math.sqrt(sensor_w**2 + sensor_h**2)
        return round(diag / 1730.0, 6)

    def _derive_hyperfocal_distance(self) -> Optional[float]:
        """Deriva distancia hiperfocal (m): f^2 / (N * CoC)."""
        focal = self._to_float(self._first_value(["FocalLength", "focal_length"]))
        fnum = self._to_float(self._first_value(["FNumber", "f_number"]))
        coc = self._derive_circle_of_confusion()
        if None in (focal, fnum, coc) or fnum <= 0 or coc <= 0:
            return None
        return round(focal**2 / (fnum * coc) / 1000.0, 4)

    def _derive_dof(self) -> Optional[float]:
        """Deriva Depth of Field (m)."""
        focal = self._to_float(self._first_value(["FocalLength", "focal_length"]))
        fnum = self._to_float(self._first_value(["FNumber", "f_number"]))
        focus = self._to_float(self._first_value(["FocusDistance", "focus_distance"]))
        coc = self._derive_circle_of_confusion()
        if None in (focal, fnum, focus, coc) or fnum <= 0 or coc <= 0:
            return None
        h = focal**2 / (fnum * coc)
        if h <= focal:
            return None
        dof = 2.0 * h * focus * (focus - focal) / (h**2 - (focus - focal)**2)
        return round(dof / 1000.0, 4) if dof > 0 else None

    def _derive_nadir(self) -> Optional[str]:
        """Deriva classificacao Nadir/Obliqua a partir do pitch do gimbal."""
        pitch = self._to_float(self._first_value(["GimbalPitchDegree", "gimbal_pitch_degree"]))
        if pitch is None:
            return None
        if abs(abs(pitch) - 90.0) <= 3.0:
            return "Nadir"
        return "Obliqua"

    def _derive_total_heat_index(self) -> Optional[float]:
        """Deriva indice termico medio (C) entre sensor e lente."""
        sensor = self._to_float(self._first_value(["SensorTemperature", "sensor_temp_c"]))
        lens = self._to_float(self._first_value(["LensTemperature", "lens_temperature"]))
        vals = [v for v in (sensor, lens) if v is not None]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 4)

    def _derive_shutter_life_pct(self) -> Optional[float]:
        """Deriva percentual de vida util do obturador (assume 200k disparos)."""
        shutter = self._to_float(self._first_value(["ShutterCount", "shutter_count"]))
        if shutter is None:
            return None
        return round(shutter / 200000.0 * 100.0, 4)

    def _derive_orthorectification_potential(self) -> Optional[float]:
        """Deriva potencial de ortorretificacao (0-100) a partir do angulo de incidencia."""
        inc = self._derive_incidence_angle()
        if inc is None:
            return None
        return round(max(0.0, 100.0 - inc), 4)

    def _derive_photogrammetry_quality_index(self) -> Optional[float]:
        """Deriva PQI (0-100) a partir do overall_score."""
        if self.overall_score > 0:
            return round(self.overall_score * 20.0, 4)
        return None

    def _derive_linear_velocity_instant(self) -> Optional[float]:
        """Deriva velocidade linear instantanea (alias de 3DSpeed)."""
        return self._derive_speed_3d_ms()

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distancia em metros entre dois pontos geograficos (Haversine)."""
        r = 6371000.0
        p1 = math.radians(lat1)
        p2 = math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2.0)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0)**2
        return 2.0 * r * math.asin(math.sqrt(a))

    def get_indicator(self, key: str) -> Any:
        """Obtém o valor de um indicador com suporte a aliases e campos derivados."""
        norm = _normalize_key(key)
        if norm == "speed_3d_ms":
            return self._derive_speed_3d_ms()
        if norm == "speed_3d_kmh":
            return self._derive_speed_3d_kmh()
        if norm == "incidence_angle":
            return self._derive_incidence_angle()
        if norm == "sensor_temp_c":
            return self._to_float(self._first_value(["SensorTemperature", "LensTemperature", "sensor_temp_c"]))
        if norm == "gsd_cm":
            return self._derive_gsd_cm()
        if norm == "motion_blur_risk":
            return self._derive_motion_blur_risk()
        if norm == "gimbal_offset":
            return self._derive_gimbal_offset()
        if norm == "yaw_alignment_error":
            return self._derive_yaw_alignment_error()
        if norm == "yaw_relative_error":
            return self._derive_yaw_relative_error()
        if norm == "rtk_effective_precision":
            return self._derive_rtk_effective_precision()
        if norm == "rtk_type":
            return self._derive_rtk_type()
        if norm == "rtk_stability_score":
            return self._derive_rtk_stability_score()
        if norm == "xy_difference":
            return self._derive_xy_difference()
        if norm == "z_difference":
            return self._derive_z_difference()
        if norm == "ground_elevation":
            return self._derive_ground_elevation()
        if norm == "flight_altitude":
            return self._derive_flight_altitude()
        if norm == "coverage_width":
            return self._derive_coverage_width()
        if norm == "coverage_height":
            return self._derive_coverage_height()
        if norm == "predicted_overlap":
            return self._derive_predicted_overlap()
        if norm == "f_overlap":
            return self._derive_f_overlap()
        if norm == "is_ideal_overlap":
            return self._derive_is_ideal_overlap()
        if norm == "light_source_classification":
            return self._derive_light_source_classification()
        if norm == "light_consistency":
            return self._derive_light_consistency()
        if norm == "exposure_value_ev":
            return self._derive_ev()
        if norm == "light_value":
            return self._derive_light_value()
        if norm == "ev_classification":
            return self._derive_ev_classification()
        if norm == "focal_length_35efl":
            return self._derive_focal_length_35efl()
        if norm == "fov":
            return self._derive_fov()
        if norm == "circle_of_confusion":
            return self._derive_circle_of_confusion()
        if norm == "hyperfocal_distance":
            return self._derive_hyperfocal_distance()
        if norm == "dof":
            return self._derive_dof()
        if norm == "nadir":
            return self._derive_nadir()
        if norm == "total_heat_index":
            return self._derive_total_heat_index()
        if norm == "shutter_life_pct":
            return self._derive_shutter_life_pct()
        if norm == "orthorectification_potential":
            return self._derive_orthorectification_potential()
        if norm == "photogrammetry_quality_index":
            return self._derive_photogrammetry_quality_index()
        if norm == "linear_velocity_instant":
            return self._derive_linear_velocity_instant()
        return self._first_value([key, norm])

    @staticmethod
    def _derive_flight_id(mrk_file_value: Any) -> str:
        """Gera identificador de voo padronizado com base no nome do arquivo MRK."""
        if not mrk_file_value:
            return "unknown"
        text = str(mrk_file_value).strip()
        text = re.sub(r"_Timestamp\.MRK$", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\.MRK$", "", text, flags=re.IGNORECASE)
        return text or "unknown"

    def score(self) -> "IMGMetadata":
        """Calcula niveis, mensagens e score geral da imagem e retorna o proprio objeto."""
        if range_metadata_manager._config is None:
            range_metadata_manager.load()

        self.filename = str(self.get_indicator("File") or "unknown")
        self.mrk_file = str(self.get_indicator("MrkFile") or "")
        self.flight_id = self._derive_flight_id(self.mrk_file)

        self.dewarp_flag = self.get_indicator("DewarpFlag")
        self.alt_mrk = self.get_indicator("Alt")
        self.absolute_altitude = self.get_indicator("AbsoluteAltitude")
        self.shutter_count = self.get_indicator("ShutterCount")

        self.equipment_model = str(
            self.get_indicator("DroneModel")
            or self.get_indicator("Model")
            or "unknown"
        )
        self.equipment_serial_number = str(self.get_indicator("DroneSerialNumber") or "unknown")
        self.camera_model = str(self.get_indicator("Model") or "unknown")
        self.camera_serial_number = str(self.get_indicator("CameraSerialNumber") or "unknown")
        self.capture_datetime = str(
            self.get_indicator("DateTimeOriginal")
            or self.get_indicator("UTCAtExposure")
            or ""
        )

        indicators = list((range_metadata_manager._config or {}).get("thresholds", {}).keys())
        level5_field_keys = [
            key for key, field in MetadataFields.all_fields().items()
            if getattr(field, "level", None) == 5
        ]

        self.values = {}
        self.level5_values = {}
        self.levels = {}
        self.messages = {}

        total = 0
        count = 0

        for indicator in indicators:
            value = self.get_indicator(indicator)
            if value is None:
                continue
            self.values[indicator] = value
            level, message = range_metadata_manager.classify(indicator, value)
            self.levels[indicator] = level
            self.messages[indicator] = message
            total += level
            count += 1

        # Popula level5_values com TODOS os campos disponiveis em _data,
        # nao apenas level-5. Isso garante que campos EXIF como ISOSpeedRatings,
        # GPSMapDatum, etc. fiquem acessiveis para graficos e analises.
        for field_key in level5_field_keys:
            value = self.get_indicator(field_key)
            if value is not None:
                self.level5_values[field_key] = value

        # Adiciona tambem campos de _data que nao sao level-5 mas existem
        # (ex: ISOSpeedRatings, GPSMapDatum, GpsStatusExif, etc.)
        for key, value in self._data.items():
            if key not in self.level5_values and self._is_present(value):
                self.level5_values[key] = value
        for key, value in self._extras.items():
            if key not in self.level5_values and self._is_present(value):
                self.level5_values[key] = value

        # Adiciona valores derivados ao level5_values para que os agregadores
        # (AggregateAnalyzer, JsonMetadataManager) encontrem os dados.
        derived_keys = [
            "3DSpeed", "Speed3dKmh", "GroundSampleDistanceCm", "MotionBlurRisk",
            "GimbalOffset", "YawAlignmentError", "YawRelativeError",
            "RtkEffectivePrecision", "RtkType", "RtkStabilityScore",
            "XYDifference", "ZDifference", "GroundElevation", "FlightAltitude",
            "CoverageWidth", "CoverageHeight", "PredictedOverlap", "FOverlap",
            "IsIdealOverlap", "LightSourceClassification", "LightConsistency",
            "ExposureValueEv", "LightValue", "EvClassification",
            "FocalLength35efl", "FOV", "CircleOfConfusion", "HyperfocalDistance",
            "DOF", "Nadir", "TotalHeatIndex", "ShutterLifePct",
            "OrthorectificationPotential", "PhotogrammetryQualityIndex",
            "LinearVelocityInstant",
        ]
        for dk in derived_keys:
            if dk in self.level5_values:
                continue
            val = self.get_indicator(dk)
            if val is not None:
                self.level5_values[dk] = val

        score = (total / count) if count > 0 else 0.0
        self.overall_score = round(score, 1)
        return self

    @staticmethod
    def compute_sequence_indicators(results: List["IMGMetadata"]) -> None:
        """Calcula indicadores baseados em sequencia (foto anterior/proxima) e armazena nos resultados.

        Indicadores calculados:
            - time_since_previous, geodesic_distance_previous, distance_3d_previous
            - avg_velocity_between_photos, displacement_direction
            - gimbal_angular_velocity, vertical_stability, trajectory_smoothness
            - speed_variation_index, capture_efficiency, abrupt_change_flag
            - strip_id, is_valid_sequence_prev, is_valid_sequence_next
        """
        if not results:
            return

        def _sort_key(r: "IMGMetadata") -> datetime:
            dt = FormatUtils.parse_capture_datetime(r.capture_datetime)
            return dt if dt is not None else datetime.min

        ordered = sorted(results, key=_sort_key)

        for i, r in enumerate(ordered):
            prev = ordered[i - 1] if i > 0 else None
            nxt = ordered[i + 1] if i < len(ordered) - 1 else None

            # Tempo desde a foto anterior
            time_sec = None
            if prev is not None:
                dt_prev = FormatUtils.parse_capture_datetime(prev.capture_datetime)
                dt_cur = FormatUtils.parse_capture_datetime(r.capture_datetime)
                if dt_prev and dt_cur:
                    time_sec = (dt_cur - dt_prev).total_seconds()
                    r.values["time_since_previous"] = round(time_sec, 4)
                    r.level5_values["TimeSincePrevious"] = round(time_sec, 4)

            # Distancia geodesica e 3D entre fotos consecutivas
            if prev is not None:
                lat1 = r._to_float(r._first_value(["Lat", "lat"]))
                lon1 = r._to_float(r._first_value(["Lon", "lon"]))
                lat2 = prev._to_float(prev._first_value(["Lat", "lat"]))
                lon2 = prev._to_float(prev._first_value(["Lon", "lon"]))
                if None not in (lat1, lon1, lat2, lon2):
                    dist = IMGMetadata._haversine(lat1, lon1, lat2, lon2)
                    r.values["geodesic_distance_previous"] = round(dist, 4)
                    r.level5_values["GeodesicDistancePrevious"] = round(dist, 4)

                    alt1 = r._to_float(
                        r._first_value(["Alt", "alt", "AbsoluteAltitude", "absolute_altitude"])
                    )
                    alt2 = prev._to_float(
                        prev._first_value(["Alt", "alt", "AbsoluteAltitude", "absolute_altitude"])
                    )
                    if alt1 is not None and alt2 is not None:
                        dist3d = math.sqrt(dist**2 + (alt1 - alt2)**2)
                        r.values["distance_3d_previous"] = round(dist3d, 4)
                        r.level5_values["Distance3dPrevious"] = round(dist3d, 4)

                    if time_sec and time_sec > 0:
                        vel = dist / time_sec
                        r.values["avg_velocity_between_photos"] = round(vel, 4)
                        r.level5_values["AvgVelocityBetweenPhotos"] = round(vel, 4)

                    if dist > 0:
                        bearing = math.degrees(
                            math.atan2(
                                math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2)),
                                math.cos(math.radians(lat1)) * math.sin(math.radians(lat2))
                                - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2))
                                * math.cos(math.radians(lon2 - lon1)),
                            )
                        )
                        bearing = (bearing + 360.0) % 360.0
                        r.values["displacement_direction"] = round(bearing, 4)
                        r.level5_values["DisplacementDirection"] = round(bearing, 4)

            # Velocidade angular do gimbal
            if prev is not None and time_sec and time_sec > 0:
                gimbal_cur = r._to_float(r._first_value(["GimbalYawDegree", "gimbal_yaw_degree"]))
                gimbal_prev = prev._to_float(prev._first_value(["GimbalYawDegree", "gimbal_yaw_degree"]))
                if gimbal_cur is not None and gimbal_prev is not None:
                    gimbal_vel = abs(gimbal_cur - gimbal_prev) / time_sec
                    r.values["gimbal_angular_velocity"] = round(gimbal_vel, 4)
                    r.level5_values["GimbalAngularVelocity"] = round(gimbal_vel, 4)

            # Estabilidade vertical
            if prev is not None:
                rel_cur = r._to_float(r._first_value(["RelativeAltitude", "relative_altitude"]))
                rel_prev = prev._to_float(prev._first_value(["RelativeAltitude", "relative_altitude"]))
                if rel_cur is not None and rel_prev is not None:
                    vert = abs(rel_cur - rel_prev)
                    r.values["vertical_stability"] = round(vert, 4)
                    r.level5_values["VerticalStability"] = round(vert, 4)

            # Suavidade da trajetoria (variacao de yaw)
            if prev is not None:
                yaw_cur = r._to_float(r._first_value(["FlightYawDegree", "flight_yaw_degree"]))
                yaw_prev = prev._to_float(prev._first_value(["FlightYawDegree", "flight_yaw_degree"]))
                if yaw_cur is not None and yaw_prev is not None:
                    diff = abs(yaw_cur - yaw_prev) % 360.0
                    if diff > 180.0:
                        diff = 360.0 - diff
                    r.values["trajectory_smoothness"] = round(diff, 4)
                    r.level5_values["TrajectorySmoothness"] = round(diff, 4)

            # Indice de variacao de velocidade
            speed_cur = r._derive_speed_3d_ms()
            speed_prev = prev._derive_speed_3d_ms() if prev else None
            if speed_cur is not None and speed_prev is not None and speed_prev > 0:
                var = abs(speed_cur - speed_prev) / speed_prev
                r.values["speed_variation_index"] = round(var, 4)
                r.level5_values["SpeedVariationIndex"] = round(var, 4)

            # Eficiencia de captura
            dist = r.values.get("geodesic_distance_previous")
            cov_w = r._derive_coverage_width()
            if dist is not None and cov_w is not None and cov_w > 0:
                eff = dist / cov_w
                r.values["capture_efficiency"] = round(eff, 4)
                r.level5_values["CaptureEfficiency"] = round(eff, 4)

            # Flag de mudanca abrupta
            if time_sec is not None and dist is not None:
                abrupt = time_sec > 10.0 or dist > 100.0
                r.values["abrupt_change_flag"] = abrupt
                r.level5_values["AbruptChangeFlag"] = abrupt

            # Strip ID (mudanca de direcao > 45 graus)
            if prev is not None:
                yaw_cur = r._to_float(r._first_value(["FlightYawDegree", "flight_yaw_degree"]))
                yaw_prev = prev._to_float(prev._first_value(["FlightYawDegree", "flight_yaw_degree"]))
                if yaw_cur is not None and yaw_prev is not None:
                    diff = abs(yaw_cur - yaw_prev) % 360.0
                    if diff > 180.0:
                        diff = 360.0 - diff
                    if diff > 45.0:
                        r.values["strip_id"] = prev.values.get("strip_id", 1) + 1
                    else:
                        r.values["strip_id"] = prev.values.get("strip_id", 1)
                else:
                    r.values["strip_id"] = prev.values.get("strip_id", 1)
            else:
                r.values["strip_id"] = 1
            r.level5_values["StripId"] = r.values.get("strip_id")

            # Validacao de sequencia
            r.values["is_valid_sequence_prev"] = 1 if (time_sec is not None and 0 < time_sec <= 10) else 0
            r.level5_values["IsValidSequencePrev"] = r.values["is_valid_sequence_prev"]
            if nxt is not None:
                dt_cur = FormatUtils.parse_capture_datetime(r.capture_datetime)
                dt_next = FormatUtils.parse_capture_datetime(nxt.capture_datetime)
                if dt_cur and dt_next:
                    time_next = (dt_next - dt_cur).total_seconds()
                    r.values["is_valid_sequence_next"] = 1 if 0 < time_next <= 10 else 0
                    r.level5_values["IsValidSequenceNext"] = r.values["is_valid_sequence_next"]

    def to_json(self) -> Dict[str, Any]:
        """Exporta o estado completo do objeto em formato de dicionario serializavel."""
        payload = dict(self._data)
        payload.update(self._extras)
        payload.update(
            {
                "filename": self.filename,
                "mrk_file": self.mrk_file,
                "flight_id": self.flight_id,
                "dewarp_flag": self.dewarp_flag,
                "alt_mrk": self.alt_mrk,
                "absolute_altitude": self.absolute_altitude,
                "shutter_count": self.shutter_count,
                "equipment_model": self.equipment_model,
                "equipment_serial_number": self.equipment_serial_number,
                "camera_model": self.camera_model,
                "camera_serial_number": self.camera_serial_number,
                "capture_datetime": self.capture_datetime,
                "values": self.values,
                "level5_values": self.level5_values,
                "levels": self.levels,
                "messages": self.messages,
                "overall_score": self.overall_score,
            }
        )
        return payload