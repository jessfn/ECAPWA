"""Modelo `Actividad` — ECA-013.

Unidad principal de evidencia del MVP (`03` §8). **No** lleva estado de
transmisión (§2.3 de `04_ARQUITECTURA_OBJETIVO.md`): `PENDIENTE`/
`SINCRONIZANDO`/`SINCRONIZADO`/`RECHAZADO` son estados **locales del
outbox** que vivirán en el cliente (ECA-016), no una columna aquí. Este
ticket es online: `creado_en_dispositivo`/`recibido_en` ya dejan la forma
lista para cuando el outbox exista, sin tener que migrar de nuevo.
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base


class Actividad(Base):
    __tablename__ = "actividades"
    __table_args__ = (
        CheckConstraint("num_participantes IS NULL OR num_participantes >= 0", name="ck_act_participantes"),
        CheckConstraint(
            "fecha_proximo_seguimiento IS NULL OR requiere_seguimiento",
            name="ck_act_seguimiento_coherente",
        ),
        CheckConstraint(
            "(latitud IS NULL) = (longitud IS NULL)", name="ck_act_coordenadas_par"
        ),
        Index("idx_act_usuario_fecha", "usuario_id", "fecha_hora"),
        Index("idx_act_jornada", "jornada_id"),
        Index("idx_act_eca", "eca_id"),
        Index("idx_act_tipo", "tipo_actividad_id"),
        Index("idx_act_tema", "tema_id"),
        Index("idx_act_sistema", "sistema_productivo_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()")
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    jornada_id: Mapped[int] = mapped_column(ForeignKey("jornadas.id"), nullable=False)
    eca_id: Mapped[int | None] = mapped_column(ForeignKey("ecas.id"), nullable=True)
    # Nombre de ECA escrito a mano por el técnico — cuando el tipo de
    # actividad requiere ECA pero no hay ninguna en su catálogo/ámbito
    # para seleccionar (`eca_id` se queda NULL en ese caso). Ver 0021.
    eca_nombre: Mapped[str | None] = mapped_column(Text, nullable=True)
    modalidad_id: Mapped[int] = mapped_column(ForeignKey("modalidades.id"), nullable=False)
    tipo_actividad_id: Mapped[int] = mapped_column(ForeignKey("tipos_actividad.id"), nullable=False)
    tema_id: Mapped[int | None] = mapped_column(ForeignKey("temas.id"), nullable=True)
    subtema_id: Mapped[int | None] = mapped_column(ForeignKey("subtemas.id"), nullable=True)
    sistema_productivo_id: Mapped[int | None] = mapped_column(
        ForeignKey("sistemas_productivos.id"), nullable=True
    )

    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    resultado: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # GPS: se llena en ECA-014, nullable desde ya.
    latitud: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitud: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    precision_gps_m: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    estado_gps: Mapped[str | None] = mapped_column(Text, nullable=True)

    num_participantes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requiere_seguimiento: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    fecha_proximo_seguimiento: Mapped[date_type | None] = mapped_column(nullable=True)

    # BOF (05 §1.3) — sin usar aún (flujo online), listo para ECA-016.
    dispositivo_id: Mapped[int | None] = mapped_column(nullable=True)
    creado_en_dispositivo: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recibido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sincronizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    origen: Mapped[str] = mapped_column(Text, nullable=False, server_default="APP")

    # BAE (05 §1.2)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    actualizado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)

    eliminado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
