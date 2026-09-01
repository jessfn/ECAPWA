"""Pruebas del router `/ecas` — ECA-007 (CRUD individual + permisos).

La lógica de importación masiva se prueba aparte en `test_importacion_eca.py`
(a nivel de servicio, sin pasar por HTTP). Aquí solo se cubre el CRUD
individual y que cada endpoint exija el permiso correcto.
"""
from __future__ import annotations

import uuid as uuid_lib

import pytest
from fastapi.testclient import TestClient

from app.models.eca import Eca
from app.models.usuario import Usuario
from app.repositories import ecas as repo_ecas


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
    def add(self, _obj) -> None:
        pass

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def refresh(self, _obj) -> None:
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


def _eca(id_=1, uuid_=None) -> Eca:
    return Eca(
        id=id_,
        uuid=uuid_ or uuid_lib.uuid4(),
        clave_fuente="ECA-001",
        clave_institucional=None,
        nombre="Escuela de prueba",
        estado_id=1,
        municipio_id=1,
        localidad_nombre=None,
        latitud=None,
        longitud=None,
        activo=True,
        fuente_carga="MANUAL",
    )


def test_listar_sin_permiso_es_403(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: set())

    respuesta = cliente.get("/ecas")

    assert respuesta.status_code == 403


def test_listar_con_permiso_devuelve_paginado(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"ecas.ver"})
    monkeypatch.setattr(repo_ecas, "listar", lambda _db, **kw: ([_eca()], 1))

    respuesta = cliente.get("/ecas")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 1
    assert cuerpo["resultados"][0]["clave_fuente"] == "ECA-001"


def test_obtener_inexistente_es_404(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"ecas.ver"})
    monkeypatch.setattr(repo_ecas, "obtener_por_id", lambda _db, _id: None)

    respuesta = cliente.get("/ecas/9999")

    assert respuesta.status_code == 404


def test_crear_eca_sin_permiso_es_403(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"ecas.ver"})

    respuesta = cliente.post(
        "/ecas", json={"nombre": "Nueva", "estado_id": 1, "municipio_id": 1}
    )

    assert respuesta.status_code == 403


def test_crear_eca_con_permiso_201(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    def _crear_eca(_db, eca):
        eca.id = 1
        eca.uuid = uuid_lib.uuid4()
        eca.activo = True
        return eca

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"ecas.gestionar"})
    monkeypatch.setattr(repo_ecas, "crear_eca", _crear_eca)

    respuesta = cliente.post(
        "/ecas", json={"nombre": "Nueva ECA", "estado_id": 1, "municipio_id": 1}
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == "Nueva ECA"
    assert respuesta.json()["fuente_carga"] == "MANUAL"


def test_importar_sin_permiso_es_403(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: set())

    respuesta = cliente.post(
        "/ecas/importar", files={"archivo": ("ecas.csv", b"a,b\n1,2\n", "text/csv")}
    )

    assert respuesta.status_code == 403


def test_importar_sin_identificador_es_422(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"ecas.importar"})

    csv_sin_id = b"nombre,estado_clave_inegi,municipio_clave_inegi\nX,09,09002\n"
    respuesta = cliente.post(
        "/ecas/importar", files={"archivo": ("ecas.csv", csv_sin_id, "text/csv")}
    )

    assert respuesta.status_code == 422


def test_confirmar_lote_inexistente_es_404(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"ecas.importar"})
    monkeypatch.setattr(repo_ecas, "obtener_lote_por_uuid", lambda _db, _uuid: None)

    respuesta = cliente.post(f"/ecas/importar/{uuid_lib.uuid4()}/confirmar")

    assert respuesta.status_code == 404
