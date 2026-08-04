# -*- coding: utf-8 -*-
"""
ComplexCrsSelector — Seletor de CRS (EPSG) com label e QgsProjectionSelectionWidget.
=====================================================================================
Widget raiz (SEM versão grid). Plugins USAM este widget.

Composição (layout horizontal):
    [SimpleLabel] [QgsProjectionSelectionWidget]

Autoconfiguração total:
- AppStyles para estilos globais
- ThemeManager → BaseTheme para tokens visuais
- _specific_style() para estilo próprio

Uso em plugins:
    crs_selector = ComplexCrsSelector(
        label_text=STR.DEFAULT_CRS,
        default_auth_id="EPSG:4326",
        tooltip="Selecione o SRC padrão",
        tool_key=self.TOOL_KEY,
        parent=self,
    )
    self.layout.addWidget(crs_selector)

    crs_selector.set_crs_authid("EPSG:31983")
    crs = crs_selector.get_crs()
    authid = crs_selector.get_crs_authid()
"""

from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout
from qgis.core import QgsCoordinateReferenceSystem
from qgis.gui import QgsProjectionSelectionWidget

from ...core.config.LogUtils import LogUtils
from ..styles.AppStyles import AppStyles
from .simple.SimpleLabel import SimpleLabel


class ComplexCrsSelector(QWidget):
    """
    Seletor de CRS com label e QgsProjectionSelectionWidget.

    Parâmetros
    ----------
    label_text : str, optional
        Texto do label.
    default_auth_id : str, optional
        Authid inicial (ex: "EPSG:4326").
    tooltip : str, optional
        Tooltip do seletor.
    tool_key : ToolKey, optional
        ToolKey para logs.
    parent : QWidget, optional
        Widget pai.
    """

    def __init__(
        self,
        label_text: str = "",
        default_auth_id: str = "",
        tooltip: str = "",
        tool_key=None,
        parent=None,
    ):
        super().__init__(parent)

        self._label_text = label_text
        self._default_auth_id = default_auth_id
        self._tooltip = tooltip
        self._tool_key = tool_key

        # Logger
        tool_name = tool_key or "ComplexCrsSelector"
        self.logger = LogUtils(tool=tool_name, class_name="ComplexCrsSelector")

        try:
            self._build_ui()
            self._apply_styles()
        except Exception as error:
            self.logger.exception(
                "Erro ao construir ComplexCrsSelector",
                code="CRS_SELECTOR_BUILD_ERROR",
                error=str(error),
            )

    # ══════════════════════════════════════════════════════════════════
    # UI
    # ══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        """Monta layout horizontal: label + QgsProjectionSelectionWidget."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ── Label ────────────────────────────────────────────────
        self._label = SimpleLabel(text=self._label_text, parent=self)
        if self._tooltip:
            self._label.setToolTip(self._tooltip)
        layout.addWidget(self._label, 0)

        # ── QgsProjectionSelectionWidget (seletor de CRS) ────────
        self._selector = QgsProjectionSelectionWidget(self)
        self._selector.setToolTip(self._tooltip or "Selecione um SRC")
        self._selector.crsChanged.connect(self._on_crs_changed)
        layout.addWidget(self._selector, 1)

        # Define CRS inicial
        if self._default_auth_id:
            self.set_crs_authid(self._default_auth_id)

    # ══════════════════════════════════════════════════════════════════
    # Handlers
    # ══════════════════════════════════════════════════════════════════

    def _on_crs_changed(self, crs: QgsCoordinateReferenceSystem):
        """Loga quando o CRS muda."""
        authid = crs.authid() if crs and crs.isValid() else ""
        description = crs.description() if crs and crs.isValid() else ""
        self.logger.debug(
            f"CRS selecionado: {authid} | {description}",
            code="CRS_SELECTOR_CHANGED",
        )

    # ══════════════════════════════════════════════════════════════════
    # API Pública
    # ══════════════════════════════════════════════════════════════════

    def set_crs(self, crs: QgsCoordinateReferenceSystem):
        """Define o CRS via QgsCoordinateReferenceSystem."""
        if crs and crs.isValid():
            self._selector.setCrs(crs)

    def set_crs_authid(self, authid: str) -> bool:
        """
        Define o CRS por authid.

        Retorna True se o authid é válido e foi aplicado, False caso contrário.
        """
        crs = QgsCoordinateReferenceSystem(authid)
        if crs.isValid():
            self._selector.setCrs(crs)
            return True
        return False

    def get_crs(self) -> QgsCoordinateReferenceSystem:
        """Retorna o CRS atual."""
        return self._selector.crs()

    def get_crs_authid(self) -> str:
        """Retorna o authid do CRS atual."""
        crs = self.get_crs()
        return crs.authid() if crs and crs.isValid() else ""

    def selector(self) -> QgsProjectionSelectionWidget:
        """Acesso direto ao QgsProjectionSelectionWidget."""
        return self._selector

    # ══════════════════════════════════════════════════════════════════
    # Estilos
    # ══════════════════════════════════════════════════════════════════

    def _apply_styles(self):
        """Aplica estilos globais + específico."""
        combined_style = self._get_global_style() + self._specific_style()
        self.setStyleSheet(combined_style)

    def _get_global_style(self) -> str:
        """Estilos globais via AppStyles."""
        return AppStyles.label() + AppStyles.combobox()

    def _specific_style(self) -> str:
        """
        Estilo específico deste widget.
        Usa tokens do tema com nomes descritivos.
        """
        return ""

