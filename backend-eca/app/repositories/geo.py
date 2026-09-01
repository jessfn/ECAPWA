"""Acceso a datos de catálogos geográficos — ECA-006."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.geo import Estado, Municipio


def listar_estados(db: Session, *, solo_activos: bool = False) -> list[Estado]:
    consulta = select(Estado).order_by(Estado.nombre)
    if solo_activos:
        consulta = consulta.where(Estado.activo.is_(True))
    return list(db.execute(consulta).scalars())


def listar_todos_municipios(db: Session) -> list[Municipio]:
    """Sin filtro por estado — usado por la importación masiva de ECA para
    construir un índice `clave_inegi -> Municipio` en memoria (`06`
    ECA-007)."""
    return list(db.execute(select(Municipio)).scalars())


def obtener_estado(db: Session, estado_id: int) -> Estado | None:
    return db.get(Estado, estado_id)


def listar_municipios(
    db: Session, *, estado_id: int, solo_activos: bool = False, texto: str | None = None
) -> list[Municipio]:
    consulta = select(Municipio).where(Municipio.estado_id == estado_id)
    if solo_activos:
        consulta = consulta.where(Municipio.activo.is_(True))
    if texto:
        consulta = consulta.where(Municipio.nombre.ilike(f"%{texto}%"))
    return list(db.execute(consulta.order_by(Municipio.nombre)).scalars())


def obtener_municipio(db: Session, municipio_id: int) -> Municipio | None:
    return db.get(Municipio, municipio_id)
