"""Lógica de negocio de autenticación — ECA-003.

Login, refresh (con rotación), logout (revocación) y cambio de contraseña.
Los routers (`app/api/routers/auth.py`) son delgados: validan forma con
Pydantic y delegan aquí toda decisión.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import (
    RefrescoGenerado,
    crear_access_token,
    extraer_jti_de_refresh_token,
    generar_refresh_token,
    hash_contrasena,
    hash_refresh_token,
    validar_fortaleza_contrasena,
    verificar_contrasena,
)
from app.models.usuario import Usuario
from app.repositories import usuarios as repo


class CredencialesInvalidasError(Exception):
    """Correo/contraseña no coinciden, o el usuario no existe."""


class UsuarioNoAutorizadoError(Exception):
    """El usuario existe y la contraseña es correcta, pero su `estado` no permite login."""


class RefreshTokenInvalidoError(Exception):
    """El refresh token no existe, ya fue revocado, o expiró."""


def _emitir_par_de_tokens(
    db: Session, usuario: Usuario, *, user_agent: str | None = None, ip_hash: str | None = None
) -> tuple[str, RefrescoGenerado, datetime]:
    access_token, expira_en = crear_access_token(usuario.id)
    refresco = generar_refresh_token()
    repo.crear_token_refresco(
        db,
        usuario_id=usuario.id,
        jti=refresco.jti,
        hash_token=refresco.hash_token,
        expira_en=refresco.expira_en,
        user_agent=user_agent,
        ip_hash=ip_hash,
    )
    return access_token, refresco, expira_en


def login(
    db: Session, *, correo: str, contrasena: str, user_agent: str | None = None
) -> tuple[str, str, datetime]:
    usuario = repo.obtener_por_correo(db, correo)
    if usuario is None or not verificar_contrasena(contrasena, usuario.contrasena_hash):
        raise CredencialesInvalidasError("Correo o contraseña incorrectos.")
    if not usuario.esta_activo:
        raise UsuarioNoAutorizadoError(f"El usuario está en estado {usuario.estado}.")

    access_token, refresco, expira_en = _emitir_par_de_tokens(db, usuario, user_agent=user_agent)
    usuario.ultimo_acceso_en = datetime.now(timezone.utc)
    db.add(usuario)
    db.commit()
    return access_token, refresco.token_en_claro, expira_en


def refrescar(
    db: Session, *, refresh_token: str, user_agent: str | None = None
) -> tuple[str, str, datetime]:
    jti = extraer_jti_de_refresh_token(refresh_token)
    token_guardado = repo.obtener_token_refresco_por_jti(db, jti) if jti else None

    if token_guardado is None or token_guardado.hash_token != hash_refresh_token(refresh_token):
        raise RefreshTokenInvalidoError("Refresh token desconocido.")
    if token_guardado.esta_revocado:
        raise RefreshTokenInvalidoError("Refresh token revocado.")
    if token_guardado.expira_en < datetime.now(timezone.utc):
        raise RefreshTokenInvalidoError("Refresh token expirado.")

    usuario = repo.obtener_por_id(db, token_guardado.usuario_id)
    if usuario is None or not usuario.esta_activo:
        raise RefreshTokenInvalidoError("El usuario ya no puede autenticarse.")

    # Rotación: el refresh usado queda revocado y se emite un par nuevo.
    repo.revocar_token_refresco(db, token_guardado, motivo="ROTACION")
    access_token, refresco, expira_en = _emitir_par_de_tokens(db, usuario, user_agent=user_agent)
    db.commit()
    return access_token, refresco.token_en_claro, expira_en


def logout(db: Session, *, refresh_token: str) -> None:
    jti = extraer_jti_de_refresh_token(refresh_token)
    token_guardado = repo.obtener_token_refresco_por_jti(db, jti) if jti else None
    if token_guardado is None or token_guardado.hash_token != hash_refresh_token(refresh_token):
        # Logout es idempotente desde el punto de vista del cliente: un
        # token ya inválido/desconocido no es un error a reportar.
        return
    if not token_guardado.esta_revocado:
        repo.revocar_token_refresco(db, token_guardado, motivo="LOGOUT")
        db.commit()


def cambiar_contrasena(
    db: Session, *, usuario: Usuario, contrasena_actual: str, contrasena_nueva: str
) -> None:
    if not verificar_contrasena(contrasena_actual, usuario.contrasena_hash):
        raise CredencialesInvalidasError("La contraseña actual no es correcta.")
    validar_fortaleza_contrasena(contrasena_nueva)

    usuario.contrasena_hash = hash_contrasena(contrasena_nueva)
    usuario.requiere_cambio_contrasena = False
    db.add(usuario)
    # Cambiar la contraseña revoca todas las sesiones existentes: si la
    # cuenta estaba comprometida, el atacante pierde acceso de inmediato.
    repo.revocar_todos_los_tokens_de(db, usuario.id, motivo="SEGURIDAD")
    db.commit()
