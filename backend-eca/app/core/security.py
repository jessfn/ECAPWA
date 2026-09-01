"""Primitivas de seguridad — ECA-003.

Hash de contraseñas (Argon2id), emisión/verificación de JWT de acceso, y
generación/hash de refresh tokens. Corrige `docs-eca/02_INVENTARIO_TECNICO.md`
§4/§20: Sembrando Vida guarda contraseñas en texto plano y emite JWT sin
expiración.

El refresh token es un secreto aleatorio de alta entropía (no una
contraseña elegida por un humano): se hashea con SHA-256 antes de guardarlo
(nunca Argon2, que es deliberadamente lento y no aporta nada aquí salvo
costo de CPU en cada `refresh`).
"""
from __future__ import annotations

import hashlib
import secrets
import uuid as uuid_lib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.settings import get_settings

_hasher = PasswordHasher()

ALGORITMO_JWT = "HS256"
LONGITUD_MINIMA_CONTRASENA = 10


class ContrasenaDebilError(ValueError):
    """La contraseña propuesta no cumple la política mínima."""


class TokenInvalidoError(Exception):
    """El JWT de acceso es inválido, está mal firmado o expiró."""


def hash_contrasena(contrasena_en_claro: str) -> str:
    return _hasher.hash(contrasena_en_claro)


def verificar_contrasena(contrasena_en_claro: str, contrasena_hash: str) -> bool:
    try:
        return _hasher.verify(contrasena_hash, contrasena_en_claro)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def validar_fortaleza_contrasena(contrasena: str) -> None:
    """Política mínima MVP: longitud + variedad de caracteres.

    No es el foco de ECA-003 (no hay lista de contraseñas filtradas ni
    zxcvbn); solo evita los casos obviamente débiles.
    """
    if len(contrasena) < LONGITUD_MINIMA_CONTRASENA:
        raise ContrasenaDebilError(
            f"La contraseña debe tener al menos {LONGITUD_MINIMA_CONTRASENA} caracteres."
        )
    tiene_letra = any(c.isalpha() for c in contrasena)
    tiene_numero = any(c.isdigit() for c in contrasena)
    if not (tiene_letra and tiene_numero):
        raise ContrasenaDebilError("La contraseña debe combinar letras y números.")


def crear_access_token(usuario_id: int) -> tuple[str, datetime]:
    """Devuelve `(jwt, expira_en)`. Siempre incluye `exp` (04 §6 / 02 §20)."""
    settings = get_settings()
    ahora = datetime.now(timezone.utc)
    expira_en = ahora + timedelta(minutes=settings.ACCESS_TOKEN_MIN)
    payload = {"sub": str(usuario_id), "iat": ahora, "exp": expira_en}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITMO_JWT)
    return token, expira_en


def decodificar_access_token(token: str) -> int:
    """Devuelve el `usuario_id` del token. Lanza `TokenInvalidoError` si no sirve."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITMO_JWT])
    except jwt.PyJWTError as exc:
        raise TokenInvalidoError(str(exc)) from exc
    try:
        return int(payload["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise TokenInvalidoError("Token sin `sub` válido.") from exc


@dataclass(frozen=True)
class RefrescoGenerado:
    token_en_claro: str
    jti: uuid_lib.UUID
    hash_token: str
    expira_en: datetime


def generar_refresh_token() -> RefrescoGenerado:
    settings = get_settings()
    jti = uuid_lib.uuid4()
    secreto = secrets.token_urlsafe(48)
    token_en_claro = f"{jti}.{secreto}"
    expira_en = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_DIAS)
    return RefrescoGenerado(
        token_en_claro=token_en_claro,
        jti=jti,
        hash_token=hash_refresh_token(token_en_claro),
        expira_en=expira_en,
    )


def hash_refresh_token(token_en_claro: str) -> str:
    return hashlib.sha256(token_en_claro.encode("utf-8")).hexdigest()


def extraer_jti_de_refresh_token(token_en_claro: str) -> uuid_lib.UUID | None:
    """El `jti` va como prefijo del token (`<jti>.<secreto>`) para poder
    buscar la fila en `tokens_refresco` sin escanear toda la tabla comparando
    hashes uno a uno."""
    try:
        jti_str, _secreto = token_en_claro.split(".", 1)
        return uuid_lib.UUID(jti_str)
    except (ValueError, AttributeError):
        return None
