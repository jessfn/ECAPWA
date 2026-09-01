"""Router `/auth` — ECA-003.

Login, refresh (con rotación), logout, `GET /auth/me`, cambio de contraseña.
Delgado a propósito: toda decisión de negocio vive en
`app/services/auth_service.py`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.permissions import resolver_permisos_efectivos
from app.core.ratelimit import limitar
from app.core.security import ContrasenaDebilError
from app.models.usuario import Usuario
from app.schemas.auth import (
    CambioContrasenaPeticion,
    LoginPeticion,
    LogoutPeticion,
    MeRespuesta,
    RefreshPeticion,
    TokenRespuesta,
)
from app.services import auth_service, usuarios_service

router = APIRouter(prefix="/auth", tags=["auth"])

# Límites deliberadamente laxos para no estorbar el uso real (un técnico
# que se equivoca de contraseña dos veces), pero suficientes para frenar
# fuerza bruta básica — ver docstring de `app/core/ratelimit.py`.
_limite_login = limitar(nombre="auth.login", limite=10, ventana_seg=60)
_limite_refresh = limitar(nombre="auth.refresh", limite=20, ventana_seg=60)


@router.post("/login", response_model=TokenRespuesta, dependencies=[Depends(_limite_login)])
def login(peticion: LoginPeticion, request: Request, db: Session = Depends(get_db)) -> TokenRespuesta:
    try:
        access_token, refresh_token, expira_en = auth_service.login(
            db,
            correo=peticion.correo,
            contrasena=peticion.contrasena,
            user_agent=request.headers.get("user-agent"),
        )
    except (auth_service.CredencialesInvalidasError, auth_service.UsuarioNoAutorizadoError) as exc:
        # Mismo mensaje/código para credenciales inexistentes y estado no
        # autorizado: no se filtra si el correo existe o no.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos.") from exc

    return TokenRespuesta(access_token=access_token, refresh_token=refresh_token, expira_en=expira_en)


@router.post("/refresh", response_model=TokenRespuesta, dependencies=[Depends(_limite_refresh)])
def refrescar(
    peticion: RefreshPeticion, request: Request, db: Session = Depends(get_db)
) -> TokenRespuesta:
    try:
        access_token, refresh_token, expira_en = auth_service.refrescar(
            db,
            refresh_token=peticion.refresh_token,
            user_agent=request.headers.get("user-agent"),
        )
    except auth_service.RefreshTokenInvalidoError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token inválido.") from exc

    return TokenRespuesta(access_token=access_token, refresh_token=refresh_token, expira_en=expira_en)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(peticion: LogoutPeticion, db: Session = Depends(get_db)) -> None:
    auth_service.logout(db, refresh_token=peticion.refresh_token)


@router.get("/me", response_model=MeRespuesta)
def me(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)) -> MeRespuesta:
    permisos = sorted(resolver_permisos_efectivos(db, usuario.id))
    return MeRespuesta(usuario=usuarios_service.a_publico(db, usuario), permisos=permisos)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def cambiar_contrasena(
    peticion: CambioContrasenaPeticion,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        auth_service.cambiar_contrasena(
            db,
            usuario=usuario,
            contrasena_actual=peticion.contrasena_actual,
            contrasena_nueva=peticion.contrasena_nueva,
        )
    except auth_service.CredencialesInvalidasError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "La contraseña actual no es correcta.") from exc
    except ContrasenaDebilError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
