"""Semilla eca.max_offline + índice ecas.actualizado_en

Revisión: 0018
Revisión anterior: 0017

ECA-018. El ticket sugiere aditivo sobre `0006`/`0016`; como esas ya están
aplicadas, se hace aquí como su propia migración aditiva, siguiendo la
secuencia real. `eca.max_offline` es el tope configurable del riesgo
señalado por el ticket (técnico con ámbito enorme); `idx_ecas_actualizado_en`
deja lista una columna que un futuro delta real por `actualizado_en` podría
usar (ver desviación documentada en `app/services/bootstrap_service.py`).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_ecas_actualizado_en", "ecas", ["actualizado_en"])

    parametros = sa.table(
        "parametros_config",
        sa.column("clave", sa.Text),
        sa.column("valor", postgresql.JSONB),
        sa.column("tipo_dato", sa.Text),
        sa.column("descripcion", sa.Text),
    )
    op.get_bind().execute(
        sa.insert(parametros).values(
            clave="eca.max_offline",
            valor=1500,
            tipo_dato="ENTERO",
            descripcion=(
                "Tope de ECA que se entregan en GET /sync/bootstrap. Si el conjunto del "
                "técnico lo supera, se recorta y se agrega un aviso en la respuesta."
            ),
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM parametros_config WHERE clave = 'eca.max_offline'"))
    op.drop_index("idx_ecas_actualizado_en", table_name="ecas")
