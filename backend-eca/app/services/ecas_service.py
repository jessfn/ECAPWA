"""CRUD individual de ECA (alta/edición manual) — ECA-007.

La importación masiva tiene su propio servicio
(`app/services/importacion_eca_service.py`); este es solo para el alta y
edición de una ECA a la vez desde el panel.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.models.eca import Eca
from app.models.usuario import Usuario
from app.repositories import ecas as repo_ecas


def crear_eca(
    db: Session,
    *,
    nombre: str,
    estado_id: int,
    municipio_id: int,
    clave_institucional: str | None,
    localidad_nombre: str | None,
    latitud: float | None,
    longitud: float | None,
    actor: Usuario,
) -> Eca:
    eca = Eca(
        nombre=nombre,
        estado_id=estado_id,
        municipio_id=municipio_id,
        clave_institucional=clave_institucional,
        localidad_nombre=localidad_nombre,
        latitud=latitud,
        longitud=longitud,
        fuente_carga="MANUAL",
        creado_por=actor.id,
    )
    repo_ecas.crear_eca(db, eca)

    registrar_evento(
        db,
        accion="eca.alta",
        modulo="ecas",
        actor_usuario_id=actor.id,
        entidad_tipo="eca",
        entidad_id=eca.id,
        entidad_uuid=eca.uuid,
        descripcion=f"Alta manual de ECA {nombre}",
        datos_despues={"nombre": nombre, "estado_id": estado_id, "municipio_id": municipio_id},
    )
    db.commit()
    db.refresh(eca)
    return eca


def editar_eca(
    db: Session,
    *,
    eca: Eca,
    nombre: str | None,
    estado_id: int | None,
    municipio_id: int | None,
    clave_institucional: str | None,
    localidad_nombre: str | None,
    latitud: float | None,
    longitud: float | None,
    activo: bool | None,
    actor: Usuario,
) -> Eca:
    antes = {
        "nombre": eca.nombre,
        "estado_id": eca.estado_id,
        "municipio_id": eca.municipio_id,
        "activo": eca.activo,
    }
    if nombre is not None:
        eca.nombre = nombre
    if estado_id is not None:
        eca.estado_id = estado_id
    if municipio_id is not None:
        eca.municipio_id = municipio_id
    if clave_institucional is not None:
        eca.clave_institucional = clave_institucional
    if localidad_nombre is not None:
        eca.localidad_nombre = localidad_nombre
    if latitud is not None:
        eca.latitud = latitud
    if longitud is not None:
        eca.longitud = longitud
    if activo is not None:
        eca.activo = activo
    eca.actualizado_por = actor.id

    db.add(eca)
    registrar_evento(
        db,
        accion="eca.edicion",
        modulo="ecas",
        actor_usuario_id=actor.id,
        entidad_tipo="eca",
        entidad_id=eca.id,
        entidad_uuid=eca.uuid,
        datos_antes=antes,
        datos_despues={
            "nombre": eca.nombre,
            "estado_id": eca.estado_id,
            "municipio_id": eca.municipio_id,
            "activo": eca.activo,
        },
    )
    db.commit()
    db.refresh(eca)
    return eca
