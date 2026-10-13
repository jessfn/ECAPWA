"""Sistema de notificaciones (admin -> técnicos) + permisos

Revisión: 0030
Revisión anterior: 0029
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030"
down_revision: Union[str, None] = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISOS = [
    ("vista.notificaciones", "vistas", "Ver vista: Notificaciones"),
    ("notificaciones.enviar", "notificaciones", "Enviar y programar notificaciones"),
    ("notificaciones.retirar", "notificaciones", "Retirar notificaciones enviadas"),
]


def upgrade() -> None:
    op.create_table(
        "notificaciones",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()"), unique=True),
        sa.Column("titulo", sa.String(160), nullable=False),
        sa.Column("subtitulo", sa.String(200)),
        sa.Column("descripcion", sa.Text),
        sa.Column("url", sa.Text),
        sa.Column("url_texto", sa.String(60)),
        sa.Column("tipo", sa.String, nullable=False, server_default="INFO"),
        sa.Column("destino", sa.String, nullable=False, server_default="TODOS"),
        sa.Column("usuario_destino_id", sa.BigInteger, sa.ForeignKey("usuarios.id")),
        sa.Column("estado", sa.String, nullable=False, server_default="PUBLICADA"),
        sa.Column("programada_para", sa.DateTime(timezone=True)),
        sa.Column("publicada_en", sa.DateTime(timezone=True)),
        sa.Column("expira_en", sa.DateTime(timezone=True)),
        sa.Column("retirada_en", sa.DateTime(timezone=True)),
        sa.Column("destinatarios_total", sa.Integer),
        sa.Column("push_enviados", sa.Integer, nullable=False, server_default="0"),
        sa.Column("creado_por", sa.BigInteger, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("tipo IN ('INFO', 'EXITO', 'ALERTA', 'URGENTE')", name="ck_notif_tipo"),
        sa.CheckConstraint("destino IN ('TODOS', 'USUARIO')", name="ck_notif_destino"),
        sa.CheckConstraint("estado IN ('PROGRAMADA', 'PUBLICADA', 'RETIRADA')", name="ck_notif_estado"),
        sa.CheckConstraint("(destino = 'USUARIO') = (usuario_destino_id IS NOT NULL)", name="ck_notif_destino_usuario"),
    )
    op.create_index("idx_notif_estado_prog", "notificaciones", ["estado", "programada_para"])
    op.create_index("idx_notif_publicada", "notificaciones", ["publicada_en"])

    op.create_table(
        "notificaciones_adjuntos",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()"), unique=True),
        sa.Column("notificacion_id", sa.BigInteger, sa.ForeignKey("notificaciones.id", ondelete="CASCADE")),
        sa.Column("tipo", sa.String, nullable=False),
        sa.Column("mime", sa.String, nullable=False),
        sa.Column("nombre_original", sa.Text),
        sa.Column("storage_clave", sa.Text, nullable=False),
        sa.Column("tamano_bytes", sa.BigInteger, nullable=False),
        sa.Column("orden", sa.Integer, nullable=False, server_default="0"),
        sa.Column("subido_por", sa.BigInteger, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("tipo IN ('IMAGEN', 'VIDEO')", name="ck_notif_adj_tipo"),
    )
    op.create_index("idx_notif_adj_notif", "notificaciones_adjuntos", ["notificacion_id"])

    op.create_table(
        "notificaciones_lecturas",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("notificacion_id", sa.BigInteger, sa.ForeignKey("notificaciones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leida_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("uq_notif_lect", "notificaciones_lecturas", ["notificacion_id", "usuario_id"], unique=True)

    op.create_table(
        "suscripciones_push",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.Text, nullable=False, unique=True),
        sa.Column("p256dh", sa.Text, nullable=False),
        sa.Column("auth", sa.Text, nullable=False),
        sa.Column("user_agent", sa.Text),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ultimo_exito_en", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_push_usuario", "suscripciones_push", ["usuario_id"], postgresql_where=sa.text("activo"))

    conn = op.get_bind()
    permisos = sa.table(
        "permisos",
        sa.column("id", sa.BigInteger),
        sa.column("clave", sa.Text),
        sa.column("modulo", sa.Text),
        sa.column("nombre", sa.Text),
        sa.column("activo", sa.Boolean),
    )
    roles = sa.table("roles", sa.column("id", sa.BigInteger), sa.column("clave", sa.Text))
    roles_permisos = sa.table(
        "roles_permisos", sa.column("rol_id", sa.BigInteger), sa.column("permiso_id", sa.BigInteger)
    )
    id_admin = conn.execute(sa.select(roles.c.id).where(roles.c.clave == "ADMIN")).scalar_one()
    for clave, modulo, nombre in PERMISOS:
        pid = conn.execute(sa.select(permisos.c.id).where(permisos.c.clave == clave)).scalar_one_or_none()
        if pid is None:
            pid = conn.execute(
                sa.insert(permisos)
                .values(clave=clave, modulo=modulo, nombre=nombre, activo=True)
                .returning(permisos.c.id)
            ).scalar_one()
        ya = conn.execute(
            sa.select(roles_permisos.c.rol_id).where(
                roles_permisos.c.rol_id == id_admin, roles_permisos.c.permiso_id == pid
            )
        ).first()
        if ya is None:
            conn.execute(sa.insert(roles_permisos).values(rol_id=id_admin, permiso_id=pid))


def downgrade() -> None:
    conn = op.get_bind()
    claves = [c for c, _, _ in PERMISOS]
    for tabla in ("roles_permisos", "usuarios_permisos"):
        conn.execute(
            sa.text(f"DELETE FROM {tabla} WHERE permiso_id IN (SELECT id FROM permisos WHERE clave = ANY(:c))"),
            {"c": claves},
        )
    conn.execute(sa.text("DELETE FROM permisos WHERE clave = ANY(:c)"), {"c": claves})
    op.drop_table("suscripciones_push")
    op.drop_table("notificaciones_lecturas")
    op.drop_table("notificaciones_adjuntos")
    op.drop_table("notificaciones")
