"""Pruebas de `app/core/errors.py` — ECA-002.

Cubre específicamente que un 500 no controlado también lleve cabeceras CORS
(bug real encontrado en un proyecto hermano: Starlette conecta
`add_exception_handler(Exception, ...)` a `ServerErrorMiddleware`, que queda
fuera de `CORSMiddleware` — un 500 real se veía como `net::ERR_FAILED` en el
navegador en vez de una respuesta legible).
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.core.errors import ManejadorExcepcionesNoControladasMiddleware, registrar_manejadores_error


def _app_de_prueba() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ManejadorExcepcionesNoControladasMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True)
    registrar_manejadores_error(app)

    @app.get("/explota")
    async def _explota() -> None:
        raise RuntimeError("boom")

    return app


def test_500_no_controlado_usa_formato_uniforme() -> None:
    cliente = TestClient(_app_de_prueba(), raise_server_exceptions=False)

    respuesta = cliente.get("/explota")

    assert respuesta.status_code == 500
    cuerpo = respuesta.json()
    assert cuerpo["error"]["code"] == "error_interno"
    assert "incidente_id" in cuerpo["error"]["details"]
    assert "boom" not in respuesta.text  # nunca se filtra el detalle interno


def test_500_no_controlado_lleva_cabeceras_cors() -> None:
    cliente = TestClient(_app_de_prueba(), raise_server_exceptions=False)

    respuesta = cliente.get("/explota", headers={"Origin": "http://localhost:5173"})

    assert respuesta.status_code == 500
    assert respuesta.headers.get("access-control-allow-origin") == "http://localhost:5173"
