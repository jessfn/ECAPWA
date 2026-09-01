"""Schema de solicitud de acceso — ECA-020 (rediseño de la pantalla de
autenticación, pedido explícito de Jesús: "apartado de registro igual" a
`pwasuper`).

**No crea cuentas.** ECA sigue con el modelo del proyecto (admin crea
técnicos, ver ECA-004): esto solo deja constancia en la bitácora de
auditoría de que alguien pidió acceso, para que el administrador la revise
y, si procede, cree la cuenta él mismo desde el panel.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SolicitudAccesoPeticion(BaseModel):
    nombre: str = Field(min_length=2, max_length=200)
    correo: str = Field(min_length=3, max_length=254)
    telefono: str | None = Field(default=None, max_length=30)
    notas: str | None = Field(default=None, max_length=1000)

    @field_validator("correo")
    @classmethod
    def _validar_correo(cls, valor: str) -> str:
        # Validación mínima a propósito: igual que `LoginPeticion.correo`
        # (`app/schemas/auth.py`), sin la dependencia `email-validator`
        # solo para este campo.
        if "@" not in valor or "." not in valor.split("@")[-1]:
            raise ValueError("Correo inválido.")
        return valor


class SolicitudAccesoPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    correo: str
    telefono: str | None
    notas: str | None
    estado: str
    creado_en: datetime


class SolicitudAccesoResolverPeticion(BaseModel):
    estado: str = Field(pattern="^(aprobada|rechazada)$")
