"""Asignaciones directas técnico-ECA

Revisión: 0010
Revisión anterior: 0009

ECA-009.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "asignaciones_tecnico_eca",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("eca_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False, server_default=sa.text("current_date")),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("origen", sa.Text(), nullable=False, server_default="MANUAL"),
        sa.Column("asignado_por", sa.BigInteger(), nullable=True),
        sa.Column("lote_importacion_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("actualizado_por", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio", name="ck_asignaciones_fecha_fin_valida"
        ),
        sa.CheckConstraint("origen IN ('MANUAL','IMPORTACION','INSTITUCIONAL')", name="ck_asignaciones_origen"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["eca_id"], ["ecas.id"]),
        sa.ForeignKeyConstraint(["asignado_por"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["lote_importacion_id"], ["lotes_importacion.id"]),
        sa.ForeignKeyConstraint(["creado_por"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["actualizado_por"], ["usuarios.id"]),
    )
    op.create_index("uq_ate_uuid", "asignaciones_tecnico_eca", ["uuid"], unique=True)
    op.create_index(
        "uq_ate_usuario_eca_activo",
        "asignaciones_tecnico_eca",
        ["usuario_id", "eca_id"],
        unique=True,
        postgresql_where=sa.text("activo"),
    )
    op.create_index(
        "idx_ate_usuario", "asignaciones_tecnico_eca", ["usuario_id"], postgresql_where=sa.text("activo")
    )
    op.create_index(
        "idx_ate_eca", "asignaciones_tecnico_eca", ["eca_id"], postgresql_where=sa.text("activo")
    )


def downgrade() -> None:
    op.drop_table("asignaciones_tecnico_eca")
