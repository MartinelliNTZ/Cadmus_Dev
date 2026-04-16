# -*- coding: utf-8 -*-
from .Strings_de import Strings_de
from qgis.core import QgsApplication
from .Strings_pt_BR import Strings_pt_BR

# futuramente:
from .Strings_en import Strings_en
from .Strings_es import Strings_es
from ..utils.ToolKeys import ToolKey
from ..core.config.LogUtils import LogUtils
from ..utils.Preferences import Preferences


class TranslationManager:
    INGLES = "en"
    PORTUGUES_BR = "pt_BR"
    PORTUGES_PT = "pt_PT"
    ESPANHOL = "es"
    ALEMAO = "de"
    FRANCES = "fr"

    def __init__(self):

        self.logger = LogUtils(tool=ToolKey.SYSTEM, class_name="TranslationManager")
        self.system_prefs = Preferences.load_tool_prefs(ToolKey.SYSTEM)
        self.locale = self.system_prefs.get("plugin_language", None)  # ex: 'pt_BR'

        if not self.locale:
            self.logger.debug(
                f"Nenhuma preferência de idioma encontrada, usando locale do QGIS. Prefs: {self.system_prefs}"
            )
            self.locale = QgsApplication.locale()  # ex: 'pt_BR'
        self.lang = self.locale[:2]

        if self.locale == self.INGLES:
            self.STR = Strings_en()

        elif self.locale == self.ESPANHOL:
            self.STR = Strings_es()  # fallback
        if self.locale == self.ALEMAO:
            self.STR = Strings_de()  # fallback
        else:
            self.STR = Strings_pt_BR()
        self.logger.info(
            f"TranslationManager inicializado com locale: {self.locale}, idioma: {self.lang}"
        )


TM = TranslationManager()
STR = TM.STR
LOCALE = TM.locale
"""Locale: TranslationManager.INGLES,TranslationManager.PORTUGUES_BR,TranslationManager.ESPANHOL"""


# "Locale: pt_BR,  Language: Português (Brasil)"
# "Locale: en, Language: English"
# "Locale: es,  Language: Español"
# "Locale: pt_PT, Language: Português (Portugal)"
# "Locale: ar, Language: العربية"
# "Locale: az, Language: Azərbaycan"
# "Locale: bg, Language: Български"
# "Locale: bs, Language: Bosanski"
# "Locale: ca, Language: Català"
# "Locale: cs, Language: Čeština"
# "Locale: da, Language: Dansk"
# "Locale: de, Language: Deutsch"
# "Locale: en_US, Language: English (United States)"
# "Locale: es,  Language: Español"
# "Locale: et, Language: Eesti"
# "Locale: eu, Language: Euskara"
# "Locale: fa, Language: فارسی"
# "Locale: fi, Language: Suomi"
# "Locale: fr, Language: Français"
# "Locale: gl, Language: Galego"
# "Locale: hu, Language: Magyar"
# "Locale: is, Language: Íslenska"
# "Locale: it, Language: Italiano"
# "Locale: ja, Language: 日本語"
# "Locale: ko, Language: 한국어"
# "Locale: ky, Language: Кыргызча"
# "Locale：lt, Language：Lietuvių"
# "Locale：lv, Language：Latviešu"
# "Locale：nb, Language：Norsk bokmål"
# "Locale：nl, Language：Nederlands"
# "Locale：pl, Language：Polski"
# "Locale：pt_BR, Language：Português (Brasil)"
# "Locale：pt_PT, Language：Português (Portugal)"
# "Locale：ro, Language：Română"
# "Locale：ru, Language：Русский"
# "getLocale：sc, Language：Sardu"
# "getLocale：sk, Language：Slovenčina"
# "getLocale：sv, Language：Svenska"
# "getLocale：tr, Language：Türkçe"
# "getLocale：uk,Language ：Українська'
# 'getLocale ：vi ，Language ：Tiếng Việt'
# 'getLocale ：zh-Hans ，Language ：简体中文'
# 'getLocale ：zh-Hant ，Language ：繁體中文'
