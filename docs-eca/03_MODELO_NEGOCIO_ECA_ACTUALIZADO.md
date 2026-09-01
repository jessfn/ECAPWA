# 03 — Modelo de negocio ECA

> **Propósito.** Definir las reglas funcionales y el alcance inicial del nuevo sistema para Escuelas de Campo (ECA), independiente del sistema de Sembrando Vida, pero reutilizando parte de su base tecnológica: PWA, georreferencia, evidencia fotográfica, trabajo offline y sincronización.
>
> **Estado.** Documento funcional V1. Las reglas institucionales aún no confirmadas se identifican explícitamente como pendientes para evitar hardcodearlas.

---

## 1. Principio general

El sistema ECA será un sistema independiente del sistema de Sembrando Vida.

No se migrarán los registros históricos de Sembrando Vida como si fueran actividades ECA. La aplicación ECA podrá reutilizar componentes técnicos del proyecto clonado, pero su modelo funcional, catálogos, jerarquía, actividades, productores y formularios serán propios.

La V1 debe permitir iniciar operación aun cuando algunas reglas institucionales todavía no estén formalmente definidas.

---

## 2. Objetivo de la V1

La primera versión debe permitir:

- administrar usuarios técnicos;
- organizar técnicos en grupos;
- asignar responsables de grupo;
- registrar y administrar un catálogo de aproximadamente 5,000 ECA;
- importar ECA masivamente;
- definir ámbitos geográficos de trabajo por técnico;
- asignar técnicos a una o varias ECA;
- registrar jornadas de trabajo;
- registrar actividades georreferenciadas;
- capturar evidencia fotográfica;
- clasificar actividades por tipo, tema, subtema y sistema productivo;
- registrar participantes cuando aplique;
- trabajar sin conexión;
- sincronizar posteriormente sin duplicar registros;
- consultar actividades en historial y mapa;
- generar indicadores descriptivos de operación;
- generar un reporte periódico básico por técnico.

La V1 no debe depender de una calificación o esquema de evaluación institucional todavía no definido.

---

## 3. Alcance posterior

Se deja preparada la arquitectura para una segunda etapa con:

- productores;
- unidades productivas;
- cultivos o sistemas productivos por unidad;
- formularios dinámicos;
- versiones de formularios;
- levantamientos individuales;
- respuestas;
- asignación de formularios;
- indicadores productivos y ambientales;
- revisión y aprobación formal;
- firma de reportes.

---

## 4. Actores

### 4.1 Administrador ECA

En V1 es el rol con mayor capacidad funcional.

Puede:

- crear/importar usuarios;
- activar o desactivar usuarios;
- administrar grupos;
- asignar técnicos a grupos;
- definir responsables de grupo;
- crear y editar ECA;
- asignar técnicos a ECA;
- administrar catálogos;
- consultar actividades;
- consultar mapas;
- consultar reportes;
- administrar formularios cuando el módulo sea activado.

Los permisos deben modelarse de forma independiente del nombre del cargo.

### 4.2 Técnico

Usuario de campo que:

- inicia y termina su jornada;
- consulta sus ECA asignadas;
- registra actividades;
- captura GPS y evidencia;
- trabaja offline;
- sincroniza registros;
- posteriormente registra productores y levantamientos.

### 4.3 Enlace / responsable de grupo

Nombre provisional.

Representa a la persona responsable de un grupo de técnicos.

Puede requerir en el futuro:

- consultar actividades del grupo;
- consultar reportes;
- revisar reportes;
- realizar observaciones;
- aprobar o firmar.

Estas facultades no se consideran obligatorias en V1 hasta que sean confirmadas institucionalmente.

### 4.4 Supervisor de enlaces

Nivel superior aún no definido formalmente.

Debe poder representarse en el modelo sin requerir una estructura fija de cargos.

---

## 5. Grupos de trabajo

Debido a que la jerarquía institucional todavía no está completamente definida, la organización de usuarios debe ser flexible.

Conceptualmente:

```text
GRUPO
 ├── RESPONSABLE(S)
 └── TÉCNICOS
```

Ejemplos:

- Grupo Café Chiapas 01
- Grupo Puebla Norte
- Grupo ECA 17

Un usuario puede tener un rol dentro del grupo:

- TECNICO
- ENLACE
- SUPERVISOR

Los nombres oficiales podrán cambiar posteriormente.

La relación grupo–usuario debe tener:

- fecha de inicio;
- fecha de fin;
- estado activo/inactivo;
- rol dentro del grupo;
- usuario que realizó la asignación.

