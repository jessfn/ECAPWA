<!-- admin-eca — pantalla "Visor de Seguimiento" (reemplaza a "Geografía"):
     mapa (mismo Mapbox GL que ya traía Geografía, vía CDN en index.html)
     con la ubicación real de las actividades registradas por los técnicos
     y de las ECA geolocalizadas — pensado para dar seguimiento a dónde se
     está trabajando, no para administrar catálogo geográfico (por eso ya
     no lleva los toggles de activar/desactivar estado/municipio que tenía
     Geografía: ese no era el propósito de esta vista).
     Layout pedido explícito: panel de controles fijo a la IZQUIERDA (mismo
     acomodo que el Visor de Seguimiento de admin-pwa) + mapa a pantalla
     completa a la derecha. El detalle de cada ubicación es un panel
     ACOPLADO dentro del propio mapa (nunca un modal de página completa ni
     una navegación a otra vista): arranca compacto y se agranda ahí mismo
     cuando se quiere ver todo. -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../services/api'
import { listarActividades, obtenerActividad, urlVistaPreviaEvidencia } from '../services/actividadesService'
import { listarEcas } from '../services/ecasService'
import { listarCatalogo } from '../services/catalogosService'
import AuthIcon from '../components/auth/AuthIcon.vue'

const cargando = ref(false)
const error = ref('')

