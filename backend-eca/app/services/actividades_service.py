"""Lógica de negocio de actividad — ECA-013.

Las reglas de catálogo (`requiere_eca`, `permite_participantes`, coherencia
tema/subtema) se validan **aquí**, en backend, nunca solo en el formulario
de la PWA (criterio de aceptación del ticket).
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.audit import registrar_evento
from app.models.actividad import Actividad
from app.models.catalogos import SistemaProductivo, Subtema, Tema, TipoActividad
from app.models.usuario import Usuario
from app.repositories import actividades as repo_actividades
from app.repositories import jornadas as repo_jornadas
from app.schemas.gps import GpsPeticion


class JornadaDesconocidaError(Exception):
    pass


class TipoActividadDesconocidoError(Exception):
    pass


class EcaRequeridaError(Exception):
    pass


class OtroTextoRequeridoError(Exception):
    pass


class ParticipantesNoPermitidosError(Exception):
    pass


class SubtemaIncoherenteError(Exception):
    pass


class GpsInvalidoError(ValueError):
    pass


class ActividadNoEncontradaError(Exception):
    pass


def _validar_gps(gps: GpsPeticion) -> None:
    if (gps.latitud is None) != (gps.longitud is None):
        raise GpsInvalidoError("latitud y longitud deben venir juntas o ninguna.")
    if gps.estado_gps == "CON_GPS" and (gps.latitud is None or gps.longitud is None):
        raise GpsInvalidoError("estado_gps='CON_GPS' requiere latitud y longitud.")
    # Ubicación OBLIGATORIA (pedido explícito): una actividad no puede
    # guardarse sin coordenadas reales. Bloquea estado SIN_GPS o cualquier
    # envío sin latitud/longitud, tanto por el endpoint online como por sync.
    if gps.latitud is None or gps.longitud is None:
        raise GpsInvalidoError("La ubicación (GPS) es obligatoria para registrar una actividad.")


# Solo el acento de las vocales — la "ñ" NO se toca: es una letra propia
# del español, no una "n acentuada". Un `unicodedata.normalize("NFD", …)`
# genérico (quitar toda marca combinante) la convierte en "N" — bug real
# probado con "Muñoz" -> "MUNOZ", "Peña" -> "PENA", que corrompería nombres
# de lugar comunes en México.
_MAPA_ACENTOS = str.maketrans("áéíóúü", "aeiouu")


def _normalizar_texto_libre(texto: str | None) -> str | None:
    """MAYÚSCULAS y sin tildes en vocales (pedido explícito) — usada tanto
    para `eca_nombre` como para el texto de cualquier opción "Otro". La PWA
    ya manda el texto así (transformado mientras el técnico escribe), pero
    se vuelve a normalizar aquí por si acaso: un cliente viejo, la API
    usada directo, o cualquier otro origen no debe poder colar texto con
    minúsculas o acentos."""
    if texto is None:
        return None
    limpio = texto.strip()
    if not limpio:
        return None
    return limpio.lower().translate(_MAPA_ACENTOS).upper()


# Claves de la opción "Otro" en cada catálogo (ver 0012_seed_catalogos):
# "OTR" en tipos_actividad, "OTRO" en temas/subtemas/sistemas_productivos.
_CLAVE_OTRO_TIPO_ACTIVIDAD = "OTR"
_CLAVE_OTRO = "OTRO"


def _validar_y_normalizar_otro(texto: str | None, *, es_otro: bool, etiqueta: str) -> str | None:
    """Cuando la opción elegida en el catálogo es "Otro", el texto que
    especifica cuál es ese "otro" es obligatorio — sin esto, el admin solo
    veía "Otro" en el listado sin saber a qué se refería el técnico. Si la
    opción elegida NO es "Otro", el texto (si vino) se descarta: no tiene
    sentido guardarlo pegado a una opción distinta."""
    if not es_otro:
        return None
    normalizado = _normalizar_texto_libre(texto)
    if not normalizado:
        raise OtroTextoRequeridoError(f'Escribe cuál es el/la "{etiqueta}" cuando eliges la opción Otro.')
    return normalizado


def crear(
    db: Session,
    *,
    uuid: uuid_lib.UUID,
    jornada_uuid: uuid_lib.UUID,
    eca_id: int | None,
    eca_nombre: str | None = None,
    modalidad_id: int,
    tipo_actividad_id: int,
    tema_id: int | None,
    subtema_id: int | None,
    sistema_productivo_id: int | None,
    tipo_actividad_otro_texto: str | None = None,
    tema_otro_texto: str | None = None,
    subtema_otro_texto: str | None = None,
    sistema_productivo_otro_texto: str | None = None,
    descripcion: str,
    resultado: str | None,
    fecha_hora: datetime,
    num_participantes: int | None,
    requiere_seguimiento: bool,
    fecha_proximo_seguimiento: date | None,
    actor: Usuario,
    gps: GpsPeticion | None = None,
) -> Actividad:
    existente = repo_actividades.obtener_por_uuid(db, uuid)
    if existente is not None:
        return existente  # idempotente por uuid

    gps = gps or GpsPeticion()
    _validar_gps(gps)

    jornada = repo_jornadas.obtener_por_uuid(db, jornada_uuid)
    if jornada is None or jornada.usuario_id != actor.id:
        raise JornadaDesconocidaError(f"Jornada desconocida: {jornada_uuid}")

    tipo = db.get(TipoActividad, tipo_actividad_id)
    if tipo is None:
        raise TipoActividadDesconocidoError(f"Tipo de actividad desconocido: {tipo_actividad_id}")
    # `eca_id` (catálogo) o `eca_nombre` (escrita a mano) — lo segundo
    # existe porque muchos técnicos no tienen ninguna ECA para elegir en
    # su ámbito/asignación todavía (ver 0021).
    # Pedido explícito (2026-09-08): la ECA es obligatoria SIEMPRE, sin
    # importar `tipo.requiere_eca` — antes solo se exigía para los tipos
    # marcados así en el catálogo.
    eca_nombre = _normalizar_texto_libre(eca_nombre)
    if eca_id is None and not eca_nombre:
        raise EcaRequeridaError("El nombre de la ECA es obligatorio.")
    if num_participantes is not None and not tipo.permite_participantes:
        raise ParticipantesNoPermitidosError(
            f"El tipo de actividad «{tipo.nombre}» no admite número de participantes."
        )

    subtema_obj = None
    if subtema_id is not None:
        subtema_obj = db.get(Subtema, subtema_id)
        if subtema_obj is None or (tema_id is not None and subtema_obj.tema_id != tema_id):
            raise SubtemaIncoherenteError("El subtema no corresponde al tema indicado.")
        if tema_id is None:
            tema_id = subtema_obj.tema_id
    tema_obj = db.get(Tema, tema_id) if tema_id is not None else None
    sistema_obj = db.get(SistemaProductivo, sistema_productivo_id) if sistema_productivo_id is not None else None

    # Texto obligatorio cuando la opción elegida en el catálogo es "Otro"
    # (pedido explícito) — mismo criterio que `eca_nombre` arriba.
    tipo_actividad_otro_texto = _validar_y_normalizar_otro(
        tipo_actividad_otro_texto, es_otro=tipo.clave == _CLAVE_OTRO_TIPO_ACTIVIDAD, etiqueta="tipo de actividad"
    )
    tema_otro_texto = _validar_y_normalizar_otro(
        tema_otro_texto, es_otro=tema_obj is not None and tema_obj.clave == _CLAVE_OTRO, etiqueta="tema"
    )
    subtema_otro_texto = _validar_y_normalizar_otro(
        subtema_otro_texto, es_otro=subtema_obj is not None and subtema_obj.clave == _CLAVE_OTRO, etiqueta="subtema"
    )
    sistema_productivo_otro_texto = _validar_y_normalizar_otro(
        sistema_productivo_otro_texto,
        es_otro=sistema_obj is not None and sistema_obj.clave == _CLAVE_OTRO,
        etiqueta="sistema productivo",
    )

    # Red anti-duplicado (además de la idempotencia por `uuid` de arriba):
    # el doble-toque en la PWA generaba dos `uuid` distintos para la MISMA
    # actividad, así que la idempotencia por uuid no la atrapaba y quedaban
    # dos filas iguales. Si ya existe una actividad viva equivalente del
    # mismo técnico en una ventana corta, se devuelve esa en vez de crear
    # otra — el backend nunca vuelve a duplicar, venga de donde venga.
    equivalente = repo_actividades.buscar_equivalente_reciente(
        db,
        usuario_id=actor.id,
        jornada_id=jornada.id,
        tipo_actividad_id=tipo_actividad_id,
        descripcion=descripcion,
        fecha_hora=fecha_hora,
    )
    if equivalente is not None:
        return equivalente

    actividad = Actividad(
        uuid=uuid,
        usuario_id=actor.id,
        jornada_id=jornada.id,
        eca_id=eca_id,
        eca_nombre=eca_nombre,  # ya normalizado (mayúsculas, sin tildes) arriba
        modalidad_id=modalidad_id,
        tipo_actividad_id=tipo_actividad_id,
        tema_id=tema_id,
        subtema_id=subtema_id,
        sistema_productivo_id=sistema_productivo_id,
        tipo_actividad_otro_texto=tipo_actividad_otro_texto,
        tema_otro_texto=tema_otro_texto,
        subtema_otro_texto=subtema_otro_texto,
        sistema_productivo_otro_texto=sistema_productivo_otro_texto,
        descripcion=descripcion,
        resultado=resultado,
        fecha_hora=fecha_hora,
        latitud=gps.latitud,
        longitud=gps.longitud,
        precision_gps_m=gps.precision_gps_m,
        estado_gps=gps.estado_gps,
        num_participantes=num_participantes,
        requiere_seguimiento=requiere_seguimiento,
        fecha_proximo_seguimiento=fecha_proximo_seguimiento,
        creado_por=actor.id,
        actualizado_por=actor.id,
    )
    repo_actividades.crear(db, actividad)

    registrar_evento(
        db,
        accion="actividad.alta",
        modulo="actividades",
        actor_usuario_id=actor.id,
        entidad_tipo="actividad",
        entidad_id=actividad.id,
        entidad_uuid=actividad.uuid,
    )
    db.commit()
    db.refresh(actividad)
    return actividad


def listar_propias(
    db: Session,
    *,
    usuario_id: int,
    eca_id=None,
    tipo_actividad_id=None,
    tema_id=None,
    estado_gps=None,
    desde=None,
    hasta=None,
    page=1,
    page_size=50,
):
    return repo_actividades.listar(
        db,
        usuario_id=usuario_id,
        eca_id=eca_id,
        tipo_actividad_id=tipo_actividad_id,
        tema_id=tema_id,
        estado_gps=estado_gps,
        desde=desde,
        hasta=hasta,
        page=page,
        page_size=page_size,
    )


def listar_todas(
    db: Session,
    *,
    usuario_id=None,
    eca_id=None,
    municipio_id=None,
    tipo_actividad_id=None,
    tema_id=None,
    estado_gps=None,
    desde=None,
    hasta=None,
    page=1,
    page_size=50,
):
    return repo_actividades.listar(
        db,
        usuario_id=usuario_id,
        eca_id=eca_id,
        municipio_id=municipio_id,
        tipo_actividad_id=tipo_actividad_id,
        tema_id=tema_id,
        estado_gps=estado_gps,
        desde=desde,
        hasta=hasta,
        page=page,
        page_size=page_size,
    )


def eliminar(db: Session, *, uuid: uuid_lib.UUID, actor: Usuario) -> None:
    """Borrado lógico (admin, permiso `actividades.eliminar`) — nunca borra
    la fila física, mismo criterio que el resto del RBAC del proyecto
    (deactivar/marcar, nunca DELETE físico)."""
    actividad = repo_actividades.obtener_por_uuid(db, uuid)
    if actividad is None or actividad.eliminado_en is not None:
        raise ActividadNoEncontradaError(f"Actividad desconocida: {uuid}")

    repo_actividades.eliminar(db, actividad)

    registrar_evento(
        db,
        accion="actividad.eliminar",
        modulo="actividades",
        actor_usuario_id=actor.id,
        entidad_tipo="actividad",
        entidad_id=actividad.id,
        entidad_uuid=actividad.uuid,
    )
    db.commit()


def exportar_csv(
    db: Session,
    *,
    usuario_id=None,
    eca_id=None,
    municipio_id=None,
    tipo_actividad_id=None,
    tema_id=None,
    estado_gps=None,
    desde=None,
    hasta=None,
) -> list[Actividad]:
    return repo_actividades.listar_todas_sin_paginar(
        db,
        usuario_id=usuario_id,
        eca_id=eca_id,
        municipio_id=municipio_id,
        tipo_actividad_id=tipo_actividad_id,
        tema_id=tema_id,
        estado_gps=estado_gps,
        desde=desde,
        hasta=hasta,
    )
