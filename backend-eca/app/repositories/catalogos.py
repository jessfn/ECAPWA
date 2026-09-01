"""Acceso a datos de catálogos de actividad — ECA-010."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalogos import Modalidad, SistemaProductivo, Subtema, Tema, TipoActividad

# Mapa clave→modelo usado por el router genérico `PATCH /catalogos/{tipo}/{id}`.
MODELOS_POR_TIPO = {
    "modalidades": Modalidad,
    "tipos-actividad": TipoActividad,
    "temas": Tema,
    "subtemas": Subtema,
    "sistemas-productivos": SistemaProductivo,
}


def _listar(db: Session, modelo, *, solo_activos: bool, filtro_extra=None) -> list:
    consulta = select(modelo).order_by(modelo.orden, modelo.nombre)
    if solo_activos:
        consulta = consulta.where(modelo.activo.is_(True))
    if filtro_extra is not None:
        consulta = consulta.where(filtro_extra)
    return list(db.execute(consulta).scalars())


def listar_modalidades(db: Session, *, solo_activos: bool = True) -> list[Modalidad]:
    return _listar(db, Modalidad, solo_activos=solo_activos)


def listar_tipos_actividad(db: Session, *, solo_activos: bool = True) -> list[TipoActividad]:
    return _listar(db, TipoActividad, solo_activos=solo_activos)


def listar_temas(db: Session, *, solo_activos: bool = True) -> list[Tema]:
    return _listar(db, Tema, solo_activos=solo_activos)


def listar_subtemas(db: Session, *, tema_id: int | None = None, solo_activos: bool = True) -> list[Subtema]:
    filtro = Subtema.tema_id == tema_id if tema_id is not None else None
    return _listar(db, Subtema, solo_activos=solo_activos, filtro_extra=filtro)


def listar_sistemas_productivos(db: Session, *, solo_activos: bool = True) -> list[SistemaProductivo]:
    return _listar(db, SistemaProductivo, solo_activos=solo_activos)


def obtener(db: Session, tipo: str, item_id: int):
    modelo = MODELOS_POR_TIPO.get(tipo)
    if modelo is None:
        return None
    return db.get(modelo, item_id)


def obtener_tema(db: Session, tema_id: int) -> Tema | None:
    return db.get(Tema, tema_id)


def crear_subtema(db: Session, subtema: Subtema) -> Subtema:
    db.add(subtema)
    db.flush()
    return subtema
