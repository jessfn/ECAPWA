"""Evidencias fotográficas

Revisión: 0016
Revisión anterior: 0015

ECA-015. El ticket sugiere el número `0014`, ya tomado por
`0014_actividades.py` (ECA-013) — renumerado a `0016` siguiendo la
secuencia real de migraciones aplicadas. Sin `hash_perceptual` (sin pHash,
fuera de alcance del MVP).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "actividades_evidencias",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("actividad_id", sa.BigInteger(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("storage_clave", sa.Text(), nullable=False),
        sa.Column("nombre_archivo", sa.Text(), nullable=False),
        sa.Column("mime", sa.Text(), nullable=False),
        sa.Column("tamano_bytes", sa.Integer(), nullable=False),
        sa.Column("hash_sha256", sa.Text(), nullable=False),
        sa.Column("latitud", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitud", sa.Numeric(9, 6), nullable=True),
        sa.Column("capturada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sincronizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["actividad_id"], ["actividades.id"]),
        sa.CheckConstraint("orden BETWEEN 1 AND 3", name="ck_ev_orden"),
        sa.CheckConstraint("(latitud IS NULL) = (longitud IS NULL)", name="ck_ev_coordenadas_par"),
        sa.UniqueConstraint("actividad_id", "orden", name="uq_ev_actividad_orden"),
    )
    op.create_index("uq_evidencias_uuid", "actividades_evidencias", ["uuid"], unique=True)
    op.create_index("idx_ev_actividad", "actividades_evidencias", ["actividad_id"])
    op.create_index("idx_ev_sha", "actividades_evidencias", ["hash_sha256"])


def downgrade() -> None:
    op.drop_table("actividades_evidencias")
