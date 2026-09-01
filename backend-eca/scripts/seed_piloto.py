"""Script de despliegue — ECA-020, "Pasos de despliegue" paso 5.

Carga la lista real de técnicos del piloto desde un CSV, reutilizando
`importacion_usuarios_service` (ECA-004) — el mismo motor que ya usa el
panel admin, no una ruta distinta. Cada técnico recibe una **contraseña
temporal generada por el propio sistema** (`requiere_cambio_contrasena =
true`); este script **nunca** elige ni pide contraseñas — las imprime al
final para que Jesús se las entregue a cada técnico por un canal seguro.

Columnas del CSV: `nombre, apellido_paterno, apellido_materno, correo,
curp, rol` (mismo formato que `POST /usuarios/importar` — `curp` y
`apellido_materno` son opcionales; `rol` normalmente `TECNICO`).

Uso (en el servidor, con el entorno del backend activado):
    python -m scripts.seed_piloto --csv tecnicos_piloto.csv --admin-correo admin@ejemplo.org
"""
from __future__ import annotations

import argparse
import sys

from app.core.db import SessionLocal
from app.repositories.usuarios import obtener_por_correo
from app.services.importacion_usuarios_service import importar_usuarios


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="Ruta al CSV de técnicos del piloto.")
    parser.add_argument(
        "--admin-correo",
        required=True,
        help="Correo de un usuario ADMIN ya existente — queda como autor de la alta en la auditoría.",
    )
    argumentos = parser.parse_args()

    with open(argumentos.csv, encoding="utf-8-sig") as archivo:
        contenido_csv = archivo.read()

    db = SessionLocal()
    try:
        actor = obtener_por_correo(db, argumentos.admin_correo)
        if actor is None:
            raise SystemExit(f"No existe un usuario con el correo {argumentos.admin_correo}.")

        respuesta = importar_usuarios(db, contenido_csv=contenido_csv, actor=actor)
    finally:
        db.close()

    print(f"\nTotal filas: {respuesta.total_filas}  ·  Creados: {respuesta.creados}  ·  Con error: {respuesta.con_error}\n")

    if respuesta.creados:
        print("Contraseñas temporales generadas (entrégalas por un canal seguro, no por correo en claro):")
        for fila in respuesta.detalle:
            if fila.resultado == "creado":
                print(f"  fila {fila.fila}: {fila.correo}  →  {fila.contrasena_temporal}")

    if respuesta.con_error:
        print("\nFilas con error (nada se creó si hubo al menos una — revisa y vuelve a correr el CSV completo):", file=sys.stderr)
        for fila in respuesta.detalle:
            if fila.resultado == "error":
                print(f"  fila {fila.fila}: {fila.error}", file=sys.stderr)


if __name__ == "__main__":
    main()