No se debe guardar al supervisor únicamente como texto.

---

## 6. ECA

Una Escuela de Campo es una entidad propia del sistema.

El sistema debe soportar inicialmente un catálogo aproximado de **5,000 ECA**, con posibilidad de crecimiento.

### 6.1 Datos mínimos de una ECA

Debe permitir al menos:

- identificador interno;
- clave o código institucional;
- nombre;
- estado;
- municipio;
- localidad, cuando esté disponible;
- coordenadas de referencia opcionales;
- sistema(s) productivo(s) asociado(s), cuando estén disponibles;
- estado activo/inactivo;
- metadatos adicionales posteriores.

La clave institucional de ECA, cuando exista, debe conservarse separada del identificador interno.

### 6.2 Catálogos geográficos

Estado y municipio no deben capturarse como texto libre. Deben provenir de catálogos geográficos normalizados, preferentemente con claves oficiales cuando corresponda.

```text
ESTADO
   └── MUNICIPIO
          └── ECA
```

Esto permitirá filtros consistentes, análisis territorial, mapas y explotación posterior.

### 6.3 Carga masiva de ECA

El panel administrativo debe permitir cargar o actualizar el catálogo de ECA mediante CSV y/o XLSX.

Campos mínimos esperados:

- clave de ECA;
- nombre;
- estado;
- municipio;
- activo.

Campos opcionales:

- localidad;
- latitud;
- longitud;
- sistema productivo;
- otros metadatos institucionales.

La importación debe validar duplicados, claves geográficas y errores por fila antes de confirmar cambios.

### 6.4 Ámbito geográfico del técnico

Mientras no exista una relación institucional completa entre técnicos y ECA, cada técnico podrá tener definido un **ámbito geográfico de trabajo**.

Un técnico puede trabajar en uno o varios municipios. No se debe modelar como una única columna `municipio` dentro del usuario.

```text
TÉCNICO
   └── MUNICIPIOS DE TRABAJO
```

La relación debe permitir múltiples municipios por técnico y conservar vigencia/estado de la asignación cuando sea necesario.

### 6.5 Asignación directa técnico–ECA

El sistema debe soportar una relación explícita entre técnicos y ECA:

```text
TÉCNICO
   └── ECA ASIGNADAS
```

Un técnico puede tener una o varias ECA y una ECA puede estar asociada a uno o varios técnicos.

La relación técnico–ECA debe ser independiente de la pertenencia del técnico a un grupo de trabajo.

### 6.6 Regla provisional de disponibilidad de ECA

Mientras la institución no entregue una relación completa técnico–ECA:

```text
SI el técnico tiene ECA asignadas explícitamente:
    mostrar/priorizar sus ECA asignadas

SI el técnico todavía no tiene ECA asignadas explícitamente:
    mostrar las ECA correspondientes a sus municipios de trabajo
```

Esta regla es provisional y debe ser configurable. No se debe hardcodear como una regla institucional definitiva.

### 6.7 Selección de ECA en la actividad

El técnico no debe navegar una lista plana de aproximadamente 5,000 registros.

La selección debe permitir:

- filtrado por estado;
- filtrado por municipio;
- búsqueda por clave;
- búsqueda por nombre;
- búsqueda por localidad, cuando exista;
- presentación prioritaria de ECA asignadas directamente.

Cuando el perfil del técnico ya determine su ámbito, la aplicación debe precargar esos filtros.

### 6.8 Operación offline del catálogo ECA

La PWA no necesita descargar obligatoriamente las ~5,000 ECA nacionales en cada dispositivo.

Durante sincronización debe descargar únicamente el subconjunto relevante para el técnico:

1. sus ECA asignadas directamente; o
2. en ausencia de asignación directa, las ECA de sus municipios de trabajo.

Este subconjunto debe quedar disponible offline.

### 6.9 Separación entre grupo, ámbito y ECA

```text
TÉCNICO
   ├── GRUPO DE TRABAJO
   │      └── organización / supervisión
   ├── ÁMBITO GEOGRÁFICO
   │      └── dónde puede operar
   └── ECA ASIGNADAS
          └── escuelas concretas bajo su atención
```

Estos conceptos no deben fusionarse.

---

## 7. Jornada

La jornada representa el periodo operativo del técnico durante un día.

### V1

Registrar:

- técnico;
- fecha;
- hora de inicio;
- hora de término;
- estado.

La fotografía no debe ser obligatoria para iniciar o terminar jornada.

La georreferencia tampoco debe considerarse evidencia principal de jornada.

La evidencia principal se captura en las actividades.

