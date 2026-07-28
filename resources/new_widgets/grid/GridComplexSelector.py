# -*- coding: utf-8 -*-
"""
GridComplexSelector — Grade de ComplexSelectors configurados por dicionário,
com suporte a linking entre selectores e dynamic_parent.
============================================================================
Plugins USAM este widget.

Cada ComplexSelector com parent tem seu próprio botão 📥 nativo.

Uso em plugins:
    grid = GridComplexSelector(
        config={
            "Entrada": {
                "label": "Arquivo de entrada",
                "description": "Selecione o arquivo LAS/LAZ",
                "file_filter": "LAS/LAZ (*.las *.laz)",
                "mode_type": "input",
                "allow_file": True,
                "allow_folder": True,
                "multiple": False,
                "layer_filters": QgsMapLayerProxyModel.PointCloud,
            },
            "Saída": {
                "label": "Pasta de saída",
                "description": "Pasta para salvar os arquivos",
                "mode_type": "output",
                "parent": "Entrada",
                "suffix": "_converted",
                "fixed_extension": "gpkg",
                "subfolder": "output",
                "fixed_name": "resultado.gpkg",
            },
        },
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    self.layout.addWidget(grid)

    # Salvar/carregar preferências
    prefs = grid.get_preferences()
    Preferences.save_tool_prefs(self.TOOL_KEY, {"my_grid": prefs})
    grid.set_preferences(Preferences.load_tool_prefs(self.TOOL_KEY).get("my_grid", {}))

    grid.get_paths()                    # ["/path/to/file.las", "/path/to/resultado.gpkg"]
    grid.get_path("Entrada")            # "/path/to/file.las"
    grid.get_path("Saída")              # "/path/to/resultado.gpkg"
    grid.set_path("Entrada", "/novo/path.las")
"""

from __future__ import annotations

import os
from functools import partial
from typing import Callable, Optional

from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QGroupBox,
)
from qgis.PyQt.QtCore import QTimer

from ..simple.ComplexSelector import ComplexSelector
from ..SeparatorWidget import SeparatorWidget
from ...styles.AppStyles import AppStyles
from ....core.config.LogUtils import LogUtils


