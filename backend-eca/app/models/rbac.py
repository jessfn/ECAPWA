"""Modelos RBAC — ECA-004.

`roles`, `permisos`, `roles_permisos` (catálogos, sin borrado físico:
`activo`), `usuarios_roles` (asignación con vigencia). Autorización
resuelta siempre en backend (`04_ARQUITECTURA_OBJETIVO.md` §6) — corrige
`02_INVENTARIO_TECNICO.md` §6: en Sembrando Vida la autorización es 100 %
del cliente.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_base import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class Rol(Base):
    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint(r"clave ~ '^[A-Z_]+$'", name="ck_roles_clave_formato"),
        Index("idx_roles_activo", "activo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    es_sistema: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    permisos: Mapped[list["RolPermiso"]] = relationship(back_populates="rol", cascade="all, delete-orphan")


class Permiso(Base):
    __tablename__ = "permisos"
    __table_args__ = (
        CheckConstraint(r"clave ~ '^[a-z_]+\.[a-z_]+$'", name="ck_permisos_clave_formato"),
        Index("idx_permisos_modulo", "modulo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    modulo: Mapped[str] = mapped_column(String, nullable=False)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class RolPermiso(Base):
    __tablename__ = "roles_permisos"
    __table_args__ = (Index("uq_rp_rol_permiso", "rol_id", "permiso_id", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permiso_id: Mapped[int] = mapped_column(ForeignKey("permisos.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)

    rol: Mapped["Rol"] = relationship(back_populates="permisos")
    permiso: Mapped["Permiso"] = relationship()


class UsuarioRol(Base):
    __tablename__ = "usuarios_roles"
    __table_args__ = (
        Index("uq_ur_usuario_rol_activo", "usuario_id", "rol_id", unique=True, postgresql_where=text("activo")),
        Index("idx_ur_usuario", "usuario_id", postgresql_where=text("activo")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    vigente_desde: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    vigente_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    asignado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="roles", foreign_keys=[usuario_id])
    rol: Mapped["Rol"] = relationship()
