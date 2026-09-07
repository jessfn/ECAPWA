"""Notificaciones en tiempo real de cambios de permisos — ECA-021.

Pedido explícito: si un admin le quita/agrega acceso a alguien, ese
alguien debe dejar de ver la vista de inmediato, sin recargar el
navegador. Con `--workers 4` (ver `apieca.service`) un WebSocket abierto
en el worker A no se entera de nada que pase en el worker B con solo
memoria de proceso — por eso el aviso entre workers viaja por Postgres
(`LISTEN`/`NOTIFY`, transaccional: nunca se dispara si el `COMMIT` que lo
originó se revierte), no por una lista en memoria compartida entre ellos.

Cada worker mantiene:
  - Un diccionario `usuario_id -> {WebSocket}` con SUS propias conexiones.
  - Una tarea de fondo que hace `LISTEN permisos_cambiados` con su propia
    conexión async de psycopg y, por cada aviso, revisa si tiene alguna
    conexión abierta de ese `usuario_id` y le manda un mensaje.

El mensaje nunca lleva los permisos nuevos (evitaría duplicar la lógica
de resolución de permisos aquí) — solo avisa "algo cambió"; el cliente
responde pidiendo `GET /auth/me` de nuevo, la misma fuente de verdad que
ya usa en el login.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging

import psycopg
from fastapi import WebSocket
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.settings import get_settings

logger = logging.getLogger("app.ws_permisos")

CANAL_PERMISOS = "permisos_cambiados"


class GestorConexionesPermisos:
    def __init__(self) -> None:
        self._conexiones: dict[int, set[WebSocket]] = {}

    def conectar(self, usuario_id: int, socket: WebSocket) -> None:
        self._conexiones.setdefault(usuario_id, set()).add(socket)

    def desconectar(self, usuario_id: int, socket: WebSocket) -> None:
        conexiones = self._conexiones.get(usuario_id)
        if not conexiones:
            return
        conexiones.discard(socket)
        if not conexiones:
            self._conexiones.pop(usuario_id, None)

    async def avisar(self, usuario_id: int) -> None:
        for socket in list(self._conexiones.get(usuario_id, ())):
            try:
                await socket.send_json({"tipo": "permisos_cambiados"})
            except Exception:
                # Conexión muerta que el propio WebSocketDisconnect todavía
                # no limpió — mejor esfuerzo, se autolimpia en su momento.
                pass


gestor = GestorConexionesPermisos()


def notificar_cambio_permisos(db: Session, usuario_id: int) -> None:
    """Se llama DENTRO de la misma transacción, antes del `commit()` — un
    `NOTIFY`/`pg_notify()` de Postgres es transaccional: si el `COMMIT` que
    lo originó se revierte, el aviso nunca sale. `pg_notify()` (función) en
    vez de `NOTIFY canal, 'texto'` (sentencia) porque esta última no acepta
    parámetros ligados, solo literales — y el payload es dinámico."""
    db.execute(text("SELECT pg_notify(:canal, :payload)"), {"canal": CANAL_PERMISOS, "payload": str(usuario_id)})


def _dsn_para_listen() -> str:
    # `DATABASE_URL` viene como `postgresql+psycopg://...` (formato que
    # SQLAlchemy necesita para elegir el driver) — psycopg.connect() por sí
    # solo espera el esquema plano `postgresql://`.
    return get_settings().DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)


async def escuchar_notificaciones() -> None:
    """Tarea de fondo (una por worker, arrancada en el lifespan de la app):
    mantiene una conexión async dedicada SOLO a este LISTEN — nunca
    comparte conexión con el pool de negocio de SQLAlchemy — y reintenta
    con backoff si Postgres se reinicia o hay un corte de red breve."""
    dsn = _dsn_para_listen()
    espera = 1
    while True:
        try:
            async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conexion:
                await conexion.execute(f"LISTEN {CANAL_PERMISOS}")
                logger.info("escuchando notificaciones de permisos (%s)", CANAL_PERMISOS)
                espera = 1
                async for aviso in conexion.notifies():
                    try:
                        usuario_id = int(aviso.payload)
                    except (TypeError, ValueError):
                        continue
                    await gestor.avisar(usuario_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("se perdió la escucha de permisos, reintentando en %ss", espera, exc_info=True)
            await asyncio.sleep(espera)
            espera = min(espera * 2, 30)


def arrancar_tarea_escucha() -> asyncio.Task:
    return asyncio.create_task(escuchar_notificaciones())


async def detener_tarea_escucha(tarea: asyncio.Task) -> None:
    tarea.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await tarea
