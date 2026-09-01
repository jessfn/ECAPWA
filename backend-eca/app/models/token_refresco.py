"""Modelo `TokenRefresco` — ECA-003.

Persistencia y revocación de refresh tokens (`04_ARQUITECTURA_OBJETIVO.md`
§6). Corrige el "JWT sin expiración" de Sembrando Vida
(`02_INVENTARIO_TECNICO.md` §4/§20): nunca se guarda el token en claro, solo
su hash, y cada uno es revocable individualmente.
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_base import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class TokenRefresco(Base):
    __tablename__ = "tokens_refresco"
    __table_args__ = (
        CheckConstraint("expira_en > emitido_en", name="ck_tokens_refresco_expira_despues_emitido"),
        Index("idx_tr_usuario_activo", "usuario_id", postgresql_where=text("revocado_en IS NULL")),
        Index("idx_tr_expira", "expira_en"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[uuid_lib.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    hash_token: Mapped[str] = mapped_column(String, nullable=False)

    emitido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revocado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_revocacion: Mapped[str | None] = mapped_column(String, nullable=True)

    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    usuario: Mapped["Usuario"] = relationship(back_populates="tokens_refresco")

    @property
    def esta_revocado(self) -> bool:
        return self.revocado_en is not None
