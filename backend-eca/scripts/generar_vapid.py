"""Genera un par de claves VAPID para Web Push.

Uso (en el servidor):  .venv/bin/python scripts/generar_vapid.py
Copia las 2 líneas impresas al `.env` y reinicia el servicio. Genera el par UNA
sola vez: cambiarlo invalida todas las suscripciones push existentes.
"""
import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


vapid = Vapid()
vapid.generate_keys()
privada = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
publica = vapid.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
print(f"VAPID_PRIVATE_KEY={_b64(privada)}")
print(f"VAPID_PUBLIC_KEY={_b64(publica)}")
