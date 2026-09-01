# 02 — Inventario técnico del sistema actual

> **Propósito.** Documento de auditoría técnica basado exclusivamente en el código real del
> repositorio (rama actual, sin `.git`). Sirve para que una persona desarrolladora que no
> conoce el proyecto entienda cómo funciona hoy el sistema y qué partes son relevantes para
> la migración a ECA (Escuelas de Campo).
>
> **Alcance.** Solo lectura. No se modificó código, base de datos ni migraciones.
>
> **Método.** Lectura directa de `backend/main.py`, `pwasuper/` (PWA de técnicos),
> `admin-pwa/` (panel administrativo), configuración y documentación interna. Se contrastaron
> las afirmaciones de `docs-eca/01_AUDITORIA_INICIAL.md` con la implementación.
>
> **Leyenda de decisión por componente:**
> `CONSERVAR` = usar tal cual · `ADAPTAR` = reutilizar con cambios ·
> `REEMPLAZAR` = sustituir la implementación · `CREAR NUEVO` = no existe.

---

## 0. Contraste con `01_AUDITORIA_INICIAL.md`

| Afirmación previa | ¿Se confirma en el código? | Detalle |
|---|---|---|
| Backend monolítico (~12 mil líneas) en `backend/main.py` | **Sí** | `backend/main.py` tiene **11 963 líneas**. Concentra modelos Pydantic, migraciones, conexión BD, auth, ~150 endpoints, reportes PDF y reglas de negocio. |
| `Home.vue` con >6 mil líneas | **Sí** | `pwasuper/src/views/Home.vue` tiene **6 852 líneas**. Contiene jornada, actividad, GPS, imágenes, validación y sincronización. |
| CURP ya existe en `usuarios` y se valida duplicidad | **Sí** | `usuarios.curp VARCHAR(18) UNIQUE`; validación de formato y unicidad en `POST /usuarios` y `PUT /usuarios/{id}`. |
| Categorías de actividad codificadas en backend + defaults de Sembrando Vida | **Sí** | Lista `categorias_validas` hardcodeada en `POST /registro` (`backend/main.py:1168`) y duplicada en `pwasuper/src/services/syncService.js:504`. Default `Acompañamiento técnico` / `Trabajo administrativo y captura`. |
| Offline con IndexedDB, stores separados, `id_cliente`, intentos, estado | **Sí (parcial)** | `pwasuper/src/services/offlineService.js`: DB `PWAOfflineDB` v1, stores `registros_pendientes` y `asistencias_pendientes`. `id_cliente` existe **solo en registros** y con formato `reg_<epoch>_<rand>` (no UUID) y **no se envía al servidor**. |
| "Contraseña sin encriptar" al insertar usuario, conviviendo con bcrypt/passlib | **Sí (crítico)** | `backend/main.py:800` comentario literal *"contraseña sin encriptar"*; `POST /login` compara texto plano (`backend/main.py:909`). `admin_users` sí usa bcrypt (`passlib`). |
| Conexión/cursor PostgreSQL global compartida, con parches de concurrencia | **Sí** | `conn` y `cursor` globales (`backend/main.py:69`). Función `abrir_conexion_aislada()` (`:100`) creada explícitamente por condiciones de carrera en endpoints de estadísticas. |
| ~120 usuarios ya cargados, objetivo ~1 200 técnicos | No verificable desde el código | No hay fixtures ni conteos en el repo. Se asume del enunciado de negocio. |
| "Jornada" como entidad | **Matiz importante** | No existe la palabra `jornada` en el backend. La "jornada" es la tabla **`asistencias`** (una fila por `usuario_id`+`fecha`, con `hora_entrada`/`hora_salida`, fotos y descripciones). El estado del día se guarda además en `localStorage` del cliente. |
| Territorio como concepto de negocio Sembrando Vida | **Sí** | Lista fija `TERRITORIOS_SEMBRANDO_VIDA` de 31 valores (`backend/main.py:4560`), endpoints `/territorios-sembrando-vida`, columna `usuarios.territorio` y `admin_users.territorio`. |

---

## 1. Estructura general del repositorio

```
/
├── backend/
│   ├── main.py            # TODO el backend (FastAPI monolito, 11 963 líneas)
│   ├── requirements.txt    # fastapi 0.104, psycopg2-binary, bcrypt, passlib, python-jose, reportlab, imagehash, Pillow
│   └── .env.example        # DB_HOST/NAME/USER/PASS + SECRET_KEY
├── pwasuper/               # PWA de técnicos (Vue 3 + Vite + vite-plugin-pwa)
│   ├── src/views/          # Home.vue (6852), Reportes.vue (6085), Historial.vue (2798), Profile.vue (3866)...
│   ├── src/services/       # offlineService, syncService, apiService, geoLocationService, asistenciasService...
│   ├── src/components/     # FirmaDigital.vue, ConnectivityStatus.vue, TerritorioModal.vue, CargoModal.vue...
│   ├── public/sw.js        # Service worker adicional propio (además del de vite-plugin-pwa)
│   └── *.md / *.txt        # ~30 documentos de bitácora de features (ruido, no técnico-normativo)
├── admin-pwa/              # Panel administrativo (Vue 3 + Vite, NO es PWA offline)
│   ├── src/views/          # UsuariosView (9824), RegistrosView (11652), ConfiguracionView (9673), PermisosView (6480)...
│   ├── src/services/       # ~30 servicios; varios duplicados (usuariosService + usuariosServiceAlternativo...)
│   ├── src/*.js            # ~15 scripts test-*.js / probar-*.js / descubrir-api.js commiteados en src/
│   └── src/views/*.corrupted, *_OLD_BACKUP.vue, *_Apple.vue  # archivos muertos commiteados
├── admin_nginx.conf        # vhost nginx solo para admin.sembrandodatos.com (SPA estática)
├── start.js                # arranca "mock-server.js" (ausente en el repo) + frontend
├── package.json (raíz)     # express + pdf-lib + cors (no usado por el sistema real)
└── docs-eca/               # 00_START_HERE, 01_AUDITORIA_INICIAL, 02 (este documento)
```

### Observaciones estructurales

- **Tres aplicaciones**, un solo backend. Dominios de producción (deducidos de CORS y config):
  `app.sembrandodatos.com` (PWA técnicos), `admin.sembrandodatos.com` (panel),
  `apipwa.sembrandodatos.com` / `/api` (backend), `ubicacion.sembrandodatos.com`.
- **No hay control de versiones dentro del repo** (`Is a git repository: false` en el entorno).
  No hay historial de migraciones ni ramas; `AGENTS.md` asume Git pero el snapshot entregado no lo tiene.
- **No hay tests automatizados.** Los `test-*.js` de `admin-pwa/src/` son scripts manuales de
  exploración de API, no pruebas.
- **Sin CI/CD, sin linters activos, sin Docker/compose** en el repo.
- **Backups y archivos muertos versionados**: `Home_backup.vue`, `Historial_backup.vue`,
  `Historial_new.vue`, `Notificaciones_new.vue`, `AsistenciaView_OLD_BACKUP.vue`,
  `UsuariosView.vue.corrupted`, `PermisosView-new.vue`, `permisosServiceSimple.js`,
  `asistenciasServiceOptimized.js`, `usuariosServiceAlternativo.js`.

| Componente | Decisión | Nota |
|---|---|---|
| Estructura de 3 apps + 1 backend | **CONSERVAR** | El patrón (PWA campo / panel admin / API) sirve para ECA. |
| Monolito `backend/main.py` | **ADAPTAR** | Modularizar por routers; los módulos ECA deben nacer separados (regla 5 de `AGENTS.md`). No reescribir. |
| `Home.vue` monolítico | **ADAPTAR** | Extraer vistas/lógica; nuevas pantallas ECA fuera de este archivo. |
| Archivos muertos / backups / scripts sueltos | **REEMPLAZAR** (limpiar) | No migrar; eliminar en una tarea de higiene separada. |
| `start.js` + `package.json` raíz + `mock-server.js` | **REEMPLAZAR** | Referencian un mock inexistente. Definir arranque real (uvicorn + vite). |

---

## 2. Frontend / PWA de técnicos (`pwasuper/`)

### 2.1 Stack

- **Vue 3** (Composition API en las vistas nuevas, Options en componentes viejos), **Vue Router 4**
  con `createWebHistory`. **No hay store global** (ni Pinia ni Vuex); el estado vive en
  `localStorage` + refs locales de `Home.vue`.
- **Vite 6** + **vite-plugin-pwa 1.0** (`registerType: 'autoUpdate'`, `injectRegister: 'auto'`,
  `manifest: false` → el manifiesto es `pwasuper/public/manifest.json` manual).
- **Axios 1.9** para HTTP.
- **Leaflet 1.9** para mapas (marcadores de GPS).
- **IndexedDB** con API nativa (no `idb`). `idb-keyval` está en `package.json` pero **no se usa**.
- **jsPDF 4 + html2canvas + pdf-lib** para generar reportes PDF **en el cliente**.
- **Tailwind 3** + CSS propio (estilo "Apple").
- **Font Awesome** parcial.

### 2.2 Arranque y Service Worker

- `pwasuper/src/main.js`: registra el SW vía `utils/serviceWorkerRegistration.js`, pide permiso
  de notificaciones, inicializa audio de notificaciones tras el primer click.
- `pwasuper/vite.config.js` → Workbox: `navigateFallback: '/index.html'`,
  `navigateFallbackDenylist: [/^\/api\//]`, `runtimeCaching`: `/api/` → `NetworkOnly`;
  resto del dominio → `NetworkFirst` (cache `app-cache-v1.0.6`, TTL 24 h).
- Existe además `pwasuper/public/sw.js` (SW propio) → **potencial doble registro / conflicto de SW**.
- `server.port: 5174` en vite; `start.js` asume 5173. Inconsistencia menor.

### 2.3 Rutas y "protección"

`pwasuper/src/router/index.js`:

```js
router.beforeEach((to, from, next) => {
  const isLoggedIn = !!localStorage.getItem('user')   // única comprobación
  ...
})
```

- No hay token en la PWA de técnicos. El "login" (`POST /login`) devuelve un JSON de usuario
  (incluida la **CURP**) que se guarda en `localStorage.user`. No hay JWT, no hay expiración,
  no hay `Authorization` header en ninguna llamada de la PWA.
- Todas las rutas protegidas se basan en la mera presencia de `localStorage.user`.

### 2.4 Selección de URL de API

`pwasuper/src/utils/network.js`:

- `development` → `http://localhost:8000` / `:8001`; `production` → `'/api'` (relativa, mismo
  dominio, para evitar `ERR_CERT_AUTHORITY_INVALID` en Android antiguo).
- `checkInternetConnection()` hace `fetch('/api/health')`; si falla pero `navigator.onLine`
  es `true`, **asume online** y deja que la subida real decida (fallback offline).
