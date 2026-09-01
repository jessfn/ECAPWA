"""Pruebas de actividades — ECA-013.

Sin PostgreSQL real: repositorios en memoria + `db.get` monkeypatcheado,
mismo patrón que el resto de la suite.

Criterios de aceptación cubiertos:
- `POST` con el mismo `uuid` no duplica (idempotente).
- Tipo con `requiere_eca=true` sin `eca_id` → error.
- `subtema_id` de otro tema → error.
- `num_participantes` en un tipo que no lo permite → error.
- Jornada desconocida o de otro técnico → error.
"""
from __future__ import annotations

import itertools
import uuid as uuid_lib
from datetime import datetime, timezone

import pytest

from app.models.actividad import Actividad
from app.models.catalogos import Subtema, TipoActividad
from app.models.jornada import Jornada
from app.models.usuario import Usuario
from app.schemas.gps import GpsPeticion
from app.services import actividades_service

_contador_ids = itertools.count(1)


class DBFalsa:
    def __init__(self) -> None:
        self._objetos: dict = {}

    def add(self, _obj) -> None:
        pass

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def refresh(self, _obj) -> None:
        pass

    def registrar(self, modelo, id_, obj) -> None:
        self._objetos[(modelo, id_)] = obj

    def get(self, modelo, id_):
        return self._objetos.get((modelo, id_))


@pytest.fixture
def db() -> DBFalsa:
    return DBFalsa()


@pytest.fixture
def actor() -> Usuario:
    return Usuario(id=1, nombre="T", apellido_paterno="T", correo="tecnico@ejemplo.org", contrasena_hash="x")


@pytest.fixture
def jornada(actor: Usuario) -> Jornada:
    return Jornada(id=1, uuid=uuid_lib.uuid4(), usuario_id=actor.id, fecha="2026-03-05", estado="ABIERTA", inicio_en=datetime(2026, 3, 5, 8, tzinfo=timezone.utc))


class RepoActividadesEnMemoria:
    def __init__(self) -> None:
        self.filas: list[Actividad] = []

    def obtener_por_uuid(self, _db, uuid):
        return next((a for a in self.filas if a.uuid == uuid), None)

    def crear(self, _db, actividad: Actividad) -> Actividad:
        actividad.id = next(_contador_ids)
        self.filas.append(actividad)
        return actividad


@pytest.fixture
def repo_actividades(monkeypatch: pytest.MonkeyPatch):
    repo = RepoActividadesEnMemoria()
    monkeypatch.setattr(actividades_service.repo_actividades, "obtener_por_uuid", repo.obtener_por_uuid)
    monkeypatch.setattr(actividades_service.repo_actividades, "crear", repo.crear)
    return repo


@pytest.fixture
def repo_jornadas(monkeypatch: pytest.MonkeyPatch, jornada: Jornada):
    monkeypatch.setattr(
        actividades_service.repo_jornadas, "obtener_por_uuid", lambda _db, uuid: jornada if uuid == jornada.uuid else None
    )
    return jornada


def _tipo(**overrides) -> TipoActividad:
    base = dict(
        id=next(_contador_ids),
        clave="CAP",
        nombre="Capacitación",
        activo=True,
        orden=0,
        requiere_evidencia=True,
        min_fotos=1,
        max_fotos=3,
        permite_participantes=True,
        requiere_eca=True,
    )
    base.update(overrides)
    return TipoActividad(**base)


DATOS_BASE = dict(
    eca_id=5,
    modalidad_id=1,
    tema_id=None,
    subtema_id=None,
    sistema_productivo_id=None,
    descripcion="Se explicó manejo de plagas.",
    resultado=None,
    fecha_hora=datetime(2026, 3, 5, 9, tzinfo=timezone.utc),
    num_participantes=None,
    requiere_seguimiento=False,
    fecha_proximo_seguimiento=None,
)


