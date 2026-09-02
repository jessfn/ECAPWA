"""Pruebas del motor de sincronización (push) — ECA-017.

Sin PostgreSQL real: se monkeypatchean los módulos de repositorio
directamente (`app.repositories.jornadas`, `.actividades`,
`.dispositivos`) — como son el mismo objeto de módulo que usan
`jornadas_service`/`actividades_service`/`sync_service` internamente
(`from app.repositories import X as repo_X`), un solo parche por función
cubre a los tres.

Criterios de aceptación cubiertos:
- Reenviar el mismo lote dos veces → 0 duplicados (segunda vez todo
  `DUPLICADO`, nada se crea de nuevo).
- Un objeto con `tipo_actividad` inexistente → `RECHAZADO`, los demás
  `APLICADO`.
- Jornada referida por `jornada_uuid` inexistente → la actividad queda
  `RECHAZADO` con motivo claro.
- El cierre de una jornada ya sincronizada (mismo `uuid`, ahora con
  `fin_en`) se aplica en un push posterior.
"""
from __future__ import annotations

import itertools
import uuid as uuid_lib
from datetime import datetime, timezone

import pytest

import app.repositories.actividades as repo_actividades_modulo
import app.repositories.dispositivos as repo_dispositivos_modulo
import app.repositories.jornadas as repo_jornadas_modulo
from app.models.actividad import Actividad
from app.models.catalogos import TipoActividad
from app.models.dispositivo import Dispositivo
from app.models.jornada import Jornada
from app.models.usuario import Usuario
from app.schemas.sync import ActividadSyncItem, JornadaSyncItem
from app.services import sync_service

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


class RepoJornadasEnMemoria:
    def __init__(self) -> None:
        self.filas: list[Jornada] = []

    def obtener_por_uuid(self, _db, uuid):
        return next((j for j in self.filas if j.uuid == uuid), None)

    def obtener_abierta_del_dia(self, _db, *, usuario_id, fecha):
        return next(
            (j for j in self.filas if j.usuario_id == usuario_id and j.fecha == fecha and j.estado != "ANULADA"),
            None,
        )

    def crear(self, _db, jornada: Jornada) -> Jornada:
        jornada.id = next(_contador_ids)
        self.filas.append(jornada)
        return jornada

    def listar_de_usuario(self, _db, *, usuario_id, fecha=None):
        return [j for j in self.filas if j.usuario_id == usuario_id]


class RepoActividadesEnMemoria:
    def __init__(self) -> None:
        self.filas: list[Actividad] = []

    def obtener_por_uuid(self, _db, uuid):
        return next((a for a in self.filas if a.uuid == uuid), None)

    def crear(self, _db, actividad: Actividad) -> Actividad:
        actividad.id = next(_contador_ids)
        self.filas.append(actividad)
        return actividad


class RepoDispositivosEnMemoria:
    def __init__(self) -> None:
        self.filas: list[Dispositivo] = []

    def obtener_por_uuid(self, _db, uuid):
        return next((d for d in self.filas if d.uuid == uuid), None)

    def crear(self, _db, dispositivo: Dispositivo) -> Dispositivo:
        dispositivo.id = next(_contador_ids)
        self.filas.append(dispositivo)
        return dispositivo


@pytest.fixture
def repos(monkeypatch: pytest.MonkeyPatch):
    jornadas = RepoJornadasEnMemoria()
    actividades = RepoActividadesEnMemoria()
    dispositivos = RepoDispositivosEnMemoria()

    monkeypatch.setattr(repo_jornadas_modulo, "obtener_por_uuid", jornadas.obtener_por_uuid)
    monkeypatch.setattr(repo_jornadas_modulo, "obtener_abierta_del_dia", jornadas.obtener_abierta_del_dia)
    monkeypatch.setattr(repo_jornadas_modulo, "crear", jornadas.crear)
    monkeypatch.setattr(repo_jornadas_modulo, "listar_de_usuario", jornadas.listar_de_usuario)

    monkeypatch.setattr(repo_actividades_modulo, "obtener_por_uuid", actividades.obtener_por_uuid)
    monkeypatch.setattr(repo_actividades_modulo, "crear", actividades.crear)

    monkeypatch.setattr(repo_dispositivos_modulo, "obtener_por_uuid", dispositivos.obtener_por_uuid)
    monkeypatch.setattr(repo_dispositivos_modulo, "crear", dispositivos.crear)

    return type("Repos", (), {"jornadas": jornadas, "actividades": actividades, "dispositivos": dispositivos})()


DISPOSITIVO_UUID = uuid_lib.uuid4()
INICIO = datetime(2026, 3, 5, 8, 0, tzinfo=timezone.utc)


def _tipo_actividad(db: DBFalsa, **overrides) -> TipoActividad:
    base = dict(
        id=next(_contador_ids),
        clave="CAP",
        nombre="Capacitación",
        activo=True,
        orden=0,
        requiere_evidencia=False,
        min_fotos=0,
        max_fotos=3,
        permite_participantes=True,
        requiere_eca=False,
    )
    base.update(overrides)
    tipo = TipoActividad(**base)
    db.registrar(TipoActividad, tipo.id, tipo)
    return tipo


def test_push_jornada_nueva_es_aplicado(db: DBFalsa, repos, actor: Usuario) -> None:
    item = JornadaSyncItem(uuid=uuid_lib.uuid4(), inicio_en=INICIO, nota="Detalle.")

    resultados = sync_service.push(db, dispositivo_uuid=DISPOSITIVO_UUID, jornadas=[item], actividades=[], actor=actor)

    assert resultados[0].resultado == "APLICADO"
    assert len(repos.jornadas.filas) == 1
    assert repos.jornadas.filas[0].sincronizado_en is not None


