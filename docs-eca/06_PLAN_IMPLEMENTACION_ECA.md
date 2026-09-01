# 06 — Plan de implementación ECA (MVP para piloto)

> **Propósito.** Traducir la arquitectura objetivo (`04`) y el modelo de datos de referencia
> (`05`) en un **plan de tickets pequeños y desplegables** que lleve a un **MVP operativo para un
> piloto controlado**, evitando sobreingeniería.
>
> **Regla de oro.** `04` y `05` son **referencia de destino**, no el alcance del MVP. Cuando este
> plan simplifica algo respecto de `04`/`05`, **manda este plan** hasta el HITO E.
>
> **No se toca Sembrando Vida.** `backend/main.py`, `agricultura_db`, `pwasuper/`, `admin-pwa/`
> quedan congelados. ECA es un sistema aparte (`backend-eca/`, `pwa-eca/`, `admin-eca/`, `eca_db`).
>
> **Estado.** Plan. **No se ha creado código ni migraciones.**

---

## 0. Qué NO forma parte del MVP

> Sección de contención de alcance. Si algo de esta lista aparece en un ticket, el ticket está
> mal planteado.

| No incluido en el MVP | Cuándo |
|---|---|
| **Productores** (entidad, CRUD, deduplicación) | Fase 2, post-piloto |
| **Unidades productivas** y cultivos por unidad | Fase 2 |
| **Formularios dinámicos**, versiones, secciones, preguntas, opciones, reglas condicionales | Fase 2 |
| **Levantamientos** y respuestas | Fase 2 |
| **Evaluación / puntaje / calificación del técnico**, metas, ponderaciones | Cuando la institución defina metodología |
| **Firma de reportes** (obligatoria o no) | Post-MVP; el modelo lo permitirá después |
| **Reportes periódicos avanzados** y **generación de PDF** | Post-HITO E |
| **Indicadores/tableros analíticos** más allá de "consultar actividades" | Post-HITO E |
| **Detección antifraude por hash perceptual (pHash)** | No se implementa en el MVP |
| **Módulo antifraude** de cualquier tipo | No en el MVP |
| **Celery / RQ / Redis / colas / workers asíncronos** | Solo si hay una necesidad real demostrada (no la hay en el MVP) |
| **Grupos de trabajo, `roles_grupo`, jerarquía de enlaces/supervisores** | Post-MVP (roles y asignaciones se mantienen flexibles, pero sin UI de grupos en el MVP) |
| **`sync_operaciones` como ledger dedicado** | Post-MVP; en el MVP la idempotencia se apoya en `UNIQUE(uuid)` + `auditoria_eventos` |
| **Particionado de `auditoria_eventos`** | Post-piloto, cuando se conozca el volumen |
| **`localidades` normalizadas** (catálogo INEGI de localidades) | Post-MVP; en el MVP la localidad de una ECA es texto libre (`ecas.localidad_nombre`) |
| **Object storage S3/MinIO** | Post-MVP; en el MVP las evidencias van a filesystem local con una capa de abstracción `Storage` |
| **PostGIS / índices espaciales** | Post-MVP; en el MVP lat/long son `numeric` con índice btree |
| **Notificaciones push, manuales, historial de perfil, avisos de privacidad** (features de SV) | No aplican al MVP |
| **Flujo de revisión de actividades** (`ENVIADO→REVISADO→OBSERVADO→APROBADO`) | Post-MVP; en el MVP la tabla `actividades` **no lleva estado de flujo** (ver §2.3): la sincronización se deriva de `recibido_en`, y el estado de negocio se limita —solo si hace falta— a `ACTIVA`/`ANULADA` |
| **Multi-jornada por día**, GPS obligatorio en jornada, foto en jornada | El MVP: 1 jornada/día, sin foto ni GPS obligatorios |
| **Edición de una actividad ya sincronizada desde la PWA** | El MVP: la actividad es inmutable para el técnico tras sincronizarse; correcciones solo por admin (auditadas) |
| **Migración de datos históricos de Sembrando Vida** | Nunca |

---

## 1. Principios del plan

1. **Slices verticales y desplegables.** Cada ticket deja el sistema en un estado desplegable y
   probado. Nada de "media feature".
2. **Aditividad.** Todas las migraciones son aditivas y reversibles (`alembic downgrade -1`).
   Ninguna migración destruye datos.
3. **Backend primero, seguridad primero.** No hay endpoint de datos sin autenticación +
   `require_permission`.
4. **Offline se construye sobre lo online.** Primero actividad online funcionando (HITO C),
   luego se le añade la capa offline (HITO D). No al revés.
5. **Sin infraestructura opcional.** Sin colas, sin cache distribuida, sin storage externo hasta
   que el piloto demuestre que hace falta.
6. **Catálogos y configuración, no constantes.** Las reglas pendientes (`03` §27) se resuelven
   con `parametros_config`, permisos y asignaciones.
7. **El piloto valida, no la teoría.** El HITO E se alcanza **antes** de reportes avanzados,
   productores o formularios.

---

## 2. Convenciones

| Concepto | Valor MVP |
|---|---|
| Repos / carpetas | `backend-eca/`, `pwa-eca/`, `admin-eca/` (repos o carpetas independientes; **no** dentro de `backend/`, `pwasuper/`, `admin-pwa/`) |
| Base de datos | `eca_db` (PostgreSQL ≥ 13). Extensiones: `citext`, `pg_trgm` |
| Roles MVP | `ADMIN`, `TECNICO` (tabla `roles`, extensible; sin UI de edición de roles en el MVP) |
| Responsable de despliegue | **Jesús** (provisiona servidor, BD, variables de entorno, ejecuta migraciones y despliegues, valida en servidor) |
| Preparación de código | **Claude Code** (estructura, migraciones, endpoints, componentes, pruebas; **no** ejecuta en el servidor de producción) |
| Zona horaria | BD en UTC (`timestamptz`); presentación en hora local del técnico |
| Identidad de objetos de campo | `uuid` v4 generado en el dispositivo; `UNIQUE(uuid)` en servidor |

### 2.1 Stack del MVP (simplificado desde `04`)

| Capa | MVP |
|---|---|
| Backend | FastAPI · SQLAlchemy 2.x · Alembic · `psycopg` (v3) · **pool de conexiones** · gunicorn+uvicorn workers tras nginx |
| Auth | `argon2-cffi` (hash) · JWT de acceso **corto** (p. ej. 15 min, configurable) + **refresh token en BD revocable** de vida más larga · **sesión local offline** para trabajo sin red (§2.2, **DP-1**) |
| Almacenamiento de evidencias | **Filesystem local privado** vía capa `Storage` (interfaz con implementación `LocalStorage`; `S3Storage` queda para después). Servido por endpoint autenticado, nunca estático público |
| Integridad de archivos | **SHA-256** del archivo, solo para idempotencia de subida y verificación de integridad. **Sin** pHash, **sin** módulo antifraude |
| Tareas diferidas | **Ninguna.** Todo síncrono, incluida la importación de ~5 000 ECA |
| PWA técnico | Vue 3 · Vite · `vite-plugin-pwa` (Workbox, un solo SW) · Pinia · `idb` (IndexedDB) · Leaflet · axios |
| Panel admin | Vue 3 · Vite · Pinia · axios · (tabla simple; mapa solo si sobra tiempo) |
| Pruebas | Backend: `pytest` + `httpx` + BD de prueba. Front: `vitest` (mínimo, lógica de outbox/sync) |
| Config | Pydantic Settings desde variables de entorno; `SECRET_KEY` sin valor por defecto |

### 2.2 Sesión de servidor vs. sesión local offline

Son **dos conceptos distintos** y no deben confundirse:

- **Sesión / autorización de servidor.** El `access_token` (JWT corto) + `refresh_token`.
  Autoriza llamadas al backend. El `access_token` caduca pronto; renovarlo
  (`refresh` o, si el refresh también expiró, `login`) **requiere red**.
- **Sesión local offline (previamente validada).** Marca guardada en el dispositivo que indica
  *"esta persona hizo login + bootstrap con conexión en el pasado reciente"*. Habilita **abrir la
  PWA y capturar** jornadas, actividades, GPS y evidencias **aunque el `access_token` haya
  expirado** mientras no hay red.

**Reglas:**

1. Tras un login + bootstrap con red, la PWA guarda una **marca de sesión local**: identidad del
   usuario, permisos efectivos del último `/auth/me`, y fecha de validación.
2. Con esa marca vigente, el técnico **puede seguir trabajando offline** aunque el JWT de acceso
   haya expirado: todo lo que capture queda en el **outbox** como `PENDIENTE`.
3. Para **sincronizar** (enviar el outbox o hacer `pull`) **sí** es obligatorio recuperar una
   **sesión de servidor válida** vía `refresh`/`login`. Hasta entonces, los pendientes
   **permanecen intactos** localmente.
4. La PWA **nunca** descarta datos del outbox por expiración de sesión (ni de servidor ni local).
5. **Duración de validez de la sesión local offline** y **vida del `refresh_token`**:
   **configurables** (`parametros_config` + configuración de cliente entregada en el bootstrap).
   **Este plan no fija un valor institucional** → ver **DP-1**. Vencida la validez local, la PWA
   exige reconexión para *volver a capturar*, pero **conserva** los pendientes ya creados.

**Escenario que debe funcionar de extremo a extremo:**

```
login con red → bootstrap → pérdida de red → expira el access_token →
el técnico sigue capturando jornada/actividad/GPS/evidencia (todo queda PENDIENTE) →
vuelve la conexión → refresh/login recupera sesión de servidor →
sincroniza SIN pérdida ni duplicados (reintentar el push → 0 cambios)
```

### 2.3 Estado de negocio vs. estado de transmisión

No mezclar el estado de **transmisión** (*¿llegó al servidor?*) con el estado de **negocio**
(*¿qué es esta actividad?*).

- **Estado de transmisión = SOLO local (outbox / IndexedDB).** Valores:
  `PENDIENTE` · `SINCRONIZANDO` · `SINCRONIZADO` · `RECHAZADO`. **No** se persiste como columna en
  la tabla `actividades` del servidor ni se envía como estado de negocio. En el código de cliente
  se nombra `estado_local` para evitar confusión.
- **La tabla `actividades` del servidor** deriva la "sincronización" de columnas de tiempo, no de
  un enum de transmisión:
  - `creado_en_dispositivo` — hora del evento según el dispositivo;
  - `recibido_en` / `sincronizado_en` — marca del servidor al aceptar el objeto (basta una columna);
  - `eliminado_en` — borrado lógico.
- **Estado de negocio en `actividades`**: en el MVP **no hay flujo de revisión**. Solo si el
  negocio lo exige se añade un enum **simple** `estado ∈ {ACTIVA, ANULADA}` (por defecto `ACTIVA`).
  **No** se usan `BORRADOR`/`SINCRONIZADA` en la BD.
- En el historial, la PWA muestra "sin sincronizar" leyendo el **outbox local**; "sincronizada" =
  la actividad existe en el servidor (tiene `recibido_en`).

### 2.4 Decisiones pendientes que este plan deja explícitas

| ID | Decisión pendiente | Mecanismo provisional | Referencia |
|---|---|---|---|
| **DP-1** | Duración de la **autorización/sesión offline** (validez de la sesión local sin red) y vida del `refresh_token`. | **Configurable** (`parametros_config` + config de cliente en el bootstrap). Valores iniciales de trabajo, revisables con la institución. **Sin valor institucional fijado en este plan.** | §2.2 |
| **DP-2** | **Columna identificador estable** del archivo institucional real de ECA (se mapeará a `clave_fuente` / `identificador_fuente`: `ID_ECA`, folio, clave institucional, …). Si el archivo **no** trae ningún identificador estable: cómo se resuelve el upsert. | La importación **exige** `clave_fuente`; sin ella **se detiene y se escala**. **No** se deduplica automáticamente por nombre/municipio. | `03` §27.14 · ECA-007 |

---

## 3. Hitos

| Hito | Se alcanza tras | Significa |
|---|---|---|
| **HITO A — Backend seguro funcionando** | ECA-004 | `eca_db` creada, `backend-eca` desplegado, login/refresh/logout con Argon2 + JWT, `require_permission` operativo, auditoría básica. |
| **HITO B — Administración de usuarios/ECA funcionando** | ECA-010 | Un administrador puede: crear/importar usuarios; administrar estados/municipios; importar ~5 000 ECA; asignar municipios de trabajo; asignar ECA directas; administrar catálogos de actividad. |
| **HITO C — Actividad online funcionando** | ECA-015 | Un técnico (con red) inicia sesión, ve sus ECA relevantes, inicia jornada, registra una actividad clasificada con GPS + precisión + 1–3 fotos, y la ve en su historial. |
| **HITO D — Actividad offline + sincronización funcionando** | ECA-018 | Lo anterior **sin conexión**: los datos se guardan localmente, se sincronizan al recuperar red **sin duplicar**, y el subconjunto de ECA/catálogos relevante queda disponible offline. |
| **HITO E — MVP listo para piloto** | ECA-020 | Sistema endurecido, observabilidad mínima, datos de piloto cargados, checklist de piloto aprobado. **Antes** de reportes avanzados, productores o formularios. |

```
ECA-001 ─ ECA-002 ─ ECA-003 ─ ECA-004  ──►  ★ HITO A
                                   │
        ┌──────────────────────────┤
      ECA-005 (scaffold admin)     │
        │                          │
      ECA-006 ─ ECA-007 ─ ECA-008 ─ ECA-009 ─ ECA-010  ──►  ★ HITO B
                                                   │
      ECA-011 (scaffold PWA) ──────────────────────┤
        │                                          │
      ECA-012 ─ ECA-013 ─ ECA-014 ─ ECA-015  ──────────►  ★ HITO C
                                        │
      ECA-016 ─ ECA-017 ─ ECA-018  ─────────────────────►  ★ HITO D
                              │
      ECA-019 (historial) ────┤
        │                     │
      ECA-020 ─ ECA-021  ─────────────────────────────►  ★ HITO E
```

---

## 4. Tickets

> Plantilla por ticket: **ID · Nombre · Objetivo · Por qué · Dependencias · Crear · Modificar ·
> Tablas · Migraciones · Endpoints · PWA · Panel admin · Offline · Permisos · Pruebas unitarias ·
> Pruebas de integración · Pruebas manuales · Criterios de aceptación · Pasos de despliegue (Jesús)
> · Rollback · Riesgos · Complejidad.**
> "N/A" = no aplica en este ticket.

---

### ECA-001 — Preparar estructura independiente ECA

- **Objetivo.** Crear los tres proyectos vacíos (`backend-eca/`, `pwa-eca/`, `admin-eca/`) con su
  estructura de carpetas, README, `.gitignore`, `.env.example` y licencia/So propietaria, sin
  lógica de negocio.
- **Por qué se necesita.** `03` §1 y `AGENTS.md` regla 5 exigen que ECA nazca separado del
  monolito y del frontend de SV. Sin esta base, todo lo demás se contaminaría con el legado.
