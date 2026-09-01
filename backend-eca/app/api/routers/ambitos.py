"""Router de ámbitos geográficos de técnico — ECA-008.

Rutas bajo `/usuarios/{id}/ambito` y `/usuarios/me/ambito` (no bajo
`/ambitos`, salvo la importación masiva) porque un ámbito no existe sin un
técnico dueño — ver `docs-eca/06_PLAN_IMPLEMENTACION_ECA.md` ticket ECA-008.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.permissions import require_permission
from app.models.usuario import Usuario
from app.repositories import usuarios as repo_usuarios
from app.schemas.ambito import AmbitoReemplazarPeticion, ImportarAmbitosRespuesta, MunicipioDelAmbito
from app.services import ambitos_service
from app.services.importacion_ambitos_service import importar_ambitos

router = APIRouter(tags=["ambitos"])


@router.get("/usuarios/me/ambito", response_model=list[MunicipioDelAmbito])
def obtener_mi_ambito(
    db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)
) -> list[MunicipioDelAmbito]:
    return ambitos_service.obtener_ambito(db, usuario.id)


@router.get("/usuarios/{usuario_id}/ambito", response_model=list[MunicipioDelAmbito])
def obtener_ambito(
    usuario_id: int,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("ambitos.gestionar")),
) -> list[MunicipioDelAmbito]:
    if repo_usuarios.obtener_por_id(db, usuario_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    return ambitos_service.obtener_ambito(db, usuario_id)


@router.put("/usuarios/{usuario_id}/ambito", response_model=list[MunicipioDelAmbito])
def reemplazar_ambito(
    usuario_id: int,
    peticion: AmbitoReemplazarPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("ambitos.gestionar")),
) -> list[MunicipioDelAmbito]:
    if repo_usuarios.obtener_por_id(db, usuario_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    try:
        return ambitos_service.reemplazar_ambito(
            db, usuario_id=usuario_id, municipio_ids=peticion.municipio_ids, actor=actor
        )
    except ambitos_service.MunicipioDesconocidoError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except ambitos_service.MunicipioInactivoError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.post("/ambitos/importar", response_model=ImportarAmbitosRespuesta)
async def importar_ambitos_csv(
    archivo: UploadFile,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("ambitos.gestionar")),
) -> ImportarAmbitosRespuesta:
    contenido = (await archivo.read()).decode("utf-8-sig")
    try:
        return importar_ambitos(db, contenido_csv=contenido, actor=actor)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
