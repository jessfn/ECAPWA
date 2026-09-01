"""Pruebas de rate limiting, cabeceras de seguridad y solicitudes de acceso
— ECA-020.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.ratelimit import _reiniciar_para_pruebas


@pytest.fixture(autouse=True)
def _limpiar_ratelimit():
    _reiniciar_para_pruebas()
    yield
    _reiniciar_para_pruebas()


@pytest.fixture
def cliente(env_valido: None):
    from app.main import crear_app

    return TestClient(crear_app())


def test_login_bloquea_tras_n_intentos(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import auth_service

    monkeypatch.setattr(
        auth_service,
        "login",
        lambda *a, **k: (_ for _ in ()).throw(auth_service.CredencialesInvalidasError()),
    )

    respuestas = [
        cliente.post("/auth/login", json={"correo": "x@x.com", "contrasena": "malapass"}) for _ in range(11)
    ]

    assert [r.status_code for r in respuestas[:10]] == [401] * 10
    assert respuestas[10].status_code == 429


def test_cabeceras_de_seguridad_presentes(cliente: TestClient) -> None:
    respuesta = cliente.get("/health")

    assert respuesta.headers.get("x-content-type-options") == "nosniff"
    assert respuesta.headers.get("x-frame-options") == "DENY"
    assert "referrer-policy" in respuesta.headers


def test_health_incluye_storage_y_migracion(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import health as health_router

    monkeypatch.setattr(health_router, "verificar_conexion", lambda: True)

    cuerpo = cliente.get("/health").json()

    assert "storage" in cuerpo
    assert "migracion_actual" in cuerpo


def test_solicitud_acceso_no_requiere_auth_ni_crea_usuario(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No requiere sesión y no crea ningún `Usuario`: solo dos objetos
    nuevos, la fila `SolicitudAcceso` (para que `admin-eca` la liste) y el
    evento de auditoría (para el histórico) — ninguno de los dos es un
    usuario con credenciales."""
    from app.core.db import get_db
    from app.main import crear_app
    from app.models.solicitud_acceso import SolicitudAcceso
    from app.models.usuario import Usuario

    objetos_agregados = []

    class _DBFalsa:
        def add(self, obj) -> None:
            objetos_agregados.append(obj)

        def flush(self) -> None:
            pass

        def commit(self) -> None:
            pass

    app = crear_app()
    def _db_falsa():
        yield _DBFalsa()

    app.dependency_overrides[get_db] = _db_falsa
    cliente_local = TestClient(app)

    respuesta = cliente_local.post(
        "/solicitudes-acceso",
        json={"nombre": "Ana Técnica", "correo": "ana@ejemplo.org", "telefono": "555", "notas": "quiero acceso"},
    )

    assert respuesta.status_code == 204
    assert len(objetos_agregados) == 2
    assert not any(isinstance(obj, Usuario) for obj in objetos_agregados)

    solicitud = next(obj for obj in objetos_agregados if isinstance(obj, SolicitudAcceso))
    assert solicitud.correo == "ana@ejemplo.org"
    # `estado` es `server_default="pendiente"`: solo lo aplica un INSERT real
    # (no esta `_DBFalsa`), así que aquí solo se confirma que no se fijó
    # explícitamente a otra cosa.
    assert solicitud.estado is None

    evento = next(obj for obj in objetos_agregados if not isinstance(obj, SolicitudAcceso))
    assert evento.accion == "solicitud_acceso.creada"


def test_solicitud_acceso_correo_invalido_es_422(cliente: TestClient) -> None:
    respuesta = cliente.post("/solicitudes-acceso", json={"nombre": "Ana", "correo": "no-es-correo"})
    assert respuesta.status_code == 422


def test_solicitud_acceso_rate_limit(cliente: TestClient) -> None:
    from app.core.db import get_db
    from app.main import crear_app

    class _DBFalsa:
        def add(self, _obj) -> None:
            pass

        def flush(self) -> None:
            pass

        def commit(self) -> None:
            pass

    app = crear_app()
    def _db_falsa():
        yield _DBFalsa()

    app.dependency_overrides[get_db] = _db_falsa
    cliente_local = TestClient(app)

    respuestas = [
        cliente_local.post("/solicitudes-acceso", json={"nombre": "Ana", "correo": "ana@ejemplo.org"})
        for _ in range(6)
    ]

    assert [r.status_code for r in respuestas[:5]] == [204] * 5
    assert respuestas[5].status_code == 429
