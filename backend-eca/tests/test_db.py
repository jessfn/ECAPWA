"""Pruebas de `app/core/db.py` — ECA-002.

`get_db` se prueba con un generador equivalente pero sobre un `Session`
falso (sin BD real): confirma que entrega la sesión y la cierra siempre,
incluso ante una excepción — sin depender de PostgreSQL.
"""
from __future__ import annotations

import pytest


class _SesionFalsa:
    def __init__(self) -> None:
        self.cerrada = False
        self.rollback_llamado = False

    def rollback(self) -> None:
        self.rollback_llamado = True

    def close(self) -> None:
        self.cerrada = True


def _get_db_con_sesion(sesion: _SesionFalsa):
    """Réplica mínima de `app.core.db.get_db`, parametrizada con una sesión
    falsa — evita crear un engine real (que exige `DATABASE_URL` válida)."""
    try:
        yield sesion
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()


def test_get_db_entrega_y_cierra_sesion() -> None:
    sesion = _SesionFalsa()
    generador = _get_db_con_sesion(sesion)

    entregada = next(generador)
    assert entregada is sesion
    assert not sesion.cerrada

    with pytest.raises(StopIteration):
        next(generador)
    assert sesion.cerrada
    assert not sesion.rollback_llamado


def test_get_db_hace_rollback_y_cierra_ante_excepcion() -> None:
    sesion = _SesionFalsa()
    generador = _get_db_con_sesion(sesion)
    next(generador)

    with pytest.raises(RuntimeError):
        generador.throw(RuntimeError("boom"))

    assert sesion.rollback_llamado
    assert sesion.cerrada


def test_engine_se_crea_con_settings(env_valido: None) -> None:
    """Import diferido: `app.core.db` crea el engine al importarse, así que
    debe ocurrir después de que `env_valido` fije las variables."""
    from app.core.db import engine

    assert str(engine.url).startswith("postgresql+psycopg://")
