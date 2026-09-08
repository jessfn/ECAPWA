<!-- admin-eca — pantalla "Visor de Seguimiento" (reemplaza a "Geografía"):
     mapa (mismo Mapbox GL que ya traía Geografía, vía CDN en index.html)
     con la ubicación real de las actividades registradas por los técnicos
     y de las ECA geolocalizadas — pensado para dar seguimiento a dónde se
     está trabajando, no para administrar catálogo geográfico (por eso ya
     no lleva los toggles de activar/desactivar estado/municipio que tenía
     Geografía: ese no era el propósito de esta vista).
     Mismo lenguaje visual que Actividades/Técnicos: header + panel de
     filtros fusionados, tarjeta de mapa a pantalla completa (sin scroll
     vertical de página). -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { api } from '../services/api'
import { listarActividades, obtenerActividad, urlVistaPreviaEvidencia } from '../services/actividadesService'
import { listarEcas } from '../services/ecasService'
import { listarCatalogo } from '../services/catalogosService'
import AuthIcon from '../components/auth/AuthIcon.vue'

const auth = useAuthStore()

const cargando = ref(false)
const error = ref('')

const actividades = ref([]) // solo las que tienen coordenadas
const ecas = ref([]) // solo las que tienen coordenadas
const tecnicos = ref([])
const tecnicosPorId = computed(() => new Map(tecnicos.value.map((t) => [t.id, t])))
const tiposActividad = ref([])

const ETIQUETAS_GPS = { CON_GPS: 'Con GPS', GPS_IMPRECISO: 'GPS impreciso' }

// ---- Filtros ----
const tecnicoId = ref(null)
const tipoActividadId = ref(null)
const desde = ref('')
const hasta = ref('')
const capaActividades = ref(true)
const capaEcas = ref(true)

// Buscador de técnico en tiempo real (mismo patrón que Actividades/Técnicos).
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

// ---- Stats del panel ----
const stats = computed(() => {
  const tecnicosConActividad = new Set(actividades.value.map((a) => a.usuario_id))
  return {
    ubicaciones: actividades.value.length,
    tecnicos: tecnicosConActividad.size,
    ecas: ecas.value.length,
    impreciso: actividades.value.filter((a) => a.estado_gps === 'GPS_IMPRECISO').length,
  }
})

// ---- Carga de datos ----
async function cargarTecnicos() {
  try {
    const { data } = await api.get('/usuarios/tecnicos-basico')
    tecnicos.value = data
  } catch {
    tecnicos.value = []
  }
}
async function cargarTiposActividad() {
  try {
    tiposActividad.value = await listarCatalogo('tipos-actividad', { todos: true })
  } catch {
    tiposActividad.value = []
  }
}
async function cargarEcas() {
  try {
    // `page_size` alto en una sola pasada (mismo criterio que tenía
    // Geografía): el catálogo de ECA de este proyecto no se acerca al
    // volumen donde hiciera falta paginar solo para pintar el mapa.
    const { resultados } = await listarEcas({ pageSize: 2000 })
    ecas.value = resultados.filter((e) => e.latitud != null && e.longitud != null)
  } catch {
    ecas.value = []
  }
}
async function cargarActividades() {
  try {
    const { resultados } = await listarActividades({
      tecnicoId: tecnicoId.value || undefined,
      tipoActividadId: tipoActividadId.value || undefined,
      desde: desde.value || undefined,
      hasta: hasta.value || undefined,
      page: 1,
      pageSize: 2000,
    })
    // Defensivo: la ubicación es obligatoria desde el 2026-09-08, pero una
    // actividad más vieja pudo haberse guardado sin coordenadas.
    actividades.value = resultados.filter((a) => a.latitud != null && a.longitud != null)
  } catch {
    error.value = 'No se pudieron cargar las ubicaciones de actividades.'
    actividades.value = []
  }
}

async function aplicarFiltros() {
  cargando.value = true
  error.value = ''
  await cargarActividades()
  cargando.value = false
  pintarMarcadores()
}

async function recargarTodo() {
  cargando.value = true
  error.value = ''
  await Promise.all([cargarActividades(), cargarEcas()])
  cargando.value = false
  pintarMarcadores()
  ajustarVista()
}

