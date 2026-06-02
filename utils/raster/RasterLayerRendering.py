# -*- coding: utf-8 -*-
import os
import xml.etree.ElementTree as ET

from typing import Optional

from qgis.core import (
    QgsProcessingLayerPostProcessorInterface,
    QgsRasterLayer,
)

from ..ToolKeys import ToolKey
from ..ExplorerUtils import ExplorerUtils
from ...core.config.LogUtils import LogUtils


class QmlStylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    """
    Post-processor que aplica um estilo QML a uma camada raster
    imediatamente apos o QGIS carrega-la no projeto.

    Uso tipico: dentro de processAlgorithm de um QgsProcessingAlgorithm,
    retornar este post-processor via context.layerToLoadOnCompletionDetails().
    """

    def __init__(self, qml_path: str):
        super().__init__()
        self.qml_path = qml_path

    def postProcessLayer(self, layer, context, feedback):
        if layer is None:
            return
        try:
            ok = layer.loadNamedStyle(self.qml_path)
            if ok:
                layer.triggerRepaint()
                if feedback:
                    feedback.pushInfo(
                        f"  [POST-PROCESSOR] Estilo aplicado via postProcessLayer: {self.qml_path}"
                    )
            else:
                if feedback:
                    feedback.pushInfo(
                        f"  [POST-PROCESSOR] loadNamedStyle retornou False para: {self.qml_path}"
                    )
        except Exception as e:
            if feedback:
                feedback.pushInfo(f"  [POST-PROCESSOR] ERRO: {e}")


