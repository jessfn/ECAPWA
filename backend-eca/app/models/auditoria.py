"""Modelo `AuditoriaEvento` — ECA-004.

Bitácora append-only de acciones de escritura relevantes
(`04_ARQUITECTURA_OBJETIVO.md` §6). Rediseño de `sys_telemetry` de
Sembrando Vida, sin secretos hardcodeados. Versión MVP de
`05_MODELO_DATOS_ECA.md` §4.10: sin particionado todavía (se añade si hace
falta por volumen, fuera del alcance de ECA-004).

`datos_antes`/`datos_despues` deben llegar ya saneados (ver
`app/core/audit.py::sanear_datos_auditoria`) — este modelo no sanea nada por
su cuenta.
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base

ORIGENES_AUDITORIA = ("BACKEND", "PWA", "ADMIN", "WORKER", "IMPORTACION")


class AuditoriaEvento(Base):
    __tablename__ = "auditoria_eventos"
    __table_args__ = (
        CheckConstraint(f"origen IN {ORIGENES_AUDITORIA}", name="ck_auditoria_origen"),
        Index("idx_aud_fecha", "ocurrido_en"),
        Index("idx_aud_actor", "actor_usuario_id"),
        Index("idx_aud_entidad", "entidad_tipo", "entidad_id"),
        Index("idx_aud_accion", "accion"),
        Index("idx_aud_modulo", "modulo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ocurrido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actor_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    actor_rol: Mapped[str | None] = mapped_column(String, nullable=True)
    origen: Mapped[str] = mapped_column(String, nullable=False)
    accion: Mapped[str] = mapped_column(String, nullable=False)
    modulo: Mapped[str] = mapped_column(String, nullable=False)
    entidad_tipo: Mapped[str | None] = mapped_column(String, nullable=True)
    entidad_id: Mapped[int | None] = mapped_column(nullable=True)
    entidad_uuid: Mapped[uuid_lib.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    datos_antes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    datos_despues: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    sesion_id: Mapped[uuid_lib.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
