"""Acceso a datos de `Jornada` — ECA-012."""
from __future__ import annotations

import uuid as uuid_lib
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.jornada import Jornada


def obtener_por_uuid(db: Session, uuid: uuid_lib.UUID) -> Jornada | None:
    return db.execute(select(Jornada).where(Jornada.uuid == uuid)).scalar_one_or_none()


def obtener_abierta_del_dia(db: Session, *, usuario_id: int, fecha: date) -> Jornada | None:
    """La jornada 'principal' del técnico en esa fecha: cualquiera que no
    esté anulada (abierta o ya cerrada), para poder decidir si `POST
    /jornadas` debe crear una nueva o rechazar por duplicado."""
    return db.execute(
        select(Jornada).where(
            Jornada.usuario_id == usuario_id,
            Jornada.fecha == fecha,
            Jornada.estado != "ANULADA",
        )
    ).scalar_one_or_none()


def crear(db: Session, jornada: Jornada) -> Jornada:
    db.add(jornada)
    db.flush()
    return jornada


def listar_de_usuario(db: Session, *, usuario_id: int, fecha: date | None = None) -> list[Jornada]:
    consulta = select(Jornada).where(Jornada.usuario_id == usuario_id).order_by(Jornada.fecha.desc())
    if fecha is not None:
        consulta = consulta.where(Jornada.fecha == fecha)
    return list(db.execute(consulta).scalars())
