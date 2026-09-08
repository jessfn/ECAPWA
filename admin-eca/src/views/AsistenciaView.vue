<!-- admin-eca — pantalla "Asistencia" (nueva): entrada y salida de jornada
     de TODOS los técnicos (hora + ubicación de cada una). Reutiliza el
     modelo `Jornada` que ya existía (`inicio_en`/`fin_en` + GPS de cada
     una) — "asistencia" es exactamente eso, entrada = inicio de jornada,
     salida = cierre; no se creó ninguna tabla nueva.
     Mismo lenguaje visual que Actividades/Técnicos: header + panel de
     filtros fusionados, tabla a pantalla completa con scroll interno (sin
     scroll vertical de página). Al tocar un registro se abre un modal con
     un mapa Mapbox chico: entrada en azul, salida en rojo. -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { api } from '../services/api'
import { listarTodasJornadas } from '../services/jornadasService'
import AuthIcon from '../components/auth/AuthIcon.vue'

const cargando = ref(false)
const error = ref('')

const jornadas = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 30
const tecnicos = ref([])
const tecnicosPorId = computed(() => new Map(tecnicos.value.map((t) => [t.id, t])))

const ETIQUETAS_ESTADO = { ABIERTA: 'En curso', CERRADA: 'Completa', ANULADA: 'Anulada' }
const BADGE_ESTADO = { ABIERTA: 'eca-badge--ambar', CERRADA: 'eca-badge--verde', ANULADA: 'eca-badge--rojo' }

// ---- Filtros ----
const tecnicoId = ref(null)
const estado = ref('')
const desde = ref('')
const hasta = ref('')

// Buscador de técnico en tiempo real (mismo patrón que Actividades/Técnicos/Visor).
const busquedaTecnico = ref('')
const mostrarSugerencias = ref(false)
function normalizar(texto) {
  return (texto || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
}
const sugerenciasTecnico = computed(() => {
  const q = normalizar(busquedaTecnico.value.trim())
  if (!q) return []
  return tecnicos.value
    .filter((t) => {
      const nombre = normalizar(`${t.nombre} ${t.apellido_paterno} ${t.apellido_materno || ''}`)
      const curp = normalizar(t.curp || '')
      return nombre.includes(q) || curp.includes(q)
    })
    .slice(0, 8)
})
function iniciales(u) {
  const n = (u?.nombre || '').trim()
  const a = (u?.apellido_paterno || '').trim()
  if (n && a) return (n[0] + a[0]).toUpperCase()
  return '??'
}
function seleccionarTecnico(t) {
  tecnicoId.value = t.id
  busquedaTecnico.value = `${t.nombre} ${t.apellido_paterno}`
  mostrarSugerencias.value = false
  aplicarFiltros()
}
function limpiarBusquedaTecnico() {
  tecnicoId.value = null
  busquedaTecnico.value = ''
  mostrarSugerencias.value = false
  aplicarFiltros()
}

const totalPaginas = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const stats = computed(() => ({
  total: total.value,
  tecnicos: new Set(jornadas.value.map((j) => j.usuario_id)).size,
  enCurso: jornadas.value.filter((j) => j.estado === 'ABIERTA').length,
  completas: jornadas.value.filter((j) => j.estado === 'CERRADA').length,
}))

async function cargarTecnicos() {
  try {
    const { data } = await api.get('/usuarios/tecnicos-basico')
    tecnicos.value = data
  } catch {
    tecnicos.value = []
  }
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const respuesta = await listarTodasJornadas({
      tecnicoId: tecnicoId.value || undefined,
      estado: estado.value || undefined,
      desde: desde.value || undefined,
      hasta: hasta.value || undefined,
      page: page.value,
      pageSize,
    })
    jornadas.value = respuesta.resultados
    total.value = respuesta.total
  } catch {
    error.value = 'No se pudo cargar la asistencia.'
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
async function recargar() {
  await Promise.all([cargarTecnicos(), cargar()])
}

function tecnicoDe(j) {
  return tecnicosPorId.value.get(j.usuario_id) || null
}
function formatearHora(iso) {
  if (!iso) return null
  return new Date(iso).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
}
function formatearFecha(fecha) {
  // `fecha` ya viene como YYYY-MM-DD (columna `Date` del backend) — se
  // arma la fecha en local para no correrse un día por huso horario.
  const [anio, mes, dia] = fecha.split('-').map(Number)
  return new Date(anio, mes - 1, dia).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })
}
function duracion(j) {
  if (!j.fin_en) return j.estado === 'ABIERTA' ? 'En curso' : '—'
  const ms = new Date(j.fin_en) - new Date(j.inicio_en)
  const horas = Math.floor(ms / 3_600_000)
  const minutos = Math.round((ms % 3_600_000) / 60_000)
  return `${horas}h ${minutos}m`
}

// ---- Modal de detalle: entrada (azul) / salida (rojo) + mapa Mapbox ----
const modalAbierto = ref(false)
const jornadaSeleccionada = ref(null)
const mapaModalContenedor = ref(null)
const mapaModalError = ref('')
let mapaModal = null
let marcadoresModal = []

function limpiarMapaModal() {
  marcadoresModal.forEach((m) => m.remove())
  marcadoresModal = []
  mapaModal?.remove()
  mapaModal = null
}

