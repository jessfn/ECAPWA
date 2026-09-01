"""Pruebas de catálogos de actividad — ECA-010.

Sin PostgreSQL real: repositorios en memoria vía monkeypatch, mismo patrón
que el resto de la suite.

Criterios de aceptación cubiertos:
- `actualizar_item` aplica solo los campos presentes en la petición.
- El rango `min_fotos <= max_fotos` se valida sobre el estado *efectivo* tras
  el cambio (no solo sobre los campos que llegaron en esta petición).
- `crear_subtema` rechaza un `tema_id` desconocido.
- El schema `TipoActividadEditarPeticion` valida rangos y orden relativo
  cuando ambos campos llegan juntos en la misma petición.
"""
from __future__ import annotations

import itertools

import pytest

from app.models.catalogos import Subtema, Tema, TipoActividad
from app.models.usuario import Usuario
from app.schemas.catalogos import TipoActividadEditarPeticion
from app.services import catalogos_service

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
    return Usuario(id=1, nombre="Ada", apellido_paterno="Admin", correo="admin@ejemplo.org", contrasena_hash="x")


def _tipo_actividad(**overrides) -> TipoActividad:
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


def test_actualizar_item_aplica_solo_campos_presentes(actor: Usuario) -> None:
    item = _tipo_actividad()

    resultado = catalogos_service.actualizar_item(
        DB, tipo="tipos-actividad", item=item, cambios={"nombre": "Capacitación técnica"}, actor=actor
    )

    assert resultado.nombre == "Capacitación técnica"
    assert resultado.min_fotos == 1  # sin tocar
    assert resultado.max_fotos == 3  # sin tocar


def test_actualizar_item_rechaza_rango_invalido_contra_valor_existente(actor: Usuario) -> None:
    # Solo se manda min_fotos, pero excede el max_fotos ya guardado (3).
    item = _tipo_actividad(min_fotos=1, max_fotos=3)

    with pytest.raises(catalogos_service.RangoFotosInvalidoError):
        catalogos_service.actualizar_item(
            DB, tipo="tipos-actividad", item=item, cambios={"min_fotos": 4}, actor=actor
        )


def test_actualizar_item_acepta_rango_valido_combinado(actor: Usuario) -> None:
    item = _tipo_actividad(min_fotos=1, max_fotos=3)

    resultado = catalogos_service.actualizar_item(
        DB, tipo="tipos-actividad", item=item, cambios={"min_fotos": 2, "max_fotos": 2}, actor=actor
    )

    assert resultado.min_fotos == 2
    assert resultado.max_fotos == 2


def test_actualizar_item_catalogo_simple_no_valida_fotos(actor: Usuario) -> None:
    item = Tema(id=1, clave="SUELO", nombre="Suelo", activo=True, orden=0)

    resultado = catalogos_service.actualizar_item(
        DB, tipo="temas", item=item, cambios={"nombre": "Manejo de suelo"}, actor=actor
    )

    assert resultado.nombre == "Manejo de suelo"


def test_crear_subtema_tema_inexistente_es_error(monkeypatch: pytest.MonkeyPatch, actor: Usuario) -> None:
    monkeypatch.setattr(catalogos_service.repo_catalogos, "obtener_tema", lambda _db, _id: None)

    with pytest.raises(catalogos_service.TemaInexistenteError):
        catalogos_service.crear_subtema(DB, tema_id=999, clave="X", nombre="X", orden=0, actor=actor)


def test_crear_subtema_exitoso(monkeypatch: pytest.MonkeyPatch, actor: Usuario) -> None:
    tema = Tema(id=1, clave="SUELO", nombre="Suelo", activo=True, orden=0)
    monkeypatch.setattr(catalogos_service.repo_catalogos, "obtener_tema", lambda _db, _id: tema)

    creados: list[Subtema] = []

    def _crear(_db, subtema: Subtema) -> Subtema:
        subtema.id = next(_contador_ids)
        creados.append(subtema)
        return subtema

    monkeypatch.setattr(catalogos_service.repo_catalogos, "crear_subtema", _crear)

    resultado = catalogos_service.crear_subtema(
        DB, tema_id=1, clave="FERT", nombre="Fertilización", orden=0, actor=actor
    )

    assert resultado.tema_id == 1
    assert resultado.nombre == "Fertilización"
    assert len(creados) == 1


# --- validación del schema de petición -------------------------------------


def test_peticion_edicion_rechaza_min_mayor_que_max() -> None:
    with pytest.raises(ValueError):
        TipoActividadEditarPeticion(min_fotos=3, max_fotos=1)


def test_peticion_edicion_rechaza_fuera_de_rango() -> None:
    with pytest.raises(ValueError):
        TipoActividadEditarPeticion(min_fotos=5)


def test_peticion_edicion_acepta_parcial() -> None:
    peticion = TipoActividadEditarPeticion(nombre="Nuevo nombre")

    assert peticion.model_dump(exclude_unset=True) == {"nombre": "Nuevo nombre"}
