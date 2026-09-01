"""Pruebas de evidencias fotográficas — ECA-015.

Sin PostgreSQL real ni disco real: repositorio y `Storage` en memoria vía
monkeypatch/fake, mismo patrón que el resto de la suite.

Criterios de aceptación cubiertos:
- Subir el mismo archivo (mismo `uuid`, o mismo hash) dos veces no duplica.
- Rechazo de `mime` no permitido y de tamaño excesivo.
- No se permite `orden` fuera de 1..3.
- Solo el dueño de la actividad puede subir evidencias a ella.
"""
from __future__ import annotations

import itertools
import uuid as uuid_lib

import pytest

from app.models.actividad import Actividad
from app.models.evidencia import ActividadEvidencia
from app.models.usuario import Usuario
from app.services import evidencias_service

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

    def delete(self, _obj) -> None:
        pass


class StorageFalso:
    def __init__(self) -> None:
        self.archivos: dict[str, bytes] = {}

    def guardar(self, clave, contenido) -> None:
        self.archivos[clave] = contenido

    def leer(self, clave) -> bytes:
        return self.archivos[clave]

    def eliminar(self, clave) -> None:
        self.archivos.pop(clave, None)


class RepoEvidenciasEnMemoria:
    def __init__(self) -> None:
        self.filas: list[ActividadEvidencia] = []

    def obtener_por_uuid(self, _db, uuid):
        return next((e for e in self.filas if e.uuid == uuid), None)

    def obtener_por_hash(self, _db, *, actividad_id, hash_sha256):
        return next(
            (e for e in self.filas if e.actividad_id == actividad_id and e.hash_sha256 == hash_sha256),
            None,
        )

    def listar_de_actividad(self, _db, actividad_id):
        return [e for e in self.filas if e.actividad_id == actividad_id]

    def crear(self, _db, evidencia: ActividadEvidencia) -> ActividadEvidencia:
        evidencia.id = next(_contador_ids)
        self.filas.append(evidencia)
        return evidencia

    def eliminar(self, _db, evidencia: ActividadEvidencia) -> None:
        self.filas.remove(evidencia)


@pytest.fixture
def db() -> DBFalsa:
    return DBFalsa()


@pytest.fixture
def storage() -> StorageFalso:
    return StorageFalso()


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch):
    repo_en_memoria = RepoEvidenciasEnMemoria()
    monkeypatch.setattr(evidencias_service.repo_evidencias, "obtener_por_uuid", repo_en_memoria.obtener_por_uuid)
    monkeypatch.setattr(evidencias_service.repo_evidencias, "obtener_por_hash", repo_en_memoria.obtener_por_hash)
    monkeypatch.setattr(
        evidencias_service.repo_evidencias, "listar_de_actividad", repo_en_memoria.listar_de_actividad
    )
    monkeypatch.setattr(evidencias_service.repo_evidencias, "crear", repo_en_memoria.crear)
    monkeypatch.setattr(evidencias_service.repo_evidencias, "eliminar", repo_en_memoria.eliminar)
    return repo_en_memoria


@pytest.fixture
def actor() -> Usuario:
    return Usuario(id=1, nombre="T", apellido_paterno="T", correo="tecnico@ejemplo.org", contrasena_hash="x")


@pytest.fixture
def actividad(actor: Usuario) -> Actividad:
    return Actividad(id=1, uuid=uuid_lib.uuid4(), usuario_id=actor.id, jornada_id=1, modalidad_id=1, tipo_actividad_id=1, descripcion="x", fecha_hora="2026-03-05T09:00:00Z")


CONTENIDO = b"contenido-de-imagen-de-prueba"


def _subir(db, actividad, actor, storage, **overrides):
    datos = dict(
        uuid=uuid_lib.uuid4(),
        orden=1,
        contenido=CONTENIDO,
        nombre_archivo="foto.jpg",
        mime="image/jpeg",
        latitud=None,
        longitud=None,
        capturada_en=None,
        actor=actor,
        storage=storage,
    )
    datos.update(overrides)
    return evidencias_service.subir(db, actividad=actividad, **datos)


def test_subir_evidencia(db, repo, storage, actividad, actor) -> None:
    evidencia = _subir(db, actividad, actor, storage)

    assert evidencia.actividad_id == actividad.id
    assert evidencia.orden == 1
    assert len(storage.archivos) == 1
    assert evidencia.hash_sha256


def test_subir_evidencia_mismo_uuid_es_idempotente(db, repo, storage, actividad, actor) -> None:
    identificador = uuid_lib.uuid4()

    primera = _subir(db, actividad, actor, storage, uuid=identificador)
    segunda = _subir(db, actividad, actor, storage, uuid=identificador)

    assert primera.id == segunda.id
    assert len(repo.filas) == 1


def test_subir_evidencia_mismo_contenido_distinto_uuid_es_idempotente(db, repo, storage, actividad, actor) -> None:
    primera = _subir(db, actividad, actor, storage)
    segunda = _subir(db, actividad, actor, storage, uuid=uuid_lib.uuid4(), orden=2)

    assert primera.id == segunda.id  # mismo hash → misma fila, no importa el `orden` pedido
    assert len(repo.filas) == 1


def test_subir_evidencia_reemplaza_la_del_mismo_orden(db, repo, storage, actividad, actor) -> None:
    primera = _subir(db, actividad, actor, storage, orden=1, contenido=b"foto-A")
    segunda = _subir(db, actividad, actor, storage, orden=1, contenido=b"foto-B")

    assert primera.id != segunda.id
    assert len(repo.filas) == 1  # la vieja se reemplazó, no se acumuló
    assert primera.storage_clave not in storage.archivos  # el archivo viejo se borró


def test_subir_evidencia_mime_no_permitido_es_error(db, repo, storage, actividad, actor) -> None:
    with pytest.raises(evidencias_service.MimeNoPermitidoError):
        _subir(db, actividad, actor, storage, mime="application/pdf")


def test_subir_evidencia_demasiado_grande_es_error(db, repo, storage, actividad, actor) -> None:
    grande = b"x" * (evidencias_service.TAMANO_MAXIMO_BYTES + 1)
    with pytest.raises(evidencias_service.ArchivoDemasiadoGrandeError):
        _subir(db, actividad, actor, storage, contenido=grande)


def test_subir_evidencia_orden_invalido_es_error(db, repo, storage, actividad, actor) -> None:
    with pytest.raises(evidencias_service.OrdenInvalidoError):
        _subir(db, actividad, actor, storage, orden=4)


def test_subir_evidencia_actividad_ajena_es_error(db, repo, storage, actividad, actor) -> None:
    otro = Usuario(id=2, nombre="B", apellido_paterno="B", correo="otro@ejemplo.org", contrasena_hash="x")
    with pytest.raises(evidencias_service.ActividadAjenaError):
        _subir(db, actividad, otro, storage)


def test_eliminar_evidencia_borra_archivo_y_fila(db, repo, storage, actividad, actor) -> None:
    evidencia = _subir(db, actividad, actor, storage)
    clave = evidencia.storage_clave

    evidencias_service.eliminar(db, evidencia=evidencia, actor=actor, storage=storage)

    assert clave not in storage.archivos
    assert evidencia not in repo.filas
