"""Modelo `Usuario` — ECA-003.

Identidad única de acceso al sistema ECA (técnico, administrador, enlace o
supervisor). Corrige `docs-eca/02_INVENTARIO_TECNICO.md` §4/§20: sin
contraseñas en texto plano y sin el doble `usuarios`/`admin_users` de
Sembrando Vida. Versión MVP de `05_MODELO_DATOS_ECA.md` §4.1: sin
`lote_importacion_id` todavía (se añade aditivamente en ECA-004/ECA-006).
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_base import Base

if TYPE_CHECKING:
    from app.models.rbac import UsuarioRol
    from app.models.token_refresco import TokenRefresco

ESTADOS_USUARIO = ("ACTIVO", "SUSPENDIDO", "BAJA")


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(f"estado IN {ESTADOS_USUARIO}", name="ck_usuarios_estado"),
        CheckConstraint(
            r"curp IS NULL OR curp ~ '^[A-Z]{4}\d{6}[A-Z]{6}[A-Z0-9]\d$'",
            name="ck_usuarios_curp_formato",
        ),
        Index("idx_usuarios_estado", "estado"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()")
    )
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    apellido_paterno: Mapped[str] = mapped_column(String, nullable=False)
    apellido_materno: Mapped[str | None] = mapped_column(String, nullable=True)
    correo: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    telefono: Mapped[str | None] = mapped_column(String, nullable=True)
    curp: Mapped[str | None] = mapped_column(String(18), unique=True, nullable=True)
    # Puesto/cargo del padrón oficial (Responsable de CEDA, Coordinadora
    # Estatal, etc.) — texto libre, solo informativo, sin catálogo propio.
    cargo: Mapped[str | None] = mapped_column(Text, nullable=True)

    contrasena_hash: Mapped[str] = mapped_column(String, nullable=False)
    algoritmo_hash: Mapped[str] = mapped_column(String, nullable=False, server_default="argon2id")
    requiere_cambio_contrasena: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    estado: Mapped[str] = mapped_column(String, nullable=False, server_default="ACTIVO")
    ultimo_acceso_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    actualizado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)

    tokens_refresco: Mapped[list["TokenRefresco"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )
    roles: Mapped[list["UsuarioRol"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", foreign_keys="UsuarioRol.usuario_id"
    )

    @property
    def esta_activo(self) -> bool:
        return self.estado == "ACTIVO"
