"""Base declarativa de SQLAlchemy — ECA-003.

Punto único del que heredan todos los modelos ORM (`app/models/*.py`).
Separado de `app/core/db.py` (engine/sesión) para que `alembic/env.py` pueda
importar `Base.metadata` sin arrastrar la creación del engine.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
