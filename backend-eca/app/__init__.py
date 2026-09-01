"""Paquete raíz del backend ECA (Escuelas de Campo).

ECA-002: app FastAPI mínima (settings, engine+pool SQLAlchemy, sesión por
request, Alembic, `GET /health`, logging estructurado, CORS, manejo de
errores uniforme). Sin modelos ni lógica de negocio todavía — llegan a
partir de ECA-003.

Este backend es independiente del sistema Sembrando Vida: no importa ni referencia
`backend/`, `pwasuper/` ni `admin-pwa/`.
"""

__version__ = "0.0.1"
