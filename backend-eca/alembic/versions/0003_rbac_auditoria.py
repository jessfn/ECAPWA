"""RBAC (roles, permisos, roles_permisos, usuarios_roles) y auditoria_eventos

Revisión: 0003
Revisión anterior: 0002

ECA-004. `auditoria_eventos` sin particionado (fuera del alcance MVP, `06` §0).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("clave", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("es_sistema", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.CheckConstraint(r"clave ~ '^[A-Z_]+$'", name="ck_roles_clave_formato"),
    )
    op.create_index("uq_roles_clave", "roles", ["clave"], unique=True)
    op.create_index("idx_roles_activo", "roles", ["activo"])

    op.create_table(
        "permisos",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("clave", sa.Text(), nullable=False),
        sa.Column("modulo", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.CheckConstraint(r"clave ~ '^[a-z_]+\.[a-z_]+$'", name="ck_permisos_clave_formato"),
    )
    op.create_index("uq_permisos_clave", "permisos", ["clave"], unique=True)
    op.create_index("idx_permisos_modulo", "permisos", ["modulo"])

    op.create_table(
        "roles_permisos",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("rol_id", sa.BigInteger(), nullable=False),
        sa.Column("permiso_id", sa.BigInteger(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["rol_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permiso_id"], ["permisos.id"]),
        sa.ForeignKeyConstraint(["creado_por"], ["usuarios.id"]),
    )
    op.create_index("uq_rp_rol_permiso", "roles_permisos", ["rol_id", "permiso_id"], unique=True)
    op.create_index("idx_rp_permiso", "roles_permisos", ["permiso_id"])

    op.create_table(
        "usuarios_roles",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("rol_id", sa.BigInteger(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "vigente_desde", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("vigente_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("asignado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rol_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["asignado_por"], ["usuarios.id"]),
    )
    op.create_index(
        "uq_ur_usuario_rol_activo",
        "usuarios_roles",
        ["usuario_id", "rol_id"],
        unique=True,
        postgresql_where=sa.text("activo"),
    )
    op.create_index(
        "idx_ur_usuario", "usuarios_roles", ["usuario_id"], postgresql_where=sa.text("activo")
    )

    op.create_table(
        "auditoria_eventos",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "ocurrido_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("actor_usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_rol", sa.Text(), nullable=True),
        sa.Column("origen", sa.Text(), nullable=False),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column("modulo", sa.Text(), nullable=False),
        sa.Column("entidad_tipo", sa.Text(), nullable=True),
        sa.Column("entidad_id", sa.BigInteger(), nullable=True),
        sa.Column("entidad_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("datos_antes", postgresql.JSONB(), nullable=True),
        sa.Column("datos_despues", postgresql.JSONB(), nullable=True),
        sa.Column("ip_hash", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("sesion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "origen IN ('BACKEND','PWA','ADMIN','WORKER','IMPORTACION')", name="ck_auditoria_origen"
        ),
        sa.ForeignKeyConstraint(["actor_usuario_id"], ["usuarios.id"]),
    )
    op.create_index("idx_aud_fecha", "auditoria_eventos", ["ocurrido_en"])
    op.create_index("idx_aud_actor", "auditoria_eventos", ["actor_usuario_id"])
    op.create_index("idx_aud_entidad", "auditoria_eventos", ["entidad_tipo", "entidad_id"])
    op.create_index("idx_aud_accion", "auditoria_eventos", ["accion"])
    op.create_index("idx_aud_modulo", "auditoria_eventos", ["modulo"])


def downgrade() -> None:
    op.drop_table("auditoria_eventos")
    op.drop_table("usuarios_roles")
    op.drop_table("roles_permisos")
    op.drop_table("permisos")
    op.drop_table("roles")