- **Dependencias.** Ninguna.
- **Archivos/carpetas a crear.**
  - `backend-eca/` → `app/`, `app/core/`, `app/models/`, `app/schemas/`, `app/repositories/`,
    `app/services/`, `app/api/routers/`, `alembic/`, `tests/`, `pyproject.toml`/`requirements.txt`,
    `README.md`, `.env.example`, `.gitignore`, `Dockerfile` (opcional).
  - `pwa-eca/` → scaffold Vite+Vue (`src/`, `src/stores/`, `src/services/`, `src/views/`,
    `src/router/`, `public/`), `README.md`, `.env.example`, `.gitignore`.
  - `admin-eca/` → scaffold Vite+Vue análogo.
  - `docs-eca/` → (ya existe) añadir `07_CONVENCIONES_CODIGO_ECA.md` breve (naming, ramas,
    versionado) — opcional.
- **Archivos/carpetas a modificar.** N/A (no se toca SV).
- **Tablas involucradas.** N/A.
- **Migraciones necesarias.** N/A.
- **Endpoints.** N/A.
- **Cambios PWA.** Scaffold inicial únicamente.
- **Cambios panel admin.** Scaffold inicial únicamente.
- **Comportamiento offline.** N/A.
- **Permisos.** N/A.
- **Pruebas unitarias.** `backend-eca`: un test dummy que importe la app y pase (`pytest` corre).
- **Pruebas de integración.** N/A.
- **Pruebas manuales.** `pip install` / `npm install` en cada proyecto sin errores;
  `npm run build` de los dos frontends produce artefacto.
- **Criterios de aceptación.** Los tres proyectos compilan/instalan en limpio; ningún import
  apunta a `backend/`, `pwasuper/` o `admin-pwa/`; `.env.example` sin secretos reales.
- **Pasos de despliegue (Jesús).** Crear los repos remotos (o carpetas) y ramas base
  (`main`, `develop`). Configurar acceso. Nada en servidor de producción todavía.
- **Rollback.** Eliminar carpetas/repos nuevos. Sin impacto en SV.
- **Riesgos.** Bajo. Riesgo de "copiar de más" del repo clonado → revisar que no se arrastre
  código de negocio SV.
- **Complejidad.** **BAJA**.

---

### ECA-002 — Configuración y base técnica del backend

- **Objetivo.** App FastAPI mínima con: settings por entorno, engine + pool SQLAlchemy, sesión
  por request (`get_db`), Alembic inicializado, `GET /health`, logging estructurado, CORS con
  lista blanca, manejo de errores uniforme.
- **Por qué se necesita.** Corrige de raíz los hallazgos de `02` §3/§21 (cursor global, sin pool,
  migraciones al importar). Es el esqueleto sobre el que se monta todo.
- **Dependencias.** ECA-001.
- **Crear.**
  - `app/main.py` (creación de app, middlewares, router de health).
  - `app/core/settings.py` (Pydantic Settings: `DATABASE_URL`, `SECRET_KEY` sin default,
    `ACCESS_TOKEN_MIN`, `REFRESH_TOKEN_DIAS`, `OFFLINE_SESSION_DIAS` (validez de la sesión local
    offline — **DP-1**, configurable), `CORS_ORIGINS`, `STORAGE_DIR`).
  - `app/core/db.py` (engine con `pool_size`/`max_overflow`, `SessionLocal`, `get_db`).
  - `app/core/logging.py` (JSON logs, sin datos sensibles).
  - `app/core/errors.py` (handlers → respuesta JSON uniforme).
  - `alembic.ini`, `alembic/env.py`, `alembic/versions/` (vacío).
  - `app/api/routers/health.py`.
  - `tests/conftest.py` (BD de prueba efímera), `tests/test_health.py`.
  - `docker-compose.yml` (opcional, para dev local: postgres + backend).
- **Modificar.** N/A.
- **Tablas.** Ninguna (Alembic queda listo, sin revisiones).
- **Migraciones.** `alembic init` + configuración; primera revisión vacía o con
  `CREATE EXTENSION IF NOT EXISTS citext; CREATE EXTENSION IF NOT EXISTS pg_trgm;`.
- **Endpoints.** `GET /health` → `{status, db: "ok"|"error", version}`.
- **Cambios PWA / panel.** N/A.
- **Offline.** N/A.
- **Permisos.** `GET /health` público (sin datos sensibles).
- **Pruebas unitarias.** Settings carga y falla si falta `SECRET_KEY`; `get_db` entrega y cierra
  sesión.
- **Pruebas de integración.** `GET /health` responde 200 con BD arriba; 503 con BD caída.
- **Pruebas manuales.** Arrancar con `SECRET_KEY` ausente → la app **no** arranca (correcto).
- **Criterios de aceptación.** App arranca con múltiples workers; `alembic upgrade head` sin
  revisiones no falla; `/health` verde; logs en JSON sin secretos; CORS rechaza origen no listado.
- **Pasos de despliegue (Jesús).**
  1. Crear BD `eca_db` y usuario dedicado con permisos sobre ese esquema.
  2. Instalar extensiones `citext`, `pg_trgm` (o dejar que la 1ª migración las cree).
  3. Definir variables de entorno (`.env` fuera del repo): `DATABASE_URL`, `SECRET_KEY` (aleatoria
     larga), `CORS_ORIGINS`, `STORAGE_DIR`.
  4. Desplegar `backend-eca` (gunicorn+uvicorn, 2–4 workers) tras nginx en `api-eca.<dominio>`.
  5. `alembic upgrade head`.
  6. Verificar `GET /health`.
- **Rollback.** Bajar el servicio; `alembic downgrade base`; la BD `eca_db` puede quedar vacía o
  eliminarse. Sin impacto en SV.
- **Riesgos.** Configuración de pool mal dimensionada (ajustar `pool_size` según workers × conexiones).
- **Complejidad.** **MEDIA**.

---

### ECA-003 — Migración inicial de identidad y autenticación

- **Objetivo.** Tabla `usuarios` única + `tokens_refresco`; login con Argon2, emisión de JWT de
  acceso + refresh token persistido, refresh, logout (revocación), `GET /auth/me`, cambio de
  contraseña.
- **Por qué se necesita.** `02` §4/§20: SV guarda contraseñas en texto plano, JWT sin expiración,
  `/auth/me` es un stub. ECA no puede tener usuarios sin esto.
- **Dependencias.** ECA-002.
- **Crear.**
  - `app/models/usuario.py`, `app/models/token_refresco.py`.
  - `app/core/security.py` (hash Argon2, verificación, emisión/verificación JWT, hash de refresh).
  - `app/schemas/auth.py`, `app/schemas/usuario.py`.
  - `app/repositories/usuarios.py`, `app/services/auth_service.py`.
  - `app/api/routers/auth.py`, `app/api/deps.py` (`get_current_user`).
  - `alembic/versions/0001_identidad.py`.
  - `tests/test_auth.py`.
- **Modificar.** `app/main.py` (incluir router `auth`).
- **Tablas.** `usuarios`, `tokens_refresco` (según `05` §4.1, versión MVP: sin `lote_importacion_id`
  todavía — se añade aditivamente en ECA-004/ECA-006 si hace falta; **incluir** `estado`,
  `curp` nullable, BAE).
- **Migraciones.** `0001_identidad`: crea `usuarios` y `tokens_refresco` con índices
  (`UNIQUE(correo)`, `UNIQUE(uuid)`, `UNIQUE(curp) WHERE curp IS NOT NULL`, `UNIQUE(jti)`).
- **Endpoints.**
  - `POST /auth/login` (correo + contraseña) → `{access_token, refresh_token, expira_en}`.
  - `POST /auth/refresh` → nuevo par (rota el refresh).
  - `POST /auth/logout` → revoca el refresh actual.
  - `GET /auth/me` → datos del usuario + permisos (permisos llegan en ECA-004).
  - `POST /auth/password` → cambio de contraseña propia (exige contraseña actual).
- **Cambios PWA / panel.** N/A (se consume en ECA-005/ECA-011).
- **Offline.** N/A en este ticket: el login inicial requiere red. La **sesión local offline** que
  habilita capturar sin red (aunque el `access_token` expire) se construye en ECA-011 (§2.2);
  el `refresh_token` debe tener vida **mayor** que el `access_token` (**DP-1**).
- **Permisos.** `login`/`refresh` públicos con rate limiting; `me`/`password` requieren token
  válido y usuario `ACTIVO`.
- **Pruebas unitarias.** Hash Argon2 verifica correctamente; JWT expira; refresh revocado no sirve;
  contraseña débil rechazada.
- **Pruebas de integración.** Flujo login→me→refresh→logout; login con usuario `SUSPENDIDO`/`BAJA`
  → 403; refresh caducado → 401.
- **Pruebas manuales.** Crear un usuario semilla por script; login desde `curl`/Postman; verificar
  que el `access_token` caduca y `refresh` lo renueva.
- **Criterios de aceptación.** No existe ninguna ruta que devuelva o acepte contraseña en claro;
  el JWT tiene `exp`; logout invalida el refresh; un usuario en `BAJA` no puede autenticarse.
- **Pasos de despliegue (Jesús).**
  1. `alembic upgrade head`.
  2. Ejecutar script `crear_admin.py` (lo prepara Claude Code) para el **primer usuario ADMIN**
     con contraseña provista por Jesús (no en el repo).
  3. Probar `POST /auth/login` con ese usuario.
- **Rollback.** `alembic downgrade -1` (elimina `usuarios`, `tokens_refresco`). Redeploy build
  anterior.
- **Riesgos.** Manejo del refresh token (rotación y revocación) mal hecho → sesiones no
  invalidables. Mitigar con pruebas de integración explícitas.
- **Complejidad.** **MEDIA**.

---

### ECA-004 — Usuarios y permisos mínimos

- **Objetivo.** RBAC mínimo: `roles`, `permisos`, `roles_permisos`, `usuarios_roles` (semilla
  fija, sin UI de edición); dependencia `require_permission("clave")`; CRUD de usuarios (alta,
  edición, alta/baja de estado, asignación de rol) para ADMIN; importación de usuarios por CSV.
- **Por qué se necesita.** `02` §6: en SV la autorización es 100 % del cliente. ECA exige control
  en backend por endpoint. El admin necesita crear/importar técnicos (`03` §4.1).
- **Dependencias.** ECA-003.
- **Crear.**
  - `app/models/rbac.py` (roles, permisos, roles_permisos, usuarios_roles).
  - `app/core/permissions.py` (`require_permission`, resolución de permisos efectivos).
  - `app/services/usuarios_service.py`, `app/services/importacion_usuarios_service.py`.
  - `app/api/routers/usuarios.py`, `app/api/routers/permisos.py` (solo lectura de catálogo).
  - `app/core/audit.py` + `app/models/auditoria.py` (tabla `auditoria_eventos` MVP: sin
    particionado).
  - `alembic/versions/0002_rbac_auditoria.py`.
  - `alembic/versions/0003_seed_roles_permisos.py` (data migration de semilla).
  - `scripts/crear_admin.py`.
  - `tests/test_permisos.py`, `tests/test_usuarios.py`.
- **Modificar.** `app/api/routers/auth.py` (`/auth/me` devuelve permisos efectivos);
  `app/models/usuario.py` (relación con `usuarios_roles`).
- **Tablas.** `roles`, `permisos`, `roles_permisos`, `usuarios_roles`, `auditoria_eventos`.
  (Se añade `usuarios.lote_importacion_id` en ECA-006; aquí un import de usuarios simple registra
  en `auditoria_eventos`.)
- **Migraciones.** `0002` (estructura RBAC + auditoría), `0003` (semilla de roles `ADMIN`/`TECNICO`
  y permisos MVP; asigna todos los permisos a `ADMIN` y el subconjunto de campo a `TECNICO`).
- **Endpoints.**
  - `GET /usuarios` (filtros: estado, rol, texto), `POST /usuarios`, `GET/PATCH /usuarios/{id}`,
    `PATCH /usuarios/{id}/estado`, `PUT /usuarios/{id}/roles`.
  - `POST /usuarios/importar` (CSV: nombre, apellidos, correo, curp?, rol) → valida por fila,
    responde resumen + errores; crea con contraseña temporal + `requiere_cambio_contrasena`.
  - `GET /roles`, `GET /permisos` (solo lectura).
- **Cambios PWA.** N/A.
- **Cambios panel admin.** N/A (la pantalla llega en ECA-005; aquí solo el backend).
- **Offline.** N/A.
- **Permisos MVP (semilla).**
  `usuarios.gestionar`, `usuarios.importar`, `geo.gestionar`, `ecas.ver`, `ecas.gestionar`,
  `ecas.importar`, `ambitos.gestionar`, `asignaciones.gestionar`, `catalogos.ver`,
  `catalogos.gestionar`, `actividades.crear`, `actividades.ver_propias`, `actividades.ver_todas`,
  `jornadas.crear`, `jornadas.ver_propias`, `sync.usar`.
  - `ADMIN` → todos. `TECNICO` → `ecas.ver`, `catalogos.ver`, `actividades.crear`,
    `actividades.ver_propias`, `jornadas.crear`, `jornadas.ver_propias`, `sync.usar`.
- **Pruebas unitarias.** `require_permission` niega sin permiso (403) y permite con permiso;
  resolución de permisos = unión de roles; import rechaza correo duplicado / rol inexistente.
- **Pruebas de integración.** ADMIN crea TECNICO; TECNICO no puede llamar `POST /usuarios` (403);
  cambiar rol de un usuario cambia sus permisos en el siguiente `/auth/me`.
- **Pruebas manuales.** Importar un CSV de 20 técnicos de ejemplo; verificar credenciales
  temporales y forzado de cambio de contraseña.
- **Criterios de aceptación.** Ningún endpoint de datos responde sin `require_permission`;
  el import valida por fila y no crea nada si el lote se cancela; toda alta/baja/cambio de rol
  queda en `auditoria_eventos` sin CURP completa.
- **Pasos de despliegue (Jesús).**
  1. `alembic upgrade head` (aplica `0002` y `0003`).
  2. Verificar que la semilla creó roles y permisos (`GET /roles`, `GET /permisos`).
  3. Confirmar que el usuario ADMIN inicial tiene rol `ADMIN`.
- **Rollback.** `alembic downgrade` hasta antes de `0002`. Redeploy anterior. Los usuarios creados
  por import se pierden (aceptable en pre-piloto).
- **Riesgos.** Semilla de permisos incompleta → endpoints inaccesibles. Mitigar con un test que
  recorra todos los routers y verifique que cada permiso usado existe en la semilla.
- **Complejidad.** **MEDIA**.

> **★ HITO A — Backend seguro funcionando** (tras ECA-004).

---

### ECA-005 — Scaffold del panel administrativo ECA + login

- **Objetivo.** App `admin-eca` funcional: login, guard de ruta por token, layout, store `auth`
  con permisos, cierre de sesión, pantalla vacía de "Inicio". Autorización de menús por permiso
  (solo UX; el backend ya la impone).
- **Por qué se necesita.** Sin panel no hay forma de administrar usuarios/ECA (HITO B).
- **Dependencias.** ECA-003, ECA-004.
- **Crear.**
  - `admin-eca/src/stores/auth.js` (login, refresh, permisos, logout).
  - `admin-eca/src/services/api.js` (axios + interceptor de refresh en 401).
  - `admin-eca/src/router/index.js` (guard `requiresAuth` + `requiresPermission`).
  - `admin-eca/src/layouts/DefaultLayout.vue`, `src/views/LoginView.vue`, `src/views/InicioView.vue`.
  - `admin-eca/.env.example` (`VITE_API_URL`).
