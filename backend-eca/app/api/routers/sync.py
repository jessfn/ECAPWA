"""Router `/sync` — ECA-017.

Ambos endpoints exigen sesión de servidor válida (igual que cualquier otra
ruta con `require_permission`): la PWA debe haber hecho `refresh`/`login`
antes de llamar aquí — la captura offline (escribir en el outbox) nunca
pasa por este router (§2.2).
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.permissions import require_permission
from app.core.ratelimit import limitar
from app.models.usuario import Usuario
from app.schemas.sync import (
    BootstrapRespuesta,
    DispositivoPeticion,
    DispositivoPublico,
    SyncPushPeticion,
    SyncPushRespuesta,
)
from app.services import bootstrap_service, sync_service

router = APIRouter(prefix="/sync", tags=["sync"])

# Ya autenticado (require_permission("sync.usar")), pero un lote de push
# malicioso/roto reintentando en bucle no debe poder martillar el backend.
_limite_push = limitar(nombre="sync.push", limite=30, ventana_seg=60)


@router.post("/dispositivo", response_model=DispositivoPublico)
def registrar_dispositivo(
    peticion: DispositivoPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("sync.usar")),
) -> DispositivoPublico:
    dispositivo = sync_service.registrar_dispositivo(
        db, uuid=peticion.uuid, plataforma=peticion.plataforma, user_agent=peticion.user_agent, actor=actor
    )
    return DispositivoPublico.model_validate(dispositivo)


@router.post("/push", response_model=SyncPushRespuesta, dependencies=[Depends(_limite_push)])
def push(
    peticion: SyncPushPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("sync.usar")),
) -> SyncPushRespuesta:
    resultados = sync_service.push(
        db,
        dispositivo_uuid=peticion.dispositivo_uuid,
        jornadas=peticion.jornadas,
        actividades=peticion.actividades,
        actor=actor,
    )
    return SyncPushRespuesta(resultados=resultados)


@router.get("/bootstrap", response_model=BootstrapRespuesta)
def bootstrap(
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("sync.usar")),
) -> BootstrapRespuesta:
    return BootstrapRespuesta.model_validate(bootstrap_service.bootstrap(db, actor))


@router.get("/pull", response_model=BootstrapRespuesta)
def pull(
    desde: datetime | None = None,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("sync.usar")),
) -> BootstrapRespuesta:
    return BootstrapRespuesta.model_validate(bootstrap_service.pull(db, actor, desde=desde))
