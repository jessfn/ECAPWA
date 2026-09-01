"""Router de solo lectura para los catálogos `roles`/`permisos` — ECA-004."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.permissions import require_permission
from app.models.usuario import Usuario
from app.repositories import rbac as repo_rbac
from app.schemas.rbac import PermisoPublico, RolPublico

router = APIRouter(tags=["catalogos"])


@router.get("/roles", response_model=list[RolPublico])
def listar_roles(
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("catalogos.ver")),
) -> list[RolPublico]:
    return [RolPublico.model_validate(r) for r in repo_rbac.listar_roles_activos(db)]


@router.get("/permisos", response_model=list[PermisoPublico])
def listar_permisos(
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("catalogos.ver")),
) -> list[PermisoPublico]:
    return [PermisoPublico.model_validate(p) for p in repo_rbac.listar_permisos_activos(db)]