- **Modificar.** N/A.
- **Tablas / migraciones / endpoints.** N/A (consume `auth`).
- **Cambios PWA.** N/A.
- **Cambios panel admin.** Este ticket **es** el panel base.
- **Offline.** N/A (panel siempre online).
- **Permisos.** Consume permisos de `/auth/me` para mostrar/ocultar navegación.
- **Pruebas unitarias.** Store `auth`: guarda token, detecta expiración, limpia en logout.
- **Pruebas de integración.** N/A (front). Vitest sobre el interceptor de refresh (mock).
- **Pruebas manuales.** Login con ADMIN; recargar página mantiene sesión; token caducado dispara
  refresh transparente; logout limpia y redirige a login.
- **Criterios de aceptación.** No se accede a ninguna ruta sin token; el refresh es transparente;
  un usuario sin permiso no ve la opción de menú (y si fuerza la URL, el backend responde 403).
- **Pasos de despliegue (Jesús).**
  1. `npm run build` de `admin-eca`.
  2. Publicar estáticos en `admin-eca.<dominio>` (nginx `try_files ... /index.html`,
     `Cache-Control: no-store` en `index.html`).
  3. Configurar `VITE_API_URL` a `api-eca.<dominio>`.
  4. Smoke test de login.
- **Rollback.** Restaurar build anterior de estáticos.
- **Riesgos.** CORS mal configurado entre `admin-eca.<dominio>` y `api-eca.<dominio>`.
- **Complejidad.** **MEDIA**.

---

### ECA-006 — Catálogos geográficos (estados y municipios)

- **Objetivo.** Tablas `estados` y `municipios` con semilla INEGI; endpoints de lectura;
  pantalla admin de consulta (y edición mínima de `activo`).
- **Por qué se necesita.** `03` §6.2: estado y municipio no son texto libre. Base para ECA,
  ámbitos y filtros.
- **Dependencias.** ECA-004, ECA-005.
- **Crear.**
  - `app/models/geo.py`, `app/schemas/geo.py`, `app/repositories/geo.py`.
  - `app/api/routers/geo.py`.
  - `alembic/versions/0004_geo.py` + `alembic/versions/0005_seed_geo.py` (o carga por script/CSV
    versionado en `backend-eca/data/inegi/`).
  - `admin-eca/src/views/GeografiaView.vue`, servicio `geoService.js`.
  - `tests/test_geo.py`.
- **Modificar.** `app/main.py` (router `geo`), `admin-eca/src/router` (ruta).
- **Tablas.** `estados`, `municipios` (según `05` §4.3; **sin** `localidades` en el MVP).
- **Migraciones.** `0004` (estructura + `UNIQUE(clave_inegi)`, FK `municipios.estado_id`,
  `idx_municipios_estado`), `0005` (semilla: 32 estados + ~2 469 municipios).
- **Endpoints.**
  - `GET /geo/estados`, `GET /geo/municipios?estado_id=` (obligatorio el filtro o paginación),
  - `PATCH /geo/estados/{id}` / `PATCH /geo/municipios/{id}` (solo `activo`; permiso `geo.gestionar`).
- **Cambios PWA.** N/A (llega vía bootstrap en ECA-018).
- **Cambios panel admin.** Pantalla "Geografía": árbol/tabla estado→municipios, buscador,
  toggle `activo`.
- **Offline.** N/A todavía.
- **Permisos.** Lectura: cualquier usuario autenticado. Edición: `geo.gestionar`.
- **Pruebas unitarias.** Semilla carga 32 estados; `clave_inegi` de municipio es única;
  `municipios?estado_id=` filtra correctamente.
- **Pruebas de integración.** `GET /geo/municipios` sin filtro → 400 o paginado; `PATCH` sin
  permiso → 403.
- **Pruebas manuales.** Revisar 3–4 estados contra INEGI; buscar un municipio por nombre.
- **Criterios de aceptación.** Semilla completa y verificable; búsqueda por nombre con `pg_trgm`
  responde < 300 ms; no hay texto libre de estado/municipio en ninguna parte.
- **Pasos de despliegue (Jesús).**
  1. `alembic upgrade head` (aplica `0004`, `0005`).
  2. Verificar conteos: `SELECT count(*) FROM estados;` (=32), `municipios` (~2469).
- **Rollback.** `alembic downgrade -1` (dos pasos si semilla y estructura están separadas).
- **Riesgos.** Fuente INEGI desactualizada o con claves cambiadas → acordar con Jesús la fuente
  exacta (año del catálogo). Documentar la fuente en `data/inegi/FUENTE.md`.
- **Complejidad.** **MEDIA** (la carga de datos es el grueso).

---

### ECA-007 — Catálogo e importación masiva de ECA

- **Objetivo.** Tabla `ecas`; CRUD de lectura + alta/edición individual; **importación
  síncrona** CSV/XLSX de ~5 000 ECA con validación por fila (previsualización) y confirmación
  mediante **upsert determinista por un identificador de origen estable**
  (`clave_fuente` / `identificador_fuente` — el nombre real de la columna del archivo
  institucional está **por definir**, ver **DP-2**). **Ninguna importación debe crear ECA sin
  identificador estable.**
- **Por qué se necesita.** `03` §6: la ECA es la entidad central; el admin debe poder cargar el
  catálogo nacional.
- **Dependencias.** ECA-006.
- **Crear.**
  - `app/models/eca.py`, `app/models/lote_importacion.py`.
  - `app/schemas/eca.py`, `app/repositories/ecas.py`.
  - `app/services/importacion_eca_service.py` (parseo CSV/XLSX, validación, upsert transaccional).
  - `app/api/routers/ecas.py`.
  - `alembic/versions/0006_ecas.py`.
  - `admin-eca/src/views/EcasView.vue`, `EcaImportarView.vue`, `ecasService.js`.
  - `tests/test_ecas.py`, `tests/test_importacion_eca.py` + fixtures CSV (10 filas OK, 5 con error).
- **Modificar.** `app/main.py`; `admin-eca/src/router`.
- **Tablas.** `ecas` (versión MVP: `id`, `uuid`,
  **`clave_fuente` TEXT** (identificador estable del archivo de origen; **clave de upsert**;
  `UNIQUE` cuando no es NULL; se mapea a la columna real —`ID_ECA`/folio/clave institucional—
  cuando se conozca, **DP-2**),
  `clave_institucional` TEXT nullable UNIQUE (código oficial, si es distinto del anterior),
  `nombre`, `estado_id`, `municipio_id`, `localidad_nombre` **texto libre**,
  `latitud`/`longitud` nullable, `activo`, `fuente_carga`, `lote_importacion_id` nullable, BAE,
  `eliminado_en` nullable);
  `lotes_importacion` (una sola tabla; errores en `resumen jsonb`, **sin** `errores_importacion`
  separada).
- **Migraciones.** `0006`: `ecas` + `lotes_importacion` + índices
  (`UNIQUE(uuid)`, **`UNIQUE(clave_fuente) WHERE clave_fuente IS NOT NULL`**,
  `UNIQUE(clave_institucional) WHERE clave_institucional IS NOT NULL`, `idx_ecas_estado`,
  `idx_ecas_municipio`, `idx_ecas_nombre_trgm`, `idx_ecas_activo`).
- **Endpoints.**
  - `GET /ecas?estado_id=&municipio_id=&q=&activo=&page=` (paginado; `q` = clave o nombre).
  - `GET /ecas/{id}`, `POST /ecas`, `PATCH /ecas/{id}` (permiso `ecas.gestionar`).
  - `POST /ecas/importar` (multipart, `{columna_identificador}` opcional) → parsea, valida por
    fila; **si el archivo no tiene una columna identificador estable configurada/detectada,
    responde `422` "sin identificador estable" y NO crea nada** (ver **DP-2** — no se deduplica
    por nombre/municipio); si la tiene, crea `lote` en estado `VALIDADO` y responde
    `{lote_uuid, total, validas, con_error, errores:[{fila, campo, mensaje}]}`.
  - `POST /ecas/importar/{lote_uuid}/confirmar` → **upsert transaccional por `clave_fuente`** de
    las filas válidas; marca `lote` `CONFIRMADO`.
  - `GET /ecas/importar/{lote_uuid}` → estado y resumen del lote.
- **Cambios PWA.** N/A (llega por bootstrap).
- **Cambios panel admin.** Pantalla "ECA": tabla con filtros estado/municipio/búsqueda, alta/edición.
  Pantalla "Importar ECA": subir archivo, **elegir/confirmar la columna identificador estable**,
  ver previsualización con errores por fila, confirmar/cancelar. Si el archivo no tiene columna
  identificador, la pantalla lo indica y **bloquea la confirmación**.
- **Offline.** N/A.
- **Permisos.** Lectura `ecas.ver`; edición `ecas.gestionar`; importación `ecas.importar`.
- **Pruebas unitarias.** Parser acepta CSV y XLSX; detecta `clave_fuente` duplicada en el
  archivo, municipio inexistente, campos requeridos vacíos; **upsert por `clave_fuente` actualiza
  sin duplicar**; **archivo sin columna identificador → la importación se rechaza entera** (no se
  inserta ninguna fila; **no** se deduplica por nombre/municipio).
- **Pruebas de integración.** Importar 5 000 filas de prueba → medir tiempo (objetivo < 30 s en el
  servidor de piloto); confirmar dos veces el mismo lote → idempotente (no duplica);
  importar de nuevo el mismo archivo → 0 altas, N actualizaciones;
  **importar un archivo SIN identificador estable → `422`, BD sin cambios**.
- **Pruebas manuales.** Cargar el archivo real (o una muestra representativa) que provea Jesús;
  revisar 10 ECA contra la fuente; probar el flujo cancelar; probar el rechazo por falta de
  identificador estable.
- **Criterios de aceptación.** 5 000 ECA importadas en tiempo aceptable **de forma síncrona**;
  **el upsert usa `clave_fuente` y reimportar el mismo archivo NO genera duplicados**
  (`count(DISTINCT clave_fuente)` = filas válidas del archivo);
  **una importación sin identificador estable se detiene y se escala (DP-2), sin insertar ni
  deduplicar por nombre/municipio**; los errores por fila se muestran antes de confirmar; ninguna
  ECA queda con estado/municipio inválido.
- **Pasos de despliegue (Jesús).**
  1. `alembic upgrade head` (`0006`).
  2. Entregar a Claude Code la **estructura real** del archivo de ECA (columnas y, sobre todo,
     **cuál columna es el identificador estable**: `ID_ECA`, folio, clave, …).
  3. **Si el archivo real NO trae ningún identificador estable**: NO cargar; escalar **DP-2** para
     decidir cómo obtener/generar uno (no se improvisa deduplicación por nombre/municipio).
  4. Cargar el archivo desde el panel con un usuario ADMIN **indicando la columna identificador**.
  5. Verificar `SELECT count(*) FROM ecas WHERE eliminado_en IS NULL;` y que
     `SELECT count(DISTINCT clave_fuente) FROM ecas` coincide con las filas válidas del archivo.
  6. **Si la importación síncrona supera ~60 s** en el servidor real: escalar el ticket a
     "importación por lotes en background" (ver Riesgos) antes del piloto.
- **Rollback.** `alembic downgrade -1`. Para deshacer una carga concreta:
  `DELETE FROM ecas WHERE lote_importacion_id = <id>` (o `activo=false`), documentado en el runbook.
- **Riesgos.**
  - **Rendimiento de la importación síncrona.** Mitigación: `COPY`/`execute_values` por bloques de
    500–1 000 filas dentro de una transacción; si aun así es lento, mover a un endpoint que
    procese en un hilo con estado consultable (sin colas). Decisión con datos reales, no a priori.
  - **El archivo institucional real no trae un identificador estable (DP-2).** Impacto: sin
    `clave_fuente` no hay upsert determinista y reimportar duplicaría. Mitigación: **detener la
    importación** y escalar; **no** implementar deduplicación automática por nombre/municipio;
    salidas posibles a decidir con la institución: pedir el archivo con la clave oficial, derivar
    una clave compuesta **estable y documentada**, o cargar una sola vez de forma controlada.
  - Archivo real con formato imprevisto → acordar plantilla con Jesús.
- **Complejidad.** **ALTA**.

---

### ECA-008 — Ámbitos geográficos técnico–municipio

- **Objetivo.** Tabla `ambitos_tecnico` (N municipios por técnico, con vigencia); endpoints;
  pantalla admin para asignar municipios de trabajo a un técnico (individual y por CSV).
- **Por qué se necesita.** `03` §6.4: mientras no exista relación completa técnico–ECA, el ámbito
  geográfico determina qué ECA ve el técnico.
- **Dependencias.** ECA-006, ECA-004.
- **Crear.**
  - `app/models/ambito.py`, `app/schemas/ambito.py`, `app/repositories/ambitos.py`.
  - `app/api/routers/ambitos.py`.
  - `alembic/versions/0007_ambitos.py`.
  - `admin-eca/src/views/AmbitosView.vue`, `ambitosService.js`.
  - `tests/test_ambitos.py`.
- **Modificar.** `app/main.py`; `admin-eca/src/router`.
- **Tablas.** `ambitos_tecnico` (según `05` §4.4).
- **Migraciones.** `0007`: estructura + `UNIQUE(usuario_id, municipio_id) WHERE activo` +
  `idx_amb_usuario` + `idx_amb_municipio` + FKs.
- **Endpoints.**
  - `GET /usuarios/{id}/ambito` → municipios activos del técnico.
  - `PUT /usuarios/{id}/ambito` → reemplaza el conjunto (da de baja los que faltan, alta los nuevos).
  - `POST /ambitos/importar` (CSV: correo_tecnico, clave_municipio).
- **Cambios PWA.** N/A (se entrega en bootstrap ECA-018).
- **Cambios panel admin.** En la ficha de usuario: selector de estados→municipios (multi) con
  guardado; opción de import masivo.
- **Offline.** N/A todavía.
- **Permisos.** `ambitos.gestionar` para editar; el técnico puede leer su propio ámbito
  (`GET /usuarios/me/ambito`).
- **Pruebas unitarias.** `PUT` calcula altas/bajas correctamente; no permite municipio inactivo;
  no duplica activos.
- **Pruebas de integración.** Asignar 3 municipios, quitar 1 → quedan 2 activos y 1 con `fecha_fin`.
- **Pruebas manuales.** Asignar ámbito a 5 técnicos de prueba en distintos estados.
- **Criterios de aceptación.** Un técnico puede tener N municipios; el histórico se conserva
  (bajas con `fecha_fin`); import valida correo y clave de municipio.
- **Pasos de despliegue (Jesús).** `alembic upgrade head` (`0007`). Cargar ámbitos de los
  técnicos del piloto (panel o CSV).
- **Rollback.** `alembic downgrade -1`.
- **Riesgos.** Un técnico con demasiados municipios en un estado denso → subconjunto de ECA
  offline muy grande (se aborda en ECA-018 con tope + aviso).
- **Complejidad.** **BAJA**.

