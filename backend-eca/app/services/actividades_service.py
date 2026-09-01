"""Lógica de negocio de actividad — ECA-013.

Las reglas de catálogo (`requiere_eca`, `permite_participantes`, coherencia
tema/subtema) se validan **aquí**, en backend, nunca solo en el formulario
de la PWA (criterio de aceptación del ticket).
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.models.actividad import Actividad
from app.models.catalogos import Subtema, TipoActividad
from app.models.usuario import Usuario
from app.repositories import actividades as repo_actividades
from app.repositories import jornadas as repo_jornadas
from app.schemas.gps import GpsPeticion


class JornadaDesconocidaError(Exception):
    pass


class TipoActividadDesconocidoError(Exception):
    pass


class EcaRequeridaError(Exception):
    pass


class ParticipantesNoPermitidosError(Exception):
    pass


class SubtemaIncoherenteError(Exception):
    pass


class GpsInvalidoError(ValueError):
    pass


def _validar_gps(gps: GpsPeticion) -> None:
    if (gps.latitud is None) != (gps.longitud is None):
        raise GpsInvalidoError("latitud y longitud deben venir juntas o ninguna.")
    if gps.estado_gps == "CON_GPS" and (gps.latitud is None or gps.longitud is None):
        raise GpsInvalidoError("estado_gps='CON_GPS' requiere latitud y longitud.")


def crear(
    db: Session,
    *,
    uuid: uuid_lib.UUID,
    jornada_uuid: uuid_lib.UUID,
    eca_id: int | None,
    modalidad_id: int,
    tipo_actividad_id: int,
    tema_id: int | None,
    subtema_id: int | None,
    sistema_productivo_id: int | None,
    descripcion: str,
    resultado: str | None,
    fecha_hora: datetime,
    num_participantes: int | None,
    requiere_seguimiento: bool,
    fecha_proximo_seguimiento: date | None,
    actor: Usuario,
    gps: GpsPeticion | None = None,
) -> Actividad:
    existente = repo_actividades.obtener_por_uuid(db, uuid)
    if existente is not None:
        return existente  # idempotente por uuid

    gps = gps or GpsPeticion()
    _validar_gps(gps)

    jornada = repo_jornadas.obtener_por_uuid(db, jornada_uuid)
    if jornada is None or jornada.usuario_id != actor.id:
        raise JornadaDesconocidaError(f"Jornada desconocida: {jornada_uuid}")

    tipo = db.get(TipoActividad, tipo_actividad_id)
    if tipo is None:
        raise TipoActividadDesconocidoError(f"Tipo de actividad desconocido: {tipo_actividad_id}")
    if tipo.requiere_eca and eca_id is None:
        raise EcaRequeridaError(f"El tipo de actividad «{tipo.nombre}» requiere una ECA.")
    if num_participantes is not None and not tipo.permite_participantes:
        raise ParticipantesNoPermitidosError(
            f"El tipo de actividad «{tipo.nombre}» no admite número de participantes."
        )

    if subtema_id is not None:
        subtema = db.get(Subtema, subtema_id)
        if subtema is None or (tema_id is not None and subtema.tema_id != tema_id):
            raise SubtemaIncoherenteError("El subtema no corresponde al tema indicado.")
        if tema_id is None:
            tema_id = subtema.tema_id

    actividad = Actividad(
        uuid=uuid,
        usuario_id=actor.id,
        jornada_id=jornada.id,
        eca_id=eca_id,
        modalidad_id=modalidad_id,
        tipo_actividad_id=tipo_actividad_id,
        tema_id=tema_id,
        subtema_id=subtema_id,
        sistema_productivo_id=sistema_productivo_id,
        descripcion=descripcion,
        resultado=resultado,
        fecha_hora=fecha_hora,
        latitud=gps.latitud,
        longitud=gps.longitud,
        precision_gps_m=gps.precision_gps_m,
        estado_gps=gps.estado_gps,
        num_participantes=num_participantes,
        requiere_seguimiento=requiere_seguimiento,
        fecha_proximo_seguimiento=fecha_proximo_seguimiento,
        creado_por=actor.id,
        actualizado_por=actor.id,
    )
    repo_actividades.crear(db, actividad)

    registrar_evento(
        db,
        accion="actividad.alta",
        modulo="actividades",
        actor_usuario_id=actor.id,
        entidad_tipo="actividad",
        entidad_id=actividad.id,
        entidad_uuid=actividad.uuid,
    )
    db.commit()
    db.refresh(actividad)
    return actividad


def listar_propias(
    db: Session,
    *,
    usuario_id: int,
    eca_id=None,
    tipo_actividad_id=None,
    tema_id=None,
    estado_gps=None,
    desde=None,
    hasta=None,
    page=1,
    page_size=50,
):
    return repo_actividades.listar(
        db,
        usuario_id=usuario_id,
        eca_id=eca_id,
        tipo_actividad_id=tipo_actividad_id,
        tema_id=tema_id,
        estado_gps=estado_gps,
        desde=desde,
        hasta=hasta,
        page=page,
        page_size=page_size,
    )


def listar_todas(
    db: Session,
    *,
    usuario_id=None,
    eca_id=None,
    municipio_id=None,
    tipo_actividad_id=None,
    tema_id=None,
    estado_gps=None,
    desde=None,
    hasta=None,
    page=1,
    page_size=50,
):
    return repo_actividades.listar(
        db,
        usuario_id=usuario_id,
        eca_id=eca_id,
        municipio_id=municipio_id,
        tipo_actividad_id=tipo_actividad_id,
        tema_id=tema_id,
        estado_gps=estado_gps,
        desde=desde,
        hasta=hasta,
        page=page,
        page_size=page_size,
    )


def exportar_csv(
    db: Session,
    *,
    usuario_id=None,
    eca_id=None,
    municipio_id=None,
    tipo_actividad_id=None,
    tema_id=None,
    estado_gps=None,
    desde=None,
    hasta=None,
) -> list[Actividad]:
    return repo_actividades.listar_todas_sin_paginar(
        db,
        usuario_id=usuario_id,
        eca_id=eca_id,
        municipio_id=municipio_id,
        tipo_actividad_id=tipo_actividad_id,
        tema_id=tema_id,
        estado_gps=estado_gps,
        desde=desde,
        hasta=hasta,
    )
