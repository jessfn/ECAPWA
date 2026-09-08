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
import { listarEstados, listarMunicipios } from '../services/geoService'
import { listarCatalogo } from '../services/catalogosService'
import {
  listarActividades,
  urlVistaPreviaEvidencia,
  obtenerActividad,
  descargarEvidencia,
} from '../services/actividadesService'
import { listarEcas, obtenerEca } from '../services/ecasService'
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

// Buscador de técnico en tiempo real (nombre o CURP) — sustituye el select
// "Todos los técnicos" por un campo con sugerencias. Filtra en el cliente
// sobre la lista ya cargada de técnicos (normalmente unas decenas, nunca
// miles), así que no hace falta pegarle al backend por cada tecleo.
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
    // Endpoint ligero (solo id/nombre/apellidos, sin correo/roles) que
    // cualquier cuenta del panel autenticada puede leer — antes se usaba
    // `GET /usuarios`, que exige `usuarios.gestionar`; un USUARIO con solo
    // `vista.actividades` se quedaba sin ese permiso y la tabla mostraba
    // "Técnico #63" en vez del nombre real.
    const { data } = await api.get('/usuarios/tecnicos-basico')
    tecnicos.value = data
  } catch {
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

// ---- Modal de detalle (pedido explícito: ya no navega a otra vista) ----
const modalUuid = ref(null)
const modalDetalle = ref(null)
const modalTecnico = ref(null)
const modalEca = ref(null)
const modalCargando = ref(false)
const modalError = ref('')
const modalVistasPrevias = ref({})

function limpiarModalVistasPrevias() {
  for (const url of Object.values(modalVistasPrevias.value)) URL.revokeObjectURL(url)
  modalVistasPrevias.value = {}
}

async function abrirDetalle(actividad) {
  modalUuid.value = actividad.uuid
  modalDetalle.value = null
  modalTecnico.value = null
  modalEca.value = null
  modalError.value = ''
  modalCargando.value = true
  limpiarModalMapa()
  document.body.style.overflow = 'hidden'
  try {
    modalDetalle.value = await obtenerActividad(actividad.uuid)
    for (const evidencia of modalDetalle.value.evidencias) {
      urlVistaPreviaEvidencia(evidencia.id)
        .then((url) => {
          modalVistasPrevias.value = { ...modalVistasPrevias.value, [evidencia.id]: url }
        })
        .catch(() => {})
    }
    api
      .get(`/usuarios/${modalDetalle.value.usuario_id}`)
      .then(({ data }) => (modalTecnico.value = data))
      .catch(() => {})
    if (modalDetalle.value.eca_id) {
      obtenerEca(modalDetalle.value.eca_id)
        .then((data) => (modalEca.value = data))
        .catch(() => {})
    }
  } catch {
    modalError.value = 'No se pudo cargar el detalle de esta actividad.'
  } finally {
    modalCargando.value = false
  }
}

function cerrarDetalle() {
  modalUuid.value = null
  limpiarModalVistasPrevias()
  limpiarModalMapa()
  document.body.style.overflow = ''
}

// ---- Mapa Mapbox del detalle: en vez de mostrar las coordenadas en
// crudo, un botón que despliega el mapa dentro del propio modal (sin
// apilar un segundo modal encima) — mismo estilo/patrón que el mapa de
// la vista Asistencia. ----
const modalMapaAbierto = ref(false)
const modalMapaContenedor = ref(null)
const modalMapaError = ref('')
let modalMapaInstancia = null

function limpiarModalMapa() {
  modalMapaInstancia?.remove()
  modalMapaInstancia = null
  modalMapaAbierto.value = false
  modalMapaError.value = ''
}

async function alternarModalMapa() {
  if (modalMapaAbierto.value) {
    limpiarModalMapa()
    return
  }
  modalMapaAbierto.value = true
  modalMapaError.value = ''
  await nextTick()
  iniciarModalMapa()
}

function iniciarModalMapa() {
  if (!modalMapaContenedor.value || !modalDetalle.value?.latitud) return

  if (!window.mapboxgl) {
    modalMapaError.value = 'No se pudo cargar Mapbox (revisa tu conexión).'
    return
  }
  const token = import.meta.env.VITE_MAPBOX_TOKEN
  if (!token) {
    modalMapaError.value = 'Falta configurar VITE_MAPBOX_TOKEN.'
    return
  }
  window.mapboxgl.accessToken = token
  const { latitud, longitud } = modalDetalle.value
  modalMapaInstancia = new window.mapboxgl.Map({
    container: modalMapaContenedor.value,
    style: 'mapbox://styles/mapbox/satellite-streets-v12',
    center: [longitud, latitud],
    zoom: 15,
  })
  modalMapaInstancia.addControl(new window.mapboxgl.NavigationControl(), 'top-right')
  modalMapaInstancia.on('load', () => {
    new window.mapboxgl.Marker({ color: '#2e7d32' }).setLngLat([longitud, latitud]).addTo(modalMapaInstancia)
  })
  modalMapaInstancia.on('error', () => {
    modalMapaError.value = 'No se pudo cargar el mapa.'
  })
}

// ---- Visor de fotos (lightbox) ----
// Al tocar la miniatura de una actividad se abre este visor con TODAS sus
// evidencias: si es una sola, solo la imagen + cerrar; si son varias,
// contador "n / total" y botones anterior/siguiente.
const visorAbierto = ref(false)
const visorFotos = ref([]) // [{ id, url }]
const visorIndice = ref(0)
const visorCargando = ref(false)
const visorError = ref('')

function limpiarVisor() {
  for (const f of visorFotos.value) {
    if (f.url) URL.revokeObjectURL(f.url)
  }
  visorFotos.value = []
}

async function abrirFotos(actividad) {
  if (!actividad.primera_evidencia_id) return
  visorAbierto.value = true
  visorCargando.value = true
  visorError.value = ''
  visorIndice.value = 0
  limpiarVisor()
  document.body.style.overflow = 'hidden'
  try {
    const detalle = await obtenerActividad(actividad.uuid)
    const evidencias = detalle.evidencias || []
    // Se crean las entradas en orden y se cargan las miniaturas en
    // paralelo; cada una rellena su `url` cuando llega.
    visorFotos.value = evidencias.map((e) => ({ id: e.id, url: null }))
    await Promise.all(
      evidencias.map((e, i) =>
        urlVistaPreviaEvidencia(e.id)
          .then((url) => {
            if (visorFotos.value[i]) visorFotos.value[i] = { id: e.id, url }
          })
          .catch(() => {}),
      ),
    )
    if (!visorFotos.value.length) visorError.value = 'Esta actividad no tiene fotos.'
  } catch {
    visorError.value = 'No se pudieron cargar las fotos.'
  } finally {
    visorCargando.value = false
  }
}
function cerrarVisor() {
  visorAbierto.value = false
  limpiarVisor()
  document.body.style.overflow = ''
}
function fotoSiguiente() {
  if (!visorFotos.value.length) return
  visorIndice.value = (visorIndice.value + 1) % visorFotos.value.length
}
function fotoAnterior() {
  if (!visorFotos.value.length) return
  visorIndice.value = (visorIndice.value - 1 + visorFotos.value.length) % visorFotos.value.length
}

function onTeclaEscape(evento) {
  if (evento.key === 'Escape') {
    if (visorAbierto.value) return cerrarVisor()
    if (modalUuid.value) return cerrarDetalle()
  }
  if (visorAbierto.value && visorFotos.value.length > 1) {
    if (evento.key === 'ArrowRight') fotoSiguiente()
    if (evento.key === 'ArrowLeft') fotoAnterior()
  }
}

onBeforeUnmount(() => {
  limpiarVistasPrevias()
  limpiarModalVistasPrevias()
  limpiarModalMapa()
  limpiarVisor()
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onTeclaEscape)
})