---

### ECA-009 — Asignaciones directas técnico–ECA

- **Objetivo.** Tabla `asignaciones_tecnico_eca` (N:M con vigencia y origen); endpoints; pantalla
  admin para asignar ECA a un técnico (individual y por CSV).
- **Por qué se necesita.** `03` §6.5/§6.6: cuando exista la relación oficial, es la fuente
  primaria; independiente de grupos.
- **Dependencias.** ECA-007, ECA-004.
- **Crear.**
  - `app/models/asignacion_eca.py`, `app/schemas/asignacion_eca.py`,
    `app/repositories/asignaciones.py`.
  - `app/api/routers/asignaciones.py`.
  - `alembic/versions/0008_asignaciones_eca.py`.
  - `admin-eca/src/views/AsignacionesView.vue`, `asignacionesService.js`.
  - `tests/test_asignaciones.py`.
- **Modificar.** `app/main.py`; `admin-eca/src/router`.
- **Tablas.** `asignaciones_tecnico_eca` (según `05` §4.4).
- **Migraciones.** `0008`: estructura + `UNIQUE(uuid)` +
  `UNIQUE(usuario_id, eca_id) WHERE activo` + `idx_ate_usuario` + `idx_ate_eca` + FKs.
- **Endpoints.**
  - `GET /asignaciones?tecnico_id=` / `?eca_id=`.
  - `POST /asignaciones` (una), `DELETE /asignaciones/{id}` (baja lógica).
  - `POST /asignaciones/importar` (CSV: correo_tecnico, identificador de ECA — `clave_fuente` o
    `clave_institucional`).
  - `GET /usuarios/me/ecas` → **resuelve la REGLA DE ECA** (ver abajo) y devuelve el conjunto
    relevante para el técnico autenticado.
- **REGLA DE ECA (implementada aquí, consumida por PWA y bootstrap).**

  ```
  si existe asignación activa en asignaciones_tecnico_eca para el técnico:
      conjunto = esas ECA
  si no:
      conjunto = ECA activas cuyo municipio_id ∈ municipios del ámbito activo del técnico
  ```

  El comportamiento se controla con `parametros_config.eca.regla_disponibilidad`
  (`ASIGNADAS_LUEGO_AMBITO` por defecto; alternativas `SOLO_ASIGNADAS`, `SOLO_AMBITO`).
- **Cambios PWA.** N/A directo (consume `GET /usuarios/me/ecas` vía bootstrap).
- **Cambios panel admin.** En la ficha de usuario: buscador de ECA (por clave/nombre/municipio) y
  lista de asignadas; alta/baja; import masivo.
- **Offline.** N/A todavía.
- **Permisos.** `asignaciones.gestionar` para editar; el técnico lee lo suyo (`/usuarios/me/ecas`).
- **Pruebas unitarias.** La regla devuelve las asignadas si existen; si no, las del ámbito;
  respeta `regla_disponibilidad`; no duplica asignaciones activas.
- **Pruebas de integración.** Técnico sin asignaciones + ámbito con 2 municipios → ve las ECA de
  esos municipios; se le asigna 1 ECA directa → ahora ve solo esa.
- **Pruebas manuales.** Configurar 3 técnicos: uno con asignaciones, uno solo con ámbito, uno sin
  nada (debe ver lista vacía y un mensaje claro).
- **Criterios de aceptación.** `GET /usuarios/me/ecas` implementa exactamente la regla; el cambio
  de `regla_disponibilidad` en `parametros_config` altera el resultado sin desplegar código.
- **Pasos de despliegue (Jesús).** `alembic upgrade head` (`0008`). Cargar asignaciones directas
  **si Jesús ya dispone de esa información**; si no, dejar solo ámbitos.
- **Rollback.** `alembic downgrade -1`.
- **Riesgos.** Regla mal entendida → técnicos ven ECA que no les tocan. Mitigar con las pruebas
  de integración de los 3 escenarios y validación de Jesús con datos reales.
- **Complejidad.** **MEDIA**.

---

### ECA-010 — Catálogos de actividad

- **Objetivo.** Tablas `modalidades`, `tipos_actividad`, `temas`, `subtemas`,
  `sistemas_productivos` con semilla (`03` §9–§12); endpoints de lectura; pantalla admin para
  activar/desactivar y editar etiquetas/orden.
- **Por qué se necesita.** `03` §12 y `02` §12: en SV las categorías están hardcodeadas y
  duplicadas. La actividad ECA se clasifica contra estos catálogos.
- **Dependencias.** ECA-004, ECA-005.
- **Crear.**
  - `app/models/catalogos.py`, `app/schemas/catalogos.py`, `app/repositories/catalogos.py`.
  - `app/api/routers/catalogos.py`.
  - `alembic/versions/0009_catalogos_actividad.py` + `0010_seed_catalogos.py`.
  - `admin-eca/src/views/CatalogosView.vue`, `catalogosService.js`.
  - `tests/test_catalogos.py`.
- **Modificar.** `app/main.py`; `admin-eca/src/router`.
- **Tablas.** `modalidades`, `tipos_actividad` (con `requiere_evidencia`, `min_fotos`, `max_fotos`,
  `permite_participantes`, `requiere_eca`), `temas`, `subtemas` (FK `tema_id`),
  `sistemas_productivos`. (`05` §4.7.)
- **Migraciones.** `0009` (estructura + `UNIQUE(clave)` por catálogo + `UNIQUE(tema_id, clave)` en
  subtemas), `0010` (semilla: 2 modalidades, 10 tipos, ~14 temas, subtemas iniciales de `03` §11,
  ~14 sistemas productivos).
- **Endpoints.**
  - `GET /catalogos/modalidades|tipos-actividad|temas|subtemas?tema_id=|sistemas-productivos`
    (por defecto solo `activo=true`; admin puede pedir todos).
  - `PATCH /catalogos/{tipo}/{id}` (permiso `catalogos.gestionar`): `activo`, `nombre`, `orden`, y
    para tipos: `requiere_evidencia`, `min_fotos`, `max_fotos`, `permite_participantes`,
    `requiere_eca`.
  - `POST /catalogos/subtemas` (alta de subtema sobre un tema existente).
- **Cambios PWA.** N/A (llega por bootstrap).
- **Cambios panel admin.** Pantalla "Catálogos" con pestañas por catálogo; edición inline de
  `activo`/`orden`/etiqueta; para tipos, edición de las banderas de evidencia/participantes/ECA.
- **Offline.** N/A todavía.
- **Permisos.** Lectura: autenticado. Edición: `catalogos.gestionar`.
- **Pruebas unitarias.** Semilla completa; `min_fotos ≤ max_fotos ≤ 3`; subtema exige tema
  existente; desactivar un tema no borra sus subtemas.
- **Pruebas de integración.** `GET /catalogos/subtemas?tema_id=` filtra; `PATCH` sin permiso → 403.
- **Pruebas manuales.** Desactivar el tipo "OTR" y ver que desaparece de la lista pública;
  cambiar `requiere_evidencia` de un tipo.
- **Criterios de aceptación.** Todos los catálogos de `03` §9–§12 sembrados; se pueden
  activar/desactivar sin desplegar; la obligatoriedad de foto es **por tipo**, nunca global.
- **Pasos de despliegue (Jesús).** `alembic upgrade head` (`0009`, `0010`). Revisar con el equipo
  funcional que la semilla de temas/subtemas/sistemas es la deseada para el piloto (se puede
  ajustar desde el panel).
- **Rollback.** `alembic downgrade` hasta antes de `0009`.
- **Riesgos.** Semilla de subtemas incompleta → el técnico no encuentra el subtema adecuado.
  Mitigar: el admin puede añadir subtemas en caliente; documentar ese flujo para el piloto.
- **Complejidad.** **MEDIA**.

> **★ HITO B — Administración de usuarios/ECA funcionando** (tras ECA-010).
> El administrador ya puede: crear/importar usuarios · administrar estados/municipios ·
> importar ~5 000 ECA · asignar municipios de trabajo · asignar ECA directas · administrar
> catálogos de actividad. (La "consulta de actividades registradas" se cierra en ECA-019.)

---

### ECA-011 — Estructura de la PWA ECA y autenticación del técnico

- **Objetivo.** App `pwa-eca` instalable: login, store `auth`, interceptor de refresh, guard de
  ruta, un solo service worker (Workbox), pantalla "Inicio" y "Perfil" (cambio de contraseña),
  detección de conectividad, y **sesión local offline** (§2.2): tras un login + bootstrap con red,
  la PWA conserva una marca que permite **seguir abriendo la app y navegando** aunque el
  `access_token` expire mientras no hay red.
- **Por qué se necesita.** Base de todo el trabajo de campo. `02` §2: no repetir el doble SW ni
  la "sesión" basada solo en `localStorage`. Además, un JWT de acceso corto **no debe impedir
  trabajar offline** cuando expira sin red (§2.2).
- **Dependencias.** ECA-003, ECA-004.
- **Crear.**
  - `pwa-eca/vite.config.js` (VitePWA, Workbox: `/api` → NetworkOnly, `navigateFallback`).
  - `pwa-eca/src/stores/auth.js`, `src/services/api.js` (axios + refresh), `src/services/conectividad.js`.
  - `pwa-eca/src/services/sesionLocal.js` (**sesión local offline**: identidad, permisos efectivos
    del último `/auth/me`, fecha de validación, validez configurable — **DP-1**).
  - `pwa-eca/src/router/index.js` (guard: **sesión de servidor válida _o_ sesión local offline
    vigente**).
  - `pwa-eca/src/views/LoginView.vue`, `InicioView.vue`, `PerfilView.vue`.
  - `pwa-eca/public/manifest.webmanifest`, iconos.
  - `pwa-eca/src/components/EstadoConexion.vue`.
- **Modificar.** N/A.
- **Tablas / migraciones / endpoints.** N/A (consume `auth`).
- **Cambios PWA.** Este ticket **es** la PWA base.
- **Cambios panel admin.** N/A.
- **Comportamiento offline.** El **app shell** se cachea (Workbox). **Primer ingreso**: requiere
  red (login + bootstrap). **Después**: con **sesión local offline vigente** (§2.2), la app abre
  sin red, permite navegar y —desde ECA-016— capturar; **el `access_token` expirado NO bloquea la
  captura**. Sin sesión local vigente (nunca hubo login+bootstrap) o **vencida su validez
  configurable (DP-1)**, la PWA pide reconexión para *volver a capturar*, pero **conserva**
  cualquier pendiente ya creado. La PWA nunca borra el outbox por expiración de sesión.
- **Permisos.** El técnico necesita rol `TECNICO` (o `ADMIN`) para entrar; la PWA valida que el
  usuario tenga `actividades.crear`. **Los permisos efectivos para trabajar offline son los del
  último `/auth/me`** guardado en la sesión local.
- **Pruebas unitarias.** Store `auth`: persistencia de token, expiración, refresh; guard permite
  con sesión de servidor **o** con sesión local vigente y bloquea sin ninguna;
  `sesionLocal`: marca válida habilita modo offline; **marca vencida (validez configurable)
  deshabilita nueva captura pero NO borra pendientes**.
- **Pruebas de integración.** N/A (front). Vitest sobre interceptor, guard y `sesionLocal`.
- **Pruebas manuales.** Instalar la PWA en Android; login; cerrar y reabrir (mantiene sesión);
  **login con red → modo avión → forzar expiración del `access_token` → la app sigue abriendo y
  navegando** (sin errores de sesión); refresh de token transparente al volver la red.
- **Criterios de aceptación.** Un solo service worker registrado; la PWA es instalable;
  sin sesión de servidor **ni** local no se entra; **un `access_token` expirado sin red NO cierra
  la sesión ni impide navegar/capturar**; la validez de la sesión offline es **configurable**
  (no un valor fijo en código, DP-1); `Lighthouse PWA` pasa checks básicos.
- **Pasos de despliegue (Jesús).**
  1. `npm run build` de `pwa-eca`.
  2. Publicar en `eca.<dominio>` con nginx (HTTPS obligatorio, `navigateFallback`).
  3. Configurar `VITE_API_URL`.
  4. Probar instalación en un dispositivo Android real.
- **Rollback.** Restaurar build anterior. **Nota:** un SW mal publicado puede quedar cacheado;
  incluir en el runbook cómo forzar actualización (`skipWaiting`, versión de cache).
- **Riesgos.** Service worker "pegajoso" (problema conocido en `02` §2). Mitigar con
  `registerType: 'autoUpdate'` + `UpdateNotification` + versión de cache explícita.
- **Complejidad.** **MEDIA**.

---

### ECA-012 — Jornada

- **Objetivo.** Tabla `jornadas`; endpoints de inicio/cierre/consulta; pantalla PWA para iniciar y
  terminar la jornada del día. **Sin foto ni descripción obligatorias. GPS opcional.**
- **Por qué se necesita.** `03` §7: la jornada es el marco temporal de las actividades.
- **Dependencias.** ECA-011, ECA-004.
- **Crear.**
  - `app/models/jornada.py`, `app/schemas/jornada.py`, `app/repositories/jornadas.py`,
    `app/services/jornadas_service.py`.
  - `app/api/routers/jornadas.py`.
  - `alembic/versions/0011_jornadas.py`.
  - `pwa-eca/src/stores/jornada.js`, `src/views/JornadaView.vue`, `src/services/jornadasService.js`.
  - `tests/test_jornadas.py`.
- **Modificar.** `app/main.py`; `pwa-eca/src/router`, navegación.
- **Tablas.** `jornadas` (versión MVP de `05` §4.8: `id`, `uuid`, `usuario_id`, `fecha`,
  `inicio_en`, `fin_en` nullable, `estado` (`ABIERTA`/`CERRADA`/`ANULADA`), lat/long/precision/
  estado_gps de inicio y fin **todos nullable**, `nota` nullable, BOF, BAE, `eliminado_en` nullable).
- **Migraciones.** `0011`: estructura + `UNIQUE(uuid)` +
  `UNIQUE(usuario_id, fecha) WHERE estado <> 'ANULADA' AND eliminado_en IS NULL` +
  `idx_jornadas_usuario_fecha`.
- **Endpoints.**
  - `POST /jornadas` `{uuid, inicio_en, gps?}` → crea la jornada del día (idempotente por `uuid`;
    si ya hay jornada abierta del día, la devuelve).
  - `PATCH /jornadas/{uuid}/cerrar` `{fin_en, gps?}`.
  - `GET /jornadas?fecha=` / `GET /jornadas/me/hoy`.
- **Cambios PWA.** Pantalla "Jornada": botón "Iniciar jornada" / "Terminar jornada", estado
  actual, hora de inicio. GPS se intenta capturar pero **no bloquea**.
- **Comportamiento offline.** La jornada se crea/cierra en el **outbox** (ECA-016). En el MVP,
  hasta que ECA-016 esté, este ticket funciona **online**; la integración offline se cierra en
  ECA-016. (Se implementa el store con esa forma desde ya.)
- **Permisos.** `jornadas.crear`, `jornadas.ver_propias`.
- **Pruebas unitarias.** No se pueden abrir dos jornadas activas el mismo día; cerrar una jornada
  ya cerrada es idempotente; `fin_en ≥ inicio_en`.
