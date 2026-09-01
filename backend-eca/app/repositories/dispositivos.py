"""Acceso a datos de `Dispositivo` — ECA-017."""
from __future__ import annotations

import uuid as uuid_lib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dispositivo import Dispositivo


def obtener_por_uuid(db: Session, uuid: uuid_lib.UUID) -> Dispositivo | None:
    return db.execute(select(Dispositivo).where(Dispositivo.uuid == uuid)).scalar_one_or_none()


def crear(db: Session, dispositivo: Dispositivo) -> Dispositivo:
    db.add(dispositivo)
    db.flush()
    return dispositivo
