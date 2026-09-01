"""Pruebas de ámbitos geográficos de técnico — ECA-008.

Sin PostgreSQL real: repositorios en memoria vía monkeypatch, mismo patrón
que el resto de la suite.

Criterios de aceptación cubiertos:
- `PUT` calcula altas/bajas correctamente (reemplazo del conjunto).
- No permite municipio inactivo ni desconocido.
- No duplica asignaciones ya activas.
- El histórico se conserva: una baja queda con `fecha_fin`, no se borra.
"""
from __future__ import annotations

import itertools

import pytest

from app.models.geo import Municipio
from app.models.usuario import Usuario
from app.repositories import ambitos as repo_ambitos
from app.services import ambitos_service, importacion_ambitos_service

_contador_ids = itertools.count(1)


class DBFalsa:
    def add(self, _obj) -> None:
        pass

    def commit(self) -> None:
        pass

    def flush(self) -> None:
        pass


class RepoAmbitosEnMemoria:
    def __init__(self) -> None:
        self.filas: list = []  # todas las filas, activas e históricas

    def listar_activos_de(self, _db, usuario_id: int) -> list:
        return [f for f in self.filas if f.usuario_id == usuario_id and f.activo]

    def crear(self, _db, *, usuario_id: int, municipio_id: int, asignado_por) -> object:
        class _Ambito:
            pass

        a = _Ambito()
        a.id = next(_contador_ids)
        a.usuario_id = usuario_id
        a.municipio_id = municipio_id
        a.activo = True
        a.fecha_fin = None
        a.fecha_inicio = "2026-01-01"
        a.asignado_por = asignado_por
        a.municipio = _municipios_globales[municipio_id]
        self.filas.append(a)
        return a

    def dar_de_baja(self, _db, ambito) -> None:
        ambito.activo = False
        ambito.fecha_fin = "2026-06-01"


_municipios_globales: dict[int, Municipio] = {
    1: Municipio(id=1, estado_id=1, clave_inegi="09002", nombre="Azcapotzalco", activo=True),
    2: Municipio(id=2, estado_id=1, clave_inegi="09003", nombre="Coyoacán", activo=True),
    3: Municipio(id=3, estado_id=1, clave_inegi="09004", nombre="Cuajimalpa", activo=False),  # inactivo
}


@pytest.fixture
def repos(monkeypatch: pytest.MonkeyPatch):
    repo_a = RepoAmbitosEnMemoria()
    monkeypatch.setattr(ambitos_service.repo_ambitos, "listar_activos_de", repo_a.listar_activos_de)
    monkeypatch.setattr(ambitos_service.repo_ambitos, "crear", repo_a.crear)
    monkeypatch.setattr(ambitos_service.repo_ambitos, "dar_de_baja", repo_a.dar_de_baja)
    monkeypatch.setattr(
        ambitos_service.repo_geo, "obtener_municipio", lambda _db, mid: _municipios_globales.get(mid)
    )
    monkeypatch.setattr(
        importacion_ambitos_service.repo_geo,
        "listar_todos_municipios",
        lambda _db: list(_municipios_globales.values()),
    )
    monkeypatch.setattr(importacion_ambitos_service.repo_ambitos, "listar_activos_de", repo_a.listar_activos_de)
    monkeypatch.setattr(importacion_ambitos_service.repo_ambitos, "crear", repo_a.crear)
    return repo_a


@pytest.fixture
def actor() -> Usuario:
    return Usuario(id=1, nombre="Ada", apellido_paterno="Admin", correo="admin@ejemplo.org", contrasena_hash="x")


DB = DBFalsa()


def test_reemplazar_ambito_asigna_municipios_nuevos(repos, actor: Usuario) -> None:
    resultado = ambitos_service.reemplazar_ambito(DB, usuario_id=10, municipio_ids=[1, 2], actor=actor)

    assert {r["municipio_id"] for r in resultado} == {1, 2}
    assert len(repos.listar_activos_de(DB, 10)) == 2


