"""Semilla de roles y permisos MVP

Revisión: 0004
Revisión anterior: 0003

ECA-004 (`06_PLAN_IMPLEMENTACION_ECA.md`, ticket ECA-004): crea los roles
`ADMIN`/`TECNICO` y el catálogo de permisos MVP; asigna todos los permisos a
`ADMIN` y el subconjunto de campo a `TECNICO`. Migración de datos (no de
esquema): usa `sa.table`/`sa.column` para no depender de los modelos ORM
(que pueden cambiar de forma después de esta revisión).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLES = [
    ("ADMIN", "Administrador", "Acceso total al sistema ECA.", True),
    ("TECNICO", "Técnico de campo", "Captura de jornadas y actividades en campo.", True),
]

PERMISOS = [
    ("usuarios.gestionar", "usuarios", "Gestionar usuarios"),
    ("usuarios.importar", "usuarios", "Importar usuarios por CSV"),
    ("geo.gestionar", "geo", "Gestionar catálogos geográficos"),
    ("ecas.ver", "ecas", "Ver ECA"),
    ("ecas.gestionar", "ecas", "Gestionar ECA"),
    ("ecas.importar", "ecas", "Importar ECA"),
    ("ambitos.gestionar", "ambitos", "Gestionar ámbitos de técnico"),
    ("asignaciones.gestionar", "asignaciones", "Gestionar asignaciones técnico-ECA"),
    ("catalogos.ver", "catalogos", "Ver catálogos"),
    ("catalogos.gestionar", "catalogos", "Gestionar catálogos"),
    ("actividades.crear", "actividades", "Crear actividades"),
    ("actividades.ver_propias", "actividades", "Ver actividades propias"),
    ("actividades.ver_todas", "actividades", "Ver todas las actividades"),
    ("jornadas.crear", "jornadas", "Crear jornadas"),
    ("jornadas.ver_propias", "jornadas", "Ver jornadas propias"),
    ("sync.usar", "sync", "Usar sincronización offline"),
]

PERMISOS_TECNICO = {
    "ecas.ver",
    "catalogos.ver",
    "actividades.crear",
    "actividades.ver_propias",
    "jornadas.crear",
    "jornadas.ver_propias",
    "sync.usar",
}


def _tablas():
    roles = sa.table(
        "roles",
        sa.column("id", sa.BigInteger),
        sa.column("clave", sa.Text),
        sa.column("nombre", sa.Text),
        sa.column("descripcion", sa.Text),
        sa.column("es_sistema", sa.Boolean),
    )
    permisos = sa.table(
        "permisos",
        sa.column("id", sa.BigInteger),
        sa.column("clave", sa.Text),
        sa.column("modulo", sa.Text),
        sa.column("nombre", sa.Text),
    )
    roles_permisos = sa.table(
        "roles_permisos",
        sa.column("rol_id", sa.BigInteger),
        sa.column("permiso_id", sa.BigInteger),
    )
    return roles, permisos, roles_permisos


def upgrade() -> None:
    conn = op.get_bind()
    roles, permisos, roles_permisos = _tablas()

    ids_rol: dict[str, int] = {}
    for clave, nombre, descripcion, es_sistema in ROLES:
        resultado = conn.execute(
            sa.insert(roles)
            .values(clave=clave, nombre=nombre, descripcion=descripcion, es_sistema=es_sistema)
            .returning(roles.c.id)
        )
        ids_rol[clave] = resultado.scalar_one()

    ids_permiso: dict[str, int] = {}
    for clave, modulo, nombre in PERMISOS:
        resultado = conn.execute(
            sa.insert(permisos).values(clave=clave, modulo=modulo, nombre=nombre).returning(permisos.c.id)
        )
        ids_permiso[clave] = resultado.scalar_one()

    filas_admin = [
        {"rol_id": ids_rol["ADMIN"], "permiso_id": permiso_id} for permiso_id in ids_permiso.values()
    ]
    filas_tecnico = [
        {"rol_id": ids_rol["TECNICO"], "permiso_id": ids_permiso[clave]} for clave in PERMISOS_TECNICO
    ]
    conn.execute(sa.insert(roles_permisos), filas_admin + filas_tecnico)


def downgrade() -> None:
    conn = op.get_bind()
    roles, permisos, roles_permisos = _tablas()
    conn.execute(sa.delete(roles_permisos))
    conn.execute(sa.delete(permisos))
    conn.execute(sa.delete(roles))