async function abrirModal(j) {
  jornadaSeleccionada.value = j
  modalAbierto.value = true
  mapaModalError.value = ''
  await nextTick()
  iniciarMapaModal(j)
}

function cerrarModal() {
  modalAbierto.value = false
  jornadaSeleccionada.value = null
  limpiarMapaModal()
}

function iniciarMapaModal(j) {
  limpiarMapaModal()
  if (!mapaModalContenedor.value) return

  const puntos = []
  if (j.latitud_inicio != null && j.longitud_inicio != null) {
    puntos.push({ tipo: 'entrada', lng: j.longitud_inicio, lat: j.latitud_inicio })
  }
  if (j.latitud_fin != null && j.longitud_fin != null) {
    puntos.push({ tipo: 'salida', lng: j.longitud_fin, lat: j.latitud_fin })
  }
  if (!puntos.length) return // sin coordenadas: el template muestra el aviso, sin mapa

  if (!window.mapboxgl) {
    mapaModalError.value = 'No se pudo cargar Mapbox (revisa tu conexión).'
    return
  }
  const token = import.meta.env.VITE_MAPBOX_TOKEN
  if (!token) {
    mapaModalError.value = 'Falta configurar VITE_MAPBOX_TOKEN.'
    return
  }
  window.mapboxgl.accessToken = token
  mapaModal = new window.mapboxgl.Map({
    container: mapaModalContenedor.value,
    style: 'mapbox://styles/mapbox/satellite-streets-v12',
    center: [puntos[0].lng, puntos[0].lat],
    zoom: 14,
  })
  mapaModal.addControl(new window.mapboxgl.NavigationControl(), 'top-right')

  mapaModal.on('load', () => {
    puntos.forEach((p) => {
      const color = p.tipo === 'entrada' ? '#2563eb' : '#dc2626'
      const marcador = new window.mapboxgl.Marker({ color }).setLngLat([p.lng, p.lat]).addTo(mapaModal)
      marcadoresModal.push(marcador)
    })
    if (puntos.length === 2) {
      const bounds = new window.mapboxgl.LngLatBounds()
      puntos.forEach((p) => bounds.extend([p.lng, p.lat]))
      mapaModal.fitBounds(bounds, { padding: 60, maxZoom: 16, duration: 0 })
    }
  })
  mapaModal.on('error', () => {
    mapaModalError.value = 'No se pudo cargar el mapa.'
  })
}

// ---- Modal de detalles: información completa en dos columnas (entrada/salida) ----
const detalleAbierto = ref(false)
const jornadaDetalle = ref(null)

