"""Web Push: suscripciones de dispositivos y envío de notificaciones.

El envío se dispara UNA sola vez por notificación, desde el flujo que la
publica (la petición del admin o el publicador de programadas, que ya está
protegido con SKIP LOCKED) — nunca desde el listener de LISTEN/NOTIFY, que
corre en los 4 workers y duplicaría el aviso x4.
`pywebpush` es síncrono, así que se corre en un hilo con su propia sesión.
"""
from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from pywebpush import WebPushException, webpush
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.settings import get_settings
from app.models.notificacion import Notificacion, SuscripcionPush
from app.models.rbac import Rol, UsuarioRol
from app.models.usuario import Usuario
from app.services import notificaciones_service as notif_svc

logger = logging.getLogger("app.push")


def push_habilitado() -> bool:
    s = get_settings()
    return bool(s.VAPID_PUBLIC_KEY and s.VAPID_PRIVATE_KEY)


def clave_publica() -> str | None:
    return get_settings().VAPID_PUBLIC_KEY or None


# ------------------------------------------------------------ suscripciones
def suscribir(db: Session, *, usuario: Usuario, endpoint: str, p256dh: str, auth: str, user_agent: str | None) -> None:
    """Alta/actualización idempotente por `endpoint`. Si el dispositivo ya
    estaba ligado a otra cuenta (se compartió el celular), pasa a esta."""
    if not endpoint.startswith("https://"):
        raise notif_svc.NotificacionError("Endpoint de suscripción inválido.")
    sus = db.execute(select(SuscripcionPush).where(SuscripcionPush.endpoint == endpoint)).scalar_one_or_none()
    if sus is None:
        sus = SuscripcionPush(endpoint=endpoint, usuario_id=usuario.id, p256dh=p256dh, auth=auth)
        db.add(sus)
    sus.usuario_id = usuario.id
    sus.p256dh = p256dh
    sus.auth = auth
    sus.user_agent = (user_agent or "")[:300] or None
    sus.activo = True
    db.commit()


def desuscribir(db: Session, *, usuario: Usuario, endpoint: str) -> None:
    db.execute(
        update(SuscripcionPush)
        .where(SuscripcionPush.endpoint == endpoint, SuscripcionPush.usuario_id == usuario.id)
        .values(activo=False)
    )
    db.commit()


# ------------------------------------------------------------------- envío
def armar_payload(n: Notificacion) -> str:
    partes = [p for p in (n.subtitulo, n.descripcion) if p]
    cuerpo = " · ".join(partes)[:180] if partes else ""
    imagen = next((a for a in n.adjuntos if a.tipo == "IMAGEN"), None)
    return json.dumps(
        {
            "uuid": str(n.uuid),
            "titulo": n.titulo,
            "cuerpo": cuerpo,
            "tipo": n.tipo,
            "url": n.url,
            "imagen": (get_settings().API_PUBLIC_URL.rstrip("/") + notif_svc.url_medio(imagen.uuid)) if imagen else None,
        },
        ensure_ascii=False,
    )


def _suscripciones_destino(db: Session, n: Notificacion) -> list[SuscripcionPush]:
    consulta = (
        select(SuscripcionPush)
        .join(Usuario, Usuario.id == SuscripcionPush.usuario_id)
        .where(SuscripcionPush.activo.is_(True), Usuario.estado == "ACTIVO")
    )
    if n.destino == "USUARIO":
        consulta = consulta.where(SuscripcionPush.usuario_id == n.usuario_destino_id)
    else:
        consulta = consulta.where(
            SuscripcionPush.usuario_id.in_(
                select(UsuarioRol.usuario_id)
                .join(Rol, Rol.id == UsuarioRol.rol_id)
                .where(UsuarioRol.activo.is_(True), Rol.clave == "TECNICO")
            )
        )
    return list(db.execute(consulta).scalars())


def _enviar_una(sus: tuple[int, str, str, str], payload: str) -> tuple[int, str]:
    """(id, resultado): 'ok' | 'expirada' | 'error'."""
    s = get_settings()
    sid, endpoint, p256dh, auth = sus
    try:
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=payload,
            vapid_private_key=s.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": s.VAPID_SUBJECT},
            ttl=24 * 3600,
            timeout=10,
        )
        return sid, "ok"
    except WebPushException as e:
        codigo = getattr(e.response, "status_code", None)
        if codigo in (404, 410):
            return sid, "expirada"
        logger.warning("push falló (%s) para suscripción %s", codigo, sid)
        return sid, "error"
    except Exception:
        logger.warning("push falló para suscripción %s", sid, exc_info=True)
        return sid, "error"


def enviar_notificacion(notif_id: int) -> dict:
    if not push_habilitado():
        return {"enviados": 0, "motivo": "push deshabilitado"}
    with SessionLocal() as db:
        n = notif_svc.obtener_por_id(db, notif_id)
        if n is None or not notif_svc.esta_vigente(n):
            return {"enviados": 0}
        payload = armar_payload(n)
        subs = [(s.id, s.endpoint, s.p256dh, s.auth) for s in _suscripciones_destino(db, n)]
        if not subs:
            return {"enviados": 0}
        with ThreadPoolExecutor(max_workers=10) as pool:
            resultados = list(pool.map(lambda x: _enviar_una(x, payload), subs))
        ok = [i for i, r in resultados if r == "ok"]
        expiradas = [i for i, r in resultados if r == "expirada"]
        ahora = datetime.now(timezone.utc)
        if ok:
            db.execute(update(SuscripcionPush).where(SuscripcionPush.id.in_(ok)).values(ultimo_exito_en=ahora))
        if expiradas:
            db.execute(update(SuscripcionPush).where(SuscripcionPush.id.in_(expiradas)).values(activo=False))
        db.execute(update(Notificacion).where(Notificacion.id == notif_id).values(push_enviados=len(ok)))
        db.commit()
        return {"enviados": len(ok), "expiradas": len(expiradas), "total": len(subs)}


def enviar_en_segundo_plano(notif_id: int) -> None:
    """Dispara el envío en un hilo (la petición del admin no espera a los
    servicios push de Google/Apple/Mozilla)."""
    if not push_habilitado():
        return

    def _trabajo() -> None:
        try:
            enviar_notificacion(notif_id)
        except Exception:
            logger.warning("falló el envío de push de la notificación %s", notif_id, exc_info=True)

    threading.Thread(target=_trabajo, name=f"push-{notif_id}", daemon=True).start()
