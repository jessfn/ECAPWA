<!-- admin-eca — pantalla "Actividades" (ECA-019). Rediseño pedido
     explícito: mismo lenguaje visual que `RegistrosView.vue` de
     admin-pwa — tabla con scroll interno (encabezado fijo), miniatura de
     evidencia por fila, badges de tipo/GPS, botones de acción circulares,
     avatar + nombre real del técnico (el listado del backend solo trae
     `usuario_id`, se cruza con `GET /usuarios`), nombre real de la ECA
     (se cruza con `GET /ecas`), y paginación real con los metadatos que
     el backend ya devuelve (`total/page/page_size`). La miniatura usa
     `primera_evidencia_id` (una sola consulta extra para toda la página,
     ver `repo_evidencias.primera_por_actividad` en el backend — nunca
     N+1); el detalle completo con galería sigue en
     `ActividadDetalleView.vue`. -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { RouterLink } from 'vue-router'
import { listarEstados, listarMunicipios } from '../services/geoService'
import { listarCatalogo } from '../services/catalogosService'
import { listarActividades, exportarCsv, urlVistaPreviaEvidencia } from '../services/actividadesService'
import { listarEcas } from '../services/ecasService'
import { api } from '../services/api'
import AuthIcon from '../components/auth/AuthIcon.vue'

const tecnicos = ref([])
const tecnicosPorId = computed(() => new Map(tecnicos.value.map((t) => [t.id, t])))
const ecasPorId = ref(new Map())

const tecnicoId = ref(null)
const estados = ref([])
const estadoId = ref(null)
const municipios = ref([])
const municipioId = ref(null)
const tiposActividad = ref([])
const tipoActividadId = ref(null)
const estadoGps = ref('')
const desde = ref('')
const hasta = ref('')

const actividades = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const cargando = ref(false)
const error = ref('')
const exportando = ref(false)

const ETIQUETAS_GPS = { CON_GPS: 'Con GPS', GPS_IMPRECISO: 'GPS impreciso', SIN_GPS: 'Sin GPS' }
const BADGE_GPS = { CON_GPS: 'eca-badge--verde', GPS_IMPRECISO: 'eca-badge--ambar', SIN_GPS: 'eca-badge--gris' }
const COLORES_TIPO = ['morado', 'verde', 'azul', 'ambar']

// Miniatura de evidencia: `evidenciaId -> object URL`, cargadas bajo
// demanda solo para las filas visibles de la página actual (nunca todas
// las evidencias de golpe). Se liberan (`URL.revokeObjectURL`) al
// cambiar de página o desmontar la vista — si no, cada blob se queda
// vivo en memoria del navegador para siempre.
const vistasPrevias = ref({})
function limpiarVistasPrevias() {
  for (const url of Object.values(vistasPrevias.value)) URL.revokeObjectURL(url)
  vistasPrevias.value = {}
}
async function cargarVistasPrevias(lista) {
  for (const a of lista) {
    if (!a.primera_evidencia_id) continue
    urlVistaPreviaEvidencia(a.primera_evidencia_id)
      .then((url) => {
        vistasPrevias.value = { ...vistasPrevias.value, [a.primera_evidencia_id]: url }
      })
      .catch(() => {})
  }
}

const totalPaginas = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

// Estadísticas SOLO de la página actual (el backend pagina server-side —
// no hay un endpoint de agregados sobre el total filtrado). Se etiqueta
// explícitamente "en esta página" para no insinuar un dato que no es.
const statsPagina = computed(() => ({
  conGps: actividades.value.filter((a) => a.estado_gps === 'CON_GPS').length,
  impreciso: actividades.value.filter((a) => a.estado_gps === 'GPS_IMPRECISO').length,
  sinGps: actividades.value.filter((a) => a.estado_gps === 'SIN_GPS').length,
}))

async function cargarTecnicos() {
  try {
    const { data } = await api.get('/usuarios', { params: { rol: 'TECNICO' } })
    tecnicos.value = data
  } catch {
    // Mejor esfuerzo: si el admin actual no tiene permiso de usuarios
    // (distinto de `actividades.ver_todas`), la tabla sigue funcionando,
    // solo sin nombre/avatar — muestra "Técnico #id" en vez de tronar
    // toda la pantalla (bug real: antes esto no tenía catch y un 403
    // aquí rompía la vista completa en el `Promise.all` de `onMounted`).
    tecnicos.value = []
  }
}