// ---- Mapa (Mapbox GL, mismo patrón que tenía Geografía) ----
const mapaContenedor = ref(null)
const mapaListo = ref(false)
const mapaError = ref('')
let mapa = null
let marcadoresActividades = []
let marcadoresEcas = []

const CENTRO_MEXICO = [-99.1332, 23.6345]

function tecnicoDe(a) {
  return tecnicosPorId.value.get(a.usuario_id) || null
}
function tipoNombre(a) {
  return tiposActividad.value.find((t) => t.id === a.tipo_actividad_id)?.nombre || '—'
}
function ecaNombreDe(a) {
  return a.eca_nombre || (a.eca_id ? `ECA #${a.eca_id}` : '—')
}

// ---- Modal de detalle al tocar una ubicación (solo actividades: son las
// únicas con fotos) — mismo patrón de galería/lightbox que Actividades:
// una foto sola muestra solo la imagen + cerrar; varias traen contador
// "n / total" y botones anterior/siguiente. ----
const modalAbierto = ref(false)
const modalActividad = ref(null) // fila básica (lista) — header inmediato
const modalDetalle = ref(null) // detalle completo (con evidencias), llega después
const modalCargando = ref(false)
const modalError = ref('')
const modalFotos = ref([]) // [{ id, url }]
const modalIndice = ref(0)

function limpiarModalFotos() {
  for (const f of modalFotos.value) {
    if (f.url) URL.revokeObjectURL(f.url)
  }
  modalFotos.value = []
}
async function abrirModalActividad(a) {
  modalAbierto.value = true
  modalActividad.value = a
  modalDetalle.value = null
  modalError.value = ''
  modalCargando.value = true
  modalIndice.value = 0
  limpiarModalFotos()
  document.body.style.overflow = 'hidden'
  try {
    const detalle = await obtenerActividad(a.uuid)
    modalDetalle.value = detalle
    const evidencias = detalle.evidencias || []
    modalFotos.value = evidencias.map((e) => ({ id: e.id, url: null }))
    await Promise.all(
      evidencias.map((e, i) =>
        urlVistaPreviaEvidencia(e.id)
          .then((url) => {
            if (modalFotos.value[i]) modalFotos.value[i] = { id: e.id, url }
          })
          .catch(() => {}),
      ),
    )
  } catch {
    modalError.value = 'No se pudo cargar el detalle de esta actividad.'
  } finally {
    modalCargando.value = false
  }
}
function cerrarModal() {
  modalAbierto.value = false
  modalActividad.value = null
  modalDetalle.value = null
  limpiarModalFotos()
  document.body.style.overflow = ''
}
function fotoSiguiente() {
  if (!modalFotos.value.length) return
  modalIndice.value = (modalIndice.value + 1) % modalFotos.value.length
}
function fotoAnterior() {
  if (!modalFotos.value.length) return
  modalIndice.value = (modalIndice.value - 1 + modalFotos.value.length) % modalFotos.value.length
}
function onTeclaModal(evento) {
  if (!modalAbierto.value) return
  if (evento.key === 'Escape') return cerrarModal()
  if (modalFotos.value.length < 2) return
  if (evento.key === 'ArrowRight') fotoSiguiente()
  if (evento.key === 'ArrowLeft') fotoAnterior()
}

function limpiarMarcadoresActividades() {
  marcadoresActividades.forEach((m) => m.remove())
  marcadoresActividades = []
}
function limpiarMarcadoresEcas() {
  marcadoresEcas.forEach((m) => m.remove())
  marcadoresEcas = []
}

function pintarMarcadores() {
  if (!mapa || !mapaListo.value) return
  limpiarMarcadoresActividades()
  limpiarMarcadoresEcas()

  if (capaActividades.value) {
    actividades.value.forEach((a) => {
      const color = a.estado_gps === 'GPS_IMPRECISO' ? '#d97706' : '#2e7d32'
      // Sin popup nativo: al tocar la ubicación se abre el modal de detalle
      // (con fotos) — mucho más útil aquí que un globo de texto, ya que
      // las actividades sí tienen evidencia fotográfica.
      const marcador = new window.mapboxgl.Marker({ color }).setLngLat([a.longitud, a.latitud]).addTo(mapa)
      const el = marcador.getElement()
      el.style.cursor = 'pointer'
      el.setAttribute('role', 'button')
      el.setAttribute('aria-label', 'Ver detalle de la actividad')
      el.addEventListener('click', (evento) => {
        evento.stopPropagation()
        abrirModalActividad(a)
      })
      marcadoresActividades.push(marcador)
    })
  }

  if (capaEcas.value) {
    ecas.value.forEach((eca) => {
      const popup = new window.mapboxgl.Popup({ offset: 14, closeButton: false }).setHTML(
        `<strong>${eca.nombre}</strong><br>${eca.activo ? 'Activa' : 'Inactiva'}${
          eca.localidad_nombre ? `<br>${eca.localidad_nombre}` : ''
        }`,
      )
      const marcador = new window.mapboxgl.Marker({ color: '#1d4ed8' })
        .setLngLat([eca.longitud, eca.latitud])
        .setPopup(popup)
        .addTo(mapa)
      marcadoresEcas.push(marcador)
    })
  }
}

