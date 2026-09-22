<!-- pwa-eca — pantalla "Historial" (ECA-019). Rediseño pedido explícito:
     mismo lenguaje visual que el historial de pwasuper — pestañas
     "Registros" (jornadas de inicio/salida) y "Actividades", agrupadas
     por fecha con un separador tipo "píldora" con ícono de calendario,
     tarjetas con íconos profesionales (AuthIcon, sin emojis) y estado
     vacío con llamada a la acción. Sigue combinando lo local (outbox)
     con lo del servidor — el indicador "sin sincronizar" se calcula del
     `estado_local` del outbox, nunca de una columna de la BD (§2.3). -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { RouterLink } from 'vue-router'
import { listar } from '../services/outbox'
import { listarMisActividades, obtenerActividad, urlVistaPreviaEvidencia } from '../services/actividadesService'
import { listarMisJornadas } from '../services/jornadasService'
import { obtenerCatalogos, nombrePorId } from '../services/catalogosCache'
import { useConectividad } from '../services/conectividad'
import ActividadCard from '../components/ActividadCard.vue'
import HistorialJornadaCard from '../components/HistorialJornadaCard.vue'
import BackButton from '../components/BackButton.vue'
import AuthIcon from '../components/auth/AuthIcon.vue'

const { enLinea } = useConectividad()
const pestana = ref('registros') // 'registros' | 'actividades'
const jornadas = ref([])
const actividades = ref([])
// Pedido explícito: una foto que no llegó al servidor no debe desaparecer
// en silencio — antes solo se veía entrando a la pantalla de
// "Sincronización" (genérica, sin relacionarla con la actividad). Aquí se
// cruza `outbox_evidencias` por `actividad_uuid` para que la propia
// tarjeta de la actividad avise si le falta o le fue rechazada una foto,
// sin importar si la actividad en sí ya se sincronizó.
const evidenciasPorActividad = ref(new Map())
// Pedido explícito: que en Historial > Actividades aparezcan las fotos que
// se van subiendo. Miniatura por actividad (`actividad_uuid -> Object URL`)
// — se arma PRIMERO desde el propio dispositivo (`outbox_evidencias`, que
// conserva el archivo hasta 30 días después de sincronizado, ver
// `services/outbox.js: purgar`) y solo se pide al servidor si no hay nada
// local (actividad sincronizada hace tiempo desde otro dispositivo, o ya
// purgada). Así casi nunca depende de la red.
const vistasPrevias = ref({})
const catalogos = ref(null)
const cargando = ref(false)
const error = ref('')

function claveFechaLocal(iso) {
  return new Date(iso).toLocaleDateString('en-CA')
}
function tituloFecha(iso) {
  const texto = new Date(iso).toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}

// Agrupa una lista ya ordenada (más reciente primero) en bloques por
// fecha local — mismo patrón que el separador "píldora" del historial
// de pwasuper, sin usar "Hoy"/"Ayer": siempre la fecha completa.
function agruparPorFecha(items, obtenerIso) {
  const grupos = []
  let claveActual = null
  for (const item of items) {
    const iso = obtenerIso(item)
    const clave = claveFechaLocal(iso)
    if (clave !== claveActual) {
      grupos.push({ clave, titulo: tituloFecha(iso), items: [] })
      claveActual = clave
    }
    grupos[grupos.length - 1].items.push(item)
  }
  return grupos
}

const gruposJornadas = computed(() => agruparPorFecha(jornadas.value, (j) => j.inicio_en))
const gruposActividades = computed(() => agruparPorFecha(actividades.value, (a) => a.actividad.fecha_hora))

function nombresDe(actividad) {
  if (!catalogos.value) return { modalidadNombre: null, tipoActividadNombre: null }
  return {
    modalidadNombre: nombrePorId(catalogos.value.modalidades, actividad.modalidad_id),
    tipoActividadNombre: nombrePorId(catalogos.value.tiposActividad, actividad.tipo_actividad_id),
  }
}

