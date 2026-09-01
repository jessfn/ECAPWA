"""Fixtures compartidas — ECA-002.

Dos niveles de prueba conviven aquí:

1. **Unitarias**, sin red ni base de datos real: validan `Settings` y el
   comportamiento del generador `get_db` con una sesión falsa.
2. **De integración contra una base de datos real** (`GET /health`): se
   ejecutan solo si hay una `DATABASE_URL` de prueba realmente alcanzable.
   Si no la hay (como en este entorno de desarrollo sin PostgreSQL local),
   se **saltan explícitamente** en vez de fallar — así `pytest` queda verde
   por defecto, y el mismo test sirve para verificar de verdad en cualquier
   entorno que sí tenga una BD (CI, servidor de Jesús).

Variable de entorno para habilitar las pruebas de integración con BD real:

    TEST_DATABASE_URL=postgresql+psycopg://usuario:pass@localhost:5432/eca_db_test
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

ENV_VARS_VALIDAS = {
    "DATABASE_URL": "postgresql+psycopg://usuario:password@localhost:5432/eca_db_test",
    "SECRET_KEY": "clave-de-prueba-suficientemente-larga-000000",
    "CORS_ORIGINS": "http://localhost:5173",
}


@pytest.fixture(autouse=True)
def _limpiar_cache_settings():
    """`get_settings()` está cacheada por proceso (`lru_cache`); cada test
    que toque variables de entorno debe partir de una caché limpia."""
    from app.core.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def env_valido(monkeypatch: pytest.MonkeyPatch) -> None:
    """Variables de entorno mínimas válidas para que `Settings()` cargue."""
    for clave, valor in ENV_VARS_VALIDAS.items():
        monkeypatch.setenv(clave, valor)


def _url_bd_prueba() -> str | None:
    return os.environ.get("TEST_DATABASE_URL")


def _bd_prueba_alcanzable(url: str) -> bool:
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except OperationalError:
        return False


@pytest.fixture
def app_con_bd_real(monkeypatch: pytest.MonkeyPatch):
    """App FastAPI apuntando a una BD real de prueba.

    Salta el test (no lo falla) si `TEST_DATABASE_URL` no está definida o no
    es alcanzable — ver docstring del módulo.
    """
    url = _url_bd_prueba()
    if not url:
        pytest.skip(
            "TEST_DATABASE_URL no definida: se omite la prueba de integración "
            "con base de datos real. Definir esta variable (p. ej. en CI o en "
            "el servidor) para ejecutarla de verdad contra PostgreSQL."
        )
    if not _bd_prueba_alcanzable(url):
        pytest.skip(f"TEST_DATABASE_URL definida pero no alcanzable: {url}")

    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("SECRET_KEY", ENV_VARS_VALIDAS["SECRET_KEY"])
    monkeypatch.setenv("CORS_ORIGINS", ENV_VARS_VALIDAS["CORS_ORIGINS"])

    from app.core.settings import get_settings

    get_settings.cache_clear()

    # Import diferido: app.main crea el engine al importarse, así que debe
    # ocurrir después de fijar las variables de entorno.
    from app.main import crear_app

    return crear_app()
