# 05 — Modelo de datos del sistema ECA V1

> **Propósito.** Definir las entidades, tablas, relaciones, índices, restricciones y campos
> auditables de la base de datos `eca_db` del sistema ECA V1, más el **diseño reservado** de las
> entidades de Fase 2 (productores, unidades productivas, formularios, levantamientos) sin
> implementarlas.
>
> **Fuente funcional principal.** `docs-eca/03_MODELO_NEGOCIO_ECA_ACTUALIZADO.md`.
> **Arquitectura.** `docs-eca/04_ARQUITECTURA_OBJETIVO.md`.
>
> **Estado.** Diseño. **No se crean migraciones ni se modifica código.** Motor:
> **PostgreSQL ≥ 13** (se usa `gen_random_uuid()` nativo; extensiones `citext` y `pg_trgm`).
>
> **Regla de diseño.** Entidades explícitas con columnas explícitas. `JSONB` solo en 3 casos
> acotados y justificados (`ecas.metadatos`, `reportes_periodo.snapshot`,
> `auditoria_eventos.datos_antes/despues`). Sin EAV ni motor de reglas.

---

## 1. Convenciones

### 1.1 Claves e identificadores

| Concepto | Regla |
|---|---|
| **PK interna** | `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` en todas las tablas. Nunca se expone como identificador de negocio. |
| **`uuid` público** | `uuid UUID NOT NULL UNIQUE`. En entidades creadas en dispositivo lo genera el cliente (`crypto.randomUUID()`); en las creadas en panel, `DEFAULT gen_random_uuid()`. Es la **clave de idempotencia** de sincronización. |
| **Clave institucional** | Cuando una entidad tiene código externo (ECA, estado, municipio) se guarda en columna aparte (`clave_*`), **nunca** como PK ni como `uuid`. |
| **Enumeraciones** | Conjuntos pequeños y estables → `TEXT` + `CHECK (col IN (...))`. Conjuntos que el administrador puede ampliar → **tabla de catálogo con FK**. No se usan tipos `ENUM` nativos (para evolucionarlos por migración sin bloqueos). |

### 1.2 Bloque de auditoría estándar (BAE)

Presente en **todas** las tablas salvo que se indique lo contrario:

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `creado_en` | `timestamptz` | NOT NULL | `now()` | UTC. |
| `actualizado_en` | `timestamptz` | NOT NULL | `now()` | Actualizado por trigger `BEFORE UPDATE`. |
| `creado_por` | `bigint` | NULL | — | FK → `usuarios(id)`. NULL = sistema/importación/semilla. |
| `actualizado_por` | `bigint` | NULL | — | FK → `usuarios(id)`. |

### 1.3 Bloque offline (BOF)

En entidades que se pueden crear/editar en campo sin conexión:

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `uuid` | `uuid` | NOT NULL | — | Generado en dispositivo. `UNIQUE`. |
| `dispositivo_id` | `bigint` | NULL | — | FK → `dispositivos(id)`. |
| `creado_en_dispositivo` | `timestamptz` | NOT NULL | — | Hora del evento según el dispositivo. |
| `sincronizado_en` | `timestamptz` | NULL | — | Fijado por el servidor al aceptar el objeto. NULL = aún no confirmado. |
| `origen` | `text` | NOT NULL | `'APP'` | `CHECK (origen IN ('APP','PANEL','IMPORTACION'))`. |

### 1.4 Estrategia de eliminación lógica

| Tipo de tabla | Estrategia |
|---|---|
| **Catálogos** (roles, permisos, geo, modalidades, tipos, temas, subtemas, sistemas productivos, roles_grupo, parametros_config) | **No borrado físico.** Columna `activo BOOLEAN NOT NULL DEFAULT true`. Desactivar conserva la integridad histórica de los registros que ya lo referencian. |
| **Relaciones de asignación** (grupos_usuarios, ambitos_tecnico, asignaciones_tecnico_eca, usuarios_roles, ecas_sistemas_productivos) | **Baja lógica con vigencia.** `activo BOOLEAN` + `fecha_fin`/`vigente_hasta`. La fila permanece para historial. |
| **Entidades transaccionales** (jornadas, actividades, actividades_evidencias, reportes_periodo) | **Bloque de borrado lógico transaccional (BLT):** `eliminado_en timestamptz NULL`, `eliminado_por bigint NULL FK usuarios(id)`, `motivo_eliminacion text NULL`. Toda consulta operativa filtra `eliminado_en IS NULL`. Además `estado`/`estado_revision` controla el ciclo de vida. |
| **Bitácora** (auditoria_eventos, sync_operaciones) | **Append-only.** No se borra ni se edita. Retención por particionado/archivado. |
| **`usuarios`** | Nunca se borra físicamente. `estado IN ('ACTIVO','SUSPENDIDO','BAJA')`. `BAJA` revoca tokens y bloquea login, conserva la autoría histórica. |

### 1.5 Tipos de dato sugeridos (resumen)

| Uso | Tipo |
|---|---|
| Texto corto identificador / clave | `text` (con `CHECK (char_length(...))` cuando aplique) o `varchar(n)` |
| Texto libre descriptivo | `text` |
| Correo | `citext` (unicidad case-insensitive) |
| CURP | `char(18)` con `CHECK` de formato; `NULL` permitido |
| Coordenadas | `numeric(9,6)` latitud, `numeric(9,6)` longitud (≈0.1 m de resolución) |
| Precisión GPS (metros) | `numeric(7,2)` |
| Superficie (ha) | `numeric(10,4)` |
| Fecha (día) | `date` |
| Fecha y hora | `timestamptz` (siempre UTC en BD) |
| Booleano | `boolean` |
| Conteos | `integer` |
| Identificadores internos | `bigint` |
| Metadatos acotados | `jsonb` |

---

## 2. Mapa de entidades

| # | Dominio | Entidad | Fase | Creable offline |
|---|---|---|---|---|
| 1 | Identidad/acceso | `usuarios` | 1A | No |
| 2 | Identidad/acceso | `roles` | 1A | No |
| 3 | Identidad/acceso | `permisos` | 1A | No |
| 4 | Identidad/acceso | `roles_permisos` | 1A | No |
| 5 | Identidad/acceso | `usuarios_roles` | 1A | No |
| 6 | Identidad/acceso | `tokens_refresco` | 1A | No |
| 7 | Identidad/acceso | `dispositivos` | 1A/1B | No (lo crea el backend en el 1er sync) |
| 8 | Organización | `roles_grupo` (catálogo) | 1A | No |
| 9 | Organización | `grupos` | 1A | No |
| 10 | Organización | `grupos_usuarios` | 1A | No |
| 11 | Geografía | `estados` | 1A | No |
| 12 | Geografía | `municipios` | 1A | No |
| 13 | Geografía | `localidades` | 1A | No |
| 14 | ECA | `ecas` | 1A | No |
| 15 | ECA | `ecas_sistemas_productivos` | 1A | No |
| 16 | ECA | `ambitos_tecnico` | 1A | No |
| 17 | ECA | `asignaciones_tecnico_eca` | 1A | No |
| 18 | Importación | `lotes_importacion` | 1A | No |
| 19 | Importación | `errores_importacion` | 1A | No |
| 20 | Configuración | `parametros_config` | 1A | No |
| 21 | Catálogos actividad | `modalidades` | 1A | No |
| 22 | Catálogos actividad | `tipos_actividad` | 1A | No |
| 23 | Catálogos actividad | `temas` | 1A | No |
| 24 | Catálogos actividad | `subtemas` | 1A | No |
| 25 | Catálogos actividad | `sistemas_productivos` | 1A | No |
| 26 | Operación campo | `jornadas` | 1B | **Sí** |
| 27 | Operación campo | `actividades` | 1B | **Sí** |
| 28 | Operación campo | `actividades_evidencias` | 1B | **Sí** |
| 29 | Sincronización | `sync_operaciones` | 1B | No (ledger de servidor) |
| 30 | Auditoría | `auditoria_eventos` | 1A→ | No |
| 31 | Reportes | `reportes_periodo` | 1C | No |
| F2 | Productores | `productores` | 2 | Sí (futuro) |
| F2 | Productores | `unidades_productivas` | 2 | Sí (futuro) |
| F2 | Productores | `unidades_sistemas_productivos` | 2 | Sí (futuro) |
| F2 | Productores | `productores_eca` | 2 | No |
| F2 | Formularios | `formularios` | 2 | No |
| F2 | Formularios | `formularios_versiones` | 2 | No |
| F2 | Formularios | `secciones` | 2 | No |
| F2 | Formularios | `preguntas` | 2 | No |
| F2 | Formularios | `opciones_pregunta` | 2 | No |
| F2 | Formularios | `reglas_condicionales` | 2 | No |
| F2 | Formularios | `asignaciones_formulario` | 2 | No |
| F2 | Levantamientos | `levantamientos` | 2 | Sí (futuro) |
| F2 | Levantamientos | `respuestas` | 2 | Sí (futuro) |
| F2 | Levantamientos | `respuestas_evidencias` | 2 | Sí (futuro) |

---

## 3. Diagrama entidad-relación (textual)

Notación: `||`=uno obligatorio · `o|`=cero-o-uno · `o{`=cero-o-muchos · `|{`=uno-o-muchos.

