"""Permisos para la vista "Asistencia" (entrada/salida de jornada, admin)

Revisión: 0026
Revisión anterior: 0025

Pedido explícito: nueva vista "Asistencia" en el panel — entrada y salida
de TODOS los técnicos (hora + ubicación de cada una), no solo las propias.
El backend ya tenía `jornadas.ver_propias` (para que un técnico consulte
las suyas) pero ningún permiso "ver todas" — se agrega, mismo patrón que
`actividades.ver_propias`/`actividades.ver_todas`.

- `jornadas.ver_todas`: gatea `GET /jornadas/todas`.
- `vista.asistencia`: gatea la entrada del sidebar (mismo patrón que el
  resto de `vista.*`, migración 0023/0024).

Ambos otorgados a ADMIN, igual que el resto de permisos "ver todo".
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISOS_NUEVOS = [
    ("jornadas.ver_todas", "jornadas", "Ver jornadas de todos los técnicos"),
    ("vista.asistencia", "vistas", "Ver vista: Asistencia"),
]


def _tablas():
    permisos = sa.table(
        "permisos",
        sa.column("id", sa.BigInteger),
        sa.column("clave", sa.Text),
        sa.column("modulo", sa.Text),
        sa.column("nombre", sa.Text),
    )
    roles = sa.table("roles", sa.column("id", sa.BigInteger), sa.column("clave", sa.Text))
    roles_permisos = sa.table(
        "roles_permisos",
        sa.column("rol_id", sa.BigInteger),
        sa.column("permiso_id", sa.BigInteger),
    )
    return permisos, roles, roles_permisos


def upgrade() -> None:
    conn = op.get_bind()
    permisos, roles, roles_permisos = _tablas()

    id_admin = conn.execute(sa.select(roles.c.id).where(roles.c.clave == "ADMIN")).scalar_one()

    ids_permiso: list[int] = []
    for clave, modulo, nombre in PERMISOS_NUEVOS:
        resultado = conn.execute(
            sa.insert(permisos).values(clave=clave, modulo=modulo, nombre=nombre).returning(permisos.c.id)
        )
        ids_permiso.append(resultado.scalar_one())

    conn.execute(
        sa.insert(roles_permisos),
        [{"rol_id": id_admin, "permiso_id": permiso_id} for permiso_id in ids_permiso],
    )


def downgrade() -> None:
    conn = op.get_bind()
    permisos, roles, roles_permisos = _tablas()
    claves = [clave for clave, _, _ in PERMISOS_NUEVOS]
    ids_permiso = conn.execute(sa.select(permisos.c.id).where(permisos.c.clave.in_(claves))).scalars().all()
    if ids_permiso:
        conn.execute(sa.delete(roles_permisos).where(roles_permisos.c.permiso_id.in_(ids_permiso)))
        conn.execute(sa.delete(permisos).where(permisos.c.id.in_(ids_permiso)))
