"""Router `/actividades` — ECA-013 + ECA-019 (historial y consulta admin).

Online en este ticket (igual que jornadas, ECA-012); la integración con el
outbox llega en ECA-016. Sin GPS ni fotos todavía (ECA-014/ECA-015).
"""
from __future__ import annotations

import csv
import io
import uuid as uuid_lib
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.permissions import require_permission, resolver_permisos_efectivos
from app.models.usuario import Usuario
from app.repositories import actividades as repo_actividades
from app.repositories import evidencias as repo_evidencias
from app.schemas.actividad import (
    ActividadCrearPeticion,
    ActividadDetallePublica,
    ActividadListaPaginada,
    ActividadPublica,
)
from app.schemas.evidencia import EvidenciaPublica
from app.services import actividades_service

router = APIRouter(prefix="/actividades", tags=["actividades"])

_ERRORES_422 = (
    actividades_service.JornadaDesconocidaError,
    actividades_service.TipoActividadDesconocidoError,
    actividades_service.EcaRequeridaError,
    actividades_service.ParticipantesNoPermitidosError,
    actividades_service.SubtemaIncoherenteError,
    actividades_service.GpsInvalidoError,
)


@router.post("", response_model=ActividadPublica, status_code=status.HTTP_201_CREATED)
def crear_actividad(
    peticion: ActividadCrearPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("actividades.crear")),
) -> ActividadPublica:
    try:
        actividad = actividades_service.crear(
            db,
            uuid=peticion.uuid,
            jornada_uuid=peticion.jornada_uuid,
            eca_id=peticion.eca_id,
            eca_nombre=peticion.eca_nombre,
            modalidad_id=peticion.modalidad_id,
            tipo_actividad_id=peticion.tipo_actividad_id,
            tema_id=peticion.tema_id,
            subtema_id=peticion.subtema_id,
            sistema_productivo_id=peticion.sistema_productivo_id,
            descripcion=peticion.descripcion,
            resultado=peticion.resultado,
            fecha_hora=peticion.fecha_hora,
            num_participantes=peticion.num_participantes,
            requiere_seguimiento=peticion.requiere_seguimiento,
            fecha_proximo_seguimiento=peticion.fecha_proximo_seguimiento,
            actor=actor,
            gps=peticion.gps,
        )
    except _ERRORES_422 as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return ActividadPublica.model_validate(actividad)


@router.get("/me", response_model=ActividadListaPaginada)
def listar_mis_actividades(
    eca_id: int | None = None,
    tipo_actividad_id: int | None = None,
    tema_id: int | None = None,
    estado_gps: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("actividades.ver_propias")),
) -> ActividadListaPaginada:
    resultados, total = actividades_service.listar_propias(
        db,
        usuario_id=actor.id,
        eca_id=eca_id,
        tipo_actividad_id=tipo_actividad_id,
        tema_id=tema_id,
        estado_gps=estado_gps,
        desde=desde,
        hasta=hasta,
        page=page,
        page_size=page_size,
    )
    return ActividadListaPaginada(total=total, page=page, page_size=page_size, resultados=resultados)


def _filtros_admin(
    tecnico_id: int | None,
    eca_id: int | None,
    municipio_id: int | None,
    tipo_actividad_id: int | None,
    tema_id: int | None,
    estado_gps: str | None,
    desde: date | None,
    hasta: date | None,
) -> dict:
    return dict(
        usuario_id=tecnico_id,
        eca_id=eca_id,
        municipio_id=municipio_id,
        tipo_actividad_id=tipo_actividad_id,
        tema_id=tema_id,
        estado_gps=estado_gps,
        desde=desde,
        hasta=hasta,
    )


@router.get("", response_model=ActividadListaPaginada)
def listar_actividades(
    tecnico_id: int | None = None,
    eca_id: int | None = None,
    municipio_id: int | None = None,
    tipo_actividad_id: int | None = None,
    tema_id: int | None = None,
    estado_gps: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("actividades.ver_todas")),
) -> ActividadListaPaginada:
    filtros = _filtros_admin(tecnico_id, eca_id, municipio_id, tipo_actividad_id, tema_id, estado_gps, desde, hasta)
    resultados, total = actividades_service.listar_todas(db, page=page, page_size=page_size, **filtros)
    return ActividadListaPaginada(total=total, page=page, page_size=page_size, resultados=resultados)


@router.get("/exportar")
def exportar_actividades_csv(
    tecnico_id: int | None = None,
    eca_id: int | None = None,
    municipio_id: int | None = None,
    tipo_actividad_id: int | None = None,
    tema_id: int | None = None,
    estado_gps: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("actividades.ver_todas")),
) -> StreamingResponse:
    filtros = _filtros_admin(tecnico_id, eca_id, municipio_id, tipo_actividad_id, tema_id, estado_gps, desde, hasta)
    actividades = actividades_service.exportar_csv(db, **filtros)

    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(
        [
            "uuid",
            "usuario_id",
            "eca_id",
            "eca_nombre",
            "modalidad_id",
            "tipo_actividad_id",
            "tema_id",
            "subtema_id",
            "sistema_productivo_id",
            "descripcion",
            "resultado",
            "fecha_hora",
            "estado_gps",
            "num_participantes",
            "requiere_seguimiento",
            "recibido_en",
        ]
    )
    for a in actividades:
        escritor.writerow(
            [
                a.uuid,
                a.usuario_id,
                a.eca_id or "",
                a.eca_nombre or "",
                a.modalidad_id,
                a.tipo_actividad_id,
                a.tema_id or "",
                a.subtema_id or "",
                a.sistema_productivo_id or "",
                a.descripcion,
                a.resultado or "",
                a.fecha_hora.isoformat(),
                a.estado_gps or "",
                a.num_participantes if a.num_participantes is not None else "",
                a.requiere_seguimiento,
                a.recibido_en.isoformat() if a.recibido_en else "",
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=actividades.csv"},
    )


@router.get("/{uuid}", response_model=ActividadDetallePublica)
def obtener_actividad(
    uuid: uuid_lib.UUID,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(get_current_user),
) -> ActividadDetallePublica:
    actividad = repo_actividades.obtener_por_uuid(db, uuid)
    if actividad is None or actividad.eliminado_en is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Actividad no encontrada.")

    permisos = resolver_permisos_efectivos(db, actor.id)
    es_propia = actividad.usuario_id == actor.id
    if not es_propia and "actividades.ver_todas" not in permisos:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para ver esta actividad.")
    if es_propia and "actividades.ver_propias" not in permisos and "actividades.ver_todas" not in permisos:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para ver actividades.")

    evidencias = repo_evidencias.listar_de_actividad(db, actividad.id)
    datos = ActividadPublica.model_validate(actividad).model_dump()
    datos["evidencias"] = [EvidenciaPublica.model_validate(e) for e in evidencias]
    return ActividadDetallePublica(**datos)
