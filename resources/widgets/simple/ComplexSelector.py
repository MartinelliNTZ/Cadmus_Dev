# -*- coding: utf-8 -*-
"""
ComplexSelector -— Seletor avançado com suporte a file/folder/files/folders.
============================================================================
NÃO usa GridRadio. O comportamento é definido pelos parâmetros:
  - allow_file / allow_folder: quais botões aparecem (🔍 / 📁)
  - multiple: se pode selecionar múltiplos itens
  - selection_mode: modo padrão ("file" ou "folder")
  - mode_type: "input" ou "output"

Lógica central:
  - O widget sempre guarda: root_path (diretório base) + selected_list (itens)
  - 🔍 clicado → seleciona arquivo(s) via ExplorerUtils
  - 📁 clicado → seleciona pasta(s) via ExplorerUtils
  - 📂 (só output) → gera path com ProjectUtil + subfolder + fixed_name
  - 📄 (só input) → ListFileDialog
  - ➡️ → abre o Windows Explorer no diretório do path atual

Uso:
    sel = ComplexSelector(label_text="Entrada:", allow_file=True, allow_folder=True, multiple=False, selection_mode="file")

    sel.get_root_path()      # diretório base
    sel.get_selected_list()  # itens selecionados
    sel.path()               # primeiro item
    sel.path_type()          # "file" | "folder" | "files" | "folders"
"""

from __future__ import annotations

import os
import subprocess
from typing import Callable, Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit

from core.config.LogUtils import LogUtils
from resources.widgets.dialogs.ListFileDialog import ListFileDialog
from resources.widgets.simple.SimpleSecondaryButton import SimpleSecondaryButton
from utils.ExplorerUtils import ExplorerUtils
from utils.ProjectUtil import ProjectUtil


