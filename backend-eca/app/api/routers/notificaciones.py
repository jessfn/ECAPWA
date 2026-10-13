"""Router de notificaciones (admin -> técnicos de la PWA).

Admin (permisos `vista.notificaciones` / `notificaciones.enviar` /
`notificaciones.retirar`): crear/programar, historial, retirar, buscar
destinatarios y subir medios (por partes: Cloudflare corta cada petición a
100 MB y el video llega a 200 MB).
Técnico (sesión normal): bandeja, contador, marcar leída.
Los medios se sirven con URL firmada de vida larga (un <img>/<video> no manda
`Authorization`) y soportan Range (FileResponse) para reproducir video.
"""
from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.permissions import require_permission
from app.core.storage import get_storage
from app.models.notificacion import Notificacion
from app.models.usuario import Usuario
from app.schemas.notificacion import (
    PushClave,
    PushDesuscribir,
    PushSuscripcion,
    AdjuntoPublico,
    BandejaRespuesta,
    DestinatarioBasico,
    NotificacionAdmin,
    NotificacionCrear,
    NotificacionUsuario,
    SubidaIniciada,
    SubidaIniciar,
)
from app.services import notificaciones_service as svc
from app.services import push_service

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


def _http(error: svc.NotificacionError) -> HTTPException:
    codigo = status.HTTP_404_NOT_FOUND if isinstance(error, svc.NoEncontradaError) else status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(codigo, str(error))


def _adjuntos(n: Notificacion) -> list[AdjuntoPublico]:
    return [
        AdjuntoPublico(
            uuid=a.uuid, tipo=a.tipo, mime=a.mime, nombre_original=a.nombre_original,
            tamano_bytes=a.tamano_bytes, url=svc.url_medio(a.uuid),
        )
        for a in n.adjuntos
    ]


def _a_admin(db: Session, n: Notificacion, leidas: int) -> NotificacionAdmin:
    destinatario = None
    if n.destino == "USUARIO" and n.usuario_destino_id:
        destinatario = svc.nombre_completo(db.get(Usuario, n.usuario_destino_id))
    return NotificacionAdmin(
        uuid=n.uuid, titulo=n.titulo, subtitulo=n.subtitulo, descripcion=n.descripcion, url=n.url,
        url_texto=n.url_texto, tipo=n.tipo, destino=n.destino, destinatario=destinatario, estado=n.estado,
        programada_para=n.programada_para, publicada_en=n.publicada_en, expira_en=n.expira_en,
        vigente=svc.esta_vigente(n), destinatarios_total=n.destinatarios_total, leidas=leidas,
        push_enviados=n.push_enviados, creado_por=svc.nombre_completo(db.get(Usuario, n.creado_por)),
        creado_en=n.creado_en, adjuntos=_adjuntos(n),
    )


# ------------------------------------------------------------------- admin
@router.post("", response_model=NotificacionAdmin, status_code=status.HTTP_201_CREATED)
def crear_notificacion(
    peticion: NotificacionCrear,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("notificaciones.enviar")),
) -> NotificacionAdmin:
    try:
        notif = svc.crear(db, actor=actor, datos=peticion)
    except svc.NotificacionError as e:
        db.rollback()
        raise _http(e)
    if notif.estado == "PUBLICADA":
        push_service.enviar_en_segundo_plano(notif.id)
    return _a_admin(db, notif, 0)


@router.get("", response_model=list[NotificacionAdmin])
def historial(
    estado: str | None = None,
    texto: str | None = None,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("vista.notificaciones")),
) -> list[NotificacionAdmin]:
    # Antes de consultar, publica las que ya cumplieron su hora (red de
    # seguridad por si el proceso de fondo aún no pasó).
    svc.publicar_programadas(db)
    notifs = svc.listar_admin(db, estado=estado, texto=texto)
    lecturas = svc.lecturas_por_notificacion(db, [n.id for n in notifs])
    return [_a_admin(db, n, lecturas.get(n.id, 0)) for n in notifs]


@router.get("/destinatarios", response_model=list[DestinatarioBasico])
def buscar_destinatarios(
    texto: str | None = None,
    db: Session = Depends(get_db),
    _actor: Usuario = Depends(require_permission("notificaciones.enviar")),
) -> list[DestinatarioBasico]:
    return [
        DestinatarioBasico(id=u.id, nombre=svc.nombre_completo(u) or "", correo=str(u.correo))
        for u in svc.buscar_destinatarios(db, texto)
    ]


@router.post("/{notif_uuid}/retirar", response_model=NotificacionAdmin)
def retirar_notificacion(
    notif_uuid: uuid_lib.UUID,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("notificaciones.retirar")),
) -> NotificacionAdmin:
    try:
        notif = svc.retirar(db, actor=actor, notif_uuid=notif_uuid)
    except svc.NotificacionError as e:
        raise _http(e)
    return _a_admin(db, notif, svc.lecturas_por_notificacion(db, [notif.id]).get(notif.id, 0))


