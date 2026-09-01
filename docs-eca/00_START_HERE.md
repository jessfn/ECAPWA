# ECA — Punto de inicio

## Objetivo
Adaptar la PWA existente de Seguimiento SADER / Sembrando Vida a un nuevo modelo de negocio para técnicos de Escuelas de Campo (ECA), conservando los componentes maduros del sistema y evitando una reescritura completa.

## Principio rector
No comenzar implementando pantallas nuevas de forma aislada. Primero se debe separar:

1. **Lo reutilizable del sistema actual**: autenticación, usuarios, PWA, GPS, evidencia fotográfica, operación offline, sincronización, administración y reportes.
2. **Lo específico de Sembrando Vida**: categorías actuales, territorios usados como concepto de negocio, relación facilitador-técnico y reglas actuales de jornada.
3. **Lo nuevo para ECA**: ECA, productores, asignaciones técnico–ECA, formularios dinámicos, versiones de formulario, levantamientos por productor, respuestas, indicadores y reportes ECA.

## Decisiones funcionales acordadas para la primera versión

### Jornada
- Mantener inicio y término de jornada.
- Eliminar fotografía obligatoria para iniciar y terminar jornada.
- Eliminar descripción obligatoria de inicio/término.
- Revisar si el GPS de jornada aporta valor; el GPS importante será el de la actividad.
- La jornada sirve como marco temporal, no como evidencia principal del trabajo.

### Actividades
Cada actividad debe registrar, como mínimo:
- Técnico.
- Fecha y hora.
- Coordenadas y precisión GPS.
- Modalidad: campo / gabinete.
- ECA asociada cuando aplique.
- Tipo de actividad.
- Tema de actividad.
- Descripción / resultado.
- Evidencia fotográfica cuando la regla de negocio lo exija.

### Productores y levantamientos
- **No usar “número de productores atendidos” como indicador principal declarado por el técnico.**
- Crear entidad `productor`.
- Identificar y deduplicar productores mediante CURP cuando esté disponible y sea válido.
- Un levantamiento corresponde a un productor + un formulario + una versión del formulario + técnico + fecha/hora.
- Los productores únicos atendidos se calculan desde levantamientos válidos.
- Para actividades grupales se puede registrar número de participantes como indicador distinto de productores únicos.

### Formularios dinámicos
Un superior autorizado debe poder crear y publicar formularios para levantamientos específicos, por ejemplo “Diagnóstico de café 2026”.

V1 debe soportar:
- texto corto;
- texto largo;
- entero;
- decimal;
- sí/no;
- selección única;
- selección múltiple;
- fecha;
- fotografía;
- GPS;
- obligatoriedad;
- límites numéricos;
- longitud mínima/máxima;
- reglas condicionales simples.

Todo formulario publicado debe quedar **versionado**. Una edición posterior no puede modificar retroactivamente las respuestas históricas.

## Arquitectura conceptual objetivo

```text
USUARIO / TÉCNICO
│
├── JORNADAS
│
├── ASIGNACIONES ──> ECA
│
├── ACTIVIDADES
│   ├── GPS
│   ├── EVIDENCIAS
│   └── LEVANTAMIENTOS (0..n)
│       ├── PRODUCTOR
│       ├── FORMULARIO
│       ├── VERSIÓN
│       └── RESPUESTAS
│
└── REPORTES CALCULADOS
```

## Orden recomendado
1. Congelar una versión base del repositorio actual.
2. Auditar código, modelo de datos, endpoints y sincronización offline.
3. Definir modelo de negocio ECA y reglas de indicadores.
4. Diseñar modelo de datos y contratos API.
5. Diseñar estrategia de migración sin romper usuarios existentes.
6. Implementar por módulos pequeños.
7. Probar primero con un grupo piloto antes de desplegar a ~1,200 técnicos.

## Regla para el agente de programación
Antes de modificar código, leer `01_AUDITORIA_INICIAL.md` y `AGENTS.md`. No realizar refactorizaciones masivas ni cambios de esquema destructivos sin una migración explícita y reversible.
