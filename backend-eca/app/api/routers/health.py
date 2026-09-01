"""`GET /health` — ECA-002 + ECA-020 (extendido: storage, migración actual).

Criterio de aceptación del ticket original: responde 200 con BD arriba,
503 con BD caída. Sigue público (sin datos sensibles) — solo nombres de
componentes y un número de revisión de esquema, nada de credenciales ni
datos de negocio.
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__
from app.core.db import engine, verificar_conexion
from app.core.settings import get_settings

router = APIRouter()
logger = logging.getLogger("app.health")


def _migracion_actual() -> str | None:
    try:
        with engine.connect() as conn:
            fila = conn.execute(text("SELECT version_num FROM alembic_version")).first()
            return fila[0] if fila else None
    except Exception:
        return None


def _storage_ok() -> bool:
    try:
        directorio = get_settings().STORAGE_DIR
        return os.path.isdir(directorio) and os.access(directorio, os.W_OK)
    except Exception:
        return False


@router.get("/health")
async def health() -> JSONResponse:
    try:
        verificar_conexion()
    except Exception:
        logger.exception("Fallo de conexión a base de datos en /health")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "db": "error", "version": __version__},
        )

    # `status`/código HTTP siguen dependiendo solo de la BD (criterio del
    # ticket original de ECA-002); storage/migración son informativos —
    # útiles para operar, no un semáforo que tumbe el healthcheck.
    contenido = {
        "status": "ok",
        "db": "ok",
        "storage": "ok" if _storage_ok() else "error",
        "migracion_actual": _migracion_actual(),
        "version": __version__,
    }
    return JSONResponse(status_code=200, content=contenido)
