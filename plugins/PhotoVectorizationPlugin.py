# -*- coding: utf-8 -*-
import os

from ..core.ui.WidgetFactory import WidgetFactory
from ..core.engine_tasks.AsyncPipelineEngine import AsyncPipelineEngine
from ..core.engine_tasks.ExecutionContext import ExecutionContext
from ..core.engine_tasks.PhotoVectorizationStep import PhotoVectorizationStep
from ..core.engine_tasks.ReportGenerationStep import ReportGenerationStep
from ..i18n.TranslationManager import STR
from ..plugins.BasePlugin import BasePluginMTL
from ..utils.Preferences import Preferences
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.ToolKeys import ToolKey


class PhotoVectorizationPlugin(BasePluginMTL):
    """Ferramenta dedicada para geração de vetores a partir de imagens."""

    TOOL_KEY = ToolKey.PHOTO_VECTORIZATION
    PREF_PHOTO_FOLDER = "photo_folder"
    PREF_PHOTO_RECURSIVE = "photo_recursive"
    PREF_PHOTO_GENERATE_REPORT = "photo_generate_report"

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.init(self.TOOL_KEY, self.__class__.__name__)

    def _build_ui(self, **kwargs):
        super()._build_ui(
            title=STR.PHOTO_VECTORIZATION_TITLE,
            icon_path="coord.ico",
            enable_scroll=True,
        )

        folder_layout, self.photo_folder_selector = WidgetFactory.create_path_selector(
            parent=self,
            title=STR.PHOTO_FOLDER,
            mode="folder",
            separator_top=False,
            separator_bottom=False,
        )

        photo_opts_layout, self.photo_opts_map = WidgetFactory.create_checkbox_grid(
            options_data={
                "photo_recursive": STR.RECURSIVE_SEARCH,
                "photo_generate_report": STR.GENERATE_REPORT,
            },
            items_per_row=1,
            checked_by_default=False,
            separator_top=False,
            separator_bottom=False,
        )

        buttons_layout, _ = WidgetFactory.create_bottom_action_buttons(
            parent=self,
            run_callback=self.execute_tool,
            close_callback=self.close,
            info_callback=self.show_info_dialog,
            tool_key=self.TOOL_KEY,
            run_text=STR.VECTORIZE_PHOTOS,
        )

        self.layout.add_items(
            [
                folder_layout,
                photo_opts_layout,
                buttons_layout,
            ]
        )

    def _save_prefs(self):
        photo_paths = self.photo_folder_selector.get_paths()
        photo_folder = photo_paths[0] if photo_paths else ""
        self.preferences[self.PREF_PHOTO_FOLDER] = photo_folder
        self.preferences[self.PREF_PHOTO_RECURSIVE] = bool(
            self.photo_opts_map["photo_recursive"].isChecked()
        )
        self.preferences[self.PREF_PHOTO_GENERATE_REPORT] = bool(
            self.photo_opts_map["photo_generate_report"].isChecked()
        )
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)

    def _load_prefs(self):
        folder = self.preferences.get(self.PREF_PHOTO_FOLDER, "")
        if folder:
            self.photo_folder_selector.set_path(folder)
        self.photo_opts_map["photo_recursive"].setChecked(
            self.preferences.get(self.PREF_PHOTO_RECURSIVE, True)
        )
        self.photo_opts_map["photo_generate_report"].setChecked(
            self.preferences.get(self.PREF_PHOTO_GENERATE_REPORT, True)
        )

    def execute_tool(self):
        self._run_photo_vectorization_with_task()

    def _run_photo_vectorization_with_task(self):
        photo_paths = self.photo_folder_selector.get_paths()
        photo_folder = (photo_paths[0] if photo_paths else "").strip()
        if not photo_folder or not os.path.isdir(photo_folder):
            QgisMessageUtil.modal_warning(self.iface, STR.SELECT_VALID_FOLDER)
            return

        recursive = bool(self.photo_opts_map["photo_recursive"].isChecked())
        generate_report = bool(self.photo_opts_map["photo_generate_report"].isChecked())

        try:
            self._save_prefs()

            context = ExecutionContext()
            context.set("base_folder", photo_folder)
            context.set("recursive", recursive)
            context.set("generate_report", generate_report)
            context.set("layer_name", STR.PHOTOS_WITHOUT_MRK_LAYER_NAME)
            context.set("tool_key", self.TOOL_KEY)
            context.set("iface", self.iface)

            steps = [PhotoVectorizationStep()]

            # Adicionar step de geração de relatório se solicitado
            if generate_report:
                steps.append(ReportGenerationStep())

            self.logger.info("Iniciando pipeline de vetorização de fotos", data={
                "base_folder": photo_folder,
                "recursive": recursive,
                "generate_report": generate_report
            })

            engine = AsyncPipelineEngine(
                steps=steps,
                context=context,
                on_finished=self._on_pipeline_finished,
                on_error=self._on_pipeline_error,
            )
            engine.start()

        except Exception as e:
            self.logger.error(f"Erro ao iniciar vetorização com TASK: {e}")
            QgisMessageUtil.modal_error(self.iface, f"{STR.ERROR}: {e}")

    def _on_pipeline_finished(self, context):
        """Callback chamado quando o pipeline de TASK é concluído com sucesso."""
        layer = context.get("layer")
        total_points = context.get("total_points", 0)
        json_path = context.get("json_path")
        report_payload = context.get("report_payload")

        summary = (
            f"{STR.SUCCESS_MESSAGE} "
            f"{STR.POINTS}: {total_points}"
        )

        if json_path:
            summary += f" | JSON: {json_path}"

        if report_payload and isinstance(report_payload, dict):
            html_path = report_payload.get("html_path")
            if html_path:
                summary += f" | HTML: {html_path}"

        self.logger.info("Pipeline de vetorização concluído", data={
            "total_points": total_points,
            "has_layer": layer is not None,
            "has_json": json_path is not None,
            "has_report": report_payload is not None
        })

        QgisMessageUtil.bar_success(self.iface, summary, duration=8)

    def _on_pipeline_error(self, context, exception):
        """Callback chamado quando ocorre erro no pipeline de TASK."""
        self.logger.error(f"Erro no pipeline de vetorização: {exception}")
        QgisMessageUtil.modal_error(self.iface, f"{STR.ERROR}: {exception}")

    def _run_photo_vectorization(self):
        """Método legado mantido para compatibilidade, mas não usado."""
        pass


def run(iface):
    dlg = PhotoVectorizationPlugin(iface)
    dlg.setModal(False)
    dlg.show()
    return dlg
