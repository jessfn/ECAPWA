# Auditoría inicial del sistema existente

> Estado: primera radiografía del repositorio. Este documento debe ampliarse antes de la implementación.

## Stack encontrado

### PWA de técnicos
- Vue 3.
- Vite.
- Vue Router.
- Axios.
- IndexedDB mediante código propio y `idb-keyval`.
- PWA mediante `vite-plugin-pwa`.
- Leaflet.
- Compresión / manejo de imágenes.
- Generación de PDF en cliente.

### Panel administrativo
- Vue 3 + Vite.
- Servicios para usuarios, permisos, asistencias, reportes, dispositivos, historial, estadísticas e imágenes.

### Backend
- FastAPI.
- PostgreSQL mediante `psycopg2`.
- JWT / bcrypt / passlib presentes.
- Generación PDF mediante ReportLab.
- Archivo principal `backend/main.py` de aproximadamente 12 mil líneas.

## Hallazgos estructurales

### 1. Backend monolítico
`backend/main.py` concentra modelos, migraciones, autenticación, acceso a BD, endpoints, reportes y lógica de negocio. Agregar ECA + productores + formularios + levantamientos directamente en ese archivo aumentaría mucho el acoplamiento.

**Recomendación:** modularización progresiva, no reescritura completa.

Posible estructura futura:

```text
backend/
  main.py
  routers/
    auth.py
    usuarios.py
    jornadas.py
    actividades.py
    ecas.py
    productores.py
    formularios.py
    levantamientos.py
    reportes.py
  schemas/
  services/
  repositories/
```

### 2. `Home.vue` concentra demasiada lógica
`pwasuper/src/views/Home.vue` supera las 6 mil líneas y contiene UI y lógica relacionada con jornada, actividad, GPS, imágenes, validaciones y sincronización.

**Recomendación:** extraer gradualmente vistas y componentes ECA nuevos en vez de seguir incrementando `Home.vue`.

### 3. Usuarios existentes deben conservarse
La tabla `usuarios` y las cuentas existentes deben funcionar como identidad base. ECA debe agregarse mediante roles/perfiles/asignaciones, no mediante una segunda tabla de autenticación independiente.

### 4. CURP ya existe en usuarios
El backend actualmente exige CURP para creación de ciertos usuarios y verifica duplicidad. Este patrón puede servir como referencia para productores, pero la entidad `productor` debe ser independiente de `usuarios`.

### 5. Categorías de actividad están codificadas en backend
El endpoint de registros valida categorías contra un catálogo codificado en código y aplica valores por defecto de Sembrando Vida.

Para ECA se recomienda:
- catálogo persistido en BD;
- catálogos independientes para modalidad, tipo de actividad y tema;
- posibilidad de activar/desactivar categorías sin desplegar código.

### 6. Actividad actual
El registro de actividad actual se persiste aproximadamente con:

```text
usuario_id
latitud
longitud
descripcion
foto_url
fecha_hora
tipo_actividad
categoria_actividad
categoria_actividad_otro
```

La entidad ECA futura requerirá al menos:

```text
uuid
usuario_id / tecnico_id
jornada_id
eca_id
modalidad_id
tipo_actividad_id
tema_id
latitud
longitud
precision_gps
fecha_hora_inicio
fecha_hora_fin (opcional)
descripcion
resultado
estado_sync
created_at
updated_at
```

Las fotografías deberían moverse conceptualmente a una relación `actividad_evidencia` para soportar 1..n evidencias sin ensanchar la tabla principal.

### 7. Offline ya es una fortaleza del sistema
La PWA usa IndexedDB con stores separados para registros y asistencias. Los registros offline incluyen metadatos útiles como estado, intentos, fecha de creación e `id_cliente`.

Esto debe conservarse, pero ECA necesitará más entidades offline:
- actividades;
- productores pendientes de creación/actualización;
- formularios publicados y sus versiones;
- levantamientos;
- respuestas;
- evidencias.

### 8. Riesgo de duplicados / idempotencia
`id_cliente` existe en registros offline, pero el nuevo modelo debe formalizar UUID de cliente y restricciones únicas en servidor para que un reintento de sincronización no cree el mismo levantamiento dos veces.

### 9. Conexión PostgreSQL compartida
El backend mantiene una conexión/cursor global y ya contiene comentarios que reconocen problemas de concurrencia en ciertos endpoints, usando conexiones aisladas para algunos casos.

Para una población de ~1,200 técnicos, esto debe revisarse antes de escalar módulos de sincronización y formularios.

**Recomendación futura:** pool de conexiones y transacciones por request / unidad de trabajo.

### 10. Seguridad: hallazgo crítico a revisar
En el flujo `/usuarios`, el código contiene explícitamente el comentario “contraseña sin encriptar” al insertar un usuario. A la vez existen bcrypt/passlib en el proyecto.

Esto requiere una auditoría específica antes del despliegue ECA:
- determinar qué cuentas están almacenadas en texto plano;
- unificar hashing de contraseñas;
- diseñar migración gradual de credenciales;
- impedir exposición de CURP y otros datos personales en respuestas o logs;
- revisar autorización real de endpoints, no solo autenticación.

No migrar productores/CURP/datos productivos sensibles hasta cerrar esta revisión.

## Qué se conserva / adapta / crea

| Componente | Decisión |
|---|---|
| Autenticación / identidad | Conservar y corregir seguridad |
| Usuarios actuales | Conservar |
| PWA Vue | Conservar |
| Panel administrativo | Conservar y extender |
| GPS | Conservar para actividades |
| Evidencia fotográfica | Conservar para actividades |
| Offline / IndexedDB | Conservar y ampliar |
| Sincronización | Conservar concepto, robustecer |
| Jornada | Simplificar |
| Foto en inicio/término | Eliminar como requisito |
| Descripción inicio/término | Eliminar como requisito |
| Categorías Sembrando Vida | Sustituir por catálogos ECA |
| Territorio | Auditar y generalizar |
| Facilitador–técnico | Auditar y mapear a jerarquía ECA |
| ECA | Crear |
| Técnico–ECA | Crear |
| Productor | Crear |
| Formularios dinámicos | Crear |
| Versiones de formulario | Crear |
| Levantamientos | Crear |
| Respuestas | Crear |
| Reportes ECA | Crear sobre datos transaccionales |

## Siguiente auditoría requerida
Antes de implementar se deben producir inventarios de:
1. tablas reales y columnas actuales;
2. endpoints y consumidores frontend;
3. stores offline y flujo de sincronización;
4. roles/permisos y jerarquía actual;
5. reportes y reglas de cálculo actuales;
6. referencias explícitas a `territorio`, `facilitador`, `Sembrando Vida` y categorías codificadas;
7. secretos/configuración y riesgos de seguridad;
8. estrategia de migración de los ~120 usuarios ya cargados y posterior carga hasta ~1,200.