@router.post("/{notif_uuid}/eliminar", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def eliminar_notificacion(
    notif_uuid: uuid_lib.UUID,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("notificaciones.retirar")),
) -> Response:
    try:
        svc.eliminar(db, actor=actor, notif_uuid=notif_uuid)
    except svc.NotificacionError as e:
        raise _http(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- subida de medios por partes
@router.post("/subidas", response_model=SubidaIniciada, status_code=status.HTTP_201_CREATED)
def iniciar_subida(
    peticion: SubidaIniciar,
    actor: Usuario = Depends(require_permission("notificaciones.enviar")),
) -> SubidaIniciada:
    try:
        sid = svc.iniciar_subida(
            actor=actor, nombre=peticion.nombre, tamano=peticion.tamano, total_partes=peticion.total_partes
        )
    except svc.NotificacionError as e:
        raise _http(e)
    return SubidaIniciada(subida_id=sid, tamano_parte_max=svc.TAMANO_PARTE_MAX)


@router.put("/subidas/{subida_id}/partes/{numero}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def subir_parte(
    subida_id: uuid_lib.UUID,
    numero: int,
    request: Request,
    actor: Usuario = Depends(require_permission("notificaciones.enviar")),
) -> Response:
    try:
        ruta = svc.ruta_parte(actor, subida_id, numero)
    except svc.NotificacionError as e:
        raise _http(e)
    tamano = 0
    with ruta.open("wb") as f:
        async for trozo in request.stream():
            tamano += len(trozo)
            if tamano > svc.TAMANO_PARTE_MAX + 1024:
                f.close()
                ruta.unlink(missing_ok=True)
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "La parte es demasiado grande.")
            f.write(trozo)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/subidas/{subida_id}/finalizar", response_model=AdjuntoPublico)
def finalizar_subida(
    subida_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("notificaciones.enviar")),
) -> AdjuntoPublico:
    try:
        adj = svc.finalizar_subida(db, actor=actor, subida_id=subida_id)
    except svc.NotificacionError as e:
        raise _http(e)
    return AdjuntoPublico(
        uuid=adj.uuid, tipo=adj.tipo, mime=adj.mime, nombre_original=adj.nombre_original,
        tamano_bytes=adj.tamano_bytes, url=svc.url_medio(adj.uuid),
    )


@router.get("/medios/{adjunto_uuid}")
def descargar_medio(adjunto_uuid: uuid_lib.UUID, exp: int, sig: str, db: Session = Depends(get_db)) -> FileResponse:
    """Sin `Authorization` a propósito: la URL va firmada (HMAC + vencimiento)."""
    if not svc.firma_valida(str(adjunto_uuid), exp, sig):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Enlace inválido o vencido.")
    try:
        adj = svc.adjunto_por_uuid(db, adjunto_uuid)
    except svc.NotificacionError as e:
        raise _http(e)
    ruta = get_storage().ruta(adj.storage_clave)
    if not ruta.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no encontrado.")
    return FileResponse(ruta, media_type=adj.mime, headers={"Cache-Control": "private, max-age=86400"})


# ----------------------------------------------------------------- técnico
@router.get("/mias", response_model=BandejaRespuesta)
def mis_notificaciones(
    limite: int = 50,
    desde: datetime | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> BandejaRespuesta:
    svc.publicar_programadas(db)
    filas, no_leidas = svc.bandeja(db, usuario=usuario, limite=max(1, min(limite, 200)), desde=desde)
    return BandejaRespuesta(
        notificaciones=[
            NotificacionUsuario(
                uuid=n.uuid, titulo=n.titulo, subtitulo=n.subtitulo, descripcion=n.descripcion, url=n.url,
                url_texto=n.url_texto, tipo=n.tipo, publicada_en=n.publicada_en, expira_en=n.expira_en,
                leida=leida, adjuntos=_adjuntos(n),
            )
            for n, leida in filas
        ],
        no_leidas=no_leidas,
        ahora=svc.ahora_utc(),
    )


@router.post("/leer-todas")
def leer_todas(db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)) -> dict:
    return {"marcadas": svc.marcar_todas_leidas(db, usuario=usuario)}


@router.post("/{notif_uuid}/leida", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def marcar_leida(
    notif_uuid: uuid_lib.UUID, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)
) -> Response:
    try:
        svc.marcar_leida(db, usuario=usuario, notif_uuid=notif_uuid)
    except svc.NotificacionError as e:
        raise _http(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------- Web Push
@router.get("/push/clave", response_model=PushClave)
def clave_push(_usuario: Usuario = Depends(get_current_user)) -> PushClave:
    return PushClave(clave=push_service.clave_publica())


@router.post("/push/suscribir", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def suscribir_push(
    peticion: PushSuscripcion,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Response:
    try:
        push_service.suscribir(
            db, usuario=usuario, endpoint=peticion.endpoint, p256dh=peticion.keys.p256dh,
            auth=peticion.keys.auth, user_agent=request.headers.get("user-agent"),
        )
    except svc.NotificacionError as e:
        raise _http(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/push/desuscribir", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def desuscribir_push(
    peticion: PushDesuscribir, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)
) -> Response:
    push_service.desuscribir(db, usuario=usuario, endpoint=peticion.endpoint)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
