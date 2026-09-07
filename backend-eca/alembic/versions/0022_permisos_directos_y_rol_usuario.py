"""Permisos administrativos: tabla usuarios_permisos + rol USUARIO

Revisión: 0022
Revisión anterior: 0021

Pedido explícito (2026-09-07): una nueva vista "Permisos administrativos"
en admin-eca donde solo existen dos roles con acceso al panel:
- ADMIN (ya existía): acceso a todo, sin cambios.
- USUARIO (nuevo): acceso de panel con permisos elegidos uno por uno.

`USUARIO` se siembra sin ninguna fila en `roles_permisos` — a propósito:
todo lo que puede hacer un usuario con este rol sale de la nueva tabla
`usuarios_permisos` (otorgado directamente a esa persona, nunca a su
rol), para poder darle acceso a exactamente las vistas que se elijan sin
tener que inventar un rol nuevo por cada combinación posible.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios_permisos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "usuario_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("permiso_id", sa.Integer(), sa.ForeignKey("permisos.id"), nullable=False),
        sa.Column("otorgado_por", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column(
            "otorgado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_index(
        "uq_up_usuario_permiso", "usuarios_permisos", ["usuario_id", "permiso_id"], unique=True
    )

    roles = sa.table(
        "roles",
        sa.column("clave", sa.Text),
        sa.column("nombre", sa.Text),
        sa.column("descripcion", sa.Text),
        sa.column("es_sistema", sa.Boolean),
    )
    op.bulk_insert(
        roles,
        [
            {
                "clave": "USUARIO",
                "nombre": "Usuario de panel",
                "descripcion": "Acceso administrativo con permisos elegidos vista por vista (ver usuarios_permisos).",
                "es_sistema": True,
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM roles WHERE clave = 'USUARIO'")
    op.drop_index("uq_up_usuario_permiso", table_name="usuarios_permisos")
    op.drop_table("usuarios_permisos")
