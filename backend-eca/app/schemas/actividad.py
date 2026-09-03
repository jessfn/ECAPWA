"""Schemas Pydantic de actividad — ECA-013."""
from __future__ import annotations

import uuid as uuid_lib
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidencia import EvidenciaPublica
from app.schemas.gps import GpsPeticion


class ActividadCrearPeticion(BaseModel):
    uuid: uuid_lib.UUID
    jornada_uuid: uuid_lib.UUID
    eca_id: int | None = None
    eca_nombre: str | None = None
    modalidad_id: int
    tipo_actividad_id: int
    tema_id: int | None = None
    subtema_id: int | None = None
    sistema_productivo_id: int | None = None
    descripcion: str = Field(min_length=1)
    resultado: str | None = None
    fecha_hora: datetime
    num_participantes: int | None = Field(default=None, ge=0)
    requiere_seguimiento: bool = False
    fecha_proximo_seguimiento: date | None = None
    gps: GpsPeticion | None = None


class ActividadPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: uuid_lib.UUID
    usuario_id: int
    jornada_id: int
    eca_id: int | None
    eca_nombre: str | None
    modalidad_id: int
    tipo_actividad_id: int
    tema_id: int | None
    subtema_id: int | None
    sistema_productivo_id: int | None
    descripcion: str
    resultado: str | None
    fecha_hora: datetime
    latitud: float | None
    longitud: float | None
    precision_gps_m: float | None
    estado_gps: str | None
    num_participantes: int | None
    requiere_seguimiento: bool
    fecha_proximo_seguimiento: date | None


class ActividadListaPaginada(BaseModel):
    total: int
    page: int
    page_size: int
    resultados: list[ActividadPublica]


class ActividadDetallePublica(ActividadPublica):
    evidencias: list[EvidenciaPublica] = Field(default_factory=list)