function gpsDeRemota(lat, lon, precision, estado) {
  if (lat == null && lon == null && !estado) return null
  return { latitud: lat, longitud: lon, precision_gps_m: precision, estado_gps: estado }
}

async function cargarJornadas() {
  const locales = await listar('outbox_jornadas')
  const porUuid = new Map()
  for (const local of locales) porUuid.set(local.uuid, local)

  if (enLinea.value) {
    try {
      const remotas = await listarMisJornadas()
      for (const remota of remotas) {
        porUuid.set(remota.uuid, {
          ...remota,
          gps_inicio: gpsDeRemota(remota.latitud_inicio, remota.longitud_inicio, remota.precision_gps_inicio_m, remota.estado_gps_inicio),
          gps_fin: remota.fin_en
            ? gpsDeRemota(remota.latitud_fin, remota.longitud_fin, remota.precision_gps_fin_m, remota.estado_gps_fin)
            : null,
        })
      }
    } catch {
      error.value = 'No se pudo consultar el historial del servidor; se muestra lo guardado en el dispositivo.'
    }
  }

  jornadas.value = [...porUuid.values()].sort((a, b) => new Date(b.inicio_en) - new Date(a.inicio_en))
}

async function cargarActividades() {
  const locales = await listar('outbox_actividades')
  const porUuid = new Map()
  for (const local of locales) {
    porUuid.set(local.uuid, { actividad: local, estadoSincronizacion: local.estado_local })
  }

  if (enLinea.value) {
    try {
      const { resultados } = await listarMisActividades({ page_size: 100 })
      for (const remota of resultados) {
        porUuid.set(remota.uuid, { actividad: remota, estadoSincronizacion: 'SINCRONIZADO' })
      }
    } catch {
      error.value = 'No se pudo consultar el historial del servidor; se muestra lo guardado en el dispositivo.'
    }
  }

  actividades.value = [...porUuid.values()].sort(
    (a, b) => new Date(b.actividad.fecha_hora) - new Date(a.actividad.fecha_hora),
  )
}

function limpiarVistasPrevias() {
  for (const url of Object.values(vistasPrevias.value)) URL.revokeObjectURL(url)
  vistasPrevias.value = {}
}

async function cargarEvidencias() {
  const locales = await listar('outbox_evidencias')
  const mapa = new Map()
  const primeraLocalPorActividad = new Map() // actividad_uuid -> registro con menor `orden`
  for (const e of locales) {
    const actual = mapa.get(e.actividad_uuid) || { rechazadas: 0, pendientes: 0, ultimoError: null }
    if (e.estado_local === 'RECHAZADO') {
      actual.rechazadas += 1
      actual.ultimoError = actual.ultimoError || e.ultimo_error
    } else if (e.estado_local === 'PENDIENTE' || e.estado_local === 'SINCRONIZANDO') {
      actual.pendientes += 1
    }
    mapa.set(e.actividad_uuid, actual)

    const previa = primeraLocalPorActividad.get(e.actividad_uuid)
    if (!previa || e.orden < previa.orden) primeraLocalPorActividad.set(e.actividad_uuid, e)
  }
  evidenciasPorActividad.value = mapa

  // Miniaturas locales: se reconstruye el Blob desde los bytes guardados
  // (`archivo_buffer`, el formato durable — ver `stores/actividad.js`) o,
  // para registros más viejos, el `archivo` (Blob) tal cual.
  for (const [actividadUuid, evidencia] of primeraLocalPorActividad) {
    const blob = evidencia.archivo_buffer
      ? new Blob([evidencia.archivo_buffer], { type: evidencia.archivo_mime || 'image/jpeg' })
      : evidencia.archivo
    if (blob) vistasPrevias.value[actividadUuid] = URL.createObjectURL(blob)
  }
}

