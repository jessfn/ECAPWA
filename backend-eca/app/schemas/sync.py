"""Schemas Pydantic de sincronización — ECA-017/ECA-018."""
from __future__ import annotations

import uuid as uuid_lib
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.gps import GpsPeticion


class DispositivoPeticion(BaseModel):
    uuid: uuid_lib.UUID
    plataforma: str | None = None
    user_agent: str | None = None


class DispositivoPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: uuid_lib.UUID
    plataforma: str | None
    user_agent: str | None


class JornadaSyncItem(BaseModel):
    uuid: uuid_lib.UUID
    inicio_en: datetime
    gps_inicio: GpsPeticion | None = None
    # Detalle obligatorio de inicio — validado de nuevo en
    # `sync_service._procesar_jornada` (aquí solo se exige no-vacío en
    # cuanto al *formato*; la regla de negocio vive en el servicio, igual
    # que el resto de reglas de jornadas/actividades).
    nota: str = Field(min_length=1)
    fin_en: datetime | None = None
    gps_fin: GpsPeticion | None = None
    # Solo obligatorio cuando `fin_en` viene en el mismo item (un push de
    # solo-inicio no cierra nada, así que no tiene nota de cierre todavía).
    nota_fin: str | None = None


class ActividadSyncItem(BaseModel):
    uuid: uuid_lib.UUID
    jornada_uuid: uuid_lib.UUID
    eca_id: int | None = None
    modalidad_id: int
    tipo_actividad_id: int
    tema_id: int | None = None
    subtema_id: int | None = None
    sistema_productivo_id: int | None = None
    descripcion: str = Field(min_length=1)
    resultado: str | None = None
    fecha_hora: datetime
    num_participantes: int | None = None
    requiere_seguimiento: bool = False
    fecha_proximo_seguimiento: date | None = None
    gps: GpsPeticion | None = None


class SyncPushPeticion(BaseModel):
    dispositivo_uuid: uuid_lib.UUID
    jornadas: list[JornadaSyncItem] = Field(default_factory=list)
    actividades: list[ActividadSyncItem] = Field(default_factory=list)


class ResultadoSync(BaseModel):
    uuid: uuid_lib.UUID
    # Resultado de TRANSMISIÓN (§2.3) — nunca se guarda como estado de
    # negocio de `jornadas`/`actividades`.
    resultado: str  # 'APLICADO' | 'DUPLICADO' | 'RECHAZADO'
    id: int | None = None
    error: str | None = None


class SyncPushRespuesta(BaseModel):
    resultados: list[ResultadoSync]


# --- ECA-018: bootstrap y pull (lectura offline) ----------------------------


class CatalogoItemPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clave: str
    nombre: str
    orden: int


class TipoActividadPublicoSync(CatalogoItemPublico):
    requiere_evidencia: bool
    min_fotos: int
    max_fotos: int
    permite_participantes: bool
    requiere_eca: bool


class SubtemaPublicoSync(CatalogoItemPublico):
    tema_id: int


class CatalogosBootstrap(BaseModel):
    modalidades: list[CatalogoItemPublico]
    tipos_actividad: list[TipoActividadPublicoSync]
    temas: list[CatalogoItemPublico]
    subtemas: list[SubtemaPublicoSync]
    sistemas_productivos: list[CatalogoItemPublico]


class EstadoPublicoSync(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class MunicipioPublicoSync(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado_id: int
    nombre: str


class GeoBootstrap(BaseModel):
    estados: list[EstadoPublicoSync]
    municipios: list[MunicipioPublicoSync]


class EcaBootstrap(BaseModel):
    eca_id: int
    eca_uuid: uuid_lib.UUID
    eca_nombre: str
    municipio_id: int
    origen: str
    activo: bool = True


class ConfigBootstrap(BaseModel):
    regla_disponibilidad: str
    gps_precision_maxima_m: Any
    eca_max_offline: Any
    sesion_offline_dias: int


class BootstrapRespuesta(BaseModel):
    generado_en: datetime
    catalogos: CatalogosBootstrap
    geo: GeoBootstrap
    ambito: list[int]
    ecas: list[EcaBootstrap]
    config: ConfigBootstrap
    aviso: str | None = None
