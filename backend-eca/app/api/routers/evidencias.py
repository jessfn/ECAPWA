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

router = APIRouter(tags=["evidencias"])

_ERRORES_422 = (
    evidencias_service.OrdenInvalidoError,
    evidencias_service.MimeNoPermitidoError,
    evidencias_service.ArchivoDemasiadoGrandeError,
)


@router.post(
    "/actividades/{actividad_uuid}/evidencias",
    response_model=EvidenciaPublica,
    status_code=status.HTTP_201_CREATED,
)
async def subir_evidencia(
    actividad_uuid: uuid_lib.UUID,
    archivo: UploadFile,
    uuid: uuid_lib.UUID = Form(...),
    orden: int = Form(...),
    latitud: float | None = Form(default=None),
    longitud: float | None = Form(default=None),
    capturada_en: datetime | None = Form(default=None),
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
            orden=orden,
            contenido=contenido,
            nombre_archivo=archivo.filename or "evidencia",
            mime=archivo.content_type or "application/octet-stream",
            latitud=latitud,
            longitud=longitud,
            capturada_en=capturada_en,
            actor=actor,
            storage=storage,
        )
    except evidencias_service.ActividadAjenaError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except _ERRORES_422 as exc:
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