function abrirDetalle(j) {
  jornadaDetalle.value = j
  detalleAbierto.value = true
}
function cerrarDetalle() {
  detalleAbierto.value = false
  jornadaDetalle.value = null
}
function verMapaDesdeDetalle() {
  const j = jornadaDetalle.value
  cerrarDetalle()
  abrirModal(j)
}
function formatearFechaHora(iso) {
  if (!iso) return null
  return new Date(iso).toLocaleString('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
function coordenadasDe(lat, lng) {
  if (lat == null || lng == null) return null
  return `${lat.toFixed(6)}, ${lng.toFixed(6)}`
}
function precisionGpsDe(estado, metros) {
  if (!estado) return null
  const base = estado === 'CON_GPS' ? 'Ubicación precisa' : 'Ubicación aproximada'
  return metros != null ? `${base} (±${Math.round(metros)} m)` : base
}

function onTeclaEscape(evento) {
  if (evento.key !== 'Escape') return
  if (detalleAbierto.value) cerrarDetalle()
  else if (modalAbierto.value) cerrarModal()
}

onMounted(async () => {
  window.addEventListener('keydown', onTeclaEscape)
  await Promise.all([cargarTecnicos(), cargar()])
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onTeclaEscape)
  limpiarMapaModal()
})
</script>

<template>
  <section class="asistencia-vista">
    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="check-circle" /></span>
      <div class="eca-page-header__texto">
        <h1>Asistencia</h1>
        <p>Entrada y salida de los técnicos, con hora y ubicación.</p>
      </div>
      <button
        type="button"
        class="eca-page-header__accion"
        :class="{ 'eca-page-header__accion--girando': cargando }"
        :disabled="cargando"
        aria-label="Recargar"
        @click="recargar"
      >
        <AuthIcon name="sync" />
      </button>
    </div>

    <div class="eca-panel-fusionado">
      <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>

      <div class="asistencia__stats">
        <div class="eca-stat-card eca-stat-card--morado">
          <span class="eca-stat-card__icono"><AuthIcon name="check-circle" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.total }}</div><div class="eca-stat-card__etiqueta">Registros (filtro actual)</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--azul">
          <span class="eca-stat-card__icono"><AuthIcon name="user" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.tecnicos }}</div><div class="eca-stat-card__etiqueta">Técnicos (en esta página)</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--ambar">
          <span class="eca-stat-card__icono"><AuthIcon name="alert" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.enCurso }}</div><div class="eca-stat-card__etiqueta">En curso (sin salida)</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--verde">
          <span class="eca-stat-card__icono"><AuthIcon name="check-circle" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.completas }}</div><div class="eca-stat-card__etiqueta">Completas (en esta página)</div></div>
        </div>
      </div>

      <div class="asistencia__filtros">
        <div class="asistencia__buscador">
          <span class="asistencia__buscador-icono"><AuthIcon name="search" /></span>
          <input
            v-model="busquedaTecnico"
            type="text"
            placeholder="Buscar técnico por nombre o CURP…"
            @focus="mostrarSugerencias = true"
            @blur="() => setTimeout(() => (mostrarSugerencias = false), 150)"
          />
          <button
            v-if="busquedaTecnico"
            type="button"
            class="asistencia__buscador-limpiar"
            aria-label="Limpiar búsqueda de técnico"
            @mousedown.prevent="limpiarBusquedaTecnico"
          >
            <AuthIcon name="close" />
          </button>

          <Transition name="asistencia-sugerencias">
            <div v-if="mostrarSugerencias && busquedaTecnico && sugerenciasTecnico.length" class="asistencia__sugerencias">
              <button
                v-for="t in sugerenciasTecnico"
                :key="t.id"
                type="button"
                class="asistencia__sugerencia"
                @mousedown.prevent="seleccionarTecnico(t)"
              >
                <span class="asistencia__sugerencia-avatar">{{ iniciales(t) }}</span>
                <span class="asistencia__sugerencia-texto">
                  <strong>{{ t.nombre }} {{ t.apellido_paterno }} {{ t.apellido_materno || '' }}</strong>
                  <small v-if="t.curp">{{ t.curp }}</small>
                </span>
              </button>
            </div>
          </Transition>
        </div>

        <div class="asistencia__selects">
          <select v-model="estado" class="asistencia__control" @change="aplicarFiltros">
            <option value="">Todos los estados</option>
            <option value="ABIERTA">En curso</option>
            <option value="CERRADA">Completa</option>
            <option value="ANULADA">Anulada</option>
          </select>
          <div class="asistencia__fecha asistencia__control">
            <span class="asistencia__fecha-etiqueta">Desde</span>
            <input v-model="desde" type="date" @change="aplicarFiltros" />
          </div>
          <div class="asistencia__fecha asistencia__control">
            <span class="asistencia__fecha-etiqueta">Hasta</span>
            <input v-model="hasta" type="date" @change="aplicarFiltros" />
          </div>
        </div>
      </div>
    </div>

    <div class="eca-card asistencia__cuerpo">
      <p v-if="cargando" class="eca-ayuda">Cargando…</p>

      <div v-else-if="!jornadas.length" class="eca-vacio">
        <AuthIcon name="check-circle" />
        <p>No hay registros de asistencia con estos filtros.</p>
      </div>

      <div v-else class="asistencia__tabla-contenedor">
        <table class="eca-tabla asistencia__tabla">
          <thead>
            <tr>
              <th>Técnico</th>
              <th>Fecha</th>
              <th>Entrada</th>
              <th>Salida</th>
              <th>Duración</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="j in jornadas" :key="j.uuid">
              <td>
                <div class="eca-tabla__usuario">
                  <span class="eca-avatar">{{ iniciales(tecnicoDe(j)) }}</span>
                  <span class="eca-tabla__usuario-texto">
                    <strong>{{ tecnicoDe(j) ? `${tecnicoDe(j).nombre} ${tecnicoDe(j).apellido_paterno}` : `Técnico #${j.usuario_id}` }}</strong>
                  </span>
                </div>
              </td>
              <td>{{ formatearFecha(j.fecha) }}</td>
              <td>
                <span class="asistencia__badge asistencia__badge--entrada">
                  <span class="asistencia__punto asistencia__punto--azul"></span>
                  {{ formatearHora(j.inicio_en) }}
                </span>
              </td>
              <td>
                <span v-if="j.fin_en" class="asistencia__badge asistencia__badge--salida">
                  <span class="asistencia__punto asistencia__punto--rojo"></span>
                  {{ formatearHora(j.fin_en) }}
                </span>
                <span v-else class="asistencia__sin-salida">Sin registrar</span>
              </td>
              <td>{{ duracion(j) }}</td>
              <td>
                <span class="eca-badge" :class="BADGE_ESTADO[j.estado]">{{ ETIQUETAS_ESTADO[j.estado] || j.estado }}</span>
              </td>
              <td>
                <div class="asistencia__acciones">
                  <button type="button" class="asistencia__accion asistencia__accion--detalle" title="Ver detalles" @click="abrirDetalle(j)">
                    <AuthIcon name="clipboard" />
                  </button>
                  <button type="button" class="asistencia__accion" title="Ver ubicación" @click="abrirModal(j)">
                    <AuthIcon name="map-pin" />
                  </button>
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
        <span>Página {{ page }} de {{ totalPaginas }} · {{ total }} registro(s)</span>
        <button type="button" :disabled="page >= totalPaginas" aria-label="Página siguiente" @click="irAPagina(page + 1)">
          <AuthIcon name="chevron-right" />
        </button>
      </div>
    </div>

    <!-- ============ Modal: detalle de entrada/salida con mapa ============ -->
    <Teleport to="body">
      <Transition name="asistencia-modal-fondo">
        <div v-if="modalAbierto" class="asistencia-modal__fondo" @click.self="cerrarModal">
          <Transition name="asistencia-modal-tarjeta" appear>
            <div class="asistencia-modal" role="dialog" aria-modal="true">
              <button type="button" class="asistencia-modal__cerrar" aria-label="Cerrar" @click="cerrarModal">
                <AuthIcon name="close" />
              </button>

              <div class="asistencia-modal__cabecera">
                <span class="asistencia-modal__avatar">{{ iniciales(tecnicoDe(jornadaSeleccionada)) }}</span>
                <div class="asistencia-modal__cabecera-texto">
                  <strong>
                    {{
                      tecnicoDe(jornadaSeleccionada)
                        ? `${tecnicoDe(jornadaSeleccionada).nombre} ${tecnicoDe(jornadaSeleccionada).apellido_paterno}`
                        : `Técnico #${jornadaSeleccionada?.usuario_id}`
                    }}
                  </strong>
                  <span>{{ jornadaSeleccionada ? formatearFecha(jornadaSeleccionada.fecha) : '' }}</span>
                </div>
                <span
                  v-if="jornadaSeleccionada"
                  class="eca-badge"
                  :class="BADGE_ESTADO[jornadaSeleccionada.estado]"
                >
                  {{ ETIQUETAS_ESTADO[jornadaSeleccionada.estado] }}
                </span>
              </div>

              <div class="asistencia-modal__cuerpo">
                <div class="asistencia-modal__filas">
                  <div class="asistencia-modal__fila asistencia-modal__fila--entrada">
                    <span class="asistencia-modal__fila-punto"></span>
                    <div class="asistencia-modal__fila-texto">
                      <strong>Entrada</strong>
                      <span>{{ formatearHora(jornadaSeleccionada?.inicio_en) || '—' }}</span>
                      <small v-if="jornadaSeleccionada?.estado_gps_inicio">
                        GPS: {{ jornadaSeleccionada.estado_gps_inicio === 'CON_GPS' ? 'preciso' : 'impreciso' }}
                        <template v-if="jornadaSeleccionada.precision_gps_inicio_m">
                          (±{{ Math.round(jornadaSeleccionada.precision_gps_inicio_m) }} m)
                        </template>
                      </small>
                      <small v-else class="asistencia-modal__sin-gps">Sin ubicación registrada</small>
                    </div>
                  </div>
                  <div class="asistencia-modal__fila asistencia-modal__fila--salida">
                    <span class="asistencia-modal__fila-punto"></span>
                    <div class="asistencia-modal__fila-texto">
                      <strong>Salida</strong>
                      <span v-if="jornadaSeleccionada?.fin_en">{{ formatearHora(jornadaSeleccionada.fin_en) }}</span>
                      <span v-else class="asistencia-modal__pendiente">Aún no registrada</span>
                      <small v-if="jornadaSeleccionada?.estado_gps_fin">
                        GPS: {{ jornadaSeleccionada.estado_gps_fin === 'CON_GPS' ? 'preciso' : 'impreciso' }}
                        <template v-if="jornadaSeleccionada.precision_gps_fin_m">
                          (±{{ Math.round(jornadaSeleccionada.precision_gps_fin_m) }} m)
                        </template>
                      </small>
                    </div>
                  </div>
                </div>

                <p v-if="mapaModalError" class="eca-alerta-error" role="alert">{{ mapaModalError }}</p>
                <div
                  v-if="jornadaSeleccionada && (jornadaSeleccionada.latitud_inicio != null || jornadaSeleccionada.latitud_fin != null)"
                  ref="mapaModalContenedor"
                  class="asistencia-modal__mapa"
                ></div>
                <p v-else class="asistencia-modal__sin-mapa">
                  <AuthIcon name="map-pin" /> No hay ubicación registrada para este día.
                </p>

                <div v-if="jornadaSeleccionada?.nota || jornadaSeleccionada?.nota_fin" class="asistencia-modal__notas">
                  <p v-if="jornadaSeleccionada.nota"><strong>Nota de entrada:</strong> {{ jornadaSeleccionada.nota }}</p>
                  <p v-if="jornadaSeleccionada.nota_fin"><strong>Nota de salida:</strong> {{ jornadaSeleccionada.nota_fin }}</p>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>

    <!-- ============ Modal: detalles completos en dos columnas ============ -->
    <Teleport to="body">
      <Transition name="asistencia-modal-fondo">
        <div v-if="detalleAbierto" class="asistencia-modal__fondo" @click.self="cerrarDetalle">
          <Transition name="asistencia-modal-tarjeta" appear>
            <div v-if="jornadaDetalle" class="asistencia-detalle" role="dialog" aria-modal="true">
              <button type="button" class="asistencia-modal__cerrar" aria-label="Cerrar" @click="cerrarDetalle">
                <AuthIcon name="close" />
              </button>

              <div class="asistencia-detalle__cabecera">
                <span class="asistencia-modal__avatar">{{ iniciales(tecnicoDe(jornadaDetalle)) }}</span>
                <div class="asistencia-modal__cabecera-texto">
                  <strong>
                    {{
                      tecnicoDe(jornadaDetalle)
                        ? `${tecnicoDe(jornadaDetalle).nombre} ${tecnicoDe(jornadaDetalle).apellido_paterno}`
                        : `Técnico #${jornadaDetalle.usuario_id}`
                    }}
                  </strong>
                  <span>{{ formatearFecha(jornadaDetalle.fecha) }} · {{ duracion(jornadaDetalle) }}</span>
                </div>
                <span class="eca-badge" :class="BADGE_ESTADO[jornadaDetalle.estado]">
                  {{ ETIQUETAS_ESTADO[jornadaDetalle.estado] }}
                </span>
              </div>

              <div class="asistencia-detalle__columnas">
                <!-- Columna Entrada -->
                <div class="asistencia-detalle__col asistencia-detalle__col--entrada">
                  <div class="asistencia-detalle__col-cabecera">
                    <span class="asistencia-detalle__col-icono"><AuthIcon name="arrow-right" /></span>
                    <strong>Entrada</strong>
                  </div>

                  <template v-if="jornadaDetalle.inicio_en">
                    <div class="asistencia-detalle__hora">{{ formatearHora(jornadaDetalle.inicio_en) }}</div>
                    <div class="asistencia-detalle__dato">
                      <span class="asistencia-detalle__dato-etiqueta">Fecha y hora</span>
                      <span class="asistencia-detalle__dato-valor">{{ formatearFechaHora(jornadaDetalle.inicio_en) }}</span>
                    </div>
                    <div class="asistencia-detalle__dato">
                      <span class="asistencia-detalle__dato-etiqueta">Ubicación GPS</span>
                      <span
                        v-if="precisionGpsDe(jornadaDetalle.estado_gps_inicio, jornadaDetalle.precision_gps_inicio_m)"
                        class="asistencia-detalle__dato-valor"
                      >
                        {{ precisionGpsDe(jornadaDetalle.estado_gps_inicio, jornadaDetalle.precision_gps_inicio_m) }}
                      </span>
                      <span v-else class="asistencia-detalle__vacio">Sin ubicación registrada</span>
                    </div>
                    <div v-if="coordenadasDe(jornadaDetalle.latitud_inicio, jornadaDetalle.longitud_inicio)" class="asistencia-detalle__dato">
                      <span class="asistencia-detalle__dato-etiqueta">Coordenadas</span>
                      <span class="asistencia-detalle__dato-valor asistencia-detalle__coordenadas">
                        {{ coordenadasDe(jornadaDetalle.latitud_inicio, jornadaDetalle.longitud_inicio) }}
                      </span>
                    </div>
                    <div class="asistencia-detalle__dato">
                      <span class="asistencia-detalle__dato-etiqueta">Nota</span>
                      <span v-if="jornadaDetalle.nota" class="asistencia-detalle__dato-valor">{{ jornadaDetalle.nota }}</span>
                      <span v-else class="asistencia-detalle__vacio">Aún no hay un mensaje</span>
                    </div>
                  </template>
                  <div v-else class="asistencia-detalle__pendiente">
                    <AuthIcon name="clock" />
                    <p>Aún no hay un mensaje</p>
                  </div>
                </div>

                <!-- Columna Salida -->
                <div class="asistencia-detalle__col asistencia-detalle__col--salida">
                  <div class="asistencia-detalle__col-cabecera">
                    <span class="asistencia-detalle__col-icono"><AuthIcon name="arrow-left" /></span>
                    <strong>Salida</strong>
                  </div>

                  <template v-if="jornadaDetalle.fin_en">
                    <div class="asistencia-detalle__hora">{{ formatearHora(jornadaDetalle.fin_en) }}</div>
                    <div class="asistencia-detalle__dato">
                      <span class="asistencia-detalle__dato-etiqueta">Fecha y hora</span>
                      <span class="asistencia-detalle__dato-valor">{{ formatearFechaHora(jornadaDetalle.fin_en) }}</span>
                    </div>
                    <div class="asistencia-detalle__dato">
                      <span class="asistencia-detalle__dato-etiqueta">Ubicación GPS</span>
                      <span
                        v-if="precisionGpsDe(jornadaDetalle.estado_gps_fin, jornadaDetalle.precision_gps_fin_m)"
                        class="asistencia-detalle__dato-valor"
                      >
                        {{ precisionGpsDe(jornadaDetalle.estado_gps_fin, jornadaDetalle.precision_gps_fin_m) }}
                      </span>
                      <span v-else class="asistencia-detalle__vacio">Sin ubicación registrada</span>
                    </div>
                    <div v-if="coordenadasDe(jornadaDetalle.latitud_fin, jornadaDetalle.longitud_fin)" class="asistencia-detalle__dato">
                      <span class="asistencia-detalle__dato-etiqueta">Coordenadas</span>
                      <span class="asistencia-detalle__dato-valor asistencia-detalle__coordenadas">
                        {{ coordenadasDe(jornadaDetalle.latitud_fin, jornadaDetalle.longitud_fin) }}
                      </span>
                    </div>
                    <div class="asistencia-detalle__dato">
                      <span class="asistencia-detalle__dato-etiqueta">Nota</span>
                      <span v-if="jornadaDetalle.nota_fin" class="asistencia-detalle__dato-valor">{{ jornadaDetalle.nota_fin }}</span>
                      <span v-else class="asistencia-detalle__vacio">Aún no hay un mensaje</span>
                    </div>
                  </template>
                  <div v-else class="asistencia-detalle__pendiente">
                    <AuthIcon name="clock" />
                    <p>Aún no hay un mensaje</p>
                    <small>La salida todavía no se ha registrado.</small>
                  </div>
                </div>
              </div>

              <button type="button" class="asistencia-detalle__ver-mapa" @click="verMapaDesdeDetalle">
                <AuthIcon name="map-pin" /> Ver ubicación en el mapa
              </button>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped>
