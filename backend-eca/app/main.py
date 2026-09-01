"""Punto de entrada de la aplicación FastAPI — ECA-002.

Deliberadamente delgado: crea la app, aplica middlewares, registra
manejadores de error y monta routers. La lógica de negocio vive en
``services``/``repositories``; los routers de dominio (auth, usuarios, ecas,
...) se añaden a partir de ECA-003 en adelante.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routers import (
    actividades,
    ambitos,
    asignaciones,
    auth,
    catalogos,
    ecas,
    evidencias,
    geo,
    health,
    jornadas,
    parametros_config,
    permisos,
    solicitudes_acceso,
    sync,
    usuarios,
)
from app.core.errors import ManejadorExcepcionesNoControladasMiddleware, registrar_manejadores_error
from app.core.logging import configurar_logging
from app.core.security_headers import CabecerasSeguridadMiddleware
from app.core.settings import get_settings

settings = get_settings()

configurar_logging(nivel="DEBUG" if settings.APP_ENV == "development" else "INFO")
logger = logging.getLogger("app.main")


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "backend-eca arrancó",
        extra={"app_env": settings.APP_ENV, "version": __version__},
    )
    yield


def crear_app() -> FastAPI:
    app = FastAPI(
        title="backend-eca",
        description="API del sistema ECA (Escuelas de Campo). Independiente de Sembrando Vida.",
        version=__version__,
        # En producción no exponemos la documentación interactiva por
        # defecto; se puede reactivar vía configuración cuando haga falta
        # sin volver a tocar código.
        docs_url="/docs" if not settings.es_produccion else None,
        redoc_url="/redoc" if not settings.es_produccion else None,
        lifespan=_ciclo_de_vida,
    )

    # Debe agregarse ANTES que CORSMiddleware: con `add_middleware`, el
    # primero agregado queda más adentro en la pila, así una respuesta de
    # error también pasa por CORS de regreso al cliente (ver docstring en
    # app/core/errors.py).
    app.add_middleware(ManejadorExcepcionesNoControladasMiddleware)
    app.add_middleware(CabecerasSeguridadMiddleware)

    # CORS: lista blanca explícita desde configuración. Nunca "*" con
    # allow_credentials=True (corrige `02_INVENTARIO_TECNICO.md` §3.1/§20).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    registrar_manejadores_error(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(usuarios.router)
    app.include_router(permisos.router)
    app.include_router(geo.router)
    app.include_router(ecas.router)
    app.include_router(ambitos.router)
    app.include_router(asignaciones.router)
    app.include_router(catalogos.router)
    app.include_router(jornadas.router)
    app.include_router(actividades.router)
    app.include_router(parametros_config.router)
    app.include_router(evidencias.router)
    app.include_router(sync.router)
    app.include_router(solicitudes_acceso.router)
    # Los routers del HITO C (PWA técnico) siguen aquí, SIEMPRE antes de la
    # ruta comodín de abajo.

    # Starlette no enruta un 404 "ninguna ruta coincide" a través de los
    # manejadores de excepción registrados (los intercepta antes, con un
    # `PlainTextResponse` propio) — solo lo hace cuando el endpoint levanta
    # `HTTPException` explícitamente. Sin este comodín, una ruta inexistente
    # respondería `{"detail": "Not Found"}` en vez del formato uniforme del
    # resto de la API. Debe quedar registrado al final para actuar solo
    # como respaldo.
    @app.api_route(
        "/{camino_completo:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        include_in_schema=False,
    )
    async def _ruta_no_encontrada(camino_completo: str) -> None:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")

    return app


app = crear_app()
