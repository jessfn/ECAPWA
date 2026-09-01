"""Acceso a datos de `AsignacionTecnicoEca` — ECA-009."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asignacion_eca import AsignacionTecnicoEca


def listar_activas(
    db: Session, *, usuario_id: int | None = None, eca_id: int | None = None
) -> list[AsignacionTecnicoEca]:
    consulta = select(AsignacionTecnicoEca).where(AsignacionTecnicoEca.activo.is_(True))
    if usuario_id is not None:
        consulta = consulta.where(AsignacionTecnicoEca.usuario_id == usuario_id)
    if eca_id is not None:
        consulta = consulta.where(AsignacionTecnicoEca.eca_id == eca_id)
    return list(db.execute(consulta).scalars())


def obtener_por_id(db: Session, asignacion_id: int) -> AsignacionTecnicoEca | None:
    return db.get(AsignacionTecnicoEca, asignacion_id)


def obtener_activa(db: Session, *, usuario_id: int, eca_id: int) -> AsignacionTecnicoEca | None:
    return db.execute(
        select(AsignacionTecnicoEca).where(
            AsignacionTecnicoEca.usuario_id == usuario_id,
            AsignacionTecnicoEca.eca_id == eca_id,
            AsignacionTecnicoEca.activo.is_(True),
        )
    ).scalar_one_or_none()


def crear(
    db: Session, *, usuario_id: int, eca_id: int, origen: str, asignado_por: int | None,
    lote_importacion_id: int | None = None,
) -> AsignacionTecnicoEca:
    asignacion = AsignacionTecnicoEca(
        usuario_id=usuario_id,
        eca_id=eca_id,
        origen=origen,
        asignado_por=asignado_por,
        lote_importacion_id=lote_importacion_id,
    )
    db.add(asignacion)
    db.flush()
    return asignacion


def dar_de_baja(db: Session, asignacion: AsignacionTecnicoEca) -> None:
    asignacion.activo = False
    asignacion.fecha_fin = datetime.now(timezone.utc).date()
    db.add(asignacion)
