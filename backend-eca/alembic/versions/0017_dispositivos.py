"""Dispositivos

Revisión: 0017
Revisión anterior: 0016

ECA-017. El ticket sugiere el número `0015`, ya tomado por
`0015_seed_parametro_gps.py` (ECA-014) — renumerado a `0017` siguiendo la
secuencia real de migraciones aplicadas.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dispositivos",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("plataforma", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
    )
    op.create_index("uq_dispositivos_uuid", "dispositivos", ["uuid"], unique=True)
    op.create_index("idx_disp_usuario", "dispositivos", ["usuario_id"])


def downgrade() -> None:
    op.drop_table("dispositivos")