```
── IDENTIDAD Y ACCESO ───────────────────────────────────────────────────────
usuarios ||───o{ usuarios_roles }o───|| roles
roles    ||───o{ roles_permisos }o───|| permisos
usuarios ||───o{ tokens_refresco
usuarios ||───o{ dispositivos

── ORGANIZACIÓN ─────────────────────────────────────────────────────────────
grupos       o|───o{ grupos            (grupo_padre_id · auto-referencia opcional)
grupos       ||───o{ grupos_usuarios }o───|| usuarios
roles_grupo  ||───o{ grupos_usuarios

── GEOGRAFÍA ────────────────────────────────────────────────────────────────
estados ||───|{ municipios ||───o{ localidades

── ECA Y ASIGNACIONES ───────────────────────────────────────────────────────
estados     ||───o{ ecas
municipios  ||───o{ ecas
localidades o|───o{ ecas
ecas ||───o{ ecas_sistemas_productivos }o───|| sistemas_productivos
usuarios ||───o{ ambitos_tecnico }o───|| municipios
usuarios ||───o{ asignaciones_tecnico_eca }o───|| ecas
lotes_importacion ||───o{ errores_importacion
lotes_importacion ||───o{ ecas            (lote_importacion_id · trazabilidad)
lotes_importacion ||───o{ usuarios        (lote_importacion_id · trazabilidad)

── CATÁLOGOS DE ACTIVIDAD ───────────────────────────────────────────────────
temas ||───o{ subtemas
(modalidades, tipos_actividad, temas, sistemas_productivos: catálogos raíz)

── OPERACIÓN DE CAMPO ───────────────────────────────────────────────────────
usuarios ||───o{ jornadas
jornadas ||───o{ actividades
usuarios ||───o{ actividades              (usuario_id · técnico autor)
ecas     o|───o{ actividades
modalidades      ||───o{ actividades
tipos_actividad  ||───o{ actividades
temas            o|───o{ actividades
subtemas         o|───o{ actividades
sistemas_productivos o|───o{ actividades
actividades ||───o{ actividades_evidencias
usuarios o|───o{ actividades              (revisado_por)
dispositivos o|───o{ jornadas / actividades / actividades_evidencias

── SINCRONIZACIÓN Y AUDITORÍA ───────────────────────────────────────────────
usuarios     ||───o{ sync_operaciones
dispositivos o|───o{ sync_operaciones
usuarios     o|───o{ auditoria_eventos    (actor_usuario_id)

── REPORTES ─────────────────────────────────────────────────────────────────
usuarios ||───o{ reportes_periodo         (usuario_id · técnico)
usuarios o|───o{ reportes_periodo         (revisado_por)

── FASE 2 (reservado) ───────────────────────────────────────────────────────
productores ||───o{ unidades_productivas ||───o{ unidades_sistemas_productivos }o──|| sistemas_productivos
productores ||───o{ productores_eca }o───|| ecas
formularios ||───|{ formularios_versiones ||───|{ secciones ||───|{ preguntas ||───o{ opciones_pregunta
preguntas   ||───o{ reglas_condicionales
formularios_versiones ||───o{ asignaciones_formulario }o───|| usuarios/ecas
formularios_versiones ||───o{ levantamientos }o───|| productores
levantamientos }o───o| actividades        (actividad_id · opcional)
levantamientos ||───|{ respuestas }o───|| preguntas
respuestas ||───o{ respuestas_evidencias
```

---

## 4. Entidades V1 — especificación

> Cada ficha incluye: **propósito · campos · PK · FK · índices · restricciones · relaciones ·
> auditoría · eliminación lógica**. El "Bloque de auditoría estándar (BAE)" y el "Bloque offline
> (BOF)" se referencian por sigla para no repetirlos.

### 4.1 Identidad y acceso

---

#### `usuarios`

- **Propósito.** Persona con acceso al sistema ECA: técnico, administrador, enlace o supervisor.
  Identidad única (sin el doble `usuarios`/`admin_users` de SV). El rol se asigna aparte.
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `uuid` | uuid | NOT NULL | `gen_random_uuid()` | público, `UNIQUE` |
| `nombre` | text | NOT NULL | — | nombre(s) |
| `apellido_paterno` | text | NOT NULL | — | |
| `apellido_materno` | text | NULL | — | |
| `correo` | citext | NOT NULL | — | `UNIQUE`; usuario de login |
| `telefono` | text | NULL | — | `CHECK` formato E.164 opcional |
| `curp` | char(18) | NULL | — | `UNIQUE` cuando no es NULL; `CHECK` formato CURP |
| `contrasena_hash` | text | NOT NULL | — | Argon2id/bcrypt; **nunca** texto plano |
| `algoritmo_hash` | text | NOT NULL | `'argon2id'` | para rotación futura |
| `requiere_cambio_contrasena` | boolean | NOT NULL | `true` | alta/reseteo |
| `estado` | text | NOT NULL | `'ACTIVO'` | `CHECK (estado IN ('ACTIVO','SUSPENDIDO','BAJA'))` |
| `ultimo_acceso_en` | timestamptz | NULL | — | |
| `lote_importacion_id` | bigint | NULL | — | FK trazabilidad de alta masiva |
| BAE | | | | |

- **PK.** `id`.
- **FK.** `lote_importacion_id → lotes_importacion(id)`; `creado_por/actualizado_por → usuarios(id)`
  (auto-referencia, nullable).
- **Índices.** `UNIQUE(uuid)`, `UNIQUE(correo)`, `UNIQUE(curp) WHERE curp IS NOT NULL`,
  `idx_usuarios_estado (estado)`, `idx_usuarios_nombre_trgm` (trigram sobre
  `nombre || ' ' || apellido_paterno`) para búsqueda.
- **Restricciones.** `CHECK` formato CURP (`^[A-Z]{4}\d{6}[A-Z]{6}[A-Z0-9]\d$`); `CHECK` estado.
- **Relaciones.** 1—N con `usuarios_roles`, `tokens_refresco`, `dispositivos`, `jornadas`,
  `actividades`, `reportes_periodo`, `grupos_usuarios`, `ambitos_tecnico`,
  `asignaciones_tecnico_eca`.
- **Auditoría.** BAE. Cambios de `estado`, `correo`, roles → evento en `auditoria_eventos`.
- **Eliminación lógica.** Sin borrado físico. `estado = 'BAJA'` (revoca `tokens_refresco`,
  bloquea login). Conserva autoría histórica.

---

#### `roles`

- **Propósito.** Catálogo de roles funcionales, **independiente del nombre del cargo**
  (`03` §4.1). Ej.: `ADMIN`, `TECNICO`, `ENLACE`, `SUPERVISOR`, `CONSULTA`.
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `clave` | text | NOT NULL | — | `UNIQUE`, mayúsculas sin espacios |
| `nombre` | text | NOT NULL | — | etiqueta visible |
| `descripcion` | text | NULL | — | |
| `es_sistema` | boolean | NOT NULL | `false` | roles base no eliminables |
| `activo` | boolean | NOT NULL | `true` | |
| BAE | | | | |

- **PK.** `id`. **FK.** BAE.
- **Índices.** `UNIQUE(clave)`, `idx_roles_activo (activo)`.
- **Restricciones.** `CHECK (clave ~ '^[A-Z_]+$')`.
- **Relaciones.** N—M con `permisos` vía `roles_permisos`; N—M con `usuarios` vía `usuarios_roles`.
- **Auditoría.** BAE. **Eliminación lógica.** `activo = false` (nunca físico si `es_sistema`).

---

#### `permisos`

- **Propósito.** Catálogo de permisos atómicos por módulo. La autorización del backend se hace
  contra estas claves (`04` §6).
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `clave` | text | NOT NULL | — | `UNIQUE`, formato `modulo.accion` (ej. `ecas.importar`, `actividades.ver_todas`) |
| `modulo` | text | NOT NULL | — | agrupador (`usuarios`, `ecas`, `actividades`, …) |
| `nombre` | text | NOT NULL | — | etiqueta |
| `descripcion` | text | NULL | — | |
| `activo` | boolean | NOT NULL | `true` | |
| BAE | | | | |

- **PK.** `id`. **Índices.** `UNIQUE(clave)`, `idx_permisos_modulo (modulo)`.
- **Restricciones.** `CHECK (clave ~ '^[a-z_]+\.[a-z_]+$')`.
- **Relaciones.** N—M con `roles`.
- **Eliminación lógica.** `activo = false`. Semilla fija en migración; no editable por usuarios
  finales.

---

#### `roles_permisos`

- **Propósito.** Relación N—M rol ↔ permiso.
- **Campos**: `id` (PK), `rol_id`, `permiso_id`, `creado_en`, `creado_por`.
- **PK.** `id`. **FK.** `rol_id → roles(id)` ON DELETE CASCADE; `permiso_id → permisos(id)`.
- **Índices.** `UNIQUE(rol_id, permiso_id)`, `idx_rp_permiso (permiso_id)`.
- **Restricciones.** unicidad del par.
- **Eliminación lógica.** No aplica (se borra la fila al revocar; queda registrado en
  `auditoria_eventos`).

---

#### `usuarios_roles`

- **Propósito.** Asignación de roles a un usuario, con vigencia y trazabilidad.
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `usuario_id` | bigint | NOT NULL | — | FK |
| `rol_id` | bigint | NOT NULL | — | FK |
| `activo` | boolean | NOT NULL | `true` | |
| `vigente_desde` | timestamptz | NOT NULL | `now()` | |
| `vigente_hasta` | timestamptz | NULL | — | |
| `asignado_por` | bigint | NULL | — | FK `usuarios(id)` |
| `creado_en` | timestamptz | NOT NULL | `now()` | |

- **PK.** `id`. **FK.** `usuario_id → usuarios(id)`, `rol_id → roles(id)`.
- **Índices.** `UNIQUE (usuario_id, rol_id) WHERE activo`, `idx_ur_usuario (usuario_id) WHERE activo`.
- **Restricciones.** partial unique sobre asignación activa.
- **Eliminación lógica.** `activo = false` + `vigente_hasta`. Fila permanece para historial.

---

#### `tokens_refresco`

- **Propósito.** Persistencia y revocación de refresh tokens (`04` §6). Corrige el "JWT sin
  expiración" de SV.
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `jti` | uuid | NOT NULL | — | `UNIQUE`; id del token |
| `usuario_id` | bigint | NOT NULL | — | FK |
| `hash_token` | text | NOT NULL | — | hash del refresh token (no el token) |
| `emitido_en` | timestamptz | NOT NULL | `now()` | |
| `expira_en` | timestamptz | NOT NULL | — | |
| `revocado_en` | timestamptz | NULL | — | |
| `motivo_revocacion` | text | NULL | — | `LOGOUT`, `BAJA_USUARIO`, `ROTACION`, `SEGURIDAD` |
| `user_agent` | text | NULL | — | |
| `ip_hash` | text | NULL | — | IP hasheada, no en claro |

- **PK.** `id`. **FK.** `usuario_id → usuarios(id)` ON DELETE CASCADE.
- **Índices.** `UNIQUE(jti)`, `idx_tr_usuario_activo (usuario_id) WHERE revocado_en IS NULL`,
  `idx_tr_expira (expira_en)`.
- **Restricciones.** `CHECK (expira_en > emitido_en)`.
- **Eliminación lógica.** `revocado_en`. Limpieza física de expirados > 30 días por job.

---

#### `dispositivos`

