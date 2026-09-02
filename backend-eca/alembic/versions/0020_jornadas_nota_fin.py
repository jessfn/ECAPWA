"""Jornadas: nota de cierre

Revisión: 0020
Revisión anterior: 0019

Pedido explícito: registrar inicio y salida de jornada ahora exige un
detalle escrito por el técnico en cada acción. La columna `nota`
(0013_jornadas) ya cubre el detalle de inicio; falta una columna propia
para el detalle de cierre — no se reutiliza `nota` para ambos porque
perdería el texto de inicio en cuanto se cierre la jornada.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jornadas", sa.Column("nota_fin", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("jornadas", "nota_fin")
