from pathlib import Path
from typing import Any, Dict, List

import jinja2

from ...core.config.LogUtils import LogUtils
from ...resources.IconManager import IconManager as IM
from ..ToolKeys import ToolKey


class RenderEngine:
    """Render HTML + charts + mapa."""

    def __init__(self, tool_key: str = ToolKey.UNTRACEABLE):
        """Inicializa ambiente Jinja2 e carrega o template principal do relatorio."""
        self.tool_key = tool_key
        self.logger = LogUtils(tool=tool_key, class_name="RenderEngine")
        self.resources_dir = Path(__file__).resolve().parents[2] / "resources"
        template_dir = self.resources_dir / "reports"
        loader = jinja2.FileSystemLoader(str(template_dir))
        self.env = jinja2.Environment(
            loader=loader,
            autoescape=jinja2.select_autoescape(["html", "xml"]),
        )
        self.template = self.env.get_template("template.html")

    @staticmethod
    def generate_charts(agg_data: Dict[str, Any]) -> Dict[str, Any]:
        """Monta payload de graficos consumido pelo template (Chart.js)."""
        charts: Dict[str, Any] = {}

        dist = agg_data.get("level_distribution", {})
        total = sum(dist.values())
        labels = ["Critical (1)", "Poor (2)", "OK (3)", "Good (4)", "Excellent (5)"]
        if total == 0:
            pie_data = [0, 0, 0, 0, 0]
        else:
            pie_data = [round(dist.get(i, 0) / total * 100, 2) for i in range(1, 6)]

        charts["level_pie"] = {
            "type": "pie",
            "labels": labels,
            "data": pie_data,
            "title": "Level Distribution (%)",
        }

        ind_means = {k: v["mean"] for k, v in agg_data.get("per_indicator", {}).items()}
        bar_labels = list(ind_means.keys())[:10]
        charts["indicator_bar"] = {
            "type": "bar",
            "labels": bar_labels,
            "data": [ind_means[k] for k in bar_labels],
            "title": "Average Level per Indicator",
        }

        return charts

    @staticmethod
    def _to_float(value: Any):
        """Converte valor para float com tolerancia a strings vazias."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace("+", "")
        if text.lower() in {"", "none", "null", "nan"}:
            return None
        try:
            return float(text)
        except Exception:
            return None

    @staticmethod
    def _extract_lat_lon(result: Any):
        """Extrai lat/lon reais a partir do resultado da imagem."""
        if hasattr(result, "get_indicator"):
            lat = RenderEngine._to_float(result.get_indicator("Lat"))
            lon = RenderEngine._to_float(result.get_indicator("Lon"))
            if lat is None or lon is None:
                lat = RenderEngine._to_float(result.get_indicator("GpsLatitude"))
                lon = RenderEngine._to_float(result.get_indicator("GpsLongitude"))
            if lat is not None and lon is not None:
                return lat, lon

        for lat_key, lon_key in (
            ("Lat", "Lon"),
            ("GpsLatitude", "GpsLongitude"),
            ("lat", "lon"),
            ("latitude", "longitude"),
        ):
            if isinstance(result, dict):
                lat = RenderEngine._to_float(result.get(lat_key))
                lon = RenderEngine._to_float(result.get(lon_key))
            else:
                lat = RenderEngine._to_float(getattr(result, lat_key, None))
                lon = RenderEngine._to_float(getattr(result, lon_key, None))
            if lat is not None and lon is not None:
                return lat, lon

        return None, None

    @staticmethod
    def generate_map_data(results: List[Any]) -> Dict[str, Any]:
        """Gera snippet Leaflet com pontos reais (lat/lon) das imagens."""
        markers = []

        for result in results:
            lat, lon = RenderEngine._extract_lat_lon(result)
            if lat is None or lon is None:
                continue
            if abs(lat) < 0.000001 and abs(lon) < 0.000001:
                continue

            filename = getattr(result, "filename", "unknown")
            score = getattr(result, "overall_score", "-")
            levels = getattr(result, "levels", {}) or {}
            popup = (
                f"<b>{filename}</b><br>"
                f"Score: {score}<br>"
                f"GSD nivel: {levels.get('gsd_cm', '?')}"
            )
            markers.append({"lat": lat, "lon": lon, "popup": popup})

        if markers:
            center_lat = sum(m["lat"] for m in markers) / len(markers)
            center_lon = sum(m["lon"] for m in markers) / len(markers)
        else:
            center_lat, center_lon = -10.217, -48.359

        leaflet_lines = [
            '<div id="map" style="height:220px;border-radius:8px"></div>',
            '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>',
            '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>',
            "<script>",
            f'var map = L.map("map").setView([{center_lat}, {center_lon}], 16);',
            'L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 21}).addTo(map);',
        ]

        for marker in markers:
            leaflet_lines.append(
                f'L.marker([{marker["lat"]}, {marker["lon"]}]).addTo(map).bindPopup(`{marker["popup"]}`);'
            )
        if len(markers) >= 2:
            leaflet_lines.append(
                "L.polyline(["
                + ",".join([f"[{m['lat']},{m['lon']}]" for m in markers])
                + "], {color:'#1e88e5', weight:2, opacity:0.8}).addTo(map);"
            )

        if markers:
            leaflet_lines.append(
                "var bounds = L.latLngBounds(["
                + ",".join([f"[{m['lat']},{m['lon']}]" for m in markers])
                + "]);"
            )
            leaflet_lines.append("if (bounds.isValid()) { map.fitBounds(bounds.pad(0.15)); }")
        else:
            leaflet_lines.append(
                'L.popup({closeButton:false,autoClose:false,closeOnClick:false})'
                f'.setLatLng([{center_lat}, {center_lon}])'
                '.setContent("Sem coordenadas válidas para exibir no mapa.")'
                ".openOn(map);"
            )

        leaflet_lines.append("</script>")

        return {
            "leaflet_snippet": "".join(leaflet_lines),
            "markers_count": len(markers),
        }

    def render_report(
        self,
        *,
        results: List[Any],
        agg: Dict[str, Any],
        charts: Dict[str, Any],
        map_data: Dict[str, Any],
    ) -> str:
        """Renderiza o HTML final do relatorio com dados agregados e detalhes por imagem."""
        total_images = len(results)
        mean_overall = agg.get("mean_overall", 0)
        per_indicator = agg.get("per_indicator", {})
        cadmus_icon_path = Path(IM.icon_path(IM.CADMUS_PNG)).resolve()
        mtl_agro_icon_path = Path(IM.icon_path(IM.MTL_AGRO_PNG)).resolve()
        cadmus_icon_url = cadmus_icon_path.as_uri()
        mtl_agro_icon_url = mtl_agro_icon_path.as_uri()

        return self.template.render(
            results=results,
            agg=agg,
            charts=charts,
            map_snippet=map_data.get("leaflet_snippet", ""),
            total_images=total_images,
            mean_overall=mean_overall,
            per_indicator=per_indicator,
            cadmus_icon_url=cadmus_icon_url,
            mtl_agro_icon_url=mtl_agro_icon_url,
            cadmus_icon_path=str(cadmus_icon_path),
            mtl_agro_icon_path=str(mtl_agro_icon_path),
        )

    def save_report(self, html: str, output_path: str = "relatorio.html") -> None:
        """Salva o HTML renderizado no caminho de saida definido."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        self.logger.info(f"Relatorio salvo: {output_path}")
