"""Acceso a datos de `ActividadEvidencia` — ECA-015."""
from __future__ import annotations

import uuid as uuid_lib

from sqlalchemy import func, select
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


def primera_por_actividad(db: Session, actividad_ids: list[int]) -> dict[int, int]:
    """`{actividad_id: evidencia_id}` de la evidencia con `orden` más bajo de
    cada actividad — UNA sola consulta para toda una página de resultados
    (nunca N+1), usada por el listado admin para mostrar una miniatura sin
    tener que pedir el detalle completo de cada actividad."""
    if not actividad_ids:
        return {}
    subconsulta = (
        select(
            ActividadEvidencia.actividad_id,
            func.min(ActividadEvidencia.orden).label("orden_min"),
        )
        .where(ActividadEvidencia.actividad_id.in_(actividad_ids))
        .group_by(ActividadEvidencia.actividad_id)
        .subquery()
    )
    filas = db.execute(
        select(ActividadEvidencia.actividad_id, ActividadEvidencia.id).join(
            subconsulta,
            (ActividadEvidencia.actividad_id == subconsulta.c.actividad_id)
            & (ActividadEvidencia.orden == subconsulta.c.orden_min),
        )
    ).all()
    return {actividad_id: evidencia_id for actividad_id, evidencia_id in filas}


def conteo_por_actividad(db: Session, actividad_ids: list[int]) -> dict[int, int]:
    """`{actividad_id: nº de evidencias}` para toda una página — UNA sola
    consulta. Lo usa el listado admin para saber cuántas fotos tiene cada
    actividad (miniatura "apilada" + contador del visor) sin pedir el
    detalle completo de cada una."""
    if not actividad_ids:
        return {}
    filas = db.execute(
        select(ActividadEvidencia.actividad_id, func.count().label("n"))
        .where(ActividadEvidencia.actividad_id.in_(actividad_ids))
        .group_by(ActividadEvidencia.actividad_id)
    ).all()
    return {actividad_id: n for actividad_id, n in filas}


def crear(db: Session, evidencia: ActividadEvidencia) -> ActividadEvidencia:
    db.add(evidencia)
    db.flush()
    return evidencia


def eliminar(db: Session, evidencia: ActividadEvidencia) -> None:
    db.delete(evidencia)
