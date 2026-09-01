<!-- admin-eca — pantalla "Asignaciones" (ECA-009): asignar ECA directas a un
     técnico (buscador + alta/baja) y opción de import CSV. -->
<script setup>
import { ref, onMounted, watch } from 'vue'
import { api } from '../services/api'
import { listarEcas } from '../services/ecasService'
import {
  listarAsignaciones,
  crearAsignacion,
  eliminarAsignacion,
  importarAsignaciones,
} from '../services/asignacionesService'

const tecnicos = ref([])
const tecnicoId = ref(null)
const asignaciones = ref([])

const busquedaEca = ref('')
const resultadosBusqueda = ref([])

const cargando = ref(false)
const error = ref('')
const mensaje = ref('')

const archivoImportar = ref(null)
const importando = ref(false)
const resultadoImportacion = ref(null)

async function cargarTecnicos() {
  const { data } = await api.get('/usuarios', { params: { rol: 'TECNICO' } })
  tecnicos.value = data
}

async function cargarAsignaciones() {
  if (!tecnicoId.value) {
    asignaciones.value = []
    return
  }
  asignaciones.value = await listarAsignaciones({ tecnicoId: tecnicoId.value })
}

let temporizador = null
function onBuscarEca() {
  clearTimeout(temporizador)
  temporizador = setTimeout(async () => {
    if (!busquedaEca.value) {
      resultadosBusqueda.value = []
      return
    }
    const respuesta = await listarEcas({ q: busquedaEca.value, pageSize: 10 })
    resultadosBusqueda.value = respuesta.resultados
  }, 300)
}

async function asignar(eca) {
  if (!tecnicoId.value) return
  error.value = ''
  mensaje.value = ''
  try {
    await crearAsignacion(tecnicoId.value, eca.id)
    mensaje.value = `Asignada: ${eca.nombre}.`
    await cargarAsignaciones()
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'No se pudo asignar.'
  }
}

async function quitar(asignacion) {
  error.value = ''
  try {
    await eliminarAsignacion(asignacion.id)
    await cargarAsignaciones()
  } catch (err) {
    error.value = 'No se pudo quitar la asignación.'
  }
}

async function onImportar() {
  if (!archivoImportar.value) return
  importando.value = true
  error.value = ''
  resultadoImportacion.value = null
  try {
    resultadoImportacion.value = await importarAsignaciones(archivoImportar.value)
  } catch (err) {
    error.value = 'No se pudo importar el archivo.'
  } finally {
    importando.value = false
  }
}

watch(tecnicoId, cargarAsignaciones)

onMounted(async () => {
  cargando.value = true
  try {
    await cargarTecnicos()
  } finally {
    cargando.value = false
  }
})
</script>

<template>
  <section class="eca-card asignaciones">
    <h1 class="eca-titulo">Asignaciones técnico–ECA</h1>
    <p class="eca-ayuda asignaciones__ayuda">
      Cuando un técnico tiene al menos una asignación directa, esas ECA tienen prioridad sobre su
      ámbito geográfico (ver <code>GET /usuarios/me/ecas</code>).
    </p>

    <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>
    <p v-if="mensaje" class="eca-alerta-ok">{{ mensaje }}</p>

    <select v-model="tecnicoId" class="asignaciones__select">
      <option :value="null" disabled>Selecciona un técnico</option>
      <option v-for="t in tecnicos" :key="t.uuid" :value="t.id">
        {{ t.nombre }} {{ t.apellido_paterno }} — {{ t.correo }}
      </option>
    </select>

    <template v-if="tecnicoId">
      <h2 class="eca-titulo">Asignadas actualmente</h2>
      <ul v-if="asignaciones.length" class="asignaciones__lista">
        <li v-for="a in asignaciones" :key="a.uuid">
          ECA #{{ a.eca_id }}
          <button type="button" class="eca-btn eca-btn-peligro" @click="quitar(a)">Quitar</button>
        </li>
      </ul>
      <p v-else class="eca-ayuda">Ninguna todavía.</p>

      <h2 class="eca-titulo">Buscar y asignar</h2>
      <input v-model="busquedaEca" type="search" class="asignaciones__select" placeholder="Buscar ECA por nombre o clave…" @input="onBuscarEca" />
      <ul v-if="resultadosBusqueda.length" class="asignaciones__lista">
        <li v-for="eca in resultadosBusqueda" :key="eca.uuid">
          {{ eca.nombre }}
          <button type="button" class="eca-btn eca-btn-primary" @click="asignar(eca)">Asignar</button>
        </li>
      </ul>
    </template>

    <hr />

    <h2 class="eca-titulo">Importar por CSV</h2>
    <p class="eca-ayuda asignaciones__ayuda">
      Columnas: <code>correo_tecnico</code>, <code>identificador_eca</code> (clave fuente o
      institucional de la ECA).
    </p>
    <input type="file" accept=".csv" @change="(e) => (archivoImportar = e.target.files?.[0] || null)" />
    <button type="button" class="eca-btn eca-btn-secundario" :disabled="!archivoImportar || importando" @click="onImportar">
      {{ importando ? 'Importando…' : 'Importar' }}
    </button>
    <p v-if="resultadoImportacion" class="eca-alerta-ok">
      Asignadas: {{ resultadoImportacion.asignadas }} · Con error: {{ resultadoImportacion.con_error }}
    </p>
  </section>
</template>

<style scoped>
.asignaciones__select {
  padding: 0.5rem 0.7rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid var(--eca-surface-border);
  margin: 0.5rem 0;
}
.asignaciones__lista {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0;
}
.asignaciones__lista li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.25rem 0;
}
</style>