// Para actividades sin ninguna evidencia local (sincronizadas hace tiempo
// desde otro dispositivo, o ya purgadas) se pide la miniatura al servidor
// — mejor esfuerzo, en paralelo, sin bloquear el resto de la pantalla.
function cargarVistasPreviasRemotas() {
  if (!enLinea.value) return
  for (const item of actividades.value) {
    const uuid = item.actividad.uuid
    const evidenciaId = item.actividad.primera_evidencia_id
    if (vistasPrevias.value[uuid] || !evidenciaId) continue
    urlVistaPreviaEvidencia(evidenciaId)
      .then((url) => {
        vistasPrevias.value = { ...vistasPrevias.value, [uuid]: url }
      })
      .catch(() => {})
  }
}

async function cargar() {
  cargando.value = true
  error.value = ''
  limpiarVistasPrevias()
  try {
    catalogos.value = await obtenerCatalogos()
    await Promise.all([cargarJornadas(), cargarActividades(), cargarEvidencias()])
    cargarVistasPreviasRemotas()
  } finally {
    cargando.value = false
  }
}

function onTeclaVisor(evento) {
  if (!visorAbierto.value) return
  if (evento.key === 'Escape') cerrarVisor()
  if (visorFotos.value.length > 1) {
    if (evento.key === 'ArrowRight') fotoSiguiente()
    if (evento.key === 'ArrowLeft') fotoAnterior()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onTeclaVisor)
  cargar()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onTeclaVisor)
  limpiarVistasPrevias()
  limpiarVisor()
})

// ---- Visor de fotos (lightbox) — pedido explícito: poder ver las fotos
// que se van subiendo, no solo una miniatura chica. Al tocar la miniatura
// se piden TODAS las evidencias de esa actividad (detalle completo) y se
// navega entre ellas, mismo patrón que ya usa admin-eca. ----
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

