"""Manejo uniforme de errores — ECA-002.

Toda respuesta de error del backend ECA tiene la misma forma, sin importar el
origen (excepción HTTP explícita, error de validación de Pydantic, o
excepción no controlada):

    {
      "error": {
        "code": "<slug_estable>",
        "message": "<mensaje seguro para el usuario/cliente>",
        "details": <opcional, estructura libre>
      }
    }

Una excepción no controlada nunca debe filtrar el traceback ni el mensaje
interno al cliente: se loguea completo en el servidor y se responde un 500
genérico.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.errors")


def _cuerpo_error(code: str, message: str, details: object | None = None) -> dict:
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def _slug_desde_status(status_code: int) -> str:
    return {
        status.HTTP_400_BAD_REQUEST: "solicitud_invalida",
        status.HTTP_401_UNAUTHORIZED: "no_autenticado",
        status.HTTP_403_FORBIDDEN: "no_autorizado",
        status.HTTP_404_NOT_FOUND: "no_encontrado",
        status.HTTP_409_CONFLICT: "conflicto",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "datos_invalidos",
        status.HTTP_429_TOO_MANY_REQUESTS: "demasiadas_solicitudes",
        status.HTTP_503_SERVICE_UNAVAILABLE: "servicio_no_disponible",
    }.get(status_code, "error")


async def _manejar_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_cuerpo_error(_slug_desde_status(exc.status_code), str(exc.detail)),
        headers=getattr(exc, "headers", None),
    )


def _detalles_serializables(errores: list[dict]) -> list[dict]:
    """`RequestValidationError.errors()` puede traer, dentro de `ctx`, la
    excepción Python original que un `@field_validator` levantó (p. ej.
    `ValueError("CURP con formato inválido.")`) — `json.dumps` no sabe
    serializar un objeto `Exception`. Se detectó con ECA-020 al agregar el
    primer `field_validator` que de verdad se ejercita vía HTTP en las
    pruebas (`SolicitudAccesoPeticion`); el mismo patrón ya existía sin
    probar en `UsuarioEditarPeticion`/`UsuarioCambioEstadoPeticion`."""
    saneados = []
    for error in errores:
        error = dict(error)
        ctx = error.get("ctx")
        if isinstance(ctx, dict) and "error" in ctx:
            ctx = dict(ctx)
            ctx["error"] = str(ctx["error"])
            error["ctx"] = ctx
        saneados.append(error)
    return saneados


async def _manejar_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_cuerpo_error(
            "datos_invalidos",
            "Los datos enviados no son válidos.",
            details=_detalles_serializables(exc.errors()),
        ),
    )


async def _manejar_excepcion_no_controlada(request: Request, exc: Exception) -> JSONResponse:
    incidente_id = uuid.uuid4().hex
    # El traceback completo va al log del servidor con un id correlacionable;
    # el cliente solo recibe el id, nunca el detalle interno.
    logger.exception(
        "Excepción no controlada",
        extra={"incidente_id": incidente_id, "path": str(request.url.path)},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_cuerpo_error(
            "error_interno",
            "Ocurrió un error inesperado. Si persiste, reporta este identificador.",
            details={"incidente_id": incidente_id},
        ),
    )


class ManejadorExcepcionesNoControladasMiddleware(BaseHTTPMiddleware):
    """Atrapa cualquier excepción que ningún handler más específico capturó.

    Starlette conecta `add_exception_handler(Exception, ...)` a su
    `ServerErrorMiddleware`, que queda FUERA de todo middleware de usuario
    (incluido `CORSMiddleware`). Un 500 real así nunca lleva cabeceras CORS
    y el navegador lo ve como `net::ERR_FAILED` en vez de una respuesta
    legible. Al atrapar la excepción aquí, como middleware normal (agregado
    antes que `CORSMiddleware` en `app/main.py`, para quedar por dentro de
    él), la respuesta sí pasa por `CORSMiddleware` de regreso.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001 — atrapa cualquier excepción a propósito
            return await _manejar_excepcion_no_controlada(request, exc)


def registrar_manejadores_error(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _manejar_http_exception)
    app.add_exception_handler(RequestValidationError, _manejar_validacion)
