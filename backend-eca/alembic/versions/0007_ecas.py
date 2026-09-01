"""ECA y lotes de importación

Revisión: 0007
Revisión anterior: 0006

ECA-007. `clave_fuente` es la clave de upsert de la importación masiva
(DP-2, `06` ECA-007) — `UNIQUE` solo cuando no es NULL. Sin `localidades`
normalizadas en el MVP: `localidad_nombre` es texto libre.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lotes_importacion",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("archivo_nombre", sa.Text(), nullable=False),
        sa.Column("total_filas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("filas_validas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("filas_con_error", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estado", sa.Text(), nullable=False, server_default="PROCESANDO"),
        sa.Column("resumen", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("confirmado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.CheckConstraint(
            "tipo IN ('ECA','USUARIOS','ASIGNACIONES_TECNICO_ECA','AMBITOS')", name="ck_lotes_tipo"
        ),
        sa.CheckConstraint(
            "estado IN ('PROCESANDO','VALIDADO','CONFIRMADO','CANCELADO','ERROR')",
            name="ck_lotes_estado",
        ),
    )
    op.create_index("uq_lotes_uuid", "lotes_importacion", ["uuid"], unique=True)
    op.create_index("idx_lotes_tipo_estado", "lotes_importacion", ["tipo", "estado"])

    op.create_table(
        "ecas",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("clave_fuente", sa.Text(), nullable=True),
        sa.Column("clave_institucional", sa.Text(), nullable=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("estado_id", sa.BigInteger(), nullable=False),
        sa.Column("municipio_id", sa.BigInteger(), nullable=False),
        sa.Column("localidad_nombre", sa.Text(), nullable=True),
        sa.Column("latitud", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitud", sa.Numeric(9, 6), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("fuente_carga", sa.Text(), nullable=False, server_default="MANUAL"),
        sa.Column("lote_importacion_id", sa.BigInteger(), nullable=True),
        sa.Column("metadatos", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("actualizado_por", sa.BigInteger(), nullable=True),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(latitud IS NULL) = (longitud IS NULL)", name="ck_ecas_coordenadas_par"
        ),
        sa.CheckConstraint("fuente_carga IN ('MANUAL','IMPORTACION')", name="ck_ecas_fuente_carga"),
        sa.ForeignKeyConstraint(["estado_id"], ["estados.id"]),
        sa.ForeignKeyConstraint(["municipio_id"], ["municipios.id"]),
        sa.ForeignKeyConstraint(["lote_importacion_id"], ["lotes_importacion.id"]),
        sa.ForeignKeyConstraint(["creado_por"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["actualizado_por"], ["usuarios.id"]),
    )
    op.create_index("uq_ecas_uuid", "ecas", ["uuid"], unique=True)
    op.create_index(
        "uq_ecas_clave_fuente", "ecas", ["clave_fuente"], unique=True,
        postgresql_where=sa.text("clave_fuente IS NOT NULL"),
    )
    op.create_index(
        "uq_ecas_clave_institucional",
        "ecas",
        ["clave_institucional"],
        unique=True,
        postgresql_where=sa.text("clave_institucional IS NOT NULL"),
    )
    op.create_index("idx_ecas_estado", "ecas", ["estado_id"])
    op.create_index("idx_ecas_municipio", "ecas", ["municipio_id"])
    op.create_index("idx_ecas_activo", "ecas", ["activo"])
    op.execute("CREATE INDEX idx_ecas_nombre_trgm ON ecas USING gin (nombre gin_trgm_ops)")


def downgrade() -> None:
    op.drop_table("ecas")
    op.drop_table("lotes_importacion")
