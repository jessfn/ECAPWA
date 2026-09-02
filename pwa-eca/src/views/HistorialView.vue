<!-- pwa-eca — pantalla "Historial" (ECA-019). Rediseño pedido explícito:
     mismo lenguaje visual que el historial de pwasuper — pestañas
     "Registros" (jornadas de inicio/salida) y "Actividades", agrupadas
     por fecha con un separador tipo "píldora" con ícono de calendario,
     tarjetas con íconos profesionales (AuthIcon, sin emojis) y estado
     vacío con llamada a la acción. Sigue combinando lo local (outbox)
     con lo del servidor — el indicador "sin sincronizar" se calcula del
     `estado_local` del outbox, nunca de una columna de la BD (§2.3). -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { listar } from '../services/outbox'
import { listarMisActividades } from '../services/actividadesService'
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

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    catalogos.value = await obtenerCatalogos()
    await Promise.all([cargarJornadas(), cargarActividades()])
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
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
              v-bind="nombresDe(item.actividad)"
            />
          </section>
        </div>
      </template>
    </div>
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
</style>
