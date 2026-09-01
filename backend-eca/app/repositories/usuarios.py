"""Acceso a datos de `Usuario` / `TokenRefresco` — ECA-003/ECA-004.

Capa delgada sobre SQLAlchemy: sin lógica de negocio (eso vive en
`app/services/auth_service.py` y `app/services/usuarios_service.py`).
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.rbac import Rol, UsuarioRol
from app.models.token_refresco import TokenRefresco
from app.models.usuario import Usuario


def obtener_por_correo(db: Session, correo: str) -> Usuario | None:
    return db.execute(select(Usuario).where(Usuario.correo == correo)).scalar_one_or_none()


def obtener_por_id(db: Session, usuario_id: int) -> Usuario | None:
    return db.get(Usuario, usuario_id)


def crear_usuario(db: Session, usuario: Usuario) -> Usuario:
    db.add(usuario)
    db.flush()
    return usuario


def listar(
    db: Session, *, estado: str | None = None, rol: str | None = None, texto: str | None = None
) -> list[Usuario]:
    consulta = select(Usuario)
    if estado:
        consulta = consulta.where(Usuario.estado == estado)
    if rol:
        consulta = (
            consulta.join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)
            .join(Rol, Rol.id == UsuarioRol.rol_id)
            .where(UsuarioRol.activo.is_(True), Rol.clave == rol)
        )
    if texto:
        patron = f"%{texto}%"
        consulta = consulta.where(
            or_(
                Usuario.correo.ilike(patron),
                (Usuario.nombre + " " + Usuario.apellido_paterno).ilike(patron),
            )
        )
    consulta = consulta.order_by(func.lower(Usuario.apellido_paterno), func.lower(Usuario.nombre))
    return list(db.execute(consulta).scalars())


def crear_token_refresco(
    db: Session,
    *,
    usuario_id: int,
    jti: uuid_lib.UUID,
    hash_token: str,
    expira_en: datetime,
    user_agent: str | None = None,
    ip_hash: str | None = None,
) -> TokenRefresco:
    token = TokenRefresco(
        usuario_id=usuario_id,
        jti=jti,
        hash_token=hash_token,
        expira_en=expira_en,
        user_agent=user_agent,
        ip_hash=ip_hash,
    )
    db.add(token)
    db.flush()
    return token


def obtener_token_refresco_por_jti(db: Session, jti: uuid_lib.UUID) -> TokenRefresco | None:
    return db.execute(
        select(TokenRefresco).where(TokenRefresco.jti == jti)
    ).scalar_one_or_none()


def revocar_token_refresco(db: Session, token: TokenRefresco, *, motivo: str) -> None:
    token.revocado_en = datetime.now(timezone.utc)
    token.motivo_revocacion = motivo
    db.add(token)


def revocar_todos_los_tokens_de(db: Session, usuario_id: int, *, motivo: str) -> None:
    tokens = db.execute(
        select(TokenRefresco).where(
            TokenRefresco.usuario_id == usuario_id,
            TokenRefresco.revocado_en.is_(None),
        )
    ).scalars()
    for token in tokens:
        revocar_token_refresco(db, token, motivo=motivo)
