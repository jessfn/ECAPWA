"""Pruebas de las reglas puras de notificaciones (sin base de datos)."""
from __future__ import annotations

import time
import uuid as uuid_lib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.services import notificaciones_service as svc


def test_fecha_sin_zona_se_interpreta_como_cdmx(env_valido) -> None:
    # 10:00 en CDMX (UTC-6, sin horario de verano desde 2022) = 16:00 UTC
    utc = svc.normalizar_fecha(datetime(2026, 1, 15, 10, 0))
    assert utc == datetime(2026, 1, 15, 16, 0, tzinfo=timezone.utc)


def test_fecha_con_zona_se_respeta(env_valido) -> None:
    con_zona = datetime(2026, 1, 15, 10, 0, tzinfo=ZoneInfo("America/Mexico_City"))
    assert svc.normalizar_fecha(con_zona) == datetime(2026, 1, 15, 16, 0, tzinfo=timezone.utc)
    assert svc.normalizar_fecha(None) is None


@pytest.mark.parametrize("url", ["https://ejemplo.com/a?b=1", "/historial", None, "  ", ""])
def test_urls_permitidas(url) -> None:
    resultado = svc._url_valida(url)
    assert resultado is None or resultado.startswith(("https://", "/"))


@pytest.mark.parametrize("url", ["javascript:alert(1)", "http://inseguro.com", "//evil.com", "data:text/html,x"])
def test_urls_peligrosas_se_rechazan(url) -> None:
    with pytest.raises(svc.NotificacionError):
        svc._url_valida(url)


def test_firma_de_medios(env_valido) -> None:
    u = str(uuid_lib.uuid4())
    exp = int(time.time()) + 60
    sig = svc._firmar(u, exp)
    assert svc.firma_valida(u, exp, sig)
    assert not svc.firma_valida(u, exp, "x" * 40)
    assert not svc.firma_valida(str(uuid_lib.uuid4()), exp, sig)
    assert not svc.firma_valida(u, int(time.time()) - 1, svc._firmar(u, int(time.time()) - 1))


def test_tipo_por_firma_del_archivo() -> None:
    assert svc._tipo_por_bytes(b"\xff\xd8\xff\xe0" + b"0" * 28) == ("IMAGEN", "image/jpeg")
    assert svc._tipo_por_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 24) == ("IMAGEN", "image/png")
    assert svc._tipo_por_bytes(b"\x00\x00\x00\x18ftypmp42" + b"0" * 20) == ("VIDEO", "video/mp4")
    assert svc._tipo_por_bytes(b"\x00\x00\x00\x14ftypqt  " + b"0" * 20) == ("VIDEO", "video/quicktime")
    assert svc._tipo_por_bytes(b"\x1a\x45\xdf\xa3" + b"0" * 28) == ("VIDEO", "video/webm")
    assert svc._tipo_por_bytes(b"MZ\x90\x00" + b"0" * 28) is None  # ejecutable: no permitido
