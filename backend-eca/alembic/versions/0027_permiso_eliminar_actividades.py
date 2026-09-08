"""Permiso para eliminar actividades desde el panel admin

Revisión: 0027
Revisión anterior: 0026

Pedido explícito: en la vista "Actividades" del panel, un botón para
eliminar (borrado lógico, `Actividad.eliminado_en`) solo visible para
quien tenga el permiso. Se agrega `actividades.eliminar` con
`modulo="actividades"` — mismo `modulo` que ya usa `actividades.ver_todas`,
así que en "Permisos administrativos" aparece como sub-permiso togglable
bajo la vista "Actividades" (mismo mecanismo que expone
`jornadas.ver_todas` bajo "Asistencia", migración 0026).

Otorgado a ADMIN, igual que el resto de permisos delicados.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISOS_NUEVOS = [
    ("actividades.eliminar", "actividades", "Eliminar actividades"),
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
