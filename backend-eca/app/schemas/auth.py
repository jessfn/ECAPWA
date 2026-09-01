"""Schemas Pydantic de autenticación — ECA-003."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.usuario import UsuarioPublico


class LoginPeticion(BaseModel):
    correo: str
    contrasena: str = Field(min_length=1)


class TokenRespuesta(BaseModel):
    access_token: str
    refresh_token: str
    tipo_token: str = "bearer"
    expira_en: datetime


class RefreshPeticion(BaseModel):
    refresh_token: str


class LogoutPeticion(BaseModel):
    refresh_token: str


class CambioContrasenaPeticion(BaseModel):
    contrasena_actual: str
    contrasena_nueva: str


class MeRespuesta(BaseModel):
    usuario: UsuarioPublico
    permisos: list[str] = Field(default_factory=list)