async function cargarEcas() {
  try {
    const { resultados } = await listarEcas({ pageSize: 500 })
    ecasPorId.value = new Map(resultados.map((e) => [e.id, e.nombre]))
  } catch {
    ecasPorId.value = new Map()
  }
}

async function onCambioEstado() {
  municipioId.value = null
  municipios.value = estadoId.value ? await listarMunicipios(estadoId.value) : []
}

function filtrosActuales() {
  return {
    tecnicoId: tecnicoId.value || undefined,
    municipioId: municipioId.value || undefined,
    tipoActividadId: tipoActividadId.value || undefined,
    estadoGps: estadoGps.value || undefined,
    desde: desde.value || undefined,
    hasta: hasta.value || undefined,
  }
}

async function cargar() {
  cargando.value = true
  error.value = ''
  limpiarVistasPrevias()
  try {
    const respuesta = await listarActividades({ ...filtrosActuales(), page: page.value, pageSize })
    actividades.value = respuesta.resultados
    total.value = respuesta.total
    cargarVistasPrevias(respuesta.resultados)
  } catch {
    error.value = 'No se pudieron cargar las actividades.'
  } finally {
    cargando.value = false
  }
}

function aplicarFiltros() {
  page.value = 1
  cargar()
}

function irAPagina(nueva) {
  if (nueva < 1 || nueva > totalPaginas.value) return
  page.value = nueva
  cargar()
}

async function onExportar() {
  exportando.value = true
  error.value = ''
  try {
    await exportarCsv(filtrosActuales())
  } catch {
    error.value = 'No se pudo exportar el CSV.'
  } finally {
    exportando.value = false
  }
}

function tecnicoDe(actividad) {
  return tecnicosPorId.value.get(actividad.usuario_id) || null
}
function iniciales(u) {
  const n = (u?.nombre || '').trim()
  const a = (u?.apellido_paterno || '').trim()
  if (n && a) return (n[0] + a[0]).toUpperCase()
  return '??'
}
function ecaNombre(actividad) {
  if (actividad.eca_id) return ecasPorId.value.get(actividad.eca_id) || `ECA #${actividad.eca_id}`
  // Escrita a mano por el técnico cuando no tenía ninguna ECA de catálogo
  // para elegir (ver 0021) — se marca para distinguirla de una ECA real.
  if (actividad.eca_nombre) return `${actividad.eca_nombre} (escrita)`
  return '—'
}
function tipoInfo(actividad) {
  const tipo = tiposActividad.value.find((t) => t.id === actividad.tipo_actividad_id)
  const indice = tiposActividad.value.findIndex((t) => t.id === actividad.tipo_actividad_id)
  return { nombre: tipo?.nombre || '—', color: COLORES_TIPO[Math.max(0, indice) % COLORES_TIPO.length] }
}

onBeforeUnmount(limpiarVistasPrevias)

onMounted(async () => {
  await Promise.all([
    cargarTecnicos(),
    cargarEcas(),
    listarEstados().then((r) => (estados.value = r)),
    listarCatalogo('tipos-actividad', { todos: true }).then((r) => (tiposActividad.value = r)),
  ])
  await cargar()
})
</script>

