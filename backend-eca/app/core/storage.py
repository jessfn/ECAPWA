"""Capa de almacenamiento de archivos — ECA-015.

`Storage` es la interfaz mínima que `evidencias_service` necesita;
`LocalStorage` es la única implementación del MVP (disco local, fuera del
webroot — nginx nunca debe servirlo como estático, ver criterio de
aceptación del ticket). Separarla como interfaz deja la puerta abierta a
un `S3Storage` futuro (el propio ticket lo anota como "siguiente paso si
el piloto lo confirma") sin tocar el resto del código.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.settings import get_settings


class Storage(Protocol):
    def guardar(self, clave: str, contenido: bytes) -> None: ...
    def leer(self, clave: str) -> bytes: ...
    def eliminar(self, clave: str) -> None: ...


class LocalStorage:
    def __init__(self, directorio_base: str) -> None:
        self._base = Path(directorio_base)
        self._base.mkdir(parents=True, exist_ok=True)

    def _ruta(self, clave: str) -> Path:
        # `clave` la genera siempre el servicio (nunca el cliente
        # directamente) con un patrón fijo — ver
        # `evidencias_service._clave_de`. Aun así, se resuelve y se verifica
        # que no escape del directorio base como defensa en profundidad.
        ruta = (self._base / clave).resolve()
        if self._base.resolve() not in ruta.parents and ruta != self._base.resolve():
            raise ValueError(f"Clave de almacenamiento inválida: {clave}")
        return ruta

    def guardar(self, clave: str, contenido: bytes) -> None:
        ruta = self._ruta(clave)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(contenido)

    def leer(self, clave: str) -> bytes:
        return self._ruta(clave).read_bytes()

    def eliminar(self, clave: str) -> None:
        ruta = self._ruta(clave)
        ruta.unlink(missing_ok=True)


@lru_cache
def get_storage() -> Storage:
    return LocalStorage(get_settings().STORAGE_DIR)