def test_push_mismo_lote_dos_veces_no_duplica(db: DBFalsa, repos, actor: Usuario) -> None:
    tipo = _tipo_actividad(db)
    jornada_item = JornadaSyncItem(uuid=uuid_lib.uuid4(), inicio_en=INICIO, nota="Detalle.")
    actividad_item = ActividadSyncItem(
        uuid=uuid_lib.uuid4(),
        jornada_uuid=jornada_item.uuid,
        modalidad_id=1,
        tipo_actividad_id=tipo.id,
        descripcion="Visita de campo.",
        fecha_hora=INICIO,
    )

    primera = sync_service.push(
        db, dispositivo_uuid=DISPOSITIVO_UUID, jornadas=[jornada_item], actividades=[actividad_item], actor=actor
    )
    segunda = sync_service.push(
        db, dispositivo_uuid=DISPOSITIVO_UUID, jornadas=[jornada_item], actividades=[actividad_item], actor=actor
    )

    assert [r.resultado for r in primera] == ["APLICADO", "APLICADO"]
    assert [r.resultado for r in segunda] == ["DUPLICADO", "DUPLICADO"]
    assert len(repos.jornadas.filas) == 1
    assert len(repos.actividades.filas) == 1


def test_push_tipo_actividad_inexistente_es_rechazado_los_demas_aplicados(db: DBFalsa, repos, actor: Usuario) -> None:
    tipo = _tipo_actividad(db)
    jornada_item = JornadaSyncItem(uuid=uuid_lib.uuid4(), inicio_en=INICIO, nota="Detalle.")
    buena = ActividadSyncItem(
        uuid=uuid_lib.uuid4(),
        jornada_uuid=jornada_item.uuid,
        modalidad_id=1,
        tipo_actividad_id=tipo.id,
        descripcion="Actividad válida.",
        fecha_hora=INICIO,
    )
    mala = ActividadSyncItem(
        uuid=uuid_lib.uuid4(),
        jornada_uuid=jornada_item.uuid,
        modalidad_id=1,
        tipo_actividad_id=9999,
        descripcion="Actividad con tipo inexistente.",
        fecha_hora=INICIO,
    )

    resultados = sync_service.push(
        db, dispositivo_uuid=DISPOSITIVO_UUID, jornadas=[jornada_item], actividades=[buena, mala], actor=actor
    )

    resultados_actividades = resultados[1:]
    assert resultados_actividades[0].resultado == "APLICADO"
    assert resultados_actividades[1].resultado == "RECHAZADO"
    assert resultados_actividades[1].error
    assert len(repos.actividades.filas) == 1  # solo la buena se creó


def test_push_actividad_con_jornada_inexistente_es_rechazada(db: DBFalsa, repos, actor: Usuario) -> None:
    tipo = _tipo_actividad(db)
    item = ActividadSyncItem(
        uuid=uuid_lib.uuid4(),
        jornada_uuid=uuid_lib.uuid4(),  # no viene en este lote ni existe
        modalidad_id=1,
        tipo_actividad_id=tipo.id,
        descripcion="x",
        fecha_hora=INICIO,
    )

    resultados = sync_service.push(db, dispositivo_uuid=DISPOSITIVO_UUID, jornadas=[], actividades=[item], actor=actor)

    assert resultados[0].resultado == "RECHAZADO"
    assert "esconocida" in resultados[0].error or "jornada" in resultados[0].error.lower()


def test_push_cierre_de_jornada_ya_sincronizada_se_aplica(db: DBFalsa, repos, actor: Usuario) -> None:
    identificador = uuid_lib.uuid4()
    inicio_item = JornadaSyncItem(uuid=identificador, inicio_en=INICIO, nota="Detalle.")
    sync_service.push(db, dispositivo_uuid=DISPOSITIVO_UUID, jornadas=[inicio_item], actividades=[], actor=actor)

    fin = datetime(2026, 3, 5, 17, 0, tzinfo=timezone.utc)
    cierre_item = JornadaSyncItem(uuid=identificador, inicio_en=INICIO, nota="Detalle.", fin_en=fin, nota_fin="Detalle de cierre.")
    resultados = sync_service.push(
        db, dispositivo_uuid=DISPOSITIVO_UUID, jornadas=[cierre_item], actividades=[], actor=actor
    )

    assert resultados[0].resultado == "APLICADO"
    assert repos.jornadas.filas[0].estado == "CERRADA"
    assert len(repos.jornadas.filas) == 1  # no se creó una segunda fila


def test_push_registra_dispositivo_sobre_la_marcha(db: DBFalsa, repos, actor: Usuario) -> None:
    item = JornadaSyncItem(uuid=uuid_lib.uuid4(), inicio_en=INICIO, nota="Detalle.")

    sync_service.push(db, dispositivo_uuid=DISPOSITIVO_UUID, jornadas=[item], actividades=[], actor=actor)

    assert len(repos.dispositivos.filas) == 1
    assert repos.dispositivos.filas[0].uuid == DISPOSITIVO_UUID


def test_registrar_dispositivo_es_idempotente(db: DBFalsa, repos, actor: Usuario) -> None:
    primero = sync_service.registrar_dispositivo(
        db, uuid=DISPOSITIVO_UUID, plataforma="Android", user_agent="ua-1", actor=actor
    )
    segundo = sync_service.registrar_dispositivo(
        db, uuid=DISPOSITIVO_UUID, plataforma="Android", user_agent="ua-2", actor=actor
    )

    assert primero.id == segundo.id
    assert len(repos.dispositivos.filas) == 1
    assert segundo.user_agent == "ua-2"
