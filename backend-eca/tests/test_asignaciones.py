"""Pruebas de asignaciones técnico↔ECA y la REGLA DE ECA — ECA-009.

Sin PostgreSQL real: repositorios en memoria vía monkeypatch.

Criterios de aceptación cubiertos:
- `GET /usuarios/me/ecas` implementa exactamente la REGLA DE ECA: devuelve
  las asignadas directas si existen; si no, las del ámbito.
- El cambio de `regla_disponibilidad` altera el resultado sin desplegar
  código (se lee de `parametros_config` en cada llamada).
- No duplica asignaciones activas.
"""
from __future__ import annotations

import itertools
import uuid as uuid_lib

import pytest

from app.models.eca import Eca
from app.models.usuario import Usuario
from app.services import asignaciones_service as svc

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


def _eca(id_: int, municipio_id: int = 1, activo: bool = True) -> Eca:
    return Eca(
        id=id_,
        uuid=uuid_lib.uuid4(),
        nombre=f"ECA {id_}",
        estado_id=1,
        municipio_id=municipio_id,
        activo=activo,
    )


class _AsignacionFalsa:
    def __init__(self, usuario_id: int, eca: Eca) -> None:
        self.id = next(_contador_ids)
        self.uuid = uuid_lib.uuid4()
        self.usuario_id = usuario_id
        self.eca = eca
        self.activo = True
        self.fecha_fin = None


class _AmbitoFalso:
    def __init__(self, municipio_id: int) -> None:
        self.municipio_id = municipio_id


class RepoAsignacionesEnMemoria:
    def __init__(self) -> None:
        self.filas: list[_AsignacionFalsa] = []

    def listar_activas(self, _db, *, usuario_id=None, eca_id=None):
        return [
            f
            for f in self.filas
            if f.activo
            and (usuario_id is None or f.usuario_id == usuario_id)
            and (eca_id is None or f.eca.id == eca_id)
        ]

    def obtener_activa(self, _db, *, usuario_id: int, eca_id: int):
        for f in self.filas:
            if f.usuario_id == usuario_id and f.eca.id == eca_id and f.activo:
                return f
        return None

    def crear(self, _db, *, usuario_id, eca_id, origen, asignado_por, lote_importacion_id=None):
        asignacion = _AsignacionFalsa(usuario_id, _ecas_globales[eca_id])
        self.filas.append(asignacion)
        return asignacion

    def dar_de_baja(self, _db, asignacion) -> None:
        asignacion.activo = False
        asignacion.fecha_fin = "2026-06-01"


_ecas_globales: dict[int, Eca] = {1: _eca(1, municipio_id=10), 2: _eca(2, municipio_id=20)}


@pytest.fixture
def repos(monkeypatch: pytest.MonkeyPatch):
    repo_a = RepoAsignacionesEnMemoria()
    ambitos_por_usuario: dict[int, list[_AmbitoFalso]] = {}
    valores_config: dict[str, str] = {}

    monkeypatch.setattr(svc.repo_asignaciones, "listar_activas", repo_a.listar_activas)
    monkeypatch.setattr(svc.repo_asignaciones, "obtener_activa", repo_a.obtener_activa)
    monkeypatch.setattr(svc.repo_asignaciones, "crear", repo_a.crear)
    monkeypatch.setattr(svc.repo_asignaciones, "dar_de_baja", repo_a.dar_de_baja)
    monkeypatch.setattr(svc.repo_ambitos, "listar_activos_de", lambda _db, uid: ambitos_por_usuario.get(uid, []))
    monkeypatch.setattr(
        svc.repo_ecas,
        "listar_activas_en_municipios",
        lambda _db, municipio_ids: [e for e in _ecas_globales.values() if e.municipio_id in municipio_ids],
    )
    monkeypatch.setattr(
        svc.repo_config, "obtener_valor", lambda _db, clave, por_defecto=None: valores_config.get(clave, por_defecto)
    )

    repo_a.ambitos_por_usuario = ambitos_por_usuario
    repo_a.valores_config = valores_config
    return repo_a


