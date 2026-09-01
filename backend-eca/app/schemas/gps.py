"""Schema Pydantic de GPS compartido — ECA-012/ECA-014.

GPS es siempre opcional: nunca bloquea guardar una jornada o una actividad
la falta de ubicación (`03` §7, §20). Compartido entre jornadas y
actividades para no duplicarlo.
"""
from __future__ import annotations

from pydantic import BaseModel


class GpsPeticion(BaseModel):
    latitud: float | None = None
    longitud: float | None = None
    precision_gps_m: float | None = None
    estado_gps: str | None = None  # 'CON_GPS' | 'GPS_IMPRECISO' | 'SIN_GPS'
