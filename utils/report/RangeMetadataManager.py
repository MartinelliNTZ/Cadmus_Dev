import math
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from ...core.config.LogUtils import LogUtils
from ..ToolKeys import ToolKey


class RangeMetadataManager:
    """Fonte unica para configuracao de thresholds e classificacao de niveis."""

    _instance = None
    DEFAULT_CONFIG_PATH = (
        Path(__file__).resolve().parents[2] / "resources" / "reports" / "config.yaml"
    )

    def __new__(cls):
        """Garante instancia unica para compartilhamento de configuracao carregada."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = None
            cls._instance._logger = LogUtils(
                tool=ToolKey.UNTRACEABLE,
                class_name="RangeMetadataManager",
            )
        return cls._instance

    def load(
        self,
        config_path: str = None,
        tool_key: str = ToolKey.UNTRACEABLE,
    ) -> None:
        """Carrega configuracoes de thresholds e mensagens a partir de arquivo YAML."""
        self._logger = LogUtils(tool=tool_key, class_name="RangeMetadataManager")
        target_path = config_path or str(self.DEFAULT_CONFIG_PATH)
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
            total = len((self._config or {}).get("thresholds", {}))
            self._logger.info(
                f"Config de report carregada: {target_path} ({total} indicadores)"
            )
        except Exception as e:
            raise ValueError(f"Erro carregando config: {e}")

    def get_thresholds(self, indicator: str) -> Optional[Dict[str, Any]]:
        """Retorna a configuracao de threshold de um indicador especifico."""
        if self._config is None:
            return None
        return self._config.get("thresholds", {}).get(indicator)

    def get_templates(self) -> Dict[str, str]:
        """Retorna configuracoes de templates definidas no YAML, quando existirem."""
        if self._config is None:
            return {}
        return self._config.get("templates", {})

    @staticmethod
    def _parse_num(raw: Any) -> float:
        """Converte um valor textual ou numerico em float com suporte a infinitos."""
        if raw is None:
            return math.inf
        if isinstance(raw, (int, float)):
            return float(raw)
        text = str(raw).strip().lower()
        if text in {"inf", "+inf", "infinity", "+infinity", "float('inf')", 'float("inf")'}:
            return math.inf
        if text in {"-inf", "-infinity", "float('-inf')", 'float("-inf")'}:
            return -math.inf
        return float(text)

    def classify(self, indicator: str, value: Any) -> Tuple[int, str]:
        """Classifica um valor em nivel (1..5) e mensagem conforme regra do indicador."""
        if self._config is None:
            self.load()

        thresh = self.get_thresholds(indicator)
        if not thresh:
            return 3, f"Indicator {indicator} nao configurado (OK default)"

        ttype = thresh.get("type")
        levels = thresh.get("levels", [])
        messages = thresh.get("messages", [f"Nivel {{}}" for _ in levels])

        if ttype == "categorical":
            mapping = thresh.get("mapping", {})
            if value in mapping:
                level = mapping[value]
            else:
                level = mapping.get(str(value), 3)
            msg_idx = level - 1 if 1 <= level <= 5 else 2
            msg = messages[msg_idx] if msg_idx < len(messages) else f"Nivel {level}"
            return level, msg

        try:
            vnum = self._parse_num(value)
        except (ValueError, TypeError):
            return 3, f"Valor invalido para {indicator}: {value}"

        if ttype == "higher_better":
            try:
                level = sum(1 for cut in levels if vnum >= self._parse_num(cut))
            except Exception:
                level = 3
        elif ttype == "lower_better":
            try:
                level = sum(1 for cut in levels if vnum <= self._parse_num(cut))
            except Exception:
                level = 3
        elif ttype == "range_best":
            for i, interval in enumerate(levels):
                if isinstance(interval, list):
                    minv = self._parse_num(interval[0]) if len(interval) > 0 else -math.inf
                    maxv = self._parse_num(interval[1]) if len(interval) > 1 else math.inf
                else:
                    minv, maxv = -math.inf, self._parse_num(interval)
                maxv = math.inf if maxv is None else maxv
                if minv <= vnum <= maxv:
                    return i + 1, messages[i]
            level = 3
        else:
            level = 3

        level = max(1, min(5, level))
        msg = messages[level - 1] if level - 1 < len(messages) else f"Nivel {level}"
        return level, msg


range_metadata_manager = RangeMetadataManager()