class GridComplexSelector(QWidget):
    """
    Grade de ComplexSelectors configurados por dicionário.

    Suporta mode_type="input"/"output" com parent linking.
    dynamic_parent: filho adapta selection_mode conforme o pai.
    Cada output com parent exibe seu próprio botão 📥 nativo.

    Suporta parent cross-grid: parent="grid1.selector1" faz busca
    por um selector de outro GridComplexSelector registrado.
    """

    # Registro global de grids, para suporte a parent cross-grid
    _grid_registry: dict[str, "GridComplexSelector"] = {}

    def __init__(
        self,
        config: dict[str, dict] = None,
        tool_key=None,
        title: Optional[str] = None,
        grid_id: str = "",
        separator_top: bool = False,
        separator_bottom: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self._config = config or {}
        self._tool_key = tool_key
        self._grid_id = grid_id or ""
        self._separator_top = separator_top
        self._separator_bottom = separator_bottom

        self._logger = LogUtils(
            tool=self._tool_key or "GridComplexSelector",
            class_name="GridComplexSelector",
        )

        # Mapa interno: key -> ComplexSelector
        self._selectors: dict[str, ComplexSelector] = {}
        self._link_meta: dict[str, dict] = {}
        self._self_generated: dict[str, bool] = {}
        self._user_callbacks: dict[str, Optional[Callable]] = {}
        self._generating_output: set[str] = set()

        self._build(title)

        # Registra no registry global
        if self._grid_id:
            GridComplexSelector._grid_registry[self._grid_id] = self

    def __del__(self):
        if self._grid_id and self._grid_id in GridComplexSelector._grid_registry:
            del GridComplexSelector._grid_registry[self._grid_id]

    # ══════════════════════════════════════════════════════════════════
    # Preferências
    # ══════════════════════════════════════════════════════════════════

    def get_preferences(self) -> dict:
        """
        Retorna dict com todos os estados dos seletores para salvar em Preferences.

        Inclui:
        - paths de cada selector
        - lock_state de cada selector (se allow_lock_check)
        - checked_state de cada selector (se allow_features_check)

        QgsMapLayerComboBox não é salvo.
        """
        prefs = {}
        for key, sel in self._selectors.items():
            item = {}
            p = sel.path()
            if p:
                item["path"] = p
            # Lock state
            if self._link_meta.get(key, {}).get("allow_lock_check", False) or \
               hasattr(sel, '_allow_lock_check') and sel._allow_lock_check:
                item["lock_state"] = sel.get_lock_state()
            # Features/checked state
            if self._link_meta.get(key, {}).get("allow_features_check", False) or \
               hasattr(sel, '_allow_features_check') and sel._allow_features_check:
                item["checked_state"] = sel.get_checked_state()
            if item:
                prefs[key] = item
        return prefs

    def set_preferences(self, prefs: dict):
        """
        Carrega todos os estados de um dict (vindo de Preferences).

        Inclui:
        - paths de cada selector
        - lock_state de cada selector (se existir no prefs)
        - checked_state de cada selector (se existir no prefs)
        """
        if not prefs:
            return
        for key, data in prefs.items():
            sel = self._selectors.get(key)
            if not sel:
                continue
            # Trata formato antigo (string direta) e novo (dict)
            if isinstance(data, str):
                path = data
            elif isinstance(data, dict):
                path = data.get("path", "")
                lock_state = data.get("lock_state")
                if lock_state is not None:
                    sel.set_lock_state(bool(lock_state))
                checked_state = data.get("checked_state")
                if checked_state is not None:
                    sel.set_checked_state(bool(checked_state))
            else:
                path = ""
            if path:
                sel.set_path(path)

    # ══════════════════════════════════════════════════════════════════
    # API Pública para Callbacks
    # ══════════════════════════════════════════════════════════════════

    def set_on_input_changed(self, callback: Optional[Callable[[str, list[str]], None]]):
        """
        Registra callback para quando QUALQUER selector de entrada mudar.
        O plugin NÃO precisa saber de parent-child relationships.
        """
        for label, selector in self._selectors.items():
            meta = self._link_meta.get(label, {})
            if meta.get("mode_type") == "output":
                continue
            if callback is not None:
                self._user_callbacks[label] = lambda paths, _label=label: callback(
                    _label, paths)
            else:
                self._user_callbacks[label] = None
            if not getattr(selector, '_grid_wrapper_installed', False):
                self._install_user_callback_wrapper(label, selector)

    def set_on_changed(self, label: str, callback: Optional[Callable[[list[str]], None]]):
        self._user_callbacks[label] = callback
        selector = self._selectors.get(label)
        if selector and not getattr(selector, '_grid_wrapper_installed', False):
            self._install_user_callback_wrapper(label, selector)

    def _install_user_callback_wrapper(self, label: str, selector: ComplexSelector):
        original_cb = selector.on_path_change

        def wrapper(paths: list[str]):
            if original_cb:
                original_cb(paths)
            user_cb = self._user_callbacks.get(label)
            if user_cb and user_cb is not original_cb:
                user_cb(paths)

        selector.on_path_change = wrapper
        selector._grid_wrapper_installed = True  # type: ignore[attr-defined]

    # ══════════════════════════════════════════════════════════════════
    # Build
    # ══════════════════════════════════════════════════════════════════

    def _build(self, title: Optional[str]):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        if self._separator_top:
            outer_layout.addWidget(SeparatorWidget())

        if title:
            container = QGroupBox(title)
            inner = QVBoxLayout(container)
        else:
            container = QWidget()
            inner = QVBoxLayout(container)

        theme = AppStyles._get_theme()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(theme.LAYOUT_VERTICAL_SPACING)

        for label, field_config in self._config.items():
            selector = self._build_selector(label, field_config)
            inner.addWidget(selector)
            self._selectors[label] = selector

        outer_layout.addWidget(container)

        if self._separator_bottom:
            outer_layout.addWidget(SeparatorWidget())

    def _resolve_parent_selector(self, parent_key: str) -> Optional[ComplexSelector]:
        if parent_key in self._selectors:
            return self._selectors[parent_key]

        if "." in parent_key:
            grid_id, sel_label = parent_key.split(".", 1)
            grid = GridComplexSelector._grid_registry.get(grid_id)
            if grid:
                return grid.get(sel_label)

        self._logger.warning(
            f"Parent '{parent_key}' não encontrado (local nem cross-grid)",
            code="GRID_PARENT_NOT_FOUND",
        )
        return None

    def _build_selector(self, label: str, field_config: dict) -> ComplexSelector:
        """Constrói um ComplexSelector com base no field_config."""
        label_text = field_config.get("label", label)
        description = field_config.get("description", "")
        path = field_config.get("path", "")
        mode_type = field_config.get("mode_type", "input")
        parent_key = field_config.get("parent", "")
        suffix = field_config.get("suffix", "")
        fixed_extension = field_config.get("fixed_extension", "")
        subfolder = field_config.get("subfolder", "")
        fixed_name = field_config.get("fixed_name", "")
        allow_file = field_config.get("allow_file", True)
        allow_folder = field_config.get("allow_folder", False)
        multiple = field_config.get("multiple", False)
        file_filter = field_config.get("file_filter", "Todos (*.*)")
        layer_filters = field_config.get("layer_filters", None)
        show_explorer_button = field_config.get("show_explorer_button", True)
        show_copy_button = field_config.get("show_copy_button", True)
        allow_layer = field_config.get("allow_layer", False)
        allow_lock_check = field_config.get("allow_lock_check", False)
        lock_check_default = field_config.get("lock_check_default", True)
        allow_features_check = field_config.get("allow_features_check", False)
        features_check_text = field_config.get("features_check_text", "")
        features_check_default = field_config.get("features_check_default", False)

        # Resolve o parent_selector
        parent_selector = None
        if parent_key:
            parent_selector = self._resolve_parent_selector(parent_key)

        selector = ComplexSelector(
            label_text=label_text,
            default_path=path,
            tooltip=description,
            file_filter=file_filter,
            allow_file=allow_file,
            allow_folder=allow_folder,
            multiple=multiple,
            selection_mode="file" if allow_file and not allow_folder else "folder",
            show_explorer_button=show_explorer_button,
            show_copy_button=show_copy_button,
            allow_layer=allow_layer,
            mode_type=mode_type,
            fixed_name=fixed_name,
            subfolder=subfolder,
            suffix=suffix,
            fixed_extension=fixed_extension,
            parent_selector=parent_selector,
            layer_filters=layer_filters,
            allow_lock_check=allow_lock_check,
            lock_check_default=lock_check_default,
            allow_features_check=allow_features_check,
            features_check_text=features_check_text,
            features_check_default=features_check_default,
            tool_key=self._tool_key or "GridComplexSelector",
            parent=self,
        )

        if parent_key:
            self._link_meta[label] = {
                "parent": parent_key,
                "suffix": suffix,
                "fixed_extension": fixed_extension,
                "subfolder": subfolder,
                "mode_type": mode_type,
                "fixed_name": fixed_name,
            }
            self._self_generated[label] = False

        if mode_type == "output" and parent_key and parent_selector:
            self._connect_output_listener(label, parent_selector)
            selector.set_origin_callback(
                partial(self._on_use_origin, label),
                tooltip="Usar mesmo diretório da origem",
            )

        return selector

    # ══════════════════════════════════════════════════════════════════
    # Listener Unificado
    # ══════════════════════════════════════════════════════════════════

    def _connect_output_listener(self, child_label: str, parent_selector: ComplexSelector):
        child_selector = self._selectors.get(child_label)
        if not child_selector:
            return

        original_cb = parent_selector.on_path_change

        def unified_handler(paths: list[str]):
            if original_cb:
                original_cb(paths)
            if child_label not in self._generating_output:
                should_generate = (
                    self._self_generated.get(child_label, False)
                    or not child_selector.get_paths()
                )
                if should_generate:
                    self._generate_output(child_label, paths)

        parent_selector.on_path_change = unified_handler

    # ══════════════════════════════════════════════════════════════════
    # Lógica de linking (USAR ORIGEM)
    # ══════════════════════════════════════════════════════════════════

    def _on_use_origin(self, label: str):
        meta = self._link_meta.get(label)
        if not meta:
            self._logger.warning(f"'{label}' não tem metadados de linking", code="GRID_NO_LINK_META")
            return

        parent_key = meta["parent"]
        parent_selector = self._resolve_parent_selector(parent_key)
        if not parent_selector:
            self._logger.warning(f"Parent '{parent_key}' não encontrado", code="GRID_PARENT_NOT_FOUND")
            return

        parent_paths = parent_selector.get_paths()
        if not parent_paths:
            self._logger.warning(f"Parent '{parent_key}' vazio", code="GRID_PARENT_EMPTY")
            return

        self._generate_output(label, parent_paths)
        self._self_generated[label] = True

    def set_output_extension(self, label: str, extension: str):
        """Atualiza a extensão fixa do output para um selector."""
        meta = self._link_meta.get(label)
        if meta:
            meta["fixed_extension"] = extension
            selector = self._selectors.get(label)
            if selector:
                selector.set_fixed_extension(extension)
                fixed_base = meta.get("fixed_name", "")
                if fixed_base and not fixed_base.endswith(f".{extension}"):
                    base_name = os.path.splitext(fixed_base)[0]
                    new_fixed_name = f"{base_name}.{extension}"
                    meta["fixed_name"] = new_fixed_name
                    selector.set_fixed_name(new_fixed_name)

    def set_output_suffix(self, label: str, suffix: str):
        meta = self._link_meta.get(label)
        if meta:
            meta["suffix"] = suffix
            selector = self._selectors.get(label)
            if selector:
                selector.set_origin_config(suffix=suffix)

    # ══════════════════════════════════════════════════════════════════
    # API Pública para manipular selectors
    # ══════════════════════════════════════════════════════════════════

    def set_input_placeholder(self, label: str, placeholder: str):
        selector = self._selectors.get(label)
        if selector:
            selector.edit.setPlaceholderText(placeholder)

    def set_input_file_filter(self, label: str, file_filter: str):
        selector = self._selectors.get(label)
        if selector:
            selector.file_filter = file_filter

    def suspend_callbacks(self) -> dict[str, Optional[Callable]]:
        snapshot: dict[str, Optional[Callable]] = {}
        for label in list(self._user_callbacks.keys()):
            snapshot[label] = self._user_callbacks.get(label)
        for label in list(self._user_callbacks.keys()):
            self.set_on_changed(label, None)
        return snapshot

    def resume_callbacks(self, snapshot: dict[str, Optional[Callable]]):
        for label, callback in snapshot.items():
            if callback is not None:
                self._user_callbacks[label] = callback
                selector = self._selectors.get(label)
                if selector and not getattr(selector, '_grid_wrapper_installed', False):
                    self._install_user_callback_wrapper(label, selector)

    def _generate_output(self, label: str, parent_paths: list[str]):
        if label in self._generating_output:
            return
        self._generating_output.add(label)

        try:
            meta = self._link_meta.get(label)
            if not meta:
                return

            parent_key = meta["parent"]
            parent_selector = self._resolve_parent_selector(parent_key)
            if not parent_selector:
                return

            selector = self._selectors[label]
            parent_path = parent_paths[0] if parent_paths else ""

            if not parent_path:
                return

            parent_dir = os.path.dirname(parent_path) if os.path.isfile(parent_path) else parent_path
            parent_stem = os.path.splitext(os.path.basename(parent_path))[0]
            suffix = meta.get("suffix", "")
            fixed_extension = meta.get("fixed_extension", "")
            fixed_name = meta.get("fixed_name", "")

            # Usa fixed_extension se definida, senão usa extensão do parent
            ext = fixed_extension if fixed_extension else os.path.splitext(parent_path)[1]
            if not ext.startswith("."):
                ext = f".{ext}"

            if suffix:
                output_name = f"{parent_stem}{suffix}{ext}"
            elif fixed_name:
                output_name = fixed_name
                if fixed_extension and not os.path.splitext(fixed_name)[1]:
                    output_name = f"{fixed_name}.{fixed_extension}"
            else:
                output_name = f"{parent_stem}{ext}"

            output_path = os.path.join(parent_dir, output_name)
            selector.set_path(output_path)
            self._self_generated[label] = True

            self._logger.info(
                f"Output gerado '{label}': {selector.path()}",
                code="GRID_OUTPUT_GENERATED",
            )
        finally:
            self._generating_output.discard(label)

    # ══════════════════════════════════════════════════════════════════
    # Erro visual
    # ══════════════════════════════════════════════════════════════════

    def show_error(self, label: str, message: str, duration_ms: int = 3000):
        selector = self._selectors.get(label)
        if not selector:
            return

        edit = selector.edit
        if not edit:
            return

        if not hasattr(edit, '_saved_stylesheet'):
            edit._saved_stylesheet = edit.styleSheet()

        error_color = "#FF4444"
        radius = 4
        surface_2 = "#2D2D2D"
        text_medium = "#CCCCCC"

        edit.setStyleSheet(
            f"QLineEdit {{ border: 2px solid {error_color}; "
            f"border-radius: {radius}px; "
            f"background-color: {surface_2}; "
            f"color: {text_medium}; "
            f"padding: 2px 6px; }}"
        )
        edit.setToolTip(f"⚠ {message}")

        if duration_ms > 0:
            QTimer.singleShot(duration_ms, lambda: self._clear_error(edit))

    def _clear_error(self, edit: QLineEdit):
        if hasattr(edit, '_saved_stylesheet'):
            edit.setStyleSheet(edit._saved_stylesheet)
        else:
            edit.setStyleSheet("")

    # ══════════════════════════════════════════════════════════════════
    # API Pública — Lock Checkbox
    # ══════════════════════════════════════════════════════════════════

    def get_lock_state(self, label: str) -> bool:
        """
        Retorna estado do lock checkbox para um selector.
        Se o selector não tem allow_lock_check, retorna lock_check_default.
        """
        sel = self._selectors.get(label)
        return sel.get_lock_state() if sel else True

    def set_lock_state(self, label: str, checked: bool):
        """Define estado do lock checkbox programaticamente."""
        sel = self._selectors.get(label)
        if sel:
            sel.set_lock_state(checked)

    # ══════════════════════════════════════════════════════════════════
    # API Pública — Features Checkbox
    # ══════════════════════════════════════════════════════════════════

    def get_checked_state(self, label: str) -> bool:
        """
        Retorna estado do features checkbox para um selector.
        Se o selector não tem allow_features_check, retorna features_check_default.
        """
        sel = self._selectors.get(label)
        return sel.get_checked_state() if sel else False

    def set_checked_state(self, label: str, checked: bool):
        """Define estado do features checkbox programaticamente."""
        sel = self._selectors.get(label)
        if sel:
            sel.set_checked_state(checked)

    # ══════════════════════════════════════════════════════════════════
    # API Pública
    # ══════════════════════════════════════════════════════════════════

    def get(self, label: str) -> Optional[ComplexSelector]:
        return self._selectors.get(label)

    def __getitem__(self, label: str) -> ComplexSelector:
        return self._selectors[label]

    def __contains__(self, label: str) -> bool:
        return label in self._selectors

    def items(self):
        return self._selectors.items()

    def selectors(self) -> dict[str, ComplexSelector]:
        return self._selectors.copy()

    def paths(self) -> dict[str, str]:
        return {label: sel.path() for label, sel in self._selectors.items()}

    def all_paths(self) -> list[str]:
        return [sel.path() for sel in self._selectors.values() if sel.path()]

    def get_paths(self) -> list[str]:
        return self.all_paths()

    def get_path(self, key: str) -> str:
        sel = self._selectors.get(key)
        return sel.path() if sel else ""

    def set_paths(self, paths: list[str]):
        if not paths:
            return
        for i, key in enumerate(self._selectors):
            if i < len(paths):
                self._selectors[key].set_path(paths[i])
            else:
                break

    def set_path(self, key: str, path: str):
        sel = self._selectors.get(key)
        if sel:
            sel.set_path(path)

    def get_selector(self, key: str) -> Optional[ComplexSelector]:
        return self._selectors.get(key)

    def get_input(self) -> dict[str, ComplexSelector]:
        inputs = {}
        for label, sel in self._selectors.items():
            meta = self._link_meta.get(label, {})
            if meta.get("mode_type") != "output":
                inputs[label] = sel
        return inputs

    def get_output(self) -> dict[str, ComplexSelector]:
        outputs = {}
        for label, sel in self._selectors.items():
            meta = self._link_meta.get(label, {})
            if meta.get("mode_type") == "output":
                outputs[label] = sel
        return outputs

    def use_origin(self, label: str):
        selector = self._selectors.get(label)
        if selector and hasattr(selector, 'on_origin_click') and selector.on_origin_click:
            selector.on_origin_click()

    def use_origin_all(self):
        for label in self._link_meta:
            self.use_origin(label)

    def refresh_links(self):
        for label, meta in self._link_meta.items():
            parent_key = meta["parent"]
            parent_selector = self._resolve_parent_selector(parent_key)
            if parent_selector and parent_selector.get_paths():
                self._generate_output(label, parent_selector.get_paths())

    def has_linked(self, label: str) -> bool:
        return label in self._link_meta

    def get_parent_of(self, label: str) -> Optional[str]:
        meta = self._link_meta.get(label)
        return meta.get("parent") if meta else None