/* Layout de alto completo — mismo patrón que Actividades/Técnicos. */
.asistencia-vista {
  height: calc(100dvh - 1rem);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.asistencia-vista > .eca-page-header,
.asistencia-vista > .eca-panel-fusionado {
  flex-shrink: 0;
}
.asistencia-vista > .asistencia__cuerpo {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
  padding: 0.75rem 0.9rem;
  overflow: hidden;
}

/* Stats */
.asistencia__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.55rem;
  margin-bottom: 0.65rem;
}
.asistencia__stats .eca-stat-card {
  min-width: 0;
  padding: 0.45rem 0.65rem;
  gap: 0.5rem;
}
.asistencia__stats .eca-stat-card :deep(.eca-stat-card__icono) {
  width: 1.7rem;
  height: 1.7rem;
}
.asistencia__stats .eca-stat-card :deep(.eca-stat-card__icono svg) {
  width: 0.85rem;
  height: 0.85rem;
}
.asistencia__stats .eca-stat-card :deep(.eca-stat-card__valor) {
  font-size: 0.98rem;
}
.asistencia__stats .eca-stat-card :deep(.eca-stat-card__etiqueta) {
  font-size: 0.66rem;
}
@media (max-width: 820px) {
  .asistencia__stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 460px) {
  .asistencia__stats {
    grid-template-columns: 1fr;
  }
}