- **Propósito.** Dispositivo físico de un técnico; ancla la sincronización y las notificaciones.
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `uuid` | uuid | NOT NULL | — | `UNIQUE`; generado por el cliente |
| `usuario_id` | bigint | NOT NULL | — | FK |
| `identificador_cliente` | text | NULL | — | id estable de instalación |
| `plataforma` | text | NULL | — | `ANDROID`/`IOS`/`WEB` |
| `user_agent` | text | NULL | — | |
| `push_token` | text | NULL | — | notificaciones (futuro) |
| `ultima_sync_en` | timestamptz | NULL | — | usado para deltas |
| `activo` | boolean | NOT NULL | `true` | |
| BAE | | | | |

- **PK.** `id`. **FK.** `usuario_id → usuarios(id)`.
- **Índices.** `UNIQUE(uuid)`, `idx_disp_usuario (usuario_id)`.
- **Relaciones.** 1—N con `jornadas`, `actividades`, `actividades_evidencias`, `sync_operaciones`.
- **Eliminación lógica.** `activo = false` (revoca capacidad de sync desde ese dispositivo).

---

### 4.2 Organización flexible (grupos y jerarquía)

---

#### `roles_grupo` (catálogo)

- **Propósito.** Roles que un usuario puede tener **dentro de un grupo**: `TECNICO`, `ENLACE`,
  `SUPERVISOR`. Nombres provisionales (`03` §5) → catálogo activable, no `ENUM`.
- **Campos.** `id` PK, `clave` (`UNIQUE`), `nombre`, `descripcion` NULL, `es_responsable` boolean
  (marca los roles que "dirigen" el grupo, ej. ENLACE/SUPERVISOR), `activo` boolean, BAE.
- **Índices.** `UNIQUE(clave)`.
- **Relaciones.** 1—N con `grupos_usuarios`.
- **Eliminación lógica.** `activo = false`.

---

#### `grupos`

- **Propósito.** Grupo de trabajo que organiza técnicos y sus responsables (`03` §5).
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `uuid` | uuid | NOT NULL | `gen_random_uuid()` | `UNIQUE` |
| `clave` | text | NULL | — | `UNIQUE` cuando no es NULL |
| `nombre` | text | NOT NULL | — | ej. "Grupo Café Chiapas 01" |
| `descripcion` | text | NULL | — | |
| `grupo_padre_id` | bigint | NULL | — | auto-FK opcional; permite "supervisor de enlaces" sin fijar niveles (decisión abierta D-02) |
| `activo` | boolean | NOT NULL | `true` | |
| BAE | | | | |

- **PK.** `id`. **FK.** `grupo_padre_id → grupos(id)`; BAE.
- **Índices.** `UNIQUE(uuid)`, `UNIQUE(clave) WHERE clave IS NOT NULL`,
  `idx_grupos_padre (grupo_padre_id)`, `idx_grupos_activo (activo)`.
- **Restricciones.** `CHECK (grupo_padre_id <> id)`; evitar ciclos → validación en servicio.
- **Relaciones.** 1—N con `grupos_usuarios`; 0—N auto-referencia.
- **Eliminación lógica.** `activo = false` (no se borra si tiene miembros o historial).

---

#### `grupos_usuarios`

