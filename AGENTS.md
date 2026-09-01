# Instrucciones para agentes de programación — Migración ECA

## Contexto
Este repositorio ya está en operación para un negocio relacionado con Sembrando Vida. La meta es incorporar un nuevo modelo ECA sin destruir funciones maduras como autenticación, PWA, GPS, trabajo offline, sincronización, usuarios y administración.

## Reglas obligatorias

1. **No reescribir el sistema desde cero.**
2. **No cambiar simultáneamente backend, frontend, modelo de datos y offline sin un plan de migración explícito.**
3. **No eliminar tablas ni columnas existentes en una primera migración.** Preferir cambios aditivos y deprecación controlada.
4. **No modificar migraciones históricas.** Crear nuevas migraciones versionadas.
5. **No agregar más lógica ECA a `backend/main.py` o `pwasuper/src/views/Home.vue` salvo adaptadores mínimos.** Los módulos nuevos deben nacer separados.
6. **No almacenar contraseñas en texto plano.** Cualquier flujo nuevo debe usar hashing seguro.
7. **No registrar CURP completa, contraseñas, tokens o datos sensibles en logs.**
8. **No confiar solo en validación frontend.** Repetir restricciones críticas en backend y BD.
9. **Todo objeto creado offline debe usar UUID estable generado en cliente.**
10. **Todos los POST de sincronización deben ser idempotentes.** Un reintento no puede duplicar actividad, productor, levantamiento ni respuesta.
11. **Los formularios publicados son inmutables.** Una modificación genera una nueva versión.
12. **No mezclar participantes de una actividad grupal con productores únicos atendidos.** Son indicadores distintos.
13. **Productores únicos atendidos deben calcularse a partir de productores identificados vinculados a levantamientos válidos.**
14. Antes de implementar una funcionalidad, documentar:
   - tablas afectadas;
   - endpoints nuevos/modificados;
   - stores IndexedDB afectados;
   - reglas offline;
   - estrategia de rollback;
   - pruebas mínimas.

## Estrategia de ramas / entregas
Cada módulo debe implementarse de manera independiente y revisable:

```text
feature/eca-catalogos
feature/eca-ecas
feature/eca-productores
feature/eca-formularios
feature/eca-levantamientos
feature/eca-actividades
feature/eca-offline-sync
feature/eca-reportes
```

No se requiere usar exactamente estos nombres, pero sí mantener cambios pequeños y temáticos.

## Orden de implementación recomendado

### Fase A — Preparación
- auditoría completa;
- pruebas smoke del sistema actual;
- corrección prioritaria de seguridad crítica;
- definir migraciones y convención UUID.

### Fase B — Catálogos y estructura ECA
- ECA;
- asignación técnico–ECA;
- catálogos de modalidad / tipo / tema;
- endpoints de lectura.

### Fase C — Productores
- entidad productor;
- normalización CURP;
- deduplicación;
- permisos;
- búsqueda offline/online.

### Fase D — Formularios dinámicos
- formulario;
- versión;
- sección/pregunta;
- opciones;
- restricciones;
- publicación;
- reglas condicionales simples.

### Fase E — Levantamientos
- respuesta por productor;
- vínculo con actividad;
- almacenamiento offline;
- sincronización idempotente.

### Fase F — Actividades ECA
- simplificar jornada;
- adaptar nueva actividad;
- asociar ECA / tipo / tema;
- evidencia;
- lanzamiento de levantamientos desde actividad.

### Fase G — Reportes
- actividades;
- ECA atendidas;
- productores únicos;
- levantamientos;
- participaciones grupales;
- temas;
- mapas;
- filtros por jerarquía / ámbito.

## Definition of Done mínima por módulo
Un módulo no se considera terminado si no incluye:
- migración de BD;
- modelos/esquemas backend;
- autorización;
- endpoint(s);
- manejo de errores;
- integración frontend;
- comportamiento offline si aplica;
- prueba de reintento de sincronización si aplica;
- documentación de cambios;
- validación de que el sistema previo continúa funcionando.
