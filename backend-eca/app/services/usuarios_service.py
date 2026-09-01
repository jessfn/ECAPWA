"""Lógica de negocio de gestión de usuarios (CRUD, roles) — ECA-004.

Todo alta/edición/cambio de estado/cambio de rol pasa por `app/core/audit.py`
(criterio de aceptación del ticket). Los routers son delgados: validan forma
con Pydantic y delegan aquí toda decisión de negocio.
"""
from __future__ import annotations

import secrets
import string

from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.core.security import hash_contrasena
from app.models.usuario import Usuario
from app.repositories import rbac as repo_rbac
from app.repositories import usuarios as repo_usuarios
from app.schemas.usuario import UsuarioPublico

_ALFABETO_CONTRASENA_TEMPORAL = string.ascii_letters + string.digits


class CorreoDuplicadoError(Exception):
    pass


class RolDesconocidoError(Exception):
    pass


def generar_contrasena_temporal() -> str:
    """12 caracteres alfanuméricos aleatorios: cumple la política mínima de
    `validar_fortaleza_contrasena` (longitud + letras y números) por
    construcción, sin depender de reintentos."""
    letras = "".join(secrets.choice(string.ascii_letters) for _ in range(8))
    numeros = "".join(secrets.choice(string.digits) for _ in range(4))
    caracteres = list(letras + numeros)
    secrets.SystemRandom().shuffle(caracteres)
    return "".join(caracteres)


def a_publico(db: Session, usuario: Usuario) -> UsuarioPublico:
    """`Usuario.roles` es la relación ORM (objetos `UsuarioRol`), no la lista
    de claves que expone `UsuarioPublico.roles: list[str]`. Si se deja que
    `model_validate(usuario, from_attributes=True)` lea `roles` directo del
    ORM, Pydantic falla la validación ahí mismo (antes de que un
    `.model_copy(update=...)` posterior pudiera corregirlo) — por eso se arma
    el dict a mano, excluyendo esa relación, con las claves ya resueltas."""
    roles = [a.rol.clave for a in repo_rbac.asignaciones_activas_de(db, usuario.id)]
    datos = {
        campo: getattr(usuario, campo)
        for campo in UsuarioPublico.model_fields
        if campo != "roles"
    }
    datos["roles"] = roles
    return UsuarioPublico.model_validate(datos)


def crear_usuario(
    db: Session,
    *,
    nombre: str,
    apellido_paterno: str,
    apellido_materno: str | None,
    correo: str,
    telefono: str | None,
    curp: str | None,
    claves_rol: list[str],
    actor: Usuario | None,
) -> tuple[Usuario, str]:
    if repo_usuarios.obtener_por_correo(db, correo) is not None:
        raise CorreoDuplicadoError(f"Ya existe un usuario con el correo {correo}.")

    for clave in claves_rol:
        if repo_rbac.obtener_rol_por_clave(db, clave) is None:
            raise RolDesconocidoError(f"Rol desconocido o inactivo: {clave}")

    contrasena_temporal = generar_contrasena_temporal()
    usuario = Usuario(
        nombre=nombre,
        apellido_paterno=apellido_paterno,
        apellido_materno=apellido_materno,
        correo=correo,
        telefono=telefono,
        curp=curp,
        contrasena_hash=hash_contrasena(contrasena_temporal),
        requiere_cambio_contrasena=True,
        estado="ACTIVO",
    )
    repo_usuarios.crear_usuario(db, usuario)

    for clave in claves_rol:
        rol = repo_rbac.obtener_rol_por_clave(db, clave)
        repo_rbac.asignar_rol(
            db, usuario_id=usuario.id, rol_id=rol.id, asignado_por=actor.id if actor else None
        )

    registrar_evento(
        db,
        accion="usuario.alta",
        modulo="usuarios",
        actor_usuario_id=actor.id if actor else None,
        entidad_tipo="usuario",
        entidad_id=usuario.id,
        entidad_uuid=usuario.uuid,
        descripcion=f"Alta de usuario {correo}",
        datos_despues={"correo": correo, "estado": usuario.estado, "roles": claves_rol},
    )
    db.commit()
    db.refresh(usuario)
    return usuario, contrasena_temporal


def editar_usuario(
    db: Session,
    *,
    usuario: Usuario,
    nombre: str | None,
    apellido_paterno: str | None,
    apellido_materno: str | None,
    telefono: str | None,
    curp: str | None,
    actor: Usuario,
) -> Usuario:
    antes = {
        "nombre": usuario.nombre,
        "apellido_paterno": usuario.apellido_paterno,
        "apellido_materno": usuario.apellido_materno,
        "telefono": usuario.telefono,
    }
    if nombre is not None:
        usuario.nombre = nombre
    if apellido_paterno is not None:
        usuario.apellido_paterno = apellido_paterno
    if apellido_materno is not None:
        usuario.apellido_materno = apellido_materno
    if telefono is not None:
        usuario.telefono = telefono
    if curp is not None:
        usuario.curp = curp

    db.add(usuario)
    registrar_evento(
        db,
        accion="usuario.edicion",
        modulo="usuarios",
        actor_usuario_id=actor.id,
        entidad_tipo="usuario",
        entidad_id=usuario.id,
        entidad_uuid=usuario.uuid,
        datos_antes=antes,
        datos_despues={
            "nombre": usuario.nombre,
            "apellido_paterno": usuario.apellido_paterno,
            "apellido_materno": usuario.apellido_materno,
            "telefono": usuario.telefono,
        },
    )
    db.commit()
    db.refresh(usuario)
    return usuario


def cambiar_estado(db: Session, *, usuario: Usuario, estado_nuevo: str, actor: Usuario) -> Usuario:
    estado_anterior = usuario.estado
    usuario.estado = estado_nuevo
    db.add(usuario)

    if estado_nuevo == "BAJA":
        # Corrige `05_MODELO_DATOS_ECA.md` §1.4: BAJA revoca tokens y bloquea login.
        repo_usuarios.revocar_todos_los_tokens_de(db, usuario.id, motivo="BAJA_USUARIO")

    registrar_evento(
        db,
        accion="usuario.cambio_estado",
        modulo="usuarios",
        actor_usuario_id=actor.id,
        entidad_tipo="usuario",
        entidad_id=usuario.id,
        entidad_uuid=usuario.uuid,
        datos_antes={"estado": estado_anterior},
        datos_despues={"estado": estado_nuevo},
    )
    db.commit()
    db.refresh(usuario)
    return usuario


def asignar_roles(db: Session, *, usuario: Usuario, claves_rol: list[str], actor: Usuario) -> Usuario:
    roles_antes = [a.rol.clave for a in repo_rbac.asignaciones_activas_de(db, usuario.id)]
    try:
        repo_rbac.reemplazar_roles(
            db, usuario_id=usuario.id, claves_rol_nuevas=set(claves_rol), asignado_por=actor.id
        )
    except ValueError as exc:
        raise RolDesconocidoError(str(exc)) from exc

    registrar_evento(
        db,
        accion="permisos.cambio",
        modulo="usuarios",
        actor_usuario_id=actor.id,
        entidad_tipo="usuario",
        entidad_id=usuario.id,
        entidad_uuid=usuario.uuid,
        datos_antes={"roles": roles_antes},
        datos_despues={"roles": claves_rol},
    )
    db.commit()
    db.refresh(usuario)
    return usuario
