# 07 — Convenciones de código ECA

> Documento **breve**. Solo convenciones de nombres, estructura, ramas y versionado.
> No define arquitectura (ver `04`) ni modelo de datos (ver `05`) ni plan (ver `06`).

---

## 1. Proyectos

| Proyecto | Carpeta | Rol |
|---|---|---|
| Backend ECA | `backend-eca/` | API FastAPI + BD `eca_db` |
| PWA técnico | `pwa-eca/` | app de campo (Vue 3 + Vite) |
| Panel admin | `admin-eca/` | SPA de administración (Vue 3 + Vite) |

**Independencia estricta:** ningún proyecto ECA importa, referencia ni llama a
`backend/`, `pwasuper/`, `admin-pwa/` ni a la base de datos de Sembrando Vida.

---

## 2. Nombres

- **Idioma:** español para dominio de negocio (entidades, columnas, rutas de negocio,
  variables de dominio). Inglés solo donde lo impone el framework/estándar
  (`GET`, `id`, `created_at` de librerías, etc. → aun así se prefiere `creado_en`).
- **Python:** `snake_case` para módulos, funciones y variables; `PascalCase` para clases;
  `MAYUSCULAS` para constantes. Un dominio por archivo dentro de `models/`, `schemas/`,
  `repositories/`, `services/`, `api/routers/`.
- **SQL / BD:** tablas y columnas en `snake_case`, plural para tablas (`usuarios`, `ecas`,
  `actividades`). PK interna `id`; identificador público `uuid`; claves de origen
  `clave_*` / `clave_fuente`.
- **JavaScript / Vue:** `camelCase` para variables y funciones; componentes `.vue` en
  `PascalCase`; stores y servicios en `camelCase` (`authStore`, `apiService`).
  Vistas en `src/views/*View.vue`.
- **Endpoints:** sustantivos en plural, kebab/`snake` según recurso
  (`/usuarios`, `/geo/municipios`, `/actividades`, `/sync/push`). Acciones como subruta
  (`/jornadas/{uuid}/cerrar`).
- **Permisos:** `modulo.accion` en minúsculas (`ecas.importar`, `actividades.ver_todas`).
- **Migraciones Alembic:** `NNNN_descripcion_corta.py` (`0001_identidad.py`), numeración
  secuencial de 4 dígitos.

---

## 3. Estructura de carpetas

### backend-eca

```
app/
  core/         settings, db, seguridad, permisos, storage, auditoría (transversal)
  models/       SQLAlchemy (1 archivo por dominio)
  schemas/      Pydantic request/response
  repositories/ acceso a datos, sin HTTP
  services/     reglas de negocio, transacciones (unidad de trabajo)
  api/
    deps.py     dependencias (get_current_user, require_permission…)
    routers/    1 archivo por módulo
alembic/        migraciones versionadas
tests/          pytest
```

Regla: `api/routers` no importa otros `routers`; la colaboración pasa por `services/` y
`repositories/`. Los módulos de Fase 2 no son dependencia de los de Fase 1.

### pwa-eca / admin-eca

```
src/
  main.js       entrada
  App.vue       raíz
  router/       rutas + guards
  stores/       Pinia (uno por dominio de estado)
  services/     api, sync, gps, sesión local, IndexedDB…
  views/        pantallas (*View.vue)
  components/    componentes reutilizables
public/         estáticos servidos tal cual
```

---

## 4. Ramas y entregas

- Rama base: `main` (siempre desplegable). Integración opcional en `develop`.
- Una rama por ticket: `feature/ECA-00X-descripcion-corta`
  (ej. `feature/ECA-003-identidad-auth`).
- Correcciones: `fix/ECA-00X-...`. Higiene/documentación: `chore/...`, `docs/...`.
- PR pequeño y temático por ticket. No mezclar tickets en un PR.
- Mensajes de commit: `ECA-00X: <qué cambia>` en imperativo, en español.
- Cada PR debe dejar el proyecto **instalable/compilable** y con sus pruebas en verde.
- Migraciones: **siempre aditivas y reversibles** (`alembic downgrade -1`). No se editan
  migraciones ya aplicadas; se crea una nueva.

---

## 5. Versionado

- **Versión de proyecto** (`package.json` / `pyproject.toml`): SemVer.
  `0.x` durante el desarrollo del MVP; `1.0.0` al superar el piloto (HITO E + checklist).
- **Contrato de API:** el `openapi.json` de FastAPI es la referencia. Cambios incompatibles
  → nueva versión de ruta solo si es imprescindible (se evita en el MVP).
- **Esquema IndexedDB** (PWA): número de versión entero incremental con migración
  `onupgradeneeded` explícita (desde ECA-016).
- **Formularios publicados** (Fase 2): inmutables; una edición genera una versión nueva.
- **Catálogos:** no se borran; se desactivan (`activo = false`) para preservar el histórico.

---

## 6. Seguridad (recordatorio)

- Sin secretos en el repo. `.env.example` sin valores reales; `.env` en `.gitignore`.
- Contraseñas con hash (Argon2). Nunca texto plano.
- Autorización en el backend por endpoint (`require_permission`). El cliente solo oculta UI.
- Sin CURP completa, contraseñas ni tokens en logs.
