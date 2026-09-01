"""Pruebas de `require_permission` / catálogos `roles`/`permisos` — ECA-004.

Criterio de aceptación cubierto: `require_permission` niega sin permiso
(403) y permite con permiso, y ningún endpoint de datos responde sin él
(se verifica indirectamente: los routers de `usuarios`/`permisos` no
declaran ninguna ruta sin `require_permission`).
"""
from __future__ import annotations

import uuid as uuid_lib

import pytest
from fastapi.testclient import TestClient

from app.models.usuario import Usuario
from app.repositories import rbac as repo_rbac


@pytest.fixture
def usuario_falso() -> Usuario:
    usuario = Usuario(
        id=1,
        uuid=uuid_lib.uuid4(),
        nombre="Ana",
        apellido_paterno="Pérez",
        correo="ana@ejemplo.org",
        contrasena_hash="x",
        estado="ACTIVO",
        requiere_cambio_contrasena=False,
    )
    return usuario


@pytest.fixture
def cliente(env_valido: None, usuario_falso: Usuario):
    from app.api.deps import get_current_user
    from app.main import crear_app

    app = crear_app()
    app.dependency_overrides[get_current_user] = lambda: usuario_falso
    return TestClient(app)


def test_require_permission_niega_sin_permiso(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: set())

    respuesta = cliente.get("/usuarios")

    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "no_autorizado"


def test_require_permission_permite_con_permiso(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"usuarios.gestionar"})
    monkeypatch.setattr("app.repositories.usuarios.listar", lambda _db, **kw: [])

    respuesta = cliente.get("/usuarios")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_get_roles_sin_permiso_es_403(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: set())

    respuesta = cliente.get("/roles")

    assert respuesta.status_code == 403


def test_get_permisos_sin_permiso_es_403(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: set())

    respuesta = cliente.get("/permisos")

    assert respuesta.status_code == 403


def test_usuario_desconocido_en_get_usuario_es_404_con_permiso(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"usuarios.gestionar"})
    monkeypatch.setattr("app.repositories.usuarios.obtener_por_id", lambda _db, _uid: None)

    respuesta = cliente.get("/usuarios/9999")

    assert respuesta.status_code == 404
