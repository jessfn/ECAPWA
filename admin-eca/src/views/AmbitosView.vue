<!-- admin-eca — pantalla "Ámbitos" (ECA-008): asignar municipios de trabajo
     a un técnico (selector + toggle por municipio) y opción de import CSV. -->
<script setup>
import { ref, onMounted, watch } from 'vue'
import { api } from '../services/api'
import { listarEstados, listarMunicipios } from '../services/geoService'
import { obtenerAmbito, reemplazarAmbito, importarAmbitos } from '../services/ambitosService'
import AuthIcon from '../components/auth/AuthIcon.vue'

const tecnicos = ref([])
const tecnicoId = ref(null)
const estados = ref([])
const estadoId = ref(null)
const municipios = ref([])
const municipiosSeleccionados = ref(new Set())
const ambitoActual = ref([])

const cargando = ref(false)
const guardando = ref(false)
const error = ref('')
const mensaje = ref('')

const archivoImportar = ref(null)
const importando = ref(false)
const resultadoImportacion = ref(null)

async function cargarTecnicos() {
  const { data } = await api.get('/usuarios', { params: { rol: 'TECNICO' } })
  tecnicos.value = data
}

async function cargarAmbitoActual() {
  if (!tecnicoId.value) {
    ambitoActual.value = []
    return
  }
  ambitoActual.value = await obtenerAmbito(tecnicoId.value)
  municipiosSeleccionados.value = new Set(ambitoActual.value.map((a) => a.municipio_id))
}

async function onCambioEstado() {
  municipios.value = estadoId.value ? await listarMunicipios(estadoId.value) : []
}

function alternarMunicipio(municipioId) {
  const nuevo = new Set(municipiosSeleccionados.value)
  if (nuevo.has(municipioId)) {
    nuevo.delete(municipioId)
  } else {
    nuevo.add(municipioId)
  }
  municipiosSeleccionados.value = nuevo
}

async function guardar() {
  if (!tecnicoId.value) return
  guardando.value = true
  error.value = ''
  mensaje.value = ''
  try {
    ambitoActual.value = await reemplazarAmbito(tecnicoId.value, [...municipiosSeleccionados.value])
    mensaje.value = 'Ámbito actualizado.'
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'No se pudo guardar el ámbito.'
  } finally {
    guardando.value = false
  }
}

async function onImportar() {
  if (!archivoImportar.value) return
  importando.value = true
  error.value = ''
  resultadoImportacion.value = null
  try {
    resultadoImportacion.value = await importarAmbitos(archivoImportar.value)
  } catch (err) {
    error.value = 'No se pudo importar el archivo.'
  } finally {
    importando.value = false
  }
}

watch(tecnicoId, cargarAmbitoActual)

onMounted(async () => {
  cargando.value = true
  try {
    await cargarTecnicos()
    estados.value = await listarEstados()
  } finally {
    cargando.value = false
  }
})
</script>

<template>
  <section>
    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="shield" /></span>
      <div class="eca-page-header__texto">
        <h1>Ámbitos geográficos</h1>
        <p>Municipios de trabajo por técnico.</p>
      </div>
    </div>
    <div class="eca-card eca-panel-fusionado ambitos">
    <p class="eca-ayuda ambitos__ayuda">
      Municipios de trabajo de un técnico. Determina qué ECA ve en campo cuando no tiene
      asignaciones directas.
    </p>

    <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>
    <p v-if="mensaje" class="eca-alerta-ok">{{ mensaje }}</p>

    <div class="ambitos__selector">
      <select v-model="tecnicoId">
        <option :value="null" disabled>Selecciona un técnico</option>
        <option v-for="t in tecnicos" :key="t.uuid" :value="t.id">
          {{ t.nombre }} {{ t.apellido_paterno }} — {{ t.correo }}
        </option>
      </select>
    </div>

    <template v-if="tecnicoId">
      <p class="ambitos__actual">
        Municipios activos actualmente: {{ ambitoActual.map((a) => a.municipio_nombre).join(', ') || 'ninguno' }}
      </p>

      <div class="ambitos__editor">
        <select v-model="estadoId" @change="onCambioEstado">
          <option :value="null">Elige un estado para ver sus municipios</option>
          <option v-for="e in estados" :key="e.id" :value="e.id">{{ e.nombre }}</option>
        </select>

        <ul v-if="municipios.length" class="ambitos__lista">
          <li v-for="m in municipios" :key="m.id">
            <label>
              <input
                type="checkbox"
                :checked="municipiosSeleccionados.has(m.id)"
                @change="alternarMunicipio(m.id)"
              />
              {{ m.nombre }}
            </label>
          </li>
        </ul>

        <button type="button" class="eca-btn eca-btn-primary" :disabled="guardando" @click="guardar">
          {{ guardando ? 'Guardando…' : 'Guardar ámbito' }}
        </button>
      </div>
    </template>

    <hr />

    <h2 class="eca-titulo">Importar por CSV</h2>
    <p class="eca-ayuda ambitos__ayuda">Columnas: <code>correo_tecnico</code>, <code>clave_municipio</code>.</p>
    <div class="ambitos__importar">
      <input type="file" accept=".csv" @change="(e) => (archivoImportar = e.target.files?.[0] || null)" />
      <button type="button" class="eca-btn eca-btn-secundario" :disabled="!archivoImportar || importando" @click="onImportar">
        {{ importando ? 'Importando…' : 'Importar' }}
      </button>
    </div>
    <p v-if="resultadoImportacion" class="eca-alerta-ok">
      Asignadas: {{ resultadoImportacion.asignadas }} · Con error: {{ resultadoImportacion.con_error }}
    </p>
    </div>
  </section>
</template>

<style scoped>
.ambitos__selector select,
.ambitos__editor select {
  padding: 0.5rem 0.7rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid var(--eca-surface-border);
}
.ambitos__selector,
.ambitos__editor,
.ambitos__importar {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin: 1rem 0;
  align-items: flex-start;
}
.ambitos__lista {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 40vh;
  overflow-y: auto;
}
</style>
