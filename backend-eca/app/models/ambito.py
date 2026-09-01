"""Modelo `AmbitoTecnico` — ECA-008.

Ámbito geográfico de trabajo del técnico: uno o varios municipios
(`03_MODELO_NEGOCIO_ECA_ACTUALIZADO.md` §6.4). **No** es una columna
`municipio` en `usuarios` — es una relación N:M con vigencia, para que un
técnico pueda tener varios municipios y el historial se conserve al quitar
alguno (baja lógica con `fecha_fin`, nunca borrado físico).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_base import Base

if TYPE_CHECKING:
    from app.models.geo import Municipio
    from app.models.usuario import Usuario


class AmbitoTecnico(Base):
    __tablename__ = "ambitos_tecnico"
    __table_args__ = (
        CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio", name="ck_ambitos_fecha_fin_valida"
        ),
        Index("uq_amb_usuario_municipio_activo", "usuario_id", "municipio_id", unique=True, postgresql_where=text("activo")),
        Index("idx_amb_usuario", "usuario_id", postgresql_where=text("activo")),
        Index("idx_amb_municipio", "municipio_id", postgresql_where=text("activo")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    municipio_id: Mapped[int] = mapped_column(ForeignKey("municipios.id"), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False, server_default=text("current_date"))
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    asignado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    actualizado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)

    usuario: Mapped["Usuario"] = relationship(foreign_keys=[usuario_id])
    municipio: Mapped["Municipio"] = relationship()
