# -*- coding: utf-8 -*-
import os
import tempfile

from qgis.core import (
    QgsProcessingException,
    QgsProcessingLayerPostProcessorInterface,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterBand,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsRasterLayer,
)

from ..core.config.LogUtils import LogUtils
from ..i18n.TranslationManager import STR
from ..utils.ToolKeys import ToolKey
from ..utils.ExplorerUtils import ExplorerUtils
from ..utils.XmlUtil import XmlUtil
from .BaseProcessingAlgorithm import BaseProcessingAlgorithm


class RgbMosaicStylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    """
    Post-processor que aplica um estilo QML a uma camada raster
    imediatamente apos o QGIS carrega-la no projeto.
    Isso funciona com qualquer tipo de resultado (arquivo, memory, etc).
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
                    feedback.pushInfo(f"  [POST-PROCESSOR] Estilo aplicado via postProcessLayer: {self.qml_path}")
            else:
                if feedback:
                    feedback.pushInfo(f"  [POST-PROCESSOR] loadNamedStyle retornou False para: {self.qml_path}")
        except Exception as e:
            if feedback:
                feedback.pushInfo(f"  [POST-PROCESSOR] ERRO: {e}")


class RgbMosaicCreator(BaseProcessingAlgorithm):
    """
    QgsProcessingAlgorithm: Cria um mosaico RGB a partir de 3 rasters individuais
    (bandas R, G, B), com opcao de criar banda alpha para valores NoData.
    Ao final, salva o estilo QML na pasta temp e aplica no raster de saida.
    """

    TOOL_KEY = ToolKey.RGB_MOSAIC_CREATOR
    ALGORITHM_NAME = "rgb_mosaic_creator"
    ALGORITHM_DISPLAY_NAME = STR.RGB_MOSAIC_CREATOR_TITLE
    ALGORITHM_GROUP = BaseProcessingAlgorithm.GROUP_RASTER
    ICON = "cadmus_icon.ico"
    INSTRUCTIONS_FILE = "rgb_mosaic_creator.html"
    logger = LogUtils(tool=TOOL_KEY, class_name="RgbMosaicCreator", level="DEBUG")

    INPUT_R = "INPUT_R"
    BAND_R = "BAND_R"
    INPUT_G = "INPUT_G"
    BAND_G = "BAND_G"
    INPUT_B = "INPUT_B"
    BAND_B = "BAND_B"
    CREATE_ALPHA = "CREATE_ALPHA"
    ALPHA_NODATA = "ALPHA_NODATA"
    OUTPUT = "OUTPUT"
    DISPLAY_HELP = "DISPLAY_HELP"
    OPEN_OUTPUT_FOLDER = "OPEN_OUTPUT_FOLDER"

    def initAlgorithm(self, config=None):
        self.logger.debug("Inicializando algoritmo RgbMosaicCreator...")
        self.load_preferences()

        self.addParameter(
            QgsProcessingParameterRasterLayer(self.INPUT_R, STR.INPUT_RASTER_RED_BAND)
        )
        self.addParameter(
            QgsProcessingParameterBand(
                self.BAND_R,
                STR.BAND_RED_LABEL,
                parentLayerParameterName=self.INPUT_R,
                defaultValue=self.prefs.get("band_r", 1),
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterLayer(self.INPUT_G, STR.INPUT_RASTER_GREEN_BAND)
        )
        self.addParameter(
            QgsProcessingParameterBand(
                self.BAND_G,
                STR.BAND_GREEN_LABEL,
                parentLayerParameterName=self.INPUT_G,
                defaultValue=self.prefs.get("band_g", 1),
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterLayer(self.INPUT_B, STR.INPUT_RASTER_BLUE_BAND)
        )
        self.addParameter(
            QgsProcessingParameterBand(
                self.BAND_B,
                STR.BAND_BLUE_LABEL,
                parentLayerParameterName=self.INPUT_B,
                defaultValue=self.prefs.get("band_b", 1),
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.CREATE_ALPHA,
                STR.CREATE_ALPHA_BAND,
                defaultValue=self.prefs.get("create_alpha", True),
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.ALPHA_NODATA,
                STR.ALPHA_NODATA_VALUE,
                type=QgsProcessingParameterNumber.Double,
                defaultValue=self.prefs.get("alpha_nodata", 0.0),
                optional=True,
            )
        )

        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, STR.RGB_COMPOSITE))

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.OPEN_OUTPUT_FOLDER,
                STR.OPEN_OUTPUT_FOLDER,
                defaultValue=self.prefs.get("open_output_folder", True),
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DISPLAY_HELP,
                STR.DISPLAY_HELP_FIELD,
                defaultValue=self.prefs.get("display_help", True),
            )
        )

    def processAlgorithm(self, params, context, feedback):
        self.logger.debug("Iniciando processAlgorithm do RgbMosaicCreator...")

        try:
            raster_r = self.parameterAsRasterLayer(params, self.INPUT_R, context)
            raster_g = self.parameterAsRasterLayer(params, self.INPUT_G, context)
            raster_b = self.parameterAsRasterLayer(params, self.INPUT_B, context)

            if not raster_r or not raster_r.isValid():
                raise QgsProcessingException("Raster R (Vermelho) invalido ou nao encontrado.")
            if not raster_g or not raster_g.isValid():
                raise QgsProcessingException("Raster G (Verde) invalido ou nao encontrado.")
            if not raster_b or not raster_b.isValid():
                raise QgsProcessingException("Raster B (Azul) invalido ou nao encontrado.")

            band_r = self.parameterAsInt(params, self.BAND_R, context)
            band_g = self.parameterAsInt(params, self.BAND_G, context)
            band_b = self.parameterAsInt(params, self.BAND_B, context)

            create_alpha = self.parameterAsBool(params, self.CREATE_ALPHA, context)
            alpha_nodata = self.parameterAsDouble(params, self.ALPHA_NODATA, context)

            open_output_folder = self.parameterAsBool(params, self.OPEN_OUTPUT_FOLDER, context)
            display_help = self.parameterAsBool(params, self.DISPLAY_HELP, context)
            output_path = self.parameterAsOutputLayer(params, self.OUTPUT, context)

            feedback.pushInfo("=" * 50)
            feedback.pushInfo("CRIADOR DE MOSAICO RGB - CADMUS")
            feedback.pushInfo("=" * 50)
            feedback.pushInfo(f"R (Red):   {raster_r.source()}  | Banda {band_r}")
            feedback.pushInfo(f"G (Green): {raster_g.source()}  | Banda {band_g}")
            feedback.pushInfo(f"B (Blue):  {raster_b.source()}  | Banda {band_b}")
            feedback.pushInfo(f"Alpha: {'Sim' if create_alpha else 'Nao'}  |  NoData: {alpha_nodata}")
            feedback.pushInfo(f"Saida: {output_path}")

            from osgeo import gdal
            import numpy as np

            temp_dir = tempfile.mkdtemp(prefix="cadmus_rgb_")

            def _extract_band(raster, band_num, label):
                src_path = raster.source()
                band_path = os.path.join(temp_dir, f"band_{label}.tif")
                src_ds = gdal.Open(src_path, gdal.GA_ReadOnly)
                if src_ds is None:
                    raise QgsProcessingException(
                        f"Nao foi possivel abrir o raster {label}: {src_path}"
                    )
                gdal.Translate(band_path, src_ds, format="GTiff", bandList=[band_num])
                src_ds = None
                return band_path

            # --- FASE 1: Extrair bandas ---
            path_r = _extract_band(raster_r, band_r, "R")
            path_g = _extract_band(raster_g, band_g, "G")
            path_b = _extract_band(raster_b, band_b, "B")

            # --- FASE 2: Extrair min/max de cada banda com percentil 2%-98% (corte acumulativo) ---
            # O QGIS usa por padrao "Corte acumulativo 2% a 98%" mesmo com "Estender para MinMax"
            # Isso remove outliers e melhora o contraste visual.
            def _get_band_percentiles(band_path, label, lower_pct=2, upper_pct=98):
                """Retorna (p_lower, p_upper) de uma banda raster usando percentis.
                
                Simula o corte acumulativo 2%-98% que o QGIS aplica por padrao,
                ignorando pixels extremos (outliers).
                """
                ds = gdal.Open(band_path, gdal.GA_ReadOnly)
                if ds is None:
                    raise QgsProcessingException(f"Falha ao abrir banda {label}: {band_path}")
                band = ds.GetRasterBand(1)
                data = band.ReadAsArray()
                ds = None
                if data is None or data.size == 0:
                    raise QgsProcessingException(f"Dados vazios na banda {label}: {band_path}")
                p_low = float(np.percentile(data, lower_pct))
                p_high = float(np.percentile(data, upper_pct))
                return p_low, p_high

            min_r, max_r = _get_band_percentiles(path_r, "R")
            min_g, max_g = _get_band_percentiles(path_g, "G")
            min_b, max_b = _get_band_percentiles(path_b, "B")

            # --- FASE 3: Calcular min global e max global ---
            global_min = min(min_r, min_g, min_b)
            global_max = max(max_r, max_g, max_b)

            feedback.pushInfo(f"Estatisticas das bandas:")
            feedback.pushInfo(f"  R: min={min_r:.7f}  max={max_r:.7f}")
            feedback.pushInfo(f"  G: min={min_g:.7f}  max={max_g:.7f}")
            feedback.pushInfo(f"  B: min={min_b:.7f}  max={max_b:.7f}")
            feedback.pushInfo(f"  Global min={global_min:.7f}  Global max={global_max:.7f}")

            # --- FASE 4: Compor mosaico RGB ---
            feedback.pushInfo("Compondo bandas no mosaico RGB...")

            vrt_path = os.path.join(temp_dir, "rgb_composite.vrt")
            band_files = [path_r, path_g, path_b]

            vrt_options = gdal.BuildVRTOptions(separate=True)
            ds_vrt = gdal.BuildVRT(vrt_path, band_files, options=vrt_options)
            if ds_vrt is None:
                raise QgsProcessingException("Falha ao criar VRT do mosaico RGB.")
            ds_vrt = None

            num_bands = 3
            if create_alpha and alpha_nodata is not None:
                feedback.pushInfo("Criando banda alpha para NoData...")
                alpha_path = os.path.join(temp_dir, "alpha.tif")

                ds_r_alpha = gdal.Open(path_r, gdal.GA_ReadOnly)
                if ds_r_alpha is None:
                    raise QgsProcessingException("Falha ao abrir banda R para criar alpha.")

                drv = gdal.GetDriverByName("GTiff")
                ds_alpha = drv.Create(
                    alpha_path,
                    ds_r_alpha.RasterXSize,
                    ds_r_alpha.RasterYSize,
                    1,
                    gdal.GDT_Byte,
                )
                ds_alpha.SetGeoTransform(ds_r_alpha.GetGeoTransform())
                ds_alpha.SetProjection(ds_r_alpha.GetProjection())

                band_r_data = ds_r_alpha.GetRasterBand(1).ReadAsArray()

                nodata_mask = np.isclose(band_r_data, alpha_nodata, atol=1e-6)
                alpha_data = np.where(nodata_mask, 0, 255).astype(np.uint8)

                ds_alpha.GetRasterBand(1).WriteArray(alpha_data)
                ds_alpha.FlushCache()
                ds_alpha = None
                ds_r_alpha = None

                vrt_rgba_path = os.path.join(temp_dir, "rgba_composite.vrt")
                band_files_rgba = band_files + [alpha_path]
                vrt_options_rgba = gdal.BuildVRTOptions(separate=True)
                ds_vrt_rgba = gdal.BuildVRT(vrt_rgba_path, band_files_rgba, options=vrt_options_rgba)
                if ds_vrt_rgba is None:
                    raise QgsProcessingException("Falha ao criar VRT com banda alpha.")
                ds_vrt_rgba = None
                vrt_path = vrt_rgba_path
                num_bands = 4

            feedback.pushInfo(f"Gerando mosaico RGB com {num_bands} banda(s)...")

            translate_options = gdal.TranslateOptions(
                format="GTiff",
                bandList=list(range(1, num_bands + 1)),
                creationOptions=["COMPRESS=LZW", "BIGTIFF=IF_NEEDED", "TILED=YES"],
            )
            gdal.Translate(output_path, vrt_path, options=translate_options)

            feedback.pushInfo("Mosaico RGB criado com sucesso!")

            # --- FASE 5: Salvar estilo QML sidecar (mesmo nome, mesma pasta do .tif) ---
            # O QGIS carrega automaticamente um .qml ao lado do raster com o mesmo nome base
            # quando adiciona uma camada ao projeto. Isso funciona tanto via Processing
            # quanto manualmente.
            feedback.pushInfo("Gerando estilo QML com valores globais de contraste...")

            # Define numero de bandas para o renderizador
            if create_alpha and alpha_nodata is not None:
                # 4 bandas: R=1, G=2, B=3, alpha=4
                qml_root = XmlUtil.build_raster_multiband_qml(
                    min_value=global_min,
                    max_value=global_max,
                    red_band=1,
                    green_band=2,
                    blue_band=3,
                    alpha_band=4,
                    opacity=1.0,
                    algorithm="StretchToMinimumMaximum",
                )
            else:
                # 3 bandas: R=1, G=2, B=3, sem alpha
                qml_root = XmlUtil.build_raster_multiband_qml(
                    min_value=global_min,
                    max_value=global_max,
                    red_band=1,
                    green_band=2,
                    blue_band=3,
                    alpha_band=-1,
                    opacity=1.0,
                    algorithm="StretchToMinimumMaximum",
                )

            # Salva QML como sidecar: mesmo nome base, mesma pasta do output
            output_dir = os.path.dirname(output_path)
            output_base = os.path.splitext(os.path.basename(output_path))[0]
            qml_path = os.path.join(output_dir, f"{output_base}.qml")
            qml_ok = XmlUtil.save_qml_style(qml_root, qml_path)
            if qml_ok:
                feedback.pushInfo(f"[OK] Estilo QML salvo como sidecar: {qml_path}")
                self.logger.info(f"Sidecar QML salvo: {qml_path}")
            else:
                feedback.pushInfo(f"[ERRO] Falha ao salvar estilo QML sidecar em {qml_path}")
                self.logger.error(f"Falha ao salvar sidecar QML: {qml_path}")

            # --- FASE 6: Aplicar estilo carregando a layer e usando loadNamedStyle ---
            # Como QgsMapLayerStyle nao tem setXmlData nem readFromFile no QGIS 3.34,
            # a abordagem mais confiavel e: carregar o raster resultado como QgsRasterLayer,
            # aplicar loadNamedStyle, e registrar no temporaryLayerStore do context.
            # O QGIS entao carrega esta layer (ja estilizada) no projeto ao final.
            feedback.pushInfo("=" * 50)
            feedback.pushInfo("FASE 6 - Aplicando estilo no raster de saida")
            feedback.pushInfo("=" * 50)

            qml_exists = os.path.isfile(qml_path)
            tif_exists = os.path.isfile(output_path)
            tif_size = os.path.getsize(output_path) if tif_exists else 0
            feedback.pushInfo(f"  [VERIFICACAO] QML sidecar: existe={qml_exists} em {qml_path}")
            feedback.pushInfo(f"  [VERIFICACAO] Raster saida: existe={tif_exists} tamanho={tif_size} bytes em {output_path}")
            self.logger.info(f"FASE6: qml_exists={qml_exists}, tif_exists={tif_exists}, tif_size={tif_size}")

            # METODO PRINCIPAL: Carregar layer, aplicar estilo, registrar no context
            try:
                from qgis.core import QgsProject, QgsRasterLayer as QgsRL

                # Cria QgsRasterLayer apontando para o arquivo de saida
                styled_layer = QgsRL(output_path, "RGB Mosaic")
                if styled_layer and styled_layer.isValid():
                    feedback.pushInfo(f"  [LAYER] QgsRasterLayer criado e valido: {output_path}")
                    self.logger.info(f"Layer criada: {output_path}")

                    # Aplica o estilo QML
                    style_ok = styled_layer.loadNamedStyle(qml_path)
                    feedback.pushInfo(f"  [LAYER] loadNamedStyle({qml_path}) -> ok={style_ok}")
                    self.logger.info(f"loadNamedStyle applied: ok={style_ok}")

                    if style_ok:
                        styled_layer.triggerRepaint()
                        feedback.pushInfo(f"  [LAYER] triggerRepaint() chamado")

                    # Registra a layer (ja estilizada) no temporaryLayerStore
                    # O QGIS promove automaticamente temporary layers para o projeto
                    store = context.temporaryLayerStore()
                    store.addMapLayer(styled_layer)
                    feedback.pushInfo(f"  [LAYER] Adicionada ao temporaryLayerStore do context")
                    self.logger.info(f"Layer adicionada ao temporaryLayerStore")
                else:
                    feedback.pushInfo(f"  [LAYER] ERRO: Nao foi possivel carregar raster de saida como QgsRasterLayer")
                    self.logger.error(f"Falha ao criar QgsRasterLayer para {output_path}")
            except Exception as e_layer:
                feedback.pushInfo(f"  [LAYER] ERRO: {e_layer}")
                self.logger.error(f"Layer style exception: {e_layer}")

            # METODO 2 (backup): salva o QML tambem na pasta temp/styles
            try:
                temp_qml_dir = ExplorerUtils.ensure_temp_subfolder(
                    "styles", tool_key=self.TOOL_KEY
                )
                temp_qml_path = os.path.join(temp_qml_dir, f"{output_base}.qml")
                temp_ok = XmlUtil.save_qml_style(qml_root, temp_qml_path)
                if temp_ok:
                    feedback.pushInfo(f"  [BACKUP] Estilo salvo em temp/styles: {temp_qml_path}")
                    self.logger.info(f"Backup QML em temp/styles: {temp_qml_path}")
            except Exception as e_backup:
                feedback.pushInfo(f"  [BACKUP] ERRO: {e_backup}")

            self.prefs.update({
                "band_r": band_r,
                "band_g": band_g,
                "band_b": band_b,
                "create_alpha": create_alpha,
                "alpha_nodata": alpha_nodata,
                "open_output_folder": open_output_folder,
                "display_help": display_help,
            })
            self.save_preferences()

            if output_path and isinstance(output_path, str) and not output_path.startswith("memory:"):
                out_folder = os.path.dirname(output_path)
                if out_folder and open_output_folder:
                    self.open_folder_in_explorer(out_folder)

            feedback.pushInfo("Processamento concluido com sucesso.")
            return {self.OUTPUT: output_path}

        except QgsProcessingException:
            raise
        except ImportError as e:
            msg = f"Biblioteca necessaria nao disponivel: {e}"
            self.logger.error(msg)
            raise QgsProcessingException(msg)
        except Exception as e:
            msg = f"Erro nao tratado em processAlgorithm: {e}"
            self.logger.error(msg)
            raise QgsProcessingException(msg)