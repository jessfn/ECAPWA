"""Repositorio de `SolicitudAcceso` — ECA-020b."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.solicitud_acceso import SolicitudAcceso


def crear(
    db: Session, *, nombre: str, correo: str, telefono: str | None, notas: str | None
) -> SolicitudAcceso:
    solicitud = SolicitudAcceso(nombre=nombre, correo=correo, telefono=telefono, notas=notas)
    db.add(solicitud)
    db.flush()
    return solicitud


def listar(db: Session, *, estado: str | None = None) -> list[SolicitudAcceso]:
    consulta = select(SolicitudAcceso).order_by(SolicitudAcceso.creado_en.desc())
    if estado:
        consulta = consulta.where(SolicitudAcceso.estado == estado)
    return list(db.scalars(consulta))


def obtener_por_id(db: Session, solicitud_id: int) -> SolicitudAcceso | None:
    return db.get(SolicitudAcceso, solicitud_id)


def resolver(db: Session, *, solicitud: SolicitudAcceso, estado: str, atendida_por: int) -> SolicitudAcceso:
    solicitud.estado = estado
    solicitud.atendida_por = atendida_por
    solicitud.atendida_en = datetime.now(timezone.utc)
    db.flush()
    return solicitud