function ajustarVista() {
  if (!mapa || !mapaListo.value) return
  const puntos = [
    ...(capaActividades.value ? actividades.value.map((a) => [a.longitud, a.latitud]) : []),
    ...(capaEcas.value ? ecas.value.map((e) => [e.longitud, e.latitud]) : []),
  ]
  if (!puntos.length) return
  if (puntos.length === 1) {
    mapa.flyTo({ center: puntos[0], zoom: 12, duration: 600 })
    return
  }
  const bounds = new window.mapboxgl.LngLatBounds()
  puntos.forEach((p) => bounds.extend(p))
  mapa.fitBounds(bounds, { padding: 56, maxZoom: 13, duration: 600 })
}

function iniciarMapa() {
  if (!window.mapboxgl) {
    mapaError.value = 'No se pudo cargar Mapbox (revisa tu conexión y vuelve a intentar).'
    return
  }
  const token = import.meta.env.VITE_MAPBOX_TOKEN
  if (!token) {
    mapaError.value = 'Falta configurar VITE_MAPBOX_TOKEN.'
    return
  }
  window.mapboxgl.accessToken = token
  mapa = new window.mapboxgl.Map({
    container: mapaContenedor.value,
    style: 'mapbox://styles/mapbox/streets-v11',
    center: CENTRO_MEXICO,
    zoom: 4.6,
  })
  mapa.addControl(new window.mapboxgl.NavigationControl(), 'top-right')
  mapa.addControl(new window.mapboxgl.ScaleControl({ unit: 'metric' }), 'bottom-left')
  mapa.on('load', () => {
    mapaListo.value = true
    pintarMarcadores()
    ajustarVista()
  })
  mapa.on('error', () => {
    mapaError.value = 'No se pudo cargar el mapa. Revisa el token de Mapbox.'
  })
}

function alternarCapa(capa) {
  if (capa === 'actividades') capaActividades.value = !capaActividades.value
  else capaEcas.value = !capaEcas.value
  pintarMarcadores()
}

onMounted(async () => {
  window.addEventListener('keydown', onTeclaModal)
  cargando.value = true
  await Promise.all([cargarTecnicos(), cargarTiposActividad(), cargarActividades(), cargarEcas()])
  cargando.value = false
  iniciarMapa()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onTeclaModal)
  limpiarModalFotos()
  document.body.style.overflow = ''
  limpiarMarcadoresActividades()
  limpiarMarcadoresEcas()
  mapa?.remove()
  mapa = null
})
</script>

