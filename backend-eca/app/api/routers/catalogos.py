"""Router `/catalogos` — ECA-010.

Lectura: cualquier usuario autenticado (por defecto solo `activo=true`;
`todos=true` para el panel). Edición: `catalogos.gestionar`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.permissions import require_permission
from app.models.usuario import Usuario
from app.repositories import catalogos as repo_catalogos
from app.models.catalogos import Subtema, TipoActividad
from app.schemas.catalogos import (
    CatalogoSimplePublico,
    SubtemaCrearPeticion,
    SubtemaPublico,
    TipoActividadEditarPeticion,
    TipoActividadPublico,
)
from app.services import catalogos_service

router = APIRouter(prefix="/catalogos", tags=["catalogos-actividad"])


@router.get("/modalidades", response_model=list[CatalogoSimplePublico])
def listar_modalidades(
    todos: bool = False,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
) -> list[CatalogoSimplePublico]:
    return repo_catalogos.listar_modalidades(db, solo_activos=not todos)


@router.get("/tipos-actividad", response_model=list[TipoActividadPublico])
def listar_tipos_actividad(
    todos: bool = False,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
) -> list[TipoActividadPublico]:
    return repo_catalogos.listar_tipos_actividad(db, solo_activos=not todos)


@router.get("/temas", response_model=list[CatalogoSimplePublico])
def listar_temas(
    todos: bool = False,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
) -> list[CatalogoSimplePublico]:
    return repo_catalogos.listar_temas(db, solo_activos=not todos)


@router.get("/subtemas", response_model=list[SubtemaPublico])
def listar_subtemas(
    tema_id: int | None = None,
    todos: bool = False,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
) -> list[SubtemaPublico]:
    return repo_catalogos.listar_subtemas(db, tema_id=tema_id, solo_activos=not todos)


@router.get("/sistemas-productivos", response_model=list[CatalogoSimplePublico])
def listar_sistemas_productivos(
    todos: bool = False,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
) -> list[CatalogoSimplePublico]:
    return repo_catalogos.listar_sistemas_productivos(db, solo_activos=not todos)


@router.post("/subtemas", response_model=SubtemaPublico, status_code=status.HTTP_201_CREATED)
def crear_subtema(
    peticion: SubtemaCrearPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("catalogos.gestionar")),
) -> SubtemaPublico:
    try:
        return catalogos_service.crear_subtema(
            db,
            tema_id=peticion.tema_id,
            clave=peticion.clave,
            nombre=peticion.nombre,
            orden=peticion.orden,
            actor=actor,
        )
    except catalogos_service.TemaInexistenteError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.patch("/{tipo}/{item_id}")
def editar_item(
    tipo: str,
    item_id: int,
    peticion: TipoActividadEditarPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("catalogos.gestionar")),
):
    """`TipoActividadEditarPeticion` es un superconjunto de `CatalogoEditarPeticion`
    (todos sus campos son opcionales); para catálogos que no son
    `tipos-actividad`, las banderas extra simplemente no se aplican —
    `actualizar_item` solo toca atributos que el modelo real tiene."""
    if tipo not in repo_catalogos.MODELOS_POR_TIPO:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Catálogo desconocido: {tipo}")

    item = repo_catalogos.obtener(db, tipo, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Elemento no encontrado.")

    try:
        item = catalogos_service.actualizar_item(
            db, tipo=tipo, item=item, cambios=peticion.model_dump(exclude_unset=True), actor=actor
        )
    except catalogos_service.RangoFotosInvalidoError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    if isinstance(item, TipoActividad):
        return TipoActividadPublico.model_validate(item)
    if isinstance(item, Subtema):
        return SubtemaPublico.model_validate(item)
    return CatalogoSimplePublico.model_validate(item)