- **Pruebas de integración.** `POST /jornadas` dos veces con el mismo `uuid` → una sola fila;
  `POST` con `uuid` distinto el mismo día → 409 (o devuelve la existente, según diseño acordado).
- **Pruebas manuales.** Iniciar jornada sin dar permiso de GPS → funciona; terminar jornada;
  intentar iniciar otra el mismo día → mensaje claro.
- **Criterios de aceptación.** 1 jornada principal por técnico por fecha; sin foto ni descripción
  obligatorias; GPS opcional; idempotente por `uuid`.
- **Pasos de despliegue (Jesús).** `alembic upgrade head` (`0011`). Rebuild + publish PWA.
- **Rollback.** `alembic downgrade -1`.
- **Riesgos.** Definición de "fecha" de la jornada (zona horaria del técnico). Fijar: la deriva el
  servidor de `inicio_en` convertido a la zona configurada (`parametros_config` o constante MVP
  `America/Mexico_City`).
- **Complejidad.** **BAJA**.

---

### ECA-013 — Registro de actividad (online)

- **Objetivo.** Tabla `actividades`; endpoint de creación y de consulta; formulario PWA con
  selectores de modalidad, tipo, tema, subtema, sistema productivo, ECA, descripción y resultado.
  **Sin GPS ni fotos todavía** (llegan en ECA-014 y ECA-015).
- **Por qué se necesita.** `03` §8: la actividad es la unidad principal de evidencia del MVP.
- **Dependencias.** ECA-009 (regla de ECA), ECA-010 (catálogos), ECA-012 (jornada).
- **Crear.**
  - `app/models/actividad.py`, `app/schemas/actividad.py`, `app/repositories/actividades.py`,
    `app/services/actividades_service.py`.
  - `app/api/routers/actividades.py`.
  - `alembic/versions/0012_actividades.py`.
  - `pwa-eca/src/stores/actividad.js`, `src/views/NuevaActividadView.vue`,
    `src/components/SelectorEca.vue`, `src/services/actividadesService.js`,
    `src/services/catalogosCache.js`.
  - `tests/test_actividades.py`.
- **Modificar.** `app/main.py`; `pwa-eca/src/router`.
- **Tablas.** `actividades` (versión MVP de `05` §4.8: técnico, `jornada_id`, `eca_id` nullable,
  `modalidad_id`, `tipo_actividad_id`, `tema_id` nullable, `subtema_id` nullable,
  `sistema_productivo_id` nullable, `descripcion`, `resultado` nullable, `fecha_hora`,
  lat/long/precision/estado_gps nullable (se llenan en ECA-014), `num_participantes` nullable,
  `requiere_seguimiento` bool default false, `fecha_proximo_seguimiento` nullable,
  **BOF** (`uuid`, `dispositivo_id` nullable, `creado_en_dispositivo`,
  `recibido_en`/`sincronizado_en` nullable — marca del servidor al aceptar), **BAE**,
  `eliminado_en` nullable.
  **La tabla NO lleva estado de transmisión** — `PENDIENTE`/`SINCRONIZANDO`/`SINCRONIZADO`/`RECHAZADO`
  son estados **locales del outbox** (§2.3). El estado de **negocio** se limita a un enum
  **opcional** `estado ∈ {ACTIVA, ANULADA}` (por defecto `ACTIVA`), y **solo se añade si el
  negocio lo exige**. **Sin flujo de revisión.**)
- **Migraciones.** `0012`: estructura + `UNIQUE(uuid)` + índices
  (`idx_act_usuario_fecha`, `idx_act_jornada`, `idx_act_eca`, `idx_act_tipo`, `idx_act_tema`,
  `idx_act_sistema`) + FKs + CHECKs (`num_participantes >= 0`,
  `fecha_proximo_seguimiento IS NULL OR requiere_seguimiento`). **No** se crea columna de estado
  de transmisión.
- **Endpoints.**
  - `POST /actividades` `{uuid, jornada_uuid, eca_id?, modalidad_id, tipo_actividad_id, tema_id?,
    subtema_id?, sistema_productivo_id?, descripcion, resultado?, fecha_hora, num_participantes?,
    requiere_seguimiento?, fecha_proximo_seguimiento?}` → idempotente por `uuid`; resuelve
    `jornada_id` desde `jornada_uuid`; valida reglas de catálogo en backend
    (`requiere_eca`, `permite_participantes`, coherencia tema/subtema).
  - `GET /actividades?tecnico_id=&eca_id=&desde=&hasta=&page=` (admin: `actividades.ver_todas`).
  - `GET /actividades/me?desde=&hasta=&page=` (técnico: `actividades.ver_propias`).
  - `GET /actividades/{uuid}`.
- **Cambios PWA.** Pantalla "Nueva actividad": selectores encadenados (tema→subtema),
  `SelectorEca` con búsqueda/filtro por estado/municipio y **priorización de ECA asignadas**,
  descripción y resultado. Guarda vía `POST /actividades` (online en este ticket).
- **Comportamiento offline.** Se implementa el store con forma de outbox; la persistencia offline
  real llega en ECA-015/ECA-016. En este ticket: online.
- **Permisos.** `actividades.crear` (crear), `actividades.ver_propias` / `actividades.ver_todas`
  (consulta).
- **Pruebas unitarias.** `POST` con el mismo `uuid` no duplica; tipo con `requiere_eca=true` sin
  `eca_id` → 422; `subtema_id` de otro tema → 422; `num_participantes` en tipo que no lo permite → 422.
- **Pruebas de integración.** Crear jornada + actividad; consultar `/actividades/me` la devuelve;
  un técnico no puede ver actividades de otro (`ver_todas` requerido).
- **Pruebas manuales.** Registrar una actividad completa con red; verla en el historial (ECA-019);
  probar validaciones (quitar ECA en un tipo que la exige).
- **Criterios de aceptación.** La actividad se guarda con toda la clasificación; las validaciones
  de catálogo se aplican **en backend** (no solo en el formulario); idempotente por `uuid`;
  `usuario_id` se toma del token, nunca del cuerpo; **la tabla `actividades` no almacena estado
  de transmisión** (§2.3), solo `creado_en_dispositivo` + `recibido_en`.
- **Pasos de despliegue (Jesús).** `alembic upgrade head` (`0012`). Rebuild + publish PWA.
- **Rollback.** `alembic downgrade -1`.
- **Riesgos.** El `SelectorEca` sobre ~5 000 filas debe ser server-side (no cargar todo). Ya está
  cubierto por `GET /ecas` paginado + `GET /usuarios/me/ecas`.
- **Complejidad.** **ALTA**.

---

### ECA-014 — GPS y precisión

- **Objetivo.** Servicio de geolocalización en la PWA (multi-intento, **sin ubicación por
  defecto**); persistir `latitud`, `longitud`, `precision_gps_m`, `estado_gps`
  (`CON_GPS`/`GPS_IMPRECISO`/`SIN_GPS`) en la actividad (y opcionalmente en la jornada).
- **Por qué se necesita.** `03` §20 y `02` §13: la ubicación es evidencia; SV inventa coordenadas
  por defecto.
- **Dependencias.** ECA-013.
- **Crear.**
  - `pwa-eca/src/services/gps.js` (getCurrentPosition con reintentos y umbrales; devuelve
    `{lat, lon, accuracy}` o `{estado: 'SIN_GPS'}`).
  - `pwa-eca/src/components/CapturaGps.vue`.
  - `tests` front del servicio GPS (mock de `navigator.geolocation`).
- **Modificar.**
  - `app/schemas/actividad.py` (campos GPS), `app/services/actividades_service.py` (aceptar y
    validar par de coordenadas + `estado_gps`).
  - `alembic/versions/0013_actividad_gps.py` **solo si** `0012` no incluyó ya las columnas GPS
    (recomendado: incluirlas en `0012` y este ticket es solo backend de validación + PWA).
  - `pwa-eca/src/views/NuevaActividadView.vue` (integra `CapturaGps`).
  - `app/api/routers/actividades.py` (validación).
- **Tablas.** `actividades` (columnas GPS; ya creadas en `0012`).
- **Migraciones.** Ninguna nueva si `0012` incluyó las columnas (preferido). Si no: `0013`
  aditiva.
- **Endpoints.** Sin nuevos; `POST /actividades` acepta y valida GPS.
- **Cambios PWA.** Al abrir "Nueva actividad" se intenta capturar GPS; el usuario ve la precisión
  y un estado ("buena / imprecisa / sin señal"). Si `SIN_GPS`, la actividad se puede guardar con
  `estado_gps = 'SIN_GPS'` (nunca coordenadas falsas). El umbral de "precisión válida" viene de
  `parametros_config.gps.precision_valida_maxima_m`.
- **Comportamiento offline.** El GPS del dispositivo funciona sin red; la captura no depende de
  internet.
- **Permisos.** N/A (parte de `actividades.crear`).
- **Pruebas unitarias.** `gps.js` devuelve `SIN_GPS` si el usuario niega permiso o hay timeout;
  clasifica `GPS_IMPRECISO` sobre el umbral; backend rechaza `estado_gps='CON_GPS'` sin coordenadas.
- **Pruebas de integración.** `POST /actividades` con lat sin lon → 422; con `SIN_GPS` y sin
  coordenadas → 200.
- **Pruebas manuales.** Registrar actividad con GPS bueno (exterior), con GPS malo (interior), y
  negando permiso; verificar los tres `estado_gps` en BD.
- **Criterios de aceptación.** Nunca se guardan coordenadas por defecto; `precision_gps_m` se
  persiste; `estado_gps` refleja la realidad; el CHECK de coherencia funciona.
- **Pasos de despliegue (Jesús).** Rebuild + publish PWA. (`alembic upgrade head` solo si hubo
  `0013`.)
- **Rollback.** Revertir build de PWA; `alembic downgrade -1` si aplicó `0013`.
- **Riesgos.** Comportamiento dispar de `geolocation` entre navegadores Android antiguos.
  Mitigar con timeouts generosos y mensajes claros; documentar dispositivos soportados para el
  piloto.
- **Complejidad.** **MEDIA**.

---

### ECA-015 — Evidencias fotográficas

- **Objetivo.** Tabla `actividades_evidencias`; capa `Storage` local; endpoint de subida
  (multipart) y de descarga autenticada; compresión en cliente; 1–3 fotos por actividad según
  `tipos_actividad`. **SHA-256 solo para idempotencia/integridad. Sin pHash.**
- **Por qué se necesita.** `03` §8: evidencia real por actividad; `02` §14: SV expone fotos
  públicas y genera placeholders.
- **Dependencias.** ECA-013, ECA-014.
- **Crear.**
  - `app/models/evidencia.py`, `app/schemas/evidencia.py`, `app/repositories/evidencias.py`,
    `app/services/evidencias_service.py`.
  - `app/core/storage.py` (`Storage` interface + `LocalStorage`).
  - `app/api/routers/evidencias.py`.
  - `alembic/versions/0014_evidencias.py`.
  - `pwa-eca/src/services/imagen.js` (compresión: reutiliza el enfoque de
    `pwasuper/src/utils/imageCompressor.js`, adaptado — **copiar, no importar**).
  - `pwa-eca/src/components/CapturaEvidencia.vue`.
  - `tests/test_evidencias.py`.
- **Modificar.** `app/main.py`; `pwa-eca/src/views/NuevaActividadView.vue`;
  `pwa-eca/vite.config.js` (nada especial); `app/services/actividades_service.py` (regla de
  `min_fotos`: la PWA la valida **antes de encolar** la actividad en el outbox, y el backend la
  **re-valida al recibir** la actividad y sus evidencias por `POST /sync/push` /
  `POST /actividades/{uuid}/evidencias` si `requiere_evidencia`. **No** se usa un cambio de estado
  `BORRADOR→SINCRONIZADA` para disparar la validación).
- **Tablas.** `actividades_evidencias` (versión MVP de `05` §4.8: `id`, `uuid`, `actividad_id`,
  `orden`, `storage_clave`, `nombre_archivo`, `mime`, `tamano_bytes`, `hash_sha256`,
  lat/long nullable, `capturada_en` nullable, `sincronizado_en` nullable, `creado_en`.
  **Sin** `hash_perceptual`).
- **Migraciones.** `0014`: estructura + `UNIQUE(uuid)` + `UNIQUE(actividad_id, orden)` +
  `idx_ev_actividad` + `idx_ev_sha (hash_sha256)` + CHECK `orden BETWEEN 1 AND 3`.
- **Endpoints.**
  - `POST /actividades/{actividad_uuid}/evidencias` (multipart: `orden`, `archivo`, `gps?`,
    `capturada_en?`, `uuid`) → guarda en `Storage`, calcula SHA-256; si ya existe una evidencia
    con ese `uuid` **o** con ese `(actividad_id, hash_sha256)` → responde la existente (idempotente).
  - `GET /evidencias/{id}` → **descarga autenticada** (verifica permiso; devuelve el binario o un
    302 a URL firmada local de expiración corta). **Nunca estático público.**
  - `DELETE /evidencias/{id}` (admin, auditado).
- **Cambios PWA.** En "Nueva actividad": añadir 1–3 fotos (cámara o galería), previsualización,
  compresión antes de subir/guardar; el mínimo exigido depende del tipo de actividad.
- **Comportamiento offline.** En este ticket: subida **online** tras crear la actividad. La
  persistencia offline de los `Blob` y su subida diferida se cierra en ECA-016/ECA-017.
- **Permisos.** Subir: `actividades.crear` sobre actividad propia. Ver: `actividades.ver_propias`
  (propias) o `actividades.ver_todas`. Borrar: `actividades.ver_todas` + permiso de gestión.
- **Pruebas unitarias.** `LocalStorage` guarda y recupera; SHA-256 estable; subir el mismo archivo
  dos veces al mismo `orden` no duplica; rechazo de `mime` no permitido y de tamaño excesivo;
  no se permite `orden` 4.
- **Pruebas de integración.** Crear actividad + 2 evidencias; `GET /evidencias/{id}` sin token →
  401; con token de otro técnico sin `ver_todas` → 403.
- **Pruebas manuales.** Subir 3 fotos desde un móvil; verificar tamaño tras compresión (<~500 KB);
  descargar desde el panel.
- **Criterios de aceptación.** 1–3 fotos por actividad según el tipo; **sin placeholders**;
  archivos **no** accesibles sin autenticación; reintento de subida idempotente; SHA-256
  registrado.
- **Pasos de despliegue (Jesús).**
  1. `alembic upgrade head` (`0014`).
  2. Crear el directorio `STORAGE_DIR` (fuera del webroot, con permisos del usuario del servicio)
     y su política de respaldo.
  3. Verificar que nginx **no** sirve `STORAGE_DIR` como estático.
  4. Rebuild + publish PWA.
- **Rollback.** `alembic downgrade -1`. Los archivos en `STORAGE_DIR` quedan huérfanos; limpieza
  manual documentada.
- **Riesgos.** Espacio en disco del servidor con miles de fotos/día (estimar con Jesús;
  ~300 KB × 10 fotos × 1 200 técnicos/día ≈ 3,4 GB/día → **plan de respaldo y rotación desde el
  piloto**, y S3 como siguiente paso si el piloto lo confirma).
