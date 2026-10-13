"""Borrado lógico de notificaciones retiradas (eliminada_en)

Revisión: 0031
Revisión anterior: 0030
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0031"
down_revision: Union[str, None] = "0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("notificaciones", sa.Column("eliminada_en", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("notificaciones", "eliminada_en")
