"""Schemas Pydantic de ámbitos geográficos de técnico — ECA-008."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class MunicipioDelAmbito(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    municipio_id: int
    municipio_nombre: str
    estado_id: int
    fecha_inicio: date


class AmbitoReemplazarPeticion(BaseModel):
    municipio_ids: list[int] = Field(default_factory=list)


class ImportarAmbitosFila(BaseModel):
    fila: int
    correo_tecnico: str | None = None
    resultado: str  # "asignado" | "error"
    error: str | None = None


class ImportarAmbitosRespuesta(BaseModel):
    total_filas: int
    asignadas: int
    con_error: int
    detalle: list[ImportarAmbitosFila]
