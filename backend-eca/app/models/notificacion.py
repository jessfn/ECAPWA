"""Modelos del sistema de notificaciones (admin -> técnicos de la PWA).

- `Notificacion`: contenido + destino (TODOS los técnicos o UN técnico) +
  vigencia. Las fechas se guardan en UTC (timestamptz); el panel y la PWA las
  capturan y muestran en horario de la Ciudad de México.
- `programada_para`: si es NULL se publica al instante; si no, un proceso de
  fondo la publica cuando llega la hora.
- `expira_en`: NULL = indefinida; si no, deja de mostrarse al llegar la fecha.
- `NotificacionAdjunto`: imagen o video (solo la clave de Storage, nunca el
  archivo en la fila).
- `NotificacionLectura`: una fila por (notificación, técnico) solo cuando la
  lee; así el envío a "todos" es UNA sola escritura.
- `SuscripcionPush`: suscripción Web Push de un dispositivo del técnico.
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db_base import Base

TIPOS_NOTIFICACION = ("INFO", "EXITO", "ALERTA", "URGENTE")
DESTINOS_NOTIFICACION = ("TODOS", "USUARIO")
ESTADOS_NOTIFICACION = ("PROGRAMADA", "PUBLICADA", "RETIRADA")


class Notificacion(Base):
    __tablename__ = "notificaciones"
    __table_args__ = (
        CheckConstraint(f"tipo IN {TIPOS_NOTIFICACION}", name="ck_notif_tipo"),
        CheckConstraint(f"destino IN {DESTINOS_NOTIFICACION}", name="ck_notif_destino"),
        CheckConstraint(f"estado IN {ESTADOS_NOTIFICACION}", name="ck_notif_estado"),
        CheckConstraint(
            "(destino = 'USUARIO') = (usuario_destino_id IS NOT NULL)", name="ck_notif_destino_usuario"
        ),
        Index("idx_notif_estado_prog", "estado", "programada_para"),
        Index("idx_notif_publicada", "publicada_en"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()")
    )
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    subtitulo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_texto: Mapped[str | None] = mapped_column(String(60), nullable=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False, server_default="INFO")

    destino: Mapped[str] = mapped_column(String, nullable=False, server_default="TODOS")
    usuario_destino_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)

    estado: Mapped[str] = mapped_column(String, nullable=False, server_default="PUBLICADA")
    programada_para: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publicada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expira_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retirada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Borrado lógico: una notificación retirada puede eliminarse del historial.
    eliminada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    destinatarios_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    push_enviados: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    creado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    adjuntos: Mapped[list["NotificacionAdjunto"]] = relationship(
        back_populates="notificacion", cascade="all, delete-orphan", order_by="NotificacionAdjunto.orden"
    )


class NotificacionAdjunto(Base):
    __tablename__ = "notificaciones_adjuntos"
    __table_args__ = (
        CheckConstraint("tipo IN ('IMAGEN', 'VIDEO')", name="ck_notif_adj_tipo"),
        Index("idx_notif_adj_notif", "notificacion_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()")
    )
    # NULL mientras el adjunto está subido pero aún no se envía la notificación.
    notificacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("notificaciones.id", ondelete="CASCADE"), nullable=True
    )
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    mime: Mapped[str] = mapped_column(String, nullable=False)
    nombre_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_clave: Mapped[str] = mapped_column(Text, nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    subido_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    notificacion: Mapped["Notificacion | None"] = relationship(back_populates="adjuntos")


class NotificacionLectura(Base):
    __tablename__ = "notificaciones_lecturas"
    __table_args__ = (Index("uq_notif_lect", "notificacion_id", "usuario_id", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    notificacion_id: Mapped[int] = mapped_column(
        ForeignKey("notificaciones.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    leida_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class SuscripcionPush(Base):
    __tablename__ = "suscripciones_push"
    __table_args__ = (Index("idx_push_usuario", "usuario_id", postgresql_where=text("activo")),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    ultimo_exito_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
