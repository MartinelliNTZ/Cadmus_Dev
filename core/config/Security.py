class Security:
    """Configurações de segurança e credenciais para serviços externos."""

    SUPABASE_URL: str = "https://ynlameyuhvmesozcuanh.supabase.co"
    SUPABASE_API_KEY: str = "sb_publishable_TTKVxJBQndH8tqtnyru1Uw_CVwgVzxE"

    SUPABASE_HEADERS: dict = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
    }

    SUPABASE_LICENSE_TABLE: str = "api_keys"
