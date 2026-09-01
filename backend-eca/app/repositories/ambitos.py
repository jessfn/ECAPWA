"""Acceso a datos de `AmbitoTecnico` — ECA-008."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ambito import AmbitoTecnico


def listar_activos_de(db: Session, usuario_id: int) -> list[AmbitoTecnico]:
    return list(
        db.execute(
            select(AmbitoTecnico).where(
                AmbitoTecnico.usuario_id == usuario_id, AmbitoTecnico.activo.is_(True)
            )
        ).scalars()
    )


def crear(db: Session, *, usuario_id: int, municipio_id: int, asignado_por: int | None) -> AmbitoTecnico:
    ambito = AmbitoTecnico(usuario_id=usuario_id, municipio_id=municipio_id, asignado_por=asignado_por)
    db.add(ambito)
    db.flush()
    return ambito


def dar_de_baja(db: Session, ambito: AmbitoTecnico) -> None:
    ambito.activo = False
    ambito.fecha_fin = datetime.now(timezone.utc).date()
    db.add(ambito)
