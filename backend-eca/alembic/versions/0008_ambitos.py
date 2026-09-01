"""Ámbitos geográficos de técnico

Revisión: 0008
Revisión anterior: 0007

ECA-008.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ambitos_tecnico",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("municipio_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False, server_default=sa.text("current_date")),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("asignado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("actualizado_por", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio", name="ck_ambitos_fecha_fin_valida"
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["municipio_id"], ["municipios.id"]),
        sa.ForeignKeyConstraint(["asignado_por"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["creado_por"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["actualizado_por"], ["usuarios.id"]),
    )
    op.create_index(
        "uq_amb_usuario_municipio_activo",
        "ambitos_tecnico",
        ["usuario_id", "municipio_id"],
        unique=True,
        postgresql_where=sa.text("activo"),
    )
    op.create_index(
        "idx_amb_usuario", "ambitos_tecnico", ["usuario_id"], postgresql_where=sa.text("activo")
    )
    op.create_index(
        "idx_amb_municipio", "ambitos_tecnico", ["municipio_id"], postgresql_where=sa.text("activo")
    )


def downgrade() -> None:
    op.drop_table("ambitos_tecnico")