def test_crear_actividad(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo(requiere_eca=True)
    db.registrar(TipoActividad, tipo.id, tipo)

    actividad = actividades_service.crear(
        db, uuid=uuid_lib.uuid4(), jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=actor, **DATOS_BASE
    )

    assert actividad.usuario_id == actor.id
    assert actividad.jornada_id == repo_jornadas.id
    assert len(repo_actividades.filas) == 1


def test_crear_actividad_mismo_uuid_es_idempotente(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo()
    db.registrar(TipoActividad, tipo.id, tipo)
    identificador = uuid_lib.uuid4()

    primera = actividades_service.crear(
        db, uuid=identificador, jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=actor, **DATOS_BASE
    )
    segunda = actividades_service.crear(
        db, uuid=identificador, jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=actor, **DATOS_BASE
    )

    assert primera.id == segunda.id
    assert len(repo_actividades.filas) == 1


def test_crear_actividad_requiere_eca_sin_eca_es_error(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo(requiere_eca=True)
    db.registrar(TipoActividad, tipo.id, tipo)
    datos = dict(DATOS_BASE, eca_id=None)

    with pytest.raises(actividades_service.EcaRequeridaError):
        actividades_service.crear(
            db, uuid=uuid_lib.uuid4(), jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=actor, **datos
        )


def test_crear_actividad_participantes_no_permitidos_es_error(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo(permite_participantes=False)
    db.registrar(TipoActividad, tipo.id, tipo)
    datos = dict(DATOS_BASE, num_participantes=5)

    with pytest.raises(actividades_service.ParticipantesNoPermitidosError):
        actividades_service.crear(
            db, uuid=uuid_lib.uuid4(), jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=actor, **datos
        )


def test_crear_actividad_subtema_de_otro_tema_es_error(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo()
    db.registrar(TipoActividad, tipo.id, tipo)
    subtema = Subtema(id=1, clave="X", nombre="X", activo=True, orden=0, tema_id=99)
    db.registrar(Subtema, subtema.id, subtema)
    datos = dict(DATOS_BASE, tema_id=1, subtema_id=subtema.id)  # subtema pertenece al tema 99, no al 1

    with pytest.raises(actividades_service.SubtemaIncoherenteError):
        actividades_service.crear(
            db, uuid=uuid_lib.uuid4(), jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=actor, **datos
        )


def test_crear_actividad_tipo_desconocido_es_error(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    with pytest.raises(actividades_service.TipoActividadDesconocidoError):
        actividades_service.crear(
            db, uuid=uuid_lib.uuid4(), jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=9999, actor=actor, **DATOS_BASE
        )


def test_crear_actividad_jornada_desconocida_es_error(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo()
    db.registrar(TipoActividad, tipo.id, tipo)

    with pytest.raises(actividades_service.JornadaDesconocidaError):
        actividades_service.crear(
            db, uuid=uuid_lib.uuid4(), jornada_uuid=uuid_lib.uuid4(), tipo_actividad_id=tipo.id, actor=actor, **DATOS_BASE
        )


def test_crear_actividad_jornada_de_otro_usuario_es_error(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo()
    db.registrar(TipoActividad, tipo.id, tipo)
    otro = Usuario(id=2, nombre="B", apellido_paterno="B", correo="otro@ejemplo.org", contrasena_hash="x")

    with pytest.raises(actividades_service.JornadaDesconocidaError):
        actividades_service.crear(
            db, uuid=uuid_lib.uuid4(), jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=otro, **DATOS_BASE
        )


# --- GPS (ECA-014) ----------------------------------------------------------


def test_crear_actividad_con_gps_bueno(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo()
    db.registrar(TipoActividad, tipo.id, tipo)
    gps = GpsPeticion(latitud=19.4, longitud=-99.1, precision_gps_m=8.5, estado_gps="CON_GPS")

    actividad = actividades_service.crear(
        db, uuid=uuid_lib.uuid4(), jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=actor, gps=gps, **DATOS_BASE
    )

    assert actividad.latitud == 19.4
    assert actividad.estado_gps == "CON_GPS"


def test_crear_actividad_sin_gps_no_bloquea(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo()
    db.registrar(TipoActividad, tipo.id, tipo)
    gps = GpsPeticion(estado_gps="SIN_GPS")

    actividad = actividades_service.crear(
        db, uuid=uuid_lib.uuid4(), jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=actor, gps=gps, **DATOS_BASE
    )

    assert actividad.latitud is None
    assert actividad.estado_gps == "SIN_GPS"


def test_crear_actividad_con_gps_ausente_no_bloquea(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo()
    db.registrar(TipoActividad, tipo.id, tipo)

    actividad = actividades_service.crear(
        db, uuid=uuid_lib.uuid4(), jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=actor, gps=None, **DATOS_BASE
    )

    assert actividad.latitud is None
    assert actividad.estado_gps is None


def test_crear_actividad_con_gps_imprecisa(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo()
    db.registrar(TipoActividad, tipo.id, tipo)
    gps = GpsPeticion(latitud=19.4, longitud=-99.1, precision_gps_m=120, estado_gps="GPS_IMPRECISO")

    actividad = actividades_service.crear(
        db, uuid=uuid_lib.uuid4(), jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=actor, gps=gps, **DATOS_BASE
    )

    assert actividad.estado_gps == "GPS_IMPRECISO"


def test_crear_actividad_con_gps_true_sin_coordenadas_es_error(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo()
    db.registrar(TipoActividad, tipo.id, tipo)
    gps = GpsPeticion(estado_gps="CON_GPS")

    with pytest.raises(actividades_service.GpsInvalidoError):
        actividades_service.crear(
            db, uuid=uuid_lib.uuid4(), jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=actor, gps=gps, **DATOS_BASE
        )


def test_crear_actividad_con_lat_sin_lon_es_error(db: DBFalsa, repo_actividades, repo_jornadas, actor: Usuario) -> None:
    tipo = _tipo()
    db.registrar(TipoActividad, tipo.id, tipo)
    gps = GpsPeticion(latitud=19.4, longitud=None)

    with pytest.raises(actividades_service.GpsInvalidoError):
        actividades_service.crear(
            db, uuid=uuid_lib.uuid4(), jornada_uuid=repo_jornadas.uuid, tipo_actividad_id=tipo.id, actor=actor, gps=gps, **DATOS_BASE
        )
