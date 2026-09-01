"""Router de asignaciones técnico↔ECA — ECA-009.

`GET /usuarios/me/ecas` es el endpoint que de verdad consumen la PWA y el
bootstrap: implementa la REGLA DE ECA completa (ver
`app/services/asignaciones_service.py`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.permissions import require_permission
from app.models.usuario import Usuario
from app.repositories import asignaciones as repo_asignaciones
from app.schemas.asignacion_eca import (
    AsignacionCrearPeticion,
    AsignacionPublica,
    EcaDelTecnico,
    ImportarAsignacionesRespuesta,
)
from app.services import asignaciones_service
from app.services.importacion_asignaciones_service import importar_asignaciones

router = APIRouter(tags=["asignaciones"])


@router.get("/usuarios/me/ecas", response_model=list[EcaDelTecnico])
def obtener_mis_ecas(
    db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)
) -> list[EcaDelTecnico]:
    return asignaciones_service.ecas_del_tecnico(db, usuario.id)


@router.get("/asignaciones", response_model=list[AsignacionPublica])
def listar_asignaciones(
    tecnico_id: int | None = None,
    eca_id: int | None = None,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("asignaciones.gestionar")),
) -> list[AsignacionPublica]:
    return repo_asignaciones.listar_activas(db, usuario_id=tecnico_id, eca_id=eca_id)


@router.post("/asignaciones", response_model=AsignacionPublica, status_code=status.HTTP_201_CREATED)
def crear_asignacion(
    peticion: AsignacionCrearPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("asignaciones.gestionar")),
) -> AsignacionPublica:
    try:
        return asignaciones_service.crear_asignacion(
            db, usuario_id=peticion.usuario_id, eca_id=peticion.eca_id, actor=actor
        )
    except asignaciones_service.AsignacionDuplicadaError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.delete("/asignaciones/{asignacion_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def eliminar_asignacion(
    asignacion_id: int,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("asignaciones.gestionar")),
) -> None:
    asignacion = repo_asignaciones.obtener_por_id(db, asignacion_id)
    if asignacion is None or not asignacion.activo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asignación no encontrada.")
    asignaciones_service.dar_de_baja_asignacion(db, asignacion=asignacion, actor=actor)


@router.post("/asignaciones/importar", response_model=ImportarAsignacionesRespuesta)
async def importar_asignaciones_csv(
    archivo: UploadFile,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("asignaciones.gestionar")),
) -> ImportarAsignacionesRespuesta:
    contenido = (await archivo.read()).decode("utf-8-sig")
    try:
        return importar_asignaciones(db, contenido_csv=contenido, actor=actor)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
