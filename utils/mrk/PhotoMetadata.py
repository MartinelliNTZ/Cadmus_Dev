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
      Etapa 1 – Esqueleto inicial (sempre): varre fotos, cria dict {filename: {Path, FolderLevel1..5, FlightNumber, FlightName}}
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

    # Regex para extrair FlightNumber e FlightName do nome da pasta
    # Ex: "DJI_202605101003_001_IRIA01" → number=1, name=IRIA01
    FLIGHT_FOLDER_RE = re.compile(
        r"DJI_\d+_(?P<flight_number>\d+?)_(?P<flight_name>[^_]+)",
        re.IGNORECASE,
    )

    # Cache de timestamps de extracao
    _timestamps: Dict[str, str] = {}

    @staticmethod
    def get_timestamps() -> Dict[str, str]:
        return dict(PhotoMetadata._timestamps)

    @staticmethod
    def clear_timestamps():
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
        skeleton = PhotoMetadata._build_file_skeleton(base_folder, recursive, tool_key)
        if not skeleton:
            logger.warning("Nenhuma foto encontrada no diretorio")
            return [], {"total_files": 0, "with_xmp": 0, "with_mrk": 0, "with_exif_gps": 0}

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

        # Converte dict para lista de records e normaliza coordenadas
        all_records = []
        quality = {
            "total_files": len(skeleton),
            "with_xmp": 0,
            "with_mrk": 0,
            "with_exif_gps": 0,
        }

        for filename, payload in skeleton.items():
            if not payload:
                continue

            merged = MetadataFields.normalize_record_to_keys(payload)

            # MRK já vem em Lat/Lon/Alt (decimais) - mantém como está
            # EXIF DMS→decimal já foi convertido em _enrich_exif() (GpsLatRef/GpsLongRef)
            # XMP GpsLatitude/GpsLongitude (float) já sobrescreveu se existir

            # Se GpsLatitude/GpsLongitude ainda são tupla DMS (sem XMP para coordenadas),
            # converte para float decimal usando GpsLatitudeRef/GpsLongitudeRef
            gps_lat = merged.get(MetadataFieldKey.GPS_LATITUDE.value)
            gps_lon = merged.get(MetadataFieldKey.GPS_LONGITUDE.value)
            
            if isinstance(gps_lat, (list, tuple)):
                dec_val = PhotoMetadata._to_float(
                    merged.get(MetadataFieldKey.GPS_LATITUDE_REF.value)
                )
                if dec_val is not None:
                    merged[MetadataFieldKey.GPS_LATITUDE.value] = dec_val
            if isinstance(gps_lon, (list, tuple)):
                dec_val = PhotoMetadata._to_float(
                    merged.get(MetadataFieldKey.GPS_LONGITUDE_REF.value)
                )
                if dec_val is not None:
                    merged[MetadataFieldKey.GPS_LONGITUDE.value] = dec_val

            # Heurísticas de qualidade
            has_mrk = merged.get(MetadataFieldKey.COORD_SOURCE.value) == "MRK"
            has_xmp = any(
                k in merged
                for k in [
                    MetadataFieldKey.ABSOLUTE_ALTITUDE.value,
                    MetadataFieldKey.RELATIVE_ALTITUDE.value,
                    MetadataFieldKey.GIMBAL_YAW_DEGREE.value,
                    MetadataFieldKey.RTK_FLAG.value,
                ]
            )
            has_exif_gps = (
                merged.get(MetadataFieldKey.GPS_LATITUDE.value) is not None
                or merged.get(MetadataFieldKey.GPS_LONGITUDE.value) is not None
            )

            merged["HasXmp"] = has_xmp
            merged["HasExifGps"] = has_exif_gps

            if has_xmp:
                quality["with_xmp"] += 1
            if has_mrk:
                quality["with_mrk"] += 1
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

        PhotoMetadata._timestamps = {
            "exif_start": exif_start,
            "exif_xmp_end": xmp_end,
            "custom_start": custom_start,
            "custom_end": custom_end,
        }

        return all_records, quality


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

        - File, Path
        - FolderLevel1..FolderLevel5 (determinístico pelo path real)
        - FlightNumber, FlightName (extraídos do nome da pasta mais profunda
          que segue o padrão DJI_YYYYMMDD_HHMMSS_NNN_NAME)
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

                abs_path = os.path.join(root, fname)#

                # Calcula FolderLevels subindo a hierarquia de pastas
                rel_path = os.path.relpath(root, base_folder)
                folder_levels = PhotoMetadata._extract_folder_levels(rel_path)

                # ── Correcão: quando rel_path == "." (fotos diretamente na base_folder) ──
                # O caminho relativo vira "." e _extract_folder_levels retorna vazio.
                # Precisamos usar o nome da pasta atual para garantir FolderLevel1 e
                # a extração de FlightNumber/FlightName.
                current_folder_name = os.path.basename(root)

                # Se rel_path for ".", força FolderLevel1 como o nome da pasta atual
                # (a própria pasta do voo) e prepara path_parts para extração de voo
                if rel_path == ".":
                    if not folder_levels.get("FolderLevel1"):
                        folder_levels["FolderLevel1"] = current_folder_name
                    path_parts = [current_folder_name]
                else:
                    path_parts = rel_path.replace("\\", "/").strip("/").split("/")

                # Extrai FlightNumber e FlightName do nome da pasta mais específica
                # que segue o padrão DJI_*_NNN_NAME (última subpasta que casa)
                flight_number = None
                flight_name = None
                for part in reversed(path_parts):
                    fm = PhotoMetadata.FLIGHT_FOLDER_RE.search(part)
                    if fm:
                        try:
                            flight_number = int(fm.group("flight_number"))
                        except (ValueError, TypeError):
                            flight_number = None
                        flight_name = fm.group("flight_name")
                        break

                record = {
                    MetadataFieldKey.FILE.value: fname,
                    MetadataFieldKey.PATH.value: abs_path,
                    MetadataFieldKey.FOLDER_LEVEL_1.value: folder_levels.get("FolderLevel1", ""),
                    MetadataFieldKey.FOLDER_LEVEL_2.value: folder_levels.get("FolderLevel2", ""),
                    MetadataFieldKey.FOLDER_LEVEL_3.value: folder_levels.get("FolderLevel3", ""),
                    MetadataFieldKey.FOLDER_LEVEL_4.value: folder_levels.get("FolderLevel4", ""),
                    MetadataFieldKey.FOLDER_LEVEL_5.value: folder_levels.get("FolderLevel5", ""),
                    MetadataFieldKey.FLIGHT_NUMBER.value: flight_number,
                    MetadataFieldKey.FLIGHT_NAME.value: flight_name,
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

        A lógica inverte a ordem das pastas: FolderLevel1 é a pasta mais
        próxima do arquivo (immediate parent), FolderLevel2 é a pai desta,
        e assim sucessivamente.

        Exemplo:
            Path: "10052026/M3E/IMAGEM/DJI_202605101003_001_IRIA01"
            FolderLevel1 = "DJI_202605101003_001_IRIA01" (pasta da foto)
            FolderLevel2 = "IMAGEM"
            FolderLevel3 = "M3E"
            FolderLevel4 = "10052026"
        """
        if not rel_path or rel_path == ".":
            return {}

        parts = rel_path.replace("\\", "/").strip("/").split("/")
        # Inverte para que FolderLevel1 seja a pasta mais próxima da foto
        reversed_parts = list(reversed(parts))

        levels = {}
        for i in range(min(len(reversed_parts), 5)):
            levels[f"FolderLevel{i + 1}"] = reversed_parts[i]

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

        Para cada ponto MRK, busca no skeleton a foto cujo filename
        contém a sequência correspondente. O match é feito pela
        sequência numérica extraída do filename (ex.: 0001 de
        DJI_..._0001_V.JPG).

        Diferente da abordagem anterior (que tentava filtrar por
        FolderLevel1), agora buscamos em TODAS as fotos do skeleton.
        Isso resolve o caso onde MRK e fotos estão em pastas diferentes
        mas com a mesma estrutura de numeração.
        """
        logger = PhotoMetadata._get_logger(tool_key)

        matched_count = 0

        # Para cada ponto MRK, busca a foto correspondente no skeleton
        for point in points:
            foto = point.get("foto")
            if foto is None:
                continue

            try:
                seq = f"{int(foto):04d}"
            except (ValueError, TypeError):
                continue

            # Procura no skeleton por fotos cujo nome contenha a sequência
            for filename, record in skeleton.items():
                seq_match = PhotoMetadata.DJI_RE.search(filename)
                if not seq_match:
                    continue
                filename_seq = seq_match.group(1)

                if filename_seq == seq:
                    # Verifica se já foi enriquecido por MRK (evita sobrescrita)
                    if record.get(MetadataFieldKey.COORD_SOURCE.value) == "MRK":
                        continue

                    # Enriquece o registro com dados MRK
                    flight_context = PhotoMetadata._extract_flight_context(point)
                    # NÃO sobrescreve FlightNumber/FlightName se já vieram da Etapa 1
                    for k, v in flight_context.items():
                        if v is not None:
                            record[k] = v

                    # Garante que o CoordSource seja MRK
                    record[MetadataFieldKey.COORD_SOURCE.value] = "MRK"
                    record[MetadataFieldKey.QUALITY_FLAG.value] = "OK"
                    matched_count += 1
                    break

        logger.info(
            "Enriquecimento MRK concluido",
            data={
                "total_points": len(points),
                "matched_photos": matched_count,
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
        
        Além da extração padrão, converte coordenadas DMS (EXIF bruto) para decimal.
        
        Mapeamento final:
        - GpsLatitude (atributo "GpsLat"): mantém tupla DMS do EXIF (RAW)
        - GpsLatitudeRef (atributo "GpsLatRef"): S/N → convertido para decimal com sinal
        - GpsLongitude (atributo "GPSLong"): mantém tupla DMS do EXIF (RAW)
        - GpsLongitudeRef (atributo "GpsLongRef"): E/W → convertido para decimal com sinal
        
        A conversão é feita AQUI, ANTES do XMP, para que o XMP possa sobrescrever
        GpsLatitude/GpsLongitude sem perder a coordenada decimal do EXIF.
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

                for payload in [exif_payload, os_payload, image_payload]:
                    for k, v in payload.items():
                        if k not in record or record.get(k) in (None, "", "None", "null"):
                            record[k] = v

                # A conversão DMS→decimal já é feita pelo ExifUtil.extract_metadata_exif()
                # GpsLatRef / GpsLongRef já vêm como decimal com sinal
                # GpsLat / GpsLong mantêm a tupla DMS original (RAW)

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
        Os aliases DJI são resolvidos pelo XmpUtil.extract_metadata.

        Regras de sobrescrita:
        - GpsLat (GpsLatitude) / GPSLong (GpsLongitude): 
            SEMPRE sobrescritos pelo XMP se disponíveis (float).
            Se não houver XMP, mantém a tupla DMS do EXIF.
        - GpsLatRef (GpsLatitudeRef) / GpsLongRef (GpsLongitudeRef):
            NUNCA sobrescritos pelo XMP. São EXCLUSIVOS do EXIF (decimal com sinal).
        """
        logger = PhotoMetadata._get_logger(tool_key)

        for filename, record in skeleton.items():
            image_path = record.get(MetadataFieldKey.PATH.value)
            if not image_path or not os.path.exists(image_path):
                continue

            try:
                xmp_payload = XmpUtil.extract_metadata(image_path, tool_key=tool_key)
                # XmpUtil já resolve os aliases internamente

                # Mescla campos XMP (APENAS campos que não são do EXIF)
                # GpsLatRef/GpsLongRef são EXCLUSIVOS do EXIF, NUNCA sobrescritos
                exif_exclusive = {"GpsLatRef", "GpsLongRef"}
                
                for k, v in xmp_payload.items():
                    if k in exif_exclusive:
                        continue  # NUNCA sobrescreve campos exclusivos do EXIF
                    # Sobrescreve GpsLat/GPSLong com XMP (float sobrescreve tupla DMS)
                    if k in ("GpsLat", "GPSLong") and v is not None:
                        record[k] = v
                    elif k not in record or record.get(k) in (None, "", "None", "null"):
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

        Agrupa por FolderLevel1 e calcula campos derivados.
        """
        try:
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
    # UTILITÁRIOS
    # ─────────────────────────────────────────────

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

    @staticmethod
    def _extract_position(merged_payload: dict) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
        """
        Extrai posição GPS do payload mesclado.
        Retorna (lat, lon, alt, source).
        
        Ordem de resolução:
        1. MRK (Lat/Lon) → já mapeado para GpsLatitude/GpsLongitude pelo pipeline
        2. XMP (drone-dji:AbsoluteAltitude, etc) → já mapeado para GpsLatitude/GpsLongitude
        3. EXIF DMS (tupla graus/min/seg) → convertido para decimal usando GpsLatitudeRef/GpsLongitudeRef
        """
        canonical = MetadataFields.normalize_record_to_keys(merged_payload or {})
        
        # --- Tentativa 1: Valor já é float (XMP ou MRK) ---
        lat_val = canonical.get(MetadataFieldKey.GPS_LATITUDE.value)
        lon_val = canonical.get(MetadataFieldKey.GPS_LONGITUDE.value)
        
        lat = PhotoMetadata._to_float(lat_val)
        lon = PhotoMetadata._to_float(lon_val)
        
        # --- Tentativa 2: Se é tupla/list (DMS do EXIF bruto), converte ---
        if lat is None and isinstance(lat_val, (list, tuple)) and len(lat_val) >= 3:
            lat_ref = canonical.get(MetadataFieldKey.GPS_LATITUDE_REF.value, "")
            lat = PhotoMetadata._extract_gps_decimal_from_dms(lat_val, lat_ref)
        if lon is None and isinstance(lon_val, (list, tuple)) and len(lon_val) >= 3:
            lon_ref = canonical.get(MetadataFieldKey.GPS_LONGITUDE_REF.value, "")
            lon = PhotoMetadata._extract_gps_decimal_from_dms(lon_val, lon_ref)
            
        if lat is not None and lon is not None:
            alt = PhotoMetadata._to_float(
                canonical.get(MetadataFieldKey.ABSOLUTE_ALTITUDE.value)
                or canonical.get("GPSAltitude")
            )
            has_dji = any("drone-dji:" in str(k) for k in (merged_payload or {}).keys())
            coord_source = str(canonical.get(MetadataFieldKey.COORD_SOURCE.value) or "")
            if coord_source == "MRK":
                source = "MRK"
            elif has_dji:
                source = "XMP"
            else:
                source = "EXIF"
            return lat, lon, alt, source

        # --- Tentativa 3: Fallback DMS usando chaves RAW do merged_payload (para compatibilidade) ---
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