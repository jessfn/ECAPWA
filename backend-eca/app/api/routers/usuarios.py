"""Router `/usuarios` — ECA-004.

CRUD de usuarios y asignación de roles para ADMIN. Cada endpoint declara su
`require_permission` explícito: ningún endpoint de datos debe responder sin
uno (criterio de aceptación del ticket).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.permissions import require_permission
from app.models.usuario import Usuario
from app.repositories import usuarios as repo_usuarios
from app.schemas.usuario import (
    ImportacionUsuariosRespuesta,
    UsuarioCambioEstadoPeticion,
    UsuarioCrearPeticion,
    UsuarioCreadoRespuesta,
    UsuarioEditarPeticion,
    UsuarioPublico,
    UsuarioRolesPeticion,
)
from app.services import usuarios_service
from app.services.importacion_usuarios_service import importar_usuarios

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


def _obtener_o_404(db: Session, usuario_id: int) -> Usuario:
    usuario = repo_usuarios.obtener_por_id(db, usuario_id)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    return usuario


@router.get("", response_model=list[UsuarioPublico])
def listar_usuarios(
    estado: str | None = None,
    rol: str | None = None,
    texto: str | None = None,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("usuarios.gestionar")),
) -> list[UsuarioPublico]:
    usuarios = repo_usuarios.listar(db, estado=estado, rol=rol, texto=texto)
    return [usuarios_service.a_publico(db, u) for u in usuarios]


@router.post("", response_model=UsuarioCreadoRespuesta, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    peticion: UsuarioCrearPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("usuarios.gestionar")),
) -> UsuarioCreadoRespuesta:
    try:
        usuario, contrasena_temporal = usuarios_service.crear_usuario(
            db,
            nombre=peticion.nombre,
            apellido_paterno=peticion.apellido_paterno,
            apellido_materno=peticion.apellido_materno,
            correo=peticion.correo,
            telefono=peticion.telefono,
            curp=peticion.curp,
            claves_rol=peticion.roles,
            actor=actor,
        )
    except usuarios_service.CorreoDuplicadoError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except usuarios_service.RolDesconocidoError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    return UsuarioCreadoRespuesta(
        usuario=usuarios_service.a_publico(db, usuario), contrasena_temporal=contrasena_temporal
    )


@router.get("/{usuario_id}", response_model=UsuarioPublico)
def obtener_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("usuarios.gestionar")),
) -> UsuarioPublico:
    return usuarios_service.a_publico(db, _obtener_o_404(db, usuario_id))


@router.patch("/{usuario_id}", response_model=UsuarioPublico)
def editar_usuario(
    usuario_id: int,
    peticion: UsuarioEditarPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("usuarios.gestionar")),
) -> UsuarioPublico:
    usuario = _obtener_o_404(db, usuario_id)
    usuario = usuarios_service.editar_usuario(
        db,
        usuario=usuario,
        nombre=peticion.nombre,
        apellido_paterno=peticion.apellido_paterno,
        apellido_materno=peticion.apellido_materno,
        telefono=peticion.telefono,
        curp=peticion.curp,
        actor=actor,
    )
    return usuarios_service.a_publico(db, usuario)


@router.patch("/{usuario_id}/estado", response_model=UsuarioPublico)
def cambiar_estado_usuario(
    usuario_id: int,
    peticion: UsuarioCambioEstadoPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("usuarios.gestionar")),
) -> UsuarioPublico:
    usuario = _obtener_o_404(db, usuario_id)
    usuario = usuarios_service.cambiar_estado(db, usuario=usuario, estado_nuevo=peticion.estado, actor=actor)
    return usuarios_service.a_publico(db, usuario)


@router.put("/{usuario_id}/roles", response_model=UsuarioPublico)
def asignar_roles_usuario(
    usuario_id: int,
    peticion: UsuarioRolesPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("usuarios.gestionar")),
) -> UsuarioPublico:
    usuario = _obtener_o_404(db, usuario_id)
    try:
        usuario = usuarios_service.asignar_roles(db, usuario=usuario, claves_rol=peticion.roles, actor=actor)
    except usuarios_service.RolDesconocidoError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return usuarios_service.a_publico(db, usuario)


@router.post("/importar", response_model=ImportacionUsuariosRespuesta)
async def importar_usuarios_csv(
    archivo: UploadFile,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("usuarios.importar")),
) -> ImportacionUsuariosRespuesta:
    contenido = (await archivo.read()).decode("utf-8-sig")
    try:
        return importar_usuarios(db, contenido_csv=contenido, actor=actor)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
