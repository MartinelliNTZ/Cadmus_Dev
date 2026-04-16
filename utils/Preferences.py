# -*- coding: utf-8 -*-
import os
import json
from qgis.PyQt.QtCore import QStandardPaths
from ..core.config.LogUtils import LogUtils

# module logger for preferences utils
logger = LogUtils(tool="preferences", class_name="Preferences")


def _resolve_app_data_path():
    """Retorna o caminho adequado para armazenar configurações entre Qt5/Qt6."""
    for candidate in (
        "AppDataLocation",
        "AppLocalDataLocation",
        "AppConfigLocation",
        "DataLocation",
        "GenericDataLocation",
    ):
        if hasattr(QStandardPaths, candidate):
            return QStandardPaths.writableLocation(getattr(QStandardPaths, candidate))

    # fallback mais básico se nenhum atributo estiver disponível.
    return os.path.expanduser("~")


class Preferences:
    """Gerencia as preferências do plugin, armazenando em um JSON local."""

    PREF_FOLDER = os.path.join(_resolve_app_data_path(), "MTLTools")
    PREF_FILE = os.path.join(PREF_FOLDER, "mtl_prefs.json")

    def _ensure_pref_folder():
        os.makedirs(Preferences.PREF_FOLDER, exist_ok=True)
        if not os.path.exists(Preferences.PREF_FILE):
            with open(Preferences.PREF_FILE, "w", encoding="utf-8") as f:
                f.write("{}")

    def load_prefs():
        """Carrega todo o JSON de preferências."""
        Preferences._ensure_pref_folder()
        try:
            with open(Preferences.PREF_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar preferences file: {e}")
            return {}

    def save_prefs(data):
        """Salva o JSON inteiro de preferências."""
        Preferences._ensure_pref_folder()
        with open(Preferences.PREF_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def load_tool_prefs(tool_key):
        """Carrega apenas as prefs da ferramenta específica."""
        prefs = Preferences.load_prefs()
        return prefs.get(tool_key, {})

    @staticmethod
    def save_tool_prefs(tool_key, values: dict):
        """Salva prefs de uma ferramenta específica."""
        prefs = Preferences.load_prefs()
        prefs[tool_key] = values
        Preferences.save_prefs(prefs)

    @staticmethod
    def load_pref_key_by_tool(pref_key):
        """
        Retorna {tool_key: valor} para todos os tools
        que possuem a chave informada.
        """
        prefs = Preferences.load_prefs()
        result = {}

        for tool_key, tool_prefs in prefs.items():
            if isinstance(tool_prefs, dict) and pref_key in tool_prefs:
                result[tool_key] = tool_prefs[pref_key]

        return result

    @staticmethod
    def set_value_for_all_tools(pref_key, value, filter_by=None):
        """
        Define um valor em uma chave específica para ferramentas, com filtro opcional.
        GENÉRICO: filtra por QUALQUER chave-valor no dict de prefs, não apenas category.
        
        Exemplos:
            - set_value_for_all_tools("main_action", False)  
              → seta main_action=False para TODOS os tools
            - set_value_for_all_tools("main_action", False, filter_by={"category": "VECTOR"})
              → seta main_action=False apenas para tools onde prefs["category"]=="VECTOR"
            - set_value_for_all_tools("width", 100, filter_by={"tool_type": "DIALOG"})
              → seta width=100 apenas para tools onde prefs["tool_type"]=="DIALOG"
        
        Args:
            pref_key (str): Chave de preferência a ser setada (ex: "main_action", "width")
            value: Valor a ser atribuído
            filter_by (dict): Filtro opcional. Se fornecido, apenas ferramentas que
                            atendem TODAS as condições são modificadas.
                            Ex: {"category": "VECTOR", "tool_type": "DIALOG"}
        
        Retorna:
            int: Número de ferramentas modificadas
        """
        if filter_by is None:
            filter_by = {}
        
        prefs = Preferences.load_prefs()
        modified_count = 0
        
        logger.debug(
            f"[set_value_for_all_tools] Iniciando. pref_key='{pref_key}', "
            f"value={value}, filter_by={filter_by}, total_tools={len(prefs)}"
        )
        
        # DEBUG: Log todas as ferramentas e suas categorias/tipos
        if filter_by:
            logger.debug(f"[set_value_for_all_tools] Ferramentas disponíveis:")
            for tool_key, tool_prefs in prefs.items():
                if isinstance(tool_prefs, dict):
                    cat = tool_prefs.get("category", "UNDEFINED")
                    ttype = tool_prefs.get("tool_type", "UNDEFINED")
                    logger.debug(f"[set_value_for_all_tools]   '{tool_key}': category={cat}, tool_type={ttype}")
        
        for tool_key in list(prefs.keys()):
            if not isinstance(prefs[tool_key], dict):
                logger.debug(
                    f"[set_value_for_all_tools] Tool '{tool_key}' não é dict, pulando"
                )
                continue
            
            tool_prefs = prefs[tool_key]
            
            # Aplicar filtro: verificar se TODAS as condições do filter_by são atendidas
            skip_this_tool = False
            if filter_by:
                for filter_key, filter_value in filter_by.items():
                    tool_filter_value = tool_prefs.get(filter_key, "UNDEFINED")
                    if tool_filter_value != filter_value:
                        logger.debug(
                            f"[set_value_for_all_tools] Tool '{tool_key}' "
                            f"'{filter_key}'={tool_filter_value}, filtro '{filter_key}'={filter_value}, PULANDO"
                        )
                        skip_this_tool = True
                        break
            
            if skip_this_tool:
                continue
            
            # Se passou no filtro (ou não há filtro), seta o valor
            old_value = tool_prefs.get(pref_key, "UNDEFINED")
            prefs[tool_key][pref_key] = value
            modified_count += 1
            
            logger.debug(
                f"[set_value_for_all_tools] Tool '{tool_key}': "
                f"'{pref_key}' {old_value} → {value}"
            )
        
        Preferences.save_prefs(prefs)
        logger.info(
            f"[set_value_for_all_tools] ✓ Concluído: {modified_count} ferramentas "
            f"modificadas. pref_key='{pref_key}', value={value}, filtro={filter_by}"
        )
        
        return modified_count

    @staticmethod
    def delete_value_for_all_tools(pref_key, filter_by=None):
        """
        Deleta um valor de chave específica em ferramentas, com filtro opcional.
        GENÉRICO: filtra por QUALQUER chave-valor no dict de prefs.
        
        Exemplos:
            - delete_value_for_all_tools("width")  
              → deleta a chave "width" de TODOS os tools
            - delete_value_for_all_tools("width", filter_by={"category": "VECTOR"})
              → deleta "width" apenas de tools onde prefs["category"]=="VECTOR"
            - delete_value_for_all_tools("enabled", filter_by={"tool_type": "DIALOG"})
              → deleta "enabled" apenas de tools onde prefs["tool_type"]=="DIALOG"
        
        Args:
            pref_key (str): Chave de preferência a ser deletada (ex: "main_action", "width")
            filter_by (dict): Filtro opcional. Se fornecido, apenas ferramentas que
                            atendem TODAS as condições são modificadas.
                            Ex: {"category": "VECTOR", "tool_type": "DIALOG"}
        
        Retorna:
            int: Número de ferramentas onde a chave foi deletada
        """
        if filter_by is None:
            filter_by = {}
        
        prefs = Preferences.load_prefs()
        deleted_count = 0
        
        logger.debug(
            f"[delete_value_for_all_tools] Iniciando. pref_key='{pref_key}', "
            f"filter_by={filter_by}, total_tools={len(prefs)}"
        )
        
        # DEBUG: Log todas as ferramentas e suas categorias/tipos
        if filter_by:
            logger.debug(f"[delete_value_for_all_tools] Ferramentas disponíveis:")
            for tool_key, tool_prefs in prefs.items():
                if isinstance(tool_prefs, dict):
                    cat = tool_prefs.get("category", "UNDEFINED")
                    ttype = tool_prefs.get("tool_type", "UNDEFINED")
                    logger.debug(f"[delete_value_for_all_tools]   '{tool_key}': category={cat}, tool_type={ttype}")
        
        for tool_key in list(prefs.keys()):
            if not isinstance(prefs[tool_key], dict):
                logger.debug(
                    f"[delete_value_for_all_tools] Tool '{tool_key}' não é dict, pulando"
                )
                continue
            
            tool_prefs = prefs[tool_key]
            
            # Aplicar filtro: verificar se TODAS as condições do filter_by são atendidas
            skip_this_tool = False
            if filter_by:
                for filter_key, filter_value in filter_by.items():
                    tool_filter_value = tool_prefs.get(filter_key, "UNDEFINED")
                    if tool_filter_value != filter_value:
                        logger.debug(
                            f"[delete_value_for_all_tools] Tool '{tool_key}' "
                            f"'{filter_key}'={tool_filter_value}, filtro '{filter_key}'={filter_value}, PULANDO"
                        )
                        skip_this_tool = True
                        break
            
            if skip_this_tool:
                continue
            
            # Se passou no filtro (ou não há filtro), deleta a chave se existir
            if pref_key in tool_prefs:
                old_value = tool_prefs.pop(pref_key)
                deleted_count += 1
                logger.debug(
                    f"[delete_value_for_all_tools] Tool '{tool_key}': "
                    f"'{pref_key}' (valor: {old_value}) deletado ✓"
                )
            else:
                logger.debug(
                    f"[delete_value_for_all_tools] Tool '{tool_key}': "
                    f"'{pref_key}' não encontrada, pulando"
                )
        
        Preferences.save_prefs(prefs)
        logger.info(
            f"[delete_value_for_all_tools] ✓ Concluído: {deleted_count} ferramentas "
            f"modificadas. pref_key='{pref_key}', filtro={filter_by}"
        )
        
        return deleted_count


# DEPRECATED - manter funções abaixo para compatibilidade, mas usar as versões da classe Preferences acima.
PREF_FOLDER = os.path.join(_resolve_app_data_path(), "MTLTools")
PREF_FILE = os.path.join(PREF_FOLDER, "mtl_prefs.json")


def _ensure_pref_folder():
    """DEPRECATED USE Preferences._ensure_pref_folder() instead."""
    os.makedirs(PREF_FOLDER, exist_ok=True)
    if not os.path.exists(PREF_FILE):
        with open(PREF_FILE, "w", encoding="utf-8") as f:
            f.write("{}")


def load_prefs():
    """DEPRECATED USE Preferences.load_prefs() instead."""
    _ensure_pref_folder()
    try:
        with open(PREF_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar deprecated preferences file: {e}")
        return {}


def save_prefs(data):
    """DEPRECATED USE Preferences.save_prefs() instead."""
    _ensure_pref_folder()
    with open(PREF_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_tool_prefs(tool_key):
    """DEPRECATED USE Preferences.load_tool_prefs() instead."""
    prefs = load_prefs()
    return prefs.get(tool_key, {})


def save_tool_prefs(tool_key, values: dict):
    """DEPRECATED USE Preferences.save_tool_prefs() instead."""
    prefs = load_prefs()
    prefs[tool_key] = values
    save_prefs(prefs)


def load_pref_key_by_tool(pref_key):
    """DEPRECATED USE Preferences.load_pref_key_by_tool() instead."""
    return Preferences.load_pref_key_by_tool(pref_key)