/* Filtros — mismo lenguaje que Actividades/Visor. */
.asistencia__filtros {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.asistencia__buscador {
  position: relative;
  width: 100%;
}
.asistencia__buscador-icono {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--eca-ink-soft);
  display: flex;
  pointer-events: none;
}
.asistencia__buscador-icono svg {
  width: 0.9rem;
  height: 0.9rem;
}
.asistencia__buscador input {
  width: 100%;
  padding: 0.55rem 2.4rem;
  border-radius: 999px;
  border: 1.5px solid #cfe3d5;
  background: #fff;
  font-family: inherit;
  font-size: 0.88rem;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.asistencia__buscador input:focus {
  outline: none;
  border-color: var(--eca-green-500);
  box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.14);
}
.asistencia__buscador-limpiar {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 50%;
  border: none;
  background: var(--eca-surface-border);
  color: var(--eca-ink-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease;
}
.asistencia__buscador-limpiar:hover {
  background: #e2e2e2;
  transform: translateY(-50%) scale(1.08);
}
.asistencia__buscador-limpiar svg {
  width: 0.7rem;
  height: 0.7rem;
}
.asistencia__sugerencias {
  position: absolute;
  z-index: 20;
  top: calc(100% + 0.4rem);
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid var(--eca-surface-border);
  border-radius: var(--eca-r-md);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.14);
  overflow: hidden;
  max-height: 18rem;
  overflow-y: auto;
}
.asistencia-sugerencias-enter-active,
.asistencia-sugerencias-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.asistencia-sugerencias-enter-from,
.asistencia-sugerencias-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
.asistencia__sugerencia {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.55rem 0.85rem;
  border: none;
  background: none;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease;
}
.asistencia__sugerencia:hover {
  background: var(--eca-surface);
}
.asistencia__sugerencia + .asistencia__sugerencia {
  border-top: 1px solid var(--eca-surface-border);
}
.asistencia__sugerencia-avatar {
  flex-shrink: 0;
  width: 1.9rem;
  height: 1.9rem;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--eca-green-500), var(--eca-green-700));
  color: #fff;
  font-size: 0.7rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}