async function abrirFotos(item) {
  const actividad = item.actividad
  visorAbierto.value = true
  visorCargando.value = true
  visorError.value = ''
  visorIndice.value = 0
  limpiarVisor()
  try {
    // Local primero (sin red, siempre disponible mientras no se purgue):
    // todas las evidencias de esa actividad que sigan en el outbox.
    const locales = (await listar('outbox_evidencias'))
      .filter((e) => e.actividad_uuid === actividad.uuid)
      .sort((a, b) => a.orden - b.orden)

    if (locales.length) {
      visorFotos.value = locales.map((e) => {
        const blob = e.archivo_buffer
          ? new Blob([e.archivo_buffer], { type: e.archivo_mime || 'image/jpeg' })
          : e.archivo
        return { id: e.uuid, url: blob ? URL.createObjectURL(blob) : null }
      })
    } else if (item.estadoSincronizacion === 'SINCRONIZADO' && navigator.onLine) {
      // Sin nada local: se pide el detalle completo al servidor.
      const detalle = await obtenerActividad(actividad.uuid)
      const evidencias = detalle.evidencias || []
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
    }
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
}
function fotoSiguiente() {
  if (!visorFotos.value.length) return
  visorIndice.value = (visorIndice.value + 1) % visorFotos.value.length
}
function fotoAnterior() {
  if (!visorFotos.value.length) return
  visorIndice.value = (visorIndice.value - 1 + visorFotos.value.length) % visorFotos.value.length
}
</script>

<template>
  <main class="eca-contenido">
    <BackButton class="eca-entrar" />

    <div class="eca-card eca-entrar" style="--eca-delay: 0.06s">
      <h1 class="eca-titulo">Historial</h1>
      <p class="eca-ayuda">Tus registros y actividades, guardados en el dispositivo y en el servidor.</p>

      <div class="historial__tabs" role="tablist">
        <button
          type="button"
          role="tab"
          class="historial__tab"
          :class="{ 'historial__tab--activa historial__tab--registros': pestana === 'registros' }"
          @click="pestana = 'registros'"
        >
          <AuthIcon name="login" /> Registros
        </button>
        <button
          type="button"
          role="tab"
          class="historial__tab"
          :class="{ 'historial__tab--activa historial__tab--actividades': pestana === 'actividades' }"
          @click="pestana = 'actividades'"
        >
          <AuthIcon name="briefcase" /> Actividades
        </button>
      </div>

      <p v-if="error" class="eca-alerta-aviso">{{ error }}</p>
      <p v-if="cargando" class="eca-ayuda">Cargando…</p>

      <template v-else-if="pestana === 'registros'">
        <div v-if="!jornadas.length" class="historial__vacio">
          <AuthIcon name="clock" />
          <p>Aún no tienes registros de jornada</p>
          <span>Marca tu inicio de jornada para verlo aquí.</span>
          <RouterLink :to="{ name: 'jornada' }" class="eca-btn eca-btn-secundario">Ir a Jornada</RouterLink>
        </div>
        <div v-else class="historial__grupos">
          <section v-for="grupo in gruposJornadas" :key="grupo.clave" class="historial__grupo">
            <div class="historial__separador historial__separador--registros">
              <span class="historial__separador-linea"></span>
              <span class="historial__separador-pildora">
                <AuthIcon name="calendar" /> {{ grupo.titulo }}
              </span>
              <span class="historial__separador-linea"></span>
            </div>
            <HistorialJornadaCard v-for="j in grupo.items" :key="j.uuid" :jornada="j" />
          </section>
        </div>
      </template>

      <template v-else>
        <div v-if="!actividades.length" class="historial__vacio">
          <AuthIcon name="briefcase" />
          <p>Aún no tienes actividades registradas</p>
          <span>Crea tu primera actividad para verla aquí.</span>
          <RouterLink :to="{ name: 'nueva-actividad' }" class="eca-btn eca-btn-secundario">Nueva actividad</RouterLink>
        </div>
        <div v-else class="historial__grupos">
          <section v-for="grupo in gruposActividades" :key="grupo.clave" class="historial__grupo">
            <div class="historial__separador historial__separador--actividades">
              <span class="historial__separador-linea"></span>
              <span class="historial__separador-pildora">
                <AuthIcon name="calendar" /> {{ grupo.titulo }}
              </span>
              <span class="historial__separador-linea"></span>
            </div>
            <ActividadCard
              v-for="item in grupo.items"
              :key="item.actividad.uuid"
              :actividad="item.actividad"
              :estado-sincronizacion="item.estadoSincronizacion"
              :evidencias-estado="evidenciasPorActividad.get(item.actividad.uuid)"
              :foto-previa="vistasPrevias[item.actividad.uuid]"
              v-bind="nombresDe(item.actividad)"
              @ver-fotos="abrirFotos(item)"
            />
          </section>
        </div>
      </template>
    </div>

    <!-- ============ Visor de fotos (lightbox) ============ -->
    <Teleport to="body">
      <Transition name="historial-visor-fondo">
        <div v-if="visorAbierto" class="historial-visor" @click.self="cerrarVisor">
          <button type="button" class="historial-visor__cerrar" aria-label="Cerrar" @click="cerrarVisor">
            <AuthIcon name="close" />
          </button>

          <span v-if="visorFotos.length > 1" class="historial-visor__contador">
            {{ visorIndice + 1 }} / {{ visorFotos.length }}
          </span>

          <button
            v-if="visorFotos.length > 1"
            type="button"
            class="historial-visor__nav historial-visor__nav--prev"
            aria-label="Anterior"
            @click="fotoAnterior"
          >
            <AuthIcon name="chevron-left" />
          </button>

          <div class="historial-visor__lienzo">
            <p v-if="visorCargando" class="historial-visor__estado">Cargando…</p>
            <p v-else-if="visorError" class="historial-visor__estado">{{ visorError }}</p>
            <Transition v-else name="historial-visor-imagen" mode="out-in">
              <img
                v-if="visorFotos[visorIndice]?.url"
                :key="visorFotos[visorIndice].id"
                :src="visorFotos[visorIndice].url"
                alt="Evidencia"
                class="historial-visor__img"
              />
              <p v-else key="cargando-img" class="historial-visor__estado">Cargando imagen…</p>
            </Transition>
          </div>

          <button
            v-if="visorFotos.length > 1"
            type="button"
            class="historial-visor__nav historial-visor__nav--next"
            aria-label="Siguiente"
            @click="fotoSiguiente"
          >
            <AuthIcon name="chevron-right" />
          </button>
        </div>
      </Transition>
    </Teleport>
  </main>
</template>

<style scoped>
.historial__tabs {
  display: flex;
  gap: 0.4rem;
  background: var(--eca-surface);
  border-radius: 999px;
  padding: 0.3rem;
  margin: 0.85rem 0;
}
.historial__tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.55rem 0.6rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--eca-ink-soft);
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.25s ease, color 0.25s ease;
}
.historial__tab svg {
  width: 15px;
  height: 15px;
}
.historial__tab--activa {
  background: #fff;
  box-shadow: 0 2px 8px rgba(2, 20, 10, 0.12);
}
.historial__tab--registros.historial__tab--activa {
  color: #0a84ff;
}
.historial__tab--actividades.historial__tab--activa {
  color: #9333ea;
}

