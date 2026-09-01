"""Carga/actualiza el catálogo de municipios desde un CSV — ECA-006.

Ver `data/inegi/FUENTE.md`: el CSV real todavía no está definido (pendiente
de que Jesús confirme la fuente y el año del catálogo). Este script solo
sabe *cómo* cargarlo cuando exista.

CSV esperado (encabezado incluido), columnas:
    clave_inegi,nombre,estado_clave_inegi

- `clave_inegi`: 5 dígitos (2 de estado + 3 de municipio).
- `estado_clave_inegi`: 2 dígitos, debe existir ya en `estados` (ver
  `0006_seed_estados.py` — los 32 estados siempre están sembrados).

Upsert por `clave_inegi`: correrlo más de una vez con el mismo archivo no
duplica filas, solo actualiza `nombre`/`estado_id` si cambiaron.

Uso (desde `backend-eca/`):
    python -m scripts.cargar_municipios data/inegi/municipios.csv
"""
from __future__ import annotations

import argparse
import csv
import sys

from app.core.db import SessionLocal
from app.models.geo import Estado, Municipio


def cargar_municipios(ruta_csv: str) -> tuple[int, int]:
    db = SessionLocal()
    creados = actualizados = 0
    try:
        estados_por_clave = {e.clave_inegi: e.id for e in db.query(Estado).all()}
        if not estados_por_clave:
            raise SystemExit(
                "No hay estados en la BD. Corre `alembic upgrade head` primero "
                "(la migración 0006 siembra los 32 estados)."
            )

        with open(ruta_csv, encoding="utf-8-sig", newline="") as f:
            lector = csv.DictReader(f)
            faltantes = {"clave_inegi", "nombre", "estado_clave_inegi"} - set(lector.fieldnames or [])
            if faltantes:
                raise SystemExit(f"Faltan columnas en el CSV: {sorted(faltantes)}")

            for numero_fila, fila in enumerate(lector, start=2):
                clave = (fila.get("clave_inegi") or "").strip()
                nombre = (fila.get("nombre") or "").strip()
                clave_estado = (fila.get("estado_clave_inegi") or "").strip()

                if not (clave and nombre and clave_estado):
                    print(f"Fila {numero_fila}: faltan datos, se omite.", file=sys.stderr)
                    continue
                estado_id = estados_por_clave.get(clave_estado)
                if estado_id is None:
                    print(
                        f"Fila {numero_fila}: estado_clave_inegi={clave_estado!r} no existe, se omite.",
                        file=sys.stderr,
                    )
                    continue

                existente = db.query(Municipio).filter_by(clave_inegi=clave).one_or_none()
                if existente is None:
                    db.add(Municipio(clave_inegi=clave, nombre=nombre, estado_id=estado_id))
                    creados += 1
                else:
                    existente.nombre = nombre
                    existente.estado_id = estado_id
                    actualizados += 1

        db.commit()
    finally:
        db.close()

    return creados, actualizados


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ruta_csv")
    args = parser.parse_args()

    creados, actualizados = cargar_municipios(args.ruta_csv)
    print(f"Municipios creados: {creados}. Actualizados: {actualizados}.")


if __name__ == "__main__":
    main()
