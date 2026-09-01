"""Modelo `AsignacionTecnicoEca` — ECA-009.

Relación N—M técnico↔ECA explícita, independiente de la pertenencia a
grupo (`03_MODELO_NEGOCIO_ECA_ACTUALIZADO.md` §6.5/§6.6). Fuente primaria
de "qué ECA ve un técnico" cuando existe — ver la REGLA DE ECA en
`app/services/asignaciones_service.py`.
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_base import Base

if TYPE_CHECKING:
    from app.models.eca import Eca
    from app.models.usuario import Usuario

ORIGENES_ASIGNACION = ("MANUAL", "IMPORTACION", "INSTITUCIONAL")


class AsignacionTecnicoEca(Base):
    __tablename__ = "asignaciones_tecnico_eca"
    __table_args__ = (
        CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio", name="ck_asignaciones_fecha_fin_valida"
        ),
        CheckConstraint(f"origen IN {ORIGENES_ASIGNACION}", name="ck_asignaciones_origen"),
        Index(
            "uq_ate_usuario_eca_activo", "usuario_id", "eca_id", unique=True, postgresql_where=text("activo")
        ),
        Index("idx_ate_usuario", "usuario_id", postgresql_where=text("activo")),
        Index("idx_ate_eca", "eca_id", postgresql_where=text("activo")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()")
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    eca_id: Mapped[int] = mapped_column(ForeignKey("ecas.id"), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False, server_default=text("current_date"))
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    activo: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    origen: Mapped[str] = mapped_column(Text, nullable=False, server_default="MANUAL")
    asignado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    lote_importacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("lotes_importacion.id"), nullable=True
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    actualizado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)

    usuario: Mapped["Usuario"] = relationship(foreign_keys=[usuario_id])
    eca: Mapped["Eca"] = relationship()
