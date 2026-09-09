"""Router de evidencias fotográficas — ECA-015.

Subida bajo `/actividades/{actividad_uuid}/evidencias` (no existe una
evidencia sin actividad dueña, mismo criterio que ámbitos en ECA-008);
descarga y borrado bajo `/evidencias/{id}`. La descarga nunca es estática
pública: siempre pasa por autenticación y verificación de permiso aquí.

**Desviación del ticket**: pide "Borrar: `actividades.ver_todas` + permiso
de gestión", pero no existe un `evidencias.gestionar` sembrado en RBAC
(ECA-004) y crear uno solo para esto sería sobreingeniería para el
piloto — se gatea únicamente con `actividades.ver_todas` (hoy solo
`ADMIN`).
"""
from __future__ import annotations

import logging
import uuid as uuid_lib
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.permissions import require_permission, resolver_permisos_efectivos
from app.core.storage import Storage, get_storage
from app.models.evidencia import ActividadEvidencia
from app.models.usuario import Usuario
from app.repositories import actividades as repo_actividades
from app.repositories import evidencias as repo_evidencias
from app.schemas.evidencia import EvidenciaPublica
from app.services import evidencias_service

logger = logging.getLogger("app.evidencias")

router = APIRouter(tags=["evidencias"])

_ERRORES_422 = (
    evidencias_service.OrdenInvalidoError,
    evidencias_service.MimeNoPermitidoError,
    evidencias_service.ArchivoDemasiadoGrandeError,
    evidencias_service.ArchivoVacioError,
)


def _a_float(valor: str | None) -> float | None:
    """Parseo tolerante: la latitud/longitud llegan como campo de formulario
    (texto). Antes se declaraban `float | None` y una cadena vacía o mal
    formada provocaba un 422 de validación de FastAPI ANTES de entrar al
    endpoint — un modo de falla que dejaba la evidencia atorada. Aquí se
    aceptan como texto y se parsean con tolerancia: vacío/None/ilegible ->
    None, nunca un error."""
    if valor is None:
        return None
    valor = valor.strip()
    if not valor:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _a_datetime(valor: str | None) -> datetime | None:
    if valor is None:
        return None
    valor = valor.strip()
    if not valor:
        return None
    try:
        # Acepta el ISO de `Date.toISOString()` (con o sin 'Z').
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _a_orden(valor: str | None) -> int:
    """`orden` tolerante: si llega vacío/ilegible, cae a 1 (la validación de
    rango 1..3 la sigue haciendo el servicio)."""
    if valor is None:
        return 1
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return 1


@router.post(
    "/actividades/{actividad_uuid}/evidencias",
    response_model=EvidenciaPublica,
    status_code=status.HTTP_201_CREATED,
)
async def subir_evidencia(
    actividad_uuid: uuid_lib.UUID,
    archivo: UploadFile,
    uuid: uuid_lib.UUID = Form(...),
    # `orden`, `latitud`, `longitud` y `capturada_en` se reciben como TEXTO y
    # se parsean con tolerancia (ver helpers arriba) — declararlos con tipo
    # estricto hacía que un valor vacío/mal formado del celular reventara con
    # un 422 de validación de FastAPI antes de entrar aquí, dejando la
    # evidencia atorada para siempre.
    orden: str | None = Form(default=None),
    latitud: str | None = Form(default=None),
    longitud: str | None = Form(default=None),
    capturada_en: str | None = Form(default=None),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    actor: Usuario = Depends(require_permission("actividades.crear")),
) -> EvidenciaPublica:
    actividad = repo_actividades.obtener_por_uuid(db, actividad_uuid)
    if actividad is None or actividad.eliminado_en is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Actividad no encontrada.")

    contenido = await archivo.read()
    try:
        evidencia = evidencias_service.subir(
            db,
            actividad=actividad,
            uuid=uuid,
            orden=_a_orden(orden),
            contenido=contenido,
            nombre_archivo=archivo.filename or "evidencia",
            mime=archivo.content_type or "application/octet-stream",
            latitud=_a_float(latitud),
            longitud=_a_float(longitud),
            capturada_en=_a_datetime(capturada_en),
            actor=actor,
            storage=storage,
        )
    except evidencias_service.ActividadAjenaError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except _ERRORES_422 as exc:
        # Antes esto era invisible en los logs (solo se veía "422" en el
        # access log, sin el motivo) — diagnosticar una evidencia rechazada
        # exigía adivinar o entrar por SSH a cruzar contra la base de datos.
        # Con el motivo y el tamaño real del archivo en el log, se ve de
        # inmediato en `journalctl -u apieca` por qué se rechazó cada una.
        logger.warning(
            "evidencia rechazada: actividad=%s uuid=%s orden=%s mime_declarado=%s tamano_bytes=%s motivo=%s",
            actividad_uuid,
            uuid,
            orden,
            archivo.content_type,
            len(contenido),
            exc,
        )
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return EvidenciaPublica.model_validate(evidencia)


def _puede_ver(db: Session, evidencia: ActividadEvidencia, actor: Usuario) -> bool:
    actividad = repo_actividades.obtener_por_id(db, evidencia.actividad_id)
    if actividad is None:
        return False
    permisos = resolver_permisos_efectivos(db, actor.id)
    if actividad.usuario_id == actor.id:
        return "actividades.ver_propias" in permisos or "actividades.ver_todas" in permisos
    return "actividades.ver_todas" in permisos


@router.get("/evidencias/{evidencia_id}")
def descargar_evidencia(
    evidencia_id: int,
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    actor: Usuario = Depends(get_current_user),
) -> Response:
    evidencia = repo_evidencias.obtener_por_id(db, evidencia_id)
    if evidencia is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidencia no encontrada.")
    if not _puede_ver(db, evidencia, actor):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para ver esta evidencia.")

    contenido = storage.leer(evidencia.storage_clave)
    return Response(content=contenido, media_type=evidencia.mime)


@router.delete("/evidencias/{evidencia_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def eliminar_evidencia(
    evidencia_id: int,
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    actor: Usuario = Depends(require_permission("actividades.ver_todas")),
) -> None:
    evidencia = repo_evidencias.obtener_por_id(db, evidencia_id)
    if evidencia is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidencia no encontrada.")
    evidencias_service.eliminar(db, evidencia=evidencia, actor=actor, storage=storage)
