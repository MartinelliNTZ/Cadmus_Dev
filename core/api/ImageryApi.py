# -*- coding: utf-8 -*-
"""
ImageryApi — Cliente de catálogo STAC (imagens de satélite) e download.
========================================================================
Roda em thread de trabalho (tasks). Usa apenas stdlib, requests,
pystac_client, osgeo/gdal, numpy e pyproj — **sem objetos QGIS**
(QgsProject, QgsLayer, canvas). Apenas paths e geometrias serializadas.

Primeira fonte: Sentinel-2 L2A via Earth Search (Element 84).
"""

import json
import os
from pathlib import Path
from typing import Callable, Optional, Union

import requests

from ...utils.BaseUtil import BaseUtil
from ...utils.ExplorerUtils import ExplorerUtils
from ...utils.raster.RasterLayerProcessing import RasterLayerProcessing
from ...utils.raster.RasterVectorBridge import RasterVectorBridge


class ImageryApi(BaseUtil):
    """Cliente de catálogo STAC e download de imagens de satélite.

    Fonte primária: Sentinel-2 L2A (collection ``sentinel-2-l2a``).
    O atributo ``SOURCES`` permite adicionar novas fontes no futuro.

    Parâmetros
    ----------
    tool_key : str, optional
        ToolKey para logging rastreável (via BaseUtil).
    """

    STAC_URL = "https://earth-search.aws.element84.com/v1"
    CHAVES_THUMB = ["thumbnail", "overview"]
    DEFAULT_SOURCE = "sentinel2"

    SOURCES = {
        "sentinel2": {
            "label": "Sentinel-2 L2A",
            "collection": "sentinel-2-l2a",
            "assets": {
                "B01": ("Coastal Aerosol", "60m"),
                "B02": ("Blue", "10m"),
                "B03": ("Green", "10m"),
                "B04": ("Red", "10m"),
                "B05": ("Red Edge", "20m"),
                "B06": ("Red Edge", "20m"),
                "B07": ("Red Edge", "20m"),
                "B08": ("Near Infrared", "10m"),
                "B8A": ("Red Edge", "20m"),
                "B09": ("Water Vapour", "60m"),
                "B11": ("SWIR 1", "20m"),
                "B12": ("SWIR 2", "20m"),
                "SCL": ("Scene Classification", "20m"),
            },
            "asset_map": {
                "B01": ["coastal", "B01"],
                "B02": ["blue", "B02"],
                "B03": ["green", "B03"],
                "B04": ["red", "B04"],
                "B05": ["rededge1", "B05"],
                "B06": ["rededge2", "B06"],
                "B07": ["rededge3", "B07"],
                "B08": ["nir", "B08"],
                "B8A": ["nir08", "B8A"],
                "B09": ["nir09", "B09"],
                "B11": ["swir16", "B11"],
                "B12": ["swir22", "B12"],
                "SCL": ["scl", "SCL"],
            },
            "compositions": {
                "RGB": {"nome": "RGB Natural", "bandas": ["B04", "B03", "B02"]},
                "FALSA_COR": {"nome": "Falsa Cor (NIR)", "bandas": ["B08", "B04", "B03"]},
                "SWIR": {"nome": "SWIR (Vegetação)", "bandas": ["B12", "B8A", "B04"]},
                "AGRICULTURA": {"nome": "Agricultura", "bandas": ["B11", "B08", "B02"]},
                "URBANO": {"nome": "Índice Urbano", "bandas": ["B12", "B11", "B04"]},
                "TODAS": {"nome": "Todas as bandas", "bandas": None},
            },
        },
    }

    def __init__(self, tool_key: Optional[str] = None):
        """Inicializa o cliente STAC (lazy) com tool_key de rastreamento."""
        super().__init__(tool_key or BaseUtil.TOOL_KEY_UNTRACEABLE)
        self._client = None


    # ── Catálogo / configuração da fonte ─────────────────────────────

    def get_source_config(self, source: Optional[str] = None) -> dict:
        """Retorna a config da fonte (assets, asset_map, compositions, collection)."""
        src = source or self.DEFAULT_SOURCE
        cfg = self.SOURCES.get(src)
        if cfg is None:
            raise ValueError(f"Fonte STAC desconhecida: {src}")
        return cfg

    def source_labels(self) -> dict:
        """Retorna {chave: label} de todas as fontes (para GridComboBox)."""
        return {key: cfg.get("label", key) for key, cfg in self.SOURCES.items()}

    # ── Cliente STAC ─────────────────────────────────────────────────

    def _open_client(self):
        """Abre (lazy) o cliente STAC."""
        if self._client is None:
            from pystac_client import Client  # import tardio (validação RF1)

            self._client = Client.open(self.STAC_URL)
        return self._client

    # ── Busca de cenas ───────────────────────────────────────────────

    def search_scenes(
        self,
        bbox_wgs84,
        date_from: str,
        date_to: str,
        max_cloud: float = 100.0,
        source: Optional[str] = None,
        max_items: int = 200,
    ) -> list:
        """Busca cenas no STAC para a bbox/intervalo/% de nuvens.

        Parâmetros
        ----------
        bbox_wgs84 : list[float]
            Extent em EPSG:4326 [xmin, ymin, xmax, ymax].
        date_from : str
            Data inicial (YYYY-MM-DD).
        date_to : str
            Data final (YYYY-MM-DD).
        max_cloud : float
            Nuvens máximas (eo:cloud_cover <= max_cloud).
        source : str, optional
            Chave da fonte (default "sentinel2").
        max_items : int
            Limite de itens retornados (default 200).

        Returns
        -------
        list[dict]
            Cenas normalizadas (id, date, tile, plataforma, nuvens, assets,
            geometry, proj_epsg, datetime).
        """
        cfg = self.get_source_config(source)
        catalog = self._open_client()
        self.logger.info(
            "Busca STAC iniciada",
            code="IMAGERY_SEARCH_START",
            bbox=bbox_wgs84,
            date_from=date_from,
            date_to=date_to,
            max_cloud=float(max_cloud),
        )

        search = catalog.search(
            collections=[cfg["collection"]],
            bbox=bbox_wgs84,
            datetime=f"{date_from}/{date_to}",
            query={"eo:cloud_cover": {"lte": float(max_cloud)}},
            max_items=max_items,
        )

        items = list(search.items())
        items.sort(key=lambda it: it.properties.get("datetime", ""))
        scenes = [self._normalize_scene(it) for it in items]

        self.logger.info(
            f"Busca STAC: {len(scenes)} cenas encontradas",
            code="IMAGERY_SEARCH_RESULT",
            total=len(scenes),
        )
        return scenes

    @staticmethod
    def _normalize_scene(item) -> dict:
        """Converte um Item do pystac em dict serializável (sem objetos de biblioteca)."""
        props = item.properties
        date = str(props.get("datetime", ""))[:10]
        mdate = str(props.get("datetime", "")) or ""
        return {
            "id": item.id,
            "date": date,
            "datetime": mdate,
            "tile": props.get("s2:mgrs_tile", props.get("mgrs:utm_zone", "")),
            "plataforma": str(props.get("platform", "")).upper(),
            "nuvens": float(props.get("eo:cloud_cover") or 0),
            "assets": {
                key: asset.href for key, asset in item.assets.items()
            } if item.assets else {},
            "geometry": item.geometry,
            "proj_epsg": props.get("proj:epsg"),
        }