- `apiService.js` cambia de servidor alternativo ante error de red y reintenta.

| Componente | Decisión |
|---|---|
| Vue 3 + Vite + vite-plugin-pwa | **CONSERVAR** |
| Ausencia de store global | **ADAPTAR** (introducir Pinia para estado ECA: asignaciones, catálogos, formularios) |
| Router guard basado solo en `localStorage.user` | **REEMPLAZAR** (token con expiración + verificación backend) |
| Selección dinámica de API / `/api` relativo | **CONSERVAR** |
| Doble service worker (`public/sw.js` + Workbox) | **ADAPTAR** (unificar en uno) |
| Generación de PDF en cliente | **ADAPTAR** (ver §16) |

---

## 3. Backend (`backend/main.py`)

### 3.1 Stack y arranque

- **FastAPI 0.104** + **uvicorn**. Arranque: `uvicorn.run(app, host="0.0.0.0", port=8000)` en
  `__main__` → **1 solo proceso, sin `workers`, sin `--reload`**. En producción presumiblemente
  detrás de nginx.
- **PostgreSQL** vía **psycopg2** (no SQLAlchemy, no ORM). SQL string-based con parámetros `%s`
  (parametrizado en la mayoría de casos; ver §17 para excepciones).
- **Middleware**: `CORSMiddleware` (`allow_origins=[..., "*"]`, `allow_credentials=True`),
  `GZipMiddleware` (`minimum_size=1000`).
- **PDF**: ReportLab (server-side, en varios endpoints de reportes admin).
- **Imágenes**: Pillow + `imagehash` (perceptual hashing para detección de fotos repetidas).
- **JWT**: `python-jose` (HS256) — **solo para `admin-pwa`**, no para la PWA de técnicos.
- **Hashing**: `passlib`/`bcrypt` — **solo para `admin_users`**.

### 3.2 Conexión a base de datos

- `conn` / `cursor` **globales de módulo** (`backend/main.py:69-71`), compartidos por todos los
  requests (FastAPI ejecuta endpoints sync en un threadpool → varios threads sobre el **mismo
  cursor**).
- `ejecutar_consulta_segura(query, params, fetch_type)` (`:139`): reconexión con 3 reintentos,
  `rollback` ante error, `commit` si la query empieza por `INSERT/UPDATE/DELETE`.
- `verificar_conexion_db()` (`:123`): `SELECT 1` y reconecta si falla.
- `abrir_conexion_aislada()` (`:100`): conexión+cursor propios; el docstring reconoce
  explícitamente una **condición de carrera** en `/estadisticas/*` cuando corren en paralelo con
  `/registros` y `/asistencias` desde el visor de mapa. Solo esos endpoints usan la conexión aislada.
- La bitácora (`sys_telemetry`) usa una **tercera** conexión dedicada (`_tel_conn`) con lock
  (`_tel_lock`).
- **Sin pool de conexiones. Sin transacciones por request. Sin `async` real en el acceso a datos.**

### 3.3 Migraciones

- No hay carpeta de migraciones ni Alembic. Al **importar el módulo** (`backend/main.py:202-460`)
  se ejecuta un bloque `try` que:
  - `CREATE TABLE IF NOT EXISTS admin_users` y siembra `admin/admin123` si está vacía;
  - bloques `DO $$ ... IF NOT EXISTS ... ALTER TABLE ADD COLUMN ...` para columnas de
    `admin_users` (`permisos`, `activo`, `es_territorial`, `territorio`, `usuario_id`),
    `usuarios` (`territorio`, `rol`) y `registros` (`categoria_actividad`, `categoria_actividad_otro`);
  - `CREATE TABLE IF NOT EXISTS facilitador_tecnico_asignaciones` + índices + backfill;
  - normalización única de `admin_users.cargo` a MAYÚSCULAS sin tildes (`:4634`).
- Otras tablas (`usuarios`, `registros`, `asistencias`, `reportes_generados`, `historial`,
  `notificaciones*`, `usuarios_terminos`) **se asumen preexistentes**: no hay `CREATE TABLE`
  para ellas salvo en el volcado SQL de `/descargar-bd-completa`.
- `POST /usuarios` y `PUT /usuarios/{id}` incluso ejecutan `ALTER TABLE usuarios ADD COLUMN rol`
  en caliente si detectan que falta (`:797`, `:4423`).

### 3.4 Endpoints (inventario resumido, ~150)

Prefijos y familias (línea de referencia en `backend/main.py`):

| Familia | Endpoints (muestra) | Auth aplicada |
|---|---|---|
| Salud | `GET /health` (x3, duplicado), `POST /sys/ping` | ninguna |
| Términos | `GET /usuarios/{id}/terminos`, `POST /usuarios/aceptar_terminos` | ninguna |
| Usuarios (técnicos) | `POST /usuarios` (`:735`), `GET /usuarios` (`:4169`), `GET/PUT /usuarios/{id}`, `PATCH /usuarios/{id}/info|estado|territorio|rol|cargo|password`, `DELETE /usuarios/{id}` (`:4797`), `GET /usuarios/buscar`, `GET /usuarios/buscar-curp/{curp}` (`:9980`), `POST /usuarios/transferir-actividades` (`:10048`), `GET /api/buscar-usuarios` (`:11455`) | **ninguna** |
| Login técnico | `POST /login` (`:899`), `POST /verificar_contrasena`, `POST /cambiar_contrasena` | texto plano |
| Dispositivos | `POST /actualizar_dispositivo`, `GET /estadisticas/dispositivos` | ninguna |
| Actividades | `POST /registro` (`:1139`), `GET /registros` (`:1238`), `GET /admin/registros` (`:1370`), `PUT /api/registros/{id}`, `DELETE /admin/registros/{id}`, `DELETE /admin/registros/all` | ninguna |
| Jornada / asistencia | `POST /asistencia/entrada` (`:5259`), `POST /asistencia/salida` (`:5349`), `GET /asistencia/hoy/{id}`, `GET /asistencias`, `PUT/DELETE /admin/asistencias/{id}`, `DELETE /admin/asistencias/all` | ninguna |
| Estadísticas | `GET /estadisticas`, `/estadisticas/rapidas`, `/dia-actual`, `/usuarios-dia`, `/entradas-dia`, `/salidas-dia`, `/actividades-dia`, `/tipo-actividad` | ninguna |
| Reportes | `POST /reportes/guardar` (`:2144`), `GET /reportes/verificar/{id}`, `/reportes/historial/{id}`, `DELETE /reportes/eliminar/{id}`, `GET /reportes/descargar/{id}`, `POST /reportes/firmar/{id}` (`:2501`), `DELETE /reportes/quitar-firma/{id}`, `GET /reportes/facilitador/mis-reportes`, `GET /reportes/admin/todos`, `/reportes/admin/descargar-zip`, `/reportes/admin/estadisticas[-pdf]` | mixta / parcial |
| Facilitador–técnico | `GET /facilitadores/mis-tecnicos`, `/tecnicos-disponibles`, `POST/DELETE /facilitadores/asignar-tecnico`, `GET /facilitadores/buscar-publico`, `POST /usuarios/{id}/cambiar-facilitador`, `GET /usuarios/{id}/facilitador-asignado`, `/supervisor-automatico`, `POST /actualizar-supervisores-tecnicos`, `GET /supervisor-territorio/{territorio}` | parcial (solo `firmar` valida) |
| Territorios | `GET /territorios-sembrando-vida`, `GET /estados-mexico` (deprecado, alias), `POST /admin/reset-territorios` | ninguna |
| Admin auth | `POST /admin/login` (`:4942`), `GET /auth/me` (`:5043`, **stub**), `GET /auth/check-active/{u}`, `/auth/check-session/{u}` (`:5091`), `/auth/check-permission/{p}` (`:5147`, **stub**), `GET /admin/auth/validar`, `GET /auth/validar` | JWT solo en `/admin/login` |
| Admin usuarios | `GET/POST /admin/usuarios`, `GET/PUT/DELETE /admin/usuarios/{id}`, `PUT /admin/usuarios/{id}/rol|password`, `PATCH .../estado`, `GET /admin/usuarios/estadisticas|buscar`, `GET /admin/cargos-catalogo` | **ninguna real** (el frontend manda `Bearer` pero el backend no lo verifica) |
| Notificaciones | `POST /notificaciones`, `GET /notificaciones[...]`, `/unread_count`, `/list`, `GET/PUT/DELETE /notificaciones/{id}`, `POST /notificaciones/{id}/leer`, `/notificaciones/{id}/archivo[/base64|/mobile]`, `/estadisticas`, `/usuario/{id}` | ninguna |
| Manuales | `POST /manuales`, `GET /manuales[...]`, `/manuales/{id}/archivo|imagen|video`, `POST /manuales/{id}/leer`, `GET /estadisticas`, `PUT/DELETE /manuales/{id}` | ninguna |
| Historial (bitácora de perfil) | `POST /historial`, `GET /historial[/{id}|/resumen/{id}]` | ninguna |
| Imágenes / mantenimiento | `GET /fotos-base64/{path}`, `POST /admin/buscar-imagen-similar` (`:9077`), `DELETE /imagenes/eliminar-todas`, `DELETE|POST /imagenes/eliminar-por-fecha` | ninguna |
| Volcado masivo | `GET /descargar-bd-completa` (`:9623`), `GET /exportar-registros-csv` (`:9867`), `DELETE /admin/usuarios/all` (`:5924`) | **ninguna** |
| Debug (en producción) | `GET /debug/tiempo-actual`, `/debug/problema-fecha-actual`, `/debug/fecha-zona-horaria`, `POST /debug/test-*`, `GET /debug/usuarios-estructura`, `/debug/asistencias-estructura` | ninguna |
| Bitácora observador | `POST /sys/status/auth` (`:11843`), `GET /sys/status/data|actions` | JWT propio con **secreto hardcodeado** |
| CORS catch-all | `OPTIONS /{path:path}` | — |

| Componente | Decisión |
|---|---|
| FastAPI como framework | **CONSERVAR** |
| psycopg2 SQL a mano, sin ORM | **ADAPTAR** (para módulos ECA: SQLAlchemy Core o al menos capa `repositories/`; migraciones con Alembic) |
| Conexión/cursor global | **REEMPLAZAR** (pool + sesión por request) — **bloqueante para escalar a 1 200 técnicos** |
| Migraciones "al importar" con `ALTER TABLE` en runtime | **REEMPLAZAR** (migraciones versionadas, regla 4/11 de `AGENTS.md`) |
| Endpoints `/debug/*` en producción | **REEMPLAZAR** (eliminar o proteger) |
| Endpoints de volcado sin auth | **REEMPLAZAR** (auth + rol + auditoría) |

---

## 4. Autenticación

### 4.1 PWA de técnicos — `POST /login` (`backend/main.py:899`)

