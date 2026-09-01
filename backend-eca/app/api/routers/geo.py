"""Router `/geo` — ECA-006.

Lectura: cualquier usuario autenticado. Edición (solo `activo`): permiso
`geo.gestionar`. Estado y municipio nunca son texto libre en ninguna otra
parte del sistema (`03_MODELO_NEGOCIO_ECA_ACTUALIZADO.md` §6.2) — todo lo
que los referencia (ECA, ámbitos de técnico, ...) usa `estado_id`/
`municipio_id` hacia estas tablas.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.permissions import require_permission
from app.models.usuario import Usuario
from app.repositories import geo as repo_geo
from app.schemas.geo import ActivoPeticion, EstadoPublico, MunicipioPublico

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/estados", response_model=list[EstadoPublico])
def listar_estados(
    activo: bool | None = None,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
) -> list[EstadoPublico]:
    return repo_geo.listar_estados(db, solo_activos=bool(activo))


@router.get("/municipios", response_model=list[MunicipioPublico])
def listar_municipios(
    estado_id: int | None = None,
    activo: bool | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_current_user),
) -> list[MunicipioPublico]:
    if estado_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "El filtro estado_id es obligatorio para listar municipios."
        )
    return repo_geo.listar_municipios(db, estado_id=estado_id, solo_activos=bool(activo), texto=q)


@router.patch("/estados/{estado_id}", response_model=EstadoPublico)
def actualizar_estado(
    estado_id: int,
    peticion: ActivoPeticion,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("geo.gestionar")),
) -> EstadoPublico:
    estado = repo_geo.obtener_estado(db, estado_id)
    if estado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estado no encontrado.")
    estado.activo = peticion.activo
    db.add(estado)
    db.commit()
    db.refresh(estado)
    return estado


@router.patch("/municipios/{municipio_id}", response_model=MunicipioPublico)
def actualizar_municipio(
    municipio_id: int,
    peticion: ActivoPeticion,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("geo.gestionar")),
) -> MunicipioPublico:
    municipio = repo_geo.obtener_municipio(db, municipio_id)
    if municipio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Municipio no encontrado.")
    municipio.activo = peticion.activo
    db.add(municipio)
    db.commit()
    db.refresh(municipio)
    return municipio
