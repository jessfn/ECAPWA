"""Script de despliegue — ECA-003/ECA-004 (`06_PLAN_IMPLEMENTACION_ECA.md`,
"Pasos de despliegue").

Crea el primer usuario ADMIN y le asigna el rol `ADMIN` (sembrado por la
migración `0004_seed_roles_permisos.py`). Lo ejecuta **Jesús en el
servidor**, con la `DATABASE_URL`/`SECRET_KEY` reales del entorno y una
contraseña que **él** teclea de forma interactiva (nunca como argumento de
línea de comandos, para que no quede en el historial de la shell ni en logs
del proceso).

Uso:
    python -m scripts.crear_admin --correo admin@ejemplo.org \
        --nombre "Jesús" --apellido-paterno "Ríos"

Pide la contraseña dos veces (con confirmación) por `getpass`, sin eco en
pantalla y sin guardarla en ningún archivo.
"""
from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.security import ContrasenaDebilError, hash_contrasena, validar_fortaleza_contrasena
from app.models.usuario import Usuario
from app.repositories.rbac import asignar_rol, obtener_rol_por_clave
from app.repositories.usuarios import obtener_por_correo

ROL_ADMIN = "ADMIN"


def _leer_contrasena() -> str:
    while True:
        contrasena = getpass.getpass("Contraseña para el nuevo usuario ADMIN: ")
        confirmacion = getpass.getpass("Confirma la contraseña: ")
        if contrasena != confirmacion:
            print("Las contraseñas no coinciden. Intenta de nuevo.\n", file=sys.stderr)
            continue
        try:
            validar_fortaleza_contrasena(contrasena)
        except ContrasenaDebilError as exc:
            print(f"Contraseña rechazada: {exc}\n", file=sys.stderr)
            continue
        return contrasena


def crear_admin(
    db: Session, *, correo: str, nombre: str, apellido_paterno: str, apellido_materno: str | None
) -> Usuario:
    if obtener_por_correo(db, correo) is not None:
        raise SystemExit(f"Ya existe un usuario con el correo {correo}.")

    rol_admin = obtener_rol_por_clave(db, ROL_ADMIN)
    if rol_admin is None:
        raise SystemExit(
            f"No existe el rol {ROL_ADMIN}. ¿Ya corriste `alembic upgrade head` "
            "(migración 0004, semilla de roles/permisos)?"
        )

    contrasena = _leer_contrasena()

    usuario = Usuario(
        correo=correo,
        nombre=nombre,
        apellido_paterno=apellido_paterno,
        apellido_materno=apellido_materno,
        contrasena_hash=hash_contrasena(contrasena),
        requiere_cambio_contrasena=False,
        estado="ACTIVO",
    )
    db.add(usuario)
    db.flush()

    asignar_rol(db, usuario_id=usuario.id, rol_id=rol_admin.id, asignado_por=None)

    db.commit()
    db.refresh(usuario)
    return usuario


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--correo", required=True)
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--apellido-paterno", required=True, dest="apellido_paterno")
    parser.add_argument("--apellido-materno", default=None, dest="apellido_materno")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        usuario = crear_admin(
            db,
            correo=args.correo,
            nombre=args.nombre,
            apellido_paterno=args.apellido_paterno,
            apellido_materno=args.apellido_materno,
        )
    finally:
        db.close()

    print(f"Usuario creado: {usuario.correo} (uuid={usuario.uuid}, id={usuario.id}, rol={ROL_ADMIN})")
    print("Ya puede iniciar sesión vía POST /auth/login.")


if __name__ == "__main__":
    main()
