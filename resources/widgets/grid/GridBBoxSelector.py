# -*- coding: utf-8 -*-
"""
GridBBoxSelector — Seletor de extensão de linha única (camada / tela / desenho).
================================================================================
Genérico e reaproveitável. Plugins USAM este widget. NUNCA importa Simple.

Layout (linha única):
    [ QgsMapLayerComboBox (todas as camadas) ] [Tela] [Desenhar]

O widget armazena, para uso pela ferramenta:
    - boundary   : QgsRectangle + CRS da origem (canvas/camada/desenho)
    - path       : source da camada selecionada (quando origem = "layer")
    - tipo       : "drawn" (desenhado) | "layer" (camada) | "canvas" (tela)
    - geom_type  : "raster" | "polygon" | "line" | "point" (quando "layer")
    - polygon_wkt: polígono desenhado em EPSG:4326 (recorte por máscara)

Decisão de recorte (usada pela ferramenta, ex: ImageryDownloader):
    - tipo "drawn" ou camada de polígono -> clip POR POLÍGONO (formato da máscara)
    - demais origens (ponto, linha, raster, tela) -> clip PELO BOUNDARY (extent)

API pública:
    get_input_type()  -> "drawn"|"layer"|"canvas"
    get_extent()      -> QgsRectangle
    get_crs()         -> QgsCoordinateReferenceSystem
    get_layer_path()  -> str (path da camada quando tipo "layer")
    bbox_wgs84()      -> [xmin, ymin, xmax, ymax] em EPSG:4326 (p/ STAC)
    get_polygon_wkt() -> str | None (WKT EPSG:4326 do polígono desenhado)
    is_polygon_clip() -> bool
    is_clip_valid()   -> bool
    build_clip_data() -> dict ({"mode": "polygon"|"extent", ...})
    get_source()      -> str (compat: "canvas"|"raster"|"vector")
    get_preferences() / set_preferences(prefs)

Uso em plugins:
    bbox = GridBBoxSelector(
        iface=self.iface,
        config={
            "capture_label": STR.BBOX_CAPTURE_SCREEN,
            "capture_description": STR.BBOX_CAPTURE_SCREEN_DESC,
            "draw_label": STR.BBOX_DRAW_MAP,
            "draw_description": STR.BBOX_DRAW_MAP_DESC,
        },
        title=STR.BBOX_SOURCE,
        parent=self,
    )
    self.layout.addWidget(bbox)
    extent_wgs84 = bbox.bbox_wgs84()
    clip = bbox.build_clip_data()
"""

from qgis.PyQt.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QGroupBox,
    QSizePolicy,
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
)
from qgis.gui import QgsMapLayerComboBox, QgsMapTool, QgsRubberBand

from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles
from ....core.config.LogUtils import LogUtils
from qgis.PyQt import sip

from ..simple.SimpleModernButton import SimpleModernButton


# ── Compatibilidade Qt5 / Qt6 — size policy ─────────────────────────
try:  # Qt6
    _SIZE_POLICY_PREFERRED = QSizePolicy.Policy.Preferred
    _SIZE_POLICY_FIXED = QSizePolicy.Policy.Fixed
except AttributeError:  # Qt5
    _SIZE_POLICY_PREFERRED = QSizePolicy.Preferred
    _SIZE_POLICY_FIXED = QSizePolicy.Fixed


# ── Compatibilidade Qt5 / Qt6 ─────────────────────────────────────────
def _qt_enum(name: str, group: str):
    """Resolve enum do Qt (ex: Qt.MouseButton.LeftButton vs Qt.LeftButton)."""
    try:
        return getattr(getattr(Qt, group), name)
    except AttributeError:
        return getattr(Qt, name)


_LEFT_BUTTON = _qt_enum("LeftButton", "MouseButton")
_RIGHT_BUTTON = _qt_enum("RightButton", "MouseButton")


def _cross_cursor():
    """Cursor cruz para a ferramenta de desenho (Qt5/Qt6)."""
    try:
        return Qt.CursorShape.CrossCursor
    except AttributeError:
        return Qt.CrossCursor