```python
cursor.execute("SELECT id, correo, nombre_completo, cargo, contrasena, territorio, curp, supervisor, activo FROM usuarios WHERE correo = %s", (usuario.correo,))
if usuario.contrasena != user[4]:           # comparación de texto plano
    raise HTTPException(401, ...)
...
return { "id":..., "correo":..., "curp": user[6], ... }   # devuelve la CURP en claro
```

- **Contraseñas en texto plano** en `usuarios.contrasena`. No hay hash de verificación.
- `POST /cambiar_contrasena` (`:1105`) **sí** hashea con `bcrypt.hashpw` → el sistema queda
  con **credenciales mixtas** (unas en claro, otras bcrypt).
- `POST /verificar_contrasena` (`:1065`) intenta primero comparación plana y luego `bcrypt.checkpw`.
- No se emite token. La "sesión" es `localStorage.user` en el cliente, sin expiración.
- No se registra `ultimo_acceso` con éxito/fallo salvo `UPDATE usuarios SET ultimo_acceso`.

### 4.2 Panel admin — `POST /admin/login` (`backend/main.py:4942`)

- `admin_users.password` con **bcrypt** (`pwd_context.verify`). Correcto.
- Emite **JWT HS256** con `{sub, role, user_id, tipo, es_territorial, territorio}` y
  **sin `exp` (no expira)**. Firmado con `SECRET_KEY`.
- `SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esto-por-una-clave-muy-larga-y-unica")`
  → **fallback inseguro** si la env var falta.
- El token **no se valida en casi ningún endpoint**. `GET /auth/me` (`:5043`) es un **stub** que
  devuelve `{id:1, username:"admin", rol:"admin", is_authenticated:true}` **siempre**.
  `GET /auth/check-permission/{p}` (`:5147`) **siempre** concede (`user_role = "admin"` hardcodeado).
- La verificación "en tiempo real" (`admin-pwa/src/services/authService.js:startSessionCheck`,
  cada 5 s) sí consulta `GET /auth/check-session/{username}` que lee `admin_users` real
  (activo, rol, permisos, territorio) y fuerza logout/refresh si cambian. Pero es **client-side
  enforcement**: el backend no rechaza peticiones de un usuario desactivado en los endpoints de datos.

### 4.3 Bitácora observador — `/sys/status/*`

- `_SYS_OBSERVER_SECRET = "xK9#mP2$vL7@nQ4&wR6!tY3^uI8*oE5"` **hardcodeado** en `backend/main.py:11545`.
- `POST /sys/status/auth` valida contra `sys_observers.secret_hash` (bcrypt) y emite JWT de 7 días
  firmado con ese secreto.

| Componente | Decisión |
|---|---|
| Identidad basada en tabla `usuarios` | **CONSERVAR** (regla de `01_AUDITORIA`: identidad base) |
| Login de técnicos con contraseña en claro | **REEMPLAZAR** (bcrypt/argon2 + migración gradual de credenciales) — **bloqueante antes de cargar productores/CURP** |
| Emisión de token para la PWA de técnicos | **CREAR NUEVO** (hoy no existe token; ECA lo necesita para autorización real) |
| JWT de admin sin expiración + `SECRET_KEY` con fallback | **ADAPTAR** (añadir `exp`, refresh, exigir env var) |
| Verificación de sesión en tiempo real (`check-session`) | **ADAPTAR** (mover el enforcement al backend, mantener el patrón de invalidación) |
| `/auth/me` y `/auth/check-permission` stubs | **REEMPLAZAR** (implementar validación real de JWT + dependencia FastAPI `Depends(get_current_user)`) |
| `_SYS_OBSERVER_SECRET` hardcodeado | **REEMPLAZAR** (env var / secreto rotable) |

---

## 5. Creación y administración de usuarios

### 5.1 Dos tablas de identidad

| Tabla | Uso | Login | Hash |
|---|---|---|---|
| `usuarios` | Técnicos / personal de campo (PWA) | `POST /login` | **texto plano** |
| `admin_users` | Panel administrativo | `POST /admin/login` | bcrypt |

- Vínculo opcional: `admin_users.usuario_id → usuarios.id` (columna añadida por migración,
  `backend/main.py:349`). Se usa para que un facilitador con cuenta admin también exista como técnico.

### 5.2 `POST /usuarios` (`backend/main.py:735`)

- Valida: `rol ∈ {admin,user}`, CURP obligatoria (18 chars, `^[A-Z0-9]{18}$`, unicidad),
  teléfono obligatorio con formato `+<pais> <numero>`, correo único, territorio opcional
  (no valida contra la lista aquí).
- Inserta con **contraseña sin encriptar** (`:800-803`).
- Registra automáticamente aceptación de términos (`usuarios_terminos`).
- Si `facilitador_admin_id` viene y el cargo contiene `TECNICO`: crea fila en
  `facilitador_tecnico_asignaciones` (`ON CONFLICT ... DO UPDATE`) y setea `usuarios.supervisor`
  al nombre del facilitador.
- **Sin autenticación**: cualquiera puede crear usuarios (incluido `rol='admin'` de la tabla `usuarios`).

### 5.3 Administración

- `admin-pwa/src/views/UsuariosView.vue` (9 824 líneas) + `admin-pwa/src/services/usuariosService.js`
  (y `usuariosServiceAlternativo.js`).
- CRUD de `usuarios` vía `GET/PUT/PATCH/DELETE /usuarios/{id}` y `.../rol|estado|territorio|cargo|password`.
- CRUD de `admin_users` vía `/admin/usuarios*` (incluye `permisos` JSON, `es_territorial`,
  `territorio`, `cargo`, `curp`, `nombre_completo`).
- `DELETE /usuarios/{id}` (`:4797`) revisa dependencias en `registros`/`asistencias`.
- `POST /usuarios/transferir-actividades` (`:10048`) reasigna `registros`/`asistencias` de un
  usuario a otro (útil al depurar duplicados / bajas).
- `DELETE /admin/usuarios/all` (`:5924`) y `DELETE /admin/registros|asistencias/all`: borrado masivo sin auth.

| Componente | Decisión |
|---|---|
| Tabla `usuarios` como identidad de técnicos | **CONSERVAR** |
| Doble tabla `usuarios` / `admin_users` | **ADAPTAR** (mantener, pero unificar reglas de hash y auditoría; ECA añade roles/asignaciones, no una 3.ª tabla) |
| `POST /usuarios` sin auth | **REEMPLAZAR** (exigir rol autorizado) |
| Validación CURP/teléfono | **CONSERVAR / ADAPTAR** (reutilizar patrón para entidad `productor`, pero `productor` ≠ `usuarios`) |
| `transferir-actividades` | **CONSERVAR** (patrón útil para deduplicar) |
| Borrados masivos `.../all` | **REEMPLAZAR** (proteger o eliminar) |
| `UsuariosView.vue` 9.8k líneas | **ADAPTAR** (dividir; extender para asignación técnico–ECA) |

---

## 6. Roles y permisos

### 6.1 Modelo de roles

- `usuarios.rol ∈ {'user','admin'}` (`VARCHAR(10)`). Poco usado; el "rol de negocio" real es
  `usuarios.cargo` (texto libre: `TECNICO SOCIAL`, `TECNICO PRODUCTIVO`, `FACILITADOR`, ...).
- `admin_users.rol ∈ {'admin','user'}` (CHECK). Además:
  - `admin_users.permisos` = **JSON de booleanos** con claves fijas:
    `visor, asistencia, registros, registros_acciones, usuarios, usuarios_acciones, historiales,
    notificaciones, notificaciones_crear, notificaciones_acciones, permisos, configuracion,
    reportes, manuales` (`PERMISOS_ADMIN_DEFAULT` / `PERMISOS_USER_DEFAULT`, `backend/main.py:8449`).
    El código también referencia `firmas` y `estadisticas` que **no están** en los defaults.
  - `admin_users.es_territorial` (bool) + `admin_users.territorio` → restringe el panel a un territorio.
  - `admin_users.cargo` normalizado contra `CARGOS_ADMIN_CATALOGO` (`:4596`).

### 6.2 Aplicación de permisos

- **Toda la autorización es del lado del cliente.** `admin-pwa/src/services/authService.js`:
  `hasPermission(permiso)` lee `this.user.permisos[permiso]` desde `localStorage`;
  `router/index.js` bloquea rutas con `meta.requiredPermission`.
- El backend **no** revisa `permisos` salvo en `POST /reportes/firmar/{id}` (comprueba
  `permisos.get('firmas')` y cargo `FACILITADOR` y asignación activa — `backend/main.py:2540`).
- `GET /auth/check-permission/{permission}` existe pero es un stub que siempre concede.

| Componente | Decisión |
|---|---|
| `permisos` como JSON de flags en `admin_users` | **ADAPTAR** (sirve como base; añadir permisos ECA: `eca.gestion`, `formularios.publicar`, `productores.ver`, `levantamientos.ver`, jerarquía) |
| Enforcement solo en frontend | **REEMPLAZAR** (dependencia de autorización en backend por endpoint — regla 8 de `AGENTS.md`) |
| `usuarios.rol` (user/admin) | **ADAPTAR** (insuficiente; el rol de negocio real es `cargo`) |
| `cargo` como texto semilibre | **ADAPTAR** (catálogo persistido; hoy hay dos catálogos hardcodeados distintos) |
| Restricción territorial `es_territorial`/`territorio` | **ADAPTAR** (generalizar a "ámbito" jerárquico ECA) |

---

## 7. CURP

- **`usuarios.curp VARCHAR(18) UNIQUE`** (índice `idx_usuarios_curp`).
- Validación (en `POST /usuarios`, `PUT /usuarios/{id}`, `PATCH /usuarios/{id}/info`):
  `upper().strip()`, longitud exacta 18, regex `^[A-Z0-9]{18}$` (no valida dígito verificador ni
  estructura real de CURP), unicidad contra la tabla.
- Búsqueda: `GET /usuarios/buscar-curp/{curp}` (`:9980`), y `GET /api/buscar-usuarios?curp=`
  (`:11455`) con heurística: 18 chars alfanum → exacta; ≥13 → parcial `ILIKE %...%`.
- **La CURP se expone en claro** en respuestas: `POST /login`, `GET /usuarios*`,
  `GET /api/buscar-usuarios`, `GET /admin/usuarios*`, `POST /admin/buscar-imagen-similar`,
  volcado `/descargar-bd-completa`.
- `admin_users.curp` también existe (CURP del personal administrativo).
- No hay registro/enmascarado de CURP en logs, pero tampoco se loguea completa explícitamente
  (los `print` de creación no imprimen la CURP; sí aparece en payloads de respuesta).

| Componente | Decisión |
|---|---|
| Patrón de CURP única + validación de formato | **ADAPTAR** (reutilizar para deduplicar `productor`; `productor.curp` nullable, no todos los productores la tendrán) |
| CURP en `usuarios` | **CONSERVAR** (identidad del técnico) |
| Exposición de CURP en respuestas/listados | **REEMPLAZAR** (minimizar; enmascarar salvo permiso explícito) |
| Validación regex laxa | **ADAPTAR** (validación estructural de CURP + normalización) |

