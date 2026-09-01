"""Catálogos geográficos: estados, municipios

Revisión: 0005
Revisión anterior: 0004

ECA-006. Sin `localidades` en el MVP (`06` §0). El `UNIQUE(clave_inegi)`
más el trigram de `municipios.nombre` (vía `pg_trgm`, ya habilitado en
`0001`) soportan búsqueda por nombre en <300ms (criterio de aceptación del
ticket) sin depender de texto libre en ninguna otra tabla.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "estados",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("clave_inegi", sa.CHAR(2), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("abreviatura", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_index("uq_estados_clave_inegi", "estados", ["clave_inegi"], unique=True)
    op.create_index("uq_estados_nombre", "estados", ["nombre"], unique=True)

    op.create_table(
        "municipios",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("estado_id", sa.BigInteger(), nullable=False),
        sa.Column("clave_inegi", sa.CHAR(5), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(["estado_id"], ["estados.id"]),
    )
    op.create_index("uq_municipios_clave_inegi", "municipios", ["clave_inegi"], unique=True)
    op.create_index(
        "uq_municipios_estado_nombre", "municipios", ["estado_id", "nombre"], unique=True
    )
    op.create_index("idx_municipios_estado", "municipios", ["estado_id"])
    op.execute(
        "CREATE INDEX idx_municipios_nombre_trgm ON municipios USING gin (nombre gin_trgm_ops)"
    )


def downgrade() -> None:
    op.drop_table("municipios")
    op.drop_table("estados")
