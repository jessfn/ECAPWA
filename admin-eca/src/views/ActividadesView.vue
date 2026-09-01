<!-- admin-eca — pantalla "Actividades" (ECA-019): consulta con filtros +
     exportación CSV. No filtra por "estado de sincronización" — eso no
     existe en la BD (§2.3); solo ofrece rangos por fecha (`fecha_hora`). -->
<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { listarEstados, listarMunicipios } from '../services/geoService'
import { listarCatalogo } from '../services/catalogosService'
import { listarActividades, exportarCsv } from '../services/actividadesService'
import { api } from '../services/api'

const tecnicos = ref([])
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
const pageSize = 50
const cargando = ref(false)
const error = ref('')
const exportando = ref(false)

async function cargarTecnicos() {
  const { data } = await api.get('/usuarios', { params: { rol: 'TECNICO' } })
  tecnicos.value = data
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

onMounted(async () => {
  await Promise.all([
    cargarTecnicos(),
    listarEstados().then((r) => (estados.value = r)),
    listarCatalogo('tipos-actividad', { todos: true }).then((r) => (tiposActividad.value = r)),
  ])
  await cargar()
})
</script>

<template>
  <section class="eca-card">
    <h1 class="eca-titulo">Actividades</h1>
    <p class="eca-ayuda">Consulta de actividades de todos los técnicos, con filtros y exportación.</p>

    <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>

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

    <p v-if="cargando" class="eca-ayuda">Cargando…</p>
    <table v-else class="eca-tabla">
      <thead>
        <tr>
          <th>Fecha</th>
          <th>Técnico</th>
          <th>ECA</th>
          <th>Descripción</th>
          <th>GPS</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="a in actividades" :key="a.uuid">
          <td>{{ new Date(a.fecha_hora).toLocaleString() }}</td>
          <td>{{ a.usuario_id }}</td>
          <td>{{ a.eca_id || '—' }}</td>
          <td>{{ a.descripcion }}</td>
          <td>{{ a.estado_gps || '—' }}</td>
          <td><RouterLink :to="{ name: 'actividad-detalle', params: { uuid: a.uuid } }">Ver</RouterLink></td>
        </tr>
      </tbody>
    </table>
    <p class="eca-ayuda">{{ total }} resultado(s).</p>
  </section>
</template>

<style scoped>
.actividades__filtros {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
  margin: 1rem 0;
}
.actividades__filtros select,
.actividades__filtros input {
  padding: 0.5rem 0.7rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid var(--eca-surface-border);
}
.actividades__fecha {
  display: flex;
  flex-direction: column;
  font-size: 0.8rem;
  color: var(--eca-ink-soft);
  gap: 0.2rem;
}
</style>
