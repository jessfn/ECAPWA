"""Modelo `ParametroConfig` — ECA-009.

Tabla clave-valor **acotada** para reglas operativas que de otro modo
quedarían hardcodeadas (`05_MODELO_DATOS_ECA.md` §4.6, `03` §26/§27). No es
un motor de reglas genérico: solo claves conocidas y documentadas.

Se crea aquí (no en un ticket anterior) porque ECA-009 es el primer ticket
que necesita de verdad una clave real: `eca.regla_disponibilidad`, que
`GET /usuarios/me/ecas` debe poder cambiar **sin desplegar código**
(criterio de aceptación del ticket).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base

TIPOS_DATO = ("BOOLEAN", "ENTERO", "TEXTO", "LISTA", "OBJETO")


class ParametroConfig(Base):
    __tablename__ = "parametros_config"
    __table_args__ = (CheckConstraint(f"tipo_dato IN {TIPOS_DATO}", name="ck_parametros_tipo_dato"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    clave: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    valor: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tipo_dato: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    editable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