const actividades = ref([]) // solo las que tienen coordenadas
const ecas = ref([]) // solo las que tienen coordenadas
const tecnicos = ref([])
const tecnicosPorId = computed(() => new Map(tecnicos.value.map((t) => [t.id, t])))
const tiposActividad = ref([])
// Solo para mostrar el nombre real en el panel de detalle (antes no se
// mostraban en absoluto tema/subtema/sistema productivo, igual que pasaba
// en Actividades) — no se usan como filtro del mapa.
const temas = ref([])
const subtemas = ref([])
const sistemasProductivos = ref([])

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
async function cargarTemas() {
  try {
    temas.value = await listarCatalogo('temas', { todos: true })
  } catch {
    temas.value = []
  }
}
async function cargarSubtemas() {
  try {
    subtemas.value = await listarCatalogo('subtemas', { todos: true })
  } catch {
    subtemas.value = []
  }
}
async function cargarSistemasProductivos() {
  try {
    sistemasProductivos.value = await listarCatalogo('sistemas-productivos', { todos: true })
  } catch {
    sistemasProductivos.value = []
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
// Elemento DOM del marcador de actividad actualmente resaltado (no es
// reactivo a propósito: solo se usa para alternar una clase CSS sobre el
// nodo directo, sin pasar por el ciclo de reactividad de Vue).
let elementoMarcadorSeleccionado = null

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
function temaNombre(a) {
  if (!a?.tema_id) return null
  return temas.value.find((t) => t.id === a.tema_id)?.nombre || `Tema #${a.tema_id}`
}
function subtemaNombre(a) {
  if (!a?.subtema_id) return null
  return subtemas.value.find((s) => s.id === a.subtema_id)?.nombre || `Subtema #${a.subtema_id}`
}
function sistemaProductivoNombre(a) {
  if (!a?.sistema_productivo_id) return null
  return (
    sistemasProductivos.value.find((s) => s.id === a.sistema_productivo_id)?.nombre ||
    `Sistema #${a.sistema_productivo_id}`
  )
}

// ---- Panel de detalle al tocar una ubicación (solo actividades: son las
// únicas con fotos) — ACOPLADO al mapa, nunca navega a otra vista: arranca
// compacto y se agranda ahí mismo cuando se quiere ver todo. ----
const modalAbierto = ref(false)
const modalActividad = ref(null) // fila básica (lista) — header inmediato
const modalDetalle = ref(null) // detalle completo (con evidencias), llega después
const modalCargando = ref(false)
const modalError = ref('')
const modalFotos = ref([]) // [{ id, url }]
const modalIndice = ref(0)
// Panel acoplado al mapa: arranca compacto (avatar + fecha + miniatura +
// descripción corta) y se agranda "ahí mismo" (nunca navega a otra vista)
// cuando el admin quiere ver todo — galería completa con contador y
// flechas, descripción sin recortar.
const panelExpandido = ref(false)
// Pedido explícito: el panel no mostraba toda la información al seleccionar
// un punto (tema/subtema/sistema productivo, el texto de "Otro", resultado,
// coordenadas...). Esos campos ya vienen en la fila básica de la lista
// (`modalActividad`, `ActividadPublica` los incluye todos) — no hace falta
// esperar a que cargue el detalle completo (`modalDetalle`, que solo agrega
// las evidencias) para mostrarlos. Este computed usa lo que haya disponible
// más rápido, y se actualiza solo cuando el detalle completo llega.
const infoActividad = computed(() => modalDetalle.value || modalActividad.value || {})

// Pedido explícito: al seleccionar una ubicación, el mapa hace un zoom
// suave hacia ella (poco, no un acercamiento extremo) y el marcador se
// anima para que quede claro cuál se tocó. `seleccionarMarcador` es el
// punto de entrada único desde el click del marcador: resalta, centra y
// abre el panel de detalle, en ese orden.
function seleccionarMarcador(a, el) {
  if (elementoMarcadorSeleccionado && elementoMarcadorSeleccionado !== el) {
    elementoMarcadorSeleccionado.classList.remove('visor-marcador--seleccionado')
  }
  // Se retira y se vuelve a poner la clase aunque ya la tuviera (reinicia
  // la animación) — tocar el mismo marcador dos veces debe rebotar de
  // nuevo, no quedarse quieto la segunda vez.
  el.classList.remove('visor-marcador--seleccionado')
  void el.offsetWidth // fuerza reflow para que el navegador note el "quita y pon" de la clase
  el.classList.add('visor-marcador--seleccionado')
  elementoMarcadorSeleccionado = el

  centrarEnMarcador(a)
  abrirModalActividad(a)
}

function centrarEnMarcador(a) {
  if (!mapa) return
  // "Zoom poco": si ya se estaba bastante cerca, no se aleja ni se
  // exagera; si se estaba viendo el país completo, sí se acerca lo
  // suficiente para distinguir la ubicación exacta. Nunca menos de 12 ni
  // más de 15 — sigue siendo un acercamiento moderado, no al máximo.
  const zoomActual = mapa.getZoom()
  const zoomObjetivo = Math.min(15, Math.max(zoomActual + 1.3, 12.5))
  mapa.flyTo({
    center: [a.longitud, a.latitud],
    zoom: zoomObjetivo,
    speed: 0.85,
    curve: 1.35,
    essential: true,
  })
}

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
  panelExpandido.value = false
  limpiarModalFotos()
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
  panelExpandido.value = false
  fotoGrandeAbierta.value = false
  limpiarModalFotos()
  if (elementoMarcadorSeleccionado) {
    elementoMarcadorSeleccionado.classList.remove('visor-marcador--seleccionado')
    elementoMarcadorSeleccionado = null
  }
}
function fotoSiguiente() {
  if (!modalFotos.value.length) return
  modalIndice.value = (modalIndice.value + 1) % modalFotos.value.length
}
function fotoAnterior() {
  if (!modalFotos.value.length) return
  modalIndice.value = (modalIndice.value - 1 + modalFotos.value.length) % modalFotos.value.length
}

// ---- Ver la foto en grande (pedido explícito): al dar clic en la imagen
// del panel se abre el mismo visor de pantalla completa que ya existe en
// la columna de fotos de Actividades — contador + anterior/siguiente,
// reutilizando el MISMO índice (`modalIndice`) que ya gobierna la
// miniatura del panel, así que ambos quedan siempre sincronizados. ----
const fotoGrandeAbierta = ref(false)
function abrirFotoGrande() {
  if (!modalFotos.value.length) return
  fotoGrandeAbierta.value = true
}
function cerrarFotoGrande() {
  fotoGrandeAbierta.value = false
}

function onTeclaModal(evento) {
  if (!modalAbierto.value) return
  if (evento.key === 'Escape') {
    if (fotoGrandeAbierta.value) return cerrarFotoGrande()
    return cerrarModal()
  }
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
  elementoMarcadorSeleccionado = null

  if (capaActividades.value) {
    actividades.value.forEach((a) => {
      const color = a.estado_gps === 'GPS_IMPRECISO' ? '#d97706' : '#2e7d32'
      // Elemento PROPIO (en vez de dejar que Mapbox arme su pin por
      // defecto): así el "seleccionado" se anima en un hijo interno
      // (`.visor-marcador__nucleo`/`__anillo`), nunca en la raíz — la raíz
      // es la que Mapbox mueve con su propio `transform` para ubicarla en
      // el mapa, y animar esa misma propiedad ahí pelearía con esa
      // posición (el marcador "temblaría" fuera de su lugar).
      const el = document.createElement('div')
      el.className = 'visor-marcador'
      el.style.color = color
      el.innerHTML = '<span class="visor-marcador__anillo"></span><span class="visor-marcador__nucleo"></span>'
      el.style.cursor = 'pointer'
      el.setAttribute('role', 'button')
      el.setAttribute('aria-label', 'Ver detalle de la actividad')

      const marcador = new window.mapboxgl.Marker({ element: el, anchor: 'center' })
        .setLngLat([a.longitud, a.latitud])
        .addTo(mapa)

      // Sin popup nativo: al tocar la ubicación se abre el panel de detalle
      // acoplado al mapa (con fotos) — mucho más útil aquí que un globo de
      // texto, ya que las actividades sí tienen evidencia fotográfica.
      el.addEventListener('click', (evento) => {
        evento.stopPropagation()
        seleccionarMarcador(a, el)
      })
      marcadoresActividades.push(marcador)

      // Si el panel ya estaba abierto para esta actividad (p. ej. se
      // reconstruyeron los marcadores por un cambio de filtro mientras se
      // veía su detalle), se re-marca como seleccionada sin volver a
      // hacer zoom — solo se conserva el resaltado visual.
      if (modalAbierto.value && modalActividad.value?.uuid === a.uuid) {
        el.classList.add('visor-marcador--seleccionado')
        elementoMarcadorSeleccionado = el
      }
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
    // Vista satelital (pedido explícito) — la versión "streets" incluye
    // calles/etiquetas sobre la imagen satelital, más útil aquí que la
    // vista pura (`satellite-v9`, sin ningún contexto de calles/pueblos)
    // para ubicar de un vistazo dónde cae cada actividad.
    style: 'mapbox://styles/mapbox/satellite-streets-v12',
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
  await Promise.all([
    cargarTecnicos(),
    cargarTiposActividad(),
    cargarTemas(),
    cargarSubtemas(),
    cargarSistemasProductivos(),
    cargarActividades(),
    cargarEcas(),
  ])
  cargando.value = false
  iniciarMapa()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onTeclaModal)
  limpiarModalFotos()
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

    <!-- Cuerpo en dos columnas — mismo acomodo que el Visor de Seguimiento
         de admin-pwa: panel de controles fijo a la izquierda, mapa
         ocupando el resto del ancho. -->
    <div class="visor__cuerpo">
      <aside class="visor__lateral">
        <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>

        <div class="visor__stats">
          <div class="eca-stat-card eca-stat-card--verde">
            <span class="eca-stat-card__icono"><AuthIcon name="map-pin" /></span>
            <div><div class="eca-stat-card__valor">{{ stats.ubicaciones }}</div><div class="eca-stat-card__etiqueta">Ubicaciones</div></div>
          </div>
          <div class="eca-stat-card eca-stat-card--morado">
            <span class="eca-stat-card__icono"><AuthIcon name="user" /></span>
            <div><div class="eca-stat-card__valor">{{ stats.tecnicos }}</div><div class="eca-stat-card__etiqueta">Técnicos activos</div></div>
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

        <div class="visor__seccion">
          <h3 class="visor__seccion-titulo"><AuthIcon name="search" /> Buscar técnico</h3>
          <div class="visor__buscador">
            <span class="visor__buscador-icono"><AuthIcon name="search" /></span>
            <input
              v-model="busquedaTecnico"
              type="text"
              placeholder="Nombre o CURP…"
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
        </div>

        <div class="visor__seccion">
          <h3 class="visor__seccion-titulo"><AuthIcon name="clock" /> Filtros</h3>
          <label class="visor__campo">
            <span>Tipo de actividad</span>
            <select v-model="tipoActividadId" @change="aplicarFiltros">
              <option :value="null">Todos los tipos</option>
              <option v-for="t in tiposActividad" :key="t.id" :value="t.id">{{ t.nombre }}</option>
            </select>
          </label>
          <label class="visor__campo">
            <span>Desde</span>
            <input v-model="desde" type="date" @change="aplicarFiltros" />
          </label>
          <label class="visor__campo">
            <span>Hasta</span>
            <input v-model="hasta" type="date" @change="aplicarFiltros" />
          </label>
        </div>

        <div class="visor__seccion">
          <h3 class="visor__seccion-titulo"><AuthIcon name="map-pin" /> Capas del mapa</h3>
          <button
            type="button"
            class="visor__chip-capa"
            :class="{ 'visor__chip-capa--activo': capaActividades }"
            @click="alternarCapa('actividades')"
          >
            <span class="visor__chip-punto visor__chip-punto--verde"></span> Actividades
            <span class="visor__chip-conteo">{{ actividades.length }}</span>
          </button>
          <button
            type="button"
            class="visor__chip-capa"
            :class="{ 'visor__chip-capa--activo': capaEcas }"
            @click="alternarCapa('ecas')"
          >
            <span class="visor__chip-punto visor__chip-punto--azul"></span> ECA
            <span class="visor__chip-conteo">{{ ecas.length }}</span>
          </button>
        </div>
      </aside>

      <div class="eca-card visor__mapa-card">
        <p v-if="mapaError" class="eca-alerta-error" role="alert">{{ mapaError }}</p>
        <div class="visor__mapa-envoltura">
          <div ref="mapaContenedor" class="visor__mapa"></div>

          <!-- Panel de detalle ACOPLADO al mapa (no navega a otra vista):
               arranca compacto y se agranda ahí mismo cuando se quiere ver
               todo — mismo espíritu que el Visor de Seguimiento de
               admin-pwa. -->
          <Transition name="visor-panel-deslizar">
            <div
              v-if="modalAbierto"
              class="visor-panel"
              :class="{ 'visor-panel--expandido': panelExpandido }"
              role="dialog"
              aria-modal="false"
            >
              <button type="button" class="visor-panel__cerrar" aria-label="Cerrar" @click="cerrarModal">
                <AuthIcon name="close" />
              </button>

              <div class="visor-panel__cabecera">
                <span class="visor-panel__avatar">{{ iniciales(tecnicoDe(modalActividad)) }}</span>
                <div class="visor-panel__cabecera-texto">
                  <strong>{{
                    tecnicoDe(modalActividad)
                      ? `${tecnicoDe(modalActividad).nombre} ${tecnicoDe(modalActividad).apellido_paterno}`
                      : `Técnico #${modalActividad?.usuario_id}`
                  }}</strong>
                  <span>{{ new Date(modalActividad?.fecha_hora).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' }) }}</span>
                </div>
              </div>

              <div class="visor-panel__badges">
                <span
                  class="visor-panel__badge-gps"
                  :class="modalActividad?.estado_gps === 'GPS_IMPRECISO' ? 'visor-panel__badge-gps--ambar' : 'visor-panel__badge-gps--verde'"
                >
                  <AuthIcon name="map-pin" /> {{ ETIQUETAS_GPS[modalActividad?.estado_gps] || modalActividad?.estado_gps }}
                </span>
                <span class="eca-badge eca-badge--morado">{{ tipoNombre(modalActividad || {}) }}</span>
              </div>
              <p class="visor-panel__eca"><AuthIcon name="school" /> {{ ecaNombreDe(modalActividad || {}) }}</p>
              <p v-if="modalError" class="eca-alerta-error" role="alert">{{ modalError }}</p>

              <!-- Información completa de la actividad (pedido explícito):
                   antes solo se veían técnico/fecha/GPS/tipo/ECA/descripción
                   y una foto — faltaban tema/subtema/sistema productivo, el
                   texto de "Otro" cuando aplica, resultado y coordenadas. -->
              <div class="visor-panel__datos">
                <p v-if="infoActividad.tipo_actividad_otro_texto" class="visor-panel__dato visor-panel__dato--otro">
                  <span class="visor-panel__dato-etiqueta">Otro (tipo de actividad)</span>
                  <span class="visor-panel__dato-valor">{{ infoActividad.tipo_actividad_otro_texto }}</span>
                </p>
                <p v-if="temaNombre(infoActividad)" class="visor-panel__dato">
                  <span class="visor-panel__dato-etiqueta">Tema</span>
                  <span class="visor-panel__dato-valor">{{ temaNombre(infoActividad) }}</span>
                </p>
                <p v-if="infoActividad.tema_otro_texto" class="visor-panel__dato visor-panel__dato--otro">
                  <span class="visor-panel__dato-etiqueta">Otro (tema)</span>
                  <span class="visor-panel__dato-valor">{{ infoActividad.tema_otro_texto }}</span>
                </p>
                <p v-if="subtemaNombre(infoActividad)" class="visor-panel__dato">
                  <span class="visor-panel__dato-etiqueta">Subtema</span>
                  <span class="visor-panel__dato-valor">{{ subtemaNombre(infoActividad) }}</span>
                </p>
                <p v-if="infoActividad.subtema_otro_texto" class="visor-panel__dato visor-panel__dato--otro">
                  <span class="visor-panel__dato-etiqueta">Otro (subtema)</span>
                  <span class="visor-panel__dato-valor">{{ infoActividad.subtema_otro_texto }}</span>
                </p>
                <p v-if="sistemaProductivoNombre(infoActividad)" class="visor-panel__dato">
                  <span class="visor-panel__dato-etiqueta">Sistema productivo</span>
                  <span class="visor-panel__dato-valor">{{ sistemaProductivoNombre(infoActividad) }}</span>
                </p>
                <p v-if="infoActividad.sistema_productivo_otro_texto" class="visor-panel__dato visor-panel__dato--otro">
                  <span class="visor-panel__dato-etiqueta">Otro (sistema productivo)</span>
                  <span class="visor-panel__dato-valor">{{ infoActividad.sistema_productivo_otro_texto }}</span>
                </p>
                <p v-if="infoActividad.num_participantes != null" class="visor-panel__dato">
                  <span class="visor-panel__dato-etiqueta">Participantes</span>
                  <span class="visor-panel__dato-valor">{{ infoActividad.num_participantes }}</span>
                </p>
                <p v-if="infoActividad.latitud != null" class="visor-panel__dato">
                  <span class="visor-panel__dato-etiqueta">Coordenadas</span>
                  <span class="visor-panel__dato-valor visor-panel__coordenadas">
                    {{ infoActividad.latitud.toFixed(6) }}, {{ infoActividad.longitud.toFixed(6) }}
                    <template v-if="infoActividad.precision_gps_m"> (±{{ Math.round(infoActividad.precision_gps_m) }} m)</template>
                  </span>
                </p>
                <p v-if="infoActividad.requiere_seguimiento" class="visor-panel__dato">
                  <span class="visor-panel__dato-etiqueta">Seguimiento</span>
                  <span class="visor-panel__dato-valor">
                    Requiere seguimiento
                    <template v-if="infoActividad.fecha_proximo_seguimiento">
                      — {{ new Date(`${infoActividad.fecha_proximo_seguimiento}T00:00:00`).toLocaleDateString('es-MX') }}
                    </template>
                  </span>
                </p>
                <p v-if="infoActividad.resultado" class="visor-panel__dato">
                  <span class="visor-panel__dato-etiqueta">Resultado</span>
                  <span class="visor-panel__dato-valor">{{ infoActividad.resultado }}</span>
                </p>
              </div>

              <!-- Compacto: miniatura + descripción recortada -->
              <template v-if="!panelExpandido">
                <button
                  v-if="modalCargando || modalFotos.length"
                  type="button"
                  class="visor-panel__miniatura"
                  :disabled="modalCargando"
                  @click="panelExpandido = true"
                >
                  <span v-if="modalCargando" class="visor-panel__miniatura-cargando">Cargando…</span>
                  <template v-else-if="modalFotos.length">
                    <img v-if="modalFotos[0]?.url" :src="modalFotos[0].url" alt="Evidencia" />
                    <span v-else class="visor-panel__miniatura-cargando">Cargando…</span>
                    <span v-if="modalFotos.length > 1" class="visor-panel__miniatura-conteo">+{{ modalFotos.length - 1 }}</span>
                  </template>
                </button>
                <p v-if="!modalCargando && !modalFotos.length" class="visor-panel__sinfotos">
                  <AuthIcon name="clock" /> Sin fotos.
                </p>
                <p class="visor-panel__descripcion visor-panel__descripcion--corta">
                  {{ modalDetalle?.descripcion || modalActividad?.descripcion }}
                </p>
                <button type="button" class="visor-panel__vermas" @click="panelExpandido = true">
                  Ver todo <AuthIcon name="chevron-right" />
                </button>
              </template>

              <!-- Expandido: galería completa + descripción entera, sigue
                   dentro del mapa (nunca cambia de vista). -->
              <template v-else>
                <button type="button" class="visor-panel__vermenos" @click="panelExpandido = false">
                  <AuthIcon name="chevron-left" /> Ver menos
                </button>

                <div class="visor-panel__galeria">
                  <p v-if="modalCargando" class="visor-panel__estado">Cargando…</p>
                  <p v-else-if="!modalFotos.length" class="visor-panel__estado">
                    <AuthIcon name="clock" /> Esta actividad no tiene fotos.
                  </p>
                  <template v-else>
                    <span v-if="modalFotos.length > 1" class="visor-panel__contador">
                      {{ modalIndice + 1 }} / {{ modalFotos.length }}
                    </span>
                    <button
                      v-if="modalFotos.length > 1"
                      type="button"
                      class="visor-panel__nav visor-panel__nav--prev"
                      aria-label="Foto anterior"
                      @click="fotoAnterior"
                    >
                      <AuthIcon name="chevron-left" />
                    </button>
                    <Transition name="visor-panel-imagen" mode="out-in">
                      <button
                        v-if="modalFotos[modalIndice]?.url"
                        :key="modalFotos[modalIndice].id"
                        type="button"
                        class="visor-panel__img-boton"
                        aria-label="Ver foto en grande"
                        @click="abrirFotoGrande"
                      >
                        <img :src="modalFotos[modalIndice].url" alt="Evidencia de la actividad" class="visor-panel__img" />
                        <span class="visor-panel__img-ampliar"><AuthIcon name="search" /></span>
                      </button>
                      <p v-else key="cargando-img" class="visor-panel__estado">Cargando imagen…</p>
                    </Transition>
                    <button
                      v-if="modalFotos.length > 1"
                      type="button"
                      class="visor-panel__nav visor-panel__nav--next"
                      aria-label="Foto siguiente"
                      @click="fotoSiguiente"
                    >
                      <AuthIcon name="chevron-right" />
                    </button>
                  </template>
                </div>

                <p class="visor-panel__descripcion">{{ modalDetalle?.descripcion || modalActividad?.descripcion }}</p>
              </template>
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <!-- ============ Foto en grande (pedido explícito): mismo visor de
         pantalla completa que la columna de fotos de Actividades —
         contador + anterior/siguiente, comparte `modalIndice` con la
         miniatura del panel de arriba. ============ -->
    <Teleport to="body">
      <Transition name="visor-foto-grande-fondo">
        <div v-if="fotoGrandeAbierta" class="visor-foto-grande" @click.self="cerrarFotoGrande">
          <button type="button" class="visor-foto-grande__cerrar" aria-label="Cerrar" @click="cerrarFotoGrande">
            <AuthIcon name="close" />
          </button>

          <span v-if="modalFotos.length > 1" class="visor-foto-grande__contador">
            {{ modalIndice + 1 }} / {{ modalFotos.length }}
          </span>

          <button
            v-if="modalFotos.length > 1"
            type="button"
            class="visor-foto-grande__nav visor-foto-grande__nav--prev"
            aria-label="Anterior"
            @click="fotoAnterior"
          >
            <AuthIcon name="chevron-left" />
          </button>

          <div class="visor-foto-grande__lienzo">
            <Transition name="visor-foto-grande-imagen" mode="out-in">
              <img
                v-if="modalFotos[modalIndice]?.url"
                :key="modalFotos[modalIndice].id"
                :src="modalFotos[modalIndice].url"
                alt="Evidencia de la actividad"
                class="visor-foto-grande__img"
              />
            </Transition>
          </div>

          <button
            v-if="modalFotos.length > 1"
            type="button"
            class="visor-foto-grande__nav visor-foto-grande__nav--next"
            aria-label="Siguiente"
            @click="fotoSiguiente"
          >
            <AuthIcon name="chevron-right" />
          </button>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped>
/* Layout de alto completo — mismo patrón que Actividades/Técnicos: el
   cuerpo llena el espacio restante bajo el header, sin scroll vertical de
   página. Dos columnas: panel de controles fijo a la izquierda + mapa. */
.visor-vista {
  height: calc(100dvh - 1rem);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.visor-vista > .eca-page-header {
  flex-shrink: 0;
}
.visor__cuerpo {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 0.75rem;
  padding: 0.75rem;
  overflow: hidden;
}

/* ---- Panel lateral (izquierda) ---- */
.visor__lateral {
  flex-shrink: 0;
  width: 17.5rem;
  overflow-y: auto;
  background: #fff;
  border: 1px solid var(--eca-surface-border);
  border-radius: var(--eca-r-lg);
  box-shadow: var(--eca-shadow-card);
  padding: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}
.visor__lateral::-webkit-scrollbar {
  width: 6px;
}
.visor__lateral::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 10px;
}

.visor__stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}
.visor__stats .eca-stat-card {
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.3rem;
  padding: 0.55rem 0.6rem;
}
.visor__stats .eca-stat-card :deep(.eca-stat-card__icono) {
  width: 1.6rem;
  height: 1.6rem;
}
.visor__stats .eca-stat-card :deep(.eca-stat-card__icono svg) {
  width: 0.8rem;
  height: 0.8rem;
}
.visor__stats .eca-stat-card :deep(.eca-stat-card__valor) {
  font-size: 1.05rem;
}
.visor__stats .eca-stat-card :deep(.eca-stat-card__etiqueta) {
  font-size: 0.64rem;
  line-height: 1.2;
}

.visor__seccion {
  padding-top: 0.75rem;
  border-top: 1px solid var(--eca-surface-border);
}
.visor__seccion-titulo {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0 0 0.6rem;
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--eca-green-700);
}
.visor__seccion-titulo svg {
  width: 0.8rem;
  height: 0.8rem;
}

.visor__campo {
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--eca-ink-soft);
  margin-bottom: 0.55rem;
}
.visor__campo:last-child {
  margin-bottom: 0;
}
.visor__campo select,
.visor__campo input {
  padding: 0.45rem 0.6rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid #cfe3d5;
  background: var(--eca-surface);
  font-family: inherit;
  font-size: 0.8rem;
  color: var(--eca-ink);
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}
.visor__campo select:focus,
.visor__campo input:focus {
  outline: none;
  border-color: var(--eca-green-500);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.12);
}

.visor__buscador {
  position: relative;
  width: 100%;
}
.visor__buscador-icono {
  position: absolute;
  left: 0.65rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--eca-ink-soft);
  display: flex;
  pointer-events: none;
}
.visor__buscador-icono svg {
  width: 0.85rem;
  height: 0.85rem;
}
.visor__buscador input {
  width: 100%;
  padding: 0.42rem 2rem;
  border-radius: 999px;
  border: 1.5px solid #cfe3d5;
  background: var(--eca-surface);
  font-family: inherit;
  font-size: 0.78rem;
  box-sizing: border-box;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}
.visor__buscador input:focus {
  outline: none;
  border-color: var(--eca-green-500);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.14);
}
.visor__buscador-limpiar {
  position: absolute;
  right: 0.4rem;
  top: 50%;
  transform: translateY(-50%);
  width: 1.35rem;
  height: 1.35rem;
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
  width: 0.62rem;
  height: 0.62rem;
}
.visor__sugerencias {
  position: absolute;
  z-index: 20;
  top: calc(100% + 0.35rem);
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid var(--eca-surface-border);
  border-radius: var(--eca-r-md);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.16);
  overflow: hidden;
  max-height: 16rem;
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
  gap: 0.55rem;
  padding: 0.5rem 0.7rem;
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
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--eca-green-500), var(--eca-green-700));
  color: #fff;
  font-size: 0.64rem;
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
  font-size: 0.78rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.visor__sugerencia-texto small {
  font-size: 0.66rem;
  color: var(--eca-ink-soft);
}

