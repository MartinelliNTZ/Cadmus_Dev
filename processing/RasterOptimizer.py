# -*- coding: utf-8 -*-
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from qgis.core import (
    QgsProcessing,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from ..core.config.LogUtils import LogUtils
from ..i18n.TranslationManager import STR
from ..resources.IconManager import IconManager as im
from ..utils.ToolKeys import ToolKey
from .BaseProcessingAlgorithm import BaseProcessingAlgorithm

OVERVIEW_LEVELS_DEFAULT = ["2", "4", "8", "16", "32", "64", "128", "256"]
OVERVIEW_LEVEL_ALL = OVERVIEW_LEVELS_DEFAULT

RESAMPLING_METHODS = [
    "average",
    "nearest",
    "gauss",
    "cubic",
    "cubicspline",
    "lanczos",
    "mode",
]

COMPRESSION_METHODS = [
    "LZW",
    "DEFLATE",
    "ZSTD",
]

PREDICTOR_VALUES = [
    "1 (Default)",
    "2 (Horizontal)",
    "3 (Vertical)",
]


class RasterOptimizer(BaseProcessingAlgorithm):

    TOOL_KEY = ToolKey.RASTER_OPTIMIZER
    ALGORITHM_NAME = "raster_optimizer"
    ALGORITHM_DISPLAY_NAME = STR.RASTER_OPTIMIZER_TITLE
    ALGORITHM_GROUP = BaseProcessingAlgorithm.GROUP_RASTER
    INSTRUCTIONS_FILE = "raster_optimizer.html"
    logger = LogUtils(tool=TOOL_KEY, class_name="RasterOptimizer", level="DEBUG")
    ICON = im.RASTER_OPTIMIZER

    # Parameter names
    INPUT_RASTERS = "INPUT_RASTERS"
    INPUT_FOLDER = "INPUT_FOLDER"
    RECURSIVE = "RECURSIVE"
    OVERVIEW_LEVELS = "OVERVIEW_LEVELS"
    RESAMPLING = "RESAMPLING"
    COMPRESSION = "COMPRESSION"
    PREDICTOR = "PREDICTOR"
    ZLEVEL = "ZLEVEL"
    DELETE_EXISTING = "DELETE_EXISTING"
    BIGTIFF = "BIGTIFF"

    def initAlgorithm(self, config=None):
        self.logger.debug("Inicializando algoritmo RasterOptimizer...")

        self.load_preferences()

        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.INPUT_RASTERS,
                STR.INPUT_RASTER_LAYERS,
                QgsProcessing.TypeRaster,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_FOLDER,
                STR.INPUT_RASTER_FOLDER,
                behavior=QgsProcessingParameterFile.Folder,
                optional=True,
                defaultValue=self.prefs.get("last_folder", ""),
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.RECURSIVE,
                STR.USE_RECURSIVE_SEARCH,
                defaultValue=self.prefs.get("recursive", True),
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.OVERVIEW_LEVELS,
                STR.OVERVIEW_LEVELS,
                options=OVERVIEW_LEVEL_ALL,
                allowMultiple=True,
                defaultValue=self.prefs.get("overview_levels", [0, 1, 2, 3, 4, 5, 6, 7]),
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.RESAMPLING,
                STR.RESAMPLING_METHOD,
                options=RESAMPLING_METHODS,
                defaultValue=self.prefs.get("resampling", 0),
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.COMPRESSION,
                STR.COMPRESS_OVERVIEW,
                options=COMPRESSION_METHODS,
                defaultValue=self.prefs.get("compression", 0),  # LZW
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.PREDICTOR,
                STR.PREDICTOR,
                options=PREDICTOR_VALUES,
                defaultValue=self.prefs.get("predictor", 0),  # 1 (Default)
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.ZLEVEL,
                STR.ZLEVEL,
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=self.prefs.get("zlevel", 6),
                minValue=1,
                maxValue=9,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DELETE_EXISTING,
                STR.DELETE_EXISTING_OVERVIEWS,
                defaultValue=self.prefs.get("delete_existing", False),
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.BIGTIFF,
                STR.BIGTIFF_YES,
                defaultValue=self.prefs.get("bigtiff", False),
            )
        )

    def processAlgorithm(self, params, context, feedback):
        if feedback.isCanceled():
            return {}

        raster_layers = self.parameterAsLayerList(params, self.INPUT_RASTERS, context)
        input_folder = self.parameterAsString(params, self.INPUT_FOLDER, context)
        recursive = self.parameterAsBool(params, self.RECURSIVE, context)
        selected_levels = self.parameterAsEnums(params, self.OVERVIEW_LEVELS, context)
        resampling_idx = self.parameterAsEnum(params, self.RESAMPLING, context)
        compression_idx = self.parameterAsEnum(params, self.COMPRESSION, context)
        predictor_idx = self.parameterAsEnum(params, self.PREDICTOR, context)
        zlevel = self.parameterAsInt(params, self.ZLEVEL, context)
        delete_existing = self.parameterAsBool(params, self.DELETE_EXISTING, context)
        bigtiff = self.parameterAsBool(params, self.BIGTIFF, context)

        self.logger.debug(
            f"Parametros: folder={input_folder}, recursive={recursive}, "
            f"levels={selected_levels}, resampling={RESAMPLING_METHODS[resampling_idx]}, "
            f"compression={COMPRESSION_METHODS[compression_idx]}, "
            f"predictor={predictor_idx + 1}, zlevel={zlevel}, bigtiff={bigtiff}"
        )

        # Coletar rasters
        raster_paths = []

        # De camadas do projeto
        if raster_layers:
            for rl in raster_layers:
                path = rl.source()
                if path.lower().endswith(".tif") or path.lower().endswith(".tiff"):
                    if path not in raster_paths:
                        raster_paths.append(path)
                    self.logger.debug(f"Raster de camada adicionado: {path}")

        # De pasta
        if input_folder and os.path.isdir(input_folder):
            self.logger.debug(f"Buscando rasters em: {input_folder} (recursive={recursive})")
            for root, dirs, files in os.walk(input_folder):
                for f in files:
                    if f.lower().endswith(".tif") or f.lower().endswith(".tiff"):
                        full_path = os.path.join(root, f)
                        if full_path not in raster_paths:
                            raster_paths.append(full_path)
                if not recursive:
                    break

        if not raster_paths:
            feedback.pushInfo("Nenhum raster encontrado para processar.")
            self.logger.warning("Nenhum raster encontrado.")
            return {}

        # Converter indices de niveis para valores reais
        level_values = [OVERVIEW_LEVEL_ALL[i] for i in selected_levels]

        self.logger.info(f"Total de rasters para processar: {len(raster_paths)}")
        feedback.pushInfo(f"Total de rasters: {len(raster_paths)}")
        feedback.pushInfo(f"Niveis de overview: {', '.join(level_values)}")
        feedback.pushInfo(f"Compressao: {COMPRESSION_METHODS[compression_idx]}")
        feedback.pushInfo(f"Reamostragem: {RESAMPLING_METHODS[resampling_idx]}")

        # Salvar preferencias
        self.prefs.update(
            {
                "last_folder": input_folder,
                "recursive": bool(recursive),
                "overview_levels": selected_levels,
                "resampling": resampling_idx,
                "compression": compression_idx,
                "predictor": predictor_idx,
                "zlevel": zlevel,
                "delete_existing": bool(delete_existing),
                "bigtiff": bool(bigtiff),
            }
        )
        self.save_preferences()

        # Processar com ThreadPoolExecutor
        total = len(raster_paths)
        tasks = []

        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            for i, raster_path in enumerate(raster_paths):
                if feedback.isCanceled():
                    break

                tasks.append(
                    executor.submit(
                        self._process_single_raster,
                        raster_path,
                        level_values,
                        resampling_idx,
                        compression_idx,
                        predictor_idx,
                        zlevel,
                        delete_existing,
                        bigtiff,
                        feedback,
                    )
                )

            for future in as_completed(tasks):
                if feedback.isCanceled():
                    break
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Erro ao processar raster: {e}")
                    feedback.pushInfo(f"ERRO: {e}")

        feedback.pushInfo(STR.RASTER_OPTIMIZER_COMPLETED)
        self.logger.info("Otimizacao de rasters concluida.")
        return {}

    def _process_single_raster(
        self,
        raster_path,
        level_values,
        resampling_idx,
        compression_idx,
        predictor_idx,
        zlevel,
        delete_existing,
        bigtiff,
        feedback,
    ):
        self.logger.debug(f"Processando: {raster_path}")

        if not os.path.exists(raster_path):
            msg = f"Arquivo nao encontrado: {raster_path}"
            self.logger.warning(msg)
            feedback.pushInfo(msg)
            return

        # Deletar overviews existentes se solicitado
        if delete_existing:
            self._delete_overviews(raster_path, feedback)

        # Construir comando gdaladdo
        resampling = RESAMPLING_METHODS[resampling_idx]
        compression = COMPRESSION_METHODS[compression_idx]
        predictor_value = str(predictor_idx + 1)

        cmd = [
            "gdaladdo",
            "-r", resampling,
            "--config", "COMPRESS_OVERVIEW", compression,
            "--config", "PREDICTOR_OVERVIEW", predictor_value,
            "--config", "ZLEVEL", str(zlevel),
            raster_path,
            *level_values,
        ]

        if bigtiff:
            cmd.insert(1, "--config")
            cmd.insert(2, "BIGTIFF_OVERVIEW")
            cmd.insert(3, "YES")

        self.logger.debug(f"Comando: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        feedback.pushInfo(f"[{os.path.basename(raster_path)}] {line.strip()}")
            feedback.pushInfo(f"OK: {os.path.basename(raster_path)}")
            self.logger.debug(f"Overviews criadas com sucesso: {raster_path}")
        except subprocess.CalledProcessError as e:
            msg = f"Falha ao criar overviews para {os.path.basename(raster_path)}: {e.stderr.strip()}"
            self.logger.error(msg)
            feedback.pushInfo(msg)
        except Exception as e:
            msg = f"Erro inesperado em {os.path.basename(raster_path)}: {e}"
            self.logger.error(msg)
            feedback.pushInfo(msg)

    def _delete_overviews(self, raster_path, feedback):
        """Remove overviews existentes de um TIFF usando gdaladdo -clean."""
        self.logger.debug(f"Limpando overviews existentes: {raster_path}")
        try:
            cmd = ["gdaladdo", "-clean", raster_path]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.logger.debug(f"Overviews limpas: {raster_path}")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Falha ao limpar overviews (pode ser ignorado): {e.stderr.strip()}")
        except Exception as e:
            self.logger.warning(f"Erro ao limpar overviews: {e}")