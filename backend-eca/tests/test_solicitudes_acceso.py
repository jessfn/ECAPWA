"""Pruebas de listar/resolver solicitudes de acceso — ECA-020b.

Mismo patrón que `test_actividades_historial.py`: `TestClient` con
`repo_rbac.permisos_efectivos_de` monkeypatcheado (sin BD real) para simular
el permiso `usuarios.gestionar`.

Criterios cubiertos:
- Sin el permiso, `GET`/`PATCH` devuelven 403.
- `GET` lista lo que devuelva el repositorio.
- `PATCH` marca la solicitud aprobada/rechazada y no se puede resolver dos
  veces.
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.models.solicitud_acceso import SolicitudAcceso
from app.models.usuario import Usuario
from app.repositories import rbac as repo_rbac
from app.repositories import solicitudes_acceso as repo_solicitudes


@pytest.fixture
def usuario_falso() -> Usuario:
    return Usuario(
        id=1,
        uuid=uuid_lib.uuid4(),
        nombre="Ada",
        apellido_paterno="Admin",
        correo="admin@ejemplo.org",
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


def _solicitud(**overrides) -> SolicitudAcceso:
    base = dict(
        id=1,
        nombre="Ana Técnica",
        correo="ana@ejemplo.org",
        telefono="555",
        notas="quiero acceso",
        estado="pendiente",
        atendida_por=None,
        atendida_en=None,
        creado_en=datetime(2026, 3, 5, 9, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return SolicitudAcceso(**base)


def test_listar_sin_permiso_es_403(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: set())

    respuesta = cliente.get("/solicitudes-acceso")

    assert respuesta.status_code == 403


def test_listar_devuelve_lo_del_repositorio(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"usuarios.gestionar"})
    monkeypatch.setattr(repo_solicitudes, "listar", lambda _db, estado=None: [_solicitud()])

    respuesta = cliente.get("/solicitudes-acceso")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo) == 1
    assert cuerpo[0]["correo"] == "ana@ejemplo.org"
    assert cuerpo[0]["estado"] == "pendiente"


def test_resolver_aprueba_y_marca_atendida(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"usuarios.gestionar"})
    solicitud = _solicitud()
    monkeypatch.setattr(repo_solicitudes, "obtener_por_id", lambda _db, _id: solicitud)

    def _resolver_falso(_db, *, solicitud, estado, atendida_por):
        solicitud.estado = estado
        solicitud.atendida_por = atendida_por
        return solicitud

    monkeypatch.setattr(repo_solicitudes, "resolver", _resolver_falso)

    respuesta = cliente.patch("/solicitudes-acceso/1", json={"estado": "aprobada"})

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "aprobada"


def test_resolver_solicitud_inexistente_es_404(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"usuarios.gestionar"})
    monkeypatch.setattr(repo_solicitudes, "obtener_por_id", lambda _db, _id: None)

    respuesta = cliente.patch("/solicitudes-acceso/999", json={"estado": "aprobada"})

    assert respuesta.status_code == 404


def test_resolver_solicitud_ya_atendida_es_409(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"usuarios.gestionar"})
    monkeypatch.setattr(
        repo_solicitudes, "obtener_por_id", lambda _db, _id: _solicitud(estado="rechazada")
    )

    respuesta = cliente.patch("/solicitudes-acceso/1", json={"estado": "aprobada"})

    assert respuesta.status_code == 409