Regla inicial:

> Máximo una jornada principal por técnico por fecha, salvo que posteriormente exista una necesidad institucional distinta.

---

## 8. Actividad

La actividad es la unidad principal de evidencia operativa de la V1.

Cada actividad debe responder:

> ¿Qué hizo el técnico, sobre qué tema, en qué sistema productivo, dónde, cuándo y con qué evidencia?

### Campos mínimos

- UUID generado en dispositivo;
- técnico;
- jornada;
- ECA;
- fecha/hora;
- modalidad;
- tipo de actividad;
- tema;
- subtema;
- sistema productivo/cultivo;
- descripción;
- resultado;
- GPS;
- precisión GPS;
- evidencia fotográfica;
- participantes, cuando aplique;
- seguimiento requerido;
- próxima fecha de seguimiento opcional;
- fecha de creación;
- fecha de sincronización.

### Evidencia

Una actividad puede tener de 1 a 3 fotografías cuando el tipo de actividad requiera evidencia.

La obligatoriedad de fotografía debe ser configurable por tipo de actividad, no hardcodeada globalmente.

Nunca se deben generar fotografías placeholder para simular evidencia inexistente.

---

## 9. Catálogo de tipo de actividad — V1

| Código | Tipo |
|---|---|
| CAP | Capacitación / sesión ECA |
| ATE | Acompañamiento técnico |
| VIS | Visita de seguimiento |
| MON | Monitoreo / diagnóstico |
| PRA | Práctica / demostración |
| ORG | Asamblea / reunión |
| INT | Intercambio / día de campo |
| GES | Gestión / vinculación |
| EVA | Evaluación / seguimiento |
| OTR | Otra |

El catálogo debe almacenarse en base de datos y permitir activar/desactivar valores.

---

## 10. Temas de actividad — V1

Catálogo inicial:

- Manejo del cultivo
- Bioinsumos
- Suelo
- Agua
- Sanidad vegetal
- Semillas
- Agrobiodiversidad
- Huertos
- Cosecha / poscosecha
- Organización de productores
- Comercialización
- Ganadería
- Apicultura
- Otro

El tema representa el contenido de la actividad, no la acción realizada.

Ejemplo:

```text
Tipo: Capacitación
Tema: Bioinsumos
Subtema: Elaboración de composta
Sistema productivo: Café
```

frente a:

```text
Tipo: Acompañamiento técnico
Tema: Bioinsumos
Subtema: Aplicación de composta
Sistema productivo: Café
```

---

## 11. Subtemas

Los subtemas dependen del tema.

Ejemplos iniciales:

```text
Bioinsumos
 ├── Composta
 ├── Biofertilizantes
 ├── Biopreparados
 └── Microorganismos

Suelo
 ├── Fertilidad
 ├── Conservación
 ├── Muestreo
 └── Cobertura

Sanidad vegetal
 ├── Identificación de plagas
 ├── Enfermedades
 ├── Arvenses
 └── Manejo preventivo
```

La V1 no necesita un catálogo exhaustivo.

El administrador debe poder ampliar los subtemas posteriormente.

---

## 12. Sistema productivo / cultivo

No se debe mezclar el cultivo con el tipo de actividad.

Catálogo inicial sugerido:

- Maíz
- Frijol
- Milpa
- Trigo
- Arroz
- Café
- Caña de azúcar
- Cacao
- Amaranto
- Chía
- Miel / Apicultura
- Leche / Ganadería
- Hortalizas
- Otro

Debe ser administrable desde catálogo.

Una actividad puede vincularse inicialmente a un sistema productivo principal.

La posibilidad de múltiples sistemas por actividad puede agregarse posteriormente si la operación lo requiere.

---

## 13. Participantes y productores atendidos

Los conceptos no deben mezclarse.

### Participaciones grupales

Número de personas que participan en una actividad grupal.

Ejemplo:

```text
Capacitación:
30 participantes
```

### Productores únicos atendidos

Productores identificados individualmente y vinculados a una interacción o levantamiento durante el periodo.

Ejemplo:

```text
Levantamientos: 5
Personas:
Ana
Pedro
Luis
Ana
Pedro

Productores únicos atendidos: 3
Levantamientos: 5
```

La participación grupal no debe sumarse automáticamente a productores únicos.

---

## 14. Productor — modelo conceptual

Un productor es una persona que realiza actividad productiva y puede tener una o varias unidades productivas.

Modelo conceptual:

```text
PRODUCTOR
   └── UNIDAD PRODUCTIVA
          └── CULTIVO / SISTEMA PRODUCTIVO
```