def test_reemplazar_ambito_calcula_altas_y_bajas(repos, actor: Usuario) -> None:
    ambitos_service.reemplazar_ambito(DB, usuario_id=10, municipio_ids=[1, 2], actor=actor)

    resultado = ambitos_service.reemplazar_ambito(DB, usuario_id=10, municipio_ids=[2], actor=actor)

    assert {r["municipio_id"] for r in resultado} == {2}
    # El municipio 1 debe quedar dado de baja (fecha_fin), no borrado.
    historico = [f for f in repos.filas if f.usuario_id == 10 and f.municipio_id == 1]
    assert len(historico) == 1
    assert historico[0].activo is False
    assert historico[0].fecha_fin is not None


def test_reemplazar_ambito_no_duplica_activos(repos, actor: Usuario) -> None:
    ambitos_service.reemplazar_ambito(DB, usuario_id=10, municipio_ids=[1], actor=actor)
    ambitos_service.reemplazar_ambito(DB, usuario_id=10, municipio_ids=[1, 2], actor=actor)

    activos_municipio_1 = [f for f in repos.filas if f.usuario_id == 10 and f.municipio_id == 1 and f.activo]
    assert len(activos_municipio_1) == 1  # no se creó una segunda fila activa


def test_reemplazar_ambito_municipio_inactivo_rechazado(repos, actor: Usuario) -> None:
    with pytest.raises(ambitos_service.MunicipioInactivoError):
        ambitos_service.reemplazar_ambito(DB, usuario_id=10, municipio_ids=[3], actor=actor)


def test_reemplazar_ambito_municipio_desconocido_rechazado(repos, actor: Usuario) -> None:
    with pytest.raises(ambitos_service.MunicipioDesconocidoError):
        ambitos_service.reemplazar_ambito(DB, usuario_id=10, municipio_ids=[9999], actor=actor)


# --- importación CSV -------------------------------------------------------


CSV_VALIDO = "correo_tecnico,clave_municipio\ntecnico@ejemplo.org,09002\n"
CSV_MUNICIPIO_INEXISTENTE = "correo_tecnico,clave_municipio\ntecnico@ejemplo.org,00000\n"


def test_importar_ambitos_correo_inexistente_es_error(
    repos, actor: Usuario, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(importacion_ambitos_service.repo_usuarios, "obtener_por_correo", lambda _db, _c: None)

    resultado = importacion_ambitos_service.importar_ambitos(DB, contenido_csv=CSV_VALIDO, actor=actor)

    assert resultado.asignadas == 0
    assert resultado.con_error == 1
    assert "no encontrado" in resultado.detalle[0].error.lower()


def test_importar_ambitos_municipio_inexistente_es_error(
    repos, actor: Usuario, monkeypatch: pytest.MonkeyPatch
) -> None:
    tecnico = Usuario(id=20, nombre="T", apellido_paterno="T", correo="tecnico@ejemplo.org", contrasena_hash="x")
    monkeypatch.setattr(importacion_ambitos_service.repo_usuarios, "obtener_por_correo", lambda _db, _c: tecnico)

    resultado = importacion_ambitos_service.importar_ambitos(
        DB, contenido_csv=CSV_MUNICIPIO_INEXISTENTE, actor=actor
    )

    assert resultado.asignadas == 0
    assert resultado.con_error == 1


def test_importar_ambitos_fila_valida_asigna(repos, actor: Usuario, monkeypatch: pytest.MonkeyPatch) -> None:
    tecnico = Usuario(id=20, nombre="T", apellido_paterno="T", correo="tecnico@ejemplo.org", contrasena_hash="x")
    monkeypatch.setattr(importacion_ambitos_service.repo_usuarios, "obtener_por_correo", lambda _db, _c: tecnico)

    resultado = importacion_ambitos_service.importar_ambitos(DB, contenido_csv=CSV_VALIDO, actor=actor)

    assert resultado.asignadas == 1
    assert resultado.con_error == 0
    assert len(repos.listar_activos_de(DB, 20)) == 1