# ── Thumbnail ────────────────────────────────────────────────────

    def get_thumbnail(self, scene: dict) -> Optional[bytes]:
        """Baixa a thumbnail (JPEG) da cena. Retorna None em falha."""
        assets = scene.get("assets", {}) or {}
        for key in self.CHAVES_THUMB:
            url = assets.get(key)
            if not url:
                continue
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                return resp.content
            except Exception as e:  # noqa: BLE001 - thumbnail é opcional
                self.logger.warning(
                    f"get_thumbnail: falha em '{key}': {e}",
                    code="IMAGERY_THUMB_FAIL",
                    scene=scene.get("id"),
                )
        return None

    # ── Download de asset ────────────────────────────────────────────

    def download_asset(
        self,
        scene: dict,
        asset_key: str,
        dest_path: Union[str, Path],
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> str:
        """Baixa um asset (banda) da cena para `dest_path` com progresso."""
        url = (scene.get("assets") or {}).get(asset_key)
        if not url:
            raise RuntimeError(
                f"Asset '{asset_key}' nao encontrado na cena {scene.get('id')}"
            )

        dest_path = str(dest_path)
        parent = os.path.dirname(dest_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        self.logger.info(
            f"download_asset: {asset_key} ({scene.get('id')})",
            code="IMAGERY_DOWNLOAD_ASSET",
            url=url,
        )

        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length") or 0)
        written = 0
        with open(dest_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                fh.write(chunk)
                written += len(chunk)
                if progress_cb is not None and total:
                    progress_cb(min(100.0, written * 100.0 / total))
        if progress_cb is not None and not total:
            progress_cb(100.0)
        return dest_path

    # ── Resolvedores ─────────────────────────────────────────────────

    @staticmethod
    def resolve_asset_key(scene: dict, cfg: dict, banda: str) -> str:
        """Resolve a chave real do asset no catálogo a partir da banda lógica."""
        assets = scene.get("assets") or {}
        if banda in assets:
            return banda
        aliases = cfg.get("asset_map", {}).get(banda, [banda])
        for alias in aliases:
            if alias in assets:
                return alias
        return banda

    def resolve_bands(self, bands_cfg, source: Optional[str] = None) -> list:
        """Expande composições/checkboxes em uma lista única e ordenada de bandas.

        Aceita dict ``{banda_or_composicao: bool}`` ou list de bandas.
        Composições com ``bandas=None`` expandem para todas as bandas da fonte.
        """
        cfg = self.get_source_config(source)
        comps = cfg.get("compositions", {})
        all_bands = list(cfg.get("assets", {}).keys())
        result = []

        if isinstance(bands_cfg, dict):
            for key, enabled in bands_cfg.items():
                if not enabled:
                    continue
                if key in comps:
                    bandas = comps[key].get("bandas")
                    result.extend(bandas if bandas else all_bands)
                elif key in all_bands or key in cfg.get("asset_map", {}):
                    result.append(key)
        elif isinstance(bands_cfg, (list, tuple)):
            for key in bands_cfg:
                if key in comps:
                    bandas = comps[key].get("bandas")
                    result.extend(bandas if bandas else all_bands)
                else:
                    result.append(key)

        seen = set()
        unique = []
        for b in result:
            if b not in seen:
                seen.add(b)
                unique.append(b)
        return unique

    @staticmethod
    def resolve_epsg(epsg_cfg, source_epsg: Optional[int]) -> Optional[int]:
        """Resolve o EPSG de saída.

        - "utm"/"native"/vazio → None (CRS nativo da cena).
        - int ou "EPSG:xxxx" → int do EPSG escolhido.
        """
        if isinstance(epsg_cfg, int):
            return epsg_cfg if epsg_cfg > 0 else None
        v = str(epsg_cfg or "").strip().lower()
        if v in ("utm", "native", ""):
            return None
        try:
            if ":" in v:
                return int(v.split(":")[-1])
            return int(v)
        except ValueError:
            return source_epsg
# ── Processamento nativo GDAL (worker-safe) ──────────────────────

    @staticmethod
    def _get_raster_epsg(raster_path: str) -> Optional[int]:
        """Retorna o EPSG do raster via GDAL (sem objetos QGIS)."""
        from osgeo import gdal
        from osgeo import osr

        src_ds = gdal.Open(str(raster_path), gdal.GA_ReadOnly)
        if src_ds is None:
            return None
        proj = src_ds.GetProjection()
        src_ds = None
        if not proj:
            return None
        srs = osr.SpatialReference()
        srs.ImportFromWkt(proj)
        code = srs.GetAuthorityCode(None)
        return int(code) if code else None

    def _reproject_raster(self, src_path, target_epsg: int, output_path) -> str:
        """Reprojeta raster via ``gdal.Warp`` (thread-safe, sem QGIS)."""
        from osgeo import gdal

        src_ds = gdal.Open(str(src_path), gdal.GA_ReadOnly)
        if src_ds is None:
            raise RuntimeError(f"Nao foi possivel abrir raster: {src_path}")

        parent = os.path.dirname(str(output_path))
        if parent:
            os.makedirs(parent, exist_ok=True)

        options = gdal.WarpOptions(
            dstSRS=f"EPSG:{int(target_epsg)}",
            format="GTiff",
            resampleAlg="bilinear",
        )
        try:
            result = gdal.Warp(str(output_path), src_ds, options=options)
        finally:
            src_ds = None
        if result is None:
            raise RuntimeError(
                f"Falha ao reprojetar raster para EPSG:{target_epsg}"
            )
        self.logger.info(
            f"Raster reprojetado p/ EPSG:{target_epsg} -> {output_path}",
            code="IMAGERY_REPROJECT_DONE",
        )
        return str(output_path)

    def _clip_by_extent(
        self,
        src_path,
        extent_wgs84,
        scene_epsg,
        output_path,
    ) -> str:
        """Recorta pelo boundary da extensão (bbox WGS84) no CRS da cena.

        Usa ``gdal.Translate`` com ``projWin`` calculado via pyproj
        (thread-safe, sem objetos QGIS).
        """
        from osgeo import gdal

        if not scene_epsg:
            self.logger.warning(
                "Recorte por extenso sem EPSG da cena; usando raster sem recorte",
                code="IMAGERY_CLIP_NO_EPSG",
            )
            return src_path

        from pyproj import Transformer

        transformer = Transformer.from_crs(
            "EPSG:4326", f"EPSG:{int(scene_epsg)}", always_xy=True
        )
        xmin, ymin, xmax, ymax = extent_wgs84
        xs = []
        ys = []
        for lx, ly in ((xmin, ymin), (xmin, ymax), (xmax, ymin), (xmax, ymax)):
            px, py = transformer.transform(lx, ly)
            xs.append(px)
            ys.append(py)
        # gdal projWin: [ulx, uly, lrx, lry]
        proj_win = [min(xs), max(ys), max(xs), min(ys)]

        src_ds = gdal.Open(str(src_path), gdal.GA_ReadOnly)
        if src_ds is None:
            raise RuntimeError(f"Nao foi possivel abrir raster: {src_path}")

        parent = os.path.dirname(str(output_path))
        if parent:
            os.makedirs(parent, exist_ok=True)

        try:
            result = gdal.Translate(str(output_path), src_ds, projWin=proj_win)
        finally:
            src_ds = None
        if result is None:
            raise RuntimeError("Falha ao recortar raster pelo boundary")
        self.logger.info(
            f"Raster recortado pelo boundary -> {output_path}",
            code="IMAGERY_CLIP_EXTENT_DONE",
        )
        return str(output_path)
# ── Processamento de item (cena) ─────────────────────────────────

    def process_item(
        self,
        item: dict,
        bandas: list,
        clip_mode: Optional[str],
        clip_geom: Optional[dict],
        epsg_out: Optional[int],
        output_folder: str,
        convert_uint16: bool = True,
        delete_originals: bool = False,
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> dict:
        """Baixa e processa as bandas de uma cena.

        Parâmetros
        ----------
        item : dict
            Cena normalizada (de ``search_scenes``).
        bandas : list[str]
            Bandas lógicas (ex: B04, B03, B02).
        clip_mode : str | None
            ``"polygon"`` (recorte por camada de polígono), ``"extent"``
            (recorte pelo boundary da extensão) ou ``None``.
        clip_geom : dict | None
            ``{"polygon_path": str}`` para polygon; ``{"extent_wgs84": list}``
            para extent.
        epsg_out : int | None
            EPSG de saída (None = nativo da cena).
        output_folder : str
            Pasta raiz de saída (cada cena em ``{folder}/data_tile_plataforma``).
        convert_uint16 : bool
            Se True, divide por 10000 e salva float32 ``_refl.tif``.
        delete_originals : bool
            Se True, lista os originais uint16 para remoção (feita no main thread).
        progress_cb : callable, optional
            Callback de progresso 0-100.

        Returns
        -------
        dict
            Resultado com ``item_id``, ``prefix``, ``folder``, ``files``,
            ``originals_to_delete`` e ``metadata`` (path do JSON).
        """
        cfg = self.get_source_config(None)
        prefixo = ExplorerUtils.sanitize_path_component(
            f"{item.get('date', '')}_{item.get('tile', '')}_{item.get('plataforma', '')}"
        ) or item.get("id", "item")
        pasta_item = Path(output_folder) / prefixo
        pasta_item.mkdir(parents=True, exist_ok=True)

        scene_epsg = item.get("proj_epsg")
        total_bandas = len(bandas)
        files = []
        originals_to_delete = []
        convertidos = 0

        for idx, banda in enumerate(bandas, start=1):
            if progress_cb is not None:
                progress_cb(((idx - 1) / total_bandas) * 100.0)

            asset_key = self.resolve_asset_key(item, cfg, banda)
            caminho_temp = pasta_item / f"_tmp_{banda}.tif"

            def _band_progress(part, base=idx - 1, total=total_bandas, cb=progress_cb):
                if cb is not None:
                    cb((base / total) * 100.0 + (part / total))

            self.download_asset(item, asset_key, caminho_temp, progress_cb=_band_progress)

            start_path = caminho_temp

            # 1. Clip por polígono (RasterVectorBridge, worker-safe paths)
            if clip_mode == "polygon" and clip_geom and clip_geom.get("polygon_path"):
                out_clip = pasta_item / f"{prefixo}_{banda}_clip.tif"
                RasterVectorBridge().clip_raster_by_vector(
                    str(start_path),
                    str(clip_geom["polygon_path"]),
                    str(out_clip),
                    external_tool_key=self.tool_key,
                )
                start_path = out_clip
            # 2. Clip por boundary (sem polígono — bbox de raster/vetor/tela)
            elif clip_mode == "extent" and clip_geom and clip_geom.get("extent_wgs84"):
                out_clip = pasta_item / f"{prefixo}_{banda}_clip.tif"
                start_path = self._clip_by_extent(
                    str(start_path),
                    clip_geom["extent_wgs84"],
                    scene_epsg,
                    str(out_clip),
                )

            # 3. Arquivo final base (sem conversão)
            final_path = pasta_item / f"{prefixo}_{banda}.tif"
            if start_path != final_path:
                if os.path.exists(str(final_path)):
                    ExplorerUtils.delete_file(str(final_path), tool_key=self.tool_key)
                try:
                    os.replace(str(start_path), str(final_path))
                except OSError as e:
                    self.logger.warning(
                        f"Falha ao mover '{start_path}': {e}",
                        code="IMAGERY_MOVE_RENAME",
                    )
                    ExplorerUtils.rename_file(
                        str(start_path), str(final_path), tool_key=self.tool_key
                    )
# 4. Conversão uint16 → float32 (÷10000); SCL passa direto
            if convert_uint16:
                refl_path = pasta_item / f"{prefixo}_{banda}_refl.tif"
                result_path = RasterLayerProcessing.scale_raster_to_float32(
                    str(final_path),
                    str(refl_path),
                    band_name=banda,
                    tool_key=self.tool_key,
                )
                if os.path.exists(str(refl_path)):
                    files.append(str(refl_path))
                    convertidos += 1
                    if delete_originals and os.path.exists(str(final_path)):
                        originals_to_delete.append(str(final_path))
                    continue

            files.append(str(final_path))

        if progress_cb is not None:
            progress_cb(100.0)

        # Metadados da cena (RF13)
        meta = {
            "id": item.get("id"),
            "data": item.get("datetime"),
            "tile": item.get("tile"),
            "plataforma": item.get("plataforma"),
            "nuvens_%": item.get("nuvens"),
            "epsg_original": scene_epsg,
            "epsg_saida": epsg_out,
            "clip_mode": clip_mode,
            "bandas_baixadas": [Path(f).name for f in files],
            "convertidos_/10000": convertidos,
            "apagar_originais": delete_originals,
        }
        meta_path = pasta_item / f"{prefixo}_metadata.json"
        with open(str(meta_path), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2, default=str)

        self.logger.info(
            f"process_item: {len(files)} arquivos ({pasta_item})",
            code="IMAGERY_ITEM_DONE",
            item=item.get("id"),
            bandas=len(bandas),
        )
        return {
            "item_id": item.get("id"),
            "prefix": prefixo,
            "folder": str(pasta_item),
            "files": files,
            "originals_to_delete": originals_to_delete,
            "metadata": str(meta_path),
        }