El productor debe ser una entidad independiente del usuario técnico.

Datos mínimos previstos:

- UUID;
- CURP cuando exista;
- nombre;
- apellidos;
- datos de localización;
- estado;
- metadatos de creación y actualización.

La CURP no debe ser la única clave interna del sistema.

---

## 15. Unidad productiva

Una unidad productiva representa una parcela, predio o unidad donde el productor desarrolla actividad productiva.

Debe poder contener posteriormente:

- ubicación;
- superficie;
- tenencia;
- sistemas productivos;
- cultivos;
- características ambientales;
- infraestructura;
- datos derivados de formularios.

Un productor puede tener múltiples unidades productivas.

---

## 16. Levantamiento

Un levantamiento es la aplicación de un formulario a un productor.

Debe guardar:

- formulario;
- versión del formulario;
- productor;
- técnico;
- ECA;
- actividad asociada opcional;
- fecha/hora;
- respuestas;
- estado;
- UUID;
- estado de sincronización.

Cada aplicación del formulario es un levantamiento independiente.

---

## 17. Formularios dinámicos

En la primera implementación del módulo, únicamente el administrador podrá crear y publicar formularios.

Un formulario publicado quedará disponible en un catálogo.

Cuando un técnico deba aplicar uno específico, el sistema podrá mostrarlo como asignado o requerido.

### Tipos de pregunta V1

- Texto corto
- Texto largo
- Número entero
- Número decimal
- Fecha
- Sí / No
- Selección única
- Selección múltiple
- Lista desplegable
- Fotografía
- Coordenada

### Validaciones V1

- obligatorio;
- longitud mínima;
- longitud máxima;
- valor mínimo;
- valor máximo;
- número de decimales;
- opciones permitidas.

### Lógica condicional V1

Ejemplo:

```text
SI "Cuenta con riego" = Sí
MOSTRAR "Tipo de riego"
```

No se consideran V1:

- matrices complejas;
- scripts;
- fórmulas arbitrarias;
- repeticiones anidadas;
- programación dentro de formularios.

---

## 18. Versionado de formularios

Un formulario publicado no debe modificarse destructivamente.

Ejemplo:

```text
Diagnóstico Café
 ├── Versión 1
 └── Versión 2
```

Los levantamientos existentes permanecen asociados a la versión que fue contestada.

Cuando se cambia un formulario publicado:

1. se genera una nueva versión;
2. los levantamientos históricos permanecen intactos;
3. los nuevos levantamientos usan la nueva versión.

Para el usuario administrativo podrá seguir viéndose como un único formulario con historial de versiones.

---

## 19. Trabajo offline

La aplicación debe asumir que los técnicos pueden trabajar durante periodos sin conexión.

### Requisitos

Los catálogos y formularios necesarios se descargan cuando existe internet.

Durante trabajo offline se guardan localmente:

- actividades;
- evidencias;
- productores;
- levantamientos;
- respuestas;
- metadatos de sincronización.

Cada objeto creado offline debe utilizar un UUID estable generado en dispositivo.

El servidor debe garantizar idempotencia:

```text
Mismo UUID enviado varias veces
=
Mismo recurso
```

No se deben identificar duplicados interpretando textos de errores.

---

## 20. Georreferencia

La ubicación debe ser evidencia de la actividad.

Guardar:

- latitud;
- longitud;
- precisión GPS;
- timestamp de captura.

No se deben inventar coordenadas cuando no existe permiso o señal GPS.

En ese caso:

```text
estado_gps = SIN_GPS
```

o equivalente.

---

## 21. Análisis del Agroecosistema — AESA

Dentro de Monitoreo / diagnóstico podrá existir el subtema:

**Análisis del agroecosistema (AESA)**

Campos futuros posibles:

- etapa fenológica;
- estado general del cultivo;
- plagas;
- enfermedades;
- arvenses;
- humedad/suelo;
- problema observado;
- recomendación;
- fotografía;
- ubicación.

No es obligatorio implementar todos estos campos en la primera liberación de actividades.

---

## 22. Indicadores V1

Mientras no exista una metodología institucional de evaluación, el sistema no asignará una calificación o puntaje al técnico.

Debe generar indicadores descriptivos.

### Operación

- jornadas registradas;
- actividades realizadas;
- actividades de campo;
- actividades de gabinete;
- ECA atendidas;
- municipios/localidades atendidos.

### Tipo de intervención

- capacitaciones;
- acompañamientos;
- visitas;
- monitoreos;
- prácticas;
- asambleas;
- intercambios;
- gestiones;
- evaluaciones.

