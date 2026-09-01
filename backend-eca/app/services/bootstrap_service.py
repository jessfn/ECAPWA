"""Bootstrap y pull offline — ECA-018.

Entrega al técnico **solo su subconjunto relevante** (catálogos + geo +
ECA según la REGLA DE ECA de ECA-009) — nunca las ~5 000 ECA completas
(`03` §6.8).

**Desviación documentada de `pull`**: el ticket describe `GET
/sync/pull?desde=` como un delta "solo lo que cambió". El conjunto de ECA
de un técnico no depende únicamente de `actualizado_en` de cada ECA —
depende de la REGLA DE ECA completa (asignaciones directas, ámbito,
`regla_disponibilidad`), que puede cambiar sin que ninguna ECA individual
se haya tocado (p. ej. una asignación nueva). Calcular un delta *real* de
membresía de conjunto exigiría una bitácora de cambios que no existe en el
MVP. En su lugar, `pull` recalcula el subconjunto completo (igual que
`bootstrap`) y lo devuelve entero — el cliente simplemente reemplaza su
copia local. Sigue siendo correcto (nunca queda desactualizado) y el
tamaño se mantiene acotado por `eca.max_offline`, solo no es un delta
mínimo en bytes. `desde` se acepta en la firma por compatibilidad con el
ticket pero no cambia el resultado.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models.usuario import Usuario
from app.repositories import ambitos as repo_ambitos
from app.repositories import catalogos as repo_catalogos
from app.repositories import geo as repo_geo
from app.repositories import parametros_config as repo_config
from app.services import asignaciones_service

CLAVE_MAX_OFFLINE = "eca.max_offline"
MAX_OFFLINE_POR_DEFECTO = 1500
CLAVE_PRECISION_GPS = "gps.precision_valida_maxima_m"
PRECISION_GPS_POR_DEFECTO = 30


def _config(db: Session) -> dict:
    settings = get_settings()
    return {
        "regla_disponibilidad": repo_config.obtener_valor(
            db, asignaciones_service.CLAVE_REGLA, por_defecto=asignaciones_service.REGLA_POR_DEFECTO
        ),
        "gps_precision_maxima_m": repo_config.obtener_valor(
            db, CLAVE_PRECISION_GPS, por_defecto=PRECISION_GPS_POR_DEFECTO
        ),
        "eca_max_offline": repo_config.obtener_valor(db, CLAVE_MAX_OFFLINE, por_defecto=MAX_OFFLINE_POR_DEFECTO),
        "sesion_offline_dias": settings.OFFLINE_SESSION_DIAS,
    }


def _catalogos(db: Session) -> dict:
    return {
        "modalidades": repo_catalogos.listar_modalidades(db, solo_activos=True),
        "tipos_actividad": repo_catalogos.listar_tipos_actividad(db, solo_activos=True),
        "temas": repo_catalogos.listar_temas(db, solo_activos=True),
        "subtemas": repo_catalogos.listar_subtemas(db, solo_activos=True),
        "sistemas_productivos": repo_catalogos.listar_sistemas_productivos(db, solo_activos=True),
    }


def _subconjunto_ecas_y_geo(db: Session, actor: Usuario, *, max_offline: int) -> tuple[list[dict], list[int], dict]:
    ecas = asignaciones_service.ecas_del_tecnico(db, actor.id)

    aviso = None
    if len(ecas) > max_offline:
        aviso = (
            f"Tu conjunto de ECA disponibles ({len(ecas)}) supera el límite offline "
            f"({max_offline}). Se entregan las primeras {max_offline}; pide al administrador "
            "acotar tu ámbito o cargar asignaciones directas."
        )
        ecas = ecas[:max_offline]

    ambitos = repo_ambitos.listar_activos_de(db, actor.id)
    municipio_ids_ambito = {a.municipio_id for a in ambitos}
    municipio_ids = municipio_ids_ambito | {e["municipio_id"] for e in ecas}

    municipios = [repo_geo.obtener_municipio(db, mid) for mid in municipio_ids]
    municipios = [m for m in municipios if m is not None]
    estado_ids = {m.estado_id for m in municipios}
    estados = [repo_geo.obtener_estado(db, eid) for eid in estado_ids]
    estados = [e for e in estados if e is not None]

    return ecas, sorted(municipio_ids_ambito), {
        "estados": estados,
        "municipios": municipios,
        "ecas": ecas,
        "aviso": aviso,
    }


def bootstrap(db: Session, actor: Usuario) -> dict:
    config = _config(db)
    _, ambito_municipio_ids, subconjunto = _subconjunto_ecas_y_geo(
        db, actor, max_offline=config["eca_max_offline"]
    )

    return {
        "generado_en": datetime.now(timezone.utc),
        "catalogos": _catalogos(db),
        "geo": {"estados": subconjunto["estados"], "municipios": subconjunto["municipios"]},
        "ambito": ambito_municipio_ids,
        "ecas": subconjunto["ecas"],
        "config": config,
        "aviso": subconjunto["aviso"],
    }


def pull(db: Session, actor: Usuario, *, desde: datetime | None = None) -> dict:
    # Ver docstring del módulo: `desde` no filtra el resultado en el MVP.
    return bootstrap(db, actor)
