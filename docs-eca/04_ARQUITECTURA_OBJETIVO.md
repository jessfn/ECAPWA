# 04 — Arquitectura objetivo del sistema ECA V1

> **Propósito.** Definir la arquitectura técnica objetivo del sistema ECA (Escuelas de Campo)
> **como sistema independiente**, reutilizando componentes tecnológicos del repositorio clonado
> de Sembrando Vida (SV) pero **sin extender su código, sin migrar sus datos y sin acoplarse a
> su base de datos**.
>
> **Fuentes.** `AGENTS.md`, `docs-eca/00_START_HERE.md`, `01_AUDITORIA_INICIAL.md`,
> `02_INVENTARIO_TECNICO.md` y — como fuente funcional principal —
> `03_MODELO_NEGOCIO_ECA_ACTUALIZADO.md`.
>
> **Estado.** Diseño. **No se modifica código, no se crean migraciones, no se implementan
> pantallas.** Las reglas institucionales pendientes (`03` §27) se resuelven con
> catálogos / permisos / configuración / asignaciones, nunca con constantes en código.
>
> **Documento hermano.** `05_MODELO_DATOS_ECA.md` (entidades, tablas, índices, ERD).

---

## 1. Principios rectores

| # | Principio | Origen |
|---|---|---|
| P1 | ECA es un **sistema independiente** de SV. Repos, backend, base de datos, dominios y despliegues separados. | `03` §1 |
| P2 | El repo clonado se usa para **reutilizar componentes técnicos**, no para heredar el modelo de negocio SV. | `03` §1 |
| P3 | **No** se migran datos históricos de SV. Sin FKs ni JOINs entre `eca_db` y la BD de SV. | `03` §1 |
| P4 | **Aditividad y reversibilidad**: cambios de esquema por migraciones versionadas (Alembic), nunca `ALTER TABLE` en runtime. | `AGENTS.md` 3–4, `02` §3 |
| P5 | **Offline-first**: todo objeto creado en campo lleva UUID estable de cliente; toda sincronización es idempotente. | `AGENTS.md` 9–10, `03` §19 |
| P6 | **Seguridad real en backend**: autenticación con expiración + autorización por permiso en cada endpoint. Validación crítica repetida en BD (constraints). | `AGENTS.md` 6–8, `02` §4/§6/§20 |
| P7 | **Sin motor abstracto innecesario**: entidades explícitas con columnas explícitas. `JSONB` solo para casos acotados y justificados. | `03` §26, instrucción de diseño |
| P8 | **No hardcodear reglas pendientes**: catálogos activables, parámetros de configuración, permisos y asignaciones. | `03` §26–27–29 |
| P9 | **Escala objetivo**: ~1 200 técnicos concurrentes en campo, catálogo de ~5 000 ECA, crecimiento posterior a productores / unidades / formularios / levantamientos. | `03` §2–3 |
| P10 | **Evidencia real**: nunca placeholders de foto; nunca coordenadas inventadas. | `03` §8/§20 |

---

## 2. Panorama de sistemas

```
                         ┌───────────────────────────────────────────────┐
                         │              SISTEMA ECA (nuevo)               │
                         │                                               │
   PWA TÉCNICO ECA ──────┤  backend-eca (FastAPI)   ──►  PostgreSQL eca_db│
   (pwa-eca)             │        │                                      │
                         │        ├──► Object Storage (S3/MinIO)         │
   PANEL ADMIN ECA ──────┤        │      evidencias + PDF de reportes    │
   (admin-eca)           │        └──► Worker/cron (imports, indicadores)│
                         └───────────────────────────────────────────────┘

                         ┌───────────────────────────────────────────────┐
                         │   LEGADO SEMBRANDO VIDA (congelado)            │
                         │   backend/main.py · agricultura_db             │
                         │   pwasuper/ · admin-pwa/                       │
                         │   — sin cambios, sin nuevas features —         │
                         └───────────────────────────────────────────────┘

   Relación entre ambos: NINGUNA en runtime.
   Solo se comparte conocimiento y código copiado de utilidades genéricas.
```

- **Dominios sugeridos** (parametrizables): `eca.<dominio>` (PWA técnico),
  `admin-eca.<dominio>` (panel), `api-eca.<dominio>` (backend). Distintos de los de SV.
- **Base de datos**: `eca_db` en la misma instancia PostgreSQL o en otra; **schema propio**,
  sin objetos compartidos con SV.

---

## 3. Arquitectura del backend ECA (`backend-eca/`)

### 3.1 Decisión estructural

> **Nuevo servicio backend, no extensión del monolito.** `AGENTS.md` regla 5 prohíbe agregar
> lógica ECA a `backend/main.py`; `03` §1 exige independencia. El monolito SV queda congelado.

### 3.2 Stack

