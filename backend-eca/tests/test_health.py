"""Pruebas de `GET /health` — ECA-002.

Criterio de aceptación del ticket: *"GET /health responde 200 con BD arriba;
503 con BD caída"*.

Dos variantes:

- `test_health_*_simulado`: siempre se ejecutan; simulan la conexión a BD
  (arriba/caída) sin necesitar PostgreSQL real, para validar la lógica del
  endpoint (código de estado, forma de la respuesta) en cualquier entorno.
- `test_health_bd_real_arriba`: prueba de integración de verdad, contra
  PostgreSQL. Se salta si no hay `TEST_DATABASE_URL` alcanzable (ver
  `conftest.py`) — es la que corre en el servidor / CI con BD disponible.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def cliente(env_valido: None, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from app.main import crear_app

    return TestClient(crear_app())


def test_health_bd_arriba_simulado(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import health as health_router

    monkeypatch.setattr(health_router, "verificar_conexion", lambda: True)

    respuesta = cliente.get("/health")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "ok"
    assert cuerpo["db"] == "ok"
    assert "version" in cuerpo


def test_health_bd_caida_simulado(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import health as health_router

    def _fallo() -> bool:
        raise ConnectionError("simulado: base de datos no disponible")

    monkeypatch.setattr(health_router, "verificar_conexion", _fallo)

    respuesta = cliente.get("/health")

    assert respuesta.status_code == 503
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "error"
    assert cuerpo["db"] == "error"


def test_health_no_expone_datos_sensibles(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import health as health_router

    monkeypatch.setattr(health_router, "verificar_conexion", lambda: True)

    cuerpo = cliente.get("/health").json()

    claves_prohibidas = {"database_url", "secret_key", "password", "token"}
    claves_presentes = {k.lower() for k in cuerpo}
    assert not (claves_prohibidas & claves_presentes)


def test_ruta_inexistente_usa_formato_uniforme(cliente: TestClient) -> None:
    """Starlette no enruta el 404 de "ninguna ruta coincide" por los manejadores
    de excepción por defecto; `app/main.py` registra un comodín para que
    también respete el formato uniforme `{"error": {...}}`."""
    respuesta = cliente.get("/esta-ruta-no-existe")

    assert respuesta.status_code == 404
    cuerpo = respuesta.json()
    assert cuerpo == {"error": {"code": "no_encontrado", "message": "Recurso no encontrado"}}


def test_health_caido_lleva_cabeceras_cors(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """El 503 de BD caída también debe llevar CORS (prueba dedicada al 500
    no controlado en `tests/test_errors.py`)."""
    from app.api.routers import health as health_router

    monkeypatch.setattr(
        health_router, "verificar_conexion", lambda: (_ for _ in ()).throw(ConnectionError("boom"))
    )

    respuesta = cliente.get("/health", headers={"Origin": "http://localhost:5173"})

    assert respuesta.status_code == 503
    assert respuesta.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_health_bd_real_arriba(app_con_bd_real) -> None:  # noqa: ANN001 — fixture tipada en conftest
    """Integración real: requiere TEST_DATABASE_URL alcanzable (se salta si no la hay)."""
    cliente = TestClient(app_con_bd_real)

    respuesta = cliente.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json()["db"] == "ok"
