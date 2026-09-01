"""Motor de sincronización (push) — ECA-017.

Reutiliza `jornadas_service`/`actividades_service` (misma validación e
idempotencia por `uuid` que ya usan los endpoints online de ECA-012/013),
en vez de reimplementar las reglas de negocio aquí. Este módulo solo añade
lo propio del *transporte*: nunca levanta una excepción por un objeto malo
— cada uno se resuelve a `APLICADO`/`DUPLICADO`/`RECHAZADO` y el resto del
lote se sigue procesando (criterio de aceptación del ticket).

**Interpretación del "conflicto simple" del ticket**: el ticket dice que
una jornada ya existente por `uuid` es `DUPLICADO` sin más detalle, pero
una jornada puede llegar primero como "inicio" (sin `fin_en`) y en un push
posterior como "cierre" (mismo `uuid`, ahora con `fin_en`) — a diferencia
de una actividad, que sí es inmutable tras sincronizarse. Aquí: si la
jornada ya existe y el push trae `fin_en` nuevo sobre una jornada aún
`ABIERTA`, se aplica el cierre (`APLICADO`); si no hay nada nuevo que
aplicar, es `DUPLICADO`.
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.dispositivo import Dispositivo
from app.models.usuario import Usuario
from app.repositories import actividades as repo_actividades
from app.repositories import dispositivos as repo_dispositivos
from app.repositories import jornadas as repo_jornadas
from app.schemas.sync import ActividadSyncItem, JornadaSyncItem, ResultadoSync
from app.services import actividades_service, jornadas_service

APLICADO = "APLICADO"
DUPLICADO = "DUPLICADO"
RECHAZADO = "RECHAZADO"

_ERRORES_ACTIVIDAD = (
    actividades_service.JornadaDesconocidaError,
    actividades_service.TipoActividadDesconocidoError,
    actividades_service.EcaRequeridaError,
    actividades_service.ParticipantesNoPermitidosError,
    actividades_service.SubtemaIncoherenteError,
    actividades_service.GpsInvalidoError,
)


def registrar_dispositivo(
    db: Session, *, uuid: uuid_lib.UUID, plataforma: str | None, user_agent: str | None, actor: Usuario
) -> Dispositivo:
    dispositivo = repo_dispositivos.obtener_por_uuid(db, uuid)
    if dispositivo is not None:
        dispositivo.plataforma = plataforma
        dispositivo.user_agent = user_agent
        dispositivo.actualizado_en = datetime.now(timezone.utc)
        db.add(dispositivo)
    else:
        dispositivo = Dispositivo(uuid=uuid, usuario_id=actor.id, plataforma=plataforma, user_agent=user_agent)
        repo_dispositivos.crear(db, dispositivo)
    db.commit()
    db.refresh(dispositivo)
    return dispositivo


def _obtener_o_crear_dispositivo(db: Session, dispositivo_uuid: uuid_lib.UUID, actor: Usuario) -> Dispositivo:
    dispositivo = repo_dispositivos.obtener_por_uuid(db, dispositivo_uuid)
    if dispositivo is None:
        # El dispositivo debería registrarse antes vía `POST /sync/dispositivo`,
        # pero un push nunca debe fallar por eso: se registra sobre la marcha
        # con datos mínimos.
        dispositivo = Dispositivo(uuid=dispositivo_uuid, usuario_id=actor.id)
        repo_dispositivos.crear(db, dispositivo)
        db.commit()
        db.refresh(dispositivo)
    return dispositivo


def _procesar_jornada(db: Session, item: JornadaSyncItem, *, dispositivo: Dispositivo, actor: Usuario) -> ResultadoSync:
    ahora = datetime.now(item.inicio_en.tzinfo)
    existente = repo_jornadas.obtener_por_uuid(db, item.uuid)

    if existente is None:
        try:
            jornada = jornadas_service.iniciar(
                db, uuid=item.uuid, inicio_en=item.inicio_en, gps=item.gps_inicio, actor=actor
            )
        except Exception as exc:  # nunca 500 por un objeto malo
            return ResultadoSync(uuid=item.uuid, resultado=RECHAZADO, error=str(exc))

        if jornada.uuid != item.uuid:
            # Cayó en la deduplicación "una jornada principal por día" de
            # `jornadas_service.iniciar` contra OTRA jornada ya existente
            # ese día — no es el mismo objeto que se mandó a sincronizar.
            return ResultadoSync(uuid=item.uuid, resultado=RECHAZADO, error="Ya existe otra jornada ese día.")

        jornada.dispositivo_id = dispositivo.id
        jornada.creado_en_dispositivo = item.inicio_en
        jornada.sincronizado_en = ahora
        db.add(jornada)
        db.commit()
        existente = jornada
        resultado_base = APLICADO
    else:
        resultado_base = DUPLICADO

    if item.fin_en is not None and existente.estado == "ABIERTA":
        try:
            jornadas_service.cerrar(
                db, uuid=item.uuid, fin_en=item.fin_en, gps=item.gps_fin, actor=actor
            )
        except jornadas_service.JornadaNoEncontradaError as exc:
            return ResultadoSync(uuid=item.uuid, resultado=RECHAZADO, error=str(exc))
        except jornadas_service.RangoFechasInvalidoError as exc:
            return ResultadoSync(uuid=item.uuid, resultado=RECHAZADO, error=str(exc))
        return ResultadoSync(uuid=item.uuid, resultado=APLICADO, id=existente.id)

    return ResultadoSync(uuid=item.uuid, resultado=resultado_base, id=existente.id)


def _procesar_actividad(
    db: Session, item: ActividadSyncItem, *, dispositivo: Dispositivo, actor: Usuario
) -> ResultadoSync:
    existente = repo_actividades.obtener_por_uuid(db, item.uuid)
    if existente is not None:
        return ResultadoSync(uuid=item.uuid, resultado=DUPLICADO, id=existente.id)

    try:
        actividad = actividades_service.crear(
            db,
            uuid=item.uuid,
            jornada_uuid=item.jornada_uuid,
            eca_id=item.eca_id,
            modalidad_id=item.modalidad_id,
            tipo_actividad_id=item.tipo_actividad_id,
            tema_id=item.tema_id,
            subtema_id=item.subtema_id,
            sistema_productivo_id=item.sistema_productivo_id,
            descripcion=item.descripcion,
            resultado=item.resultado,
            fecha_hora=item.fecha_hora,
            num_participantes=item.num_participantes,
            requiere_seguimiento=item.requiere_seguimiento,
            fecha_proximo_seguimiento=item.fecha_proximo_seguimiento,
            actor=actor,
            gps=item.gps,
        )
    except _ERRORES_ACTIVIDAD as exc:
        return ResultadoSync(uuid=item.uuid, resultado=RECHAZADO, error=str(exc))
    except Exception as exc:  # defensa final: nunca 500 por un objeto malo
        return ResultadoSync(uuid=item.uuid, resultado=RECHAZADO, error=str(exc))

    ahora = datetime.now(item.fecha_hora.tzinfo)
    actividad.dispositivo_id = dispositivo.id
    actividad.creado_en_dispositivo = item.fecha_hora
    actividad.recibido_en = ahora
    actividad.sincronizado_en = ahora
    db.add(actividad)
    db.commit()

    return ResultadoSync(uuid=item.uuid, resultado=APLICADO, id=actividad.id)


def push(
    db: Session,
    *,
    dispositivo_uuid: uuid_lib.UUID,
    jornadas: list[JornadaSyncItem],
    actividades: list[ActividadSyncItem],
    actor: Usuario,
) -> list[ResultadoSync]:
    dispositivo = _obtener_o_crear_dispositivo(db, dispositivo_uuid, actor)

    resultados = [_procesar_jornada(db, item, dispositivo=dispositivo, actor=actor) for item in jornadas]
    # Actividades después de jornadas: una actividad puede depender de una
    # jornada que llega en el mismo lote (riesgo señalado por el ticket).
    resultados += [_procesar_actividad(db, item, dispositivo=dispositivo, actor=actor) for item in actividades]
    return resultados
