"""Lógica de negocio de asignaciones técnico↔ECA y la REGLA DE ECA — ECA-009.

REGLA DE ECA (`06_PLAN_IMPLEMENTACION_ECA.md`, ticket ECA-009), implementada
aquí y consumida por `GET /usuarios/me/ecas`:

    si existe asignación activa en asignaciones_tecnico_eca para el técnico:
        conjunto = esas ECA
    si no:
        conjunto = ECA activas cuyo municipio_id está en el ámbito activo del técnico

Controlada por `parametros_config.eca.regla_disponibilidad`
(`ASIGNADAS_LUEGO_AMBITO` por defecto — el comportamiento de arriba;
`SOLO_ASIGNADAS` nunca cae al ámbito; `SOLO_AMBITO` ignora las asignaciones
directas) para poder ajustarla **sin desplegar código** (criterio de
aceptación del ticket).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.models.asignacion_eca import AsignacionTecnicoEca
from app.models.usuario import Usuario
from app.repositories import ambitos as repo_ambitos
from app.repositories import asignaciones as repo_asignaciones
from app.repositories import ecas as repo_ecas
from app.repositories import parametros_config as repo_config

CLAVE_REGLA = "eca.regla_disponibilidad"
REGLA_POR_DEFECTO = "ASIGNADAS_LUEGO_AMBITO"
REGLAS_VALIDAS = ("ASIGNADAS_LUEGO_AMBITO", "SOLO_ASIGNADAS", "SOLO_AMBITO")


class AsignacionDuplicadaError(Exception):
    pass


def _ecas_por_asignacion_directa(db: Session, usuario_id: int) -> list[dict]:
    asignaciones = repo_asignaciones.listar_activas(db, usuario_id=usuario_id)
    return [
        {
            "eca_id": a.eca.id,
            "eca_uuid": a.eca.uuid,
            "eca_nombre": a.eca.nombre,
            "municipio_id": a.eca.municipio_id,
            "origen": "ASIGNACION_DIRECTA",
        }
        for a in asignaciones
        if a.eca.eliminado_en is None and a.eca.activo
    ]


def _ecas_por_ambito(db: Session, usuario_id: int) -> list[dict]:
    ambitos = repo_ambitos.listar_activos_de(db, usuario_id)
    municipio_ids = {a.municipio_id for a in ambitos}
    ecas = repo_ecas.listar_activas_en_municipios(db, municipio_ids)
    return [
        {
            "eca_id": e.id,
            "eca_uuid": e.uuid,
            "eca_nombre": e.nombre,
            "municipio_id": e.municipio_id,
            "origen": "AMBITO",
        }
        for e in ecas
    ]


def ecas_del_tecnico(db: Session, usuario_id: int) -> list[dict]:
    regla = repo_config.obtener_valor(db, CLAVE_REGLA, por_defecto=REGLA_POR_DEFECTO)
    if regla not in REGLAS_VALIDAS:
        regla = REGLA_POR_DEFECTO

    if regla == "SOLO_AMBITO":
        return _ecas_por_ambito(db, usuario_id)

    directas = _ecas_por_asignacion_directa(db, usuario_id)
    if directas:
        return directas
    if regla == "SOLO_ASIGNADAS":
        return []
    return _ecas_por_ambito(db, usuario_id)  # ASIGNADAS_LUEGO_AMBITO, sin directas


def crear_asignacion(
    db: Session, *, usuario_id: int, eca_id: int, actor: Usuario, origen: str = "MANUAL"
) -> AsignacionTecnicoEca:
    if repo_asignaciones.obtener_activa(db, usuario_id=usuario_id, eca_id=eca_id) is not None:
        raise AsignacionDuplicadaError("Ya existe una asignación activa para ese técnico y esa ECA.")

    asignacion = repo_asignaciones.crear(
        db, usuario_id=usuario_id, eca_id=eca_id, origen=origen, asignado_por=actor.id
    )
    registrar_evento(
        db,
        accion="asignacion.alta",
        modulo="asignaciones",
        actor_usuario_id=actor.id,
        entidad_tipo="asignacion_tecnico_eca",
        entidad_id=asignacion.id,
        entidad_uuid=asignacion.uuid,
        datos_despues={"usuario_id": usuario_id, "eca_id": eca_id},
    )
    db.commit()
    db.refresh(asignacion)
    return asignacion


def dar_de_baja_asignacion(db: Session, *, asignacion: AsignacionTecnicoEca, actor: Usuario) -> None:
    repo_asignaciones.dar_de_baja(db, asignacion)
    registrar_evento(
        db,
        accion="asignacion.baja",
        modulo="asignaciones",
        actor_usuario_id=actor.id,
        entidad_tipo="asignacion_tecnico_eca",
        entidad_id=asignacion.id,
        entidad_uuid=asignacion.uuid,
    )
    db.commit()