onMounted(async () => {
  window.addEventListener('keydown', onTeclaEscape)
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
  <section class="actividades-vista">
    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="clock" /></span>
      <div class="eca-page-header__texto">
        <h1>Actividades</h1>
        <p>Registros de todos los técnicos, con filtros y búsqueda.</p>
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

      <div class="actividades__stats">
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
        <div class="actividades__buscador">
          <span class="actividades__buscador-icono"><AuthIcon name="search" /></span>
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
            class="actividades__buscador-limpiar"
            aria-label="Limpiar búsqueda de técnico"
            @mousedown.prevent="limpiarBusquedaTecnico"
          >
            <AuthIcon name="close" />
          </button>

          <Transition name="actividades-sugerencias">
            <div v-if="mostrarSugerencias && busquedaTecnico && sugerenciasTecnico.length" class="actividades__sugerencias">
              <button
                v-for="t in sugerenciasTecnico"
                :key="t.id"
                type="button"
                class="actividades__sugerencia"
                @mousedown.prevent="seleccionarTecnico(t)"
              >
                <span class="actividades__sugerencia-avatar">{{ iniciales(t) }}</span>
                <span class="actividades__sugerencia-texto">
                  <strong>{{ t.nombre }} {{ t.apellido_paterno }} {{ t.apellido_materno || '' }}</strong>
                  <small v-if="t.curp">{{ t.curp }}</small>
                </span>
              </button>
            </div>
          </Transition>
          <Transition name="actividades-sugerencias">
            <div v-if="mostrarSugerencias && busquedaTecnico && !sugerenciasTecnico.length" class="actividades__sugerencias actividades__sugerencias--vacio">
              Sin coincidencias para "{{ busquedaTecnico }}"
            </div>
          </Transition>
        </div>

        <div class="actividades__selects">
          <select v-model="estadoId" class="actividades__control" @change="onCambioEstado">
            <option :value="null">Todos los estados</option>
            <option v-for="e in estados" :key="e.id" :value="e.id">{{ e.nombre }}</option>
          </select>
          <select v-model="municipioId" class="actividades__control" :disabled="!estadoId" @change="aplicarFiltros">
            <option :value="null">Todos los municipios</option>
            <option v-for="m in municipios" :key="m.id" :value="m.id">{{ m.nombre }}</option>
          </select>
          <select v-model="tipoActividadId" class="actividades__control" @change="aplicarFiltros">
            <option :value="null">Todos los tipos</option>
            <option v-for="t in tiposActividad" :key="t.id" :value="t.id">{{ t.nombre }}</option>
          </select>
          <select v-model="estadoGps" class="actividades__control" @change="aplicarFiltros">
            <option value="">Cualquier GPS</option>
            <option value="CON_GPS">Con GPS</option>
            <option value="GPS_IMPRECISO">GPS impreciso</option>
            <option value="SIN_GPS">Sin GPS</option>
          </select>
          <div class="actividades__fecha actividades__control">
            <span class="actividades__fecha-etiqueta">Desde</span>
            <input v-model="desde" type="date" @change="aplicarFiltros" />
          </div>
          <div class="actividades__fecha actividades__control">
            <span class="actividades__fecha-etiqueta">Hasta</span>
            <input v-model="hasta" type="date" @change="aplicarFiltros" />
          </div>
        </div>
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
              <td class="actividades__foto-col">
                <button
                  type="button"
                  class="actividades__foto-enlace"
                  :class="{ 'actividades__foto-enlace--multi': a.num_evidencias > 1 }"
                  :disabled="!a.primera_evidencia_id"
                  @click="abrirFotos(a)"
                >
                  <!-- Mitades "apiladas" desvanecidas cuando hay más de una foto -->
                  <template v-if="a.num_evidencias > 1">
                    <span
                      class="actividades__foto-pila actividades__foto-pila--izq"
                      :style="vistasPrevias[a.primera_evidencia_id] ? { backgroundImage: `url(${vistasPrevias[a.primera_evidencia_id]})` } : null"
                    ></span>
                    <span
                      class="actividades__foto-pila actividades__foto-pila--der"
                      :style="vistasPrevias[a.primera_evidencia_id] ? { backgroundImage: `url(${vistasPrevias[a.primera_evidencia_id]})` } : null"
                    ></span>
                  </template>

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

                  <span v-if="a.num_evidencias > 1" class="actividades__foto-conteo">{{ a.num_evidencias }}</span>
                </button>
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
                  <button
                    type="button"
                    class="actividades__accion actividades__accion--ver"
                    title="Ver detalle"
                    @click="abrirDetalle(a)"
                  >
                    <AuthIcon name="clipboard" />
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
        <span>Página {{ page }} de {{ totalPaginas }} · {{ total }} resultado(s)</span>
        <button type="button" :disabled="page >= totalPaginas" aria-label="Página siguiente" @click="irAPagina(page + 1)">
          <AuthIcon name="chevron-right" />
        </button>
      </div>
    </div>

    <Teleport to="body">
      <Transition name="actividades-fondo">
        <div v-if="modalUuid" class="actividades__modal-fondo" @click.self="cerrarDetalle">
          <Transition name="actividades-modal" appear>
            <div class="actividades__modal" role="dialog" aria-modal="true">
              <button type="button" class="actividades__modal-cerrar" aria-label="Cerrar" @click="cerrarDetalle">
                <AuthIcon name="close" />
              </button>

              <div v-if="modalCargando" class="actividades__modal-estado">
                <span class="actividades__modal-spinner"></span>
                <p>Cargando actividad…</p>
              </div>
              <div v-else-if="modalError" class="actividades__modal-estado">
                <AuthIcon name="alert" />
                <p>{{ modalError }}</p>
              </div>

              <template v-else-if="modalDetalle">
                <div class="actividades__modal-cabecera">
                  <span class="actividades__modal-icono"><AuthIcon name="clipboard" /></span>
                  <div class="actividades__modal-titulo">
                    <h2>Detalle de actividad</h2>
                    <p>{{ modalDetalle.uuid }}</p>
                  </div>
                  <span class="eca-badge" :class="BADGE_GPS[modalDetalle.estado_gps] || 'eca-badge--gris'">
                    <AuthIcon name="map-pin" /> {{ ETIQUETAS_GPS[modalDetalle.estado_gps] || '—' }}
                  </span>
                </div>

                <div class="actividades__modal-cuerpo">
                  <div class="actividades__modal-usuario">
                    <span class="eca-avatar">{{ iniciales(modalTecnico) }}</span>
                    <div>
                      <strong>
                        {{ modalTecnico ? `${modalTecnico.nombre} ${modalTecnico.apellido_paterno}` : `Técnico #${modalDetalle.usuario_id}` }}
                      </strong>
                      <span v-if="modalTecnico" class="eca-ayuda">{{ modalTecnico.correo }}</span>
                    </div>
                  </div>

                  <dl class="actividades__modal-datos">
                    <dt>Fecha</dt>
                    <dd>{{ new Date(modalDetalle.fecha_hora).toLocaleString('es-MX') }}</dd>
                    <dt>Tipo</dt>
                    <dd>{{ tipoInfo(modalDetalle).nombre }}</dd>
                    <dt>ECA</dt>
                    <dd>
                      {{
                        modalEca
                          ? modalEca.nombre
                          : modalDetalle.eca_id
                            ? `ECA #${modalDetalle.eca_id}`
                            : modalDetalle.eca_nombre
                              ? `${modalDetalle.eca_nombre} (escrita a mano)`
                              : '—'
                      }}
                    </dd>
                    <dt>Descripción</dt>
                    <dd>{{ modalDetalle.descripcion }}</dd>
                    <dt>Resultado</dt>
                    <dd>{{ modalDetalle.resultado || '—' }}</dd>
                    <dt>Ubicación GPS</dt>
                    <dd>
                      <button
                        v-if="modalDetalle.latitud"
                        type="button"
                        class="actividades__modal-btn-mapa"
                        :class="{ 'actividades__modal-btn-mapa--activo': modalMapaAbierto }"
                        @click="alternarModalMapa"
                      >
                        <AuthIcon name="map-pin" />
                        {{ modalMapaAbierto ? 'Ocultar mapa' : 'Ver ubicación en el mapa' }}
                        <small>(±{{ Math.round(modalDetalle.precision_gps_m || 0) }} m)</small>
                      </button>
                      <span v-else class="actividades__modal-sin-gps">Sin coordenadas</span>
                    </dd>
                  </dl>

                  <Transition name="actividades-mapa">
                    <div v-if="modalMapaAbierto" class="actividades__modal-mapa-seccion">
                      <p v-if="modalMapaError" class="eca-alerta-error" role="alert">{{ modalMapaError }}</p>
                      <div ref="modalMapaContenedor" class="actividades__modal-mapa"></div>
                    </div>
                  </Transition>

                  <div class="actividades__modal-galeria-seccion">
                    <h3><AuthIcon name="camera" /> Evidencias fotográficas</h3>
                    <div v-if="!modalDetalle.evidencias.length" class="eca-vacio">
                      <AuthIcon name="camera" />
                      <p>Sin fotos.</p>
                    </div>
                    <div v-else class="actividades__modal-galeria">
                      <figure v-for="e in modalDetalle.evidencias" :key="e.uuid" class="actividades__modal-foto">
                        <img v-if="modalVistasPrevias[e.id]" :src="modalVistasPrevias[e.id]" :alt="e.nombre_archivo" />
                        <div v-else class="actividades__modal-foto-cargando">Cargando…</div>
                        <figcaption>
                          <span>{{ e.nombre_archivo }}</span>
                          <button type="button" class="eca-btn eca-btn-secundario" @click="descargarEvidencia(e.id, e.nombre_archivo)">
                            Descargar
                          </button>
                        </figcaption>
                      </figure>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>

    <!-- ============ Visor de fotos (lightbox) ============ -->
    <Teleport to="body">
      <Transition name="visor-fondo">
        <div v-if="visorAbierto" class="visor" @click.self="cerrarVisor">
          <button type="button" class="visor__cerrar" aria-label="Cerrar" @click="cerrarVisor">
            <AuthIcon name="close" />
          </button>

          <span v-if="visorFotos.length > 1" class="visor__contador">
            {{ visorIndice + 1 }} / {{ visorFotos.length }}
          </span>

          <button
            v-if="visorFotos.length > 1"
            type="button"
            class="visor__nav visor__nav--prev"
            aria-label="Anterior"
            @click="fotoAnterior"
          >
            <AuthIcon name="chevron-left" />
          </button>

          <div class="visor__lienzo">
            <p v-if="visorCargando" class="visor__estado">Cargando…</p>
            <p v-else-if="visorError" class="visor__estado">{{ visorError }}</p>
            <Transition v-else name="visor-imagen" mode="out-in">
              <img
                v-if="visorFotos[visorIndice]?.url"
                :key="visorFotos[visorIndice].id"
                :src="visorFotos[visorIndice].url"
                alt="Evidencia"
                class="visor__img"
              />
              <p v-else key="cargando-img" class="visor__estado">Cargando imagen…</p>
            </Transition>
          </div>

          <button
            v-if="visorFotos.length > 1"
            type="button"
            class="visor__nav visor__nav--next"
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
/* ---- La vista ocupa exactamente el alto de la pantalla: header + panel
   de filtros arriba (altura natural) y la tabla llena el resto y hace su
   propio scroll interno — nunca scroll vertical de la página (pedido
   explícito). El `1rem` que se resta es el padding inferior de
   `.layout__contenido`. ---- */
.actividades-vista {
  height: calc(100dvh - 1rem);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.actividades-vista > .eca-page-header,
.actividades-vista > .eca-panel-fusionado {
  flex-shrink: 0;
}
.actividades-vista > .eca-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
  padding: 0.75rem 0.9rem;
  overflow: hidden;
}
.actividades-vista :deep(.eca-paginacion) {
  flex-shrink: 0;
  margin-top: 0.6rem;
  margin-bottom: 0;
}

/* ---- Barra de filtros: buscador de técnico (en tiempo real, nombre o
   CURP) arriba, ancho completo; el resto de los filtros abajo, en una
   fila que se centra y reparte el espacio de lado a lado, envolviendo en
   pantallas chicas. Controles más compactos que antes (pedido explícito:
   "más pequeños"). ---- */
/* Contadores: 4 columnas iguales que llenan TODO el ancho del panel de
   lado a lado (pedido explícito) — a diferencia del `.eca-stats-grid`
   global, que las capa a 210px y deja hueco a la derecha. Bajan a 2 y a 1
   columna en pantallas chicas. */
.actividades__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.55rem;
  margin-bottom: 0.65rem;
}
/* Tarjetas de contador más compactas (pedido explícito): menos padding,
   ícono y número más chicos. */
.actividades__stats .eca-stat-card {
  min-width: 0;
  padding: 0.45rem 0.65rem;
  gap: 0.5rem;
}
.actividades__stats .eca-stat-card :deep(.eca-stat-card__icono) {
  width: 1.7rem;
  height: 1.7rem;
}
.actividades__stats .eca-stat-card :deep(.eca-stat-card__icono svg) {
  width: 0.85rem;
  height: 0.85rem;
}
.actividades__stats .eca-stat-card :deep(.eca-stat-card__valor) {
  font-size: 0.98rem;
}
.actividades__stats .eca-stat-card :deep(.eca-stat-card__etiqueta) {
  font-size: 0.66rem;
}
@media (max-width: 820px) {
  .actividades__stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 460px) {
  .actividades__stats {
    grid-template-columns: 1fr;
  }
}

.actividades__filtros {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.6rem;
}
.actividades__buscador {
  position: relative;
  width: 100%;
}
.actividades__buscador-icono {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--eca-ink-soft);
  display: flex;
  pointer-events: none;
}
.actividades__buscador-icono svg {
  width: 0.9rem;
  height: 0.9rem;
}
.actividades__buscador input {
  width: 100%;
  padding: 0.42rem 2.2rem;
  border-radius: 999px;
  border: 1.5px solid #cfe3d5;
  background: #fff;
  font-family: inherit;
  font-size: 0.8rem;
  box-sizing: border-box;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}
