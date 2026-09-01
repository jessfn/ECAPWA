"""Schemas Pydantic de jornada — ECA-012."""
from __future__ import annotations

import uuid as uuid_lib
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.gps import GpsPeticion

__all__ = ["GpsPeticion", "JornadaIniciarPeticion", "JornadaCerrarPeticion", "JornadaPublica"]


class JornadaIniciarPeticion(BaseModel):
    uuid: uuid_lib.UUID
    inicio_en: datetime
    gps: GpsPeticion | None = None


class JornadaCerrarPeticion(BaseModel):
    fin_en: datetime
    gps: GpsPeticion | None = None


class JornadaPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: uuid_lib.UUID
    usuario_id: int
    fecha: date
    estado: str
    inicio_en: datetime
    latitud_inicio: float | None
    longitud_inicio: float | None
    precision_gps_inicio_m: float | None
    estado_gps_inicio: str | None
    fin_en: datetime | None
    latitud_fin: float | None
    longitud_fin: float | None
    precision_gps_fin_m: float | None
    estado_gps_fin: str | None
    nota: str | None
