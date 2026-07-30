# -*- coding: utf-8 -*-
"""
ComplexSelector — Seletor avançado com suporte a QgsMapLayerComboBox e file/folder.
============================================================================
USO INTERNO apenas (para compor Grid widgets). NUNCA importado por plugins.

Widget autoconfigurável que segue o novo sistema:
- SimpleModernButton para botões com glow
- AppStyles para estilos

Comportamento:
  - label + QStackedWidget (QLineEdit | QgsMapLayerComboBox) + botões
  - 📄 (project): alterna entre QLineEdit e QgsMapLayerComboBox (só input)
  - 🔍 (file): busca arquivo(s) por extensão, força line edit
  - 📁 (folder): busca pasta(s), força line edit
  - 📥 (origin): gera path via parent + suffix + fixed_extension (só output)
  - 🛠️ (suggest): gera path via ProjectUtils + subfolder + fixed_name (só output)
  - ➡️ (explorer): abre Windows Explorer no diretório do path/layer

Lock Button:
  - allow_lock_check: botão LOCK/UNLOCK (ícone `layer.ico` / `raster.ico`) na mesma
    linha dos botões, estilo SquareIconButton.
    locked (marcado) = desbloqueado; unlocked (desmarcado) = bloqueia widget.
    Default: True (locked = desbloqueado).
  - allow_features_check: checkbox ABAIXO da linha principal, com texto.
    Default: False (desmarcado).
    Texto padrão: STR.ONLY_SELECTED_FEATURES
"""

from __future__ import annotations

import os
from typing import Callable, Optional

from qgis.PyQt.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QStackedWidget, QSizePolicy, QCheckBox,
)
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsMapLayerProxyModel, QgsProject

from ....core.config.LogUtils import LogUtils
from ...styles.AppStyles import AppStyles
from ....utils.ExplorerUtils import ExplorerUtils
from ....utils.ProjectUtils import ProjectUtils
from ....utils.QgisMessageUtil import QgisMessageUtil
from ...IconManager import IconManager
from .SquareIconButton import SquareIconButton


