"""Acceso a datos de `Actividad` — ECA-013 + ECA-019 (filtros de historial)."""
from __future__ import annotations

import uuid as uuid_lib
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.actividad import Actividad
from app.models.eca import Eca


def obtener_por_uuid(db: Session, uuid: uuid_lib.UUID) -> Actividad | None:
    return db.execute(select(Actividad).where(Actividad.uuid == uuid)).scalar_one_or_none()


def obtener_por_id(db: Session, actividad_id: int) -> Actividad | None:
    return db.get(Actividad, actividad_id)


def crear(db: Session, actividad: Actividad) -> Actividad:
    db.add(actividad)
    db.flush()
    return actividad


def _paginar(consulta, *, db: Session, page: int, page_size: int) -> tuple[list[Actividad], int]:
    total = db.execute(select(func.count()).select_from(consulta.subquery())).scalar_one()
    resultados = db.execute(
        consulta.order_by(Actividad.fecha_hora.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars()
    return list(resultados), total


def _consulta_filtrada(
    *,
    usuario_id: int | None,
    eca_id: int | None,
    municipio_id: int | None,
    tipo_actividad_id: int | None,
    tema_id: int | None,
    estado_gps: str | None,
    desde: date | None,
    hasta: date | None,
):
    consulta = select(Actividad).where(Actividad.eliminado_en.is_(None))
    if usuario_id is not None:
        consulta = consulta.where(Actividad.usuario_id == usuario_id)
    if eca_id is not None:
        consulta = consulta.where(Actividad.eca_id == eca_id)
    if municipio_id is not None:
        consulta = consulta.join(Eca, Eca.id == Actividad.eca_id).where(Eca.municipio_id == municipio_id)
    if tipo_actividad_id is not None:
        consulta = consulta.where(Actividad.tipo_actividad_id == tipo_actividad_id)
    if tema_id is not None:
        consulta = consulta.where(Actividad.tema_id == tema_id)
    if estado_gps is not None:
        consulta = consulta.where(Actividad.estado_gps == estado_gps)
    if desde is not None:
        consulta = consulta.where(func.date(Actividad.fecha_hora) >= desde)
    if hasta is not None:
        consulta = consulta.where(func.date(Actividad.fecha_hora) <= hasta)
    return consulta


def listar(
    db: Session,
    *,
    usuario_id: int | None = None,
    eca_id: int | None = None,
    municipio_id: int | None = None,
    tipo_actividad_id: int | None = None,
    tema_id: int | None = None,
    estado_gps: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Actividad], int]:
    consulta = _consulta_filtrada(
        usuario_id=usuario_id,
        eca_id=eca_id,
        municipio_id=municipio_id,
        tipo_actividad_id=tipo_actividad_id,
        tema_id=tema_id,
        estado_gps=estado_gps,
        desde=desde,
        hasta=hasta,
    )
    return _paginar(consulta, db=db, page=page, page_size=page_size)


def listar_todas_sin_paginar(
    db: Session,
    *,
    usuario_id: int | None = None,
    eca_id: int | None = None,
    municipio_id: int | None = None,
    tipo_actividad_id: int | None = None,
    tema_id: int | None = None,
    estado_gps: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = 5000,
) -> list[Actividad]:
    """Usada por la exportación CSV — un tope defensivo (`limite`) evita que
    un filtro demasiado amplio genere un archivo descontrolado."""
    consulta = _consulta_filtrada(
        usuario_id=usuario_id,
        eca_id=eca_id,
        municipio_id=municipio_id,
        tipo_actividad_id=tipo_actividad_id,
        tema_id=tema_id,
        estado_gps=estado_gps,
        desde=desde,
        hasta=hasta,
    )
    return list(db.execute(consulta.order_by(Actividad.fecha_hora.desc()).limit(limite)).scalars())