.asistencia__sugerencia-texto {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}
.asistencia__sugerencia-texto strong {
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.asistencia__sugerencia-texto small {
  font-size: 0.72rem;
  color: var(--eca-ink-soft);
}

.asistencia__selects {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 0.5rem;
}
.asistencia__control {
  flex: 1 1 0;
  min-width: 8.5rem;
  height: 2.4rem;
  box-sizing: border-box;
}
select.asistencia__control {
  padding: 0 0.7rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid #cfe3d5;
  background: #fff;
  font-family: inherit;
  font-size: 0.82rem;
  color: var(--eca-ink);
  cursor: pointer;
}
.asistencia__fecha {
  position: relative;
  display: flex;
  align-items: flex-end;
  border-radius: var(--eca-r-sm);
  border: 1px solid #cfe3d5;
  background: #fff;
}
.asistencia__fecha:focus-within {
  border-color: var(--eca-green-500);
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.12);
}
.asistencia__fecha-etiqueta {
  position: absolute;
  top: 0.28rem;
  left: 0.7rem;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--eca-ink-soft);
  pointer-events: none;
}
.asistencia__fecha input {
  width: 100%;
  height: 100%;
  border: none;
  background: none;
  padding: 0.75rem 0.7rem 0.25rem;
  font-family: inherit;
  font-size: 0.8rem;
  color: var(--eca-ink);
  box-sizing: border-box;
}
.asistencia__fecha input:focus {
  outline: none;
}
@media (max-width: 720px) {
  .asistencia__control {
    flex: 1 1 calc(50% - 0.25rem);
  }
}
@media (max-width: 460px) {
  .asistencia__control {
    flex: 1 1 100%;
  }
}

