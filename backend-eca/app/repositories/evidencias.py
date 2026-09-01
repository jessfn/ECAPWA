"""Acceso a datos de `ActividadEvidencia` — ECA-015."""
from __future__ import annotations

import uuid as uuid_lib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidencia import ActividadEvidencia


def obtener_por_uuid(db: Session, uuid: uuid_lib.UUID) -> ActividadEvidencia | None:
    return db.execute(
        select(ActividadEvidencia).where(ActividadEvidencia.uuid == uuid)
    ).scalar_one_or_none()


def obtener_por_hash(db: Session, *, actividad_id: int, hash_sha256: str) -> ActividadEvidencia | None:
    return db.execute(
        select(ActividadEvidencia).where(
            ActividadEvidencia.actividad_id == actividad_id,
            ActividadEvidencia.hash_sha256 == hash_sha256,
        )
    ).scalar_one_or_none()


def obtener_por_id(db: Session, evidencia_id: int) -> ActividadEvidencia | None:
    return db.get(ActividadEvidencia, evidencia_id)


def listar_de_actividad(db: Session, actividad_id: int) -> list[ActividadEvidencia]:
    return list(
        db.execute(
            select(ActividadEvidencia)
            .where(ActividadEvidencia.actividad_id == actividad_id)
            .order_by(ActividadEvidencia.orden)
        ).scalars()
    )


def crear(db: Session, evidencia: ActividadEvidencia) -> ActividadEvidencia:
    db.add(evidencia)
    db.flush()
    return evidencia


def eliminar(db: Session, evidencia: ActividadEvidencia) -> None:
    db.delete(evidencia)