.visor__chip-capa {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.65rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid #cfe3d5;
  background: var(--eca-surface);
  color: var(--eca-ink-soft);
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease, opacity 0.15s ease;
  opacity: 0.6;
  margin-bottom: 0.45rem;
}
.visor__chip-capa:last-child {
  margin-bottom: 0;
}
.visor__chip-capa--activo {
  opacity: 1;
  color: var(--eca-ink);
  background: #fff;
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
.visor__chip-conteo {
  margin-left: auto;
  font-size: 0.7rem;
  font-weight: 800;
  color: var(--eca-ink-faint, #9aa1af);
}

/* ---- Mapa (columna derecha) ---- */
.visor__mapa-card {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
  padding: 0.6rem;
  overflow: hidden;
}
.visor__mapa-envoltura {
  position: relative;
  flex: 1;
  min-height: 0;
  border-radius: var(--eca-r-md);
  overflow: hidden;
}
.visor__mapa {
  position: absolute;
  inset: 0;
}
:deep(.mapboxgl-popup-content) {
  font-family: inherit;
  font-size: 0.8rem;
  line-height: 1.4;
  padding: 0.6rem 0.75rem;
}

/* ---- Marcador de actividad (elemento propio, no el pin por defecto de
   Mapbox): la raíz (`.visor-marcador`) es la que Mapbox reposiciona con su
   propio `transform` — las animaciones de abajo van SIEMPRE en los hijos
   (`__nucleo`/`__anillo`), nunca en la raíz, para no pelearse con esa
   posición. ---- */
:deep(.visor-marcador) {
  /* SIN `position` aquí — Mapbox ya le pone `position: absolute` por su
     cuenta (clase `.mapboxgl-marker` de su propio CSS) y calcula el
     `transform` de cada marcador asumiendo esa posición fija; pisarla con
     `relative` sacaba al marcador de ese cálculo y lo dejaba apilarse en
     el flujo normal del documento — la causa real de que "se movieran" al
     hacer zoom/paneo (terminaban todos en fila, muy al sur, en el mar).
     `position: absolute` de Mapbox de todos modos ya sirve como contexto
     de posicionamiento para los hijos `position: absolute` de abajo. */
  width: 1.35rem;
  height: 1.35rem;
}
:deep(.visor-marcador__nucleo) {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: currentColor;
  border: 2.5px solid #fff;
  box-shadow: 0 2px 7px rgba(0, 0, 0, 0.35);
  transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1);
}
:deep(.visor-marcador:hover .visor-marcador__nucleo) {
  transform: scale(1.18);
}
:deep(.visor-marcador__anillo) {
  position: absolute;
  inset: -0.5rem;
  border-radius: 50%;
  border: 2px solid currentColor;
  opacity: 0;
  pointer-events: none;
}
/* Seleccionado: el núcleo rebota y crece un poco; el anillo pulsa hacia
   afuera en bucle mientras el panel de detalle sigue abierto. */
:deep(.visor-marcador--seleccionado .visor-marcador__nucleo) {
  transform: scale(1.35);
  animation: visor-marcador-rebote 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}
:deep(.visor-marcador--seleccionado .visor-marcador__anillo) {
  animation: visor-marcador-pulso 1.6s ease-out infinite;
}
@keyframes visor-marcador-rebote {
  0% {
    transform: scale(0.5);
  }
  55% {
    transform: scale(1.5);
  }
  100% {
    transform: scale(1.35);
  }
}
@keyframes visor-marcador-pulso {
  0% {
    opacity: 0.9;
    transform: scale(0.5);
  }
  70% {
    opacity: 0;
    transform: scale(1.9);
  }
  100% {
    opacity: 0;
    transform: scale(1.9);
  }
}

@media (max-width: 900px) {
  .visor__cuerpo {
    flex-direction: column;
    overflow-y: auto;
  }
  .visor__lateral {
    width: 100%;
    max-height: 40vh;
  }
  .visor__mapa-card {
    min-height: 60vh;
  }
}

/* ---- Panel de detalle ACOPLADO al mapa: flota sobre la esquina, arranca
   compacto y se agranda ahí mismo — nunca cubre toda la pantalla ni sale
   del área del mapa. Mismo espíritu que el panel lateral del Visor de
   Seguimiento de admin-pwa. ---- */
.visor-panel {
  position: absolute;
  top: 0.7rem;
  right: 0.7rem;
  bottom: 0.7rem;
  z-index: 50;
  width: 18rem;
  max-width: calc(100% - 1.4rem);
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 16px;
  box-shadow: 0 16px 44px rgba(0, 0, 0, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.6);
  overflow-y: auto;
  padding: 0.9rem 0.9rem 1rem;
  transition: width 0.32s cubic-bezier(0.34, 1.2, 0.64, 1);
}
.visor-panel--expandido {
  width: 24rem;
}
.visor-panel-deslizar-enter-active,
.visor-panel-deslizar-leave-active {
  transition: opacity 0.22s ease, transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.visor-panel-deslizar-enter-from,
.visor-panel-deslizar-leave-to {
  opacity: 0;
  transform: translateX(16px);
}
@media (max-width: 640px) {
  .visor-panel {
    left: 0.6rem;
    right: 0.6rem;
    top: auto;
    bottom: 0.6rem;
    max-height: 70%;
    width: auto !important;
    max-width: none;
  }
}

.visor-panel__cerrar {
  position: absolute;
  top: 0.6rem;
  right: 0.6rem;
  z-index: 2;
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 50%;
  border: none;
  background: var(--eca-surface);
  color: var(--eca-ink);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.2s ease;
}
.visor-panel__cerrar:hover {
  transform: rotate(90deg);
  background: #e2e2e2;
}
.visor-panel__cerrar svg {
  width: 0.7rem;
  height: 0.7rem;
}

.visor-panel__cabecera {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding-right: 1.8rem;
  margin-bottom: 0.6rem;
}
.visor-panel__avatar {
  flex-shrink: 0;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--eca-green-500), var(--eca-green-700));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.68rem;
  font-weight: 800;
}
.visor-panel__cabecera-texto {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.visor-panel__cabecera-texto strong {
  font-size: 0.84rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.visor-panel__cabecera-texto span {
  font-size: 0.68rem;
  color: var(--eca-ink-soft);
}

.visor-panel__badges {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.4rem;
}
.visor-panel__badge-gps {
  display: flex;
  align-items: center;
  gap: 0.28rem;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  font-size: 0.64rem;
  font-weight: 800;
}
.visor-panel__badge-gps svg {
  width: 0.62rem;
  height: 0.62rem;
}
.visor-panel__badge-gps--verde {
  background: #dcfce7;
  color: var(--eca-green-700);
}
.visor-panel__badge-gps--ambar {
  background: #fef3c7;
  color: #92400e;
}
.visor-panel__eca {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin: 0 0 0.6rem;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--eca-ink-soft);
}
.visor-panel__eca svg {
  width: 0.7rem;
  height: 0.7rem;
}

/* Información completa (pedido explícito): lista compacta de datos extra
   de la actividad — tema/subtema/sistema productivo, participantes,
   coordenadas, seguimiento, resultado. Los renglones "Otro" van en azul
   rey, mismo color que ya distingue ese campo en Actividades y en la PWA
   de captura, para reconocerlo de un vistazo. */
.visor-panel__datos {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin: 0 0 0.65rem;
  padding: 0.55rem 0.65rem;
  border-radius: var(--eca-r-sm);
  background: var(--eca-surface);
  border: 1px solid var(--eca-surface-border);
}
.visor-panel__dato {
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
  margin: 0;
}
.visor-panel__dato-etiqueta {
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--eca-ink-soft);
}
.visor-panel__dato-valor {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--eca-ink);
  word-break: break-word;
}
.visor-panel__dato--otro .visor-panel__dato-etiqueta,
.visor-panel__dato--otro .visor-panel__dato-valor {
  color: #1d3fd6;
}
.visor-panel__coordenadas {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 0.72rem;
  font-weight: 500;
}

