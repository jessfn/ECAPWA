"""Schemas Pydantic de catálogos de actividad — ECA-010."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CatalogoSimplePublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clave: str
    nombre: str
    activo: bool
    orden: int


class TipoActividadPublico(CatalogoSimplePublico):
    requiere_evidencia: bool
    min_fotos: int
    max_fotos: int
    permite_participantes: bool
    requiere_eca: bool


class SubtemaPublico(CatalogoSimplePublico):
    tema_id: int


class CatalogoEditarPeticion(BaseModel):
    activo: bool | None = None
    nombre: str | None = None
    orden: int | None = None


class TipoActividadEditarPeticion(CatalogoEditarPeticion):
    requiere_evidencia: bool | None = None
    min_fotos: int | None = None
    max_fotos: int | None = None
    permite_participantes: bool | None = None
    requiere_eca: bool | None = None

    @model_validator(mode="after")
    def _validar_rango_fotos(self) -> "TipoActividadEditarPeticion":
        if self.min_fotos is not None and not (0 <= self.min_fotos <= 3):
            raise ValueError("min_fotos debe estar entre 0 y 3.")
        if self.max_fotos is not None and not (0 <= self.max_fotos <= 3):
            raise ValueError("max_fotos debe estar entre 0 y 3.")
        if self.min_fotos is not None and self.max_fotos is not None and self.min_fotos > self.max_fotos:
            raise ValueError("min_fotos no puede ser mayor que max_fotos.")
        return self


class SubtemaCrearPeticion(BaseModel):
    tema_id: int
    clave: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    orden: int = 0
