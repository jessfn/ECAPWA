"""Retira la vista "Inicio" — el panel abre directo en Visor de Seguimiento

Revisión: 0025
Revisión anterior: 0024

Pedido explícito: se elimina la pantalla "Inicio" (dashboard). El panel
abre directo en "Visor de Seguimiento" (ya la vista más completa: mapa +
stats + accesos), que pasa a vivir en la ruta raíz `/`.

Mismo criterio no-destructivo que 0024: se desactiva `vista.inicio`
(`activo=false`, nunca DELETE) en vez de borrarla — sigue sin tocar
`usuarios_permisos`/`roles_permisos`.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CLAVE = "vista.inicio"


def _permisos():
    return sa.table(
        "permisos",
        sa.column("id", sa.BigInteger),
        sa.column("clave", sa.Text),
        sa.column("activo", sa.Boolean),
    )


def upgrade() -> None:
    conn = op.get_bind()
    permisos = _permisos()
    conn.execute(sa.update(permisos).where(permisos.c.clave == CLAVE).values(activo=False))


def downgrade() -> None:
    conn = op.get_bind()
    permisos = _permisos()
    conn.execute(sa.update(permisos).where(permisos.c.clave == CLAVE).values(activo=True))