| Capa | Elección | Motivo (contra hallazgos de `02`) |
|---|---|---|
| Framework | **FastAPI** | Se conserva (`02` §3): productivo, tipado, OpenAPI. |
| Servidor | **uvicorn + gunicorn, múltiples workers** tras nginx | `02` §3/§21: hoy 1 solo proceso; ECA necesita escalar CPU. |
| Acceso a datos | **SQLAlchemy 2.x (ORM + Core) + `psycopg` (v3)** | `02` §3/§21: elimina el cursor global compartido. |
| Pool / sesión | **Pool de conexiones + sesión por request** (`Depends(get_db)`) | `02` §21: la condición de carrera del cursor global desaparece. |
| Migraciones | **Alembic**, versionadas, fuera del ciclo de request | `02` §3: elimina migraciones "al importar" y `ALTER TABLE` en caliente. |
| Migración de arranque | Comando explícito `alembic upgrade head` en el pipeline de despliegue | multi-worker seguro. |
| Auth | **JWT de acceso corto (15 min) + refresh token en BD revocable** | `02` §4: hoy JWT sin `exp` y stubs que conceden admin. |
| Hash de contraseña | **Argon2id** (`argon2-cffi`) o bcrypt (coste ≥ 12) | `AGENTS.md` 6, `02` §4: nunca texto plano. |
| Validación | **Pydantic v2** en API + **constraints** en BD | `AGENTS.md` 8: no confiar solo en frontend. |
| Almacenamiento de archivos | **Abstracción `StorageBackend`** → local (dev) / S3-MinIO (prod) | `02` §14: hoy filesystem público. |
| PDF de reportes | **ReportLab server-side** | `02` §16: hoy jsPDF/html2canvas en el móvil, frágil. |
| Tareas diferidas | **Worker** (cron simple o RQ/Celery si crece): imports masivos, PDFs, refresco de indicadores | evita bloquear requests. |
| Logging | **Structured logging** (JSON), sin CURP/tokens/contraseñas | `AGENTS.md` 7. |
| Config | **Pydantic Settings** desde variables de entorno; sin secretos en el repo | `02` §20: `_SYS_OBSERVER_SECRET`, fallback de `SECRET_KEY`. |
| Zona horaria | **`TIMESTAMPTZ` (UTC en BD)** + conversión en presentación | `02` §10/§22: elimina el sufijo `-06:00` manual. |
| CORS | Lista blanca explícita de orígenes ECA; **sin `"*"` con credenciales** | `02` §20. |

### 3.3 Estructura de carpetas propuesta

```
backend-eca/
├── alembic/                     # migraciones versionadas
├── app/
│   ├── main.py                  # creación de la app, middlewares, routers (delgado)
│   ├── core/
│   │   ├── settings.py          # Pydantic Settings (env)
│   │   ├── db.py                # engine, pool, get_db()
│   │   ├── security.py          # hashing, JWT emisión/verificación
│   │   ├── permissions.py       # dependencias require_permission("...")
│   │   ├── storage.py           # StorageBackend (local | s3)
│   │   ├── uuidkit.py           # validación/normalización UUID
│   │   ├── pagination.py
│   │   └── audit.py             # servicio de escritura en auditoria_eventos
│   ├── models/                  # SQLAlchemy (1 archivo por dominio)
│   ├── schemas/                 # Pydantic (request/response)
│   ├── repositories/            # acceso a datos, sin lógica HTTP
│   ├── services/                # reglas de negocio, transacciones (unidad de trabajo)
│   ├── api/
│   │   ├── deps.py              # get_current_user, get_current_device
│   │   └── routers/
│   │       ├── auth.py
│   │       ├── usuarios.py
│   │       ├── permisos.py
│   │       ├── grupos.py
│   │       ├── geo.py
│   │       ├── ambitos.py
│   │       ├── ecas.py
│   │       ├── asignaciones.py
│   │       ├── catalogos.py
│   │       ├── jornadas.py
│   │       ├── actividades.py
│   │       ├── evidencias.py
│   │       ├── sync.py
│   │       ├── importacion.py
│   │       ├── indicadores.py
│   │       ├── reportes.py
│   │       ├── auditoria.py
│   │       └── config.py
│   │       # Fase 2 (reservados, no implementados):
│   │       # productores.py, unidades.py, formularios.py, levantamientos.py
│   └── workers/
│       ├── importacion_worker.py
│       └── indicadores_worker.py
└── tests/
```

### 3.4 Módulos del backend ECA (nuevos)