.actividades__buscador input:focus {
  outline: none;
  border-color: var(--eca-green-500);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.14);
}
.actividades__buscador-limpiar {
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
.actividades__buscador-limpiar:hover {
  background: #e2e2e2;
  transform: translateY(-50%) scale(1.08);
}
.actividades__buscador-limpiar svg {
  width: 0.7rem;
  height: 0.7rem;
}
.actividades__sugerencias {
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
.actividades__sugerencias--vacio {
  padding: 0.9rem 1rem;
  font-size: 0.82rem;
  color: var(--eca-ink-soft);
  text-align: center;
}
.actividades-sugerencias-enter-active,
.actividades-sugerencias-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.actividades-sugerencias-enter-from,
.actividades-sugerencias-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
.actividades__sugerencia {
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
.actividades__sugerencia:hover {
  background: var(--eca-surface);
}
.actividades__sugerencia + .actividades__sugerencia {
  border-top: 1px solid var(--eca-surface-border);
}
.actividades__sugerencia-avatar {
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
.actividades__sugerencia-texto {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}
.actividades__sugerencia-texto strong {
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.actividades__sugerencia-texto small {
  font-size: 0.72rem;
  color: var(--eca-ink-soft);
  letter-spacing: 0.02em;
}

/* Fila de filtros: cada control (`.actividades__control`) ocupa una
   fracción igual del ancho y todos comparten la MISMA altura fija. Clave:
   el `flex` va sobre `.actividades__control` (hijo directo de la fila),
   nunca sobre el `<input>` de fecha — ese input vive dentro de un
   contenedor `column`, y ponerle `flex-basis` ahí lo estiraba en vertical
   (el bug de las cajas de fecha gigantes). */
.actividades__selects {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 0.5rem;
}
.actividades__control {
  flex: 1 1 0;
  min-width: 8rem;
  height: 2.05rem;
  box-sizing: border-box;
}
select.actividades__control {
  padding: 0 0.7rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid #cfe3d5;
  background: #fff;
  font-family: inherit;
  font-size: 0.82rem;
  color: var(--eca-ink);
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}
select.actividades__control:focus {
  outline: none;
  border-color: var(--eca-green-500);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.12);
}
select.actividades__control:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
/* Campo de fecha: label pequeño arriba-izquierda dentro de la misma caja,
   como un input "material" — así ocupa la misma altura que los selects sin
   una etiqueta externa que descuadre la fila. */
.actividades__fecha {
  position: relative;
  display: flex;
  align-items: flex-end;
  border-radius: var(--eca-r-sm);
  border: 1px solid #cfe3d5;
  background: #fff;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}
.actividades__fecha:focus-within {
  border-color: var(--eca-green-500);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.12);
}
.actividades__fecha-etiqueta {
  position: absolute;
  top: 0.28rem;
  left: 0.7rem;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--eca-ink-soft);
  pointer-events: none;
}
.actividades__fecha input {
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
.actividades__fecha input:focus {
  outline: none;
}
@media (max-width: 720px) {
  .actividades__control {
    flex: 1 1 calc(50% - 0.25rem);
  }
}
@media (max-width: 460px) {
  .actividades__control {
    flex: 1 1 100%;
  }
}
/* ---- Tabla con scroll INTERNO (pedido explícito): el contenedor llena
   el alto que le deja la tarjeta (flex) y es ÉL el que hace scroll —
   nunca la página completa — con el encabezado siempre visible arriba
   (`position: sticky`). ---- */
.actividades__tabla-contenedor {
  flex: 1;
  min-height: 0;
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
/* Columna de foto: el círculo va centrado en la celda. */
.actividades__foto-col {
  text-align: center;
}
.actividades__foto-enlace {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 2.6rem;
  border: none;
  background: none;
  padding: 0;
  cursor: pointer;
}
.actividades__foto-enlace:disabled {
  cursor: default;
}
.actividades__foto {
  position: relative;
  z-index: 2;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.actividades__foto-enlace:hover:not(:disabled) .actividades__foto {
  transform: scale(1.12);
}
/* Mitades "apiladas" que asoman desvanecidas a los lados cuando hay varias
   fotos — dan la sensación de un montón de imágenes detrás. */
.actividades__foto-pila {
  position: absolute;
  z-index: 1;
  top: 50%;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 50%;
  background-size: cover;
  background-position: center;
  background-color: var(--eca-surface);
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.25s ease;
}
.actividades__foto-pila--izq {
  left: 0;
  transform: translate(-38%, -50%) scale(0.82);
  opacity: 0.45;
  -webkit-mask-image: linear-gradient(to right, transparent 0%, #000 65%);
  mask-image: linear-gradient(to right, transparent 0%, #000 65%);
}
.actividades__foto-pila--der {
  right: 0;
  transform: translate(38%, -50%) scale(0.82);
  opacity: 0.45;
  -webkit-mask-image: linear-gradient(to left, transparent 0%, #000 65%);
  mask-image: linear-gradient(to left, transparent 0%, #000 65%);
}
.actividades__foto-enlace--multi:hover:not(:disabled) .actividades__foto-pila--izq {
  transform: translate(-58%, -50%) scale(0.82);
  opacity: 0.7;
}
.actividades__foto-enlace--multi:hover:not(:disabled) .actividades__foto-pila--der {
  transform: translate(58%, -50%) scale(0.82);
  opacity: 0.7;
}
.actividades__foto-conteo {
  position: absolute;
  z-index: 3;
  bottom: -0.15rem;
  right: -0.15rem;
  min-width: 1.05rem;
  height: 1.05rem;
  padding: 0 0.25rem;
  border-radius: 999px;
  background: var(--eca-green-600);
  color: #fff;
  font-size: 0.62rem;
  font-weight: 800;
  line-height: 1.05rem;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}
.actividades__foto--vacia,
.actividades__foto--cargando {
  color: var(--eca-ink-faint, #9aa1af);
  background: var(--eca-surface);
  border: 1px solid var(--eca-surface-border);
}
.actividades__foto--vacia svg,
.actividades__foto-spinner {
  width: 1.1rem;
  height: 1.1rem;
}
.actividades__foto-spinner {
  animation: eca-girar 0.9s linear infinite;
}

/* ---- Visor de fotos (lightbox) ---- */
.visor {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1.5rem;
  background: rgba(10, 15, 12, 0.82);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.visor-fondo-enter-active,
.visor-fondo-leave-active {
  transition: opacity 0.2s ease;
}
.visor-fondo-enter-from,
.visor-fondo-leave-to {
  opacity: 0;
}
.visor__lienzo {
  flex: 1;
  max-width: min(92vw, 900px);
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.visor__img {
  max-width: 100%;
  max-height: 82vh;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  object-fit: contain;
}
.visor-imagen-enter-active,
.visor-imagen-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.visor-imagen-enter-from {
  opacity: 0;
  transform: scale(0.98);
}
.visor-imagen-leave-to {
  opacity: 0;
}
.visor__estado {
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.95rem;
}
.visor__cerrar {
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
.visor__cerrar:hover {
  background: rgba(255, 255, 255, 0.28);
  transform: rotate(90deg);
}
.visor__cerrar svg {
  width: 1.1rem;
  height: 1.1rem;
}
.visor__contador {
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
.visor__nav {
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
.visor__nav:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.08);
}
.visor__nav svg {
  width: 1.3rem;
  height: 1.3rem;
}
@media (max-width: 640px) {
  .visor {
    padding: 0.6rem;
    gap: 0.25rem;
  }
  .visor__nav {
    width: 2.4rem;
    height: 2.4rem;
  }
  .visor__img {
    max-height: 74vh;
  }
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

/* ---- Modal de detalle (pedido explícito: ya no navega a otra vista) —
   fondo con blur, tarjeta con entrada tipo resorte y esquinas grandes,
   pantalla completa en móvil. ---- */
.actividades__modal-fondo {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(20, 24, 20, 0.45);
  backdrop-filter: blur(10px) saturate(1.4);
  -webkit-backdrop-filter: blur(10px) saturate(1.4);
}
.actividades-fondo-enter-active,
.actividades-fondo-leave-active {
  transition: opacity 0.25s ease;
}
.actividades-fondo-enter-from,
.actividades-fondo-leave-to {
  opacity: 0;
}

.actividades__modal {
  position: relative;
  width: 100%;
  max-width: 640px;
  max-height: 88vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 28px;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.35), 0 2px 8px rgba(0, 0, 0, 0.1);
}
.actividades__modal::-webkit-scrollbar {
  width: 8px;
}
.actividades__modal::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 10px;
}
.actividades-modal-enter-active {
  transition: opacity 0.35s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.actividades-modal-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.actividades-modal-enter-from {
  opacity: 0;
  transform: scale(0.92) translateY(18px);
}
.actividades-modal-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(10px);
}

.actividades__modal-cerrar {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 1;
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
.actividades__modal-cerrar:hover {
  transform: rotate(90deg) scale(1.08);
  background: #fff;
}
.actividades__modal-cerrar svg {
  width: 0.95rem;
  height: 0.95rem;
}

.actividades__modal-estado {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.7rem;
  padding: 4rem 2rem;
  color: var(--eca-ink-soft);
}
.actividades__modal-spinner {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  border: 3px solid var(--eca-surface-border);
  border-top-color: var(--eca-green-600);
  animation: eca-girar 0.8s linear infinite;
}

.actividades__modal-cabecera {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.6rem 0.9rem;
  padding: 1.5rem 3rem 1.5rem 1.75rem;
  border-radius: 28px 28px 0 0;
  background: linear-gradient(135deg, #4caf50 0%, #45a049 50%, #2e7d32 100%);
  color: #fff;
}
.actividades__modal-icono {
  flex-shrink: 0;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: var(--eca-r-sm);
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}
.actividades__modal-titulo {
  flex: 1;
  min-width: 140px;
}
.actividades__modal-cabecera .eca-badge {
  flex-shrink: 0;
}
.actividades__modal-titulo h2 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 800;
}
.actividades__modal-titulo p {
  margin: 0.15rem 0 0;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.8);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actividades__modal-cuerpo {
  padding: 1.5rem 1.75rem 1.75rem;
}
.actividades__modal-usuario {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-bottom: 1.1rem;
  padding-bottom: 1.1rem;
  border-bottom: 1px solid var(--eca-surface-border);
}
.actividades__modal-usuario div {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.actividades__modal-datos {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.55rem 1.3rem;
  margin: 0;
}
.actividades__modal-datos dt {
  color: var(--eca-ink-soft);
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.actividades__modal-datos dd {
  margin: 0;
}
.actividades__modal-btn-mapa {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.8rem;
  border: 1.5px solid #cfe3d5;
  border-radius: 999px;
  background: #fff;
  color: var(--eca-green-700, #2e7d32);
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease;
}
.actividades__modal-btn-mapa svg {
  width: 0.85rem;
  height: 0.85rem;
}
.actividades__modal-btn-mapa small {
  color: var(--eca-ink-soft);
  font-weight: 500;
  font-size: 0.72rem;
}
.actividades__modal-btn-mapa:hover {
  background: #eef6f0;
  border-color: var(--eca-green-500);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.18);
}
.actividades__modal-btn-mapa--activo {
  background: linear-gradient(135deg, #4caf50, #2e7d32);
  border-color: transparent;
  color: #fff;
}
.actividades__modal-btn-mapa--activo:hover {
  background: linear-gradient(135deg, #43a047, #256a2a);
  box-shadow: 0 4px 14px rgba(46, 125, 50, 0.3);
}
.actividades__modal-btn-mapa--activo small {
  color: rgba(255, 255, 255, 0.85);
}
.actividades__modal-sin-gps {
  color: var(--eca-ink-faint, #9aa1af);
  font-style: italic;
  font-size: 0.85rem;
}
.actividades__modal-mapa-seccion {
  overflow: hidden;
  margin-top: 0.75rem;
}
.actividades__modal-mapa {
  width: 100%;
  height: 15rem;
  border-radius: var(--eca-r-md);
  overflow: hidden;
  box-shadow: var(--eca-shadow-card);
}
.actividades-mapa-enter-active {
  transition: opacity 0.3s ease, max-height 0.35s cubic-bezier(0.34, 1.06, 0.64, 1);
}
.actividades-mapa-leave-active {
  transition: opacity 0.2s ease, max-height 0.25s ease;
}
.actividades-mapa-enter-from,
.actividades-mapa-leave-to {
  opacity: 0;
  max-height: 0;
}
.actividades-mapa-enter-to,
.actividades-mapa-leave-from {
  max-height: 16rem;
}

.actividades__modal-galeria-seccion {
  margin-top: 1.4rem;
}
.actividades__modal-galeria-seccion h3 {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0 0 0.9rem;
  color: var(--eca-purple-700);
  font-size: 0.95rem;
}
.actividades__modal-galeria-seccion h3 svg {
  width: 15px;
  height: 15px;
}
.actividades__modal-galeria {
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
}
.actividades__modal-foto {
  margin: 0;
  width: 150px;
}
.actividades__modal-foto img,
.actividades__modal-foto-cargando {
  width: 100%;
  height: 120px;
  object-fit: cover;
  border-radius: var(--eca-r-sm);
  box-shadow: var(--eca-shadow-card);
}
.actividades__modal-foto-cargando {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--eca-surface);
  color: var(--eca-ink-soft);
  font-size: 0.78rem;
}
.actividades__modal-foto figcaption {
  font-size: 0.75rem;
  margin-top: 0.3rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  word-break: break-all;
}
.actividades__modal-foto figcaption .eca-btn {
  padding: 0.3rem 0.6rem;
  font-size: 0.75rem;
}

@media (max-width: 640px) {
  .actividades__modal-fondo {
    padding: 0;
    align-items: flex-end;
  }
  .actividades__modal {
    max-width: 100%;
    max-height: 92vh;
    border-radius: 24px 24px 0 0;
  }
  .actividades-modal-enter-from,
  .actividades-modal-leave-to {
    transform: translateY(100%);
  }
  .actividades__modal-cabecera {
    border-radius: 24px 24px 0 0;
  }
}
</style>
