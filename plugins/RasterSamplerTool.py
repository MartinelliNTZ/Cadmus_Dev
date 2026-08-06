# -*- coding: utf-8 -*-
"""
RasterSamplerTool — Map tool de amostragem de valores de rasters.
=================================================================
Herda QgsMapTool (padrao CoordClickTool).

Ao ativar a ferramenta, a dialog ja abre direto com a selecao de rasters.
Ao clicar no canvas, amostra o valor de cada raster selecionado
e atualiza os labels com os valores.
"""

from qgis.gui import QgsMapTool
from qgis.core import QgsCoordinateTransform

from ..core.config.LogUtils import LogUtils
from ..utils.ToolKeys import ToolKey
from ..utils.ProjectUtils import ProjectUtils
from .RasterSamplerDialog import RasterSamplerDialog


class RasterSamplerTool(QgsMapTool):
    """Map tool que amostra valores de rasters no ponto clicado."""

    def __init__(self, iface):
        """Inicializa a map tool e abre a dialog imediatamente."""
        super().__init__(iface.mapCanvas())
        self.iface = iface
        self.canvas = iface.mapCanvas()

        self.dialog = None

        self.logger = LogUtils(
            tool=ToolKey.RASTER_SAMPLER, class_name="RasterSamplerTool"
        )
        self.logger.debug("RasterSamplerTool inicializado")

        # Abre a dialog imediatamente (diferente do CoordClickTool)
        self._open_dialog()

    # ------------------------------------------------------------------
    # Dialog
    # ------------------------------------------------------------------
    def _open_dialog(self):
        """Cria e exibe a dialog da ferramenta."""
        try:
            self.logger.debug("Criando RasterSamplerDialog")
            self.dialog = RasterSamplerDialog(self.iface)
            self.dialog.show()
            self.dialog.raise_()
            self.dialog.activateWindow()
            self.logger.debug("RasterSamplerDialog exibida")
        except Exception as e:
            self.logger.error(f"Erro ao abrir dialog de amostragem: {e}")

    def _ensure_dialog_visible(self):
        """Garante que a dialog esta visivel, recriando se necessario."""
        if not self.dialog or not self.dialog.isVisible():
            self._open_dialog()
        else:
            try:
                self.dialog.refresh_raster_list()
                self.dialog.raise_()
                self.dialog.activateWindow()
            except Exception as e:
                self.logger.error(f"Erro ao atualizar dialog: {e}")

    # ------------------------------------------------------------------
    # Eventos do canvas
    # ------------------------------------------------------------------
    def canvasReleaseEvent(self, event):
        """Captura o clique no mapa e amostra os rasters selecionados."""
        self.logger.debug("canvasReleaseEvent disparado")

        point = self.toMapCoordinates(event.pos())

        # Garante dialog visivel
        self._ensure_dialog_visible()

        # ── Amostragem ──
        selected_ids = self.dialog.get_selected_raster_ids()
        if not selected_ids:
            self.logger.debug("Nenhum raster selecionado")
            self.dialog.clear_values()
            return

        values = self._sample_rasters(point, selected_ids)
        self.dialog.set_raster_values(values)

    # ------------------------------------------------------------------
    # Amostragem
    # ------------------------------------------------------------------
    def _sample_rasters(self, point, layer_ids: list) -> dict:
        """
        Amostra o valor de cada raster no ponto clicado.

        Converte o ponto para o CRS de cada raster antes de amostrar.
        Retorna dict {layer_id: valor} — valor None quando NoData/fora.
        """
        values = {}
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        project = ProjectUtils.get_project_instance()

        for layer_id in layer_ids:
            layer = project.mapLayer(layer_id)
            if layer is None:
                self.logger.warning(f"Raster {layer_id} nao encontrado no projeto")
                values[layer_id] = None
                continue

            try:
                # Converte ponto para o CRS do raster
                raster_crs = layer.crs()
                if (
                    raster_crs.isValid()
                    and canvas_crs.isValid()
                    and raster_crs != canvas_crs
                ):
                    transform = QgsCoordinateTransform(canvas_crs, raster_crs, project)
                    sample_point = transform.transform(point)
                else:
                    sample_point = point

                # Amostra o raster
                provider = layer.dataProvider()
                if provider is None:
                    self.logger.warning(
                        f"Raster {layer.name()} sem dataProvider, pulando"
                    )
                    values[layer_id] = None
                    continue

                value, result_ok = provider.sample(sample_point, 1)
                if result_ok:
                    values[layer_id] = float(value)
                    self.logger.debug(
                        f"Raster {layer.name()} = {value} no ponto {sample_point}"
                    )
                else:
                    values[layer_id] = None
                    self.logger.debug(
                        f"Raster {layer.name()} sem dados no ponto (fora da extensao)"
                    )
            except Exception as e:
                self.logger.exception(e, code="RASTER_SAMPLE_ERROR")
                values[layer_id] = None

        return values