---

## 8. Territorios

- **Lista fija de 31 valores** `TERRITORIOS_SEMBRANDO_VIDA` (`backend/main.py:4560`), p. ej.
  `"Acapulco - Centro - Norte - Tierra Caliente"`, `"Balancán"`, `"Istmo"`, `"Oficinas Centrales"`.
- Columnas: `usuarios.territorio VARCHAR(100)` y `admin_users.territorio VARCHAR(100)` (ambas
  añadidas por migración, nullable).
- Endpoints: `GET /territorios-sembrando-vida`, `GET /estados-mexico` (**deprecado**, devuelve la
  misma lista), `PATCH /usuarios/{id}/territorio` (valida contra la lista),
  `POST /admin/reset-territorios` (pone todo a NULL para re-captura).
- Uso como **filtro de datos** en `GET /registros?territorio=`, `GET /admin/registros`,
  reportes admin, estadísticas y en `admin-pwa` (`authService.getTerritorioFilter()`).
- Uso jerárquico: el "supervisor automático" de un técnico se resuelve por su territorio
  (`GET /usuarios/{id}/supervisor-automatico`, `:10222`; `GET /supervisor-territorio/{territorio}`,
  `:10405`) buscando el `admin_users` con `es_territorial=TRUE AND territorio=<x>`.
- Frontend: `pwasuper/src/components/TerritorioModal.vue`, selección en `Register.vue` / `Profile.vue`.

| Componente | Decisión |
|---|---|
| Concepto "territorio" como lista fija SV | **REEMPLAZAR** (catálogo persistido y editable; el vocabulario ECA será distinto: estado / DDR / CADER / municipio o "ámbito") |
| Columna `territorio` en `usuarios`/`admin_users` | **ADAPTAR** (mantener aditivamente; mapear a nueva estructura de ámbito) |
| Filtro territorial en queries y panel | **ADAPTAR** (generalizar a filtro por ámbito/jerarquía ECA) |
| Resolución de supervisor por territorio | **ADAPTAR** (ver §9) |

---

## 9. Relaciones jerárquicas entre usuarios

Hay **tres mecanismos superpuestos y parcialmente redundantes**:

1. **`usuarios.supervisor VARCHAR(255)`** — nombre del supervisor **como texto** (no FK).
   Se rellena automáticamente al asignar facilitador o por territorio.
2. **`facilitador_tecnico_asignaciones`** (tabla real, `backend/main.py:361`):
   ```
   id BIGSERIAL PK
   facilitador_usuario_id  INT NULL  → usuarios(id)
   facilitador_admin_id    INT NULL  → admin_users(id)   (añadida después)
   tecnico_usuario_id      INT NOT NULL → usuarios(id)
   origen ∈ {'csv','manual'}
   activo BOOLEAN
   created_at / updated_at / created_by_admin_user_id
   CHECK (facilitador_usuario_id IS NOT NULL OR facilitador_admin_id IS NOT NULL)
   índices únicos parciales por (facilitador_*, tecnico_usuario_id)
   ```
   Endpoints: `/facilitadores/mis-tecnicos`, `/tecnicos-disponibles`,
   `POST|DELETE /facilitadores/asignar-tecnico`, `POST /usuarios/{id}/cambiar-facilitador`,
   `GET /usuarios/{id}/facilitador-asignado`.
3. **Jerarquía por territorio** — `admin_users.es_territorial` + `territorio` actúa como nivel
   coordinador sobre los técnicos de ese territorio (`supervisor-automatico`,
   `actualizar-supervisores-tecnicos` masivo).

- No hay un árbol jerárquico formal (niveles, `parent_id`), ni tabla de "estructura organizativa".
- El cargo (`TECNICO SOCIAL`, `TECNICO PRODUCTIVO`, `FACILITADOR`, coordinaciones) es el que
  define el "nivel" de forma implícita.

| Componente | Decisión |
|---|---|
| `usuarios.supervisor` como texto | **REEMPLAZAR** (no es relación; usar FK / tabla de asignación) |
| `facilitador_tecnico_asignaciones` | **ADAPTAR** (buen patrón de asignación N:M con `activo`/`origen`; ECA necesita `asignacion_tecnico_eca` análoga, y quizá jerarquía multinivel) |
| Jerarquía implícita por territorio + cargo | **REEMPLAZAR** (modelo explícito de jerarquía / ámbito ECA con niveles) |
| `origen ∈ {csv,manual}` + carga CSV | **CONSERVAR** (patrón de import masivo reutilizable para 1 200 técnicos) |

---

## 10. Jornadas

- **No existe tabla `jornadas`.** La jornada es la tabla **`asistencias`**:
  ```
  asistencias(
    id, usuario_id → usuarios(id),
    fecha DATE,
    hora_entrada TIMESTAMP, hora_salida TIMESTAMP,
    latitud_entrada, longitud_entrada, latitud_salida, longitud_salida,
    foto_entrada_url, foto_salida_url,
    descripcion_entrada TEXT, descripcion_salida TEXT,
    created_at
  )
  ```
- `POST /asistencia/entrada` (`:5259`): **1 fila por `usuario_id`+`fecha`**; si ya existe →
  `400 "ya tiene registro de entrada para el día"`. Requiere **foto obligatoria** (`File(...)`).
- `POST /asistencia/salida` (`:5349`): busca la fila del día; si no hay entrada → error; si ya hay
  salida → error. Requiere **foto obligatoria**.
- Estado del día en el cliente: `localStorage[`asistencia_${userId}_${fechaCDMX}`]` +
  `localStorage[`asistencia_ultima_fecha_${userId}`]`, con limpieza de días anteriores
  (`Home.vue:2794`).
- Zona horaria: todo se calcula en **America/Mexico_City** vía `obtener_fecha_hora_cdmx()`
  (`:5185`); las fechas se guardan **naive en hora CDMX** y al serializar se les añade `-06:00`
  manualmente (`GET /registros`, `:1330`) — **frágil ante horario de verano / cambios de offset**.
- Decisiones ECA ya acordadas (`00_START_HERE.md`): mantener inicio/fin, **quitar foto y
  descripción obligatorias**, revisar utilidad del GPS de jornada.

| Componente | Decisión |
|---|---|
| Tabla `asistencias` (marco temporal día) | **ADAPTAR** (mantener; hacer foto y descripción opcionales; renombrar conceptualmente a "jornada" sin migración destructiva) |
| Regla "1 por día" (dedup natural por `usuario_id`+`fecha`) | **CONSERVAR** (es el mecanismo de idempotencia que hoy sí funciona para jornada) |
| Foto/descr. obligatorias en entrada/salida | **REEMPLAZAR** (quitar obligatoriedad) |
| Manejo de zona horaria (`-06:00` fijo) | **REEMPLAZAR** (usar `TIMESTAMPTZ` / UTC + conversión en presentación) |
| Estado de jornada en `localStorage` | **ADAPTAR** (mover a IndexedDB / store; sincronizar con backend como fuente de verdad) |

---

## 11. Actividades

### 11.1 Modelo (`registros`)

```
registros(
  id SERIAL PK,
  usuario_id INT → usuarios(id),
  latitud DECIMAL(10,8), longitud DECIMAL(11,8),
  descripcion TEXT,
  foto_url VARCHAR(500),           -- ruta en disco: backend/fotos/<archivo>
  fecha_hora TIMESTAMP NOT NULL,   -- naive, hora CDMX
  tipo_actividad VARCHAR(50) DEFAULT 'campo',        -- MODALIDAD: 'campo' | 'gabinete'
  categoria_actividad VARCHAR(100),                  -- "tipo de actividad" (catálogo hardcodeado)
  categoria_actividad_otro VARCHAR(255),
  created_at TIMESTAMP DEFAULT now()
)
```

> Nota de nomenclatura confusa: `tipo_actividad` = **modalidad** (campo/gabinete);
> `categoria_actividad` = **tipo/categoría** de actividad.

### 11.2 `POST /registro` (`backend/main.py:1139`)

- `multipart/form-data`, **foto obligatoria** (`File(...)`), **sin autenticación**.
- No recibe ni valida `usuario_id` contra sesión (viene como `Form`).
- **No hay clave de idempotencia**: ignora `X-Offline-ID`, `id_offline`, `id_cliente`.
  Cada POST hace un `INSERT` nuevo → un reintento de sync **duplica la actividad**.
- Guarda la foto en disco con nombre `f"{usuario_id}_{timestamp}_{ms%100000}_{rand4}{ext}"`.
- Asigna valores por defecto de Sembrando Vida si faltan/invalidan modalidad o categoría.
- **No persiste precisión GPS, `jornada_id`, ni datos de ECA/tema.**

### 11.3 Cliente (`Home.vue`)

- Online: `axios.post('/registro', formData)` con `timestamp_offline` = timestamp CDMX del cliente.
- Offline o error de red: `offlineService.guardarRegistroOffline(...)` en IndexedDB.
- **La precisión GPS (`accuracy`) se calcula y se loguea pero nunca se envía** (`Home.vue:1986`).

| Componente | Decisión |
|---|---|
| Tabla `registros` | **ADAPTAR** (base de la actividad ECA; añadir aditivamente `uuid`, `precision_gps`, `jornada_id`, `eca_id`, `modalidad_id`, `tipo_actividad_id`, `tema_id`, `resultado`, `estado_sync`, `updated_at`) |
| Fotos 1:1 embebidas en `registros.foto_url` | **REEMPLAZAR** (tabla `actividad_evidencia` 1..N — `01_AUDITORIA` §6) |
| `POST /registro` sin auth ni idempotencia | **REEMPLAZAR** (auth + `uuid` cliente + `UNIQUE` servidor + upsert idempotente — reglas 9/10 de `AGENTS.md`) |
| Nomenclatura `tipo_actividad` vs `categoria_actividad` | **ADAPTAR** (renombrar a modalidad/tipo/tema con catálogos) |
| Precisión GPS no enviada | **ADAPTAR** (enviar y persistir) |

---

## 12. Categorías

- **Catálogo de "categoría de actividad" hardcodeado y DUPLICADO** en dos lugares:
  - `backend/main.py:1168` (`categorias_validas` en `POST /registro`),
  - `pwasuper/src/services/syncService.js:504` (misma lista, para reintentos offline).
  Valores: `Acompañamiento técnico`, `Productivas directas`, `Ahorro y trámites financieros`,
  `Capacitación / talleres / cursos`, `Difusión y comunicación`,
  `Eventos comunitarios / ferias / tianguis`, `Reuniones y asambleas`,
  `Trabajo administrativo y captura`, `Viveros y biofábricas`, `Otro`.
