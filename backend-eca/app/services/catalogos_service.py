"""Lógica de negocio de catálogos de actividad — ECA-010."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.models.catalogos import Subtema, TipoActividad
from app.models.usuario import Usuario
from app.repositories import catalogos as repo_catalogos


class TemaInexistenteError(Exception):
    pass


class RangoFotosInvalidoError(ValueError):
    pass


def actualizar_item(db: Session, *, tipo: str, item, cambios: dict, actor: Usuario):
    antes = {campo: getattr(item, campo) for campo in cambios if hasattr(item, campo)}

    for campo, valor in cambios.items():
        if valor is not None and hasattr(item, campo):
            setattr(item, campo, valor)

    if isinstance(item, TipoActividad):
        # Validación del rango efectivo (tras aplicar los cambios), no solo
        # de los campos que llegaron en esta petición — un `PATCH` que solo
        # manda `min_fotos` igual debe respetar el `max_fotos` ya guardado.
        if item.min_fotos > item.max_fotos:
            raise RangoFotosInvalidoError("min_fotos no puede ser mayor que max_fotos.")

    db.add(item)
    registrar_evento(
        db,
        accion="catalogo.edicion",
        modulo="catalogos",
        actor_usuario_id=actor.id,
        entidad_tipo=tipo,
        entidad_id=item.id,
        datos_antes=antes,
        datos_despues={campo: getattr(item, campo) for campo in cambios if hasattr(item, campo)},
    )
    db.commit()
    db.refresh(item)
    return item


def crear_subtema(
    db: Session, *, tema_id: int, clave: str, nombre: str, orden: int, actor: Usuario
) -> Subtema:
    tema = repo_catalogos.obtener_tema(db, tema_id)
    if tema is None:
        raise TemaInexistenteError(f"Tema desconocido: {tema_id}")

    subtema = Subtema(tema_id=tema_id, clave=clave, nombre=nombre, orden=orden)
    repo_catalogos.crear_subtema(db, subtema)

    registrar_evento(
        db,
        accion="catalogo.alta",
        modulo="catalogos",
        actor_usuario_id=actor.id,
        entidad_tipo="subtemas",
        entidad_id=subtema.id,
        descripcion=f"Alta de subtema {nombre} en tema {tema.nombre}",
    )
    db.commit()
    db.refresh(subtema)
    return subtema
