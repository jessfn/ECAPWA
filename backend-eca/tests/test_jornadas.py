"""Pruebas de jornadas — ECA-012.

Sin PostgreSQL real: repositorio en memoria vía monkeypatch, mismo patrón
que el resto de la suite.

Criterios de aceptación cubiertos:
- No se abren dos jornadas principales activas el mismo día (idempotente,
  no error): un segundo `POST` con `uuid` distinto el mismo día devuelve la
  jornada ya existente.
- `POST` repetido con el mismo `uuid` no duplica (idempotente por `uuid`).
- Cerrar una jornada ya cerrada es idempotente.
- `fin_en` no puede ser anterior a `inicio_en`.
"""
from __future__ import annotations

import itertools
import uuid as uuid_lib
from datetime import datetime, timezone

import pytest

from app.models.jornada import Jornada
from app.models.usuario import Usuario
from app.schemas.jornada import GpsPeticion
from app.services import jornadas_service

_contador_ids = itertools.count(1)


class DBFalsa:
    def add(self, _obj) -> None:
        pass

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def refresh(self, _obj) -> None:
        pass


DB = DBFalsa()


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
        filas = [j for j in self.filas if j.usuario_id == usuario_id]
        if fecha is not None:
            filas = [j for j in filas if j.fecha == fecha]
        return filas


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch):
    repo_en_memoria = RepoJornadasEnMemoria()
    monkeypatch.setattr(jornadas_service.repo_jornadas, "obtener_por_uuid", repo_en_memoria.obtener_por_uuid)
    monkeypatch.setattr(
        jornadas_service.repo_jornadas, "obtener_abierta_del_dia", repo_en_memoria.obtener_abierta_del_dia
    )
    monkeypatch.setattr(jornadas_service.repo_jornadas, "crear", repo_en_memoria.crear)
    monkeypatch.setattr(jornadas_service.repo_jornadas, "listar_de_usuario", repo_en_memoria.listar_de_usuario)
    return repo_en_memoria


INICIO = datetime(2026, 3, 5, 8, 0, tzinfo=timezone.utc)


def test_iniciar_jornada_crea_una_nueva(repo, actor: Usuario) -> None:
    jornada = jornadas_service.iniciar(DB, uuid=uuid_lib.uuid4(), inicio_en=INICIO, gps=None, actor=actor)

    assert jornada.estado == "ABIERTA"
    assert jornada.usuario_id == actor.id
    assert len(repo.filas) == 1


def test_iniciar_jornada_mismo_uuid_es_idempotente(repo, actor: Usuario) -> None:
    identificador = uuid_lib.uuid4()
    primera = jornadas_service.iniciar(DB, uuid=identificador, inicio_en=INICIO, gps=None, actor=actor)
    segunda = jornadas_service.iniciar(DB, uuid=identificador, inicio_en=INICIO, gps=None, actor=actor)

    assert primera.id == segunda.id
    assert len(repo.filas) == 1


def test_iniciar_jornada_mismo_dia_distinto_uuid_devuelve_la_existente(repo, actor: Usuario) -> None:
    primera = jornadas_service.iniciar(DB, uuid=uuid_lib.uuid4(), inicio_en=INICIO, gps=None, actor=actor)
    segunda = jornadas_service.iniciar(DB, uuid=uuid_lib.uuid4(), inicio_en=INICIO, gps=None, actor=actor)

    assert primera.id == segunda.id
    assert len(repo.filas) == 1  # no se duplicó


def test_iniciar_jornada_con_gps(repo, actor: Usuario) -> None:
    gps = GpsPeticion(latitud=19.4, longitud=-99.1, precision_gps_m=8.5, estado_gps="CON_GPS")

    jornada = jornadas_service.iniciar(DB, uuid=uuid_lib.uuid4(), inicio_en=INICIO, gps=gps, actor=actor)

    assert jornada.latitud_inicio == 19.4
    assert jornada.estado_gps_inicio == "CON_GPS"


def test_cerrar_jornada(repo, actor: Usuario) -> None:
    identificador = uuid_lib.uuid4()
    jornadas_service.iniciar(DB, uuid=identificador, inicio_en=INICIO, gps=None, actor=actor)
    fin = datetime(2026, 3, 5, 17, 0, tzinfo=timezone.utc)

    jornada = jornadas_service.cerrar(DB, uuid=identificador, fin_en=fin, gps=None, actor=actor)

    assert jornada.estado == "CERRADA"
    assert jornada.fin_en == fin


def test_cerrar_jornada_ya_cerrada_es_idempotente(repo, actor: Usuario) -> None:
    identificador = uuid_lib.uuid4()
    jornadas_service.iniciar(DB, uuid=identificador, inicio_en=INICIO, gps=None, actor=actor)
    fin = datetime(2026, 3, 5, 17, 0, tzinfo=timezone.utc)
    jornadas_service.cerrar(DB, uuid=identificador, fin_en=fin, gps=None, actor=actor)

    # Segundo cierre con otra hora: no debe cambiar nada, solo devolver la ya cerrada.
    otra_hora = datetime(2026, 3, 5, 18, 0, tzinfo=timezone.utc)
    jornada = jornadas_service.cerrar(DB, uuid=identificador, fin_en=otra_hora, gps=None, actor=actor)

    assert jornada.fin_en == fin  # no se sobrescribió


def test_cerrar_jornada_fin_antes_de_inicio_es_error(repo, actor: Usuario) -> None:
    identificador = uuid_lib.uuid4()
    jornadas_service.iniciar(DB, uuid=identificador, inicio_en=INICIO, gps=None, actor=actor)
    antes = datetime(2026, 3, 5, 7, 0, tzinfo=timezone.utc)

    with pytest.raises(jornadas_service.RangoFechasInvalidoError):
        jornadas_service.cerrar(DB, uuid=identificador, fin_en=antes, gps=None, actor=actor)


def test_cerrar_jornada_desconocida_es_error(repo, actor: Usuario) -> None:
    with pytest.raises(jornadas_service.JornadaNoEncontradaError):
        jornadas_service.cerrar(DB, uuid=uuid_lib.uuid4(), fin_en=INICIO, gps=None, actor=actor)


def test_cerrar_jornada_de_otro_usuario_es_error(repo, actor: Usuario) -> None:
    identificador = uuid_lib.uuid4()
    jornadas_service.iniciar(DB, uuid=identificador, inicio_en=INICIO, gps=None, actor=actor)
    otro = Usuario(id=2, nombre="B", apellido_paterno="B", correo="otro@ejemplo.org", contrasena_hash="x")

    with pytest.raises(jornadas_service.JornadaNoEncontradaError):
        jornadas_service.cerrar(DB, uuid=identificador, fin_en=INICIO, gps=None, actor=otro)