<template>
  <section>
    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="clock" /></span>
      <div class="eca-page-header__texto">
        <h1>Actividades</h1>
        <p>Registros de todos los técnicos, con filtros y exportación.</p>
      </div>
      <button
        type="button"
        class="eca-page-header__accion"
        :class="{ 'eca-page-header__accion--girando': cargando }"
        :disabled="cargando"
        aria-label="Recargar"
        @click="cargar"
      >
        <AuthIcon name="sync" />
      </button>
    </div>

    <div class="eca-panel-fusionado">
      <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>

      <div class="eca-stats-grid">
        <div class="eca-stat-card eca-stat-card--morado">
          <span class="eca-stat-card__icono"><AuthIcon name="clock" /></span>
          <div><div class="eca-stat-card__valor">{{ total }}</div><div class="eca-stat-card__etiqueta">Total (filtro actual)</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--verde">
          <span class="eca-stat-card__icono"><AuthIcon name="map-pin" /></span>
          <div><div class="eca-stat-card__valor">{{ statsPagina.conGps }}</div><div class="eca-stat-card__etiqueta">Con GPS (en esta página)</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--ambar">
          <span class="eca-stat-card__icono"><AuthIcon name="alert" /></span>
          <div><div class="eca-stat-card__valor">{{ statsPagina.impreciso }}</div><div class="eca-stat-card__etiqueta">GPS impreciso (en esta página)</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--rojo">
          <span class="eca-stat-card__icono"><AuthIcon name="wifi-off" /></span>
          <div><div class="eca-stat-card__valor">{{ statsPagina.sinGps }}</div><div class="eca-stat-card__etiqueta">Sin GPS (en esta página)</div></div>
        </div>
      </div>

      <div class="actividades__filtros">
        <select v-model="tecnicoId" @change="aplicarFiltros">
          <option :value="null">Todos los técnicos</option>
          <option v-for="t in tecnicos" :key="t.uuid" :value="t.id">{{ t.nombre }} {{ t.apellido_paterno }}</option>
        </select>
        <select v-model="estadoId" @change="onCambioEstado">
          <option :value="null">Todos los estados</option>
          <option v-for="e in estados" :key="e.id" :value="e.id">{{ e.nombre }}</option>
        </select>
        <select v-model="municipioId" :disabled="!estadoId" @change="aplicarFiltros">
          <option :value="null">Todos los municipios</option>
          <option v-for="m in municipios" :key="m.id" :value="m.id">{{ m.nombre }}</option>
        </select>
        <select v-model="tipoActividadId" @change="aplicarFiltros">
          <option :value="null">Todos los tipos</option>
          <option v-for="t in tiposActividad" :key="t.id" :value="t.id">{{ t.nombre }}</option>
        </select>
        <select v-model="estadoGps" @change="aplicarFiltros">
          <option value="">Cualquier GPS</option>
          <option value="CON_GPS">Con GPS</option>
          <option value="GPS_IMPRECISO">GPS impreciso</option>
          <option value="SIN_GPS">Sin GPS</option>
        </select>
        <label class="actividades__fecha">
          Desde
          <input v-model="desde" type="date" @change="aplicarFiltros" />
        </label>
        <label class="actividades__fecha">
          Hasta
          <input v-model="hasta" type="date" @change="aplicarFiltros" />
        </label>
        <button type="button" class="eca-btn eca-btn-secundario" :disabled="exportando" @click="onExportar">
          {{ exportando ? 'Exportando…' : 'Exportar CSV' }}
        </button>
      </div>
    </div>

    <div class="eca-card">
      <p v-if="cargando" class="eca-ayuda">Cargando…</p>

      <div v-else-if="!actividades.length" class="eca-vacio">
        <AuthIcon name="clock" />
        <p>No hay actividades con estos filtros.</p>
      </div>

      <div v-else class="actividades__tabla-contenedor">
        <table class="eca-tabla actividades__tabla">
          <thead>
            <tr>
              <th>Técnico</th>
              <th>Foto</th>
              <th>Tipo</th>
              <th>Fecha</th>
              <th>ECA</th>
              <th>Descripción</th>
              <th>GPS</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in actividades" :key="a.uuid">
              <td>
                <div class="eca-tabla__usuario">
                  <span class="eca-avatar">{{ iniciales(tecnicoDe(a)) }}</span>
                  <span class="eca-tabla__usuario-texto">
                    <strong>{{ tecnicoDe(a) ? `${tecnicoDe(a).nombre} ${tecnicoDe(a).apellido_paterno}` : `Técnico #${a.usuario_id}` }}</strong>
                    <span v-if="tecnicoDe(a)">{{ tecnicoDe(a).correo }}</span>
                  </span>
                </div>
              </td>
              <td>
                <RouterLink :to="{ name: 'actividad-detalle', params: { uuid: a.uuid } }" class="actividades__foto-enlace">
                  <img
                    v-if="a.primera_evidencia_id && vistasPrevias[a.primera_evidencia_id]"
                    :src="vistasPrevias[a.primera_evidencia_id]"
                    alt="Evidencia"
                    class="actividades__foto"
                  />
                  <span v-else-if="a.primera_evidencia_id" class="actividades__foto actividades__foto--cargando">
                    <AuthIcon name="sync" class="actividades__foto-spinner" />
                  </span>
                  <span v-else class="actividades__foto actividades__foto--vacia">
                    <AuthIcon name="camera" />
                  </span>
                </RouterLink>
              </td>
              <td>
                <span class="eca-badge" :class="`eca-badge--${tipoInfo(a).color}`">{{ tipoInfo(a).nombre }}</span>
              </td>
              <td>
                <span class="actividades__fecha-badge">{{ new Date(a.fecha_hora).toLocaleDateString('es-MX') }}</span>
                <span class="actividades__hora-badge">{{ new Date(a.fecha_hora).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' }) }}</span>
              </td>
              <td class="actividades__eca">{{ ecaNombre(a) }}</td>
              <td class="actividades__descripcion">{{ a.descripcion }}</td>
              <td>
                <span class="eca-badge" :class="BADGE_GPS[a.estado_gps] || 'eca-badge--gris'">
                  <AuthIcon name="map-pin" /> {{ ETIQUETAS_GPS[a.estado_gps] || '—' }}
                </span>
              </td>
              <td>
                <div class="actividades__acciones">
                  <RouterLink
                    class="actividades__accion actividades__accion--ver"
                    :to="{ name: 'actividad-detalle', params: { uuid: a.uuid } }"
                    title="Ver detalle"
                  >
                    <AuthIcon name="search" />
                  </RouterLink>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total" class="eca-paginacion">
        <button type="button" :disabled="page <= 1" aria-label="Página anterior" @click="irAPagina(page - 1)">
          <AuthIcon name="chevron-left" />
        </button>
        <span>Página {{ page }} de {{ totalPaginas }} · {{ total }} resultado(s)</span>
        <button type="button" :disabled="page >= totalPaginas" aria-label="Página siguiente" @click="irAPagina(page + 1)">
          <AuthIcon name="chevron-right" />
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.actividades__filtros {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 1rem;
}
.actividades__filtros select,
.actividades__filtros input {
  padding: 0.5rem 0.7rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid var(--eca-surface-border);
  font-family: inherit;
}
.actividades__fecha {
  display: flex;
  flex-direction: column;
  font-size: 0.8rem;
  color: var(--eca-ink-soft);
  gap: 0.2rem;
}
/* ---- Tabla con scroll INTERNO (pedido explícito, mismo patrón que
   `.apple-table-container`/`.apple-table-wrapper` de admin-pwa): el
   contenedor tiene una altura acotada y es ÉL el que hace scroll —
   nunca la página completa — con el encabezado siempre visible arriba
   (`position: sticky`). ---- */
.actividades__tabla-contenedor {
  max-height: 60vh;
  overflow: auto;
  border-radius: var(--eca-r-md);
  border: 1px solid var(--eca-surface-border);
}
.actividades__tabla-contenedor::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
.actividades__tabla-contenedor::-webkit-scrollbar-track {
  background: transparent;
}
.actividades__tabla-contenedor::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 10px;
  border: 2px solid transparent;
  background-clip: content-box;
}
.actividades__tabla-contenedor::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.28);
  background-clip: content-box;
}
.actividades__tabla {
  min-width: 900px;
}
.actividades__tabla thead th {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--eca-surface);
  box-shadow: 0 1px 0 var(--eca-surface-border);
}
.actividades__tabla tbody tr {
  transition: background 0.15s ease;
}

