"""Pruebas del scaffold — ECA-001.

Verifican los criterios de aceptación del ticket ECA-001:

1. el paquete ``app`` es importable;
2. la estructura de carpetas esperada existe (con su ``__init__.py``);
3. ningún módulo del backend ECA (``app/``) importa código del sistema legado
   Sembrando Vida (``backend/``, ``pwasuper/``, ``admin-pwa/``).
"""
from __future__ import annotations

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[1]

PAQUETES_ESPERADOS = [
    "app",
    "app/core",
    "app/models",
    "app/schemas",
    "app/repositories",
    "app/services",
    "app/api",
    "app/api/routers",
]

# Tokens de módulos del sistema legado que NO deben aparecer en líneas `import`.
_LEGADO = re.compile(
    r"(^|[\s.(])(backend|pwasuper|admin_pwa|sembrandodatos|sembrando_vida)([\s.)]|$)",
    re.IGNORECASE,
)


def test_paquete_app_importable() -> None:
    import app

    assert app.__version__ == "0.0.1"


def test_estructura_de_carpetas() -> None:
    faltantes = [p for p in PAQUETES_ESPERADOS if not (RAIZ / p).is_dir()]
    assert not faltantes, f"Faltan carpetas del scaffold: {faltantes}"

    sin_init = [
        p for p in PAQUETES_ESPERADOS if not (RAIZ / p / "__init__.py").is_file()
    ]
    assert not sin_init, f"Faltan __init__.py en: {sin_init}"

    assert (RAIZ / "alembic").is_dir()
    assert (RAIZ / "tests").is_dir()


def test_app_no_importa_sembrando_vida() -> None:
    ofensores: list[str] = []
    for py in (RAIZ / "app").rglob("*.py"):
        for n, linea in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            s = linea.strip()
            if not (s.startswith("import ") or s.startswith("from ")):
                continue
            if _LEGADO.search(s):
                ofensores.append(f"{py.relative_to(RAIZ)}:{n}: {s}")
    assert not ofensores, "Imports del legado Sembrando Vida:\n" + "\n".join(ofensores)
