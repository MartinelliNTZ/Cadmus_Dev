from __future__ import annotations

import re

from typing import Any, Dict, List, Optional

from ..StringManager import StringManager
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
        """Converte valor para float com tratamento de nulos e strings vazias."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace("+", "")
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

    def _derive_speed_3d_ms(self) -> Optional[float]:
        """Deriva velocidade 3D em m/s usando campo explicito ou conversao de km/h."""
        explicit_ms = self._to_float(self._first_value(["3DSpeed", "speed_3d_ms"]))
        if explicit_ms is not None:
            return explicit_ms
        kmh = self._to_float(self._first_value(["Speed3dKmh", "speed_3d_kmh"]))
        if kmh is None:
            return None
        return kmh / 3.6

    def _derive_incidence_angle(self) -> Optional[float]:
        """Deriva angulo de incidencia a partir do campo explicito ou do pitch do gimbal."""
        explicit = self._to_float(self._first_value(["IncidenceAngle", "incidence_angle"]))
        if explicit is not None:
            return explicit
        pitch = self._to_float(self._first_value(["GimbalPitchDegree", "gimbal_pitch_degree"]))
        return abs(pitch) if pitch is not None else None

    def get_indicator(self, key: str) -> Any:
        """Obtém o valor de um indicador com suporte a aliases e campos derivados."""
        norm = _normalize_key(key)
        if norm == "speed_3d_ms":
            return self._derive_speed_3d_ms()
        if norm == "incidence_angle":
            return self._derive_incidence_angle()
        if norm == "sensor_temp_c":
            return self._to_float(self._first_value(["SensorTemperature", "LensTemperature", "sensor_temp_c"]))
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

        for field_key in level5_field_keys:
            value = self.get_indicator(field_key)
            if value is not None:
                self.level5_values[field_key] = value

        score = (total / count) if count > 0 else 0.0
        self.overall_score = round(score, 1)
        return self

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
