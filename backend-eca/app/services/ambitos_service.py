"""Lógica de negocio de ámbitos geográficos de técnico — ECA-008."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.models.usuario import Usuario
from app.repositories import ambitos as repo_ambitos
from app.repositories import geo as repo_geo


class MunicipioInactivoError(Exception):
    pass


class MunicipioDesconocidoError(Exception):
    pass


def obtener_ambito(db: Session, usuario_id: int) -> list[dict]:
    activos = repo_ambitos.listar_activos_de(db, usuario_id)
    return [
        {
            "municipio_id": a.municipio_id,
            "municipio_nombre": a.municipio.nombre,
            "estado_id": a.municipio.estado_id,
            "fecha_inicio": a.fecha_inicio,
        }
        for a in activos
    ]


def reemplazar_ambito(
    db: Session, *, usuario_id: int, municipio_ids: list[int], actor: Usuario
) -> list[dict]:
    """Deja activos exactamente los municipios de `municipio_ids`: da de baja
    (con `fecha_fin`, conserva historial) los que sobran y da de alta los
    que faltan. No duplica asignaciones ya activas."""
    for municipio_id in municipio_ids:
        municipio = repo_geo.obtener_municipio(db, municipio_id)
        if municipio is None:
            raise MunicipioDesconocidoError(f"Municipio desconocido: {municipio_id}")
        if not municipio.activo:
            raise MunicipioInactivoError(f"El municipio {municipio.nombre} está inactivo.")

    activos = repo_ambitos.listar_activos_de(db, usuario_id)
    ids_activos = {a.municipio_id for a in activos}
    ids_nuevos = set(municipio_ids)

    for ambito in activos:
        if ambito.municipio_id not in ids_nuevos:
            repo_ambitos.dar_de_baja(db, ambito)

    for municipio_id in ids_nuevos - ids_activos:
        repo_ambitos.crear(db, usuario_id=usuario_id, municipio_id=municipio_id, asignado_por=actor.id)

    registrar_evento(
        db,
        accion="ambito.reemplazo",
        modulo="ambitos",
        actor_usuario_id=actor.id,
        entidad_tipo="usuario",
        entidad_id=usuario_id,
        datos_antes={"municipio_ids": sorted(ids_activos)},
        datos_despues={"municipio_ids": sorted(ids_nuevos)},
    )
    db.commit()
    return obtener_ambito(db, usuario_id)
