"""Router `/solicitudes-acceso` — ECA-020 + ECA-020b.

`POST` es público (nadie tiene cuenta todavía para pedir una), rate-limited,
y **no crea ningún usuario**: solo registra la solicitud con estado
`pendiente`. `GET`/`PATCH` son para `admin-eca` (permiso
`usuarios.gestionar`): listan las solicitudes y permiten marcarlas
aprobada/rechazada — el alta real de la cuenta sigue siendo un paso
independiente y manual del administrador, vía `POST /usuarios` (ECA-004);
resolver aquí solo saca la solicitud de la bandeja de pendientes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.core.db import get_db
from app.core.permissions import require_permission
from app.core.ratelimit import limitar
from app.models.usuario import Usuario
from app.repositories import solicitudes_acceso as repo_solicitudes
from app.schemas.solicitud_acceso import (
    SolicitudAccesoPeticion,
    SolicitudAccesoPublica,
    SolicitudAccesoResolverPeticion,
)

router = APIRouter(prefix="/solicitudes-acceso", tags=["solicitudes-acceso"])

_limite = limitar(nombre="solicitudes_acceso", limite=5, ventana_seg=300)


@router.post("", status_code=204, response_model=None, dependencies=[Depends(_limite)])
def crear_solicitud(
    peticion: SolicitudAccesoPeticion, request: Request, db: Session = Depends(get_db)
) -> Response:
    repo_solicitudes.crear(
        db, nombre=peticion.nombre, correo=peticion.correo, telefono=peticion.telefono, notas=peticion.notas
    )
    registrar_evento(
        db,
        accion="solicitud_acceso.creada",
        modulo="usuarios",
        origen="PWA",
        entidad_tipo="solicitud_acceso",
        descripcion=f"{peticion.nombre} <{peticion.correo}>",
        datos_despues={
            "nombre": peticion.nombre,
            "correo": peticion.correo,
            "telefono": peticion.telefono,
            "notas": peticion.notas,
        },
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return Response(status_code=204)


@router.get("", response_model=list[SolicitudAccesoPublica])
def listar_solicitudes(
    estado: str | None = None,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("usuarios.gestionar")),
) -> list[SolicitudAccesoPublica]:
    return repo_solicitudes.listar(db, estado=estado)


@router.patch("/{solicitud_id}", response_model=SolicitudAccesoPublica)
def resolver_solicitud(
    solicitud_id: int,
    peticion: SolicitudAccesoResolverPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("usuarios.gestionar")),
) -> SolicitudAccesoPublica:
    solicitud = repo_solicitudes.obtener_por_id(db, solicitud_id)
    if solicitud is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada.")
    if solicitud.estado != "pendiente":
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta solicitud ya fue atendida.")

    solicitud = repo_solicitudes.resolver(
        db, solicitud=solicitud, estado=peticion.estado, atendida_por=actor.id
    )
    registrar_evento(
        db,
        accion=f"solicitud_acceso.{peticion.estado}",
        modulo="usuarios",
        origen="ADMIN",
        entidad_tipo="solicitud_acceso",
        entidad_id=solicitud.id,
        descripcion=f"{solicitud.nombre} <{solicitud.correo}>",
        actor_usuario_id=actor.id,
    )
    db.commit()
    return solicitud
