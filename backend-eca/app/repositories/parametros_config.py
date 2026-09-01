"""Acceso a datos de `ParametroConfig` — ECA-009."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.parametro_config import ParametroConfig


def obtener(db: Session, clave: str) -> ParametroConfig | None:
    return db.execute(select(ParametroConfig).where(ParametroConfig.clave == clave)).scalar_one_or_none()


def obtener_valor(db: Session, clave: str, *, por_defecto=None):
    parametro = obtener(db, clave)
    return parametro.valor if parametro is not None else por_defecto
