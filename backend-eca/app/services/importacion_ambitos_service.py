"""Importación masiva de ámbitos por CSV — ECA-008.

Columnas esperadas: `correo_tecnico, clave_municipio` (clave INEGI de 5
dígitos). A diferencia de `PUT /usuarios/{id}/ambito` (que reemplaza el
conjunto completo de un técnico), cada fila del CSV **agrega** un municipio
al ámbito del técnico correspondiente — no reemplaza lo que ya tenía. Cada
fila se valida por separado; una fila con error no cancela las demás.
"""
from __future__ import annotations

import csv
import io

from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.models.usuario import Usuario
from app.repositories import ambitos as repo_ambitos
from app.repositories import geo as repo_geo
from app.repositories import usuarios as repo_usuarios
from app.schemas.ambito import ImportarAmbitosFila, ImportarAmbitosRespuesta

COLUMNAS_REQUERIDAS = {"correo_tecnico", "clave_municipio"}


def _leer_filas(contenido_csv: str) -> list[dict[str, str]]:
    lector = csv.DictReader(io.StringIO(contenido_csv))
    faltantes = COLUMNAS_REQUERIDAS - set(campo.strip() for campo in (lector.fieldnames or []))
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas en el CSV: {sorted(faltantes)}")
    return list(lector)


def importar_ambitos(db: Session, *, contenido_csv: str, actor: Usuario) -> ImportarAmbitosRespuesta:
    filas = _leer_filas(contenido_csv)
    municipios_por_clave = {m.clave_inegi: m for m in repo_geo.listar_todos_municipios(db)}

    detalle: list[ImportarAmbitosFila] = []
    asignadas = 0

    for indice, fila in enumerate(filas, start=2):  # fila 1 = encabezado
        correo = (fila.get("correo_tecnico") or "").strip()
        clave_municipio = (fila.get("clave_municipio") or "").strip()

        if not (correo and clave_municipio):
            detalle.append(
                ImportarAmbitosFila(fila=indice, correo_tecnico=correo or None, resultado="error", error="correo_tecnico y clave_municipio son obligatorios.")
            )
            continue

        tecnico = repo_usuarios.obtener_por_correo(db, correo)
        if tecnico is None:
            detalle.append(
                ImportarAmbitosFila(fila=indice, correo_tecnico=correo, resultado="error", error=f"Usuario no encontrado: {correo}.")
            )
            continue

        municipio = municipios_por_clave.get(clave_municipio)
        if municipio is None or not municipio.activo:
            detalle.append(
                ImportarAmbitosFila(fila=indice, correo_tecnico=correo, resultado="error", error=f"Municipio desconocido o inactivo: {clave_municipio}.")
            )
            continue

        ya_activos = {a.municipio_id for a in repo_ambitos.listar_activos_de(db, tecnico.id)}
        if municipio.id not in ya_activos:
            repo_ambitos.crear(db, usuario_id=tecnico.id, municipio_id=municipio.id, asignado_por=actor.id)
        detalle.append(ImportarAmbitosFila(fila=indice, correo_tecnico=correo, resultado="asignado"))
        asignadas += 1

    if asignadas:
        registrar_evento(
            db,
            accion="ambito.importacion",
            modulo="ambitos",
            origen="IMPORTACION",
            actor_usuario_id=actor.id,
            descripcion=f"Importación de {asignadas} ámbitos por CSV",
        )
        db.commit()

    con_error = len(detalle) - asignadas
    return ImportarAmbitosRespuesta(
        total_filas=len(filas), asignadas=asignadas, con_error=con_error, detalle=detalle
    )
