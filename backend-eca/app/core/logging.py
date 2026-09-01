"""Logging estructurado (JSON) — ECA-002.

Nunca loguea datos sensibles: contraseñas, tokens, CURP completo. Corrige
`docs-eca/02_INVENTARIO_TECNICO.md` §21 (prints sin estructura, sin control
sobre qué se filtra al log).
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

_CAMPOS_SENSIBLES = frozenset(
    {"contrasena", "password", "secret_key", "token", "access_token", "refresh_token", "authorization"}
)


def sanear(valor: object) -> object:
    if isinstance(valor, dict):
        return {
            k: ("***" if k.lower() in _CAMPOS_SENSIBLES else sanear(v)) for k, v in valor.items()
        }
    if isinstance(valor, list):
        return [sanear(v) for v in valor]
    return valor


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        cuerpo: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # `extra={...}` pasado por el llamador queda como atributos sueltos
        # del record; los recogemos filtrando los propios de LogRecord.
        estandar = logging.LogRecord(
            "", 0, "", 0, "", (), None
        ).__dict__.keys()
        for clave, valor in record.__dict__.items():
            if clave not in estandar and clave not in cuerpo:
                cuerpo[clave] = sanear(valor)

        if record.exc_info:
            cuerpo["exception"] = self.formatException(record.exc_info)

        return json.dumps(sanear(cuerpo), ensure_ascii=False)


def configurar_logging(nivel: str = "INFO") -> None:
    raiz = logging.getLogger()
    raiz.setLevel(nivel)
    raiz.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())
    raiz.addHandler(handler)
