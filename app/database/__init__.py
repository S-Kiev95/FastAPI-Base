from .connection import engine, get_session, init_db, Base

# Alias para compatibilidad con módulos que usan get_db
get_db = get_session

__all__ = ["engine", "get_session", "get_db", "init_db", "Base"]
