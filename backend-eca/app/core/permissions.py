"""Autorización por permiso — ECA-004.

`require_permission("clave")` es la única forma en la que un endpoint debe
proteger un recurso: corrige `docs-eca/02_INVENTARIO_TECNICO.md` §6 (en
Sembrando Vida la autorización vive 100 % en el cliente). Nunca confiar en
lo que la PWA/el panel decidan mostrar u ocultar.

La resolución en sí vive en `app/repositories/rbac.py` (capa de datos), no
aquí: este módulo es la fábrica de dependencias FastAPI que la usa.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.usuario import Usuario
from app.repositories import rbac as repo_rbac


def resolver_permisos_efectivos(db: Session, usuario_id: int) -> set[str]:
    return repo_rbac.permisos_efectivos_de(db, usuario_id)


def require_permission(clave: str):
    """Fábrica de dependencia FastAPI: 403 si el usuario actual no tiene `clave`."""

    def _dependencia(
        usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> Usuario:
        permisos = repo_rbac.permisos_efectivos_de(db, usuario.id)
        if clave not in permisos:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"No tienes el permiso requerido: {clave}."
            )
        return usuario

    return _dependencia