- Modalidad: lista cerrada `['campo','gabinete']` en backend y cliente.
- Otros "catálogos" hardcodeados: `TERRITORIOS_SEMBRANDO_VIDA` (31), `CARGOS_ADMIN_CATALOGO` (13),
  claves de `PERMISOS_*`.
- **No hay tablas de catálogo en BD.** No se pueden activar/desactivar valores sin desplegar código.

| Componente | Decisión |
|---|---|
| Catálogo de categorías en código (x2) | **REEMPLAZAR** (tablas `modalidad`, `tipo_actividad`, `tema` en BD, con `activo`, endpoints de lectura, cache offline) |
| Catálogos de territorios/cargos/permisos hardcodeados | **REEMPLAZAR / ADAPTAR** (persistir; versionar) |

---

## 13. Geolocalización

- Cliente: `pwasuper/src/services/geoLocationService.js` (+ `geoLocationSimple.js`, `debugGeoLocation.js`).
  - `navigator.geolocation.getCurrentPosition` con varias configuraciones de `enableHighAccuracy`/
    `timeout`/`maximumAge` probadas en cascada (`Home.vue:1831`, `:1973`).
  - Cache en `localStorage['geoLocationCache']` (`lastKnownLocation` + hasta 50 ubicaciones).
  - **Ubicación por defecto** (centro de México aprox.) si el navegador no da permiso/soporte
    (`setDefaultLocation()`) → riesgo de registros con coordenadas ficticias.
  - Clasifica calidad por `accuracy` (≤10 excelente … >100 baja) pero **no bloquea** el registro
    por baja precisión.
- Servidor: solo almacena `latitud`/`longitud` (`DECIMAL`). **No guarda `accuracy`.**
- Visor de mapas: `admin-pwa` con Leaflet + Mapbox GL (`VisorMap.vue`, `VisorView.vue`),
  `pwasuper` con Leaflet.
- `GEOLOCALIZACION_OFFLINE.md` y `MEJORAS_GEOLOCALIZACION.md` documentan el diseño.

| Componente | Decisión |
|---|---|
| Captura GPS multi-intento en cliente | **CONSERVAR / ADAPTAR** (buena base; añadir envío de `accuracy`) |
| Ubicación por defecto silenciosa | **REEMPLAZAR** (marcar explícitamente "sin GPS"; no inventar coordenadas) |
| No persistir precisión | **ADAPTAR** (persistir `precision_gps` en actividad) |
| Leaflet + Mapbox mezclados en admin | **ADAPTAR** (unificar librería de mapa) |

---

## 14. Fotografías

- **Almacenamiento en disco del servidor**: carpeta `backend/fotos/` (`FOTOS_DIR`, `os.makedirs`),
  servida **públicamente y sin auth** vía `app.mount("/fotos", StaticFiles(directory="fotos"))`
  (`backend/main.py:640`). En `.gitignore`.
- `foto_url` en `registros` / `foto_entrada_url` / `foto_salida_url` en `asistencias` guardan la
  **ruta local completa** (`os.path.join(FOTOS_DIR, nombre)`), no una URL.
- Proxy base64: `GET /fotos-base64/{path}` (`:584`) con validación anti-path-traversal
  (`ruta_absoluta.startswith(ruta_base)`), para CORS en móviles.
- Compresión: **en cliente** — `pwasuper/src/utils/imageCompressor.js` y en `syncService.js`
  (`comprimirImagenBase64`: redimensiona a máx 1024 px, calidad 0.5, objetivo 400 KB).
- En offline las fotos se guardan como **base64 dentro de IndexedDB** (puede inflar mucho el store).
- `syncService` genera **imágenes placeholder "Sin imagen"** cuando la foto falla o falta, para
  no chocar con la obligatoriedad del backend (`crearImagenPlaceholder`, `:733`) → **evidencia
  falsa silenciosa**.
- Antifraude: `POST /admin/buscar-imagen-similar` (`:9077`) usa `imagehash.phash` para detectar
  fotos reutilizadas; recorre **todos** los registros con foto y abre cada archivo → O(n) en disco.
- Manuales / notificaciones guardan archivos como **BYTEA en PostgreSQL** (`manuales.video BYTEA`,
  etc.) — patrón distinto y pesado para la BD.

| Componente | Decisión |
|---|---|
| Fotos en filesystem local del backend | **ADAPTAR** (mantener a corto plazo; planificar object storage / S3 para 1 200 técnicos) |
| `/fotos` estático público sin auth | **REEMPLAZAR** (URLs firmadas / endpoint con autorización) |
| Ruta de disco guardada como `foto_url` | **ADAPTAR** (guardar id/clave relativa, no ruta absoluta) |
| Compresión en cliente | **CONSERVAR** |
| Placeholders "Sin imagen" automáticos | **REEMPLAZAR** (permitir actividad sin foto explícitamente; no falsear evidencia) |
| `phash` antifraude O(n) | **ADAPTAR** (persistir hash en columna, comparar en BD) |
| Archivos como BYTEA (manuales/notificaciones) | **ADAPTAR** (mover a storage) |

---

## 15. IndexedDB / funcionamiento offline / sincronización

### 15.1 IndexedDB (`pwasuper/src/services/offlineService.js`)

- DB `PWAOfflineDB`, **versión 1**. Object stores:
  - `registros_pendientes` (`keyPath: id` autoincrement; índices `timestamp`, `usuario_id`).
  - `asistencias_pendientes` (índices `timestamp`, `usuario_id`, `tipo`).
- Registro offline (campos): `usuario_id, latitud, longitud, descripcion, tipo_actividad,
  categoria_actividad, categoria_actividad_otro, foto_base64, foto_filename, foto_type,
  timestamp, sync_timestamp, tipo:'actividad', fecha_creacion, intentos:0, estado:'pendiente',
  origen:'pwa_super', id_cliente:'reg_<epoch>_<rand>'`.
- Asistencia offline: `usuario_id, tipo:'entrada'|'salida', latitud, longitud, descripcion,
  foto_base64, foto_filename, foto_type, timestamp, sync_timestamp, fecha` — **sin `id_cliente`,
  sin `intentos`, sin `estado`**.
- Solo `contarPendientes`, `obtenerRegistrosPendientes`, `eliminar*`, `limpiarTodo`.
  No hay purga de registros "muertos" (muchos intentos fallidos) ni límite de tamaño.

### 15.2 Flujo offline (`Home.vue`)

1. Se intenta el POST online directo.
2. Ante error `err.response` (4xx/5xx real) → se muestra el error y **no** se guarda offline.
3. Ante error de red / timeout / SSL / SW → se guarda en IndexedDB y se informa al usuario.
4. Si `checkInternetConnection()` da `false` de entrada → se guarda offline directamente.

### 15.3 Sincronización (`pwasuper/src/services/syncService.js`)

- Singleton. Listeners `window: 'online'/'offline'` + **polling cada 2 minutos** + verificación al
  iniciar la app + botón manual (`sincronizarManual`).
- Al recuperar conexión: espera 3 s, `checkInternetConnection`, luego `sincronizarTodo`.
- `sincronizarTodo`: procesa **de 1 en 1** (`chunkSize: 1`), reintentos `maxRetries: 3` con backoff
  lineal (`retryDelayBase * intento`), timeout adaptativo 30 s→120 s.
- Éxito → `eliminarRegistro(id)`. Fallo → incrementa `intentos`, guarda `ultimo_error`,
  `detalles_error`; **permanece en el store indefinidamente**.
- **Detección de duplicados = frágil**: solo si el backend responde `400` con un `detail` que
  contenga `"ya existe"`, `"duplicado"`, `"Ya registrado"`, `"ya registrada"`, etc.
  - Para **asistencias** funciona: `POST /asistencia/entrada` devuelve `400 "ya tiene registro..."`.
  - Para **actividades NO funciona**: `POST /registro` nunca detecta duplicados → **reintento tras
    timeout con respuesta perdida = actividad duplicada en BD**.
- `transformRequest: [(data) => data]`, `maxBodyLength: Infinity`; límite duro cliente: foto
  decodificada >10 MB → se descarta y se usa placeholder (evita `413` de nginx).

| Componente | Decisión |
|---|---|
| IndexedDB con stores por tipo + metadatos (`intentos`, `estado`, `origen`) | **CONSERVAR / ADAPTAR** (ampliar a stores ECA: actividades, productores, formularios, versiones, levantamientos, respuestas, evidencias) |
| `DB_VERSION = 1` sin estrategia de `onupgradeneeded` incremental | **ADAPTAR** (versionado de esquema IndexedDB planificado) |
| `id_cliente` `reg_<epoch>_<rand>`, no UUID, no enviado al servidor | **REEMPLAZAR** (UUID v4 estable en cliente, enviado y con `UNIQUE` en servidor — reglas 9/10) |
| Asistencias offline sin `id_cliente`/`intentos`/`estado` | **ADAPTAR** (homogeneizar metadatos) |
| Sync 1-a-1 con reintentos y backoff | **CONSERVAR / ADAPTAR** (añadir cola con idempotencia real; considerar batch) |
| Dedup por texto del mensaje de error | **REEMPLAZAR** (respuesta idempotente `200` con el recurso, o `409` estructurado) |
| Sin purga de pendientes "muertos" | **ADAPTAR** (política de descarte / alerta tras N intentos) |
| Placeholders de foto en sync | **REEMPLAZAR** (ver §14) |
| Polling cada 2 min por cliente | **ADAPTAR** (con 1 200 clientes = ~10 req/s solo de sync-check; usar backoff / eventos) |

---

## 16. Generación de reportes

### 16.1 Reporte mensual del técnico (`pwasuper/src/views/Reportes.vue`, 6 085 líneas)

- **PDF generado en el navegador**: `jsPDF` + `html2canvas` (captura el DOM del reporte) +
  `pdf-lib` (`PDFDocument`, para fusionar/insertar firmas).
- Flujo (`POST /reportes/guardar`, `backend/main.py:2144`): el cliente envía
  `datos_reporte` (JSON de actividades), `firma_usuario_base64` y opcionalmente `pdf_base64`.
  Se guarda en **`reportes_generados`**:
  ```
  reportes_generados(
    id, usuario_id, nombre_reporte, mes, anio, tipo ('PDF'|'CSV'),
    fecha_generacion, pdf_base64 TEXT, datos_reporte TEXT(json),
    firma_usuario_base64 TEXT, firmado_supervisor BOOL, nombre_supervisor,
    firma_supervisor_base64, fecha_firma_supervisor, ...
  )
  ```
- **Regla "1 reporte por mes/año por usuario"**: `POST /reportes/guardar` responde `409` si ya
  existe (`WHERE usuario_id=%s AND mes=%s AND anio=%s`). Es la idempotencia efectiva de reportes.
- `GET /reportes/descargar/{id}`: regenera / entrega el PDF (con ambas firmas si ya está firmado).
- `mes` se guarda como **string** (nombre del mes) — filtros dependen de coincidencia exacta.

