"""Solicitudes de acceso

Revisión: 0019
Revisión anterior: 0018

ECA-020b. `POST /solicitudes-acceso` solo escribía en la bitácora de
auditoría (no listable/accionable); esta tabla le da estado propio para que
`admin-eca` pueda mostrarlas y marcarlas atendidas.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "solicitudes_acceso",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("correo", sa.String(), nullable=False),
        sa.Column("telefono", sa.String(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(), nullable=False, server_default="pendiente"),
        sa.Column("atendida_por", sa.BigInteger(), nullable=True),
        sa.Column("atendida_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "estado IN ('pendiente', 'aprobada', 'rechazada')", name="ck_solicitudes_acceso_estado"
        ),
        sa.ForeignKeyConstraint(["atendida_por"], ["usuarios.id"]),
    )
    op.create_index("idx_solicitudes_acceso_estado", "solicitudes_acceso", ["estado"])


def downgrade() -> None:
    op.drop_table("solicitudes_acceso")