/* Compacto */
.visor-panel__miniatura {
  position: relative;
  display: block;
  width: 100%;
  height: 6.5rem;
  border: none;
  border-radius: 10px;
  overflow: hidden;
  background: var(--eca-surface);
  cursor: pointer;
  margin-bottom: 0.55rem;
  padding: 0;
}
.visor-panel__miniatura img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.visor-panel__miniatura-cargando {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  font-size: 0.72rem;
  color: var(--eca-ink-soft);
}
.visor-panel__miniatura-conteo {
  position: absolute;
  bottom: 0.4rem;
  right: 0.4rem;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 0.66rem;
  font-weight: 800;
}
.visor-panel__sinfotos {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin: 0 0 0.55rem;
  font-size: 0.74rem;
  color: var(--eca-ink-soft);
}
.visor-panel__sinfotos svg {
  width: 0.75rem;
  height: 0.75rem;
}
.visor-panel__descripcion {
  margin: 0 0 0.6rem;
  font-size: 0.78rem;
  color: var(--eca-ink);
  line-height: 1.5;
}
.visor-panel__descripcion--corta {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.visor-panel__vermas,
.visor-panel__vermenos {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  width: 100%;
  padding: 0.42rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid var(--eca-green-500);
  background: none;
  color: var(--eca-green-700);
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s ease;
}
.visor-panel__vermas:hover,
.visor-panel__vermenos:hover {
  background: #f0fdf4;
}
.visor-panel__vermas svg,
.visor-panel__vermenos svg {
  width: 0.65rem;
  height: 0.65rem;
}
.visor-panel__vermenos {
  margin-bottom: 0.6rem;
  border-color: var(--eca-surface-border);
  color: var(--eca-ink-soft);
}

/* Expandido: galería */
.visor-panel__galeria {
  position: relative;
  background: #111;
  height: 12rem;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.6rem;
}
.visor-panel__estado {
  color: rgba(255, 255, 255, 0.75);
  font-size: 0.76rem;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 1rem;
  text-align: center;
}
.visor-panel__estado svg {
  width: 0.75rem;
  height: 0.75rem;
  flex-shrink: 0;
}
.visor-panel__img-boton {
  position: relative;
  max-width: 100%;
  max-height: 100%;
  border: none;
  background: none;
  padding: 0;
  cursor: zoom-in;
  display: flex;
}
.visor-panel__img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.visor-panel__img-ampliar {
  position: absolute;
  bottom: 0.4rem;
  right: 0.4rem;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transform: scale(0.85);
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.visor-panel__img-boton:hover .visor-panel__img-ampliar {
  opacity: 1;
  transform: scale(1);
}
.visor-panel__img-ampliar svg {
  width: 0.6rem;
  height: 0.6rem;
}
.visor-panel-imagen-enter-active,
.visor-panel-imagen-leave-active {
  transition: opacity 0.16s ease;
}
.visor-panel-imagen-enter-from,
.visor-panel-imagen-leave-to {
  opacity: 0;
}
.visor-panel__contador {
  position: absolute;
  top: 0.5rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
  padding: 0.18rem 0.55rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  font-size: 0.66rem;
  font-weight: 700;
}
.visor-panel__nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  width: 1.8rem;
  height: 1.8rem;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease;
}
.visor-panel__nav:hover {
  background: rgba(255, 255, 255, 0.32);
}
.visor-panel__nav--prev {
  left: 0.4rem;
}
.visor-panel__nav--next {
  right: 0.4rem;
}
.visor-panel__nav svg {
  width: 0.8rem;
  height: 0.8rem;
}

/* ---- Foto en grande: mismo lenguaje que el visor de fotos de
   Actividades (fondo oscuro con desenfoque, imagen centrada, contador y
   flechas) — esta sí es una capa de pantalla completa a propósito: ver
   una foto ampliada es una acción secundaria explícita (clic en la
   imagen), no cambia de vista ni navega a otra pantalla. ---- */
.visor-foto-grande {
  position: fixed;
  inset: 0;
  z-index: 4000;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1.5rem;
  background: rgba(10, 15, 12, 0.85);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.visor-foto-grande-fondo-enter-active,
.visor-foto-grande-fondo-leave-active {
  transition: opacity 0.2s ease;
}
.visor-foto-grande-fondo-enter-from,
.visor-foto-grande-fondo-leave-to {
  opacity: 0;
}
.visor-foto-grande__lienzo {
  flex: 1;
  max-width: min(92vw, 900px);
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.visor-foto-grande__img {
  max-width: 100%;
  max-height: 82vh;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  object-fit: contain;
}
.visor-foto-grande-imagen-enter-active,
.visor-foto-grande-imagen-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.visor-foto-grande-imagen-enter-from {
  opacity: 0;
  transform: scale(0.98);
}
.visor-foto-grande-imagen-leave-to {
  opacity: 0;
}
.visor-foto-grande__cerrar {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.visor-foto-grande__cerrar:hover {
  background: rgba(255, 255, 255, 0.28);
  transform: rotate(90deg);
}
.visor-foto-grande__cerrar svg {
  width: 1.1rem;
  height: 1.1rem;
}
.visor-foto-grande__contador {
  position: absolute;
  top: 1.25rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.3rem 0.85rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.03em;
}
.visor-foto-grande__nav {
  flex-shrink: 0;
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease;
}
.visor-foto-grande__nav:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.08);
}
.visor-foto-grande__nav svg {
  width: 1.3rem;
  height: 1.3rem;
}
@media (max-width: 640px) {
  .visor-foto-grande {
    padding: 0.6rem;
    gap: 0.25rem;
  }
  .visor-foto-grande__nav {
    width: 2.4rem;
    height: 2.4rem;
  }
  .visor-foto-grande__img {
    max-height: 74vh;
  }
}
</style>