# ── Compatibilidade QGIS 3.x / 4.x ────────────────────────────────────
def _polygon_geometry_type():
    """Retorna o enum de geometria de polígono (QGIS 3.x e 4.x)."""
    try:
        from qgis.core import Qgis  # pylint: disable=import-outside-toplevel

        return Qgis.GeometryType.Polygon
    except (ImportError, AttributeError):
        from qgis.core import QgsWkbTypes  # pylint: disable=import-outside-toplevel

        return QgsWkbTypes.PolygonGeometry


def _layer_geometry_name(layer) -> str:
    """Nome da geometria da camada ("raster"|"polygon"|"line"|"point"/"")."""
    if isinstance(layer, QgsRasterLayer):
        return "raster"
    try:
        from qgis.core import Qgis  # pylint: disable=import-outside-toplevel

        geom = int(layer.geometryType())
        if geom == int(Qgis.GeometryType.Point):
            return "point"
        if geom == int(Qgis.GeometryType.LineString):
            return "line"
        if geom == int(Qgis.GeometryType.Polygon):
            return "polygon"
        return ""
    except (AttributeError, ImportError):
        pass
    try:
        from qgis.core import QgsWkbTypes  # pylint: disable=import-outside-toplevel

        geom = int(layer.geometryType())
        if geom == int(QgsWkbTypes.PointGeometry):
            return "point"
        if geom == int(QgsWkbTypes.LineGeometry):
            return "line"
        if geom == int(QgsWkbTypes.PolygonGeometry):
            return "polygon"
        return ""
    except (AttributeError, ImportError):
        return "polygon"


class _MapExtentDrawTool(QgsMapTool):
    """
    Ferramenta de desenho de polígono no canvas para definir a extensão.

    Clique esquerdo adiciona vértices; botão direito ou duplo clique conclui.
    Chama ``on_finished(QgsGeometry | None)`` ao concluir.
    """

    def __init__(self, canvas, on_finished):
        super().__init__(canvas)
        self._on_finished = on_finished
        self._rubber = QgsRubberBand(canvas, _polygon_geometry_type())
        self._rubber.setColor(QColor(255, 80, 80, 110))
        self._rubber.setWidth(3)
        self.setCursor(_cross_cursor())
        self._points = []

    def canvasPressEvent(self, event):
        if event.button() == _RIGHT_BUTTON:
            if self._points:
                self._finish()
            return
        if event.button() != _LEFT_BUTTON:
            return
        point = self.toMapCoordinates(event.pos())
        self._points.append(point)
        if len(self._points) == 1:
            self._rubber.reset()
        self._rubber.addPoint(point)
        self._rubber.show()

    def canvasDoubleClickEvent(self, event):
        if self._points:
            self._points.pop()  # duplo clique também dispara press; remove duplicado
        self._finish()

    def deactivate(self):
        self._points = []
        try:
            self._rubber.reset()
        except RuntimeError:
            pass
        super().deactivate()

    def _finish(self):
        geometry = None
        if len(self._points) >= 3:
            polygon = QgsGeometry.fromPolygonXY([list(self._points)])
            if not polygon.isEmpty():
                geometry = polygon
        self._points = []
        try:
            self.canvas().unsetMapTool(self)
        except RuntimeError:
            pass
        if geometry is not None and self._on_finished is not None:
            self._on_finished(geometry)


