<!-- admin-eca — pantalla "Geografía" (ECA-006).
     Árbol estado→municipios, buscador, toggle `activo`. Edición requiere
     `geo.gestionar`; sin ese permiso los toggles quedan deshabilitados
     (el backend igual rechaza el PATCH con 403 si alguien lo forza). -->
<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import {
  listarEstados,
  listarMunicipios,
  actualizarEstadoActivo,
  actualizarMunicipioActivo,
} from '../services/geoService'

const auth = useAuthStore()
const puedeEditar = computed(() => auth.tienePermiso('geo.gestionar'))

const estados = ref([])
const estadoSeleccionadoId = ref(null)
const municipios = ref([])
const busqueda = ref('')
const cargandoEstados = ref(false)
const cargandoMunicipios = ref(false)
const error = ref('')

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

onMounted(cargarEstados)
</script>

<template>
  <section class="eca-card geografia">
    <h1 class="eca-titulo">Geografía</h1>
    <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>

    <div class="geografia__layout">
      <aside class="geografia__estados">
        <h2>Estados</h2>
        <p v-if="cargandoEstados">Cargando…</p>
        <ul v-else>
          <li
            v-for="estado in estados"
            :key="estado.id"
            :class="{ activo: estado.id === estadoSeleccionadoId }"
          >
            <button type="button" @click="seleccionarEstado(estado.id)">
              {{ estado.nombre }}
            </button>
            <label class="geografia__toggle">
              <input
                type="checkbox"
                :checked="estado.activo"
                :disabled="!puedeEditar"
                @change="alternarEstado(estado)"
              />
            </label>
          </li>
        </ul>
      </aside>

      <div class="geografia__municipios">
        <h2>Municipios</h2>
        <input
          v-model="busqueda"
          type="search"
          placeholder="Buscar municipio…"
          :disabled="!estadoSeleccionadoId"
          @input="onBuscar"
        />
        <p v-if="!estadoSeleccionadoId">Selecciona un estado.</p>
        <p v-else-if="cargandoMunicipios">Cargando…</p>
        <p v-else-if="municipios.length === 0">Sin municipios para este estado todavía.</p>
        <ul v-else>
          <li v-for="municipio in municipios" :key="municipio.id">
            <span>{{ municipio.nombre }}</span>
            <label class="geografia__toggle">
              <input
                type="checkbox"
                :checked="municipio.activo"
                :disabled="!puedeEditar"
                @change="alternarMunicipio(municipio)"
              />
            </label>
          </li>
        </ul>
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
  grid-template-columns: 260px 1fr;
  gap: 1.5rem;
  align-items: start;
}
.geografia__estados ul,
.geografia__municipios ul {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 60vh;
  overflow-y: auto;
}
.geografia__estados li,
.geografia__municipios li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.35rem 0.25rem;
}
.geografia__estados li.activo button {
  font-weight: 700;
}
.geografia__estados button {
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  padding: 0;
  flex: 1;
}
.geografia__toggle {
  flex-shrink: 0;
}
</style>
