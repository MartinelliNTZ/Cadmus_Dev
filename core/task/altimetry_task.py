# -*- coding: utf-8 -*-
from qgis.core import QgsTask
import json
from urllib.parse import urlparse
import http.client
from ..config.LogUtils import LogUtils


class AltimetriaTask(QgsTask):
    """
    Model puro:
    - Consulta altimetria (OpenTopoData / SRTM 90m)
    - Retorna altitude ou erro
    - NÃO interage com UI
    """

    def __init__(self, lat, lon, callback):
        super().__init__("Altimetria (SRTM 90m)", QgsTask.CanCancel)
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
                "https://api.opentopodata.org/v1/srtm90m"
                f"?locations={self.lat},{self.lon}"
            )

            # Validação de segurança: aceitar apenas esquemas http/https
            parsed = urlparse(url)
            if parsed.scheme.lower() not in ("http", "https"):
                self.error = f"Invalid URL scheme: {parsed.scheme}"
                return False

            # Use http.client to avoid bandit B310 on urllib.request.urlopen
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
                conn.request(
                    "GET", path, headers={"User-Agent": "Cadmus-Altimetry-Task"}
                )
                resp = conn.getresponse()
                if resp.status != 200:
                    self.error = f"HTTP error {resp.status}"
                    conn.close()
                    return False
                data = json.loads(resp.read().decode("utf-8"))
                conn.close()
            except Exception as e:
                self.error = str(e)
                return False

            if data.get("status") != "OK":
                self.error = "Resposta inválida da API"
                return False

            results = data.get("results") or []
            if not results:
                self.error = "Nenhum dado retornado"
                return False

            elevation = results[0].get("elevation")
            if elevation is None:
                self.error = "Elevação indisponível"
                return False

            self.result = float(elevation)
            return True

        except Exception as e:
            self.error = str(e)
            return False

    # --------------------------------------------------
    # CALLBACK FINAL
    # --------------------------------------------------
    def finished(self, success):
        # Backwards-compatible callback
        logger = LogUtils(tool="altimetry_task", class_name="AltimetriaTask")
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
