"""Importación masiva de asignaciones técnico↔ECA por CSV — ECA-009.

Columnas esperadas: `correo_tecnico, identificador_eca` — este último puede
ser `clave_fuente` o `clave_institucional` de la ECA (se busca por
cualquiera de las dos). Igual que `importacion_ambitos_service`: cada fila
se valida por separado, una fila con error no cancela las demás.
"""
from __future__ import annotations

import csv
import io

from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.models.usuario import Usuario
from app.repositories import asignaciones as repo_asignaciones
from app.repositories import ecas as repo_ecas
from app.repositories import usuarios as repo_usuarios
from app.schemas.asignacion_eca import ImportarAsignacionesFila, ImportarAsignacionesRespuesta

COLUMNAS_REQUERIDAS = {"correo_tecnico", "identificador_eca"}


def _leer_filas(contenido_csv: str) -> list[dict[str, str]]:
    lector = csv.DictReader(io.StringIO(contenido_csv))
    faltantes = COLUMNAS_REQUERIDAS - set(campo.strip() for campo in (lector.fieldnames or []))
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas en el CSV: {sorted(faltantes)}")
    return list(lector)


def importar_asignaciones(
    db: Session, *, contenido_csv: str, actor: Usuario
) -> ImportarAsignacionesRespuesta:
    filas = _leer_filas(contenido_csv)
    detalle: list[ImportarAsignacionesFila] = []
    asignadas = 0

    for indice, fila in enumerate(filas, start=2):  # fila 1 = encabezado
        correo = (fila.get("correo_tecnico") or "").strip()
        identificador_eca = (fila.get("identificador_eca") or "").strip()

        if not (correo and identificador_eca):
            detalle.append(
                ImportarAsignacionesFila(fila=indice, correo_tecnico=correo or None, resultado="error", error="correo_tecnico e identificador_eca son obligatorios.")
            )
            continue

        tecnico = repo_usuarios.obtener_por_correo(db, correo)
        if tecnico is None:
            detalle.append(
                ImportarAsignacionesFila(fila=indice, correo_tecnico=correo, resultado="error", error=f"Usuario no encontrado: {correo}.")
            )
            continue

        eca = repo_ecas.buscar_por_clave_fuente_o_institucional(db, identificador_eca)
        if eca is None:
            detalle.append(
                ImportarAsignacionesFila(fila=indice, correo_tecnico=correo, resultado="error", error=f"ECA no encontrada: {identificador_eca}.")
            )
            continue

        if repo_asignaciones.obtener_activa(db, usuario_id=tecnico.id, eca_id=eca.id) is None:
            repo_asignaciones.crear(
                db, usuario_id=tecnico.id, eca_id=eca.id, origen="IMPORTACION", asignado_por=actor.id
            )
        detalle.append(ImportarAsignacionesFila(fila=indice, correo_tecnico=correo, resultado="asignado"))
        asignadas += 1

    if asignadas:
        registrar_evento(
            db,
            accion="asignacion.importacion",
            modulo="asignaciones",
            origen="IMPORTACION",
            actor_usuario_id=actor.id,
            descripcion=f"Importación de {asignadas} asignaciones técnico-ECA por CSV",
        )
        db.commit()

    con_error = len(detalle) - asignadas
    return ImportarAsignacionesRespuesta(
        total_filas=len(filas), asignadas=asignadas, con_error=con_error, detalle=detalle
    )
