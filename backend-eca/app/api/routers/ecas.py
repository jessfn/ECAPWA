"""Router `/ecas` — ECA-007.

Lectura: `ecas.ver`. Alta/edición individual: `ecas.gestionar`. Importación
masiva (2 pasos: validar → confirmar): `ecas.importar`.
"""
from __future__ import annotations

import uuid as uuid_lib

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.permissions import require_permission
from app.models.usuario import Usuario
from app.repositories import ecas as repo_ecas
from app.schemas.eca import (
    ConfirmarImportacionRespuesta,
    EcaCrearPeticion,
    EcaEditarPeticion,
    EcaListaPaginada,
    EcaPublica,
    ErrorFilaImportacion,
    ImportarEcaRespuesta,
    LoteImportacionRespuesta,
)
from app.services import ecas_service, importacion_eca_service

router = APIRouter(prefix="/ecas", tags=["ecas"])


def _lote_a_respuesta(lote) -> LoteImportacionRespuesta:
    return LoteImportacionRespuesta(
        lote_uuid=lote.uuid,
        tipo=lote.tipo,
        archivo_nombre=lote.archivo_nombre,
        estado=lote.estado,
        total_filas=lote.total_filas,
        filas_validas=lote.filas_validas,
        filas_con_error=lote.filas_con_error,
        confirmado_en=lote.confirmado_en,
    )


@router.get("", response_model=EcaListaPaginada)
def listar_ecas(
    estado_id: int | None = None,
    municipio_id: int | None = None,
    q: str | None = None,
    activo: bool | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("ecas.ver")),
) -> EcaListaPaginada:
    resultados, total = repo_ecas.listar(
        db, estado_id=estado_id, municipio_id=municipio_id, q=q, activo=activo, page=page, page_size=page_size
    )
    return EcaListaPaginada(total=total, page=page, page_size=page_size, resultados=resultados)


@router.get("/{eca_id}", response_model=EcaPublica)
def obtener_eca(
    eca_id: int,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("ecas.ver")),
) -> EcaPublica:
    eca = repo_ecas.obtener_por_id(db, eca_id)
    if eca is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ECA no encontrada.")
    return eca


@router.post("", response_model=EcaPublica, status_code=status.HTTP_201_CREATED)
def crear_eca(
    peticion: EcaCrearPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("ecas.gestionar")),
) -> EcaPublica:
    return ecas_service.crear_eca(
        db,
        nombre=peticion.nombre,
        estado_id=peticion.estado_id,
        municipio_id=peticion.municipio_id,
        clave_institucional=peticion.clave_institucional,
        localidad_nombre=peticion.localidad_nombre,
        latitud=peticion.latitud,
        longitud=peticion.longitud,
        actor=actor,
    )


@router.patch("/{eca_id}", response_model=EcaPublica)
def editar_eca(
    eca_id: int,
    peticion: EcaEditarPeticion,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("ecas.gestionar")),
) -> EcaPublica:
    eca = repo_ecas.obtener_por_id(db, eca_id)
    if eca is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ECA no encontrada.")
    return ecas_service.editar_eca(
        db,
        eca=eca,
        nombre=peticion.nombre,
        estado_id=peticion.estado_id,
        municipio_id=peticion.municipio_id,
        clave_institucional=peticion.clave_institucional,
        localidad_nombre=peticion.localidad_nombre,
        latitud=peticion.latitud,
        longitud=peticion.longitud,
        activo=peticion.activo,
        actor=actor,
    )


@router.post("/importar", response_model=ImportarEcaRespuesta)
async def importar_ecas(
    archivo: UploadFile,
    columna_identificador: str | None = Form(default=None),
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("ecas.importar")),
) -> ImportarEcaRespuesta:
    contenido = await archivo.read()
    try:
        lote = importacion_eca_service.iniciar_importacion(
            db,
            contenido=contenido,
            nombre_archivo=archivo.filename or "archivo",
            columna_identificador=columna_identificador,
            actor=actor,
        )
    except importacion_eca_service.SinIdentificadorEstableError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    errores = [ErrorFilaImportacion(**e) for e in lote.resumen.get("errores", [])]
    return ImportarEcaRespuesta(
        lote_uuid=lote.uuid,
        estado=lote.estado,
        total=lote.total_filas,
        validas=lote.filas_validas,
        con_error=lote.filas_con_error,
        errores=errores,
    )


@router.get("/importar/{lote_uuid}", response_model=LoteImportacionRespuesta)
def obtener_lote(
    lote_uuid: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("ecas.importar")),
) -> LoteImportacionRespuesta:
    lote = repo_ecas.obtener_lote_por_uuid(db, lote_uuid)
    if lote is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lote no encontrado.")
    return _lote_a_respuesta(lote)


@router.post("/importar/{lote_uuid}/confirmar", response_model=ConfirmarImportacionRespuesta)
def confirmar_importacion(
    lote_uuid: uuid_lib.UUID,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("ecas.importar")),
) -> ConfirmarImportacionRespuesta:
    try:
        lote, creadas, actualizadas = importacion_eca_service.confirmar_importacion(
            db, lote_uuid=lote_uuid, actor=actor
        )
    except importacion_eca_service.LoteNoEncontradoError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except importacion_eca_service.LoteEnEstadoInvalidoError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    return ConfirmarImportacionRespuesta(
        lote_uuid=lote.uuid, estado=lote.estado, creadas=creadas, actualizadas=actualizadas
    )
