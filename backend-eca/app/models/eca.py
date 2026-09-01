"""Modelo `Eca` — ECA-007.

Escuela de Campo: entidad central del sistema (`03_MODELO_NEGOCIO_ECA_ACTUALIZADO.md`
§6). `clave_fuente` es la clave de upsert de la importación masiva —
identificador estable del archivo institucional de origen; **nunca** se
deduplica por nombre/municipio (DP-2, `06` ECA-007). `localidad_nombre` es
texto libre a propósito en el MVP: `localidades` normalizadas quedan fuera
de alcance (`06` §0).
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_base import Base

if TYPE_CHECKING:
    from app.models.geo import Estado, Municipio


class Eca(Base):
    __tablename__ = "ecas"
    __table_args__ = (
        CheckConstraint(
            "(latitud IS NULL) = (longitud IS NULL)", name="ck_ecas_coordenadas_par"
        ),
        CheckConstraint(
            "fuente_carga IN ('MANUAL','IMPORTACION')", name="ck_ecas_fuente_carga"
        ),
        Index("idx_ecas_estado", "estado_id"),
        Index("idx_ecas_municipio", "municipio_id"),
        Index("idx_ecas_activo", "activo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()")
    )
    clave_fuente: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    clave_institucional: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    estado_id: Mapped[int] = mapped_column(ForeignKey("estados.id"), nullable=False)
    municipio_id: Mapped[int] = mapped_column(ForeignKey("municipios.id"), nullable=False)
    localidad_nombre: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitud: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitud: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    activo: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    fuente_carga: Mapped[str] = mapped_column(Text, nullable=False, server_default="MANUAL")
    lote_importacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("lotes_importacion.id"), nullable=True
    )
    metadatos: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    actualizado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    eliminado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    estado: Mapped["Estado"] = relationship()
    municipio: Mapped["Municipio"] = relationship()

    @property
    def esta_eliminada(self) -> bool:
        return self.eliminado_en is not None
