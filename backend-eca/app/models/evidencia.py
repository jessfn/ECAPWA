"""Modelo `ActividadEvidencia` — ECA-015.

Foto de evidencia de una actividad. `hash_sha256` es solo para
idempotencia/integridad (reintento de subida no duplica) — **no** hay
`hash_perceptual`/pHash en el MVP (fuera de alcance explícito del ticket).
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base


class ActividadEvidencia(Base):
    __tablename__ = "actividades_evidencias"
    __table_args__ = (
        CheckConstraint("orden BETWEEN 1 AND 3", name="ck_ev_orden"),
        CheckConstraint("(latitud IS NULL) = (longitud IS NULL)", name="ck_ev_coordenadas_par"),
        UniqueConstraint("actividad_id", "orden", name="uq_ev_actividad_orden"),
        Index("idx_ev_actividad", "actividad_id"),
        Index("idx_ev_sha", "hash_sha256"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()")
    )
    actividad_id: Mapped[int] = mapped_column(ForeignKey("actividades.id"), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_clave: Mapped[str] = mapped_column(Text, nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str] = mapped_column(Text, nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    hash_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    latitud: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitud: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    capturada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sincronizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
