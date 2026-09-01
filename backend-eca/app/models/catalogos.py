"""Catálogos de actividad — ECA-010.

`modalidades`, `tipos_actividad`, `temas`, `subtemas`, `sistemas_productivos`
(`05_MODELO_DATOS_ECA.md` §4.7). Corrige `02_INVENTARIO_TECNICO.md` §12:
en Sembrando Vida estas categorías están hardcodeadas y duplicadas en
código; aquí son catálogos persistidos, activables/editables sin desplegar.

La obligatoriedad de evidencia fotográfica es **por tipo de actividad**
(`requiere_evidencia`/`min_fotos`/`max_fotos`), nunca una regla global.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_base import Base

if TYPE_CHECKING:
    pass


class Modalidad(Base):
    __tablename__ = "modalidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    orden: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class TipoActividad(Base):
    __tablename__ = "tipos_actividad"
    __table_args__ = (
        CheckConstraint("min_fotos BETWEEN 0 AND 3", name="ck_tipos_actividad_min_fotos"),
        CheckConstraint("max_fotos BETWEEN min_fotos AND 3", name="ck_tipos_actividad_max_fotos"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    orden: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    requiere_evidencia: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    min_fotos: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    max_fotos: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    permite_participantes: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    requiere_eca: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Tema(Base):
    __tablename__ = "temas"

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    orden: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    subtemas: Mapped[list["Subtema"]] = relationship(back_populates="tema")


class Subtema(Base):
    __tablename__ = "subtemas"
    __table_args__ = (Index("uq_subtemas_tema_clave", "tema_id", "clave", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tema_id: Mapped[int] = mapped_column(ForeignKey("temas.id"), nullable=False)
    clave: Mapped[str] = mapped_column(Text, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    orden: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    tema: Mapped["Tema"] = relationship(back_populates="subtemas")


class SistemaProductivo(Base):
    __tablename__ = "sistemas_productivos"

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    orden: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
