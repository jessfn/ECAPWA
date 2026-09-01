"""Semilla: modalidades, tipos_actividad, temas, subtemas iniciales, sistemas_productivos

Revisión: 0012
Revisión anterior: 0011

ECA-010. **Nota de la semilla** (ver "Pasos de despliegue" del ticket: "revisar con
el equipo funcional que la semilla... es la deseada para el piloto"): las banderas
por tipo de actividad (`requiere_evidencia`/`min_fotos`/`max_fotos`/
`permite_participantes`/`requiere_eca`) y los subtemas iniciales son un punto de
partida razonable, **no** una decisión funcional cerrada — todo se puede ajustar
desde el panel (`PATCH /catalogos/{tipo}/{id}`, `POST /catalogos/subtemas`) sin
desplegar código, tal como pide el criterio de aceptación del ticket. La semilla
de subtemas es deliberadamente parcial (uno por tema, no exhaustiva): el propio
ticket acepta ese riesgo y lo mitiga permitiendo que el admin añada más en
caliente.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MODALIDADES = [
    ("CAMPO", "Campo"),
    ("GABINETE", "Gabinete"),
]

# (clave, nombre, requiere_evidencia, min_fotos, max_fotos, permite_participantes, requiere_eca)
TIPOS_ACTIVIDAD = [
    ("CAP", "Capacitación", True, 1, 3, True, True),
    ("ATE", "Atención técnica", True, 1, 3, False, True),
    ("VIS", "Visita", True, 1, 3, False, True),
    ("MON", "Monitoreo", True, 1, 3, False, True),
    ("PRA", "Práctica demostrativa", True, 1, 3, True, True),
    ("ORG", "Organización de productores", False, 0, 3, True, True),
    ("INT", "Intercambio de experiencias", True, 1, 3, True, True),
    ("GES", "Gestión", False, 0, 3, False, False),
    ("EVA", "Evaluación", True, 1, 3, False, True),
    ("OTR", "Otro", False, 0, 3, False, False),
]

TEMAS = [
    "Manejo del cultivo",
    "Bioinsumos",
    "Suelo",
    "Agua",
    "Sanidad vegetal",
    "Semillas",
    "Agrobiodiversidad",
    "Huertos",
    "Cosecha y poscosecha",
    "Organización de productores",
    "Comercialización",
    "Ganadería",
    "Apicultura",
    "Otro",
]

# Un subtema inicial por tema (semilla deliberadamente parcial, ver docstring).
SUBTEMAS_POR_TEMA = {
    "Manejo del cultivo": "Fertilización",
    "Bioinsumos": "Elaboración de bioinsumos",
    "Suelo": "Conservación de suelo",
    "Agua": "Uso eficiente del agua",
    "Sanidad vegetal": "Manejo de plagas",
    "Semillas": "Selección de semilla",
    "Agrobiodiversidad": "Policultivos",
    "Huertos": "Huerto familiar",
    "Cosecha y poscosecha": "Manejo poscosecha",
    "Organización de productores": "Formación de grupos",
    "Comercialización": "Canales de venta",
    "Ganadería": "Manejo de traspatio",
    "Apicultura": "Manejo de colmenas",
    "Otro": "Otro",
}

SISTEMAS_PRODUCTIVOS = [
    "Maíz",
    "Frijol",
    "Milpa",
    "Trigo",
    "Arroz",
    "Café",
    "Caña de azúcar",
    "Cacao",
    "Amaranto",
    "Chía",
    "Miel / Apicultura",
    "Leche / Ganadería",
    "Hortalizas",
    "Otro",
]


def _clave(nombre: str) -> str:
    import re
    import unicodedata

    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", nombre) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^A-Z0-9]+", "_", sin_acentos.upper()).strip("_")


def upgrade() -> None:
    conn = op.get_bind()

    modalidades = sa.table(
        "modalidades", sa.column("clave", sa.Text), sa.column("nombre", sa.Text), sa.column("orden", sa.Integer)
    )
    conn.execute(
        sa.insert(modalidades),
        [{"clave": c, "nombre": n, "orden": i} for i, (c, n) in enumerate(MODALIDADES)],
    )

    tipos = sa.table(
        "tipos_actividad",
        sa.column("clave", sa.Text),
        sa.column("nombre", sa.Text),
        sa.column("orden", sa.Integer),
        sa.column("requiere_evidencia", sa.Boolean),
        sa.column("min_fotos", sa.Integer),
        sa.column("max_fotos", sa.Integer),
        sa.column("permite_participantes", sa.Boolean),
        sa.column("requiere_eca", sa.Boolean),
    )
    conn.execute(
        sa.insert(tipos),
        [
            {
                "clave": clave,
                "nombre": nombre,
                "orden": i,
                "requiere_evidencia": req_ev,
                "min_fotos": min_f,
                "max_fotos": max_f,
                "permite_participantes": participantes,
                "requiere_eca": req_eca,
            }
            for i, (clave, nombre, req_ev, min_f, max_f, participantes, req_eca) in enumerate(
                TIPOS_ACTIVIDAD
            )
        ],
    )

    temas = sa.table(
        "temas", sa.column("id", sa.BigInteger), sa.column("clave", sa.Text), sa.column("nombre", sa.Text), sa.column("orden", sa.Integer)
    )
    ids_tema: dict[str, int] = {}
    for i, nombre in enumerate(TEMAS):
        resultado = conn.execute(
            sa.insert(temas).values(clave=_clave(nombre), nombre=nombre, orden=i).returning(temas.c.id)
        )
        ids_tema[nombre] = resultado.scalar_one()

    subtemas = sa.table(
        "subtemas",
        sa.column("tema_id", sa.BigInteger),
        sa.column("clave", sa.Text),
        sa.column("nombre", sa.Text),
        sa.column("orden", sa.Integer),
    )
    conn.execute(
        sa.insert(subtemas),
        [
            {"tema_id": ids_tema[tema], "clave": _clave(subtema), "nombre": subtema, "orden": 0}
            for tema, subtema in SUBTEMAS_POR_TEMA.items()
        ],
    )

    sistemas = sa.table(
        "sistemas_productivos", sa.column("clave", sa.Text), sa.column("nombre", sa.Text), sa.column("orden", sa.Integer)
    )
    conn.execute(
        sa.insert(sistemas),
        [{"clave": _clave(n), "nombre": n, "orden": i} for i, n in enumerate(SISTEMAS_PRODUCTIVOS)],
    )


def downgrade() -> None:
    conn = op.get_bind()
    for tabla in ("subtemas", "temas", "tipos_actividad", "modalidades", "sistemas_productivos"):
        conn.execute(sa.text(f"DELETE FROM {tabla}"))
