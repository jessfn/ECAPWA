"""Schemas Pydantic de ECA e importación masiva — ECA-007."""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EcaPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # `id` interno (no solo `uuid`): la PWA lo necesita para mandarlo como
    # `eca_id` en `POST /actividades` — mismo precedente que
    # `UsuarioPublico.id` (ECA-004): uso interno dentro del propio sistema,
    # no un identificador de negocio expuesto a terceros.
    id: int
    uuid: uuid_lib.UUID
    clave_fuente: str | None
    clave_institucional: str | None
    nombre: str
    estado_id: int
    municipio_id: int
    localidad_nombre: str | None
    latitud: float | None
    longitud: float | None
    activo: bool
    fuente_carga: str


class EcaCrearPeticion(BaseModel):
    nombre: str = Field(min_length=1)
    estado_id: int
    municipio_id: int
    clave_institucional: str | None = None
    localidad_nombre: str | None = None
    latitud: float | None = None
    longitud: float | None = None


class EcaEditarPeticion(BaseModel):
    nombre: str | None = None
    estado_id: int | None = None
    municipio_id: int | None = None
    clave_institucional: str | None = None
    localidad_nombre: str | None = None
    latitud: float | None = None
    longitud: float | None = None
    activo: bool | None = None


class EcaListaPaginada(BaseModel):
    total: int
    page: int
    page_size: int
    resultados: list[EcaPublica]


class ErrorFilaImportacion(BaseModel):
    fila: int
    campo: str | None = None
    mensaje: str


class ImportarEcaRespuesta(BaseModel):
    lote_uuid: uuid_lib.UUID
    estado: str
    total: int
    validas: int
    con_error: int
    errores: list[ErrorFilaImportacion]


class ConfirmarImportacionRespuesta(BaseModel):
    lote_uuid: uuid_lib.UUID
    estado: str
    creadas: int
    actualizadas: int


class LoteImportacionRespuesta(BaseModel):
    lote_uuid: uuid_lib.UUID
    tipo: str
    archivo_nombre: str
    estado: str
    total_filas: int
    filas_validas: int
    filas_con_error: int
    confirmado_en: datetime | None
