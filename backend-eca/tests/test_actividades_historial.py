"""Pruebas del historial/consulta admin de actividades — ECA-019.

Router con `TestClient` (mismo patrón que `test_ecas.py`): repositorio en
memoria + `db.get` falso, sin PostgreSQL real.

Criterios cubiertos:
- Los filtros del endpoint admin se combinan con AND.
- Un técnico sin `actividades.ver_todas` no puede usar `GET /actividades`.
- El detalle (`GET /actividades/{uuid}`) incluye la lista de evidencias.
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.models.actividad import Actividad
from app.models.evidencia import ActividadEvidencia
from app.models.usuario import Usuario
from app.repositories import actividades as repo_actividades
from app.repositories import evidencias as repo_evidencias


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


def _actividad(**overrides) -> Actividad:
    base = dict(
        id=1,
        uuid=uuid_lib.uuid4(),
        usuario_id=1,
        jornada_id=1,
        eca_id=5,
        modalidad_id=1,
        tipo_actividad_id=2,
        tema_id=None,
        subtema_id=None,
        sistema_productivo_id=None,
        descripcion="x",
        resultado=None,
        fecha_hora=datetime(2026, 3, 5, 9, tzinfo=timezone.utc),
        latitud=None,
        longitud=None,
        precision_gps_m=None,
        estado_gps=None,
        num_participantes=None,
        requiere_seguimiento=False,
        fecha_proximo_seguimiento=None,
        eliminado_en=None,
    )
    base.update(overrides)
    return Actividad(**base)


def test_listar_actividades_requiere_permiso(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: set())

    respuesta = cliente.get("/actividades")

    assert respuesta.status_code == 403


def test_listar_actividades_admin_combina_filtros_con_and(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"actividades.ver_todas"})

    capturado = {}

    def _listar_falso(_db, *, usuario_id=None, eca_id=None, municipio_id=None, tipo_actividad_id=None, tema_id=None, estado_gps=None, desde=None, hasta=None, page=1, page_size=50):
        capturado.update(
            usuario_id=usuario_id,
            eca_id=eca_id,
            municipio_id=municipio_id,
            tipo_actividad_id=tipo_actividad_id,
            tema_id=tema_id,
            estado_gps=estado_gps,
        )
        return [], 0

    monkeypatch.setattr(repo_actividades, "listar", _listar_falso)

    respuesta = cliente.get(
        "/actividades",
        params={"tecnico_id": 7, "eca_id": 5, "municipio_id": 3, "tipo_actividad_id": 2, "tema_id": 4, "estado_gps": "CON_GPS"},
    )

    assert respuesta.status_code == 200
    assert capturado == {
        "usuario_id": 7,
        "eca_id": 5,
        "municipio_id": 3,
        "tipo_actividad_id": 2,
        "tema_id": 4,
        "estado_gps": "CON_GPS",
    }


def test_detalle_incluye_evidencias(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"actividades.ver_propias"})

    actividad = _actividad(usuario_id=1)
    monkeypatch.setattr(repo_actividades, "obtener_por_uuid", lambda _db, _uuid: actividad)

    evidencia = ActividadEvidencia(
        id=1,
        uuid=uuid_lib.uuid4(),
        actividad_id=1,
        orden=1,
        storage_clave="x",
        nombre_archivo="foto.jpg",
        mime="image/jpeg",
        tamano_bytes=100,
        hash_sha256="abc",
        latitud=None,
        longitud=None,
        capturada_en=None,
    )
    monkeypatch.setattr(repo_evidencias, "listar_de_actividad", lambda _db, _aid: [evidencia])

    respuesta = cliente.get(f"/actividades/{actividad.uuid}")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo["evidencias"]) == 1
    assert cuerpo["evidencias"][0]["nombre_archivo"] == "foto.jpg"


def test_detalle_ajeno_sin_ver_todas_es_403(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.repositories import rbac as repo_rbac

    monkeypatch.setattr(repo_rbac, "permisos_efectivos_de", lambda _db, _uid: {"actividades.ver_propias"})

    actividad = _actividad(usuario_id=999)
    monkeypatch.setattr(repo_actividades, "obtener_por_uuid", lambda _db, _uuid: actividad)

    respuesta = cliente.get(f"/actividades/{actividad.uuid}")

    assert respuesta.status_code == 403
