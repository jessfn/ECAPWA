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

# Extensión con la que se guarda cada tipo de imagen conocido. Sirve tanto
# para el nombre en storage como para responder el `media_type` correcto al
# descargar.
MIME_PERMITIDOS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heif",
    "image/gif": "gif",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
}
# Pedido explícito (2026-09-09, reiterado): "que no exista límite en las
# imágenes... cada imagen no tenga límite en lo que pese". Ya NO se rechaza
# una evidencia por tamaño — Nginx también se puso en `client_max_body_size
# 0` (ilimitado) para este sitio, así que no hay corte por peso en ninguna
# capa.


def _sniff_imagen(contenido: bytes) -> tuple[str, str] | None:
    """Detecta el tipo real de imagen por sus "magic bytes" (la firma del
    archivo), no por el MIME que declara el cliente — pedido explícito
    (2026-09-08): algunas fotos NO se subían.

    Causa: cuando el navegador del celular no puede decodificar la foto
    (típico con HEIC de iPhone en Android, o un archivo cuyo `.type` llega
    vacío), `CapturaEvidencia.vue` sube el ORIGINAL sin comprimir; el MIME
    que entonces llega es a menudo `application/octet-stream` (vacío) o uno
    equivocado, y la lista blanca estricta lo rechazaba — la evidencia se
    perdía y la actividad quedaba "Sin fotos". Mirar los bytes es fiable
    aunque el MIME venga mal o vacío."""
    b = contenido[:32]
    if b[:3] == b"\xff\xd8\xff":
        return ("image/jpeg", "jpg")
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return ("image/png", "png")
    if b[:6] in (b"GIF87a", b"GIF89a"):
        return ("image/gif", "gif")
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return ("image/webp", "webp")
    if b[:2] == b"BM":
        return ("image/bmp", "bmp")
    if b[:4] in (b"II*\x00", b"MM\x00*"):
        return ("image/tiff", "tiff")
    # HEIC/HEIF (contenedor ISO-BMFF): 'ftyp' en el offset 4, luego la marca.
    if b[4:8] == b"ftyp":
        marca = b[8:12]
        if marca in (b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"hevm", b"hevs"):
            return ("image/heic", "heic")
        if marca in (b"mif1", b"msf1", b"heif"):
            return ("image/heif", "heif")
    return None


def _resolver_tipo(contenido: bytes, mime_declarado: str) -> tuple[str, str]:
    """Decide con qué (mime, extensión) guardar la evidencia. Los BYTES
    mandan sobre el MIME declarado; si no se reconoce la firma pero el
    cliente asegura que es una imagen (`image/*`), se acepta igual — así
    una foto nunca se pierde por un MIME raro. Solo se rechaza contenido
    que ni tiene firma de imagen ni se declara como imagen (p. ej. un PDF).

    Devuelve `(mime, extension)` o levanta `MimeNoPermitidoError`."""
    sniff = _sniff_imagen(contenido)
    if sniff is not None:
        return sniff
    if mime_declarado in MIME_PERMITIDOS:
        return (mime_declarado, MIME_PERMITIDOS[mime_declarado])
    if (mime_declarado or "").startswith("image/"):
        # Dice ser imagen pero no reconocimos la firma: se acepta con una
        # extensión genérica antes que perder la evidencia.
        return (mime_declarado, "img")
    raise MimeNoPermitidoError(f"Tipo de archivo no permitido: {mime_declarado or 'desconocido'}")


class ActividadAjenaError(Exception):
    pass


class OrdenInvalidoError(ValueError):
    pass


class MimeNoPermitidoError(ValueError):
    pass


class ArchivoDemasiadoGrandeError(ValueError):
    pass


class ArchivoVacioError(ValueError):
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
    # El tipo real lo dan los bytes (el MIME declarado suele venir mal o
    # vacío desde el celular); `mime`/`extension` finales salen de aquí.
    mime, extension = _resolver_tipo(contenido, mime)
    # Sin límite de tamaño (pedido explícito). Se conserva la validación de
    # que el archivo no venga VACÍO — un archivo de 0 bytes no es una foto y
    # es señal de un blob corrupto en el cliente; mejor rechazarlo con un
    # mensaje claro que guardar un archivo inservible.
    if not contenido:
        raise ArchivoVacioError("El archivo llegó vacío (0 bytes).")

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

    clave = _clave_de(actividad.id, uuid, extension)
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
