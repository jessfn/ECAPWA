"""Modelos de catálogos geográficos — ECA-006.

`estados` y `municipios`: estado y municipio no son texto libre
(`03_MODELO_NEGOCIO_ECA_ACTUALIZADO.md` §6.2). Sin `localidades` en el MVP
(`06` §0). Semilla oficial INEGI — ver `data/inegi/FUENTE.md`.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CHAR, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_base import Base

if TYPE_CHECKING:
    pass


class Estado(Base):
    __tablename__ = "estados"

    id: Mapped[int] = mapped_column(primary_key=True)
    clave_inegi: Mapped[str] = mapped_column(CHAR(2), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    abreviatura: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    municipios: Mapped[list["Municipio"]] = relationship(back_populates="estado")


class Municipio(Base):
    __tablename__ = "municipios"
    __table_args__ = (
        Index("idx_municipios_estado", "estado_id"),
        Index("uq_municipios_estado_nombre", "estado_id", "nombre", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    estado_id: Mapped[int] = mapped_column(ForeignKey("estados.id"), nullable=False)
    clave_inegi: Mapped[str] = mapped_column(CHAR(5), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    estado: Mapped["Estado"] = relationship(back_populates="municipios")
