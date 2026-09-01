"""Actividades

Revisión: 0014
Revisión anterior: 0013

ECA-013. El ticket sugiere el número `0012`, ya tomado por
`0012_seed_catalogos.py` (ECA-010) — renumerado a `0014` siguiendo la
secuencia real de migraciones aplicadas. Sin columna de estado de
transmisión (§2.3 de `04_ARQUITECTURA_OBJETIVO.md`): eso es local del
outbox del cliente, no persiste en el servidor.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "actividades",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("jornada_id", sa.BigInteger(), nullable=False),
        sa.Column("eca_id", sa.BigInteger(), nullable=True),
        sa.Column("modalidad_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo_actividad_id", sa.BigInteger(), nullable=False),
        sa.Column("tema_id", sa.BigInteger(), nullable=True),
        sa.Column("subtema_id", sa.BigInteger(), nullable=True),
        sa.Column("sistema_productivo_id", sa.BigInteger(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("resultado", sa.Text(), nullable=True),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitud", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitud", sa.Numeric(9, 6), nullable=True),
        sa.Column("precision_gps_m", sa.Numeric(7, 2), nullable=True),
        sa.Column("estado_gps", sa.Text(), nullable=True),
        sa.Column("num_participantes", sa.Integer(), nullable=True),
        sa.Column("requiere_seguimiento", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("fecha_proximo_seguimiento", sa.Date(), nullable=True),
        sa.Column("dispositivo_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en_dispositivo", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recibido_en", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["jornada_id"], ["jornadas.id"]),
        sa.ForeignKeyConstraint(["eca_id"], ["ecas.id"]),
        sa.ForeignKeyConstraint(["modalidad_id"], ["modalidades.id"]),
        sa.ForeignKeyConstraint(["tipo_actividad_id"], ["tipos_actividad.id"]),
        sa.ForeignKeyConstraint(["tema_id"], ["temas.id"]),
        sa.ForeignKeyConstraint(["subtema_id"], ["subtemas.id"]),
        sa.ForeignKeyConstraint(["sistema_productivo_id"], ["sistemas_productivos.id"]),
        sa.ForeignKeyConstraint(["creado_por"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["actualizado_por"], ["usuarios.id"]),
        sa.CheckConstraint(
            "num_participantes IS NULL OR num_participantes >= 0", name="ck_act_participantes"
        ),
        sa.CheckConstraint(
            "fecha_proximo_seguimiento IS NULL OR requiere_seguimiento",
            name="ck_act_seguimiento_coherente",
        ),
        sa.CheckConstraint("(latitud IS NULL) = (longitud IS NULL)", name="ck_act_coordenadas_par"),
    )
    op.create_index("uq_actividades_uuid", "actividades", ["uuid"], unique=True)
    op.create_index("idx_act_usuario_fecha", "actividades", ["usuario_id", "fecha_hora"])
    op.create_index("idx_act_jornada", "actividades", ["jornada_id"])
    op.create_index("idx_act_eca", "actividades", ["eca_id"])
    op.create_index("idx_act_tipo", "actividades", ["tipo_actividad_id"])
    op.create_index("idx_act_tema", "actividades", ["tema_id"])
    op.create_index("idx_act_sistema", "actividades", ["sistema_productivo_id"])


def downgrade() -> None:
    op.drop_table("actividades")