- **Propósito.** Membresía de un usuario en un grupo, con rol en grupo y vigencia. Sustituye a
  `usuarios.supervisor` como texto de SV (`03` §5: "no se debe guardar al supervisor únicamente
  como texto").
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `grupo_id` | bigint | NOT NULL | — | FK |
| `usuario_id` | bigint | NOT NULL | — | FK |
| `rol_grupo_id` | bigint | NOT NULL | — | FK → `roles_grupo(id)` |
| `fecha_inicio` | date | NOT NULL | `current_date` | |
| `fecha_fin` | date | NULL | — | |
| `activo` | boolean | NOT NULL | `true` | |
| `asignado_por` | bigint | NULL | — | FK `usuarios(id)` |
| BAE | | | | |

- **PK.** `id`. **FK.** `grupo_id → grupos(id)`, `usuario_id → usuarios(id)`,
  `rol_grupo_id → roles_grupo(id)`.
- **Índices.** `UNIQUE (grupo_id, usuario_id, rol_grupo_id) WHERE activo`,
  `idx_gu_usuario (usuario_id) WHERE activo`, `idx_gu_grupo (grupo_id) WHERE activo`.
- **Restricciones.** `CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)`.
- **Relaciones.** N—M efectiva grupo↔usuario con atributo de rol.
- **Eliminación lógica.** `activo = false` + `fecha_fin`. Fila permanece.

---

### 4.3 Catálogos geográficos

> Semilla oficial (INEGI). Estado y municipio **no** son texto libre (`03` §6.2).

---

#### `estados`

- **Propósito.** Catálogo de entidades federativas.
- **Campos.** `id` PK · `clave_inegi char(2)` (`UNIQUE`) · `nombre` (`UNIQUE`) · `abreviatura` ·
  `activo` boolean · BAE.
- **Índices.** `UNIQUE(clave_inegi)`, `UNIQUE(nombre)`.
- **Relaciones.** 1—N con `municipios`, `ecas`.
- **Eliminación lógica.** `activo = false` (en la práctica nunca).

---

#### `municipios`

- **Propósito.** Catálogo de municipios por estado.
- **Campos**

| Columna | Tipo | Null | Nota |
|---|---|---|---|
| `id` | bigint identity | NOT NULL | PK |
| `estado_id` | bigint | NOT NULL | FK |
| `clave_inegi` | char(5) | NOT NULL | `UNIQUE` (estado+municipio) |
| `nombre` | text | NOT NULL | |
| `activo` | boolean | NOT NULL | default `true` |
| BAE | | | |

- **PK.** `id`. **FK.** `estado_id → estados(id)`.
- **Índices.** `UNIQUE(clave_inegi)`, `UNIQUE(estado_id, nombre)`, `idx_municipios_estado (estado_id)`.
- **Relaciones.** 1—N con `localidades`, `ecas`, `ambitos_tecnico`.
- **Eliminación lógica.** `activo = false`.

---

#### `localidades`

- **Propósito.** Catálogo de localidades (opcional; muchas ECA no la tendrán en V1).
- **Campos.** `id` PK · `municipio_id` FK · `clave_inegi char(9)` NULL (`UNIQUE` cuando no NULL) ·
  `nombre` · `latitud numeric(9,6)` NULL · `longitud numeric(9,6)` NULL · `activo` · BAE.
- **Índices.** `idx_localidades_municipio (municipio_id)`, `UNIQUE(clave_inegi) WHERE clave_inegi IS NOT NULL`,
  `UNIQUE(municipio_id, nombre)`.
- **Relaciones.** 1—N con `ecas`.
- **Eliminación lógica.** `activo = false`.

---

### 4.4 ECA y asignaciones

---

#### `ecas`

- **Propósito.** Escuela de Campo: entidad propia del sistema. Catálogo objetivo ≈ 5 000 filas,
  con crecimiento (`03` §6).
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK interna |
| `uuid` | uuid | NOT NULL | `gen_random_uuid()` | `UNIQUE` |
| `clave_institucional` | text | NULL | — | clave oficial; `UNIQUE` cuando no NULL; **separada del id interno** (`03` §6.1) |
| `nombre` | text | NOT NULL | — | |
| `estado_id` | bigint | NOT NULL | — | FK |
| `municipio_id` | bigint | NOT NULL | — | FK |
| `localidad_id` | bigint | NULL | — | FK |
| `latitud` | numeric(9,6) | NULL | — | coordenada de referencia opcional |
| `longitud` | numeric(9,6) | NULL | — | |
| `activo` | boolean | NOT NULL | `true` | |
| `fuente_carga` | text | NOT NULL | `'MANUAL'` | `CHECK (fuente_carga IN ('MANUAL','IMPORTACION'))` |
| `lote_importacion_id` | bigint | NULL | — | FK trazabilidad |
| `metadatos` | jsonb | NOT NULL | `'{}'` | **acotado**: campos institucionales adicionales aún no normalizados (`03` §6.1). No se consulta como filtro primario. |
| BAE + BLT | | | | eliminación lógica transaccional |

- **PK.** `id`. **FK.** `estado_id → estados(id)`, `municipio_id → municipios(id)`,
  `localidad_id → localidades(id)`, `lote_importacion_id → lotes_importacion(id)`, BAE, BLT.
- **Índices.**
  - `UNIQUE(uuid)`
  - `UNIQUE(clave_institucional) WHERE clave_institucional IS NOT NULL`
  - `idx_ecas_estado (estado_id) WHERE eliminado_en IS NULL`
  - `idx_ecas_municipio (municipio_id) WHERE eliminado_en IS NULL`
  - `idx_ecas_activo (activo) WHERE eliminado_en IS NULL`
  - `idx_ecas_nombre_trgm` (GIN trigram sobre `nombre`) — búsqueda por nombre
  - `idx_ecas_localidad (localidad_id)`
- **Restricciones.**
  - `CHECK ( (latitud IS NULL) = (longitud IS NULL) )` (coordenadas van en par)
  - `CHECK (latitud IS NULL OR latitud BETWEEN 14 AND 33)` / `longitud BETWEEN -119 AND -86` (México aprox.)
  - coherencia `municipio ∈ estado` y `localidad ∈ municipio` → validada en servicio + (opcional)
    FK compuesta.
- **Relaciones.** N—M con `sistemas_productivos` (`ecas_sistemas_productivos`); 1—N con
  `asignaciones_tecnico_eca`, `actividades`. Vía municipio, elegible por `ambitos_tecnico`.
- **Auditoría.** BAE + evento en `auditoria_eventos` en alta/baja/edición y en importaciones.
- **Eliminación lógica.** BLT (`eliminado_en`) para retirada real; `activo=false` para
  "no disponible operativamente" conservando historial de actividades.

---

#### `ecas_sistemas_productivos`

- **Propósito.** Sistemas productivos asociados a una ECA cuando estén disponibles (`03` §6.1).
- **Campos.** `id` PK · `eca_id` FK · `sistema_productivo_id` FK · `principal` boolean
  (default `false`) · `creado_en` · `creado_por`.
- **Índices.** `UNIQUE(eca_id, sistema_productivo_id)`,
  `UNIQUE(eca_id) WHERE principal` (a lo sumo un principal),
  `idx_esp_sistema (sistema_productivo_id)`.
- **Eliminación lógica.** No aplica (se borra la fila; queda en auditoría).

---

#### `ambitos_tecnico`

- **Propósito.** Ámbito geográfico de trabajo del técnico: uno o varios municipios (`03` §6.4).
  **No** es una columna `municipio` en `usuarios`.
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `usuario_id` | bigint | NOT NULL | — | FK (técnico) |
| `municipio_id` | bigint | NOT NULL | — | FK |
| `fecha_inicio` | date | NOT NULL | `current_date` | |
| `fecha_fin` | date | NULL | — | |
| `activo` | boolean | NOT NULL | `true` | |
| `asignado_por` | bigint | NULL | — | FK `usuarios(id)` |
| BAE | | | | |

- **PK.** `id`. **FK.** `usuario_id → usuarios(id)`, `municipio_id → municipios(id)`.
- **Índices.** `UNIQUE (usuario_id, municipio_id) WHERE activo`,
  `idx_amb_usuario (usuario_id) WHERE activo`, `idx_amb_municipio (municipio_id) WHERE activo`.
- **Restricciones.** `CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)`.
- **Relaciones.** Determina, junto con `config.eca.regla_disponibilidad`, qué ECA ve el técnico
  cuando no tiene asignación directa.
- **Eliminación lógica.** `activo = false` + `fecha_fin`.

---

#### `asignaciones_tecnico_eca`

- **Propósito.** Relación explícita técnico ↔ ECA, independiente de la pertenencia a grupo
  (`03` §6.5). N—M.
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `uuid` | uuid | NOT NULL | `gen_random_uuid()` | `UNIQUE` |
| `usuario_id` | bigint | NOT NULL | — | FK (técnico) |
| `eca_id` | bigint | NOT NULL | — | FK |
| `fecha_inicio` | date | NOT NULL | `current_date` | |
| `fecha_fin` | date | NULL | — | |
| `activo` | boolean | NOT NULL | `true` | |
| `origen` | text | NOT NULL | `'MANUAL'` | `CHECK (origen IN ('MANUAL','IMPORTACION','INSTITUCIONAL'))` |
| `asignado_por` | bigint | NULL | — | FK `usuarios(id)` |
| `lote_importacion_id` | bigint | NULL | — | FK |
| BAE | | | | |

- **PK.** `id`. **FK.** `usuario_id → usuarios(id)`, `eca_id → ecas(id)`,
  `lote_importacion_id → lotes_importacion(id)`.
- **Índices.** `UNIQUE(uuid)`, `UNIQUE (usuario_id, eca_id) WHERE activo`,
  `idx_ate_usuario (usuario_id) WHERE activo`, `idx_ate_eca (eca_id) WHERE activo`.
- **Restricciones.** `CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)`.
- **Relaciones.** Fuente primaria de "ECA asignadas" para la PWA y para el subconjunto offline.
- **Eliminación lógica.** `activo = false` + `fecha_fin`.

---

### 4.5 Importación masiva

---

#### `lotes_importacion`

- **Propósito.** Cabecera de una carga masiva (ECA, usuarios, asignaciones) vía CSV/XLSX, con
  previsualización y confirmación (`03` §6.3).
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `uuid` | uuid | NOT NULL | `gen_random_uuid()` | `UNIQUE` |
| `tipo` | text | NOT NULL | — | `CHECK (tipo IN ('ECA','USUARIOS','ASIGNACIONES_TECNICO_ECA','AMBITOS'))` |
| `archivo_nombre` | text | NOT NULL | — | |
| `archivo_storage_clave` | text | NULL | — | archivo original en storage |
| `total_filas` | integer | NOT NULL | `0` | |
| `filas_validas` | integer | NOT NULL | `0` | |
| `filas_con_error` | integer | NOT NULL | `0` | |
| `estado` | text | NOT NULL | `'PROCESANDO'` | `CHECK (estado IN ('PROCESANDO','VALIDADO','CONFIRMADO','CANCELADO','ERROR'))` |
| `resumen` | jsonb | NOT NULL | `'{}'` | conteos por acción (altas/actualizaciones/omitidos) |
| `confirmado_en` | timestamptz | NULL | — | |
| BAE | | | | |

- **PK.** `id`. **FK.** BAE.
- **Índices.** `UNIQUE(uuid)`, `idx_lotes_tipo_estado (tipo, estado)`.
- **Relaciones.** 1—N con `errores_importacion`; referenciado por `ecas`, `usuarios`,
  `asignaciones_tecnico_eca` (`lote_importacion_id`).
- **Eliminación lógica.** No se borra (trazabilidad). `estado = 'CANCELADO'`.

---

#### `errores_importacion`

- **Propósito.** Errores por fila detectados en validación previa a confirmar (`03` §6.3).
- **Campos.** `id` PK · `lote_id` FK · `numero_fila` int · `columna` text NULL · `valor` text NULL ·
  `codigo` text (`DUPLICADO`, `CLAVE_GEO_INVALIDA`, `CAMPO_REQUERIDO`, `FORMATO`, …) ·
  `mensaje` text · `severidad` text (`CHECK IN ('ERROR','ADVERTENCIA')`) · `creado_en`.
- **PK.** `id`. **FK.** `lote_id → lotes_importacion(id)` ON DELETE CASCADE.
- **Índices.** `idx_errimp_lote (lote_id)`, `idx_errimp_lote_fila (lote_id, numero_fila)`.
- **Eliminación lógica.** No aplica (se elimina con el lote si este se descarta).

---

### 4.6 Configuración

---

#### `parametros_config`

- **Propósito.** Conjunto **acotado** de parámetros operativos que sustituyen suposiciones
  institucionales hardcodeadas (`03` §26, `04` §13). **No es un motor de reglas**: es una tabla
  clave-valor con claves conocidas y documentadas.
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `clave` | text | NOT NULL | — | `UNIQUE` |
| `valor` | jsonb | NOT NULL | — | valor tipado |
| `tipo_dato` | text | NOT NULL | — | `CHECK IN ('BOOLEAN','ENTERO','TEXTO','LISTA','OBJETO')` |
| `descripcion` | text | NOT NULL | — | |
| `editable` | boolean | NOT NULL | `true` | algunos son solo lectura |
| BAE | | | | |

- **PK.** `id`. **Índices.** `UNIQUE(clave)`.
- **Claves iniciales (semilla).**
  - `eca.regla_disponibilidad` = `"ASIGNADAS_LUEGO_AMBITO"` (`CHECK` lógico: `ASIGNADAS_LUEGO_AMBITO` | `SOLO_ASIGNADAS` | `SOLO_AMBITO`) — regla provisional de `03` §6.6.
  - `jornada.maxima_por_dia` = `1` — regla inicial de `03` §7.
  - `actividad.evidencia.min_default` = `1`, `actividad.evidencia.max` = `3`.
  - `sync.tam_lote` = `50`.
  - `sync.dias_retencion_sincronizados` = `15`.
  - `gps.precision_valida_maxima_m` = `50` (para el indicador "precisión GPS válida").
- **Auditoría.** BAE + evento en `auditoria_eventos` en cada cambio.
- **Eliminación lógica.** No se borra; claves fijas por semilla.

---

### 4.7 Catálogos de actividad

> Todos comparten: `id` PK, `clave` (`UNIQUE`), `nombre`, `activo boolean DEFAULT true`,
> `orden integer` (para presentación), BAE. Eliminación lógica = `activo = false`.
> Semilla inicial en migración a partir de `03` §9–§12.

---

#### `modalidades`

- **Propósito.** Modalidad de la actividad. Semilla: `CAMPO`, `GABINETE`.
- **Campos extra.** ninguno.
- **Índices.** `UNIQUE(clave)`.
- **Relaciones.** 1—N con `actividades`.

---

#### `tipos_actividad`

- **Propósito.** Tipo de acción realizada (`03` §9). Semilla: `CAP, ATE, VIS, MON, PRA, ORG, INT,
  GES, EVA, OTR`.
- **Campos extra**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `requiere_evidencia` | boolean | NOT NULL | `true` | obligatoriedad de foto **por tipo**, no global (`03` §8) |
| `min_fotos` | integer | NOT NULL | `1` | `CHECK (min_fotos BETWEEN 0 AND 3)` |
| `max_fotos` | integer | NOT NULL | `3` | `CHECK (max_fotos BETWEEN min_fotos AND 3)` |
| `permite_participantes` | boolean | NOT NULL | `false` | habilita `actividades.num_participantes` (`03` §13) |
| `requiere_eca` | boolean | NOT NULL | `true` | si la actividad de este tipo exige ECA |

- **Índices.** `UNIQUE(clave)`.
- **Relaciones.** 1—N con `actividades`.

---

#### `temas`

- **Propósito.** Contenido temático de la actividad (`03` §10). Semilla: Manejo del cultivo,
  Bioinsumos, Suelo, Agua, Sanidad vegetal, Semillas, Agrobiodiversidad, Huertos,
  Cosecha/poscosecha, Organización de productores, Comercialización, Ganadería, Apicultura, Otro.
- **Índices.** `UNIQUE(clave)`.
- **Relaciones.** 1—N con `subtemas`, 1—N con `actividades`.

---

#### `subtemas`

- **Propósito.** Desglose de un tema (`03` §11). El administrador puede ampliarlos.
- **Campos extra.** `tema_id bigint NOT NULL` (FK).
- **PK.** `id`. **FK.** `tema_id → temas(id)`.
- **Índices.** `UNIQUE(tema_id, clave)`, `idx_subtemas_tema (tema_id) WHERE activo`.
- **Relaciones.** N—1 con `temas`; 1—N con `actividades`.
- **Restricción de integridad.** En `actividades`: si `subtema_id` no es NULL, su `tema_id` debe
  coincidir con `actividades.tema_id` → validación en servicio + (opcional) FK compuesta
  `(tema_id, subtema_id) → subtemas(tema_id, id)` con columna espejo.

---

#### `sistemas_productivos`

- **Propósito.** Cultivo / sistema productivo (`03` §12). Semilla: Maíz, Frijol, Milpa, Trigo,
  Arroz, Café, Caña de azúcar, Cacao, Amaranto, Chía, Miel/Apicultura, Leche/Ganadería,
  Hortalizas, Otro.
- **Índices.** `UNIQUE(clave)`.
- **Relaciones.** 1—N con `actividades`; N—M con `ecas` y (Fase 2) `unidades_productivas`.

---

### 4.8 Operación de campo

---

#### `jornadas`

- **Propósito.** Periodo operativo de un técnico en un día; marco temporal de las actividades.
  **Sin** foto ni descripción obligatorias; GPS no es evidencia principal (`03` §7).
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `usuario_id` | bigint | NOT NULL | — | FK (técnico) |
| `fecha` | date | NOT NULL | — | día de la jornada (local del técnico, derivado del inicio) |
| `inicio_en` | timestamptz | NOT NULL | — | |
| `fin_en` | timestamptz | NULL | — | |
| `estado` | text | NOT NULL | `'ABIERTA'` | `CHECK (estado IN ('ABIERTA','CERRADA','ANULADA'))` |
| `latitud_inicio` | numeric(9,6) | NULL | — | opcional |
| `longitud_inicio` | numeric(9,6) | NULL | — | opcional |
| `precision_inicio_m` | numeric(7,2) | NULL | — | |
| `estado_gps_inicio` | text | NULL | — | `CHECK IN ('CON_GPS','GPS_IMPRECISO','SIN_GPS')` |
| `latitud_fin` | numeric(9,6) | NULL | — | |
| `longitud_fin` | numeric(9,6) | NULL | — | |
| `precision_fin_m` | numeric(7,2) | NULL | — | |
| `estado_gps_fin` | text | NULL | — | |
| `nota` | text | NULL | — | opcional (no obligatoria) |
| BOF | | | | `uuid`, `dispositivo_id`, `creado_en_dispositivo`, `sincronizado_en`, `origen` |
| BAE + BLT | | | | |

- **PK.** `id`. **FK.** `usuario_id → usuarios(id)`, `dispositivo_id → dispositivos(id)`, BAE, BLT.
- **Índices.**
  - `UNIQUE(uuid)`
  - `UNIQUE (usuario_id, fecha) WHERE estado <> 'ANULADA' AND eliminado_en IS NULL`
    → implementa "máx. 1 jornada principal por técnico por fecha" (`03` §7; relajable vía
    decisión abierta D-05).
  - `idx_jornadas_usuario_fecha (usuario_id, fecha DESC) WHERE eliminado_en IS NULL`
  - `idx_jornadas_sync (sincronizado_en) WHERE sincronizado_en IS NULL`
- **Restricciones.** `CHECK (fin_en IS NULL OR fin_en >= inicio_en)`;
  `CHECK ((latitud_inicio IS NULL) = (longitud_inicio IS NULL))` (y análogo fin).
- **Relaciones.** 1—N con `actividades`.
- **Auditoría.** BAE + BOF. **Eliminación lógica.** `estado = 'ANULADA'` (operativo) o BLT
  (`eliminado_en`) para retirada administrativa con motivo.

---

#### `actividades`

- **Propósito.** Unidad principal de evidencia operativa de la V1: qué hizo el técnico, sobre qué
  tema, en qué sistema productivo, dónde, cuándo y con qué evidencia (`03` §8).
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `usuario_id` | bigint | NOT NULL | — | FK (técnico autor; tomado de la sesión, no del formulario) |
| `jornada_id` | bigint | NOT NULL | — | FK; resuelto por `uuid` de jornada al sincronizar |
| `eca_id` | bigint | NULL | — | FK; obligatorio según `tipos_actividad.requiere_eca` |
| `modalidad_id` | bigint | NOT NULL | — | FK |
| `tipo_actividad_id` | bigint | NOT NULL | — | FK |
| `tema_id` | bigint | NULL | — | FK |
| `subtema_id` | bigint | NULL | — | FK (coherente con `tema_id`) |
| `sistema_productivo_id` | bigint | NULL | — | FK; un principal en V1 (`03` §12) |
| `descripcion` | text | NOT NULL | — | |
| `resultado` | text | NULL | — | |
| `fecha_hora` | timestamptz | NOT NULL | — | hora del evento (del dispositivo) |
| `latitud` | numeric(9,6) | NULL | — | |
| `longitud` | numeric(9,6) | NULL | — | |
| `precision_gps_m` | numeric(7,2) | NULL | — | |
| `estado_gps` | text | NOT NULL | `'SIN_GPS'` | `CHECK IN ('CON_GPS','GPS_IMPRECISO','SIN_GPS')` — nunca coordenadas inventadas (`03` §20) |
| `num_participantes` | integer | NULL | — | solo si `tipos_actividad.permite_participantes`; `CHECK (num_participantes >= 0)` |
| `requiere_seguimiento` | boolean | NOT NULL | `false` | |
| `fecha_proximo_seguimiento` | date | NULL | — | |
| `estado_revision` | text | NOT NULL | `'BORRADOR'` | `CHECK IN ('BORRADOR','ENVIADO','REVISADO','OBSERVADO','APROBADO')` (`03` §25) |
| `revisado_por` | bigint | NULL | — | FK `usuarios(id)` |
| `fecha_revision` | timestamptz | NULL | — | |
| `comentario_revision` | text | NULL | — | |
| BOF | | | | `uuid` (**NOT NULL, UNIQUE — clave de idempotencia**), `dispositivo_id`, `creado_en_dispositivo`, `sincronizado_en`, `origen` |
| BAE + BLT | | | | |

- **PK.** `id`.
- **FK.** `usuario_id → usuarios(id)`; `jornada_id → jornadas(id)`; `eca_id → ecas(id)`;
  `modalidad_id → modalidades(id)`; `tipo_actividad_id → tipos_actividad(id)`;
  `tema_id → temas(id)`; `subtema_id → subtemas(id)`;
  `sistema_productivo_id → sistemas_productivos(id)`; `revisado_por → usuarios(id)`;
  `dispositivo_id → dispositivos(id)`; BAE; BLT.
- **Índices.**
  - `UNIQUE(uuid)`
  - `idx_act_usuario_fecha (usuario_id, fecha_hora DESC) WHERE eliminado_en IS NULL`
  - `idx_act_jornada (jornada_id)`
  - `idx_act_eca (eca_id) WHERE eliminado_en IS NULL`
  - `idx_act_tipo (tipo_actividad_id)`
  - `idx_act_tema (tema_id)`
  - `idx_act_sistema (sistema_productivo_id)`
  - `idx_act_estado_revision (estado_revision) WHERE eliminado_en IS NULL`
  - `idx_act_sync (sincronizado_en) WHERE sincronizado_en IS NULL`
  - `idx_act_seguimiento (fecha_proximo_seguimiento) WHERE requiere_seguimiento AND eliminado_en IS NULL`
  - `idx_act_geo (latitud, longitud) WHERE latitud IS NOT NULL` (o índice espacial si se adopta PostGIS — decisión abierta D-08)
- **Restricciones.**
  - `CHECK ((latitud IS NULL) = (longitud IS NULL))`
  - `CHECK (estado_gps <> 'CON_GPS' OR latitud IS NOT NULL)` (si dice tener GPS, debe haber coordenadas)
  - `CHECK (num_participantes IS NULL OR num_participantes >= 0)`
  - `CHECK (fecha_proximo_seguimiento IS NULL OR requiere_seguimiento = true)`
  - `CHECK (revisado_por IS NULL) = (fecha_revision IS NULL)`
  - reglas dependientes de catálogo (`requiere_eca`, `permite_participantes`, coherencia
    `tema`/`subtema`, obligatoriedad de evidencia) → **servicio + BD**, no solo cliente
    (`AGENTS.md` 8). La obligatoriedad de foto se verifica al pasar de `BORRADOR` a `ENVIADO`.
- **Relaciones.** N—1 con `jornadas`, `ecas`, catálogos; 1—N con `actividades_evidencias`;
  (Fase 2) 1—0..N con `levantamientos` (`levantamientos.actividad_id`).
- **Auditoría.** BAE + BOF; cambios de `estado_revision` → `auditoria_eventos`.
- **Eliminación lógica.** BLT (`eliminado_en`, `eliminado_por`, `motivo_eliminacion`). Las
  consultas operativas y los indicadores filtran `eliminado_en IS NULL`. Una actividad `APROBADO`
  no se puede editar por el técnico (solo administración, auditado).

---

#### `actividades_evidencias`

- **Propósito.** Fotografías de una actividad: 1 a 3 cuando el tipo lo exige (`03` §8).
  **Nunca placeholders.**
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `uuid` | uuid | NOT NULL | — | generado en dispositivo; `UNIQUE` |
| `actividad_id` | bigint | NOT NULL | — | FK |
| `orden` | integer | NOT NULL | — | 1..3 |
| `storage_clave` | text | NOT NULL | — | clave en object storage (no ruta de disco) |
| `nombre_archivo` | text | NULL | — | |
| `mime` | text | NOT NULL | — | `CHECK (mime IN ('image/jpeg','image/png','image/webp'))` |
| `tamano_bytes` | integer | NOT NULL | — | `CHECK (tamano_bytes > 0)` |
| `ancho_px` | integer | NULL | — | |
| `alto_px` | integer | NULL | — | |
| `hash_sha256` | char(64) | NOT NULL | — | integridad y anti-reenvío |
| `hash_perceptual` | bigint | NULL | — | pHash para detección de fotos reutilizadas (`02` §16) |
| `latitud` | numeric(9,6) | NULL | — | EXIF/captura |
| `longitud` | numeric(9,6) | NULL | — | |
| `capturada_en` | timestamptz | NULL | — | |
| `dispositivo_id` | bigint | NULL | — | FK |
| `sincronizado_en` | timestamptz | NULL | — | |
| `creado_en` | timestamptz | NOT NULL | `now()` | |

- **PK.** `id`. **FK.** `actividad_id → actividades(id)` ON DELETE CASCADE;
  `dispositivo_id → dispositivos(id)`.
- **Índices.** `UNIQUE(uuid)`, `UNIQUE(actividad_id, orden)`,
  `idx_ev_actividad (actividad_id)`, `idx_ev_phash (hash_perceptual)`,
  `idx_ev_sha (hash_sha256)`.
- **Restricciones.** `CHECK (orden BETWEEN 1 AND 3)`;
  `CHECK ((latitud IS NULL) = (longitud IS NULL))`. Máx. 3 filas por actividad → validación en
  servicio + índice único de `orden`.
- **Relaciones.** N—1 con `actividades`.
- **Auditoría.** `creado_en` + traza en `auditoria_eventos` al subir/eliminar.
- **Eliminación lógica.** Se elimina en cascada al borrar (lógicamente) la actividad; la
  eliminación individual de una evidencia se audita y borra el objeto de storage por job.

---

### 4.9 Sincronización

---

#### `sync_operaciones`

- **Propósito.** Ledger append-only de operaciones de sincronización recibidas; refuerza la
  idempotencia (además del `UNIQUE(uuid)` de cada entidad) y da trazabilidad de reintentos
  (`03` §19, `04` §7).
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `uuid_operacion` | uuid | NOT NULL | — | id de la operación en el cliente; `UNIQUE` |
| `usuario_id` | bigint | NOT NULL | — | FK |
| `dispositivo_id` | bigint | NULL | — | FK |
| `entidad_tipo` | text | NOT NULL | — | `CHECK IN ('JORNADA','ACTIVIDAD','EVIDENCIA')` (Fase 2 amplía) |
| `entidad_uuid` | uuid | NOT NULL | — | uuid del objeto de negocio |
| `accion` | text | NOT NULL | — | `CHECK IN ('CREAR','ACTUALIZAR')` |
| `hash_payload` | char(64) | NULL | — | sha256 del cuerpo, para detectar reenvío idéntico |
| `resultado` | text | NOT NULL | — | `CHECK IN ('APLICADO','DUPLICADO','RECHAZADO')` |
| `error_codigo` | text | NULL | — | cuando `RECHAZADO` |
| `error_detalle` | text | NULL | — | |
| `recibido_en` | timestamptz | NOT NULL | `now()` | |
| `procesado_en` | timestamptz | NULL | — | |

- **PK.** `id`. **FK.** `usuario_id → usuarios(id)`, `dispositivo_id → dispositivos(id)`.
- **Índices.** `UNIQUE(uuid_operacion)`, `idx_syncop_entidad (entidad_tipo, entidad_uuid)`,
  `idx_syncop_usuario_fecha (usuario_id, recibido_en DESC)`.
- **Restricciones.** unicidad de `uuid_operacion` (reenvío = respuesta idéntica).
- **Eliminación lógica.** No aplica. Retención ~90 días, archivado posterior.

---

### 4.10 Auditoría

---

#### `auditoria_eventos`

- **Propósito.** Bitácora append-only de acciones de escritura relevantes y accesos sensibles
  (`04` §6). Rediseño del `sys_telemetry` de SV, sin secreto hardcodeado.
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `ocurrido_en` | timestamptz | NOT NULL | `now()` | |
| `actor_usuario_id` | bigint | NULL | — | FK; NULL = sistema |
| `actor_rol` | text | NULL | — | rol efectivo al momento |
| `origen` | text | NOT NULL | — | `CHECK IN ('BACKEND','PWA','ADMIN','WORKER','IMPORTACION')` |
| `accion` | text | NOT NULL | — | clave (`usuario.baja`, `eca.importacion_confirmada`, `permisos.cambio`, `reporte.aprobado`, `evidencia.eliminada`, …) |
| `modulo` | text | NOT NULL | — | |
| `entidad_tipo` | text | NULL | — | |
| `entidad_id` | bigint | NULL | — | |
| `entidad_uuid` | uuid | NULL | — | |
| `descripcion` | text | NULL | — | legible |
| `datos_antes` | jsonb | NULL | — | **saneado**: sin CURP completa, contraseñas ni tokens |
| `datos_despues` | jsonb | NULL | — | idem |
| `ip_hash` | text | NULL | — | IP hasheada |
| `user_agent` | text | NULL | — | |
| `sesion_id` | uuid | NULL | — | correlación |

- **PK.** `id`. **FK.** `actor_usuario_id → usuarios(id)` (sin cascade).
- **Índices.** `idx_aud_fecha (ocurrido_en DESC)`, `idx_aud_actor (actor_usuario_id)`,
  `idx_aud_entidad (entidad_tipo, entidad_id)`, `idx_aud_accion (accion)`,
  `idx_aud_modulo (modulo)`.
- **Restricciones.** Tabla **solo INSERT** (revocar UPDATE/DELETE a la app a nivel de rol de BD).
- **Particionado.** `PARTITION BY RANGE (ocurrido_en)` mensual, para escala (`02` §23, `04` §12).
- **Eliminación lógica.** No aplica. Retención por política (p. ej. 24 meses en línea, archivado
  posterior).

---

### 4.11 Reportes / indicadores

---

#### `reportes_periodo`

- **Propósito.** Reporte periódico por técnico, **calculado desde datos transaccionales**
  (`03` §24), con flujo de revisión y (a futuro) firma.
- **Campos**

| Columna | Tipo | Null | Default | Nota |
|---|---|---|---|---|
| `id` | bigint identity | NOT NULL | — | PK |
| `uuid` | uuid | NOT NULL | `gen_random_uuid()` | `UNIQUE` |
| `usuario_id` | bigint | NOT NULL | — | FK (técnico) |
| `grupo_id` | bigint | NULL | — | FK; grupo del técnico al generar |
| `periodo_inicio` | date | NOT NULL | — | |
| `periodo_fin` | date | NOT NULL | — | |
| `estado` | text | NOT NULL | `'BORRADOR'` | `CHECK IN ('BORRADOR','ENVIADO','REVISADO','OBSERVADO','APROBADO','ANULADO')` |
| `snapshot` | jsonb | NOT NULL | `'{}'` | indicadores congelados al generar; **recomputable** desde las tablas |
| `generado_en` | timestamptz | NOT NULL | `now()` | |
| `generado_por` | bigint | NULL | — | FK `usuarios(id)` |
| `revisado_por` | bigint | NULL | — | FK `usuarios(id)` |
| `fecha_revision` | timestamptz | NULL | — | |
| `comentario_revision` | text | NULL | — | |
| `pdf_storage_clave` | text | NULL | — | PDF generado server-side (ReportLab) |
| `hash_contenido` | char(64) | NULL | — | integridad del PDF/snapshot (`02` §17) |
| BAE + BLT | | | | |

- **PK.** `id`. **FK.** `usuario_id → usuarios(id)`, `grupo_id → grupos(id)`,
  `generado_por/revisado_por → usuarios(id)`, BAE, BLT.
- **Índices.** `UNIQUE(uuid)`,
  `UNIQUE (usuario_id, periodo_inicio, periodo_fin) WHERE estado <> 'ANULADO' AND eliminado_en IS NULL`,
  `idx_rep_usuario (usuario_id)`, `idx_rep_estado (estado)`,
  `idx_rep_periodo (periodo_inicio, periodo_fin)`.
- **Restricciones.** `CHECK (periodo_fin >= periodo_inicio)`;
  `CHECK ((revisado_por IS NULL) = (fecha_revision IS NULL))`.
- **Relaciones.** N—1 con `usuarios` y `grupos`.
- **Auditoría.** BAE + evento en cada cambio de `estado`.
- **Eliminación lógica.** `estado = 'ANULADO'` o BLT. La firma se añadirá como tabla
  `reportes_firmas` en el futuro (decisión abierta D-07); la estructura no la incluye en V1.

---

#### Vistas de indicadores (no son tablas)

Los indicadores de `03` §22 se calculan con **vistas** (o **vistas materializadas** con refresco
por job para tableros a escala):

| Vista (sugerida) | Contenido |
|---|---|
| `vw_ind_operacion_tecnico` | jornadas, actividades totales/campo/gabinete, ECA atendidas, municipios/localidades atendidos, por técnico y periodo. |
| `vw_ind_intervencion_tecnico` | actividades por `tipo_actividad`, por técnico y periodo. |
| `vw_ind_tematica_tecnico` | actividades por `tema` / `subtema` / `sistema_productivo`. |
| `vw_ind_evidencia_tecnico` | % con fotografía, % con GPS, % con precisión ≤ `gps.precision_valida_maxima_m`. |
| `vw_ind_seguimiento_tecnico` | actividades que requieren seguimiento, pendientes, realizadas. |
| `vw_ind_operacion_grupo` | agregación de lo anterior por `grupo`. |

> "Productores únicos atendidos", "levantamientos" y "participaciones grupales" (`03` §13) se
> incorporan en Fase 2 sobre `levantamientos` (productores únicos = `COUNT(DISTINCT productor_id)`
> de levantamientos válidos), sin sumar `num_participantes` (`AGENTS.md` 12–13).

---

## 5. Fase 2 — diseño reservado (NO se implementa en V1)

> Se documenta con detalle **medio** para asegurar que las tablas de V1 dejan los huecos
> correctos y no habrá que rehacerlas. **Ninguna de estas tablas se crea en V1.**

### 5.1 Productores

**`productores`** — persona con actividad productiva, **independiente de `usuarios`** (`03` §14).

| Campo | Tipo | Nota |
|---|---|---|
| `id` bigint PK · `uuid` uuid UNIQUE (BOF: creable offline) | | |
| `curp` char(18) NULL, `UNIQUE` cuando no NULL | | **no es la única clave interna** (`03` §14) |
| `nombre`, `apellido_paterno`, `apellido_materno` text | | |
| `sexo` text NULL `CHECK IN ('H','M','X')` | | |
| `fecha_nacimiento` date NULL | | |
| `telefono` text NULL | | |
| `estado_id`, `municipio_id`, `localidad_id` FK geo | | |
| `domicilio_referencia` text NULL | | |
| `latitud`,`longitud` numeric(9,6) NULL | | |
| BAE + BLT | | |

- Índices: `UNIQUE(uuid)`, `UNIQUE(curp) WHERE curp IS NOT NULL`, trigram sobre nombre,
  `(municipio_id)`.
- Eliminación lógica: BLT.
- Deduplicación: por `curp` cuando existe; si no, por (nombre normalizado + municipio +
  fecha_nacimiento) con revisión manual (regla institucional pendiente `03` §27.12).

**`unidades_productivas`** — parcela/predio del productor (`03` §15).

| Campo | Tipo | Nota |
|---|---|---|
| `id` PK · `uuid` UNIQUE (BOF) | | |
| `productor_id` bigint NOT NULL FK | | 1 productor : N unidades |
| `identificador` text NULL | | nombre/clave local |
| `municipio_id`, `localidad_id` FK geo | | |
| `latitud`,`longitud` numeric(9,6) NULL · `precision_gps_m` numeric(7,2) NULL | | |
| `superficie_ha` numeric(10,4) NULL | | |
| `tenencia` text NULL | | catálogo futuro `tenencias` |
| `caracteristicas` jsonb | | acotado; se normaliza al madurar formularios |
| BAE + BLT | | |

- Índices: `UNIQUE(uuid)`, `(productor_id)`, `(municipio_id)`.

**`unidades_sistemas_productivos`** — N:M unidad ↔ `sistemas_productivos` (+ `superficie_ha`,
`principal`).

**`productores_eca`** — N:M productor ↔ ECA. Relación oficial pendiente (`03` §27.12); tabla con
`activo`, `fecha_inicio`, `fecha_fin`, `origen`.

### 5.2 Formularios dinámicos (`03` §17–18)

- **`formularios`** — `id` PK, `uuid` UNIQUE, `clave` UNIQUE, `nombre`, `descripcion`, `activo`,
  BAE. Contenedor lógico ("Diagnóstico Café").
- **`formularios_versiones`** — `id` PK, `uuid` UNIQUE, `formulario_id` FK, `numero_version` int,
  `estado` `CHECK IN ('BORRADOR','PUBLICADA','ARCHIVADA')`, `publicado_en`, `publicado_por`,
  `notas_version`, BAE. `UNIQUE(formulario_id, numero_version)`. **Inmutable tras publicar**: una
  edición genera una versión nueva (`AGENTS.md` 11, `03` §18). Los levantamientos apuntan a la
  versión concreta.
- **`secciones`** — `id` PK, `version_id` FK, `orden`, `titulo`, `descripcion`.
  `UNIQUE(version_id, orden)`.
- **`preguntas`** — `id` PK, `uuid`, `seccion_id` FK, `orden`, `etiqueta`, `tipo`
  (`CHECK IN ('TEXTO_CORTO','TEXTO_LARGO','ENTERO','DECIMAL','FECHA','BOOLEANO','SELECCION_UNICA','SELECCION_MULTIPLE','LISTA','FOTO','COORDENADA')`),
  `obligatoria` bool, `long_min` int NULL, `long_max` int NULL, `valor_min` numeric NULL,
  `valor_max` numeric NULL, `decimales` int NULL, `ayuda` text NULL.
  `UNIQUE(seccion_id, orden)`.
- **`opciones_pregunta`** — `id` PK, `pregunta_id` FK, `orden`, `valor`, `etiqueta`, `activo`.
  `UNIQUE(pregunta_id, valor)`.
- **`reglas_condicionales`** — `id` PK, `version_id` FK, `pregunta_origen_id` FK,
  `operador` (`IGUAL`,`DISTINTO`,`EN`,`>`, `<`), `valor_comparacion` jsonb,
  `pregunta_destino_id` FK, `accion` (`MOSTRAR`,`OCULTAR`,`REQUERIR`). Lógica **simple**
  (`03` §17): sin fórmulas ni scripts.
- **`asignaciones_formulario`** — `id` PK, `version_id` FK, `usuario_id` FK NULL, `eca_id` FK NULL,
  `obligatorio` bool, `vigente_desde`, `vigente_hasta`, `activo`. Al menos uno de
  `usuario_id`/`eca_id` no nulo.

### 5.3 Levantamientos (`03` §16)

- **`levantamientos`** — `id` PK, `uuid` UNIQUE (BOF: creable offline), `version_id` FK
  (`formularios_versiones`), `productor_id` FK, `usuario_id` FK (técnico), `eca_id` FK,
  `actividad_id` FK **NULL** (vínculo opcional con `actividades` de V1), `fecha_hora` timestamptz,
  `estado` `CHECK IN ('BORRADOR','COMPLETADO','ENVIADO','VALIDADO')`, BOF, BAE + BLT.
  Índices: `UNIQUE(uuid)`, `(productor_id)`, `(usuario_id, fecha_hora)`, `(version_id)`,
  `(actividad_id)`. **Cada aplicación del formulario es un levantamiento independiente** (`03` §16).
- **`respuestas`** — `id` PK, `uuid`, `levantamiento_id` FK, `pregunta_id` FK,
  `valor_texto` text NULL, `valor_numerico` numeric NULL, `valor_fecha` date NULL,
  `valor_booleano` boolean NULL, `valor_opcion_id` bigint NULL FK `opciones_pregunta(id)`,
  `latitud`/`longitud` numeric NULL. `UNIQUE(levantamiento_id, pregunta_id)` para
  selección única/escalares; selección múltiple → varias filas o tabla
  `respuestas_opciones (respuesta_id, opcion_id)`.
- **`respuestas_evidencias`** — análoga a `actividades_evidencias`, para preguntas tipo `FOTO`.

### 5.4 Huecos que V1 ya deja preparados

| En V1 | Hueco para Fase 2 |
|---|---|
| `actividades.uuid` estable y `sync_operaciones.entidad_tipo` extensible | `levantamientos.actividad_id` referenciará `actividades.id`. |
| `sistemas_productivos` como catálogo | reutilizado por `unidades_sistemas_productivos`. |
| Catálogos geográficos (`estados`/`municipios`/`localidades`) | reutilizados por `productores` y `unidades_productivas`. |
| `dispositivos` + BOF + motor de sync | reutilizados tal cual para productores/levantamientos. |
| Indicadores como vistas | se añaden vistas de productores únicos / levantamientos sin tocar V1. |
| `auditoria_eventos` genérico por `entidad_tipo`/`entidad_uuid` | cubre las entidades nuevas sin cambios de esquema. |

---

## 6. Índices — resumen consolidado

| Tabla | Índice | Tipo | Motivo |
|---|---|---|---|
| usuarios | `UNIQUE(correo)`, `UNIQUE(uuid)`, `UNIQUE(curp) WHERE curp IS NOT NULL` | btree | login, idempotencia, dedup |
| usuarios | `idx_usuarios_nombre_trgm` | GIN trgm | búsqueda por nombre |
| roles/permisos | `UNIQUE(clave)` | btree | resolución de permisos |
| roles_permisos | `UNIQUE(rol_id, permiso_id)` | btree | integridad N:M |
| usuarios_roles | `UNIQUE(usuario_id, rol_id) WHERE activo` | btree parcial | 1 asignación activa |
| tokens_refresco | `UNIQUE(jti)`, `(usuario_id) WHERE revocado_en IS NULL`, `(expira_en)` | btree | revocación, limpieza |
| dispositivos | `UNIQUE(uuid)`, `(usuario_id)` | btree | sync |
| grupos | `UNIQUE(uuid)`, `UNIQUE(clave) WHERE clave IS NOT NULL`, `(grupo_padre_id)` | btree | jerarquía opcional |
| grupos_usuarios | `UNIQUE(grupo_id, usuario_id, rol_grupo_id) WHERE activo`, `(usuario_id) WHERE activo`, `(grupo_id) WHERE activo` | btree parcial | membresía vigente |
| estados/municipios/localidades | `UNIQUE(clave_inegi)`, `(estado_id)`, `(municipio_id)` | btree | catálogos geo |
| ecas | `UNIQUE(uuid)`, `UNIQUE(clave_institucional) WHERE NOT NULL` | btree | idempotencia / clave oficial |
| ecas | `(estado_id)`, `(municipio_id)`, `(activo)` (parciales `WHERE eliminado_en IS NULL`) | btree parcial | filtros del selector ECA |
| ecas | `idx_ecas_nombre_trgm` | GIN trgm | búsqueda por nombre |
| ecas_sistemas_productivos | `UNIQUE(eca_id, sistema_productivo_id)`, `UNIQUE(eca_id) WHERE principal` | btree parcial | 1 principal |
| ambitos_tecnico | `UNIQUE(usuario_id, municipio_id) WHERE activo`, `(usuario_id) WHERE activo`, `(municipio_id) WHERE activo` | btree parcial | ámbito vigente |
| asignaciones_tecnico_eca | `UNIQUE(uuid)`, `UNIQUE(usuario_id, eca_id) WHERE activo`, `(usuario_id) WHERE activo`, `(eca_id) WHERE activo` | btree parcial | ECA del técnico |
| lotes_importacion | `UNIQUE(uuid)`, `(tipo, estado)` | btree | seguimiento de cargas |
| errores_importacion | `(lote_id)`, `(lote_id, numero_fila)` | btree | revisión por fila |
| parametros_config | `UNIQUE(clave)` | btree | lectura de config |
| subtemas | `UNIQUE(tema_id, clave)`, `(tema_id) WHERE activo` | btree | desglose por tema |
| catálogos actividad | `UNIQUE(clave)` cada uno | btree | resolución |
| jornadas | `UNIQUE(uuid)`, `UNIQUE(usuario_id, fecha) WHERE estado<>'ANULADA' AND eliminado_en IS NULL`, `(usuario_id, fecha DESC)`, `(sincronizado_en) WHERE NULL` | btree parcial | 1/día, historial, sync |
| actividades | `UNIQUE(uuid)` | btree | **idempotencia** |
| actividades | `(usuario_id, fecha_hora DESC)`, `(jornada_id)`, `(eca_id)`, `(tipo_actividad_id)`, `(tema_id)`, `(sistema_productivo_id)`, `(estado_revision)`, `(sincronizado_en) WHERE NULL`, `(fecha_proximo_seguimiento) WHERE requiere_seguimiento` — parciales `WHERE eliminado_en IS NULL` donde aplica | btree parcial | historial, mapa, filtros admin, sync, seguimiento |
| actividades_evidencias | `UNIQUE(uuid)`, `UNIQUE(actividad_id, orden)`, `(actividad_id)`, `(hash_perceptual)`, `(hash_sha256)` | btree | orden, dedup, antifraude |
| sync_operaciones | `UNIQUE(uuid_operacion)`, `(entidad_tipo, entidad_uuid)`, `(usuario_id, recibido_en DESC)` | btree | idempotencia, trazabilidad |
| auditoria_eventos | `(ocurrido_en DESC)`, `(actor_usuario_id)`, `(entidad_tipo, entidad_id)`, `(accion)`, `(modulo)` + **particionado mensual** | btree | consulta de bitácora a escala |
| reportes_periodo | `UNIQUE(uuid)`, `UNIQUE(usuario_id, periodo_inicio, periodo_fin) WHERE estado<>'ANULADO' AND eliminado_en IS NULL`, `(usuario_id)`, `(estado)`, `(periodo_inicio, periodo_fin)` | btree parcial | 1 reporte/periodo/técnico |

---

## 7. Constraints y reglas de integridad — resumen

| # | Regla | Implementación |
|---|---|---|
| C1 | Sin contraseñas en texto plano | `usuarios.contrasena_hash` + `algoritmo_hash`; validación en `security.py`. |
| C2 | 1 jornada principal por técnico/fecha | `UNIQUE(usuario_id, fecha) WHERE estado<>'ANULADA'` en `jornadas` (relajable vía `config`). |
| C3 | Idempotencia de sincronización | `UNIQUE(uuid)` en `jornadas`, `actividades`, `actividades_evidencias`, `asignaciones_tecnico_eca`; `UNIQUE(uuid_operacion)` en `sync_operaciones`. |
| C4 | 1–3 evidencias por actividad | `UNIQUE(actividad_id, orden)` + `CHECK (orden BETWEEN 1 AND 3)` + validación de conteo en servicio. |
| C5 | Coordenadas siempre en par | `CHECK ((latitud IS NULL) = (longitud IS NULL))` en `ecas`, `jornadas`, `actividades`, `actividades_evidencias`. |
| C6 | Coherencia GPS | `CHECK (estado_gps <> 'CON_GPS' OR latitud IS NOT NULL)` en `actividades`. Nunca coordenadas por defecto (regla de aplicación). |
| C7 | Obligatoriedad de evidencia por tipo | `tipos_actividad.requiere_evidencia` + `min_fotos`/`max_fotos`; verificado al pasar `BORRADOR → ENVIADO`. **No** global. |
| C8 | Participantes solo donde aplica | `tipos_actividad.permite_participantes`; `CHECK (num_participantes IS NULL OR num_participantes >= 0)`. |
| C9 | Coherencia tema/subtema | FK + validación en servicio (subtema pertenece al tema de la actividad). |
| C10 | CURP única cuando existe | `UNIQUE(curp) WHERE curp IS NOT NULL` en `usuarios` y (F2) `productores`; `CHECK` de formato. |
| C11 | ECA: municipio ∈ estado, localidad ∈ municipio | validación en servicio + (opcional) FK compuesta. |
| C12 | Vigencias coherentes | `CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)` en todas las tablas de asignación. |
| C13 | Auditoría inmutable | `auditoria_eventos` y `sync_operaciones` solo permiten `INSERT` (rol de BD sin UPDATE/DELETE). |
| C14 | Un sistema productivo principal por ECA | `UNIQUE(eca_id) WHERE principal` en `ecas_sistemas_productivos`. |
| C15 | Revisión coherente | `CHECK ((revisado_por IS NULL) = (fecha_revision IS NULL))` en `actividades` y `reportes_periodo`. |
| C16 | `usuario_id` de campo = sesión | No es columna editable por el cliente; lo fija el backend desde el token. |
| C17 | Formulario publicado inmutable (F2) | `formularios_versiones.estado='PUBLICADA'` bloquea edición; cambios → nueva versión. |

---

## 8. Campos auditables y estrategia de borrado — resumen

| Grupo de tablas | Auditoría | Borrado |
|---|---|---|
| Catálogos (roles, permisos, roles_grupo, geo, modalidades, tipos_actividad, temas, subtemas, sistemas_productivos, parametros_config) | BAE; cambios registrados en `auditoria_eventos` | **Lógico**: `activo = false`. Nunca físico. |
| Asignaciones (usuarios_roles, grupos_usuarios, ambitos_tecnico, asignaciones_tecnico_eca, ecas_sistemas_productivos) | BAE + `asignado_por` | **Lógico con vigencia**: `activo = false` + `fecha_fin`/`vigente_hasta`. |
| Identidad (usuarios) | BAE; `estado`, roles y correo auditados | **Nunca físico**. `estado = 'BAJA'`. |
| Seguridad (tokens_refresco) | campos propios | `revocado_en`; purga física de expirados > 30 d por job. |
| Transaccional (jornadas, actividades, actividades_evidencias, reportes_periodo) | BAE + BOF (campo) + `auditoria_eventos` en cambios de estado | **Lógico (BLT)**: `eliminado_en`, `eliminado_por`, `motivo_eliminacion`; consultas filtran `eliminado_en IS NULL`. Evidencias en storage se borran por job tras la baja lógica. |
| Bitácora (auditoria_eventos, sync_operaciones) | son la auditoría | **Append-only**; retención + archivado, sin borrado en línea. |
| ECA (ecas) | BAE + `auditoria_eventos` (incl. importaciones) | `activo = false` (no disponible) y BLT (`eliminado_en`) para retirada; las actividades históricas conservan la FK. |
| Importación (lotes_importacion, errores_importacion) | BAE | No se borra el lote (trazabilidad); `estado='CANCELADO'`. |

---

## 9. Cardinalidades (resumen)

| Relación | Cardinalidad | Nota |
|---|---|---|
| usuarios — usuarios_roles — roles | N:M | roles múltiples por usuario, vigencia |
| roles — roles_permisos — permisos | N:M | |
| usuarios — tokens_refresco | 1:N | |
| usuarios — dispositivos | 1:N | |
| grupos — grupos_usuarios — usuarios | N:M | atributo `rol_grupo_id` |
| grupos — grupos (padre) | 1:0..N | jerarquía opcional (D-02) |
| estados — municipios — localidades | 1:N — 1:N | |
| estados/municipios — ecas | 1:N | localidad 0..1 |
| ecas — ecas_sistemas_productivos — sistemas_productivos | N:M | 1 principal |
| usuarios — ambitos_tecnico — municipios | N:M | ámbito de trabajo |
| usuarios — asignaciones_tecnico_eca — ecas | N:M | asignación directa |
| usuarios — jornadas | 1:N | 1 principal por fecha |
| jornadas — actividades | 1:N | |
| usuarios — actividades | 1:N | técnico autor |
| ecas — actividades | 1:0..N | `eca_id` nullable |
| modalidades/tipos_actividad — actividades | 1:N | obligatorias |
| temas/subtemas/sistemas_productivos — actividades | 1:0..N | opcionales |
| actividades — actividades_evidencias | 1:0..3 | |
| usuarios — reportes_periodo | 1:N | 1 por periodo/técnico |
| lotes_importacion — errores_importacion | 1:N | |
| lotes_importacion — ecas / usuarios / asignaciones | 1:N | trazabilidad |
| **(F2)** productores — unidades_productivas | 1:N | |
| **(F2)** unidades_productivas — sistemas_productivos | N:M | |
| **(F2)** productores — ecas | N:M | relación institucional pendiente |
| **(F2)** formularios — formularios_versiones | 1:N | versión inmutable |
| **(F2)** formularios_versiones — secciones — preguntas — opciones | 1:N — 1:N — 1:N | |
| **(F2)** formularios_versiones — levantamientos — productores | 1:N / N:1 | cada aplicación = 1 levantamiento |
| **(F2)** levantamientos — respuestas — preguntas | 1:N / N:1 | |
| **(F2)** levantamientos — actividades | N:0..1 | vínculo opcional |

---

## 10. Decisiones abiertas

> Ligadas a las reglas pendientes de `03` §27. Cada una tiene un mecanismo provisional que **no**
> bloquea la V1 de actividades.

| ID | Decisión abierta | Mecanismo provisional en el modelo | Regla `03` §27 |
|---|---|---|---|
| D-01 | Nombres oficiales y número de niveles jerárquicos | `roles`, `roles_grupo` (catálogos activables) | 1 |
| D-02 | ¿Jerarquía de grupos multinivel? | `grupos.grupo_padre_id` nullable; se puede ignorar en V1 | 1, 4 |
| D-03 | Estructura territorial definitiva | catálogos `estados`/`municipios`/`localidades` (INEGI) + `ambitos_tecnico` | 2 |
| D-04 | Alcance de consulta por nivel jerárquico | permisos `*.ver_propias` / `*.ver_grupo` / `*.ver_todas` + `config` | 4 |
| D-05 | ¿Se permite más de una jornada por día? | `UNIQUE` parcial en `jornadas` + `config.jornada.maxima_por_dia` | — |
| D-06 | Regla definitiva técnico–ECA y cantidad de ECA por técnico | `config.eca.regla_disponibilidad` + `asignaciones_tecnico_eca` + `ambitos_tecnico` | 6, 13 |
| D-07 | ¿Firma de reportes obligatoria? ¿quién firma/aprueba? | `reportes_periodo.estado` + permisos; tabla `reportes_firmas` **no** creada en V1 | 5, 6, 7 |
| D-08 | ¿PostGIS para consultas espaciales de actividades/ECA? | por ahora `numeric` lat/long + índice btree; migración aditiva a `geography` si se requiere | 15 |
| D-09 | Metodología de evaluación / calificación del técnico | **fuera de V1**: no hay tabla de puntaje; indicadores solo descriptivos | 9, 10 |
| D-10 | Estructura final del catálogo de ~5 000 ECA y su fuente | `ecas` con columnas núcleo + `ecas.metadatos` (jsonb acotado) + `lotes_importacion` | 14 |
| D-11 | Obligatoriedad de evidencia/GPS por tipo de actividad | `tipos_actividad.requiere_evidencia` / `min_fotos` / `max_fotos` + `config` | 15 |
| D-12 | Estrategia de resolución de conflictos de sincronización | V1: last-write-wins por marca de servidor + edición solo en `BORRADOR` por el autor | — |
| D-13 | Deduplicación de productores sin CURP (F2) | (nombre normalizado + municipio + fecha_nac) con revisión manual | 12 |
| D-14 | Relación oficial ECA ↔ productores (F2) | tabla `productores_eca` N:M reservada, sin regla fija | 12 |
| D-15 | ¿SSO / identidad compartida con Sembrando Vida? | **no se diseña**; ECA mantiene su propia tabla `usuarios` | — (aislamiento `03` §1) |
| D-16 | Catálogo de tenencias, unidades de medida, etc. (F2) | catálogos nuevos al activar el módulo de unidades productivas | 11 |
| D-17 | Formularios prioritarios de la primera campaña | Fase 2; `formularios` + `formularios_versiones` ya diseñados | 16 |

---

*Fin de `05_MODELO_DATOS_ECA.md`. Este documento y `04_ARQUITECTURA_OBJETIVO.md` son la base para
las migraciones Alembic de la Fase 1A, que **no** se generan todavía.*