### 16.2 Reportes / estadísticas del panel admin

- `admin-pwa/src/views/ReportesView.vue` (7 684 líneas) + `EstadisticasView.vue` +
  `DashboardView.vue` + servicios (`reportesService`, `estadisticasService`, `analyticsService`,
  `asistenciasServiceOptimized`).
- Backend: `GET /reportes/admin/todos`, `/reportes/admin/descargar-zip` (ZIP de PDFs con
  `zipfile`), `/reportes/admin/estadisticas`, `/reportes/admin/estadisticas-pdf` (ReportLab),
  familia `/estadisticas/*`, `/exportar-registros-csv`, `/descargar-bd-completa`.
- `admin-pwa` también usa `xlsx` (SheetJS) y `jszip` para exportaciones.
- Cálculos: conteos simples sobre `registros` / `asistencias` (`COUNT`, `GROUP BY`,
  agrupación por día/tipo/territorio). **No hay "productores únicos" ni indicadores derivados de
  levantamientos** (no existen aún).

| Componente | Decisión |
|---|---|
| PDF de reporte del técnico en cliente (jsPDF/html2canvas) | **ADAPTAR** (frágil y pesado en móvil; evaluar generación server-side con ReportLab como en admin) |
| `reportes_generados` con `pdf_base64` + `datos_reporte` json en TEXT | **ADAPTAR** (mantener; para ECA los reportes deben calcularse desde datos transaccionales, no desde el JSON congelado del técnico) |
| Regla "1 reporte/mes" vía `409` | **CONSERVAR** (patrón de idempotencia válido) |
| `mes` como string | **REEMPLAZAR** (fecha/periodo numérico) |
| Estadísticas admin (COUNT/GROUP BY ad-hoc) | **ADAPTAR** (reescribir sobre modelo ECA: actividades, ECA atendidas, productores únicos desde levantamientos válidos, temas, mapas, filtros por jerarquía — `AGENTS.md` Fase G) |
| Exportaciones (CSV/XLSX/ZIP/BD completa) | **ADAPTAR** (conservar formatos; proteger con auth y filtrar por ámbito) |

---

## 17. Firmas

- **Firma digital = trazo en `<canvas>`** → `toDataURL()` PNG base64.
  Componentes: `pwasuper/src/components/FirmaDigital.vue`, `admin-pwa/src/components/FirmaDigitalAdmin.vue`.
- Se almacenan como base64 en `reportes_generados`:
  `firma_usuario_base64` (técnico), `firma_supervisor_base64` (facilitador/supervisor).
- **`POST /reportes/firmar/{reporte_id}`** (`backend/main.py:2501`) es **el único endpoint con
  autorización de negocio real**:
  - Si `admin_id` tiene `permisos.firmas` o `rol='admin'`, y `cargo` contiene `FACILITADOR`, y
    existe **asignación activa** en `facilitador_tecnico_asignaciones` entre ese facilitador y el
    técnico dueño del reporte → permite firmar. Si no → `403`.
  - Flujo "legacy supervisor" sin `admin_id`: menos estricto.
- `DELETE /reportes/quitar-firma/{id}` revierte la firma del supervisor.
- No hay firma criptográfica, sello de tiempo confiable, ni hash del contenido firmado: es una
  imagen de trazo + metadatos. No hay inmutabilidad garantizada del PDF firmado.

| Componente | Decisión |
|---|---|
| Captura de firma en canvas → base64 | **CONSERVAR** (UX válida) |
| Almacenamiento de firma en `reportes_generados` | **ADAPTAR** (para ECA: tabla de firmas/aprobaciones ligada a documento + versión) |
| Autorización de firma por asignación facilitador–técnico | **CONSERVAR / ADAPTAR** (patrón correcto; extender a jerarquía ECA) |
| Ausencia de integridad (hash/timestamp) del documento firmado | **ADAPTAR** (hash del contenido + fecha servidor; documento inmutable — regla 11) |

---

## 18. Componentes administrativos (`admin-pwa/`)

- **SPA Vue 3 + Vite** (no PWA, no offline). Servida como estáticos por nginx
  (`admin_nginx.conf`, `try_files ... /index.html`, `Cache-Control: no-store`).
- **Vistas** (líneas): `RegistrosView` 11 652, `UsuariosView` 9 824, `ConfiguracionView` 9 673,
  `ReportesView` 7 684, `PermisosView` 6 480, `VisorMap` 6 201, `VisorView` 5 948,
  `HistorialesView` 5 825, `NotificacionesView` 5 764, `ManualesView` 4 932, `AsistenciaView` 3 592,
  `DashboardView` 3 459, `EstadisticasView` 1 953, `LoginView` 121.
- **Servicios**: ~30 archivos; varios pares duplicados/alternativos
  (`usuariosService` + `usuariosServiceAlternativo`, `permisosService` + `permisosServiceSimple`,
  `asistenciasService` + `asistenciasServiceOptimized`).
- **Realtime**: `useRealtimeStats.js`, `healthCheckService.js`, `authService.startSessionCheck`
  (polling 5 s), `analyticsService` (envía eventos a `/sys/ping`).
- **Auth cliente**: `admin_token` (JWT) + `admin_user_data` en `localStorage`. Todo el gating de
  navegación y de acciones es client-side (`hasPermission`).
- **Librerías pesadas**: `mapbox-gl`, `leaflet`, `xlsx`, `jszip`, `jspdf`, `pdf-lib`,
  `file-saver` — todo en el bundle del panel.
- **Ruido**: `src/consultar-openapi.js`, `descubrir-api.js`, `probar-*.js`, `test-*.js`,
  `verificar-api-conexion.js` (scripts de exploración de API commiteados en `src/`).
- **Config**: `admin-pwa/.env.example` → `VITE_API_URL`.

| Componente | Decisión |
|---|---|
| Panel admin Vue 3 + Vite | **CONSERVAR / ADAPTAR** (extender con módulos ECA: catálogos, ECA, formularios, levantamientos, reportes ECA) |
| Vistas de 6k–11k líneas | **ADAPTAR** (dividir en componentes; no crecerlas más) |
| Servicios duplicados / scripts sueltos en `src/` | **REEMPLAZAR** (consolidar y limpiar) |
| Autorización solo en cliente | **REEMPLAZAR** (backend) |
| Polling 5 s de sesión por cada admin | **ADAPTAR** (aceptable a baja escala de admins; revisar) |

---

## 19. Variables / configuración relacionadas con Sembrando Vida

| Referencia | Ubicación | Tipo |
|---|---|---|
| `TERRITORIOS_SEMBRANDO_VIDA` (31 valores) | `backend/main.py:4560` | catálogo hardcodeado |
| `GET /territorios-sembrando-vida`, `GET /estados-mexico` (alias deprecado) | `backend/main.py:4753`, `:4759` | endpoints |
| CORS: `app.sembrandodatos.com`, `apipwa.sembrandodatos.com`, `admin.sembrandodatos.com`, `ubicacion.sembrandodatos.com` | `backend/main.py:39-47` | dominios de producción |
| `DB_NAME = "agricultura_db"` (default) / comentarios "app_registros" / "PWASV" | `backend/main.py:64`, `:9643`; `start.js` | nombres heredados |
| `admin-pwa` `name: "admin-pwa-sembrando-vida"`, `pwasuper` `name: "pwasv"` | `package.json` | metadatos |
| Categorías de actividad SV (x2), `CARGOS_ADMIN_CATALOGO` (FACILITADOR, COORDINACION TERRITORIAL...) | `backend/main.py:1168`, `:4596`, `syncService.js:504` | catálogos hardcodeados |
| `usuarios.supervisor`, "supervisor territorial", "facilitador comunitario" | múltiples endpoints | modelo de negocio SV |
| `caché app-cache-v1.0.6`, `origen: 'pwa_super'`, cadenas "Sembrando Vida" en textos UI | `vite.config.js`, `offlineService.js`, vistas | strings |
| Imágenes `logosv.png`, `fondoverde.jpeg`, `superior*.png`, flor de nochebuena | `pwasuper/images/`, `PoinsettiaFlower.vue` | branding |
| `admin_nginx.conf` → `admin.sembrandodatos.com` | raíz | infraestructura |

| Componente | Decisión |
|---|---|
| Catálogos y listas SV hardcodeados | **REEMPLAZAR** (catálogos ECA en BD) |
| Dominios / nombres de BD / branding SV | **ADAPTAR** (parametrizar por entorno; nuevo branding ECA) |
| Relación facilitador–técnico como concepto | **ADAPTAR** (mapear a jerarquía/asignación ECA) |

---

## 20. Riesgos de seguridad

> Prioridad **antes** de cargar productores/CURP (coherente con `01_AUDITORIA` §10).

1. **Contraseñas de técnicos en texto plano** (`usuarios.contrasena`); login por comparación
   directa (`backend/main.py:909`). Credenciales mixtas (algunas bcrypt vía `/cambiar_contrasena`).
2. **Casi ningún endpoint de datos exige autenticación.** `POST /usuarios`, `GET /usuarios`,
   `POST /registro`, `GET /registros`, `/asistencia/*`, `/admin/usuarios*`, `/notificaciones*`,
   `/manuales*`, `/historial*`, `/estadisticas*` son accesibles sin token.
3. **`GET /descargar-bd-completa`** (`:9623`): vuelca **toda** la BD (incluidas contraseñas en
   claro y CURPs) en SQL, **sin autenticación**. `GET /exportar-registros-csv` y
   `DELETE /admin/usuarios/all`, `DELETE /admin/registros|asistencias/all` idem.
4. **Autorización 100 % en el cliente** (admin-pwa). `GET /auth/me` y
   `GET /auth/check-permission` son stubs que siempre conceden admin.
5. **JWT de admin sin expiración** (`:5007`) + `SECRET_KEY` con **fallback hardcodeado** (`:60`).
6. **`_SYS_OBSERVER_SECRET` hardcodeado** en el repo (`:11545`).
7. **CORS `allow_origins=["*"]` junto con `allow_credentials=True`** (`:39-51`) — configuración
   contradictoria/insegura.
8. **CURP y datos personales expuestos** en múltiples respuestas y en `/fotos` público
   (`app.mount("/fotos", StaticFiles(...))`, sin auth, rutas predecibles).
9. **`/debug/*` en producción** (estructura de tablas, pruebas de fecha, etc.).
10. **`usuario_id` no ligado a sesión** en `POST /registro` y `/asistencia/*`: se puede registrar
    actividad "como" cualquier usuario.
11. **Contraseña por defecto `admin/admin123`** creada automáticamente si `admin_users` está vacía
    (`:223`).
12. **SQL dinámico**: la mayoría parametrizado, pero hay concatenación de `WHERE`/`ORDER BY`
    construidos con listas internas (no input directo) — revisar `GET /registros`, `/admin/registros`,
    `/api/buscar-usuarios`, `sys/status/data` para asegurar que ningún parámetro string entre por f-string.
