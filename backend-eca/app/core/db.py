"""Engine, pool de conexiones y sesión por request — ECA-002.

Reemplaza de raíz el patrón de Sembrando Vida (`conn`/`cursor` globales de
módulo, compartidos entre threads — ver `docs-eca/02_INVENTARIO_TECNICO.md`
§3.2/§21). Aquí cada request obtiene su propia sesión de SQLAlchemy, tomada
de un pool de conexiones administrado por el engine, y la sesión se cierra
siempre al terminar el request (éxito o error).
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings

settings = get_settings()

# `pool_pre_ping` evita entregar conexiones muertas (p. ej. tras un reinicio
# de PostgreSQL o un firewall que cierra conexiones idle) — sustituye al
# patrón manual `verificar_conexion_db()` / reconexión con reintentos del
# sistema legado.
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DB_ECHO,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI: una sesión por request.

    No hace ``commit`` implícito: cada endpoint/servicio de escritura
    controla su propia unidad de trabajo (ver `04_ARQUITECTURA_OBJETIVO.md`
    §3.5 "Unidad de trabajo"). Ante una excepción no controlada se hace
    ``rollback`` para no dejar la sesión en un estado inconsistente antes de
    devolverla al pool.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def verificar_conexion() -> bool:
    """``SELECT 1`` con una conexión de vida corta, para `GET /health`.

    Usa una conexión propia (no la sesión de un request) y la libera de
    inmediato: un chequeo de salud no debe competir por conexiones del pool
    de negocio ni dejarlas abiertas.
    """
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
