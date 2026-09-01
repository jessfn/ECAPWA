"""Identidad y autenticación: usuarios, tokens_refresco

Revisión: 0002
Revisión anterior: 0001

ECA-003. Versión MVP de `docs-eca/05_MODELO_DATOS_ECA.md` §4.1: sin
`lote_importacion_id` todavía (se añade aditivamente en ECA-004/ECA-006).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("apellido_paterno", sa.Text(), nullable=False),
        sa.Column("apellido_materno", sa.Text(), nullable=True),
        sa.Column("correo", postgresql.CITEXT(), nullable=False),
        sa.Column("telefono", sa.Text(), nullable=True),
        sa.Column("curp", sa.CHAR(18), nullable=True),
        sa.Column("contrasena_hash", sa.Text(), nullable=False),
        sa.Column("algoritmo_hash", sa.Text(), nullable=False, server_default="argon2id"),
        sa.Column(
            "requiere_cambio_contrasena", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("estado", sa.Text(), nullable=False, server_default="ACTIVO"),
        sa.Column("ultimo_acceso_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("actualizado_por", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("estado IN ('ACTIVO','SUSPENDIDO','BAJA')", name="ck_usuarios_estado"),
        sa.CheckConstraint(
            r"curp IS NULL OR curp ~ '^[A-Z]{4}\d{6}[A-Z]{6}[A-Z0-9]\d$'",
            name="ck_usuarios_curp_formato",
        ),
        sa.ForeignKeyConstraint(["creado_por"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["actualizado_por"], ["usuarios.id"]),
    )
    op.create_index("uq_usuarios_uuid", "usuarios", ["uuid"], unique=True)
    op.create_index("uq_usuarios_correo", "usuarios", ["correo"], unique=True)
    op.create_index(
        "uq_usuarios_curp",
        "usuarios",
        ["curp"],
        unique=True,
        postgresql_where=sa.text("curp IS NOT NULL"),
    )
    op.create_index("idx_usuarios_estado", "usuarios", ["estado"])

    op.create_table(
        "tokens_refresco",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("jti", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("hash_token", sa.Text(), nullable=False),
        sa.Column(
            "emitido_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_revocacion", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_hash", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "expira_en > emitido_en", name="ck_tokens_refresco_expira_despues_emitido"
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
    )
    op.create_index("uq_tokens_refresco_jti", "tokens_refresco", ["jti"], unique=True)
    op.create_index(
        "idx_tr_usuario_activo",
        "tokens_refresco",
        ["usuario_id"],
        postgresql_where=sa.text("revocado_en IS NULL"),
    )
    op.create_index("idx_tr_expira", "tokens_refresco", ["expira_en"])


def downgrade() -> None:
    op.drop_table("tokens_refresco")
    op.drop_table("usuarios")
