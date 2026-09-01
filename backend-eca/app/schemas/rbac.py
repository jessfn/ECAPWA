"""Schemas Pydantic de RBAC — ECA-004."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RolPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    clave: str
    nombre: str
    descripcion: str | None


class PermisoPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    clave: str
    modulo: str
    nombre: str
    descripcion: str | None
