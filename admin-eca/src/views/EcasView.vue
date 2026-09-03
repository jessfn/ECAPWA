<!-- admin-eca — pantalla "ECA" (ECA-007): tabla con filtros, alta/edición. -->
<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { listarEstados, listarMunicipios } from '../services/geoService'
import { listarEcas, crearEca } from '../services/ecasService'
import AuthIcon from '../components/auth/AuthIcon.vue'

const auth = useAuthStore()
const puedeGestionar = auth.tienePermiso('ecas.gestionar')

const ecas = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 50
const q = ref('')
const estadoId = ref(null)
const municipioId = ref(null)
const estados = ref([])
const municipios = ref([])
const cargando = ref(false)
const error = ref('')

const mostrarFormAlta = ref(false)
const nuevaEca = ref({ nombre: '', estado_id: null, municipio_id: null })
const guardando = ref(false)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const respuesta = await listarEcas({
      estadoId: estadoId.value || undefined,
      municipioId: municipioId.value || undefined,
      q: q.value || undefined,
      page: page.value,
      pageSize,
    })
    ecas.value = respuesta.resultados
    total.value = respuesta.total
  } catch (err) {
    error.value = 'No se pudieron cargar las ECA.'
  } finally {
    cargando.value = false
  }
}

async function onCambioEstado() {
  municipioId.value = null
  municipios.value = estadoId.value ? await listarMunicipios(estadoId.value) : []
  page.value = 1
  cargar()
}

let temporizador = null
function onBuscar() {
  clearTimeout(temporizador)
  temporizador = setTimeout(() => {
    page.value = 1
    cargar()
  }, 300)
}

async function guardarNuevaEca() {
  guardando.value = true
  error.value = ''
  try {
    await crearEca(nuevaEca.value)
    mostrarFormAlta.value = false
    nuevaEca.value = { nombre: '', estado_id: null, municipio_id: null }
    await cargar()
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'No se pudo crear la ECA.'
  } finally {
    guardando.value = false
  }
}

onMounted(async () => {
  estados.value = await listarEstados()
  await cargar()
})
</script>

<template>
  <section>
    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="school" /></span>
      <div class="eca-page-header__texto">
        <h1>ECA</h1>
        <p>Escuelas de Campo registradas, con filtros y alta rápida.</p>
      </div>
      <RouterLink v-if="auth.tienePermiso('ecas.importar')" :to="{ name: 'ecas-importar' }" class="eca-btn eca-btn-secundario ecas__importar">
        Importar CSV/XLSX
      </RouterLink>
    </div>
    <div class="eca-card eca-panel-fusionado ecas">
    <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>

    <div class="ecas__filtros">
      <select v-model="estadoId" @change="onCambioEstado">
        <option :value="null">Todos los estados</option>
        <option v-for="e in estados" :key="e.id" :value="e.id">{{ e.nombre }}</option>
      </select>
      <select v-model="municipioId" :disabled="!estadoId" @change="() => { page = 1; cargar() }">
        <option :value="null">Todos los municipios</option>
        <option v-for="m in municipios" :key="m.id" :value="m.id">{{ m.nombre }}</option>
      </select>
      <input v-model="q" type="search" placeholder="Buscar por nombre o clave…" @input="onBuscar" />
      <button v-if="puedeGestionar" type="button" class="eca-btn eca-btn-primary" @click="mostrarFormAlta = !mostrarFormAlta">
        {{ mostrarFormAlta ? 'Cancelar' : '+ Nueva ECA' }}
      </button>
    </div>

    <form v-if="mostrarFormAlta" class="ecas__alta" @submit.prevent="guardarNuevaEca">
      <input v-model="nuevaEca.nombre" placeholder="Nombre" required />
      <select v-model="nuevaEca.estado_id" required>
        <option :value="null" disabled>Estado</option>
        <option v-for="e in estados" :key="e.id" :value="e.id">{{ e.nombre }}</option>
      </select>
      <select v-model="nuevaEca.municipio_id" required>
        <option :value="null" disabled>Municipio</option>
        <option v-for="m in municipios" :key="m.id" :value="m.id">{{ m.nombre }}</option>
      </select>
      <button type="submit" class="eca-btn eca-btn-primary" :disabled="guardando">Guardar</button>
    </form>

    <p v-if="cargando" class="eca-ayuda">Cargando…</p>
    <table v-else class="eca-tabla ecas__tabla">
      <thead>
        <tr>
          <th>Nombre</th>
          <th>Clave fuente</th>
          <th>Activa</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="eca in ecas" :key="eca.uuid">
          <td>{{ eca.nombre }}</td>
          <td>{{ eca.clave_fuente || '—' }}</td>
          <td>{{ eca.activo ? 'Sí' : 'No' }}</td>
        </tr>
      </tbody>
    </table>
    <p class="eca-ayuda ecas__total">{{ total }} resultado(s).</p>
    </div>
  </section>
</template>

<style scoped>
.ecas__importar {
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.9);
}
.ecas__filtros,
.ecas__alta {
  display: flex;
  gap: 0.5rem;
  margin: 1rem 0;
  flex-wrap: wrap;
}
.ecas__filtros select,
.ecas__filtros input,
.ecas__alta select,
.ecas__alta input {
  padding: 0.5rem 0.7rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid var(--eca-surface-border);
}
</style>
