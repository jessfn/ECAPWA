"""Modelo `Jornada` — ECA-012.

Marco temporal de las actividades de un técnico (`03` §7): una jornada
principal por técnico por fecha. Sin foto ni descripción obligatorias; GPS
opcional en inicio y cierre. La tabla lleva BOF (para que ECA-016 pueda
crearla/cerrarla desde el outbox sin migración adicional) aunque en este
ticket el flujo es online — ver docstring del router.
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base


class Jornada(Base):
    __tablename__ = "jornadas"
    __table_args__ = (
        CheckConstraint("estado IN ('ABIERTA','CERRADA','ANULADA')", name="ck_jornadas_estado"),
        CheckConstraint(
            "fin_en IS NULL OR fin_en >= inicio_en", name="ck_jornadas_fin_despues_de_inicio"
        ),
        CheckConstraint(
            "(latitud_inicio IS NULL) = (longitud_inicio IS NULL)",
            name="ck_jornadas_coordenadas_inicio_par",
        ),
        CheckConstraint(
            "(latitud_fin IS NULL) = (longitud_fin IS NULL)", name="ck_jornadas_coordenadas_fin_par"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()")
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(Text, nullable=False, server_default="ABIERTA")

    inicio_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latitud_inicio: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitud_inicio: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    precision_gps_inicio_m: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    estado_gps_inicio: Mapped[str | None] = mapped_column(Text, nullable=True)

    fin_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latitud_fin: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitud_fin: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    precision_gps_fin_m: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    estado_gps_fin: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Detalle escrito por el técnico — pedido explícito de que iniciar y
    # terminar jornada pidan obligatoriamente un detalle cada uno; una sola
    # columna no alcanza porque el cierre no debe borrar el texto de inicio.
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    nota_fin: Mapped[str | None] = mapped_column(Text, nullable=True)

    # BOF (05 §1.3) — no se usa aún en este ticket (flujo online), pero deja
    # la tabla lista para que ECA-016 la escriba desde el outbox sin migrar
    # de nuevo.
    dispositivo_id: Mapped[int | None] = mapped_column(nullable=True)
    creado_en_dispositivo: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
