<!-- admin-eca — pantalla "Geografía" (ECA-006).
     Árbol estado→municipios, buscador, toggle `activo`. Edición requiere
     `geo.gestionar`; sin ese permiso los toggles quedan deshabilitados
     (el backend igual rechaza el PATCH con 403 si alguien lo forza). -->
<script setup>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import {
  listarEstados,
  listarMunicipios,
  actualizarEstadoActivo,
  actualizarMunicipioActivo,
} from '../services/geoService'
import { listarEcas } from '../services/ecasService'
import AuthIcon from '../components/auth/AuthIcon.vue'

const auth = useAuthStore()
const puedeEditar = computed(() => auth.tienePermiso('geo.gestionar'))

const estados = ref([])
const estadoSeleccionadoId = ref(null)
const municipios = ref([])
const busqueda = ref('')
const busquedaEstados = ref('')
const cargandoEstados = ref(false)
const cargandoMunicipios = ref(false)
const error = ref('')

const estadoSeleccionado = computed(() => estados.value.find((e) => e.id === estadoSeleccionadoId.value) || null)
const estadosFiltrados = computed(() => {
  const texto = busquedaEstados.value.trim().toLowerCase()
  if (!texto) return estados.value
  return estados.value.filter((e) => e.nombre.toLowerCase().includes(texto))
})
const municipiosActivosCount = computed(() => municipios.value.filter((m) => m.activo).length)

// Mapa (mismo Mapbox GL que el Visor de Seguimiento de admin-pwa, cargado
// por CDN en `index.html`): pinta las ECA que ya tienen coordenadas
// capturadas. Es un complemento visual sobre las mismas listas de arriba
// — nunca bloquea el flujo de activar/desactivar estados/municipios si
// falla (sin token, sin red, etc.).
const mapaContenedor = ref(null)
const mapaListo = ref(false)
const mapaError = ref('')
const cargandoEcasMapa = ref(false)
const ecasConCoordenadas = ref([])
let mapa = null
let marcadores = []

const CENTRO_MEXICO = [-99.1332, 23.6345]

const ecasVisiblesEnMapa = computed(() =>
  estadoSeleccionadoId.value
    ? ecasConCoordenadas.value.filter((e) => e.estado_id === estadoSeleccionadoId.value)
    : ecasConCoordenadas.value,
)

async function cargarEstados() {
  cargandoEstados.value = true
  error.value = ''
  try {
    estados.value = await listarEstados()
  } catch (err) {
    error.value = 'No se pudieron cargar los estados.'
  } finally {
    cargandoEstados.value = false
  }
}

async function seleccionarEstado(estadoId) {
  estadoSeleccionadoId.value = estadoId
  await cargarMunicipios()
}

async function cargarMunicipios() {
  if (!estadoSeleccionadoId.value) {
    municipios.value = []
    return
  }
  cargandoMunicipios.value = true
  error.value = ''
  try {
    municipios.value = await listarMunicipios(estadoSeleccionadoId.value, {
      q: busqueda.value || undefined,
    })
  } catch (err) {
    error.value = 'No se pudieron cargar los municipios.'
  } finally {
    cargandoMunicipios.value = false
  }
}

async function alternarEstado(estado) {
  if (!puedeEditar.value) return
  try {
    const actualizado = await actualizarEstadoActivo(estado.id, !estado.activo)
    estado.activo = actualizado.activo
  } catch (err) {
    error.value = 'No se pudo actualizar el estado.'
  }
}

async function alternarMunicipio(municipio) {
  if (!puedeEditar.value) return
  try {
    const actualizado = await actualizarMunicipioActivo(municipio.id, !municipio.activo)
    municipio.activo = actualizado.activo
  } catch (err) {
    error.value = 'No se pudo actualizar el municipio.'
  }
}

let temporizadorBusqueda = null
function onBuscar() {
  clearTimeout(temporizadorBusqueda)
  temporizadorBusqueda = setTimeout(cargarMunicipios, 300)
}

