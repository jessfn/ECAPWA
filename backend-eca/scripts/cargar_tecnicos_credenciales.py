"""Script de alta masiva — carga técnicos ECA con la contraseña temporal
YA asignada y distribuida por el equipo (a diferencia de
`scripts/seed_piloto.py`/`POST /usuarios/importar`, que siempre generan
una contraseña aleatoria nueva: aquí el correo y la contraseña de cada
fila deben respetarse tal cual, porque ya se entregaron a los técnicos).

No reutiliza `services.importacion_usuarios_service` (ese motor no acepta
contraseña por fila) — inserta directamente con `repo_usuarios`/`repo_rbac`,
igual que hace el servicio real por debajo, hasheando cada contraseña con
`hash_contrasena` (argon2id, la misma función que usa el login).

Idempotente: un correo que ya existe en la base se omite (se reporta,
nunca se sobrescribe ni se duplica) — se puede volver a correr sin riesgo
si el archivo de entrada cambia o el script se interrumpió a medias.

Entrada: un JSON (lista de objetos) con `correo`, `contrasena`, `nombre`,
`apellido_paterno`, `apellido_materno` (opcional) — nunca se commitea a
git (son contraseñas reales en texto plano); vive solo en el servidor
mientras se corre esto, y debe borrarse después.

Uso (en el servidor, con el entorno del backend activado):
    python -m scripts.cargar_tecnicos_credenciales --json tecnicos.json --admin-correo admin@ejemplo.org
"""
from __future__ import annotations

import argparse
import json
import sys

from app.core.audit import registrar_evento
from app.core.security import hash_contrasena
from app.core.db import SessionLocal
from app.models.usuario import Usuario
from app.repositories import rbac as repo_rbac
from app.repositories import usuarios as repo_usuarios


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", required=True, help="Ruta al JSON con nombre/correo/contraseña por técnico.")
    parser.add_argument(
        "--admin-correo",
        required=True,
        help="Correo de un usuario ADMIN ya existente — queda como autor de la alta en la auditoría.",
    )
    parser.add_argument("--rol", default="TECNICO", help="Clave de rol a asignar a todos (default: TECNICO).")
    argumentos = parser.parse_args()

    with open(argumentos.json, encoding="utf-8") as archivo:
        filas = json.load(archivo)

    db = SessionLocal()
    try:
        actor = repo_usuarios.obtener_por_correo(db, argumentos.admin_correo)
        if actor is None:
            raise SystemExit(f"No existe un usuario con el correo {argumentos.admin_correo}.")

        rol = repo_rbac.obtener_rol_por_clave(db, argumentos.rol)
        if rol is None:
            raise SystemExit(f"Rol desconocido: {argumentos.rol}.")

        creados: list[str] = []
        omitidos: list[tuple[str, str]] = []

        for fila in filas:
            correo = fila["correo"].strip()
            if repo_usuarios.obtener_por_correo(db, correo) is not None:
                omitidos.append((correo, "ya existe un usuario con ese correo"))
                continue

            usuario = Usuario(
                nombre=fila["nombre"].strip(),
                apellido_paterno=fila["apellido_paterno"].strip(),
                apellido_materno=(fila.get("apellido_materno") or "").strip() or None,
                correo=correo,
                contrasena_hash=hash_contrasena(fila["contrasena"]),
                requiere_cambio_contrasena=True,
                estado="ACTIVO",
                creado_por=actor.id,
            )
            repo_usuarios.crear_usuario(db, usuario)
            repo_rbac.asignar_rol(db, usuario_id=usuario.id, rol_id=rol.id, asignado_por=actor.id)
            creados.append(correo)

        if creados:
            registrar_evento(
                db,
                accion="usuario.importacion",
                modulo="usuarios",
                origen="IMPORTACION",
                actor_usuario_id=actor.id,
                descripcion=f"Carga masiva de {len(creados)} técnicos ECA (padrón oficial, contraseñas ya asignadas)",
                datos_despues={"correos": creados},
            )
            db.commit()
        else:
            db.rollback()
    finally:
        db.close()

    print(f"\nCreados: {len(creados)}  ·  Omitidos (ya existían): {len(omitidos)}\n")
    if omitidos:
        print("Omitidos:", file=sys.stderr)
        for correo, motivo in omitidos:
            print(f"  {correo}: {motivo}", file=sys.stderr)


if __name__ == "__main__":
    main()
