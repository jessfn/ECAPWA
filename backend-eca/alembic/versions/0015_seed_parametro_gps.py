"""Semilla: gps.precision_valida_maxima_m

Revisión: 0015
Revisión anterior: 0014

ECA-014. Solo se siembra la clave que este ticket necesita de verdad
(`gps.precision_valida_maxima_m`), mismo criterio que `0009` para
`eca.regla_disponibilidad`: el resto de claves de `05` §4.6 se siembran
cuando su ticket correspondiente las necesite.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    parametros = sa.table(
        "parametros_config",
        sa.column("clave", sa.Text),
        sa.column("valor", postgresql.JSONB),
        sa.column("tipo_dato", sa.Text),
        sa.column("descripcion", sa.Text),
    )
    op.get_bind().execute(
        sa.insert(parametros).values(
            clave="gps.precision_valida_maxima_m",
            valor=30,
            tipo_dato="ENTERO",
            descripcion=(
                "Precisión GPS máxima (metros) para clasificar una captura como CON_GPS; "
                "por encima de este umbral se marca GPS_IMPRECISO. Consumido por la PWA "
                "(pwa-eca/src/services/gps.js) vía GET /parametros-config/gps.precision_valida_maxima_m."
            ),
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM parametros_config WHERE clave = 'gps.precision_valida_maxima_m'")
    )
