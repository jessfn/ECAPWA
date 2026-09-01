"""Pruebas del router `/parametros-config` — ECA-014.

Criterios cubiertos: lectura autenticada de un parámetro conocido; 404 en
uno desconocido; requiere autenticación.
"""
from __future__ import annotations

import uuid as uuid_lib

import pytest
from fastapi.testclient import TestClient

from app.models.parametro_config import ParametroConfig
from app.models.usuario import Usuario
from app.repositories import parametros_config as repo_config


@pytest.fixture
def usuario_falso() -> Usuario:
    return Usuario(
        id=1,
        uuid=uuid_lib.uuid4(),
        nombre="Ana",
        apellido_paterno="Pérez",
        correo="ana@ejemplo.org",
        contrasena_hash="x",
        estado="ACTIVO",
        requiere_cambio_contrasena=False,
    )


class _DBFalsa:
    pass


@pytest.fixture
def cliente(env_valido: None, usuario_falso: Usuario):
    from app.api.deps import get_current_user
    from app.core.db import get_db
    from app.main import crear_app

    def _db_falsa():
        yield _DBFalsa()

    app = crear_app()
    app.dependency_overrides[get_current_user] = lambda: usuario_falso
    app.dependency_overrides[get_db] = _db_falsa
    return TestClient(app)


def test_obtener_parametro_conocido(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    parametro = ParametroConfig(
        id=1,
        clave="gps.precision_valida_maxima_m",
        valor=30,
        tipo_dato="ENTERO",
        descripcion="x",
    )
    monkeypatch.setattr(repo_config, "obtener", lambda _db, clave: parametro if clave == parametro.clave else None)

    respuesta = cliente.get("/parametros-config/gps.precision_valida_maxima_m")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"clave": "gps.precision_valida_maxima_m", "valor": 30}


def test_obtener_parametro_desconocido_es_404(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo_config, "obtener", lambda _db, _clave: None)

    respuesta = cliente.get("/parametros-config/no.existe")

    assert respuesta.status_code == 404


def test_sin_autenticar_es_401(env_valido: None, usuario_falso: Usuario) -> None:
    from app.core.db import get_db
    from app.main import crear_app

    def _db_falsa():
        yield _DBFalsa()

    app = crear_app()
    app.dependency_overrides[get_db] = _db_falsa
    cliente = TestClient(app)

    respuesta = cliente.get("/parametros-config/gps.precision_valida_maxima_m")

    assert respuesta.status_code == 401