13. **`X-Forwarded-For` confiado sin validar** para IP de auditoría (`:4945`).
14. **Sin rate limiting** en login ni en endpoints de escritura.

| Riesgo | Decisión |
|---|---|
| Todos los de §20 | **REEMPLAZAR / CORREGIR** en Fase A (`AGENTS.md`) antes de cargar datos sensibles ECA |

---

## 21. Riesgos de concurrencia

1. **`conn`/`cursor` globales compartidos entre threads** (`backend/main.py:69`). FastAPI corre
   los endpoints `def` (no `async`) en un threadpool → dos requests pueden ejecutar
   `cursor.execute()`/`fetch*()` sobre el **mismo cursor** simultáneamente. El propio código lo
   documenta como causa de "estadísticas en cero intermitentes" (`:100-113`).
2. **Parche parcial**: solo `/estadisticas/*` usan `abrir_conexion_aislada()`. El resto
   (incluido `/registro`, `/asistencia/*`, `/usuarios*`) sigue con el cursor global.
3. **`commit`/`rollback` globales**: un `rollback` disparado por el error de un request puede
   abortar la transacción en curso de otro request.
4. **`asistencia/entrada`**: check-then-insert (`SELECT ... ; if existe: 400 ; INSERT`) **sin
   `UNIQUE` ni transacción atómica** → dos requests concurrentes del mismo usuario pueden crear
   dos filas del mismo día (carrera). Mitigado en la práctica por baja frecuencia.
5. **`/registro`**: sin idempotencia → ráfagas de reintentos de sync generan inserciones múltiples.
6. **`facilitador_tecnico_asignaciones`**: sí tiene índices únicos parciales + `ON CONFLICT`
   (bien).
7. **Migraciones "al importar"**: si se lanzan varios workers, todos ejecutan los `ALTER TABLE`
   / `CREATE TABLE IF NOT EXISTS` a la vez → posibles errores de arranque.
8. **Un solo proceso uvicorn sin workers** → no escala CPU, pero "esconde" el problema de
   cursor global mientras haya poca carga. Al escalar a 1 200 técnicos habrá que añadir workers
   y ahí el cursor global **rompe**.

| Riesgo | Decisión |
|---|---|
| Cursor/conn global | **REEMPLAZAR** (pool `psycopg2.pool` o SQLAlchemy; conexión por request) — **prerequisito para escalar** |
| Check-then-insert sin `UNIQUE` (asistencias, actividades) | **REEMPLAZAR** (constraints `UNIQUE` + upsert idempotente) |
| Migraciones en runtime multi-worker | **REEMPLAZAR** (migraciones fuera del ciclo de request) |

---

## 22. Acoplamientos fuertes

1. **`backend/main.py` monolítico**: modelos + migraciones + auth + SQL + 150 endpoints +
   reportes + reglas en un archivo. Cambiar algo de usuarios roza reportes, estadísticas, etc.
2. **Catálogo de categorías duplicado** backend ↔ `syncService.js` (hay que editar dos sitios).
3. **`Home.vue`** acopla jornada + actividad + GPS + imágenes + IndexedDB + sincronización + UI.
4. **Zona horaria CDMX** incrustada en decenas de funciones (`obtener_fecha_hora_cdmx`, sufijo
   `-06:00` manual). Cambiar el modelo de fecha toca todo.
5. **`usuarios.supervisor` (texto)** se sincroniza a mano desde 3 flujos distintos (creación,
   cambio de facilitador, territorio, actualización masiva).
6. **Fotos**: la ruta de disco absoluta se guarda en la fila; mover el storage obliga a migrar datos.
7. **Frontend ↔ contrato implícito**: no hay OpenAPI usado como fuente; el `admin-pwa` tiene
   scripts para "descubrir" la API. Los campos se acoplan por nombre string en FormData.
8. **`admin-pwa`** depende de que el backend **no** valide permisos (si se activa la validación,
   hay que revisar cada vista).
9. **Idempotencia de sync** acoplada al **texto** de los mensajes de error del backend.
10. **`reportes_generados.datos_reporte`** congela un JSON producido por el cliente → el reporte
    no refleja correcciones posteriores de datos.

| Acoplamiento | Decisión |
|---|---|
| Monolito / `Home.vue` / catálogos duplicados | **ADAPTAR** (modularizar; catálogos en BD; módulos ECA separados) |
| Fecha CDMX incrustada | **REEMPLAZAR** (UTC + capa de presentación) |
| `supervisor` texto multi-origen | **REEMPLAZAR** (relación única) |
| Contrato API implícito por strings | **ADAPTAR** (esquemas Pydantic + OpenAPI como contrato; tipos compartidos) |

---

## 23. Escalabilidad a ~1 200 técnicos

Estimación de carga (asunciones: 1 técnico ≈ 1 jornada + 5–15 actividades/día, foto ~300 KB
comprimida):

| Área | Estado actual | Riesgo a 1 200 | Acción |
|---|---|---|---|
| Backend | 1 proceso uvicorn, cursor global | **Alto** — no escala CPU; añadir workers rompe el cursor global | Pool + workers + conexión por request |
| Base de datos | Sin pool, sin transacciones por request, índices básicos (`correo`, `curp`, `usuario_id`, `fecha_hora`, `fecha`) | Medio-alto — conexiones agotadas, locks, secuencial | Pooling (pgbouncer), revisar índices para filtros por territorio/fecha/usuario |
| Sync | Polling cada 2 min × 1 200 + reintentos + `checkInternetConnection` (`/health`) | **Alto** — ~10–20 req/s de fondo solo en "estoy vivo"; picos al volver señal a zonas rurales | Backoff, jitter, endpoint de sync batch idempotente, cola |
| Fotos | Filesystem local del backend, servidas estáticas | **Alto** — miles de archivos/día en un disco; sin CDN; backups pesados | Object storage + CDN + URLs firmadas |
| `/registros` sin `usuario_id` | `LIMIT 5000`, devuelve todo para el visor de mapa | Alto — payloads enormes, GZip mitiga parcialmente | Paginación obligatoria, tiles/clustering server-side |
| `/admin/buscar-imagen-similar` | O(n) sobre todas las fotos en disco por request | **Muy alto** — inutilizable con cientos de miles de fotos | Persistir `phash` en columna; comparación en BD / índice |
| `/descargar-bd-completa` | Serializa toda la BD en memoria-stream | Alto — bloquea, timeouts | Eliminar o reemplazar por `pg_dump` administrado |
| Reportes PDF en cliente | `html2canvas` + `jsPDF` en móviles de gama baja | Medio — lentitud, cuelgues | Generación server-side |
| IndexedDB | base64 de fotos, sin purga, `DB_VERSION` 1 | Medio — cuota de almacenamiento del navegador, registros zombie | Guardar `Blob` en vez de base64; purga; versionado |
| Notificaciones/manuales BYTEA | Archivos en PostgreSQL | Medio — infla la BD y los backups | Mover a storage |
| Auditoría `sys_telemetry` | Insert por acción, conexión dedicada con lock | Medio — el lock serializa; crecimiento de tabla | Particionar / retención; escritura asíncrona |

---

## 24. Modelo de datos inferido (tablas reales)

> Reconstruido desde `INSERT/SELECT/CREATE` en `backend/main.py` y el volcado de
> `/descargar-bd-completa`. Los tipos de las tablas sin `CREATE TABLE` explícito son aproximados.

| Tabla | Columnas conocidas | Notas |
|---|---|---|
| **usuarios** | `id PK`, `correo UNIQUE`, `nombre_completo`, `cargo`, `supervisor` (texto), `contrasena` (**texto plano**), `curp VARCHAR(18) UNIQUE`, `telefono`, `rol VARCHAR(10) DEFAULT 'user'`, `territorio VARCHAR(100)`, `activo BOOLEAN`, `created_at`, `ultimo_acceso`, `dispositivo`, `user_agent` | Identidad de técnicos |
| **admin_users** | `id PK`, `username UNIQUE`, `password` (bcrypt), `rol CHECK(admin,user)`, `activo BOOLEAN`, `permisos TEXT`(json), `es_territorial BOOLEAN`, `territorio VARCHAR(100)`, `usuario_id → usuarios(id)`, `nombre_completo`, `curp`, `cargo`, `created_at` | Identidad de panel; creada por la app |
| **registros** | `id PK`, `usuario_id → usuarios(id)`, `latitud DECIMAL(10,8)`, `longitud DECIMAL(11,8)`, `descripcion TEXT`, `foto_url VARCHAR(500)`, `fecha_hora TIMESTAMP`, `tipo_actividad VARCHAR(50)` (modalidad), `categoria_actividad VARCHAR(100)`, `categoria_actividad_otro VARCHAR(255)`, `created_at` | Actividades |
| **asistencias** | `id PK`, `usuario_id → usuarios(id)`, `fecha DATE`, `hora_entrada`, `hora_salida`, `latitud_entrada/longitud_entrada`, `latitud_salida/longitud_salida`, `foto_entrada_url`, `foto_salida_url`, `descripcion_entrada`, `descripcion_salida`, `created_at` | "Jornada"; 1 por (usuario, fecha) |
| **facilitador_tecnico_asignaciones** | `id BIGSERIAL PK`, `facilitador_usuario_id NULL`, `facilitador_admin_id NULL`, `tecnico_usuario_id NOT NULL`, `origen CHECK(csv,manual)`, `activo BOOLEAN`, `created_at`, `updated_at`, `created_by_admin_user_id`, índices únicos parciales | Asignación N:M jerárquica |
| **reportes_generados** | `id PK`, `usuario_id`, `nombre_reporte`, `mes` (texto), `anio INT`, `tipo`('PDF'/'CSV'), `fecha_generacion`, `pdf_base64 TEXT`, `datos_reporte TEXT`(json), `firma_usuario_base64 TEXT`, `firmado_supervisor BOOLEAN`, `nombre_supervisor`, `firma_supervisor_base64`, `fecha_firma_supervisor` | 1 por (usuario, mes, anio) |
| **usuarios_terminos** | `id PK`, `usuario_id UNIQUE → usuarios(id)`, `aceptado BOOLEAN`, `fecha_aceptado` | Aviso de privacidad |
| **historial** | `id PK`, `usuario_id`, campos de evento (fecha, acción/detalle) | Bitácora visible en `Profile.vue` |
| **notificaciones** | `id PK`, `titulo`, `subtitulo`, `descripcion`, `enlace_url`, `enviada_a_todos BOOLEAN`, `archivo_nombre`, `archivo_tipo`, `archivo`(BYTEA?), `fecha_creacion`, `fecha_envio` | Push interno |
| **notificacion_usuarios** | `notificacion_id`, `usuario_id` | Destinatarios (cuando no es "a todos") |
| **notificacion_leidos** | `notificacion_id`, `usuario_id`, `device_id`, `fecha` | Lecturas |
| **manuales** | `id PK`, ..., `archivo BYTEA`, `imagen BYTEA`, `video BYTEA`, `video_nombre` | Contenido en BD |
| **manual_usuarios** / **manual_leidos** | relaciones manual↔usuario | Asignación y lectura |
| **sys_telemetry** | `id`, `ts`, `usr`, `usr_id`, `usr_nombre`, `usr_rol`, `usr_territorio`, `usr_cargo`, `action_type`, `module`, `detail`, `target_id`, `target_label`, `http_method/path/status`, `ip_hint`, `ua`, `session_id`, `source`, `extra` | Bitácora de auditoría |
| **sys_observers** | `handle`, `secret_hash` (bcrypt) | Acceso a la bitácora |