class GridBBoxSelector(QWidget):
    """
    Seletor de extensão de linha única: camada, tela atual ou desenho no mapa.

    Parâmetros
    ----------
    iface : QgisInterface, optional
        Interface do QGIS (canvas para "tela" e "desenhar").
    config : dict, optional
        Dict com labels: "capture_label", "capture_description",
        "draw_label" e "draw_description".
    title : str, optional
        Título do grupo (QGroupBox).
    separator_top / separator_bottom : bool, optional
        Separadores acima/abaixo.
    parent : QWidget, optional
        Widget pai.

    Autoconfiguração
    ----------------
    - AppStyles.map_layer_combobox() no QgsMapLayerComboBox
    - SimpleModernButton nos botões

    Pré-visualização
    ----------------
    Após selecionar a extensão, uma borda vermelha é desenhada no canvas
    apenas como feedback breve e some sozinha após ``_PREVIEW_CLEAR_MS`` ms
    (comportamento fiel ao QGIS, sem deixar marca permanente na tela).
    """

    # Tempo (ms) até a prévia vermelha sumir sozinha do canvas.
    _PREVIEW_CLEAR_MS = 3000

    def __init__(
        self,
        iface=None,
        config: dict = None,
        title: str = "",
        separator_top: bool = False,
        separator_bottom: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.iface = iface
        self._config = config or {}
        self._title = title
        self._separator_top = separator_top
        self._separator_bottom = separator_bottom
        self._logger = LogUtils(
            tool="GridBBoxSelector", class_name="GridBBoxSelector"
        )

        # Estado armazenado (boundary, path e tipo de entrada)
        self._tipo = "canvas"
        self._boundary = None  # QgsRectangle
        self._boundary_crs = None  # QgsCoordinateReferenceSystem
        self._path = ""
        self._geom_type = ""
        self._polygon_wkt = None  # WKT EPSG:4326 (polígono desenhado)
        self._polygon_crs_wkt = None  # WKT no CRS da tela (pré-visualização)

        # Widgets / ferramenta
        self._combo = None
        self._btn_capture = None
        self._btn_draw = None
        self._rubber_preview = None
        self._draw_tool = None
        self._previous_tool = None
        self._preview_timer = None  # QTimer p/ limpar a prévia automaticamente

        self._build_ui()

    # ── API pública ────────────────────────────────────────────────

    def get_input_type(self) -> str:
        """Retorna o tipo de entrada: "drawn"|"layer"|"canvas"."""
        return self._tipo

    def get_extent(self):
        """Retorna a extensão atual (QgsRectangle) no CRS da origem."""
        return self._boundary

    def get_crs(self):
        """Retorna o CRS da extensão atual (ou None)."""
        return self._boundary_crs

    def get_layer_path(self) -> str:
        """Retorna o path da camada quando a origem for uma camada."""
        if self._tipo == "layer":
            return self._path
        return ""

    def get_polygon_wkt(self):
        """Retorna o WKT (EPSG:4326) do polígono desenhado, ou None."""
        return self._polygon_wkt

    def is_polygon_clip(self) -> bool:
        """True quando o recorte deve usar o formato do polígono (máscara)."""
        if self._tipo == "drawn":
            return bool(self._polygon_wkt)
        if self._tipo == "layer":
            return bool(self._geom_type == "polygon" and self._path)
        return False

    def bbox_wgs84(self) -> list:
        """Retorna a extensão reprojetada p/ EPSG:4326 [xmin,ymin,xmax,ymax]."""
        extent = self._boundary
        crs = self._boundary_crs
        if extent is None or crs is None:
            return []

        try:
            if crs.authid() == "EPSG:4326":
                return [
                    float(extent.xMinimum()),
                    float(extent.yMinimum()),
                    float(extent.xMaximum()),
                    float(extent.yMaximum()),
                ]
            transform = QgsCoordinateTransform(
                crs,
                QgsCoordinateReferenceSystem("EPSG:4326"),
                QgsProject.instance(),
            )
            transformed = transform.transformBoundingBox(extent)
            return [
                float(transformed.xMinimum()),
                float(transformed.yMinimum()),
                float(transformed.xMaximum()),
                float(transformed.yMaximum()),
            ]
        except Exception as e:  # noqa: BLE001 - transformação é opcional
            self._logger.warning(
                f"bbox_wgs84: falha na transformação: {e}",
                code="BBOX_TRANSFORM_ERROR",
            )
            return []

    def build_clip_data(self) -> dict:
        """
        Retorna os dados de recorte para a ferramenta.

        - polígono desenhado ou camada de polígono -> {"mode": "polygon", ...}
        - demais origens -> {"mode": "extent", "extent_wgs84": [...]}
        """
        wgs84 = self.bbox_wgs84()
        if self._tipo == "drawn" and self._polygon_wkt:
            return {
                "mode": "polygon",
                "polygon_wkt": self._polygon_wkt,
                "extent_wgs84": wgs84,
            }
        if self._tipo == "layer" and self._geom_type == "polygon":
            path = self.get_layer_path()
            if path:
                return {
                    "mode": "polygon",
                    "polygon_path": path,
                    "extent_wgs84": wgs84,
                }
        return {"mode": "extent", "extent_wgs84": wgs84}

    def is_clip_valid(self) -> bool:
        """Valida se há dado suficiente para o recorte (polígono ou extent)."""
        clip = self.build_clip_data()
        if clip.get("mode") == "polygon":
            return bool(clip.get("polygon_path") or clip.get("polygon_wkt"))
        return bool(clip.get("extent_wgs84"))

    def get_source(self) -> str:
        """Compat: origem da extensão ("canvas"|"raster"|"vector")."""
        if self._tipo == "drawn":
            return "canvas"
        if self._tipo == "layer":
            return "raster" if self._geom_type == "raster" else "vector"
        return "canvas"

    # ── Build ───────────────────────────────────────────────────────

    def _build_ui(self):
        """Monta a linha única: combo de camadas + botões Tela/Desenhar."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        theme = AppStyles._get_theme()

        if self._separator_top:
            outer.addWidget(SeparatorWidget())

        if self._title:
            container = QGroupBox(self._title)
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(
                theme.CONTAINER_MARGIN_LEFT,
                theme.CONTAINER_MARGIN_TOP,
                theme.CONTAINER_MARGIN_RIGHT,
                theme.CONTAINER_MARGIN_BOTTOM,
            )
        else:
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(theme.LAYOUT_VERTICAL_SPACING)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        # Combo com todas as camadas (raster + vetor)
        self._combo = QgsMapLayerComboBox(self)
        self._combo.setAllowEmptyLayer(True)
        self._combo.setShowCrs(True)
        self._combo.setStyleSheet(AppStyles.map_layer_combobox())
        self._combo.layerChanged.connect(self._on_layer_changed)
        row.addWidget(self._combo, 1)

        # Botão: definir extensão da tela atual
        self._btn_capture = SimpleModernButton(
            text=self._config.get("capture_label", "Tela"), parent=self
        )
        description = self._config.get("capture_description", "")
        if description:
            self._btn_capture.setToolTip(description)
        self._btn_capture.clicked.connect(self._on_capture_clicked)
        row.addWidget(self._btn_capture)

        # Botão: desenhar no mapa
        self._btn_draw = SimpleModernButton(
            text=self._config.get("draw_label", "Desenhar"), parent=self
        )
        draw_description = self._config.get("draw_description", "")
        if draw_description:
            self._btn_draw.setToolTip(draw_description)
        self._btn_draw.clicked.connect(self._on_draw_clicked)
        row.addWidget(self._btn_draw)

        container_layout.addLayout(row)
        outer.addWidget(container)

        if self._separator_bottom:
            outer.addWidget(SeparatorWidget())

        # Sem canvas, os botões de tela/desenho ficam desabilitados
        has_canvas = self._canvas() is not None
        self._btn_capture.setEnabled(has_canvas)
        self._btn_draw.setEnabled(has_canvas)

        # Tamanho mínimo do conteúdo — evita "encavalamento" no collapsible
        self.setMinimumHeight(self.minimumSizeHint().height())
        # Sem stretch vertical: o widget usa a altura do próprio conteúdo
        self.setSizePolicy(_SIZE_POLICY_PREFERRED, _SIZE_POLICY_FIXED)

    # ── Estado ──────────────────────────────────────────────────────

    def _set_state(self, tipo, boundary=None, crs=None, path="", geom_type=""):
        """Armazena boundary, path e tipo de entrada do widget."""
        self._tipo = tipo
        self._path = path or ""
        self._geom_type = geom_type or ""
        if boundary is not None:
            self._boundary = boundary
            self._boundary_crs = crs
        if tipo != "drawn":
            self._polygon_wkt = None
            self._polygon_crs_wkt = None

    def _canvas(self):
        """Canvas do QGIS (ou None)."""
        if self.iface is not None:
            return self.iface.mapCanvas()
        return None

    # ── Eventos ─────────────────────────────────────────────────────

    def _on_capture_clicked(self):
        """Captura a extensão atual da tela (canvas)."""
        canvas = self._canvas()
        if canvas is None:
            return
        self._set_state(
            tipo="canvas",
            boundary=canvas.extent(),
            crs=canvas.mapSettings().destinationCrs(),
        )
        self._redraw_extent()
        self._logger.info("Extensão capturada da tela", code="BBOX_CAPTURE_DONE")

    def _on_layer_changed(self, layer):
        """Usa a extensão da camada selecionada no combo."""
        if layer is None:
            return
        try:
            self._set_state(
                tipo="layer",
                boundary=layer.extent(),
                crs=layer.crs(),
                path=str(layer.source()).split("|")[0],
                geom_type=_layer_geometry_name(layer),
            )
            self._redraw_extent()
        except Exception as e:  # noqa: BLE001 - camada pode ter sido deletada
            self._logger.warning(
                f"Falha ao capturar extensão da camada: {e}",
                code="BBOX_LAYER_ERROR",
            )

    def _on_draw_clicked(self):
        """Ativa/desativa a ferramenta de desenho no mapa."""
        canvas = self._canvas()
        if canvas is None:
            return

        if self._draw_tool is not None and canvas.mapTool() == self._draw_tool:
            prev = self._previous_tool
            self._previous_tool = None
            self._draw_tool = None
            try:
                if prev is not None and not sip.isdeleted(prev):
                    canvas.setMapTool(prev)
            except RuntimeError:
                pass
            return

        self._previous_tool = canvas.mapTool()
        self._draw_tool = _MapExtentDrawTool(canvas, self._on_draw_finished)
        canvas.setMapTool(self._draw_tool)

    def _on_draw_finished(self, geometry):
        """Processa o polígono desenhado e restaura a ferramenta anterior."""
        try:
            if geometry is not None and not geometry.isEmpty():
                canvas = self._canvas()
                source_crs = (
                    canvas.mapSettings().destinationCrs()
                    if canvas is not None
                    else QgsCoordinateReferenceSystem("EPSG:4326")
                )
                wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
                geom_wgs84 = QgsGeometry(geometry)
                if canvas is not None and source_crs.authid() != wgs84.authid():
                    transform = QgsCoordinateTransform(
                        source_crs, wgs84, QgsProject.instance()
                    )
                    geom_wgs84.transform(transform)

                self._set_state(
                    tipo="drawn",
                    boundary=QgsRectangle(geometry.boundingBox()),
                    crs=source_crs,
                )
                self._polygon_wkt = geom_wgs84.asWkt()  # WGS84 (recorte/máscara)
                self._polygon_crs_wkt = self._polygon_wkt
                self._redraw_extent()
                self._logger.info(
                    "Polígono desenhado no mapa",
                    code="BBOX_DRAW_DONE",
                )
        except Exception as e:  # noqa: BLE001 - desenho é opcional
            self._logger.warning(
                f"Falha ao processar polígono desenhado: {e}",
                code="BBOX_DRAW_ERROR",
            )
        self._restore_previous_tool()

    def _restore_previous_tool(self):
        """Restaura a ferramenta do canvas anterior ao desenho."""
        canvas = self._canvas()
        if canvas is None:
            self._draw_tool = None
            self._previous_tool = None
            return
        prev = self._previous_tool
        self._previous_tool = None
        self._draw_tool = None
        try:
            if prev is not None and not sip.isdeleted(prev):
                canvas.setMapTool(prev)
        except RuntimeError:
            pass

    # ── Pré-visualização no canvas ──────────────────────────────────

    def _redraw_extent(self):
        """Desenha a extensão atual (rect ou polígono) no canvas."""
        canvas = self._canvas()
        if canvas is None:
            return

        if self._rubber_preview is not None:
            try:
                self._rubber_preview.reset()
            except RuntimeError:
                self._rubber_preview = None

        target_crs = canvas.mapSettings().destinationCrs()

        # Polígono desenhado: exibe o formato real
        if self._tipo == "drawn" and self._polygon_wkt:
            try:
                polygon = QgsGeometry.fromWkt(self._polygon_wkt)
                polygon.transform(
                    QgsCoordinateTransform(
                        QgsCoordinateReferenceSystem("EPSG:4326"),
                        target_crs,
                        QgsProject.instance(),
                    )
                )
                if self._rubber_preview is None:
                    self._rubber_preview = QgsRubberBand(
                        canvas, _polygon_geometry_type()
                    )
                    self._rubber_preview.setColor(QColor(255, 80, 80, 120))
                    self._rubber_preview.setWidth(2)
                self._rubber_preview.setToGeometry(polygon, target_crs)
                self._rubber_preview.show()
                self._schedule_preview_clear()
                return
            except Exception as e:  # noqa: BLE001 - preview é opcional
                self._logger.warning(
                    f"Preview do polígono falhou: {e}",
                    code="BBOX_PREVIEW_ERROR",
                )

        extent = self._boundary
        crs = self._boundary_crs
        if extent is None or crs is None:
            return

        try:
            transform = QgsCoordinateTransform(
                crs, target_crs, QgsProject.instance()
            )
            transformed = transform.transformBoundingBox(extent)
            rectangle = QgsGeometry.fromRect(transformed)
        except Exception:  # noqa: BLE001 - sem transformação usa extent puro
            rectangle = QgsGeometry.fromRect(extent)

        if self._rubber_preview is None:
            self._rubber_preview = QgsRubberBand(
                canvas, _polygon_geometry_type()
            )
            self._rubber_preview.setColor(QColor(255, 0, 0, 120))
            self._rubber_preview.setWidth(2)
        self._rubber_preview.setToGeometry(rectangle, target_crs)
        self._rubber_preview.show()
        self._schedule_preview_clear()

    def _schedule_preview_clear(self, delay_ms: int = None):
        """Agenda a limpeza da prévia (a borda some sozinha, como no QGIS)."""
        try:
            if self._preview_timer is None:
                self._preview_timer = QTimer(self)
                self._preview_timer.setSingleShot(True)
                self._preview_timer.timeout.connect(self._clear_preview)
            if delay_ms is None:
                delay_ms = self._PREVIEW_CLEAR_MS
            self._preview_timer.start(delay_ms)
        except RuntimeError:
            self._preview_timer = None

    def _clear_preview(self):
        """Remove a prévia (QgsRubberBand) do canvas sem apagar o estado."""
        if self._rubber_preview is None:
            return
        try:
            self._rubber_preview.reset()
            self._rubber_preview.hide()
        except RuntimeError:
            self._rubber_preview = None

    # ── Preferências ────────────────────────────────────────────────

    def get_preferences(self) -> dict:
        """Retorna dict para salvar em Preferences (boundary + tipo + path)."""
        return {
            "tipo": self._tipo,
            "path": self._path,
            "geom_type": self._geom_type,
            "boundary_wgs84": self.bbox_wgs84(),
            "polygon_wkt": self._polygon_wkt or "",
        }

    def set_preferences(self, prefs: dict):
        """Carrega estado de um dict vindo de Preferences."""
        if not prefs:
            return
        self._tipo = prefs.get("tipo", "canvas")
        self._path = prefs.get("path", "") or ""
        self._geom_type = prefs.get("geom_type", "") or ""
        self._polygon_wkt = prefs.get("polygon_wkt") or None
        self._polygon_crs_wkt = self._polygon_wkt

        boundary = prefs.get("boundary_wgs84") or []
        if len(boundary) == 4:
            try:
                self._boundary = QgsRectangle(*[float(v) for v in boundary])
                self._boundary_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            except (TypeError, ValueError) as e:
                self._logger.warning(
                    f"boundary inválido nas preferências: {e}",
                    code="BBOX_PREFS_INVALID",
                )

        if self._tipo == "layer" and self._path:
            self._select_layer_by_path(self._path)
        self._redraw_extent()

    def _select_layer_by_path(self, path: str):
        """Seleciona no combo a camada com o source informado."""
        if self._combo is None:
            return
        try:
            for layer in QgsProject.instance().mapLayers().values():
                if layer is not None and str(layer.source()).split("|")[0] == path:
                    self._combo.setLayer(layer)
                    return
        except RuntimeError:
            pass