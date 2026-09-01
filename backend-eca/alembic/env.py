"""Entorno de Alembic — backend-eca (ECA-002).

Deliberadamente sin `Base.metadata` todavía: ECA-002 no crea tablas de
dominio (eso empieza en ECA-003 con `usuarios`/`tokens_refresco`). Cuando
existan modelos, `target_metadata` se apunta a `app.core.db_base.Base.metadata`
para habilitar `--autogenerate`.

La URL de conexión se toma de `app.core.settings`, nunca de `alembic.ini`,
para no duplicar (ni arriesgar) el secreto de base de datos.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.db_base import Base
from app.core.settings import get_settings

# Importar el paquete de modelos registra cada tabla en `Base.metadata`
# (necesario para que `--autogenerate` los vea).
import app.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    return get_settings().DATABASE_URL


def run_migrations_offline() -> None:
    """Genera SQL sin abrir conexión (``alembic upgrade head --sql``)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica migraciones con una conexión real (modo normal)."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
