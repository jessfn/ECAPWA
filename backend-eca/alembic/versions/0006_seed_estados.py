"""Semilla: 32 estados (INEGI)

Revisión: 0006
Revisión anterior: 0005

ECA-006. Los 32 estados son un catálogo estable y de bajo riesgo de error
(sin cambios desde 1974); se siembran aquí directamente con clave INEGI de
2 dígitos.

**Los municipios NO se siembran en esta migración** — a diferencia de los
estados, son ~2,469 registros que cambian con el tiempo (México crea
municipios nuevos periódicamente) y el propio ticket ECA-006 exige acordar
con Jesús la fuente exacta y su año antes de cargarlos («Riesgos»: "Fuente
INEGI desactualizada o con claves cambiadas"). Se cargan aparte con
`scripts/cargar_municipios.py` desde un CSV versionado en
`data/inegi/municipios.csv` — ver `data/inegi/FUENTE.md` (documenta que ese
CSV está pendiente de la fuente real).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (clave_inegi, nombre, abreviatura) — 32 entidades federativas.
ESTADOS = [
    ("01", "Aguascalientes", "AGU"),
    ("02", "Baja California", "BCN"),
    ("03", "Baja California Sur", "BCS"),
    ("04", "Campeche", "CAM"),
    ("05", "Coahuila de Zaragoza", "COA"),
    ("06", "Colima", "COL"),
    ("07", "Chiapas", "CHP"),
    ("08", "Chihuahua", "CHH"),
    ("09", "Ciudad de México", "CMX"),
    ("10", "Durango", "DUR"),
    ("11", "Guanajuato", "GUA"),
    ("12", "Guerrero", "GRO"),
    ("13", "Hidalgo", "HID"),
    ("14", "Jalisco", "JAL"),
    ("15", "México", "MEX"),
    ("16", "Michoacán de Ocampo", "MIC"),
    ("17", "Morelos", "MOR"),
    ("18", "Nayarit", "NAY"),
    ("19", "Nuevo León", "NLE"),
    ("20", "Oaxaca", "OAX"),
    ("21", "Puebla", "PUE"),
    ("22", "Querétaro", "QUE"),
    ("23", "Quintana Roo", "ROO"),
    ("24", "San Luis Potosí", "SLP"),
    ("25", "Sinaloa", "SIN"),
    ("26", "Sonora", "SON"),
    ("27", "Tabasco", "TAB"),
    ("28", "Tamaulipas", "TAM"),
    ("29", "Tlaxcala", "TLA"),
    ("30", "Veracruz de Ignacio de la Llave", "VER"),
    ("31", "Yucatán", "YUC"),
    ("32", "Zacatecas", "ZAC"),
]


def _tabla_estados():
    return sa.table(
        "estados",
        sa.column("clave_inegi", sa.CHAR),
        sa.column("nombre", sa.Text),
        sa.column("abreviatura", sa.Text),
    )


def upgrade() -> None:
    conn = op.get_bind()
    estados = _tabla_estados()
    conn.execute(
        sa.insert(estados),
        [{"clave_inegi": c, "nombre": n, "abreviatura": a} for c, n, a in ESTADOS],
    )


def downgrade() -> None:
    conn = op.get_bind()
    estados = _tabla_estados()
    conn.execute(sa.delete(estados))