| Módulo | Propósito | Endpoints núcleo (indicativos) | Fase |
|---|---|---|---|
| **auth** | Login, refresh, logout, cambio de contraseña, revocación de sesión. | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/password` | 1A |
| **usuarios** | CRUD de personas con acceso; alta/baja; asignación de roles. | `GET/POST /usuarios`, `GET/PATCH /usuarios/{id}`, `PATCH /usuarios/{id}/estado`, `PUT /usuarios/{id}/roles` | 1A |
| **permisos** | Catálogo de roles y permisos; asignación rol↔permiso. Solo lectura para clientes; edición para admin. | `GET /roles`, `GET /permisos`, `PUT /roles/{id}/permisos` | 1A |
| **grupos** | Grupos de trabajo, membresías con rol en grupo y vigencia, responsables. | `GET/POST /grupos`, `POST /grupos/{id}/miembros`, `DELETE /grupos/{id}/miembros/{uid}` | 1A |
| **geo** | Catálogos geográficos normalizados (estado / municipio / localidad) con claves oficiales. Solo lectura + carga administrativa. | `GET /geo/estados`, `GET /geo/municipios?estado=`, `GET /geo/localidades?municipio=` | 1A |
| **ambitos** | Ámbito geográfico de trabajo del técnico (municipios, N:M, con vigencia). | `GET/PUT /usuarios/{id}/ambito`, `GET /ambitos?municipio=` | 1A |
| **ecas** | CRUD de ECA, búsqueda filtrada (estado/municipio/clave/nombre/localidad), sistemas productivos asociados. | `GET /ecas` (filtros + paginación), `GET/POST /ecas`, `PATCH /ecas/{id}` | 1A |
| **asignaciones** | Relación explícita técnico↔ECA, con vigencia y origen. Independiente de grupos. | `GET /asignaciones?tecnico=`, `POST /asignaciones`, `DELETE /asignaciones/{id}` | 1A |
| **catalogos** | Modalidad, tipo de actividad, tema, subtema, sistema productivo. Activables/desactivables. | `GET /catalogos/{tipo}`, `POST/PATCH` (admin) | 1A |
| **importacion** | Carga masiva CSV/XLSX de ECA (y usuarios) con validación por fila, previsualización y confirmación. | `POST /importaciones` (sube), `GET /importaciones/{id}` (resultado), `POST /importaciones/{id}/confirmar` | 1A |
| **config** | Parámetros operativos configurables (regla de disponibilidad ECA, máx. jornadas/día, tamaño de lote sync, etc.). | `GET /config`, `PUT /config/{clave}` | 1A |
| **jornadas** | Alta/cierre de jornada, sin foto ni GPS obligatorios. | `POST /jornadas`, `PATCH /jornadas/{uuid}/cerrar`, `GET /jornadas?tecnico=&fecha=` | 1B |
| **actividades** | Registro y consulta de actividades georreferenciadas y clasificadas; historial y mapa. | `POST /actividades`, `GET /actividades` (filtros), `GET /actividades/{uuid}`, `PATCH /actividades/{uuid}` | 1B |
| **evidencias** | Subida y consulta de 1–3 fotos por actividad; URLs firmadas; hash para deduplicación. | `POST /actividades/{uuid}/evidencias`, `GET /evidencias/{id}` (redirige a URL firmada) | 1B |
| **sync** | Empuje idempotente (outbox) y descarga delta de catálogos/ECA/asignaciones/ámbito. | `POST /sync/push`, `GET /sync/pull?desde=`, `GET /sync/bootstrap` | 1B |
| **indicadores** | Indicadores descriptivos de operación/tipo/temática/evidencia/seguimiento (sin calificación). | `GET /indicadores?tecnico=&grupo=&periodo=` | 1C |
| **reportes** | Reporte periódico por técnico calculado desde datos transaccionales; flujo de revisión. | `POST /reportes`, `GET /reportes/{uuid}`, `PATCH /reportes/{uuid}/estado`, `GET /reportes/{uuid}/pdf` | 1C |
| **auditoria** | Consulta de la bitácora append-only. Escritura vía servicio transversal. | `GET /auditoria` (filtros + paginación) | 1A→ |
| *(Fase 2)* **productores / unidades / formularios / levantamientos** | Reservados. Diseño en `05` §Fase 2. **No se implementan en V1.** | — | 2 |

### 3.5 Contratos transversales

- **`get_current_user`**: valida JWT de acceso, carga usuario + permisos efectivos (unión de
  permisos de sus roles). Rechaza si el usuario está `SUSPENDIDO`/`BAJA` (enforcement en backend,
  no solo en cliente — corrige `02` §4).
- **`require_permission("clave")`**: dependencia FastAPI por endpoint. Sin permiso → `403`.
- **`get_current_device`**: para endpoints de sync, asocia la operación a un `dispositivo`.
- **Unidad de trabajo**: cada endpoint de escritura abre una transacción; commit al final,
  rollback ante excepción. Sin `commit`/`rollback` globales.
- **Idempotencia**: los endpoints de `sync/push` y de creación en campo aceptan el `uuid` del
  cliente; si el recurso ya existe con ese `uuid`, responden `200` con el recurso existente
  (no `409`, no duplican). Ledger en `sync_operaciones`.
- **Auditoría**: middleware/servicio que registra en `auditoria_eventos` toda acción de
  escritura relevante, con `datos_antes`/`datos_despues` saneados (nunca CURP completa,
  contraseñas ni tokens).

---

## 4. Frontend técnico — PWA ECA (`pwa-eca/`)

### 4.1 Decisión estructural

> **Nueva PWA**, partiendo del *andamiaje* técnico de `pwasuper/` (copiar y limpiar), no de su
> código de negocio. `pwasuper/` queda congelado.

### 4.2 Stack

| Aspecto | Elección | Contra hallazgo de `02` |
|---|---|---|
| Base | Vue 3 + Vite + `vite-plugin-pwa` (Workbox) | se conserva (`02` §2). |
| Estado | **Pinia** (stores: `auth`, `catalogos`, `ecas`, `jornada`, `outbox`, `sync`, `conectividad`) | `02` §2: hoy no hay store; el estado vive en `Home.vue` + `localStorage`. |
| Router | Vue Router con **guard basado en token válido + expiración**, no en `localStorage.user` | `02` §2/§4. |
| Service Worker | **uno solo** (Workbox). Se elimina `public/sw.js`. | `02` §2: hoy hay doble SW. |
| HTTP | Axios con interceptor: adjunta `Authorization`, refresca token en `401`, encola en outbox ante error de red | `02` §15. |
| Offline store | **IndexedDB** (vía `idb`), esquema versionado, **fotos como `Blob`** (no base64) | `02` §15: hoy base64 infla el store; `DB_VERSION` sin estrategia de upgrade. |
| GPS | Servicio de captura multi-intento **sin ubicación por defecto**; expone `estado_gps` | `02` §13: hoy inventa coordenadas. |
| Imágenes | Compresión en cliente (se reutiliza el enfoque de `imageCompressor.js`), **sin placeholders** | `02` §14. |
| Mapa | Leaflet | se conserva. |
| UUID | `crypto.randomUUID()` al crear cualquier objeto en campo | `AGENTS.md` 9. |

### 4.3 Módulos / vistas nuevas

| Vista / módulo | Propósito | Offline |
|---|---|---|
| **Login / sesión** | Autenticación, refresh, bloqueo por cuenta suspendida. | Requiere red la 1ª vez; luego token en `IndexedDB` cifrado por origen. |
| **Bootstrap de sincronización** | Al primer login con red: descarga catálogos, ECA relevantes, asignaciones y ámbito del técnico. | Genera caché offline. |
| **Jornada** | Iniciar / terminar jornada del día. Sin foto ni descripción obligatorias. | Sí (outbox). |
| **Mis ECA** | Lista priorizada: ECA asignadas directamente; si no hay, ECA de los municipios del ámbito. Búsqueda por clave/nombre/localidad, filtros estado/municipio. | Sí (subconjunto cacheado). |
| **Nueva actividad** | Formulario de actividad: modalidad, tipo, tema, subtema, sistema productivo, ECA, descripción, resultado, GPS + precisión, 1–3 fotos (según config del tipo), participantes si aplica, seguimiento. | Sí (outbox + Blobs). |
| **Historial** | Actividades del técnico con estado de sincronización y de revisión. | Sí (lee caché local + servidor). |
| **Mapa** | Actividades del técnico georreferenciadas. | Parcial (marcadores locales). |
| **Sincronización** | Estado del outbox, reintentos, conflictos, forzar sync. | — |
| **Perfil / Ajustes** | Datos del técnico, ámbito, cambio de contraseña, limpieza de caché. | Lectura offline. |

### 4.4 Motor offline (resumen; detalle de datos en `05` §Diseño offline)

- **Outbox pattern**: cada creación/edición en campo se escribe primero en IndexedDB con
  `estado = 'PENDIENTE'`, `uuid`, `intentos = 0`. La UI muestra el objeto de inmediato.
- **Sync push**: envía en lotes (tamaño configurable, por defecto 50) al endpoint idempotente;
  ante éxito marca `SINCRONIZADO`; ante error de validación (`422`) marca `RECHAZADO` con motivo
  y **no reintenta**; ante error de red reintenta con backoff + jitter.
- **Sync pull (delta)**: descarga cambios de catálogos/ECA/asignaciones/ámbito desde
  `?desde=<timestamp_última_sync>`.
- **Dedup**: por `uuid` en servidor (constraint). **Nunca** por texto de mensajes de error
  (corrige `02` §15).
- **Purga**: los objetos `SINCRONIZADO` se conservan N días y luego se limpian; los `RECHAZADO`
  se muestran al técnico para corrección manual.
- **Evidencias**: se suben por separado, después de que la actividad exista en el servidor,
  referenciadas por el `uuid` de la actividad.

---

## 5. Panel administrativo — Admin ECA (`admin-eca/`)

### 5.1 Decisión estructural

> **Nuevo panel**, partiendo del andamiaje de `admin-pwa/` (copiar y limpiar). El panel SV queda
> congelado. Se descartan los scripts `test-*.js`/`probar-*.js` y los servicios duplicados.

### 5.2 Stack

- Vue 3 + Vite (SPA, servida estática por nginx). **No** PWA offline.
- **Pinia**. Router con guard de token.
- **La autorización es del backend.** El gating de menús/botones en el cliente es solo UX;
  cada acción se re-valida server-side (corrige `02` §6/§18).
- Mapas: **Leaflet** (se descarta la mezcla con Mapbox GL de `02` §13).
- Exportación: se reutilizan `xlsx` / `jszip` / `file-saver`; PDF vía backend (ReportLab).

### 5.3 Módulos

| Módulo | Propósito |
|---|---|
| **Usuarios** | CRUD, alta/baja, asignación de roles, importación masiva, reseteo de contraseña. |
| **Roles y permisos** | Ver/crear roles, asignar permisos. Permisos independientes del nombre del cargo (`03` §4.1). |
| **Grupos** | CRUD de grupos, alta/baja de miembros, rol en grupo (TÉCNICO/ENLACE/SUPERVISOR — catálogo), responsables, vigencia. |
| **Catálogos geográficos** | Alta y mantenimiento de estados/municipios/localidades (semilla oficial + edición controlada). |
| **ECA** | CRUD, búsqueda filtrada, sistemas productivos asociados, activar/desactivar. |
| **Importación de ECA** | Subir CSV/XLSX, previsualizar validación por fila, ver errores, confirmar o cancelar el lote. |
| **Ámbitos geográficos** | Asignar municipios de trabajo a cada técnico (N:M). |
| **Asignaciones técnico–ECA** | Alta/baja de asignaciones directas, individual o por lote. |
| **Catálogos de actividad** | Modalidad, tipo (con `requiere_evidencia`, `min/max_fotos`, `permite_participantes`), tema, subtema, sistema productivo. |
| **Actividades** | Consulta con filtros (técnico, grupo, ECA, estado, municipio, tipo, tema, fecha), detalle, evidencias, mapa. |
| **Mapa / visor** | Visualización territorial de actividades y ECA. |
| **Indicadores** | Tableros descriptivos de operación, tipo de intervención, temática, evidencia, seguimiento. |
| **Reportes** | Generar/consultar reporte periódico por técnico; descargar PDF; flujo de revisión (BORRADOR→ENVIADO→REVISADO→OBSERVADO→APROBADO). |
| **Revisión** | Bandeja de reportes/actividades por revisar; observaciones. La firma **no** es obligatoria en V1 (`03` §25). |
| **Auditoría** | Consulta de la bitácora. |
| **Configuración** | Parámetros operativos (`config`), catálogos de roles y roles de grupo. |
| *(Fase 2)* **Productores / Unidades / Formularios** | Reservados. No implementados en V1. |

---

## 6. Seguridad

> Resuelve los riesgos de `02` §20. Es la **Fase 1A** obligatoria antes de cualquier dato real.

| Área | Diseño ECA |
|---|---|
| **Identidad** | Tabla **única** `usuarios` (sin el doble `usuarios`/`admin_users` de SV). Todo el que entra —técnico, administrador, enlace, supervisor— es un `usuario` con uno o más `roles`. |
| **Contraseñas** | **Argon2id** (o bcrypt coste ≥ 12). Nunca texto plano. `requiere_cambio_contrasena` para altas y reseteos. Política mínima de longitud/robustez validada en backend. |
| **Autenticación** | JWT de acceso **con `exp` corto (≈15 min)** + **refresh token persistido y revocable** (`tokens_refresco`). Logout y baja de usuario revocan refresh tokens. |
| **Autorización** | RBAC: `roles` → `permisos` (catálogo de claves atómicas por módulo). `require_permission()` en **cada** endpoint. Sin stubs que concedan admin (corrige `02` §4). El cliente solo oculta UI; el backend decide. |
| **Ámbito de datos** | Los permisos "ver todo" vs "ver mi grupo" vs "ver mis datos" se modelan como permisos distintos (`actividades.ver_propias`, `actividades.ver_grupo`, `actividades.ver_todas`). El alcance por nivel jerárquico queda **configurable** (regla institucional pendiente `03` §27.4). |
| **CURP y datos personales** | La CURP se almacena en `usuarios`/(Fase 2)`productores`, **no se devuelve en listados** por defecto; se expone solo a permisos específicos y **enmascarada** salvo `*.ver_curp`. Nunca en logs (`AGENTS.md` 7). |
| **Evidencias** | Object storage privado. Acceso vía **URL firmada de expiración corta** emitida por el backend tras verificar permiso. Sin `StaticFiles` público (corrige `02` §14). |
| **`usuario_id` ligado a la sesión** | En jornada/actividad el técnico se toma del token, no de un campo del formulario (corrige `02` §20 pto. 10). |
| **CORS** | Lista blanca de orígenes ECA. `allow_credentials=True` **solo** con orígenes explícitos, nunca con `"*"`. |
| **Secretos** | Todos en variables de entorno / gestor de secretos. `SECRET_KEY` sin valor por defecto (la app no arranca sin él). Sin secretos en el repo. |
| **Rate limiting** | En `login`, `refresh` y endpoints de escritura de sync (defensa ante fuerza bruta y tormentas de reintentos). |
| **Endpoints de diagnóstico** | No se exponen `/debug/*` en producción. Un `/health` mínimo sin datos sensibles. |
| **Auditoría** | `auditoria_eventos` append-only para acciones de escritura y accesos sensibles (exportaciones, cambios de permisos, bajas). |
| **Transporte** | HTTPS obligatorio; HSTS; cabeceras de seguridad (CSP básica en el panel). |

---

## 7. Offline / sincronización

| Aspecto | Diseño |
|---|---|
| **Alcance offline (técnico)** | Crear/editar: jornadas, actividades, evidencias. (Fase 2: productores, levantamientos, respuestas.) Leer: catálogos, ECA relevantes, asignaciones, ámbito, historial propio. |
| **Descarga de catálogo ECA** | **Nunca las ~5 000 ECA nacionales.** Solo el subconjunto del técnico: (1) ECA asignadas directamente; (2) en su defecto, ECA de sus municipios de ámbito (`03` §6.8). Endpoint `GET /sync/bootstrap` y deltas por `?desde=`. |
| **Identidad de objetos** | `uuid` v4 generado en el dispositivo para cada objeto (`AGENTS.md` 9). El servidor lo usa como clave de idempotencia (`UNIQUE`). |
| **Idempotencia** | `POST /sync/push` acepta lote de operaciones con `uuid_operacion` + `uuid` de entidad. Reenvío = mismo recurso, respuesta `200`. Ledger `sync_operaciones`. Sin interpretación de textos de error (`03` §19). |
| **Conflictos** | V1: **last-write-wins por campo con marca de servidor**, y el objeto solo es editable por su técnico creador mientras esté en estado `BORRADOR`. Ediciones administrativas quedan auditadas. (Estrategia de conflicto más fina = decisión abierta.) |
| **Reintentos** | Backoff exponencial + jitter; límite de intentos; los `RECHAZADO` (error de validación) no se reintentan y se muestran al técnico. |
| **Evidencias** | Se suben tras confirmarse la actividad en servidor; referencia por `uuid` de actividad; `hash_sha256` evita re-subir la misma imagen; `hash_perceptual` alimenta detección de fotos reutilizadas. |
| **Frecuencia** | Sync disparada por: recuperación de conexión, acción manual, y verificación periódica con **backoff** (no polling fijo agresivo — a escala de 1 200 clientes, ver `02` §23). |
| **Versionado del store local** | Esquema IndexedDB con número de versión y migraciones `onupgradeneeded` explícitas. |

---

## 8. Almacenamiento de imágenes

| Tema | Diseño |
|---|---|
| **Backend de almacenamiento** | Interfaz `StorageBackend` con implementaciones `LocalStorage` (dev / despliegue mínimo) y `S3Storage` (MinIO / S3 en producción). El código de negocio no conoce el backend concreto. |
| **Ubicación** | Bucket/carpeta **privada**. Clave estructurada: `evidencias/{eca_id}/{actividad_uuid}/{n}.jpg`; PDFs: `reportes/{usuario_id}/{reporte_uuid}.pdf`. |
| **Referencia en BD** | La tabla guarda `storage_clave` (relativa), `mime`, `tamano_bytes`, `hash_sha256`, `hash_perceptual` — **no** rutas absolutas de disco (corrige `02` §14). |
| **Acceso** | El backend emite **URL firmada** de expiración corta tras validar permiso. Sin montaje estático público. |
| **Procesamiento** | Compresión y redimensionado **en el cliente** antes de subir (se reutiliza el enfoque de `imageCompressor.js`); el backend valida tamaño/mime/dimensiones y rechaza lo que exceda límites. |
| **Sin placeholders** | Si no hay foto, la actividad se guarda **sin evidencia** (si el tipo lo permite). Nunca se genera una imagen "Sin imagen" (corrige `02` §14, `03` §8). |
| **Deduplicación / antifraude** | `hash_perceptual` (pHash) se calcula al subir y se **persiste en columna**; la búsqueda de imágenes similares se hace por índice sobre esa columna, no recorriendo el disco (corrige `02` §16). |
| **Retención / respaldo** | Política de respaldo del bucket independiente de la BD; los archivos como BYTEA de SV **no** se replican en ECA. |

---

## 9. Separación del legado Sembrando Vida

### 9.1 Qué se **reutiliza** del repo clonado (copiar y adaptar, **no importar**)

| Componente reutilizado | De | Uso en ECA |
|---|---|---|
| Andamiaje PWA (Vue 3 + Vite + vite-plugin-pwa + Workbox: `/api` NetworkOnly, `navigateFallback`) | `pwasuper/vite.config.js` | Base de `pwa-eca`. |
| Enfoque de compresión de imágenes | `pwasuper/src/utils/imageCompressor.js` | Preprocesado de evidencia. |
| Enfoque de captura GPS multi-intento | `pwasuper/src/services/geoLocationService.js` | Servicio GPS ECA (**sin** ubicación por defecto). |
| Patrón de store offline con metadatos (`intentos`, `estado`, `origen`) | `pwasuper/src/services/offlineService.js` | Diseño del outbox IndexedDB ECA. |
| Esqueleto del motor de sync (listeners online/offline, backoff, proceso por lotes) | `pwasuper/src/services/syncService.js` | Motor de sync ECA (**con** idempotencia por UUID). |
| Componentes de conectividad / actualización de SW | `pwasuper/src/components/ConnectivityStatus*.vue`, `UpdateNotification.vue` | UI de estado. |
| Patrones de tabla/paginación/exportación (xlsx, jszip) | `admin-pwa/src/` | Base de `admin-eca`. |
| Generación de PDF server-side con ReportLab | `backend/main.py` (reportes admin) | Reporte periódico ECA. |
| Idea de bitácora de auditoría | `backend/main.py` (`sys_telemetry`) | `auditoria_eventos` ECA (rediseñada). |
| Patrón de asignación N:M con vigencia/origen/activo | `facilitador_tecnico_asignaciones` | `asignaciones_tecnico_eca`, `grupos_usuarios`, `ambitos_tecnico`. |
| FastAPI + `pytz`/tz helper (como referencia) | `backend/main.py` | Base del backend (con `TIMESTAMPTZ`). |
| Config externalizada por `.env` | `backend/.env.example` | Pydantic Settings. |

### 9.2 Qué queda **aislado como legado** (congelado, sin cambios, sin FKs cruzadas)

- **Backend SV**: `backend/main.py` íntegro y su base `agricultura_db` (tablas `usuarios`,
  `admin_users`, `registros`, `asistencias`, `reportes_generados`,
  `facilitador_tecnico_asignaciones`, `usuarios_terminos`, `historial`, `notificaciones*`,
  `manuales*`, `sys_telemetry`, `sys_observers`).
- **Frontends SV**: `pwasuper/`, `admin-pwa/`.
- **Catálogos y reglas SV**: `TERRITORIOS_SEMBRANDO_VIDA`, categorías de actividad SV,
  `CARGOS_ADMIN_CATALOGO`, flujo de firma SV, reportes SV, endpoints `/debug/*`,
  `/descargar-bd-completa`, `/fotos` estático.
- **Datos históricos SV**: no se migran. No hay proceso de importación SV→ECA.
- **Dominios / despliegues SV**: separados de los de ECA.

### 9.3 Reglas de aislamiento

1. `eca_db` no contiene ninguna tabla de SV ni FK hacia SV.
2. `backend-eca` no importa módulos de `backend/main.py`; el código común se **copia** a
   `backend-eca/app/core/` y evoluciona por separado.
3. No hay llamadas HTTP de ECA al backend SV ni viceversa.
4. La única "unión" admisible es a nivel de identidad de personas **si** la institución lo pide
   más adelante (p. ej. un SSO común) — hoy es **decisión abierta**, no se diseña.
5. Repos/carpetas separadas: `backend-eca/`, `pwa-eca/`, `admin-eca/` (o repos independientes).

---

## 10. Diagrama textual de módulos

```
╔══════════════════════════════ PWA TÉCNICO ECA (pwa-eca) ═══════════════════════════╗
║  Vistas:  Login · Jornada · MisECA · NuevaActividad · Historial · Mapa · Sync      ║
║  Stores (Pinia): auth · catalogos · ecas · jornada · outbox · sync · conectividad  ║
║  Infra local: IndexedDB (outbox + catálogos + Blobs) · Service Worker (Workbox)    ║
╚═══════════════════════════════╤═══════════════════════════════════════════════════╝
                                │  HTTPS/JSON + JWT           ▲ delta pull / push idempotente
╔═══════════════════════════════▼═══════════════════════════════════════════════════╗
║                        BACKEND ECA (backend-eca · FastAPI)                          ║
║                                                                                   ║
║  api/routers ───────────────────────────────────────────────────────────────────  ║
║   ┌──────────┐  ┌──────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌─────────────┐  ║
║   │  auth    │  │ usuarios │  │ grupos │  │  geo   │  │ambitos │  │   ecas      │  ║
║   └────┬─────┘  └────┬─────┘  └───┬────┘  └───┬────┘  └───┬────┘  └──────┬──────┘  ║
║        │             │            │           │           │              │         ║
║   ┌────▼─────┐  ┌────▼─────┐  ┌───▼──────┐  ┌─▼────────┐  ┌▼───────────┐ │         ║
║   │ permisos │  │  config  │  │asignac.  │  │catalogos │  │importacion │ │         ║
║   └────┬─────┘  └────┬─────┘  └───┬──────┘  └────┬─────┘  └─────┬──────┘ │         ║
║        │             │            │              │              │        │         ║
║   ┌────▼─────────────▼────────────▼──────────────▼──────────────▼────────▼──────┐ ║
║   │                       jornadas · actividades · evidencias                    │ ║
║   └───────────────────────────────┬──────────────────────────────┬─────────────┘ ║
║                                   │                              │               ║
║                              ┌────▼─────┐                   ┌────▼──────┐         ║
║                              │   sync   │                   │indicadores│         ║
║                              └────┬─────┘                   └────┬──────┘         ║
║                                   │                              │               ║
║                                   │                         ┌────▼──────┐         ║
║                                   │                         │ reportes  │         ║
║                                   │                         └───────────┘         ║
║   ┌───────────────────────────────▼──────────────────────────────────────────┐   ║
║   │  auditoria (transversal, solo escritura desde services · lectura admin)   │   ║
║   └─────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                   ║
║   core/: settings · db(pool) · security(jwt/hash) · permissions · storage ·        ║
║          audit · uuidkit · pagination                                              ║
║   models/ (SQLAlchemy) · schemas/ (Pydantic) · repositories/ · services/           ║
║   alembic/ (migraciones)                                                           ║
║                                                                                   ║
║   [Fase 2 — reservado, no implementado]                                            ║
║     productores · unidades_productivas · formularios(+versiones) · levantamientos  ║
╚════════╤════════════════════════╤═══════════════════════════╤═════════════════════╝
         │                        │                           │
   ┌─────▼──────┐        ┌────────▼─────────┐        ┌────────▼──────────┐
   │ PostgreSQL │        │ Object Storage   │        │ Worker / cron     │
   │  eca_db    │        │ (S3 / MinIO)     │        │ imports · PDFs ·  │
   │ pool·TZ UTC│        │ evidencias·PDFs  │        │ indicadores       │
   └────────────┘        └──────────────────┘        └───────────────────┘
         ▲
╔════════╧═════════════════════ PANEL ADMIN ECA (admin-eca) ═════════════════════════╗
║  Usuarios · Roles/Permisos · Grupos · Geo · ECA · Importación · Ámbitos ·           ║
║  Asignaciones · Catálogos · Actividades · Mapa · Indicadores · Reportes ·           ║
║  Revisión · Auditoría · Configuración        [Fase 2: Productores · Formularios]    ║
║  Stores (Pinia) · Router (guard JWT) · autorización delegada al backend            ║
╚═══════════════════════════════════════════════════════════════════════════════════╝

──────────────────────────────────────────────────────────────────────────────────────
LEGADO SEMBRANDO VIDA (congelado · sin cambios · sin relación en runtime)
   backend/main.py   ·   agricultura_db   ·   pwasuper/   ·   admin-pwa/
──────────────────────────────────────────────────────────────────────────────────────
```

---

## 11. Dependencias entre módulos (backend ECA)

> `A → B` = A depende de B (lo consume). La auditoría y la configuración son transversales.

| Módulo | Depende de | Notas |
|---|---|---|
| `auth` | `usuarios`, `core.security` | Emite/renueva/revoca tokens. |
| `permisos` | `auth` | Catálogo; lo consumen todos los routers vía `require_permission()`. |
| `usuarios` | `auth`, `permisos` | Alta/baja; asignación de roles. |
| `grupos` | `usuarios`, catálogo `roles_grupo` | Membresías con vigencia. |
| `geo` | — | Catálogo base (estado/municipio/localidad). Sin dependencias. |
| `ambitos` | `usuarios`, `geo` | Municipios de trabajo del técnico. |
| `catalogos` | — | Modalidad/tipo/tema/subtema/sistema productivo. |
| `ecas` | `geo`, `catalogos` (sistemas productivos), `importacion` | Búsqueda filtrada + carga masiva. |
| `asignaciones` | `usuarios`, `ecas` | Relación técnico↔ECA, independiente de `grupos`. |
| `importacion` | `usuarios`, `ecas`, `geo` | Valida claves geográficas y duplicados por fila. |
| `config` | — | Parámetros; consumido por `ecas` (regla de disponibilidad), `jornadas` (máx/día), `actividades` (obligatoriedad de evidencia), `sync` (tamaño de lote). |
| `jornadas` | `usuarios`, `config` | Una jornada principal por técnico/fecha (configurable). |
| `actividades` | `jornadas`, `ecas`, `catalogos`, `evidencias`, `config` | Unidad de evidencia. |
| `evidencias` | `actividades`, `core.storage` | 1–3 fotos; hash; URL firmada. |
| `sync` | `actividades`, `jornadas`, `evidencias` (push); `ecas`, `asignaciones`, `ambitos`, `catalogos` (pull) | Idempotente por `uuid`. |
| `indicadores` | `actividades`, `jornadas`, `asignaciones`, `ecas` | Solo descriptivos. |
| `reportes` | `indicadores`, `usuarios`, `grupos`, `core.storage` | Cálculo desde datos transaccionales; PDF server-side; flujo de revisión. |
| `auditoria` | — (escrito por `services` de todos los módulos) | Append-only; lectura por admin. |
| *(Fase 2)* `productores` | `geo` | — |
| *(Fase 2)* `unidades_productivas` | `productores`, `geo`, `catalogos` | — |
| *(Fase 2)* `formularios` (+ versiones) | `catalogos` | Versiones inmutables. |
| *(Fase 2)* `levantamientos` | `formularios_versiones`, `productores`, `ecas`, `actividades` (opcional) | Base de "productores únicos atendidos". |

**Reglas de dependencia:**

1. Ningún módulo de negocio importa `api.routers` de otro módulo; la colaboración pasa por
   `services/` y `repositories/`.
2. `auditoria` y `config` son de sentido único (todos escriben en auditoría; todos leen config).
3. Los módulos de **Fase 2** no pueden ser dependencia de módulos de **Fase 1**; las tablas de
   Fase 1 solo dejan **huecos de FK nulos** hacia Fase 2 (p. ej. `actividades` no referencia
   `levantamientos`; es `levantamientos` quien referenciará `actividades`).
4. `sync` es el único módulo autorizado a escribir jornadas/actividades/evidencias "en nombre de"
   un técnico a partir de un lote offline; valida `uuid`, dispositivo y permisos.

---

## 12. Escala (~1 200 técnicos) — decisiones que la soportan

| Riesgo de `02` §23 | Decisión en esta arquitectura |
|---|---|
| Cursor/conexión global → no escala con workers | Pool + sesión por request + SQLAlchemy; múltiples workers. |
| Polling de sync agresivo por cliente | Sync por evento + verificación con backoff/jitter; `GET /sync/pull?desde=` (delta, no full). |
| Descarga de 5 000 ECA por dispositivo | Solo el subconjunto del técnico (asignadas o por ámbito). |
| Fotos en filesystem del backend | Object storage + URL firmada; sin estático público. |
| `phash` O(n) sobre disco | `hash_perceptual` en columna indexada. |
| `/registros` sin filtro devuelve todo | Paginación obligatoria + filtros server-side + endpoints de mapa con agregación. |
| PDF en el móvil | ReportLab server-side (worker). |
| IndexedDB con base64 y sin purga | `Blob` + esquema versionado + política de purga. |
| Auditoría con lock que serializa | `auditoria_eventos` con escritura asíncrona y **particionado mensual**. |
| Migraciones al importar (multi-worker) | Alembic fuera del ciclo de request, en el pipeline. |
| Reportes desde JSON congelado del cliente | Indicadores calculados desde tablas transaccionales; snapshot recomputable. |

---

## 13. Qué NO se decide todavía (remite a `03` §27)

- Nombres oficiales y número de niveles jerárquicos → `roles`, `roles_grupo`, `grupos.grupo_padre_id`
  nullable y `config` lo permiten sin fijarlos.
- Estructura territorial definitiva → catálogos `geo` normalizados + `ambitos_tecnico`.
- Alcance de consulta por nivel → permisos `*.ver_propias|ver_grupo|ver_todas` + `config`.
- Quién revisa/aprueba/firma reportes → estados en `reportes_periodo` + permisos; firma reservada.
- Metas, ponderaciones, metodología de evaluación → **fuera de V1** (`03` §22–23). No hay tabla de calificación.
- Regla definitiva técnico–ECA y cantidad de ECA por técnico → `config.eca.regla_disponibilidad`
  + `asignaciones_tecnico_eca` + `ambitos_tecnico`.
- Fuente y estructura final del catálogo de ~5 000 ECA → `ecas.metadatos JSONB` acotado +
  `lotes_importacion`.
- Obligatoriedad de evidencia/GPS por tipo → `tipos_actividad.requiere_evidencia`, `min/max_fotos`
  + `config`, nunca global.
- Formularios prioritarios → **Fase 2**.

Cada punto queda anclado a un mecanismo configurable y documentado como **decisión abierta** en
`05` §Decisiones abiertas.

---

*Fin de `04_ARQUITECTURA_OBJETIVO.md`. Ver `05_MODELO_DATOS_ECA.md` para el detalle de entidades,
tablas, índices, constraints y el diagrama entidad-relación.*
