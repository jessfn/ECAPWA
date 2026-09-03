"""Usuarios: cargo/puesto — Actividades: nombre de ECA escrito a mano

Revisión: 0021
Revisión anterior: 0020

Pedido explícito (2026-09-03):
- `usuarios.cargo`: puesto/cargo del técnico (Responsable de CEDA,
  Coordinadora Estatal, Enlace Informático, etc. — vienen del padrón
  oficial, ver `scripts/cargar_tecnicos_credenciales.py`). Sin catálogo
  propio: es texto libre, solo para mostrarlo, no para reglas de negocio.
- `actividades.eca_nombre`: en la práctica muchos técnicos no tienen
  ninguna ECA en su ámbito/asignación todavía (catálogo de ECA
  incompleto para su municipio), así que el selector de ECA los dejaba
  sin poder guardar ninguna actividad que la requiriera. Se agrega esta
  columna para permitir escribir el nombre de la ECA a mano cuando no
  hay ninguna que seleccionar — sigue siendo obligatoria para los tipos
  de actividad con `requiere_eca`, solo cambia CÓMO se captura.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("cargo", sa.Text(), nullable=True))
    op.add_column("actividades", sa.Column("eca_nombre", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("actividades", "eca_nombre")
    op.drop_column("usuarios", "cargo")
