"""Schemas Pydantic de asignaciones técnico↔ECA — ECA-009."""
from __future__ import annotations

import uuid as uuid_lib
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class AsignacionPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: uuid_lib.UUID
    usuario_id: int
    eca_id: int
    fecha_inicio: date
    fecha_fin: date | None
    activo: bool
    origen: str


class AsignacionCrearPeticion(BaseModel):
    usuario_id: int
    eca_id: int


class EcaDelTecnico(BaseModel):
    """Lo que ve un técnico en `GET /usuarios/me/ecas` — ver REGLA DE ECA."""

    model_config = ConfigDict(from_attributes=True)

    eca_id: int
    eca_uuid: uuid_lib.UUID
    eca_nombre: str
    municipio_id: int
    origen: str  # "ASIGNACION_DIRECTA" | "AMBITO"


class ImportarAsignacionesFila(BaseModel):
    fila: int
    correo_tecnico: str | None = None
    resultado: str  # "asignado" | "error"
    error: str | None = None


class ImportarAsignacionesRespuesta(BaseModel):
    total_filas: int
    asignadas: int
    con_error: int
    detalle: list[ImportarAsignacionesFila] = Field(default_factory=list)
