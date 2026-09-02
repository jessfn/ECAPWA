"""Lógica de negocio de jornadas — ECA-012.

Riesgo documentado en el ticket: la "fecha" de la jornada depende de la
zona horaria del técnico. Se fija en el servidor a partir de `inicio_en`
convertido a una zona constante del MVP (`America/Mexico_City`) — no una
zona por usuario, no `parametros_config` todavía; si el negocio lo pide
más adelante, se vuelve configurable sin tocar el resto del flujo.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.models.jornada import Jornada
from app.models.usuario import Usuario
from app.repositories import jornadas as repo_jornadas
from app.schemas.jornada import GpsPeticion

ZONA_MVP = ZoneInfo("America/Mexico_City")


class JornadaNoEncontradaError(Exception):
    pass


class RangoFechasInvalidoError(ValueError):
    pass


def _fecha_local(momento: datetime):
    return momento.astimezone(ZONA_MVP).date()


class DetalleRequeridoError(ValueError):
    pass


def iniciar(
    db: Session, *, uuid, inicio_en: datetime, gps: GpsPeticion | None, nota: str, actor: Usuario
) -> Jornada:
    existente = repo_jornadas.obtener_por_uuid(db, uuid)
    if existente is not None:
        return existente  # idempotente por uuid

    if not nota or not nota.strip():
        raise DetalleRequeridoError("El detalle de inicio de jornada es obligatorio.")

    fecha = _fecha_local(inicio_en)
    ya_del_dia = repo_jornadas.obtener_abierta_del_dia(db, usuario_id=actor.id, fecha=fecha)
    if ya_del_dia is not None:
        # Ya hay una jornada principal ese día: se devuelve, no se duplica
        # (criterio de aceptación: 1 jornada principal por técnico/fecha).
        return ya_del_dia

    gps = gps or GpsPeticion()
    jornada = Jornada(
        uuid=uuid,
        usuario_id=actor.id,
        fecha=fecha,
        estado="ABIERTA",
        inicio_en=inicio_en,
        latitud_inicio=gps.latitud,
        longitud_inicio=gps.longitud,
        precision_gps_inicio_m=gps.precision_gps_m,
        estado_gps_inicio=gps.estado_gps,
        nota=nota.strip(),
        creado_por=actor.id,
        actualizado_por=actor.id,
    )
    repo_jornadas.crear(db, jornada)

    registrar_evento(
        db,
        accion="jornada.inicio",
        modulo="jornadas",
        actor_usuario_id=actor.id,
        entidad_tipo="jornada",
        entidad_id=jornada.id,
    )
    db.commit()
    db.refresh(jornada)
    return jornada


def cerrar(
    db: Session, *, uuid, fin_en: datetime, gps: GpsPeticion | None, nota_fin: str, actor: Usuario
) -> Jornada:
    jornada = repo_jornadas.obtener_por_uuid(db, uuid)
    if jornada is None or jornada.usuario_id != actor.id:
        raise JornadaNoEncontradaError(f"Jornada desconocida: {uuid}")

    if jornada.estado == "CERRADA":
        return jornada  # cerrar una jornada ya cerrada es idempotente

    if fin_en < jornada.inicio_en:
        raise RangoFechasInvalidoError("fin_en no puede ser anterior a inicio_en.")

    if not nota_fin or not nota_fin.strip():
        raise DetalleRequeridoError("El detalle de cierre de jornada es obligatorio.")

    gps = gps or GpsPeticion()
    jornada.estado = "CERRADA"
    jornada.fin_en = fin_en
    jornada.latitud_fin = gps.latitud
    jornada.longitud_fin = gps.longitud
    jornada.precision_gps_fin_m = gps.precision_gps_m
    jornada.estado_gps_fin = gps.estado_gps
    jornada.nota_fin = nota_fin.strip()
    jornada.actualizado_por = actor.id

    db.add(jornada)
    registrar_evento(
        db,
        accion="jornada.cierre",
        modulo="jornadas",
        actor_usuario_id=actor.id,
        entidad_tipo="jornada",
        entidad_id=jornada.id,
    )
    db.commit()
    db.refresh(jornada)
    return jornada


def listar(db: Session, *, usuario_id: int, fecha=None) -> list[Jornada]:
    return repo_jornadas.listar_de_usuario(db, usuario_id=usuario_id, fecha=fecha)


def obtener_de_hoy(db: Session, *, usuario_id: int) -> Jornada | None:
    hoy = _fecha_local(datetime.now(ZONA_MVP))
    return repo_jornadas.obtener_abierta_del_dia(db, usuario_id=usuario_id, fecha=hoy)
