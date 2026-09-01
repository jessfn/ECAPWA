"""Registro de auditoría — ECA-004.

Toda alta/baja/cambio de rol/cambio de estado pasa por aquí (criterio de
aceptación del ticket). `sanear_datos_auditoria` es la única puerta hacia
`auditoria_eventos.datos_antes/datos_despues`: nunca deben llegar contraseñas,
hashes, tokens ni el CURP completo (`05_MODELO_DATOS_ECA.md` §4.10).
"""
from __future__ import annotations

import hashlib
import uuid as uuid_lib
from typing import Any

from sqlalchemy.orm import Session

from app.models.auditoria import AuditoriaEvento

_CAMPOS_EXCLUIDOS = frozenset(
    {
        "contrasena",
        "contrasena_actual",
        "contrasena_nueva",
        "contrasena_hash",
        "access_token",
        "refresh_token",
        "hash_token",
        "curp",
    }
)


def sanear_datos_auditoria(datos: dict[str, Any] | None) -> dict[str, Any] | None:
    """Quita del payload cualquier campo sensible antes de guardarlo.

    Se excluye completo en vez de enmascarar parcialmente (p. ej. el CURP):
    más simple y a prueba de errores de formato que un enmascarado a medias.
    """
    if datos is None:
        return None
    return {clave: valor for clave, valor in datos.items() if clave not in _CAMPOS_EXCLUIDOS}


def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def registrar_evento(
    db: Session,
    *,
    accion: str,
    modulo: str,
    origen: str = "BACKEND",
    actor_usuario_id: int | None = None,
    actor_rol: str | None = None,
    entidad_tipo: str | None = None,
    entidad_id: int | None = None,
    entidad_uuid: uuid_lib.UUID | None = None,
    descripcion: str | None = None,
    datos_antes: dict[str, Any] | None = None,
    datos_despues: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    sesion_id: uuid_lib.UUID | None = None,
) -> AuditoriaEvento:
    evento = AuditoriaEvento(
        accion=accion,
        modulo=modulo,
        origen=origen,
        actor_usuario_id=actor_usuario_id,
        actor_rol=actor_rol,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        entidad_uuid=entidad_uuid,
        descripcion=descripcion,
        datos_antes=sanear_datos_auditoria(datos_antes),
        datos_despues=sanear_datos_auditoria(datos_despues),
        ip_hash=hash_ip(ip),
        user_agent=user_agent,
        sesion_id=sesion_id,
    )
    db.add(evento)
    db.flush()
    return evento
