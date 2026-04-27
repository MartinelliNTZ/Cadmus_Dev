#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CustomUtil - Calcula campos derivados CUSTOM_FIELDS.

Recebe output do Manager.collect_metadata() â†’ adiciona 23 campos custom calculados

DependÃªncias:
- MetadataFields.CUSTOM_FIELDS
- math, datetime, numpy (haversine)
"""

import math
import statistics
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from ...core.config.LogUtils import LogUtils
from ...core.enum.LightSourceEnum import LightSourceEnum
from ..ToolKeys import ToolKey

DECIMAL_PLACES = 4


class CustomPhotosFieldsUtil:
    """Calcula todos os campos CUSTOM_FIELDS para cada foto, validando sequÃªncias."""

    @staticmethod
    def _get_logger(tool_key: str = ToolKey.UNTRACEABLE) -> LogUtils:
        return LogUtils(tool=tool_key, class_name="CustomPhotosFieldsUtil")

    # Constantes
    MAX_DT_DIFF = 120  # segundos
    MAX_ALT_DIFF = 200  # metros
    MAX_SHUTTER_JUMP = 5000  # fotos (arrochado)
    IDEAL_OVERLAP = 60  # %
    ORTO_SCORE_WEIGHTS = {
        "rtk_high": 30,
        "incidence_low": 25,
        "dewarp": 20,
        "rtk_fresh": 15,
        "overlap_good": 10,
    }
    
    BLUR_THRESHOLD = 0.5  # motion blur in pixels
    COVERAGE_FACTOR = 1.45  # approx for 84Â° HFOV
    STRIP_CHANGE_THRESHOLD = 150  # degrees

    @staticmethod
    def safe_float(val: any, default: float = 0.0) -> float:
        """Converte para float seguro (strings '+123.4' â†’ 123.4)."""
        if val is None:
            return default
        return float(str(val).replace("+", ""))

    @staticmethod
    def safe_int(val: any, default: int = 0) -> int:
        """Converte para int seguro."""
        if val is None:
            return default
        return int(str(val))

    @staticmethod
    def parse_datetime(dt_str: str) -> datetime:
        """Parse robusto de datetime com suporte a formatos EXIF/ISO."""
        if dt_str is None:
            return None
        raw = str(dt_str).strip()
        if not raw or raw.lower() in ("none", "null", "nan"):
            return None

        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            pass

        formats = (
            "%Y:%m:%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y%m%d%H%M",
            "%Y%m%d",
        )
        for fmt in formats:
            try:
                return datetime.strptime(raw, fmt)
            except Exception:
                continue
        return None

    @staticmethod
    def resolve_capture_datetime(data: Dict) -> Tuple[Optional[datetime], Optional[str]]:
        """Resolve data/hora de captura usando fallback entre campos conhecidos."""
        candidates = (
            ("DateTimeOriginal", data.get("DateTimeOriginal")),
            ("DateTime", data.get("DateTime")),
            ("UTCAtExposure", data.get("UTCAtExposure")),
            ("DtFull", data.get("DtFull")),
        )
        for source, value in candidates:
            parsed = CustomPhotosFieldsUtil.parse_datetime(value)
            if parsed is not None:
                return parsed, source

        dt_date = str(data.get("DtDate") or "").strip()
        dt_time = str(data.get("DtTime") or "").strip()
        if dt_date and dt_time and dt_date.lower() not in ("none", "null"):
            hhmm = dt_time.zfill(4)
            parsed = CustomPhotosFieldsUtil.parse_datetime(f"{dt_date}{hhmm}")
            if parsed is not None:
                return parsed, "DtDate+DtTime"

        return None, None

    @staticmethod
    def get_voo_id(data: Dict) -> str:
        """VOO_ID = drone_sn[:8] + camera_sn[:8] + YYYY-MM-DD."""
        drone_sn = data.get("DroneSerialNumber", "UNKNOWN")
        camera_sn = data.get("CameraSerialNumber", "UNKNOWN")
        dt, _ = CustomPhotosFieldsUtil.resolve_capture_datetime(data)
        date_str = dt.strftime("%Y-%m-%d") if dt is not None else "UNKNOWN_DATE"
        return f"{drone_sn[:8]}_{camera_sn[:8]}_{date_str}"

    @staticmethod
    def is_valid_sequence(
        curr_data: Dict, other_data: Dict, direction: str = "prev"
    ) -> bool:
        """Valida se 2 fotos sÃ£o sequÃªncia vÃ¡lida (mesmo voo)."""
        if other_data is None:
            return False

        # 1. Mesmo VOO_ID
        voo_curr = CustomPhotosFieldsUtil.get_voo_id(curr_data)
        voo_other = CustomPhotosFieldsUtil.get_voo_id(other_data)
        if voo_curr != voo_other:
            return False

        # 2. dt_diff
        dt_curr, _ = CustomPhotosFieldsUtil.resolve_capture_datetime(curr_data)
        dt_other, _ = CustomPhotosFieldsUtil.resolve_capture_datetime(other_data)
        if dt_curr is None or dt_other is None:
            return False
        dt_diff = abs((dt_curr - dt_other).total_seconds())
        if dt_diff > CustomPhotosFieldsUtil.MAX_DT_DIFF:
            return False

        # 3. alt_diff
        alt_curr = CustomPhotosFieldsUtil.safe_float(curr_data.get("AbsoluteAltitude", 0))
        alt_other = CustomPhotosFieldsUtil.safe_float(other_data.get("AbsoluteAltitude", 0))
        alt_diff = abs(alt_curr - alt_other)
        if alt_diff > CustomPhotosFieldsUtil.MAX_ALT_DIFF:
            return False

        # 4. shutter_jump (arrochado)
        shutter_curr = CustomPhotosFieldsUtil.safe_int(curr_data.get("ShutterCount"))
        shutter_other = CustomPhotosFieldsUtil.safe_int(other_data.get("ShutterCount"))
        shutter_jump = abs(shutter_curr - shutter_other) > CustomPhotosFieldsUtil.MAX_SHUTTER_JUMP
        if shutter_jump:
            return False

        return True

    @staticmethod
    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """DistÃ¢ncia Haversine entre 2 pontos GPS (metros)."""
        R = 6371000  # Raio Terra

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def bearing_angle(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Azimute bearing entre 2 pontos (0=Norte)."""
        delta_lon = math.radians(lon2 - lon1)
        y = math.sin(delta_lon) * math.cos(math.radians(lat2))
        x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(
            math.radians(lat1)
        ) * math.cos(math.radians(lat2)) * math.cos(delta_lon)
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360) % 360

    @staticmethod
    def angle_difference(a: float, b: float) -> float:
        """Menor diferenÃ§a angular entre dois azimutes (0-180)."""
        diff = abs((a - b) % 360)
        return diff if diff <= 180 else 360 - diff

    @staticmethod
    def calculate_estimated_coverage(data: Dict) -> Tuple[float, float]:
        """Estimativa de cobertura no solo (largura, altura) em metros."""
        effective_distance = CustomPhotosFieldsUtil.safe_float(data.get("LRFTargetDistance", 0))
        if effective_distance <= 0:
            effective_distance = CustomPhotosFieldsUtil.safe_float(data.get("AbsoluteAltitude", 0))

        focal_length_mm = CustomPhotosFieldsUtil.safe_float(data.get("FocalLength", 12.29))
        sensor_width_mm = 7.49
        img_w_px = CustomPhotosFieldsUtil.safe_float(data.get("ExifImageWidth", 5280))
        img_h_px = CustomPhotosFieldsUtil.safe_float(data.get("ExifImageHeight", 3956))
        aspect_ratio = img_h_px / img_w_px if img_w_px > 0 else 0.75

        width_m = (
            effective_distance * sensor_width_mm / focal_length_mm
            if effective_distance > 0 and focal_length_mm > 0
            else 0.0
        )
        height_m = width_m * aspect_ratio
        return (round(width_m, DECIMAL_PLACES), round(height_m, DECIMAL_PLACES))

    @staticmethod
    def _calculate_sequence_fields(
        data: Dict, other_data: Optional[Dict], valid_seq: bool, direction: str
    ) -> Dict:
        """Campos sequÃªncia (prev/next)."""
        if not valid_seq or other_data is None:
            prefix = f"{direction}_"
            return {
                f"{prefix}time_since": round(0.0, DECIMAL_PLACES),
                f"{prefix}geodesic_distance": round(0.0, DECIMAL_PLACES),
                f"{prefix}distance_3d": round(0.0, DECIMAL_PLACES),
                f"{prefix}avg_velocity": round(0.0, DECIMAL_PLACES),
                f"{prefix}displacement_direction": round(0.0, DECIMAL_PLACES),
            }

        dt_curr, _ = CustomPhotosFieldsUtil.resolve_capture_datetime(data)
        dt_other, _ = CustomPhotosFieldsUtil.resolve_capture_datetime(other_data)
        if dt_curr is None or dt_other is None:
            prefix = f"{direction}_"
            return {
                f"{prefix}time_since": round(0.0, DECIMAL_PLACES),
                f"{prefix}geodesic_distance": round(0.0, DECIMAL_PLACES),
                f"{prefix}distance_3d": round(0.0, DECIMAL_PLACES),
                f"{prefix}avg_velocity": round(0.0, DECIMAL_PLACES),
                f"{prefix}displacement_direction": round(0.0, DECIMAL_PLACES),
            }
        dt_diff = abs((dt_curr - dt_other).total_seconds())

        # GPS (haversine precisa lat/lon reais - usar LRFTarget se GPS None)
        lat_curr = CustomPhotosFieldsUtil.safe_float(
            data.get("LRFTargetLat") or data.get("GpsLatitude", 0)
        )
        lon_curr = CustomPhotosFieldsUtil.safe_float(
            data.get("LRFTargetLon") or data.get("GpsLongitude", 0)
        )
        lat_other = CustomPhotosFieldsUtil.safe_float(
            other_data.get("LRFTargetLat") or other_data.get("GpsLatitude", 0)
        )
        lon_other = CustomPhotosFieldsUtil.safe_float(
            other_data.get("LRFTargetLon") or other_data.get("GpsLongitude", 0)
        )

        geo_dist = CustomPhotosFieldsUtil.haversine(lat_curr, lon_curr, lat_other, lon_other)
        alt_curr = CustomPhotosFieldsUtil.safe_float(data.get("AbsoluteAltitude", 0))
        alt_other = CustomPhotosFieldsUtil.safe_float(other_data.get("AbsoluteAltitude", 0))
        alt_diff = abs(alt_curr - alt_other)
        dist_3d = math.sqrt(geo_dist**2 + alt_diff**2)

        avg_vel = dist_3d / dt_diff if dt_diff > 0 else 0.0
        dir_displ = CustomPhotosFieldsUtil.bearing_angle(lat_curr, lon_curr, lat_other, lon_other)

        prefix = f"{direction}_"
        return {
            f"{prefix}time_since": round(dt_diff, DECIMAL_PLACES),
            f"{prefix}geodesic_distance": round(geo_dist, DECIMAL_PLACES),
            f"{prefix}distance_3d": round(dist_3d, DECIMAL_PLACES),
            f"{prefix}avg_velocity": round(avg_vel, DECIMAL_PLACES),
            f"{prefix}displacement_direction": round(dir_displ, DECIMAL_PLACES),
        }

    @staticmethod
    def _calculate_individual_fields(data: Dict) -> Dict:
        # Campos custom individuais derivados (speed_3d calculated here)
        shutter_count = CustomPhotosFieldsUtil.safe_int(data.get("ShutterCount", 0))
        shutter_life_pct = (shutter_count / 400000) * 100

        lrf_distance_m = CustomPhotosFieldsUtil.safe_float(data.get("LRFTargetDistance", 0))
        focal_length_mm = CustomPhotosFieldsUtil.safe_float(data.get("FocalLength", 12.29))
        sensor_width_mm = 7.49  # M3E/M4E sensor width
        img_w_px = CustomPhotosFieldsUtil.safe_float(data.get("ExifImageWidth", 5280))

        if lrf_distance_m == 0:
            lrf_distance_m = CustomPhotosFieldsUtil.safe_float(data.get("AbsoluteAltitude", 0)) * 0.85

        pixel_pitch_mm = sensor_width_mm / img_w_px
        gsd_cm_px = (lrf_distance_m * pixel_pitch_mm / focal_length_mm * 100) if lrf_distance_m > 0 and focal_length_mm > 0 else 0
        gsd_m_px = gsd_cm_px / 100

        # Heat index
        sens_temp = CustomPhotosFieldsUtil.safe_float(data.get("SensorTemperature"))
        lens_temp = CustomPhotosFieldsUtil.safe_float(data.get("LensTemperature"))
        total_heat_index = (sens_temp + lens_temp) / 2 if sens_temp > 0 and lens_temp > 0 else (sens_temp or lens_temp or 0.0)

        # Speed 3D for blur risk
        xspd = CustomPhotosFieldsUtil.safe_float(data.get("FlightXSpeed", 0))
        yspd = CustomPhotosFieldsUtil.safe_float(data.get("FlightYSpeed", 0))
        zspd = CustomPhotosFieldsUtil.safe_float(data.get("FlightZSpeed", 0))
        speed_3d = math.sqrt(xspd**2 + yspd**2 + zspd**2)

        # New fields
        exp_time = CustomPhotosFieldsUtil.safe_float(data.get("ExposureTime", 0))
        fnumber = CustomPhotosFieldsUtil.safe_float(data.get("FNumber", 2.8))
        
        motion_blur_risk = (speed_3d * exp_time / gsd_m_px) if gsd_m_px > 0 else 0.0
        exposure_value_ev = math.log2(fnumber**2 / exp_time) if exp_time > 0 else 0.0

        coverage_width = CustomPhotosFieldsUtil.safe_float(data.get("AbsoluteAltitude", 0)) * CustomPhotosFieldsUtil.COVERAGE_FACTOR

        return {
            "shutter_life_pct": round(shutter_life_pct, DECIMAL_PLACES),
            "ground_sample_distance_cm": round(gsd_cm_px, DECIMAL_PLACES),
            "total_heat_index": round(total_heat_index, DECIMAL_PLACES),
            "motion_blur_risk": round(motion_blur_risk, DECIMAL_PLACES),
            "exposure_value_ev": round(exposure_value_ev, DECIMAL_PLACES),
            "coverage_width": round(coverage_width, DECIMAL_PLACES),
            "linear_velocity_instant": round(speed_3d, DECIMAL_PLACES),
        }

    @staticmethod
    def _calculate_gimbal_offset(gim_yaw: float, flight_yaw: float) -> float:
        """Calcula o offset do gimbal baseado na diferenÃ§a mÃ­nima com flight yaw."""
        # Normaliza Ã¢ngulos para 0-360
        gim_yaw_norm = (gim_yaw % 360 + 360) % 360
        flight_yaw_norm = (flight_yaw % 360 + 360) % 360
        
        # DiferenÃ§a absoluta
        diff = abs(gim_yaw_norm - flight_yaw_norm)
        diff_min = min(diff, 360 - diff)
        if diff > 150 and diff < 300:
            diff = abs(180 - diff)
        elif diff > 300:
            diff = abs(360 - diff)
        # Ajuste para casos extremos (ex: 10Â° vs 190Â°)
        # Offset = |diff_min - 180|
        return abs(diff)

    @staticmethod
    def _calculate_gimbal_3d(data: Dict, prev_dir: float = None) -> Dict:
        """GimbalOffset, 3DSpeed + yaw_alignment_error."""
        gim_yaw = CustomPhotosFieldsUtil.safe_float(data.get("GimbalYawDegree", 0))
        flight_yaw = CustomPhotosFieldsUtil.safe_float(data.get("FlightYawDegree", 0))
        gimbal_offset = CustomPhotosFieldsUtil._calculate_gimbal_offset(gim_yaw, flight_yaw)

        xspd = CustomPhotosFieldsUtil.safe_float(data.get("FlightXSpeed", 0))
        yspd = CustomPhotosFieldsUtil.safe_float(data.get("FlightYSpeed", 0))
        zspd = CustomPhotosFieldsUtil.safe_float(data.get("FlightZSpeed", 0))
        speed_3d = math.sqrt(xspd**2 + yspd**2 + zspd**2)

        displacement_dir = prev_dir if prev_dir is not None else flight_yaw
        yaw_alignment_error = min(abs(flight_yaw - displacement_dir), 360 - abs(flight_yaw - displacement_dir))

        yaw_alignment_error = min(abs(flight_yaw - displacement_dir), 360 - abs(flight_yaw - displacement_dir))

        return {
            "gimbal_offset": round(gimbal_offset, DECIMAL_PLACES),
            "speed_3d": round(speed_3d, DECIMAL_PLACES),
            "speed_3d_kmh": round(speed_3d * 3.6, 1),
            "yaw_alignment_error": round(yaw_alignment_error, DECIMAL_PLACES),
        }

    @staticmethod
    def _get_light_source_label(light_source: any) -> str:
        """Retorna o texto da fonte de luz a partir do cÃ³digo LightSource EXIF."""
        code = CustomPhotosFieldsUtil.safe_int(light_source, default=0)
        return LightSourceEnum.get_label(code)

    @staticmethod
    def _check_light_consistency(light_source: any, cct: any) -> str:
        """Verifica se o valor de CCT estÃ¡ coerente com a fonte de luz declarada."""
        code = CustomPhotosFieldsUtil.safe_int(light_source, default=0)
        cct_value = CustomPhotosFieldsUtil.safe_float(cct, default=0.0)
        if cct_value <= 0:
            return "Unknown"

        expected_ranges = {
            1: (5200, 6500),
            2: (3000, 6500),
            3: (2800, 3200),
            4: (4500, 6500),
            9: (6000, 7500),
            10: (6500, 7500),
            11: (7000, 10000),
            12: (5700, 7100),
            13: (4600, 5400),
            14: (3800, 4500),
            15: (3250, 3800),
            16: (2600, 3250),
            17: (2800, 3300),
            18: (5000, 6500),
            19: (5000, 6500),
            20: (5400, 5600),
            21: (6400, 6600),
            22: (7400, 7600),
            23: (4900, 5100),
            24: (3000, 3300),
        }

        expected = expected_ranges.get(code)
        if expected is None:
            label = CustomPhotosFieldsUtil._get_light_source_label(code)
            if "daylight" in label.lower():
                expected = (5200, 7500)
            elif "fluorescent" in label.lower():
                expected = (2600, 7100)
            elif "shade" in label.lower():
                expected = (7000, 10000)
            elif "tungsten" in label.lower():
                expected = (2600, 3300)
            elif "flash" in label.lower():
                expected = (4500, 6500)
            else:
                return "Unknown"

        low, high = expected
        return "Consistent" if low <= cct_value <= high else "Inconsistent"

    @staticmethod
    def _calculate_quality_scores(
        data: Dict,
        prev_data: Optional[Dict],
        valid_prev: bool,
        prev_seq: Optional[Dict] = None,
        coverage_width: float = 0.0,
        yaw_alignment_error: float = 0.0,
        motion_blur_risk: float = 0.0,
    ) -> Dict:
        """RTK precision, overlap, ortho score, estabilidade e Ã­ndices."""
        if prev_seq is None:
            prev_seq = {
                "prev_time_since": 0.0,
                "prev_geodesic_distance": 0.0,
                "prev_distance_3d": 0.0,
                "prev_avg_velocity": 0.0,
                "prev_displacement_direction": 0.0,
            }
        # RTK Precision
        rtk_flag = data.get("RtkFlag")
        rtk_stds = [
            CustomPhotosFieldsUtil.safe_float(data.get("RtkStdLon", 999)),
            CustomPhotosFieldsUtil.safe_float(data.get("RtkStdLat", 999)),
            CustomPhotosFieldsUtil.safe_float(data.get("RtkStdHgt", 999)),
        ]
        avg_std = sum(rtk_stds) / 3

        if rtk_flag == "50" and avg_std < 0.02:
            rtk_prec = "Alta"
        elif avg_std < 0.1:
            rtk_prec = "MÃ©dia"
        elif avg_std < 1.0:
            rtk_prec = "Baixa"
        else:
            rtk_prec = "Sem RTK"

        prev_avg_std = 0.0
        rtk_stability_score = 0.0
        if valid_prev and prev_data is not None:
            prev_rtk_stds = [
                CustomPhotosFieldsUtil.safe_float(prev_data.get("RtkStdLon", 999)),
                CustomPhotosFieldsUtil.safe_float(prev_data.get("RtkStdLat", 999)),
                CustomPhotosFieldsUtil.safe_float(prev_data.get("RtkStdHgt", 999)),
            ]
            prev_avg_std = sum(prev_rtk_stds) / 3
            rtk_stability_score = max(
                0.0,
                100.0 - min(100.0, abs(avg_std - prev_avg_std) * 100.0),
            )

        # Incidence angle
        gim_pitch = CustomPhotosFieldsUtil.safe_float(data.get("GimbalPitchDegree", 0))
        flight_pitch = CustomPhotosFieldsUtil.safe_float(data.get("FlightPitchDegree", 0))
        inc_angle = round(abs(gim_pitch + flight_pitch), DECIMAL_PLACES)

        # Predicted overlap
        pred_overlap = 0.0
        if valid_prev and coverage_width > 0:
            pred_overlap = max(
                0.0,
                min(
                    100.0,
                    (1.0 - prev_seq.get("prev_geodesic_distance", 0.0) / coverage_width) * 100.0,
                ),
            )

        # Ortho score
        score = 0
        if rtk_prec == "Alta":
            score += 30
        if inc_angle < 5:
            score += 25
        if data.get("DewarpFlag") == "0":
            score += 20
        if CustomPhotosFieldsUtil.safe_float(data.get("RtkDiffAge", 999)) < 2:
            score += 15
        if pred_overlap > 70:
            score += 10
        ortho_potential = min(100, score)

        # Flags
        abrupt_flag = False  # atualiza depois com mediana do conjunto
        ideal_overlap = pred_overlap >= CustomPhotosFieldsUtil.IDEAL_OVERLAP

        # Angular velocity gimbal
        gim_ang_vel = 0.0
        if valid_prev and prev_data is not None and prev_seq["prev_time_since"] > 0:
            prev_gim_yaw = CustomPhotosFieldsUtil.safe_float(prev_data.get("GimbalYawDegree", 0))
            curr_gim_yaw = CustomPhotosFieldsUtil.safe_float(data.get("GimbalYawDegree", 0))
            yaw_diff = CustomPhotosFieldsUtil.angle_difference(curr_gim_yaw, prev_gim_yaw)
            gim_ang_vel = yaw_diff / prev_seq["prev_time_since"]

        # Vertical stability
        vertical_stability = 0.0
        if valid_prev and prev_data is not None:
            alt_curr = CustomPhotosFieldsUtil.safe_float(data.get("AbsoluteAltitude", 0))
            alt_prev = CustomPhotosFieldsUtil.safe_float(prev_data.get("AbsoluteAltitude", 0))
            vertical_stability = abs(alt_curr - alt_prev)

        # Speed variation
        speed_variation_index = 0.0
        if valid_prev and prev_data is not None:
            prev_speed = math.sqrt(
                CustomPhotosFieldsUtil.safe_float(prev_data.get("FlightXSpeed", 0)) ** 2
                + CustomPhotosFieldsUtil.safe_float(prev_data.get("FlightYSpeed", 0)) ** 2
                + CustomPhotosFieldsUtil.safe_float(prev_data.get("FlightZSpeed", 0)) ** 2
            )
            current_speed = math.sqrt(
                CustomPhotosFieldsUtil.safe_float(data.get("FlightXSpeed", 0)) ** 2
                + CustomPhotosFieldsUtil.safe_float(data.get("FlightYSpeed", 0)) ** 2
                + CustomPhotosFieldsUtil.safe_float(data.get("FlightZSpeed", 0)) ** 2
            )
            mean_speed = statistics.mean([prev_speed, current_speed])
            if mean_speed > 0:
                speed_variation_index = statistics.pstdev([prev_speed, current_speed]) / mean_speed

        capture_efficiency = (
            prev_seq.get("prev_geodesic_distance", 0.0) / coverage_width
            if valid_prev and coverage_width > 0
            else 0.0
        )

        photogrammetry_quality_index = min(
            100,
            ortho_potential
            + (10 if motion_blur_risk < CustomPhotosFieldsUtil.BLUR_THRESHOLD else 0)
            + (10 if yaw_alignment_error < 5 else 0)
            + (10 if pred_overlap >= CustomPhotosFieldsUtil.IDEAL_OVERLAP else 0),
        )

        return {
            "rtk_effective_precision": rtk_prec,
            "incidence_angle": inc_angle,
            "predicted_overlap": round(pred_overlap, DECIMAL_PLACES),
            "is_ideal_overlap": ideal_overlap,
            "abrupt_change_flag": abrupt_flag,
            "gimbal_angular_velocity": round(gim_ang_vel, DECIMAL_PLACES),
            "orthorectification_potential": round(ortho_potential, DECIMAL_PLACES),
            "vertical_stability": round(vertical_stability, DECIMAL_PLACES),
            "speed_variation_index": round(speed_variation_index, DECIMAL_PLACES),
            "rtk_stability_score": round(rtk_stability_score, DECIMAL_PLACES),
            "capture_efficiency": round(capture_efficiency, DECIMAL_PLACES),
            "photogrammetry_quality_index": round(
                photogrammetry_quality_index, DECIMAL_PLACES
            ),
        }

    @classmethod
    def calculate_all_custom_fields(
        cls,
        metadata_dict: Dict[str, Dict],
        tool_key: str = ToolKey.UNTRACEABLE,
    ) -> Dict[str, Dict]:
        """Orquestra todos calculos custom."""
        logger = cls._get_logger(tool_key)
        logger.debug(
            f"Iniciando calculo de campos custom para {len(metadata_dict) if metadata_dict else 0} fotos"
        )
        if not metadata_dict:
            return {}

        dt_source_counts = {}
        missing_datetime_count = 0
        for _, data in metadata_dict.items():
            dt, source = cls.resolve_capture_datetime(data or {})
            if dt is None:
                missing_datetime_count += 1
                continue
            dt_source_counts[source] = dt_source_counts.get(source, 0) + 1
            if data.get("DateTimeOriginal") in (None, "", "None", "null"):
                data["DateTimeOriginal"] = dt.strftime("%Y:%m:%d %H:%M:%S")
            if data.get("DtFull") in (None, "", "None", "null"):
                data["DtFull"] = dt.strftime("%Y%m%d%H%M")
            if data.get("DtDate") in (None, "", "None", "null"):
                data["DtDate"] = dt.strftime("%Y%m%d")
            if data.get("DtTime") in (None, "", "None", "null"):
                data["DtTime"] = dt.strftime("%H%M")

        # Ordenar por datetime
        sorted_items = sorted(
            metadata_dict.items(),
            key=lambda x: cls.resolve_capture_datetime(x[1])[0] or datetime.max,
        )
        logger.info(
            "Fallback de datetime aplicado no calculo custom",
            code="CUSTOM_FIELDS_DATETIME_FALLBACK",
            data={
                "total_items": len(metadata_dict),
                "missing_datetime_count": missing_datetime_count,
                "datetime_sources": dt_source_counts,
            },
        )

        result = {}
        prev_segment_dir = None
        strip_id = 1
        prev_time_values: List[float] = []
        prev_geo_values: List[float] = []

        for i, (filename, data) in enumerate(sorted_items):
            prev_item = sorted_items[i - 1] if i > 0 else None
            prev_prev_item = sorted_items[i - 2] if i > 1 else None
            next_item = sorted_items[i + 1] if i < len(sorted_items) - 1 else None

            prev_data = prev_item[1] if prev_item else None
            prev_prev_data = prev_prev_item[1] if prev_prev_item else None
            next_data = next_item[1] if next_item else None

            # ValidaÃ§Ãµes sequÃªncia
            valid_prev = cls.is_valid_sequence(data, prev_data)
            valid_next = cls.is_valid_sequence(next_data, data) if next_data else False

            # SequÃªncia campos
            prev_seq = cls._calculate_sequence_fields(
                data, prev_data, valid_prev, "prev"
            )
            next_seq = cls._calculate_sequence_fields(
                data, next_data, valid_next, "next"
            )

            estimated_coverage = cls.calculate_estimated_coverage(data)
            coverage_width, coverage_height = estimated_coverage

            # Campos individuais NOVOS
            individual = cls._calculate_individual_fields(data)

            # Outros
            gim_3d = cls._calculate_gimbal_3d(
                data,
                prev_seq["prev_displacement_direction"] if valid_prev else None,
            )
            quality = cls._calculate_quality_scores(
                data,
                prev_data,
                valid_prev,
                prev_seq,
                coverage_width,
                gim_3d["yaw_alignment_error"],
                individual["motion_blur_risk"],
            )

            current_segment_dir = prev_seq["prev_displacement_direction"] if valid_prev else None
            trajectory_smoothness = 0.0
            if current_segment_dir is not None and prev_segment_dir is not None:
                trajectory_smoothness = cls.angle_difference(
                    current_segment_dir, prev_segment_dir
                )
                if trajectory_smoothness > cls.STRIP_CHANGE_THRESHOLD:
                    strip_id += 1

            if current_segment_dir is not None:
                prev_segment_dir = current_segment_dir

            validation = {
                "is_valid_sequence_prev": valid_prev,
                "is_valid_sequence_next": valid_next,
                "voo_id": cls.get_voo_id(data),
            }

            custom = {
                **individual,
                **quality,
                **next_seq,
                **validation,
                "GimbalOffset": round(gim_3d["gimbal_offset"], DECIMAL_PLACES),
                "3DSpeed": round(gim_3d["speed_3d"], DECIMAL_PLACES),
                "speed_3d_kmh": round(gim_3d["speed_3d_kmh"], 1),
                "yaw_alignment_error": round(gim_3d["yaw_alignment_error"], DECIMAL_PLACES),
                "time_since_previous": round(prev_seq["prev_time_since"], DECIMAL_PLACES),
                "geodesic_distance_previous": round(prev_seq["prev_geodesic_distance"], DECIMAL_PLACES),
                "distance_3d_previous": round(prev_seq["prev_distance_3d"], DECIMAL_PLACES),
                "avg_velocity_between_photos": round(prev_seq["prev_avg_velocity"], DECIMAL_PLACES),
                "displacement_direction": round(prev_seq["prev_displacement_direction"], DECIMAL_PLACES),
                "estimated_coverage": estimated_coverage,
                "coverage_width": round(coverage_width, DECIMAL_PLACES),
                "trajectory_smoothness": round(trajectory_smoothness, DECIMAL_PLACES),
                "strip_id": strip_id,
                "light_source_classification": cls._get_light_source_label(data.get("LightSource")),
                "light_consistency": cls._check_light_consistency(
                    data.get("LightSource"), data.get("WhiteBalanceCCT")
                ),
            }

            if valid_prev:
                prev_time_values.append(custom["time_since_previous"])
                prev_geo_values.append(custom["geodesic_distance_previous"])

            result[filename] = {**data, **custom}

        median_time = statistics.median(prev_time_values) if prev_time_values else 0.0
        median_geo = statistics.median(prev_geo_values) if prev_geo_values else 0.0
        for filename, item in result.items():
            if (
                median_time > 0
                and item.get("time_since_previous", 0.0) > median_time * 2
            ) or (
                median_geo > 0
                and item.get("geodesic_distance_previous", 0.0) > median_geo * 2
            ):
                item["abrupt_change_flag"] = True

        return result

