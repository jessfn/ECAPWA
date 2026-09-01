"""Extensiones base de PostgreSQL para eca_db

Revisión: 0001
Revisión anterior: None
Creada: ECA-002

Sin tablas de dominio todavía (llegan en ECA-003+). Esta primera revisión
solo habilita las extensiones que el modelo de datos de referencia
(`docs-eca/05_MODELO_DATOS_ECA.md`) y el plan (`06` §2) dan por sentadas:

- ``citext``: comparaciones case-insensitive (p. ej. correo electrónico) sin
  tener que normalizar manualmente en cada consulta.
- ``pg_trgm``: búsqueda por similitud/trigram, usada más adelante para
  búsqueda de ECA por nombre.

Downgrade: elimina ambas extensiones. Solo es seguro mientras ninguna tabla
dependa todavía de ellas (cierto en ECA-002; a partir de que existan columnas
``citext`` o índices ``gin ... gin_trgm_ops``, un downgrade real requeriría
revertir primero esas revisiones posteriores — Alembic ya fuerza ese orden).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS citext")
