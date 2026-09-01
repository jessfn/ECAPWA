"""Configuración por entorno del backend ECA — ECA-002.

Todas las variables se leen de entorno (o de un archivo ``.env`` fuera del
repo) vía Pydantic Settings. Nada de secretos ni valores reales viven aquí ni
en ``.env.example``.

``SECRET_KEY`` no tiene valor por defecto a propósito: si falta, la app debe
fallar al arrancar en vez de operar con un secreto predecible (corrige el
hallazgo de `docs-eca/02_INVENTARIO_TECNICO.md` §4/§20 sobre el fallback
inseguro de Sembrando Vida).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Entorno ---
    APP_ENV: str = Field(default="development", description="development | staging | production")
    APP_NAME: str = Field(default="backend-eca")

    # --- Base de datos (ECA-002) ---
    # Formato: postgresql+psycopg://usuario:password@host:puerto/eca_db
    DATABASE_URL: str = Field(..., description="Cadena de conexión SQLAlchemy/psycopg a eca_db")
    DB_POOL_SIZE: int = Field(default=5, ge=1)
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1, description="Segundos de espera por una conexión del pool")
    DB_POOL_RECYCLE: int = Field(default=1800, ge=60, description="Segundos antes de reciclar una conexión")
    DB_ECHO: bool = Field(default=False, description="Log de SQL emitido (solo development)")

    # --- Seguridad (cableado en ECA-003; declarado desde ECA-002 para que la
    # app no arranque sin él, aunque todavía no se use para emitir tokens) ---
    SECRET_KEY: str = Field(..., min_length=32, description="Cadena aleatoria larga. Sin valor por defecto.")
    ACCESS_TOKEN_MIN: int = Field(default=15, ge=1, description="Vida del access token, minutos")
    REFRESH_TOKEN_DIAS: int = Field(default=30, ge=1, description="DP-1 (06 §2.2): configurable")
    OFFLINE_SESSION_DIAS: int = Field(default=30, ge=1, description="DP-1: validez de sesión local offline")

    # --- CORS (ECA-002) ---
    # Lista blanca explícita. Nunca "*" con allow_credentials=True.
    # `NoDecode`: pydantic-settings intenta parsear tipos complejos desde env
    # como JSON por defecto; con esto delega en nuestro field_validator
    # `_parse_cors_origins` (CSV), en vez de fallar con un `.env` que trae
    # "https://a.com,https://b.com" en texto plano.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # --- Almacenamiento de evidencias (declarado desde ECA-002; se usa desde ECA-015+) ---
    STORAGE_DIR: str = Field(default="./storage", description="Directorio local privado de evidencias")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> list[str]:
        """Acepta ``CORS_ORIGINS`` como CSV en la env var (formato habitual de
        un ``.env``) o como lista ya parseada (útil en tests)."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return list(value)  # type: ignore[arg-type]

    @field_validator("DATABASE_URL")
    @classmethod
    def _validar_database_url(cls, value: str) -> str:
        # Validamos la forma (esquema + host + base de datos) sin exigir que
        # el driver sea literalmente "postgresql+psycopg" en tests que usan
        # otros drivers; el uso real en app/core/db.py sí requiere psycopg.
        PostgresDsn(value)
        return value

    @property
    def es_produccion(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    """Punto único de acceso a la configuración, cacheado por proceso.

    Usar ``get_settings.cache_clear()`` en tests que necesiten variables de
    entorno distintas entre casos.
    """
    return Settings()  # type: ignore[call-arg]
