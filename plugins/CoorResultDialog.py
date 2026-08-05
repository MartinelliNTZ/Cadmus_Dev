# -*- coding: utf-8 -*-
from ..utils.ToolKeys import ToolKey

from .BasePlugin import BasePluginMTL
from ..utils.ProjectUtils import ProjectUtils
from ..utils.QgisMessageUtil import QgisMessageUtil
from ..utils.Preferences import Preferences
from ..i18n.TranslationManager import STR
from ..resources.widgets.grid.GridReadOnly import GridReadOnly
from ..resources.widgets.grid.GridLabel import GridLabel
from ..resources.widgets.grid.GridExecutionButtons import GridExecutionButtons
from ..resources.widgets.simple.SimpleLabel import SimpleLabel


class CoordResultDialog(BasePluginMTL):
    TOOL_KEY = ToolKey.COORD_CLICK_TOOL

    def __init__(self, iface, info):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.info = info
        self.init(
            tool_key=self.TOOL_KEY, class_name="CoordResultDialog", build_ui=True
        )

        try:
            self.update_info(info)
        except Exception as e:
            self.logger.error(f"Error {e}")

    def _build_ui(self, **kwargs):
        super()._build_ui(
            title=STR.POINT_COORDINATES,
            icon_path="mtl_agro.ico",
            enable_scroll=True,
        )

        # ── WGS84 ReadOnly ────────────────────────────────────
        self.wgs_widget = GridReadOnly(
            title=STR.WGS84_EPSG4326,
            fields={
                "lat_dec": {"title": STR.LATITUDE_DECIMAL, "value": ""},
                "lon_dec": {"title": STR.LONGITUDE_DECIMAL, "value": ""},
                "lat_dms": {"title": STR.LATITUDE_DMS, "value": ""},
                "lon_dms": {"title": STR.LONGITUDE_DMS, "value": ""},
            },
            show_copy_buttons=True,
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self.wgs_widget)

        # ── UTM ReadOnly ─────────────────────────────────────
        self.utm_widget = GridReadOnly(
            title=STR.UTM_SIRGAS_2000,
            fields={
                "utm_x": {"title": STR.EASTING_X, "value": ""},
                "utm_y": {"title": STR.NORTHING_Y, "value": ""},
            },
            show_copy_buttons=True,
            parent=self,
        )
        self.layout.addWidget(self.utm_widget)

        # ── UTM Info Label ────────────────────────────────────
        self.lbl_utm_info = SimpleLabel(text="", parent=self)
        self.layout.addWidget(self.lbl_utm_info)

        # ── Altimetria ReadOnly ──────────────────────────────
        self.alt_widget = GridReadOnly(
            title=STR.ALTIMETRY_OPENTOPO,
            fields={
                "altitude": {
                    "title": STR.APPROX_ALTITUDE_METERS,
                    "value": STR.LOADING,
                }
            },
            show_copy_buttons=True,
            separator_top=True,
            separator_bottom=True,
            parent=self,
        )
        self.layout.addWidget(self.alt_widget)

        # ── Labels de Endereço ────────────────────────────────
        self.address_labels = GridLabel(config={
            "municipio": {"text": f"{STR.CITY}: {STR.LOADING_LOWER}"},
            "state_district": {"text": f"{STR.INTERMEDIATE_REGION}: {STR.LOADING_LOWER}"},
            "state": {"text": f"{STR.STATE}: {STR.LOADING_LOWER}"},
            "region": {"text": f"{STR.REGION}: {STR.LOADING_LOWER}"},
            "country": {"text": f"{STR.COUNTRY}: {STR.LOADING_LOWER}"},
        }, separator_bottom=True, parent=self)
        self.layout.addWidget(self.address_labels)

        # ── Botões de Ação (Copiar Tudo + Fechar + Info) ─────
        self.action_buttons = GridExecutionButtons(
            config={
                "copy_all": {
                    "label": STR.COPY_LOCATION_FULL,
                    "description": "Copia todas as coordenadas e endereço",
                    "callback": self.copy_all_info,
                    "is_run_button": True,
                },
            },
            enable_close_button=True,
            enable_info=True,
            tool_key=self.TOOL_KEY,
            parent=self,
        )
        self.layout.add_execution_buttons(self.action_buttons)

    def _load_prefs(self):
        self.logger.debug(
            f"_load_prefs: loaded prefs keys={list(self.preferences.keys())}"
        )

    def _save_prefs(self):
        Preferences.save_tool_prefs(self.TOOL_KEY, self.preferences)
        self.logger.debug(
            f"_save_prefs: prefs salvas: {self.preferences.get('window_width')}x{self.preferences.get('window_height')}"
        )

    def copy_all_info(self):
        parts = []

        lat_dec = self.wgs_widget.get_value("lat_dec") or ""
        lon_dec = self.wgs_widget.get_value("lon_dec") or ""
        lat_dms = self.wgs_widget.get_value("lat_dms") or ""
        lon_dms = self.wgs_widget.get_value("lon_dms") or ""
        parts.append(STR.WGS84_EPSG4326)
        parts.append(f"{STR.LATITUDE_DECIMAL}: {lat_dec}")
        parts.append(f"{STR.LONGITUDE_DECIMAL}: {lon_dec}")
        if lat_dms or lon_dms:
            parts.append(f"{STR.LATITUDE_DMS}: {lat_dms}")
            parts.append(f"{STR.LONGITUDE_DMS}: {lon_dms}")

        parts.append(STR.UTM_SIRGAS_2000)
        parts.append(self.lbl_utm_info.text())
        utm_x = self.utm_widget.get_value("utm_x") or ""
        utm_y = self.utm_widget.get_value("utm_y") or ""
        parts.append(f"{STR.EASTING_X}: {utm_x}")
        parts.append(f"{STR.NORTHING_Y}: {utm_y}")

        alt = self.alt_widget.get_value("altitude") or ""
        parts.append(f"{STR.APPROX_ALTITUDE_METERS}: {alt}")

        parts.append(STR.ADDRESS_OSM)
        parts.append(self.address_labels.get_text("municipio"))
        parts.append(self.address_labels.get_text("state_district"))
        parts.append(self.address_labels.get_text("state"))
        parts.append(self.address_labels.get_text("region"))
        parts.append(self.address_labels.get_text("country"))

        text = "\n".join(parts)
        ok = ProjectUtils.set_clipboard_text(text)
        if ok:
            QgisMessageUtil.bar_success(
                self.iface,
                STR.LOCATION_COPIED_TO_CLIPBOARD,
                title=STR.COPIED,
            )
            self.logger.info(
                "copy_all_info: conteúdo copiado para área de transferência"
            )
        else:
            self.logger.warning(
                "copy_all_info: falha ao copiar para área de transferência"
            )

    def update_info(self, info):
        self.info = info
        self.logger.debug(f"update_info: info={info}")

        self.wgs_widget.set_value("lat_dec", f"{info['lat']:.8f}")
        self.wgs_widget.set_value("lon_dec", f"{info['lon']:.8f}")
        self.wgs_widget.set_value("lat_dms", info.get("lat_dms", ""))
        self.wgs_widget.set_value("lon_dms", info.get("lon_dms", ""))

        self.lbl_utm_info.setText(
            f"EPSG:{info['epsg']} | {STR.ZONE} {info['zona_num']}{info['zona_letra']} | "
            f"{STR.HEMISPHERE} {info['hemisferio']}"
        )

        self.utm_widget.set_value("utm_x", f"{info['utm_x']:.3f}")
        self.utm_widget.set_value("utm_y", f"{info['utm_y']:.3f}")

        self.alt_widget.set_value("altitude", STR.LOADING)
        self.set_address(None)

    def set_altitude(self, value):
        self.alt_widget.set_value(
            "altitude", STR.UNAVAILABLE if value is None else f"{value:.2f} m"
        )
        self.logger.debug(f"set_altitude: {value}")

    def set_address(self, data):
        if not data:
            self.address_labels.set_config({
                "municipio": {"text": f"{STR.CITY}: {STR.LOADING_LOWER}"},
                "state_district": {"text": f"{STR.INTERMEDIATE_REGION}: {STR.LOADING_LOWER}"},
                "state": {"text": f"{STR.STATE}: {STR.LOADING_LOWER}"},
                "region": {"text": f"{STR.REGION}: {STR.LOADING_LOWER}"},
                "country": {"text": f"{STR.COUNTRY}: {STR.LOADING_LOWER}"},
            })
            return

        self.address_labels.set_config({
            "municipio": {"text": f"{STR.CITY}: {data.get('municipio', '-')}"},
            "state_district": {"text": f"{STR.INTERMEDIATE_REGION}: {data.get('state_district', '-')}"},
            "state": {"text": f"{STR.STATE}: {data.get('state', '-')}"},
            "region": {"text": f"{STR.REGION}: {data.get('region', '-')}"},
            "country": {"text": f"{STR.COUNTRY}: {data.get('country', '-')}"},
        })
        self.logger.debug(f"set_address: {data}")

    def copy_address(self):
        text_parts = []
        text_parts.append(self.address_labels.get_text("municipio"))
        text_parts.append(self.address_labels.get_text("state_district"))
        text_parts.append(self.address_labels.get_text("state"))
        text_parts.append(self.address_labels.get_text("region"))
        text_parts.append(self.address_labels.get_text("country"))
        text = "\n".join(text_parts)
        ok = ProjectUtils.set_clipboard_text(text)
        if ok:
            QgisMessageUtil.bar_success(
                self.iface,
                STR.ADDRESS_COPIED_TO_CLIPBOARD,
                title=STR.COPIED,
            )
            self.logger.info("copy_address: endereço copiado")
        else:
            self.logger.warning(
                "copy_address: falha ao copiar para área de transferência"
            )