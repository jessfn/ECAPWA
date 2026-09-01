"""Pruebas de catálogos geográficos — ECA-006.

Mismo enfoque que `test_permisos.py`: sin PostgreSQL real, sustituyendo
`app.repositories.geo` por monkeypatch y usando `dependency_overrides` para
`get_current_user`.

Criterios de aceptación cubiertos:
- `GET /geo/municipios` sin `estado_id` → 400.
- `PATCH` sin permiso → 403.
- Filtro por `estado_id` funciona (verificado a nivel de repositorio, que es
  donde vive la consulta real).
"""
from __future__ import annotations

import uuid as uuid_lib

import pytest
from fastapi.testclient import TestClient

from app.models.geo import Estado, Municipio
from app.models.usuario import Usuario
from app.repositories import geo as repo_geo


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
    """Evita que los endpoints de escritura (`db.add`/`commit`/`refresh`)
    toquen una base de datos real: aquí no hay ninguna."""

    def add(self, _obj) -> None:
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


def _estado(id_=1, clave="09", nombre="Ciudad de México") -> Estado:
    return Estado(id=id_, clave_inegi=clave, nombre=nombre, abreviatura="CMX", activo=True)


def _municipio(id_=1, estado_id=1, clave="09002", nombre="Azcapotzalco") -> Municipio:
    return Municipio(id=id_, estado_id=estado_id, clave_inegi=clave, nombre=nombre, activo=True)


# --- lectura: cualquier usuario autenticado, sin permiso especial --------


def test_listar_estados_no_requiere_permiso_especial(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(repo_geo, "listar_estados", lambda _db, **kw: [_estado()])

    respuesta = cliente.get("/geo/estados")

    assert respuesta.status_code == 200
    assert respuesta.json()[0]["clave_inegi"] == "09"


def test_listar_municipios_sin_estado_id_es_400(cliente: TestClient) -> None:
    respuesta = cliente.get("/geo/municipios")

    assert respuesta.status_code == 400


def test_listar_municipios_con_estado_id_200(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    llamadas = {}

    def _fake_listar(_db, *, estado_id, solo_activos=False, texto=None):
        llamadas["estado_id"] = estado_id
        llamadas["texto"] = texto
        return [_municipio(estado_id=estado_id)]

    monkeypatch.setattr(repo_geo, "listar_municipios", _fake_listar)

    respuesta = cliente.get("/geo/municipios", params={"estado_id": 1, "q": "Azca"})

    assert respuesta.status_code == 200
    assert respuesta.json()[0]["estado_id"] == 1
    assert llamadas == {"estado_id": 1, "texto": "Azca"}


# --- edición: requiere geo.gestionar --------------------------------------


def test_patch_estado_sin_permiso_es_403(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: set())

    respuesta = cliente.patch("/geo/estados/1", json={"activo": False})

    assert respuesta.status_code == 403


def test_patch_estado_con_permiso_actualiza(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"geo.gestionar"})
    monkeypatch.setattr(repo_geo, "obtener_estado", lambda _db, _id: _estado())

    respuesta = cliente.patch("/geo/estados/1", json={"activo": False})

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False


def test_patch_estado_inexistente_es_404(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"geo.gestionar"})
    monkeypatch.setattr(repo_geo, "obtener_estado", lambda _db, _id: None)

    respuesta = cliente.patch("/geo/estados/9999", json={"activo": False})

    assert respuesta.status_code == 404


def test_patch_municipio_sin_permiso_es_403(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: set())

    respuesta = cliente.patch("/geo/municipios/1", json={"activo": False})

    assert respuesta.status_code == 403


def test_patch_municipio_con_permiso_actualiza(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"geo.gestionar"})
    monkeypatch.setattr(repo_geo, "obtener_municipio", lambda _db, _id: _municipio())

    respuesta = cliente.patch("/geo/municipios/1", json={"activo": False})

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False


# --- repositorio: filtro real, sin BD (in-memory vía SQLAlchemy no aplica
#     aquí — se prueba la semilla de estados directamente en el módulo de
#     migración, ver test_seed_estados_32_entidades) --------------------


def test_seed_estados_32_entidades() -> None:
    # El archivo de revisión empieza con dígitos (`0006_...`), así que no es
    # un nombre de módulo Python válido para un `import` normal — se carga
    # por ruta.
    import importlib.util
    import pathlib

    ruta = (
        pathlib.Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0006_seed_estados.py"
    )
    spec = importlib.util.spec_from_file_location("_revision_0006", ruta)
    modulo_seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo_seed)

    assert len(modulo_seed.ESTADOS) == 32
    claves = [c for c, _n, _a in modulo_seed.ESTADOS]
    assert len(set(claves)) == 32  # sin duplicados
    assert claves == sorted(claves)  # 01..32 en orden