<template>
  <section class="visor-vista">
    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="map-pin" /></span>
      <div class="eca-page-header__texto">
        <h1>Visor de Seguimiento</h1>
        <p>Ubicación de actividades y Escuelas de Campo en el mapa.</p>
      </div>
      <button
        type="button"
        class="eca-page-header__accion"
        :class="{ 'eca-page-header__accion--girando': cargando }"
        :disabled="cargando"
        aria-label="Recargar"
        @click="recargarTodo"
      >
        <AuthIcon name="sync" />
      </button>
    </div>

    <div class="eca-panel-fusionado">
      <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>

      <div class="visor__stats">
        <div class="eca-stat-card eca-stat-card--verde">
          <span class="eca-stat-card__icono"><AuthIcon name="map-pin" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.ubicaciones }}</div><div class="eca-stat-card__etiqueta">Ubicaciones en mapa</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--morado">
          <span class="eca-stat-card__icono"><AuthIcon name="user" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.tecnicos }}</div><div class="eca-stat-card__etiqueta">Técnicos con actividad</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--azul">
          <span class="eca-stat-card__icono"><AuthIcon name="school" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.ecas }}</div><div class="eca-stat-card__etiqueta">ECA geolocalizadas</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--ambar">
          <span class="eca-stat-card__icono"><AuthIcon name="alert" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.impreciso }}</div><div class="eca-stat-card__etiqueta">GPS impreciso</div></div>
        </div>
      </div>

      <div class="visor__filtros">
        <div class="visor__buscador">
          <span class="visor__buscador-icono"><AuthIcon name="search" /></span>
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
            class="visor__buscador-limpiar"
            aria-label="Limpiar búsqueda de técnico"
            @mousedown.prevent="limpiarBusquedaTecnico"
          >
            <AuthIcon name="close" />
          </button>

          <Transition name="visor-sugerencias">
            <div v-if="mostrarSugerencias && busquedaTecnico && sugerenciasTecnico.length" class="visor__sugerencias">
              <button
                v-for="t in sugerenciasTecnico"
                :key="t.id"
                type="button"
                class="visor__sugerencia"
                @mousedown.prevent="seleccionarTecnico(t)"
              >
                <span class="visor__sugerencia-avatar">{{ iniciales(t) }}</span>
                <span class="visor__sugerencia-texto">
                  <strong>{{ t.nombre }} {{ t.apellido_paterno }} {{ t.apellido_materno || '' }}</strong>
                  <small v-if="t.curp">{{ t.curp }}</small>
                </span>
              </button>
            </div>
          </Transition>
        </div>

        <div class="visor__selects">
          <select v-model="tipoActividadId" class="visor__control" @change="aplicarFiltros">
            <option :value="null">Todos los tipos</option>
            <option v-for="t in tiposActividad" :key="t.id" :value="t.id">{{ t.nombre }}</option>
          </select>
          <div class="visor__fecha visor__control">
            <span class="visor__fecha-etiqueta">Desde</span>
            <input v-model="desde" type="date" @change="aplicarFiltros" />
          </div>
          <div class="visor__fecha visor__control">
            <span class="visor__fecha-etiqueta">Hasta</span>
            <input v-model="hasta" type="date" @change="aplicarFiltros" />
          </div>
          <button
            type="button"
            class="visor__chip-capa"
            :class="{ 'visor__chip-capa--activo': capaActividades }"
            @click="alternarCapa('actividades')"
          >
            <span class="visor__chip-punto visor__chip-punto--verde"></span> Actividades
          </button>
          <button
            type="button"
            class="visor__chip-capa"
            :class="{ 'visor__chip-capa--activo': capaEcas }"
            @click="alternarCapa('ecas')"
          >
            <span class="visor__chip-punto visor__chip-punto--azul"></span> ECA
          </button>
        </div>
      </div>
    </div>

    <div class="eca-card visor__mapa-card">
      <p v-if="mapaError" class="eca-alerta-error" role="alert">{{ mapaError }}</p>
      <div ref="mapaContenedor" class="visor__mapa"></div>
    </div>

    <!-- ============ Modal moderno: detalle de la actividad tocada en el
         mapa, con galería de fotos (contador + anterior/siguiente cuando
         hay más de una). ============ -->
    <Teleport to="body">
      <Transition name="visor-modal-fondo">
        <div v-if="modalAbierto" class="visor-modal__fondo" @click.self="cerrarModal">
          <Transition name="visor-modal-tarjeta" appear>
            <div class="visor-modal" role="dialog" aria-modal="true">
              <button type="button" class="visor-modal__cerrar" aria-label="Cerrar" @click="cerrarModal">
                <AuthIcon name="close" />
              </button>

              <div class="visor-modal__cabecera">
                <span class="visor-modal__avatar">{{ iniciales(tecnicoDe(modalActividad)) }}</span>
                <div class="visor-modal__cabecera-texto">
                  <strong>{{
                    tecnicoDe(modalActividad)
                      ? `${tecnicoDe(modalActividad).nombre} ${tecnicoDe(modalActividad).apellido_paterno}`
                      : `Técnico #${modalActividad?.usuario_id}`
                  }}</strong>
                  <span>{{ new Date(modalActividad?.fecha_hora).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' }) }}</span>
                </div>
                <span
                  class="visor-modal__badge-gps"
                  :class="modalActividad?.estado_gps === 'GPS_IMPRECISO' ? 'visor-modal__badge-gps--ambar' : 'visor-modal__badge-gps--verde'"
                >
                  <AuthIcon name="map-pin" /> {{ ETIQUETAS_GPS[modalActividad?.estado_gps] || modalActividad?.estado_gps }}
                </span>
              </div>

              <!-- Galería -->
              <div class="visor-modal__galeria">
                <p v-if="modalCargando" class="visor-modal__estado">Cargando…</p>
                <p v-else-if="!modalFotos.length" class="visor-modal__estado">
                  <AuthIcon name="clock" /> Esta actividad no tiene fotos.
                </p>
                <template v-else>
                  <span v-if="modalFotos.length > 1" class="visor-modal__contador">
                    {{ modalIndice + 1 }} / {{ modalFotos.length }}
                  </span>
                  <button
                    v-if="modalFotos.length > 1"
                    type="button"
                    class="visor-modal__nav visor-modal__nav--prev"
                    aria-label="Foto anterior"
                    @click="fotoAnterior"
                  >
                    <AuthIcon name="chevron-left" />
                  </button>
                  <Transition name="visor-modal-imagen" mode="out-in">
                    <img
                      v-if="modalFotos[modalIndice]?.url"
                      :key="modalFotos[modalIndice].id"
                      :src="modalFotos[modalIndice].url"
                      alt="Evidencia de la actividad"
                      class="visor-modal__img"
                    />
                    <p v-else key="cargando-img" class="visor-modal__estado">Cargando imagen…</p>
                  </Transition>
                  <button
                    v-if="modalFotos.length > 1"
                    type="button"
                    class="visor-modal__nav visor-modal__nav--next"
                    aria-label="Foto siguiente"
                    @click="fotoSiguiente"
                  >
                    <AuthIcon name="chevron-right" />
                  </button>
                </template>
              </div>

              <!-- Información -->
              <div class="visor-modal__info">
                <p v-if="modalError" class="eca-alerta-error" role="alert">{{ modalError }}</p>
                <div class="visor-modal__badges">
                  <span class="eca-badge eca-badge--morado">{{ tipoNombre(modalActividad || {}) }}</span>
                  <span class="visor-modal__eca"><AuthIcon name="school" /> {{ ecaNombreDe(modalActividad || {}) }}</span>
                </div>
                <p class="visor-modal__descripcion">{{ modalDetalle?.descripcion || modalActividad?.descripcion }}</p>
                <RouterLink
                  v-if="auth.tienePermiso('vista.actividades') && modalActividad"
                  :to="{ name: 'actividad-detalle', params: { uuid: modalActividad.uuid } }"
                  class="visor-modal__vertodo"
                >
                  Ver actividad completa <AuthIcon name="chevron-right" />
                </RouterLink>
              </div>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped>
/* Layout de alto completo — mismo patrón que Actividades/Técnicos: el
   mapa llena el espacio restante bajo header + filtros, sin scroll
   vertical de página. */
.visor-vista {
  height: calc(100dvh - 1rem);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.visor-vista > .eca-page-header,
.visor-vista > .eca-panel-fusionado {
  flex-shrink: 0;
}
.visor-vista > .visor__mapa-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
  padding: 0.6rem;
  overflow: hidden;
}
.visor__mapa {
  flex: 1;
  min-height: 0;
  border-radius: var(--eca-r-md);
  overflow: hidden;
}
:deep(.mapboxgl-popup-content) {
  font-family: inherit;
  font-size: 0.8rem;
  line-height: 1.4;
  padding: 0.6rem 0.75rem;
}

.visor__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.55rem;
  margin-bottom: 0.65rem;
}
.visor__stats .eca-stat-card {
  min-width: 0;
  padding: 0.45rem 0.65rem;
  gap: 0.5rem;
}
.visor__stats .eca-stat-card :deep(.eca-stat-card__icono) {
  width: 1.7rem;
  height: 1.7rem;
}
.visor__stats .eca-stat-card :deep(.eca-stat-card__icono svg) {
  width: 0.85rem;
  height: 0.85rem;
}
.visor__stats .eca-stat-card :deep(.eca-stat-card__valor) {
  font-size: 0.98rem;
}
.visor__stats .eca-stat-card :deep(.eca-stat-card__etiqueta) {
  font-size: 0.66rem;
}
@media (max-width: 820px) {
  .visor__stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 460px) {
  .visor__stats {
    grid-template-columns: 1fr;
  }
}

.visor__filtros {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.visor__buscador {
  position: relative;
  width: 100%;
}
.visor__buscador-icono {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--eca-ink-soft);
  display: flex;
  pointer-events: none;
}
.visor__buscador-icono svg {
  width: 0.9rem;
  height: 0.9rem;
}
.visor__buscador input {
  width: 100%;
  padding: 0.42rem 2.2rem;
  border-radius: 999px;
  border: 1.5px solid #cfe3d5;
  background: #fff;
  font-family: inherit;
  font-size: 0.8rem;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.visor__buscador input:focus {
  outline: none;
  border-color: var(--eca-green-500);
  box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.14);
}
.visor__buscador-limpiar {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  width: 1.5rem;
  height: 1.5rem;
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
.visor__buscador-limpiar:hover {
  background: #e2e2e2;
  transform: translateY(-50%) scale(1.08);
}
.visor__buscador-limpiar svg {
  width: 0.7rem;
  height: 0.7rem;
}
.visor__sugerencias {
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
.visor-sugerencias-enter-active,
.visor-sugerencias-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.visor-sugerencias-enter-from,
.visor-sugerencias-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
.visor__sugerencia {
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
.visor__sugerencia:hover {
  background: var(--eca-surface);
}
.visor__sugerencia + .visor__sugerencia {
  border-top: 1px solid var(--eca-surface-border);
}
.visor__sugerencia-avatar {
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
.visor__sugerencia-texto {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}
.visor__sugerencia-texto strong {
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.visor__sugerencia-texto small {
  font-size: 0.72rem;
  color: var(--eca-ink-soft);
}

.visor__selects {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 0.5rem;
}
.visor__control {
  flex: 1 1 0;
  min-width: 8rem;
  height: 2.05rem;
  box-sizing: border-box;
}
select.visor__control {
  padding: 0 0.7rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid #cfe3d5;
  background: #fff;
  font-size: 0.82rem;
  color: var(--eca-ink);
  cursor: pointer;
}
.visor__fecha {
  position: relative;
  display: flex;
  align-items: flex-end;
  border-radius: var(--eca-r-sm);
  border: 1px solid #cfe3d5;
  background: #fff;
}
.visor__fecha:focus-within {
  border-color: var(--eca-green-500);
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.12);
}
.visor__fecha-etiqueta {
  position: absolute;
  top: 0.28rem;
  left: 0.7rem;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--eca-ink-soft);
  pointer-events: none;
}
.visor__fecha input {
  width: 100%;
  height: 100%;
  border: none;
  background: none;
  padding: 0.72rem 0.6rem 0.15rem;
  font-family: inherit;
  font-size: 0.76rem;
  color: var(--eca-ink);
  box-sizing: border-box;
}
.visor__fecha input:focus {
  outline: none;
}

.visor__chip-capa {
  flex: 1 1 0;
  min-width: 8rem;
  height: 2.05rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0 0.8rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid #cfe3d5;
  background: #fff;
  color: var(--eca-ink-soft);
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease, opacity 0.15s ease;
  opacity: 0.55;
}
.visor__chip-capa--activo {
  opacity: 1;
  color: var(--eca-ink);
  background: var(--eca-surface);
  border-color: var(--eca-green-500);
}
.visor__chip-punto {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  flex-shrink: 0;
}
.visor__chip-punto--verde {
  background: #2e7d32;
}
.visor__chip-punto--azul {
  background: #1d4ed8;
}

@media (max-width: 720px) {
  .visor__control,
  .visor__chip-capa {
    flex: 1 1 calc(50% - 0.25rem);
  }
}
@media (max-width: 460px) {
  .visor__control,
  .visor__chip-capa {
    flex: 1 1 100%;
  }
}

/* ---- Modal moderno de detalle (con galería) al tocar una ubicación ---- */
.visor-modal__fondo {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.25rem;
  background: rgba(10, 15, 12, 0.6);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.visor-modal-fondo-enter-active,
.visor-modal-fondo-leave-active {
  transition: opacity 0.2s ease;
}
.visor-modal-fondo-enter-from,
.visor-modal-fondo-leave-to {
  opacity: 0;
}
.visor-modal {
  position: relative;
  width: 100%;
  max-width: 560px;
  max-height: 90vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.35), 0 2px 8px rgba(0, 0, 0, 0.1);
}
.visor-modal-tarjeta-enter-active {
  transition: opacity 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.visor-modal-tarjeta-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.visor-modal-tarjeta-enter-from {
  opacity: 0;
  transform: scale(0.94) translateY(14px);
}
.visor-modal-tarjeta-leave-to {
  opacity: 0;
  transform: scale(0.97) translateY(8px);
}
.visor-modal__cerrar {
  position: absolute;
  top: 0.85rem;
  right: 0.85rem;
  z-index: 2;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.9);
  color: var(--eca-ink);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.2s ease;
}
.visor-modal__cerrar:hover {
  transform: rotate(90deg) scale(1.08);
  background: #fff;
}
.visor-modal__cerrar svg {
  width: 0.85rem;
  height: 0.85rem;
}

.visor-modal__cabecera {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.1rem 3rem 1.1rem 1.25rem;
  background: linear-gradient(135deg, #2f7a33 0%, #256a2a 55%, #14501c 100%);
  color: #fff;
  border-radius: 24px 24px 0 0;
}
.visor-modal__avatar {
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
.visor-modal__cabecera-texto {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.visor-modal__cabecera-texto strong {
  font-size: 0.95rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.visor-modal__cabecera-texto span {
  font-size: 0.74rem;
  color: rgba(255, 255, 255, 0.8);
}
.visor-modal__badge-gps {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.28rem 0.6rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 800;
  background: rgba(255, 255, 255, 0.16);
  white-space: nowrap;
}
.visor-modal__badge-gps svg {
  width: 0.75rem;
  height: 0.75rem;
}
.visor-modal__badge-gps--ambar {
  color: #ffe6ae;
}
.visor-modal__badge-gps--verde {
  color: #d7ffd9;
}

/* Galería: mismo lenguaje que el visor de fotos de Actividades — imagen
   centrada, contador arriba, flechas a los lados. */
.visor-modal__galeria {
  position: relative;
  background: #111;
  min-height: 14rem;
  max-height: 46vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.visor-modal__estado {
  color: rgba(255, 255, 255, 0.75);
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 1.5rem;
}
.visor-modal__estado svg {
  width: 0.9rem;
  height: 0.9rem;
}
.visor-modal__img {
  max-width: 100%;
  max-height: 46vh;
  object-fit: contain;
}
.visor-modal-imagen-enter-active,
.visor-modal-imagen-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.visor-modal-imagen-enter-from {
  opacity: 0;
  transform: scale(0.98);
}
.visor-modal-imagen-leave-to {
  opacity: 0;
}
.visor-modal__contador {
  position: absolute;
  top: 0.7rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
  padding: 0.22rem 0.7rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 700;
}
.visor-modal__nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease;
}
.visor-modal__nav:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-50%) scale(1.08);
}
.visor-modal__nav--prev {
  left: 0.6rem;
}
.visor-modal__nav--next {
  right: 0.6rem;
}
.visor-modal__nav svg {
  width: 1rem;
  height: 1rem;
}

.visor-modal__info {
  padding: 1rem 1.25rem 1.25rem;
}
.visor-modal__badges {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.7rem;
}
.visor-modal__eca {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--eca-ink-soft);
}
.visor-modal__eca svg {
  width: 0.8rem;
  height: 0.8rem;
}
.visor-modal__descripcion {
  margin: 0 0 0.9rem;
  font-size: 0.88rem;
  color: var(--eca-ink);
  line-height: 1.5;
}
.visor-modal__vertodo {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--eca-green-700);
  text-decoration: none;
}
.visor-modal__vertodo svg {
  width: 0.75rem;
  height: 0.75rem;
}
.visor-modal__vertodo:hover {
  text-decoration: underline;
}

@media (max-width: 640px) {
  .visor-modal__fondo {
    padding: 0;
    align-items: flex-end;
  }
  .visor-modal {
    max-width: 100%;
    max-height: 92vh;
    border-radius: 22px 22px 0 0;
  }
  .visor-modal-tarjeta-enter-from,
  .visor-modal-tarjeta-leave-to {
    transform: translateY(100%);
  }
  .visor-modal__cabecera {
    border-radius: 22px 22px 0 0;
  }
}
</style>