async function cargarEcasParaMapa() {
  cargandoEcasMapa.value = true
  try {
    // `page_size` alto en una sola pasada: el catálogo de ECA de este
    // proyecto no se acerca al volumen donde hiciera falta paginar solo
    // para pintar el mapa (a diferencia del listado de la vista "ECA",
    // que sí pagina server-side para su tabla).
    const { resultados } = await listarEcas({ pageSize: 2000 })
    ecasConCoordenadas.value = resultados.filter((e) => e.latitud != null && e.longitud != null)
  } catch {
    // El mapa es un complemento visual — si falla, las listas de
    // estados/municipios de arriba siguen funcionando igual.
    ecasConCoordenadas.value = []
  } finally {
    cargandoEcasMapa.value = false
  }
}

function limpiarMarcadores() {
  marcadores.forEach((marcador) => marcador.remove())
  marcadores = []
}

function pintarMarcadores() {
  if (!mapa || !mapaListo.value) return
  limpiarMarcadores()
  const lista = ecasVisiblesEnMapa.value
  if (!lista.length) return

  const bounds = new window.mapboxgl.LngLatBounds()
  lista.forEach((eca) => {
    const popup = new window.mapboxgl.Popup({ offset: 16, closeButton: false }).setHTML(
      `<strong>${eca.nombre}</strong><br>${eca.activo ? 'Activa' : 'Inactiva'}${
        eca.localidad_nombre ? `<br>${eca.localidad_nombre}` : ''
      }`,
    )
    const marcador = new window.mapboxgl.Marker({ color: eca.activo ? '#2e7d32' : '#9ca3af' })
      .setLngLat([eca.longitud, eca.latitud])
      .setPopup(popup)
      .addTo(mapa)
    marcadores.push(marcador)
    bounds.extend([eca.longitud, eca.latitud])
  })

  if (lista.length === 1) {
    mapa.flyTo({ center: [lista[0].longitud, lista[0].latitud], zoom: 11, duration: 600 })
  } else {
    mapa.fitBounds(bounds, { padding: 48, maxZoom: 12, duration: 600 })
  }
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
  })
  mapa.on('error', () => {
    mapaError.value = 'No se pudo cargar el mapa. Revisa el token de Mapbox.'
  })
}

function verTodoElPais() {
  estadoSeleccionadoId.value = null
  municipios.value = []
}

watch(ecasVisiblesEnMapa, pintarMarcadores)

onMounted(async () => {
  cargarEstados()
  await cargarEcasParaMapa()
  iniciarMapa()
})

onBeforeUnmount(() => {
  limpiarMarcadores()
  mapa?.remove()
  mapa = null
})
</script>

