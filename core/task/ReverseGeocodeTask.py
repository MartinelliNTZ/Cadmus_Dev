# -*- coding: utf-8 -*-
from qgis.core import QgsTask
import json
from urllib.parse import urlparse
import http.client
from ..config.LogUtils import LogUtils


class ReverseGeocodeTask(QgsTask):
    """
    Model puro:
    - Executa reverse geocode
    - Retorna dados ou erro
    - NÃO interage com UI
    """

    def __init__(self, lat, lon, callback):
        super().__init__("Reverse Geocode (BigDataCloud)", QgsTask.CanCancel)
        self.lat = lat
        self.lon = lon
        self.callback = callback
        self.result = None
        self.error = None

    # --------------------------------------------------
    # EXECUÇÃO
    # --------------------------------------------------
    def run(self):
        try:
            url = (
                "https://api.bigdatacloud.net/data/reverse-geocode-client"
                f"?latitude={self.lat}&longitude={self.lon}"
                "&localityLanguage=pt"
            )

            # Validação de segurança: aceitar apenas esquemas http/https
            parsed = urlparse(url)
            if parsed.scheme.lower() not in ("http", "https"):
                self.error = f"Invalid URL scheme: {parsed.scheme}"
                return False

            # Follow redirects (max 5) using http.client and validate scheme on redirects
            max_redirects = 5
            current_url = url
            logger = LogUtils(tool="reverse_geocode", class_name="ReverseGeocodeTask")
            for hop in range(max_redirects + 1):
                parsed = urlparse(current_url)
                host = parsed.hostname
                port = parsed.port
                path = parsed.path or "/"
                if parsed.query:
                    path = path + "?" + parsed.query
                try:
                    if parsed.scheme.lower() == "https":
                        conn = http.client.HTTPSConnection(host, port=port, timeout=15)
                    else:
                        conn = http.client.HTTPConnection(host, port=port, timeout=15)
                    conn.request("GET", path, headers={"User-Agent": "MTL-Tools-QGIS"})
                    resp = conn.getresponse()
                    status = resp.status
                    if 300 <= status < 400:
                        # Redirect
                        location = resp.getheader("Location")
                        conn.close()
                        logger.info(
                            f"Redirect {status} -> {location}", code="REDIRECT_FOLLOW"
                        )
                        if not location:
                            self.error = (
                                f"Redirect without Location header (status {status})"
                            )
                            return False
                        # Resolve relative redirects
                        new_parsed = urlparse(location)
                        if not new_parsed.scheme:
                            # relative URL
                            from urllib.parse import urljoin

                            current_url = urljoin(current_url, location)
                        else:
                            current_url = location
                        # validate scheme
                        new_scheme = urlparse(current_url).scheme.lower()
                        if new_scheme not in ("http", "https"):
                            self.error = f"Invalid redirect scheme: {new_scheme}"
                            return False
                        # continue to next hop
                        continue
                    elif status != 200:
                        self.error = f"HTTP error {status}"
                        conn.close()
                        return False
                    else:
                        data = json.loads(resp.read().decode("utf-8"))
                        conn.close()
                        break
                except Exception as e:
                    logger.exception(e, code="HTTP_REQUEST_ERROR")
                    self.error = str(e)
                    return False

            admin = data.get("localityInfo", {}).get("administrative", [])

            municipio = state_district = state = region = None
            country = data.get("countryName")

            for item in admin:
                lvl = item.get("adminLevel")
                name = item.get("name")

                if not name:
                    continue

                if lvl == 8:
                    municipio = name
                elif lvl == 5:
                    state_district = name
                elif lvl == 4:
                    state = name
                elif lvl == 3:
                    region = name

            if not municipio:
                municipio = data.get("city") or data.get("locality")

            if not state:
                state = data.get("principalSubdivision")

            if not any([municipio, state, country]):
                self.error = "Dados administrativos indisponíveis"
                return False

            self.result = {
                "municipio": municipio,
                "state_district": state_district,
                "state": state,
                "region": region,
                "country": country,
            }

            return True

        except Exception as e:
            self.error = str(e)
            return False

    # --------------------------------------------------
    # CALLBACK FINAL
    # --------------------------------------------------
    def finished(self, success):
        # Backwards-compatible callback + pipeline hooks
        logger = LogUtils(tool="reverse_geocode", class_name="ReverseGeocodeTask")
        try:
            if success:
                if hasattr(self, "on_success") and callable(
                    getattr(self, "on_success")
                ):
                    try:
                        self.on_success(self.result)
                    except Exception as exc:
                        logger.exception(exc, code="FINISHED_ON_SUCCESS_ERROR")
                if hasattr(self, "callback") and callable(self.callback):
                    try:
                        self.callback(self.result, None)
                    except Exception as exc:
                        logger.exception(exc, code="FINISHED_CALLBACK_ERROR")
            else:
                if hasattr(self, "on_error") and callable(getattr(self, "on_error")):
                    try:
                        self.on_error(self.error)
                    except Exception as exc:
                        logger.exception(exc, code="FINISHED_ON_ERROR_ERROR")
                if hasattr(self, "callback") and callable(self.callback):
                    try:
                        self.callback(None, self.error)
                    except Exception as exc:
                        logger.exception(exc, code="FINISHED_CALLBACK_ERROR")
        except Exception as exc:
            logger.exception(exc, code="FINISHED_UNKNOWN_ERROR")
