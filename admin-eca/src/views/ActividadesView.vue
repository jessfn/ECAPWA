<!-- admin-eca — pantalla "Actividades" (ECA-019). Rediseño pedido
     explícito: mismo lenguaje visual que `RegistrosView.vue` de
     admin-pwa — header con ícono, tarjetas de estadística, avatar +
     nombre real del técnico (el listado del backend solo trae
     `usuario_id`, se cruza con `GET /usuarios`), badges de estado GPS,
     nombre real de la ECA (se cruza con `GET /ecas`), y paginación real
     con los metadatos que el backend ya devuelve (`total/page/page_size`
     — a diferencia de Técnicos, aquí SÍ pagina el servidor). El listado
     admin NO trae fotos de evidencia (serían N+1 peticiones si se
     pidieran una por una); se ve el detalle completo con galería en
     `ActividadDetalleView.vue`, ya existente. -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { listarEstados, listarMunicipios } from '../services/geoService'
import { listarCatalogo } from '../services/catalogosService'
import { listarActividades, exportarCsv } from '../services/actividadesService'
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
  try {
    const respuesta = await listarActividades({ ...filtrosActuales(), page: page.value, pageSize })
    actividades.value = respuesta.resultados
    total.value = respuesta.total
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

      <div v-else class="eca-tabla-scroll">
        <table class="eca-tabla">
          <thead>
            <tr>
              <th>Técnico</th>
              <th>Fecha</th>
              <th>ECA</th>
              <th>Descripción</th>
              <th>GPS</th>
              <th></th>
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
                <span class="actividades__fecha-badge">{{ new Date(a.fecha_hora).toLocaleDateString('es-MX') }}</span>
                <span class="actividades__hora-badge">{{ new Date(a.fecha_hora).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' }) }}</span>
              </td>
              <td>{{ ecaNombre(a) }}</td>
              <td class="actividades__descripcion">{{ a.descripcion }}</td>
              <td>
                <span class="eca-badge" :class="BADGE_GPS[a.estado_gps] || 'eca-badge--gris'">
                  <AuthIcon name="map-pin" /> {{ ETIQUETAS_GPS[a.estado_gps] || '—' }}
                </span>
              </td>
              <td>
                <RouterLink class="actividades__ver" :to="{ name: 'actividad-detalle', params: { uuid: a.uuid } }">
                  <AuthIcon name="camera" /> Ver
                </RouterLink>
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
.eca-tabla-scroll {
  overflow-x: auto;
}
.actividades__descripcion {
  max-width: 260px;
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
.actividades__ver {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.3rem 0.65rem;
  border-radius: 999px;
  background: var(--eca-surface);
  color: var(--eca-purple-700);
  text-decoration: none;
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
}
.actividades__ver svg {
  width: 13px;
  height: 13px;
}
.actividades__ver:hover {
  background: #ede9fe;
}
</style>
