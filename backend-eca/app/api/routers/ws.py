"""WebSocket de avisos de permisos — ECA-021.

No hay forma de mandar la cabecera `Authorization` en el `WebSocket` nativo
del navegador, así que el token viaja como query param (`?token=...`) —
mismo access token de siempre, mismo `decodificar_access_token`. Nunca se
resuelve autorización aquí más allá de "¿quién eres?": el mensaje que se
manda no lleva ningún dato, solo avisa "pide tu perfil de nuevo".
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import TokenInvalidoError, decodificar_access_token
from app.core.ws_permisos import gestor
from app.repositories import usuarios as repo_usuarios

router = APIRouter(tags=["ws"])


@router.websocket("/ws/permisos")
async def ws_permisos(socket: WebSocket, token: str = "", db: Session = Depends(get_db)) -> None:
    try:
        usuario_id = decodificar_access_token(token)
    except TokenInvalidoError:
        await socket.close(code=4401)
        return

    usuario = repo_usuarios.obtener_por_id(db, usuario_id)
    if usuario is None or not usuario.esta_activo:
        await socket.close(code=4403)
        return

    await socket.accept()
    gestor.conectar(usuario_id, socket)
    try:
        while True:
            # No se espera nada del cliente — este `receive` solo existe
            # para que la corrutina se quede viva y detecte la desconexión
            # (cierre de pestaña, pérdida de red, etc.) vía la excepción.
            await socket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        gestor.desconectar(usuario_id, socket)