class ComplexSelector(QWidget):
    """
    Seletor avançado com suporte a file/folder e QgsMapLayerComboBox.

    label + QStackedWidget (QLineEdit | QgsMapLayerComboBox) + botões.

    Botões:
      - 📄 (project): alterna line edit <-> combo (só input, se layer_filters != All)
      - 🔍 (file): busca arquivo(s) por extensão (se allow_file)
      - 📁 (folder): busca pasta(s) (se allow_folder)
      - 📥 (origin): gera path via parent + suffix + fixed_extension (só output)
      - 🛠️ (suggest): gera path via ProjectUtils (só output)
      - ➡️ (explorer): abre Explorer no diretório

    Lock Button:
      - Lock button: na mesma linha dos botões, estilo SquareIconButton (🔒/🔓)
      - Features check: abaixo da linha principal, com texto
    """

    pathChanged = pyqtSignal(list)

    def __init__(
        self,
        label_text: str = "",
        default_path: str = "",
        placeholder: str = "Caminho...",
        tooltip: str = "",
        file_filter: str = "Todos (*.*)",
        label_width: int = 130,
        # ── Controle de modo ──
        allow_file: bool = True,
        allow_folder: bool = False,
        multiple: bool = False,
        selection_mode: str = "file",
        # ── Botões ──
        show_explorer_button: bool = True,
        allow_layer: bool = False,
        # ── Output config ──
        mode_type: str = "input",
        fixed_name: str = "",
        subfolder: str = "",
        # ── Origin config (📥) ──
        suffix: str = "",
        fixed_extension: str = "",
        parent_selector=None,
        # ── Filtro de camada (📄) ──
        layer_filters=None,
        # ── Botão copiar ──
        show_copy_button: bool = True,
        # ── Lock checkbox (mesma linha, SEM texto, bloqueia widget) ──
        allow_lock_check: bool = False,
        lock_check_default: bool = True,
        # ── Features checkbox (abaixo da linha, com texto) ──
        allow_features_check: bool = False,
        features_check_text: str = "",
        features_check_default: bool = False,
        # ── Tool key para logger ──
        tool_key=None,
        parent=None,
    ):
        super().__init__(parent)

        # Validação
        if not allow_file and not allow_folder:
            allow_file = True
        if selection_mode not in ("file", "folder"):
            selection_mode = "file"
        if selection_mode == "folder" and not allow_folder:
            selection_mode = "file"
        if selection_mode == "file" and not allow_file:
            selection_mode = "folder"

        self._file_filter = file_filter
        self._allow_file = allow_file
        self._allow_folder = allow_folder
        self._multiple = multiple
        self._selection_mode = selection_mode
        self._show_explorer_button = show_explorer_button
        self._show_copy_button = show_copy_button
        self._allow_layer = allow_layer
        self._mode_type = mode_type
        self._fixed_name = fixed_name
        self._subfolder = subfolder
        self._suffix = suffix
        self._fixed_extension = fixed_extension
        self._parent_selector = parent_selector
        self._layer_filters = layer_filters or QgsMapLayerProxyModel.All
        self._tool_key = tool_key

        # ── Checkbox params ──
        self._allow_lock_check = allow_lock_check
        self._lock_check_default = lock_check_default
        self._allow_features_check = allow_features_check
        self._features_check_text = features_check_text or ""
        self._features_check_default = features_check_default

        # Estado interno
        self._root_path: str = ""
        self._selected_list: list[str] = []
        self._updating_display: bool = False
        self._using_layer_combo: bool = False

        # Logger
        tool_name = tool_key or "ComplexSelector"
        self.logger = LogUtils(tool=tool_name, class_name="ComplexSelector")

        # Callbacks públicos
        self.on_path_change = None
        self.on_browse_click = None
        self.on_suggest_click = None
        self.on_origin_click = None

        # Constrói UI
        self._build_ui(label_text, placeholder, tooltip, label_width)

        if default_path:
            self.set_path(default_path)

    # ══════════════════════════════════════════════════════════════════
    # UI
    # ══════════════════════════════════════════════════════════════════

    def _build_ui(self, label_text, placeholder, tooltip, label_width):
        # Layout vertical: linha principal + sub-layout para features check
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # Linha principal horizontal
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Label — tamanho automático conforme texto
        self._label = QLabel(label_text)
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if tooltip:
            self._label.setToolTip(tooltip)
        layout.addWidget(self._label, 0, Qt.AlignmentFlag.AlignVCenter)

        # QStackedWidget — expande para preencher espaço entre label e botões
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1, Qt.AlignmentFlag.AlignVCenter)

        # Página 0: QLineEdit com altura fixa do tema
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        self._edit.setStyleSheet(AppStyles.modern_input_primary())
        input_h = int(AppStyles._get_theme().INPUT_FIELD_MIN_HEIGHT.replace("px", ""))
        self._edit.setFixedHeight(input_h)
        if tooltip:
            self._edit.setToolTip(tooltip)
        self._edit.textChanged.connect(self._on_edit_text_changed)
        self._stack.addWidget(self._edit)

        # Página 1: QgsMapLayerComboBox (apenas input)
        self._combo = QgsMapLayerComboBox()
        self._combo.setAllowEmptyLayer(True)
        self._combo.setFilters(self._layer_filters)
        self._combo.setVisible(False)
        self._combo.currentIndexChanged.connect(self._on_combo_layer_changed)
        self._stack.addWidget(self._combo)

        # Botões (incluindo lock button, todos agrupados à direita)
        self._add_buttons(layout)

        # Decide estado inicial: se tem layer_filters específico, começa com combo
        has_layer_filter = self._layer_filters != QgsMapLayerProxyModel.All
        if self._mode_type == "input" and has_layer_filter:
            self._using_layer_combo = True
            self._combo.setVisible(True)

        # Adiciona linha principal ao layout vertical
        main_layout.addLayout(layout)

        # ── Features checkbox (abaixo da linha principal, com texto) ──
        # Só aparece quando allow_features_check=True E está em modo layer combo
        self._features_checkbox = None
        self._features_layout = None
        if self._allow_features_check:
            self._features_layout = QHBoxLayout()
            self._features_layout.setContentsMargins(0, 0, 0, 0)
            self._features_layout.setSpacing(2)

            self._features_checkbox = QCheckBox()
            check_text = self._features_check_text or ""
            self._features_checkbox.setText(check_text)
            self._features_checkbox.setChecked(self._features_check_default)
            self._features_checkbox.toggled.connect(self._on_features_checkbox_toggled)
            self._features_layout.addWidget(self._features_checkbox, 0, Qt.AlignmentFlag.AlignVCenter)

            self._features_layout.addStretch(1)
            main_layout.addLayout(self._features_layout)

        self._update_display()
        self._update_blocked_state()

    def _add_buttons(self, layout):
        """Adiciona botões conforme configuração. Todos com mesmo tamanho do input."""
        # ── Lock button (SquareIconButton, primeiro da direita) ──
        self._lock_button = None
        if self._allow_lock_check:
            self._lock_button = SquareIconButton(
                icon=IconManager.icon(IconManager.LOCK),
                tooltip="🔒 Desbloqueado — clique para bloquear" if self._lock_check_default else "🔓 Bloqueado — clique para desbloquear",
                parent=self,
            )
            self._lock_button.setCheckable(True)
            self._lock_button.setChecked(self._lock_check_default)
            self._lock_button.toggled.connect(self._on_lock_toggled)
            self._update_lock_button_icon()
            layout.addWidget(self._lock_button, 0, Qt.AlignmentFlag.AlignVCenter)

        # 🔍 (file)
        if self._allow_file:
            self._btn_file = SquareIconButton(
                icon=IconManager.icon(IconManager.FILE2),
                tooltip="Selecionar arquivos" if self._multiple else "Selecionar arquivo",
                parent=self,
            )
            self._btn_file.clicked.connect(self._browse_file)
            layout.addWidget(self._btn_file, 0, Qt.AlignmentFlag.AlignVCenter)

        # 📁 (folder)
        if self._allow_folder:
            self._btn_folder = SquareIconButton(
                icon=IconManager.icon(IconManager.FOLDER),
                tooltip="Selecionar pastas" if self._multiple else "Selecionar pasta",
                parent=self,
            )
            self._btn_folder.clicked.connect(self._browse_folder)
            layout.addWidget(self._btn_folder, 0, Qt.AlignmentFlag.AlignVCenter)

        # 📄 (project — só input, alterna line edit <-> combo)
        if self._mode_type == "input" and self._allow_layer:
            self._btn_project = SquareIconButton(
                icon=IconManager.icon(IconManager.LAYER2),
                tooltip="Alternar para seleção de camada",
                parent=self,
            )
            self._btn_project.clicked.connect(self._on_project_clicked)
            layout.addWidget(self._btn_project, 0, Qt.AlignmentFlag.AlignVCenter)

        # 📥 (origin — só output)
        if self._mode_type == "output" and self._parent_selector is not None:
            self._btn_origin = SquareIconButton(
                icon=IconManager.icon(IconManager.ORIGIN),
                tooltip="Usar mesmo diretório da origem",
                parent=self,
            )
            self._btn_origin.clicked.connect(self._on_origin_clicked)
            layout.addWidget(self._btn_origin, 0, Qt.AlignmentFlag.AlignVCenter)

        # 🛠️ (suggest — só output)
        if self._mode_type == "output":
            self._btn_suggest = SquareIconButton(
                icon=IconManager.icon(IconManager.PROJECT_FOLDER1),
                tooltip="Usar pasta do projeto",
                parent=self,
            )
            self._btn_suggest.clicked.connect(self._on_suggest_clicked)
            layout.addWidget(self._btn_suggest, 0, Qt.AlignmentFlag.AlignVCenter)

        # ➡️ (explorer)
        if self._show_explorer_button:
            self._btn_explorer = SquareIconButton(
                icon=IconManager.icon(IconManager.EXPLORER),
                tooltip="Abrir localização no Explorer",
                parent=self,
            )
            self._btn_explorer.clicked.connect(self._open_explorer)
            layout.addWidget(self._btn_explorer, 0, Qt.AlignmentFlag.AlignVCenter)

        # 📋 (copiar)
        if self._show_copy_button:
            self._btn_copy = SquareIconButton(
                icon=IconManager.icon(IconManager.COPY2),
                tooltip="Copiar caminho",
                parent=self,
            )
            self._btn_copy.clicked.connect(self._copy_to_clipboard)
            layout.addWidget(self._btn_copy, 0, Qt.AlignmentFlag.AlignVCenter)

    # ══════════════════════════════════════════════════════════════════
    # Display
    # ══════════════════════════════════════════════════════════════════

    def _update_display(self):
        self._updating_display = True
        try:
            if self._using_layer_combo:
                layer = self._combo.currentLayer()
                if layer:
                    src = layer.source()
                    if src:
                        layer_path = src.split("|")[0] if "|" in src else src
                        self._edit.setText(layer_path)
                    else:
                        self._edit.setText("")
                else:
                    self._edit.setText("")
                self._stack.setCurrentIndex(1)
            else:
                if not self._selected_list:
                    self._edit.setText("")
                elif not self._multiple:
                    self._edit.setText(self._selected_list[0])
                else:
                    self._edit.setText("; ".join(self._selected_list))
                self._stack.setCurrentIndex(0)
        finally:
            self._updating_display = False

        # Features checkbox só aparece quando em modo layer combo
        self._update_features_visibility()

    # ══════════════════════════════════════════════════════════════════
    # Handlers
    # ══════════════════════════════════════════════════════════════════

    def _on_edit_text_changed(self, text: str):
        if self._updating_display:
            return
        if not text:
            self._root_path = ""
            self._selected_list = []
            self._emit_path_change()
            return
        if not self._multiple:
            self._root_path = os.path.dirname(text) if os.path.isfile(text) else text
            self._selected_list = [text]
            self._emit_path_change()
        else:
            parts = [p.strip() for p in text.replace("; ", ";").split(";")]
            parts = [p for p in parts if p]
            if parts:
                first = parts[0]
                self._root_path = os.path.dirname(first) if os.path.isfile(first) else first
                self._selected_list = parts
            else:
                self._root_path = ""
                self._selected_list = []
            self._emit_path_change()

    def _on_combo_layer_changed(self, index: int):
        if self._updating_display:
            return
        layer = self._combo.currentLayer()
        if layer:
            src = layer.source()
            if src:
                layer_path = src.split("|")[0] if "|" in src else src
                self._root_path = os.path.dirname(layer_path) if os.path.isfile(layer_path) else layer_path
                self._selected_list = [layer_path]
                self._emit_path_change()

    def _ensure_line_edit_mode(self):
        self._using_layer_combo = False
        self._update_display()

    # ══════════════════════════════════════════════════════════════════
    # 🔍 (file)
    # ══════════════════════════════════════════════════════════════════

    def _browse_file(self):
        self.logger.info("🔍 clicado", code="COMPLEX_FILE_CLICKED")
        self._ensure_line_edit_mode()

        if self.on_browse_click:
            self.on_browse_click()

        initial_dir = ExplorerUtils.resolve_initial_dir(
            self._root_path or (self._selected_list[0] if self._selected_list else "")
        )

        if self._mode_type == "output":
            path = ExplorerUtils.save_file_dialog(
                "Salvar arquivo", initial_dir, self._file_filter, self,
            )
            if path:
                self._root_path = os.path.dirname(path)
                self._selected_list = [path]
                self._update_display()
                self._emit_path_change()
        elif self._multiple:
            paths = ExplorerUtils.open_files_dialog(
                "Selecionar arquivos", initial_dir, self._file_filter, self,
            )
            if paths:
                self._root_path = os.path.dirname(paths[0]) if paths else ""
                self._selected_list = list(paths)
                self._update_display()
                self._emit_path_change()
        else:
            path = ExplorerUtils.open_file_dialog(
                "Selecionar arquivo", initial_dir, self._file_filter, self,
            )
            if path:
                self._root_path = os.path.dirname(path)
                self._selected_list = [path]
                self._update_display()
                self._emit_path_change()

    # ══════════════════════════════════════════════════════════════════
    # 📁 (folder)
    # ══════════════════════════════════════════════════════════════════

    def _browse_folder(self):
        self.logger.info("📁 clicado", code="COMPLEX_FOLDER_CLICKED")
        self._ensure_line_edit_mode()

        if self.on_browse_click:
            self.on_browse_click()

        initial_dir = ExplorerUtils.resolve_initial_dir(
            self._root_path or (self._selected_list[0] if self._selected_list else "")
        )

        path = ExplorerUtils.select_directory_dialog(
            "Selecionar pasta", initial_dir, self,
        )
        if path:
            self._root_path = path
            self._selected_list = [path]
            self._update_display()
            self._emit_path_change()

    # ══════════════════════════════════════════════════════════════════
    # ➡️ (explorer)
    # ══════════════════════════════════════════════════════════════════

    def _open_explorer(self):
        target = None

        if self._using_layer_combo:
            layer = self._combo.currentLayer()
            if layer:
                src = layer.source()
                if src:
                    layer_path = src.split("|")[0] if "|" in src else src
                    if os.path.isdir(layer_path):
                        target = layer_path
                    else:
                        target = os.path.dirname(layer_path)
        elif self._selected_list:
            first = self._selected_list[0]
            if os.path.isdir(first):
                target = first
            else:
                target = os.path.dirname(first)

        if not target or not os.path.isdir(target):
            QgisMessageUtil.bar_info(
                None,
                "Nenhum caminho válido para abrir no Explorer. Selecione um arquivo, pasta ou camada primeiro.",
                title="Explorer",
            )
            return

        self.logger.info(f"Abrindo Explorer em: {target}", code="COMPLEX_EXPLORER_OPEN")
        try:
            if os.name == "nt":
                os.startfile(target)
        except Exception as e:
            self.logger.error("Erro ao abrir Explorer", code="COMPLEX_EXPLORER_ERROR", error=str(e))

    # ══════════════════════════════════════════════════════════════════
    # 📄 (project — alterna line edit <-> combo)
    # ══════════════════════════════════════════════════════════════════

    def _on_project_clicked(self):
        self.logger.info("📄 clicado", code="COMPLEX_PROJECT_CLICKED")
        if self._mode_type == "output":
            return

        self._using_layer_combo = not self._using_layer_combo

        if self._using_layer_combo:
            self._combo.setVisible(True)
            current_path = self.path()
            if current_path:
                for layer in QgsProject.instance().mapLayers().values():
                    src = layer.source()
                    if src and current_path in src:
                        self._combo.setLayer(layer)
                        break
            self._combo.setFocus()
        else:
            self._combo.setVisible(False)
            layer = self._combo.currentLayer()
            if layer:
                src = layer.source()
                if src:
                    layer_path = src.split("|")[0] if "|" in src else src
                    self._root_path = os.path.dirname(layer_path) if os.path.isfile(layer_path) else layer_path
                    self._selected_list = [layer_path]
                    self._emit_path_change()

        self._update_display()

    # ══════════════════════════════════════════════════════════════════
    # 📥 (origin — só output)
    # ══════════════════════════════════════════════════════════════════

    def _on_origin_clicked(self):
        self.logger.info("📥 clicado (origin)", code="COMPLEX_ORIGIN_CLICKED")
        self._ensure_line_edit_mode()

        if self.on_origin_click:
            self.on_origin_click()
            return

        if self._parent_selector:
            parent_paths = self._parent_selector.get_paths()
            if parent_paths:
                self._generate_from_parent(parent_paths)

    def _generate_from_parent(self, parent_paths: list[str]):
        if not parent_paths:
            return

        parent_path = parent_paths[0]
        parent_dir = os.path.dirname(parent_path) if os.path.isfile(parent_path) else parent_path
        parent_stem = os.path.splitext(os.path.basename(parent_path))[0]

        suffix = self._suffix or ""
        ext = self._fixed_extension or os.path.splitext(parent_path)[1]

        if not ext.startswith("."):
            ext = f".{ext}"

        if suffix:
            output_name = f"{parent_stem}{suffix}{ext}"
        else:
            output_name = f"{parent_stem}{ext}"

        output_path = os.path.join(parent_dir, output_name)

        self._root_path = os.path.dirname(output_path) if os.path.isfile(output_path) else output_path
        self._selected_list = [output_path]
        self._update_display()
        self._emit_path_change()

        self.logger.info(
            f"Output gerado de parent: {output_path}",
            code="COMPLEX_ORIGIN_PATH",
            parent=parent_path,
            suffix=suffix,
            extension=ext,
        )

    def set_origin_callback(self, callback: Callable[[], None], tooltip: str = ""):
        if hasattr(self, '_btn_origin'):
            try:
                self._btn_origin.clicked.disconnect()
            except TypeError:
                pass
            self._btn_origin.clicked.connect(callback)
            if tooltip:
                self._btn_origin.setToolTip(tooltip)

    # ══════════════════════════════════════════════════════════════════
    # 🛠️ (suggest — só output)
    # ══════════════════════════════════════════════════════════════════

    def _on_suggest_clicked(self):
        self.logger.info("🛠️ clicado (output)", code="COMPLEX_SUGGEST_CLICKED")
        self._ensure_line_edit_mode()

        if self.on_suggest_click:
            self.on_suggest_click()

        project = QgsProject.instance()
        root_folder = ProjectUtils.get_project_dir(project) if project else ""

        if not root_folder:
            self.logger.warning("Nenhum projeto ativo", code="COMPLEX_NO_PROJECT")
            return

        if self._subfolder:
            output_dir = os.path.join(root_folder, self._subfolder)
        else:
            output_dir = root_folder

        if self._fixed_name:
            output_name = self._fixed_name
            if self._fixed_extension and not os.path.splitext(output_name)[1]:
                ext = self._fixed_extension if self._fixed_extension.startswith(".") else f".{self._fixed_extension}"
                output_name = f"{output_name}{ext}"
            output_path = os.path.join(output_dir, output_name)
        else:
            output_path = output_dir

        self._root_path = output_dir
        self._selected_list = [output_path]
        self._update_display()
        self._emit_path_change()

        self.logger.info(
            f"Output: {output_path}",
            code="COMPLEX_SUGGEST_PATH",
            root=root_folder,
            subfolder=self._subfolder,
            fixed_name=self._fixed_name,
        )

    # ══════════════════════════════════════════════════════════════════
    # Features checkbox (conectado ao QgsMapLayerComboBox)
    # ══════════════════════════════════════════════════════════════════

    def _on_features_checkbox_toggled(self, checked: bool):
        """
        Quando o features checkbox é alternado, também atualiza o filtro
        do QgsMapLayerComboBox para mostrar apenas layers com feições selecionadas.
        """
        try:
            if self._combo:
                self._combo.setShowOnlySelectedFeatures(checked)
        except AttributeError:
            # Método não disponível nesta versão do QGIS
            pass

    # ══════════════════════════════════════════════════════════════════
    # Lock checkbox (bloqueia widget quando desmarcado)
    # ══════════════════════════════════════════════════════════════════

    def _on_lock_toggled(self, checked: bool):
        """Quando lock button muda, atualiza bloqueio do selector e ícone."""
        self._update_lock_button_icon()
        self._update_blocked_state()

    def _update_lock_button_icon(self):
        """Atualiza ícone e tooltip do lock button conforme estado checked."""
        if self._lock_button is not None:
            locked = self._lock_button.isChecked()
            self._lock_button.setIcon(
                IconManager.icon(IconManager.LOCK if locked else IconManager.UNLOCK)
            )
            self._lock_button.setToolTip(
                "🔒 Desbloqueado — clique para bloquear" if locked
                else "🔓 Bloqueado — clique para desbloquear"
            )

    def _update_blocked_state(self):
        """Gerencia bloqueio do widget baseado no estado do lock button."""
        if not self._allow_lock_check or self._lock_button is None:
            return

        blocked = not self._lock_button.isChecked()

        # Bloqueia/desbloqueia widgets internos (exceto a própria checkbox)
        self._stack.setEnabled(not blocked)
        self._edit.setEnabled(not blocked)
        self._combo.setEnabled(not blocked)

        # Botões
        for btn_name in [
            '_btn_file', '_btn_folder', '_btn_project',
            '_btn_origin', '_btn_suggest', '_btn_explorer', '_btn_copy'
        ]:
            btn = getattr(self, btn_name, None)
            if btn:
                btn.setEnabled(not blocked)

    def _update_features_visibility(self):
        """
        Mostra/esconde o features checkbox conforme o modo atual.
        Só aparece quando usando QgsMapLayerComboBox (layer combo).
        Quando em modo line edit, o checkbox fica oculto.
        """
        if self._features_checkbox is not None:
            is_visible = self._using_layer_combo
            self._features_checkbox.setVisible(is_visible)

    # ══════════════════════════════════════════════════════════════════
    # 📋 (copiar)
    # ══════════════════════════════════════════════════════════════════

    def _copy_to_clipboard(self):
        """Copia o texto atual do campo para a área de transferência."""
        text = self._edit.text()
        if text:
            ProjectUtils.set_clipboard_text(text)
            self.logger.info("Caminho copiado para área de transferência", code="COMPLEX_COPY_CLIPBOARD")

    # ══════════════════════════════════════════════════════════════════
    # Callback
    # ══════════════════════════════════════════════════════════════════

    def _emit_path_change(self):
        if self.on_path_change:
            self.on_path_change(self._selected_list)
        self.pathChanged.emit(self._selected_list)

    # ══════════════════════════════════════════════════════════════════
    # API Pública — Lock Checkbox
    # ══════════════════════════════════════════════════════════════════

    def get_lock_state(self) -> bool:
        """
        Retorna estado atual do lock button.
        Se allow_lock_check=False, retorna lock_check_default.
        """
        if not self._allow_lock_check:
            return self._lock_check_default
        return self._lock_button.isChecked()

    def set_lock_state(self, checked: bool):
        """Define estado do lock button programaticamente."""
        if self._lock_button is not None:
            self._lock_button.setChecked(checked)
            self._update_lock_button_icon()

    # ══════════════════════════════════════════════════════════════════
    # API Pública — Features Checkbox
    # ══════════════════════════════════════════════════════════════════

    def get_checked_state(self) -> bool:
        """
        Retorna estado atual do features checkbox.
        Se allow_features_check=False, retorna features_check_default.
        """
        if not self._allow_features_check:
            return self._features_check_default
        return self._features_checkbox.isChecked()

    def set_checked_state(self, checked: bool):
        """Define estado do features checkbox programaticamente."""
        if self._features_checkbox is not None:
            self._features_checkbox.setChecked(checked)

    # ══════════════════════════════════════════════════════════════════
    # API Pública — Paths
    # ══════════════════════════════════════════════════════════════════

    def get_root_path(self) -> str:
        return self._root_path

    def get_selected_list(self) -> list[str]:
        return self._selected_list.copy()

    def get_paths(self) -> list[str]:
        return self.get_selected_list()

    def get_path(self, index: int = 0) -> str:
        if 0 <= index < len(self._selected_list):
            return self._selected_list[index]
        return ""

    def path(self) -> str:
        return self.get_path(0)

    def paths(self) -> list[str]:
        return self.get_paths()

    def path_type(self) -> str:
        if self._multiple:
            return f"{self._selection_mode}s"
        return self._selection_mode

    def path_count(self) -> int:
        return len(self._selected_list)

    def is_multi(self) -> bool:
        return self._multiple

    def is_single(self) -> bool:
        return not self._multiple

    def is_folder_mode(self) -> bool:
        return self._selection_mode == "folder"

    def is_file_mode(self) -> bool:
        return self._selection_mode == "file"

    def set_path(self, path: str):
        self._using_layer_combo = False
        if path:
            self._root_path = os.path.dirname(path) if os.path.isfile(path) else path
            self._selected_list = [path]
        else:
            self._root_path = ""
            self._selected_list = []
        self._update_display()
        self._emit_path_change()

    def set_paths(self, paths: list[str]):
        self._using_layer_combo = False
        if paths:
            first = paths[0]
            self._root_path = os.path.dirname(first) if os.path.isfile(first) else first
            self._selected_list = list(paths)
        else:
            self._root_path = ""
            self._selected_list = []
        self._update_display()
        self._emit_path_change()

    def set_mode_state(self, using_layer_combo: bool, path: str = ""):
        """
        Restaura modo (layer combo ou line edit) e path.
        Usado internamente para carregar preferências.
        Não emite pathChanged para evitar chamadas de callback durante restauração.
        """
        if using_layer_combo and self._mode_type == "input" and self._allow_layer:
            # Modo layer combo: tenta encontrar layer pelo path
            self._using_layer_combo = True
            if path:
                for layer in QgsProject.instance().mapLayers().values():
                    src = layer.source()
                    if src and path in src:
                        self._combo.setLayer(layer)
                        break
            self._combo.setVisible(True)
            self._stack.setCurrentIndex(1)
            self._update_features_visibility()
            # Atualiza estado interno sem emitir sinal
            self._updating_display = True
            try:
                layer = self._combo.currentLayer()
                if layer:
                    src = layer.source()
                    if src:
                        layer_path = src.split("|")[0] if "|" in src else src
                        self._root_path = os.path.dirname(layer_path) if os.path.isfile(layer_path) else layer_path
                        self._selected_list = [layer_path]
                if not self._selected_list and path:
                    self._root_path = os.path.dirname(path) if os.path.isfile(path) else path
                    self._selected_list = [path]
            finally:
                self._updating_display = False
        else:
            # Modo line edit
            self._using_layer_combo = False
            if path:
                self._root_path = os.path.dirname(path) if os.path.isfile(path) else path
                self._selected_list = [path]
            else:
                self._root_path = ""
                self._selected_list = []
            self._update_display()

    def clear(self):
        self._using_layer_combo = False
        self._root_path = ""
        self._selected_list = []
        self._update_display()
        self._emit_path_change()

    def exists(self) -> bool:
        p = self.path()
        return bool(p) and os.path.exists(p)

    def is_file(self) -> bool:
        p = self.path()
        return bool(p) and os.path.isfile(p)

    def is_dir(self) -> bool:
        p = self.path()
        return bool(p) and os.path.isdir(p)

    def basename(self) -> str:
        return os.path.basename(self.path())

    def dirname(self) -> str:
        return os.path.dirname(self.path())

    def extension(self) -> str:
        return os.path.splitext(self.path())[1].lower()

    def has_extension(self, *exts: str) -> bool:
        if not self._selected_list:
            return False
        ext = self.extension()
        return any(ext == e.lower() for e in exts)

    # ── Configuração ────────────────────────────────────────────────

    def set_fixed_name(self, fixed_name: str):
        self._fixed_name = fixed_name
        self.logger.info(f"fixed_name: '{fixed_name}'", code="COMPLEX_FIXED_NAME_CHANGED")

    def set_fixed_extension(self, extension: str):
        """Define/atualiza a extensão fixa usada pelo 📥 e 🛠️."""
        self._fixed_extension = extension
        self.logger.info(f"fixed_extension: '{extension}'", code="COMPLEX_FIXED_EXTENSION_CHANGED")

    def set_suggested_callback(self, callback: Callable[[], None], tooltip: str = ""):
        if hasattr(self, '_btn_suggest'):
            try:
                self._btn_suggest.clicked.disconnect()
            except TypeError:
                pass
            self._btn_suggest.clicked.connect(callback)
            if tooltip:
                self._btn_suggest.setToolTip(tooltip)

    def set_origin_config(self, *, suffix: str = "", fixed_extension: str = ""):
        """Atualiza configuração do botão 📥."""
        if suffix:
            self._suffix = suffix
        if fixed_extension:
            self._fixed_extension = fixed_extension

    @property
    def file_filter(self) -> str:
        return self._file_filter

    @file_filter.setter
    def file_filter(self, value: str) -> None:
        self._file_filter = value
        self.logger.info(f"file_filter: '{value}'", code="COMPLEX_FILE_FILTER_CHANGED")

    @property
    def edit(self) -> QLineEdit:
        return self._edit

    @property
    def combo(self) -> QgsMapLayerComboBox:
        return self._combo

    @property
    def mode_type(self) -> str:
        return self._mode_type

    @property
    def selection_mode(self) -> str:
        return self._selection_mode

    @selection_mode.setter
    def selection_mode(self, value: str) -> None:
        if value in ("file", "folder"):
            self._selection_mode = value

    @property
    def allow_file(self) -> bool:
        return self._allow_file

    @allow_file.setter
    def allow_file(self, value: bool) -> None:
        self._allow_file = value
        btn = getattr(self, '_btn_file', None)
        if btn:
            btn.setVisible(value)
            btn.setEnabled(value)

    @property
    def allow_folder(self) -> bool:
        return self._allow_folder

    @allow_folder.setter
    def allow_folder(self, value: bool) -> None:
        self._allow_folder = value
        btn = getattr(self, '_btn_folder', None)
        if btn:
            btn.setVisible(value)
            btn.setEnabled(value)

    def set_mode(self, *, allow_file: Optional[bool] = None, allow_folder: Optional[bool] = None, selection_mode: Optional[str] = None):
        if allow_file is not None:
            self.allow_file = allow_file
        if allow_folder is not None:
            self.allow_folder = allow_folder
        if selection_mode is not None:
            self.selection_mode = selection_mode
        if self._selection_mode == "file" and not self._allow_file:
            self._selection_mode = "folder"
        if self._selection_mode == "folder" and not self._allow_folder:
            self._selection_mode = "file"

    @property
    def using_layer_combo(self) -> bool:
        return self._using_layer_combo

    @property
    def current_layer(self):
        return self._combo.currentLayer()

    @property
    def parent_selector(self):
        return self._parent_selector

    @parent_selector.setter
    def parent_selector(self, value):
        self._parent_selector = value


