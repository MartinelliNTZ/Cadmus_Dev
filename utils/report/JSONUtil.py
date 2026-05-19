import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...core.config.LogUtils import LogUtils
from ..ToolKeys import ToolKey
from ..adapter.StringAdapter import StringAdapter
from ..mrk.MetadataFields import MetadataFields
from ..JsonUtil import JsonUtil


class JSONUtil:
    """Responsavel por leitura e normalizacao dos JSONs de metadata."""

    @staticmethod
    def _get_logger(tool_key: str = ToolKey.UNTRACEABLE) -> LogUtils:
        return LogUtils(tool=tool_key, class_name="JSONUtil")

    @staticmethod
    def _normalize_record(
        record: Dict[str, Any],
        *,
        group_path: str = "",
        file_key: str = "",
    ) -> Dict[str, Any]:
        """Normaliza um registro bruto para o formato canonico baseado em MetadataFields."""
        if not isinstance(record, dict):
            return {}

        normalized = MetadataFields.normalize_record_to_keys(record)

        catalog = MetadataFields.all_fields()
        known_keys = StringAdapter.filter_known_keys(normalized.keys(), catalog)
        out = {key: normalized.get(key) for key in known_keys}

        # Preserva campos extras nao catalogados (pipeline custom pode gerar campos novos).
        for key, value in normalized.items():
            if key not in out:
                out[key] = value

        if out.get("File") in (None, "") and file_key:
            out["File"] = file_key
        if out.get("Path") in (None, "") and file_key:
            out["Path"] = str(Path(group_path) / file_key) if group_path else file_key

        return out

    @staticmethod
    def load_json_file(json_path: str, tool_key: str = ToolKey.UNTRACEABLE) -> Any:
        """Le um arquivo JSON do disco e retorna o objeto desserializado."""
        logger = JSONUtil._get_logger(tool_key)
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"JSON nao encontrado: {json_path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"JSON carregado: {json_path}")
        return data

    @staticmethod
    def load_timestamps(
        json_path: str,
        tool_key: str = ToolKey.UNTRACEABLE,
    ) -> Dict[str, str]:
        """Carrega apenas o bloco de timestamps do JSON v2.0.

        Retorna dict vazio se nao houver timestamps ou se o JSON nao for v2.0.
        """
        logger = JSONUtil._get_logger(tool_key)
        try:
            path = Path(json_path)
            if not path.exists():
                logger.warning(f"JSON nao encontrado para extrair timestamps: {json_path}")
                return {}

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            version = data.get("schema_version")
            if version != "2.0":
                logger.debug(f"JSON com schema_version='{version}' nao possui timestamps v2.0")
                return {}

            timestamps = data.get("timestamps", {})
            if not isinstance(timestamps, dict) or not timestamps:
                logger.debug("Nenhum timestamp encontrado no JSON")
                return {}

            logger.info(f"Timestamps carregados: {len(timestamps)} entradas")
            return dict(timestamps)

        except Exception as e:
            logger.warning(f"Erro ao carregar timestamps: {e}")
            return {}

    @staticmethod
    def load_json_metadata(json_path: str, tool_key: str = ToolKey.UNTRACEABLE) -> Dict[str, Any]:
        """Carrega metadados do JSON raiz: titulo, logotipo, generated_at.

        Args:
            json_path: Caminho do arquivo JSON

        Returns:
            Dict com 'titulo', 'logotipo', 'generated_at' (se existirem no JSON)
        """
        logger = JSONUtil._get_logger(tool_key)
        meta: Dict[str, Any] = {}
        try:
            data = JSONUtil.load_json_file(json_path, tool_key=tool_key)
            if isinstance(data, dict):
                if data.get("titulo"):
                    meta["titulo"] = data["titulo"]
                if data.get("logotipo"):
                    meta["logotipo"] = data["logotipo"]
                if data.get("generated_at"):
                    raw = str(data["generated_at"])
                    meta["generated_at_raw"] = raw
                    # Tenta converter para formato humanizado
                    try:
                        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                        meta["generated_at"] = dt.strftime("%d/%m/%Y %H:%M:%S")
                    except (ValueError, TypeError):
                        meta["generated_at"] = raw
            logger.debug(f"Metadados carregados: {meta}")
        except Exception as e:
            logger.warning(f"Erro ao carregar metadados do JSON: {e}")
        return meta

    @staticmethod
    def compute_processing_summary(timestamps: Dict[str, str]) -> Dict[str, Any]:
        """Calcula tempos de processamento a partir do dicionario de timestamps.

        Args:
            timestamps: Dict com chaves como pipeline_start, mrk_start, mrk_end, etc.

        Returns:
            Dict com:
                - total_seconds: float (tempo total pipeline_start -> report_end)
                - total_formatted: str (HH:MM:SS)
                - stages: List[Dict] com nome, inicio, fim, duracao_seg, duracao_formatada
                - all_present: bool (se todos os timestones esperados existem)
                - missing_stages: List[str] (etapas que faltam)
        """
        from datetime import datetime

        def _parse_ts(ts_str: str) -> Optional[datetime]:
            if not ts_str:
                return None
            try:
                return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return None

        # Define etapas esperadas no pipeline
        stage_defs = [
            ("initial_start", "initial_end", "Varredura"),
            ("mrk_start", "mrk_end", "MRK"),
            ("exif_start", "exif_end", "EXIF"),
            ("xmp_start", "xmp_end", "XMP"),
            ("custom_start", "custom_end", "Custom"),
            ("vectorization_start", "vectorization_end", "Vetorizacao"),
            ("report_start", "report_end", "Relatorio"),
        ]

        parsed = {k: _parse_ts(v) for k, v in timestamps.items()}

        stages = []
        missing_stages = []
        total_stage_seconds = 0.0

        for start_key, end_key, label in stage_defs:
            start_dt = parsed.get(start_key)
            end_dt = parsed.get(end_key)

            if start_dt is None or end_dt is None:
                missing_stages.append(label)
                stages.append({
                    "label": label,
                    "start": timestamps.get(start_key, ""),
                    "end": timestamps.get(end_key, ""),
                    "duration_seconds": None,
                    "duration_formatted": "N/A",
                    "present": False,
                })
                continue

            duration = (end_dt - start_dt).total_seconds()
            total_stage_seconds += duration

            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = duration % 60

            if hours > 0:
                dur_fmt = f"{hours}h {minutes:02d}m {seconds:05.2f}s"
            elif minutes > 0:
                dur_fmt = f"{minutes}m {seconds:05.2f}s"
            else:
                dur_fmt = f"{seconds:.2f}s"

            stages.append({
                "label": label,
                "start": timestamps.get(start_key, ""),
                "end": timestamps.get(end_key, ""),
                "duration_seconds": round(duration, 3),
                "duration_formatted": dur_fmt,
                "present": True,
            })

        # Tempo total pipeline_start -> report_end
        pipeline_start = parsed.get("pipeline_start")
        report_end = parsed.get("report_end")

        if pipeline_start and report_end:
            total_seconds = (report_end - pipeline_start).total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            secs = total_seconds % 60

            if hours > 0:
                total_formatted = f"{hours}h {minutes:02d}m {secs:05.2f}s"
            elif minutes > 0:
                total_formatted = f"{minutes}m {secs:05.2f}s"
            else:
                total_formatted = f"{secs:.2f}s"
        else:
            total_seconds = total_stage_seconds if total_stage_seconds > 0 else None
            if total_seconds is not None:
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                secs = total_seconds % 60
                if hours > 0:
                    total_formatted = f"{hours}h {minutes:02d}m {secs:05.2f}s"
                elif minutes > 0:
                    total_formatted = f"{minutes}m {secs:05.2f}s"
                else:
                    total_formatted = f"{secs:.2f}s"
            else:
                total_formatted = "N/A"

        # Timestamps individuais formatados sem timezone para exibicao
        formatted_individual = {}
        for key, dt in parsed.items():
            if dt is not None:
                formatted_individual[key] = dt.strftime("%H:%M:%S.%f")[:-3]
            else:
                formatted_individual[key] = timestamps.get(key, "N/A")

        # Pipeline start/end formatados
        pipeline_start_str = timestamps.get("pipeline_start", "")
        report_end_str = timestamps.get("report_end", "")

        all_present = len(missing_stages) == 0

        return {
            "total_seconds": round(total_seconds, 3) if total_seconds is not None else None,
            "total_formatted": total_formatted,
            "stages": stages,
            "missing_stages": missing_stages,
            "all_present": all_present,
            "pipeline_start": pipeline_start_str,
            "pipeline_end": report_end_str,
            "formatted_individual": formatted_individual,
        }

    @staticmethod
    def load_records(
        json_path: str = "metadata_completa_custom.json",
        tool_key: str = ToolKey.UNTRACEABLE,
    ) -> List[Dict[str, Any]]:
        """
        Carrega registros de metadata suportando JSON v2.0 e formatos legados.

        Para JSON v2.0: usa JsonUtil.load_records() que valida schema_version="2.0"
        Para formatos legados: mantém compatibilidade
        """
        logger = JSONUtil._get_logger(tool_key)

        try:
            # Tentar carregar como JSON v2.0 primeiro
            records = JsonUtil.load_records(json_path)
            logger.info(f"load_records: carregadas {len(records)} imagens de JSON v2.0")
            return records

        except ValueError as e:
            if "schema_version" in str(e):
                # Não é v2.0, tentar formatos legados
                logger.debug(f"JSON não é v2.0 ({e}), tentando formatos legados")
            else:
                raise

        # Fallback para formatos legados
        data = JSONUtil.load_json_file(json_path, tool_key=tool_key)

        if isinstance(data, dict) and isinstance(data.get("groups"), dict):
            images: List[Dict[str, Any]] = []
            total_raw = 0
            for group_path, group_payload in data["groups"].items():
                raw_records = (group_payload or {}).get("raw_records", {})
                if not isinstance(raw_records, dict):
                    continue
                total_raw += len(raw_records)
                for file_key, raw_record in raw_records.items():
                    images.append(
                        JSONUtil._normalize_record(
                            raw_record,
                            group_path=group_path,
                            file_key=file_key,
                        )
                    )
            logger.info(
                f"load_records: carregadas {len(images)} imagens de json legado (raw_records={total_raw})"
            )
            return images

        if isinstance(data, dict):
            images: List[Dict[str, Any]] = []
            for file_key, record in data.items():
                if isinstance(record, dict):
                    images.append(JSONUtil._normalize_record(record, file_key=file_key))
            logger.info(
                f"load_records: carregadas {len(images)} imagens de {len(data)} chaves (formato legado)"
            )
            return images

        raise ValueError(f"Formato JSON nao suportado em {json_path}")