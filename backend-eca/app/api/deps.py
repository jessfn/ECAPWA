"""Dependencias FastAPI de autenticación — ECA-003."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import TokenInvalidoError, decodificar_access_token
from app.models.usuario import Usuario
from app.repositories import usuarios as repo

_esquema_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_esquema_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if credenciales is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Se requiere autenticación.")

    try:
        usuario_id = decodificar_access_token(credenciales.credentials)
    except TokenInvalidoError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o expirado.") from exc

    usuario = repo.obtener_por_id(db, usuario_id)
    if usuario is None or not usuario.esta_activo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "El usuario no puede autenticarse.")

    return usuario
