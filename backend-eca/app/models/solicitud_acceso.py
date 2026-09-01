"""Modelo `SolicitudAcceso` — ECA-020b (rediseño de la pantalla de registro).

`POST /solicitudes-acceso` (público, sin cuenta) ya escribía un evento de
auditoría, pero eso no era listable ni accionable desde `admin-eca` — el
técnico veía "el administrador la revisará" y no había ningún lugar donde
revisarla. Esta tabla es lo que le falta a esa promesa: cada solicitud
queda con un estado explícito (`pendiente`/`aprobada`/`rechazada`) para que
el panel las liste y el administrador decida, sin crear ninguna cuenta por
sí sola — el alta real sigue pasando por `POST /usuarios` (ECA-004).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db_base import Base

ESTADOS_SOLICITUD_ACCESO = ("pendiente", "aprobada", "rechazada")


class SolicitudAcceso(Base):
    __tablename__ = "solicitudes_acceso"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    correo: Mapped[str] = mapped_column(String, nullable=False)
    telefono: Mapped[str | None] = mapped_column(String, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    estado: Mapped[str] = mapped_column(String, nullable=False, server_default="pendiente")
    atendida_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    atendida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
