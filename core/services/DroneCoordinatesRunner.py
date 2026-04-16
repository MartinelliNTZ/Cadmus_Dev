# -*- coding: utf-8 -*-
import os
from ..engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from ..engine_tasks.ExecutionContext import ExecutionContext
from ..engine_tasks.MrkParseStep import MrkParseStep
from ..engine_tasks.PhotoMetadataStep import PhotoMetadataStep
from ...i18n.TranslationManager import STR
from ...utils.ProjectUtils import ProjectUtils
from ...utils.QgisMessageUtil import QgisMessageUtil
from ...utils.ToolKeys import ToolKey
from ...utils.ExplorerUtils import ExplorerUtils
from ...utils.vector.VectorLayerGeometry import VectorLayerGeometry
from ...utils.vector.VectorLayerSource import VectorLayerSource
from ...utils.Preferences import load_tool_prefs
from ...utils.mrk.MetadataFields import MetadataFields
from ...core.config.LogUtils import LogUtils
from .ReportGenerationService import ReportGenerationService


class DroneCoordinatesRunner:
    """Executa o pipeline de MRK fora da UI principal do dialog."""

    def __init__(self, iface, tool_key=ToolKey.DRONE_COORDINATES):
        self.iface = iface
        self.tool_key = tool_key
        self.logger = LogUtils(tool=tool_key, class_name="DroneCoordinatesRunner")
        self._engine = None
        self._on_finished = None
        self._on_error = None

    def run_mrk_file(
        self,
        file_path: str,
        *,
        on_finished=None,
        on_error=None,
    ) -> bool:
        if not ExplorerUtils.is_file(file_path):
            return False

        self._on_finished = on_finished
        self._on_error = on_error

        points_path = ExplorerUtils.build_suffixed_output_path(
            file_path, STR.POINTS.lower()
        )
        track_path = ExplorerUtils.build_suffixed_output_path(
            file_path, STR.TRACK.lower()
        )

        existing_points = VectorLayerSource.load_existing_vector_layer(
            points_path, tool_key=self.tool_key
        )

        existing_track = VectorLayerSource.load_existing_vector_layer(
            track_path, tool_key=self.tool_key
        )
        if existing_points and existing_track:
            self._load_layer(existing_points)
            self._load_layer(existing_track)
            QgisMessageUtil.bar_success(
                self.iface, STR.LOADED_EXISTING_GPKG, duration=4
            )
            if callable(self._on_finished):
                self._on_finished(
                    {
                        "file_path": file_path,
                        "points_layer": existing_points,
                        "track_layer": existing_track,
                        "used_existing": True,
                    }
                )
            return True

        # Carregar preferências para configurar o pipeline automaticamente
        prefs = load_tool_prefs(self.tool_key)
        apply_photos = prefs.get("photos", False)
        selected_required_fields = MetadataFields.normalize_selected_keys(
            prefs.get("required_fields_selected", []),
            allowed_keys=MetadataFields.required_keys(),
        )
        selected_custom_fields = MetadataFields.normalize_selected_keys(
            prefs.get("custom_fields_selected", []),
            allowed_keys=MetadataFields.custom_keys(),
        )
        selected_mrk_fields = MetadataFields.normalize_selected_keys(
            prefs.get("mrk_fields_selected", []),
            allowed_keys=MetadataFields.mrk_keys(),
        )
        extra_fields = None
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        context = ExecutionContext()
        context.set("paths", [file_path])
        context.set("recursive", False)
        context.set("extra_fields", extra_fields)
        context.set("selected_required_fields", selected_required_fields)
        context.set("selected_custom_fields", selected_custom_fields)
        context.set("selected_mrk_fields", selected_mrk_fields)
        context.set("tool_key", self.tool_key)
        context.set("points_layer_name", f"{base_name}_{STR.POINTS}")
        context.set("track_layer_name", f"{base_name}_{STR.TRACK}")
        context.set("auto_points_output_path", points_path)
        context.set("auto_track_output_path", track_path)
        context.set("source_mrk_file", file_path)

        # Montar steps conforme preferências (mesmo que DroneCoordinates plugin)
        steps = [MrkParseStep()]
        if apply_photos:
            steps.append(PhotoMetadataStep())

        self._engine = AsyncPipelineEngine(
            steps=steps,
            context=context,
            on_finished=self._on_pipeline_finished,
            on_error=self._on_pipeline_error,
        )
        self._engine.start()
        return True

    def _on_pipeline_finished(self, context: ExecutionContext):
        layer = context.get("layer")
        points = context.get("points", []) or []

        if not layer or not layer.isValid():
            self._notify_error(STR.ERROR_LAYER_NOT_FOUND)
            return

        points_output_path = context.get("auto_points_output_path")
        track_output_path = context.get("auto_track_output_path")

        points_layer_name = context.get("points_layer_name", STR.POINTS)
        track_layer_name = context.get("track_layer_name", STR.TRACK)

        points_layer = self._save_or_load_existing(
            layer,
            points_output_path,
            fallback_name=points_layer_name,
        )
        if points_layer and points_layer.id() != layer.id():
            ProjectUtils.remove_layer_from_project(layer)

        # Aplicar estilo QML nos pontos conforme preferência
        prefs = load_tool_prefs(self.tool_key)
        if (prefs.get("apply_style_points", False) and points_layer and points_layer.isValid()):
            qml_path = prefs.get("qml_path_points", "").strip()
            if qml_path and os.path.exists(qml_path):
                ok = points_layer.loadNamedStyle(qml_path)
                if isinstance(ok, tuple):
                    ok = ok[0]
                if ok:
                    points_layer.triggerRepaint()

        line_layer = VectorLayerGeometry.create_line_layer_from_points(
            points,
            name=track_layer_name,
            group_by_fields=["mrk_path", "mrk_file"],
            attribute_fields=MetadataFields.default_track_attribute_keys(),
        )

        track_layer = None
        if line_layer and line_layer.isValid():
            track_layer = self._save_or_load_existing(
                line_layer,
                track_output_path,
                fallback_name=track_layer_name,
            )

            # Aplicar estilo QML na trilha conforme preferência
            if (prefs.get("apply_style_track", False) and track_layer and track_layer.isValid()):
                qml_path = prefs.get("qml_path_track", "").strip()
                if qml_path and os.path.exists(qml_path):
                    ok = track_layer.loadNamedStyle(qml_path)
                    if isinstance(ok, tuple):
                        ok = ok[0]
                    if ok:
                        track_layer.triggerRepaint()

        json_path = context.get("photo_metadata_json_path")
        generate_report = prefs.get("generate_report", False)
        report_payload = None
        if generate_report:
            if json_path:
                try:
                    report_payload = ReportGenerationService(
                        tool_key=self.tool_key
                    ).generate_from_json(json_path)
                    self.logger.info(
                        "Report metadata gerado pelo runner",
                        data=report_payload,
                    )
                except Exception as e:
                    self.logger.error(
                        f"Falha ao gerar report metadata no runner: {e}"
                    )
            else:
                self.logger.warning(
                    "Runner com generate_report=True sem photo_metadata_json_path no contexto"
                )

        QgisMessageUtil.bar_success(self.iface, STR.CONVERT_FILE_SUCCESS, duration=4)
        if callable(self._on_finished):
            self._on_finished(
                {
                    "file_path": context.get("source_mrk_file"),
                    "points_layer": points_layer,
                    "track_layer": track_layer,
                    "used_existing": False,
                    "report_payload": report_payload,
                }
            )

    def _on_pipeline_error(self, errors):
        exc = errors[0] if errors else Exception(STR.CONVERT_FILE_ERROR)
        self._notify_error(str(exc))

    def _notify_error(self, message: str):
        QgisMessageUtil.bar_critical(self.iface, f"{STR.CONVERT_FILE_ERROR} {message}")
        if callable(self._on_error):
            self._on_error(message)

    def _save_or_load_existing(
        self,
        layer,
        output_path: str,
        *,
        fallback_name: str,
    ):
        existing = VectorLayerSource.load_existing_vector_layer(
            output_path, tool_key=self.tool_key
        )
        if existing:
            existing.setName(fallback_name)
            self._load_layer(existing)
            return existing

        saved_layer = VectorLayerSource.save_and_load_layer(
            layer,
            output_path,
            tool_key=self.tool_key,
            decision="overwrite",
        )

        if saved_layer and saved_layer.isValid():
            saved_layer.setName(fallback_name)
            self._load_layer(saved_layer)
            return saved_layer

        # Fallback: se falhar ao salvar, ainda disponibiliza a camada em memoria.
        layer.setName(fallback_name)
        self._load_layer(layer)
        return layer

    def _load_layer(self, layer):
        if not layer or not layer.isValid():
            return
        ProjectUtils.add_layer_if_missing(layer)
