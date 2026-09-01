"""Lógica de negocio de evidencias fotográficas — ECA-015.

**Alcance de este ticket** (ver `Comportamiento offline` en el propio
ticket): la subida es siempre online, justo después de crear la actividad.
La regla completa de `min_fotos` (bloquear una actividad como "incompleta"
si le faltan evidencias) depende de una señal de "esto ya se terminó de
enviar" que hoy no existe — llega con `POST /sync/push` en ECA-016/017.
Aquí solo se implementa el mecanismo de subida/almacenamiento/descarga;
exigir el mínimo se deja para cuando exista esa señal, documentado como
alcance explícitamente diferido (no un olvido).
"""
from __future__ import annotations

import hashlib
import uuid as uuid_lib
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.core.storage import Storage
from app.models.actividad import Actividad
from app.models.evidencia import ActividadEvidencia
from app.models.usuario import Usuario
from app.repositories import evidencias as repo_evidencias

MIME_PERMITIDOS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
TAMANO_MAXIMO_BYTES = 8 * 1024 * 1024  # respaldo del servidor; el cliente comprime a ~500 KB


class ActividadAjenaError(Exception):
    pass


class OrdenInvalidoError(ValueError):
    pass


class MimeNoPermitidoError(ValueError):
    pass


class ArchivoDemasiadoGrandeError(ValueError):
    pass


def _clave_de(actividad_id: int, evidencia_uuid: uuid_lib.UUID, extension: str) -> str:
    return f"actividades/{actividad_id}/{evidencia_uuid}.{extension}"


def subir(
    db: Session,
    *,
    actividad: Actividad,
    uuid: uuid_lib.UUID,
    orden: int,
    contenido: bytes,
    nombre_archivo: str,
    mime: str,
    latitud: float | None,
    longitud: float | None,
    capturada_en: datetime | None,
    actor: Usuario,
    storage: Storage,
) -> ActividadEvidencia:
    if actividad.usuario_id != actor.id:
        raise ActividadAjenaError("No puedes subir evidencias a una actividad de otro técnico.")

    existente = repo_evidencias.obtener_por_uuid(db, uuid)
    if existente is not None:
        return existente  # idempotente por uuid (reintento de subida)

    if not (1 <= orden <= 3):
        raise OrdenInvalidoError("orden debe estar entre 1 y 3.")
    if mime not in MIME_PERMITIDOS:
        raise MimeNoPermitidoError(f"Tipo de archivo no permitido: {mime}")
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise ArchivoDemasiadoGrandeError("El archivo excede el tamaño máximo permitido.")

    hash_sha256 = hashlib.sha256(contenido).hexdigest()

    por_hash = repo_evidencias.obtener_por_hash(db, actividad_id=actividad.id, hash_sha256=hash_sha256)
    if por_hash is not None:
        return por_hash  # idempotente por (actividad_id, hash_sha256): mismo archivo ya subido

    # Reemplazo: ya hay una evidencia en ese `orden` pero con contenido
    # distinto (el técnico volvió a tomar la foto) — se sustituye en vez de
    # fallar por la restricción UNIQUE(actividad_id, orden).
    previa_en_orden = next(
        (e for e in repo_evidencias.listar_de_actividad(db, actividad.id) if e.orden == orden), None
    )
    if previa_en_orden is not None:
        storage.eliminar(previa_en_orden.storage_clave)
        repo_evidencias.eliminar(db, previa_en_orden)
        db.flush()

    clave = _clave_de(actividad.id, uuid, MIME_PERMITIDOS[mime])
    storage.guardar(clave, contenido)

    evidencia = ActividadEvidencia(
        uuid=uuid,
        actividad_id=actividad.id,
        orden=orden,
        storage_clave=clave,
        nombre_archivo=nombre_archivo,
        mime=mime,
        tamano_bytes=len(contenido),
        hash_sha256=hash_sha256,
        latitud=latitud,
        longitud=longitud,
        capturada_en=capturada_en,
    )
    repo_evidencias.crear(db, evidencia)

    registrar_evento(
        db,
        accion="evidencia.alta",
        modulo="evidencias",
        actor_usuario_id=actor.id,
        entidad_tipo="actividad_evidencia",
        entidad_id=evidencia.id,
        entidad_uuid=evidencia.uuid,
    )
    db.commit()
    db.refresh(evidencia)
    return evidencia


def eliminar(db: Session, *, evidencia: ActividadEvidencia, actor: Usuario, storage: Storage) -> None:
    storage.eliminar(evidencia.storage_clave)
    repo_evidencias.eliminar(db, evidencia)
    registrar_evento(
        db,
        accion="evidencia.baja",
        modulo="evidencias",
        actor_usuario_id=actor.id,
        entidad_tipo="actividad_evidencia",
        entidad_id=evidencia.id,
        entidad_uuid=evidencia.uuid,
    )
    db.commit()
