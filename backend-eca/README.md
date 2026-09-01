# backend-eca

Backend del sistema **ECA (Escuelas de Campo)**.

Sistema **independiente** del de Sembrando Vida (`backend/`): base de datos propia (`eca_db`),
despliegue propio, sin FKs ni llamadas cruzadas. Ver `docs-eca/04_ARQUITECTURA_OBJETIVO.md` §9.

## Estado — ECA-002

App FastAPI mínima y ejecutable: settings por entorno, engine + pool de conexiones SQLAlchemy,
sesión por request, Alembic inicializado, `GET /health`, logging estructurado en JSON, CORS con
lista blanca, manejo uniforme de errores. **Sin** modelos de dominio, autenticación ni lógica de
negocio todavía — llegan en ECA-003 en adelante.

## Estructura

```
backend-eca/
├── app/
│   ├── core/
│   │   ├── settings.py   # Pydantic Settings — SECRET_KEY/DATABASE_URL sin default
│   │   ├── db.py         # engine, pool, SessionLocal, get_db()
│   │   ├── logging.py    # logging JSON, sanea campos sensibles
│   │   └── errors.py     # respuesta de error uniforme {"error": {...}}
│   ├── models/       # modelos SQLAlchemy (ECA-003+)
│   ├── schemas/      # esquemas Pydantic (ECA-003+)
│   ├── repositories/ # acceso a datos (ECA-003+)
│   ├── services/     # reglas de negocio / transacciones (ECA-003+)
│   └── api/routers/
│       └── health.py # GET /health
├── alembic/
│   └── versions/
│       └── 0001_extensiones.py   # CREATE EXTENSION citext, pg_trgm
└── tests/
```

## Requisitos

- Python ≥ 3.11
- PostgreSQL ≥ 13

## Puesta en marcha

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# completar DATABASE_URL y SECRET_KEY (no dejar SECRET_KEY vacío: la app no arranca sin él)

# Postgres local para desarrollo (opcional, o usa uno ya existente):
docker compose up -d

alembic upgrade head
uvicorn app.main:app --reload
```

`GET http://localhost:8000/health` debe responder `{"status": "ok", "db": "ok", "version": "0.0.1"}`.

## Pruebas

```bash
pytest -v
```

Todas las pruebas corren sin PostgreSQL real, salvo `test_health_bd_real_arriba`, que se **salta**
automáticamente si no hay una `TEST_DATABASE_URL` alcanzable (ver `tests/conftest.py`).

## Convenciones

Ver `docs-eca/07_CONVENCIONES_CODIGO_ECA.md`.
