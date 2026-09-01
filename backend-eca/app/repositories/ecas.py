"""Acceso a datos de `Eca` / `LoteImportacion` — ECA-007."""
from __future__ import annotations

import uuid as uuid_lib

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.eca import Eca
from app.models.lote_importacion import LoteImportacion


def listar(
    db: Session,
    *,
    estado_id: int | None = None,
    municipio_id: int | None = None,
    q: str | None = None,
    activo: bool | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Eca], int]:
    consulta = select(Eca).where(Eca.eliminado_en.is_(None))
    if estado_id is not None:
        consulta = consulta.where(Eca.estado_id == estado_id)
    if municipio_id is not None:
        consulta = consulta.where(Eca.municipio_id == municipio_id)
    if activo is not None:
        consulta = consulta.where(Eca.activo == activo)
    if q:
        patron = f"%{q}%"
        consulta = consulta.where(or_(Eca.nombre.ilike(patron), Eca.clave_fuente.ilike(patron)))

    total = db.execute(select(func.count()).select_from(consulta.subquery())).scalar_one()
    resultados = db.execute(
        consulta.order_by(Eca.nombre).offset((page - 1) * page_size).limit(page_size)
    ).scalars()
    return list(resultados), total


def obtener_por_id(db: Session, eca_id: int) -> Eca | None:
    eca = db.get(Eca, eca_id)
    return eca if eca and eca.eliminado_en is None else None


def obtener_por_clave_fuente(db: Session, clave_fuente: str) -> Eca | None:
    return db.execute(select(Eca).where(Eca.clave_fuente == clave_fuente)).scalar_one_or_none()


def listar_activas_en_municipios(db: Session, municipio_ids: set[int]) -> list[Eca]:
    """Usada por la REGLA DE ECA (ECA-009) para el conjunto "por ámbito"."""
    if not municipio_ids:
        return []
    return list(
        db.execute(
            select(Eca).where(
                Eca.municipio_id.in_(municipio_ids), Eca.activo.is_(True), Eca.eliminado_en.is_(None)
            )
        ).scalars()
    )


def buscar_por_clave_fuente_o_institucional(db: Session, identificador: str) -> Eca | None:
    """Usada por la importación de asignaciones (ECA-009): el CSV puede
    traer cualquiera de las dos claves como identificador de la ECA."""
    return db.execute(
        select(Eca).where(
            (Eca.clave_fuente == identificador) | (Eca.clave_institucional == identificador)
        )
    ).scalar_one_or_none()


def crear_eca(db: Session, eca: Eca) -> Eca:
    db.add(eca)
    db.flush()
    return eca


# --- lotes de importación -------------------------------------------------


def crear_lote(db: Session, lote: LoteImportacion) -> LoteImportacion:
    db.add(lote)
    db.flush()
    return lote


def obtener_lote_por_uuid(db: Session, lote_uuid: uuid_lib.UUID) -> LoteImportacion | None:
    return db.execute(
        select(LoteImportacion).where(LoteImportacion.uuid == lote_uuid)
    ).scalar_one_or_none()
