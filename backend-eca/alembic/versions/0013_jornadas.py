"""Jornadas

Revisión: 0013
Revisión anterior: 0012

ECA-012. El ticket sugiere el número `0011`, ya tomado por
`0011_catalogos_actividad.py` (ECA-010) — renumerado a `0013` siguiendo la
secuencia real de migraciones aplicadas.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jornadas",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("estado", sa.Text(), nullable=False, server_default="ABIERTA"),
        sa.Column("inicio_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitud_inicio", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitud_inicio", sa.Numeric(9, 6), nullable=True),
        sa.Column("precision_gps_inicio_m", sa.Numeric(7, 2), nullable=True),
        sa.Column("estado_gps_inicio", sa.Text(), nullable=True),
        sa.Column("fin_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latitud_fin", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitud_fin", sa.Numeric(9, 6), nullable=True),
        sa.Column("precision_gps_fin_m", sa.Numeric(7, 2), nullable=True),
        sa.Column("estado_gps_fin", sa.Text(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("dispositivo_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en_dispositivo", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sincronizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("origen", sa.Text(), nullable=False, server_default="APP"),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("actualizado_por", sa.BigInteger(), nullable=True),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["creado_por"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["actualizado_por"], ["usuarios.id"]),
        sa.CheckConstraint("estado IN ('ABIERTA','CERRADA','ANULADA')", name="ck_jornadas_estado"),
        sa.CheckConstraint(
            "fin_en IS NULL OR fin_en >= inicio_en", name="ck_jornadas_fin_despues_de_inicio"
        ),
        sa.CheckConstraint(
            "(latitud_inicio IS NULL) = (longitud_inicio IS NULL)",
            name="ck_jornadas_coordenadas_inicio_par",
        ),
        sa.CheckConstraint(
            "(latitud_fin IS NULL) = (longitud_fin IS NULL)", name="ck_jornadas_coordenadas_fin_par"
        ),
    )
    op.create_index("uq_jornadas_uuid", "jornadas", ["uuid"], unique=True)
    op.create_index(
        "uq_jornadas_usuario_fecha",
        "jornadas",
        ["usuario_id", "fecha"],
        unique=True,
        postgresql_where=sa.text("estado <> 'ANULADA' AND eliminado_en IS NULL"),
    )
    op.create_index("idx_jornadas_usuario_fecha", "jornadas", ["usuario_id", "fecha"])


def downgrade() -> None:
    op.drop_table("jornadas")
