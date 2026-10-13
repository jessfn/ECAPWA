"""Schemas Pydantic de notificaciones."""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TipoNotif = Literal["INFO", "EXITO", "ALERTA", "URGENTE"]


class NotificacionCrear(BaseModel):
    titulo: str = Field(min_length=1, max_length=160)
    subtitulo: str | None = Field(default=None, max_length=200)
    descripcion: str | None = Field(default=None, max_length=5000)
    url: str | None = Field(default=None, max_length=2000)
    url_texto: str | None = Field(default=None, max_length=60)
    tipo: TipoNotif = "INFO"
    destino: Literal["TODOS", "USUARIO"] = "TODOS"
    usuario_destino_id: int | None = None
    # Fechas con zona; si llegan SIN zona se interpretan como hora de CDMX.
    programada_para: datetime | None = None
    expira_en: datetime | None = None
    adjuntos: list[uuid_lib.UUID] = Field(default_factory=list, max_length=12)


class AdjuntoPublico(BaseModel):
    uuid: uuid_lib.UUID
    tipo: str
    mime: str
    nombre_original: str | None
    tamano_bytes: int
    url: str


class NotificacionAdmin(BaseModel):
    uuid: uuid_lib.UUID
    titulo: str
    subtitulo: str | None
    descripcion: str | None
    url: str | None
    url_texto: str | None
    tipo: str
    destino: str
    destinatario: str | None
    estado: str
    programada_para: datetime | None
    publicada_en: datetime | None
    expira_en: datetime | None
    vigente: bool
    destinatarios_total: int | None
    leidas: int
    push_enviados: int
    creado_por: str | None
    creado_en: datetime
    adjuntos: list[AdjuntoPublico]


class NotificacionUsuario(BaseModel):
    uuid: uuid_lib.UUID
    titulo: str
    subtitulo: str | None
    descripcion: str | None
    url: str | None
    url_texto: str | None
    tipo: str
    publicada_en: datetime
    expira_en: datetime | None
    leida: bool
    adjuntos: list[AdjuntoPublico]


class BandejaRespuesta(BaseModel):
    notificaciones: list[NotificacionUsuario]
    no_leidas: int
    # Hora del servidor: la PWA la usa como marca `desde` de la siguiente consulta.
    ahora: datetime


class SubidaIniciar(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    mime: str = Field(max_length=100)
    tamano: int = Field(gt=0)
    total_partes: int = Field(gt=0, le=400)


class SubidaIniciada(BaseModel):
    subida_id: uuid_lib.UUID
    tamano_parte_max: int


class DestinatarioBasico(BaseModel):
    id: int
    nombre: str
    correo: str


class PushClave(BaseModel):
    clave: str | None


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=300)
    auth: str = Field(min_length=1, max_length=300)


class PushSuscripcion(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2000)
    keys: PushKeys


class PushDesuscribir(BaseModel):
    endpoint: str = Field(min_length=10, max_length=2000)
