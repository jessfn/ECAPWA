# ECA — Escuelas de Campo

Sistema para el seguimiento de actividades de campo de técnicos de Escuelas de Campo (ECA), con soporte para trabajar sin conexión.

## Componentes

- **`backend-eca/`** — API (FastAPI + PostgreSQL): autenticación JWT, RBAC, catálogos, ECA, jornadas y actividades con sincronización offline, importación por CSV, auditoría y rate limiting.
- **`admin-eca/`** — Panel de administración (Vue 3): gestión de usuarios, ECA, ámbitos geográficos, asignaciones, catálogos y solicitudes de acceso.
- **`pwa-eca/`** — App de campo para técnicos (Vue 3, PWA): funciona sin conexión (IndexedDB + outbox de sincronización), registro de jornada con geolocalización, actividades con evidencia fotográfica.
- **`docs-eca/`** — Documentación técnica y de producto del proyecto.

## Desarrollo local

Cada carpeta (`backend-eca`, `admin-eca`, `pwa-eca`) tiene su propio `README.md`/`.env.example` con instrucciones específicas de instalación y variables de entorno.

```bash
# Backend
cd backend-eca && cp .env.example .env  # completar con valores reales
python -m venv .venv && .venv/Scripts/activate  # o .venv/bin/activate en Unix
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontends
cd admin-eca && npm install && npm run dev
cd pwa-eca && npm install && npm run dev
```