class RasterLayerRendering:
    """
    Responsável pela simbologia e visualização de rasters.

    Escopo:
    - Definir estilos de renderização raster
    - Aplicar rampas de cor (color ramps)
    - Configurar transparência e contraste
    - Gerenciar simbologia por banda
    - Criar legendas e paletas
    - Salvar e aplicar estilos QML

    Responsabilidade Principal:
    - Orquestrar configuração visual de rasters
    - Aplicar estilos e rampas de cor
    - Garantir coerência de visualização

    NÃO é Responsabilidade:
    - Processar pixels (use RasterLayerProcessing)
    - Salvar ou carregar rasters (use RasterLayerSource)
    - Calcular estatísticas (use RasterLayerMetrics)
    - Alterar dados raster (qualquer modificação)
    """

    @staticmethod
    def _get_logger(tool_key: str = ToolKey.UNTRACEABLE) -> LogUtils:
        return LogUtils(tool=tool_key, class_name="RasterLayerRendering")

    # ------------------------------------------------------------------
    # Estilo QML sidecar
    # ------------------------------------------------------------------

    @staticmethod
    def save_sidecar_style(
        raster_path: str,
        qml_root: ET.Element,
        tool_key: str = ToolKey.UNTRACEABLE,
    ) -> Optional[str]:
        """
        Salva um estilo QML como sidecar (mesmo nome base, mesma pasta do raster).

        O QGIS carrega automaticamente um .qml ao lado do raster com o mesmo nome base.

        Args:
            raster_path: Caminho do raster (ex: /path/to/output.tif)
            qml_root: Elemento raiz XML do estilo (gerado por XmlUtil.build_raster_multiband_qml etc)
            tool_key: Chave da ferramenta para logging

        Returns:
            Caminho do arquivo .qml salvo, ou None em caso de erro
        """
        from ..XmlUtil import XmlUtil

        logger = RasterLayerRendering._get_logger(tool_key)
        logger.debug(f"save_sidecar_style: raster={raster_path}")

        if not raster_path:
            logger.error("save_sidecar_style: raster_path vazio")
            return None

        output_dir = os.path.dirname(raster_path)
        output_base = os.path.splitext(os.path.basename(raster_path))[0]
        qml_path = os.path.join(output_dir, f"{output_base}.qml")

        qml_ok = XmlUtil.save_qml_style(qml_root, qml_path)
        if qml_ok:
            logger.debug(f"save_sidecar_style: salvo em {qml_path}")
            return qml_path

        logger.error(f"save_sidecar_style: falha ao salvar QML em {qml_path}")
        return None

    # ------------------------------------------------------------------
    # Aplicar QML a uma layer
    # ------------------------------------------------------------------

    @staticmethod
    def apply_qml_to_layer(
        raster_path: str,
        qml_path: str,
        context=None,
        feedback=None,
        layer_name: str = "Result",
        tool_key: str = ToolKey.UNTRACEABLE,
    ) -> bool:
        """
        Carrega um raster como QgsRasterLayer, aplica estilo QML
        e registra no temporaryLayerStore do contexto.

        Args:
            raster_path: Caminho do arquivo raster
            qml_path: Caminho do arquivo QML
            context: QgsProcessingContext (para temporaryLayerStore)
            feedback: QgsProcessingFeedback (para mensagens)
            layer_name: Nome da camada no QGIS
            tool_key: Chave da ferramenta para logging

        Returns:
            True se conseguiu criar a layer e aplicar o estilo
        """
        logger = RasterLayerRendering._get_logger(tool_key)
        logger.debug(
            f"apply_qml_to_layer: raster={raster_path}, qml={qml_path}"
        )

        if not raster_path or not os.path.isfile(raster_path):
            logger.error(f"apply_qml_to_layer: raster inexistente: {raster_path}")
            return False
        if not qml_path or not os.path.isfile(qml_path):
            logger.error(f"apply_qml_to_layer: QML inexistente: {qml_path}")
            return False

        try:
            styled_layer = QgsRasterLayer(raster_path, layer_name)
            if not styled_layer or not styled_layer.isValid():
                logger.error(
                    f"apply_qml_to_layer: falha ao criar QgsRasterLayer para {raster_path}"
                )
                return False

            style_ok = styled_layer.loadNamedStyle(qml_path)
            if style_ok:
                styled_layer.triggerRepaint()
                if feedback:
                    feedback.pushInfo(
                        f"  [ESTILO] loadNamedStyle aplicado: {qml_path}"
                    )
            else:
                if feedback:
                    feedback.pushInfo(
                        f"  [ESTILO] loadNamedStyle retornou False: {qml_path}"
                    )

            if context is not None:
                store = context.temporaryLayerStore()
                store.addMapLayer(styled_layer)
                if feedback:
                    feedback.pushInfo("  [ESTILO] Layer registrada no temporaryLayerStore")

            logger.debug("apply_qml_to_layer: concluido com sucesso")
            return True

        except Exception as e:
            logger.error(f"apply_qml_to_layer: erro: {e}")
            if feedback:
                feedback.pushInfo(f"  [ESTILO] ERRO: {e}")
            return False

    # ------------------------------------------------------------------
    # Salvar backup do QML em temp/styles
    # ------------------------------------------------------------------

    @staticmethod
    def save_qml_backup(
        qml_root: ET.Element,
        output_base: str,
        tool_key: str = ToolKey.UNTRACEABLE,
    ) -> Optional[str]:
        """
        Salva uma cópia do estilo QML na pasta temp/styles do Cadmus.

        Args:
            qml_root: Elemento raiz XML do estilo
            output_base: Nome base do arquivo (sem extensão)
            tool_key: Chave da ferramenta para logging

        Returns:
            Caminho do arquivo .qml salvo, ou None
        """
        from ..XmlUtil import XmlUtil

        logger = RasterLayerRendering._get_logger(tool_key)

        try:
            temp_qml_dir = ExplorerUtils.ensure_temp_subfolder(
                "styles", tool_key=tool_key
            )
            temp_qml_path = os.path.join(temp_qml_dir, f"{output_base}.qml")
            temp_ok = XmlUtil.save_qml_style(qml_root, temp_qml_path)
            if temp_ok:
                logger.debug(f"save_qml_backup: salvo em {temp_qml_path}")
                return temp_qml_path
            logger.error("save_qml_backup: falha ao salvar QML backup")
            return None
        except Exception as e:
            logger.error(f"save_qml_backup: erro: {e}")
            return None

    # ------------------------------------------------------------------
    # Métodos pré-existentes (stubs)
    # ------------------------------------------------------------------

    def apply_single_band_renderer(
        self, raster, band_index, color_ramp_name, external_tool_key="untraceable"
    ):
        """Aplica renderizador de banda única com rampa de cores especificada."""
        pass

    def apply_multiband_renderer(
        self, raster, red_band, green_band, blue_band, external_tool_key="untraceable"
    ):
        """Aplica renderizador RGB usando três bandas especificadas."""
        pass

    def apply_paletted_renderer(
        self, raster, color_table, external_tool_key="untraceable"
    ):
        """Aplica renderizador com paleta de cores discreta para classificações."""
        pass

    def set_raster_opacity(
        self, raster, opacity_percentage, external_tool_key="untraceable"
    ):
        """Define a transparência/opacidade global do raster."""
        pass

    def set_band_opacity(
        self, raster, band_index, opacity_percentage, external_tool_key="untraceable"
    ):
        """Define a transparência de uma banda específica."""
        pass

    def apply_color_ramp(
        self,
        raster,
        band_index,
        color_ramp_name,
        invert_ramp,
        external_tool_key="untraceable",
    ):
        """Aplica rampa de cores a uma banda com opção de inversão."""
        pass

    def set_raster_contrast_enhancement(
        self, raster, enhancement_type, min_max_method, external_tool_key="untraceable"
    ):
        """Aplica enhançamento de contraste usando método especificado."""
        pass

    def create_color_table_from_values(
        self, unique_values, color_list, external_tool_key="untraceable"
    ):
        """Cria tabela de cores customizada para valores específicos."""
        pass

    def apply_hillshade_effect(
        self, raster, azimuth, altitude, external_tool_key="untraceable"
    ):
        """Aplica efeito de hillshade (sombra de terreno) com parâmetros de iluminação."""
        pass

    def generate_legend_for_raster(
        self, raster, legend_format, external_tool_key="untraceable"
    ):
        """Gera legenda visual baseada na simbologia atual do raster."""
        pass

    def apply_discrete_color_scheme(
        self, raster, band_index, num_classes, external_tool_key="untraceable"
    ):
        """Aplica esquema de cores discreto dividindo valores em n classes."""
        pass

    def export_rendering_style_to_file(
        self, raster, output_style_file, external_tool_key="untraceable"
    ):
        """Exporta configuração de renderização do raster para arquivo QML."""
        pass