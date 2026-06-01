from pathlib import Path
from typing import Any, Dict, List

import jinja2

from ...core.config.LogUtils import LogUtils
from ...resources.IconManager import IconManager as IM
from ..ToolKeys import ToolKey
from ..ColorUtil import ColorUtil


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

        dist = agg_data.get("pqi_level_distribution", agg_data.get("level_distribution", {}))
        total = sum(dist.values())
        labels = ["Critical (1)", "Poor (2)", "OK (3)", "Good (4)", "Excellent (5)"]
        title = "PQI Level Distribution (%)" if "pqi_level_distribution" in agg_data else "Level Distribution (%)"
        if total == 0:
            pie_data = [0, 0, 0, 0, 0]
        else:
            pie_data = [round(dist.get(i, 0) / total * 100, 2) for i in range(1, 6)]

        charts["level_pie"] = {
            "type": "pie",
            "labels": labels,
            "data": pie_data,
            "title": title,
        }

        per_indicator_data = agg_data.get("per_indicator", {})
        ind_means = {}
        for k, v in per_indicator_data.items():
            if isinstance(v, dict) and "mean" in v and v["mean"] is not None:
                ind_means[k] = v["mean"]
        bar_labels = list(ind_means.keys())[:10]
        charts["indicator_bar"] = {
            "type": "bar",
            "labels": bar_labels,
            "data": [ind_means[k] for k in bar_labels],
            "title": "Average Level per Indicator",
        }

        # Bucket size dos graficos de serie temporal (media de ~100 segmentos)
        bucket_size = agg_data.get("chart_bucket_size", 1)
        bucket_label = f"Bucket (media de {bucket_size} fotos)" if bucket_size > 1 else "Foto #"

        # Temperature per photo series (line chart) - bucketizada
        temp_series = agg_data.get("temp_chart_series", [])
        if temp_series:
            colors = ColorUtil.generate(len(temp_series))
            temp_datasets = []
            for idx, series in enumerate(temp_series):
                color = colors[idx % len(colors)]
                temp_datasets.append({
                    "label": series["label"],
                    "data": series["data"],
                    "borderColor": color,
                    "backgroundColor": ColorUtil.to_rgba(color, 0.1),
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 2,
                })
            x_axis_title = f"Bucket (media de {bucket_size} fotos)" if bucket_size > 1 else "Foto #"
            charts["temp_line"] = {
                "type": "line",
                "datasets": temp_datasets,
                "bucket_size": bucket_size,
                "x_axis_title": x_axis_title,
                "title": f"Temperatura do Sensor - Média a cada {bucket_size} fotos (°C)" if bucket_size > 1
                         else "Temperatura do Sensor por Foto (°C)",
            }

        # LRF Target Distance per photo series (line chart) - bucketizada
        lrf_series = agg_data.get("lrf_chart_series", [])
        if lrf_series:
            lrf_colors = ColorUtil.generate(len(lrf_series))
            lrf_datasets = []
            for idx, series in enumerate(lrf_series):
                color = lrf_colors[idx % len(lrf_colors)]
                lrf_datasets.append({
                    "label": series["label"],
                    "data": series["data"],
                    "borderColor": color,
                    "backgroundColor": ColorUtil.to_rgba(color, 0.1),
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 2,
                })
            x_axis_title = f"Bucket (media de {bucket_size} fotos)" if bucket_size > 1 else "Foto #"
            charts["lrf_line"] = {
                "type": "line",
                "datasets": lrf_datasets,
                "bucket_size": bucket_size,
                "x_axis_title": x_axis_title,
                "title": f"LRF Target Distance - Média a cada {bucket_size} fotos (m)" if bucket_size > 1
                         else "LRF Target Distance ao Longo do Voo (m)",
            }

        # ISO Speed Ratings per photo series (line chart) - bucketizada
        iso_series = agg_data.get("iso_chart_series", [])
        if iso_series:
            iso_colors = ColorUtil.generate(len(iso_series))
            iso_datasets = []
            for idx, series in enumerate(iso_series):
                color = iso_colors[idx % len(iso_colors)]
                iso_datasets.append({
                    "label": series["label"],
                    "data": series["data"],
                    "borderColor": color,
                    "backgroundColor": ColorUtil.to_rgba(color, 0.1),
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 2,
                })
            x_axis_title = f"Bucket (media de {bucket_size} fotos)" if bucket_size > 1 else "Foto #"
            charts["iso_line"] = {
                "type": "line",
                "datasets": iso_datasets,
                "bucket_size": bucket_size,
                "x_axis_title": x_axis_title,
                "title": f"ISO Speed Ratings - Média a cada {bucket_size} fotos" if bucket_size > 1
                         else "ISO Speed Ratings ao Longo do Voo",
            }

        # Médias por intervalo de hora do dia - line chart (intervalo DINAMICO)
        interval_minutes = agg_data.get("hourly_interval_minutes", 60)
        if interval_minutes == 60:
            interval_label = "Hora"
            interval_label_pt = "Hora"
        elif interval_minutes == 30:
            interval_label = "30min"
            interval_label_pt = "30 min"
        elif interval_minutes == 15:
            interval_label = "15min"
            interval_label_pt = "15 min"
        else:
            interval_label = f"{interval_minutes}min"
            interval_label_pt = f"{interval_minutes} min"

        temp_hourly = agg_data.get("temp_hourly_avg", [])
        if temp_hourly and any(h.get("mean") is not None for h in temp_hourly):
            labels = [h["label"] for h in temp_hourly]
            data = [h["mean"] if h.get("mean") is not None else None for h in temp_hourly]
            charts["temp_hourly_line"] = {
                "type": "line",
                "labels": labels,
                "datasets": [{
                    "label": "Temperatura Média (°C)",
                    "data": data,
                    "borderColor": "#00E676",
                    "backgroundColor": ColorUtil.to_rgba("#00E676", 0.1),
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointBackgroundColor": "#00E676",
                }],
                "interval_minutes": interval_minutes,
                "interval_label": interval_label,
                "title": f"Temperatura Média do Sensor a cada {interval_label_pt} (°C)",
            }

        lrf_hourly = agg_data.get("lrf_hourly_avg", [])
        if lrf_hourly and any(h.get("mean") is not None for h in lrf_hourly):
            labels = [h["label"] for h in lrf_hourly]
            data = [h["mean"] if h.get("mean") is not None else None for h in lrf_hourly]
            charts["lrf_hourly_line"] = {
                "type": "line",
                "labels": labels,
                "datasets": [{
                    "label": "LRF Média (m)",
                    "data": data,
                    "borderColor": "#1e88e5",
                    "backgroundColor": ColorUtil.to_rgba("#1e88e5", 0.1),
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointBackgroundColor": "#1e88e5",
                }],
                "interval_minutes": interval_minutes,
                "interval_label": interval_label,
                "title": f"LRF Target Distance Médio a cada {interval_label_pt} (m)",
            }

        # ISO Speed Ratings médio por intervalo de hora do dia
        iso_hourly = agg_data.get("iso_hourly_avg", [])
        if iso_hourly and any(h.get("mean") is not None for h in iso_hourly):
            labels = [h["label"] for h in iso_hourly]
            data = [h["mean"] if h.get("mean") is not None else None for h in iso_hourly]
            charts["iso_hourly_line"] = {
                "type": "line",
                "labels": labels,
                "datasets": [{
                    "label": "ISO Médio",
                    "data": data,
                    "borderColor": "#FF9100",
                    "backgroundColor": ColorUtil.to_rgba("#FF9100", 0.1),
                    "fill": False,
                    "tension": 0.4,
                    "pointRadius": 4,
                    "pointBackgroundColor": "#FF9100",
                }],
                "interval_minutes": interval_minutes,
                "interval_label": interval_label,
                "title": f"ISO Speed Ratings Médio a cada {interval_label_pt}",
            }

        return charts

    @staticmethod
    def compute_column_visibility(agg: Dict[str, Any]) -> None:
        """Decide colunas visiveis na tabela de voos com base nos dados presentes.
        
        Responsabilidade exclusiva de apresentacao: se nenhum voo tem dado de temperatura
        do sensor, a coluna e ocultada. Mutates agg in-place para o template consumir.
        """
        per_flight = agg.get("per_flight", [])
        if not per_flight:
            # Se nao ha voos, mostra tudo por seguranca
            for field in ("speed3d_kmh", "sensor_temp", "lrf", "rel_alt", "abs_alt",
                          "iso", "shutter", "wb_cct", "dist3d",
                          "flight_roll", "flight_yaw", "flight_pitch"):
                agg[f"show_column_{field}"] = True
            return

        def _is_zero_or_none(val):
            if val is None:
                return True
            if isinstance(val, (int, float)):
                return val == 0.0
            if isinstance(val, str):
                return val.strip() in ("", "N/A")
            return False

        checks = {
            "speed3d_kmh": lambda f: _is_zero_or_none(f.get("avg_speed3d_kmh")),
            "sensor_temp": lambda f: _is_zero_or_none(f.get("avg_sensor_temperature")),
            "lrf": lambda f: _is_zero_or_none(f.get("avg_lrf_target_distance")),
            "rel_alt": lambda f: _is_zero_or_none(f.get("avg_relative_altitude")),
            "abs_alt": lambda f: _is_zero_or_none(f.get("avg_absolute_altitude")),
            "iso": lambda f: _is_zero_or_none(f.get("avg_iso")),
            "shutter": lambda f: f.get("avg_shutter_speed_text") in (None, "", "N/A"),
            "wb_cct": lambda f: _is_zero_or_none(f.get("avg_white_balance_cct")),
            "dist3d": lambda f: _is_zero_or_none(f.get("avg_dist3d_previous")),
            "flight_roll": lambda f: _is_zero_or_none(f.get("avg_flight_roll")),
            "flight_yaw": lambda f: _is_zero_or_none(f.get("avg_flight_yaw")),
            "flight_pitch": lambda f: _is_zero_or_none(f.get("avg_flight_pitch")),
        }

        for field, check_fn in checks.items():
            all_none = all(check_fn(f) for f in per_flight)
            agg[f"show_column_{field}"] = not all_none

        # level5 columns: hide if ALL flights have None or 0
        level5_keys = [col["key"] for col in agg.get("flight_level5_columns", [])]
        for col_key in level5_keys:
            all_zero_or_none = all(
                _is_zero_or_none(f.get("level5_means", {}).get(col_key))
                for f in per_flight
            )
            agg[f"show_column_level5_{col_key}"] = not all_zero_or_none

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
        # Piores resultados (menor overall_score primeiro) limitado a 30
        worst_results = sorted(results, key=lambda r: r.overall_score)[:30]
        per_indicator = agg.get("per_indicator", {})
        cadmus_icon_path = Path(IM.icon_path(IM.CADMUS_PNG)).resolve()
        mtl_agro_icon_path = Path(IM.icon_path(IM.MTL_AGRO_PNG)).resolve()
        cadmus_icon_url = cadmus_icon_path.as_uri()
        mtl_agro_icon_url = mtl_agro_icon_path.as_uri()
        light_metrics = (
            (agg or {}).get("advanced_analysis", {}).get("metrics", {})
            if isinstance(agg, dict)
            else {}
        )
        self.logger.info(
            "Renderizando bloco de luz no relatorio",
            code="REPORT_LIGHT_SOURCE_BLOCK",
            data={
                "predominant": light_metrics.get("light_source_predominant"),
                "predominant_count": light_metrics.get("light_source_predominant_count"),
                "predominant_pct": light_metrics.get("light_source_predominant_pct"),
                "classes_count": len(light_metrics.get("light_source_classes") or []),
                "from_text": light_metrics.get("light_source_from_text"),
                "from_code": light_metrics.get("light_source_from_code"),
            },
        )

        # Decidir visibilidade das colunas da tabela de voos (decisao de apresentacao)
        RenderEngine.compute_column_visibility(agg)

        return self.template.render(
            results=results,
            worst_results=worst_results,
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
