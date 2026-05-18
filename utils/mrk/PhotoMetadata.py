# -*- coding: utf-8 -*-
import os
import re
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime

from ...core.config.LogUtils import LogUtils
from ...core.enum import MetadataFieldKey
from .CustomPhotosFieldsUtil import CustomPhotosFieldsUtil
from .ExifUtil import ExifUtil
from .MetadataFields import MetadataFields
from .XmpUtil import XmpUtil


class PhotoMetadata:
    """
    Orquestrador puro de metadados de fotos - Pipeline Pattern.

    RESPONSABILIDADE ÚNICA:
    Executa um pipeline linear de enriquecimentos sucessivos sobre as fotos.
    Cada etapa do pipeline pode ser ativada/desativada via flags.

    PIPELINE:
      Etapa 1 – Esqueleto inicial (sempre): varre fotos, cria dict {filename: {Path, FolderLevel1..5}}
      Etapa 2 – Enriquecimento MRK (opcional): cruza com pontos MRK
      Etapa 3 – EXIF (opcional): extrai metadados EXIF
      Etapa 4 – XMP (opcional): extrai metadados XMP
      Etapa 5 – Campos customizados (opcional): calcula campos derivados

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
    # API PÚBLICA - Pipeline completo
    # ─────────────────────────────────────────────

    @staticmethod
    def run_pipeline(
        base_folder: str,
        points: Optional[List[Dict[str, Any]]] = None,
        recursive: bool = True,
        tool_key: str = "drone_coordinates",
        *,
        enable_mrk: bool = False,
        enable_exif: bool = True,
        enable_xmp: bool = True,
        enable_custom_fields: bool = True,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Pipeline unificado de enriquecimento de fotos.

        Executa as etapas na ordem fixa, respeitando as flags habilitação.

        Args:
            base_folder: Pasta raiz das fotos
            points: Lista de pontos MRK (opcional, usado se enable_mrk=True)
            recursive: Varrer subpastas recursivamente
            tool_key: Chave para logging
            enable_mrk: Se True, executa Etapa 2 (enriquecimento MRK)
            enable_exif: Se True, executa Etapa 3 (EXIF)
            enable_xmp: Se True, executa Etapa 4 (XMP)
            enable_custom_fields: Se True, executa Etapa 5 (custom fields)

        Returns:
            (records, quality_stats)
        """
        logger = PhotoMetadata._get_logger(tool_key)
        logger.info(
            "Iniciando pipeline de metadados",
            data={
                "base_folder": base_folder,
                "recursive": recursive,
                "has_points": len(points) if points else 0,
                "enable_mrk": enable_mrk,
                "enable_exif": enable_exif,
                "enable_xmp": enable_xmp,
                "enable_custom_fields": enable_custom_fields,
            },
        )

        PhotoMetadata.clear_timestamps()

        # ── Etapa 1: Esqueleto inicial (sempre executada) ──
        skeleton_start = datetime.now().isoformat()
        skeleton = PhotoMetadata._build_file_skeleton(base_folder, recursive, tool_key)
        if not skeleton:
            logger.warning("Nenhuma foto encontrada no diretorio")
            return [], {"total_files": 0, "with_coords": 0, "without_coords": 0,
                         "with_xmp": 0, "with_exif_gps": 0, "missing_xmp_and_exif": 0}

        # ── Etapa 2: Enriquecimento MRK (opcional) ──
        if enable_mrk and points:
            skeleton = PhotoMetadata._enrich_with_mrk(skeleton, points, base_folder, tool_key)
            source = "mrk+photo"
        else:
            source = "photo"

        # Timestamps: inicio da extracao de metadados das fotos (EXIF)
        exif_start = datetime.now().isoformat()

        # ── Etapa 3: EXIF (opcional, padrão: True) ──
        if enable_exif:
            skeleton = PhotoMetadata._enrich_exif(skeleton, tool_key)

        # ── Etapa 4: XMP (opcional, padrão: True) ──
        if enable_xmp:
            skeleton = PhotoMetadata._enrich_xmp(skeleton, tool_key)

        # Timestamps: fim da extracao de metadados (EXIF + XMP)
        xmp_end = datetime.now().isoformat()

        # Converte dict para lista de records, normaliza, resolve coordenadas
        all_records = []
        quality = {
            "total_files": len(skeleton),
            "with_coords": 0,
            "without_coords": 0,
            "with_xmp": 0,
            "with_exif_gps": 0,
            "missing_xmp_and_exif": 0,
        }

        for filename, payload in skeleton.items():
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

        # ── Etapa 5: Campos customizados (opcional, padrão: True) ──
        if enable_custom_fields:
            all_records = PhotoMetadata._calculate_custom_fields(all_records, tool_key, logger)

        # Timestamps: fim calculo campos custom
        custom_end = datetime.now().isoformat()

        logger.info(
            "Pipeline concluido",
            data={
                "source": source,
                "total_records": len(all_records),
                "quality": quality,
            },
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
    # API PÚBLICA LEGADO (delegação para pipeline)
    # ─────────────────────────────────────────────

    @staticmethod
    def enrich(
        points: List[Dict[str, Any]],
        base_folder: str,
        recursive: bool = True,
        tool_key: str = "drone_coordinates",
    ) -> List[Dict[str, Any]]:
        """
        [LEGADO] Cruza pontos MRK com metadados de fotos.
        → Executa pipeline completo com todas as etapas habilitadas.
        """
        records, _ = PhotoMetadata.run_pipeline(
            base_folder=base_folder,
            points=points,
            recursive=recursive,
            tool_key=tool_key,
            enable_mrk=True,
            enable_exif=True,
            enable_xmp=True,
            enable_custom_fields=True,
        )
        return records

    @staticmethod
    def extract_photos_only(
        base_folder: str,
        recursive: bool = True,
        tool_key: str = "drone_coordinates",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        [LEGADO] Extrai metadados de fotos SEM pontos MRK (modo photo_only).
        → Executa pipeline sem etapa MRK.
        """
        return PhotoMetadata.run_pipeline(
            base_folder=base_folder,
            points=None,
            recursive=recursive,
            tool_key=tool_key,
            enable_mrk=False,
            enable_exif=True,
            enable_xmp=True,
            enable_custom_fields=True,
        )

    # ─────────────────────────────────────────────
    # ETAPA 1: Esqueleto inicial
    # ─────────────────────────────────────────────

    @staticmethod
    def _build_file_skeleton(
        base_folder: str,
        recursive: bool,
        tool_key: str,
    ) -> Dict[str, dict]:
        """
        Etapa 1 – Esqueleto inicial.

        Varre o diretório de fotos e cria um dicionário onde cada chave
        é o nome do arquivo da foto (filename). Para cada registro, já
        são calculados e armazenados:

        - Path: caminho absoluto do arquivo
        - FolderLevel1..FolderLevel5: obtidos subindo a hierarquia de pastas
          a partir da foto (FolderLevel1 é a pasta imediata onde o arquivo
          está; FolderLevel2 é a pasta pai dessa; e assim sucessivamente
          até o 5º nível, se existirem).

        Returns:
            Dict {filename: {Path, FolderLevel1, FolderLevel2, ...}}
        """
        logger = PhotoMetadata._get_logger(tool_key)
        skeleton: Dict[str, dict] = {}

        walker = os.walk(base_folder) if recursive else [(base_folder, [], os.listdir(base_folder))]
        for root, _, files in walker:
            for fname in files:
                if not fname.lower().endswith(".jpg"):
                    continue
                match = PhotoMetadata.DJI_RE.search(fname)
                if not match:
                    continue

                abs_path = os.path.join(root, fname)

                # Calcula FolderLevels subindo a hierarquia de pastas
                rel_path = os.path.relpath(root, base_folder)
                folder_levels = PhotoMetadata._extract_folder_levels(rel_path)

                record = {
                    MetadataFieldKey.FILE.value: fname,
                    MetadataFieldKey.PATH.value: abs_path,
                    MetadataFieldKey.FOLDER_LEVEL_1.value: folder_levels.get("FolderLevel1", ""),
                    MetadataFieldKey.FOLDER_LEVEL_2.value: folder_levels.get("FolderLevel2", ""),
                    "FolderLevel3": folder_levels.get("FolderLevel3", ""),
                    "FolderLevel4": folder_levels.get("FolderLevel4", ""),
                    "FolderLevel5": folder_levels.get("FolderLevel5", ""),
                }

                # Usa o nome do arquivo como chave primária
                skeleton[fname] = record

        logger.info(
            "Esqueleto inicial criado",
            data={
                "base_folder": base_folder,
                "total_photos": len(skeleton),
            },
        )

        return skeleton

    @staticmethod
    def _extract_folder_levels(rel_path: str) -> Dict[str, str]:
        """
        Extrai FolderLevel1..FolderLevel5 de um caminho relativo.

        A lógica é determinística e baseada exclusivamente no path real:
        - FolderLevel1 é a pasta imediata onde o arquivo está
        - FolderLevel2 é a pasta pai dessa
        - ... até FolderLevel5

        Args:
            rel_path: Caminho relativo (ex: "IMAGEM/IRIA01/20250101")

        Returns:
            Dict com chaves FolderLevel1..FolderLevel5
        """
        if not rel_path or rel_path == ".":
            return {}

        # Normaliza separadores e divide em partes
        parts = rel_path.replace("\\", "/").strip("/").split("/")

        levels = {}
        for i in range(min(len(parts), 5)):
            levels[f"FolderLevel{i + 1}"] = parts[i]

        return levels

    # ─────────────────────────────────────────────
    # ETAPA 2: Enriquecimento MRK
    # ─────────────────────────────────────────────

    @staticmethod
    def _enrich_with_mrk(
        skeleton: Dict[str, dict],
        points: List[Dict[str, Any]],
        base_folder: str,
        tool_key: str,
    ) -> Dict[str, dict]:
        """
        Etapa 2 – Enriquecimento MRK.

        Para cada registro cuja pasta (FolderLevel1) corresponde à pasta
        de origem do MRK, extrai a sequência numérica do nome do arquivo
        (ex.: 0001 de DJI_..._0001_V.JPG). Com a sequência e o contexto
        da pasta, busca no índice MRK as coordenadas, altitude, nome do
        voo e demais metadados de voo.

        Registros cuja pasta não coincide com a do MRK permanecem inalterados.

        Args:
            skeleton: Dict {filename: record} vindo da Etapa 1
            points: Lista de pontos MRK
            base_folder: Pasta base das fotos

        Returns:
            Dict enriquecido com dados MRK
        """
        logger = PhotoMetadata._get_logger(tool_key)

        # Indexa contexto MRK por (pasta, sequência)
        mrk_index = PhotoMetadata._build_mrk_context_by_sequence(points)

        # Para cada ponto MRK, busca foto correspondente no skeleton
        for point in points:
            foto = point.get("foto")
            if foto is None:
                continue

            try:
                seq = f"{int(foto):04d}"
            except (ValueError, TypeError):
                continue

            # Determina a pasta do MRK
            mrk_folder = str(point.get("MrkFolder") or point.get("mrk_folder") or "").strip()
            mrk_folder_rel = ""
            if mrk_folder:
                mrk_folder_rel = os.path.relpath(mrk_folder, base_folder).replace("\\", "/")

            # Extrai FolderLevel1 do MRK (primeira subpasta relevante)
            mrk_folder_parts = mrk_folder_rel.replace("\\", "/").strip("/").split("/")
            mrk_folder_level1 = mrk_folder_parts[0] if mrk_folder_parts and mrk_folder_parts[0] != "." else ""

            # Procura no skeleton por fotos cujo FolderLevel1 corresponde
            # e cujo nome contenha a sequência
            for filename, record in skeleton.items():
                record_folder = str(record.get(MetadataFieldKey.FOLDER_LEVEL_1.value) or "").strip()
                seq_match = PhotoMetadata.DJI_RE.search(filename)
                if not seq_match:
                    continue
                filename_seq = seq_match.group(1)

                # Match: mesma pasta E mesma sequência
                if record_folder == mrk_folder_level1 and filename_seq == seq:
                    # Enriquece o registro com dados MRK
                    flight_context = PhotoMetadata._extract_flight_context(point)
                    record.update(flight_context)
                    record[MetadataFieldKey.COORD_SOURCE.value] = "MRK"
                    record[MetadataFieldKey.QUALITY_FLAG.value] = "OK"
                    break

        logger.info(
            "Enriquecimento MRK concluido",
            data={
                "total_points": len(points),
                "matched_photos": sum(
                    1 for r in skeleton.values()
                    if r.get(MetadataFieldKey.COORD_SOURCE.value) == "MRK"
                ),
            },
        )

        return skeleton

    # ─────────────────────────────────────────────
    # ETAPA 3: EXIF
    # ─────────────────────────────────────────────

    @staticmethod
    def _enrich_exif(
        skeleton: Dict[str, dict],
        tool_key: str,
    ) -> Dict[str, dict]:
        """
        Etapa 3 – Extração EXIF.

        Lê os metadados EXIF de cada foto (usando o caminho já disponível
        no registro) e adiciona campos como fabricante, modelo, data/hora
        original etc. ao registro correspondente.
        """
        logger = PhotoMetadata._get_logger(tool_key)

        for filename, record in skeleton.items():
            image_path = record.get(MetadataFieldKey.PATH.value)
            if not image_path or not os.path.exists(image_path):
                continue

            try:
                exif_payload = ExifUtil.extract_metadata_exif(image_path, tool_key=tool_key)
                os_payload = ExifUtil.extract_metadata_os(image_path, tool_key=tool_key)
                image_payload = ExifUtil.extract_metadata_image(image_path, tool_key=tool_key)

                # Mescla dados EXIF no registro (sem sobrescrever campos já preenchidos pelo MRK)
                for payload in [exif_payload, os_payload, image_payload]:
                    for k, v in payload.items():
                        if k not in record or record.get(k) in (None, "", "None", "null"):
                            record[k] = v

                # Datetime
                dt = PhotoMetadata._safe_parse_datetime(
                    record.get(MetadataFieldKey.DATE_TIME_ORIGINAL.value)
                    or record.get("DateTime")
                )
                if dt is not None:
                    if record.get(MetadataFieldKey.DATE_TIME_ORIGINAL.value) in (None, "", "None", "null"):
                        record[MetadataFieldKey.DATE_TIME_ORIGINAL.value] = dt.strftime("%Y:%m:%d %H:%M:%S")

            except Exception as exc:
                logger.warning(f"Falha ao extrair EXIF de {filename}: {exc}")

        return skeleton

    # ─────────────────────────────────────────────
    # ETAPA 4: XMP
    # ─────────────────────────────────────────────

    @staticmethod
    def _enrich_xmp(
        skeleton: Dict[str, dict],
        tool_key: str,
    ) -> Dict[str, dict]:
        """
        Etapa 4 – Extração XMP.

        Lê os metadados XMP de cada foto (quando disponíveis) e incorpora
        informações como altitude relativa, guinada do gimbal, flag RTK, etc.
        """
        logger = PhotoMetadata._get_logger(tool_key)

        for filename, record in skeleton.items():
            image_path = record.get(MetadataFieldKey.PATH.value)
            if not image_path or not os.path.exists(image_path):
                continue

            try:
                xmp_payload = XmpUtil.extract_metadata(image_path, tool_key=tool_key)

                # Aliases DJI para compatibilidade
                alias_map = {
                    "drone-dji:AbsoluteAltitude": MetadataFieldKey.ABSOLUTE_ALTITUDE.value,
                    "drone-dji:RelativeAltitude": MetadataFieldKey.RELATIVE_ALTITUDE.value,
                    "drone-dji:GimbalRollDegree": MetadataFieldKey.GIMBAL_ROLL_DEGREE.value,
                    "drone-dji:GimbalYawDegree": MetadataFieldKey.GIMBAL_YAW_DEGREE.value,
                    "drone-dji:GimbalPitchDegree": MetadataFieldKey.GIMBAL_PITCH_DEGREE.value,
                    "drone-dji:FlightRollDegree": MetadataFieldKey.FLIGHT_ROLL_DEGREE.value,
                    "drone-dji:FlightYawDegree": MetadataFieldKey.FLIGHT_YAW_DEGREE.value,
                    "drone-dji:FlightPitchDegree": MetadataFieldKey.FLIGHT_PITCH_DEGREE.value,
                    "drone-dji:FlightXSpeed": MetadataFieldKey.FLIGHT_X_SPEED.value,
                    "drone-dji:FlightYSpeed": MetadataFieldKey.FLIGHT_Y_SPEED.value,
                    "drone-dji:FlightZSpeed": MetadataFieldKey.FLIGHT_Z_SPEED.value,
                    "drone-dji:RtkFlag": MetadataFieldKey.RTK_FLAG.value,
                    "drone-dji:RtkStdLon": MetadataFieldKey.RTK_STD_LON.value,
                    "drone-dji:RtkStdLat": MetadataFieldKey.RTK_STD_LAT.value,
                    "drone-dji:RtkStdHgt": MetadataFieldKey.RTK_STD_HGT.value,
                    "drone-dji:RtkDiffAge": MetadataFieldKey.RTK_DIFF_AGE.value,
                    "drone-dji:DewarpFlag": MetadataFieldKey.DEWARP_FLAG.value,
                    "drone-dji:ShutterCount": MetadataFieldKey.SHUTTER_COUNT.value,
                    "drone-dji:DroneModel": MetadataFieldKey.DRONE_MODEL.value,
                    "drone-dji:DroneSerialNumber": MetadataFieldKey.DRONE_SERIAL_NUMBER.value,
                    "drone-dji:CameraSerialNumber": MetadataFieldKey.CAMERA_SERIAL_NUMBER.value,
                    "drone-dji:CaptureUUID": MetadataFieldKey.CAPTURE_UUID.value,
                    "drone-dji:UTCAtExposure": MetadataFieldKey.UTC_AT_EXPOSURE.value,
                    "drone-dji:SensorTemperature": MetadataFieldKey.SENSOR_TEMPERATURE.value,
                    "drone-dji:LensTemperature": MetadataFieldKey.LENS_TEMPERATURE.value,
                    "drone-dji:WhiteBalanceCCT": MetadataFieldKey.WHITE_BALANCE_CCT.value,
                    "drone-dji:GpsStatus": MetadataFieldKey.GPS_STATUS.value,
                    "drone-dji:GpsLatitude": MetadataFieldKey.GPS_LATITUDE.value,
                    "drone-dji:GpsLongitude": MetadataFieldKey.GPS_LONGITUDE.value,
                }
                for src_key, tgt_key in alias_map.items():
                    if tgt_key not in record and src_key in xmp_payload:
                        record[tgt_key] = xmp_payload.get(src_key)

                # Mescla demais campos XMP não mapeados como aliases
                for k, v in xmp_payload.items():
                    if k not in record or record.get(k) in (None, "", "None", "null"):
                        record[k] = v

            except Exception as exc:
                logger.warning(f"Falha ao extrair XMP de {filename}: {exc}")

        return skeleton

    # ─────────────────────────────────────────────
    # ETAPA 5: Campos customizados
    # ─────────────────────────────────────────────

    @staticmethod
    def _calculate_custom_fields(
        all_records: List[Dict[str, Any]],
        tool_key: str,
        logger: LogUtils,
    ) -> List[Dict[str, Any]]:
        """
        Etapa 5 – Campos customizados.

        Agrupa todos os registros por FolderLevel1 (já disponível desde
        a Etapa 1). Para cada grupo, executa
        CustomPhotosFieldsUtil.calculate_all_custom_fields() para gerar
        campos derivados (velocidades, distâncias, sobreposições, etc.).

        Os resultados são mesclados de volta nos registros originais.
        """
        try:
            # Agrupa records por FolderLevel1
            grouped_records: Dict[str, List[Dict]] = {}
            for r in all_records:
                if r.get(MetadataFieldKey.DATE_TIME_ORIGINAL.value) in (None, ""):
                    continue
                group_key = str(r.get(MetadataFieldKey.FOLDER_LEVEL_1.value) or "__NO_FOLDER__")
                if group_key not in grouped_records:
                    grouped_records[group_key] = []
                grouped_records[group_key].append(r)

            for group_key, group in grouped_records.items():
                logger.debug(
                    f"Processando campos custom para grupo '{group_key}' ({len(group)} fotos)"
                )
                custom_ready = {r.get(MetadataFieldKey.FILE.value): r for r in group}
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

        return all_records

    # ─────────────────────────────────────────────
    # MÉTODOS INTERNOS
    # ─────────────────────────────────────────────

    @staticmethod
    def _extract_photo_payload(image_path: str, tool_key: str) -> dict:
        """
        [LEGADO] Extrai metadados completos de uma foto (OS + PIL + EXIF + XMP + aliases).
        Mantido para compatibilidade com código legado.
        """
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
        [LEGADO] Indexa fotos de uma pasta por chave combinada (pasta_relativa::sequencia).
        Mantido para compatibilidade com código legado.
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

        # Indice simples por sequencia (legado, para compatibilidade)
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
        """Indexa contexto MRK por (pasta, sequência) para busca rápida."""
        index = {}
        for point in points or []:
            foto = point.get("foto")
            if foto is None:
                continue
            try:
                seq = f"{int(foto):04d}"
            except Exception:
                continue

            mrk_folder = str(point.get("MrkFolder") or point.get("mrk_folder") or "").strip()
            key = (mrk_folder, seq)

            if key not in index:
                canonical = MetadataFields.normalize_record_to_keys(point)
                index[key] = canonical

        return index

    @staticmethod
    def _extract_flight_context(point: dict) -> dict:
        """Extrai contexto de voo de um ponto MRK."""
        canonical = MetadataFields.normalize_record_to_keys(point or {})
        return {
            MetadataFieldKey.FLIGHT_NUMBER.value: canonical.get(MetadataFieldKey.FLIGHT_NUMBER.value),
            MetadataFieldKey.FLIGHT_NAME.value: canonical.get(MetadataFieldKey.FLIGHT_NAME.value),
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