"""Schemas Pydantic de `Usuario` — ECA-003/ECA-004.

`UsuarioPublico` es la única forma en la que un usuario sale de la API:
nunca incluye `contrasena_hash` ni `algoritmo_hash`.
"""
from __future__ import annotations

import re
import uuid as uuid_lib
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.usuario import ESTADOS_USUARIO

_PATRON_CURP = re.compile(r"^[A-Z]{4}\d{6}[A-Z]{6}[A-Z0-9]\d$")


class UsuarioPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # `id` interno — expuesto solo en respuestas que requieren permiso de
    # administración (`usuarios.gestionar`/`ambitos.gestionar`): el panel lo
    # necesita para las rutas `/usuarios/{id}/...` (roles, estado, ámbito).
    # No es un identificador de negocio externo — para eso está `uuid`.
    id: int
    uuid: uuid_lib.UUID
    nombre: str
    apellido_paterno: str
    apellido_materno: str | None
    correo: str
    telefono: str | None
    estado: str
    requiere_cambio_contrasena: bool
    ultimo_acceso_en: datetime | None
    creado_en: datetime
    roles: list[str] = Field(default_factory=list)


class UsuarioCrearPeticion(BaseModel):
    nombre: str = Field(min_length=1)
    apellido_paterno: str = Field(min_length=1)
    apellido_materno: str | None = None
    correo: str = Field(min_length=3)
    telefono: str | None = None
    curp: str | None = None
    roles: list[str] = Field(default_factory=list, description="Claves de rol, p. ej. ['TECNICO']")

    @field_validator("curp")
    @classmethod
    def _validar_curp(cls, valor: str | None) -> str | None:
        if valor is not None and not _PATRON_CURP.match(valor):
            raise ValueError("CURP con formato inválido.")
        return valor


class UsuarioEditarPeticion(BaseModel):
    nombre: str | None = None
    apellido_paterno: str | None = None
    apellido_materno: str | None = None
    telefono: str | None = None
    curp: str | None = None

    @field_validator("curp")
    @classmethod
    def _validar_curp(cls, valor: str | None) -> str | None:
        if valor is not None and not _PATRON_CURP.match(valor):
            raise ValueError("CURP con formato inválido.")
        return valor


class UsuarioCambioEstadoPeticion(BaseModel):
    estado: str

    @field_validator("estado")
    @classmethod
    def _validar_estado(cls, valor: str) -> str:
        if valor not in ESTADOS_USUARIO:
            raise ValueError(f"Estado inválido: {valor}. Debe ser uno de {ESTADOS_USUARIO}.")
        return valor


class UsuarioRolesPeticion(BaseModel):
    roles: list[str] = Field(min_length=1)


class UsuarioCreadoRespuesta(BaseModel):
    usuario: UsuarioPublico
    contrasena_temporal: str


class ImportacionUsuariosFila(BaseModel):
    fila: int
    correo: str | None = None
    resultado: str  # "creado" | "error"
    contrasena_temporal: str | None = None
    error: str | None = None


class ImportacionUsuariosRespuesta(BaseModel):
    total_filas: int
    creados: int
    con_error: int
    detalle: list[ImportacionUsuariosFila]