### Temática

- actividades por tema;
- actividades por subtema;
- actividades por sistema productivo.

### Evidencia

- porcentaje con fotografía;
- porcentaje con GPS;
- porcentaje con precisión GPS válida.

### Productores — cuando el módulo exista

- productores únicos atendidos;
- levantamientos realizados;
- participaciones grupales.

### Seguimiento

- actividades que requieren seguimiento;
- seguimientos pendientes;
- seguimientos realizados.

---

## 23. Evaluación del técnico

En V1:

> El sistema describe actividad y cobertura; no determina desempeño institucional.

No se utilizará todavía un esquema como:

```text
85/100
```

ni ponderaciones arbitrarias por actividad.

Una evaluación formal podrá agregarse cuando la institución defina:

- metas;
- pesos;
- periodicidad;
- criterios;
- excepciones;
- responsables de validación.

---

## 24. Reporte periódico V1

El reporte por técnico podrá mostrar:

```text
Técnico
Grupo
Responsable
Periodo

Jornadas
Actividades totales
Campo
Gabinete
ECA atendidas

Capacitaciones
Acompañamientos
Visitas
Monitoreos
Prácticas
Asambleas
Intercambios
Gestiones
Evaluaciones

Temas trabajados
Sistemas productivos

Participaciones grupales
Productores únicos — cuando exista módulo
Levantamientos — cuando exista módulo

Mapa
Listado/resumen de actividades
Seguimientos pendientes
```

Los datos del reporte deben calcularse desde registros transaccionales del sistema.

---

## 25. Revisión y aprobación

Estados previstos:

- BORRADOR
- ENVIADO
- REVISADO
- OBSERVADO
- APROBADO

Campos previstos:

- revisado_por;
- fecha_revision;
- comentario_revision.

La firma no será obligatoria en V1 hasta tener confirmación institucional.

La arquitectura debe permitir agregarla posteriormente.

---

## 26. Decisiones que NO deben hardcodearse

No hardcodear:

- nombres definitivos de cargos jerárquicos;
- número de niveles de supervisión;
- número de técnicos por enlace;
- quién firma;
- quién aprueba;
- metas mensuales;
- ponderaciones;
- territorios definitivos;
- regla definitiva de asignación técnico–ECA;
- cantidad definitiva de ECA por técnico;
- catálogo completo de cultivos;
- catálogo completo de subtemas;
- formularios específicos;
- obligatoriedad universal de fotografías;
- obligatoriedad universal de GPS.

Estas reglas deben resolverse mediante catálogos, permisos, configuración o asignaciones.

---

## 27. Reglas pendientes de definición institucional

Pendientes:

1. nombre oficial de los niveles jerárquicos;
2. estructura territorial definitiva;
3. cantidad esperada de técnicos por enlace;
4. alcance de consulta de cada nivel;
5. quién revisa reportes;
6. quién aprueba reportes;
7. si se requiere firma;
8. periodicidad oficial de reporte;
9. metas mensuales;
10. metodología formal de evaluación;
11. catálogos institucionales finales;
12. relación oficial entre ECA y productores;
13. relación institucional definitiva técnico–ECA;
14. fuente oficial y estructura final del catálogo de ~5,000 ECA;
15. obligatoriedad de evidencias por tipo de actividad;
16. formularios prioritarios de la primera campaña.

La falta de definición de estos puntos no debe bloquear la implementación de la V1 de actividades.

---

## 28. Orden recomendado de implementación

### Fase 1A — Base técnica

- seguridad de autenticación;
- usuarios;
- permisos;
- grupos;
- catálogos geográficos;
- ámbitos geográficos de técnicos;
- ECA;
- importación masiva de ECA;
- asignaciones técnico–ECA;
- catálogos;
- sincronización idempotente.

### Fase 1B — Operación en campo

- jornada simplificada;
- nueva actividad ECA;
- GPS;
- precisión;
- evidencia;
- offline;
- historial;
- mapa.

### Fase 1C — Reporte

- indicadores descriptivos;
- filtros;
- reporte por técnico;
- revisión básica.

### Fase 2 — Información productiva

- productor;
- unidad productiva;
- cultivos;
- formularios;
- versiones;
- levantamientos;
- respuestas;
- asignaciones;
- indicadores avanzados.

---

## 29. Regla principal para desarrollo

> Ante una regla institucional no confirmada, el sistema debe preferir una estructura configurable y documentar el pendiente en lugar de convertir una suposición en código permanente.