- **Complejidad.** **ALTA**.

> **★ HITO C — Actividad online funcionando** (tras ECA-015).
> Un técnico con red: inicia sesión → ve sus ECA → inicia jornada → registra actividad
> clasificada con descripción/resultado + GPS/precisión + 1–3 fotos.

---

### ECA-016 — IndexedDB y outbox offline

- **Objetivo.** Esquema IndexedDB versionado en la PWA; **outbox** para jornadas, actividades y
  evidencias; escritura *write-through* (la UI escribe primero local); fotos como `Blob`;
  contador de pendientes; pantalla "Sincronización".
- **Por qué se necesita.** `03` §19 y `02` §15: trabajar sin conexión; corregir el uso de base64
  y la falta de versionado del store en SV.
- **Dependencias.** ECA-012, ECA-013, ECA-015.
- **Crear.**
  - `pwa-eca/src/services/db.js` (`idb`: stores `outbox_jornadas`, `outbox_actividades`,
    `outbox_evidencias`, `catalogos`, `ecas`, `meta`; `onupgradeneeded` con versión).
  - `pwa-eca/src/services/outbox.js` (encolar, listar, marcar estado, purgar).
  - `pwa-eca/src/stores/outbox.js`.
  - `pwa-eca/src/views/SincronizacionView.vue`, `src/components/BadgePendientes.vue`.
  - `tests` front de `outbox` (Vitest + fake-indexeddb).
- **Modificar.** `pwa-eca/src/stores/jornada.js`, `stores/actividad.js`, y los componentes de
  captura → escriben en el outbox en vez de llamar al API directamente.
- **Tablas.** N/A (cambios solo en cliente). Las columnas `sincronizado_en` ya existen en backend.
- **Migraciones.** N/A.
- **Endpoints.** N/A (se usan en ECA-017).
- **Cambios PWA.** Toda creación de jornada/actividad/evidencia pasa por el outbox con
  `uuid` de cliente, **`estado_local ∈ {PENDIENTE, SINCRONIZANDO, SINCRONIZADO, RECHAZADO}`**,
  `intentos`, `ultimo_error`. Este **`estado_local` es exclusivamente del dispositivo** (§2.3):
  **no** se envía al servidor ni se guarda como estado de negocio. La UI muestra el objeto
  inmediatamente. Fotos guardadas como `Blob`.
- **Comportamiento offline.** **Este es el ticket del offline de escritura.** Crear una actividad
  completa sin red deja 1 registro en `outbox_actividades` + N en `outbox_evidencias`, todos
  `PENDIENTE`. **La captura funciona con sesión local offline vigente (§2.2) aunque el
  `access_token` haya expirado**: no se exige token válido para escribir en el outbox.
- **Permisos.** N/A (cliente). Para *encolar* basta la **sesión local offline** vigente (§2.2).
- **Pruebas unitarias.** `outbox.encolar` persiste; `onupgradeneeded` migra de v1 a v2 sin perder
  datos; purga elimina solo `SINCRONIZADO` con antigüedad > `dias_retencion`; encolar funciona
  sin `access_token` vigente si la sesión local lo está.
- **Pruebas de integración.** N/A (front). Vitest: simular 10 actividades encoladas y su listado.
- **Pruebas manuales.** Modo avión: crear jornada + 2 actividades con fotos; cerrar la app;
  reabrir → los pendientes siguen ahí con su contador.
  **Escenario de sesión offline:** login con red → bootstrap → modo avión → provocar expiración
  del `access_token` → seguir creando jornada/actividades/GPS/fotos → todo queda `PENDIENTE`
  **sin errores de sesión**.
- **Criterios de aceptación.** Nada se pierde al cerrar la app sin red; fotos como `Blob` (no
  base64); el esquema IndexedDB tiene versión y migración; el contador de pendientes es correcto;
  **el `estado_local` del outbox nunca se confunde con un estado de la tabla `actividades`**;
  **capturar no requiere `access_token` vigente si la sesión local (§2.2) lo está**.
- **Pasos de despliegue (Jesús).** Rebuild + publish PWA. Nada en BD.
- **Rollback.** Restaurar build anterior. **Cuidado:** un downgrade de esquema IndexedDB puede
  requerir limpiar datos locales en los dispositivos de prueba (documentar).
- **Riesgos.** Cuota de almacenamiento del navegador con muchas fotos pendientes. Mitigar:
  comprimir antes de encolar; avisar al técnico si hay demasiados pendientes sin sincronizar.
- **Complejidad.** **ALTA**.

---

### ECA-017 — Sincronización idempotente (push)

- **Objetivo.** Motor de sincronización que envía el outbox al backend en lotes, **sin
  duplicar**, con reintentos y backoff; endpoints `POST /sync/push` (jornadas+actividades) y la
  subida de evidencias; manejo de conflictos simple (actividad inmutable tras sincronizarse).
  **La sincronización exige recuperar una sesión de servidor válida (`refresh`/`login`); la
  captura offline no** (§2.2).
- **Por qué se necesita.** `03` §19 y `AGENTS.md` 10: reintentos que no dupliquen; `02` §15: SV
  deduce duplicados por el texto del error (frágil).
- **Dependencias.** ECA-016.
- **Crear.**
  - `app/api/routers/sync.py`, `app/services/sync_service.py`.
  - `app/models/dispositivo.py` (registro de dispositivo en el primer sync).
  - `alembic/versions/0015_dispositivos.py`.
  - `pwa-eca/src/services/sync.js` (bucle de envío, backoff+jitter, límites de intentos).
  - `tests/test_sync.py`.
- **Modificar.** `pwa-eca/src/stores/outbox.js` (transiciones de estado), `SincronizacionView.vue`
  (botón "Sincronizar ahora", progreso); `pwa-eca/src/services/conectividad.js` (dispara sync al
  recuperar red).
- **Tablas.** `dispositivos`. Las entidades ya tienen `uuid UNIQUE` y `sincronizado_en`.
- **Migraciones.** `0015`: `dispositivos` + `UNIQUE(uuid)` + `idx_disp_usuario`.
- **Endpoints.**
  - `POST /sync/dispositivo` `{uuid, plataforma, user_agent}` → alta/actualización idempotente.
  - `POST /sync/push` `{dispositivo_uuid, jornadas:[...], actividades:[...]}` → **requiere sesión
    de servidor válida** (`access_token` vigente; si expiró, la PWA hace `refresh`/`login` antes
    — §2.2). Por cada objeto: si el `uuid` ya existe → devuelve el existente
    (`resultado: 'DUPLICADO'`); si no → lo crea, **fija `recibido_en`**, valida reglas de negocio;
    responde `{resultados:[{uuid, resultado, id?, error?}]}` con
    `resultado ∈ {APLICADO, DUPLICADO, RECHAZADO}` — **resultado de transmisión, NO estado de
    negocio** (§2.3). **Nunca 500 por un objeto malo**: ese objeto vuelve como `RECHAZADO` con
    motivo, el resto se procesa.
  - Evidencias: se suben con el endpoint de ECA-015 (`POST /actividades/{uuid}/evidencias`), que
    ya es idempotente; el motor de sync las envía **después** de confirmar su actividad.
- **Cambios PWA.** `sync.js`: **antes de enviar**, asegura sesión de servidor válida
  (`refresh`; si falla y hay red, pide `login`); si no se logra, **deja el outbox intacto** y
  avisa "reconéctate para sincronizar". Luego procesa `outbox_jornadas` → `outbox_actividades` →
  `outbox_evidencias` en orden; marca el **`estado_local`** `SINCRONIZADO` o `RECHAZADO`; los
  `RECHAZADO` se muestran al técnico para corrección (no se reintentan solos); reintenta los
  errores de red con backoff.
- **Comportamiento offline.** El motor solo actúa con red **y** con sesión de servidor válida.
  Sin red (o sin poder refrescar la sesión), el outbox se acumula **sin pérdida**. Al volver la
  red (evento `online` + verificación real contra `/health`) y recuperar sesión, sincroniza.
- **Permisos.** `sync.usar`. El backend valida que cada objeto pertenezca al técnico autenticado.
  Sincronizar exige `access_token` vigente (recuperable con `refresh`/`login`).
- **Pruebas unitarias.** `POST /sync/push` con el mismo lote dos veces → 0 duplicados;
  un objeto con `tipo_actividad` inexistente → `RECHAZADO`, los demás `APLICADO`;
  jornada referida por `jornada_uuid` inexistente → la actividad queda `RECHAZADO` con motivo claro.
- **Pruebas de integración.** Crear offline 1 jornada + 3 actividades + 6 fotos; conectar;
  sincronizar; verificar en BD: 1 jornada, 3 actividades, 6 evidencias, todo con `recibido_en`.
  Repetir la sincronización → sin cambios. Cortar la red a mitad → reanudar → completa sin duplicar.
  **Escenario completo de sesión offline:** login con red → pérdida de red → **expira el
  `access_token`** → se siguen creando actividades (quedan `PENDIENTE`) → vuelve la conexión →
  `refresh`/`login` recupera la sesión de servidor → `sync/push` envía todo **sin pérdida ni
  duplicados** (repetir el push → 0 cambios).
- **Pruebas manuales.** Escenario de campo simulado: modo avión 30 min, varias actividades,
  recuperar señal intermitente; comprobar que el historial del panel coincide exactamente.
- **Criterios de aceptación.** Reenviar el mismo objeto **nunca** crea un duplicado (garantía por
  `UNIQUE(uuid)`); un objeto inválido no bloquea el lote; los `RECHAZADO` son visibles y
  accionables; no se interpreta ningún texto de error para deducir duplicados;
  **sincronizar exige sesión de servidor válida**; un `access_token` expirado **no** causa
  pérdida de pendientes; el `resultado` de `/sync/push` es de **transmisión** y **no** se guarda
  como estado de la tabla `actividades`.
- **Pasos de despliegue (Jesús).** `alembic upgrade head` (`0015`). Rebuild + publish PWA.
- **Rollback.** `alembic downgrade -1`. Revertir build de PWA.
- **Riesgos.** Orden de dependencias (evidencia antes que su actividad) → el motor debe respetar
  el orden y no marcar evidencia `SINCRONIZADO` si su actividad falló.
- **Complejidad.** **ALTA**.

---

### ECA-018 — Bootstrap y delta offline de catálogos/ECA (pull)

- **Objetivo.** Endpoint `GET /sync/bootstrap` que entrega al técnico su **subconjunto
  relevante**: catálogos de actividad, estados/municipios necesarios, su ámbito, y sus ECA según
  la **REGLA DE ECA**; `GET /sync/pull?desde=` para deltas. La PWA guarda todo en IndexedDB y lo
  usa offline.
- **Por qué se necesita.** `03` §6.8: **no** descargar las ~5 000 ECA a cada dispositivo; solo el
  subconjunto del técnico, disponible offline.
- **Dependencias.** ECA-009 (regla de ECA), ECA-010 (catálogos), ECA-016 (IndexedDB).
- **Crear.**
  - `app/api/routers/sync.py` (añadir `bootstrap` y `pull`), `app/services/bootstrap_service.py`.
  - `pwa-eca/src/services/bootstrap.js`, `src/stores/catalogos.js`, `src/stores/ecas.js`.
  - `tests/test_bootstrap.py`.
- **Modificar.** `pwa-eca/src/services/sync.js` (llamar a `bootstrap` en el primer login y `pull`
  periódicamente); `SelectorEca.vue` (leer de IndexedDB cuando no hay red);
  `NuevaActividadView.vue` (catálogos desde store local).
- **Tablas.** Solo lectura de `ecas`, `estados`, `municipios`, `ambitos_tecnico`,
  `asignaciones_tecnico_eca`, catálogos.
- **Migraciones.** N/A (opcional: `idx` de `actualizado_en` en `ecas` para deltas eficientes —
  añadir en `0006`/`0016` aditiva).
- **Endpoints.**
  - `GET /sync/bootstrap` → `{ generado_en, catalogos:{...}, geo:{estados:[...], municipios:[...]},
    ambito:[...], ecas:[...],
    config:{regla_disponibilidad, gps_precision_maxima, eca_max_offline, sesion_offline_dias, ...} }`.
    `sesion_offline_dias` = validez de la **sesión local offline** (§2.2, **DP-1**); la PWA la usa
    para su marca de sesión local. `ecas` se resuelve con la REGLA DE ECA; `municipios` incluye
    solo los del ámbito + los de las ECA entregadas; `estados` los correspondientes.
  - `GET /sync/pull?desde=<iso8601>` → cambios en ese subconjunto desde `desde`
    (ECA nuevas/modificadas/desactivadas, cambios de ámbito/asignación, catálogos).
- **Cambios PWA.** Tras el primer login con red: `bootstrap` puebla IndexedDB. Después, `pull`
  incremental al sincronizar. `SelectorEca` y los catálogos funcionan **100 % offline** con esos
  datos. Indicador de "última actualización de datos".
- **Comportamiento offline.** Este ticket **es** el offline de lectura. Sin red, el técnico ve sus
  ECA y catálogos desde IndexedDB.
- **Permisos.** `sync.usar` + `ecas.ver` + `catalogos.ver`.
- **Pruebas unitarias.** `bootstrap_service` aplica la REGLA DE ECA (asignadas → si no, ámbito);
  respeta `regla_disponibilidad`; `pull` no devuelve nada si no hubo cambios; una ECA desactivada
  aparece en el delta como baja.
- **Pruebas de integración.** Técnico con ámbito de 2 municipios (p. ej. 400 ECA) → `bootstrap`
  entrega ~400 ECA, no 5 000. Añadir 1 asignación directa → siguiente `pull` cambia el conjunto a
  1 ECA. Cambiar `regla_disponibilidad` a `SOLO_AMBITO` → `bootstrap` ignora las asignaciones.
- **Pruebas manuales.** Login, esperar bootstrap, modo avión, crear actividad eligiendo una ECA de
  la lista offline; verificar que el tamaño descargado es razonable (revisar en DevTools).
- **Criterios de aceptación.** En ningún caso se descargan las ~5 000 ECA completas; el
  subconjunto respeta la REGLA DE ECA y `parametros_config`; los catálogos y las ECA relevantes
  están disponibles sin conexión; el delta funciona.
- **Pasos de despliegue (Jesús).** `alembic upgrade head` si hubo índice nuevo. Rebuild + publish
  PWA. Verificar con un técnico real el tamaño y tiempo del bootstrap.
- **Rollback.** Revertir build de PWA; el endpoint puede quedar (no rompe nada).
- **Riesgos.**
  - Técnico con ámbito enorme → subconjunto grande. Mitigación: **tope configurable**
    (`parametros_config.eca.max_offline`, p. ej. 1 500); si se supera, el `bootstrap` responde
    con aviso y pide al admin acotar el ámbito o cargar asignaciones directas.
  - Deltas mal calculados → datos obsoletos offline. Mitigar con `generado_en` y prueba de delta.
- **Complejidad.** **ALTA**.

> **★ HITO D — Actividad offline + sincronización funcionando** (tras ECA-018).

---

### ECA-019 — Historial de actividades (PWA + consulta admin)

