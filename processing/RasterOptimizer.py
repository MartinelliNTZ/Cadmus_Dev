# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import time

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

# Fator de estimativa de espaço para overviews internos
# Overviews internos somam ~33% do tamanho original (pirâmide geométrica)
OVERVIEW_DISK_FACTOR = 0.34


def _estimate_overview_size(raster_path):
    """
    Estima o espaço necessário para overviews internos.
    A soma de uma pirâmide geométrica converge para ~1/3 do tamanho original.
    """
    try:
        return int(os.path.getsize(raster_path) * OVERVIEW_DISK_FACTOR)
    except OSError:
        return 0


def _free_disk_space(path):
    """Retorna espaço livre em disco no mesmo volume do arquivo."""
    try:
        total, used, free = shutil.disk_usage(os.path.dirname(os.path.abspath(path)))
        return free
    except OSError:
        return None


def _has_internal_overviews(raster_path):
    """
    Verifica se o raster já possui overviews internos usando gdalinfo.
    Retorna (tem_overviews: bool, níveis: list[str])
    """
    try:
        result = subprocess.run(
            ["gdalinfo", raster_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        lines = result.stdout.splitlines()
        levels = [
            line.strip()
            for line in lines
            if "Overview" in line and "x" in line
        ]
        return len(levels) > 0, levels
    except Exception:
        return False, []


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
    SKIP_IF_HAS_OVERVIEWS = "SKIP_IF_HAS_OVERVIEWS"

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

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SKIP_IF_HAS_OVERVIEWS,
                STR.SKIP_IF_HAS_OVERVIEWS if hasattr(STR, "SKIP_IF_HAS_OVERVIEWS")
                else "Pular rasters que já possuem overviews internos",
                defaultValue=self.prefs.get("skip_if_has_overviews", True),
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
        skip_if_has_overviews = self.parameterAsBool(params, self.SKIP_IF_HAS_OVERVIEWS, context)

        self.logger.debug(
            f"Parametros: folder={input_folder}, recursive={recursive}, "
            f"levels={selected_levels}, resampling={RESAMPLING_METHODS[resampling_idx]}, "
            f"compression={COMPRESSION_METHODS[compression_idx]}, "
            f"predictor={predictor_idx + 1}, zlevel={zlevel}, bigtiff={bigtiff}, "
            f"skip_if_has_overviews={skip_if_has_overviews}"
        )

        # ── Coletar rasters ────────────────────────────────────────────────

        raster_paths = []

        if raster_layers:
            for rl in raster_layers:
                path = rl.source()
                if path.lower().endswith((".tif", ".tiff")):
                    if path not in raster_paths:
                        raster_paths.append(path)
                    self.logger.debug(f"Raster de camada adicionado: {path}")

        if input_folder and os.path.isdir(input_folder):
            self.logger.debug(f"Buscando rasters em: {input_folder} (recursive={recursive})")
            for root, dirs, files in os.walk(input_folder):
                for f in files:
                    if f.lower().endswith((".tif", ".tiff")):
                        full_path = os.path.join(root, f)
                        if full_path not in raster_paths:
                            raster_paths.append(full_path)
                if not recursive:
                    break

        if not raster_paths:
            feedback.pushInfo("Nenhum raster encontrado para processar.")
            self.logger.warning("Nenhum raster encontrado.")
            return {}

        # ── Converter índices de níveis para valores reais ─────────────────

        level_values = [OVERVIEW_LEVEL_ALL[i] for i in selected_levels]

        total = len(raster_paths)
        self.logger.info(f"Total de rasters para processar: {total}")
        feedback.pushInfo(f"Total de rasters encontrados: {total}")
        feedback.pushInfo(f"Níveis de overview: {', '.join(level_values)}")
        feedback.pushInfo(f"Compressão: {COMPRESSION_METHODS[compression_idx]}")
        feedback.pushInfo(f"Reamostragem: {RESAMPLING_METHODS[resampling_idx]}")
        feedback.pushInfo("-" * 60)

        # ── Salvar preferências ────────────────────────────────────────────

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
                "skip_if_has_overviews": bool(skip_if_has_overviews),
            }
        )
        self.save_preferences()

        # ── Contadores para relatório final ────────────────────────────────

        count_ok = 0
        count_skipped = 0
        count_skipped_disk = 0
        count_failed = 0
        t_start = time.time()

        # ── Processar sequencialmente ──────────────────────────────────────

        for i, raster_path in enumerate(raster_paths, start=1):
            if feedback.isCanceled():
                feedback.pushInfo("Processamento cancelado pelo usuário.")
                break

            name = os.path.basename(raster_path)
            feedback.setProgress(int((i - 1) / total * 100))
            feedback.pushInfo(f"[{i}/{total}] {name}")

            # Arquivo existe?
            if not os.path.exists(raster_path):
                feedback.pushInfo(f"  IGNORADO — arquivo não encontrado: {raster_path}")
                self.logger.warning(f"Arquivo não encontrado: {raster_path}")
                count_failed += 1
                continue

            # Pular se já tem overviews internos?
            if skip_if_has_overviews and not delete_existing:
                has_ovr, existing_levels = _has_internal_overviews(raster_path)
                if has_ovr:
                    feedback.pushInfo(
                        f"  PULADO — já possui overviews internos: "
                        f"{', '.join(existing_levels[:4])}{'...' if len(existing_levels) > 4 else ''}"
                    )
                    self.logger.debug(f"Pulado (já tem overviews): {raster_path}")
                    count_skipped += 1
                    continue

            # Verificação de espaço em disco
            needed = _estimate_overview_size(raster_path)
            free = _free_disk_space(raster_path)
            if free is not None:
                needed_mb = needed / (1024 ** 2)
                free_mb = free / (1024 ** 2)
                feedback.pushInfo(
                    f"  Espaço estimado para overviews: {needed_mb:.1f} MB  |  "
                    f"Livre em disco: {free_mb:.1f} MB"
                )
                if free < needed * 1.2:  # margem de segurança de 20%
                    msg = (
                        f"  IGNORADO — espaço insuficiente. "
                        f"Necessário: {needed_mb:.1f} MB, disponível: {free_mb:.1f} MB."
                    )
                    feedback.pushInfo(msg)
                    self.logger.warning(msg)
                    count_skipped_disk += 1
                    continue

            # Processar
            ok = self._process_single_raster(
                raster_path=raster_path,
                level_values=level_values,
                resampling_idx=resampling_idx,
                compression_idx=compression_idx,
                predictor_idx=predictor_idx,
                zlevel=zlevel,
                delete_existing=delete_existing,
                bigtiff=bigtiff,
                feedback=feedback,
            )

            if ok:
                count_ok += 1
            else:
                count_failed += 1

        # ── Relatório final ────────────────────────────────────────────────

        elapsed = time.time() - t_start
        feedback.setProgress(100)
        feedback.pushInfo("=" * 60)
        feedback.pushInfo("RELATÓRIO FINAL")
        feedback.pushInfo("=" * 60)
        feedback.pushInfo(f"  Total encontrado      : {total}")
        feedback.pushInfo(f"  Processados (OK)      : {count_ok}")
        feedback.pushInfo(f"  Pulados (já otimizados): {count_skipped}")
        feedback.pushInfo(f"  Pulados (disco cheio) : {count_skipped_disk}")
        feedback.pushInfo(f"  Falhas                : {count_failed}")
        feedback.pushInfo(f"  Tempo total           : {elapsed:.1f}s")
        feedback.pushInfo("=" * 60)

        self.logger.info(
            f"Otimização concluída. ok={count_ok}, pulados={count_skipped}, "
            f"disco={count_skipped_disk}, falhas={count_failed}, tempo={elapsed:.1f}s"
        )

        return {
            "PROCESSED": count_ok,
            "SKIPPED": count_skipped,
            "SKIPPED_DISK": count_skipped_disk,
            "FAILED": count_failed,
            "ELAPSED_SECONDS": round(elapsed, 1),
        }

    # ── _process_single_raster ─────────────────────────────────────────────

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
        """
        Gera overviews internos no próprio GeoTIFF usando gdaladdo.
        Overviews externos (.ovr) NÃO são gerados: o arquivo de saída
        não usa -ro, garantindo que tudo fique embutido no .tif.
        Retorna True em sucesso, False em falha.
        """
        self.logger.debug(f"Processando: {raster_path}")

        # Deletar overviews existentes se solicitado
        if delete_existing:
            self._delete_overviews(raster_path, feedback)

        resampling = RESAMPLING_METHODS[resampling_idx]
        compression = COMPRESSION_METHODS[compression_idx]
        predictor_value = str(predictor_idx + 1)

        # Monta o comando gdaladdo para overviews INTERNOS
        # Nota: ausência de -ro garante gravação interna no .tif
        cmd = [
            "gdaladdo",
            "-r", resampling,
            "--config", "COMPRESS_OVERVIEW", compression,
            "--config", "PREDICTOR_OVERVIEW", predictor_value,
            "--config", "ZLEVEL_OVERVIEW", str(zlevel),
            "--config", "USE_RRD", "NO",          # nunca usar .aux/.rrd externo
            "--config", "GDAL_TIFF_OVR_BLOCKSIZE", "512",  # bloco maior = mais eficiente
        ]

        if bigtiff:
            cmd += ["--config", "BIGTIFF_OVERVIEW", "YES"]

        cmd += [raster_path, *level_values]

        self.logger.debug(f"Comando: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                for line in result.stdout.strip().splitlines():
                    if line.strip():
                        feedback.pushInfo(f"  {line.strip()}")
            feedback.pushInfo(f"  OK — overviews internos criados: {os.path.basename(raster_path)}")
            self.logger.debug(f"Overviews criadas com sucesso: {raster_path}")
            return True

        except subprocess.CalledProcessError as e:
            msg = f"  FALHA — {os.path.basename(raster_path)}: {e.stderr.strip()}"
            self.logger.error(msg)
            feedback.pushInfo(msg)
            return False

        except Exception as e:
            msg = f"  ERRO inesperado — {os.path.basename(raster_path)}: {e}"
            self.logger.error(msg)
            feedback.pushInfo(msg)
            return False

    # ── _delete_overviews ──────────────────────────────────────────────────

    def _delete_overviews(self, raster_path, feedback):
        """
        Remove overviews internos do TIFF usando gdaladdo -clean.
        Também remove arquivo .ovr externo residual, se existir.
        """
        self.logger.debug(f"Limpando overviews existentes: {raster_path}")

        # Limpar overviews internos
        try:
            cmd = ["gdaladdo", "-clean", raster_path]
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
            feedback.pushInfo(f"  Overviews internos removidos: {os.path.basename(raster_path)}")
            self.logger.debug(f"Overviews limpas: {raster_path}")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Falha ao limpar overviews (pode ser ignorado): {e.stderr.strip()}")
        except Exception as e:
            self.logger.warning(f"Erro ao limpar overviews: {e}")

        # Remover .ovr externo residual, se existir
        ovr_path = raster_path + ".ovr"
        if os.path.exists(ovr_path):
            try:
                os.remove(ovr_path)
                feedback.pushInfo(f"  Arquivo externo .ovr residual removido: {os.path.basename(ovr_path)}")
                self.logger.debug(f".ovr externo removido: {ovr_path}")
            except OSError as e:
                self.logger.warning(f"Não foi possível remover .ovr externo: {e}")