"""Router `/jornadas` — ECA-012.

En este ticket el flujo es siempre **online**; la integración con el
outbox llega en ECA-016 (el modelo ya trae el bloque offline para no
migrar de nuevo).
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.permissions import require_permission
from app.models.usuario import Usuario
from app.schemas.jornada import JornadaCerrarPeticion, JornadaIniciarPeticion, JornadaPublica
from app.services import jornadas_service

router = APIRouter(prefix="/jornadas", tags=["jornadas"])


@router.post("", response_model=JornadaPublica, status_code=status.HTTP_201_CREATED)
def iniciar_jornada(
    peticion: JornadaIniciarPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("jornadas.crear")),
) -> JornadaPublica:
    try:
        jornada = jornadas_service.iniciar(
            db, uuid=peticion.uuid, inicio_en=peticion.inicio_en, gps=peticion.gps, nota=peticion.nota, actor=actor
        )
    except jornadas_service.DetalleRequeridoError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return JornadaPublica.model_validate(jornada)


@router.patch("/{uuid}/cerrar", response_model=JornadaPublica)
def cerrar_jornada(
    uuid: uuid_lib.UUID,
    peticion: JornadaCerrarPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("jornadas.crear")),
) -> JornadaPublica:
    try:
        jornada = jornadas_service.cerrar(
            db, uuid=uuid, fin_en=peticion.fin_en, gps=peticion.gps, nota_fin=peticion.nota_fin, actor=actor
        )
    except jornadas_service.JornadaNoEncontradaError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except jornadas_service.RangoFechasInvalidoError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except jornadas_service.DetalleRequeridoError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return JornadaPublica.model_validate(jornada)


@router.get("", response_model=list[JornadaPublica])
def listar_mis_jornadas(
    fecha: str | None = None,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("jornadas.ver_propias")),
) -> list[JornadaPublica]:
    fecha_parseada = date_cls.fromisoformat(fecha) if fecha else None
    jornadas = jornadas_service.listar(db, usuario_id=actor.id, fecha=fecha_parseada)
    return [JornadaPublica.model_validate(j) for j in jornadas]


@router.get("/me/hoy", response_model=JornadaPublica | None)
def mi_jornada_de_hoy(
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("jornadas.ver_propias")),
) -> JornadaPublica | None:
    jornada = jornadas_service.obtener_de_hoy(db, usuario_id=actor.id)
    return JornadaPublica.model_validate(jornada) if jornada else None