/* Tabla */
.asistencia__tabla-contenedor {
  flex: 1;
  min-height: 0;
  overflow: auto;
  border-radius: var(--eca-r-md);
  border: 1px solid var(--eca-surface-border);
}
.asistencia__tabla {
  min-width: 760px;
}
.asistencia__tabla thead th {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--eca-surface);
  box-shadow: 0 1px 0 var(--eca-surface-border);
}
.asistencia__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.82rem;
  font-weight: 700;
}
.asistencia__punto {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  flex-shrink: 0;
}
.asistencia__punto--azul {
  background: #2563eb;
}
.asistencia__punto--rojo {
  background: #dc2626;
}
.asistencia__sin-salida {
  font-size: 0.8rem;
  color: var(--eca-ink-faint, #9aa1af);
  font-style: italic;
}
.asistencia__acciones {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.asistencia__accion {
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, var(--eca-purple-600), var(--eca-purple-500));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.asistencia__accion:hover {
  transform: scale(1.1);
}
.asistencia__accion svg {
  width: 0.95rem;
  height: 0.95rem;
}
.asistencia__accion--detalle {
  background: linear-gradient(135deg, #2f7a33, #14501c);
}

/* ---- Modal de detalles: dos columnas entrada/salida ---- */
.asistencia-detalle {
  position: relative;
  width: 100%;
  max-width: 720px;
  max-height: 90vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.35);
}
.asistencia-detalle__cabecera {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 3rem 1.25rem 1.5rem;
  background: linear-gradient(135deg, #2f7a33 0%, #256a2a 55%, #14501c 100%);
  color: #fff;
  border-radius: 24px 24px 0 0;
}
.asistencia-detalle__columnas {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}
.asistencia-detalle__col {
  padding: 1.25rem 1.35rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  animation: asistencia-detalle-entra 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.asistencia-detalle__col--entrada {
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.07), transparent 55%);
  border-right: 1px solid var(--eca-surface-border);
  animation-delay: 0.02s;
}
.asistencia-detalle__col--salida {
  background: linear-gradient(180deg, rgba(220, 38, 38, 0.07), transparent 55%);
  animation-delay: 0.09s;
}
@keyframes asistencia-detalle-entra {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.asistencia-detalle__col-cabecera {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-bottom: 0.6rem;
  border-bottom: 2px solid var(--eca-surface-border);
}
.asistencia-detalle__col-cabecera strong {
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.asistencia-detalle__col-icono {
  width: 1.9rem;
  height: 1.9rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.asistencia-detalle__col-icono svg {
  width: 0.85rem;
  height: 0.85rem;
}
.asistencia-detalle__col--entrada .asistencia-detalle__col-icono {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  box-shadow: 0 3px 10px rgba(37, 99, 235, 0.35);
}
.asistencia-detalle__col--entrada .asistencia-detalle__col-cabecera strong {
  color: #1d4ed8;
}
.asistencia-detalle__col--salida .asistencia-detalle__col-icono {
  background: linear-gradient(135deg, #f87171, #b91c1c);
  box-shadow: 0 3px 10px rgba(220, 38, 38, 0.35);
}
.asistencia-detalle__col--salida .asistencia-detalle__col-cabecera strong {
  color: #b91c1c;
}
.asistencia-detalle__hora {
  font-size: 1.7rem;
  font-weight: 800;
  color: var(--eca-ink);
  line-height: 1.1;
}
.asistencia-detalle__dato {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px dashed var(--eca-surface-border);
}
.asistencia-detalle__dato:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.asistencia-detalle__dato-etiqueta {
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--eca-ink-soft);
}
.asistencia-detalle__dato-valor {
  font-size: 0.86rem;
  color: var(--eca-ink);
  font-weight: 600;
  word-break: break-word;
}
.asistencia-detalle__coordenadas {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--eca-ink-soft);
}
.asistencia-detalle__vacio {
  font-size: 0.82rem;
  font-style: italic;
  color: var(--eca-ink-faint, #9aa1af);
}
.asistencia-detalle__pendiente {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 1.5rem 0.5rem;
  color: var(--eca-ink-faint, #9aa1af);
  text-align: center;
}
.asistencia-detalle__pendiente svg {
  width: 1.6rem;
  height: 1.6rem;
  opacity: 0.6;
  animation: asistencia-detalle-pulso 1.8s ease-in-out infinite;
}
@keyframes asistencia-detalle-pulso {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(1);
  }
  50% {
    opacity: 0.75;
    transform: scale(1.12);
  }
}
.asistencia-detalle__pendiente p {
  margin: 0;
  font-weight: 700;
  font-style: italic;
  font-size: 0.88rem;
}
.asistencia-detalle__pendiente small {
  font-size: 0.74rem;
}
.asistencia-detalle__ver-mapa {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: calc(100% - 3rem);
  margin: 0 1.5rem 1.5rem;
  padding: 0.75rem 1rem;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--eca-purple-600), var(--eca-purple-500));
  color: #fff;
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(118, 75, 162, 0.3);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
}
.asistencia-detalle__ver-mapa:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 22px rgba(118, 75, 162, 0.4);
}
.asistencia-detalle__ver-mapa svg {
  width: 0.85rem;
  height: 0.85rem;
}
@media (max-width: 640px) {
  .asistencia-detalle {
    max-width: 100%;
    max-height: 92vh;
    border-radius: 22px 22px 0 0;
  }
  .asistencia-detalle__cabecera {
    border-radius: 22px 22px 0 0;
  }
  .asistencia-detalle__columnas {
    grid-template-columns: 1fr;
  }
  .asistencia-detalle__col--entrada {
    border-right: none;
    border-bottom: 1px solid var(--eca-surface-border);
  }
}

/* ---- Modal de detalle ---- */
.asistencia-modal__fondo {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.25rem;
  background: rgba(20, 24, 20, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
.asistencia-modal-fondo-enter-active,
.asistencia-modal-fondo-leave-active {
  transition: opacity 0.2s ease;
}
.asistencia-modal-fondo-enter-from,
.asistencia-modal-fondo-leave-to {
  opacity: 0;
}
.asistencia-modal {
  position: relative;
  width: 100%;
  max-width: 520px;
  max-height: 88vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.35);
}
.asistencia-modal-tarjeta-enter-active {
  transition: opacity 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.asistencia-modal-tarjeta-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.asistencia-modal-tarjeta-enter-from {
  opacity: 0;
  transform: scale(0.94) translateY(14px);
}
.asistencia-modal-tarjeta-leave-to {
  opacity: 0;
  transform: scale(0.97) translateY(8px);
}
.asistencia-modal__cerrar {
  position: absolute;
  top: 0.85rem;
  right: 0.85rem;
  z-index: 2;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.85);
  color: var(--eca-ink);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.2s ease;
}
.asistencia-modal__cerrar:hover {
  transform: rotate(90deg) scale(1.08);
  background: #fff;
}
.asistencia-modal__cerrar svg {
  width: 0.9rem;
  height: 0.9rem;
}
.asistencia-modal__cabecera {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 3rem 1.25rem 1.5rem;
  background: linear-gradient(135deg, #2f7a33 0%, #256a2a 55%, #14501c 100%);
  color: #fff;
  border-radius: 24px 24px 0 0;
}
.asistencia-modal__avatar {
  flex-shrink: 0;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.18);
  border: 1.5px solid rgba(255, 255, 255, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  font-weight: 800;
}
.asistencia-modal__cabecera-texto {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.asistencia-modal__cabecera-texto strong {
  font-size: 0.98rem;
}
.asistencia-modal__cabecera-texto span {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.82);
  text-transform: capitalize;
}
.asistencia-modal__cuerpo {
  padding: 1.25rem 1.5rem;
}
.asistencia-modal__filas {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  margin-bottom: 1rem;
}
.asistencia-modal__fila {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  padding: 0.7rem 0.85rem;
  border-radius: var(--eca-r-md);
  background: var(--eca-surface);
  border: 1px solid var(--eca-surface-border);
}
.asistencia-modal__fila-punto {
  flex-shrink: 0;
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 50%;
  margin-top: 0.25rem;
}
.asistencia-modal__fila--entrada .asistencia-modal__fila-punto {
  background: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18);
}
.asistencia-modal__fila--salida .asistencia-modal__fila-punto {
  background: #dc2626;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.18);
}
.asistencia-modal__fila-texto {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.asistencia-modal__fila-texto strong {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--eca-ink-soft);
}
.asistencia-modal__fila-texto span {
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--eca-ink);
}
.asistencia-modal__fila-texto small {
  font-size: 0.72rem;
  color: var(--eca-ink-soft);
}
.asistencia-modal__pendiente {
  color: var(--eca-ink-faint, #9aa1af) !important;
  font-style: italic;
  font-weight: 600 !important;
  font-size: 0.85rem !important;
}
.asistencia-modal__sin-gps {
  color: var(--eca-ink-faint, #9aa1af);
}
.asistencia-modal__mapa {
  width: 100%;
  height: 16rem;
  border-radius: var(--eca-r-md);
  overflow: hidden;
  margin-bottom: 0.9rem;
}
.asistencia-modal__sin-mapa {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  height: 8rem;
  border-radius: var(--eca-r-md);
  background: var(--eca-surface);
  border: 1px dashed var(--eca-surface-border);
  color: var(--eca-ink-soft);
  font-size: 0.85rem;
  margin-bottom: 0.9rem;
}
.asistencia-modal__sin-mapa svg {
  width: 0.9rem;
  height: 0.9rem;
}
.asistencia-modal__notas {
  padding-top: 0.9rem;
  border-top: 1px solid var(--eca-surface-border);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.asistencia-modal__notas p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--eca-ink);
  line-height: 1.5;
}

@media (max-width: 640px) {
  .asistencia-modal__fondo {
    padding: 0;
    align-items: flex-end;
  }
  .asistencia-modal {
    max-width: 100%;
    max-height: 92vh;
    border-radius: 22px 22px 0 0;
  }
  .asistencia-modal-tarjeta-enter-from,
  .asistencia-modal-tarjeta-leave-to {
    transform: translateY(100%);
  }
  .asistencia-modal__cabecera {
    border-radius: 22px 22px 0 0;
  }
}
</style>
