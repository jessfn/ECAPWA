"""Actividades: texto libre para las opciones "Otro" de cada catálogo

Revisión: 0028
Revisión anterior: 0027

Pedido explícito: varios catálogos de actividad (tipo de actividad, tema,
subtema, sistema productivo) tienen una opción "Otro", pero al elegirla no
se pedía especificar cuál era — en el panel admin quedaba solo "Otro" sin
saber a qué se refería el técnico. Mismo criterio que `eca_nombre`
(migración 0021): se agrega una columna de texto libre por catálogo,
nullable porque solo aplica cuando esa opción específica fue la elegida.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("actividades", sa.Column("tipo_actividad_otro_texto", sa.Text(), nullable=True))
    op.add_column("actividades", sa.Column("tema_otro_texto", sa.Text(), nullable=True))
    op.add_column("actividades", sa.Column("subtema_otro_texto", sa.Text(), nullable=True))
    op.add_column("actividades", sa.Column("sistema_productivo_otro_texto", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("actividades", "sistema_productivo_otro_texto")
    op.drop_column("actividades", "subtema_otro_texto")
    op.drop_column("actividades", "tema_otro_texto")
    op.drop_column("actividades", "tipo_actividad_otro_texto")
