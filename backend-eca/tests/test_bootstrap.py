"""Pruebas de bootstrap/pull offline — ECA-018.

Sin PostgreSQL real: repositorios en memoria vía monkeypatch, mismo patrón
que el resto de la suite.

Criterios de aceptación cubiertos:
- `bootstrap_service` aplica la REGLA DE ECA (asignadas → si no, ámbito) y
  respeta `regla_disponibilidad`.
- El conjunto se recorta a `eca.max_offline` y queda un aviso.
- `pull` no es distinto de `bootstrap` (ver deviación documentada) pero
  sigue siendo correcto/reflejando el estado actual.
"""
from __future__ import annotations

import pytest

from app.models.geo import Estado, Municipio
from app.models.usuario import Usuario
from app.services import asignaciones_service, bootstrap_service


class _AmbitoFalso:
    def __init__(self, municipio_id: int) -> None:
        self.municipio_id = municipio_id


@pytest.fixture
def actor() -> Usuario:
    return Usuario(id=1, nombre="T", apellido_paterno="T", correo="tecnico@ejemplo.org", contrasena_hash="x")


@pytest.fixture
def db():
    return object()  # no se usa de verdad: todo pasa por los repos monkeypatcheados


@pytest.fixture
def catalogos_vacios(monkeypatch: pytest.MonkeyPatch):
    for nombre in ("listar_modalidades", "listar_tipos_actividad", "listar_temas", "listar_subtemas", "listar_sistemas_productivos"):
        monkeypatch.setattr(bootstrap_service.repo_catalogos, nombre, lambda *_a, **_k: [])


@pytest.fixture
def geo_falso(monkeypatch: pytest.MonkeyPatch):
    municipios = {
        1: Municipio(id=1, estado_id=1, clave_inegi="09001", nombre="M1", activo=True),
        2: Municipio(id=2, estado_id=1, clave_inegi="09002", nombre="M2", activo=True),
    }
    estados = {1: Estado(id=1, clave_inegi="09", nombre="CDMX", activo=True)}
    monkeypatch.setattr(bootstrap_service.repo_geo, "obtener_municipio", lambda _db, mid: municipios.get(mid))
    monkeypatch.setattr(bootstrap_service.repo_geo, "obtener_estado", lambda _db, eid: estados.get(eid))


@pytest.fixture
def config_por_defecto(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(bootstrap_service.repo_config, "obtener_valor", lambda _db, _clave, *, por_defecto=None: por_defecto)


def test_bootstrap_usa_ecas_del_tecnico_via_regla_de_eca(
    env_valido, db, actor, catalogos_vacios, geo_falso, config_por_defecto, monkeypatch: pytest.MonkeyPatch
) -> None:
    ecas = [{"eca_id": 10, "eca_uuid": "00000000-0000-0000-0000-000000000001", "eca_nombre": "ECA 1", "municipio_id": 1, "origen": "ASIGNACION_DIRECTA"}]
    monkeypatch.setattr(asignaciones_service, "ecas_del_tecnico", lambda _db, _uid: ecas)
    monkeypatch.setattr(bootstrap_service.repo_ambitos, "listar_activos_de", lambda _db, _uid: [_AmbitoFalso(2)])

    resultado = bootstrap_service.bootstrap(db, actor)

    assert [e["eca_id"] for e in resultado["ecas"]] == [10]
    assert resultado["ambito"] == [2]
    # geo incluye tanto el municipio del ámbito (2) como el de la ECA entregada (1)
    assert {m.id for m in resultado["geo"]["municipios"]} == {1, 2}
    assert resultado["aviso"] is None


def test_bootstrap_recorta_al_maximo_offline_y_deja_aviso(
    env_valido, db, actor, catalogos_vacios, geo_falso, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        bootstrap_service.repo_config,
        "obtener_valor",
        lambda _db, clave, *, por_defecto=None: 2 if clave == "eca.max_offline" else por_defecto,
    )
    ecas = [
        {"eca_id": i, "eca_uuid": f"00000000-0000-0000-0000-00000000000{i}", "eca_nombre": f"ECA {i}", "municipio_id": 1, "origen": "AMBITO"}
        for i in range(1, 6)
    ]
    monkeypatch.setattr(asignaciones_service, "ecas_del_tecnico", lambda _db, _uid: ecas)
    monkeypatch.setattr(bootstrap_service.repo_ambitos, "listar_activos_de", lambda _db, _uid: [])

    resultado = bootstrap_service.bootstrap(db, actor)

    assert len(resultado["ecas"]) == 2
    assert resultado["aviso"] is not None
    assert "2" in resultado["aviso"]


def test_bootstrap_sin_ecas_ni_ambito_no_falla(
    env_valido, db, actor, catalogos_vacios, geo_falso, config_por_defecto, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(asignaciones_service, "ecas_del_tecnico", lambda _db, _uid: [])
    monkeypatch.setattr(bootstrap_service.repo_ambitos, "listar_activos_de", lambda _db, _uid: [])

    resultado = bootstrap_service.bootstrap(db, actor)

    assert resultado["ecas"] == []
    assert resultado["ambito"] == []
    assert resultado["geo"]["municipios"] == []
    assert resultado["geo"]["estados"] == []


def test_config_incluye_sesion_offline_dias(
    env_valido, db, actor, catalogos_vacios, geo_falso, config_por_defecto, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(asignaciones_service, "ecas_del_tecnico", lambda _db, _uid: [])
    monkeypatch.setattr(bootstrap_service.repo_ambitos, "listar_activos_de", lambda _db, _uid: [])

    resultado = bootstrap_service.bootstrap(db, actor)

    assert resultado["config"]["sesion_offline_dias"] >= 1
    assert resultado["config"]["regla_disponibilidad"] == asignaciones_service.REGLA_POR_DEFECTO


def test_pull_devuelve_el_mismo_subconjunto_que_bootstrap(
    env_valido, db, actor, catalogos_vacios, geo_falso, config_por_defecto, monkeypatch: pytest.MonkeyPatch
) -> None:
    ecas = [{"eca_id": 1, "eca_uuid": "00000000-0000-0000-0000-000000000001", "eca_nombre": "ECA 1", "municipio_id": 1, "origen": "AMBITO"}]
    monkeypatch.setattr(asignaciones_service, "ecas_del_tecnico", lambda _db, _uid: ecas)
    monkeypatch.setattr(bootstrap_service.repo_ambitos, "listar_activos_de", lambda _db, _uid: [])

    resultado = bootstrap_service.pull(db, actor, desde=None)

    assert [e["eca_id"] for e in resultado["ecas"]] == [1]
