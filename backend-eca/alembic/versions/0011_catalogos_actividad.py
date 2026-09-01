"""Catálogos de actividad: modalidades, tipos_actividad, temas, subtemas, sistemas_productivos

Revisión: 0011
Revisión anterior: 0010

ECA-010.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columnas_catalogo_simple():
    return [
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("clave", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    ]


def upgrade() -> None:
    op.create_table("modalidades", *_columnas_catalogo_simple())
    op.create_index("uq_modalidades_clave", "modalidades", ["clave"], unique=True)

    op.create_table(
        "tipos_actividad",
        *_columnas_catalogo_simple(),
        sa.Column("requiere_evidencia", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("min_fotos", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_fotos", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("permite_participantes", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requiere_eca", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("min_fotos BETWEEN 0 AND 3", name="ck_tipos_actividad_min_fotos"),
        sa.CheckConstraint("max_fotos BETWEEN min_fotos AND 3", name="ck_tipos_actividad_max_fotos"),
    )
    op.create_index("uq_tipos_actividad_clave", "tipos_actividad", ["clave"], unique=True)

    op.create_table("temas", *_columnas_catalogo_simple())
    op.create_index("uq_temas_clave", "temas", ["clave"], unique=True)

    op.create_table(
        "subtemas",
        *_columnas_catalogo_simple(),
        sa.Column("tema_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["tema_id"], ["temas.id"]),
    )
    op.create_index("uq_subtemas_tema_clave", "subtemas", ["tema_id", "clave"], unique=True)

    op.create_table("sistemas_productivos", *_columnas_catalogo_simple())
    op.create_index("uq_sistemas_productivos_clave", "sistemas_productivos", ["clave"], unique=True)


def downgrade() -> None:
    op.drop_table("subtemas")
    op.drop_table("temas")
    op.drop_table("tipos_actividad")
    op.drop_table("modalidades")
    op.drop_table("sistemas_productivos")
