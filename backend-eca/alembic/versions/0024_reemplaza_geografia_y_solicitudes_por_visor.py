"""Retira las vistas Geografía y Solicitudes de acceso; agrega Visor de Seguimiento

Revisión: 0024
Revisión anterior: 0023

Pedido explícito: el panel deja de tener las vistas "Geografía" y
"Solicitudes de acceso" — se retiran del sidebar, del router y de
"Permisos administrativos" (nadie puede ya activarlas por USUARIO). En su
lugar se agrega una vista nueva: "Visor de Seguimiento" (mapa con la
ubicación de actividades y ECA, hereda el Mapbox que ya traía Geografía).

Nunca se hace DELETE de los permisos viejos (`vista.geografia`,
`vista.solicitudes_acceso`, `geo.gestionar` — este último solo protegía el
PATCH de activar/desactivar estado/municipio que vivía exclusivamente en la
vista Geografía que se retira, así que también queda huérfano): se
desactivan (`activo=false`), igual que ya hace el resto del catálogo de
permisos con `Rol`/`Permiso.activo`. Esto es no-destructivo y reversible
por `downgrade()`:
  - `permisos_efectivos_de`/`permisos_directos_de`/`listar_permisos` ya
    filtran por `Permiso.activo=true` (ver `app/repositories/rbac.py`), así
    que un permiso desactivado desaparece del catálogo y deja de contar
    para nadie sin tocar ninguna fila de `usuarios_permisos`/`roles_permisos`
    (evita romper FKs o perder el historial de quién tenía qué).
  - El endpoint `PATCH /geo/*` sigue existiendo en el backend (por si se
    reactiva la gestión de geografía más adelante) pero queda inalcanzable
    para cualquiera mientras `geo.gestionar` esté inactivo — 403 seguro.
  - `POST /solicitudes-acceso` (pública, la usa `pwa-eca` para que un
    técnico sin cuenta pida acceso) NO se toca — sigue funcionando; lo que
    desaparece es únicamente la pantalla del panel para revisarlas.

`vista.visor_seguimiento` se agrega igual que el resto de `vista.*`
(migración 0023): se otorga a ADMIN.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CLAVES_A_DESACTIVAR = ["vista.geografia", "vista.solicitudes_acceso", "geo.gestionar"]
PERMISO_NUEVO = ("vista.visor_seguimiento", "vistas", "Ver vista: Visor de Seguimiento")


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
    return permisos, roles, roles_permisos


def upgrade() -> None:
    conn = op.get_bind()
    permisos, roles, roles_permisos = _tablas()

    conn.execute(
        sa.update(permisos).where(permisos.c.clave.in_(CLAVES_A_DESACTIVAR)).values(activo=False)
    )

    id_admin = conn.execute(sa.select(roles.c.id).where(roles.c.clave == "ADMIN")).scalar_one()
    clave, modulo, nombre = PERMISO_NUEVO
    id_permiso_nuevo = conn.execute(
        sa.insert(permisos).values(clave=clave, modulo=modulo, nombre=nombre).returning(permisos.c.id)
    ).scalar_one()
    conn.execute(sa.insert(roles_permisos).values(rol_id=id_admin, permiso_id=id_permiso_nuevo))


def downgrade() -> None:
    conn = op.get_bind()
    permisos, roles, roles_permisos = _tablas()

    conn.execute(
        sa.update(permisos).where(permisos.c.clave.in_(CLAVES_A_DESACTIVAR)).values(activo=True)
    )

    id_permiso_nuevo = conn.execute(
        sa.select(permisos.c.id).where(permisos.c.clave == PERMISO_NUEVO[0])
    ).scalar_one_or_none()
    if id_permiso_nuevo is not None:
        conn.execute(sa.delete(roles_permisos).where(roles_permisos.c.permiso_id == id_permiso_nuevo))
        conn.execute(sa.delete(permisos).where(permisos.c.id == id_permiso_nuevo))