<template>
  <section>
    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="map" /></span>
      <div class="eca-page-header__texto">
        <h1>Geografía</h1>
        <p>Estados y municipios habilitados para el registro de ECAs.</p>
      </div>
    </div>
    <div class="eca-card eca-panel-fusionado geografia">
    <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>

    <div class="geografia__layout">
      <div class="geografia__columna">
        <div class="geografia__columna-cabecera">
          <h2>Estados <span class="eca-badge eca-badge--verde">{{ estados.length }}</span></h2>
        </div>
        <label class="eca-search geografia__buscador">
          <AuthIcon name="search" />
          <input v-model="busquedaEstados" type="search" placeholder="Buscar estado…" />
        </label>

        <p v-if="cargandoEstados" class="eca-ayuda">Cargando…</p>
        <div v-else-if="!estadosFiltrados.length" class="eca-vacio geografia__vacio">
          <AuthIcon name="map" />
          <p>Ningún estado coincide con la búsqueda.</p>
        </div>
        <ul v-else class="geografia__lista">
          <li
            v-for="estado in estadosFiltrados"
            :key="estado.id"
            class="geografia__fila"
            :class="{ 'geografia__fila--activa': estado.id === estadoSeleccionadoId }"
          >
            <button type="button" class="geografia__fila-boton" @click="seleccionarEstado(estado.id)">
              <span class="geografia__fila-nombre">{{ estado.nombre }}</span>
              <span class="eca-badge" :class="estado.activo ? 'eca-badge--verde' : 'eca-badge--gris'">
                {{ estado.activo ? 'Activo' : 'Inactivo' }}
              </span>
            </button>
            <label class="geografia__switch" :class="{ 'geografia__switch--deshabilitado': !puedeEditar }">
              <input
                type="checkbox"
                :checked="estado.activo"
                :disabled="!puedeEditar"
                @change="alternarEstado(estado)"
              />
              <span class="geografia__switch-riel"></span>
            </label>
          </li>
        </ul>
      </div>

      <div class="geografia__columna">
        <div class="geografia__columna-cabecera">
          <h2>
            Municipios
            <span v-if="estadoSeleccionadoId" class="eca-badge eca-badge--verde">{{ municipiosActivosCount }}/{{ municipios.length }}</span>
          </h2>
          <span v-if="estadoSeleccionado" class="geografia__columna-subtitulo">{{ estadoSeleccionado.nombre }}</span>
        </div>
        <label class="eca-search geografia__buscador">
          <AuthIcon name="search" />
          <input
            v-model="busqueda"
            type="search"
            placeholder="Buscar municipio…"
            :disabled="!estadoSeleccionadoId"
            @input="onBuscar"
          />
        </label>

        <div v-if="!estadoSeleccionadoId" class="eca-vacio geografia__vacio">
          <AuthIcon name="map-pin" />
          <p>Elige un estado de la lista para ver sus municipios.</p>
        </div>
        <p v-else-if="cargandoMunicipios" class="eca-ayuda">Cargando…</p>
        <div v-else-if="municipios.length === 0" class="eca-vacio geografia__vacio">
          <AuthIcon name="map-pin" />
          <p>Sin municipios para este estado todavía.</p>
        </div>
        <ul v-else class="geografia__lista">
          <li v-for="municipio in municipios" :key="municipio.id" class="geografia__fila">
            <span class="geografia__fila-boton geografia__fila-boton--estatico">
              <span class="geografia__fila-nombre">{{ municipio.nombre }}</span>
              <span class="eca-badge" :class="municipio.activo ? 'eca-badge--verde' : 'eca-badge--gris'">
                {{ municipio.activo ? 'Activo' : 'Inactivo' }}
              </span>
            </span>
            <label class="geografia__switch" :class="{ 'geografia__switch--deshabilitado': !puedeEditar }">
              <input
                type="checkbox"
                :checked="municipio.activo"
                :disabled="!puedeEditar"
                @change="alternarMunicipio(municipio)"
              />
              <span class="geografia__switch-riel"></span>
            </label>
          </li>
        </ul>
      </div>

      <div class="geografia__mapa-panel">
        <div class="geografia__mapa-cabecera">
          <h2>
            Mapa de ECA
            <span class="eca-badge eca-badge--verde">{{ ecasVisiblesEnMapa.length }}</span>
          </h2>
          <button
            v-if="estadoSeleccionadoId"
            type="button"
            class="eca-btn eca-btn-secundario geografia__mapa-reset"
            @click="verTodoElPais"
          >
            Ver todo el país
          </button>
        </div>
        <p class="eca-ayuda geografia__mapa-ayuda">
          {{
            estadoSeleccionadoId
              ? 'ECA con coordenadas capturadas en el estado seleccionado.'
              : 'ECA con coordenadas capturadas en todo el país. Elige un estado para acercar el mapa.'
          }}
        </p>
        <p v-if="mapaError" class="eca-alerta-error" role="alert">{{ mapaError }}</p>
        <div class="geografia__mapa-contenedor">
          <div ref="mapaContenedor" class="geografia__mapa"></div>
          <div v-if="cargandoEcasMapa || !mapaListo" class="geografia__mapa-cargando">
            <AuthIcon name="sync" class="geografia__mapa-spinner" />
            <span>Cargando mapa…</span>
          </div>
        </div>
      </div>
    </div>
    </div>
  </section>
</template>

<style scoped>
.geografia {
  margin-top: 0.5rem;
}
.geografia__layout {
  margin-top: 1rem;
  display: grid;
  grid-template-columns: 220px 240px 1fr;
  gap: 1.25rem;
  align-items: start;
}
@media (max-width: 900px) {
  .geografia__layout {
    grid-template-columns: 1fr 1fr;
  }
  .geografia__mapa-panel {
    grid-column: 1 / -1;
  }
}
@media (max-width: 560px) {
  .geografia__layout {
    grid-template-columns: 1fr;
  }
}
.geografia__columna {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.geografia__columna-cabecera {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.6rem;
}
.geografia__columna-cabecera h2 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.95rem;
}
.geografia__columna-subtitulo {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--eca-purple-700);
  background: #ede9fe;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
}
.geografia__buscador {
  margin-bottom: 0.7rem;
}
.geografia__vacio {
  padding: 1.75rem 1rem;
}