.historial__grupos {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.historial__grupo {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.historial__separador {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0.6rem 0 0.1rem;
}
.historial__separador-linea {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, currentColor, transparent);
  opacity: 0.35;
}
.historial__separador-pildora {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.25rem 0.7rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  white-space: nowrap;
  text-transform: capitalize;
}
.historial__separador-pildora svg {
  width: 12px;
  height: 12px;
}
.historial__separador--registros {
  color: #0a84ff;
}
.historial__separador--registros .historial__separador-pildora {
  background: rgba(10, 132, 255, 0.1);
  border: 1px solid rgba(10, 132, 255, 0.25);
}
.historial__separador--actividades {
  color: #9333ea;
}
.historial__separador--actividades .historial__separador-pildora {
  background: rgba(147, 51, 234, 0.1);
  border: 1px solid rgba(147, 51, 234, 0.25);
}

.historial__vacio {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  text-align: center;
  padding: 2rem 1rem;
  color: var(--eca-ink-faint);
}
.historial__vacio svg {
  width: 2.2rem;
  height: 2.2rem;
  opacity: 0.6;
}
.historial__vacio p {
  margin: 0.2rem 0 0;
  font-weight: 700;
  color: var(--eca-ink-soft);
}
.historial__vacio span {
  font-size: 0.82rem;
  margin-bottom: 0.5rem;
}

/* ---- Visor de fotos (lightbox) ---- */
.historial-visor {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1.25rem;
  background: rgba(10, 15, 12, 0.9);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.historial-visor-fondo-enter-active,
.historial-visor-fondo-leave-active {
  transition: opacity 0.2s ease;
}
.historial-visor-fondo-enter-from,
.historial-visor-fondo-leave-to {
  opacity: 0;
}
.historial-visor__lienzo {
  flex: 1;
  max-width: min(92vw, 700px);
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.historial-visor__img {
  max-width: 100%;
  max-height: 80vh;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  object-fit: contain;
}
.historial-visor-imagen-enter-active,
.historial-visor-imagen-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.historial-visor-imagen-enter-from {
  opacity: 0;
  transform: scale(0.98);
}
.historial-visor-imagen-leave-to {
  opacity: 0;
}
.historial-visor__estado {
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.95rem;
}
.historial-visor__cerrar {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 1;
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
}
.historial-visor__cerrar svg {
  width: 1.1rem;
  height: 1.1rem;
}
.historial-visor__contador {
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
.historial-visor__nav {
  flex-shrink: 0;
  width: 2.8rem;
  height: 2.8rem;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.historial-visor__nav svg {
  width: 1.2rem;
  height: 1.2rem;
}
@media (max-width: 640px) {
  .historial-visor {
    padding: 0.6rem;
    gap: 0.25rem;
  }
  .historial-visor__nav {
    width: 2.3rem;
    height: 2.3rem;
  }
  .historial-visor__img {
    max-height: 72vh;
  }
}
</style>