- **Objetivo.** Pantalla "Historial" en la PWA (actividades propias, local + servidor, con un
  **indicador de sincronización derivado del outbox local** — §2.3: "sin sincronizar" = está en el
  outbox; "sincronizada" = existe en el servidor con `recibido_en`) y pantalla "Actividades" en
  el panel admin (consulta con filtros y detalle con evidencias).
- **Por qué se necesita.** Cierra el punto 12 del técnico y el punto 7 del administrador del MVP.
- **Dependencias.** ECA-013, ECA-015, ECA-016 (PWA); ECA-013, ECA-015 (admin).
- **Crear.**
  - `pwa-eca/src/views/HistorialView.vue`, `src/components/ActividadCard.vue`.
  - `admin-eca/src/views/ActividadesView.vue`, `src/views/ActividadDetalleView.vue`,
    `admin-eca/src/services/actividadesService.js`.
  - `tests` de la consulta admin.
- **Modificar.** `app/api/routers/actividades.py` (asegurar filtros: `tecnico_id`, `eca_id`,
  `municipio_id` vía join, `tipo_actividad_id`, `tema_id`, `desde`, `hasta`, `estado_gps`,
  paginación); `pwa-eca/src/router`, `admin-eca/src/router`.
- **Tablas.** Solo lectura de `actividades`, `actividades_evidencias`, catálogos, `ecas`, `usuarios`.
- **Migraciones.** Ninguna (los índices ya están en `0012`). Añadir `idx_act_estado_gps` si los
  filtros lo justifican (aditiva).
- **Endpoints.**
  - `GET /actividades/me?...` (PWA — técnico).
  - `GET /actividades?...` (admin — `actividades.ver_todas`) con los filtros anteriores.
  - `GET /actividades/{uuid}` (detalle + lista de evidencias con enlaces autenticados).
- **Cambios PWA.** Lista combinada: pendientes del outbox (badge "sin sincronizar" **derivado del
  `estado_local` del outbox, no de la BD**) + las del servidor; filtro por fecha; tap → detalle
  con fotos.
- **Cambios panel admin.** Tabla de actividades con filtros (técnico, ECA, municipio, tipo, tema,
  fechas, estado GPS); exportar a CSV (simple, síncrono); detalle con mapa opcional y galería de
  evidencias (descarga autenticada). **El panel NO filtra por "estado de sincronización"** (no
  existe en la BD, §2.3); ofrece rangos por `creado_en_dispositivo` y por `recibido_en`.
- **Comportamiento offline.** La PWA muestra el historial local sin red; al sincronizar se
  reconcilia con el servidor (por `uuid`).
- **Permisos.** `actividades.ver_propias` (PWA); `actividades.ver_todas` (panel).
- **Pruebas unitarias.** Filtros del endpoint admin combinan con `AND`; paginación correcta;
  un técnico sin `ver_todas` no puede usar `GET /actividades`.
- **Pruebas de integración.** Crear 5 actividades (3 sincronizadas, 2 en outbox) → la PWA muestra
  5 con el estado correcto; el panel muestra 3.
- **Pruebas manuales.** Revisar el historial en la PWA tras un día de uso offline+online;
  en el panel, filtrar por técnico y por ECA; abrir el detalle y ver las fotos.
- **Criterios de aceptación.** El técnico ve todas sus actividades (locales y remotas) con estado
  claro; **el indicador "sin sincronizar" se calcula del outbox local, no de una columna de la
  BD** (§2.3); el admin consulta y filtra las de todos y **no** ve ni almacena estado de
  transmisión; las fotos solo se ven autenticado; exportación CSV funciona.
- **Pasos de despliegue (Jesús).** Rebuild + publish PWA y panel. (`alembic upgrade head` solo si
  hubo índice nuevo.)
- **Rollback.** Restaurar builds anteriores.
- **Riesgos.** Consulta admin lenta si no se apoya en índices/paginación → verificado por diseño.
- **Complejidad.** **MEDIA**.

---

### ECA-020 — Endurecimiento, observabilidad y datos de piloto

- **Objetivo.** Cerrar los cabos de seguridad y operación antes del piloto: rate limiting,
  cabeceras de seguridad, política de contraseñas, revisión de permisos endpoint por endpoint,
  `GET /health` extendido, logs revisados (sin datos sensibles), backup de BD y de `STORAGE_DIR`,
  script de carga de datos de piloto, runbook, y **revisión de la sesión local offline** (§2.2):
  que un `access_token` expirado sin red **no** bloquee la captura y que la **validez offline
  configurable (DP-1)** funcione tal como se espera.
- **Por qué se necesita.** `AGENTS.md` Fase A ("corrección prioritaria de seguridad crítica",
  "pruebas smoke") y `02` §20. El piloto no puede salir sin esto.
- **Dependencias.** ECA-018, ECA-019.
- **Crear.**
  - `app/core/ratelimit.py` (login/refresh/sync), `app/core/security_headers.py`.
  - `backend-eca/scripts/seed_piloto.py` (usuarios de piloto, ámbitos, asignaciones de prueba).
  - `backend-eca/RUNBOOK.md` (despliegue, migraciones, rollback, backup, incidentes).
  - `backend-eca/tests/test_smoke.py` (recorre los flujos MVP end-to-end).
- **Modificar.** `app/main.py` (middlewares de seguridad); routers (auditoría de revisión de
  permisos: un test que falle si un router no declara permiso); `nginx` (cabeceras, HSTS, límites
  de tamaño de subida); semilla de `parametros_config` (**valores iniciales de trabajo** para
  `REFRESH_TOKEN_DIAS` / `OFFLINE_SESSION_DIAS` — **DP-1**, revisables con la institución);
  `pwa-eca/src/services/sesionLocal.js` + `sync.js` (revisión del flujo servidor↔offline).
- **Tablas.** N/A (posible `idx` faltante detectado en revisión → migración aditiva).
- **Migraciones.** Solo si la revisión detecta índices faltantes.
- **Endpoints.** `GET /health` extendido (`db`, `storage`, `migracion_actual`); ningún endpoint
  nuevo de negocio.
- **Cambios PWA.** Revisión: manejo de **sesión de servidor** expirada (refresh silencioso; si
  falla y **hay** red, pedir login; si **no** hay red, **mantener modo offline con la sesión
  local** y permitir seguir capturando — §2.2); mensajes claros de "reconéctate para sincronizar";
  pantalla de "app desactualizada" (nueva versión de SW).
- **Cambios panel admin.** Revisión análoga; pantalla de "estado del sistema" mínima (versión,
  conteos).
- **Comportamiento offline.** Verificación de que la app abre offline con sesión previa y que los
  pendientes sobreviven a cierres/actualizaciones.
- **Permisos.** Auditoría completa: **todo** endpoint de datos tiene `require_permission`;
  documentar la matriz permiso↔endpoint.
- **Pruebas unitarias.** Rate limiting bloquea tras N intentos; cabeceras presentes; política de
  contraseña rechaza débiles.
- **Pruebas de integración.** `test_smoke.py`: alta de técnico → login → bootstrap → jornada →
  actividad + foto offline → sync → aparece en el panel. Debe pasar en CI local antes del piloto.
  **Escenario de sesión offline:** login con red → pérdida de red → **expira el `access_token`** →
  continúa la captura de jornada/actividad/GPS/evidencia → vuelve la conexión → `refresh`/`login`
  recupera la sesión de servidor → sincroniza **sin pérdida ni duplicados**.
- **Pruebas manuales.** Checklist de seguridad (ver §9); prueba de restauración de backup en un
  entorno aparte; prueba del escenario de sesión offline en un dispositivo real.
- **Criterios de aceptación.** `test_smoke` verde; matriz de permisos completa y revisada;
  backups automáticos configurados y **probada una restauración**; runbook escrito; sin `/debug/*`
  ni endpoints de volcado sin auth; `SECRET_KEY` fuerte y fuera del repo;
  **el escenario de sesión offline (login → sin red → token expirado → captura → reconexión →
  sync) pasa sin pérdida ni duplicados**; la validez de la sesión offline y la vida del
  `refresh_token` son **configurables (DP-1)**, no constantes en código.
- **Pasos de despliegue (Jesús).**
  1. Aplicar cambios de nginx (cabeceras, HSTS, `client_max_body_size` acorde a 3 fotos).
  2. Configurar backup automático de `eca_db` (p. ej. `pg_dump` diario) y de `STORAGE_DIR`.
  3. **Ejecutar y verificar una restauración de backup** en un entorno de prueba.
  4. Definir en `.env` / `parametros_config` los **valores iniciales de trabajo** de
     `REFRESH_TOKEN_DIAS` y `OFFLINE_SESSION_DIAS` (**DP-1**) — a revisar con la institución.
  5. `python scripts/seed_piloto.py` con la lista real de técnicos del piloto.
  6. Correr `test_smoke` contra el entorno de piloto (incluye el escenario de sesión offline).
- **Rollback.** Revertir cambios de nginx y build; la configuración de backup no necesita
  rollback.
- **Riesgos.** Descubrir en esta fase un endpoint sin permiso o un dato sensible en logs →
  arreglarlo aquí, no en el piloto.
- **Complejidad.** **MEDIA**.

> **★ HITO E — MVP listo para piloto** (tras ECA-020).

---

### ECA-021 — Piloto controlado

- **Objetivo.** Operar el MVP con un grupo reducido y real de técnicos (p. ej. 5–15) durante un
  periodo acotado (p. ej. 2–3 semanas), recoger incidencias y datos de uso, y decidir el paso a
  escala.
- **Por qué se necesita.** `03` §2 y `00` §"Orden recomendado" pto. 7: probar con piloto antes de
  ~1 200 técnicos.
- **Dependencias.** ECA-020 (HITO E).
- **Crear.**
  - `docs-eca/07_BITACORA_PILOTO.md` (incidencias, decisiones, métricas).
  - Tablero simple de seguimiento (puede ser una consulta SQL guardada / vista de solo lectura).
- **Modificar.** Correcciones puntuales que surjan (cada una como sub-ticket pequeño, no como
  "refactor").
- **Tablas.** Solo lectura / vistas de seguimiento (actividades por día, técnicos activos,
  pendientes de sync por dispositivo, errores de sync).
- **Migraciones.** Idealmente ninguna; si surge una corrección, aditiva y versionada.
- **Endpoints.** Ninguno nuevo salvo que una incidencia lo exija.
- **Cambios PWA / panel.** Solo correcciones derivadas del piloto.
- **Comportamiento offline.** Observación real: ¿los técnicos logran trabajar días sin red y
  sincronizar sin pérdidas ni duplicados?
- **Permisos.** N/A.
- **Pruebas.** El piloto **es** la prueba de aceptación del sistema. Se registran:
  - tasa de actividades sincronizadas sin intervención,
  - duplicados detectados (objetivo: 0),
  - actividades `RECHAZADO` y su causa,
  - tamaño/tiempo del bootstrap por técnico,
  - consumo de disco de evidencias,
  - incidencias de login/GPS/foto por dispositivo.
- **Criterios de aceptación (salida del piloto).**
  - 0 duplicados de actividad/jornada en BD.
  - ≥ 95 % de actividades creadas offline sincronizadas correctamente sin soporte manual.
  - Ningún técnico bloqueado por el tamaño del subconjunto offline.
  - Sin incidentes de seguridad; sin datos sensibles en logs.
  - Feedback funcional recogido y priorizado.
- **Pasos de despliegue (Jesús).**
  1. Seleccionar técnicos y cargar sus usuarios/ámbitos/asignaciones.
  2. Sesión de onboarding (instalar PWA, primer login, bootstrap).
  3. Monitoreo diario (consultas de seguimiento, revisión de `auditoria_eventos` y de pendientes
     de sync).
  4. Reunión de cierre y decisión Go/No-Go para escalar.
- **Rollback.** Si el piloto falla en un criterio duro: congelar altas, corregir, repetir piloto.
  Los datos del piloto se conservan (son reales).
- **Riesgos.** Expectativa de features fuera de alcance (reportes, productores) → gestionar con la
  sección §0 de este documento.
- **Complejidad.** **MEDIA** (operativa, no técnica).

---

## 5. Orden exacto recomendado de ejecución

```
1.  ECA-001  Estructura independiente ECA
2.  ECA-002  Base técnica backend
3.  ECA-003  Identidad + autenticación
4.  ECA-004  Roles y permisos mínimos            ─────────► ★ HITO A
5.  ECA-005  Scaffold panel admin + login
6.  ECA-006  Catálogos geográficos (estados/municipios)
7.  ECA-007  Catálogo + importación masiva de ECA
8.  ECA-008  Ámbitos geográficos técnico–municipio
9.  ECA-009  Asignaciones técnico–ECA (+ REGLA DE ECA)
10. ECA-010  Catálogos de actividad              ─────────► ★ HITO B
11. ECA-011  Scaffold PWA ECA + autenticación técnico
12. ECA-012  Jornada
13. ECA-013  Registro de actividad (online)
14. ECA-014  GPS y precisión
15. ECA-015  Evidencias fotográficas             ─────────► ★ HITO C
16. ECA-016  IndexedDB + outbox offline
17. ECA-017  Sincronización idempotente (push)
18. ECA-018  Bootstrap + delta offline (pull)    ─────────► ★ HITO D
19. ECA-019  Historial de actividades (PWA + admin)
20. ECA-020  Endurecimiento + observabilidad + datos de piloto  ──► ★ HITO E
21. ECA-021  Piloto controlado
```

**Paralelizable** (si hay más de una persona):

- Tras ECA-005: ECA-006 → ECA-007 → (ECA-008, ECA-009) pueden avanzar mientras otra persona
  hace ECA-010; y ECA-011 puede empezar en cuanto ECA-004 esté (no depende de la cadena de ECA).
- ECA-013/014/015 son secuenciales entre sí (comparten la pantalla de actividad).
- ECA-016 puede prepararse en paralelo a ECA-014/015 pero se integra después.

---

## 6. Dependencias críticas

| Dependencia | Impacto si falla / se retrasa | Mitigación |
|---|---|---|
| **`eca_db` provisionada + extensiones + variables de entorno** (Jesús) | Nada avanza más allá de ECA-001 | Acordar antes de empezar ECA-002; `.env.example` claro |
| **`SECRET_KEY` fuerte y fuera del repo** (Jesús) | Riesgo de seguridad crítico | ECA-002 impide arrancar sin ella |
| **Fuente, formato e IDENTIFICADOR ESTABLE del catálogo de ~5 000 ECA** (Jesús / institución) | ECA-007 no se puede validar; bloquea HITO B. **Sin un identificador de origen estable (`ID_ECA`/folio/clave), el upsert no es determinista y reimportar duplicaría.** | Pedir a Jesús una **muestra real**, la plantilla de columnas y **cuál columna es el identificador estable** antes de ECA-007. Si no existe ninguno → **DP-2**: se detiene la importación y se decide con la institución; **no** se deduplica por nombre/municipio. (Regla pendiente `03` §27.14) |
| **Duración de la sesión/autorización offline y vida del `refresh_token`** (institución / Jesús) | Si un `access_token` corto bloqueara el trabajo sin red, el técnico no podría capturar en campo | **DP-1**: valores **configurables** (`parametros_config` + config de cliente en el bootstrap), con valores iniciales de trabajo; **no** se fija un valor institucional en este plan |
| **Catálogo INEGI de estados/municipios** (año/fuente) | ECA-006 con datos incorrectos | Fijar fuente con Jesús; documentar en `data/inegi/FUENTE.md` (regla pendiente `03` §27.2) |
| **Información de asignaciones directas técnico–ECA** (institución) | ECA-009 queda sin datos; los técnicos operan solo por ámbito | La REGLA DE ECA ya contempla el caso "sin asignaciones"; no bloquea el MVP (regla pendiente `03` §27.13) |
| **Semilla de temas/subtemas/sistemas productivos** aprobada (equipo funcional) | Técnicos no encuentran la clasificación adecuada | El admin puede editarla en caliente (ECA-010); revisar antes del piloto |
| **`STORAGE_DIR` + respaldo + no servido como estático** (Jesús) | Fuga de evidencias o pérdida de datos | Verificación explícita en ECA-015 y ECA-020 |
| **Dispositivos Android del piloto** (Jesús) | GPS/foto/SW se comportan distinto | Definir lista de modelos soportados; probar en ECA-011/014/016 |
| **Restauración de backup probada** (Jesús) | No hay garantía de recuperación ante incidente | Criterio de aceptación de ECA-020 |
| **HITO D antes que cualquier reporte** | Crecimiento de alcance, piloto tardío | Sección §0 + revisión de hitos |