**Entidades que ECA necesita y NO existen** (`CREAR NUEVO`): `eca`, `asignacion_tecnico_eca`,
`modalidad`, `tipo_actividad` (catálogo), `tema`, `productor`, `formulario`, `formulario_version`,
`seccion`, `pregunta`, `opcion`, `restriccion`, `levantamiento`, `respuesta`, `actividad_evidencia`,
`jornada` (o adaptación de `asistencias`).

---

## 25. Identificadores usados para evitar duplicados (resumen)

| Flujo | Mecanismo actual | ¿Robusto? |
|---|---|---|
| Actividad (`registros`) | **Ninguno** en servidor. Cliente genera `id_cliente` pero no lo envía. Sync depende del texto del error. | **No** — reintento duplica |
| Jornada (`asistencias`) | `SELECT` por `(usuario_id, fecha)` + `400` si existe (sin `UNIQUE`) | Parcial — funciona salvo carrera |
| Reporte mensual | `SELECT` por `(usuario_id, mes, anio)` + `409` | Sí (a nivel lógico) |
| Usuario | `correo UNIQUE`, `curp UNIQUE` | Sí (constraints DB) |
| Asignación facilitador–técnico | Índices únicos parciales + `ON CONFLICT DO UPDATE` | Sí |
| Notificación leída | `INSERT` en `notificacion_leidos` (revisar `UNIQUE`) | Parcial |
| Foto en disco | Nombre `usuario_timestamp_ms_rand` (evita colisión de archivo, no de registro) | Solo archivo |

**Para ECA** (`AGENTS.md` reglas 9–10): UUID v4 generado en cliente para **todo** objeto offline
(actividad, productor, levantamiento, respuesta, evidencia), enviado al servidor, con
`UNIQUE(uuid)` y endpoints de sync **idempotentes** (mismo UUID → mismo recurso, `200`).

---

## 26. Resumen de decisiones por componente

| # | Componente | Archivo(s) / endpoint(s) clave | Decisión |
|---|---|---|---|
| 1 | FastAPI como framework | `backend/main.py` | CONSERVAR |
| 2 | Monolito `main.py` | `backend/main.py` (11 963 L) | ADAPTAR (routers) |
| 3 | Acceso a datos psycopg2 + cursor global | `:69`, `:139`, `:100` | REEMPLAZAR (pool/ORM) |
| 4 | Migraciones "al importar" | `:202-460` | REEMPLAZAR (Alembic) |
| 5 | PWA técnicos Vue3+Vite+PWA | `pwasuper/` | CONSERVAR |
| 6 | `Home.vue` monolítico | `pwasuper/src/views/Home.vue` | ADAPTAR |
| 7 | Sin store global | `pwasuper/src/` | CREAR NUEVO (Pinia) |
| 8 | Router guard `localStorage.user` | `pwasuper/src/router/index.js` | REEMPLAZAR |
| 9 | Login técnicos texto plano | `POST /login` `:899` | REEMPLAZAR |
| 10 | Token para PWA técnicos | — | CREAR NUEVO |
| 11 | Login admin bcrypt + JWT | `POST /admin/login` `:4942` | ADAPTAR (exp, refresh) |
| 12 | `/auth/me`, `/auth/check-permission` stubs | `:5043`, `:5147` | REEMPLAZAR |
| 13 | Autorización backend por endpoint | (inexistente) | CREAR NUEVO |
| 14 | Permisos JSON en `admin_users` | `:8449` | ADAPTAR (+permisos ECA) |
| 15 | Enforcement de permisos solo en cliente | `admin-pwa/src/services/authService.js`, `router/index.js` | REEMPLAZAR |
| 16 | Tabla `usuarios` (identidad) | — | CONSERVAR |
| 17 | Doble tabla `usuarios`/`admin_users` | — | ADAPTAR |
| 18 | `POST /usuarios` sin auth | `:735` | REEMPLAZAR |
| 19 | Validación/unicidad CURP | `:748`, `:4388` | ADAPTAR (reusar para `productor`) |
| 20 | Exposición de CURP en respuestas + `/fotos` público | múltiples, `:640` | REEMPLAZAR |
| 21 | Territorios lista fija SV | `:4560` | REEMPLAZAR (catálogo BD / ámbito ECA) |
| 22 | Columna `territorio` en `usuarios`/`admin_users` | — | ADAPTAR (aditivo) |
| 23 | `usuarios.supervisor` texto | — | REEMPLAZAR (relación) |
| 24 | `facilitador_tecnico_asignaciones` | `:361` | ADAPTAR (→ `asignacion_tecnico_eca`) |
| 25 | Jerarquía implícita (territorio+cargo) | `:10222`, `:10405` | REEMPLAZAR (jerarquía explícita) |
| 26 | Jornada = `asistencias` | `:5259`, `:5349` | ADAPTAR (foto/descr opcionales) |
| 27 | Dedup jornada por `(usuario,fecha)` | `:5290` | CONSERVAR (formalizar `UNIQUE`) |
| 28 | Manejo de zona horaria CDMX | `:5185`, `:1330` | REEMPLAZAR (UTC/TIMESTAMPTZ) |
| 29 | Tabla `registros` (actividad) | `:1229` | ADAPTAR (campos ECA aditivos) |
| 30 | `POST /registro` sin auth ni idempotencia | `:1139` | REEMPLAZAR |
| 31 | Fotos 1:1 en `foto_url` | — | REEMPLAZAR (`actividad_evidencia`) |
| 32 | Catálogo categorías hardcodeado x2 | `:1168`, `syncService.js:504` | REEMPLAZAR (tablas catálogo) |
| 33 | Captura GPS multi-intento | `pwasuper/src/services/geoLocationService.js` | CONSERVAR/ADAPTAR |
| 34 | Ubicación por defecto silenciosa | `geoLocationService.setDefaultLocation` | REEMPLAZAR |
| 35 | Precisión GPS no persistida | `Home.vue:1986`, `registros` | ADAPTAR (persistir) |
| 36 | Storage de fotos en filesystem | `FOTOS_DIR`, `:640` | ADAPTAR (object storage) |
| 37 | `/fotos` estático público | `:640` | REEMPLAZAR (URLs firmadas) |
| 38 | Compresión de imágenes en cliente | `imageCompressor.js`, `syncService.js` | CONSERVAR |
| 39 | Placeholders "Sin imagen" en sync | `syncService.js:733` | REEMPLAZAR |
| 40 | `phash` antifraude O(n) | `POST /admin/buscar-imagen-similar` `:9077` | ADAPTAR (hash en columna) |
| 41 | IndexedDB stores + metadatos | `offlineService.js` | CONSERVAR/ADAPTAR (stores ECA) |
| 42 | `id_cliente` no-UUID, no enviado | `offlineService.js:229` | REEMPLAZAR (UUID) |
| 43 | Sync 1-a-1 con reintentos/backoff | `syncService.js` | CONSERVAR/ADAPTAR |
| 44 | Dedup por texto de error | `syncService.js:255` | REEMPLAZAR (idempotencia real) |
| 45 | Polling sync 2 min / sesión 5 s | `syncService.js`, `authService.js` | ADAPTAR (escala) |
| 46 | Reporte PDF en cliente | `Reportes.vue`, jsPDF/html2canvas | ADAPTAR (server-side) |
| 47 | `reportes_generados` + regla 1/mes | `:2144` | CONSERVAR (regla) / ADAPTAR (fuente de datos) |
| 48 | Estadísticas admin ad-hoc | `/estadisticas/*`, `ReportesView.vue` | ADAPTAR (indicadores ECA) |
| 49 | Exportaciones CSV/XLSX/ZIP | `/exportar-registros-csv`, admin | ADAPTAR (auth + ámbito) |
| 50 | Firma canvas → base64 | `FirmaDigital.vue` | CONSERVAR |
| 51 | Autorización de firma por asignación | `POST /reportes/firmar/{id}` `:2501` | CONSERVAR/ADAPTAR |
| 52 | Integridad del documento firmado | — | ADAPTAR (hash + timestamp servidor) |
| 53 | Panel admin (vistas 6k–11k L, servicios duplicados) | `admin-pwa/` | ADAPTAR (dividir/limpiar) |
| 54 | Scripts `test-*.js`/`probar-*.js` en `src/` | `admin-pwa/src/` | REEMPLAZAR (quitar) |
| 55 | Endpoints `/debug/*` en prod | `:5522`–`:6337` | REEMPLAZAR (quitar/proteger) |
| 56 | `/descargar-bd-completa`, `/exportar-*`, `.../all` sin auth | `:9623`, `:9867`, `:5924` | REEMPLAZAR |
| 57 | `_SYS_OBSERVER_SECRET` / `SECRET_KEY` fallback / `admin/admin123` | `:11545`, `:60`, `:223` | REEMPLAZAR |
| 58 | CORS `*` + credentials | `:39` | REEMPLAZAR |
| 59 | `sys_telemetry` auditoría | `:11539` | CONSERVAR/ADAPTAR (retención) |
| 60 | Manuales/notificaciones como BYTEA | `:10489` | ADAPTAR (storage) |
| 61 | Entidades ECA (eca, productor, formulario, versión, levantamiento, respuesta, evidencia, catálogos) | — | CREAR NUEVO |

---

## 27. Qué NO se pudo verificar desde el código

- Contenido y volumen reales de la BD de producción (nº de usuarios, cuántas contraseñas en
  claro vs bcrypt, cuántos registros/fotos).
- `mock-server.js` (referenciado por `start.js`, ausente).
- Configuración real de nginx del backend y de la PWA de técnicos (solo está
  `admin_nginx.conf`).
- Valores reales de `.env` (secretos, `SECRET_KEY`).
- Si en producción uvicorn corre con `--workers` (el código sugiere que no).
- Estructura exacta (tipos/constraints) de tablas sin `CREATE TABLE` en el código
  (`usuarios`, `historial`, `notificaciones*`).
- Comportamiento del `public/sw.js` frente al SW de Workbox en dispositivos reales.

---

*Fin del inventario técnico. Siguiente documento previsto: diseño del modelo de negocio ECA y
del modelo de datos (no incluido aquí por indicación explícita de no proponer todavía la
implementación definitiva).*
