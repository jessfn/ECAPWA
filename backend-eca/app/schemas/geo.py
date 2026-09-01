"""Schemas Pydantic de catálogos geográficos — ECA-006."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EstadoPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clave_inegi: str
    nombre: str
    abreviatura: str | None
    activo: bool


class MunicipioPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado_id: int
    clave_inegi: str
    nombre: str
    activo: bool


class ActivoPeticion(BaseModel):
    activo: bool