---

## 7. Qué puede preparar Claude Code

> Trabajo de código y documentación que **no** requiere el servidor de producción. Todo entregado
> como ramas/PRs revisables por ticket.

- **ECA-001–002:** estructura de los tres proyectos, `pyproject`/`package.json`, configuración de
  FastAPI/SQLAlchemy/Alembic, `settings`, `db.py`, `get_db`, `/health`, `docker-compose` para dev,
  `conftest` de pruebas.
- **ECA-003–004:** modelos SQLAlchemy, migraciones Alembic (identidad, RBAC, auditoría),
  `security.py` (Argon2 + JWT + refresh), `require_permission`, routers `auth`/`usuarios`/`permisos`,
  data migration de semilla de roles/permisos, `scripts/crear_admin.py`, pruebas.
- **ECA-005:** scaffold `admin-eca` (login, store auth, router guard, layout, interceptor).
- **ECA-006:** modelos/migraciones/endpoints de geo; **script de carga** del catálogo INEGI a
  partir del CSV que provea Jesús; pantalla admin de geografía; pruebas.
- **ECA-007:** modelos/migración de `ecas` (con `clave_fuente`) + `lotes_importacion`; servicio de
  importación (parseo CSV/XLSX, validación por fila, **upsert transaccional por bloques con
  `clave_fuente` como clave determinista**, y el **rechazo de importaciones sin identificador
  estable**, DP-2); endpoints; pantallas admin de ECA e importación (con selección de columna
  identificador); fixtures de prueba; pruebas de rendimiento con 5 000 filas sintéticas.
- **ECA-008–010:** modelos/migraciones/endpoints/pantallas de ámbitos, asignaciones (incl.
  **implementación de la REGLA DE ECA** y su parámetro de config), catálogos de actividad + semilla.
- **ECA-011:** scaffold `pwa-eca` (VitePWA/Workbox con **un solo SW**, store auth, interceptor,
  guard, manifest, `EstadoConexion`, `sesionLocal.js` (**sesión local offline**, §2.2), pantallas
  de login/inicio/perfil).
- **ECA-012–013:** modelos/migraciones/endpoints de jornada y actividad; validaciones de negocio
  en backend; pantallas PWA de jornada y "Nueva actividad"; `SelectorEca` server-side; pruebas.
- **ECA-014:** servicio `gps.js` (sin ubicación por defecto), componente de captura, validación
  backend de coherencia GPS; pruebas con mock de geolocalización.
- **ECA-015:** capa `Storage` + `LocalStorage`, modelos/migración de evidencias, endpoints de
  subida/descarga autenticada, `imagen.js` de compresión (adaptado de SV), componente de captura;
  pruebas (incl. idempotencia por SHA-256).
- **ECA-016:** esquema IndexedDB versionado (`db.js`), `outbox.js` con **`estado_local`
  (transmisión, no negocio)**, store `outbox`, pantalla de sincronización, badge de pendientes;
  pruebas con `fake-indexeddb` (incl. encolar con `access_token` expirado y sesión local vigente).
- **ECA-017:** router/servicio `sync` (push idempotente, **`resultado` de transmisión separado
  del estado de negocio**, `recibido_en` en servidor), modelo/migración de `dispositivos`, motor
  `sync.js` (**aseguramiento de sesión de servidor antes del push**, backoff+jitter, orden de
  dependencias); pruebas de idempotencia, de lote parcial y del escenario de sesión offline.
- **ECA-018:** `bootstrap_service` (REGLA DE ECA + recorte de geo), endpoints `bootstrap`/`pull`,
  stores `catalogos`/`ecas` offline, integración en `SelectorEca` y catálogos; pruebas de los
  3 escenarios de la regla y del tope `max_offline`.
- **ECA-019:** endpoints de consulta con filtros + paginación + exportación CSV; pantallas
  "Historial" (PWA) y "Actividades"/"Detalle" (admin); pruebas.
- **ECA-020:** middlewares de rate limiting y cabeceras, `test_smoke.py` end-to-end (**incluye el
  escenario de sesión offline**: login→sin red→token expirado→captura→reconexión→sync sin
  pérdida ni duplicados), semilla de `parametros_config` con valores iniciales de
  `REFRESH_TOKEN_DIAS`/`OFFLINE_SESSION_DIAS` (**DP-1**), `RUNBOOK.md`, `scripts/seed_piloto.py`,
  matriz permiso↔endpoint, revisión de logs.
- **ECA-021:** plantilla de `07_BITACORA_PILOTO.md`, consultas SQL de seguimiento.

---

## 8. Qué requiere ejecución / validación de Jesús en el servidor

| Ticket | Acción de Jesús (servidor / infraestructura / datos) |
|---|---|
| ECA-001 | Crear repos/ramas; accesos. |
| ECA-002 | Crear `eca_db` + usuario; instalar `citext`/`pg_trgm`; definir `.env` (con `SECRET_KEY` fuerte); desplegar `backend-eca` tras nginx (`api-eca.<dominio>`); `alembic upgrade head`; verificar `/health`. |
| ECA-003 | `alembic upgrade head`; ejecutar `crear_admin.py` con contraseña real; probar login. |
| ECA-004 | `alembic upgrade head` (RBAC + semilla); verificar roles/permisos y rol del ADMIN inicial. |
| ECA-005 | `npm run build` admin; publicar en `admin-eca.<dominio>`; configurar `VITE_API_URL`; smoke de login; revisar CORS. |
| ECA-006 | Proveer la **fuente exacta** del catálogo INEGI; `alembic upgrade head`; verificar conteos (32 / ~2469). |
| ECA-007 | **Proveer la estructura real, una muestra del archivo de ~5 000 ECA y CUÁL columna es el identificador estable** (`ID_ECA`/folio/clave). Si no hay ninguno → escalar **DP-2** y NO cargar. `alembic upgrade head`; cargar desde el panel indicando la columna identificador; verificar `count(*)` y `count(DISTINCT clave_fuente)`; **medir el tiempo de importación** y decidir si se mantiene síncrona. |
| ECA-008 | `alembic upgrade head`; cargar ámbitos de los técnicos del piloto. |
| ECA-009 | `alembic upgrade head`; cargar asignaciones directas **si existe esa información**; validar la REGLA DE ECA con datos reales. |
| ECA-010 | `alembic upgrade head`; revisar/ajustar la semilla de temas/subtemas/sistemas con el equipo funcional. |
| ECA-011 | `npm run build` PWA; publicar en `eca.<dominio>` (HTTPS, `navigateFallback`); probar instalación en Android real; **probar que la app abre y navega tras expirar el `access_token` sin red** (sesión local offline); runbook de actualización de SW. |
| ECA-012–014 | `alembic upgrade head` (jornadas, actividades); rebuild+publish PWA; pruebas de campo básicas (jornada, actividad, GPS en exterior/interior). |
| ECA-015 | `alembic upgrade head`; crear `STORAGE_DIR` (fuera del webroot, permisos correctos); **verificar que nginx no lo sirve**; configurar respaldo; ajustar `client_max_body_size`; rebuild+publish PWA. |
| ECA-016 | Rebuild+publish PWA; pruebas offline en dispositivo real. |
| ECA-017 | `alembic upgrade head` (dispositivos); rebuild+publish PWA; prueba de campo offline→online sin duplicados. |
| ECA-018 | Rebuild+publish PWA; verificar tamaño/tiempo del bootstrap con un técnico real; ajustar `eca.max_offline` si hace falta. |
| ECA-019 | Rebuild+publish PWA y panel; validar consultas con datos reales. |
| ECA-020 | Aplicar cabeceras/HSTS/límites en nginx; configurar **backup automático** de BD y `STORAGE_DIR`; **probar una restauración**; **definir valores iniciales de `REFRESH_TOKEN_DIAS` y `OFFLINE_SESSION_DIAS` (DP-1)**; `seed_piloto.py`; correr `test_smoke` contra piloto (incluye escenario de sesión offline). |
| ECA-021 | Seleccionar técnicos; onboarding; monitoreo diario; reunión Go/No-Go. |

---

## 9. Checklist para autorizar el piloto

> Todos los ítems deben estar en verde. Responsable entre paréntesis.

### Seguridad

- [ ] Ningún endpoint de datos responde sin `require_permission` (matriz revisada). (Claude Code + Jesús)
- [ ] Contraseñas con Argon2; ninguna en texto plano en BD. (Claude Code)
- [ ] JWT de acceso con expiración; refresh token revocable; logout invalida sesión. (Claude Code)
- [ ] Un `access_token` expirado **sin red** no cierra la sesión ni impide capturar (**sesión local offline**, §2.2); sincronizar sí exige `refresh`/`login`. (Claude Code + Jesús)
- [ ] La validez de la sesión offline (`OFFLINE_SESSION_DIAS`) y la vida del `refresh_token` son **configurables** (**DP-1**), no constantes en código. (Claude Code)
- [ ] `SECRET_KEY` fuerte, fuera del repo; la app no arranca sin ella. (Jesús)
- [ ] CORS restringido a los orígenes de ECA; sin `"*"` con credenciales. (Jesús)
- [ ] Rate limiting en `login`/`refresh`/`sync`. (Claude Code)
- [ ] No hay endpoints `/debug/*` ni de volcado de BD sin auth. (Claude Code)
- [ ] `STORAGE_DIR` no accesible sin autenticación; nginx no lo sirve como estático. (Jesús)
- [ ] Logs sin CURP completa, contraseñas ni tokens. (Claude Code + Jesús)
- [ ] CURP no se devuelve en listados por defecto. (Claude Code)

### Datos y catálogos

- [ ] Estados y municipios cargados y verificados contra la fuente. (Jesús)
- [ ] Identificador estable del archivo real de ECA confirmado (o **DP-2** resuelto); **no** se
      implementó deduplicación automática por nombre/municipio. (Jesús + Claude Code)
- [ ] ~5 000 ECA importadas **con upsert por identificador estable (`clave_fuente`)**; reimportar
      el mismo archivo no duplica; `count(DISTINCT clave_fuente)` = filas válidas; muestra
      verificada. (Jesús)
- [ ] Catálogos de actividad (modalidad, tipo, tema, subtema, sistema productivo) sembrados y
      revisados por el equipo funcional. (Jesús)
- [ ] `parametros_config` con `eca.regla_disponibilidad`, `eca.max_offline`,
      `gps.precision_valida_maxima_m`, retención de sync, **`OFFLINE_SESSION_DIAS` y
      `REFRESH_TOKEN_DIAS` (DP-1)**. (Claude Code + Jesús)
- [ ] Técnicos del piloto creados, con ámbito (y asignaciones directas si existen). (Jesús)

### Funcionalidad MVP (prueba end-to-end `test_smoke` + prueba de campo)

- [ ] Técnico: login → bootstrap → ve sus ECA relevantes (no las 5 000). (Jesús)
- [ ] Técnico: inicia jornada sin foto/GPS obligatorios. (Jesús)
- [ ] Técnico: registra actividad con modalidad/tipo/tema/subtema/sistema productivo +
      descripción/resultado. (Jesús)
- [ ] Técnico: captura GPS + precisión; `SIN_GPS` permitido sin coordenadas falsas. (Jesús)
- [ ] Técnico: adjunta 1–3 fotos (según el tipo); sin placeholders. (Jesús)
- [ ] Técnico: hace todo lo anterior **sin conexión**; los datos persisten al cerrar la app. (Jesús)
- [ ] Escenario completo: login con red → pérdida de red → **expira el `access_token`** → el
      técnico sigue capturando jornada/actividad/GPS/fotos → vuelve la conexión → recupera sesión
      (`refresh`/`login`) → sincroniza **sin pérdida ni duplicados**. (Jesús)
- [ ] Al recuperar red: sincroniza **sin duplicados**; reintentar no crea duplicados. (Jesús)
- [ ] Técnico: consulta su historial (local + servidor); el indicador "sin sincronizar" viene del
      outbox local (§2.3). (Jesús)
- [ ] Admin: crea/importa usuarios. (Jesús)
- [ ] Admin: administra estados/municipios. (Jesús)
- [ ] Admin: importa ECA. (Jesús)
- [ ] Admin: asigna municipios de trabajo. (Jesús)
- [ ] Admin: asigna ECA directas (si hay datos). (Jesús)
- [ ] Admin: administra catálogos de actividad. (Jesús)
- [ ] Admin: consulta actividades registradas con filtros. (Jesús)

### Operación

- [ ] Migraciones Alembic aplicadas; `GET /health` reporta `migracion_actual = head`. (Jesús)
- [ ] La tabla `actividades` **no** almacena estado de transmisión; el estado local del outbox
      (`PENDIENTE`/…) vive solo en el dispositivo (§2.3). (Claude Code)
- [ ] Backup automático de `eca_db` y `STORAGE_DIR` configurado. (Jesús)
- [ ] **Restauración de backup probada** en entorno aparte. (Jesús)
- [ ] `RUNBOOK.md` con despliegue, rollback (`alembic downgrade`), incidentes. (Claude Code)
- [ ] Lista de dispositivos Android soportados definida y probada. (Jesús)
- [ ] Consultas de seguimiento del piloto listas (actividades/día, pendientes de sync, rechazados). (Claude Code)
- [ ] Sembrando Vida intacto: `backend/main.py`, `agricultura_db`, `pwasuper/`, `admin-pwa/` sin
      cambios. (Jesús)

### Alcance

- [ ] Ningún elemento de la sección §0 ("Qué NO forma parte del MVP") se coló en la entrega. (Todos)
- [ ] HITO E alcanzado **antes** de iniciar cualquier trabajo de reportes avanzados, productores
      o formularios. (Todos)

---

*Fin de `06_PLAN_IMPLEMENTACION_ECA.md`. Al completar ECA-021 con el checklist en verde, se
habilita la planeación de la Fase 2 (productores, unidades productivas, formularios,
levantamientos) sobre la base ya probada.*
