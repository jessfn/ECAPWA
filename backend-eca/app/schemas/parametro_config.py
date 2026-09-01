"""Schema Pydantic de parámetro de configuración — ECA-014."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ParametroPublico(BaseModel):
    clave: str
    valor: Any
