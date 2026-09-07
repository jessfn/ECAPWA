"""Permisos vista.* para gatear cada entrada del sidebar de admin-eca

Revisión: 0023
Revisión anterior: 0022

Pedido explícito (ECA-021 v2): el switch de "Permisos administrativos" debe
poder prender/apagar cada vista del sidebar una por una para el rol
USUARIO. Hoy varias vistas (Inicio, Geografía, Catálogos) no tienen ningún
permiso que las proteja, y otras tres (Técnicos, Solicitudes de acceso,
Permisos administrativos) comparten el mismo `usuarios.gestionar` — no se
puede dar acceso a una sin dar a las tres. Se crea un permiso `vista.*` por
cada entrada del sidebar y se le otorgan TODOS a `ADMIN` (que ya tenía
acceso total, esto no le agrega ni quita nada en la práctica).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISOS_VISTA = [
    ("vista.inicio", "vistas", "Ver vista: Inicio"),
    ("vista.geografia", "vistas", "Ver vista: Geografía"),
    ("vista.ecas", "vistas", "Ver vista: ECA"),
    ("vista.ambitos", "vistas", "Ver vista: Ámbitos"),
    ("vista.asignaciones", "vistas", "Ver vista: Asignaciones"),
    ("vista.catalogos", "vistas", "Ver vista: Catálogos"),
    ("vista.tecnicos", "vistas", "Ver vista: Técnicos"),
    ("vista.actividades", "vistas", "Ver vista: Actividades"),
    ("vista.solicitudes_acceso", "vistas", "Ver vista: Solicitudes de acceso"),
    ("vista.permisos_administrativos", "vistas", "Ver vista: Permisos administrativos"),
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
    for clave, modulo, nombre in PERMISOS_VISTA:
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
    claves = [clave for clave, _, _ in PERMISOS_VISTA]
    ids_permiso = conn.execute(
        sa.select(permisos.c.id).where(permisos.c.clave.in_(claves))
    ).scalars().all()
    if ids_permiso:
        conn.execute(sa.delete(roles_permisos).where(roles_permisos.c.permiso_id.in_(ids_permiso)))
        conn.execute(sa.delete(permisos).where(permisos.c.id.in_(ids_permiso)))
