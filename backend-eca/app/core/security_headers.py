"""Cabeceras de seguridad — ECA-020.

Complementa el HSTS/TLS que ya impone nginx (terminación TLS) con
cabeceras que sí le corresponden a la aplicación. No sustituye la
configuración de nginx del ticket (HSTS se deja ahí, más cerca del borde).
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CabecerasSeguridadMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        respuesta = await call_next(request)
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "DENY"
        respuesta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        respuesta.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        return respuesta