.geografia__lista {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 55vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
/* Scrollbar discreto: mismo criterio que el resto del panel — visible
   solo al pasar el mouse, sin la barra gris por defecto del navegador
   ocupando espacio todo el tiempo. */
.geografia__lista::-webkit-scrollbar {
  width: 6px;
}
.geografia__lista::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 6px;
}

.geografia__fila {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.15rem;
  border-radius: var(--eca-r-md);
  border: 1px solid var(--eca-surface-border);
  background: #fff;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}
.geografia__fila:hover {
  border-color: var(--eca-green-500);
  background: #f4fbf6;
}
.geografia__fila--activa {
  border-color: var(--eca-green-600);
  background: linear-gradient(135deg, #eafcf0 0%, #f4fbf6 100%);
  box-shadow: 0 4px 12px rgba(21, 128, 61, 0.12);
}
.geografia__fila-boton {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  padding: 0.55rem 0.6rem;
  font: inherit;
  color: inherit;
  border-radius: var(--eca-r-sm);
}
.geografia__fila-boton--estatico {
  cursor: default;
}
.geografia__fila-nombre {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--eca-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.geografia__fila--activa .geografia__fila-nombre {
  color: var(--eca-green-700);
}

/* Switch tipo "pill" — mismo lenguaje visual que los toggles de
   admin-pwa, en vez del checkbox nativo diminuto que había antes. */
.geografia__switch {
  position: relative;
  width: 2.5rem;
  height: 1.4rem;
  flex-shrink: 0;
  margin-right: 0.6rem;
  cursor: pointer;
}
.geografia__switch input {
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
}
.geografia__switch-riel {
  position: absolute;
  inset: 0;
  background: #d1d5db;
  border-radius: 999px;
  transition: background 0.2s ease;
}
.geografia__switch-riel::before {
  content: '';
  position: absolute;
  width: 1.1rem;
  height: 1.1rem;
  left: 0.15rem;
  top: 50%;
  transform: translateY(-50%);
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  transition: transform 0.2s ease;
}
.geografia__switch input:checked + .geografia__switch-riel {
  background: linear-gradient(135deg, var(--eca-green-500), var(--eca-green-700));
}
.geografia__switch input:checked + .geografia__switch-riel::before {
  transform: translate(1.1rem, -50%);
}
.geografia__switch--deshabilitado {
  cursor: not-allowed;
  opacity: 0.55;
}

.geografia__mapa-panel {
  min-width: 0;
}
.geografia__mapa-cabecera {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  flex-wrap: wrap;
}
.geografia__mapa-cabecera h2 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.geografia__mapa-reset {
  padding: 0.4rem 0.8rem;
  font-size: 0.8rem;
}
.geografia__mapa-ayuda {
  margin: 0.2rem 0 0.7rem;
}
.geografia__mapa-contenedor {
  position: relative;
  height: 60vh;
  min-height: 320px;
  border-radius: var(--eca-r-md);
  overflow: hidden;
  border: 1px solid var(--eca-surface-border);
}
.geografia__mapa {
  width: 100%;
  height: 100%;
}
.geografia__mapa-cargando {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: rgba(245, 246, 251, 0.85);
  color: var(--eca-ink-soft);
  font-size: 0.9rem;
}
.geografia__mapa-spinner {
  width: 1.1rem;
  height: 1.1rem;
  animation: eca-girar 0.9s linear infinite;
}
/* Popups de Mapbox: la librería inyecta su propio CSS global (no scoped),
   así que se ajustan aquí con :deep para que combinen con el resto del
   panel en vez de quedarse con la tipografía por defecto del navegador. */
:deep(.mapboxgl-popup-content) {
  font-family: inherit;
  font-size: 0.82rem;
  padding: 0.6rem 0.8rem;
  border-radius: var(--eca-r-sm);
}
</style>
