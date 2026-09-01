"""Rate limiting mínimo — ECA-020.

Ventana deslizante en memoria del proceso, sin dependencias externas
(Redis, etc.) — proporcional al tamaño del piloto. Se aplica solo a los
endpoints sensibles a fuerza bruta/abuso: login, refresh, sync. **No** es
un rate limiter global de la API.

Limitación conocida y aceptada para el MVP: al correr con varios workers
(`apieca.service` usa 4), cada proceso lleva su propio contador — el límite
efectivo es `limite × workers`, no uno global compartido. Suficiente para
frenar fuerza bruta básica en el piloto; si hace falta un límite exacto
compartido, el siguiente paso natural es Redis (fuera de alcance aquí).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

_intentos: dict[str, deque[float]] = defaultdict(deque)


def _limpiar_y_contar(clave: str, ventana_seg: int) -> int:
    ahora = time.monotonic()
    cola = _intentos[clave]
    while cola and ahora - cola[0] > ventana_seg:
        cola.popleft()
    return len(cola)


def limitar(*, nombre: str, limite: int, ventana_seg: int):
    """Fábrica de dependencia FastAPI: 429 si `nombre`+IP supera `limite`
    peticiones en `ventana_seg` segundos."""

    def _dependencia(request: Request) -> None:
        ip = request.client.host if request.client else "desconocido"
        clave = f"{nombre}:{ip}"
        if _limpiar_y_contar(clave, ventana_seg) >= limite:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Demasiados intentos. Espera un momento antes de volver a intentarlo.",
            )
        _intentos[clave].append(time.monotonic())

    return _dependencia


def _reiniciar_para_pruebas() -> None:
    _intentos.clear()
