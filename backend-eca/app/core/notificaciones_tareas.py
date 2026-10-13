"""Publicador de notificaciones programadas: cada 20 s cada worker revisa las
PROGRAMADAS cuya hora ya llegó. `SKIP LOCKED` en el servicio garantiza que solo
un worker publique cada una (el `NOTIFY` sale dentro de la misma transacción)."""
from __future__ import annotations

import asyncio
import logging

from app.core.db import SessionLocal
from app.services import notificaciones_service, push_service

logger = logging.getLogger("app.notificaciones_tareas")

INTERVALO_S = 20


def _publicar_pendientes() -> int:
    with SessionLocal() as db:
        ids = [n.id for n in notificaciones_service.publicar_programadas(db)]
    # Solo el worker que publicó (SKIP LOCKED) envía el push: una sola vez.
    for notif_id in ids:
        push_service.enviar_en_segundo_plano(notif_id)
    return len(ids)


async def publicar_programadas_en_bucle() -> None:
    while True:
        try:
            publicadas = await asyncio.to_thread(_publicar_pendientes)
            if publicadas:
                logger.info("notificaciones programadas publicadas: %s", publicadas)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("falló la publicación de notificaciones programadas", exc_info=True)
        await asyncio.sleep(INTERVALO_S)


def arrancar_tarea_programadas() -> asyncio.Task:
    return asyncio.create_task(publicar_programadas_en_bucle())
