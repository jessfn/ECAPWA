"""Importación de usuarios por CSV — ECA-004.

Columnas esperadas: `nombre, apellido_paterno, apellido_materno, correo,
curp, rol`. `apellido_materno` y `curp` son opcionales.

Valida **todas** las filas antes de crear nada: si una sola fila tiene un
error, no se crea ningún usuario del lote (criterio de aceptación del
ticket: "no crea nada si el lote se cancela"). Los correos duplicados
**dentro del mismo CSV** también son error, no solo contra la BD.
"""
from __future__ import annotations

import csv
import io

from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.core.security import hash_contrasena
from app.models.usuario import Usuario
from app.repositories import rbac as repo_rbac
from app.repositories import usuarios as repo_usuarios
from app.schemas.usuario import ImportacionUsuariosFila, ImportacionUsuariosRespuesta
from app.services.usuarios_service import generar_contrasena_temporal

COLUMNAS_REQUERIDAS = {"nombre", "apellido_paterno", "correo", "rol"}


def _leer_filas(contenido_csv: str) -> list[dict[str, str]]:
    lector = csv.DictReader(io.StringIO(contenido_csv))
    faltantes = COLUMNAS_REQUERIDAS - set(campo.strip() for campo in (lector.fieldnames or []))
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas en el CSV: {sorted(faltantes)}")
    return list(lector)


def importar_usuarios(db: Session, *, contenido_csv: str, actor: Usuario) -> ImportacionUsuariosRespuesta:
    filas = _leer_filas(contenido_csv)

    errores: list[ImportacionUsuariosFila] = []
    validas: list[dict[str, str]] = []
    correos_en_csv: set[str] = set()

    for indice, fila in enumerate(filas, start=2):  # fila 1 = encabezado
        correo = (fila.get("correo") or "").strip()
        nombre = (fila.get("nombre") or "").strip()
        apellido_paterno = (fila.get("apellido_paterno") or "").strip()
        rol = (fila.get("rol") or "").strip()

        error = None
        if not (correo and nombre and apellido_paterno and rol):
            error = "nombre, apellido_paterno, correo y rol son obligatorios."
        elif correo in correos_en_csv:
            error = f"Correo duplicado dentro del propio archivo: {correo}."
        elif repo_usuarios.obtener_por_correo(db, correo) is not None:
            error = f"Ya existe un usuario con el correo {correo}."
        elif repo_rbac.obtener_rol_por_clave(db, rol) is None:
            error = f"Rol desconocido o inactivo: {rol}."

        if error:
            errores.append(ImportacionUsuariosFila(fila=indice, correo=correo or None, resultado="error", error=error))
            continue

        correos_en_csv.add(correo)
        validas.append(
            {
                "fila": indice,
                "nombre": nombre,
                "apellido_paterno": apellido_paterno,
                "apellido_materno": (fila.get("apellido_materno") or "").strip() or None,
                "correo": correo,
                "curp": (fila.get("curp") or "").strip() or None,
                "rol": rol,
            }
        )

    if errores:
        # Todo o nada: si hay al menos un error, no se crea ningún usuario.
        detalle = errores + [
            ImportacionUsuariosFila(fila=v["fila"], correo=v["correo"], resultado="cancelado")
            for v in validas
        ]
        detalle.sort(key=lambda f: f.fila)
        return ImportacionUsuariosRespuesta(
            total_filas=len(filas), creados=0, con_error=len(errores), detalle=detalle
        )

    detalle: list[ImportacionUsuariosFila] = []
    for v in validas:
        contrasena_temporal = generar_contrasena_temporal()
        usuario = Usuario(
            nombre=v["nombre"],
            apellido_paterno=v["apellido_paterno"],
            apellido_materno=v["apellido_materno"],
            correo=v["correo"],
            curp=v["curp"],
            contrasena_hash=hash_contrasena(contrasena_temporal),
            requiere_cambio_contrasena=True,
            estado="ACTIVO",
        )
        repo_usuarios.crear_usuario(db, usuario)
        rol = repo_rbac.obtener_rol_por_clave(db, v["rol"])
        repo_rbac.asignar_rol(db, usuario_id=usuario.id, rol_id=rol.id, asignado_por=actor.id)
        detalle.append(
            ImportacionUsuariosFila(
                fila=v["fila"],
                correo=v["correo"],
                resultado="creado",
                contrasena_temporal=contrasena_temporal,
            )
        )

    registrar_evento(
        db,
        accion="usuario.importacion",
        modulo="usuarios",
        origen="IMPORTACION",
        actor_usuario_id=actor.id,
        descripcion=f"Importación de {len(detalle)} usuarios por CSV",
        datos_despues={"correos": [v["correo"] for v in validas]},
    )
    db.commit()

    return ImportacionUsuariosRespuesta(
        total_filas=len(filas), creados=len(detalle), con_error=0, detalle=detalle
    )