.actividades__descripcion {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.actividades__eca {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.actividades__fecha-badge {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
}
.actividades__hora-badge {
  display: block;
  font-size: 0.75rem;
  color: var(--eca-ink-soft);
}

/* Miniatura de evidencia */
.actividades__foto-enlace {
  display: block;
  width: fit-content;
}
.actividades__foto {
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(139, 195, 74, 0.35);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), border-color 0.25s ease;
}
.actividades__foto-enlace:hover .actividades__foto {
  transform: scale(1.15);
  border-color: var(--eca-green-600);
}
.actividades__foto--vacia,
.actividades__foto--cargando {
  color: var(--eca-ink-faint, #9aa1af);
  background: var(--eca-surface);
  border-color: var(--eca-surface-border);
}
.actividades__foto--vacia svg,
.actividades__foto-spinner {
  width: 1.1rem;
  height: 1.1rem;
}
.actividades__foto-spinner {
  animation: eca-girar 0.9s linear infinite;
}

/* Acciones circulares — mismo lenguaje visual que las tarjetas del
   dashboard de Inicio (degradado + sombra + hover con escala). */
.actividades__acciones {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
}
.actividades__accion {
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
}
.actividades__accion svg {
  width: 0.95rem;
  height: 0.95rem;
}
.actividades__accion:hover {
  transform: scale(1.12);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.22);
}
.actividades__accion--ver {
  background: linear-gradient(135deg, var(--eca-purple-600), var(--eca-purple-500));
}

@media (max-width: 640px) {
  .actividades__tabla-contenedor {
    max-height: 70vh;
  }
}
</style>
