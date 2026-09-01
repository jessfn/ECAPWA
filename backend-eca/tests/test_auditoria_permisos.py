"""Auditoría de permisos endpoint por endpoint — ECA-020.

Recorre las rutas registradas y falla si alguna que no está en la lista
blanca explícita de rutas públicas no exige autenticación
(`get_current_user`, directo o vía `require_permission`, que depende de
él). Es la "matriz permiso↔endpoint" del criterio de aceptación, hecha
ejecutable en vez de solo documentada: si mañana alguien agrega un router
sin `require_permission`, esta prueba lo atrapa.
"""
from __future__ import annotations

import pytest

RUTAS_PUBLICAS = {
    ("GET", "/health"),
    ("POST", "/auth/login"),
    ("POST", "/auth/refresh"),
    ("POST", "/solicitudes-acceso"),
    # `logout` revoca por posesión del `refresh_token` en el cuerpo — ese
    # token ES la credencial ahí, no hace falta además un `access_token`
    # vigente (deliberado: debe poder cerrar sesión aunque haya expirado).
    ("POST", "/auth/logout"),
}

# Comodín de 404 al final de main.py: nunca toca datos, solo responde el
# formato uniforme de error para rutas inexistentes.
_METODOS_COMODIN = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
RUTAS_PUBLICAS |= {(metodo, "/{camino_completo:path}") for metodo in _METODOS_COMODIN}


def _depende_de_autenticacion(dependant, get_current_user) -> bool:
    for dep in dependant.dependencies:
        if dep.call is get_current_user:
            return True
        if _depende_de_autenticacion(dep, get_current_user):
            return True
    return False


@pytest.fixture
def rutas_de_datos(env_valido: None):
    from app.api.deps import get_current_user
    from app.main import crear_app

    app = crear_app()
    rutas = []
    for ruta in app.routes:
        metodos = getattr(ruta, "methods", None)
        dependant = getattr(ruta, "dependant", None)
        if not metodos or dependant is None:
            continue
        for metodo in metodos:
            if metodo == "HEAD":
                continue
            rutas.append((metodo, ruta.path, dependant))
    return rutas, get_current_user


def test_toda_ruta_no_publica_exige_autenticacion(rutas_de_datos) -> None:
    rutas, get_current_user = rutas_de_datos
    sin_auth = [
        (metodo, path)
        for metodo, path, dependant in rutas
        if (metodo, path) not in RUTAS_PUBLICAS and not _depende_de_autenticacion(dependant, get_current_user)
    ]
    assert sin_auth == [], f"Rutas sin autenticación y fuera de la lista blanca: {sin_auth}"


def test_lista_blanca_no_tiene_rutas_inexistentes(rutas_de_datos) -> None:
    rutas, _get_current_user = rutas_de_datos
    existentes = {(metodo, path) for metodo, path, _ in rutas}
    huerfanas = RUTAS_PUBLICAS - existentes
    assert huerfanas == set(), f"Rutas en la lista blanca que ya no existen: {huerfanas}"
