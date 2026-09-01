"""Modelo `LoteImportacion` — ECA-007.

Cabecera de una carga masiva (por ahora solo `ECA`; usuarios/asignaciones
reusarán esta misma tabla en tickets posteriores). Una sola tabla, sin
`errores_importacion` separada (`06` ticket ECA-007): los errores por fila
y las filas válidas ya parseadas viven en `resumen` (jsonb) mientras el lote
está `VALIDADO`, a la espera de que el admin confirme o cancele.
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base

TIPOS_LOTE = ("ECA", "USUARIOS", "ASIGNACIONES_TECNICO_ECA", "AMBITOS")
ESTADOS_LOTE = ("PROCESANDO", "VALIDADO", "CONFIRMADO", "CANCELADO", "ERROR")


class LoteImportacion(Base):
    __tablename__ = "lotes_importacion"
    __table_args__ = (
        CheckConstraint(f"tipo IN {TIPOS_LOTE}", name="ck_lotes_tipo"),
        CheckConstraint(f"estado IN {ESTADOS_LOTE}", name="ck_lotes_estado"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()")
    )
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    archivo_nombre: Mapped[str] = mapped_column(Text, nullable=False)
    total_filas: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    filas_validas: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    filas_con_error: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    estado: Mapped[str] = mapped_column(String, nullable=False, server_default="PROCESANDO")
    resumen: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    confirmado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