class ComplexSelector(QWidget):
    """
    Seletor avançado com suporte a file/folder/files/folders.

    Diferente do SimpleSelector, NÃO usa GridRadio. O comportamento
    é definido pelos parâmetros allow_file, allow_folder, multiple,
    selection_mode e mode_type na criação.

    O widget sempre armazena:
      - root_path: diretório base da seleção
      - selected_list: lista de itens selecionados (paths completos)
    """

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
        selection_mode: str = "file",   # "file" | "folder"
        # ── Controle de botões ──
        show_suggest_button: bool = False,
        show_project_button: bool = False,
        show_explorer_button: bool = True,
        show_origin_button: bool = False,
        suggested_path: str = "",
        # ── CRS embutido ──
        crs_enable: bool = False,
        # ── Output config ──
        mode_type: str = "input",  # "input" | "output"
        fixed_name: str = "",
        subfolder: str = "",
        parent=None,
    ):
        super().__init__(parent)

        # Validação
        if not allow_file and not allow_folder:
            allow_file = True

        # Sanitiza selection_mode
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
        self._show_suggest_button = show_suggest_button
        self._show_project_button = show_project_button
        self._show_explorer_button = show_explorer_button
        self._show_origin_button = show_origin_button
        self._suggested_rel_path: str = suggested_path
        self._mode_type = mode_type
        self._fixed_name = fixed_name
        self._subfolder = subfolder

        # Estado interno
        self._root_path: str = ""
        self._selected_list: list[str] = []
        self._updating_display: bool = False  # guard para loop textChanged

        # Logger
        self._logger = LogUtils(tool="ComplexSelector", class_name="ComplexSelector")

        # CRS embutido
        self._crs_enable = crs_enable
        self._crs_widget = None  # CrsSelectorWidget | None

        # Callbacks públicos
        self.on_path_change = None    # callback(paths: list[str])
        self.on_browse_click = None   # callback()
        self.on_suggest_click = None  # callback()
        self.on_origin_click = None   # callback() — botão 📥, grid configura

        # Constrói UI
        self._build_ui(label_text, placeholder, tooltip, label_width)

        # Se default_path foi passado, inicializa
        if default_path:
            self.set_path(default_path)

    # ══════════════════════════════════════════════════════════════════
    # UI
    # ══════════════════════════════════════════════════════════════════

    def _build_ui(self, label_text, placeholder, tooltip, label_width):
        """Constrói o layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Label
        self._label = QLabel(label_text)
        self._label.setFixedWidth(label_width)
        if tooltip:
            self._label.setToolTip(tooltip)
        layout.addWidget(self._label)

        # QLineEdit (editável — usuário pode digitar manualmente)
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        if tooltip:
            self._edit.setToolTip(tooltip)
        # Sincroniza digitação manual com estado interno
        self._edit.textChanged.connect(self._on_edit_text_changed)
        layout.addWidget(self._edit, 1)

        # Botões
        self._add_buttons(layout)

        # Atualiza display
        self._update_display()

    def _add_buttons(self, layout):
        """Adiciona botões conforme configuração."""
        # ── 🔍 (file) ──
        if self._allow_file:
            self._btn_file = SimpleSecondaryButton("🔍")
            self._btn_file.setFixedWidth(32)
            self._btn_file.setToolTip(
                "Selecionar arquivos" if self._multiple else "Selecionar arquivo"
            )
            self._btn_file.clicked.connect(self._browse_file)
            layout.addWidget(self._btn_file)

        # ── 📁 (folder) ──
        if self._allow_folder:
            self._btn_folder = SimpleSecondaryButton("📁")
            self._btn_folder.setFixedWidth(30)
            self._btn_folder.setToolTip(
                "Selecionar pastas" if self._multiple else "Selecionar pasta"
            )
            self._btn_folder.clicked.connect(self._browse_folder)
            layout.addWidget(self._btn_folder)

        # ── 📂 (suggested — só output) ──
        if self._mode_type == "output" and self._show_suggest_button:
            self._btn_suggest = SimpleSecondaryButton("🛠️")
            self._btn_suggest.setFixedWidth(30)
            self._btn_suggest.setToolTip("Usar pasta do projeto")
            self._btn_suggest.clicked.connect(self._on_suggest_clicked)
            layout.addWidget(self._btn_suggest)

        # ── 📄 (project — só input) ──
        if self._mode_type == "input" and self._show_project_button:
            self._btn_project = SimpleSecondaryButton("📄")
            self._btn_project.setFixedWidth(30)
            self._btn_project.setToolTip("Selecionar arquivo do projeto")
            self._btn_project.clicked.connect(self._on_project_clicked)
            layout.addWidget(self._btn_project)

        # ── 📥 (origin — só output com parent) ──
        if self._show_origin_button:
            self._btn_origin = SimpleSecondaryButton("📥")
            self._btn_origin.setFixedWidth(30)
            self._btn_origin.setToolTip("Usar mesmo diretório da origem")
            # Conecta ao callback público — o grid configura depois
            self._btn_origin.clicked.connect(self._on_origin_clicked)
            layout.addWidget(self._btn_origin)

        # ── ➡️ (explorer — sempre visível por padrão) ──
        if self._show_explorer_button:
            self._btn_explorer = SimpleSecondaryButton("➡️")
            self._btn_explorer.setFixedWidth(30)
            self._btn_explorer.setToolTip("Abrir localização no Explorer")
            self._btn_explorer.clicked.connect(self._open_explorer)
            layout.addWidget(self._btn_explorer)
            
        # ── CRS embutido (ao lado dos botões) ──
        if self._crs_enable:
            from resources.widgets.crs.CrsSelectorWidget import CrsSelectorWidget
            self._crs_widget = CrsSelectorWidget(label=None, compact=True)
            self._crs_widget.setFixedWidth(150)
            layout.addWidget(self._crs_widget)


    # ══════════════════════════════════════════════════════════════════
    # Display
    # ══════════════════════════════════════════════════════════════════

    def _update_display(self):
        """Atualiza o QLineEdit conforme o estado atual."""
        self._updating_display = True
        try:
            if not self._selected_list:
                self._edit.setText("")
                return

            if not self._multiple:
                # Mostra o path completo
                self._edit.setText(self._selected_list[0])
            else:
                # Mostra paths separados por "; "
                self._edit.setText("; ".join(self._selected_list))
        finally:
            self._updating_display = False

    # ══════════════════════════════════════════════════════════════════
    # Handlers de busca
    # ══════════════════════════════════════════════════════════════════

    def _on_edit_text_changed(self, text: str):
        """
        Sincroniza a digitação manual do usuário com o estado interno.
        Quando o usuário digita manualmente, atualiza _selected_list e _root_path.

        Em modo multiple, paths separados por ";" são convertidos em lista.
        """
        # Ignora se estamos atualizando o display programaticamente
        if self._updating_display:
            return

        if not text:
            self._root_path = ""
            self._selected_list = []
            self._emit_path_change()
            return

        if not self._multiple:
            # Modo single: o texto digitado vira o primeiro item
            self._root_path = os.path.dirname(text) if os.path.isfile(text) else text
            self._selected_list = [text]
            self._emit_path_change()
        else:
            # Modo multiple: paths separados por "; " ou ";"
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

    def _browse_file(self):
        """Busca arquivo(s) — disparado pelo 🔍.
        Em modo input: usa open_file/open_files.
        Em modo output: usa save_file.
        """
        self._logger.info("🔍 clicado", code="COMPLEX_FILE_CLICKED")
        if self.on_browse_click:
            self.on_browse_click()

        initial_dir = ExplorerUtils.resolve_initial_dir(
            self._root_path or (self._selected_list[0] if self._selected_list else "")
        )

        if self._mode_type == "output":
            # Output: diálogo de salvar
            path = ExplorerUtils.save_file(
                "Salvar arquivo", initial_dir, self._file_filter, self,
            )
            if path:
                self._root_path = os.path.dirname(path)
                self._selected_list = [path]
                self._update_display()
                self._emit_path_change()
        elif self._multiple:
            paths = ExplorerUtils.open_files(
                "Selecionar arquivos", initial_dir, self._file_filter, self,
            )
            if paths:
                self._root_path = os.path.dirname(paths[0]) if paths else ""
                self._selected_list = list(paths)
                self._update_display()
                self._emit_path_change()
        else:
            path = ExplorerUtils.open_file(
                "Selecionar arquivo", initial_dir, self._file_filter, self,
            )
            if path:
                self._root_path = os.path.dirname(path)
                self._selected_list = [path]
                self._update_display()
                self._emit_path_change()

    def _browse_folder(self):
        """Busca pasta(s) — disparado pelo 📁."""
        self._logger.info("📁 clicado", code="COMPLEX_FOLDER_CLICKED")
        if self.on_browse_click:
            self.on_browse_click()

        initial_dir = ExplorerUtils.resolve_initial_dir(
            self._root_path or (self._selected_list[0] if self._selected_list else "")
        )

        if self._multiple:
            paths = ExplorerUtils.select_directories(
                "Selecionar pastas", initial_dir, self,
            )
            if paths:
                self._root_path = paths[0] if paths else ""
                self._selected_list = list(paths)
                self._update_display()
                self._emit_path_change()
        else:
            path = ExplorerUtils.select_directory(
                "Selecionar pasta", initial_dir, self,
            )
            if path:
                self._root_path = path
                self._selected_list = [path]
                self._update_display()
                self._emit_path_change()

    # ══════════════════════════════════════════════════════════════════
    # ➡️ (explorer — abrir localização no Windows Explorer)
    # ══════════════════════════════════════════════════════════════════

    def _open_explorer(self):
        """Abre o Windows Explorer no diretório do path atual."""
        target = None
        if self._selected_list:
            first = self._selected_list[0]
            if os.path.isdir(first):
                target = first
            else:
                target = os.path.dirname(first)

        if not target or not os.path.isdir(target):
            self._logger.info(
                "Nenhum diretório válido para abrir no Explorer",
                code="COMPLEX_EXPLORER_NO_DIR",
            )
            return

        self._logger.info(
            f"Abrindo Explorer em: {target}",
            code="COMPLEX_EXPLORER_OPEN",
            path=target,
        )
        try:
            if os.name == "nt":
                # Windows: usa explorer com separador de subcomando
                os.startfile(target)  # type: ignore[attr-defined]
            else:
                # Linux / macOS
                subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self._logger.error(
                "Erro ao abrir Explorer",
                code="COMPLEX_EXPLORER_ERROR",
                error=str(e),
            )

    # ══════════════════════════════════════════════════════════════════
    # 📄 (project — só input)
    # ══════════════════════════════════════════════════════════════════

    def _on_project_clicked(self):
        """Abre ListFileDialog com as extensões do filtro."""
        self._logger.info("📄 clicado", code="COMPLEX_PROJECT_CLICKED")

        root_folder = ProjectUtil.get_root_folder()
        if not root_folder:
            self._logger.warning("Nenhum projeto ativo", code="COMPLEX_NO_PROJECT")
            return

        extensions = self._parse_extensions_from_filter(self._file_filter)
        if not extensions:
            self._logger.warning("Nenhuma extensão extraída", code="COMPLEX_NO_EXT")
            return

        dialog = ListFileDialog(
            extensions=extensions,
            multi_select=self._multiple,
            parent=self,
        )
        if dialog.exec():
            paths = dialog.selected_paths
            if paths:
                self._root_path = os.path.dirname(paths[0]) if paths else ""
                self._selected_list = list(paths)
                self._update_display()
                self._emit_path_change()

    @staticmethod
    def _parse_extensions_from_filter(file_filter: str) -> list[str]:
        """Extrai extensões de um filtro de arquivo."""
        import re
        match = re.search(r'\(([^)]+)\)', file_filter)
        if not match:
            return []
        parts = match.group(1).split()
        exts = [p.strip().lower() for p in parts if p.startswith("*")]
        return [e.replace("*", "") for e in exts if e.replace("*", "")]

    # ══════════════════════════════════════════════════════════════════
    # 📥 (origin — botão de usar origem)
    # ══════════════════════════════════════════════════════════════════

    def _on_origin_clicked(self):
        """Disparado pelo 📥. Delega para callback público."""
        self._logger.info(
            "📥 clicado (origin)",
            code="COMPLEX_ORIGIN_CLICKED",
            has_callback=str(self.on_origin_click is not None),
            mode=self._mode_type,
            has_parent=str(bool(self.on_origin_click)),
        )
        if self.on_origin_click:
            self.on_origin_click()

    def set_origin_callback(self, callback: Callable[[], None], tooltip: str = ""):
        """
        Define callback personalizado para o botão 📥.
        Usado pelo GridComplexSelector para conectar a lógica de geração de output.

        Args:
            callback: Função sem argumentos a ser chamada quando 📥 for clicado.
            tooltip: Tooltip opcional para o botão.
        """
        if hasattr(self, '_btn_origin'):
            try:
                self._btn_origin.clicked.disconnect()
            except TypeError:
                pass
            self._btn_origin.clicked.connect(callback)
            if tooltip:
                self._btn_origin.setToolTip(tooltip)

    @property
    def show_origin_button(self) -> bool:
        """Se o botão 📥 está visível."""
        return self._show_origin_button

    @show_origin_button.setter
    def show_origin_button(self, value: bool) -> None:
        """Mostra/esconde o botão 📥."""
        self._show_origin_button = value
        btn = getattr(self, '_btn_origin', None)
        if btn:
            btn.setVisible(value)
            btn.setEnabled(value)

    # ══════════════════════════════════════════════════════════════════
    # 📂 (suggested — só output)
    # ══════════════════════════════════════════════════════════════════

    def _on_suggest_clicked(self):
        """
        Gera path de saída: ProjectUtil.get_root_folder() + subfolder + fixed_name.
        Ex: C:/projeto/lasvectorconverter/lasvectorconverted.gpkg
        """
        self._logger.info("📂 clicado (output)", code="COMPLEX_SUGGEST_CLICKED")
        if self.on_suggest_click:
            self.on_suggest_click()

        root_folder = ProjectUtil.get_root_folder()
        if not root_folder:
            self._logger.warning("Nenhum projeto ativo", code="COMPLEX_NO_PROJECT")
            return

        if self._subfolder:
            output_dir = os.path.join(root_folder, self._subfolder)
        else:
            output_dir = root_folder

        if self._fixed_name:
            output_path = os.path.join(output_dir, self._fixed_name)
        else:
            output_path = output_dir

        self._root_path = output_dir
        self._selected_list = [output_path]
        self._update_display()
        self._emit_path_change()

        self._logger.info(
            f"Output: {output_path}",
            code="COMPLEX_SUGGEST_PATH",
            root=root_folder,
            subfolder=self._subfolder,
            fixed_name=self._fixed_name,
        )

    # ══════════════════════════════════════════════════════════════════
    # Callback
    # ══════════════════════════════════════════════════════════════════

    def _emit_path_change(self):
        """Dispara callback de path change + detecção CRS se aplicável."""
        if self.on_path_change:
            self.on_path_change(self._selected_list)

        # ── CRS: detecção automática se for input ──
        if self._crs_enable and self._mode_type == "input" and self._crs_widget:
            self._auto_detect_crs()

    def _auto_detect_crs(self):
        """Detecta CRS automaticamente ou pergunta para forçar (só input)."""
        path = self.path()
        if not path or not os.path.isfile(path):
            return

        ext = os.path.splitext(path)[1].lower()
        if ext not in (".las", ".laz"):
            return  # Só detecta CRS em LAS/LAZ

        from utils.las.LasLayerProjection import LasLayerProjection

        crs = LasLayerProjection.get_crs(path)
        if crs:
            self._crs_widget.set_crs(crs)
            self._crs_widget.setToolTip(f"CRS detectado: {crs}")
            return

        # Não detectou — pergunta se quer forçar
        from utils.MessageBox import MessageBox
        resposta = MessageBox.show_question(
            f"Não foi possível detectar a projeção do arquivo:\n{path}\n\n"
            "Deseja forçar uma projeção no arquivo?\n"
            "(será criado um arquivo .mdata)",
            title="Projeção não detectada",
            buttons=MessageBox.YES_NO,
            default_button=MessageBox.YES,
        )

        if resposta != MessageBox.YES:
            self._crs_widget.setToolTip("CRS não detectado")
            return

        from resources.widgets.crs.CrsSearchDialog import CrsSearchDialog
        dialog = CrsSearchDialog(parent=self.window() if self.window() else self)
        if dialog.exec():
            epsg = dialog.selected_epsg
            if epsg:
                LasLayerProjection.save_mdata(path, epsg)
                self._crs_widget.set_crs(epsg)
                self._crs_widget.setToolTip(f"CRS forçado: {epsg}")

    # ══════════════════════════════════════════════════════════════════
    # API Pública
    # ══════════════════════════════════════════════════════════════════

    def get_root_path(self) -> str:
        """Retorna o diretório base da seleção."""
        return self._root_path

    def get_selected_list(self) -> list[str]:
        """Retorna a lista de itens selecionados (paths completos)."""
        return self._selected_list.copy()

    def get_paths(self) -> list[str]:
        """Atalho para get_selected_list()."""
        return self.get_selected_list()

    def get_path(self, index: int = 0) -> str:
        """Retorna um path específico pelo índice."""
        if 0 <= index < len(self._selected_list):
            return self._selected_list[index]
        return ""

    def path(self) -> str:
        """Retorna o primeiro path (compatível com SimpleSelector)."""
        return self.get_path(0)

    def paths(self) -> list[str]:
        """Retorna lista de paths (compatível com SimpleSelector)."""
        return self.get_paths()

    def path_type(self) -> str:
        """
        Retorna o tipo do modo atual baseado em selection_mode e multiple:
        - single + file  → "file"
        - single + folder → "folder"
        - multi + file   → "files"
        - multi + folder → "folders"
        """
        if self._multiple:
            return f"{self._selection_mode}s"
        return self._selection_mode

    def path_count(self) -> int:
        """Número de paths selecionados."""
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
        """Define um path único."""
        if path:
            self._root_path = os.path.dirname(path) if os.path.isfile(path) else path
            self._selected_list = [path]
        else:
            self._root_path = ""
            self._selected_list = []
        self._update_display()
        self._emit_path_change()

    def set_paths(self, paths: list[str]):
        """Define múltiplos paths."""
        if paths:
            first = paths[0]
            self._root_path = os.path.dirname(first) if os.path.isfile(first) else first
            self._selected_list = list(paths)
        else:
            self._root_path = ""
            self._selected_list = []
        self._update_display()
        self._emit_path_change()

    def clear(self):
        """Limpa tudo."""
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

    # ── CRS embutido ───────────────────────────────────────────────

    @property
    def crs_widget(self):  # -> CrsSelectorWidget | None
        """Retorna o widget CRS embutido, ou None se crs_enable=False."""
        return self._crs_widget

    @property
    def crs(self) -> str:
        """Retorna o CRS selecionado (ex: 'EPSG:31983') ou vazio."""
        if self._crs_widget:
            return self._crs_widget.get_crs()
        return ""

    @crs.setter
    def crs(self, value: str) -> None:
        """Define o CRS programaticamente."""
        if self._crs_widget:
            self._crs_widget.set_crs(value)

    # ── Configuração ────────────────────────────────────────────────

    def set_suggested_path(self, suggested_rel_path: str):
        """Define o path relativo para o botão 📂."""
        self._suggested_rel_path = suggested_rel_path

    def set_fixed_name(self, fixed_name: str):
        """
        Define o nome fixo do arquivo de saída.
        Usado pelo 📂 (suggest button) para gerar o path.
        O plugin pode chamar isso para atualizar dinamicamente
        quando o formato de saída muda.

        Args:
            fixed_name: Nome do arquivo (ex: "lasvectorconverted.gpkg").
        """
        self._fixed_name = fixed_name
        self._logger.info(
            f"fixed_name: '{fixed_name}'",
            code="COMPLEX_FIXED_NAME_CHANGED",
        )

    def set_suggested_callback(self, callback: Callable[[], None], tooltip: str = ""):
        """Define callback personalizado para 📂."""
        if hasattr(self, '_btn_suggest'):
            try:
                self._btn_suggest.clicked.disconnect()
            except TypeError:
                pass
            self._btn_suggest.clicked.connect(callback)
            if tooltip:
                self._btn_suggest.setToolTip(tooltip)

    @property
    def file_filter(self) -> str:
        return self._file_filter

    @file_filter.setter
    def file_filter(self, value: str) -> None:
        self._file_filter = value
        self._logger.info(f"file_filter: '{value}'", code="COMPLEX_FILE_FILTER_CHANGED")

    @property
    def edit(self) -> QLineEdit:
        return self._edit

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

    # ── Dynamic Mode: allow_file / allow_folder ────────────────────

    @property
    def allow_file(self) -> bool:
        return self._allow_file

    @allow_file.setter
    def allow_file(self, value: bool) -> None:
        """Atualiza _allow_file e mostra/esconde 🔍."""
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
        """Atualiza _allow_folder e mostra/esconde 📁."""
        self._allow_folder = value
        btn = getattr(self, '_btn_folder', None)
        if btn:
            btn.setVisible(value)
            btn.setEnabled(value)

    def set_mode(self, *, allow_file: bool | None = None, allow_folder: bool | None = None, selection_mode: str | None = None):
        """
        Atalho para alterar modo dinamicamente.
        Atualiza allow_file/allow_folder e selection_mode em um único método.
        """
        if allow_file is not None:
            self.allow_file = allow_file
        if allow_folder is not None:
            self.allow_folder = allow_folder
        if selection_mode is not None:
            self.selection_mode = selection_mode
        # Sanitiza — se o selection_mode atual não for compatível, corrige
        if self._selection_mode == "file" and not self._allow_file:
            self._selection_mode = "folder"
        if self._selection_mode == "folder" and not self._allow_folder:
            self._selection_mode = "file"
        # Atualiza tooltips dos botões
        if hasattr(self, '_btn_file'):
            self._btn_file.setToolTip(
                "Selecionar arquivos" if self._multiple else "Selecionar arquivo"
            )
        if hasattr(self, '_btn_folder'):
            self._btn_folder.setToolTip(
                "Selecionar pastas" if self._multiple else "Selecionar pasta"
            )
        self._logger.info(
            f"Modo alterado: file={self._allow_file}, folder={self._allow_folder}, mode={self._selection_mode}",
            code="COMPLEX_MODE_CHANGED",
        )