@pytest.fixture
def actor() -> Usuario:
    return Usuario(id=1, nombre="Ada", apellido_paterno="Admin", correo="admin@ejemplo.org", contrasena_hash="x")


DB = DBFalsa()


def test_sin_asignaciones_ni_ambito_devuelve_vacio(repos) -> None:
    assert svc.ecas_del_tecnico(DB, usuario_id=10) == []


def test_sin_asignaciones_usa_ambito(repos) -> None:
    repos.ambitos_por_usuario[10] = [_AmbitoFalso(municipio_id=10)]

    resultado = svc.ecas_del_tecnico(DB, usuario_id=10)

    assert len(resultado) == 1
    assert resultado[0]["eca_id"] == 1
    assert resultado[0]["origen"] == "AMBITO"


def test_con_asignacion_directa_ignora_el_ambito(repos, actor: Usuario) -> None:
    repos.ambitos_por_usuario[10] = [_AmbitoFalso(municipio_id=20)]  # vería la ECA 2 por ámbito
    svc.crear_asignacion(DB, usuario_id=10, eca_id=1, actor=actor)  # pero tiene asignación directa a la 1

    resultado = svc.ecas_del_tecnico(DB, usuario_id=10)

    assert [r["eca_id"] for r in resultado] == [1]
    assert resultado[0]["origen"] == "ASIGNACION_DIRECTA"


def test_regla_solo_asignadas_no_cae_al_ambito(repos) -> None:
    repos.valores_config["eca.regla_disponibilidad"] = "SOLO_ASIGNADAS"
    repos.ambitos_por_usuario[10] = [_AmbitoFalso(municipio_id=10)]

    assert svc.ecas_del_tecnico(DB, usuario_id=10) == []  # sin directas, y no cae al ámbito


def test_regla_solo_ambito_ignora_asignaciones_directas(repos, actor: Usuario) -> None:
    repos.valores_config["eca.regla_disponibilidad"] = "SOLO_AMBITO"
    repos.ambitos_por_usuario[10] = [_AmbitoFalso(municipio_id=20)]
    svc.crear_asignacion(DB, usuario_id=10, eca_id=1, actor=actor)

    resultado = svc.ecas_del_tecnico(DB, usuario_id=10)

    assert [r["eca_id"] for r in resultado] == [2]  # ignora la asignación directa a la 1


def test_regla_desconocida_cae_al_valor_por_defecto(repos) -> None:
    repos.valores_config["eca.regla_disponibilidad"] = "REGLA_QUE_NO_EXISTE"
    repos.ambitos_por_usuario[10] = [_AmbitoFalso(municipio_id=10)]

    resultado = svc.ecas_del_tecnico(DB, usuario_id=10)

    assert [r["eca_id"] for r in resultado] == [1]  # se comportó como ASIGNADAS_LUEGO_AMBITO


def test_crear_asignacion_duplicada_rechazada(repos, actor: Usuario) -> None:
    svc.crear_asignacion(DB, usuario_id=10, eca_id=1, actor=actor)

    with pytest.raises(svc.AsignacionDuplicadaError):
        svc.crear_asignacion(DB, usuario_id=10, eca_id=1, actor=actor)

    assert len(repos.listar_activas(DB, usuario_id=10)) == 1  # no se duplicó


def test_dar_de_baja_conserva_historico(repos, actor: Usuario) -> None:
    asignacion = svc.crear_asignacion(DB, usuario_id=10, eca_id=1, actor=actor)

    svc.dar_de_baja_asignacion(DB, asignacion=asignacion, actor=actor)

    assert asignacion.activo is False
    assert asignacion.fecha_fin is not None
    assert asignacion in repos.filas  # sigue existiendo, solo inactiva
