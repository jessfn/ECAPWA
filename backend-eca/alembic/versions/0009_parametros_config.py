"""parametros_config: estructura + semilla eca.regla_disponibilidad

Revisión: 0009
Revisión anterior: 0008

**Desviación de ECA-009**: el ticket asume que `parametros_config` ya
existe (la usa para `eca.regla_disponibilidad`), pero ningún ticket
anterior la creó — se agrega aquí, con la única clave que ECA-009
necesita de verdad. El resto de claves documentadas en
`docs-eca/05_MODELO_DATOS_ECA.md` §4.6 (`jornada.maxima_por_dia`,
`actividad.evidencia.*`, `sync.*`, `gps.*`) se siembran cuando su ticket
correspondiente las necesite — sembrarlas ahora sin uso real violaría el
principio de "sin sobreingeniería" del propio plan (`06` §1.5).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parametros_config",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("clave", sa.Text(), nullable=False),
        sa.Column("valor", postgresql.JSONB(), nullable=False),
        sa.Column("tipo_dato", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("editable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.CheckConstraint(
            "tipo_dato IN ('BOOLEAN','ENTERO','TEXTO','LISTA','OBJETO')", name="ck_parametros_tipo_dato"
        ),
    )
    op.create_index("uq_parametros_clave", "parametros_config", ["clave"], unique=True)

    parametros = sa.table(
        "parametros_config",
        sa.column("clave", sa.Text),
        sa.column("valor", postgresql.JSONB),
        sa.column("tipo_dato", sa.Text),
        sa.column("descripcion", sa.Text),
    )
    op.get_bind().execute(
        sa.insert(parametros).values(
            clave="eca.regla_disponibilidad",
            valor="ASIGNADAS_LUEGO_AMBITO",
            tipo_dato="TEXTO",
            descripcion=(
                "Regla para resolver qué ECA ve un técnico en /usuarios/me/ecas: "
                "ASIGNADAS_LUEGO_AMBITO (por defecto) | SOLO_ASIGNADAS | SOLO_AMBITO."
            ),
        )
    )


def downgrade() -> None:
    op.drop_table("parametros_config")
