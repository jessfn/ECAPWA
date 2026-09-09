"""Consolida ECA/Ámbitos/Asignaciones/Catálogos en la vista "Modificaciones"

Revisión: 0029
Revisión anterior: 0028

Pedido explícito: las 4 vistas de configuración del panel (ECA, Ámbitos,
Asignaciones, Catálogos) se unifican en UNA sola vista llamada
"Modificaciones" (con pestañas internas por módulo). Por eso:

- Se inserta `vista.modificaciones` (módulo `vistas`) y se otorga a ADMIN.
- Se PRESERVA el acceso: cualquier rol o usuario que hoy tenga al menos uno
  de los 4 permisos antiguos (`vista.ecas`/`vista.ambitos`/
  `vista.asignaciones`/`vista.catalogos`) recibe automáticamente
  `vista.modificaciones`, para que nadie pierda acceso por la consolidación.
- Se DESACTIVAN (`activo=false`, nunca DELETE — patrón no destructivo del
  proyecto, igual que 0024/0025) los 4 permisos antiguos: dejan de aparecer
  en el catálogo de permisos y en el menú.

Los permisos FINOS de cada módulo (`ecas.gestionar`, `ecas.importar`,
`ambitos.gestionar`, `asignaciones.gestionar`, `catalogos.gestionar`)
quedan INTACTOS y activos — son los que autorizan las acciones dentro de
cada pestaña, y ahora se muestran agrupados bajo la nueva vista en Permisos
administrativos.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CLAVES_ANTIGUAS = ["vista.ecas", "vista.ambitos", "vista.asignaciones", "vista.catalogos"]
CLAVE_NUEVA = "vista.modificaciones"


def _tablas():
    permisos = sa.table(
        "permisos",
        sa.column("id", sa.BigInteger),
        sa.column("clave", sa.Text),
        sa.column("modulo", sa.Text),
        sa.column("nombre", sa.Text),
        sa.column("activo", sa.Boolean),
    )
    roles = sa.table("roles", sa.column("id", sa.BigInteger), sa.column("clave", sa.Text))
    roles_permisos = sa.table(
        "roles_permisos",
        sa.column("rol_id", sa.BigInteger),
        sa.column("permiso_id", sa.BigInteger),
    )
    usuarios_permisos = sa.table(
        "usuarios_permisos",
        sa.column("usuario_id", sa.BigInteger),
        sa.column("permiso_id", sa.BigInteger),
    )
    return permisos, roles, roles_permisos, usuarios_permisos


def upgrade() -> None:
    conn = op.get_bind()
    permisos, roles, roles_permisos, usuarios_permisos = _tablas()

    # 1) Inserta el permiso nuevo (o lo reutiliza si ya existiera, p. ej. un
    #    re-run tras un rollback parcial — idempotente).
    id_nuevo = conn.execute(
        sa.select(permisos.c.id).where(permisos.c.clave == CLAVE_NUEVA)
    ).scalar_one_or_none()
    if id_nuevo is None:
        id_nuevo = conn.execute(
            sa.insert(permisos)
            .values(clave=CLAVE_NUEVA, modulo="vistas", nombre="Ver vista: Modificaciones", activo=True)
            .returning(permisos.c.id)
        ).scalar_one()

    # 2) ids de los 4 permisos antiguos (estén activos o no).
    ids_antiguos = list(
        conn.execute(sa.select(permisos.c.id).where(permisos.c.clave.in_(CLAVES_ANTIGUAS))).scalars().all()
    )

    # 3) ADMIN siempre tiene el permiso nuevo.
    id_admin = conn.execute(sa.select(roles.c.id).where(roles.c.clave == "ADMIN")).scalar_one()

    # 4) Roles que ya tenían alguno de los 4 antiguos -> reciben el nuevo
    #    (más ADMIN), sin duplicar contra UNIQUE(rol_id, permiso_id).
    roles_destino = {id_admin}
    if ids_antiguos:
        roles_destino |= set(
            conn.execute(
                sa.select(roles_permisos.c.rol_id).where(roles_permisos.c.permiso_id.in_(ids_antiguos))
            ).scalars().all()
        )
    roles_ya = set(
        conn.execute(
            sa.select(roles_permisos.c.rol_id).where(roles_permisos.c.permiso_id == id_nuevo)
        ).scalars().all()
    )
    filas_roles = [{"rol_id": r, "permiso_id": id_nuevo} for r in roles_destino if r not in roles_ya]
    if filas_roles:
        conn.execute(sa.insert(roles_permisos), filas_roles)

    # 5) Usuarios con permiso DIRECTO a alguno de los 4 antiguos -> reciben el
    #    nuevo (sin duplicar contra UNIQUE(usuario_id, permiso_id)).
    if ids_antiguos:
        usuarios_destino = set(
            conn.execute(
                sa.select(usuarios_permisos.c.usuario_id).where(
                    usuarios_permisos.c.permiso_id.in_(ids_antiguos)
                )
            ).scalars().all()
        )
        usuarios_ya = set(
            conn.execute(
                sa.select(usuarios_permisos.c.usuario_id).where(usuarios_permisos.c.permiso_id == id_nuevo)
            ).scalars().all()
        )
        filas_usuarios = [
            {"usuario_id": u, "permiso_id": id_nuevo} for u in usuarios_destino if u not in usuarios_ya
        ]
        if filas_usuarios:
            conn.execute(sa.insert(usuarios_permisos), filas_usuarios)

    # 6) Desactiva los 4 permisos antiguos (no destructivo — las filas de
    #    otorgamiento quedan, pero `permisos_efectivos_de`/`listar_permisos`
    #    filtran por activo=True, así que desaparecen del menú y del catálogo).
    if ids_antiguos:
        conn.execute(sa.update(permisos).where(permisos.c.id.in_(ids_antiguos)).values(activo=False))


def downgrade() -> None:
    conn = op.get_bind()
    permisos, roles, roles_permisos, usuarios_permisos = _tablas()

    # Reactiva los 4 antiguos.
    conn.execute(sa.update(permisos).where(permisos.c.clave.in_(CLAVES_ANTIGUAS)).values(activo=True))

    # Quita el permiso nuevo de roles/usuarios y lo elimina.
    id_nuevo = conn.execute(
        sa.select(permisos.c.id).where(permisos.c.clave == CLAVE_NUEVA)
    ).scalar_one_or_none()
    if id_nuevo is not None:
        conn.execute(sa.delete(roles_permisos).where(roles_permisos.c.permiso_id == id_nuevo))
        conn.execute(sa.delete(usuarios_permisos).where(usuarios_permisos.c.permiso_id == id_nuevo))
        conn.execute(sa.delete(permisos).where(permisos.c.id == id_nuevo))
