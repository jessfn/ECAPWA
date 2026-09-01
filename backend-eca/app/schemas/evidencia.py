"""Schema Pydantic de evidencia — ECA-015."""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenciaPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # `id` interno: necesario para armar el enlace de descarga autenticada
    # `GET /evidencias/{id}` (ECA-015) — mismo precedente que
    # `EcaPublica.id`/`UsuarioPublico.id`.
    id: int
    uuid: uuid_lib.UUID
    actividad_id: int
    orden: int
    nombre_archivo: str
    mime: str
    tamano_bytes: int
    hash_sha256: str
    latitud: float | None
    longitud: float | None
    capturada_en: datetime | None
